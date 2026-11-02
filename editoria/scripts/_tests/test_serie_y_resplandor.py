#!/usr/bin/env python3
"""Tests de los tokens de estado/categoría y del resplandor sin borde.

QUE PROTEGE (auditoría fase 2, scratchpad/audit/mega)

  · Colores a mano: las porciones del `pie`, el "Tibio" de `leads`, el
    "PAGADO" de `recupera` y el subrayado arcoíris de la muestra llevaban RGB
    sueltos que no seguían a la marca. Ahora salen de tokens derivados del
    acento: `SERIE` (categorías, >=5, distinguibles también con daltonismo),
    `EXITO` y `AVISO`. Un pack puede declararlos en `colores`.
  · El resplandor del `orbita` se veía como un CUADRADO de bordes duros
    (zoom_orbita.png): el desenfoque se pintaba en un lienzo del tamaño
    exacto de la forma y se recortaba. `resplandor` acolcha el lienzo ~3σ.
  · El pincel por defecto de `hand_draw` (#101827) no se ve sobre fondo
    oscuro; el centro del `pie` decía "100%" (no dice nada).

Run with: python3 -m pytest -q -p no:cacheprovider _tests/test_serie_y_resplandor.py
"""

import itertools
import json
import os
import re
import sys
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
BASE = os.path.dirname(SCRIPTS)
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, os.path.join(SCRIPTS, "ffmpeg_tools"))

from _comun import NEUTRO, PALETAS, contraste, hex_a_rgb  # noqa: E402

PACKS = ("carbon", "dragonjar")
# distancia mínima entre dos categorías, con visión normal y simulando
# deuteranopía/protanopía (Machado 2009): por debajo se confunden en un pie
DISTINTAS = 50
# piso WCAG de un objeto gráfico (1.4.11) y de texto grande
PISO_GRAFICO = 3.0


def _pack(nombre):
    with open(os.path.join(BASE, "brand", f"{nombre}.json"), encoding="utf-8") as fh:
        return json.load(fh)


class TestTokensDeEstado(unittest.TestCase):
    def setUp(self):
        import render_plan as R
        self.R = R

    def _juegos(self):
        """(nombre, acento, negro, tokens) para la neutra, el catálogo y los packs."""
        R = self.R
        yield "neutra", NEUTRO["acento"], NEUTRO["negro"], R.tokens_de_estado(
            NEUTRO["acento"], NEUTRO["negro"])
        for n, p in PALETAS.items():
            yield n, p["acento"], p["negro"], R.tokens_de_estado(p["acento"], p["negro"])
        for n in PACKS:
            col = _pack(n)["colores"]
            ac, ng = hex_a_rgb(col["acento"]), hex_a_rgb(col["negro"])
            yield n, ac, ng, R.tokens_de_estado(ac, ng)

    def test_la_serie_sale_del_acento_y_se_distingue(self):
        R = self.R
        for nombre, ac, ng, tk in self._juegos():
            with self.subTest(juego=nombre):
                serie = tk["serie"]
                self.assertGreaterEqual(len(serie), 5)
                self.assertEqual(tuple(serie[0]), tuple(ac), "la primera categoría es el acento")
                for c in serie:
                    self.assertGreaterEqual(contraste(c, ng), PISO_GRAFICO,
                                            f"{c} no se ve sobre el fondo")
                peor = min(R.distancia_daltonica(a, b)
                           for a, b in itertools.combinations(serie, 2))
                self.assertGreaterEqual(peor, DISTINTAS,
                                        f"dos categorías se confunden (distancia {peor:.0f})")

    def test_exito_y_aviso_se_leen_como_texto(self):
        for nombre, ac, ng, tk in self._juegos():
            with self.subTest(juego=nombre):
                for k in ("exito", "aviso"):
                    self.assertGreaterEqual(contraste(tk[k], ng), 4.5,
                                            f"{k} no se lee sobre el fondo")

    def test_los_packs_declaran_sus_tokens_y_el_motor_los_instala(self):
        R = self.R
        self.addCleanup(R.aplicar_brand, None)   # vuelve a la paleta neutra
        for n in PACKS:
            with self.subTest(pack=n):
                col = _pack(n)["colores"]
                for k in ("serie", "exito", "aviso"):
                    self.assertIn(k, col, f"el pack {n} no declara '{k}'")
                ng = hex_a_rgb(col["negro"])
                serie = [hex_a_rgb(c) for c in col["serie"]]
                self.assertEqual(serie[0], hex_a_rgb(col["acento"]))
                for a, b in itertools.combinations(serie, 2):
                    self.assertGreaterEqual(R.distancia_daltonica(a, b), DISTINTAS)
                for c in serie:
                    self.assertGreaterEqual(contraste(c, ng), PISO_GRAFICO)
                solape = (R.SOLAPE, R.SOLAPE_PRE)
                try:
                    R.aplicar_brand(os.path.join(BASE, "brand", f"{n}.json"))
                    self.assertEqual([tuple(c) for c in R.SERIE], serie)
                    self.assertEqual(tuple(R.EXITO), hex_a_rgb(col["exito"]))
                    self.assertEqual(tuple(R.AVISO), hex_a_rgb(col["aviso"]))
                finally:
                    R.SOLAPE, R.SOLAPE_PRE = solape

    def test_no_quedan_colores_a_mano_en_las_escenas(self):
        with open(os.path.join(SCRIPTS, "render_plan.py"), encoding="utf-8") as fh:
            src = fh.read()
        for lit in ("(200,140,40)", "(90,140,200)", "(80,220,120", "(245, 130, 32)",
                    "(64, 158, 255)", "(46, 204, 113)"):
            self.assertNotIn(lit, src, f"color a mano en render_plan: {lit}")

    def test_la_muestra_del_subrayado_usa_la_serie(self):
        with open(os.path.join(SCRIPTS, "escenas_muestra.json"), encoding="utf-8") as fh:
            e = json.load(fh)["escenas"]["subrayado"]
        self.assertEqual(e.get("colores"), "serie",
                         "la muestra trae un arcoíris a mano en vez de la serie de la marca")
        R = self.R
        self.assertEqual(R.colores_de(e.get("colores")), [tuple(c) for c in R.SERIE[:4]])
        self.assertIsNone(R.colores_de(None))


