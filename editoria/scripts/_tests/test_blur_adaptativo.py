#!/usr/bin/env python3
"""Tests del motion blur ADAPTATIVO (`render_plan.py --blur auto[:N]`).

QUE PROTEGE

1. Compatibilidad: `--blur 5` / `--blur 1` / `--blur 0` siguen siendo enteros y
   siguen el camino de siempre; `auto` es opt-in.
2. Exactitud: con el mismo numero de sub-frames, el adaptativo da los MISMOS
   pixeles que el fijo (los conjuntos 1 -> 3 -> 9 estan anidados y centrados).
3. Economia: un frame en reposo para antes que uno en plena entrada.

Run with: python3 -m unittest discover -s scripts/_tests
"""

import argparse
import copy
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, os.path.join(SCRIPTS, "ffmpeg_tools"))


def _muestra(tipo):
    with open(os.path.join(SCRIPTS, "escenas_muestra.json"), encoding="utf-8") as fh:
        e = copy.deepcopy(json.load(fh)["escenas"][tipo])
    e.setdefault("tipo", tipo)
    return e


class TestTipoBlur(unittest.TestCase):
    def test_parseo(self):
        import render_plan as R
        self.assertEqual(R._tipo_blur("5"), 5)
        self.assertEqual(R._tipo_blur("1"), 1)
        self.assertEqual(R._tipo_blur("0"), 0)
        self.assertEqual(R._tipo_blur("auto"), -R.BLUR_AUTO_TOPE)
        self.assertEqual(R._tipo_blur("auto:27"), -27)
        for malo in ("x", "auto:2", "auto:x", "-3"):
            with self.assertRaises(argparse.ArgumentTypeError):
                R._tipo_blur(malo)

    def test_offsets_anidados(self):
        import render_plan as R
        for n in (1, 3, 9):
            grande = {round(x, 9) for x in R._blur_offsets(3 * n)}
            self.assertTrue({round(x, 9) for x in R._blur_offsets(n)} <= grande)


class TestBlurAdaptativo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import numpy  # noqa: F401
            from PIL import Image  # noqa: F401
        except ImportError:
            raise unittest.SkipTest("sin numpy/PIL")
        import render_plan as R
        cls.R = R
        R.formato(1080, 1920)
        cls.ctx = R.Ctx()
        cls.e = R.completar_escena(_muestra("apertura"), 0)

    def _np(self, img):
        import numpy as np
        return np.asarray(img, dtype=np.int16)

    def test_mismos_pixeles_que_el_fijo(self):
        import numpy as np
        R = self.R
        t = 0.35
        info = {}
        a = R._blur_adaptativo(self.ctx, [self.e], self.e["to"], t, 30, 3, 0.5, set(), tol=-1, info=info)
        b = R._blur_de_submuestreo(self.ctx, [self.e], self.e["to"], t, 30, 3, 0.5, set())
        self.assertEqual(info["muestras"], 3)
        self.assertLessEqual(int(np.abs(self._np(a) - self._np(b)).max()), 1)

    def test_reposo_para_antes_que_la_entrada(self):
        R = self.R
        quieto, mueve = {}, {}
        R._blur_adaptativo(self.ctx, [self.e], self.e["to"], self.e["to"] - 0.8, 30, 27, 0.5, set(), info=quieto)
        R._blur_adaptativo(self.ctx, [self.e], self.e["to"], 0.25, 30, 27, 0.5, set(), info=mueve)
        self.assertLessEqual(quieto["muestras"], mueve["muestras"])
        self.assertLessEqual(quieto["muestras"], 9)

    def test_frame_con_blur_acepta_auto(self):
        R = self.R
        img = R.frame_con_blur(self.ctx, [self.e], self.e["to"], 0.4, 30, -9, 0.5, set())
        self.assertEqual(img.size, (R.W, R.H))


if __name__ == "__main__":
    unittest.main()
