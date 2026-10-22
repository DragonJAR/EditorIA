#!/usr/bin/env python3
"""Tests del bloque `datos` (el modelo antes del dibujo) y del critico que
ubica cada defecto en su escena.

Cubre: la resolucion de referencias {"$dato": nombre} en el motor, el fallo
ruidoso cuando la referencia no existe, los chequeos del linter sobre el
modelo (referencias rotas, datos sin fuente, contradicciones entre escenas) y
el mapeo de un instante a su escena en medir_animacion.

Run with: python3 -m unittest discover -s SKILL/scripts/_tests
"""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)

import lint_copy as L  # noqa: E402


def _cargar(nombre, ruta):
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rp = _cargar("rp", os.path.join(SCRIPTS, "render_plan.py"))
ma = _cargar("ma", os.path.join(SCRIPTS, "medir_animacion.py"))


class TestResolverDatos(unittest.TestCase):
    def test_resuelve_el_valor(self):
        datos = {"servicios": {"valor": 6, "fuente": "catálogo"}}
        self.assertEqual(rp._resolver_dato({"$dato": "servicios"}, datos, 0, {}), 6)

    def test_no_toca_lo_que_no_es_referencia(self):
        datos = {"x": {"valor": 1}}
        self.assertEqual(rp._resolver_dato(7, datos, 0, {}), 7)
        self.assertEqual(rp._resolver_dato("texto", datos, 0, {}), "texto")

    def test_recorre_listas_y_diccionarios(self):
        datos = {"a": {"valor": 3}}
        nodo = {"cards": [{"valor": {"$dato": "a"}, "etiqueta": "x"}]}
        r = rp._recorrer_datos(nodo, datos, 0, {})
        self.assertEqual(r["cards"][0]["valor"], 3)
        self.assertEqual(r["cards"][0]["etiqueta"], "x")

    def test_referencia_inexistente_mata_con_mensaje(self):
        datos = {}
        with self.assertRaises(SystemExit) as ctx:
            rp._resolver_dato({"$dato": "fantasma"}, datos, 0, {"tipo": "stats"})
        self.assertIn("fantasma", str(ctx.exception))

    def test_dato_sin_valor_mata(self):
        with self.assertRaises(SystemExit) as ctx:
            rp.resolver_datos({"datos": {"x": {"fuente": "y"}}})
        self.assertIn("valor", str(ctx.exception))


class TestLinterModelo(unittest.TestCase):
    def _plan(self, **extra):
        plan = {"duracion": 10.0, "escenas": []}
        plan.update(extra)
        return plan

    def test_referencia_rota_es_fallo(self):
        plan = self._plan(escenas=[{"tipo": "gauge", "valor": {"$dato": "nada"}}])
        fallos, _a = L.analizar(plan)
        self.assertTrue(any("no declara" in f["msg"] for f in fallos))

    def test_dato_sin_fuente_es_aviso(self):
        plan = self._plan(datos={"x": {"valor": 1}},
                          escenas=[{"tipo": "gauge", "valor": {"$dato": "x"}}])
        _f, avisos = L.analizar(plan)
        self.assertTrue(any("fuente" in a["msg"] for a in avisos))

    def test_contradiccion_entre_escenas_es_aviso(self):
        plan = self._plan(escenas=[
            {"tipo": "stats", "cards": [{"valor": 3, "etiqueta": "servicios"}]},
            {"tipo": "gauge", "valor": 9, "etiqueta": "servicios"}])
        _f, avisos = L.analizar(plan)
        self.assertTrue(any("contradiccion" in a["msg"] for a in avisos))

    def test_mismo_valor_no_es_contradiccion(self):
        plan = self._plan(escenas=[
            {"tipo": "stats", "cards": [{"valor": 3, "etiqueta": "servicios"}]},
            {"tipo": "gauge", "valor": 3, "etiqueta": "servicios"}])
        _f, avisos = L.analizar(plan)
        self.assertFalse(any("contradiccion" in a["msg"] for a in avisos))

    def test_plan_sin_datos_no_falla(self):
        plan = self._plan(escenas=[{"tipo": "gauge", "valor": 5, "etiqueta": "x"}])
        fallos, _a = L.analizar(plan)
        self.assertFalse(any("no declara" in f["msg"] for f in fallos))


class TestEscenaEn(unittest.TestCase):
    ESCENAS = [(1, "apertura", 0.0, 2.0), (2, "bento", 2.0, 4.0)]

    def test_instante_dentro_de_una_escena(self):
        self.assertEqual(ma._escena_en(1.0, self.ESCENAS), "1:apertura")
        self.assertEqual(ma._escena_en(3.0, self.ESCENAS), "2:bento")

    def test_instante_sobre_el_corte(self):
        self.assertEqual(ma._escena_en(2.0, self.ESCENAS), "corte 1:apertura->2:bento")

    def test_instante_fuera(self):
        self.assertEqual(ma._escena_en(9.0, self.ESCENAS), "?")

    def test_escenas_del_plan(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump({"escenas": [{"tipo": "bento", "from": 0, "to": 3}]}, f)
            ruta = f.name
        try:
            self.assertEqual(ma._escenas_del_plan(ruta), [(1, "bento", 0.0, 3.0)])
            self.assertEqual(ma._escenas_del_plan(None), [])
        finally:
            os.unlink(ruta)


class TestCli(unittest.TestCase):
    def test_plan_inexistente_da_error_claro(self):
        r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "lint_copy.py"),
                            os.path.join(tempfile.gettempdir(), "no_existe_datos.json")],
                           capture_output=True, text=True, timeout=300)
        self.assertEqual(r.returncode, 2)
        self.assertNotIn("Traceback", r.stderr)


if __name__ == "__main__":
    unittest.main()
