#!/usr/bin/env python3
"""Visualización de audio con ffmpeg (showwaves / showspectrum / showfreqs).
Uso: python audio_viz.py audio.mp3 -o viz.mp4 [--modo waves|spectrum|freqs]
     [--color C11B05] [-s 1080x1920] [--overlay video.mp4]
Genera un video standalone de la visualización (útil para teasers) o la
superpone sobre un video con --overlay. Solo stdlib + ffmpeg.
"""
import argparse, subprocess, sys, os

COLOR_DEFAULT = "0xC11B05"  # default neutro; usar --color o --brand para otra marca

def color_desde_brand(brand_path):
    """Lee el acento de un brand pack (brand/*.json), o None si no se puede."""
    import json
    try:
        d = json.loads(open(os.path.expanduser(brand_path), encoding="utf-8").read())
    except (OSError, ValueError):
        return None
    for clave in ("colors", "colores"):
        c = d.get(clave) or {}
        for k in ("primary", "acento", "accent"):
            v = c.get(k)
            if v:
                v = v.lstrip("#")
                return "0x" + v
    return None

def duracion_audio(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        sys.exit(f"ERROR: no se pudo leer la duración de {path}")

def main():
    ap = argparse.ArgumentParser(
        description="Visualiza un audio como video (ondas, espectro o barras de frecuencia).")
    ap.add_argument("audio", help="archivo de audio de entrada")
    ap.add_argument("-o", "--out", required=True, help="video de salida (.mp4)")
    ap.add_argument("--modo", default="waves", choices=["waves", "spectrum", "freqs"],
                    help="tipo de visualización (default: waves)")
    ap.add_argument("--color", default=None,
                    help="color hex de la visualización, ej. 0xC11B05 (default: acento del --brand o 0xC11B05)")
    ap.add_argument("--brand", default=None,
                    help="brand pack (brand/*.json): el color sale de su acento")
    ap.add_argument("-s", "--size", default="1080x1920",
                    help="tamaño del video de visualización (default: 1080x1920)")
    ap.add_argument("-r", "--fps", default=30, type=int, help="fps (default: 30)")
    ap.add_argument("--overlay",
                    help="video base: la visualización se superpone abajo del cuadro")
    ap.add_argument("--altura", default=240, type=int,
                    help="altura de la banda de visualización en modo --overlay (default: 240)")
    a = ap.parse_args()

    if not os.path.exists(a.audio):
        sys.exit(f"ERROR: no existe {a.audio}")
    dur = duracion_audio(a.audio)

    color = a.color or (color_desde_brand(a.brand) if a.brand else None) or COLOR_DEFAULT

    if a.modo == "waves":
        filtro = f"showwaves=s={a.size}:mode=line:colors={color}:rate={a.fps}"
    elif a.modo == "spectrum":
        # showspectrum usa esquemas propios; fire es el más cercano a marca
        filtro = f"showspectrum=s={a.size}:color=fire:slide=scroll:mode=combined"
    else:  # freqs
        filtro = f"showfreqs=s={a.size}:mode=bar:colors={color}:rate={a.fps}"

    if a.overlay:
        if not os.path.exists(a.overlay):
            sys.exit(f"ERROR: no existe {a.overlay}")
        w, h = a.size.split("x")
        fc = (f"[0:a]{filtro},scale={w}:{a.altura}[viz];"
              f"[1:v][viz]overlay=0:H-{a.altura}[v]")
        cmd = ["ffmpeg", "-y", "-v", "error", "-i", a.audio, "-i", a.overlay,
               "-filter_complex", fc, "-map", "[v]", "-map", "0:a",
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
               "-t", str(dur), a.out]
    else:
        cmd = ["ffmpeg", "-y", "-v", "error", "-i", a.audio,
               "-filter_complex", f"[0:a]{filtro}[v]",
               "-map", "[v]", "-map", "0:a",
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
               "-t", str(dur), a.out]
    r = subprocess.run(cmd)
    if r.returncode != 0:
        sys.exit("ERROR: ffmpeg falló generando la visualización")
    print(f"OK {a.out} ({a.modo}, {dur:.1f}s)")

if __name__ == "__main__":
    main()
