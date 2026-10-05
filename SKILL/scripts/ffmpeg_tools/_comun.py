#!/usr/bin/env python3
"""Utilidades compartidas de las herramientas ffmpeg de EditorIA.

Solo stdlib. Localiza ffmpeg/ffprobe en el PATH, los ejecuta con errores
claros y ofrece un probe compacto que usa cada script.

Adaptado de las mecánicas de ffmpeg-skill (alfred-lau): orden recomendado
(color -> corte -> union -> silencio -> encuadre -> subtitulos -> sync ->
audio -> loudness -> exportacion), probe-first de los inputs, --dry-run con
JSON, nunca sobrescribir el input, verificar el output y QA con frames.
"""
import json
import os
import platform
import shutil
import subprocess
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

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
    output = cmd[-1]
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
            die(f"comando fallo (codigo {proc.returncode}): {cmd[0]}\n{tail}")
    return proc


def ffmpeg_base(overwrite: bool = True) -> List[str]:
    cmd = [require_tool("ffmpeg"), "-hide_banner", "-loglevel", "error", "-nostdin"]
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
        pix = video.get("pix_fmt") or ""
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
    """
    from . import _plataforma as _plat
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
    """Convierte '#C11B05' / 'C11B05' / '0xC11B05' a una tupla RGB (R, G, B) 0-255.
    Una sola fuente de verdad (DRY): la usan render_plan.py, thumbnail.py y resto
    del kit. Marca-blanca: la entrada sale del brand pack, no de un default quemado.
    """
    h = color_hex(value)
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


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
    ffmpeg = require_tool("ffmpeg")
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
        info("whisper.cpp encontrado pero fallo: " + (proc.stderr.strip().splitlines() or ["?"])[-1][:200])
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


def write_segmentos_json(cues, path: str) -> None:
    """Escribe [(inicio, fin, texto)] como JSON [{start, end, text}],
    el formato que consume retakes.py."""
    import json as _json
    segs = [{"start": round(float(s), 3), "end": round(float(e), 3), "text": t}
            for s, e, t in cues]
    with open(path, "w", encoding="utf-8") as fh:
        _json.dump(segs, fh, ensure_ascii=False, indent=2)
