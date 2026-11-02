#!/usr/bin/env python3
"""Compone un thumbnail con identidad de marca (brand pack opcional) sobre una imagen base.

El craft creativo (brief, tension, open loop) lo hace el agente con el usuario
(review-gate, ver references/thumbnails.md); esta herramienta ejecuta la
composicion deterministicamente: texto <=4 palabras en la fuente de
titulares (Plus Jakarta Sans ExtraBold sin pack), blanco sobre sombra, el
acento del brand pack (--brand) o el neutro del modo libre, y
posicionamiento en tercios (rule of thirds).

Ejemplos:
  python3 thumbnail.py frame.png --texto "ASI SE HACKEA" -o thumb.png
  python3 thumbnail.py frame.png --texto "ASI SE HACKEA" --brand brand/mi_marca.json
  python3 thumbnail.py frame.png --texto "EL DATO QUE FALTA" --resaltar "FALTA"
  python3 thumbnail.py frame.png --texto "MIRA ESTO" --formato 9:16 -o thumb_v.png
  python3 thumbnail.py frame.png --texto "MIRA ESTO" --guia -o thumb_guia.png
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _comun import (add_common, apply_common, asegurar_padre, die, emit, fuente_marca,  # noqa: E402
                      info, tokens_efectivos)

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
except ImportError:
    Image = ImageDraw = ImageFont = ImageFilter = None


FORMATOS = {"16:9": (1280, 720), "9:16": (1080, 1920)}


def cargar_fuente(px, fuente):
    if fuente and os.path.isfile(fuente):
        f = ImageFont.truetype(fuente, px)
        try:
            f.set_variation_by_axes([800])   # fuente variable: ExtraBold
        except Exception:
            pass
        return f
    return ImageFont.load_default()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="imagen base (frame del video o generada)")
    ap.add_argument("--texto", required=True,
                    help="texto gancho, MAXIMO 4 palabras (regla de la skill)")
    ap.add_argument("--resaltar",
                    help="palabra del texto a pintar en el color de acento")
    ap.add_argument("--paleta", help="paleta del modo libre (references/paleta.md): el "
                                     "acento sale de ella; si hay --brand, manda el pack")
    ap.add_argument("--brand", help="brand pack (brand/*.json): acento y fuente de titulares; "
                    "sin pack = modo libre (paleta neutra)")
    ap.add_argument("-o", "--output", help="PNG de salida (default: <input>_thumb.png)")
    ap.add_argument("--formato", choices=["16:9", "9:16"], default="16:9",
                    help="formato de salida (default 16:9)")
    ap.add_argument("--posicion", choices=["arriba", "abajo", "centro"],
                    default="arriba",
                    help="tercio donde va el texto (default arriba; abajo evita "
                         "la cara si esta arriba)")
    ap.add_argument("--guia", action="store_true",
                    help="quema la grilla de tercios 3x3 para verificar composicion")
    add_common(ap)
    args = ap.parse_args()
    apply_common(args)

    if not os.path.isfile(args.input):
        die(f"no existe la imagen: {args.input}")
    palabras = args.texto.split()
    if len(palabras) > 4:
        die(f"el texto tiene {len(palabras)} palabras; el maximo es 4 "
            f"(ver references/thumbnails.md): {args.texto!r}")
    if args.resaltar and args.resaltar not in palabras:
        die(f"--resaltar {args.resaltar!r} no es una palabra del texto")
    if Image is None:
        die("thumbnail.py necesita Pillow (pip install pillow)", kind="missing_tool")

    # el pack manda si se nombro una marca; si no, la paleta del catalogo
    pal = tokens_efectivos(args.brand, args.paleta)
    NEGRO, ACENTO, BLANCO = pal["negro"], pal["acento"], pal["blanco"]
    fuente = fuente_marca(args.brand)
    W, H = FORMATOS[args.formato]
    base = Image.open(args.input).convert("RGB")
    # cubrir el formato: scale + crop central
    escala = max(W / base.width, H / base.height)
    base = base.resize((int(base.width * escala) + 1, int(base.height * escala) + 1),
                       Image.LANCZOS)
    x0 = (base.width - W) // 2
    y0 = (base.height - H) // 2
    img = base.crop((x0, y0, x0 + W, y0 + H))

    # oscurecer leve para que el texto lea (gradiente inferior/superior)
    overlay = Image.new("L", (1, H), 0)
    for y in range(H):
        # sombra mas fuerte en el tercio del texto
        if args.posicion == "arriba":
            f = max(0.0, 1.0 - y / (H * 0.55))
        elif args.posicion == "abajo":
            f = max(0.0, (y - H * 0.45) / (H * 0.55))
        else:
            f = 0.55
        overlay.putpixel((0, y), int(110 * f))
    sombra = Image.new("RGB", (W, H), NEGRO)
    img = Image.composite(img, Image.blend(img, sombra, 0.5), overlay.resize((W, H)))

    d = ImageDraw.Draw(img)
    # tamaño de fuente: que el texto ocupe ~85% del ancho
    px = 10
    font = cargar_fuente(px, fuente)
    while d.textlength(args.texto, font=font) < W * 0.85 and px < H // 3:
        px += 4
        font = cargar_fuente(px, fuente)
    # medir por palabras para pintar el resaltado
    anchos = [d.textlength(p + " ", font=font) for p in palabras]
    total_w = sum(anchos) - d.textlength(" ", font=font)
    x = (W - total_w) / 2
    y = {"arriba": H * 0.10, "centro": H * 0.42, "abajo": H * 0.72}[args.posicion]

    # glow sutil del acento detras del texto (acento de marca, no fondo plano)
    pad = px * 0.35
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    dg = ImageDraw.Draw(glow)
    dg.rectangle([x - pad, y - pad * 0.5, x + total_w + pad, y + px + pad * 0.5],
                 fill=ACENTO)
    glow = glow.filter(ImageFilter.GaussianBlur(px * 0.5))
    img = Image.blend(img, Image.composite(glow, img,
                                           Image.new("L", (W, H), 60)), 0.35)
    d = ImageDraw.Draw(img)

    for p, w in zip(palabras, anchos):
        color = ACENTO if p == args.resaltar else BLANCO
        # contorno negro para legibilidad
        for ox, oy in [(-2, 0), (2, 0), (0, -2), (0, 2), (-1, -1), (1, 1)]:
            d.text((x + ox, y + oy), p, font=font, fill=NEGRO)
        d.text((x, y), p, font=font, fill=color)
        x += w

    if args.guia:
        for i in (1, 2):
            d.line([W * i / 3, 0, W * i / 3, H], fill=ACENTO, width=2)
            d.line([0, H * i / 3, W, H * i / 3], fill=ACENTO, width=2)

    output = args.output or os.path.splitext(args.input)[0] + "_thumb.png"
    asegurar_padre(output)
    img.save(output)
    info(f"OK {output} ({W}x{H}, {len(palabras)} palabras)")
    emit(output, formato=args.formato, palabras=len(palabras))


if __name__ == "__main__":
    main()
