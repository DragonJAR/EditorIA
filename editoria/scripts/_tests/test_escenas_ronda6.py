#!/usr/bin/env python3
"""Tests de las escenas de la Ronda 6 (index, callout, orbOpen) y de la
transicion `dissolve`.

Las tres nacieron de la lista de escenas futuras del propio catalogo
(`references/escenas.md`). Este archivo fija sus contratos para que no se
desvien: que compongan con las primitivas de la casa (sin logica duplicada ni
color fijo), que entren con un gesto con nombre, que no se salgan de la zona
segura y que no se pisen entre si.
"""

import json
import os
import re
import sys
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(AQUI)
SKILL = os.path.dirname(SCRIPTS)
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, os.path.join(SCRIPTS, "ffmpeg_tools"))

import render_plan as RP  # noqa: E402

NUEVAS = ("index", "callout", "orbOpen")


def _escenas():
    for n in RP.SCENES:
        yield n


class TestRonda6(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(SCRIPTS, "escenas_muestra.json"), encoding="utf-8") as fh:
            self.muestras = json.load(fh)["escenas"]
        with open(os.path.join(SCRIPTS, "render_plan.py"), encoding="utf-8") as fh:
            self.src = fh.read()

    def test_las_tres_escenas_existen_y_tienen_muestra(self):
        for n in NUEVAS:
            self.assertIn(n, RP.SCENES, f"la escena '{n}' debe estar en SCENES")
            self.assertIn(n, self.muestras, f"la escena '{n}' necesita su muestra")

    def test_no_duplican_logica_de_animacion(self):
        """Se componen con primitivas: no pueden traer su propio resorte,
        su propio bucle de entrada ni su propio reloj."""
        for n in NUEVAS:
            cuerpo = self.src.split(f"def sc_{n}(", 1)[1].split("\ndef ", 1)[0]
            self.assertNotIn("spring(", cuerpo,
                             f"sc_{n}: el gesto se pide con entra(), no con spring() directo")
            # el alfa de entrada va con entra(..., rol) y el rol es del catalogo
            for m in re.finditer(r'entra\([^)]*?"([a-z]+)"\)', cuerpo):
                self.assertIn(m.group(1), RP.MOVIMIENTO,
                              f"sc_{n}: el rol '{m.group(1)}' no existe en MOVIMIENTO")

    def test_no_hardcodean_color(self):
        """El acento lo pone el brand pack: las escenas no escriben RGB."""
        for n in NUEVAS:
            cuerpo = self.src.split(f"def sc_{n}(", 1)[1].split("\ndef ", 1)[0]
            rgb = re.findall(r"\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)", cuerpo)
            self.assertEqual(rgb, [],
                             f"sc_{n}: color fijo {rgb[:2]} (usa ACENTO / BLANCO / GRIS)")

    def test_usan_la_escala_para_el_texto(self):
        for n in NUEVAS:
            cuerpo = self.src.split(f"def sc_{n}(", 1)[1].split("\ndef ", 1)[0]
            for m in re.finditer(r"f[TMX]\(\s*(\d{2,3})\s*,", cuerpo):
                tam = int(m.group(1))
                self.assertIn(tam, set(RP.ESCALA.values()),
                              f"sc_{n}: tamano {tam} fuera de la escala "
                              f"{sorted(set(RP.ESCALA.values()))}")

    def test_el_callout_marca_el_titulo_con_placa(self):
        """Sobre una captura clara, el texto blanco no se lee: la placa es
        obligatoria, no un extra."""
        cuerpo = self.src.split("def sc_callout(", 1)[1].split("\ndef ", 1)[0]
        self.assertIn("placa_texto(", cuerpo,
                      "sc_callout: el texto sobre la captura necesita placa")

    def test_el_callout_parsea_el_enfasis(self):
        """'El *dato* que lo cambia' no puede salir con asteriscos."""
        cuerpo = self.src.split("def sc_callout(", 1)[1].split("\ndef ", 1)[0]
        self.assertIn("segs(", cuerpo, "sc_callout: el enfasis se parsea con segs()")
        self.assertIn("draw_seg(", cuerpo, "sc_callout: el enfasis se dibuja con draw_seg()")
        # y no puede dibujar el texto crudo con d.text (que no parsea enfasis)
        for m in re.finditer(r"d\.text\([^)]*e\[\"(titulo|etiqueta)\"\]", cuerpo):
            self.fail(f"sc_callout: {m.group(0)} dibuja el enfasis como texto literal")

    def test_orbOpen_no_converge_fuera_de_la_zona_segura(self):
        """Las particulas nacen dispersas: si el anillo se sale de la zona
        segura, la escena entera se encoge para meterlo."""
        cuerpo = self.src.split("def sc_orbOpen(", 1)[1].split("\ndef ", 1)[0]
        self.assertIn("r_max", cuerpo,
                      "sc_orbOpen: el anillo de nacimiento se acota a la zona segura")

    def test_la_transicion_dissolve_esta_en_el_motor(self):
        self.assertIn('"dissolve"', self.src)
        self.assertIn("SOLAPE_DISSOLVE", self.src)

    def test_la_transicion_iris_esta_en_el_motor(self):
        """El iris comparte presupuesto con la mancha: las dos piden atencion."""
        self.assertIn('"iris"', self.src)
        self.assertIn("def iris_mask(", self.src)
        m = re.search(r'get\("transicion"\) in \(([^)]*)\)', self.src)
        self.assertIsNotNone(m, "el presupuesto debe listar las transiciones que lo consumen")
        self.assertIn("mancha", m.group(1))
        self.assertIn("iris", m.group(1))

    def test_la_escena_callout_acepta_imagen(self):
        muestra = self.muestras["callout"]
        self.assertIn("captura", muestra,
                      "la muestra de callout debe traer la captura que resalta")
        cuerpo = self.src.split("def sc_callout(", 1)[1].split("\ndef ", 1)[0]
        self.assertIn('e.get("captura")', cuerpo)

    def test_el_indice_tiene_items(self):
        muestra = self.muestras["index"]
        self.assertGreaterEqual(len(muestra.get("items", [])), 3,
                                "el indice necesita al menos 3 entradas para provingar")


if __name__ == "__main__":
    unittest.main()
