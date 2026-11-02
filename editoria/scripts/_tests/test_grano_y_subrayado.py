#!/usr/bin/env python3
"""Tests de la RONDA 16: el grano de pelicula y el lema subrayado.

QUE PROTEGE

1. El GRANO es una sola implementacion: vive en `_comun.aplicar_grano` y lo
   usan los films de marca Y el motor de planes. Antes el grano solo
   existia en el motor de films: la misma tecnica, dos implementaciones, y
   el plan salia sin grano. Ademas, con canal alfa, el grano va al RGB y el
   alfa se queda (si no, los bordes salen rugosos).

2. El LEMA SUBRAYADO: el texto con su linea de luz debajo, y la linea
   partida en varios colores. La linea la dibuja la MISMA funcion que el
   camino: lo que cambian son los puntos y los colores.

Run with: python3 -m unittest discover -s scripts/_tests
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, os.path.join(SCRIPTS, "ffmpeg_tools"))


class TestGrano(unittest.TestCase):
    """El grano: una implementación, dos motores."""

    def setUp(self):
        import render_plan as R
        R.formato(1080, 1920)
        self.R = R
        from PIL import Image
        self.Image = Image

    def test_el_grano_se_define_una_sola_vez(self):
        """Una sola implementacion: la misma tecnica en dos motores no puede
        ser dos codigos.

        Se mira el CODIGO FUENTE y no la identidad del modulo: hay tests que
        sacan `_comun` de `sys.modules` y lo reimportan (para probar que se
        importa como modulo suelto), asi que la identidad no es fiable.
        """
        src_film = open(os.path.join(SCRIPTS, "_film.py"), encoding="utf-8").read()
        src_comun = open(os.path.join(SCRIPTS, "ffmpeg_tools", "_comun.py"),
                         encoding="utf-8").read()
        self.assertNotIn("def aplicar_grano", src_film,
                         "el grano se define en _comun, no en el motor de films")
        self.assertIn("aplicar_grano", src_film,
                      "el motor de films lo importa de _comun")
        self.assertIn("def aplicar_grano", src_comun,
                      "la definicion vive en _comun (una sola vez)")
        # y el motor de planes lo toma del mismo fichero
        self.assertEqual(self.R.aplicar_grano.__code__.co_filename,
                         os.path.join(SCRIPTS, "ffmpeg_tools", "_comun.py"))

    def test_sin_grano_la_imagen_no_se_toca(self):
        img = self.Image.new("RGB", (40, 30), (120, 120, 120))
        out = self.R.aplicar_grano(img, 40, 30, 0, amp=0)
        self.assertEqual(list(out.getdata()), list(img.getdata()),
                         "amp=0 tiene que devolver la imagen intacta")

    def test_el_grano_cambia_el_rgb_y_no_toca_el_alfa(self):
        img = self.Image.new("RGBA", (40, 30), (120, 120, 120, 200))
        out = self.R.aplicar_grano(img, 40, 30, 0, amp=4)
        self.assertEqual(out.mode, "RGBA")
        alfa = out.split()[3].getextrema()
        self.assertEqual(alfa, (200, 200), "el alfa no se toca: el grano va al RGB")
        self.assertNotEqual(list(out.convert("RGB").getdata()),
                            list(img.convert("RGB").getdata()),
                            "el grano tiene que cambiar el RGB")

    def test_el_plan_declara_el_grano_y_solo_afecta_a_los_frames(self):
        R = self.R
        plan = {"escenas": [{"tipo": "typewriter", "from": 0.0, "to": 4.0,
                            "texto": "hola"}]}
        R.aplicar_globales(dict(plan, grano=4))
        self.assertEqual(R._GRANO["amp"], 4)
        R.aplicar_globales(dict(plan))          # sin grano
        self.assertEqual(R._GRANO["amp"], 0, "sin grano declarado no hay grano")


class TestSubrayado(unittest.TestCase):
    """El lema con su línea de luz debajo."""

    def setUp(self):
        import render_plan as R
        R.formato(1080, 1920)
        self.R = R
        self.ctx = R.Ctx()

    def _pintar(self, e, t=3.0):
        e = self.R.completar_escena(e, 0)
        return self.R.pintar(self.ctx, e, t).convert("RGB")

    def _escena(self, **extra):
        e = {"tipo": "subrayado", "from": 0.0, "to": 5.0,
             "texto": "Un camino, todas las habilidades",
             "at": {"texto": 0.2, "linea": 0.9}}
        e.update(extra)
        return e

    def test_la_linea_esta_DEBAJO_del_texto(self):
        """La linea es la LINEA BASE: va debajo del texto, no encima.

        Se busca el color EXACTO de la linea (la escena lo declara) y con
        tolerancia estrecha: si se busca "cualquier pixel del acento", con
        un pack rojo el texto blanco tambien cuenta como acento y la
        comparacion no dice nada (el estado de la paleta lo cambia otro
        test).
        """
        ROJO = (255, 0, 0)
        img = self._pintar(self._escena(color=list(ROJO) + [255]))
        w, h = img.size
        px = img.load()
        ys = [y for y in range(h) for x in range(0, w, 2)
              if abs(px[x, y][0] - ROJO[0]) < 40
              and abs(px[x, y][1] - ROJO[1]) < 40
              and abs(px[x, y][2] - ROJO[2]) < 40]
        self.assertTrue(ys, "no hay linea de acento")
        blancos = [y for y in range(h) for x in range(0, w, 6) if min(px[x, y]) > 200]
        self.assertTrue(blancos, "no hay texto")
        self.assertLess(max(blancos), min(ys),
                        "la linea tiene que ir DEBAJO del texto")

    def test_la_linea_se_parte_en_los_colores(self):
        """Con `colores`, la linea va cambiando de color a lo largo."""
        img = self._pintar(self._escena(
            colores=[[193, 27, 5, 255], [28, 176, 246, 255]]))
        w, h = img.size
        px = img.load()
        y = None
        for yy in range(h):
            if any(px[x, yy][0] > 150 and px[x, yy][1] < 60 for x in range(0, w, 8)):
                y = yy
                break
        self.assertIsNotNone(y, "no hay la parte roja de la linea")
        rojos = [x for x in range(w) if px[x, y][0] > 150 and px[x, y][1] < 60]
        azules = [x for x in range(w)
                  if px[x, y][2] > 150 and px[x, y][0] < 90]
        self.assertTrue(rojos, "el primer color no sale")
        self.assertTrue(azules, "el segundo color no sale")
        self.assertLess(max(rojos), min(azules),
                        "el color cambia a lo largo de la linea, no a lo random")


if __name__ == "__main__":
    unittest.main()
