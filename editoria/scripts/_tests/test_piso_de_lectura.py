#!/usr/bin/env python3
"""Tests del PISO DE LECTURA: cuánto aguanta un texto en pantalla.

La skill medía el TAMAÑO de la letra (26 px) desde hacía tiempo, pero nunca
medía cuánto TIEMPO estaba el texto en pantalla: un titular de seis palabras
que sale a los 0.4 s no lo lee nadie y la puerta no lo decía. La regla ya
existía en `references/ritmo.md` (0.8 s para una etiqueta de 1–3 palabras,
0.3 s por palabra con un piso de 1.2 s para un titular) pero era PROSA: nada
la verificaba.

Estos tests fijan la regla en su canónico (`_comun.tiempo_de_lectura`), la medida
(`_defectos_lectura`) y su comportamiento en el render real. Si se borra la
regla o se suaviza el margen, el test end-to-end falla: es la mutación.

Run with: python3 -m unittest discover -s scripts/_tests
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, os.path.join(SCRIPTS, "ffmpeg_tools"))

import medir_animacion as M  # noqa: E402
from _comun import tiempo_de_lectura  # noqa: E402  (el canonico: _comun)


class TestMinLectura(unittest.TestCase):
    """El canonico del piso de lectura vive en `_comun.tiempo_de_lectura`:
    una idea, un canonico. El medidor y el motor beben de la misma funcion."""

    def test_una_etiqueta_corta_necesita_ocho_decimas(self):
        self.assertEqual(tiempo_de_lectura("Web"), 0.8)
        self.assertEqual(tiempo_de_lectura("Un solo fallo"), 0.8)      # 3 palabras

    def test_cuatro_palabras_caen_en_el_piso_de_un_veinte(self):
        self.assertEqual(tiempo_de_lectura("una frase de cuatro"), 1.2)

    def test_un_titular_cobra_tres_decimas_por_palabra(self):
        self.assertAlmostEqual(tiempo_de_lectura("uno dos tres cuatro cinco"), 1.5)
        self.assertAlmostEqual(tiempo_de_lectura("uno dos tres cuatro cinco seis"), 1.8)

    def test_un_simbolo_no_es_una_lectura(self):
        self.assertEqual(tiempo_de_lectura("✓"), 0.0)
        self.assertEqual(tiempo_de_lectura("   "), 0.0)


class TestDefectosLectura(unittest.TestCase):
    """La medida: qué textos no aguantaron lo que se leen."""

    def _lectura(self, texto, frames):
        return {(1, "apertura", texto): {"frames": set(frames)}}

    def test_un_texto_corto_se_reporta_con_escena_y_sostén(self):
        fuera = M._defectos_lectura(self._lectura("una frase de cuatro palabras", range(0, 9)), 30)
        self.assertEqual(len(fuera), 1)
        self.assertEqual(fuera[0]["escena"], "1:apertura")
        self.assertAlmostEqual(fuera[0]["sosten"], 0.3, places=2)
        self.assertEqual(fuera[0]["minimo"], 1.5)

    def test_un_texto_que_aguanta_no_se_reporta(self):
        fuera = M._defectos_lectura(self._lectura("una frase de cuatro palabras", range(0, 60)), 30)
        self.assertEqual(fuera, [])

    def test_el_margen_del_10_por_ciento_no_es_un_defecto(self):
        # 1.1 s con un piso de 1.2 s: por debajo, pero dentro del margen
        # (10 % del piso = 0.12 s)
        fuera = M._defectos_lectura(self._lectura("una frase de cuatro", range(0, 33)), 30)
        self.assertEqual(fuera, [])

    def test_mas_abajo_del_margen_si_se_reporta(self):
        fuera = M._defectos_lectura(self._lectura("una frase de cuatro", range(0, 30)), 30)
        self.assertEqual(len(fuera), 1)
        self.assertEqual(fuera[0]["minimo"], 1.2)

    def test_los_trozos_de_la_escritura_no_son_lecturas(self):
        # el typewriter escribe caracter a caracter: cada prefijo es un texto
        # distinto y cada uno dura dos frames. Lo que se lee es el texto
        # COMPLETO (el ultimo prefijo), que es el que aguanta.
        lecturas = {}
        for i, txt in enumerate(["E", "Es", "Esq", "Esqu"]):
            lecturas[(1, "typewriter", txt)] = {"frames": {i, i + 1}}
        lecturas[(1, "typewriter", "Esque")] = {"frames": set(range(4, 40))}
        self.assertEqual(M._defectos_lectura(lecturas, 30), [])

    def test_un_trozo_menor_de_tres_caracteres_no_se_juzga(self):
        lecturas = {(1, "typewriter", "E"): {"frames": {0, 1}}}
        self.assertEqual(M._defectos_lectura(lecturas, 30), [])


class TestMedidaEnElRender(unittest.TestCase):
    """La medida sobre el render real: una linea de vida, no un dato de plan."""

    @classmethod
    def setUpClass(cls):
        M._init()

    def _medir(self, to, cambio):
        escena = {"tipo": "apertura", "from": 0.0, "to": to,
                  "texto1": ["Un fallo critico"], "texto2": ["Y todo cae"],
                  "at": {"cambio": cambio,
                         "p1": [0.2, 0.3, 0.4], "p2": [cambio + 0.1, cambio + 0.2]}}
        return M.medir(("prueba", "v", [escena], to, 30))

    def test_un_titular_que_sale_pronto_se_reporta(self):
        m = self._medir(1.4, 0.7)
        self.assertTrue(m["lectura"], "un titular de 0.5 s tiene que salir en la lista")
        self.assertIn("Un fallo critico", m["lectura"][0]["texto"])

    def test_el_mismo_titular_con_tiempo_no_se_reporta(self):
        m = self._medir(3.0, 1.5)
        self.assertEqual(m["lectura"], [])


if __name__ == "__main__":
    unittest.main()
