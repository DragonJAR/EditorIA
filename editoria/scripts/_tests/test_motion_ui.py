#!/usr/bin/env python3
"""Tests del repertorio Motion UI (Zajno destilado).

QUE PROTEGE

1. Las ocho técnicas viven en `references/motion-ui.md` y cada una nombra
   un motor de la skill: si la fila se pierde, el agente no tiene ruta.
2. La entrada desde SKILL.md / mapa / animacion.md §0 existe: sin ella el
   documento es una isla (auditar_mapa ya mira alcanzabilidad; aquí se
   fija el contrato de contenido).

Run with: python3 -m unittest discover -s scripts/_tests
"""

import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
BASE = os.path.dirname(SCRIPTS)
REF = os.path.join(BASE, "references", "motion-ui.md")

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


class TestMotionUi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(REF, encoding="utf-8") as fh:
            cls.txt = fh.read()

    def test_las_ocho_tecnicas_estan(self):
        for t in TECNICAS:
            self.assertTrue(
                re.search(re.escape(t), self.txt, re.I),
                f"motion-ui.md tiene que nombrar la técnica '{t}'",
            )

    def test_fuente_declarada(self):
        self.assertIn("motion.zajno.com", self.txt)

    def test_mapea_a_motores_de_la_skill(self):
        for motor in ("Plan", "HyperFrames", "Remotion"):
            self.assertIn(motor, self.txt,
                          f"cada técnica tiene que poder aterrizar en un motor "
                          f"(falta mencionar '{motor}')")

    def test_entrada_desde_skill_y_selector(self):
        with open(os.path.join(BASE, "SKILL.md"), encoding="utf-8") as fh:
            skill = fh.read()
        self.assertIn("motion-ui.md", skill)
        with open(os.path.join(BASE, "references", "animacion.md"),
                  encoding="utf-8") as fh:
            anim = fh.read()
        self.assertIn("motion-ui.md", anim)
        with open(os.path.join(BASE, "references", "mapa.md"),
                  encoding="utf-8") as fh:
            mapa = fh.read()
        self.assertIn("motion-ui.md", mapa)


if __name__ == "__main__":
    unittest.main()
