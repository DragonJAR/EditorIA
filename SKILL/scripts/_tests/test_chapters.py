#!/usr/bin/env python3
"""Tests for chapters.py — the YouTube chapter generator.

Covers the 5 functions documented in chapters.py:
- fmt_tiempo: seconds -> "H:MM:SS" / "MM:SS"
- humanizar: snake_case / kebab-case -> human title
- capitulos_desde_plan: extracts chapters from plan.json
- capitulos_desde_shorts: extracts chapters from shorts-plan.json
- main: CLI (smoke-tested by running with --help)

Run with: python3 SKILL/scripts/_tests/test_chapters.py
Or:       python3 -m unittest SKILL/scripts/_tests/test_chapters.py
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)


class TestFmtTiempo(unittest.TestCase):
    """fmt_tiempo: seconds -> YouTube timestamp string."""

    def test_zero(self):
        self.assertEqual(__import__("chapters").fmt_tiempo(0), "00:00")

    def test_seconds_only(self):
        self.assertEqual(__import__("chapters").fmt_tiempo(45), "00:45")

    def test_minutes_seconds(self):
        self.assertEqual(__import__("chapters").fmt_tiempo(75), "01:15")

    def test_hours(self):
        self.assertEqual(__import__("chapters").fmt_tiempo(3661), "1:01:01")

    def test_negative_clamped_to_zero(self):
        self.assertEqual(__import__("chapters").fmt_tiempo(-5), "00:00")

    def test_rounds_half_seconds(self):
        self.assertEqual(__import__("chapters").fmt_tiempo(0.6), "00:01")


class TestHumanizar(unittest.TestCase):
    """humanizar: snake_case / kebab-case -> human title (capitalize first)."""

    def test_snake_case(self):
        self.assertEqual(__import__("chapters").humanizar("intro_datos_outro"), "Intro datos outro")

    def test_kebab_preserved(self):
        # Comportamiento actual: solo _ se reemplaza; - se preserva.
        self.assertEqual(__import__("chapters").humanizar("video_demo-1"), "Video demo-1")

    def test_strips_whitespace(self):
        self.assertEqual(__import__("chapters").humanizar("  hola  "), "Hola")

    def test_capitalizes(self):
        self.assertEqual(__import__("chapters").humanizar("todo"), "Todo")


class TestCapitulosDesdePlan(unittest.TestCase):
    """capitulos_desde_plan: lee plan.escenas[] -> [(t, titulo), ...]"""

    def test_basic_extraction(self):
        plan = {
            "escenas": [
                {"tipo": "intro", "from": 0, "to": 15},
                {"tipo": "datos", "from": 15, "to": 45},
                {"tipo": "outro", "from": 45, "to": 60},
            ]
        }
        result = __import__("chapters").capitulos_desde_plan(plan)
        self.assertEqual(result, [(0.0, "Intro"), (15.0, "Datos"), (45.0, "Outro")])

    def test_prefers_titulo_over_tipo(self):
        plan = {"escenas": [{"tipo": "intro", "from": 0, "to": 15, "titulo": "Bienvenida"}]}
        result = __import__("chapters").capitulos_desde_plan(plan)
        self.assertEqual(result, [(0.0, "Bienvenida")])

    def test_prefers_capitulo_over_tipo(self):
        plan = {"escenas": [{"tipo": "intro", "from": 0, "to": 15, "capitulo": "Apertura"}]}
        result = __import__("chapters").capitulos_desde_plan(plan)
        self.assertEqual(result, [(0.0, "Apertura")])

    def test_empty_escenas(self):
        self.assertEqual(__import__("chapters").capitulos_desde_plan({"escenas": []}), [])
        self.assertEqual(__import__("chapters").capitulos_desde_plan({}), [])

    def test_invalid_from_falls_back_to_zero(self):
        plan = {"escenas": [{"tipo": "intro", "from": "invalid", "to": 15}]}
        result = __import__("chapters").capitulos_desde_plan(plan)
        self.assertEqual(result, [(0.0, "Intro")])


class TestCapitulosDesdeShorts(unittest.TestCase):
    """capitulos_desde_shorts: tiempos ACUMULATIVOS sobre la salida final."""

    def test_acumulativo(self):
        plan = {
            "segmentos": [
                {"id": "hook", "from": 0, "to": 5},
                {"id": "cuerpo", "from": 0, "to": 5},
                {"id": "cierre", "from": 0, "to": 5},
            ]
        }
        result = __import__("chapters").capitulos_desde_shorts(plan)
        self.assertEqual(result, [(0.0, "Hook"), (5.0, "Cuerpo"), (10.0, "Cierre")])

    def test_titulo_override(self):
        plan = {
            "segmentos": [
                {"id": "hook", "from": 0, "to": 3, "titulo": "El gancho"},
                {"id": "cuerpo", "from": 0, "to": 7},
            ]
        }
        result = __import__("chapters").capitulos_desde_shorts(plan)
        self.assertEqual(result, [(0.0, "El gancho"), (3.0, "Cuerpo")])

    def test_invalid_duracion_falls_back_to_zero(self):
        plan = {
            "segmentos": [
                {"id": "a", "from": "x", "to": "y"},
                {"id": "b", "from": 0, "to": 5},
            ]
        }
        result = __import__("chapters").capitulos_desde_shorts(plan)
        self.assertEqual(len(result), 2)


class TestMainSmoke(unittest.TestCase):
    """main: smoke test del CLI con --help."""

    def test_help_exits_zero(self):
        import subprocess
        result = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS, "chapters.py"), "--help"],
            capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertIn("usage", result.stdout.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
