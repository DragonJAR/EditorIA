#!/usr/bin/env python3
"""Registro clone-on-demand de motores externos (manim / handraw / pintura-cpu)."""
from __future__ import annotations

import os
import subprocess
import sys
import unittest

SCRIPTS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import motores_externos as ME  # noqa: E402
import repertorio as REP  # noqa: E402

SCRIPT = os.path.join(SCRIPTS, "motores_externos.py")
CATALOGO = os.path.join(SCRIPTS, "catalogo_repertorio.py")


class TestMotoresExternos(unittest.TestCase):
    def test_validar_ok(self):
        self.assertEqual(ME.validar(), [])

    def test_tres_motores_en_repertorio(self):
        ids = {t["id"] for t in REP.cargar().get("tecnicas", [])}
        for mid in ("manim", "handraw-estilo", "pintura-cpu"):
            self.assertIn(mid, ids)
            res = REP.resolver(mid)
            self.assertEqual(res["motor"], "tecnica")
            self.assertIn("motores_externos.py receta", res["producir"])
            self.assertIn(f"--id {mid}", res["producir"])
            doc_rel = res["producir"].split("·")[-1].strip()
            self.assertTrue(doc_rel.startswith("references/"))
            doc = os.path.join(os.path.dirname(SCRIPTS), doc_rel)
            with open(doc, encoding="utf-8") as fh:
                cuerpo = fh.read()
            self.assertIn("motores_externos.py receta", cuerpo)

    def test_receta_handraw_cita_yang0(self):
        texto = ME.receta("handraw-estilo")
        self.assertIn("yang0", texto)
        self.assertIn("handraw-style", texto)
        self.assertIn("ATRIBUCIÓN OBLIGATORIA", texto)
        self.assertIn("rm -rf /tmp/handraw-style", texto)

    def test_aliases(self):
        self.assertEqual(ME.resolver("manimce"), "manim")
        self.assertEqual(ME.resolver("handraw"), "handraw-estilo")
        self.assertEqual(ME.resolver("inkpaint"), "pintura-cpu")

    def test_ya_cubierto_y_descartado_documentados(self):
        datos = ME.cargar()
        self.assertGreaterEqual(len(datos.get("ya_cubierto") or []), 4)
        self.assertGreaterEqual(len(datos.get("descartado_a_proposito") or []), 1)

    def test_cli_validar_listar_receta(self):
        """Ejecución real: el censo de CLIs solo cuenta subprocess."""
        r = subprocess.run(
            [sys.executable, SCRIPT, "validar"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("OK", r.stdout)
        r2 = subprocess.run(
            [sys.executable, SCRIPT, "listar"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(r2.returncode, 0, r2.stderr)
        self.assertIn("manim", r2.stdout)
        r3 = subprocess.run(
            [sys.executable, SCRIPT, "receta", "--id", "handraw-estilo"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(r3.returncode, 0, r3.stderr)
        self.assertIn("yang0", r3.stdout)

    def test_cli_catalogo_repertorio_help(self):
        """Smoke del catálogo visual 128 (preexistente en vertical crear/animar)."""
        r = subprocess.run(
            [sys.executable, CATALOGO, "--help"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("usage", r.stdout.lower())


if __name__ == "__main__":
    unittest.main()
