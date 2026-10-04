#!/usr/bin/env python3
"""Poster como frame 0.

El poster es el still que se muestra antes de reproducir el video — lo primero
que ve alguien cuando esta quieto o sin reproducir. No dejarlo al primer frame
crudo ni a un timestamp arbitrario: esos caen en fades, transiciones o texto
a medio animar.

Flujo:
  1. Extraer el frame del momento mas fuerte YA ASENTADO (texto completamente
     animado, antes de que salga) a poster.jpg.
  2. Hornearlo como frame 0 del mp4: reemplaza SOLO los pixeles del primer
     frame, sin tocar duracion, conteo de frames ni audio. A 30fps el poster
     se muestra 1/30s antes de que arranque el intro: imperceptible en
     reproduccion, pero es lo que todo thumbnail-grabber (Slack, X, Discord)
     captura, porque casi todos toman el frame 0 e ignoran metadatos de cover.

Uso:
    python scripts/poster_frame.py video.mp4 --t 3.2
    python scripts/poster_frame.py video.mp4 --t 3.2 -o video_poster.mp4 --jpg poster.jpg
"""
import argparse
import os
import subprocess


def run(cmd):
    subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("video", help="mp4 de entrada")
    ap.add_argument("--t", type=float, required=True,
                    help="timestamp del momento asentado mas fuerte (s)")
    ap.add_argument("--jpg", default=None,
                    help="ruta de SALIDA del poster extraido (se sobrescribe; "
                         "def: <video>_poster.jpg)")
    ap.add_argument("-o", "--out", default=None,
                    help="mp4 de salida (def: sobrescribe con backup .bak)")
    args = ap.parse_args()

    base, _ = os.path.splitext(args.video)
    jpg = args.jpg or f"{base}_poster.jpg"

    # 1. extraer el poster del momento asentado
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
         "-ss", str(args.t), "-i", args.video,
         "-frames:v", "1", "-q:v", "2", jpg])
    print(f"poster extraido en t={args.t}s -> {jpg}")

    # 2. hornear como frame 0 (mismos pixeles de dimension: sale del mismo render)
    out = args.out
    if out is None:
        bak = args.video + ".bak"
        os.replace(args.video, bak)
        src = bak
        out = args.video
        print(f"backup: {bak}")
    else:
        src = args.video

    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
         "-i", src, "-i", jpg,
         "-filter_complex", "[0:v][1:v]overlay=0:0:enable='eq(n,0)'[v]",
         "-map", "[v]", "-map", "0:a?", "-c:v", "libx264", "-crf", "18",
         "-preset", "slow", "-pix_fmt", "yuv420p", "-c:a", "copy",
         "-movflags", "+faststart", out])
    print(f"OK frame 0 = poster -> {out} (duracion y audio intactos)")


if __name__ == "__main__":
    main()
