#!/usr/bin/env python3
"""alinear.py — alineación palabra-a-palabra de una voz en off contra el guion.

Toma la voz (mp3/wav, salida de voz_off.py) y el guion original y devuelve un
JSON con el tiempo de inicio/fin de cada palabra del guion. Las escenas de
plan.json pueden leer estos tiempos para que las animaciones caigan sobre la
palabra exacta (no sobre el offset global de la escena).

Por qué existe: Whisper da tiempos de palabra aproximados; las escenas con
`at:` por palabra y los subtítulos heredan el desfase. Aquí el texto ya se
sabe (lo que el guion dice), así que solo hay que encontrar DÓNDE se dice
cada palabra. Whisper da la base; una pasada ligera con energía del audio
refina las palabras cuya marca cae sobre silencio.

Pipeline (igual que Skill-Editor-IA pero sin MMS_FA — el peso del modelo
torchaudio no compensa para piezas tan cortas):
  1. ASR con timestamps por palabra (whisper.cpp > faster-whisper > openai-whisper).
  2. Emparejar cada palabra del guion con los segmentos reconocidos
     (SequenceMatcher; tolera repeticiones y "noise" de Whisper).
  3. Refinar: si la palabra está en un tramo con energía muy baja (silencio),
     se ancla al vecino más cercano con energía alta.
  4. Salida JSON: {palabras: [{texto, inicio, fin, confianza}, ...]}

  Uso:
    python scripts/alinear.py voz.mp3 guion.txt -o palabras.json
    python scripts/alinear.py voz.mp3 guion.txt -o palabras.json --idioma es
    python scripts/alinear.py voz.mp3 guion.txt -o palabras.json --motor faster-whisper
    cat guion.txt | python scripts/alinear.py voz.mp3 -o palabras.json        # guion por stdin
    python scripts/alinear.py referencia.mp4 -o ref.palabras.json --idioma en   # sin guion: transcribe
        # un video con tiempos por palabra (lectura de referencias, contact_sheet.py --palabras)
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path

KIT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(KIT, "ffmpeg_tools"))
from _comun import die, info  # noqa: E402

try:
    import numpy as np
except ImportError:
    np = None

SR = 16000  # Whisper trabaja a 16 kHz mono


# ───────────────────────── texto ─────────────────────────

def normalizar_palabras(texto: str) -> list[str]:
    """Texto → palabras en minúsculas, sin tildes, sin signos."""
    t = unicodedata.normalize("NFKD", texto.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return [p for p in re.sub(r"[^a-z0-9' ]+", " ", t).split() if p]


# ───────────────────────── audio ─────────────────────────

def leer_audio(ruta: Path) -> "np.ndarray":
    """Lee el audio como mono 16 kHz float32 (formato Whisper)."""
    cmd = ["ffmpeg", "-v", "error", "-i", str(ruta), "-ac", "1", "-ar", str(SR),
           "-f", "f32le", "-"]
    r = subprocess.run(cmd, capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.float32).copy()


def envolvente_db(audio: "np.ndarray", hop: int = SR // 100) -> "np.ndarray":
    """Envolvente RMS en dB por ventanas de 10 ms."""
    n = len(audio) // hop
    pot = (audio[:n * hop].reshape(n, hop) ** 2).mean(1)
    pot = np.maximum(pot, 1e-12)
    return 10 * np.log10(pot)


# ───────────────────────── ASR (word-level) ─────────────────────────

def _whisper_cli_palabras(wav: Path, modelo: str, idioma: str | None) -> list[tuple[str, float, float, float]]:
    """whisper.cpp con --output-json y --word-tholds. Devuelve (texto, inicio, fin, prob)."""
    cli = shutil.which("whisper-cli") or shutil.which("whisper-cpp") or shutil.which("main")
    if not cli:
        return []
    model_path = modelo
    if not os.path.exists(model_path):
        for cand in (os.path.expanduser(f"~/.cache/whisper.cpp/ggml-{modelo}.bin"),
                     f"models/ggml-{modelo}.bin",
                     f"/usr/local/share/whisper/ggml-{modelo}.bin"):
            if os.path.exists(cand):
                model_path = cand
                break
    base = wav.parent / "out"
    cmd = [cli, "-m", model_path, "-f", str(wav), "-oj", "-of", str(base),
           "--no-prints", "--print-realtime", "false", "--print-progress", "false"]
    if idioma:
        cmd += ["-l", idioma]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if proc.returncode != 0 or not (base.with_suffix(".json")).exists():
        info(f"whisper.cpp fallo: {(proc.stderr or '').strip()[:200]}")
        return []
    info(f"transcrito con whisper.cpp ({os.path.basename(model_path)})")
    return _parsear_json_whisper(json.loads((base.with_suffix(".json")).read_text(encoding="utf-8")))


def _faster_whisper_palabras(wav: Path, modelo: str, idioma: str | None) -> list[tuple[str, float, float, float]]:
    """faster-whisper con word_timestamps=True."""
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except ImportError:
        return []
    try:
        m = WhisperModel(modelo, device="cpu", compute_type="int8")
        segments, _ = m.transcribe(str(wav), language=idioma, word_timestamps=True,
                                   condition_on_previous_text=False)
        palabras: list[tuple[str, float, float, float]] = []
        for seg in segments:
            if not seg.words:
                continue
            for tok in seg.words:
                prob = float(getattr(tok, "probability", 0.5) or 0.5)
                palabras.append((tok.word.strip(), float(tok.start), float(tok.end), prob))
        if palabras:
            info("transcrito con faster-whisper (word_timestamps=True)")
        return palabras
    except Exception as ex:
        info(f"faster-whisper fallo: {ex}")
        return []


def _openai_whisper_palabras(wav: Path, modelo: str, idioma: str | None) -> list[tuple[str, float, float, float]]:
    """openai-whisper CLI con --output_format json + --word_timestamps True."""
    if not shutil.which("whisper"):
        return []
    cmd = ["whisper", str(wav), "--model", modelo, "--output_format", "json",
           "--word_timestamps", "True", "--output_dir", str(wav.parent)]
    if idioma:
        cmd += ["--language", idioma]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    out_json = wav.parent / f"{wav.stem}.json"
    if proc.returncode != 0 or not out_json.exists():
        info(f"openai-whisper fallo: {(proc.stderr or '').strip()[:200]}")
        return []
    info("transcrito con openai-whisper (word_timestamps=True)")
    return _parsear_json_whisper(json.loads(out_json.read_text(encoding="utf-8")))


def _parsear_json_whisper(data: dict) -> list[tuple[str, float, float, float]]:
    """whisper.cpp / openai-whisper JSON → [(texto, inicio, fin, prob), ...]."""
    out: list[tuple[str, float, float, float]] = []
    for seg in data.get("transcription", data.get("segments", [])):
        # openai-whisper: words[].word; whisper.cpp JSON usa "word" o "text" con timestamps propios
        for tok in seg.get("words", []):
            t = tok.get("word") or tok.get("text") or ""
            if not t.strip():
                continue
            inicio = float(tok.get("start", tok.get("t0", 0.0)) or 0.0)
            fin = float(tok.get("end", tok.get("t1", inicio)) or inicio)
            prob = float(tok.get("probability", tok.get("p", 0.5)) or 0.5)
            out.append((t.strip(), inicio, fin, prob))
    return out


# ───────────────────────── emparejamiento ─────────────────────────

def emparejar(guion: list[str], whisper: list[tuple[str, float, float, float]]
              ) -> list[tuple[str, float, float, float]]:
    """Empareja cada palabra del guion con un timestamp de Whisper.

    Tolerancia: el guion y el reconocimiento pueden diferir en repeticiones,
    muletillas, números leídos como palabras y formato de comas/espacios.
    SequenceMatcher encuentra la subsecuencia común más larga.
    """
    texto_w = [normalizar_palabras(p)[0] if normalizar_palabras(p) else ""
               for p, *_ in whisper]
    norm_g = [normalizar_palabras(p)[0] if normalizar_palabras(p) else "" for p in guion]
    matcher = difflib.SequenceMatcher(a=norm_g, b=texto_w, autojunk=False)
    out: list[tuple[str, float, float, float]] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for gi, wj in zip(range(i1, i2), range(j1, j2)):
                p, ini, fin, prob = whisper[wj]
                out.append((guion[gi], ini, fin, prob))
        elif tag == "replace":
            # Mismas posiciones temporales; repartir los timestamps reconocidos
            n = min(i2 - i1, j2 - j1)
            for k in range(n):
                p, ini, fin, prob = whisper[j1 + k]
                out.append((guion[i1 + k], ini, fin, prob))
        # 'delete' (palabra del guion sin match) o 'insert' (palabra whisper sin guion) → se omiten
    return out


# ───────────────────────── refinamiento por energía ─────────────────────────

def refinar_energia(audio: "np.ndarray", palabras: list[tuple[str, float, float, float]],
                    ventana: float = 0.3) -> list[tuple[str, float, float, float]]:
    """Si la marca de una palabra cae en silencio, se ancla al vecino con más energía.

    Útil para las primeras/últimas palabras de frase, que Whisper suele colocar
    mal (duración 0 o tarde).
    """
    env = envolvente_db(audio)
    out: list[tuple[str, float, float, float]] = []
    for idx, (texto, ini, fin, prob) in enumerate(palabras):
        i0 = max(0, int(ini * SR))
        i1 = min(len(env), max(i0 + 1, int(fin * SR)))
        energia = float(env[i0:i1].mean()) if i1 > i0 else -60.0
        if energia > -40:
            out.append((texto, ini, fin, prob))
            continue
        # palabra en silencio (el ASR la ubicó mal): sin voz donde dice estar
        izq = max(0, int((ini - ventana) * SR))
        der = min(len(env), int((fin + ventana) * SR))
        if der <= izq:   # borde del audio: no hay ventana que revisar
            out.append((texto, ini, fin, prob))
            continue
        # anclar al vecino anterior (no salta de palabra) y bajar la confianza
        if idx > 0:
            ant = out[idx - 1]
            out.append((texto, ant[2], max(ant[2] + 0.05, fin), min(prob, 0.4)))
        else:
            out.append((texto, ini, fin, prob))
    return out


# ───────────────────────── main ─────────────────────────

def transcribir_palabras(audio_path: Path, idioma: str | None, modelo: str,
                          motor: str | None) -> list[tuple[str, float, float, float]]:
    """ASR por palabra de un audio o VIDEO (una referencia descargada sirve tal
    cual). El wav de 16 kHz y los JSON intermedios de Whisper viven en un
    directorio temporal: nada queda junto al material del usuario."""
    with tempfile.TemporaryDirectory(prefix="editoria_alinear_") as tmp:
        wav = Path(tmp) / "audio.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(audio_path), "-vn",
                        "-ac", "1", "-ar", str(SR), str(wav)], check=True)
        return _asr_en_cascada(wav, idioma, modelo, motor)


def _asr_en_cascada(wav: Path, idioma: str | None, modelo: str,
                    motor: str | None) -> list[tuple[str, float, float, float]]:
    if motor in (None, "auto", "whisper-cli"):
        r = _whisper_cli_palabras(wav, modelo, idioma)
        if r:
            return r
    if motor in (None, "auto", "faster-whisper"):
        r = _faster_whisper_palabras(wav, modelo, idioma)
        if r:
            return r
    if motor in (None, "auto", "openai-whisper"):
        r = _openai_whisper_palabras(wav, modelo, idioma)
        if r:
            return r
    die("no hay motor de ASR local.\n"
        "Instala uno (todos corren offline):\n"
        "  whisper.cpp:    brew install whisper-cpp   (luego descarga un modelo: ggml-base.bin)\n"
        "  faster-whisper: pip install faster-whisper\n"
        "  openai-whisper: pip install openai-whisper\n")
    return []  # die() sale


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("audio", help="mp3/wav de la voz en off (salida de voz_off.py) o un video")
    ap.add_argument("guion", nargs="?", default=None,
                    help="txt/md con el guion; '-' lee de stdin (default: usa lo que Whisper transcriba)")
    ap.add_argument("-o", "--out", default=None,
                    help="JSON de salida (default: <audio>.palabras.json)")
    ap.add_argument("--idioma", default="es",
                    help="código de idioma para Whisper (default es)")
    ap.add_argument("--modelo", default="base",
                    help="modelo Whisper (tiny/base/small/medium/large-v3; default base)")
    ap.add_argument("--motor", default=None, choices=["auto", "whisper-cli", "faster-whisper", "openai-whisper"],
                    help="ASR local a usar (default: auto)")
    ap.add_argument("--sin-refinar", action="store_true",
                    help="omite la pasada de refinamiento por energía")
    args = ap.parse_args()
    if np is None:
        die("numpy es requerido (pip install numpy)", kind="missing_tool")

    audio = Path(args.audio)
    if not audio.is_file():
        die(f"no existe el audio: {audio}")
    if args.guion and args.guion != "-":
        guion = Path(args.guion).read_text(encoding="utf-8")
    elif args.guion == "-":
        guion = sys.stdin.read()
    else:
        guion = None
    if guion is not None:
        guion_palabras = [p for p in re.split(r"\s+", guion.strip()) if p]
        if not guion_palabras:
            die("guion vacio")
    else:
        guion_palabras = None

    info(f"transcribiendo con ASR local (idioma={args.idioma}, modelo={args.modelo})")
    palabras = transcribir_palabras(audio, args.idioma, args.modelo, args.motor)
    if not palabras:
        die("ASR no devolvio palabras")

    if guion_palabras is not None:
        emp = emparejar(guion_palabras, palabras)
        if len(emp) < 0.5 * len(guion_palabras):
            die(f"alineacion debil ({len(emp)}/{len(guion_palabras)} palabras del guion cubiertas); "
                "revisa guion/audio (Whisper no esta reconociendo el guion)")
        palabras = emp

    if not args.sin_refinar:
        try:
            audio_np = leer_audio(audio)
            palabras = refinar_energia(audio_np, palabras)
        except Exception as ex:
            info(f"refinamiento omitido: {ex}")

    out_path = Path(args.out) if args.out else audio.with_suffix(".palabras.json")
    payload = {
        "audio": str(audio),
        "idioma": args.idioma,
        "modelo": args.modelo,
        "n_palabras": len(palabras),
        "palabras": [{"texto": t, "inicio": round(i, 3), "fin": round(f, 3), "confianza": round(p, 3)}
                     for t, i, f, p in palabras],
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    info(f"OK {out_path} ({len(palabras)} palabras)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
