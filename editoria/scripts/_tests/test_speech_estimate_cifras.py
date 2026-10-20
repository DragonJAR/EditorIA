#!/usr/bin/env python3
"""Tests for speech_estimate.py additions — numbers as spoken, calibration.

Covers: number expansion (es/en, thousands vs decimals, %, currency),
Spanish/English syllable counting through spoken text, language detection,
rate calibration from a measured palabras.json, and auditar_plan.py using
speech_estimate as its single source (core syllable tests live in
test_core_and_scenes.py).

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

import speech_estimate as ev  # noqa: E402


class TestNumeros(unittest.TestCase):
    def test_es_basicos(self):
        self.assertEqual(ev.numero_a_palabras(21, "es"), "veintiuno")
        self.assertEqual(ev.numero_a_palabras(100, "es"), "cien")
        self.assertEqual(ev.numero_a_palabras(101, "es"), "ciento uno")
        self.assertEqual(ev.numero_a_palabras(2024, "es"), "dos mil veinticuatro")
        self.assertEqual(ev.numero_a_palabras(1000000, "es"), "un millón")
        self.assertEqual(ev.numero_a_palabras(3000000, "es"), "tres millones")

    def test_en_basicos(self):
        self.assertEqual(ev.numero_a_palabras(21, "en"), "twenty one")
        self.assertEqual(ev.numero_a_palabras(1240, "en"), "one thousand two hundred forty")

    def test_miles_y_decimales(self):
        self.assertIn("ciento cuarenta y dos mil", ev.texto_hablado("$142.332", "es"))
        self.assertIn("dólares", ev.texto_hablado("$142.332", "es"))
        self.assertIn("cuatro coma ocho", ev.texto_hablado("4,8", "es"))
        self.assertIn("mil doscientos cuarenta coma cinco", ev.texto_hablado("1.240,5", "es"))
        self.assertIn("three point five", ev.texto_hablado("3.5", "en"))
        self.assertIn("por ciento", ev.texto_hablado("12%", "es"))

    def test_audio_tags_fuera(self):
        self.assertEqual(ev.silabas("[excited] hola", "es"), ev.silabas("hola", "es"))


class TestSilabas(unittest.TestCase):
    def test_es(self):
        casos = {"que": 1, "guerra": 2, "hoy": 1, "país": 2, "ciudad": 2, "aéreo": 4,
                 "pingüino": 3, "construir": 2, "desafortunadamente": 8, "creas": 2}
        for w, n in casos.items():
            self.assertEqual(ev.silabas(w, "es"), n, w)

    def test_en(self):
        self.assertLess(ev.silabas("the cat", "en"), ev.silabas("unbelievable", "en"))

    def test_sigla_sin_vocales_se_deletrea(self):
        self.assertGreater(ev.silabas("SQL", "es"), ev.silabas("sol", "es"))

    def test_cifra_dura_mas_que_su_palabra(self):
        # "$142.332" es una palabra escrita y ocho dichas
        self.assertGreater(ev.estimar_duracion("$142.332", "es"), ev.estimar_duracion("ventas", "es") + 2.0)

    def test_ritmos_ordenados(self):
        t = "La inteligencia artificial edita mientras tú creas."
        self.assertGreater(ev.estimar_duracion(t, "es", "slow"), ev.estimar_duracion(t, "es", "normal"))
        self.assertGreater(ev.estimar_duracion(t, "es", "normal"), ev.estimar_duracion(t, "es", "fast"))

    def test_tasa_calibrada_manda(self):
        t = "hola mundo"
        self.assertGreater(ev.estimar_duracion(t, "es", tasa=2.0), ev.estimar_duracion(t, "es"))


class TestIdiomaYCalibracion(unittest.TestCase):
    def test_detectar(self):
        self.assertEqual(ev.detectar_idioma("Editar video te toma horas, ahora es automático"), "es")
        self.assertEqual(ev.detectar_idioma("Video editing begins with the meaning of your story"), "en")

    def test_calibrar_con_voz_medida(self):
        palabras = [{"texto": w, "inicio": i * 0.5, "fin": i * 0.5 + 0.4}
                    for i, w in enumerate("hola mundo esto es una prueba".split())]
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "voz.palabras.json")
            with open(p, "w") as fh:
                json.dump({"palabras": palabras}, fh)
            sps, idioma = ev.calibrar(p, "es")
        # 11 sílabas entre 0.0 y 2.9 s
        self.assertEqual(idioma, "es")
        self.assertAlmostEqual(sps, 11 / 2.9, places=3)


class TestAuditarPlan(unittest.TestCase):
    def _auditar(self, plan):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "plan.json")
            with open(p, "w", encoding="utf-8") as fh:
                json.dump(plan, fh, ensure_ascii=False)
            return subprocess.run([sys.executable, os.path.join(SCRIPTS, "auditar_plan.py"), p, "--json"],
                                  capture_output=True, text=True)

    def test_cifra_larga_no_cabe(self):
        # 3 palabras escritas, ~25 sílabas dichas: con palabras cabía, con sílabas no
        r = self._auditar({"idioma": "es", "duracion": 4, "escenas": [
            {"tipo": "quote", "from": 0, "to": 2, "texto": "x", "voz": "Ventas: $142.332 (+12%)"},
            {"tipo": "quote", "from": 2, "to": 4, "texto": "y", "voz": "fin"}]})
        doc = json.loads(r.stdout)
        self.assertEqual(r.returncode, 1)
        self.assertTrue(any("pisaría" in h["msg"] and "sílabas" in h["msg"] for h in doc["hallazgos"]))

    def test_voz_corta_cabe(self):
        r = self._auditar({"idioma": "es", "duracion": 6, "escenas": [
            {"tipo": "quote", "from": 0, "to": 3, "texto": "x", "voz": "Hola, bienvenidos."},
            {"tipo": "quote", "from": 3, "to": 6, "texto": "y", "voz": "Gracias."}]})
        self.assertEqual(r.returncode, 0, r.stdout)


if __name__ == "__main__":
    unittest.main()
