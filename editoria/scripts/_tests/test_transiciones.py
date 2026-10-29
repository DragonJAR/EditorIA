#!/usr/bin/env python3
"""Tests de las transiciones entre escenas: ni hueco vacío ni fantasma.

QUE PROTEGE

Dos defectos medidos en el catálogo (auditoría fase 2, trans_zoom.png):

  · IRIS / MANCHA abrían sobre FONDO: `componer` pintaba la escena que sale
    en su instante real y esa escena ya se estaba yendo por `capa_salida`,
    así que fuera de la máscara no quedaba nada (0.3-0.5 s de lienzo vacío).
    Con una transición de máscara la SALIDA la hace la máscara: la escena
    que sale se pinta en su estado sin fundir (`instante_saliente`).
  · El CORTE por defecto dejaba la escena saliente al ~12 % de alfa 0.3 s
    después del corte, en el mismo centro: un fantasma debajo del texto de
    la siguiente. `capa_salida` llega a ~0 antes del primer elemento que
    entra (SOLAPE).

Run with: python3 -m pytest -q -p no:cacheprovider _tests/test_transiciones.py
"""

import copy
import json
import os
import sys
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, os.path.join(SCRIPTS, "ffmpeg_tools"))


def _muestra(tipo, t0, **extra):
    """La escena de muestra desplazada para empezar en t0."""
    with open(os.path.join(SCRIPTS, "escenas_muestra.json"), encoding="utf-8") as fh:
        e = copy.deepcopy(json.load(fh)["escenas"][tipo])
    e["tipo"] = tipo
    d = t0 - e["from"]
    e["from"], e["to"] = t0, e["to"] + d
    if "at" in e:
        e["at"] = {k: v + d for k, v in e["at"].items()}
    e.update(extra)
    return e


class TestTransiciones(unittest.TestCase):
    def setUp(self):
        import render_plan as R
        R.formato(1080, 1920)
        R.aplicar_globales({"escenas": []})
        R._ESCALA.clear()
        self.R = R
        self.ctx = R.Ctx()
        self._alfa = R.ALFA
        R.ALFA = True   # el cuadro sin fondo: el alfa ES el contenido

    def tearDown(self):
        self.R.ALFA = self._alfa

    def _par(self, transicion=None):
        R = self.R
        e1 = R.completar_escena(_muestra("quote", 0.0), 0)
        extra = {"transicion": transicion} if transicion else {}
        e2 = R.completar_escena(_muestra("stats", e1["to"], **extra), 1)
        return e1, e2

    def _alfa_de(self, img):
        return np.asarray(img.split()[3], np.float32)

    def test_la_mascara_no_abre_sobre_fondo(self):
        """A mitad de un iris o una mancha, lo que la máscara aún NO cubre
        sigue siendo la escena que sale, entera (no fondo)."""
        R = self.R
        for tr in ("iris", "mancha"):
            with self.subTest(transicion=tr):
                e1, e2 = self._par(tr)
                R._ESCALA.clear()
                antes = self._alfa_de(R.componer(self.ctx, [e1, e2], e2["to"],
                                                 e1["to"] - R.SOLAPE_PRE, {1}))
                fx, fy = e2.get("transicionX", 0.5), e2.get("transicionY",
                                                         0.38 if tr == "iris" else 0.45)
                fn = R.iris_mask if tr == "iris" else R.mancha_mask
                medidos = 0
                for dt in (0.1, 0.2, 0.3, 0.45):   # mientras la máscara aún no lo cubre todo
                    t = e1["to"] + dt
                    fuera = np.asarray(fn(self.ctx, t, e2["from"], 0.9, fx, fy)) < 128
                    if antes[fuera].sum() < 0.05 * antes.sum():
                        continue
                    medidos += 1
                    ahora = self._alfa_de(R.componer(self.ctx, [e1, e2], e2["to"], t, {1}))
                    quedan = ahora[fuera].sum() / antes[fuera].sum()
                    self.assertGreater(quedan, 0.8,
                                       f"{tr} +{dt}s: fuera de la máscara solo queda el "
                                       f"{quedan:.0%} de la escena que sale (abre sobre fondo)")
                self.assertTrue(medidos, f"{tr}: la máscara lo cubrió todo antes de medir")

    def test_la_disolucion_no_se_queda_vacia_ni_corta_la_salida(self):
        """La disolución cruza las dos: a mitad hay contenido de la que sale y
        al terminar ya no queda nada de ella (sin desaparición de golpe)."""
        R = self.R
        e1, e2 = self._par("dissolve")
        R._ESCALA.clear()
        cob = lambda tc: float(self._alfa_de(R.componer(  # noqa: E731
            self.ctx, [e1, e2], e2["to"], tc, set())).mean())
        antes = cob(e1["to"] - R.SOLAPE_PRE)
        self.assertGreater(cob(e1["to"] + R.SOLAPE_DISSOLVE / 2), 0.3 * antes,
                           "la disolución abre sobre fondo")
        sale = R.pintar(self.ctx, e1, R.instante_saliente(e1, e1["to"] + R.SOLAPE_DISSOLVE))
        self.assertGreater(float(self._alfa_de(sale).mean()), 0.8 * antes,
                           "la escena que sale ya venía fundida: la salida la hace la transición")

    def test_el_corte_no_deja_fantasma(self):
        """0.3 s después de un corte por defecto, la escena que sale ya no se
        ve (< 2 % de su alfa): no hay fantasma bajo el texto de la siguiente."""
        R = self.R
        e1, _ = self._par()
        lleno = float(self._alfa_de(R.pintar(self.ctx, e1, e1["to"] - 0.6)).mean())
        resto = float(self._alfa_de(R.pintar(self.ctx, e1, e1["to"] + 0.3)).mean())
        self.assertLess(resto / lleno, 0.02,
                        f"fantasma: la escena que sale sigue al {resto / lleno:.0%} "
                        "0.3 s después del corte")


if __name__ == "__main__":
    unittest.main()
