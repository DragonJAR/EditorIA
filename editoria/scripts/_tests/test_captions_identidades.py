#!/usr/bin/env python3
"""Tests del detalle de captions (elección = repertorio; aquí producción)."""
import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)

import captions_identidades as CAP  # noqa: E402
import repertorio as REP  # noqa: E402


class TestCaptionsIdentidades(unittest.TestCase):
    def test_json_valido_y_conteo(self):
        self.assertEqual(CAP.validar(), [])
        self.assertEqual(len(CAP.identidades()), CAP.cargar()["conteo"])

    def test_modelo_drop_rail_embed(self):
        m = CAP.cargar()["modelo"]
        for k in ("drop", "rail", "embed"):
            self.assertTrue(str(m[k]).strip())

    def test_receta_nativo_y_hf(self):
        nativo = CAP.receta("cap-rail-karaoke", video="x.mp4")
        self.assertIn("caption.py", nativo)
        self.assertIn("x.mp4", nativo)
        hf = CAP.receta("cap-kinetic-slam")
        self.assertIn("hyperframes", hf.lower())
        self.assertIn("caption-kinetic-slam", hf)
        matte = CAP.receta("cap-embed-matte")
        self.assertIn("remove-background", matte)
        self.assertIn("qa_entrega", matte)

    def test_en_catalogo_unico(self):
        self.assertEqual(REP.validar(), [])
        r = REP.resolver("cap-rail-karaoke")
        self.assertEqual(r["motor"], REP.MOTOR_CAPTION)
        counts = REP._resumen_conteos()
        self.assertEqual(counts["n_captions"], len(CAP.identidades()))
        self.assertEqual(
            counts["n_opciones"],
            counts["n_escenas"] + counts["n_efectos"]
            + counts["n_gestos"] + counts["n_captions"],
        )

    def test_cli(self):
        r = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS, "captions_identidades.py"),
             "validar"],
            capture_output=True, text=True,
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("CAPTIONS VALIDO", r.stdout)
        r = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS, "captions_identidades.py"),
             "receta", "--id", "cap-highlight"],
            capture_output=True, text=True,
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("caption-highlight", r.stdout)


if __name__ == "__main__":
    unittest.main()