class TestPieYPincel(unittest.TestCase):
    def test_el_centro_del_pie_dice_la_porcion_del_acento(self):
        import render_plan as R
        with open(os.path.join(SCRIPTS, "escenas_muestra.json"), encoding="utf-8") as fh:
            e = json.load(fh)["escenas"]["pie"]
        self.assertNotIn("centro", e, "la muestra fija un '100%' que no dice nada")
        cifra, etiqueta = R.centro_del_pie(e)
        acento = next(p for p in e["porciones"] if p.get("acento"))
        total = sum(p["valor"] for p in e["porciones"])
        self.assertEqual(cifra, f"{int(acento['valor'] / total * 100)}%")
        self.assertEqual(etiqueta, acento["etiqueta"])
        self.assertEqual(R.centro_del_pie(dict(e, centro="7 de 10")), ("7 de 10", ""))

    def test_el_pincel_por_defecto_se_ve_sobre_el_fondo(self):
        import hand_draw as HD
        self.assertGreaterEqual(contraste(HD.BROCHA_LAPIZ["color"], NEUTRO["negro"]), 4.5,
                                "el lápiz por defecto no se ve sobre fondo oscuro")


class TestResplandor(unittest.TestCase):
    def setUp(self):
        import render_plan as R
        self.R = R

    def test_el_resplandor_no_tiene_borde(self):
        """El borde del lienzo del resplandor es transparente: no hay cuadrado."""
        from PIL import Image
        R = self.R
        for sigma in (8, 30, 90):
            with self.subTest(sigma=sigma):
                capa = Image.new("RGBA", (800, 800), (0, 0, 0, 0))
                g = R.resplandor(capa, (300, 300, 500, 500), (255, 120, 0), sigma, alfa=255)
                a = np.asarray(g.split()[3])
                borde = max(a[0].max(), a[-1].max(), a[:, 0].max(), a[:, -1].max())
                self.assertLessEqual(int(borde), 2, f"el resplandor tiene borde ({borde})")
                self.assertGreater(int(a.max()), 100, "el resplandor no pinta nada")
                self.assertGreater(int(np.asarray(capa.split()[3]).max()), 100,
                                   "no se compuso sobre la capa")

    def test_los_cuatro_resplandores_usan_el_helper(self):
        with open(os.path.join(SCRIPTS, "render_plan.py"), encoding="utf-8") as fh:
            src = fh.read()
        llamadas = len(re.findall(r"(?<!def )\bresplandor\(", src))
        self.assertGreaterEqual(llamadas, 4, f"solo {llamadas} resplandores usan el helper")


if __name__ == "__main__":
    unittest.main()
