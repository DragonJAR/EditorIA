"""La paleta del modo libre, de UNA fuente (`ffmpeg_tools/_comun.py`).

Sintaxis `"paleta": "<nombre>|#RRGGBB[:claro]"`: un nombre del catálogo o
el color del usuario, en tema oscuro o claro. Lo que no llega al contraste
mínimo se corrige en luminancia y se avisa (nunca un acento ilegible en
silencio). El motor, la auditoría y las ayudas leen de aquí.
"""
import contextlib
import io
import os
import subprocess
import sys
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(AQUI)
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, os.path.join(SCRIPTS, "ffmpeg_tools"))
import _comun as C  # noqa: E402

with contextlib.redirect_stdout(io.StringIO()):
    import render_plan as R  # noqa: E402


class PaletaDelCatalogo(unittest.TestCase):
    def test_paletas_en_oscuro_y_claro(self):
        for k in C.PALETAS:
            for modo in ("", ":claro"):
                v = C.verificar_paleta(C.paleta_libre(k + modo))
                self.assertTrue(v["ok"], f"{k}{modo}: {v}")

    def test_acentos_pasan_sobre_fondo_y_tarjeta(self):
        """El acento es letra de énfasis: 4.5:1 sobre el fondo Y la tarjeta."""
        for k in C.PALETAS:
            t = C.paleta_libre(k)
            for f in (t["negro"], t["gris_superficie"]):
                self.assertGreaterEqual(C.contraste(t["acento"], f), 4.5, k)

    def test_neutros_del_motor_una_vez(self):
        for k in C.PALETAS:
            for tok, v in C.NEUTROS_OSCURO.items():
                self.assertEqual(C.PALETAS[k][tok], v, f"{k}.{tok}")
        self.assertEqual(C.MODOS, ("oscuro", "claro"))

    def test_tema_claro_invierte_fondo_y_tinta(self):
        t = C.paleta_libre("menta:claro")
        self.assertGreater(sum(t["negro"]), sum(t["blanco"]))
        self.assertGreaterEqual(C.contraste(t["acento"], t["negro"]), 4.5)

    def test_modo_desconocido_es_error_claro(self):
        with self.assertRaises(SystemExit):
            with contextlib.redirect_stderr(io.StringIO()):
                C.paleta_libre("menta:sepia")


class ColorDelUsuario(unittest.TestCase):
    def test_hex_es_el_acento(self):
        t = C.paleta_libre("#14C7A0")
        self.assertEqual(t["acento"], (20, 199, 160))
        self.assertEqual(t["negro"], C.NEUTROS_OSCURO["negro"])

    def test_color_ilegible_se_corrige_y_se_avisa(self):
        t, avisos = C.asegurar_contraste(dict(C.NEUTROS_OSCURO, acento=(21, 21, 21)), "test")
        self.assertTrue(avisos)
        self.assertGreaterEqual(C.contraste(t["acento"], t["negro"]), 4.5)
        self.assertGreaterEqual(C.contraste(t["acento"], t["gris_superficie"]), 4.5)
        self.assertGreaterEqual(C.contraste(C.paleta_libre("#151515")["acento"], C.NEUTROS_OSCURO["negro"]), 4.5)

    def test_en_tema_claro_se_oscurece(self):
        t = C.paleta_desde_color("#FFE14D", "claro")   # amarillo sobre crema: se oscurece
        self.assertGreaterEqual(C.contraste(t["acento"], t["negro"]), 4.5)
        self.assertLess(sum(t["acento"]), sum((255, 225, 77)))

    def test_hex_invalido_es_error_claro(self):
        with self.assertRaises(SystemExit):
            with contextlib.redirect_stderr(io.StringIO()):
                C.paleta_libre("#12")

    def test_una_regla_de_luz_para_el_motor(self):
        """El `_legible` del motor y la corrección de la paleta son la MISMA
        cuenta (`_comun._hasta_contraste`): sobre oscuro sube la luz."""
        self.assertEqual(R._legible((40, 40, 160), (10, 10, 10)),
                         C._hasta_contraste((40, 40, 160), (10, 10, 10), 4.5))


class Lectura(unittest.TestCase):
    def test_piso_y_palabras(self):
        self.assertEqual(C.tiempo_de_lectura("Hola"), C.LECTURA_MIN_S)
        seis = "una dos tres cuatro cinco seis siete ocho nueve"
        self.assertEqual(C.tiempo_de_lectura(seis), round(9 / C.PALABRAS_POR_S, 2))
        self.assertEqual(C.tiempo_de_lectura(["una dos", "tres"]), C.LECTURA_MIN_S)


class AyudaUnica(unittest.TestCase):
    def test_render_y_repertorio_citan_la_sintaxis(self):
        cola = C.SINTAXIS_PALETA.split(": ", 1)[1]
        for script in ("render_plan.py", "repertorio.py"):
            r = subprocess.run([sys.executable, os.path.join(SCRIPTS, script), "--help"],
                               capture_output=True, text=True, timeout=60)
            self.assertIn(cola, " ".join(r.stdout.split()), script)

    def test_motor_instala_la_paleta_clara(self):
        with contextlib.redirect_stdout(io.StringIO()):
            R.aplicar_paleta("menta:claro")
        try:
            self.assertGreater(sum(R.NEGRO), sum(R.BLANCO))
            self.assertGreater(sum(R.PANEL), 600)
        finally:
            with contextlib.redirect_stdout(io.StringIO()):
                R.aplicar_paleta("electrico")


if __name__ == "__main__":
    unittest.main()
