#!/usr/bin/env python3
"""Tests de scripts/sincronizar_instalada.py.

La herramienta deja la copia instalada en el estado publicado y sin
bytecode fantasma. El caso que la hace necesaria: al copiar la skill con
`tar`/`git archive`, los .py quedan con el mtime del commit (en el
pasado) y un __pycache__ que ya estaba en la copia queda MAS NUEVO: python
ejecuta ese codigo y la copia corre un motor que ya no existe. Un FAIL
que no se reproduce en el repo, y todos los checks contra la copia
mienten.

Run with: python3 -m unittest discover -s SKILL/scripts/_tests
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
BASE = os.path.dirname(SCRIPTS)
HERRAMIENTA = os.path.join(SCRIPTS, "sincronizar_instalada.py")


def _copia_skill(destino):
    shutil.copytree(os.path.join(BASE, "scripts"), os.path.join(destino, "scripts"),
                    ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(os.path.join(BASE, "references"), os.path.join(destino, "references"))
    shutil.copy(os.path.join(BASE, "SKILL.md"), os.path.join(destino, "SKILL.md"))
    return destino


def _corre(destino_padre, *args):
    return subprocess.run(
        [sys.executable, HERRAMIENTA, "--destino", destino_padre, *args],
        capture_output=True, text=True, timeout=300)


class TestSincronizarInstalada(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="editoria_sync_")
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.destino = os.path.join(self.dir, "skills")
        os.makedirs(self.destino)
        _copia_skill(os.path.join(self.destino, "editoria"))

    def _pyc_fantasma(self):
        """Un .pyc mas nuevo que su .py: python ejecuta ese codigo."""
        scripts = os.path.join(self.destino, "editoria", "scripts")
        py = os.path.join(scripts, "medir_animacion.py")
        cache = os.path.join(scripts, "__pycache__")
        os.makedirs(cache, exist_ok=True)
        pyc = os.path.join(cache, "medir_animacion.cpython-314.pyc")
        with open(pyc, "wb") as f:
            f.write(b"\x00\x00\x00\x00")
        # mas nuevo que su .py: el caso de git archive sobre una copia con cache
        os.utime(pyc, (os.path.getmtime(py) + 3600, os.path.getmtime(py) + 3600))
        return pyc

    def test_detecta_el_bytecode_fantasma(self):
        self._pyc_fantasma()
        r = _corre(self.destino, "--check")
        self.assertEqual(r.returncode, 1,
                         f"un bytecode fantasma deberia salir como fallo:\n{r.stdout}")
        self.assertIn("bytecode fantasma", r.stdout)

    def test_check_no_escribe(self):
        pyc = self._pyc_fantasma()
        r = _corre(self.destino, "--check")
        self.assertTrue(os.path.exists(pyc), "--check no debe borrar nada")

    def test_limpia_el_cache(self):
        pyc = self._pyc_fantasma()
        r = _corre(self.destino)
        self.assertEqual(r.returncode, 0, f"la sincronizacion fallo:\n{r.stdout}\n{r.stderr}")
        self.assertFalse(os.path.exists(pyc), "el bytecode fantasma tiene que quedar borrado")
        self.assertFalse(os.path.exists(os.path.dirname(pyc)), "el __pycache__ tiene que quedar borrado")

    def test_sin_fantasma_no_problema(self):
        r = _corre(self.destino, "--check")
        self.assertEqual(r.returncode, 0, f"sin fantasma deberia salir limpio:\n{r.stdout}")
        self.assertIn("sin bytecode fantasma", r.stdout)


if __name__ == "__main__":
    unittest.main()
