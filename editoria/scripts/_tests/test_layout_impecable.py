#!/usr/bin/env python3
"""Contratos de layout y contraste de la pasada de diseño (familia W-B).

Cada clase fija UNA causa raíz, medida sobre el frame que se entrega:

- R5.4 CAPA FIJA: el rótulo (`rotulo_y()`) y la línea de fuente
  (`pie_fuente`) van en una capa que NO escala ni se desplaza con el
  encuadre (`_crecer`, push-in, flotación): el rótulo cae a la misma altura
  de pantalla en toda escena y en todo instante, y la fuente sobre UNA línea
  base por encima del borde seguro inferior.

Run: python3 -m pytest -q -p no:cacheprovider _tests/test_layout_impecable.py
"""

import copy
import json
import os
import sys
import unittest

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, os.path.join(SCRIPTS, "ffmpeg_tools"))

MAGENTA = (255, 0, 255)


def _muestra(tipo):
    with open(os.path.join(SCRIPTS, "escenas_muestra.json"), encoding="utf-8") as fh:
        e = copy.deepcopy(json.load(fh)["escenas"][tipo])
    e["tipo"] = tipo
    return e


def _motor(ancho=1080, alto=1920):
    import render_plan as R
    R.formato(ancho, alto)
    R.aplicar_globales({"escenas": []})
    R._ESCALA.clear()
    R._CAMARA["activa"] = False
    return R


def _magenta(img):
    """Máscara de la tinta magenta (el rótulo o la fuente teñidos por el test)."""
    a = np.asarray(img.convert("RGB"), np.int16)
    return (a[..., 0] > 150) & (a[..., 2] > 150) & (a[..., 1] < 90)


def _filas(m):
    ys = np.where(m.any(axis=1))[0]
    return (int(ys.min()), int(ys.max())) if len(ys) else None


def _compuesto(R, e, t, tenir, crudo=False):
    """El frame compuesto de la escena sola en t, con el rótulo (`tenir` =
    "rotulo") o la fuente ("fuente") dibujados en magenta. `crudo`: la capa
    de la escena SIN encuadre (dónde la puso su layout)."""
    orig_rot, orig_pie = R.rotulo, R.pie_fuente

    def rot(ctx, layer, t_, texto, at, y=None, color=None, tam=None):
        return orig_rot(ctx, layer, t_, str(texto).replace("*", ""), at, y=y,
                        color=MAGENTA if tenir == "rotulo" else color, tam=tam)

    def pie(ctx, d, e_, t_, t_def):
        gris = R.GRIS
        if tenir == "fuente":
            R.GRIS = MAGENTA
        try:
            return orig_pie(ctx, d, e_, t_, t_def)
        finally:
            R.GRIS = gris
    R.rotulo, R.pie_fuente = rot, pie
    try:
        if crudo:
            return R.pintar(R.Ctx(), e, t)
        dur = e["to"] - e["from"]
        return R.componer(R.Ctx(), [e], dur, t, set())
    finally:
        R.rotulo, R.pie_fuente = orig_rot, orig_pie


class TestCapaFija(unittest.TestCase):
    """R5.4: el rótulo y la fuente no viajan con el encuadre del contenido."""

    ROTULADAS = ("hoy", "recupera", "stats", "timeline", "medianoche", "leads",
                 "bars", "pago", "buscador", "index", "notificacion")
    CON_FUENTE = ("bars", "stats", "timeline", "index", "gauge", "buscador")

    def _tope_rotulo(self, R, tipo, t):
        e = _muestra(tipo)
        e["from"], e["to"] = 0.0, e["to"] - e["from"]
        R._ESCALA.clear()
        f = _filas(_magenta(_compuesto(R, e, t, "rotulo")))
        self.assertIsNotNone(f, f"{tipo}: sin rótulo a {t}s")
        # la tinta de "L" y de "d" no empieza a la misma altura: se mide el
        # desplazamiento de pantalla frente al layout de la escena
        f0 = _filas(_magenta(_compuesto(R, e, t, "rotulo", crudo=True)))
        return f[0] - f0[0]

    def _formato(self, ancho, alto):
        R = _motor(ancho, alto)
        topes = {}
        for tipo in self.ROTULADAS:
            # asentado y casi al final: el push-in ya empujó todo lo que empuja
            e = _muestra(tipo)
            fin = e["to"] - e["from"] - 0.5
            topes[tipo] = (self._tope_rotulo(R, tipo, 2.5), self._tope_rotulo(R, tipo, fin))
        todos = [v for par in topes.values() for v in par]
        self.assertLessEqual(max(abs(v) for v in todos), 1,
                             f"{ancho}x{alto}: el encuadre mueve el rótulo (px de pantalla vs layout): {topes}")

    def test_rotulo_a_la_misma_altura_en_9x16(self):
        self._formato(1080, 1920)

    def test_rotulo_a_la_misma_altura_en_16x9(self):
        self._formato(1920, 1080)

    def test_fuente_sobre_una_linea_base(self):
        for ancho, alto in ((1080, 1920), (1920, 1080)):
            R = _motor(ancho, alto)
            fondos = {}
            for tipo in self.CON_FUENTE:
                e = _muestra(tipo)
                if not e.get("fuente"):
                    continue
                e["from"], e["to"] = 0.0, e["to"] - e["from"]
                R._ESCALA.clear()
                f = _filas(_magenta(_compuesto(R, e, e["to"] - 0.5, "fuente")))
                self.assertIsNotNone(f, f"{tipo}: sin línea de fuente")
                fondos[tipo] = f[1]
            self.assertGreaterEqual(len(fondos), 3)
            self.assertLessEqual(max(fondos.values()) - min(fondos.values()), 2,
                                 f"{ancho}x{alto}: la línea de fuente no comparte base: {fondos}")
            self.assertLessEqual(max(fondos.values()), R.H - R.SAFE["bottom"] - 12,
                                 f"{ancho}x{alto}: la fuente roza el borde seguro: {fondos}")


if __name__ == "__main__":
    unittest.main()
