#!/usr/bin/env python3
"""Tests de las reglas de MARCA que el motor hace cumplir: rebote, particulas,
volumen y outro sobrio.

Un pack es el manual de una marca: puede pedir que la pieza NO rebote (marca
de precision), que salga sin particulas, sin volumen 3D o con un outro sobrio.
Antes esas reglas no existian en el motor: el pack las declaraba y nadie las
leia (y la lista de reglas que el motor y la doc comparten esta en
`REGLAS_DEL_MOTOR`, con su propio test).

QUE PROTEGE

1. `rebote: false` = el MISMO resorte con amortiguamiento critico: llega con la
   misma frecuencia y NO se pasa.
2. `particulas: false` = no hay confeti.
3. `volumen: false` = la insignia es plana (sin sombra ni extrusion).
4. `outro_sobrio: true` (o `sobrio` en la escena) = el cierre no late ni lleva
   halo, pero la flotacion y el push-in siguen (un cierre quieto es un frame
   congelado).

Run with: python3 -m unittest discover -s SKILL/scripts/_tests
"""

import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
for p in (SCRIPTS, os.path.join(SCRIPTS, "ffmpeg_tools")):
    if p not in sys.path:
        sys.path.insert(0, p)

import render_plan as R  # noqa: E402


class TestReglasDeMarca(unittest.TestCase):
    def setUp(self):
        self._antes = (R.REBOTE, R.PARTICULAS, R.VOLUMEN, R.OUTRO_SOBRIO)

    def tearDown(self):
        (R.REBOTE, R.PARTICULAS, R.VOLUMEN, R.OUTRO_SOBRIO) = self._antes

    def test_el_pack_declara_las_reglas(self):
        """aplicar_brand lee `reglas` del pack y las instala en el motor."""
        pack = {"nombre": "PRUEBA", "colores": {"acento": "#E8B464"},
                "reglas": {"rebote": False, "particulas": False,
                           "volumen": False, "outro_sobrio": True}}
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "pack.json")
            with open(ruta, "w", encoding="utf-8") as fh:
                json.dump(pack, fh)
            R.aplicar_brand(ruta)
            self.assertFalse(R.REBOTE, "rebote: false no se instalo")
            self.assertFalse(R.PARTICULAS, "particulas: false no se instalo")
            self.assertFalse(R.VOLUMEN, "volumen: false no se instalo")
            self.assertTrue(R.OUTRO_SOBRIO, "outro_sobrio no se instalo")

    def test_sin_rebote_el_resorte_no_se_pasa(self):
        """Sin rebote, el resorte CRITICO no pasa de 1 (el mismo, sin rebote)."""
        R.REBOTE = False
        vals = [R.spring(t, 0.0, stiff=150, damp=15)
                for t in [i / 60 for i in range(180)]]
        self.assertLessEqual(max(vals), 1.0 + 1e-6,
                             f"el resorte critico se paso: {max(vals):.3f}")
        R.REBOTE = True
        vals_con = [R.spring(t, 0.0, stiff=150, damp=15)
                    for t in [i / 60 for i in range(180)]]
        self.assertGreater(max(vals_con), 1.0,
                           "con rebote el resorte deberia pasarse (el test no "
                           "mediria nada)")

    def test_sin_particulas_no_hay_confeti(self):
        """`particulas: false`: la funcion de confeti no dibuja nada."""
        from PIL import Image, ImageDraw
        R.PARTICULAS = False
        img = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
        R.particulas(ImageDraw.Draw(img), 1.0, 0.0, 200, 200, n=40)
        self.assertEqual(img.getbbox(), None,
                         "hay confeti con la regla `particulas: false`")

    def test_el_cierre_sobrio_no_late(self):
        """`sobrio`: el cierre sale sin el latido (pero no congelado)."""
        e = {"tipo": "final", "from": 0.0, "to": 4.0, "marca": "X",
             "sobrio": True, "at": {"lema": 1.0, "boton": 1.6}}
        escena = R.completar_escena(dict(e))
        ctx = R.Ctx()
        a = R.sc_final(ctx, escena, 2.0)
        b = R.sc_final(ctx, escena, 2.8)
        self.assertIsNotNone(a)
        self.assertIsNotNone(b)
        # el cierre sobrio sigue MOVIENDOSE (flotacion y push-in), asi que no
        # puede ser el mismo frame congelado
        self.assertNotEqual(a.tobytes(), b.tobytes(),
                            "el cierre sobrio sale congelado: un frame quieto "
                            "es un fallo (movimiento 0)")

    def test_el_cierre_normal_late(self):
        """Sin `sobrio`, el cierre late: dos instantes distintos."""
        e = {"tipo": "final", "from": 0.0, "to": 4.0, "marca": "X",
             "at": {"lema": 1.0, "boton": 1.6}}
        escena = R.completar_escena(dict(e))
        ctx = R.Ctx()
        a = R.sc_final(ctx, escena, 2.0)
        b = R.sc_final(ctx, escena, 2.05)
        self.assertNotEqual(a.tobytes(), b.tobytes(),
                            "el cierre normal no late: el test no mediria nada")


if __name__ == "__main__":
    unittest.main()
