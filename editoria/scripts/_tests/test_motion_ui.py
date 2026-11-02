#!/usr/bin/env python3
"""Tests del detalle Motion UI (Zajno) dentro del catálogo único.

QUE PROTEGE

1. Las ocho técnicas viven en `scripts/data/motion_ui.json` y en
   `references/motion-ui.md` (detalle); cada una nombra motor de producción.
2. La elección es `repertorio.py` (no un menú paralelo); SKILL/mapa/
   animacion enlazan el detalle y el catálogo único.

Run with: python3 -m unittest discover -s scripts/_tests
"""

import json
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
BASE = os.path.dirname(SCRIPTS)
REF = os.path.join(BASE, "references", "motion-ui.md")
DATOS = os.path.join(SCRIPTS, "data", "motion_ui.json")

sys.path.insert(0, SCRIPTS)
import repertorio as REP  # noqa: E402

TECNICAS = (
    "Easing",
    "Offset",
    "Fade",
    "Transform",
    "Masking",
    "Dimension",
    "Parallax",
    "Zoom",
)
IDS = (
    "easing", "offset-delay", "fade", "morph",
    "masking", "dimension", "parallax", "zoom",
)


class TestMotionUi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(REF, encoding="utf-8") as fh:
            cls.txt = fh.read()
        with open(DATOS, encoding="utf-8") as fh:
            cls.datos = json.load(fh)

    def test_no_es_catalogo_paralelo(self):
        self.assertIn("No es un catálogo paralelo", self.txt)
        self.assertIn("repertorio.py", self.txt)

    def test_las_ocho_tecnicas_estan(self):
        for t in TECNICAS:
            self.assertTrue(
                re.search(re.escape(t), self.txt, re.I),
                f"motion-ui.md tiene que nombrar la técnica '{t}'",
            )
        ids = [t["id"] for t in self.datos["tecnicas"]]
        self.assertEqual(sorted(ids), sorted(IDS))
        self.assertEqual(self.datos["conteo"], 8)

    def test_fuente_declarada(self):
        self.assertIn("motion.zajno.com", self.txt)

    def test_mapea_a_motores_de_la_skill(self):
        for motor in ("Plan", "HyperFrames", "Remotion"):
            self.assertTrue(
                re.search(motor, self.txt, re.I),
                f"cada técnica tiene que poder aterrizar en un motor "
                f"(falta mencionar '{motor}')",
            )

    def test_en_catalogo_unico_repertorio(self):
        malos = REP.validar()
        self.assertEqual(malos, [], malos)
        for gid in IDS:
            r = REP.resolver(gid)
            self.assertIsNotNone(r, gid)
            self.assertEqual(r["motor"], REP.MOTOR_GESTO)

    def test_entrada_desde_skill_y_selector(self):
        with open(os.path.join(BASE, "SKILL.md"), encoding="utf-8") as fh:
            skill = fh.read()
        self.assertIn("motion-ui.md", skill)
        self.assertIn("repertorio.py", skill)
        with open(os.path.join(BASE, "references", "animacion.md"),
                  encoding="utf-8") as fh:
            anim = fh.read()
        self.assertIn("motion-ui.md", anim)
        self.assertIn("repertorio.py", anim)
        with open(os.path.join(BASE, "references", "mapa.md"),
                  encoding="utf-8") as fh:
            mapa = fh.read()
        self.assertIn("motion-ui.md", mapa)
        self.assertIn("repertorio.py", mapa)


if __name__ == "__main__":
    unittest.main()
