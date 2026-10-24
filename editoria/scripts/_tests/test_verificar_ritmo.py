#!/usr/bin/env python3
"""Tests de verificar_ritmo.py — la verificacion de ritmo de una pieza.

Por que existe el flag `--sobre-footage-vivo`: los minimos de "cuadros
quietos" y "pausa" son de una pieza de motion graphics, donde el silencio
visual lo compone el PIECE. Una pieza sobre planos reales que siempre se
mueven no puede tener ese silencio: no es un defecto, es que el minimo no
aplica (el mismo caso que la rafaga, que ya es un WARN cuando el concepto
no la pide). Con el flag, esos dos minimos pasan a "no aplica" (con su
motivo) y los demas (cadencia, rafaga) se siguen midiendo igual.

Run with: python3 -m unittest discover -s SKILL/scripts/_tests
"""

import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
VERIFICAR = os.path.join(SCRIPTS, "verificar_ritmo.py")


def _video_movido(destino, segundos=2):
    """Imagen que cambia en cada cuadro: 0 % de cuadros quietos."""
    subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", f"testsrc=duration={segundos}:size=160x90:rate=10",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", destino],
        check=True, capture_output=True, timeout=120)
    return destino


class TestSalvedadPorConcepto(unittest.TestCase):
    """El flag pone "quietud" y "pausa" en no aplica, sin tocar el resto."""

    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp()
        cls.video = _video_movido(os.path.join(cls.dir, "vivo.mp4"))

    def _correr(self, *args):
        return subprocess.run([sys.executable, VERIFICAR, self.video] + list(args),
                              capture_output=True, text=True, timeout=300)

    def test_sin_el_flag_el_silencio_visual_falla(self):
        """Una pieza que se mueve siempre no tiene cuadros quietos: sin el
        flag, los minimos de silencio visual se cumplen como se cumplen."""
        r = self._correr()
        self.assertIn("quietud", r.stdout)
        self.assertIn("FAIL", r.stdout)
        self.assertIn("pausa", r.stdout)

    def test_con_el_flag_no_aplica_y_no_falla(self):
        r = self._correr("--sobre-footage-vivo")
        self.assertIn("no aplica sobre footage vivo", r.stdout)
        self.assertIn("N/A", r.stdout)
        self.assertNotIn("FAIL", r.stdout)
        self.assertIn("PASS", r.stdout)      # el resultado overall es PASS
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_el_plan_declara_el_hecho_y_manda_en_los_cortes(self):
        """El plan es el documento de la pieza: ahi quedan registrados los
        cortes (los beats que percibe el espectador) y el HECHO de que se
        compone sobre footage vivo. Un flag de CLI no deja constancia."""
        import json
        plan = {
            "duracion": 20.0,
            "sobre_footage_vivo": True,
            "escenas": [
                {"tipo": "apertura", "from": 0.0, "to": 3.0},
                {"tipo": "bento", "from": 3.0, "to": 9.0},
                {"tipo": "final", "from": 9.0, "to": 14.0},
            ],
        }
        ruta = os.path.join(self.dir, "plan.json")
        with open(ruta, "w", encoding="utf-8") as fh:
            json.dump(plan, fh)
        r = subprocess.run([sys.executable, VERIFICAR, self.video, "--plan", ruta],
                           capture_output=True, text=True, timeout=300)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("no aplica sobre footage vivo", r.stdout)
        # la cadencia se mide con los TIEMPOS DE LAS ESCENAS del plan:
        # duraciones 3, 6 y 5 -> CV 0.26 (no se detectan cortes en el video)
        self.assertRegex(r.stdout, r"PASS\s+cadencia\s+CV=0\.\d+")
        self.assertIn("3 tomas", r.stdout)   # 3 escenas -> 3 duraciones

    def test_un_plan_sin_el_hecho_no_exime_nada(self):
        """El campo declara el HECHO: si no esta, los minimos se miden."""
        import json
        plan = {"duracion": 20.0, "escenas": [
            {"tipo": "apertura", "from": 0.0, "to": 3.0},
            {"tipo": "final", "from": 3.0, "to": 9.0}]}
        ruta = os.path.join(self.dir, "plan_sin.json")
        with open(ruta, "w", encoding="utf-8") as fh:
            json.dump(plan, fh)
        r = subprocess.run([sys.executable, VERIFICAR, self.video, "--plan", ruta],
                           capture_output=True, text=True, timeout=300)
        self.assertIn("quietud", r.stdout)
        self.assertNotIn("no aplica sobre footage vivo", r.stdout)

    def test_el_flag_no_toca_la_cadencia_ni_la_rafaga(self):
        """El flag es una salvedad de CONCEPTO para el silencio visual: los
        otros minimos se siguen midiendo."""
        r = self._correr("--sobre-footage-vivo")
        self.assertIn("cadencia", r.stdout)
        self.assertIn("ráfaga", r.stdout)


if __name__ == "__main__":
    unittest.main()
