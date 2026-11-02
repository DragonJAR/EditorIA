#!/usr/bin/env python3
"""Contratos del lote 3 (EI-25): camino con S + chispa, confetti columnas,
hold vivo en chat/final, QUIETAS de rotulo_inferior.

Run: python3 -m pytest -q -p no:cacheprovider _tests/test_cola_animaciones_lote3.py
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


class TestColaLote3(unittest.TestCase):
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

    def test_camino_usa_chispa_y_ruta_s(self):
        """El camino lleva chispa + latido y la muestra usa ruta `s` (ocup)."""
        R = self.R
        cuerpo = open(os.path.join(SCRIPTS, "render_plan.py"), encoding="utf-8").read()
        sc = cuerpo.split("def sc_camino(", 1)[1].split("\ndef sc_", 1)[0]
        self.assertIn("chispa", sc.lower() + "p_chispa")
        self.assertIn("p_chispa", sc)
        self.assertIn("latido(", sc)
        m = _muestra("camino")
        self.assertEqual(m.get("ruta"), "s")
        im, e, _ = self._compuesta("camino", 0.7)
        a = np.asarray(im)
        # banda del path (~y centro): no es negro puro
        banda = a[int(R.H * 0.35):int(R.H * 0.60), 80:1000]
        self.assertGreater(float(banda.mean()), 8.0, banda.mean())

    def test_confetti_columnas_no_110_aleatorias(self):
        """Lluvia por columnas solapadas (dens), no el bucle de 110 RNG."""
        cuerpo = open(os.path.join(SCRIPTS, "render_plan.py"), encoding="utf-8").read()
        sc = cuerpo.split("def sc_confetti(", 1)[1].split("\ndef sc_", 1)[0]
        self.assertIn("ncols", sc)
        self.assertIn("por_col", sc)
        self.assertNotIn("for i in range(110)", sc)

    def test_chat_flota_en_hold(self):
        """El hilo de chat se desplaza entre t y t+0.5 s del hold."""
        R = self.R
        e = R.completar_escena(_muestra("chat"), 0)
        cuerpo = open(os.path.join(SCRIPTS, "render_plan.py"), encoding="utf-8").read()
        sc = cuerpo.split("def sc_chat(", 1)[1].split("\ndef sc_", 1)[0]
        self.assertIn("flota(", sc)
        a = np.asarray(R.pintar(self.ctx, e, 4.5).convert("L"), np.float32)
        b = np.asarray(R.pintar(self.ctx, e, 5.0).convert("L"), np.float32)
        self.assertGreater(float(np.abs(a - b).mean()), 0.08)

    def test_final_latido_en_hold(self):
        """El lockup de cierre late (escala) en el hold."""
        cuerpo = open(os.path.join(SCRIPTS, "render_plan.py"), encoding="utf-8").read()
        sc = cuerpo.split("def sc_final(", 1)[1].split("\ndef sc_", 1)[0]
        self.assertIn("latido(", sc)
        self.assertIn("pulso", sc)
        R = self.R
        e = R.completar_escena(_muestra("final"), 0)
        a = np.asarray(R.pintar(self.ctx, e, 2.5).convert("L"), np.float32)
        b = np.asarray(R.pintar(self.ctx, e, 3.2).convert("L"), np.float32)
        self.assertGreater(float(np.abs(a - b).mean()), 0.05)

    def test_rotulo_sigue_quieta_por_diseno(self):
        """rotulo_inferior permanece en QUIETAS (techo ocup honesto)."""
        R = self.R
        self.assertIn("rotulo_inferior", R.QUIETAS)
        e = R.completar_escena(_muestra("rotulo_inferior"), 0)
        t = e["from"] + (e["to"] - e["from"]) * 0.55
        fondo = Image.new("RGBA", (R.W, R.H), (0, 0, 0, 255))
        capa = R.pintar(self.ctx, e, t)
        fondo.alpha_composite(R.encuadrar(self.ctx, e, 0, t, capa.copy()))
        a = np.asarray(fondo.convert("RGB"))
        # hay tinta en alguna banda (lower third + vida)
        self.assertGreater(float(a.mean()), 1.0, a.mean())
        self.assertGreater(int((a > 20).sum()), 500)


if __name__ == "__main__":
    unittest.main()
