#!/usr/bin/env python3
"""Tests de medir_silencios.py con audio sintético (sin ffmpeg para las funciones puras)."""
import json
import math
import os
import struct
import subprocess
import sys
import tempfile
import unittest
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)
import medir_silencios as MS  # noqa: E402

SR = 8000


def tono(huecos, dur, amp=0.4, vuelve=1.0):
    """Seno de `dur` s con silencios en `huecos` [(ini, fin)]; tras cada hueco
    el sonido vuelve a `amp*vuelve` durante 0.5 s."""
    out = []
    for n in range(int(dur * SR)):
        t = n / SR
        a = amp
        if any(i <= t < f for i, f in huecos):
            a = 0.0
        for _, f in huecos:
            if f <= t < f + 0.5:
                a = amp * vuelve
        out.append(a * math.sin(2 * math.pi * 330 * t))
    return out


def a_wav(muestras, ruta):
    with wave.open(ruta, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, v)) * 32767)) for v in muestras))


class TestPuras(unittest.TestCase):
    def test_encuentra_dos_silencios_interiores(self):
        niv = MS.niveles_db(tono([(4.0, 5.0), (9.0, 9.6)], 14), SR)
        lista, ref = MS.silencios(niv)
        self.assertEqual(len(lista), 2)
        self.assertAlmostEqual(lista[0]["inicio"], 4.0, delta=0.1)
        self.assertAlmostEqual(lista[0]["duracion"], 1.0, delta=0.1)
        self.assertGreater(lista[0]["vuelve_db"], -3.0)      # vuelve a la referencia
        self.assertLess(ref, 0)

    def test_arranque_y_cierre_no_cuentan(self):
        niv = MS.niveles_db(tono([(0.0, 0.45), (13.5, 14.0)], 14), SR)
        self.assertEqual(MS.silencios(niv)[0], [])

    def test_hueco_corto_no_cuenta(self):
        self.assertEqual(MS.silencios(MS.niveles_db(tono([(5.0, 5.2)], 12), SR))[0], [])

    def test_retorno_debil_se_ve(self):
        niv = MS.niveles_db(tono([(5.0, 6.0)], 12, vuelve=0.15), SR)
        self.assertLess(MS.silencios(niv)[0][0]["vuelve_db"], -6.0)

    def test_todo_silencio_no_tiene_referencia(self):
        self.assertEqual(MS.silencios(MS.niveles_db([0.0] * SR * 4, SR)), ([], None))

    def test_requeridos(self):
        self.assertEqual((MS.requeridos(15), MS.requeridos(20), MS.requeridos(45)), (1, 2, 2))


class TestCLI(unittest.TestCase):
    def correr(self, muestras, *args):
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "m.wav")
            a_wav(muestras, ruta)
            return subprocess.run([sys.executable, os.path.join(SCRIPTS, "medir_silencios.py"), ruta, *args],
                                  capture_output=True, text=True)

    def test_suficientes(self):
        r = self.correr(tono([(4.0, 5.0), (9.0, 9.8)], 14), "--exigir", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        d = json.loads(r.stdout)
        self.assertTrue(d["ok"])
        self.assertEqual(len(d["silencios"]), 2)

    def test_pieza_larga_con_uno_no_alcanza(self):
        r = self.correr(tono([(10.0, 11.0)], 24), "--exigir")
        self.assertEqual(r.returncode, 1)
        self.assertIn("AVISO silencios: 1 de 2", r.stdout)

    def test_sin_exigir_siempre_sale_0(self):
        self.assertEqual(self.correr(tono([], 24)).returncode, 0)

    def test_errores_claros(self):
        r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "medir_silencios.py"), "/no/existe.wav"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        self.assertNotIn("Traceback", r.stderr)
        self.assertEqual(self.correr(tono([], 12), "--caida", "0").returncode, 1)
        self.assertEqual(self.correr(tono([], 1)).returncode, 1)


if __name__ == "__main__":
    unittest.main()
