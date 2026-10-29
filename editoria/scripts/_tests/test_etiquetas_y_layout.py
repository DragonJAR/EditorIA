#!/usr/bin/env python3
"""Tests de etiquetas y layout del 9:16 (fase 2, T13).

QUE PROTEGE

1. `ranking` cortaba sus etiquetas con "…" ("WhatsA…", "Instagra…"): la
   columna de la etiqueta tenia un tope fijo del 38 % del ancho. Ahora se
   mide con las etiquetas y la que no cabe se PARTE (`texto_que_cabe`),
   como ya hace `bars`.
2. Las `ANCLADAS` (cartel, cadena, constancia) iban abajo SIEMPRE, "bajo la
   cara", aunque debajo no hubiera nada. Solo se anclan cuando hay cara
   debajo (`sobre_cara`: overlay o `sobre_cara: true` en la escena); si no,
   se colocan como el resto (centro optico).
3. Las filas que sobran en 9:16 se reparten (`pila`, `cuadricula`): una
   regla con tope (`REPARTO_MAX`), no una por escena.
4. `camino` en 9:16 corre en VERTICAL: una linea horizontal de 778 px en un
   lienzo de 1920 de alto dejaba el 87 % de la zona en negro.
5. Lo que se rellena con un dato (barras, arcos, cifras) va con UNA duracion
   (`RELLENO`), no con 0.7/0.8/0.9/1.1/1.2 segun la escena.

Run with: python3 -m pytest -q -p no:cacheprovider _tests/test_etiquetas_y_layout.py
"""

import copy
import inspect
import json
import os
import sys
import unittest

from PIL import ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, os.path.join(SCRIPTS, "ffmpeg_tools"))


def _muestra(tipo):
    with open(os.path.join(SCRIPTS, "escenas_muestra.json"), encoding="utf-8") as fh:
        e = copy.deepcopy(json.load(fh)["escenas"][tipo])
    e["tipo"] = tipo
    return e


class _Base(unittest.TestCase):
    ancho, alto = 1080, 1920

    def setUp(self):
        import render_plan as R
        R.formato(self.ancho, self.alto)
        R.aplicar_globales({"escenas": []})
        R._ESCALA.clear()
        self.R = R
        self.ctx = R.Ctx()
        self.addCleanup(R.formato, 1080, 1920)

    def _tinta(self, capa):
        return capa.split()[3].point(lambda v: 255 if v > 110 else 0).getbbox()


class TestRankingSinRecorte(_Base):
    def _textos(self, e, t):
        dibujados = []
        original = ImageDraw.ImageDraw.text

        def espia(self_d, xy, text, *a, **k):
            dibujados.append(str(text))
            return original(self_d, xy, text, *a, **k)
        ImageDraw.ImageDraw.text = espia
        try:
            self.R.pintar(self.ctx, e, t)
        finally:
            ImageDraw.ImageDraw.text = original
        return dibujados

    def test_las_etiquetas_se_leen_enteras(self):
        R = self.R
        for ancho, alto in ((1080, 1920), (1920, 1080)):
            R.formato(ancho, alto)
            e = R.completar_escena(_muestra("ranking"), 0)
            textos = self._textos(e, e["to"] - 0.8)
            junto = " ".join(textos)
            with self.subTest(formato=(ancho, alto)):
                self.assertNotIn("…", junto, f"etiqueta recortada: {textos}")
                for it in e["items"]:
                    self.assertIn(it["etiqueta"], junto.replace("\n", " "))

    def test_una_etiqueta_larga_se_parte_y_no_se_recorta(self):
        R = self.R
        e = _muestra("ranking")
        e["items"][2]["etiqueta"] = "Instagram y TikTok orgánico"
        e = R.completar_escena(e, 0)
        textos = self._textos(e, e["to"] - 0.8)
        self.assertNotIn("…", " ".join(textos))
        palabras = " ".join(textos).split()
        for p in "Instagram y TikTok orgánico".split():
            self.assertIn(p, palabras)


