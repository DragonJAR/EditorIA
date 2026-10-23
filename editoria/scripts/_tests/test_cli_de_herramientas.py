#!/usr/bin/env python3
"""Tests de CLI de las herramientas que solo se importaban en los tests.

Por que existen: tener un test que llama a una FUNCION no prueba que la
herramienta funcione. Once de los scripts de la skill tenian tests, pero
ninguno lo ejecutaba como proceso: si reventaba al arrancar (un import
mal puesto, un argumento mal declarado), todos los tests pasaban igual.

Y el guard de "los comandos documentados se pueden ejecutar" tampoco lo
cubre: intercepta ArgumentParser.parse_args y sale ANTES de que el script
haga nada, asi que vigila la invocacion, no el efecto. Por eso hace falta
ejecutar de verdad.

Aqui se ejecutan como proceso, con entradas reales, las que faltaban:
aplicar_edl, audio_viz, auto_qa, beat_sync, caption, grade, loudness,
medir_contraste, sfx y variantes. (galeria.py y validate_skill.py quedan
fuera: la validacion ya los ejecuta, y son de minutos.)

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
ROOT = SCRIPTS
TOOLS = os.path.join(SCRIPTS, "ffmpeg_tools")


def _video(destino, segundos=2, con_audio=True, color="blue"):
    """Video minimo (con o sin audio) para las herramientas."""
    cmd = ["ffmpeg", "-y", "-v", "error",
           "-f", "lavfi", "-i", f"color=c={color}:duration={segundos}:size=320x180:rate=10"]
    if con_audio:
        cmd += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={segundos}"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p"]
    if con_audio:
        cmd += ["-c:a", "aac"]
    cmd += [destino]
    subprocess.run(cmd, check=True, capture_output=True, timeout=120)
    return destino


def _video_movido(destino, segundos=2):
    """Video que cambia en cada cuadro: auto_qa lo marca como CONGELADO si
    no se mueve, asi que para esa prueba hace falta imagen con movimiento."""
    subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", f"testsrc=duration={segundos}:size=320x180:rate=10",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", destino],
        check=True, capture_output=True, timeout=120)
    return destino


class TestCLIReal(unittest.TestCase):
    """Cada herramienta, como proceso, con una entrada de verdad."""

    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp()
        cls.video = _video(os.path.join(cls.dir, "v.mp4"))
        cls.mudo = _video(os.path.join(cls.dir, "mudo.mp4"), con_audio=False, color="red")

    def _correr(self, ruta, *args, timeout=300):
        return subprocess.run([sys.executable, ruta] + list(args),
                              capture_output=True, text=True, timeout=timeout)

    # -- ffmpeg_tools ---------------------------------------------------
    def test_aplicar_edl(self):
        edl = os.path.join(self.dir, "cortes.txt")
        with open(edl, "w", encoding="utf-8") as fh:
            fh.write("0.20-1.20\n")
        out = os.path.join(self.dir, "edl.mp4")
        r = self._correr(os.path.join(TOOLS, "aplicar_edl.py"),
                         self.video, "--edl", edl, "-o", out)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(os.path.exists(out))

    def test_audio_viz(self):
        out = os.path.join(self.dir, "audio_viz.mp4")
        r = self._correr(os.path.join(ROOT, "audio_viz.py"),
                         self.video, "-o", out, "--modo", "waves", "-s", "320x180")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(os.path.exists(out))

    def test_grade(self):
        out = os.path.join(self.dir, "grade.mp4")
        r = self._correr(os.path.join(TOOLS, "grade.py"), self.video, "-o", out)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(os.path.exists(out))

    def test_loudness(self):
        out = os.path.join(self.dir, "loud.mp4")
        r = self._correr(os.path.join(TOOLS, "loudness.py"),
                         self.video, "-o", out, "-I", "-14", "--tp", "-1.5")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(os.path.exists(out))

    def test_variantes(self):
        # un body x 2 hooks -> 2 variantes (hook + cuerpo, con audio)
        hooks = os.path.join(self.dir, "hooks")
        os.makedirs(hooks, exist_ok=True)
        _video(os.path.join(hooks, "h1.mp4"), 1.0, color="red")
        _video(os.path.join(hooks, "h2.mp4"), 1.0, color="green")
        body = _video(os.path.join(self.dir, "cuerpo.mp4"), 2.0, color="blue")
        out = os.path.join(self.dir, "variantes")
        r = self._correr(os.path.join(TOOLS, "variantes.py"),
                         hooks, body, "--proyecto", "prueba", "-o", out)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue([f for f in os.listdir(out) if f.endswith(".mp4")],
                        "no se escribieron variantes:\n" + r.stdout + r.stderr)

    # -- raiz -----------------------------------------------------------
    def test_auto_qa(self):
        # con imagen en movimiento: un color plano lo marca como congelado
        # (y con razon: lo esta).
        movido = _video_movido(os.path.join(self.dir, "mueve.mp4"))
        r = self._correr(os.path.join(ROOT, "auto_qa.py"), movido)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_caption_quema_subtitulos(self):
        out = os.path.join(self.dir, "sub.mp4")
        r = self._correr(os.path.join(TOOLS, "caption.py"),
                         self.video, "--mode", "burn", "--text", "Hola equipo", "-o", out)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(os.path.exists(out))

    def test_beat_sync(self):
        # el grid se genera con beat_grid.py sobre la propia musica
        grid = os.path.join(self.dir, "grid.json")
        r0 = self._correr(os.path.join(ROOT, "beat_grid.py"), self.video, "--json", grid)
        self.assertEqual(r0.returncode, 0, r0.stdout + r0.stderr)
        r = self._correr(os.path.join(ROOT, "beat_sync.py"), grid, "--cortes", "0.5", "1.0")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_medir_contraste(self):
        r = self._correr(os.path.join(ROOT, "medir_contraste.py"))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_sfx_genera_el_pack(self):
        out = os.path.join(self.dir, "sfx")
        r = self._correr(os.path.join(ROOT, "sfx.py"), "-o", out)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue([f for f in os.listdir(out) if f.endswith(".wav")],
                        "el pack de SFX no se genero:\n" + r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
