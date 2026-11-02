#!/usr/bin/env python3
"""Tests de scripts/hand_draw.py — dominio de trazos portado de HandDraw."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import hand_draw as hd  # noqa: E402


class TestSuavizado(unittest.TestCase):
    def test_sin_anterior_devuelve_crudo(self):
        self.assertEqual(hd.suavizar_punto(None, (300, 180)), (300.0, 180.0))

    def test_ema_en_movimiento_pequeno(self):
        out = hd.suavizar_punto((300, 180), (320, 160), alpha=0.25, snap=160)
        self.assertEqual(out, (305.0, 175.0))

    def test_snap_en_salto_grande(self):
        out = hd.suavizar_punto((100, 100), (420, 300), alpha=0.25, snap=160)
        self.assertEqual(out, (420.0, 300.0))

    def test_dibujo_responde_mas_que_idle(self):
        prev, raw = (100.0, 100.0), (140.0, 100.0)
        dibujo = hd.suavizar_punto(
            prev, raw,
            alpha=hd.SUAVIZADO_DIBUJO["alpha"],
            snap=hd.SUAVIZADO_DIBUJO["snap"],
        )
        idle = hd.suavizar_punto(
            prev, raw,
            alpha=hd.SUAVIZADO_DEFECTO["alpha"],
            snap=hd.SUAVIZADO_DEFECTO["snap"],
        )
        self.assertGreater(dibujo[0], idle[0])


class TestViewport(unittest.TestCase):
    def test_viewport_a_mundo_con_pan(self):
        canvas = {"left": 200, "top": 80, "width": 500, "height": 300}
        self.assertEqual(
            hd.punto_viewport_a_mundo((320, 180), canvas, (900, 600)),
            (1020, 700),
        )

    def test_viewport_a_mundo_con_zoom(self):
        canvas = {"left": 200, "top": 80, "width": 500, "height": 300}
        self.assertEqual(
            hd.punto_viewport_a_mundo((320, 180), canvas, (900, 600), 2),
            (960, 650),
        )

    def test_pan_sigue_la_mano(self):
        self.assertEqual(
            hd.pan_offset_viewport(
                (900, 600), (40, -30),
                {"width": 500, "height": 300},
                {"width": 2000, "height": 1400},
            ),
            (860, 630),
        )


class TestHerramienta(unittest.TestCase):
    def test_segmento_dentro_del_canvas(self):
        canvas = {"left": 100, "top": 50, "width": 400, "height": 300}
        last, seg = hd.avanzar_herramienta(None, (160, 120), canvas, kind="pencil", color="#2563eb")
        self.assertEqual(last, (60, 70))
        self.assertEqual(seg["from"], (60, 70))
        self.assertEqual(seg["to"], (60, 70))
        self.assertEqual(seg["color"], "#2563eb")

        last2, seg2 = hd.avanzar_herramienta(last, (180, 150), canvas, kind="pencil", color="#2563eb")
        self.assertEqual(seg2["from"], (60, 70))
        self.assertEqual(seg2["to"], (80, 100))
        self.assertEqual(last2, (80, 100))

    def test_fuera_limpia_last(self):
        canvas = {"left": 100, "top": 50, "width": 400, "height": 300}
        last, _ = hd.avanzar_herramienta(None, (160, 120), canvas)
        last2, seg = hd.avanzar_herramienta(last, (80, 120), canvas)
        self.assertIsNone(last2)
        self.assertIsNone(seg)


class TestGestos(unittest.TestCase):
    def test_ratio_pinch(self):
        landmarks = [{"x": 0, "y": 0, "z": 0} for _ in range(21)]
        landmarks[0] = {"x": 0.1, "y": 0.5, "z": 0}
        landmarks[5] = {"x": 0.5, "y": 0.5, "z": 0}
        landmarks[4] = {"x": 0.2, "y": 0.5, "z": 0}
        landmarks[8] = {"x": 0.3, "y": 0.5, "z": 0}
        self.assertAlmostEqual(hd.ratio_pinch(landmarks), 0.25)

    def test_histeresis_pinch(self):
        self.assertTrue(hd.siguiente_pinch(False, 0.21))
        self.assertTrue(hd.siguiente_pinch(True, 0.28))
        self.assertFalse(hd.siguiente_pinch(True, 0.36))

    def test_histeresis_puno(self):
        self.assertTrue(hd.siguiente_puno(False, 1.14))
        self.assertTrue(hd.siguiente_puno(True, 1.3))
        self.assertFalse(hd.siguiente_puno(True, 1.48))


class TestCLI(unittest.TestCase):
    def test_suavizar_y_pintar(self):
        import subprocess

        script = os.path.join(SCRIPTS, "hand_draw.py")
        with tempfile.TemporaryDirectory() as tmp:
            puntos = os.path.join(tmp, "puntos.json")
            limpio = os.path.join(tmp, "limpio.json")
            png = os.path.join(tmp, "overlay.png")
            with open(puntos, "w", encoding="utf-8") as f:
                json.dump({
                    "strokes": [{
                        "color": "#ef4444",
                        "width": 8,
                        "points": [[100, 100], [120, 100], [140, 110], [400, 400]],
                    }],
                }, f)
            # subprocess: el censo de CLIs solo cuenta ejecución real
            r1 = subprocess.run(
                [sys.executable, script, "suavizar", puntos, "-o", limpio],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(r1.returncode, 0, r1.stderr)
            self.assertTrue(os.path.isfile(limpio))
            with open(limpio, encoding="utf-8") as fh:
                data = json.load(fh)
            # el salto grande (140→400) hace snap: el último punto se conserva
            last = data["strokes"][0]["points"][-1]
            self.assertEqual((last["x"], last["y"]), (400.0, 400.0))
            r2 = subprocess.run(
                [sys.executable, script, "pintar", limpio, "-o", png,
                 "--ancho", "480", "--alto", "640"],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(r2.returncode, 0, r2.stderr)
            self.assertTrue(os.path.isfile(png))
            self.assertGreater(os.path.getsize(png), 100)


if __name__ == "__main__":
    unittest.main()