class TestAncladasSoloSobreCara(_Base):
    def test_el_predicado_es_uno(self):
        R = self.R
        e = R.completar_escena(_muestra("cartel"), 0)
        self.assertFalse(R.sobre_cara(e))
        self.assertTrue(R.sobre_cara(dict(e, sobre_cara=True)))

    def test_cartel_solo_sube_al_centro(self):
        """Sin nada debajo, el cartel no se queda pegado al pie de la zona."""
        R = self.R
        zx0, zy0, zx1, zy1 = R.caja_segura()
        objetivo = zy0 + R.CENTRO_OPTICO * (zy1 - zy0)
        for i, tipo in enumerate(("cartel", "cadena", "constancia")):
            e = R.completar_escena(_muestra(tipo), i)
            t = e["to"] - 0.8
            bb = self._tinta(R.encuadrar(self.ctx, e, i, t, R.pintar(self.ctx, e, t).copy()))
            with self.subTest(tipo=tipo):
                self.assertLess(abs((bb[1] + bb[3]) / 2 - objetivo), 0.04 * R.H,
                                f"{tipo} sin cara debajo tiene que ir al centro optico: {bb}")
                self.assertGreaterEqual(bb[1], zy0 - 3)
                self.assertLessEqual(bb[3], zy1 + 3)

    def test_con_cara_debajo_sigue_anclado(self):
        R = self.R
        for i, tipo in enumerate(("cartel", "cadena", "constancia")):
            e = R.completar_escena(dict(_muestra(tipo), sobre_cara=True), i)
            with self.subTest(tipo=tipo):
                self.assertEqual(R.llenado(self.ctx, e, i), (1.0, 0.0))


class TestRepartoVertical(_Base):
    def test_pila_reparte_el_sitio_en_vertical_con_tope(self):
        R = self.R
        centros, f = R.pila([100, 100, 100], 0, 1200, gap=24)
        self.assertEqual(f, 1.0)
        paso = centros[1] - centros[0]
        self.assertGreater(paso, 124 + 1, "en 9:16 el sitio que sobra se reparte")
        self.assertLessEqual(paso - 100, 24 + R.REPARTO_MAX * 100 + 1e-6,
                             "con tope: las filas no se leen sueltas")
        self.assertAlmostEqual((centros[0] + centros[-1]) / 2, 600, delta=1)

    def test_pila_en_horizontal_no_cambia(self):
        R = self.R
        R.formato(1920, 1080)
        centros, _ = R.pila([100, 100, 100], 0, 1200, gap=24)
        self.assertAlmostEqual(centros[1] - centros[0], 124, delta=1e-6)

    def test_cuadricula_reparte_su_hueco(self):
        R = self.R
        sin = R.cuadricula(100, 200, 800, 600, 2, 4)
        con = R.cuadricula(100, 200, 800, 600, 2, 4, alto_hueco=1100)
        self.assertEqual([c[3] for c in sin], [c[3] for c in con], "las tarjetas no se estiran")
        self.assertGreater(con[2][1] - con[0][1], sin[2][1] - sin[0][1])
        self.assertGreaterEqual(con[0][1], 200)
        self.assertLessEqual(con[-1][1] + con[-1][3], 200 + 1100)


class TestCaminoVertical(_Base):
    def _escena(self):
        return self.R.completar_escena(_muestra("camino"), 0)

    def test_en_9x16_el_camino_corre_en_vertical(self):
        R = self.R
        e = self._escena()
        bb = self._tinta(R.pintar(self.ctx, e, e["to"] - 0.8))
        self.assertGreater(bb[3] - bb[1], 2 * (bb[2] - bb[0]) * 0.6,
                           f"en 9:16 el camino tiene que ser alto: {bb}")
        self.assertGreater(R.escala_segura(self.ctx, e, 0), 0.995)

    def test_en_16x9_sigue_horizontal(self):
        R = self.R
        R.formato(1920, 1080)
        e = self._escena()
        bb = self._tinta(R.pintar(self.ctx, e, e["to"] - 0.8))
        self.assertGreater(bb[2] - bb[0], bb[3] - bb[1])


class TestRellenoUnico(_Base):
    def test_una_duracion_para_lo_que_se_rellena(self):
        R = self.R
        self.assertTrue(0.6 <= R.RELLENO <= 1.2)
        self.assertEqual(inspect.signature(R.cuenta_up).parameters["dur"].default, R.RELLENO)
        for nombre in ("sc_bars", "sc_ranking", "sc_stats", "sc_gauge", "sc_gauge_anillo"):
            src = inspect.getsource(getattr(R, nombre))
            with self.subTest(escena=nombre):
                self.assertIn("rellena(", src, f"{nombre} no usa la duracion unica")
                for cifra in ("/ 0.9)", "/ 1.1)", "/ 1.2)", "dur=0.7"):
                    self.assertNotIn(cifra, src)


if __name__ == "__main__":
    unittest.main()
