#!/usr/bin/env python3
"""Tests de la composicion vertical: el contenido va al centro optico.

QUE PROTEGE

En el video real del catalogo casi todas las escenas quedaban en una franja
y la mitad de arriba o de abajo del 9:16 era fondo negro. El llenado (T3)
solo recentraba una escena cuando CRECIA, y la mayoria no crece (las limita
el ancho). Ahora `encuadrar` aplica UNA regla a toda escena: el centro
vertical de su bbox medido cae en el centro optico de la zona segura
(`CENTRO_OPTICO`, un poco sobre el centro geometrico), sin salirse de ella.
Quedan fuera las que tienen su sitio por diseno: zona declarada, overlay,
a sangre, `y` declarada y las ancladas abajo por su rol (`ANCLADAS`).

Run with: python3 -m pytest -q -p no:cacheprovider _tests/test_composicion_vertical.py
"""

import copy
import json
import os
import sys
import unittest

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, os.path.join(SCRIPTS, "ffmpeg_tools"))


def _muestra(tipo):
    with open(os.path.join(SCRIPTS, "escenas_muestra.json"), encoding="utf-8") as fh:
        e = copy.deepcopy(json.load(fh)["escenas"][tipo])
    e["tipo"] = tipo
    return e


class TestComposicionVertical(unittest.TestCase):
    def setUp(self):
        import render_plan as R
        R.formato(1080, 1920)
        R.aplicar_globales({"escenas": []})
        R._ESCALA.clear()
        self.R = R
        self.ctx = R.Ctx()

        def alta(ctx, e, t):
            # una franja tan ancha como la zona segura (no puede crecer) y
            # anclada arriba, en H*0.2: el caso de la escena que no crece
            capa = Image.new("RGBA", (R.W, R.H), (0, 0, 0, 0))
            zx0, _, zx1, _ = R.caja_segura()
            y = int(R.H * 0.2)
            ImageDraw.Draw(capa).rectangle([zx0 + 2, y, zx1 - 2, y + 160], fill=(255, 255, 255, 255))
            return capa
        R.SCENES["_prueba_alta"] = alta
        self.addCleanup(R.SCENES.pop, "_prueba_alta", None)

    def _tinta(self, capa):
        return capa.split()[3].point(lambda v: 255 if v > 110 else 0).getbbox()

    def _bbox_final(self, e, idx, t):
        R = self.R
        return self._tinta(R.encuadrar(self.ctx, e, idx, t, R.pintar(self.ctx, e, t).copy()))

    def test_una_escena_alta_baja_al_centro_optico(self):
        R = self.R
        e = {"tipo": "_prueba_alta", "from": 0.0, "to": 4.0}
        zx0, zy0, zx1, zy1 = R.caja_segura()
        objetivo = zy0 + R.CENTRO_OPTICO * (zy1 - zy0)
        self.assertLess(R.CENTRO_OPTICO, 0.5, "el centro optico va un poco SOBRE el geometrico")
        for t in (0.6, 2.0, 3.9):
            bb = self._bbox_final(e, 0, t)
            with self.subTest(t=t):
                self.assertLess(abs((bb[1] + bb[3]) / 2 - objetivo), 0.02 * R.H,
                                "el contenido tiene que quedar en el centro optico")
                self.assertGreaterEqual(bb[0], zx0 - 2)
                self.assertLessEqual(bb[2], zx1 + 2)
                self.assertGreaterEqual(bb[1], zy0 - 2)
                self.assertLessEqual(bb[3], zy1 + 2)

    def test_el_desplazamiento_es_constante_en_la_escena(self):
        """Una funcion pura del bbox medido: el mismo dy en cada instante (sin
        temblor en las entradas) y una segunda pasada no vuelve a mover."""
        R = self.R
        e = {"tipo": "_prueba_alta", "from": 0.0, "to": 4.0}
        g, dy = R.llenado(self.ctx, e, 0)
        self.assertGreater(dy, 0.15 * R.H, "la franja de arriba tiene que bajar")
        self.assertEqual((g, dy), R.llenado(self.ctx, e, 0))
        # el bbox ya colocado, medido otra vez: la regla no lo mueve de nuevo
        zx0, _, zx1, _ = R.caja_segura()
        y = int(R.H * 0.2) + dy
        g2, dy2 = R._crecer(e, (zx0 + 2, y, zx1 - 2, y + 161))
        self.assertEqual(g2, 1.0)
        self.assertLess(abs(dy2), 2.0, "idempotente: lo centrado ya no se mueve")

    def test_las_ancladas_y_las_declaradas_no_se_mueven(self):
        R = self.R
        self.assertTrue({"cadena", "cartel", "constancia"} <= R.ANCLADAS)
        for i, tipo in enumerate(("cadena", "cartel", "rotulo_inferior")):
            e = R.completar_escena(_muestra(tipo), i)
            with self.subTest(tipo=tipo):
                self.assertEqual(R.llenado(self.ctx, e, i), (1.0, 0.0))
        base = {"tipo": "_prueba_alta", "from": 0.0, "to": 4.0}
        for j, extra in enumerate(({"y": 300}, {"zona": [151, 300, 929, 560]})):
            with self.subTest(extra=extra):
                self.assertEqual(R.llenado(self.ctx, dict(base, **extra), 10 + j), (1.0, 0.0))

    def test_la_zona_segura_se_respeta_en_las_escenas_reales(self):
        """Las escenas del catalogo que se recentran siguen dentro de la zona
        segura al final de la escena (camara al maximo): la `zona` del QA."""
        R = self.R
        zx0, zy0, zx1, zy1 = R.caja_segura()
        for i, tipo in enumerate(("apertura", "hoy", "gauge", "stats", "ranking")):
            e = R.completar_escena(_muestra(tipo), i)
            t = e["to"] - 0.65
            bb = self._bbox_final(e, i, t)
            with self.subTest(tipo=tipo):
                self.assertGreaterEqual(bb[0], zx0 - 3)
                self.assertLessEqual(bb[2], zx1 + 3)
                self.assertGreaterEqual(bb[1], zy0 - 3)
                self.assertLessEqual(bb[3], zy1 + 3)


if __name__ == "__main__":
    unittest.main()
