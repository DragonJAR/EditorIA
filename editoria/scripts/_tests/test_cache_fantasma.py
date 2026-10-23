#!/usr/bin/env python3
"""Tests del detector de codigo fantasma.

Un .pyc mas nuevo que su .py hace que python ejecute un codigo que ya no
existe. Pasa al copiar la skill con `tar`/`git archive` (preservan el mtime
del commit) sobre una copia que ya tenia __pycache__: un FAIL que no se
reproduce en el repo y si en la copia instalada.

El detector compara el CONTENIDO (el codigo compilado del .py actual contra
el que guarda el .pyc), no las fechas: un commit posterior no convierte un
.pyc en fantasma.

Run with: python3 -m unittest discover -s SKILL/scripts/_tests
"""

import os
import py_compile
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
BASE = os.path.dirname(SCRIPTS)
CHECK_ENV = os.path.join(SCRIPTS, "check_env.py")


class CacheFantasma(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="editoria_cache_")
        self.addCleanup(shutil.rmtree, self.dir, True)
        for carpeta in ("scripts", "assets", "brand"):
            origen = os.path.join(BASE, carpeta)
            if os.path.isdir(origen):
                shutil.copytree(origen, os.path.join(self.dir, carpeta),
                                ignore=shutil.ignore_patterns("__pycache__"))

    def _fantasma(self, modulo="_fantasma_de_prueba", viejo="A = 1\n", nuevo="A = 2\n"):
        """Deja un .pyc con el codigo VIEJO y un .py con el NUEVO, del mismo
        tamano y con la misma fecha: python usaria el .pyc (codigo fantasma)."""
        py = os.path.join(self.dir, "scripts", f"{modulo}.py")
        with open(py, "w", encoding="utf-8") as f:
            f.write(viejo)
        pyc = py_compile.compile(py, doraise=True)
        os.utime(py, (os.stat(pyc).st_mtime, os.stat(pyc).st_mtime))
        with open(py, "w", encoding="utf-8") as f:
            f.write(nuevo)
        os.utime(py, (os.stat(pyc).st_mtime, os.stat(pyc).st_mtime))
        return modulo

    def _correr(self):
        r = subprocess.run([sys.executable, os.path.join(self.dir, "scripts", "check_env.py")],
                           capture_output=True, text=True, timeout=300)
        return r.stdout + r.stderr

    def test_detecta_un_pyc_con_el_codigo_viejo(self):
        modulo = self._fantasma()
        salida = self._correr()
        self.assertIn("codigo fantasma", salida,
                      "un .pyc con el codigo viejo tiene que salir en la salida")
        self.assertIn(modulo, salida,
                      f"la salida tiene que nombrar el modulo fantasma ({modulo})")

    def test_no_marca_un_pyc_al_dia(self):
        """Un .pyc compilado del .py ACTUAL no es un fantasma."""
        py = os.path.join(self.dir, "scripts", "_al_dia.py")
        with open(py, "w", encoding="utf-8") as f:
            f.write("B = 1\n")
        py_compile.compile(py, doraise=True)
        salida = self._correr()
        self.assertNotIn("_al_dia.py", salida,
                         "un .pyc al dia no es un fantasma")

    def test_el_artefacto_real_es_un_pyc_viejo(self):
        """La comprobacion de que el .pyc se usa de verdad: con el .pyc viejo
        el modulo importado tiene el valor VIEJO."""
        modulo = self._fantasma(viejo="V = 'viejo'\n", nuevo="V = 'nuevo'\n")
        r = subprocess.run(
            [sys.executable, "-c",
             f"import sys; sys.path.insert(0, {os.path.join(self.dir, 'scripts')!r});"
             f"import {modulo} as m; print(m.V)"],
            capture_output=True, text=True, timeout=120)
        self.assertEqual(r.stdout.strip(), "viejo",
                         "si el .pyc no se usara, esto imprimiria 'nuevo': "
                         "el fixture no reproduce el fallo")


if __name__ == "__main__":
    unittest.main()
