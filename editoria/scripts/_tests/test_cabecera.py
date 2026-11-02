#!/usr/bin/env python3
"""Tests de la RONDA 14: la cabecera de marca (global del plan).

QUE PROTEGE

1. La cabecera es un GLOBAL y no una escena. La banda del rack esta en
   TODOS los fotogramas de la pieza mientras que una escena ocupa una
   ventana (y las escenas no se solapan). Ademas, una escena estatica la
   declara la puerta CONGELADA ("ningun hold congelado"): el rack no se
   mueve, asi que como escena no tendria nada que hacer en su propia
   ventana.

2. El CHIP lleva la FUENTE, no la accion. En el reel de "cara" el chip dice
   de donde sale el material ("CHARLA COMPLETA - youtu.be/...") y el boton
   (que es la accion) va en otra parte. Confunder los dos hace que la pieza
   prometa un canal que no se ha medido.

3. El LOGO solo sale si la pieza declara la marca del PACK. Un logo que
   acompaña a otro nombre es justo lo que la doctrina prohibe.

Run with: python3 -m unittest discover -s scripts/_tests
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)


class TestCabecera(unittest.TestCase):
    """La cabecera: la marca a la izquierda, la fuente a la derecha."""

    def setUp(self):
        import render_plan as R
        R.formato(1080, 1920)
        self.R = R
        self.ctx = R.Ctx()

    def _frame(self, cabecera=None, t=2.0):
        """El lienzo del instante t con la cabecera global aplicada."""
        R = self.R
        plan = {"escenas": [{"tipo": "typewriter", "from": 0.0, "to": 5.0,
                             "texto": "hola"}]}
        if cabecera is not None:
            plan["cabecera"] = cabecera
        R.aplicar_globales(plan)
        e = R.completar_escena(plan["escenas"][0], 0)
        return R.componer(self.ctx, [e], 5.0, t, set()).convert("RGB")

    def test_sin_cabecera_no_hay_banda(self):
        img = self._frame(None)
        w, h = img.size
        px = img.load()
        banda = [x for y in range(0, int(h * 0.15)) for x in range(w)
                 if min(px[x, y]) > 120]
        self.assertEqual(banda, [], "sin cabecera no hay banda arriba")

    def test_el_chip_va_arriba_y_a_la_derecha(self):
        """El chip esta en la banda de arriba (a ~7 % del alto) y pegado al
        borde derecho."""
        img = self._frame({"chip": "CHARLA COMPLETA - youtu.be/tu-video"})
        w, h = img.size
        px = img.load()
        banda = [(x, y) for y in range(0, int(h * 0.15)) for x in range(w)
                 if min(px[x, y]) > 120]
        self.assertTrue(banda, "el chip no se dibuja")
        xs = [x for x, y in banda]
        ys = [y for x, y in banda]
        self.assertGreater(min(xs), w * 0.3, "el chip va a la derecha")
        self.assertLess(max(xs), w * 0.98, "el chip no se sale del lienzo")
        self.assertLess(max(ys), h * 0.12, "el chip va en la banda de arriba")

    def test_un_chip_largo_no_se_sale_del_lienzo(self):
        """Un texto largo no se sale del lienzo."""
        img = self._frame({"chip": "UNA FUENTE MUY LARGA " * 6})
        w, h = img.size
        px = img.load()
        for y in range(0, int(h * 0.15)):
            for x in range(int(w * 0.99), w):
                self.assertLess(min(px[x, y]), 200,
                                "el chip se sale del lienzo por la derecha")

    def test_el_logo_no_sale_si_la_marca_no_es_la_del_pack(self):
        """Un logo solo acompaña a su propia marca."""
        R = self.R
        img = self._frame({"chip": "X", "marca": "Una Marca Distinta"})
        w, h = img.size
        px = img.load()
        banda_izq = [x for y in range(0, int(h * 0.15)) for x in range(0, int(w * 0.3))
                     if min(px[x, y]) > 120]
        self.assertEqual(banda_izq, [],
                         "el logo aparece con una marca que no es la del pack")

    def test_el_logo_sale_cuando_la_marca_es_la_del_pack(self):
        """Con la marca del pack, el logo se dibuja a la izquierda."""
        from PIL import Image
        R = self.R
        R.MARCA_NOMBRE = "MiMarca"
        self.ctx.logo = Image.new("RGBA", (220, 40), (255, 255, 255, 255))
        try:
            img = self._frame({"chip": "X", "marca": "MiMarca"})
        finally:
            R.MARCA_NOMBRE = None
        w, h = img.size
        px = img.load()
        banda_izq = [x for y in range(0, int(h * 0.15)) for x in range(0, int(w * 0.3))
                     if min(px[x, y]) > 120]
        self.assertTrue(banda_izq, "el logo del pack tiene que salir a la izquierda")


if __name__ == "__main__":
    unittest.main()
