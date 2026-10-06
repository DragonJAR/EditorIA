"""Identidad y utilidades compartidas por los films de marca (film_marca*.py).

La identidad sale del brand pack que el usuario pidió (--brand) o de flags
(--logo, --nombre, --lema); sin nada, modo libre: paleta neutra. El film
anima un logo, así que sin logo no hay film (error claro, nunca el de otra
marca). El logo se lleva a un lienzo cuadrado transparente SIN deformarlo
(escala uniforme); las coreografías están escritas en ese lienzo de LADO px.
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg_tools"))
from _comun import die, identidad_pieza, leer_pack, segmentos_enfasis  # noqa: E402

LADO = 1126   # lado del lienzo cuadrado del logo en el que se escribieron las coreografías


def clamp01(x): return max(0.0, min(1.0, x))
def lerp(a, b, k): return a + (b - a) * k
def prog(t, a, b): return clamp01((t - a) / max(1e-6, b - a))
def smooth(k):
    """Smoothstep: cruce parejo, sin el arranque brusco de bezier_out."""
    k = clamp01(k)
    return k * k * (3 - 2 * k)


def vivo(rgb, blanco=0.0):
    """El acento a brillo máximo (canal mayor = 255) y mezclado con blanco:
    brasas, láser y chispas derivan del acento del pack, no de un color fijo."""
    m = max(rgb) or 1
    base = [c * 255 / m for c in rgb]
    return tuple(int(round(c + (255 - c) * blanco)) for c in base)


def args_identidad(ap):
    ap.add_argument("--brand", help="brand pack (brand/*.json): colores, logo, nombre y lema")
    ap.add_argument("--logo", help="PNG del logo con transparencia (manda sobre el del pack)")
    ap.add_argument("--nombre", help="wordmark del cierre (default: nombre del pack)")
    ap.add_argument("--lema", help="lema del cierre; *palabras* en acento (default: lema del pack)")


def args_formato(ap):
    ap.add_argument("--formato", choices=["16:9", "9:16"], default="16:9",
                    help="16:9 (YouTube, web) o 9:16 (Reels, TikTok, Shorts)")


def lienzo(formato):
    return (1920, 1080) if formato == "16:9" else (1080, 1920)


def rejilla(W, H, paso=150):
    """Celdas (gx, gy) del patrón de mini logos: cubre el cuadro en cualquier
    formato (9×5 en 16:9, 7×11 en 9:16)."""
    nx, ny = (4, 2) if W >= H else (3, 5)
    return [(gx, gy) for gy in range(-ny, ny + 1) for gx in range(-nx, nx + 1)]


def preparar(args):
    """Identidad lista para animar: paleta, logo cuadrado (LADO px), ancla del
    logo en ese lienzo, wordmark, lema en segmentos y fuente de titulares."""
    idt = identidad_pieza(args.brand, args.logo, args.nombre, args.lema)
    if not idt["logo"] or not os.path.isfile(idt["logo"]):
        die("el film de marca anima un logo: pasa --brand (pack con logos.isotipo) "
            "o --logo archivo.png", kind="input")
    src = Image.open(idt["logo"]).convert("RGBA")
    lado = max(src.size)
    dx, dy = (lado - src.width) // 2, (lado - src.height) // 2
    cuadro = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    cuadro.paste(src, (dx, dy))
    logo = cuadro.resize((LADO, LADO), Image.LANCZOS)        # escala uniforme
    k = LADO / lado
    ancla = (leer_pack(args.brand).get("logos") or {}).get("ancla") if not args.logo else None
    if ancla:   # punto de interés medido en el PNG original (ej. el ojo de una cerradura)
        ancla = ((ancla[0] + dx) * k, (ancla[1] + dy) * k)
    else:       # sin medida: el centro de masa visible del logo
        a = np.asarray(logo.split()[3], dtype=np.float32)
        ys, xs = np.mgrid[0:LADO, 0:LADO]
        tot = a.sum() or 1
        ancla = (float((xs * a).sum() / tot), float((ys * a).sum() / tot))
    return {"paleta": idt["paleta"], "logo": logo, "ancla": ancla,
            "nombre": (idt["nombre"] or "").upper(),
            "lema": [(t.upper(), e) for t, e in segmentos_enfasis(idt["lema"] or "")],
            "fuente": idt["fuente"]}


def lineas_lema(d, segmentos, fnt, ancho_max):
    """Parte el lema en líneas que caben en `ancho_max`; cada línea es una
    lista [(texto, enfasis)] lista para mixed_line."""
    palabras = [(w, e) for t, e in segmentos for w in t.split()]
    lineas, actual = [], []
    for w, e in palabras:
        prueba = " ".join(x for x, _ in actual + [(w, e)])
        if actual and d.textlength(prueba, font=fnt) > ancho_max:
            lineas.append(actual); actual = []
        actual.append((w, e))
    if actual:
        lineas.append(actual)
    out = []
    for ln in lineas:   # palabras seguidas con el mismo énfasis = un segmento
        segs = []
        for w, e in ln:
            if segs and segs[-1][1] == e:
                segs[-1] = (segs[-1][0] + " " + w, e)
            else:
                segs.append((w, e))
        out.append(segs)
    return out


def draw_glow(layer, img, cx, cy, scale, alpha):
    w2 = int(img.width * scale); h2 = int(img.height * scale)
    if w2 < 4:
        return
    g = img.resize((w2, h2), Image.BILINEAR)
    if alpha < 255:
        al = g.split()[3].point(lambda v: int(v * alpha / 255)); g.putalpha(al)
    layer.alpha_composite(g, (int(cx - w2 / 2), int(cy - h2 / 2)))


def text_center(d, xy, txt, font, fill, tracking=0):
    x, y = xy
    if tracking <= 0:
        d.text((x, y), txt, font=font, fill=fill, anchor="ma"); return
    widths = [d.textlength(c, font=font) for c in txt]
    total = sum(widths) + tracking * (len(txt) - 1)
    cx = x - total / 2
    for c, wc in zip(txt, widths):
        d.text((cx, y), c, font=font, fill=fill, anchor="la")
        cx += wc + tracking


def mixed_line(d, cx, y, segments, font):
    """segments=[(texto,color)], centrado en cx."""
    widths = [d.textlength(t, font=font) for t, _ in segments]
    gaps = [d.textlength(" ", font=font)] * (len(segments) - 1)
    total = sum(widths) + sum(gaps)
    x = cx - total / 2
    for i, (t, col) in enumerate(segments):
        d.text((x, y), t, font=font, fill=col, anchor="la")
        x += widths[i] + (gaps[i] if i < len(gaps) else 0)


def dibujar_lema(capa, cx, y0, lineas, fnt, color, acento, interlineado):
    """Dibuja las líneas del lema (énfasis en el acento)."""
    d = ImageDraw.Draw(capa)
    for i, ln in enumerate(lineas):
        mixed_line(d, cx, y0 + i * interlineado,
                   [(t, acento if e else color) for t, e in ln], fnt)
