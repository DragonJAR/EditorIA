#!/usr/bin/env python3
"""Utilidades compartidas de las herramientas ffmpeg de EditorIA.

Solo stdlib. Localiza ffmpeg/ffprobe en el PATH, los ejecuta con errores
claros y ofrece un probe compacto que usa cada script.

Adaptado de las mecánicas de ffmpeg-skill (alfred-lau): orden recomendado
(color -> corte -> union -> silencio -> encuadre -> subtitulos -> sync ->
audio -> loudness -> exportacion), probe-first de los inputs, --dry-run con
JSON, nunca sobrescribir el input, verificar el output y QA con frames.
"""
import argparse  # noqa: F401  (anotaciones de add_common/apply_common)
import json
import os
import platform
import shutil
import subprocess
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

for _extra_bin in ("/opt/homebrew/bin", "/usr/local/bin"):
    if os.path.isdir(_extra_bin) and _extra_bin not in os.environ.get("PATH", "").split(os.pathsep):
        os.environ["PATH"] = _extra_bin + os.pathsep + os.environ.get("PATH", "")

INSTALL_HINTS = {
    "Linux": "  Debian/Ubuntu: sudo apt install ffmpeg\n  Fedora:        sudo dnf install ffmpeg",
    "Darwin": "  brew install ffmpeg",
    "Windows": "  winget install Gyan.FFmpeg\n  o descarga de https://ffmpeg.org/download.html y agregalo al PATH",
}


