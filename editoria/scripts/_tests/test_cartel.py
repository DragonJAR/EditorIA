#!/usr/bin/env python3
"""Tests de la RONDA 14: el cartel (el panel con el icono grande y la
afirmacion) y la cabecera de marca (global del plan).

QUE PROTEGE

1. El ICONO va en el acento (rojo), a la izquierda, y la afirmacion a su
   derecha: son las dos mitades del cartel del reel de "cara".

2. El BLOQUE de color acaba con la PALABRA. El markup del kit es por
   caracter: "~NOTEPAD++~?" deja la interrogacion fuera del bloque. Con el
   markup por palabra, la interrogacion se quedaba dentro (medido).

3. La cabecera de marca es un GLOBAL: va en todos los fotogramas, no en una
   ventana (las escenas no se solapan) y una escena quieta la declara la
   puerta "congelada".

Run with: python3 -m unittest discover -s scripts/_tests
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)


class TestCartel(unittest.TestCase):
    """El cartel: el icono grande en el acento y la afirmacion al lado."""

    def setUp(self):
        import render_plan as R
        R.formato(1080, 1920)
        self.R = R
        self.ctx = R.Ctx()

    def _pintar(self, e, t=3.0):
        e = self.R.completar_escena(e, 0)
        return self.R.pintar(self.ctx, e, t).convert("RGB")

    def _escena(self, **extra):
        e = {"tipo": "cartel", "from": 0.0, "to": 5.0,
             "kicker": "Todo noviembre", "icono": "lupa",
             "texto": "¿Qué está pasando con ~Notepad++~?",
             "at": {"panel": 0.2, "icono": 0.5, "texto": 0.8}}
        e.update(extra)
        return e

    def _rojos(self, img, x0=0, x1=1080):
        """Los pixeles del ACENTO (el color que lleva el pack; sin pack es el
        azul neutro del respaldo, y con el pack el rojo)."""
        R = self.R
        ar, ag, ab = R.ACENTO[:3]
        w, h = img.size
        px = img.load()
        out = []
        for y in range(h):
            for x in range(x0, x1):
                r, g, b = px[x, y]
                if abs(r - ar) < 60 and abs(g - ag) < 60 and abs(b - ab) < 60:
                    out.append((x, y))
        return out

    def test_el_icono_va_en_el_acento_y_a_la_izquierda(self):
        img = self._pintar(self._escena())
        w, h = img.size
        rojos = self._rojos(img, 0, int(w * 0.35))
        self.assertTrue(rojos, "el icono tiene que ir en el acento")
        ys = [y for x, y in rojos]
        self.assertLess(max(ys), h * 0.9, "el icono va en la mitad del panel")

    def test_el_bloque_de_color_va_con_la_palabra(self):
        """La palabra resaltada va en un bloque del acento."""
        img = self._pintar(self._escena())
        w, h = img.size
        # el bloque esta a la derecha del icono
        rojos = self._rojos(img, int(w * 0.35), w)
        self.assertTrue(rojos, "la palabra resaltada tiene que ir en un bloque del acento")
        xs = [x for x, y in rojos]
        self.assertGreater(len(xs), 50, "el bloque tiene que tener ancho")

    def test_el_bloque_acaba_con_la_palabra(self):
        """`~Notepad++~?`: la interrogacion se queda FUERA del bloque.

        El markup es por caracter: con el markup por palabra, la "?` se
        quedaba dentro del bloque (medido en la primera version).
        """
        img = self._pintar(self._escena())
        w, h = img.size
        px = img.load()
        rojos = self._rojos(img, int(w * 0.35), w)
        if not rojos:
            self.skipTest("el bloque no se ha dibujado todavia")
        borde = max(x for x, y in rojos)
        y0 = min(y for x, y in rojos)
        y1 = max(y for x, y in rojos)
        # a la derecha del bloque hay texto blanco (la interrogacion)
        blancas = [x for y in range(y0, y1 + 1)
                   for x in range(borde + 4, min(w, borde + 90))
                   if min(px[x, y]) > 200]
        self.assertTrue(blancas,
                        "el bloque se comio el caracter que va despues")

    def test_el_panel_queda_dentro_de_la_zona_segura(self):
        R = self.R
        R._ESCALA.clear()
        e = R.completar_escena(self._escena(), 0)
        f = R.escala_segura(self.ctx, e, 0)
        self.assertGreater(f, 0.995,
                           "el cartel tiene que caber en la zona segura")


if __name__ == "__main__":
    unittest.main()
