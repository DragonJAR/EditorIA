#!/usr/bin/env python3
"""Tests de scripts/actualizar_conteos.py.

La herramienta reescribe los conteos que la skill enuncia (referencias,
scripts raiz, herramientas de ffmpeg, suites). El riesgo de una herramienta
así es que se quede vieja: por eso cuenta con la MISMA fuente que el guard
y por eso hay un test que dice que lo que escribe la herramienta es
exactamente lo que el guard despues comprueba.

Tambien cubre las dos topologias: con repo (donde hay README que
actualizar) y sin repo (la copia instalada), donde la herramienta tiene que
reelegir solo lo de la skill y no fallar.

Run with: python3 -m unittest discover -s SKILL/scripts/_tests
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
BASE = os.path.dirname(SCRIPTS)
HERRAMIENTA = os.path.join(SCRIPTS, "actualizar_conteos.py")
AUDITAR = os.path.join(SCRIPTS, "auditar_mapa.py")


def _copia_skill(destino):
    """La skill entera (scripts + references + SKILL.md), sin __pycache__."""
    shutil.copytree(os.path.join(BASE, "scripts"), os.path.join(destino, "scripts"),
                    ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(os.path.join(BASE, "references"), os.path.join(destino, "references"))
    shutil.copy(os.path.join(BASE, "SKILL.md"), os.path.join(destino, "SKILL.md"))
    # los documentos citan estas carpetas: sin ellas, el auditor ve enlaces
    # rotos que no son del caso que se quiere probar
    for sub in ("brand", "film", "assets", "metricas"):
        origen = os.path.join(BASE, sub)
        if os.path.isdir(origen):
            shutil.copytree(origen, os.path.join(destino, sub),
                            ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"))
    return destino


def _git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)


def _ejecuta(skill, *args):
    return subprocess.run([sys.executable, os.path.join(skill, "scripts", "actualizar_conteos.py"),
                           *args], capture_output=True, text=True, timeout=300)


def _audita(skill):
    r = subprocess.run([sys.executable, os.path.join(skill, "scripts", "auditar_mapa.py")],
                       capture_output=True, text=True, timeout=300)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


class TestActualizarConteos(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="editoria_conteos_")
        self.addCleanup(shutil.rmtree, self.dir, True)

    def _repo(self):
        """Un repo con la skill dentro y un README con numeros ROTOS."""
        repo = os.path.join(self.dir, "repo")
        skill = _copia_skill(os.path.join(repo, "skill"))
        with open(os.path.join(repo, "README.md"), "w", encoding="utf-8") as f:
            f.write("# 1 root + 1 in ffmpeg_tools/ + 1 in _tests/ = 3 scripts\n"
                    "│   ├── references/                    # 1 referencias en kebab-case.md\n")
        _git(repo, "init", "-q")
        _git(repo, "config", "user.email", "test@local")
        _git(repo, "config", "user.name", "test")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "uno")
        return repo, skill

    def test_lo_que_escribe_es_lo_que_el_guard_comprueba(self):
        # la cifra de la herramienta y la del guard tienen que ser la misma:
        # se rompe el mapa a proposito, se corre la herramienta y el guard
        # tiene que dar MAPA OK
        repo, skill = self._repo()
        mapa = os.path.join(skill, "references", "mapa.md")
        with open(mapa, encoding="utf-8") as f:
            txt = f.read()
        with open(mapa, "w", encoding="utf-8") as f:
            f.write(re.sub(r"\d+ referencias, \d+ scripts, \d+ herramientas de ffmpeg y \d+ suites de tests",
                           "1 referencias, 1 scripts, 1 herramientas de ffmpeg y 1 suites de tests", txt))
        rc, out = _ejecuta(skill), None
        self.assertEqual(rc.returncode, 0, f"la herramienta fallo:\n{rc.stderr}")
        rc, out = _audita(skill)
        self.assertEqual(rc, 0, f"el guard no acepta lo que escribe la herramienta:\n{out}")

    def test_arregla_los_numeros_desfasados(self):
        repo, skill = self._repo()
        r = _ejecuta(skill)
        self.assertEqual(r.returncode, 0, f"la herramienta fallo:\n{r.stderr}")
        with open(os.path.join(repo, "README.md"), encoding="utf-8") as f:
            readme = f.read()
        # los numeros del README tienen que ser los del arbol, no los de antes
        n_root = len([f2 for f2 in os.listdir(os.path.join(skill, "scripts"))
                       if f2.endswith(".py")])
        self.assertIn(f"# {n_root} root + ", readme)
        with open(os.path.join(skill, "references", "mapa.md"), encoding="utf-8") as f:
            mapa = f.read()
        self.assertIn(f"{n_root} scripts,", mapa)

    def test_check_no_escribe(self):
        repo, skill = self._repo()
        antes = {}
        for ruta in (os.path.join(skill, "SKILL.md"),
                     os.path.join(skill, "references", "mapa.md"),
                     os.path.join(repo, "README.md")):
            with open(ruta, encoding="utf-8") as f:
                antes[ruta] = f.read()
        r = _ejecuta(skill, "--check")
        self.assertEqual(r.returncode, 0, f"--check fallo:\n{r.stderr}")
        for ruta, texto in antes.items():
            with open(ruta, encoding="utf-8") as f:
                self.assertEqual(f.read(), texto,
                                 f"--check escribio en {ruta}: un modo de solo informar que escribe es peor que no tenerlo")

    def test_sin_readme_no_falla(self):
        # la copia instalada no tiene README: la herramienta actualiza lo de
        # la skill y no se rompe
        skill = _copia_skill(os.path.join(self.dir, "instalada"))
        r = _ejecuta(skill)
        self.assertEqual(r.returncode, 0, f"sin README la herramienta fallo:\n{r.stderr}")
        rc, out = _audita(skill)
        self.assertEqual(rc, 0, f"el guard no acepta lo que escribe la herramienta:\n{out}")


if __name__ == "__main__":
    unittest.main()