class Context:
    """Ajustes por proceso que activan los flags comunes (--dry-run, --json)."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.dry_run = False   # imprimir comandos, no ejecutar
        self.json = False      # emitir JSON en vez de la ruta del output
        self.commands: List[str] = []

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default) if key in ("dry_run", "json", "commands") else default


STATE = Context()


ERROR_KINDS = ("input", "ffmpeg", "output", "missing_tool", "timeout",
                 "verification", "interrupted", "error")


def leer_json(ruta: str, que: str = "el archivo") -> Any:
    """Carga un JSON con error CLARO si no existe o está mal formado (con
    línea y columna): un agente lee el mensaje y corrige, no un traceback."""
    if not os.path.isfile(ruta):
        sys.exit(f"ERROR: {que} no existe: {ruta}")
    try:
        with open(ruta, encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        sys.exit(f"ERROR: {que} no es JSON válido ({ruta}, línea {exc.lineno}, columna {exc.colno}): {exc.msg}")


def die(msg: str, code: int = 1, kind: str = "error") -> "None":
    """Imprime el error en stderr y sale con codigo distinto de 0.

    kind: taxonomia del fallo (input = el archivo/argumento esta mal,
    ffmpeg = fallo ffmpeg/ffprobe, output = no se escribio el resultado,
    missing_tool = falta un binario, timeout, verification, interrupted).
    Con --json el error sale como documento estructurado en stdout.
    """
    if kind not in ERROR_KINDS:
        kind = "error"
    if STATE.json:
        print_json({"status": "failed",
                    "error": {"kind": kind, "message": msg}})
    else:
        sys.stderr.write(f"ERROR: {msg}\n")
    sys.exit(code)


def info(msg: str) -> None:
    sys.stderr.write(f"{msg}\n")


def require_tool(name: str) -> str:
    """Ruta absoluta de ffmpeg/ffprobe, o sale con instrucciones de instalacion."""
    path = shutil.which(name)
    if path:
        return path
    hint = INSTALL_HINTS.get(platform.system(), "  Ver https://ffmpeg.org/download.html")
    die(f"no se encontro '{name}' en el PATH.\nInstala FFmpeg (incluye ffprobe):\n{hint}", code=127)


def shell_quote(s: str) -> str:
    if not s or any(ch in s for ch in " \t\\\"';|&<>()[]{}$*?"):
        return "'" + s.replace("'", "'\\''") + "'"
    return s


def _cmdline(cmd: Sequence[str]) -> str:
    return " ".join(shell_quote(c) for c in cmd)


def _is_ffmpeg(cmd: Sequence[str]) -> bool:
    return os.path.basename(cmd[0]).startswith("ffmpeg")


def _cleanup_partial_output(cmd: Sequence[str]) -> None:
    """Si un ffmpeg fallo despues de abrir el contenedor de salida, borra el
    archivo parcial para que no se confunda con un resultado valido."""
    # SOLO ffmpeg escribe salidas: en ffprobe el último argumento es la ENTRADA
    # (un probe fallido sobre un archivo corrupto o un .json lo borraba: pérdida
    # de datos). Y nunca un archivo que el comando lee (-i).
    if os.path.splitext(os.path.basename(str(cmd[0])))[0].lower() != "ffmpeg":
        return
    output = cmd[-1]
    if output in {cmd[i + 1] for i, a in enumerate(cmd[:-1]) if a == "-i"}:
        return
    if output in ("-", "pipe:0", "pipe:1") or output.startswith("pipe:") or output.startswith("-"):
        return
    try:
        if os.path.exists(output):
            os.remove(output)
    except OSError:
        pass


def _check_no_overwrite_input(cmd: Sequence[str]) -> None:
    """Rechaza un comando cuya salida resuelva al mismo archivo que un input."""
    output = cmd[-1]
    if output in ("-", "pipe:0", "pipe:1") or output.startswith("pipe:") or output.startswith("-"):
        return
    try:
        out_real = os.path.realpath(output)
    except OSError:
        return
    for i, a in enumerate(cmd):
        if a == "-i" and i + 1 < len(cmd):
            try:
                if os.path.realpath(cmd[i + 1]) == out_real:
                    die(f"rechazado: la salida {output!r} es el mismo archivo que el input "
                        f"{cmd[i + 1]!r} (ffmpeg lo sobrescribiria mientras lo lee). Usa otro -o")
            except OSError:
                continue


def run(cmd: Sequence[str], *, quiet: bool = False, check: bool = True) -> subprocess.CompletedProcess:
    """Ejecuta un comando y muestra su linea en stderr. Con check=True sale con
    error si falla. En --dry-run, los comandos ffmpeg no se ejecutan."""
    is_ffmpeg = _is_ffmpeg(cmd)
    if is_ffmpeg:
        _check_no_overwrite_input(cmd)
        STATE.commands.append(_cmdline(cmd))
    if not quiet:
        info(("[dry-run] $ " if STATE.dry_run and is_ffmpeg else "$ ") + _cmdline(cmd))
    if STATE.dry_run and is_ffmpeg:
        return subprocess.CompletedProcess(list(cmd), 0, "", "")
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        _cleanup_partial_output(cmd)
        if check:
            tail = "\n".join(proc.stderr.strip().splitlines()[-12:])
            die(f"comando fallo (codigo {proc.returncode}): {cmd[0]}\n{tail}"
                + _pista_libass(cmd, proc.stderr))
    return proc


def _pista_libass(cmd, stderr):
    """El motivo real cuando falta libass en el ffmpeg.

    Sin este filtro, ffmpeg responde "No option name near 'sub.srt:...'", que
    no dice nada util: el agente no sabe que le falta `ffmpeg-full` ni que el
    motor propio (PIL) sigue funcionando. `check_env.py` ya avisa al
    arrancar; aqui se dice en el momento en que algo falla.
    """
    filtros = ("subtitles=", "ass=", "drawtext=")
    if not any(f in " ".join(cmd) for f in filtros):
        return ""
    if "No option name near" not in stderr and "No such filter" not in stderr:
        return ""
    return ("\nAVISO: este ffmpeg no trae los filtros de texto (libass). "
            "El motor propio (PIL) sigue bien; solo los subtitulos quemados fallan.\n"
            "      arreglo: brew install ffmpeg-full  (keg-only). Las herramientas\n"
            "      lo encuentran solas: no hace falta exportar PATH.")


# ---------- filtros de texto (libass + libfreetype) ----------
# El ffmpeg de Homebrew NO trae libass. `brew install ffmpeg-full` lo deja
# keg-only (sin symlink), de modo que el primer ffmpeg del PATH sigue siendo
# el que NO tiene drawtext/ass/subtitles. El remedio que documenta la skill
# (export PATH=...) no sirve dentro de un agente: cada llamada de shell es un
# proceso nuevo, el export no persiste entre llamadas. Por eso el resolver
# busca el binario CON los filtros por su cuenta.
FILTROS_TEXTO = ("ass", "subtitles", "drawtext")
_filtros_cache: Dict[str, bool] = {}


def _filtro_en_listado(listado: str, filtro: str) -> bool:
    """True si el listado de `-filters` trae ese filtro.

    Cada filtro sale como " T. drawtext   V->V   descripcion": se compara el
    nombre justo antes de la flecha, nunca dentro del texto descriptivo
    (donde "libass" o "subtitles" aparecen citados sin ser filtros).
    """
    for linea in listado.splitlines():
        partes = linea.split()
        if len(partes) >= 3 and partes[1] == filtro and "->" in partes[2]:
            return True
    return False


def tiene_filtros_texto(ruta: str) -> bool:
    """True si ese ffmpeg trae los tres filtros de texto."""
    if ruta in _filtros_cache:
        return _filtros_cache[ruta]
    try:
        r = subprocess.run([ruta, "-hide_banner", "-filters"],
                           capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        _filtros_cache[ruta] = False
        return False
    listado = (r.stdout or "") + (r.stderr or "")
    ok = all(_filtro_en_listado(listado, f) for f in FILTROS_TEXTO)
    _filtros_cache[ruta] = ok
    return ok


def _candidatos_ffmpeg() -> List[str]:
    """Binarios ffmpeg que pueden traer libass, en orden de preferencia."""
    vistos: List[str] = []

    def _add(ruta: Optional[str]) -> None:
        if (ruta and ruta not in vistos and os.path.isfile(ruta)
                and os.access(ruta, os.X_OK)):
            vistos.append(ruta)

    _add(shutil.which("ffmpeg"))
    # ffmpeg-full de Homebrew es keg-only: no hay symlink, no esta en el PATH.
    prefijos = [os.environ.get("HOMEBREW_PREFIX", "")]
    prefijos += ["/opt/homebrew", "/usr/local", "/home/linuxbrew/.linuxbrew"]
    for prefijo in prefijos:
        if not prefijo:
            continue
        _add(os.path.join(prefijo, "opt", "ffmpeg-full", "bin", "ffmpeg"))
        # La version puede cambiar: se toma la mas nueva instalada.
        cellar = os.path.join(prefijo, "Cellar", "ffmpeg-full")
        if os.path.isdir(cellar):
            for version in sorted(os.listdir(cellar), reverse=True):
                _add(os.path.join(cellar, version, "bin", "ffmpeg"))
    _add(shutil.which("ffmpeg-full"))
    return vistos


def ffmpeg_con_texto() -> Optional[str]:
    """Ruta del primer ffmpeg que trae los filtros de texto, o None.

    None significa: en esta maquina no hay ningun ffmpeg con libass (ni en el
    PATH ni en un keg de ffmpeg-full). `check_env.py` lo dice al arrancar.
    """
    for ruta in _candidatos_ffmpeg():
        if tiene_filtros_texto(ruta):
            return ruta
    return None


def ffmpeg_texto() -> str:
    """Ruta de un ffmpeg con los filtros de texto (ass/subtitles/drawtext).

    Si no hay ninguno (no instalado ffmpeg-full), devuelve el ffmpeg del PATH:
    la herramienta falla con el error de ffmpeg y `_pista_libass` explica el
    arreglo. Nunca se queda mudo.
    """
    return ffmpeg_con_texto() or require_tool("ffmpeg")


def ffmpeg_base(overwrite: bool = True, *, texto: bool = False) -> List[str]:
    """Base del comando ffmpeg. `texto=True` elige un binario con libass."""
    ffmpeg = ffmpeg_texto() if texto else require_tool("ffmpeg")
    cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin"]
    cmd.append("-y" if overwrite else "-n")
    return cmd


MEDIA_EXT = {".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi", ".ts", ".mts", ".gif",
             ".wav", ".flac", ".mp3", ".m4a", ".aac", ".ogg", ".opus", ".png", ".jpg", ".jpeg"}

AUDIO_CODECS = {
    ".wav": ["-c:a", "pcm_s16le"],
    ".flac": ["-c:a", "flac"],
    ".mp3": ["-c:a", "libmp3lame", "-q:a", "0"],
    ".m4a": ["-c:a", "aac", "-b:a", "256k"],
    ".aac": ["-c:a", "aac", "-b:a", "256k"],
    ".ogg": ["-c:a", "libvorbis", "-q:a", "6"],
    ".opus": ["-c:a", "libopus", "-b:a", "128k"],
}


def is_audio_output(output_path: str) -> bool:
    """True si la extension de salida es un contenedor solo de audio."""
    return os.path.splitext(output_path)[1].lower() in AUDIO_CODECS


def audio_codec_for(output_path: str, default_bitrate: str = "192k") -> List[str]:
    """Elige un codec de audio que el contenedor de salida pueda contener."""
    ext = os.path.splitext(output_path)[1].lower()
    return list(AUDIO_CODECS.get(ext, ["-c:a", "aac", "-b:a", default_bitrate]))


def _output_failed(path: str, why: str) -> "None":
    try:
        if os.path.exists(path) and os.path.getsize(path) == 0:
            os.remove(path)
            why += " (archivo vacio borrado)"
    except OSError:
        pass
    die(f"verificacion del output fallo: {path}: {why}")


def verify_output(path: str) -> Dict[str, Any]:
    """Criterio de exito: el archivo existe, no esta vacio y ffprobe lee al
    menos un stream. Borra archivos vacios para que no pasen como resultados."""
    if not os.path.exists(path):
        _output_failed(path, "no se escribio")
    if os.path.getsize(path) == 0:
        _output_failed(path, "0 bytes")
    if os.path.splitext(path)[1].lower() not in MEDIA_EXT:
        return {}
    meta = probe(path, role="output")
    if not meta.get("video") and not meta.get("audio"):
        _output_failed(path, "sin streams de video ni audio")
    return meta


def _to_float(v: Any) -> Optional[float]:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _to_int(v: Any) -> Optional[int]:
    try:
        return int(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _fraction(v: Optional[str]) -> Optional[Fraction]:
    if not v or v in ("0/0", "0"):
        return None
    try:
        f = Fraction(v)
        return f if f > 0 else None
    except (ValueError, ZeroDivisionError):
        return None


def probe(path: str, role: str = "input") -> Dict[str, Any]:
    """Descripcion compacta del archivo: formato, duracion, video y audio."""
    if not os.path.exists(path):
        if role == "output":
            _output_failed(path, "no se escribio")
        die(f"input no encontrado: {path}", kind="input")
    ffprobe = require_tool("ffprobe")
    proc = run([ffprobe, "-v", "error", "-print_format", "json",
                "-show_format", "-show_streams", path], quiet=True, check=False)
    if proc.returncode != 0:
        if role == "output":
            _output_failed(path, f"ffprobe no puede leerlo:\n{proc.stderr.strip()}")
        die(f"ffprobe fallo en {path}:\n{proc.stderr.strip()}", kind="ffmpeg")
    raw = json.loads(proc.stdout or "{}")
    fmt = raw.get("format", {})
    streams = raw.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"
                  and s.get("disposition", {}).get("attached_pic", 0) == 0), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)

    duration = _to_float(fmt.get("duration"))
    if duration is None and video:
        duration = _to_float(video.get("duration"))
    if duration is None and audio:
        duration = _to_float(audio.get("duration"))

    out: Dict[str, Any] = {
        "file": path,
        "format": fmt.get("format_name"),
        "duration": duration,
        "size_bytes": _to_int(fmt.get("size")),
        "bitrate": _to_int(fmt.get("bit_rate")),
        "video": None,
        "audio": None,
        "subtitle_streams": sum(1 for s in streams if s.get("codec_type") == "subtitle"),
        "audio_streams": [{
            "index": n,
            "codec": a.get("codec_name"),
            "channels": _to_int(a.get("channels")),
            "sample_rate": _to_int(a.get("sample_rate")),
            "language": (a.get("tags") or {}).get("language"),
        } for n, a in enumerate(s for s in streams if s.get("codec_type") == "audio")],
    }
    if video:
        r_rate = _fraction(video.get("r_frame_rate"))
        avg_rate = _fraction(video.get("avg_frame_rate"))
        fps = float(avg_rate) if avg_rate else (float(r_rate) if r_rate else None)
        vfr = bool(r_rate and avg_rate and abs(float(r_rate) - float(avg_rate)) > 0.01)
        trc = video.get("color_transfer") or ""
        prim = video.get("color_primaries") or ""
        hdr = trc in ("smpte2084", "arib-std-b67") or prim == "bt2020"
        rotation = 0
        if "rotate" in (video.get("tags") or {}):
            try:
                rotation = int(video["tags"]["rotate"])
            except ValueError:
                pass
        out["video"] = {
            "codec": video.get("codec_name"),
            "width": _to_int(video.get("width")),
            "height": _to_int(video.get("height")),
            "fps": round(fps, 3) if fps else None,
            "variable_frame_rate_suspected": vfr,
            "pix_fmt": video.get("pix_fmt"),
            "hdr": hdr,
            "color_transfer": trc,
            "color_primaries": prim,
            "color_space": video.get("color_space"),
            "rotation": rotation,
        }
    if audio:
        out["audio"] = {
            "codec": audio.get("codec_name"),
            "channels": _to_int(audio.get("channels")),
            "channel_layout": audio.get("channel_layout"),
            "sample_rate": _to_int(audio.get("sample_rate")),
            "bitrate": _to_int(audio.get("bit_rate")),
        }
    return out


def default_output(input_path: str, suffix: str, ext: Optional[str] = None) -> str:
    p = Path(input_path)
    new_ext = ext if ext else p.suffix.lstrip(".") or "mp4"
    return str(p.with_name(f"{p.stem}_{suffix}.{new_ext}"))


def add_common(ap: "argparse.ArgumentParser") -> None:
    """Agrega los flags que comparten todos los scripts."""
    g = ap.add_argument_group("opciones generales")
    g.add_argument("--dry-run", action="store_true",
                   help="muestra los comandos ffmpeg que se ejecutarian, sin ejecutar nada")
    g.add_argument("--json", action="store_true",
                   help="imprime un documento JSON con el resultado en vez de la ruta")


def apply_common(args: "argparse.Namespace") -> None:
    STATE.dry_run = bool(getattr(args, "dry_run", False))
    STATE.json = bool(getattr(args, "json", False))


def emit(output: Optional[str], **extra: Any) -> None:
    """Ultima linea en stdout: la ruta del output, o un JSON con --json."""
    if STATE.json:
        doc: Dict[str, Any] = {"status": "completed", "output": output,
                               "dry_run": STATE.dry_run, "commands": list(STATE.commands)}
        doc.update(extra)
        print_json(doc)
    elif output:
        print(output)


def print_json(obj: Any) -> None:
    sys.stdout.write(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def info_ok(msg: str) -> None:
    """Estilo EditorIA: prints claros de exito."""
    print(f"OK {msg}")


X264_PRESETS = ("ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow", "placebo")


def x264_args(crf: int = 18, preset: str = "medium", keep_bt709: bool = True) -> List[str]:
    args = ["-c:v", "libx264", "-preset", preset, "-crf", str(crf),
            "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
    if keep_bt709:
        args += ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709"]
    return args


# Fuentes RGB (frames PNG de PIL, filtros show*) -> YUV. Sin out_color_matrix,
# swscale convierte con la matriz BT.601 y el archivo sale sin etiqueta; los
# players tratan todo lo HD como BT.709 y el color de marca se desplaza
# (medido: el acento neutro (232,72,12) se veia (244,82,6)). Un solo lugar.
VF_RGB_A_BT709 = "scale=out_color_matrix=bt709:out_range=tv"


def h264_desde_rgb(crf: int = 20, preset: str = "medium") -> List[str]:
    """Args de encode para frames RGB: conversion BT.709 exacta + etiquetas."""
    return ["-vf", f"{VF_RGB_A_BT709},format=yuv420p"] + x264_args(crf, preset)


# Entregables con canal alfa (overlays para NLE/OBS/web). H.264 no tiene alfa.
ALFA_ENC = {
    ".webm": ["-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-auto-alt-ref", "0",
              "-crf", "20", "-b:v", "0", "-row-mt", "1"],
    ".mov": ["-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le",
             "-vendor", "apl0"],
}


def verificar_alfa(path: str, frame: Optional[int] = None) -> float:
    """Confirma que el archivo LLEVA alfa: etiqueta del stream (WebM alpha_mode=1,
    ProRes pix_fmt yuva*) y un frame decodificado mayormente transparente.
    El decoder nativo de ffmpeg para VP9 descarta el alfa: hay que forzar
    libvpx-vp9 al leer. Devuelve la fraccion transparente del frame."""
    ext = os.path.splitext(path)[1].lower()
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=pix_fmt,nb_frames:stream_tags=alpha_mode,ALPHA_MODE",
                        "-of", "default=nw=1", path], capture_output=True, text=True)
    tags = r.stdout.lower()
    if not ("alpha_mode=1" in tags if ext == ".webm" else "pix_fmt=yuva" in tags):
        die(f"{path} se escribio SIN canal alfa ({tags.strip()}); el build de ffmpeg "
            "no soporta alfa en este codec", kind="verification")
    if frame is None:   # el centro del clip: el hold, no el frame 0 (vacio)
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                            "-count_packets", "-show_entries", "stream=nb_read_packets",
                            "-of", "csv=p=0", path], capture_output=True, text=True)
        frame = int(r.stdout.strip() or 0) // 2
    dec = ["-c:v", "libvpx-vp9"] if ext == ".webm" else []
    raw = subprocess.run(["ffmpeg", "-v", "error", *dec, "-i", path, "-vf",
                          f"select=eq(n\\,{frame})", "-frames:v", "1", "-f", "rawvideo",
                          "-pix_fmt", "rgba", "-"], capture_output=True).stdout
    if not raw:
        die(f"no se pudo decodificar el frame {frame} de {path}", kind="verification")
    claros = sum(1 for i in range(3, len(raw), 4) if raw[i] == 0)
    return claros / (len(raw) / 4)


def codificar_frames(patron: str, fps: float, salida: str, crf: int = 20,
                     preset: str = "medium") -> Dict[str, Any]:
    """Frames RGB(A) numerados -> video. La extension decide el entregable:
    .mp4 = H.264 BT.709 exacto (sin alfa); .webm = VP9 con alfa (OBS, Chrome);
    .mov = ProRes 4444 con alfa (Premiere, Resolve, Final Cut)."""
    ext = os.path.splitext(salida)[1].lower()
    enc = ALFA_ENC.get(ext) or h264_desde_rgb(crf, preset)
    run(ffmpeg_base() + ["-framerate", str(fps), "-i", patron, *enc, "-an", salida],
        quiet=True)
    res: Dict[str, Any] = {"salida": salida, "alfa": ext in ALFA_ENC}
    if ext in ALFA_ENC:
        res["transparente"] = round(verificar_alfa(salida), 3)
    return res


def video_args(meta: Optional[Dict[str, Any]], crf: int = 18, preset: str = "medium") -> List[str]:
    """Args de codificacion que preservan lo que la fuente es: SDR -> H.264 8-bit
    etiquetado BT.709; HDR (HDR10/PQ, HLG, BT.2020) -> HEVC Main10 con las
    etiquetas de color de la fuente para no entregar un HDR lavado."""
    v = (meta or {}).get("video") or {}
    if not v.get("hdr"):
        return x264_args(crf, preset)
    cs = v.get("color_space") or "bt2020nc"
    prim = v.get("color_primaries") or "bt2020"
    trc = v.get("color_transfer") or "arib-std-b67"
    if trc == "smpte2084":
        x265 = f"log-level=error:colorprim={prim}:transfer={trc}:colormatrix={cs}:range=limited:hdr10-opt=1"
    else:
        x265 = f"log-level=error:colorprim={prim}:transfer={trc}:colormatrix={cs}"
    return ["-c:v", "libx265", "-preset", preset, "-crf", str(crf + 2), "-pix_fmt", "yuv420p10le",
            "-tag:v", "hvc1", "-x265-params", x265, "-colorspace", cs,
            "-color_primaries", prim, "-color_trc", trc, "-movflags", "+faststart"]


def aac_args(bitrate: str = "192k") -> List[str]:
    return ["-c:a", "aac", "-b:a", bitrate]


def cfr_args(meta: Optional[Dict[str, Any]], fps: Optional[float] = None) -> List[str]:
    """Fuerza frame rate constante si la fuente parece VFR (o se da fps)."""
    v = (meta or {}).get("video") or {}
    if fps is None and not v.get("variable_frame_rate_suspected"):
        return []
    rate = fps or v.get("fps") or 30.0
    rate = round(rate) if abs(rate - round(rate)) < 0.02 else rate
    return ["-fps_mode", "cfr", "-r", f"{rate:g}"]


def db_to_linear(db: float) -> float:
    return 10 ** (db / 20.0)


class MissingFpsError(ValueError):
    """parse_time() vio un timecode SMPTE hh:mm:ss:ff pero no se dio fps."""


def parse_time(value: str, fps: Optional[float] = None) -> float:
    """Acepta segundos ('12.5'), mm:ss ('1:30'), hh:mm:ss(.ms) ('00:01:30.250'),
    SRT '00:01:30,250', o -- con `fps` -- timecode SMPTE 'hh:mm:ss:ff'."""
    v = value.strip().replace(",", ".")
    if not v:
        raise ValueError("tiempo vacio")
    parts = v.split(":")
    if len(parts) == 4:
        if fps is None or fps <= 0:
            raise MissingFpsError(f"'{value}' parece timecode SMPTE hh:mm:ss:ff, pero no se dio fps")
        h, m, s, f = parts
        frame, whole_fps = int(f), int(round(fps))
        if not (0 <= frame < whole_fps):
            raise ValueError(f"timecode SMPTE malo '{value}' para {fps:g} fps")
        return int(h) * 3600 + int(m) * 60 + int(s) + frame / fps
    if len(parts) > 3:
        raise ValueError(f"tiempo malo: {value}")
    total = 0.0
    for part in parts:
        total = total * 60 + float(part)
    return total


def fmt_srt_time(seconds: float) -> str:
    if seconds < 0:
        seconds = 0.0
    ms = int(round(seconds * 1000))
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def fmt_smpte_time(seconds: float, fps: float) -> str:
    """Timecode SMPTE non-drop-frame 'hh:mm:ss:ff'."""
    if seconds < 0:
        seconds = 0.0
    whole_fps = int(round(fps))
    total_frames = int(round(seconds * fps))
    frame = total_frames % whole_fps
    secs_total = total_frames // whole_fps
    h, rem = divmod(secs_total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}:{frame:02d}"


def escape_filter_path(path: str) -> str:
    """Escapa una ruta para usarla como valor de opcion de filtro
    (subtitles=, ass=, fontfile=): sobrevive las dos pasadas del parser."""
    p = str(Path(path))
    p = p.replace("\\", "/")
    p = p.replace(":", "\\\\:")
    for ch in ("'", ",", ";", "[", "]"):
        p = p.replace(ch, "\\" + ch)
    return p


def escape_drawtext(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\\\\\'")
        .replace("%", "\\%")
        .replace(",", "\\,")
        .replace("[", "\\[")
        .replace("]", "\\]")
    )


def default_font_file(font_name: str) -> Optional[str]:
    """Resuelve `font_name` a un archivo de fuente en disco, para usar
    fontfile=<path> en drawtext en vez de font=<nombre>.

    Portable: busca en los directorios de fuentes del SO (Windows/macOS/Linux)
    y usa fc-match como fallback en Unix. Devuelve None si no hay coincidencia.

    El import de `_plataforma` tiene que servir en los DOS contextos: este
    modulo se importa como parte del paquete `ffmpeg_tools` (alguien hace
    `from ffmpeg_tools._comun import ...`) o como modulo suelto (los scripts
    de ffmpeg_tools meten su carpeta en sys.path y hacen `from _comun import
    ...`, que es como se ejecutan desde la linea de comandos). Con el import
    RELATIVO a secas, el segundo caso reventaba con "attempted relative
    import with no known parent package" en cuanto se pedia una fuente: tres
    herramientas (look.py, scenes.py y shorts_plan.py) se caian al usarse
    tal como las documenta la skill.
    """
    try:
        from . import _plataforma as _plat
    except ImportError:      # importado como modulo suelto (sys.path)
        import _plataforma as _plat
    # Incluye la sans genérica del SO como último recurso dentro de la misma llamada.
    return _plat.resolver_fuente(font_name, generica="sans")


def color_hex(value: str) -> str:
    """Normaliza '#ffd200' / 'ffd200' / '0xFFD200' a 'FFD200'."""
    v = str(value).strip().lstrip("#")
    if v.lower().startswith("0x"):
        v = v[2:]
    if len(v) != 6:
        die(f"el color debe ser RRGGBB, recibido '{value}'")
    return v.upper()


def hex_a_rgb(value: str) -> Tuple[int, int, int]:
    """Convierte '#E8480C' / 'E8480C' / '0xE8480C' a una tupla RGB (R, G, B) 0-255.
    Una sola fuente de verdad (DRY): la usan render_plan.py, thumbnail.py y resto
    del kit. Marca-blanca: la entrada sale del brand pack, no de un default quemado.
    """
    h = color_hex(value)
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def rgb_a_hex(color) -> str:
    """Convierte una tupla RGB (R, G, B) 0-255 a '#E8480C'.

    La vuelta de `hex_a_rgb`: una sola fuente de verdad para las dos
    direcciones (DRY). Los tokens de la identidad son tuplas; un filtro de
    ffmpeg los quiere en hex.
    """
    r, g, b = (int(v) for v in tuple(color)[:3])
    return "#%02X%02X%02X" % (r, g, b)


# Cadencia (references/ritmo.md, falla 1): coeficiente de variación mínimo de las
# duraciones de toma. Debajo, la pieza es un metrónomo. Fuente única: la usan
# verificar_ritmo.py (sobre el video) y auditar_plan.py (sobre el plan).
CV_MIN_CADENCIA = 0.25


def _como_rgb(c) -> Tuple[int, int, int]:
    return hex_a_rgb(c) if isinstance(c, str) else tuple(int(v) for v in c[:3])


def luminancia(color) -> float:
    """Luminancia relativa WCAG 2.x (0 negro .. 1 blanco) de '#RRGGBB' o (r,g,b)."""
    def lin(v: int) -> float:
        s = v / 255.0
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(v) for v in _como_rgb(color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contraste(a, b) -> float:
    """Relación de contraste WCAG entre dos colores (1.0 igual .. 21.0 negro/blanco).
    Piso: texto 4.5:1, texto grande y acentos 3:1 (references/checklist-qa.md)."""
    la, lb = luminancia(a), luminancia(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


#: El texto claro y el oscuro de la skill. Entre los dos se elige el que se
#: lee sobre el fondo que toque: el claro para fondos oscuros, el oscuro para
#: fondos claros (un acento de marca puede ser cualquiera de los dos).
TEXTO_CLARO = "#FAF8F6"
TEXTO_OSCURO = "#0A0A0A"


def _mejor_contraste(fondo, a, b) -> str:
    """El de MAS contraste entre los dos colores, con el piso de 4.5:1.

    Si ninguno llega al piso se queda con el mejor: es mejor un texto por
    debajo del piso que un texto invisible.
    """
    ca, cb = contraste(a, fondo), contraste(b, fondo)
    if ca >= 4.5 and ca >= cb:
        return a
    if cb >= 4.5:
        return b
    return a if ca >= cb else b


def texto_sobre(fondo, claro=TEXTO_CLARO, oscuro=TEXTO_OSCURO, tokens=None) -> str:
    """El color de texto que se lee sobre `fondo` (piso 4.5:1).

    Un texto con color FIJO sobre un fondo que cambia es una letra ilegible
    esperando: el hook de un short va sobre un box del ACENTO de la marca, y
    el acento lo elige el usuario. Con blanco fijo, menta daba 2:1 y el
    titular no se leia; ahora el texto sigue al fondo.

    Elige el de MAS contraste entre los dos, y solo lo baja del piso si
    ningun color llega (aun asi se queda con el mejor).

    `tokens` es la identidad de la pieza (pack de marca o paleta): su TINTA
    (blanco/negro de la marca) va primero, porque el motor ya la instala
    (BLANCO) y el hook tiene que llevar la misma; con la tinta neutra de la
    skill, el titular de una marca ajena se sale de su identidad. Si la tinta
    de la marca no llega al piso sobre ese fondo, se cae a la neutra: la
    legibilidad no se negocia.
    """
    if tokens is not None:
        tinta = _mejor_contraste(fondo, rgb_a_hex(tokens["blanco"]), rgb_a_hex(tokens["negro"]))
        if contraste(tinta, fondo) >= 4.5:
            return tinta
    return _mejor_contraste(fondo, claro, oscuro)


# ---------- identidad: modo libre por defecto, el brand pack solo si se pide ----------
# Ninguna marca concreta vive en el código; sus valores están solo en su
# brand/*.json (references/brand-packs.md).

# CATÁLOGO DE PALETAS (modo libre) — una entrada por armonía cromática.
# Cada paleta es un juego completo de tokens (acento, acento_oscuro, fondo,
# tinta, gris, superficie) más la armonía que la justifica, su temperatura y
# para qué tipo de brief encaja. El agente elige UNA por pieza, según el
# brief, y la declara en el plan ("paleta": "menta"). Reglas y tabla de
# decisión: references/paleta.md.
#
# Todos los acentos pasan WCAG AA (>= 4.5:1) sobre el fondo #0A0A0A: el
# acento se usa para texto de énfasis, no para pintar.
PALETAS: Dict[str, Dict[str, Any]] = {
    "electrico": {
        "acento": (61, 123, 255), "acento_oscuro": (32, 68, 148),
        "negro": (10, 10, 10), "blanco": (250, 248, 246), "gris": (170, 170, 170),
        "gris_superficie": (26, 26, 26),
        "esquema": "análogo azul→cian (hue 214°)",
        "tono": "frío", "para": "IA, software, datos, B2B, SaaS, ciberseguridad",
    },
    "menta": {
        "acento": (20, 199, 160), "acento_oscuro": (13, 129, 104),
        "negro": (10, 10, 10), "blanco": (250, 248, 246), "gris": (170, 170, 170),
        "gris_superficie": (26, 26, 26),
        "esquema": "análogo verde→turquesa (hue 168°)",
        "tono": "frío", "para": "finanzas, salud, crecimiento, clima, logística verde",
    },
    "grafito": {
        "acento": (148, 163, 184), "acento_oscuro": (95, 107, 124),
        "negro": (10, 10, 10), "blanco": (250, 248, 246), "gris": (170, 170, 170),
        "gris_superficie": (26, 26, 26),
        "esquema": "monocromático frío, sin chroma (hue 215°, sat 12 %)",
        "tono": "frío", "para": "documentación, legal, industria, auditoría, minimal",
    },
    "ambar": {
        "acento": (240, 163, 43), "acento_oscuro": (156, 106, 28),
        "negro": (10, 10, 10), "blanco": (250, 248, 246), "gris": (170, 170, 170),
        "gris_superficie": (26, 26, 26),
        "esquema": "análogo ámbar→dorado (hue 38°)",
        "tono": "cálido", "para": "energía, industria, deporte, formación, startups",
    },
    "coral": {
        "acento": (255, 107, 91), "acento_oscuro": (166, 70, 59),
        "negro": (10, 10, 10), "blanco": (250, 248, 246), "gris": (170, 170, 170),
        "gris_superficie": (26, 26, 26),
        "esquema": "análogo coral→rojo cálido (hue 6°)",
        "tono": "cálido", "para": "salud, RRHH, cuidado, comunidad, alertas",
    },
    "violeta": {
        "acento": (139, 92, 246), "acento_oscuro": (91, 60, 161),
        "negro": (10, 10, 10), "blanco": (250, 248, 246), "gris": (170, 170, 170),
        "gris_superficie": (26, 26, 26),
        "esquema": "análogo violeta→lila (hue 265°)",
        "tono": "frío", "para": "creatividad, educación, premium, wellness, música",
    },
    "magenta": {
        "acento": (229, 71, 155), "acento_oscuro": (149, 46, 101),
        "negro": (10, 10, 10), "blanco": (250, 248, 246), "gris": (170, 170, 170),
        "gris_superficie": (26, 26, 26),
        "esquema": "análogo magenta→fucsia (hue 330°)",
        "tono": "cálido", "para": "cultura, moda, entertainment, social, youthful",
    },
    "oro": {
        "acento": (201, 162, 39), "acento_oscuro": (131, 105, 25),
        "negro": (10, 10, 10), "blanco": (250, 248, 246), "gris": (170, 170, 170),
        "gris_superficie": (26, 26, 26),
        "esquema": "dividido complementario: dorado 45° + apoyo azul profundo",
        "tono": "cálido", "para": "lujo, premium, invitaciones, joyeria, inmobiliaria",
    },
}

# La paleta por defecto: la que se usa cuando el brief no dice nada. Es un
# azul frío DELIBERADAMENTE sin identidad —el modo libre no puede parecerse
# a ninguna marca (el pack de ejemplo es rojo)— y vive en el catálogo, no
# duplicada aquí: si cambia, NEUTRO cambia con ella.
PALETA_POR_DEFECTO = "electrico"
TOKENS_COLOR = ("acento", "acento_oscuro", "negro", "blanco", "gris", "gris_superficie")
#: paleta neutra de respaldo (modo libre sin decisión de paleta)
NEUTRO: Dict[str, Tuple[int, int, int]] = {
    k: v for k, v in PALETAS[PALETA_POR_DEFECTO].items() if k in TOKENS_COLOR
}


def paleta_libre(nombre: Optional[str] = None) -> Dict[str, Any]:
    """Tokens de color de una paleta del catálogo. Sin nombre: la por defecto.

    Lanza error claro si el nombre no existe (no degrada en silencio)."""
    if not nombre:
        return dict(NEUTRO)
    clave = str(nombre).strip().lower()
    if clave not in PALETAS:
        die(f"paleta desconocida: {nombre}. Disponibles: {', '.join(sorted(PALETAS))}",
            kind="input")
    return {k: v for k, v in PALETAS[clave].items() if k in TOKENS_COLOR}


def info_paleta(nombre: str) -> Dict[str, Any]:
    """Metadatos de una paleta del catálogo: armonía, temperatura y para qué
    brief sirve (references/paleta.md). Vacío si el nombre no existe."""
    return {k: v for k, v in PALETAS.get(str(nombre).strip().lower(), {}).items()
            if k not in TOKENS_COLOR}


def tokens_efectivos(brand: Optional[str] = None,
                     paleta: Optional[str] = None) -> Dict[str, Tuple[int, int, int]]:
    """El juego de tokens de la identidad de una pieza: pack de marca >
    paleta del catálogo > paleta por defecto. UNA puerta para todas las
    herramientas (caption, audio_viz, thumbnail, el motor).

    El pack manda si el usuario nombró una marca; si no, la paleta la elige
    el agente según el brief (references/paleta.md). Antes cada herramienta
    resolvía esto por su cuenta y la galería terminaba pasándole flags que
    no entendían.
    """
    if brand:
        return dict(colores_marca(brand))
    return dict(paleta_libre(paleta))


def acento_efectivo(brand: Optional[str] = None, paleta: Optional[str] = None,
                    color: Optional[str] = None) -> Tuple[int, int, int]:
    """El acento de una pieza: color explícito > pack de marca > paleta del
    catálogo > paleta por defecto."""
    if color:
        return hex_a_rgb(color)
    return tokens_efectivos(brand, paleta)["acento"]


SKILL_DIR = Path(__file__).resolve().parent.parent.parent


def resolver_pack(path: Optional[str]) -> Optional[str]:
    """Ruta de un brand pack: absoluta, relativa al cwd o a la carpeta de la
    skill ('brand/x.json'). None si no se pidió marca."""
    if not path:
        return None
    p = os.path.expanduser(str(path))
    for cand in (p, str(SKILL_DIR / p)):
        if os.path.isfile(cand):
            return os.path.abspath(cand)
    die(f"brand pack no encontrado: {path}", kind="input")


def leer_pack(path: Optional[str]) -> Dict[str, Any]:
    ruta = resolver_pack(path)
    if not ruta:
        return {}
    try:
        return json.loads(Path(ruta).read_text(encoding="utf-8"))
    except ValueError as exc:
        die(f"el brand pack {path} no es JSON valido: {exc}", kind="input")


def colores_marca(path: Optional[str] = None) -> Dict[str, Tuple[int, int, int]]:
    """Paleta efectiva: la del pack pedido o la neutra. Acepta claves en
    español (colores.acento) o inglés (colors.primary/accent)."""
    c = dict(NEUTRO)     # el respaldo del modo libre: una paleta del catálogo
    d = leer_pack(path)
    if not d:
        return c
    col = dict(d.get("colors") or {})
    col.update(d.get("colores") or {})
    ac = col.get("acento") or col.get("primary") or col.get("accent")
    if not ac:
        die(f"el brand pack {path} no declara color de acento", kind="input")
    c["acento"] = hex_a_rgb(ac)
    c["acento_oscuro"] = (hex_a_rgb(col["acento_oscuro"]) if col.get("acento_oscuro")
                          else tuple(max(0, int(v * 0.65)) for v in c["acento"]))
    for k in ("negro", "blanco", "gris"):
        if col.get(k):
            c[k] = hex_a_rgb(col[k])
    return c


def ruta_de_pack(path_pack: Optional[str], valor: Optional[str]) -> Optional[str]:
    """Asset del pack (logo, fuente): relativo al JSON, absoluto, ~ o nombre de
    familia tipográfica instalada."""
    if not valor:
        return None
    from _plataforma import resolver_fuente
    v = os.path.expanduser(str(valor))
    base = os.path.dirname(resolver_pack(path_pack) or "")
    cand = v if os.path.isabs(v) else os.path.join(base, v)
    return cand if os.path.exists(cand) else resolver_fuente(str(valor))


def fuente_marca(path_pack: Optional[str], rol: str = "titulares",
                 defecto: str = "Plus Jakarta Sans", generica: str = "sans-bold") -> Optional[str]:
    """Archivo de fuente para un rol del pack (titulares | texto | etiquetas_mono);
    sin pack o sin coincidencia, la empaquetada por defecto."""
    from _plataforma import resolver_fuente
    t = (leer_pack(path_pack).get("tipografias") or {}).get(rol) or {}
    return (ruta_de_pack(path_pack, t.get("archivo")) or
            (resolver_fuente(t["familia"]) if t.get("familia") else None) or
            resolver_fuente(defecto, generica=generica))


def segmentos_enfasis(texto: str) -> List[Tuple[str, bool]]:
    """'Hola *mundo*' -> [('Hola ', False), ('mundo', True)]: la convención de
    énfasis del kit (el énfasis va en el color de acento)."""
    out, buf, enf = [], "", False
    for ch in texto or "":
        if ch == "*":
            if buf:
                out.append((buf, enf))
            buf, enf = "", not enf
        else:
            buf += ch
    if buf:
        out.append((buf, enf))
    return out


def identidad_pieza(brand: Optional[str] = None, logo: Optional[str] = None,
                    nombre: Optional[str] = None, lema: Optional[str] = None) -> Dict[str, Any]:
    """Identidad de una pieza de marca (films): paleta, logo, nombre, lema y
    fuente. Los flags mandan sobre el pack; sin pack ni flags, modo libre
    (paleta neutra, sin logo, sin nombre: nunca una marca por defecto)."""
    d = leer_pack(brand)
    logos = d.get("logos") or {}
    return {"paleta": colores_marca(brand),
            "logo": logo or ruta_de_pack(brand, logos.get("isotipo") or logos.get("logotipo")),
            "nombre": nombre or d.get("nombre"),
            "lema": lema if lema is not None else d.get("lema"),
            "fuente": fuente_marca(brand)}


DEFAULTS: Dict[str, Any] = {
    "font": "DejaVu Sans",
    "font_file": None,
    "colors": {"primary": "FFD200", "text": "FFFFFF", "outline": "000000"},
    "caption": {"size": 24, "position": "bottom", "animate": "none", "karaoke": False, "bold": False, "outline": 2},
}


def load_brand(path: Optional[str]) -> Dict[str, Any]:
    """Carga un brand.json (fuente, colores, defaults de subtitulos); lo que
    falte usa los valores por defecto. None -> solo defaults."""
    import copy
    brand = copy.deepcopy(DEFAULTS)
    if not path:
        return brand
    if not os.path.exists(path):
        die(f"archivo de marca no encontrado: {path}")
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except ValueError as exc:
        die(f"el archivo de marca no es JSON valido: {exc}")
    base = Path(path).resolve().parent
    for k, v in data.items():
        if isinstance(v, dict) and isinstance(brand.get(k), dict):
            brand[k].update(v)
        else:
            brand[k] = v
    for key in ("font_file",):
        if brand.get(key) and not os.path.isabs(brand[key]):
            brand[key] = str(base / brand[key])
    return brand


def parse_srt(path: str):
    """Lee un SRT -> lista de (inicio, fin, texto) en segundos."""
    cues = []
    block = []
    with open(path, encoding="utf-8-sig") as fh:
        content = fh.read().replace("\r\n", "\n") + "\n\n"
    for line in content.split("\n"):
        if line.strip():
            block.append(line)
            continue
        if block:
            times = next((b for b in block if "-->" in b), None)
            if times:
                a, b = times.split("-->")
                text = "\n".join(block[block.index(times) + 1:]).strip()
                cues.append((parse_time(a), parse_time(b), text))
            block = []
    if not cues:
        die(f"no se encontraron cues en {path}")
    return cues


def write_srt(cues, path: str) -> None:
    """Escribe [(inicio, fin, texto)] como SRT."""
    with open(path, "w", encoding="utf-8") as fh:
        for i, (s, e, t) in enumerate(cues, 1):
            fh.write(f"{i}\n{fmt_srt_time(s)} --> {fmt_srt_time(e)}\n{t}\n\n")


def transcribir_medio(video: str, out_srt: str, language=None, model="base",
                     audio_stream: int = 0):
    """Puente opcional a ASR local. Prueba en orden: whisper-cli/main
    (whisper.cpp), faster-whisper (python), whisper (CLI de openai-whisper).
    Produce un SRT y devuelve [(inicio, fin, texto)]. Sin motor instalado ->
    error claro con como instalarlo; la skill nunca depende de uno.
    Todo corre offline."""
    import shutil
    import tempfile
    require_tool("ffmpeg")   # falla claro si no está
    tmpdir = tempfile.mkdtemp(prefix="editoria_asr_")
    try:
        return _transcribir_en_tmpdir(video, out_srt, tmpdir, language, model,
                                      audio_stream)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def _transcribir_en_tmpdir(video, out_srt, tmpdir, language, model, audio_stream):
    import shutil
    import subprocess
    ffmpeg = require_tool("ffmpeg")
    wav = os.path.join(tmpdir, "audio.wav")
    subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                    "-i", video, "-map", f"0:a:{audio_stream}", "-vn",
                    "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", wav], check=True)
    # 1. whisper.cpp
    cli = shutil.which("whisper-cli") or shutil.which("whisper-cpp") or shutil.which("main")
    if cli and (shutil.which("whisper-cli") or shutil.which("whisper-cpp")):
        model_path = model
        if not os.path.exists(model_path):
            for cand in (os.path.expanduser(f"~/.cache/whisper.cpp/ggml-{model}.bin"),
                         f"models/ggml-{model}.bin",
                         f"/usr/local/share/whisper/ggml-{model}.bin"):
                if os.path.exists(cand):
                    model_path = cand
                    break
        base = os.path.join(tmpdir, "out")
        cmd = [cli, "-m", model_path, "-f", wav, "-osrt", "-of", base]
        if language:
            cmd += ["-l", language]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.returncode == 0 and os.path.exists(base + ".srt"):
            info(f"transcrito con whisper.cpp ({os.path.basename(cli)}, modelo {os.path.basename(model_path)})")
            cues = parse_srt(base + ".srt")
            write_srt(cues, out_srt)
            return cues
        lineas = [ln.strip() for ln in (proc.stderr or "").strip().splitlines() if ln.strip()]
        # whisper.cpp, cuando le falta el modelo, imprime su AYUDA entera: la
        # ultima linea es texto de uso ("-vo N, --vad-samples-overlap...") y
        # no dice nada del fallo real. Se busca la primera linea de error de
        # verdad y, si no hay, se dice que falta el modelo (que es el caso
        # normal: el binario esta, el modelo no).
        causa = next((ln for ln in lineas
                      if "error" in ln.lower() or "fail" in ln.lower()
                      or "not found" in ln.lower() or "no such" in ln.lower()),
                     None)
        if causa is None:
            causa = (f"no se encuentra el modelo {model_path!r}" if not os.path.exists(model_path)
                     else (lineas[-1] if lineas else "?"))
        info("whisper.cpp encontrado pero fallo: " + causa[:200])
    # 2. faster-whisper (paquete python)
    try:
        from faster_whisper import WhisperModel  # type: ignore
        m = WhisperModel(model, device="cpu", compute_type="int8")
        segments, _ = m.transcribe(wav, language=language, word_timestamps=False)
        cues = [(seg.start, seg.end, seg.text.strip()) for seg in segments if seg.text.strip()]
        if cues:
            info("transcrito con faster-whisper")
            write_srt(cues, out_srt)
            return cues
    except ImportError:
        pass
    # 3. openai-whisper CLI
    if shutil.which("whisper"):
        cmd = ["whisper", wav, "--model", model, "--output_format", "srt",
               "--output_dir", tmpdir]
        if language:
            cmd += ["--language", language]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        srt = os.path.join(tmpdir, "audio.srt")
        if proc.returncode == 0 and os.path.exists(srt):
            info("transcrito con openai-whisper")
            cues = parse_srt(srt)
            write_srt(cues, out_srt)
            return cues
    die("no hay motor local de voz-a-texto.\n"
        "Instala uno (todos corren offline):\n"
        "  whisper.cpp:    brew install whisper-cpp   (luego descarga un modelo: ggml-base.bin)\n"
        "  faster-whisper: pip install faster-whisper\n"
        "  openai-whisper: pip install openai-whisper\n")


def leer_palabras(path: str) -> List[Dict[str, Any]]:
    """Tiempos por palabra -> [{texto, inicio, fin, hablante}] ordenados.
    Fuente única de los formatos que circulan por el kit: el palabras.json de
    scripts/alinear.py ({palabras: [{texto, inicio, fin}]}), una lista plana
    [{text|word, start, end}] y la salida segmentada de Whisper/WhisperX
    ({segments: [{speaker?, words: [...]}]}). `hablante` (o `speaker`, por
    palabra o por segmento) es opcional: None si el archivo no lo trae."""
    data = leer_json(path, "el JSON de palabras")
    items: List[Tuple[Dict[str, Any], Any]] = []
    if isinstance(data, dict) and isinstance(data.get("segments"), list):
        for seg in data["segments"]:
            for w in (seg.get("words") or []) if isinstance(seg, dict) else []:
                items.append((w, seg.get("hablante", seg.get("speaker"))))
    else:
        lista = (data.get("palabras") or data.get("words")) if isinstance(data, dict) else data
        items = [(w, None) for w in (lista or []) if isinstance(w, dict)]
    out = []
    for w, hab_seg in items:
        texto = str(w.get("texto") or w.get("text") or w.get("word") or "").strip()
        a, b = _to_float(w.get("inicio", w.get("start"))), _to_float(w.get("fin", w.get("end")))
        if texto and a is not None and b is not None:
            out.append({"texto": texto, "inicio": a, "fin": max(b, a + 0.05),
                        "hablante": w.get("hablante", w.get("speaker", hab_seg))})
    if not out:
        die(f"{path}: no trae palabras con inicio/fin", kind="input")
    return sorted(out, key=lambda p: p["inicio"])


def write_segmentos_json(cues, path: str) -> None:
    """Escribe [(inicio, fin, texto)] como JSON [{start, end, text}],
    el formato que consume retakes.py."""
    import json as _json
    segs = [{"start": round(float(s), 3), "end": round(float(e), 3), "text": t}
            for s, e, t in cues]
    with open(path, "w", encoding="utf-8") as fh:
        _json.dump(segs, fh, ensure_ascii=False, indent=2)


# ───────────── ayuda de CLI: ninguna opción sin explicar ─────────────
# Un agente aprende la herramienta por --help: una opción sin texto es una
# opción que adivina. Las que se repiten en todo el kit se explican UNA vez.
AYUDAS = {
    "-o": "archivo de salida",
    "--out": "archivo de salida",
    "video": "video de entrada",
    "videos": "videos de entrada, en orden",
    "plan": "plan.json (references/plan-video.md)",
    "imagen": "imagen de entrada (PNG/JPG; PNG con alfa para logos)",
    "carpeta": "carpeta de entrada",
    "--crf": "calidad x264: menor = mejor y más pesado (18 visualmente sin pérdida, 23 default web)",
    "--fps": "cuadros por segundo de la salida",
    "--ancho": "ancho de salida en px (el alto sigue la proporción)",
    "--jobs": "procesos en paralelo (default: núcleos de la máquina)",
    "--dur": "duración en segundos",
    "--duracion": "duración en segundos",
    "--formato": "formato: 9:16 (vertical, Reels/TikTok/Shorts) o 16:9 (YouTube)",
    "--titulo": "título que aparece en pantalla",
    "--subtitulo": "subtítulo bajo el título",
    "--posicion": "posición en el cuadro",
}


def ayudar(parser: "argparse.ArgumentParser", propias: Optional[Dict[str, str]] = None) -> "argparse.ArgumentParser":
    """Completa el help de toda opción (y subcomando) que no lo tenga: primero
    `propias` (las de este script), luego AYUDAS (las del kit). Recorre los
    subcomandos. Llamar antes de parse_args(). Devuelve el parser."""
    textos = dict(AYUDAS, **(propias or {}))
    for act in parser._actions:
        if isinstance(act, argparse._SubParsersAction):
            for ch in act._choices_actions:   # help del subcomando en la lista {gen,mix,…}
                if not ch.help and ch.dest in textos:
                    ch.help = textos[ch.dest]
            for sub in act.choices.values():
                ayudar(sub, propias)
            continue
        if act.help is None or act.help == "":
            claves = list(act.option_strings) + [act.dest]
            act.help = next((textos[c] for c in claves if c in textos), act.help)
    return parser
