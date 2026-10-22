#!/usr/bin/env python3
"""Tests de mezclar_audio.py — el ensamblado de voz + musica + SFX.

Cubre: la resolucion de cada ancla (escena, absoluta, palabra, beat, pico),
el salto de cues que no se pueden resolver, la densidad con turno y el
contrato de la CLI. El grafo de mezcla se prueba de punta a punta con un
video sintetico.

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
sys.path.insert(0, SCRIPTS)

import mezclar_audio as M  # noqa: E402


def _plan(duracion=20.0, escenas=None, voz=None):
    escenas = escenas if escenas is not None else [
        {"tipo": "apertura", "from": 0.0, "to": 5.0},
        {"tipo": "bento", "from": 5.0, "to": 12.0},
        {"tipo": "final", "from": 12.0, "to": 20.0},
    ]
    if voz is not None:
        escenas[0]["voz"] = voz
    return {"duracion": duracion, "escenas": escenas}


GRID = {"bpm": 120.0, "beat0": 0.5, "picos": [{"t": 1.0}, {"t": 2.5}, {"t": 4.0}]}


class TestAnclas(unittest.TestCase):
    def test_escena(self):
        t, err = M.resolver(_plan(), {"ancla": "escena", "escena": 2, "at": 0.3}, None, None)
        self.assertIsNone(err)
        self.assertAlmostEqual(t, 5.3)

    def test_absoluta(self):
        t, err = M.resolver(_plan(), {"ancla": "absoluta", "t": 12.4}, None, None)
        self.assertIsNone(err)
        self.assertAlmostEqual(t, 12.4)

    def test_beat(self):
        t, err = M.resolver(_plan(), {"ancla": "beat", "beat": 3}, None, GRID)
        self.assertIsNone(err)
        self.assertAlmostEqual(t, 0.5 + 2 * 0.5)

    def test_pico(self):
        t, err = M.resolver(_plan(), {"ancla": "pico", "pico": 2}, None, GRID)
        self.assertIsNone(err)
        self.assertAlmostEqual(t, 2.5)

    def test_palo_sin_rejilla_falla(self):
        t, err = M.resolver(_plan(), {"ancla": "beat", "beat": 3}, None, None)
        self.assertIsNone(t)
        self.assertIn("rejilla", err)

    def test_pico_fuera_de_rango(self):
        t, err = M.resolver(_plan(), {"ancla": "pico", "pico": 99}, None, GRID)
        self.assertIsNone(t)
        self.assertIsNotNone(err)

    def test_escena_fuera_de_rango(self):
        t, err = M.resolver(_plan(), {"ancla": "escena", "escena": 9, "at": 0.1}, None, None)
        self.assertIsNone(t)
        self.assertIn("rango", err)

    def test_ancla_desconocida(self):
        t, err = M.resolver(_plan(), {"ancla": "telepatia"}, None, None)
        self.assertIsNone(t)
        self.assertIn("ancla", err)

    def test_palabra_usa_el_indice_global(self):
        # la voz de la escena 1 son 3 palabras; la palabra 2 cae en la global 2
        plan = _plan(voz="una dos tres")
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump({"palabras": [{"texto": w, "inicio": i * 0.5, "fin": i * 0.5 + 0.4}
                                    for i, w in enumerate(["una", "dos", "tres"])]}, f)
            ruta = f.name
        try:
            t, err = M.resolver(plan, {"ancla": "palabra", "escena": 1, "palabra": 2}, ruta, None)
            self.assertIsNone(err)
            self.assertAlmostEqual(t, 0.5)
        finally:
            os.unlink(ruta)

    def test_indice_de_palabras_por_escena(self):
        plan = _plan(voz="una dos tres")
        idx = M._indice_palabras_por_escena(plan)
        self.assertIn(0, idx)
        self.assertEqual(idx[0][1], 3)


class TestDensidad(unittest.TestCase):
    def test_limites_de_densidad(self):
        self.assertEqual(M.CUES_MIN_MIN, 8)
        self.assertEqual(M.CUES_MIN_MAX, 12)

    def test_sonidos_del_pack(self):
        self.assertIn("click", M.SONIDOS)
        self.assertEqual(len(M.SONIDOS), 8)


class TestCli(unittest.TestCase):
    def _correr(self, args):
        return subprocess.run([sys.executable, os.path.join(SCRIPTS, "mezclar_audio.py")] + args,
                              capture_output=True, text=True, timeout=600)

    def test_plan_inexistente_da_error_claro(self):
        r = self._correr([os.path.join(tempfile.gettempdir(), "no_existe_plan.json"),
                           "--video", os.path.join(tempfile.gettempdir(), "no_existe.mp4"),
                           "-o", os.path.join(tempfile.gettempdir(), "x.mp4")])
        self.assertEqual(r.returncode, 2)
        self.assertNotIn("Traceback", r.stderr)

    def test_help_funciona(self):
        r = self._correr(["--help"])
        self.assertEqual(r.returncode, 0)
        self.assertIn("--voz-palabras", r.stdout)
        self.assertIn("--grid", r.stdout)

    def test_ensamblado_completo(self):
        """video + voz + musica + SFX: el resultado tiene audio y dura lo mismo."""
        with tempfile.TemporaryDirectory() as d:
            video = os.path.join(d, "v.mp4")
            voz = os.path.join(d, "v.wav")
            musica = os.path.join(d, "m.wav")
            sfx = os.path.join(d, "sfx")
            os.makedirs(sfx)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                           "color=c=black:s=320x240:d=2:r=24", "-c:v", "libx264",
                           "-pix_fmt", "yuv420p", video], check=True, timeout=180)
            for nombre in ("click", "ding"):
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                                "sine=frequency=800:duration=0.2", "-c:a", "pcm_s16le",
                                os.path.join(sfx, f"{nombre}.wav")], check=True, timeout=120)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                            "sine=frequency=220:duration=2", "-c:a", "pcm_s16le", voz],
                           check=True, timeout=120)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                            "sine=frequency=330:duration=2", "-c:a", "pcm_s16le", musica],
                           check=True, timeout=120)
            plan = {"duracion": 2.0, "escenas": [{"tipo": "apertura", "from": 0.0, "to": 2.0}],
                    "sfx": [{"escena": 1, "ancla": "escena", "at": 0.2, "sonido": "click"},
                            {"escena": 1, "ancla": "absoluta", "t": 1.0, "sonido": "ding"}]}
            ruta = os.path.join(d, "plan.json")
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump(plan, f)
            out = os.path.join(d, "final.mp4")
            r = self._correr([ruta, "--video", video, "--voz", voz, "--musica", musica,
                               "--pack", sfx, "-o", out])
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertTrue(os.path.exists(out))
            probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                                    "stream=codec_type", "-of", "csv=p=0", out],
                                   capture_output=True, text=True)
            self.assertIn("audio", probe.stdout)


class TestNivelMusica(unittest.TestCase):
    """La música sola va a 0.8 (como `musica.py musiconly`); bajo la voz, a 0.12.

    Sin este matiz una pieza sin voz queda 16 dB demasiado baja: es el mismo
    nivel que la ruta antigua, y las dos rutas tienen que coincidir.
    """

    def _correr(self, args):
        return subprocess.run([sys.executable, os.path.join(SCRIPTS, "mezclar_audio.py")] + args,
                              capture_output=True, text=True, timeout=600)

    def _pico(self, ruta, desde=None, dur=None):
        cmd = ["ffmpeg", "-hide_banner", "-nostats"]
        if desde is not None:
            cmd += ["-ss", str(desde)]
        if dur is not None:
            cmd += ["-t", str(dur)]
        cmd += ["-i", ruta, "-af", "astats=metadata=1:reset=0", "-f", "null", "-"]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        for linea in r.stderr.splitlines():
            if "Peak level dB" in linea:
                return float(linea.split(":")[-1].strip())
        self.fail("astats no devolvio pico para " + ruta)

    def _material(self, d):
        video = os.path.join(d, "v.mp4")
        musica = os.path.join(d, "m.wav")
        voz = os.path.join(d, "voz.wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                        "color=c=black:s=320x240:d=4:r=24", "-c:v", "libx264",
                        "-pix_fmt", "yuv420p", video], check=True, timeout=180)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                        "sine=frequency=330:duration=4", "-c:a", "pcm_s16le", musica],
                       check=True, timeout=120)
        # la voz dura 1 s y arranca en 0: despues hay una ventana solo con musica
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                        "sine=frequency=220:duration=1", "-c:a", "pcm_s16le", voz],
                       check=True, timeout=120)
        plan = {"duracion": 4.0, "escenas": [{"tipo": "apertura", "from": 0.0, "to": 4.0}]}
        ruta = os.path.join(d, "plan.json")
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(plan, f)
        return video, musica, voz, ruta

    def test_musica_sola_coincide_con_musica_py_musiconly(self):
        with tempfile.TemporaryDirectory() as d:
            video, musica, _voz, plan = self._material(d)
            a = os.path.join(d, "a.mp4")
            b = os.path.join(d, "b.mp4")
            r = self._correr([plan, "--video", video, "--musica", musica, "-o", a])
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "musica.py"),
                                "musiconly", "-v", video, "-m", musica, "-o", b],
                               capture_output=True, text=True, timeout=600)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertAlmostEqual(self._pico(a), self._pico(b), delta=0.5)

    def test_bajo_la_voz_la_musica_baja_unos_16_db(self):
        with tempfile.TemporaryDirectory() as d:
            video, musica, voz, plan = self._material(d)
            solo = os.path.join(d, "solo.mp4")
            convoz = os.path.join(d, "convoz.mp4")
            self.assertEqual(self._correr([plan, "--video", video, "--musica", musica,
                                           "-o", solo]).returncode, 0)
            self.assertEqual(self._correr([plan, "--video", video, "--musica", musica,
                                           "--voz", voz, "-o", convoz]).returncode, 0)
            # ventana sin voz (2.0-3.5 s): solo la musica
            ventana = {"desde": 2.0, "dur": 1.5}
            alto = self._pico(solo, **ventana)
            bajo = self._pico(convoz, **ventana)
            self.assertGreater(alto - bajo, 10.0,
                               f"la musica bajo la voz solo cayo {alto - bajo:.1f} dB")

    def test_el_modo_sale_dicho_en_la_salida(self):
        with tempfile.TemporaryDirectory() as d:
            video, musica, voz, plan = self._material(d)
            r = self._correr([plan, "--video", video, "--musica", musica,
                               "-o", os.path.join(d, "a.mp4")])
            self.assertIn("musica sola", r.stdout)
            r = self._correr([plan, "--video", video, "--musica", musica, "--voz", voz,
                               "-o", os.path.join(d, "b.mp4")])
            self.assertIn("musica+voz", r.stdout)


class TestGuion(unittest.TestCase):
    """El guion se genera del plan: escrito a mano, desplaza las anclas."""

    def test_el_texto_hablado_no_tiene_tags_ni_asteriscos(self):
        import voz_off as V
        self.assertEqual(V.texto_hablado("Hola [slowly] mundo"), "Hola mundo")
        self.assertEqual(V.texto_hablado("Mira *antes* esto"), "Mira antes esto")
        self.assertEqual(V.texto_hablado("[calm] Bien. [long pause] Listo."),
                         "Bien. Listo.")

    def test_el_guion_sale_del_plan_sin_necesitar_la_api(self):
        """Sin key de TTS el guion se escribe igual: no depende de la API."""
        import voz_off as V
        with tempfile.TemporaryDirectory() as d:
            plan = {"duracion": 6.0, "tamano": "1080x1920", "escenas": [
                {"tipo": "apertura", "from": 0.0, "to": 3.0, "voz": "Hola [slowly] mundo"},
                {"tipo": "bento", "from": 3.0, "to": 6.0, "voz": "Mira *antes* esto"}]}
            ruta = os.path.join(d, "plan.json")
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump(plan, f)
            guion = os.path.join(d, "guion.txt")
            clave = os.environ.pop("ELEVENLABS_API_KEY", None)
            try:
                r = subprocess.run(
                    [sys.executable, os.path.join(SCRIPTS, "voz_off.py"), ruta,
                     "-o", os.path.join(d, "voz.mp3"), "--guion", guion],
                    capture_output=True, text=True, timeout=300)
            finally:
                if clave is not None:
                    os.environ["ELEVENLABS_API_KEY"] = clave
            self.assertTrue(os.path.exists(guion),
                            f"el guion debe escribirse antes del TTS:\n{r.stdout}\n{r.stderr}")
            with open(guion, encoding="utf-8") as f:
                texto = f.read()
            self.assertIn("Hola mundo", texto)
            self.assertIn("Mira antes esto", texto)
            self.assertNotIn("[", texto)
            self.assertNotIn("*", texto)


if __name__ == "__main__":
    unittest.main()
