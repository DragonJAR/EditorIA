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
    """Corre la COPIA de la herramienta (la instalada), no la del repo.

    La herramienta calcula sus rutas desde su propio __file__: es lo que
    hace que valga para la copia instalada. Si se corriera la del repo,
    sincronizaria el repo real y el test no probaria nada.
    """
    copia = os.path.join(destino_padre, "editoria", "scripts", "sincronizar_instalada.py")
    return subprocess.run(
        [sys.executable, copia, "--destino", destino_padre, *args],
        capture_output=True, text=True, timeout=300)


class TestSincronizarInstalada(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="editoria_sync_")
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.destino = os.path.join(self.dir, "skills")
        os.makedirs(self.destino)
        _copia_skill(os.path.join(self.destino, "editoria"))

    def _pyc_fantasma(self):
        """Un .pyc LEGITIMO pero con codigo distinto al de su .py.

        Con este se ve por que la comparacion tiene que ser de contenido: el
        .pyc es valido, python lo usaria, y aun asi ejecuta un codigo que
        ya no esta en el .py.
        """
        import importlib.util
        import marshal
        scripts = os.path.join(self.destino, "editoria", "scripts")
        py = os.path.join(scripts, "medir_animacion.py")
        cache = os.path.join(scripts, "__pycache__")
        os.makedirs(cache, exist_ok=True)
        pyc = os.path.join(cache, "medir_animacion.cpython-314.pyc")
        otro = compile("CODIGO_VIEJO = 1\n", os.path.basename(py), "exec")
        with open(pyc, "wb") as f:
            f.write(importlib.util.MAGIC_NUMBER)
            f.write(b"\x00" * 12)      # flags + mtime + tamaño
            f.write(marshal.dumps(otro))
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

    def test_un_pyc_recien_compilado_no_es_fantasma(self):
        # al compilar, el .pyc nace con la hora de ahora y el .py puede
        # tener el mtime del commit (pasado): con FECHAS pareceria
        # fantasma, y no lo es. La comparacion es de contenido.
        import py_compile
        scripts = os.path.join(self.destino, "editoria", "scripts")
        py = os.path.join(scripts, "medir_animacion.py")
        cache = os.path.join(scripts, "__pycache__")
        os.makedirs(cache, exist_ok=True)
        pyc = os.path.join(cache, "medir_animacion.cpython-314.pyc")
        py_compile.compile(py, cfile=pyc, doraise=False)
        # el .py con el mtime del commit (pasado): el .pyc queda mas nuevo
        os.utime(py, (1000000, 1000000))
        self.assertGreater(os.path.getmtime(pyc), os.path.getmtime(py),
                           "el .pyc deberia quedar mas nuevo que su .py")
        r = _corre(self.destino, "--check")
        self.assertEqual(r.returncode, 0, f"no deberia marcar fantasma:\n{r.stdout}")
        self.assertIn("sin bytecode fantasma", r.stdout)

    def test_sincroniza_desde_head(self):
        # con repo: la copia queda con lo publicado, y lo que sobra se va
        repo = os.path.join(self.dir, "repo")
        skill = os.path.join(repo, "editoria")
        _copia_skill(skill)
        with open(os.path.join(skill, "references", "mapa.md"), "a", encoding="utf-8") as f:
            f.write("\n<!-- marcador del commit -->\n")

        def _git(*args):
            subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)

        _git("init", "-q")
        _git("config", "user.email", "test@local")
        _git("config", "user.name", "test")
        _git("add", "-A")
        _git("commit", "-q", "-m", "uno")
        # un archivo que solo existe en el arbol de trabajo, no en HEAD
        with open(os.path.join(skill, "references", "mapa.md"), "a", encoding="utf-8") as f:
            f.write("\n<!-- solo en el arbol -->\n")
        sobra = os.path.join(skill, "references", "mapa.md")

        # la copia instalada es OTRO sitio, y la herramienta se ejecuta
        # desde la skill del repo
        r = subprocess.run(
            [sys.executable, os.path.join(skill, "scripts", "sincronizar_instalada.py"),
             "--destino", self.destino],
            capture_output=True, text=True, timeout=300, cwd=skill)
        self.assertEqual(r.returncode, 0, f"la sincronizacion fallo:\n{r.stdout}\n{r.stderr}")
        destino_mapa = os.path.join(self.destino, "editoria", "references", "mapa.md")
        with open(destino_mapa, encoding="utf-8") as f:
            txt = f.read()
        self.assertIn("marcador del commit", txt,
                      "la copia tiene que quedar con lo publicado")
        self.assertNotIn("solo en el arbol", txt,
                         "lo que no esta publicado no puede quedar en la copia")


if __name__ == "__main__":
    unittest.main()
