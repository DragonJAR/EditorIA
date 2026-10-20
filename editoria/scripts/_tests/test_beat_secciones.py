#!/usr/bin/env python3
"""Tests for beat_grid.secciones — song sections by energy for music-driven pieces.

Covers: one section for flat energy, a loud middle detected as "pico" with
denser suggested cuts, isolated spikes not splitting a phrase, the
beat_file.py-compatible schema, and the end-to-end analysis of a synthetic
quiet-loud-quiet track.

Run with: python3 -m unittest discover -s SKILL/scripts/_tests
"""

import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import beat_grid as BG  # noqa: E402


def compases(dbs, compas_s=2.0):
    return [{"compas": i, "t": i * compas_s, "db": db} for i, db in enumerate(dbs)]


class TestSecciones(unittest.TestCase):
    def test_energia_plana_es_una_seccion(self):
        s = BG.secciones(compases([-20.0] * 16), 32.0)
        self.assertEqual(len(s), 1)
        self.assertEqual(s[0]["energia"], "media")
        self.assertEqual((s[0]["inicio"], s[0]["fin"]), (0.0, 32.0))

    def test_pico_en_el_medio(self):
        s = BG.secciones(compases([-30.0] * 8 + [-12.0] * 8 + [-30.0] * 8), 48.0)
        self.assertEqual([x["rol"] for x in s], ["intro", "pico", "outro"])
        self.assertEqual(s[1]["inicio"], 16.0)
        self.assertLess(s[1]["cortes_cada_beats"], s[0]["cortes_cada_beats"])

    def test_golpe_aislado_no_parte_la_frase(self):
        dbs = [-25.0] * 16
        dbs[5] = -10.0                       # un compás fuerte dentro de una frase
        self.assertEqual(len(BG.secciones(compases(dbs), 32.0)), 1)

    def test_esquema_compatible_con_beat_file(self):
        for x in BG.secciones(compases([-30.0] * 4 + [-10.0] * 4), 16.0):
            for k in ("nombre", "inicio", "fin"):
                self.assertIn(k, x)

    def test_vacio(self):
        self.assertEqual(BG.secciones([], 0.0), [])

    def test_pista_sintetica(self):
        with tempfile.TemporaryDirectory() as d:
            mus = os.path.join(d, "m.wav")
            expr = ("(if(lt(mod(t,0.5),0.06),sin(2*PI*60*t),0)+0.3*sin(2*PI*440*t))"
                    "*(if(between(t,16,32),1,0.12))")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                            f"aevalsrc='{expr}':s=22050:d=48", mus], check=True)
            s = BG.analizar(mus)["secciones"]
        picos = [x for x in s if x["rol"] == "pico"]
        self.assertEqual(len(picos), 1)
        self.assertAlmostEqual(picos[0]["inicio"], 16.0, delta=1.1)
        self.assertAlmostEqual(picos[0]["fin"], 32.0, delta=1.1)


if __name__ == "__main__":
    unittest.main()
