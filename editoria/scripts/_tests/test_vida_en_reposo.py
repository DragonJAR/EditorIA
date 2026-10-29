#!/usr/bin/env python3
"""Tests de la vida en reposo: un rotulo inferior sostenido no se congela.

QUE PROTEGE

`rotulo_inferior` esta en CAMARA_PROPIA (sin push-in: es un overlay) y nada
mas lo movia: en el video real del catalogo se quedo 3.0 s congelado
(222.75-225.75 s) y la puerta `quieto_max > 1.0 s` fallo. Las escenas que se
leen quietas (`QUIETAS`) llevan ahora la misma flotacion de la camara
(`vida`, FLOTA_CAM px a FLOTA_HZ): sin push-in, sin curva nueva, funcion
pura de t. `final`, `kenburns` y `demo` ya se mueven solas y no cambian.

Run with: python3 -m pytest -q -p no:cacheprovider _tests/test_vida_en_reposo.py
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


class TestVidaEnReposo(unittest.TestCase):
    def setUp(self):
        import render_plan as R
        import medir_animacion as M
        R.formato(1080, 1920)
        R.aplicar_globales({"escenas": []})
        R._ESCALA.clear()
        self.R, self.M = R, M
        self.ctx = R.Ctx()
        self.e = R.completar_escena(_muestra("rotulo_inferior"), 0)

    def _gris(self, t):
        """El cuadro del rotulo SOBRE NEGRO (un fondo quieto: el peor caso, el
        del video real) a la escala de analisis del medidor."""
        R, e = self.R, self.e
        fondo = Image.new("RGBA", (R.W, R.H), (0, 0, 0, 255))
        fondo.alpha_composite(R.encuadrar(self.ctx, e, 0, t, R.pintar(self.ctx, e, t).copy()))
        k = self.M.LADO / min(R.W, R.H)
        return np.asarray(fondo.convert("L").resize((int(R.W * k), int(R.H * k))), np.float32)

    def test_la_vida_es_una_flotacion_chica_y_pura(self):
        R, e = self.R, self.e
        self.assertIn("rotulo_inferior", R.QUIETAS)
        vals = [R.respiracion(e, 1.0 + i * 0.25) for i in range(13)]
        for f, dy, dx in vals:
            self.assertEqual(f, 1.0, "sin push-in: es un overlay")
            self.assertEqual(dx, 0.0)
            self.assertLessEqual(abs(dy), R.FLOTA_CAM + 1e-9)
        self.assertGreater(max(abs(v[1]) for v in vals), 1.0, "tiene que moverse")
        self.assertEqual(vals, [R.respiracion(e, 1.0 + i * 0.25) for i in range(13)])
        self.assertEqual(R.respiracion(dict(e, respira=False), 2.0), (1.0, 0.0, 0.0))

    def test_el_hold_cambia_al_menos_un_bloque(self):
        """Entre t y t+0.5 s del hold, algun bloque cambia mas que CELDA_MOV
        (el umbral de `quieto` del medidor)."""
        M = self.M
        for t in (1.5, 2.5, 3.5):
            a, b = self._gris(t), self._gris(t + 0.5)
            cambio = np.abs(M._rejilla(np.stack([a, b])).mean(axis=(2, 4))[1]
                            - M._rejilla(np.stack([a, b])).mean(axis=(2, 4))[0])
            with self.subTest(t=t):
                self.assertGreaterEqual(int((cambio > M.CELDA_MOV).sum()), 1)

    def test_un_hold_de_3s_no_se_congela_para_el_medidor(self):
        """El medidor real (`quietud`) sobre el rotulo sostenido 3+ s y seguido
        de mas video (si el hold es lo ultimo, cuenta como el CTA)."""
        M, e = self.M, self.e
        fps = 12
        F = [self._gris(i / fps) for i in range(int(e["to"] * fps))]
        F = F + F[:fps]   # sigue video que se mueve: la entrada otra vez
        q = M.quietud(np.array(F), fps, len(F) / fps)
        self.assertLessEqual(q["quieto_max"], 1.0, q)


if __name__ == "__main__":
    unittest.main()
