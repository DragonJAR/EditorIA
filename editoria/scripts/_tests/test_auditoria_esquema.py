#!/usr/bin/env python3
"""Tests de la AUDITORIA del plan: lo que antes pasaba como PLAN VALIDO.

QUE PROTEGE

1. Un campo obligatorio que falta es un ERROR con escena y campo (no un
   TypeError en el render).
2. Un tipo equivocado frente a la muestra es un ERROR.
3. Un campo que la escena no lee se AVISA con la sugerencia más parecida.
4. El markup en un campo que no lo admite se AVISA (el motor lo quita).
5. Un brand pack que NO existe es un ERROR (antes pasaba en silencio).
6. Una escena mas larga que su maximo es un ERROR; por encima de lo
   recomendado, un AVISO.
7. NINGUN plan de ejemplo del catalogo es rechazado por estos checks.

Run with: python3 -m unittest discover -s SKILL/scripts/_tests
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
SKILL = os.path.dirname(SCRIPTS)
for p in (SCRIPTS, os.path.join(SCRIPTS, "ffmpeg_tools")):
    if p not in sys.path:
        sys.path.insert(0, p)

import auditar_plan as A  # noqa: E402


def _audita(escenas, **plan):
    base = {"duracion": max(e["to"] for e in escenas), "escenas": escenas}
    base.update(plan)
    return A.auditar_estructura(base)


def _niveles(hallazgos, nivel):
    return [h for h in hallazgos if h.get("nivel") == nivel]


class TestAuditoriaDelPlan(unittest.TestCase):
    def test_un_obligatorio_que_falta_es_error(self):
        """La escena `constancia` sin `items` no puede pasar como PLAN VALIDO."""
        hallazgos = _audita([{"tipo": "constancia", "from": 0.0, "to": 4.0,
                              "at": {}}])
        errores = _niveles(hallazgos, "ERROR")
        self.assertTrue(errores, "una escena sin su campo obligatorio no es error")
        self.assertTrue(any("items" in h["msg"] for h in errores),
                        f"el error no nombra el campo: {[h['msg'] for h in errores]}")

    def test_un_tipo_equivocado_es_error(self):
        """Un numero escrito como palabra donde va numero."""
        hallazgos = _audita([{"tipo": "frase", "from": 0.0, "to": 4.0,
                              "frase": "Hola", "cps": "mucho",
                              "at": {}}])
        errores = _niveles(hallazgos, "ERROR")
        self.assertTrue(errores, "un tipo equivocado no es error")
        self.assertTrue(any("cps" in h["msg"] for h in errores),
                        f"el error no nombra el campo: {[h['msg'] for h in errores]}")

    def test_el_markup_en_un_campo_sin_markup_se_avisa(self):
        """`*Hablemos*` en `boton`: el motor lo quita y el enfasis no sale."""
        hallazgos = _audita([{"tipo": "final", "from": 0.0, "to": 4.0,
                              "marca": "X", "boton": "*Hablemos*",
                              "at": {"lema": 1.0, "boton": 1.5}}])
        avisos = _niveles(hallazgos, "AVISO")
        self.assertTrue(any("boton" in h["msg"] for h in avisos),
                        f"no se aviso del markup en `boton`: "
                        f"{[h['msg'] for h in avisos]}")

    def test_un_pack_que_no_existe_es_error(self):
        """El pack inexistente no puede pasar en silencio."""
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "plan.json")
            with open(ruta, "w", encoding="utf-8") as fh:
                json.dump({"duracion": 4.0, "brand": "este-pack-no-existe",
                           "escenas": [{"tipo": "final", "from": 0.0, "to": 4.0,
                                        "marca": "X", "at": {}}]}, fh)
            r = subprocess.run(
                [sys.executable, os.path.join(SCRIPTS, "auditar_plan.py"), ruta],
                capture_output=True, text=True, timeout=300)
        self.assertEqual(r.returncode, 1, f"el plan con un pack inexistente paso:\n{r.stdout}")
        self.assertIn("no existe", r.stdout)

    def test_una_escena_demasiado_larga_es_error(self):
        """Una escena de 40 s es una escena muerta: parte el contenido."""
        hallazgos = _audita([{"tipo": "apertura", "from": 0.0, "to": 40.0,
                              "texto1": ["Hola"], "texto2": ["Mundo"],
                              "at": {"cambio": 2.0, "p1": [0.2], "p2": [3.0]}}])
        errores = _niveles(hallazgos, "ERROR")
        self.assertTrue(any("maximo" in h["msg"] or "máximo" in h["msg"]
                            for h in errores),
                        f"una escena de 40 s no es error: "
                        f"{[h['msg'] for h in errores]}")

    def test_el_plan_de_ejemplo_no_es_rechazado(self):
        """El plan de la skill tiene que pasar sus propios checks."""
        ruta = os.path.join(SCRIPTS, "demo_plan.json")
        with open(ruta, encoding="utf-8") as fh:
            plan = json.load(fh)
        hallazgos = A.auditar_estructura(plan)
        errores = _niveles(hallazgos, "ERROR")
        self.assertEqual(errores, [],
                         "el plan de ejemplo se rechaza a si mismo:\n  " +
                         "\n  ".join(h["msg"] for h in errores))


if __name__ == "__main__":
    unittest.main()
