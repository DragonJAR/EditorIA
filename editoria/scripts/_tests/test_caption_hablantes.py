#!/usr/bin/env python3
"""Tests for caption.py — speaker colors and phrase grouping rules.

Covers: speaker prefixes ("ANA: ..."), grouping that never mixes speakers,
negation and quantity kept with the following word (unless the word ends
the sentence), speaker color assignment, and one ASS style per speaker.

Run with: python3 -m unittest discover -s SKILL/scripts/_tests
"""

import os
import sys
import tempfile
import unittest
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "ffmpeg_tools"))

import caption as cap  # noqa: E402


def palabras(texto, hablante=None, t0=0.0, paso=0.3):
    return [[w, t0 + i * paso, t0 + i * paso + 0.25, hablante] for i, w in enumerate(texto.split())]


class TestHablantes(unittest.TestCase):
    def test_prefijo(self):
        self.assertEqual(cap.separar_hablante("ANA: hola"), ("ANA", "hola"))
        self.assertEqual(cap.separar_hablante("[LUIS]: qué tal"), ("LUIS", "qué tal"))
        # "Nota:" no es un hablante (solo nombres en mayúsculas)
        self.assertEqual(cap.separar_hablante("Nota: algo"), (None, "Nota: algo"))

    def test_con_hablante_normaliza(self):
        cues = cap.con_hablante([(0, 1, "ANA: hola"), (1, 2, "sin prefijo")])
        self.assertEqual(cues[0], (0, 1, "hola", None, "ANA"))
        self.assertEqual(cues[1][4], None)

    def test_nunca_mezcla_hablantes(self):
        ws = palabras("hola qué tal", "ANA") + palabras("muy bien gracias", "LUIS", t0=1.0)
        cues = cap.agrupar_palabras(ws, max_words=6)
        self.assertEqual([c[4] for c in cues], ["ANA", "LUIS"])
        self.assertEqual(cues[0][2], "hola qué tal")

    def test_colores(self):
        cues = [(0, 1, "a", None, "ANA"), (1, 2, "b", None, "LUIS"), (2, 3, "c", None, "ANA")]
        auto = cap.colores_hablantes("auto", cues, "E8480C")
        self.assertEqual(auto["ANA"], "E8480C")            # el acento primero
        self.assertNotEqual(auto["ANA"], auto["LUIS"])
        fijo = cap.colores_hablantes("luis=4fc3f7", cues, "E8480C")
        self.assertEqual(fijo["LUIS"], "4FC3F7")
        self.assertNotEqual(fijo["ANA"], fijo["LUIS"])
        with self.assertRaises(SystemExit):
            cap.colores_hablantes("ANA", cues, "E8480C")

    def test_ass_un_estilo_por_hablante(self):
        args = SimpleNamespace(size=24, margin=30, max_lines=0, fonts_dir=None, font="DejaVu Sans",
                               min_size=14, karaoke=True, highlight_color="E8480C", color="FFFFFF",
                               outline_color="000000", bold=False, box=False, outline=2.0, shadow=0.0,
                               position="bottom", animate="none", karaoke_timing="even",
                               colores_hablantes={"ANA": "FFD400", "LUIS": "4FC3F7"})
        cues = [(0, 1, "hola", [100], "ANA"), (1, 2, "adiós", [100], "LUIS")]
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "x.ass")
            cap.write_ass(cues, p, args, 1080, 1920)
            with open(p, encoding="utf-8-sig") as fh:
                txt = fh.read()
        self.assertIn("Style: H0,", txt)
        self.assertIn("Style: H1,", txt)
        self.assertIn(",H0,,0,0,0,,", txt)
        self.assertIn(",H1,,0,0,0,,", txt)
        # con karaoke el color del hablante es el de la palabra dicha (BGR de ASS)
        self.assertIn("&H0000D4FF", txt)


class TestAgrupacion(unittest.TestCase):
    def test_negacion_va_con_su_verbo(self):
        # el candidato "eso ya no" terminaría en negación: "no" abre el siguiente
        cues = cap.agrupar_palabras(palabras("eso ya no funciona aquí"), max_words=3)
        self.assertEqual([c[2] for c in cues], ["eso ya", "no funciona aquí"])

    def test_cantidad_va_con_su_unidad(self):
        cues = cap.agrupar_palabras(palabras("en solo 30 segundos de video"), max_words=3)
        self.assertIn("30 segundos", " | ".join(c[2] for c in cues))

    def test_fin_de_frase_puede_cerrar(self):
        # "no." cierra la oración: no se arrastra al caption siguiente
        cues = cap.agrupar_palabras(palabras("claro que no. Mira esto"), max_words=3)
        self.assertEqual(cues[0][2], "claro que no")

    def test_phrase_aware_conserva_hablante(self):
        cues = cap.phrase_aware([(0, 2, "uno dos tres cuatro", None, "ANA")], max_words=2)
        self.assertTrue(all(c[4] == "ANA" for c in cues))


if __name__ == "__main__":
    unittest.main()
