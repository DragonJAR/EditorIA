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
BASE = os.path.dirname(SCRIPTS)


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
        # El exit code dice el veredicto: con hallazgos no puede salir 0
        # (un agente que encadena comandos ramifica por el codigo).
        if "textos con contraste por debajo" in r.stdout:
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        else:
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_delivery_check_cumple_el_spec(self):
        """La comprobacion de entrega, con un video real: si el archivo no
        cumple el spec de la plataforma, tiene que decirlo (y si lo cumple,
        pasar)."""
        out = os.path.join(self.dir, "entrega.mp4")
        # el spec incluye la sonoridad: el video se normaliza a -14 LUFS
        # vertical (9:16) a 1080 de alto y normalizado a -14 LUFS: lo que pide reels
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", self.video,
                        "-vf", "scale=1080:1920", "-af", "loudnorm=I=-14:TP=-1.5",
                        "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-b:a", "192k", out],
                       check=True, capture_output=True, timeout=180)
        r = self._correr(os.path.join(TOOLS, "delivery_check.py"), out, "--platform", "reels")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("OK", r.stdout)

    def test_delivery_check_rechaza_lo_que_no_cumple(self):
        """Un video sin el tamano de la plataforma no puede pasar."""
        out = os.path.join(self.dir, "chico.mp4")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", self.video,
                        "-vf", "scale=160:90", "-c:v", "libx264", "-crf", "20",
                        "-pix_fmt", "yuv420p", out],
                       check=True, capture_output=True, timeout=180)
        r = self._correr(os.path.join(TOOLS, "delivery_check.py"), out, "--platform", "reels")
        self.assertNotEqual(r.returncode, 0, "un video de 160x90 no cumple el spec de reels")

    def test_film_marca_v2_renderiza(self):
        """El film de marca v2 (el que la skill recomienda) renderiza de verdad:
        15 s de coreografia del isotipo."""
        out = os.path.join(self.dir, "film.mp4")
        r = self._correr(os.path.join(SCRIPTS, "film_marca_v2.py"), "-o", out,
                         "--brand", os.path.join(BASE, "brand", "dragonjar.json"),
                         "--formato", "16:9", timeout=600)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(os.path.exists(out))
        self.assertGreater(os.path.getsize(out), 10000)

    def test_sfx_genera_el_pack(self):
        out = os.path.join(self.dir, "sfx")
        r = self._correr(os.path.join(ROOT, "sfx.py"), "-o", out)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue([f for f in os.listdir(out) if f.endswith(".wav")],
                        "el pack de SFX no se genero:\n" + r.stdout + r.stderr)


class TestAlinearDiagnostico(unittest.TestCase):
    """faster-whisper instalado pero incompatible con PyAV no es «no hay motor»."""

    def test_el_fallo_metadata_errors_se_diagnostica(self):
        sys.path.insert(0, SCRIPTS)
        import alinear
        diag = alinear.diagnostico_faster_whisper(
            TypeError("open() got an unexpected keyword argument 'metadata_errors'"))
        self.assertIn("PyAV", diag)
        self.assertIn("av==12.3.0", diag)

    def test_leer_palabras_acepta_el_formato_corto(self):
        sys.path.insert(0, TOOLS)
        from _comun import leer_palabras
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump([{"w": "hola", "start": 0.0, "end": 0.4}], fh)
            ruta = fh.name
        try:
            palabras = leer_palabras(ruta)
            self.assertEqual(palabras[0]["texto"], "hola")
        finally:
            os.unlink(ruta)


class TestMusicaSinAPI(unittest.TestCase):
    """Sin ELEVENLABS_API_KEY hay cama procedural, no silencio."""

    def test_cama_genera_audio(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "cama.wav")
            r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "musica.py"),
                                "cama", "-o", out, "--dur", "2"],
                               capture_output=True, text=True, timeout=120)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertGreater(os.path.getsize(out), 10000)

    def test_gen_sin_clave_apunta_a_la_cama(self):
        env = {k: v for k, v in os.environ.items() if k != "ELEVENLABS_API_KEY"}
        r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "musica.py"),
                            "gen", "-o", "x.mp3", "--prompt", "test", "--dur", "5"],
                           capture_output=True, text=True, timeout=120, env=env)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("cama", (r.stdout + r.stderr).lower())


class TestCarpetaDestinoYValidacion(unittest.TestCase):
    """F3 en el resto del kit: una salida en carpeta inexistente se crea,
    no revienta con FileNotFoundError tras el trabajo; y un --bpm imposible
    se rechaza antes de dividir por el (o de no terminar nunca)."""

    def _correr(self, *args, timeout=120):
        return subprocess.run([sys.executable] + list(args),
                              capture_output=True, text=True, timeout=timeout)

    def test_beat_file_crea_la_carpeta(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "nueva", "beats.json")
            r = self._correr(os.path.join(SCRIPTS, "beat_file.py"),
                             "--bpm", "120", "--duracion", "4", "-o", out)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertTrue(os.path.isfile(out))

    def test_beat_file_bpm_cero_no_revienta_ni_cuelga(self):
        with tempfile.TemporaryDirectory() as d:
            r = self._correr(os.path.join(SCRIPTS, "beat_file.py"),
                             "--bpm", "0", "--duracion", "4",
                             "-o", os.path.join(d, "b.json"), timeout=30)
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertIn("--bpm", r.stderr)

    def test_chapters_crea_la_carpeta_y_plan_malo_sin_traceback(self):
        with tempfile.TemporaryDirectory() as d:
            plan = {"escenas": [{"tipo": "hero", "titulo": "Uno", "from": 0},
                                  {"tipo": "bento", "titulo": "Dos", "from": 15},
                                  {"tipo": "final", "titulo": "Tres", "from": 30}]}
            ruta = os.path.join(d, "plan.json")
            with open(ruta, "w", encoding="utf-8") as fh:
                json.dump(plan, fh)
            out = os.path.join(d, "nueva", "caps.txt")
            r = self._correr(os.path.join(SCRIPTS, "chapters.py"), ruta, "-o", out)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertTrue(os.path.isfile(out))
            malo = os.path.join(d, "mal.json")
            with open(malo, "w", encoding="utf-8") as fh:
                fh.write("no es json")
            r = self._correr(os.path.join(SCRIPTS, "chapters.py"), malo)
            self.assertNotEqual(r.returncode, 0)
            self.assertNotIn("Traceback", r.stdout + r.stderr)

    def test_silence_crea_la_carpeta_del_edl(self):
        with tempfile.TemporaryDirectory() as d:
            video = _video(os.path.join(d, "v.mp4"))
            out = os.path.join(d, "nueva", "s.txt")
            r = self._correr(os.path.join(TOOLS, "silence.py"), video, "--edl", out)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertTrue(os.path.isfile(out))


if __name__ == "__main__":
    unittest.main()
