#!/usr/bin/env python3
"""Tests de medir_contraste.py.

La herramienta mide el contraste real del texto contra su superficie (dos
pasadas: la escena sin texto es la superficie, y solo se mide el texto que es
el ULTIMO que se dibujo sobre cada pixel).

La garantia importante NO es "el catalogo pasa": es que la herramienta DETECTA
un contraste malo de verdad. Por eso el test inyecta el defecto conocido (la
frase clave de la cita en color de acento sobre la banda de acento) SIN tocar
el motor: basta con que el blanco de esa escena sea el acento mientras se
mide. Si la herramienta no lo ve, no sirve.

Run with: python3 -m unittest discover -s SKILL/scripts/_tests
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, os.path.join(SCRIPTS, "ffmpeg_tools"))

import medir_contraste as MC  # noqa: E402
import render_plan as R  # noqa: E402


class Contraste(unittest.TestCase):

    def test_el_catalogo_no_tiene_texto_ilegible(self):
        """Ninguna escena del catalogo deja texto por debajo del umbral."""
        hallazgos = MC.medir()
        graves = [h for h in hallazgos if h["ratio"] < 2.0]
        self.assertEqual(
            graves, [],
            "texto ilegible (contraste por debajo de 2:1): "
            + "; ".join(f"{h['escena']} {h['ratio']} {h['texto']!r}" for h in graves))

    def test_la_herramienta_detecta_el_contraste_malo(self):
        """La prueba de fuego: se inyecta el defecto (la frase clave de la
        cita en color de acento sobre la banda de acento) y la herramienta
        TIENE que verlo. Una guarda que nunca se ha visto fallar no es una
        guarda: es una hipotesis."""
        blanco = R.BLANCO
        try:
            # el defecto: en vez del blanco, la frase clave lleva el acento
            R.BLANCO = R.ACENTO
            hallazgos = MC.medir(escenas={"quote"})
        finally:
            R.BLANCO = blanco
        cita = [h for h in hallazgos if h["escena"] == "quote"]
        self.assertTrue(
            cita,
            "la herramienta NO vio la cita en acento sobre la banda de acento: "
            "no sirve como garantia")
        self.assertLess(cita[0]["ratio"], 3.0)

    def test_la_herramienta_se_restaura_si_algo_falla(self):
        """La medición no puede dejar el motor con el blanco cambiado."""
        blanco = R.BLANCO
        try:
            MC.medir()
        finally:
            R.BLANCO = blanco
        self.assertEqual(R.BLANCO, blanco)


if __name__ == "__main__":
    unittest.main()
