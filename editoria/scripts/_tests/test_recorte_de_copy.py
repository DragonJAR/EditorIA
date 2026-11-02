#!/usr/bin/env python3
"""Tests del recorte de copy.

`recorta_para` recorta el texto que no cabe en su columna. La pieza sigue
siendo legible, pero el copy pierde palabras: si eso no se anota, el defecto
no aparece hasta que alguien lee la pieza (no hay linter que sepa el ancho de
cada columna: lo decide la escena).

Run with: python3 -m unittest discover -s SKILL/scripts/_tests
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, os.path.join(SCRIPTS, "ffmpeg_tools"))

import render_plan as R  # noqa: E402


class RecorteDeCopy(unittest.TestCase):

    def setUp(self):
        from PIL import Image, ImageDraw, ImageFont
        R.RECORTES.clear()
        self.tmp = ImageDraw.Draw(Image.new("L", (10, 10)))
        self.fnt = ImageFont.truetype(R.FJ, 40)

    def test_un_texto_que_cabe_no_se_toca_ni_se_anota(self):
        fnt = self.fnt
        texto = "Corto"
        ancho = self.tmp.textlength(texto, font=fnt) + 10
        out = R.recorta_para(texto, fnt, ancho, self.tmp)
        self.assertEqual(out, texto)
        self.assertEqual(R.RECORTES, [], "un texto que cabe no es un recorte")

    def test_un_texto_que_no_cabe_se_anota(self):
        """El recorte se avisa: sin esto, el copy se pierde en silencio."""
        fnt = self.fnt
        texto = "Un texto mucho mas largo que la columna"
        out = R.recorta_para(texto, fnt, 40, self.tmp)
        self.assertNotEqual(out, texto)
        self.assertTrue(out.endswith("…"))
        self.assertEqual(len(R.RECORTES), 1)
        self.assertEqual(R.RECORTES[0]["texto"], texto,
                         "el aviso tiene que decir el copy ORIGINAL, no el corto")
        self.assertLessEqual(R.RECORTES[0]["ancho_max"], 40)


if __name__ == "__main__":
    unittest.main()
