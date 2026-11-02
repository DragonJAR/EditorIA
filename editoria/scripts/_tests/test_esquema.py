#!/usr/bin/env python3
"""Tests del ESQUEMA de campos: tipos, obligatorios, `at` y duración.

El esquema es la fuente única de qué campos lee cada escena, y sale del
PROPIO CÓDIGO de la escena (su `e["x"]` y sus helpers): el esquema nunca se
desincroniza del renderizador porque ES el renderizador.

QUE PROTEGE

1. Cada parametro tiene nombre, tipo, obligatorio, significado y markup.
2. `at` documenta sus claves.
3. Un obligatorio que falta es un ERROR con escena y campo (no un TypeError
   en el render).
4. Un tipo equivocado es un error claro.
5. El cierre (`final`) pide UN nombre grande: `marca` o `titulo`.
6. La prosa del plan no puede llevar el copy de muestra de una escena (eso
   es un plan de ejemplo, no una pieza).
7. NINGUNA de las muestras del catalogo es rechazada: el esquema no puede
   marcar como obligatorio un campo que la escena real no exige (eso
   rechazaria planes validos en el render).

Run with: python3 -m unittest discover -s SKILL/scripts/_tests
"""

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
SKILL = os.path.dirname(SCRIPTS)
for p in (SCRIPTS, os.path.join(SCRIPTS, "ffmpeg_tools")):
    if p not in sys.path:
        sys.path.insert(0, p)

import render_plan as R  # noqa: E402

MUESTRAS = os.path.join(SCRIPTS, "escenas_muestra.json")


def _muestras():
    with open(MUESTRAS, encoding="utf-8") as fh:
        return json.load(fh)["escenas"]


class TestEsquema(unittest.TestCase):
    def test_cada_param_tiene_nombre_tipo_obligatorio_significado(self):
        for tipo in _muestras():
            for p in R.esquema_de(tipo):
                for clave in ("nombre", "tipo", "obligatorio", "significado",
                              "markup"):
                    self.assertIn(clave, p,
                                  f"{tipo}.{p.get('nombre')} no declara {clave}")

    def test_at_documenta_sus_claves(self):
        for tipo in ("apertura", "final", "constancia"):
            at = [p for p in R.esquema_de(tipo) if p["nombre"] == "at"]
            self.assertEqual(len(at), 1, f"{tipo} no declara `at`")
            self.assertIn("claves", at[0])

    def test_el_cierre_sin_nombre_es_error(self):
        """`final` sin `marca` ni `titulo`: ERROR con el nombre del campo."""
        e = {"tipo": "final", "from": 0.0, "to": 3.0, "at": {}}
        errs = R.errores_de_esquema(e, 0)
        self.assertTrue(errs, "el cierre sin nombre no es un error")
        self.assertTrue(any("marca" in x or "titulo" in x for x in errs),
                        f"el error no nombra el campo: {errs}")

    def test_el_cierre_con_titulo_pasa(self):
        """`titulo` basta: el cierre no exige `marca`."""
        e = {"tipo": "final", "from": 0.0, "to": 3.0, "titulo": "HABLEMOS",
             "at": {"lema": 1.0, "boton": 1.6}}
        self.assertEqual(R.errores_de_esquema(e, 0), [],
                         "un cierre con `titulo` no puede ser un error")

    def test_un_tipo_equivocado_es_error_claro(self):
        """Un numero donde va texto: error con campo y tipo, no TypeError."""
        e = {"tipo": "constancia", "from": 0.0, "to": 3.0,
             "items": "no es una lista", "at": {}}
        errs = R.errores_de_esquema(e, 0)
        self.assertTrue(errs, "un tipo equivocado no es un error")
        self.assertTrue(any("items" in x for x in errs),
                        f"el error no nombra el campo: {errs}")

    def test_ninguna_muestra_del_catalogo_es_rechazada(self):
        """La red de seguridad: el esquema NO puede rechazar una muestra real.

        Si este test falla, el esquema Derived marca como obligatorio un campo
        que la escena no exige, y el render rechazaria planes validos.
        """
        malas = []
        for tipo, ej in _muestras().items():
            e = dict(ej)
            e["tipo"] = tipo
            e.setdefault("from", 0.0)
            e.setdefault("to", 5.0)
            errs = R.errores_de_esquema(e, 0)
            if errs:
                malas.append(f"{tipo}: {errs[0]}")
        self.assertEqual(malas, [],
                         "el esquema rechaza muestras propias del catalogo:\n  " +
                         "\n  ".join(malas))

    def test_la_duracion_de_una_escena_es_razonable(self):
        """Cada escena dice cuanto debe durar (min, recomendado, max)."""
        for tipo in ("apertura", "final", "constancia"):
            d = R.duracion_de(tipo)
            self.assertIsNotNone(d, f"{tipo} no declara duracion")
            self.assertLessEqual(d["min"], d["recomendada"][1])
            self.assertLessEqual(d["recomendada"][1], d["max"])

    def test_el_markup_de_un_campo_que_no_lo_admite_se_quita(self):
        """`*clave*` en un boton sale sin asteriscos (y el campo no es markup)."""
        boton = [p for p in R.esquema_de("final") if p["nombre"] == "boton"]
        self.assertTrue(boton, "el cierre no declara `boton`")
        self.assertFalse(boton[0]["markup"],
                         "`boton` no admite markup (se pinta como texto corrido)")
        e = {"tipo": "final", "from": 0.0, "to": 3.0, "marca": "X",
             "boton": "*Hablemos*", "at": {"lema": 1.0, "boton": 1.6}}
        ajustada = R.completar_escena(dict(e))
        self.assertEqual(ajustada["boton"], "Hablemos",
                         "los asteriscos del markup siguen en pantalla")


if __name__ == "__main__":
    unittest.main()
