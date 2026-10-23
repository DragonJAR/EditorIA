#!/usr/bin/env python3
"""medir_contraste.py — mide el CONTRASTE real del texto contra su superficie.

Un texto en color de acento sobre una banda del mismo color de acento es
ilegible, pero no se ve leyendo el codigo: se ve midiendo.

METODO (por que dos pasadas): el motor dibuja varias capas y algunas son
decorativas (un resplandor de acento DEBAJO de una cifra blanca). Medir una
capa intermedia daria falsos positivos. Asi que:

  Pasada A: la escena se dibuja SIN texto -> ese frame es la SUPERFICIE.
  Pasada B: la escena se dibuja normal y se registra cada texto con su color
            y la mascara real de su glifo.

Ademas, sobre esa superficie solo se mide lo que el ojo recibe de verdad: los
pixeles donde ESE texto es el ULTIMO que se dibujo (un glifo tapado por otro
no se lee). Y un texto con alfa por debajo de ALFA_MIN todavia no se ve: no
es un defecto, es una entrada.

Es la MISMA tecnica que el suelo de letra (`validate_skill.py` espia
`ImageDraw.text`), aplicada al COLOR.

Uso:
    python3 scripts/medir_contraste.py            # informe
    python3 scripts/medir_contraste.py --json r.json
    python3 scripts/medir_contraste.py --umbral 3.0
"""
import argparse
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))
sys.path.insert(0, os.path.join(BASE, "scripts", "ffmpeg_tools"))

MINIMO = 3.0        # ratio de contraste (WCAG): 3.0 para texto grande
ALFA_MIN = 128      # un texto por debajo de este alfa todavia no se ve
FONDO = (10, 10, 10, 255)   # el mundo vivo del motor es negro: si la capa es
                             # transparente, el fondo real es este

try:                       # a nivel de modulo: la espia los usa y no puede
    import numpy as np     # cerrarlos sobre el de `medir`
    from PIL import Image, ImageDraw
except ImportError:        # pragma: no cover - el tool avisa y sale
    np = None
    Image = ImageDraw = None


def _lineal(c):
    """Linealizacion sRGB de WCAG. El color entra en 0..255."""
    c = c / 255.0
    return np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _ratio(a, b):
    """Ratio de contraste WCAG entre dos luminancias."""
    hi, lo = np.maximum(a, b), np.minimum(a, b)
    return (hi + 0.05) / (lo + 0.05)


def _espia(registro, dibujar, _orig):
    """Devuelve una version de ImageDraw.text que registra (o no) cada texto."""
    def _f(self, xy, text, fill=None, font=None, *a, **k):
        if fill is not None and font is not None and str(text).strip():
            try:
                img = getattr(self, "_image", None)
                if img is not None:
                    t = str(text)
                    bb = self.textbbox(xy, t, font=font, *a, **k)
                    x0, y0, x1, y1 = (int(v) for v in bb)
                    if x1 > x0 and y1 > y0:
                        m = Image.new("L", (x1 - x0, y1 - y0), 0)
                        _orig(ImageDraw.Draw(m), (xy[0] - x0, xy[1] - y0), t,
                              font=font, fill=255, *a, **k)
                        registro.append(dict(texto=t[:40], fill=fill, msc=m,
                                             caja=(x0, y0, x1, y1)))
            except Exception:
                pass
        if not dibujar:
            return None
        return _orig(self, xy, text, fill, font, *a, **k)
    return _f


