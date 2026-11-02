#!/usr/bin/env python3
"""Tests de las herramientas de ffmpeg_tools — las que se ejecutan como scripts.

Por qué existen: `_comun.py` resolvia la fuente con un import RELATIVO
(`from . import _plataforma`). Los scripts de ffmpeg_tools meten su carpeta
en sys.path e importan `_comun` como modulo SUELTO, que es como se ejecutan
desde la linea de comandos: con el import relativo a secas, `default_font_file`
reventaba con "attempted relative import with no known parent package" y
TRES herramientas se caian al usarse tal como las documenta la skill
(look.py, scenes.py y shorts_plan.py).

Y aqui esta lo que lo hacia invisible: el guard de "los comandos documentados
se pueden ejecutar" intercepta `ArgumentParser.parse_args` y sale ANTES de
que el script haga nada. Comprueba que los argumentos valen, no que la
herramienta funcione. Este test ejecuta las herramientas de verdad.

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
TOOLS = os.path.join(SCRIPTS, "ffmpeg_tools")


def _video_sintetico(destino, segundos=2):
    """Un video minimo con imagen y audio (para las herramientas que los usan)."""
    subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", f"testsrc=duration={segundos}:size=320x180:rate=10",
        "-f", "lavfi", "-i", f"sine=frequency=440:duration={segundos}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", destino],
        check=True, capture_output=True, timeout=120)
    return destino


def _video_con_corte(destino):
    """Dos imagenes distintas pegadas: hay un corte duro en 1.5 s (scenes.py
    tiene que encontrarlo y escribir el EDL)."""
    subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", "testsrc=duration=1.5:size=320x180:rate=10",
        "-f", "lavfi", "-i", "color=c=blue:duration=1.5:size=320x180:rate=10",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
        "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]",
        "-map", "[v]", "-map", "2:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", destino],
        check=True, capture_output=True, timeout=120)
    return destino


class TestFuenteEnLosDosContextos(unittest.TestCase):
    """`_comun` se importa de dos maneras y la funcion tiene que servir en las dos."""

    def test_default_font_file_como_modulo_suelto(self):
        # asi lo importan los scripts: sys.path con su carpeta + `from _comun import ...`
        sys.path.insert(0, TOOLS)
        sys.modules.pop("_comun", None)
        try:
            import _comun as comun_suelto
            self.assertTrue(hasattr(comun_suelto, "default_font_file"))
            # no debe lanzar ImportError (el fallo que tumbaba tres herramientas)
            fuente = comun_suelto.default_font_file("sans")
            if fuente:
                self.assertTrue(os.path.exists(fuente),
                                "la fuente resuelta no existe: " + str(fuente))
        finally:
            sys.modules.pop("_comun", None)
            if TOOLS in sys.path:
                sys.path.remove(TOOLS)

    def test_default_font_file_como_paquete(self):
        sys.path.insert(0, SCRIPTS)
        try:
            from ffmpeg_tools import _comun as comun_paquete
            fuente = comun_paquete.default_font_file("sans")
            if fuente:
                self.assertTrue(os.path.exists(fuente))
        finally:
            if SCRIPTS in sys.path:
                sys.path.remove(SCRIPTS)


class TestHerramientasSeEjecutan(unittest.TestCase):
    """Las herramientas que dibujan texto, ejecutadas de verdad (no solo argparse)."""

    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp()
        cls.video = _video_sintetico(os.path.join(cls.dir, "v.mp4"))

    def _correr(self, script, *args):
        return subprocess.run([sys.executable, os.path.join(TOOLS, script)] + list(args),
                              capture_output=True, text=True, timeout=300)

    def test_look_extrae_frames(self):
        salida = os.path.join(self.dir, "sheet.png")
        r = self._correr("look.py", self.video, "--tiles", "2x2", "-o", salida)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(os.path.exists(salida))
        self.assertNotIn("ImportError", r.stdout + r.stderr)

    def test_scenes_detecta_cortes(self):
        video = _video_con_corte(os.path.join(self.dir, "corte.mp4"))
        edl = os.path.join(self.dir, "cortes.txt")
        # el EDL son los rangos HIGHLIGHT (por eso hace falta --highlights)
        r = self._correr("scenes.py", video, "--highlights", "1", "--edl", edl)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(os.path.exists(edl),
                        "no se escribio el EDL:\n" + r.stdout + r.stderr)
        with open(edl, encoding="utf-8") as fh:
            linea = fh.read().strip().splitlines()[0]
        self.assertRegex(linea, r"^\d+\.\d+-\d+\.\d+$",
                         "el EDL deberia ser START-END: " + linea)
        self.assertNotIn("ImportError", r.stdout + r.stderr)

    def test_scenes_sheet_crea_la_carpeta_destino(self):
        # --sheet a una carpeta que no existe: ffmpeg moria con 251 sin
        # decir que el fallo era la ruta, no el video.
        video = _video_con_corte(os.path.join(self.dir, "corte2.mp4"))
        sheet = os.path.join(self.dir, "no", "existe", "cortes.png")
        r = self._correr("scenes.py", video, "--sheet", sheet)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(os.path.exists(sheet))

    def test_shorts_plan_de_punta_a_punta(self):
        plan = {
            "fuente": self.video,
            "salida": os.path.join(self.dir, "short.mp4"),
            "formato": "1080x1920",
            "segmentos": [
                {"id": "hook", "from": 0.2, "to": 1.2, "hook_overlay": "ESTO LO CAMBIA TODO"},
                {"id": "cuerpo", "from": 1.3, "to": 1.9, "titulo": "El dato clave"},
            ],
            "loudness_lufs": -14,
        }
        ruta = os.path.join(self.dir, "shorts-plan.json")
        with open(ruta, "w", encoding="utf-8") as fh:
            json.dump(plan, fh, ensure_ascii=False, indent=1)
        r = self._correr("shorts_plan.py", ruta)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(os.path.exists(plan["salida"]),
                        "el short no se escribio:\n" + r.stdout + r.stderr)
        self.assertNotIn("ImportError", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
