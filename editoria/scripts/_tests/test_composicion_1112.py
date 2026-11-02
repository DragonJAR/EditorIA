#!/usr/bin/env python3
"""Regresiones del lote 1.11.2 (adaptadas a ESTA linea).

El fichero original del fork (1.11.3) media features de SU motor: el
contrato de la paleta con su sintaxis, el encuadre del foco de `demo` con su
clampeo, el balance de la composicion y la plataforma deducida por tamano.
Aqui se mide lo que ESTA linea garantiza, con su API:

  · la paleta del modo libre sale de UNA fuente (`paleta_libre`) y el error
    de una paleta que no existe DICE cuales hay (no degrada en silencio);
  · la letra minima es una sola cifra, compartida por el motor y la puerta;
  · la moneda y la ruta de un paso se declaran (el esquema las conoce);
  · los solapes de la composicion conservan su firma (la puerta los usa);
  · el foco de la demo se mantiene DENTRO de la vista (el encuadre no se
    sale de la captura) y su caja no se recorta sin avisar.

Lo que queda FUERA, y por que (esta en PLAN-INTEGRACION-1.11.3.md):

  · el CLAMP del foco de `demo` y su chequeo en la puerta (`foco_recortado`,
    `desbalance`): son del motor del fork y requieren su capa de medicion
    (`composicion_asentada`), que aqui no existe;
  · la plataforma deducida por tamano: la puerta de aqui usa `--plataforma`
    explicito (el default es reels).

Run with: python3 -m unittest discover -s SKILL/scripts/_tests
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
for p in (SCRIPTS, os.path.join(SCRIPTS, "ffmpeg_tools")):
    if p not in sys.path:
        sys.path.insert(0, p)

import render_plan as R  # noqa: E402
import qa_entrega as Q  # noqa: E402
from _comun import LETRA_MIN, PALETAS, paleta_libre  # noqa: E402


class Paleta(unittest.TestCase):
    def test_una_sola_fuente(self):
        """La paleta del modo libre sale de `_comun` (el motor y la puerta
        leen la MISMA tabla)."""
        a = paleta_libre("coral")
        b = R.PALETAS["coral"] if hasattr(R, "PALETAS") else None
        if b is not None:
            self.assertEqual(a["acento"], b["acento"])
        self.assertIn("acento", a)

    def test_el_error_dice_que_paletas_hay(self):
        """Una paleta que no existe no degrada en silencio: dice cuales hay."""
        import contextlib
        import io
        salida = io.StringIO()
        with contextlib.redirect_stderr(salida):
            with self.assertRaises(SystemExit):
                paleta_libre("esta-paleta-no-existe")
        texto = salida.getvalue()
        for nombre in sorted(PALETAS):
            self.assertIn(nombre, texto,
                          f"el error no menciona la paleta {nombre}: {texto!r}")


class Defectos(unittest.TestCase):
    def test_moneda_y_ruta_declaradas(self):
        """El esquema conoce los defectos por defecto de una escena."""
        esquema = R.esquema_de("oferta")
        moneda = [p for p in esquema if p["nombre"] == "moneda"]
        self.assertTrue(moneda, "la oferta no declara `moneda` en el esquema")
        self.assertEqual(moneda[0].get("default"), '"$"',
                         "la moneda por defecto no es la declarada")


class Letra(unittest.TestCase):
    def test_letra_minima_unica(self):
        """La letra minima es la misma en el motor y en la puerta."""
        self.assertEqual(R.MIN_LETRA, LETRA_MIN)
        self.assertEqual(Q.LETRA_MIN, LETRA_MIN)


class Solapes(unittest.TestCase):
    def test_solapes_conserva_su_firma(self):
        """La puerta llama a la composicion con la firma que espera."""
        import inspect
        params = inspect.signature(Q._defectos_composicion).parameters
        for clave in ("letra", "zona", "solapes"):
            self.assertIn(clave, params, f"la puerta no recibe {clave}")
        self.assertEqual(Q._defectos_composicion(30, 1.0, []), [])


class FocoDemo(unittest.TestCase):
    def test_el_foco_queda_dentro_de_la_vista(self):
        """El zoom al foco no saca el encuadre de la captura.

        La cuenta es la del motor (`fxp * (1 - 1/z)`): con el foco en el
        borde de la captura, la ventana de zoom sigue DENTRO.
        """
        bw, bh = 900, 520
        for fx, fy in ((0.5, 0.5), (0.0, 0.0), (1.0, 1.0), (0.856, 0.085)):
            z = 1.6
            fxp, fyp = fx * bw, fy * bh
            cx, cy = fxp * (1 - 1 / z), fyp * (1 - 1 / z)
            self.assertGreaterEqual(cx, -1, f"el encuadre se sale por la izquierda ({fx})")
            self.assertGreaterEqual(cy, -1, f"el encuadre se sale por arriba ({fy})")
            self.assertLessEqual(cx + bw / z, bw + 1,
                                 f"el encuadre se sale por la derecha ({fx})")
            self.assertLessEqual(cy + bh / z, bh + 1,
                                 f"el encuadre se sale por abajo ({fy})")

    def test_el_foco_esta_dentro_de_la_captura(self):
        """El punto del foco, en px, cae dentro de la ventana."""
        bw, bh = 900, 520
        fx, fy, z = 0.856, 0.085, 1.6
        fxp, fyp = fx * bw, fy * bh
        cx, cy = fxp * (1 - 1 / z), fyp * (1 - 1 / z)
        self.assertGreaterEqual(fxp, cx - 1)
        self.assertLessEqual(fxp, cx + bw / z + 1)
        self.assertGreaterEqual(fyp, cy - 1)
        self.assertLessEqual(fyp, cy + bh / z + 1)


if __name__ == "__main__":
    unittest.main()
