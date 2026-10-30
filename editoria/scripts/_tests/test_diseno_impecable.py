#!/usr/bin/env python3
"""Contratos de la pasada de diseño (feat/diseno-impecable, familia W-A).

Cada clase fija UNA causa raíz, medida sobre el frame que se entrega:

- R3 MONO: la mono se resuelve por NOMBRE antes que por directorio (la
  preferida gana a la de último recurso), la empaquetada (IBM Plex Mono,
  OFL) es la del motor, el peso pedido se respeta y las etiquetas mono se
  leen (la tinta mediana del glifo llega a 4.5:1 sobre su superficie).

Run: python3 -m pytest -q -p no:cacheprovider _tests/test_diseno_impecable.py
"""

import copy
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, os.path.join(SCRIPTS, "ffmpeg_tools"))
FUENTES = os.path.join(os.path.dirname(SCRIPTS), "assets", "fonts")


def _muestra(tipo):
    with open(os.path.join(SCRIPTS, "escenas_muestra.json"), encoding="utf-8") as fh:
        e = copy.deepcopy(json.load(fh)["escenas"][tipo])
    e["tipo"] = tipo
    return e


def _lum(rgb):
    """Luminancia relativa WCAG de un array (..., 3) en 0..255."""
    c = np.asarray(rgb, np.float64) / 255.0
    c = np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]


def _motor(ancho=1080, alto=1920):
    import render_plan as R
    R.formato(ancho, alto)
    R.aplicar_globales({"escenas": []})
    R._ESCALA.clear()
    return R


def _frame(R, e, t, sin=None):
    """El frame compuesto sobre negro; `sin(font)` -> True suprime ese texto."""
    orig = ImageDraw.ImageDraw.text

    def espia(self, xy, text, fill=None, font=None, *a, **k):
        if sin is not None and font is not None and sin(font):
            return None
        return orig(self, xy, text, fill, font, *a, **k)
    ImageDraw.ImageDraw.text = espia
    try:
        capa = R.pintar(R.Ctx(), e, t)
    finally:
        ImageDraw.ImageDraw.text = orig
    fondo = Image.new("RGBA", (R.W, R.H), (0, 0, 0, 255))
    fondo.alpha_composite(capa)
    return np.asarray(fondo.convert("RGB"), np.float64)


class TestMono(unittest.TestCase):
    """R3: la mono del motor es la empaquetada, con peso, y se lee."""

    def test_busca_por_nombre_antes_que_por_directorio(self):
        import _plataforma as P
        with tempfile.TemporaryDirectory() as tmp:
            primero, segundo = Path(tmp, "a"), Path(tmp, "b")
            primero.mkdir(); segundo.mkdir()
            (primero / "UltimoRecurso.ttf").write_bytes(b"x")
            (segundo / "Preferida.ttf").write_bytes(b"x")
            orig = P.dirs_fuentes
            P.dirs_fuentes = lambda: [primero, segundo]
            try:
                hit = P._buscar_en_dirs(["Preferida.ttf", "UltimoRecurso.ttf"])
            finally:
                P.dirs_fuentes = orig
        self.assertEqual(Path(hit).name, "Preferida.ttf",
                         "el ORDEN de nombres manda: el primer directorio no "
                         "puede imponer la fuente de último recurso")

    def test_la_mono_del_motor_es_la_empaquetada(self):
        R = _motor()
        self.assertEqual(os.path.dirname(os.path.abspath(R.MONO)), os.path.abspath(FUENTES),
                         f"MONO debe ser la mono empaquetada, no {R.MONO}")
        self.assertIn("IBMPlexMono", os.path.basename(R.MONO))
        lic = open(os.path.join(FUENTES, "OFL.txt"), encoding="utf-8").read()
        self.assertIn("IBM Plex Mono", lic, "la licencia OFL debe nombrar la fuente empaquetada")

    def test_el_fallback_mono_del_pack_es_la_empaquetada(self):
        from _comun import fuente_marca
        pack = os.path.join(os.path.dirname(SCRIPTS), "brand", "carbon.json")
        R = _motor()
        hit = fuente_marca(pack, "etiquetas_mono", R.MONO_FAMILIA, "mono")
        self.assertTrue(hit and os.path.exists(hit))
        if "DejaVu" not in os.path.basename(hit):   # sin DejaVu instalada
            self.assertEqual(os.path.dirname(os.path.abspath(hit)), os.path.abspath(FUENTES))

    def test_el_peso_pedido_se_respeta(self):
        R = _motor()
        f4, f7 = R.font(R.MONO, 28, 400), R.font(R.MONO, 28, 700)
        tinta = []
        for f in (f4, f7):
            m = Image.new("L", (400, 60), 0)
            ImageDraw.Draw(m).text((4, 4), "24 leads hoy", font=f, fill=255)
            tinta.append(float(np.asarray(m, np.float64).sum()))
        self.assertGreater(tinta[1], tinta[0] * 1.12,
                           "peso 700 debe dibujar un trazo más grueso que 400")

    def test_las_etiquetas_mono_se_leen(self):
        """Tinta mediana del glifo mono vs su superficie >= 4.5:1 (AA).

        El color ya pasaba (medir_contraste mide el COLOR): lo que no se leía
        era el trazo de Courier New, tan fino que la mitad de sus píxeles
        quedaban a medio pintar (~3:1 de mediana)."""
        for tipo in ("leads", "handoff"):
            R = _motor()
            e = R.completar_escena(_muestra(tipo), 0)
            t = e["from"] + (e["to"] - e["from"]) * 0.85
            # la familia, no el archivo: el 700 dibuja con el hermano SemiBold
            fam = os.path.basename(R.MONO).rpartition("-")[0] + "-"
            con = _frame(R, e, t)
            sin = _frame(R, e, t, sin=lambda f: os.path.basename(
                str(getattr(f, "path", ""))).startswith(fam))
            dif = np.abs(con - sin).sum(axis=2) > 6
            self.assertGreater(int(dif.sum()), 200, f"{tipo}: no hay etiqueta mono a medir")
            lt, ls = _lum(con[dif]), _lum(sin[dif])
            r = (np.maximum(lt, ls) + 0.05) / (np.minimum(lt, ls) + 0.05)
            self.assertGreaterEqual(float(np.median(r)), 4.5,
                                    f"{tipo}: la mono se lee a {np.median(r):.2f}:1")


if __name__ == "__main__":
    unittest.main()
