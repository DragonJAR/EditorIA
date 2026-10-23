#!/usr/bin/env python3
"""Tests de lint_copy.py — el contrato de copy medido contra el motor real.

Cubre: extraccion de textos y roles por escena, el auto-fit replicado
(titular, bloque envuelto, texto suelto), los tells de genero, el conteo de
palabras, el tricolonio y el contrato de la CLI.

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
sys.path.insert(0, SCRIPTS)

import _copy as C  # noqa: E402
import lint_copy as L  # noqa: E402


def _plan(escenas):
    return {"duracion": 20.0, "tamano": "1080x1920", "escenas": escenas}


class TestExtraccion(unittest.TestCase):
    def test_rol_por_clave(self):
        entradas = C.extraer(_plan([{"tipo": "bento", "rotulo": "X", "items": [
            {"titulo": "A", "texto": "B"}]}]))
        roles = {e["ruta"]: e["rol"] for e in entradas}
        self.assertEqual(roles["escenas[0].rotulo"], "rotulo")
        self.assertEqual(roles["escenas[0].items[0].titulo"], "item")
        self.assertEqual(roles["escenas[0].items[0].texto"], "texto")

    def test_override_por_escena(self):
        e = C.extraer(_plan([
            {"tipo": "pildoras", "texto": ["a", "b", "c"]},
            {"tipo": "remate", "lineas": ["a"], "gigante": "OWASP"},
            {"tipo": "typewriter", "texto": "hola"},
            {"tipo": "quote", "texto": "cita", "autor": "x"},
        ]))
        roles = [x["rol"] for x in e]
        self.assertIn("pildora", roles)
        self.assertIn("display", roles)
        self.assertIn("gigante", roles)
        self.assertIn("maquina", roles)
        self.assertIn("declaracion", roles)

    def test_apertura_tiene_su_propio_tamano(self):
        e = C.extraer(_plan([{"tipo": "apertura", "texto1": ["a"], "texto2": ["b"]}]))
        tams = {x["clave"]: x["tam_ef"] for x in e}
        self.assertEqual(tams["texto1"], 150)
        self.assertEqual(tams["texto2"], 124)

    def test_no_ignora_texto_vacio(self):
        e = C.extraer(_plan([{"tipo": "bento", "rotulo": "  ", "pie": "OWASP"}]))
        self.assertEqual([x["clave"] for x in e], ["pie"])


class TestAutoFit(unittest.TestCase):
    def test_titular_corto_queda_al_tamano_nominal(self):
        tam, escala = C.ajustar_titular(["Corto"], tam=120)
        self.assertEqual(tam, 120)
        self.assertEqual(escala, 1.0)

    def test_titular_largo_se_encoge(self):
        tam, escala = C.ajustar_titular(["Una linea deliberadamente muy larga " * 3], tam=120)
        self.assertLess(tam, 120)
        self.assertGreaterEqual(tam, 40)

    def test_titular_nunca_baja_del_piso(self):
        tam, _ = C.ajustar_titular(["x" * 400], tam=120)
        self.assertEqual(tam, 40)

    def test_texto_suelto_se_encoge_con_piso_18(self):
        tam, _ = C.ajustar_texto("palabra " * 200, "texto")
        self.assertGreaterEqual(tam, 18)

    def test_bloque_envuelve_y_encoge(self):
        tam, escala = C.ajustar_bloque("frase larga " * 30, "maquina")
        self.assertIsNotNone(tam)
        self.assertLessEqual(tam, 144)


class TestTells(unittest.TestCase):
    def test_tricolonio_solo_con_punto(self):
        self.assertTrue(C.es_tricolon("Rapido. Simple. Seguro."))
        self.assertFalse(C.es_tricolon("ICS · SCADA · Industrial"))
        self.assertFalse(C.es_tricolon("Solo dos. Frases."))

    def test_palabras_no_cuentan_separadores(self):
        self.assertEqual(C.n_palabras("ICS · SCADA · Industrial"), 3)
        self.assertEqual(C.n_palabras("una palabra"), 2)


class TestAnalisis(unittest.TestCase):
    def test_plan_limpio_sin_fallos(self):
        plan = _plan([
            {"tipo": "apertura", "from": 0, "to": 4, "texto1": ["Prueba", "unica"],
             "texto2": ["Segunda", "linea"]},
            {"tipo": "final", "from": 4, "to": 8, "marca": "Marca", "lema": "lema"},
        ])
        fallos, avisos = L.analizar(plan)
        self.assertEqual(fallos, [])

    def test_vocabulario_de_genero_es_aviso(self):
        plan = _plan([{"tipo": "hero", "titulo": "Potencia tu negocio hoy"}])
        fallos, avisos = L.analizar(plan)
        self.assertEqual(fallos, [])
        self.assertTrue(any("vocabulario de genero" in a["msg"] for a in avisos))

    def test_cifra_sin_fuente_es_aviso(self):
        plan = _plan([{"tipo": "gauge", "titulo": "Severidad", "valor": 9}])
        fallos, avisos = L.analizar(plan)
        self.assertTrue(any("cifra sin fuente" in a["msg"] for a in avisos))

    def test_cifra_con_fuente_no_avisa(self):
        plan = _plan([{"tipo": "gauge", "titulo": "Severidad", "valor": 9, "fuente": "CVSS 3.1"}])
        fallos, avisos = L.analizar(plan)
        self.assertFalse(any("cifra sin fuente" in a["msg"] for a in avisos))

    def test_fuente_en_una_escena_que_no_la_dibuja_avisa(self):
        # el linter acepta el campo `fuente` en cualquier escena, pero el
        # motor solo lo dibuja en las que lo llaman. si no se dibuja, el
        # espectador no la ve y la regla "toda cifra lleva su fuente" no se
        # cumple: el plan dice una cosa y la pieza dice otra.
        plan = _plan([{"tipo": "hero", "titulo": "Un titular",
                       "texto1": ["Una", "linea"], "texto2": ["Otra"],
                       "fuente": "CVSS 3.1"}])
        fallos, avisos = L.analizar(plan)
        self.assertTrue(any("no la dibuja" in a["msg"] for a in avisos),
                        f"una fuente que no se dibuja tiene que avisar: {avisos}")

    def test_cita_sin_origen_avisa(self):
        plan = _plan([{"tipo": "quote", "texto": "Una cita", "autor": "Alguien"}])
        _f, avisos = L.analizar(plan)
        self.assertTrue(any("cita sin origen" in a["msg"] for a in avisos))

    def test_escena_repetida_avisa(self):
        plan = _plan([{"tipo": "bento", "rotulo": "a"}, {"tipo": "bento", "rotulo": "b"}])
        _f, avisos = L.analizar(plan)
        self.assertTrue(any("relleno" in a["msg"] for a in avisos))


class TestLimitesDelMotor(unittest.TestCase):
    """El motor dibuja un maximo y descarta lo que excede, en silencio."""

    def test_bento_con_mas_de_cuatro_items_falla(self):
        plan = _plan([{"tipo": "bento", "rotulo": "X", "items": [
            {"titulo": f"T{i}", "texto": "texto"} for i in range(6)]}])
        fallos, _a = L.analizar(plan)
        self.assertTrue(any("se pierden en silencio" in f["msg"] for f in fallos))

    def test_bento_con_cuatro_items_no_falla(self):
        plan = _plan([{"tipo": "bento", "rotulo": "X", "items": [
            {"titulo": f"T{i}", "texto": "texto"} for i in range(4)]}])
        fallos, _a = L.analizar(plan)
        self.assertFalse(any("se pierden en silencio" in f["msg"] for f in fallos))

    def test_hero_con_subtitulo_de_tres_lineas_falla(self):
        largo = ("Una linea de apoyo bastante larga que describe el producto con muchas mas "
                 "palabras de las que el motor puede dibujar en dos lineas dentro de la zona "
                 "segura de nueve a dieciseis")
        plan = _plan([{"tipo": "hero", "titulo": "T", "subtitulo": largo}])
        fallos, _a = L.analizar(plan)
        self.assertTrue(any("la ultima se pierde" in f["msg"] for f in fallos))

    def test_hero_con_subtitulo_corto_no_falla(self):
        plan = _plan([{"tipo": "hero", "titulo": "T", "subtitulo": "Subtitulo corto"}])
        fallos, _a = L.analizar(plan)
        self.assertFalse(any("la ultima se pierde" in f["msg"] for f in fallos))


class TestCLI(unittest.TestCase):
    def _correr(self, args):
        return subprocess.run([sys.executable, os.path.join(SCRIPTS, "lint_copy.py")] + args,
                              capture_output=True, text=True, timeout=300)

    def test_plan_inexistente_da_error_claro(self):
        r = self._correr([os.path.join(tempfile.gettempdir(), "no_existe_editoria.json")])
        self.assertEqual(r.returncode, 2)
        self.assertNotIn("Traceback", r.stderr)
        self.assertIn("no existe", r.stderr)

    def test_json_valido(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(_plan([{"tipo": "hero", "titulo": "Titulo"}]), f)
            ruta = f.name
        try:
            r = self._correr([ruta, "--json"])
            self.assertEqual(r.returncode, 0)
            datos = json.loads(r.stdout)
            self.assertIn("fallos", datos)
            self.assertIn("avisos", datos)
        finally:
            os.unlink(ruta)


if __name__ == "__main__":
    unittest.main()
