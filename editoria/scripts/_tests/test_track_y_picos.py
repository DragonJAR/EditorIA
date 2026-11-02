#!/usr/bin/env python3
"""Tests del resorte multi-destino (track) y de los picos transitorios.

Cubre: track() como funcion pura del tiempo, su comportamiento con cambios
encadenados y solapados, el overshoot de los parametros del cursor, y la
deteccion de picos transitorios en la grilla de beats.

Run with: python3 -m unittest discover -s SKILL/scripts/_tests
"""

import importlib.util
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)


def _cargar(nombre, ruta):
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rp = _cargar("rp", os.path.join(SCRIPTS, "render_plan.py"))
bg = _cargar("bg", os.path.join(SCRIPTS, "beat_grid.py"))


class TestTrack(unittest.TestCase):
    PARADAS = [(0.0, 0.0), (1.0, 1.0), (3.0, 1.0), (4.0, 0.0)]

    def test_sin_paradas_devuelve_cero(self):
        self.assertEqual(rp.track(1.0, []), 0.0)

    def test_antes_del_primer_cambio_mantiene_el_valor(self):
        self.assertAlmostEqual(rp.track(-1.0, self.PARADAS), 0.0, places=6)
        self.assertAlmostEqual(rp.track(0.5, self.PARADAS), 0.0, places=6)

    def test_llega_al_objetivo_y_lo_sostiene(self):
        self.assertAlmostEqual(rp.track(1.6, self.PARADAS), 1.0, places=2)
        self.assertAlmostEqual(rp.track(2.9, self.PARADAS), 1.0, places=3)

    def test_es_funcion_pura_del_tiempo(self):
        # el frame 812 se pinta sin simular los 811 anteriores
        for t in (0.3, 1.4, 2.7, 3.9, 6.0):
            self.assertEqual(rp.track(t, self.PARADAS), rp.track(t, self.PARADAS))

    def test_overshoot_leve_y_asentamiento(self):
        pico = max(rp.track(i / 240.0, [(0.0, 0.0), (1.0, 1.0)]) for i in range(240, 1200))
        self.assertGreater(pico, 1.0)              # se pasa un pelo
        self.assertLess(pico, 1.03)                # pero casi imperceptible
        self.assertAlmostEqual(rp.track(1.6, [(0.0, 0.0), (1.0, 1.0)]), 1.0, places=2)

    def test_tramos_solapados_no_frenan_en_seco(self):
        # dos cambios separados por 0.1 s: el valor no debe quedarse quieto
        paradas = [(0.0, 0.0), (1.0, 1.0), (1.1, 0.0)]
        mitad = rp.track(1.05, paradas)
        self.assertGreater(mitad, 0.0)             # ya se movio
        self.assertLess(mitad, 1.0)

    def test_cambio_de_signo_es_continuo(self):
        # al invertir el objetivo el valor baja sin saltar: sigue siendo continuo
        paradas = [(0.0, 0.0), (1.0, 1.0), (2.0, 0.0)]
        antes = rp.track(1.95, paradas)
        despues = rp.track(2.05, paradas)
        self.assertLess(despues, antes)
        self.assertGreater(despues, 0.0)
        self.assertLess(abs(despues - antes), 0.35)   # sin salto


class TestPicos(unittest.TestCase):
    def _env(self):
        if bg.np is None:
            self.skipTest("numpy no disponible")
        import numpy as np
        fps = bg.FPS
        n = int(fps * 4)
        on = np.zeros(n, dtype=float)
        rms = np.zeros(n, dtype=float)
        for t in (0.5, 1.5, 2.5):                 # tres golpes claros
            i = int(t * fps)
            on[i] = 1.0
            on[i + 1] = 0.0
            rms[i] = 0.5
        return on, rms, 4.0

    def test_detecta_los_impactos(self):
        on, rms, dur = self._env()
        picos = bg.picos_transitorios(on, rms, dur, delta=1.0, wait_ms=100)
        instantes = [round(p["t"], 2) for p in picos]
        self.assertTrue(instantes, "deberia detectar picos")
        for t in (0.5, 1.5, 2.5):
            self.assertTrue(any(abs(i - t) < 0.06 for i in instantes),
                            f"falta el pico de {t}s: {instantes}")

    def test_sin_energia_no_hay_picos(self):
        on, rms, dur = self._env()
        picos = bg.picos_transitorios(on * 0, rms * 0, dur, delta=1.0, wait_ms=100)
        self.assertEqual(picos, [])

    def test_espera_minima_entre_picos(self):
        # mas silencio minimo -> menos picos: la espera es un filtro real
        on, rms, dur = self._env()
        muchos = bg.picos_transitorios(on, rms, dur, delta=1.0, wait_ms=50)
        pocos = bg.picos_transitorios(on, rms, dur, delta=1.0, wait_ms=3000)
        self.assertLess(len(pocos), len(muchos))
        self.assertLessEqual(len(pocos), 1)


if __name__ == "__main__":
    unittest.main()
