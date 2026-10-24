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


class TestAnalizar(unittest.TestCase):
    """El análisis: los momentos del video se MEDIDEN, no se suponen.

    Antes, el rol de cada tramo salía de su POSICIÓN (el primero es gancho,
    el segundo-to-ultimo cierre) y el ANALYSIS.md afirmaba cosas que nadie
    había medido ("Impacto en primeros 2s"). Ahora el valor de cada tramo
    viene medido (`scripts/ffmpeg_tools/scenes.py`) y el informe dice lo que
    se midió, no lo que se supone.

    La MUTACIÓN: si alguien vuelve a la suposición por posición, este test
    falla, porque desaparecen el pico, el RMS y la nota medida.
    """

    def _video_con_pico(self, ruta):
        """6 s en silencio con un tramo fuerte a los 1-2 s."""
        r = subprocess.run(
            ["ffmpeg", "-v", "error", "-y",
             "-f", "lavfi", "-i", "color=c=navy:s=320x180:d=6",
             "-f", "lavfi", "-i", "sine=frequency=440:duration=6",
             "-filter_complex",
             "[1:a]volume='if(between(t,1,2),1,0.05)':eval=frame[a]",
             "-map", "0:v", "-map", "[a]",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
             "-shortest", ruta],
            capture_output=True, text=True, timeout=180)
        self.assertEqual(r.returncode, 0, f"no se pudo crear el video de prueba: {r.stderr}")
        return ruta

    def test_los_momentos_llevan_el_valor_medido(self):
        with tempfile.TemporaryDirectory() as d:
            video = self._video_con_pico(os.path.join(d, "ref.mp4"))
            out = os.path.join(d, "clon")
            r = subprocess.run(
                [sys.executable, CLONAR, "analizar", "--video", video, "--out", out],
                capture_output=True, text=True, timeout=600)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            with open(os.path.join(out, "plantilla.json"), encoding="utf-8") as fh:
                plantilla = json.load(fh)
            self.assertIn("scenes.py", plantilla["medicion"]["fuente"],
                          "la plantilla tiene que decir de dónde sale la medición")
            segs = plantilla["segmentos"]
            self.assertTrue(segs, "la plantilla tiene que traer segmentos")
            for s in segs:
                self.assertIn("audio_rms", s, "cada tramo lleva su valor medido")
                self.assertIn("nota", s, "cada tramo lleva la nota de lo medido")
            con_pico = [s for s in segs if s.get("pico") is not None]
            self.assertTrue(con_pico, "el video tiene un pico de audio: hay que medirlo")
            self.assertAlmostEqual(con_pico[0]["pico"], 1.5, delta=0.6,
                                   msg=f"el pico medido no cae en el tramo fuerte: {con_pico[0]}")

    def test_el_informe_no_afirma_lo_que_no_medio(self):
        """La MUTACIÓN del informe: si vuelve la nota fija, el test cae."""
        with tempfile.TemporaryDirectory() as d:
            video = self._video_con_pico(os.path.join(d, "ref.mp4"))
            out = os.path.join(d, "clon")
            r = subprocess.run(
                [sys.executable, CLONAR, "analizar", "--video", video, "--out", out],
                capture_output=True, text=True, timeout=600)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            with open(os.path.join(out, "ANALYSIS.md"), encoding="utf-8") as fh:
                informe = fh.read()
            self.assertIn("Valor medido", informe,
                          "el informe tiene que decir que el valor está medido")
            for mentira in ("Impacto en primeros 2s", "Llamado a la acción claro",
                            "Notas de Retención"):
                self.assertNotIn(mentira, informe,
                                 f"el informe afirma lo que no midió: {mentira}")


if __name__ == "__main__":
    unittest.main()
