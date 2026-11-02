#!/usr/bin/env python3
"""Tests de la marca como fondo que crece y se encoge (la apertura).

La apertura dibuja detras del titular un fondo que nace de un punto, crece y
se encoge con el cambio de titular. Ese fondo es la MARCA del pack (el
isotipo) cuando la marca lo trae; sin isotipo, cae al blob organico de siempre
(el gesto no depende de que la marca tenga isotipo).

Run with: python3 -m unittest discover -s SKILL/scripts/_tests
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
BASE = os.path.dirname(SCRIPTS)
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, os.path.join(SCRIPTS, "ffmpeg_tools"))

import numpy as np  # noqa: E402
import render_plan as R  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

PACK = os.path.join(BASE, "brand", "dragonjar.json")


class MarcaFondo(unittest.TestCase):

    def setUp(self):
        self._guardado = (R.ISOTIPO, R.ACENTO, R.TRANSICIONES)
        R.aplicar_brand(PACK)
        R.formato(1080, 1920)
        self.ctx = R.Ctx()

    def tearDown(self):
        R.ISOTIPO, R.ACENTO, R.TRANSICIONES = self._guardado

    def _capa(self):
        return Image.new("RGBA", (R.W, R.H), (0, 0, 0, 0))

    def _pixeles(self, capa):
        return int((np.asarray(capa)[..., 3] > 20).sum())

    # ── la primitiva ──────────────────────────────────────────────────────
    def test_sin_isotipo_no_dibuja_y_avisa(self):
        """Sin isotipo la primitiva lo dice: el que llama cae al blob."""
        self.ctx.iso = None
        capa = self._capa()
        drew = R.marca_fondo(self.ctx, capa, R.W / 2, R.H * 0.44, 400, 1.0, 0.0, 0.7)
        self.assertFalse(drew, "sin isotipo tiene que avisar para que caiga el blob")
        self.assertEqual(capa.getbbox(), None, "no debe dibujar nada sin isotipo")

    def test_con_isotipo_dibuja_la_marca(self):
        """Con isotipo, dibuja la silueta de la marca (no un rectángulo)."""
        if self.ctx.iso is None:
            self.skipTest("el pack no trae isotipo")
        capa = self._capa()
        drew = R.marca_fondo(self.ctx, capa, R.W / 2, R.H * 0.44, 400, 1.0, 0.0, 0.7)
        self.assertTrue(drew)
        caja = capa.getbbox()
        self.assertIsNotNone(caja, "la marca tiene que dibujar algo")
        # una silueta de marca no es un rectángulo: ocupa menos que su caja
        w, h = caja[2] - caja[0], caja[3] - caja[1]
        self.assertLess(self._pixeles(capa), 0.75 * w * h,
                        "la marca esta llenando su caja entera: no es una silueta")

    def test_la_marca_crece_y_se_encoge(self):
        """El gesto es el de siempre: nace de un punto y se encoge."""
        if self.ctx.iso is None:
            self.skipTest("el pack no trae isotipo")
        areas = []
        for t in (0.05, 0.35, 0.7, 1.2):
            capa = self._capa()
            R.marca_fondo(self.ctx, capa, R.W / 2, R.H * 0.44, 400, t, 0.0, 0.7)
            areas.append(self._pixeles(capa))
        self.assertLess(areas[0], areas[2], "la marca tiene que CRECER al entrar")
        self.assertGreater(areas[1], areas[0], "y seguir creciendo despues")

    def test_la_marca_no_tapa_el_titular(self):
        """La marca es FONDO: su silueta no puede llenar la caja del titular."""
        if self.ctx.iso is None:
            self.skipTest("el pack no trae isotipo")
        capa = self._capa()
        R.marca_fondo(self.ctx, capa, R.W / 2, R.H * 0.44, 400, 1.0, 0.0, 0.7)
        # el titular va centrado en H*0.44: la marca esta ahi detras, pero
        # DEBE quedar sitio para el texto (no un bloque opaco).
        self.assertLess(self._pixeles(capa) / (R.W * R.H), 0.12,
                        "la marca ocupa demasiado: taparia el titular")

    # ── la escena ──────────────────────────────────────────────────────────
    def _apertura(self):
        return {"tipo": "apertura", "from": 0.0, "to": 5.0,
                "at": {"cambio": 2.0, "p1": [0.2, 0.6, 1.0], "p2": [2.1, 2.45, 2.8]},
                "texto1": ["Un atacante", "ya lo *probó*"],
                "texto2": ["Tu web", "no lo *sabe*"]}

    def _poligonos(self):
        """Los poligonos que dibuja la escena (el blob es UN poligono)."""
        vista = []
        orig = ImageDraw.ImageDraw.polygon

        def espia(self, xy, *a, **k):
            vista.append(k.get("fill"))
            return orig(self, xy, *a, **k)
        return vista, espia, orig

    def test_la_apertura_con_isotipo_no_dibuja_el_blob(self):
        """Con la marca del pack, el fondo es la marca: el blob no se dibuja."""
        ctx = R.Ctx()
        vista, espia, orig = self._poligonos()
        ImageDraw.ImageDraw.polygon = espia
        try:
            R.pintar(ctx, self._apertura(), 1.2)
        finally:
            ImageDraw.ImageDraw.polygon = orig
        blobs = [f for f in vista if isinstance(f, tuple) and len(f) == 4 and f[3] == 58]
        self.assertEqual(blobs, [], "con isotipo del pack el blob no se dibuja")

    def test_la_apertura_sin_isotipo_cae_al_blob(self):
        """Sin marca, el gesto sigue siendo el mismo (el blob de siempre)."""
        R.ISOTIPO = None
        ctx = R.Ctx()
        vista, espia, orig = self._poligonos()
        ImageDraw.ImageDraw.polygon = espia
        try:
            R.pintar(ctx, self._apertura(), 1.2)
        finally:
            ImageDraw.ImageDraw.polygon = orig
        blobs = [f for f in vista if isinstance(f, tuple) and len(f) == 4 and f[3] == 58]
        self.assertTrue(blobs, "sin isotipo tiene que caer al blob organico")


if __name__ == "__main__":
    unittest.main()
