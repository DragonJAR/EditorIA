#!/usr/bin/env python3
"""Mosaico de revision pre-render (metodo l3d1c / coleccion Opus 5.5).

Toma una carpeta de stills PNG (o extrae N frames equidistantes de un
video) y los mosaica en UN contact sheet etiquetado con nombre o tiempo,
para revisar un corte entero de un vistazo ANTES de pagar el render
completo. Los cambios se piden en lenguaje natural sobre el sheet.

Uso:
  python3 scripts/contact_sheet.py --dir stills/ -o sheet.png
  python3 scripts/contact_sheet.py --video corte.mp4 -n 20 -o sheet.png
  python3 scripts/contact_sheet.py --dir stills/ --cols 5 --ancho 320 -o sheet.png

Diferencia con auto_qa.py: ese hace QA de un render terminado; esto
revisa el CORTE antes de renderizar (stills de Remotion/HyperFrames).
"""
import argparse
import os
import subprocess
import sys
import tempfile

try:
    from PIL import Image, ImageDraw
except ModuleNotFoundError as _e_dep:
    if "-h" not in sys.argv and "--help" not in sys.argv:
        sys.exit(f"ERROR: falta dependencia ({_e_dep.name}): pip install pillow")
    Image = ImageDraw = None


def extraer_frames(video, n, tmpdir):
    """Extrae n frames equidistantes con ffmpeg. Devuelve [(ruta, etiqueta)]."""
    if not os.path.isfile(video):
        sys.exit(f"ERROR: no existe el video: {video}")
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", video],
        capture_output=True, text=True)
    dur_str = (r.stdout or "").strip()
    if r.returncode != 0 or not dur_str:
        sys.exit(f"ERROR: ffprobe no pudo leer {video}")
    dur = float(dur_str)
    out = []
    for i in range(n):
        # i/n (no i/(n-1)): nunca pide t=duracion exacta, que ffmpeg no sirve
        t = dur * i / n
        ruta = os.path.join(tmpdir, f"frame_{i:03d}.png")
        rf = subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", video,
             "-frames:v", "1", ruta], capture_output=True, text=True)
        if rf.returncode != 0:
            sys.exit(f"ERROR: ffmpeg no pudo extraer frame en t={t:.2f}s de {video}")
        out.append((ruta, f"t={t:.2f}s"))
    return out


def mosaico(imagenes, cols, ancho_tile, salida):
    """imagenes: [(ruta, etiqueta)]. Mosaica en cols columnas."""
    if Image is None or ImageDraw is None:
        sys.exit("ERROR: falta dependencia (PIL): pip install pillow")
    thumbs = []
    for ruta, etiqueta in imagenes:
        im = Image.open(ruta).convert("RGB")
        alto = round(im.height * ancho_tile / im.width)
        thumbs.append((im.resize((ancho_tile, alto), Image.LANCZOS), etiqueta))

    alto_tile = max(t.size[1] for t, _ in thumbs)
    barra = 28
    pad = 6
    filas = (len(thumbs) + cols - 1) // cols
    W = cols * (ancho_tile + pad) + pad
    H = filas * (alto_tile + barra + pad) + pad
    sheet = Image.new("RGB", (W, H), (18, 18, 18))
    d = ImageDraw.Draw(sheet)

    for i, (th, etiqueta) in enumerate(thumbs):
        r, c = divmod(i, cols)
        x = pad + c * (ancho_tile + pad)
        y = pad + r * (alto_tile + barra + pad)
        sheet.paste(th, (x, y + (alto_tile - th.size[1])))
        d.rectangle([x, y + alto_tile, x + ancho_tile, y + alto_tile + barra],
                    fill=(40, 40, 40))
        d.text((x + 6, y + alto_tile + 6), etiqueta, fill=(220, 220, 220))
        d.text((x + ancho_tile - 44, y + alto_tile + 6), f"#{i+1}",
               fill=(150, 150, 150))

    sheet.save(salida)
    print(f"OK {salida}: {len(thumbs)} tiles en {cols}x{filas} "
          f"({sheet.size[0]}x{sheet.size[1]})")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--dir", help="carpeta con stills PNG")
    src.add_argument("--video", help="video del que extraer frames")
    ap.add_argument("-n", type=int, default=20,
                    help="frames a extraer con --video (default 20)")
    ap.add_argument("--cols", type=int, default=4, help="columnas (default 4)")
    ap.add_argument("--ancho", type=int, default=320,
                    help="ancho de cada tile en px (default 320)")
    ap.add_argument("-o", "--salida", required=True, help="PNG de salida")
    a = ap.parse_args()

    if a.dir:
        if not os.path.isdir(a.dir):
            sys.exit(f"ERROR: no existe la carpeta: {a.dir}")
        pngs = sorted(f for f in os.listdir(a.dir)
                      if f.lower().endswith(".png"))
        if not pngs:
            sys.exit(f"sin PNG en {a.dir}")
        imagenes = [(os.path.join(a.dir, f), f) for f in pngs]
        mosaico(imagenes, a.cols, a.ancho, a.salida)
    else:
        if not os.path.isfile(a.video):
            sys.exit(f"ERROR: no existe el video: {a.video}")
        with tempfile.TemporaryDirectory() as tmp:
            imagenes = extraer_frames(a.video, a.n, tmp)
            mosaico(imagenes, a.cols, a.ancho, a.salida)


if __name__ == "__main__":
    main()
