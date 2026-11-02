#!/usr/bin/env python3
"""Tests del kit de tiempo para motores HTML (assets/js/tiempo.mjs).

QUE PROTEGE

1. PARIDAD con el motor Python: el resorte, los seis gestos (MOVIMIENTO), las
   curvas y los sub-frames del obturador dan los mismos numeros en JS que en
   render_plan.py. Si alguien cambia un gesto en un lado, el test lo dice: una
   pieza mixta (plan Python + overlay HTML) no puede tener dos fisicas.
2. Funcion pura de t: misma entrada, misma salida, en cualquier orden.
3. Lee sin conversion la rejilla de beat_grid.py y las palabras de alinear.py.

Se salta si no hay Node (capacidad opcional, references/capacidades.md).

Run with: python3 -m unittest discover -s scripts/_tests
"""

import json
import os
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
SKILL = os.path.dirname(SCRIPTS)
MJS = os.path.join(SKILL, "assets", "js", "tiempo.mjs")
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, os.path.join(SCRIPTS, "ffmpeg_tools"))

TIEMPOS = [0.0, 0.01, 0.05, 0.1, 0.17, 0.25, 0.4, 0.66, 1.0, 1.5]


def _node(js):
    r = subprocess.run(["node", "--input-type=module", "-e", js], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise AssertionError(r.stderr)
    return json.loads(r.stdout)


@unittest.skipUnless(shutil.which("node"), "sin node: el kit HTML es capacidad opcional")
class TestTiempoJS(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import render_plan as R
        cls.R = R
        url = "file://" + MJS
        cls.js = _node(f"""
import * as m from {json.dumps(url)};
const T = {json.dumps(TIEMPOS)};
const out = {{
  mov: m.MOVIMIENTO,
  roles: Object.fromEntries(Object.keys(m.MOVIMIENTO).map(r => [r, T.map(t => m.entra(t, 0.05, r))])),
  spring: T.map(t => m.resorte(t, 0.0, 200, 30)),
  curvas: Object.fromEntries(Object.entries(m.curvas).map(([k, f]) => [k, T.map(t => f(t / 1.5))])),
  sub: m.subframes(2.0, 30, 5, 0.5),
  fidx: T.map(t => m.frameIdx(t + 0.5, 30)),
  puro: [m.retarget(0.7, 0, [[0, 10], [0.3, 4]]), m.retarget(0.7, 0, [[0, 10], [0.3, 4]])],
  ret_fin: m.retarget(9, 0, [[0, 10], [0.3, 4], [1, -2]]),
  critico_max: Math.max(...Array.from({{length: 300}}, (_, i) => m.critico(i / 100, 0, 30))),
  grid: (() => {{ const g = m.rejilla({{bpm: 120, beat0: 0.2, compas0: 0.7, picos: [{{t: 1.0, fuerza: 0.8}}]}});
                 return [g.beatAt(1.2), g.tiempoDeBeat(3), g.beatCercano(0.93), g.compasAt(2.8), g.pulso(0.7),
                         g.golpe(1.0), g.golpe(0.99), g.aterriza(2)]; }})(),
  pal: (() => {{ const p = [{{texto: 'ayer', inicio: 0.5, fin: 0.9}}, {{texto: 'Binance', inicio: 1.0, fin: 1.6}}];
                return [m.progresoPalabra(p[1], 1.3), m.palabraEn(p, 0.95), m.palabraEn(p, 0.1),
                        m.caracteresDichos(p, 2), m.lineaVisible(p, 0.05), m.lineaVisible(p, 0.2)]; }})(),
  keys: [m.keys(0.5, [[0, 0], [1, 10]]), m.keys(2, [[0, [0, 0]], [1, [4, 8]]])],
}};
console.log(JSON.stringify(out));
""")

    def test_movimiento_identico(self):
        self.assertEqual({k: tuple(v) for k, v in self.js["mov"].items()}, self.R.MOVIMIENTO)

    def test_gestos_mismos_numeros(self):
        for rol, vals in self.js["roles"].items():
            for t, v in zip(TIEMPOS, vals):
                self.assertAlmostEqual(v, self.R.entra(t, 0.05, rol), places=9, msg=f"{rol} t={t}")

    def test_resorte_identico_incluso_sobreamortiguado(self):
        for t, v in zip(TIEMPOS, self.js["spring"]):
            self.assertAlmostEqual(v, self.R.spring(t, 0.0, 200, 30), places=9)

    def test_curvas_identicas(self):
        for nombre, vals in self.js["curvas"].items():
            fn = getattr(self.R, nombre)
            for t, v in zip(TIEMPOS, vals):
                self.assertAlmostEqual(v, fn(t / 1.5), places=9, msg=nombre)

    def test_subframes_como_el_motor(self):
        ventana = 0.5 / 30
        esperado = [2.0 + ventana * ((k + 0.5) / 5 - 0.5) for k in range(5)]
        for a, b in zip(self.js["sub"], esperado):
            self.assertAlmostEqual(a, b, places=12)

    def test_frame_idx_como_el_grano(self):
        # el grano del motor usa int(round(t*fps)): el mismo indice en todo el obturador
        self.assertEqual(self.js["fidx"], [int(round((t + 0.5) * 30)) for t in TIEMPOS])

    def test_funcion_pura_y_converge(self):
        a, b = self.js["puro"]
        self.assertEqual(a, b)
        self.assertAlmostEqual(self.js["ret_fin"], -2, places=3)

    def test_critico_no_pasa_del_objetivo(self):
        self.assertLessEqual(self.js["critico_max"], 1.0 + 1e-12)

    def test_rejilla_de_beat_grid(self):
        beat_at, t3, cerca, compas, pulso, golpe_en, golpe_antes, aterriza = self.js["grid"]
        self.assertAlmostEqual(beat_at, 2.0)
        self.assertAlmostEqual(t3, 1.7)
        self.assertAlmostEqual(cerca, 0.7)
        self.assertEqual(compas, 1)
        self.assertAlmostEqual(pulso, 1.0)
        self.assertAlmostEqual(golpe_en, 0.8)
        self.assertEqual(golpe_antes, 0)
        self.assertAlmostEqual(aterriza, 1.15)

    def test_palabras_de_alinear(self):
        prog, k1, k0, chars, vis_temprano, vis = self.js["pal"]
        self.assertAlmostEqual(prog, 0.5)
        self.assertEqual((k1, k0), (0, -1))
        self.assertEqual(chars, len("ayer Binance"))
        self.assertFalse(vis_temprano)
        self.assertTrue(vis)

    def test_llaves(self):
        self.assertAlmostEqual(self.js["keys"][0], 5.0)
        self.assertEqual(self.js["keys"][1], [4, 8])

    def test_sin_relojes_ni_azar_sin_semilla(self):
        with open(MJS, encoding="utf-8") as fh:
            src = fh.read()
        codigo = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("//") and not l.lstrip().startswith("*") and not l.lstrip().startswith("/**"))
        for prohibido in ("Date.now", "performance.now", "Math.random", "setTimeout", "setInterval"):
            self.assertNotIn(prohibido, codigo, prohibido)


if __name__ == "__main__":
    unittest.main()
