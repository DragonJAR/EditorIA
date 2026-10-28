#!/usr/bin/env python3
"""Tests de la cascada (stagger) y del revelado por mascara.

QUE PROTEGE

1. La CASCADA es una sola cifra: `STAGGER` (40-90 ms, animacion.md §4).
   Antes cada escena escribia su propio `i * 0.xx` (de 0.08 a 0.40 s) y una
   lista de cuatro filas tardaba 1.2 s en armarse: se leia lenta. Ahora el
   paso entre items de una lista lo da `escalonado()`, y el `at` explicito
   del plan sigue mandando.

2. El REVELADO POR MASCARA: el titular y el rotulo suben desde detras de su
   propia linea base (clip), no aparecen por fundido.

Run with: python3 -m unittest discover -s scripts/_tests
"""

import copy
import json
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, os.path.join(SCRIPTS, "ffmpeg_tools"))

DOCTRINA = (0.04, 0.09)   # animacion.md §4: 40-90 ms entre elementos
LISTAS = ("ranking", "stats", "hoy", "cadena", "bars", "bento", "index", "leads", "buscador")
# fuera: timeline, pasos y notificacion (cada item es un beat que se LEE) y pie
# (los sectores se dibujan por tiempo, no entran en cascada)


def _muestra(tipo):
    with open(os.path.join(SCRIPTS, "escenas_muestra.json"), encoding="utf-8") as fh:
        e = copy.deepcopy(json.load(fh)["escenas"][tipo])
    e.setdefault("tipo", tipo)
    return e   # completar_escena rellena los `at` que falten desde esta muestra


def _cadena_mas_larga(ts):
    """La serie aritmetica mas larga dentro de `ts` (largo, paso)."""
    ts = sorted(set(round(x, 6) for x in ts))
    mejor = (1, 0.0)
    for i in range(len(ts)):
        for j in range(i + 1, len(ts)):
            d = round(ts[j] - ts[i], 6)
            if d <= 0:
                continue
            n, x = 2, ts[j]
            while round(x + d, 6) in ts:
                x = round(x + d, 6)
                n += 1
            if n > mejor[0]:
                mejor = (n, d)
    return mejor


class TestStagger(unittest.TestCase):
    def setUp(self):
        import render_plan as R
        R.formato(1080, 1920)
        self.R = R
        self.ctx = R.Ctx()

    def test_la_cascada_es_una_cifra_de_la_doctrina(self):
        R = self.R
        self.assertTrue(DOCTRINA[0] <= R.STAGGER <= DOCTRINA[1],
                        f"STAGGER={R.STAGGER} fuera de 40-90 ms")
        self.assertAlmostEqual(R.escalonado({}, "item", 3, 1.0), 1.0 + 3 * R.STAGGER)

    def test_el_at_explicito_manda(self):
        R = self.R
        self.assertEqual(R.escalonado({"item2": 7.0}, "item", 2, 1.0), 7.0)
        # item0 explicito ancla la cascada: el resto la sigue con STAGGER
        self.assertAlmostEqual(R.escalonado({"item0": 2.0}, "item", 2, 1.0),
                               2.0 + 2 * R.STAGGER)

    def test_las_listas_entran_con_el_paso_de_la_doctrina(self):
        """El paso por defecto entre items, medido con las entradas REALES
        que el motor pide al pintar cada lista."""
        R = self.R
        original = R.entra
        for tipo in LISTAS:
            e = R.completar_escena(_muestra(tipo), 0)
            n = len(e.get("items") or e.get("tarjetas") or e.get("cards")
                    or e.get("barras") or e.get("filas") or e.get("resultados") or [])
            if n < 3:
                continue
            vistos = []

            def espia(t, t0, rol="bloque"):
                vistos.append(t0)
                return original(t, t0, rol)
            R.entra = espia
            try:
                R.pintar(self.ctx, e, e["to"] - 0.1)
            finally:
                R.entra = original
            largo, paso = _cadena_mas_larga(vistos)
            with self.subTest(tipo=tipo):
                self.assertGreaterEqual(largo, n, f"{tipo}: no hay cascada de {n} items")
                self.assertTrue(DOCTRINA[0] <= paso <= DOCTRINA[1],
                                f"{tipo}: paso {paso:.3f} s fuera de 40-90 ms")

    def test_no_quedan_pasos_de_cascada_a_mano(self):
        """Un `i * 0.xx` en un instante de entrada es una cascada sin nombre."""
        src = open(os.path.join(SCRIPTS, "render_plan.py"), encoding="utf-8").read()
        crudos = re.findall(r'at\.get\(f"(?:item|card|bar|res)\{i\}",[^)\n]*i \* 0\.\d+', src)
        self.assertEqual(crudos, [], f"cascadas a mano: {crudos[:3]}")


if __name__ == "__main__":
    unittest.main()
