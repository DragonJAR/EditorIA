#!/usr/bin/env python3
"""Cierre de la pasada de diseño (familia W-C): R7 por escena y los restos.

Cada clase fija UNA causa, medida sobre el motor o sobre el frame:

- COPY x2: el estrés de copy de validate_skill duplica SOLO el texto que el
  espectador lee (`medir_animacion.copy_x2`, con los campos token del motor
  `render_plan.CAMPOS_TOKEN`): duplicar `colores: "serie"` a "serie serie"
  terminaba el proceso (die -> SystemExit) y el bloque de humo de escenas
  (copy x2, solapes) no corría nunca.
- PACK SIN FUGA: `aplicar_brand` fija el solape de su regla en los DOS
  sentidos; un pack `corte_seco` dejaba SOLAPE=0.25 instalado para el resto
  del proceso y un test de prosa fallaba según el orden.

Run: python3 -m pytest -q -p no:cacheprovider _tests/test_cierre_impecable.py
"""

import copy
import json
import os
import sys
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
BASE = os.path.dirname(SCRIPTS)
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, os.path.join(SCRIPTS, "ffmpeg_tools"))


def _muestras():
    with open(os.path.join(SCRIPTS, "escenas_muestra.json"), encoding="utf-8") as fh:
        return json.load(fh)["escenas"]


def _muestra(tipo):
    e = copy.deepcopy(_muestras()[tipo])
    e["tipo"] = tipo
    return e


def _motor(ancho=1080, alto=1920):
    import render_plan as R
    R.formato(ancho, alto)
    R.aplicar_globales({"escenas": []})
    R._ESCALA.clear()
    R._CAMARA["activa"] = False
    return R


class TestCopyX2(unittest.TestCase):
    """El bloque de humo de validate_skill recorre las 45 escenas con copy x2."""

    def test_los_campos_token_no_se_duplican(self):
        import medir_animacion as M
        import render_plan as R
        e = M.copy_x2(R, _muestra("subrayado"))
        self.assertEqual(e["colores"], "serie")
        t0 = _muestra("subrayado")["texto"]
        self.assertEqual(e["texto"], f"{t0} {t0}")
        o = M.copy_x2(R, _muestra("oferta"))
        self.assertEqual((o["moneda"], o["miles"], o["decimal"]), ("$", ".", ","))

    def test_el_humo_completa_las_escenas_en_los_dos_formatos(self):
        import medir_animacion as M
        caidas = []
        for ancho, alto in ((1080, 1920), (1920, 1080)):
            R = _motor(ancho, alto)
            ctx = R.Ctx()
            for nombre in R.SCENES:
                e = M.copy_x2(R, _muestra(nombre))
                if "imagen" in e:
                    e["imagen"] = None
                R._ESCALA.clear()
                try:
                    # el instante asentado del bloque de solapes (80 %)
                    R.componer(ctx, [e], e["to"] + 5, e["from"] + (e["to"] - e["from"]) * 0.8, set())
                except BaseException as ex:   # noqa: B036 - un die() es SystemExit
                    caidas.append(f"{nombre} {ancho}x{alto}: {type(ex).__name__}: {ex}")
        self.assertEqual(caidas, [], "el humo de copy x2 se corta en una escena")


class TestPackSinFuga(unittest.TestCase):
    """Un pack `corte_seco` no deja su solape instalado para lo que sigue."""

    def test_volver_sin_pack_restaura_el_solape(self):
        import render_plan as R
        base = (R.SOLAPE, R.SOLAPE_PRE)
        try:
            R.aplicar_brand(os.path.join(BASE, "brand", "dragonjar.json"))
            self.assertEqual((R.SOLAPE, R.SOLAPE_PRE), (R.SOLAPE_SECO, R.SOLAPE_PRE_SECO))
        finally:
            R.aplicar_brand(None)
        self.assertEqual((R.SOLAPE, R.SOLAPE_PRE), base)
        self.assertEqual(R.TRANSICIONES, "libre")


if __name__ == "__main__":
    unittest.main()
