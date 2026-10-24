#!/usr/bin/env python3
"""Tests de _censo_clis.py — el modulo que MIDE que CLI ejecuta la suite.

Por que este modulo necesita un test que lo EJECUTE, y no un motivo
declarado: al documentarlo en `references/mapa.md`, el guard de cobertura lo
trata como una CLI documentada, y una CLI documentada o la ejecuta un test o
tiene un motivo en `MOTIVOS_SIN_EJECUCION`. Declarar el motivo habria sido la
excusa: la verdad era que el modulo no lo ejecutaba nadie, y por eso la
validacion estaba en rojo.

Aqui se ejecuta DE VERDAD, y rapido. El censo acepta `--test-dir`, asi que
este test le pasa una carpeta temporal con UN test trivial que lanza un script
de la skill, y comprueba que el censo lo registra. Es la misma mecanica de la
corrida completa, en pequena: la que el guard de cobertura mide.

Y el otro lado del mismo principio: lo que nadie ejecuta no se inventa. Un
test que no lanza nada no produce entradas, y el censo lo dice.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
BASE = os.path.dirname(SCRIPTS)
CENSO = os.path.join(SCRIPTS, "_censo_clis.py")
# un script de la skill que solo necesita argparse: el test trivial lo lanza
# para que el censo tenga algo que registrar
GUION = os.path.join(SCRIPTS, "auditar_plan.py")

_TRIVIAL = '''\
import os
import subprocess
import sys
import unittest

SCRIPT = {script!r}


class TestTrivial(unittest.TestCase):
    def test_lanza_un_script_de_la_skill(self):
        subprocess.run([sys.executable, SCRIPT, "--help"],
                       capture_output=True, text=True)


class TestMudado(unittest.TestCase):
    def test_no_lanza_nada(self):
        self.assertTrue(os.path.exists(SCRIPT))
'''


class TestCensoClis(unittest.TestCase):
    """El censo: mide, no declara."""

    def _carpeta_de_tests(self, tmp, con_script=True):
        """Una carpeta con un test trivial que lanza (o no) un script."""
        d = os.path.join(tmp, "mini_tests")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "test_trivial.py"), "w", encoding="utf-8") as fh:
            fh.write(_TRIVIAL.format(script=GUION))
        return d

    def _correr(self, test_dir, salida=None):
        cmd = [sys.executable, CENSO, "--test-dir", test_dir]
        if salida:
            cmd += ["--salida", salida]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        return p

    def test_registra_la_cli_que_la_suite_ejecuta(self):
        """El censo ve la CLI que el test lanza, y la ve CON su nombre."""
        tmp = tempfile.mkdtemp(prefix="editoria_censo_")
        try:
            d = self._carpeta_de_tests(tmp)
            salida = os.path.join(tmp, "mapa.json")
            p = self._correr(d, salida)
            self.assertEqual(p.returncode, 0,
                             f"el censo fallo: {p.stderr[-800:]}")
            self.assertTrue(os.path.exists(salida),
                            "el censo no escribio el mapa pedido")
            with open(salida, encoding="utf-8") as fh:
                mapa = json.load(fh)
            self.assertIn("scripts/auditar_plan.py", mapa,
                          f"el censo no vio la CLI ejecutada: {mapa}")
            # y el mapa dice QUE TEST la ejecuto: sin eso, el guard de
            # cobertura no puede saber si ese test sigue existiendo
            for cli, tests in mapa.items():
                for t in tests:
                    self.assertTrue(t.endswith(".py"), f"test sin nombre: {t}")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_no_inventa_entradas_para_lo_que_nadie_ejecuta(self):
        """Un test que no lanza nada no produce entradas: el mapa no se
        rellena solo, y un guard que no ve su objeto tiene que decirlo."""
        tmp = tempfile.mkdtemp(prefix="editoria_censo_")
        try:
            d = self._carpeta_de_tests(tmp)
            # una suite donde NADIE ejecuta un script de la skill
            vacia = os.path.join(tmp, "vacia")
            os.makedirs(vacia, exist_ok=True)
            with open(os.path.join(vacia, "test_nada.py"), "w", encoding="utf-8") as fh:
                fh.write("import unittest\n\n\n"
                         "class TestNada(unittest.TestCase):\n"
                         "    def test_no_hace_nada(self):\n"
                         "        self.assertTrue(True)\n")
            salida = os.path.join(tmp, "mapa_vacio.json")
            p = self._correr(vacia, salida)
            self.assertEqual(p.returncode, 0, f"el censo fallo: {p.stderr[-800:]}")
            with open(salida, encoding="utf-8") as fh:
                mapa = json.load(fh)
            self.assertEqual(mapa, {},
                             f"el censo invento entradas: {mapa}")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_las_diferencias_separan_las_dos_cosas(self):
        """La diferencia entre 'declarado y no ejecutado' y 'ejecutado y no
        declarado' son dos cosas distintas, y una guard que las mezcla
        esconde un fallo detras de otro."""
        sys.path.insert(0, SCRIPTS)
        try:
            import _censo_clis
        finally:
            sys.path.pop(0)
        # rutas de VERDAD: el guard de enlaces rotos lee tambien los .py, y
        # una ruta de ejemplo que no existe es un enlace roto (y aqui esta el
        # mapa entero, con sus claves y sus tests)
        declarado = {"scripts/auditar_plan.py":
                     ["scripts/_tests/test_auditar_plan.py"]}
        medido = {"scripts/lint_copy.py": ["scripts/_tests/test_lint_copy.py"]}
        sin_ejecutar, sin_declarar = _censo_clis._diferencias(declarado, medido)
        self.assertEqual(sin_ejecutar, declarado)
        self.assertEqual(sin_declarar, medido)
        # si coinciden, no hay diferencia que reportar
        igual = {"scripts/auditar_plan.py":
                 ["scripts/_tests/test_auditar_plan.py"]}
        self.assertEqual(_censo_clis._diferencias(igual, igual), ({}, {}))

    def test_el_censo_ayuda_como_cualquier_otra_cli(self):
        p = subprocess.run([sys.executable, CENSO, "--help"],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(p.returncode, 0)
        self.assertIn("--test-dir", p.stdout)


if __name__ == "__main__":
    unittest.main()
