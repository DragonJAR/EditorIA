#!/usr/bin/env python3
"""Tests de CLI de las cuatro herramientas que(documentadas) nadie ejecutaba.

La medicion con verdad (instrumentando subprocess durante la suite real, no
leyendo los tests: un nombre en un comentario no ejecuta nada) decia que
estas cuatro CLIs documentadas no las ejecutaba ningun test: solo las
vigilaba la intercepcion de parse_args, que prueba los ARGUMENTOS pero no el
EFECTO.

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
BASE = os.path.dirname(SCRIPTS)


def _video(destino, segundos=2):
    subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", f"testsrc=duration={segundos}:size=320x180:rate=10",
        "-f", "lavfi", "-i", f"sine=frequency=440:duration={segundos}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", destino],
        check=True, capture_output=True, timeout=180)
    return destino


class TestLasCuatroQueFaltaban(unittest.TestCase):
    """Cada una se EJECUTA: la intercepcion de argumentos no basta."""

    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp()
        cls.video = _video(os.path.join(cls.dir, "v.mp4"))

    def _correr(self, script, *args, timeout=300):
        return subprocess.run([sys.executable, os.path.join(SCRIPTS, script)] + list(args),
                              capture_output=True, text=True, timeout=timeout)

    def test_beat_file_escribe_el_beat(self):
        out = os.path.join(self.dir, "beat.json")
        r = self._correr("beat_file.py", "--bpm", "120", "--duracion", "20",
                         "--seccion", "intro:0:8", "-o", out)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        with open(out, encoding="utf-8") as fh:
            datos = json.load(fh)
        self.assertIn("bpm", datos)

    def test_registrar_aprendizaje_dry_run_no_escribe(self):
        """El registro de aprendizajes con --dry-run no toca la skill."""
        antes = os.path.getmtime(os.path.join(BASE, "references", "principios.md"))
        r = self._correr("registrar_aprendizaje.py", "--titulo", "prueba",
                         "--detalle", "prueba", "--destino", "principios", "--dry-run")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        despues = os.path.getmtime(os.path.join(BASE, "references", "principios.md"))
        self.assertEqual(antes, despues, "el dry-run toco la skill")

    def test_speech_estimate_estima_un_texto(self):
        r = self._correr("speech_estimate.py", "Una frase de unas diez palabras para estimar.")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Duración estimada", r.stdout)

    def test_qa_entrega_verifica_una_pieza(self):
        """La puerta, como proceso: devuelve un veredicto (no un traceback)."""
        r = self._correr("qa_entrega.py", self.video, "--sin-medir")
        self.assertIn(r.returncode, (0, 1), r.stdout + r.stderr)
        self.assertNotIn("Traceback", r.stdout + r.stderr)
        self.assertTrue("ENTREGA" in r.stdout or "veredicto" in r.stdout.lower(),
                        r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