def medir(umbral=MINIMO, alfa_min=ALFA_MIN):
    """Recorre el catalogo completo y devuelve los textos con poco contraste."""
    if np is None or Image is None:
        print("ERROR: PIL/numpy no disponibles", file=sys.stderr)
        return []
    import render_plan as R

    muestras = json.load(open(os.path.join(BASE, "scripts", "escenas_muestra.json"),
                              encoding="utf-8"))["escenas"]
    hallazgos = []
    _orig = ImageDraw.ImageDraw.text

    for ancho, alto in ((1080, 1920), (1920, 1080)):
        R.formato(ancho, alto)
        ctx = R.Ctx()
        # las escenas de COLUMNA se dibujan en un lienzo de 1080 de ancho y se
        # centran: sus coordenadas de dibujo NO son las del frame final
        desvio = (ancho - 1080) // 2 if (ancho > alto and ancho > 1080) else 0
        for nombre in R.SCENES:
            e = dict(muestras.get(nombre, {"from": 0, "to": 5, "at": {}}), tipo=nombre)
            peor = None
            for t in (0.5, e["to"] / 2, e["to"] - 0.3):
                registros = []
                superficie = None

                # pasada A: la escena SIN texto es la superficie
                ImageDraw.ImageDraw.text = _espia([], False, _orig)
                try:
                    superficie = R.pintar(ctx, e, t)
                except Exception:
                    pass
                finally:
                    ImageDraw.ImageDraw.text = _orig
                if superficie is None:
                    continue

                # pasada B: la escena normal, registrando cada texto
                ImageDraw.ImageDraw.text = _espia(registros, True, _orig)
                try:
                    R.pintar(ctx, e, t)
                except Exception:
                    pass
                finally:
                    ImageDraw.ImageDraw.text = _orig

                # el ULTIMO texto sobre un pixel es el que se lee: los
                # anteriores (resplandores, fantasmas) quedan tapados.
                # La visibilidad se calcula en la CAJA de cada texto: la
                # mascara es local, no del lienzo entero.
                cubierto = np.zeros(superficie.size[::-1], dtype=bool)
                for r in reversed(registros):
                    x0, y0, x1, y1 = r["caja"]
                    m = np.asarray(r["msc"], dtype=np.float64) > 127
                    libre = ~cubierto[y0:y1, x0:x1]
                    r["visible"] = m & libre
                    cubierto[y0:y1, x0:x1] |= r["visible"]

                for r in registros:
                    fill = r["fill"]
                    if not isinstance(fill, (tuple, list)) or len(fill) < 3:
                        continue
                    a = (fill[3] if len(fill) > 3 else 255) / 255.0
                    if a * 255 < alfa_min:
                        continue      # el texto todavia no se ve: no es defecto
                    x0, y0, x1, y1 = r["caja"]
                    sel = r["visible"]
                    if not sel.any():
                        continue
                    sup = superficie.crop((x0 + desvio, y0, x1 + desvio, y1)).convert("RGBA")
                    base = Image.new("RGBA", sup.size, FONDO)
                    base.alpha_composite(sup)
                    sup_np = np.asarray(base.convert("RGB"), dtype=np.float64)
                    f = np.asarray(tuple(fill[:3]) + ((fill[3],) if len(fill) > 3 else (255,)),
                                   dtype=np.float64)
                    txt = f[:3][None, None, :] * a + sup_np * (1 - a)
                    lt = (0.2126 * _lineal(txt[..., 0]) + 0.7152 * _lineal(txt[..., 1])
                          + 0.0722 * _lineal(txt[..., 2]))[sel]
                    ls = (0.2126 * _lineal(sup_np[..., 0]) + 0.7152 * _lineal(sup_np[..., 1])
                          + 0.0722 * _lineal(sup_np[..., 2]))[sel]
                    ratios = np.sort(_ratio(lt, ls))
                    med = float(ratios[len(ratios) // 2])
                    if peor is None or med < peor[0]:
                        peor = (med, r["texto"], fill[:3])
            if peor and peor[0] < umbral:
                hallazgos.append(dict(escena=nombre, formato=f"{ancho}x{alto}",
                                      ratio=round(peor[0], 2), texto=peor[1],
                                      color=list(peor[2])))
    return hallazgos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", help="escribe el informe en un JSON")
    ap.add_argument("--umbral", type=float, default=MINIMO,
                    help=f"ratio minimo aceptable (default {MINIMO})")
    a = ap.parse_args()
    h = medir(a.umbral)
    if a.json:
        json.dump(h, open(a.json, "w"), indent=1, ensure_ascii=False)
    if not h:
        print(f"OK: ningun texto del catalogo baja de {a.umbral}:1 de contraste")
    else:
        print(f"{len(h)} textos con contraste por debajo de {a.umbral}:1")
        for x in sorted(h, key=lambda d: d["ratio"]):
            print(f"  {x['ratio']:5.2f}  {x['escena']:14s} {x['formato']:10s} "
                  f"color={tuple(x['color'])} {x['texto']!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
