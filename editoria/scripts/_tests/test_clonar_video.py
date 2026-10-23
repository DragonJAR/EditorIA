#!/usr/bin/env python3
"""Tests de clonar_video.py — el motor de clonación y variación.

Por qué existen: `variar` acepta la abreviatura `--plan` por `--plantilla`
(argparse lo permite), así que pasarle un plan.json donde espera la
plantilla generaba variantes de 0 escenas y lo decía como "OK Variante 1:
0 escenas": honesto en los números, mentiroso en la palabra. Una variante
sin escenas no es una variante, y el plan que sale revienta al
renderizarlo (IndexError en el motor).

Run with: python3 -m unittest discover -s SKILL/scripts/_tests
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
CLONAR = os.path.join(SCRIPTS, "clonar_video.py")


class TestVariar(unittest.TestCase):
    """El motor de variación: una plantilla sin estructura no produce
    variantes, y lo dice."""

    def _correr(self, plantilla, out_dir):
        return subprocess.run(
            [sys.executable, CLONAR, "variar", "--plantilla", plantilla,
             "--variantes", "1", "--out", out_dir],
            capture_output=True, text=True, timeout=300)

    def test_una_plantilla_sin_segmentos_falla_con_mensaje(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "plantilla.json")
            with open(ruta, "w", encoding="utf-8") as fh:
                json.dump({"duracion_referencia": 20.0, "segmentos": []}, fh)
            r = self._correr(ruta, os.path.join(d, "variantes"))
            self.assertNotEqual(r.returncode, 0, r.stdout)
            salida = r.stdout + r.stderr
            self.assertIn("segmentos", salida)
            self.assertNotIn("OK Variante", salida,
                             "no se puede vender como OK una variante de 0 escenas")

    def test_un_plan_json_no_pasa_como_plantilla(self):
        """El camino que se puede pisar sin querer: un plan.json donde se
        espera la plantilla."""
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "plan.json")
            with open(ruta, "w", encoding="utf-8") as fh:
                json.dump({"duracion": 20.0, "escenas": [
                    {"tipo": "titular", "from": 0.0, "to": 5.0, "titulo": "Hola"}]}, fh)
            r = self._correr(ruta, os.path.join(d, "variantes"))
            self.assertNotEqual(r.returncode, 0, r.stdout)
            self.assertIn("plantilla", (r.stdout + r.stderr).lower())


if __name__ == "__main__":
    unittest.main()
