#!/usr/bin/env python3
"""Tests de `quieto` y `ocupacion` en medir_animacion.py.

Dos huecos del medidor que dejaban pasar el video que se ve mal:

1. `quieto`: cuadro congelado (nada se mueve en toda la imagen, checklist-qa.md)
   medido SIN la influencia del grano. Medido en el video real del catalogo
   (H.264 decodificado): el piso de diff por cuadro entero es ~0.42 niveles
   (percentil 5), por encima de FROZEN_DIFF (0.35), asi que una diferencia de
   cuadro entero no distingue un congelado de un grano. El grano es de media
   cero: promediado por bloque desaparece; el movimiento no.
2. `ocupacion`: fraccion de la zona segura que cubre la caja de contenido. Una
   banda chica en un lienzo enorme no la veia ninguna metrica.

Run with: python3 -m pytest -q -p no:cacheprovider _tests/test_medir_animacion_quieto.py
"""

import os
import sys
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, os.path.join(SCRIPTS, "ffmpeg_tools"))

import auto_qa as QA  # noqa: E402
import medir_animacion as M  # noqa: E402

FPS = 30
DUR = 4.0
ALTO, ANCHO = 320, 180              # escala de analisis de un 1080x1920
CAJA = (151, 192, 929, 1498)        # zona segura 9:16 a 1080 (render_plan.SAFE)


def _textura(alto, ancho, semilla=1):
    """Contenido con textura (tinta sobre fondo): desvio por bloque > TEXTURA."""
    rng = np.random.default_rng(semilla)
    return np.where(rng.random((alto, ancho)) > 0.5, 230.0, 20.0).astype(np.float32)


def _fondo():
    return np.full((ALTO, ANCHO), 12.0, np.float32)


def _grano(F, semilla=7):
    """Grano temporal de media cero como el del MP4 decodificado (entero, ±1)."""
    rng = np.random.default_rng(semilla)
    return np.clip(F + rng.integers(-1, 2, size=F.shape), 0, 255).astype(np.float32)


def _quieta(con_grano):
    cuadro = _fondo()
    cuadro[120:200, 40:140] = _textura(80, 100)
    F = np.repeat(cuadro[None], int(DUR * FPS), axis=0)
    return _grano(F) if con_grano else F


def _movil():
    """Un bloque con textura que cruza el cuadro a 2 px/frame (60 px/s de analisis)."""
    blq = _textura(40, 40)
    F = []
    for i in range(int(DUR * FPS)):
        c = _fondo()
        y = 20 + (i * 2) % (ALTO - 80)
        c[y:y + 40, 60:100] = blq
        F.append(c)
    return _grano(np.stack(F))


def _congelado_en_medio(con_grano):
    """Se mueve 1 s, se congela 2 s, vuelve a moverse 1 s (no es el cierre)."""
    m, q = _movil(), _quieta(con_grano)
    if not con_grano:
        m = np.round(m)
    return np.concatenate([m[:30], q[30:90], m[90:]])


class Quietud(unittest.TestCase):
    def test_el_grano_tapa_el_congelado_a_la_diff_de_cuadro_entero(self):
        """Premisa medida: con grano la diff de cuadro entero supera FROZEN_DIFF."""
        F = _quieta(True)
        self.assertGreater(float(np.abs(np.diff(F, axis=0)).mean()), QA.FROZEN_DIFF)

    def test_quieta_con_grano_es_quieto(self):
        q = M.quietud(_congelado_en_medio(True), FPS, DUR)
        self.assertGreater(q["quieto"], 0.5)
        self.assertGreaterEqual(q["quieto_max"], 1.5)

    def test_misma_respuesta_con_y_sin_grano(self):
        """Una sola ruta: lo compuesto (sin grano) y lo decodificado dan lo mismo."""
        a = M.quietud(_congelado_en_medio(True), FPS, DUR)
        b = M.quietud(_congelado_en_medio(False), FPS, DUR)
        self.assertGreater(a["quieto_max"], 0)
        self.assertEqual(a["quieto"], b["quieto"])
        self.assertEqual(a["quieto_max"], b["quieto_max"])

    def test_un_bloque_que_se_mueve_no_es_quieto(self):
        q = M.quietud(_movil(), FPS, DUR)
        self.assertEqual(q["quieto"], 0.0)
        self.assertEqual(q["quieto_max"], 0.0)

    def test_el_congelado_final_es_el_cierre_no_un_defecto(self):
        """Un cuadro que se queda quieto HASTA el final es el CTA de cierre
        (checklist-qa.md: ningun hold > 0.6 s salvo el CTA final)."""
        F = np.concatenate([_movil()[:60], _quieta(True)[60:]])
        q = M.quietud(F, FPS, DUR)
        self.assertEqual(q["quieto_max"], 0.0)

    def test_metricas_reporta_quieto_y_ocupacion(self):
        m = M.metricas(_quieta(True), FPS, DUR, caja=CAJA, k_=ANCHO / 1080)
        for clave in ("quieto", "quieto_max", "ocupacion"):
            self.assertIn(clave, m)


class Ocupacion(unittest.TestCase):
    def test_banda_chica_ocupa_poco(self):
        c = _fondo()
        c[150:170, 60:120] = _textura(20, 60)
        o = M.ocupacion(np.repeat(c[None], 8, axis=0), CAJA)
        self.assertLess(o, M.OCUPACION_MIN)

    def test_lienzo_lleno_ocupa_casi_todo(self):
        c = _fondo()
        c[32:250, 25:155] = _textura(218, 130)
        o = M.ocupacion(np.repeat(c[None], 8, axis=0), CAJA)
        self.assertGreater(o, 0.8)

    def test_lo_que_queda_fuera_de_la_zona_segura_no_cuenta(self):
        c = _fondo()
        c[0:30, :] = _textura(30, ANCHO)          # cabecera sobre la zona segura
        o = M.ocupacion(np.repeat(c[None], 8, axis=0), CAJA)
        self.assertEqual(o, 0.0)


class Nota(unittest.TestCase):
    BASE = {"pops": [], "tirones": 0, "arranques": [], "muerto": 0.0, "densidad": 1.0,
            "letra_min": 40, "zona": 1.0, "quieto": 0.0, "ocupacion": 0.6}

    def test_quieto_penaliza(self):
        self.assertLess(M.nota(dict(self.BASE, quieto=0.4)), M.nota(self.BASE))

    def test_ocupacion_baja_penaliza(self):
        self.assertLess(M.nota(dict(self.BASE, ocupacion=0.05)), M.nota(self.BASE))

    def test_sin_las_claves_nuevas_no_penaliza(self):
        viejo = {k: v for k, v in self.BASE.items() if k not in ("quieto", "ocupacion")}
        self.assertEqual(M.nota(viejo), 100.0)


if __name__ == "__main__":
    unittest.main()
