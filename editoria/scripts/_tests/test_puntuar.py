#!/usr/bin/env python3
"""Tests de puntuar.py — la rubrica de premios como puerta verificable.

Cubre: el catalogo de los ocho ejes, el reparto entre ejes medidos y de juicio,
el gate (ningun eje bajo 4 y media >= 4.3), el parser de --ejes y el contrato
de la CLI (sin traceback ante una entrada que no existe).

Run with: python3 -m unittest discover -s SKILL/scripts/_tests
"""

import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)

import puntuar as P  # noqa: E402


class TestRubrica(unittest.TestCase):
    def test_ocho_ejes_y_cuatro_de_juicio(self):
        self.assertEqual(len(P.EJES), 8)
        self.assertEqual(len(P.JUICIO), 4)
        self.assertEqual([n for n, _, _, _ in P.EJES], [1, 2, 3, 4, 5, 6, 7, 8])

    def test_los_juicios_preguntan(self):
        for n, _, ambito, pregunta in P.EJES:
            if n in P.JUICIO:
                self.assertTrue(ambito == "juicio")
                self.assertTrue(pregunta.strip(), f"el eje {n} no pregunta nada")

    def test_umbral_del_gate(self):
        self.assertEqual(P.UMBRAL_EJE, 4)
        self.assertEqual(P.UMBRAL_MEDIA, 4.3)

    def test_animacion_no_puntua_la_densidad(self):
        # la densidad es ritmo (eje 2), no movimiento: no penaliza
        m = {"pops": [], "tirones": 0, "arranques": [], "muerto": 0.0, "densidad": 9.9}
        s, _d = P._puntuar_animacion(m)
        self.assertEqual(s, 5.0)

    def test_animacion_penaliza_pops_y_tirones(self):
        limpio = {"pops": [], "tirones": 0, "arranques": [], "muerto": 0.0, "densidad": 1.0}
        sucio = {"pops": [1.0, 2.0], "tirones": 4, "arranques": [], "muerto": 0.0, "densidad": 1.0}
        s1, _ = P._puntuar_animacion(limpio)
        s2, _ = P._puntuar_animacion(sucio)
        self.assertGreater(s1, s2)

    def test_sonido_sin_pista_de_audio_es_el_peor(self):
        s, _d = P._puntuar_sonido([{"row": "audio", "status": "WARN",
                                     "measured": "sin pista de audio"}])
        self.assertEqual(s, 1.0)

    def test_sonido_con_audio_presente_no_penaliza(self):
        filas = [{"row": "loudness", "status": "PASS", "measured": "-14.1 LUFS"},
                 {"row": "true peak", "status": "PASS", "measured": "-1.5 dBTP"}]
        s, _d = P._puntuar_sonido(filas)
        self.assertEqual(s, 5.0)

    def test_composicion_sin_plan_no_se_puntua(self):
        s, d = P._puntuar_composicion(None)
        self.assertIsNone(s)
        self.assertTrue(d)

    def test_composicion_penaliza_solapes_y_zona(self):
        malo = {"solapes": ["a", "b"], "zona": 0.8, "letra_min": 40}
        bueno = {"solapes": [], "zona": 1.0, "letra_min": 40}
        s_malo, _ = P._puntuar_composicion(malo)
        s_bueno, _ = P._puntuar_composicion(bueno)
        self.assertLess(s_malo, s_bueno)
        self.assertEqual(s_bueno, 5.0)

    def test_letra_bajo_el_piso_no_alcanza_un_cuatro(self):
        # el piso de letra es una regla dura: el eje 4 no puede pasar
        # aunque el resto de la composicion este impecable
        s, d = P._puntuar_composicion({"solapes": [], "zona": 1.0, "letra_min": 23})
        self.assertLess(s, 4.0)
        self.assertIn("bajo el piso", d)

    def test_letra_en_el_piso_sigue_dando_cinco(self):
        s, _d = P._puntuar_composicion({"solapes": [], "zona": 1.0, "letra_min": 26})
        self.assertEqual(s, 5.0)

    def test_un_eje_medido_no_se_pisa_con_el_juicio(self):
        """La letra bajo el piso es una regla dura: un 5 a ojo no la borra."""
        s, _d = P._puntuar_composicion({"solapes": [], "zona": 1.0, "letra_min": 23})
        self.assertLess(s, 4.0)
        vals = {4: s}
        dets = {4: "medido"}
        vals, dets = P._aplicar_juicio(vals, dets, {4: 5.0}, {4})
        self.assertEqual(vals[4], s, "la medida tiene que ganar al juicio")
        self.assertIn("medido", dets[4])

    def test_el_juicio_rellena_un_eje_sin_medir(self):
        vals, dets = {}, {}
        vals, dets = P._aplicar_juicio(vals, dets, {1: 4.0}, set())
        self.assertEqual(vals[1], 4.0)
        self.assertIn("juzgado por el agente", dets[1])

    def test_parser_de_ejes(self):
        self.assertEqual(P._parse_ejes("1=4,2=5,5=3,7=4"), {1: 4.0, 2: 5.0, 5: 3.0, 7: 4.0})
        with self.assertRaises(ValueError):
            P._parse_ejes("1-4")
        with self.assertRaises(ValueError):
            P._parse_ejes("1=abc")


class TestCLI(unittest.TestCase):
    def _correr(self, args):
        return subprocess.run([sys.executable, os.path.join(SCRIPTS, "puntuar.py")] + args,
                              capture_output=True, text=True, timeout=600)

    def test_video_inexistente_da_error_claro(self):
        # una ruta que no exista en NINGUN sistema: tempfile, no "/tmp"
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            r = self._correr([os.path.join(d, "no_existe_puntuar.mp4")])
            self.assertEqual(r.returncode, 2)
            self.assertNotIn("Traceback", r.stderr)
        self.assertIn("no existe", r.stderr)

    def test_help_funciona(self):
        r = self._correr(["--help"])
        self.assertEqual(r.returncode, 0)
        self.assertIn("--ejes", r.stdout)
        self.assertIn("--plan", r.stdout)

    def test_sin_plan_no_revienta(self):
        # sin --plan el eje 4 no se puede medir: sale con codigo 2 y un mensaje,
        # nunca con un traceback. El video es sintetico: el test no depende de
        # material externo (demo/ no se versiona).
        with tempfile.TemporaryDirectory() as d:
            video = os.path.join(d, "corto.mp4")
            subprocess.run(["ffmpeg", "-v", "error", "-y",
                            "-f", "lavfi", "-i", "color=c=black:s=320x240:d=1:r=24",
                            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono:d=1",
                            "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                            "-c:a", "aac", video], check=True, timeout=180)
            r = self._correr([video, "--ejes", "1=4,2=4,5=4,7=4"])
            self.assertNotIn("Traceback", r.stderr)
            self.assertEqual(r.returncode, 2)
            self.assertIn("--plan", r.stdout)


if __name__ == "__main__":
    unittest.main()
