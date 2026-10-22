#!/usr/bin/env python3
"""Tests for the reference-reading toolkit (references/referencia-video.md).

Covers: _comun.leer_palabras (alinear.py, flat list and WhisperX formats),
contact_sheet.py (phrase search, words per tile, sampling, an end-to-end
word-labeled sheet with pagination), referencia.py's downloader (yt-dlp
selector, clear errors), proyecto.py (scaffold never overwrites) and
montaje.py dividir.

Run with: python3 -m unittest discover -s SKILL/scripts/_tests
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
TOOLS = os.path.join(SCRIPTS, "ffmpeg_tools")
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, TOOLS)

import contact_sheet as cs  # noqa: E402
import referencia  # noqa: E402
from _comun import leer_palabras  # noqa: E402


def _json(d, nombre, data):
    p = os.path.join(d, nombre)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False)
    return p


def _video(d, nombre="v.mp4", dur=2, tam="320x240"):
    p = os.path.join(d, nombre)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=s={tam}:d={dur}:r=10",
                    "-f", "lavfi", "-i", f"sine=d={dur}", "-shortest", "-pix_fmt", "yuv420p", p], check=True)
    return p


class TestLeerPalabras(unittest.TestCase):
    def test_formatos(self):
        with tempfile.TemporaryDirectory() as d:
            a = leer_palabras(_json(d, "a.json", {"palabras": [{"texto": "hola", "inicio": 0.1, "fin": 0.4}]}))
            b = leer_palabras(_json(d, "b.json", [{"word": "hi", "start": 1, "end": 1.2}]))
            c = leer_palabras(_json(d, "c.json", {"segments": [
                {"speaker": "SPEAKER_01", "words": [{"word": "yo", "start": 2, "end": 2.3}]}]}))
        self.assertEqual(a[0]["texto"], "hola")
        self.assertIsNone(a[0]["hablante"])
        self.assertEqual(b[0]["inicio"], 1.0)
        self.assertEqual(c[0]["hablante"], "SPEAKER_01")

    def test_vacio_es_error_claro(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(SystemExit):
                leer_palabras(_json(d, "x.json", {"palabras": []}))


class TestContactSheet(unittest.TestCase):
    PAL = [{"texto": w, "inicio": i * 0.3, "fin": i * 0.3 + 0.25, "hablante": None}
           for i, w in enumerate("hoy vamos a ver Cuatro cosas, que cambian todo y cuatro cosas más".split())]

    def test_buscar_frase(self):
        a, b = cs.buscar_frase(self.PAL, "cuatro COSAS")
        self.assertAlmostEqual(a, 4 * 0.3)
        self.assertAlmostEqual(b, 5 * 0.3 + 0.25)
        a2, _ = cs.buscar_frase(self.PAL, "cuatro cosas", ocurrencia=2)
        self.assertGreater(a2, a)
        with self.assertRaises(SystemExit):
            cs.buscar_frase(self.PAL, "cuatro cosas", ocurrencia=3)

    def test_palabras_en(self):
        self.assertEqual(cs.palabras_en(self.PAL, 0.0, 0.6), "hoy vamos")

    def test_tiempos(self):
        a = SimpleNamespace(en=None, cada=0.5, n=20)
        self.assertEqual(cs.tiempos_pedidos(a, 1.0, 3.0), [1.0, 1.5, 2.0, 2.5])
        a = SimpleNamespace(en="0.5, 0:01.5", cada=None, n=20)
        self.assertEqual(cs.tiempos_pedidos(a, 0, 9), [0.5, 1.5])

    def test_mosaico_con_palabras_y_paginas(self):
        with tempfile.TemporaryDirectory() as d:
            v = _video(d)
            pal = _json(d, "v.palabras.json", {"palabras": self.PAL})
            r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "contact_sheet.py"), "--video", v,
                                "--cada", "0.25", "--palabras", pal, "--cols", "2", "--filas", "2",
                                "--ancho", "160", "-o", os.path.join(d, "ev", "s.png")],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(sorted(os.listdir(os.path.join(d, "ev"))), ["s_01.png", "s_02.png"])
            r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "contact_sheet.py"), "--video", v,
                                "--inicio", "0.5", "--fin", "1.0", "--todos-los-frames",
                                "-o", os.path.join(d, "todos.png")], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("6 tiles", r.stdout)     # 0.5..1.0 a 10 fps, extremos incluidos


class TestDescargar(unittest.TestCase):
    def test_selector_prefiere_h264(self):
        f = referencia.formato_ytdlp(1080)
        self.assertTrue(f.startswith("bv*[vcodec^=avc1][height<=1080]"))
        self.assertTrue(f.endswith("/b"))          # siempre hay respaldo

    def test_errores_claros(self):
        r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "referencia.py"), "--url", "local.mp4"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        self.assertIn("no es un enlace", r.stderr)
        self.assertNotIn("Traceback", r.stderr)


class TestProyecto(unittest.TestCase):
    def test_no_sobrescribe(self):
        with tempfile.TemporaryDirectory() as d:
            raiz = os.path.join(d, "proj")
            cmd = [sys.executable, os.path.join(SCRIPTS, "proyecto.py"), raiz,
                   "--referencia", "https://example.com/v/1"]
            self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 0)
            brief = os.path.join(raiz, "BRIEF.md")
            with open(brief, "w", encoding="utf-8") as fh:
                fh.write("pedido real")
            r = subprocess.run(cmd, capture_output=True, text=True)
            self.assertIn("0 archivo(s) nuevo(s)", r.stdout)
            with open(brief, encoding="utf-8") as fh:
                self.assertEqual(fh.read(), "pedido real")
            self.assertTrue(os.path.isfile(os.path.join(raiz, "referencias", "example-com-v-1", "TIMELINE.md")))
            self.assertIn("clonar_video.py analizar --url", r.stdout)
            self.assertFalse(os.path.exists(os.path.join(raiz, "referencias", "example-com-v-1", "ANALYSIS.md")))


class TestDividir(unittest.TestCase):
    def test_arriba_abajo(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = _video(d, "a.mp4"), _video(d, "b.mp4", tam="640x360")
            out = os.path.join(d, "div.mp4")
            r = subprocess.run([sys.executable, os.path.join(TOOLS, "montaje.py"), "dividir", a, b,
                                "--tamano", "360x640", "-o", out], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            p = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                "stream=width,height", "-of", "csv=p=0", out], capture_output=True, text=True)
            self.assertEqual(p.stdout.strip(), "360,640")


class TestVariarVoz(unittest.TestCase):
    """La voz de la variante tiene que caber en su escena.

    La auditoria mide contra `to - from - AIRE_VOZ` (la voz entra en
    from+0.4 s). Antes `variar` comparaba contra la duracion completa y
    recortaba solo si el texto tenia ":": las variantes nacian con la voz
    desbordada y el plan no pasaba la puerta.
    """

    def test_una_voz_larga_se_recorta_hasta_que_cabe(self):
        import clonar_video as CV
        import speech_estimate as SE
        texto = "Ciberseguridad para bancos punto clave uno"
        util = 2.0 - SE.AIRE_VOZ
        ajuste = CV._ajustar_voz(texto, 2.0)
        self.assertLessEqual(SE.estimar_duracion(ajuste, "es"), util)
        self.assertTrue(ajuste.startswith("Ciberseguridad"))

    def test_una_voz_corta_no_se_toca(self):
        import clonar_video as CV
        self.assertEqual(CV._ajustar_voz("Hola", 5.0), "Hola")

    def test_una_voz_que_no_cabe_ni_una_palabra_queda_vacia(self):
        import clonar_video as CV
        self.assertEqual(CV._ajustar_voz("Ciberseguridad", 0.3), "")


if __name__ == "__main__":
    unittest.main()
