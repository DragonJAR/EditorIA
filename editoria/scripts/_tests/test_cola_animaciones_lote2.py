#!/usr/bin/env python3
"""Contratos del lote 2 (EI-25): contraste buscador, pop de recupera, vida index.

Run: python3 -m pytest -q -p no:cacheprovider _tests/test_cola_animaciones_lote2.py
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


def _muestra(tipo):
    with open(os.path.join(SCRIPTS, "escenas_muestra.json"), encoding="utf-8") as fh:
        e = copy.deepcopy(json.load(fh)["escenas"][tipo])
    e["tipo"] = tipo
    return e


class TestColaLote2(unittest.TestCase):
    def setUp(self):
        import render_plan as R
        import medir_animacion as M
        R.formato(1080, 1920)
        R.aplicar_globales({"escenas": []})
        R._ESCALA.clear()
        self.R, self.M = R, M
        self.ctx = R.Ctx()

    def _compuesta(self, tipo, frac=0.85):
        R = self.R
        e = R.completar_escena(_muestra(tipo), 0)
        t = e["from"] + (e["to"] - e["from"]) * frac
        fondo = Image.new("RGBA", (R.W, R.H), (0, 0, 0, 255))
        fondo.alpha_composite(R.pintar(self.ctx, e, t))
        return fondo.convert("RGB"), e, t

    def test_buscador_secundario_no_es_niebla(self):
        """El resultado sin acento usa placa PANEL2 legible, no blanco@22."""
        R = self.R
        cuerpo = open(os.path.join(SCRIPTS, "render_plan.py"), encoding="utf-8").read()
        sc = cuerpo.split("def sc_buscador(", 1)[1].split("\ndef sc_", 1)[0]
        self.assertIn("PANEL2", sc)
        self.assertNotIn("(255, 255, 255, int(22", sc)
        im, _, _ = self._compuesta("buscador", 0.85)
        a = np.asarray(im)
        # banda de resultados secundarios (~y 700–860): no debe ser casi-negro
        # ni blanco puro; PANEL2 ~ (38,38,38) compuesto opaco
        banda = a[720:780, 200:880]
        mean = banda.mean(axis=(0, 1))
        self.assertGreater(float(mean.mean()), 25.0, mean)
        self.assertLess(float(mean.mean()), 120.0, mean)

    def test_recupera_usa_cruce_no_corte(self):
        """El salto cliente→PAGADO es fundido cruzado (suave), no corte en pagado."""
        cuerpo = open(os.path.join(SCRIPTS, "render_plan.py"), encoding="utf-8").read()
        sc = cuerpo.split("def sc_recupera(", 1)[1].split("\ndef sc_", 1)[0]
        self.assertIn("fade_cli", sc)
        self.assertIn('"suave"', sc)
        R, M = self.R, self.M
        e = R.completar_escena(_muestra("recupera"), 0)
        fps = 30
        frames = []
        for i in range(int(e["to"] * fps)):
            t = i / fps
            fondo = Image.new("RGBA", (R.W, R.H), (0, 0, 0, 255))
            fondo.alpha_composite(R.pintar(self.ctx, e, t))
            k = M.LADO / min(R.W, R.H)
            frames.append(np.asarray(
                fondo.convert("L").resize((int(R.W * k), int(R.H * k))), np.float32))
        r = M.metricas(np.array(frames), fps, e["to"])
        self.assertEqual(r["pops"], [], r)

    def test_index_flota_en_hold(self):
        """El bloque del índice se desplaza entre t y t+0.5 s del hold."""
        R = self.R
        e = R.completar_escena(_muestra("index"), 0)
        cuerpo = open(os.path.join(SCRIPTS, "render_plan.py"), encoding="utf-8").read()
        sc = cuerpo.split("def sc_index(", 1)[1].split("\ndef sc_", 1)[0]
        self.assertIn("flota(", sc)
        a = np.asarray(R.pintar(self.ctx, e, 3.0).convert("L"), np.float32)
        b = np.asarray(R.pintar(self.ctx, e, 3.5).convert("L"), np.float32)
        self.assertGreater(float(np.abs(a - b).mean()), 0.05)


if __name__ == "__main__":
    unittest.main()
