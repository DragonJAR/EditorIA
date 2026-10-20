#!/usr/bin/env python3
"""referencia.py — Ingesta y análisis de video de referencia (inspirado en Hypit).

Toma un video local o una URL (YouTube, TikTok, Instagram, Twitter) vía yt-dlp,
extrae metadatos precisos, separa el audio en 48kHz (máster/edición) y 16kHz
(Whisper/transcripción), y genera automáticamente una hoja de contactos visual
(contact sheet) con contact_sheet.py para inspeccionar cortes y dinamismo.

Uso:
  python3 scripts/referencia.py --video clip.mp4 --out dir_analisis/
  python3 scripts/referencia.py --url "https://youtube.com/watch?v=..." --out ref/
  python3 scripts/referencia.py --video clip.mp4 --frames 16 --cols 4
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def descargar_url(url, out_dir):
    """Descarga el video usando yt-dlp si está instalado."""
    if not shutil.which("yt-dlp"):
        sys.exit("ERROR: se requiere yt-dlp para descargar URLs. Instalar con: brew install yt-dlp o pip install yt-dlp")
    plantilla = os.path.join(out_dir, "fuente_descargada.%(ext)s")
    cmd = [
        "yt-dlp",
        "--format", "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "-o", plantilla,
        url
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"ERROR: fallo yt-dlp al descargar '{url}':\n{r.stderr.strip()[:400]}")
    # Localizar archivo resultante
    candidatos = [os.path.join(out_dir, f) for f in os.listdir(out_dir) if f.startswith("fuente_descargada.")]
    if not candidatos:
        sys.exit("ERROR: yt-dlp terminó sin error pero no se encontró el archivo de salida.")
    return candidatos[0]


def extraer_metadatos(video_path):
    """Extrae duración, resolución, fps y aspect ratio con ffprobe."""
    if not os.path.isfile(video_path):
        sys.exit(f"ERROR: no existe el archivo de video: {video_path}")
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate,duration:format=duration",
        "-of", "json",
        video_path
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"ERROR: ffprobe no pudo leer metadatos de {video_path}")
    data = json.loads(r.stdout or "{}")
    v_stream = (data.get("streams") or [{}])[0]
    fmt = data.get("format") or {}

    dur_str = v_stream.get("duration") or fmt.get("duration") or "0"
    dur = float(dur_str)

    w = int(v_stream.get("width") or 0)
    h = int(v_stream.get("height") or 0)

    fps_num_den = (v_stream.get("r_frame_rate") or "30/1").split("/")
    fps = round(float(fps_num_den[0]) / float(fps_num_den[1]), 2) if len(fps_num_den) == 2 and float(fps_num_den[1]) > 0 else 30.0

    aspecto = "9:16" if h > w else ("1:1" if h == w else "16:9")

    return {
        "duracion": round(dur, 3),
        "ancho": w,
        "alto": h,
        "fps": fps,
        "aspecto": aspecto
    }


def extraer_audios(video_path, out_dir):
    """Extrae audio 48kHz estéreo y 16kHz mono."""
    a_48k = os.path.join(out_dir, "audio_48k.wav")
    a_16k = os.path.join(out_dir, "audio_16k.wav")

    # 48kHz stereo para master / beat detection
    cmd_48 = ["ffmpeg", "-y", "-v", "error", "-i", video_path, "-vn", "-ar", "48000", "-ac", "2", a_48k]
    r48 = subprocess.run(cmd_48, capture_output=True, text=True)

    # 16kHz mono para whisper / transcribir
    cmd_16 = ["ffmpeg", "-y", "-v", "error", "-i", video_path, "-vn", "-ar", "16000", "-ac", "1", a_16k]
    r16 = subprocess.run(cmd_16, capture_output=True, text=True)

    hay_audio = (r48.returncode == 0 and os.path.isfile(a_48k) and os.path.getsize(a_48k) > 1000)
    return {
        "audio_48k": a_48k if hay_audio else None,
        "audio_16k": a_16k if hay_audio else None,
        "tiene_audio": hay_audio
    }


def generar_hoja_contacto(video_path, out_dir, n_frames=16, cols=4):
    """Invoca contact_sheet.py para construir el mosaico visual."""
    sheet_path = os.path.join(out_dir, "contact_sheet.png")
    script_cs = os.path.join(BASE, "scripts", "contact_sheet.py")
    cmd = [
        sys.executable, script_cs,
        "--video", video_path,
        "-n", str(n_frames),
        "--cols", str(cols),
        "-o", sheet_path
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not os.path.isfile(sheet_path):
        print(f"AVISO: contact_sheet.py no pudo generar el mosaico: {r.stderr.strip()[:150]}")
        return None
    return sheet_path


def procesar_referencia(origen, es_url=False, out_dir=None, n_frames=16, cols=4):
    """Flujo unificado de ingesta de referencia."""
    out_dir = out_dir or os.path.join(os.getcwd(), "referencia_analisis")
    os.makedirs(out_dir, exist_ok=True)

    if es_url:
        print(f"Descargando video desde URL: {origen}")
        video_local = descargar_url(origen, out_dir)
    else:
        video_local = os.path.abspath(origen)
        if not os.path.isfile(video_local):
            sys.exit(f"ERROR: el archivo no existe: {video_local}")

    print(f"Analizando metadatos de video: {video_local}")
    meta = extraer_metadatos(video_local)

    print("Extrayendo pistas de audio (48kHz master y 16kHz transcripción)...")
    audios = extraer_audios(video_local, out_dir)

    print(f"Generando contact sheet visual ({n_frames} frames)...")
    sheet = generar_hoja_contacto(video_local, out_dir, n_frames, cols)

    resultado = {
        "video": video_local,
        "metadatos": meta,
        "audio": audios,
        "contact_sheet": sheet,
        "out_dir": out_dir
    }

    ref_json = os.path.join(out_dir, "referencia.json")
    with open(ref_json, "w", encoding="utf-8") as fh:
        json.dump(resultado, fh, indent=2, ensure_ascii=False)

    print(f"OK Referencia procesada exitosamente:")
    print(f"   Metadatos: {meta['duracion']}s · {meta['ancho']}x{meta['alto']} ({meta['aspecto']}) · {meta['fps']} fps")
    print(f"   Audio: {'48kHz + 16kHz extraídos' if audios['tiene_audio'] else 'Sin pista de audio'}")
    if sheet:
        print(f"   Contact sheet: {sheet}")
    print(f"   Reporte JSON: {ref_json}")
    return resultado


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--video", help="Ruta al video local de referencia")
    src.add_argument("--url", help="URL de video (YouTube, TikTok, Instagram, Twitter) para descargar con yt-dlp")
    ap.add_argument("-o", "--out", help="Directorio donde guardar assets extraídos (default: ./referencia_analisis)")
    ap.add_argument("-n", "--frames", type=int, default=16, help="Frames a extraer para el contact sheet (default: 16)")
    ap.add_argument("--cols", type=int, default=4, help="Columnas del contact sheet (default: 4)")

    args = ap.parse_args()
    es_url = bool(args.url)
    origen = args.url if es_url else args.video
    procesar_referencia(origen, es_url=es_url, out_dir=args.out, n_frames=args.frames, cols=args.cols)


if __name__ == "__main__":
    main()
