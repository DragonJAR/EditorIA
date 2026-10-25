#!/usr/bin/env python3
"""Tests de compilar_reel.py — la herramienta que junta N videos en un reel.

Lo que se verifica aqui no es el montage (eso lo hace ffmpeg), sino la
INVARIANTE que hace que la pieza no salga desfasada: **el fondo y el plan
tienen que tener la MISMA duracion**. Una disolvencia de 0,25 s se come 0,25 s
del segmento que entra; si el plan y el montage hicieran cada uno su cuenta,
la voz se desfasaria del footage. Este test es la mutacion de esa invariante:
si alguien vuelve a separar las cuentas, el test cae.
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
TOOL = os.path.join(SCRIPTS, "compilar_reel.py")


def _dur(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", path], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return -1.0


class CompilarReel(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="editoria_reel_")
        self.addCleanup(self._limpia)

    def _limpia(self):
        import shutil
        shutil.rmtree(self.dir, ignore_errors=True)

    def _video(self, nombre="a.mp4", segundos=2.0):
        """Un video de mentira: un patron de prueba y un tono, para que la
        medicion tenga algo que medir."""
        ruta = os.path.join(self.dir, nombre)
        subprocess.run(["ffmpeg", "-v", "error", "-y",
                        "-f", "lavfi", "-i",
                        f"testsrc=size=360x640:rate=24:duration={segundos}",
                        "-f", "lavfi", "-i", f"sine=frequency=440:duration={segundos}",
                        "-c:v", "libx264", "-crf", "30", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-shortest", ruta],
                       check=True, timeout=600)
        return ruta

    def test_compila_y_el_fondo_cuadra_con_el_plan(self):
        """La invariante: el fondo y el plan dicen lo mismo."""
        a = self._video("a.mp4")
        b = self._video("b.mp4")
        out = os.path.join(self.dir, "salida")
        r = subprocess.run([sys.executable, TOOL, "-o", out, "--marca", "Marca",
                            "--titulo", "Uno |dos", "--lema", "Tres |cuatro",
                            "--duracion", "1.5", a, b],
                           capture_output=True, text=True, timeout=900)
        self.assertEqual(r.returncode, 0, f"la compilacion fallo:\n{r.stdout}\n{r.stderr}")
        base = os.path.join(out, "base.mp4")
        plan = os.path.join(out, "plan.json")
        self.assertTrue(os.path.exists(base), "no se escribio el fondo")
        self.assertTrue(os.path.exists(plan), "no se escribio el plan")
        with open(plan, encoding="utf-8") as fh:
            doc = json.load(fh)
        self.assertAlmostEqual(_dur(base), doc["duracion"], delta=0.15,
                               msg="el fondo y el plan tienen que durar lo mismo: "
                                   "si no, la voz se desfasa del footage")
        # las escenas del plan no se solapan (la puerta lo prohibe)
        escenas = doc["escenas"]
        for i in range(len(escenas) - 1):
            self.assertLessEqual(escenas[i]["to"], escenas[i + 1]["from"],
                                 f"las escenas se solapan: {escenas[i]} y {escenas[i+1]}")

    def test_avisa_cuando_no_hay_footage_para_las_tarjetas(self):
        """Sin footage para las tarjetas, lo dice: van sobre negro y el auto_qa
        las marcara. Callarse seria dejar un fallo para que otro lo encuentre."""
        a = self._video("a.mp4")
        out = os.path.join(self.dir, "salida2")
        r = subprocess.run([sys.executable, TOOL, "-o", out, "--duracion", "1.0", a],
                           capture_output=True, text=True, timeout=900)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("negro", r.stderr, "tiene que avisar de las tarjetas sobre negro")

    def test_no_toca_los_videos_de_entrada(self):
        """La herramienta edita una COPIA: el original no se toca nunca."""
        a = self._video("a.mp4")
        antes = (os.path.getsize(a), _dur(a))
        out = os.path.join(self.dir, "salida3")
        subprocess.run([sys.executable, TOOL, "-o", out, "--duracion", "1.0", a],
                       capture_output=True, text=True, timeout=900)
        self.assertEqual((os.path.getsize(a), _dur(a)), antes,
                         "el video de entrada no puede cambiar")


if __name__ == "__main__":
    unittest.main()
