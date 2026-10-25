#!/usr/bin/env python3
"""Tests de scripts/actualizar_conteos.py.

La herramienta reescribe los conteos que la skill enuncia (referencias,
scripts raiz, herramientas de ffmpeg, suites). El riesgo de una herramienta
así es que se quede vieja: por eso cuenta con la MISMA fuente que el guard
y por eso hay un test que dice que lo que escribe la herramienta es
exactamente lo que el guard despues comprueba.

Y hay DOS cifras de tests que no son la misma: las SUITES (los modulos
test_*.py, que son los que enumera el SKILL.md) y los ARCHIVOS en _tests/
(que es lo que suma el total de scripts del README). Un modulo de apoyo es
un archivo y no es una suite: confundir las dos deja al guard pidiendo una
suite que no existe, y a la herramienta sin poder satisfacerlo.

Tambien cubre las dos topologias: con repo (donde hay README que
actualizar) y sin repo (la copia instalada), donde la herramienta tiene que
reelegir solo lo de la skill y no fallar.

Run with: python3 -m unittest discover -s SKILL/scripts/_tests
"""

import json
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

    def test_el_numero_del_contrato_cli_lo_escribe_la_herramienta(self):
        """El contrato de CLI declara "N de las M cumplen el contrato".

        Ese numero vivia en la prosa y NADIE lo reescribia: cada CLI nueva de
        `ffmpeg_tools/` lo dejaba viejo, y el guard lo senalaba (conteo
        obsoleto) sin que hubiera forma de arreglarlo con la herramienta
        canonica. Aqui se comprueba el ciclo entero: se rompe el numero, el
        guard lo ve, la herramienta lo arregla, y el guard ya no lo ve.

        El guard avisa (no falla) de lo que solo se desvia en el ARBOL de
        trabajo: lo publicado es un fallo, lo que aun no ha salido es un
        aviso con la herramienta como remedio. Por eso el veredicto de este
        test mira lo que el guard DICE, no solo su codigo de salida.
        """
        repo, skill = self._repo()
        contrato = os.path.join(skill, "references", "cli-contract.md")
        with open(contrato, encoding="utf-8") as f:
            txt = f.read()
        # la mutacion conserva COMO esta partida la frase: si se partiera de
        # otra forma, el guard no la encontraria y no estariamos midiendo el
        # numero sino el fallo de encontrar la frase
        roto = re.sub(r"(\d+)(\s+)de(\s+)las(\s+)(\d+)(\s+)cumplen(\s+)el(\s+)contrato",
                      r"1\2de\3las\4 2\6cumplen\7el\8contrato", txt)
        self.assertNotEqual(roto, txt, "no se pudo romper el numero del contrato")
        with open(contrato, "w", encoding="utf-8") as f:
            f.write(roto)
        # el guard lo ve (como aviso: el arbol todavia no esta publicado)
        rc, out = _audita(skill)
        self.assertIn("conteo obsoleto", out,
                      f"el guard no vio el numero roto del contrato:\n{out}")
        self.assertIn("cli-contract.md", out)
        # la herramienta lo arregla
        r = _ejecuta(skill)
        self.assertEqual(r.returncode, 0, f"la herramienta fallo:\n{r.stderr}")
        # y el guard ya no lo ve
        rc, out = _audita(skill)
        self.assertNotIn("cli-contract.md", out,
                         f"el guard sigue viendo el numero roto:\n{out}")
        # y la frase sigue partida como estaba (la prosa no se deja en una
        # linea larga): el numero se conserva, la forma tambien
        with open(contrato, encoding="utf-8") as f:
            final = f.read()
        self.assertIn("cumplen el\ncontrato", final,
                      "la frase tiene que seguir partida como estaba")

    def test_el_check_dice_que_esta_desfasado(self):
        # el --check tiene que decir QUE numero esta mal y cual seria, no solo
        # en que archivo: para eso lo usa el guard como remedy
        skill = _copia_skill(os.path.join(self.dir, "instalada"))
        mapa = os.path.join(skill, "references", "mapa.md")
        with open(mapa, encoding="utf-8") as f:
            txt = f.read()
        with open(mapa, "w", encoding="utf-8") as f:
            f.write(re.sub(r"\d+ referencias, \d+ scripts", "99 referencias, 99 scripts", txt))
        r = subprocess.run([sys.executable, os.path.join(skill, "scripts", "actualizar_conteos.py"),
                            "--check"], capture_output=True, text=True, timeout=300)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("99 referencias", r.stdout, "el --check tiene que decir que numero dice")
        self.assertIn("dice:", r.stdout)
        self.assertIn("dira:", r.stdout)

    def test_un_modulo_de_apoyo_no_cuenta_como_suite(self):
        # un .py que NO es test_*.py dentro de _tests/ es un modulo de apoyo:
        # es un archivo mas, pero no una suite. las dos cifras son distintas y
        # cada una va a su sitio: el encabezado del mapa cuenta SUITES, el
        # desglose del README cuenta ARCHIVOS en _tests/.
        repo, skill = self._repo()
        with open(os.path.join(skill, "scripts", "_tests", "apoyo.py"), "w",
                  encoding="utf-8") as f:
            f.write("# modulo de apoyo: no es una suite\n")
        r = _ejecuta(skill)
        self.assertEqual(r.returncode, 0, f"la herramienta fallo:\n{r.stderr}")
        tests_dir = os.path.join(skill, "scripts", "_tests")
        nombres = os.listdir(tests_dir)
        n_suites = len([x for x in nombres if x.startswith("test_") and x.endswith(".py")])
        n_archivos = len([x for x in nombres if x.endswith(".py") and x != "__init__.py"])
        self.assertGreater(n_archivos, n_suites,
                           "el escenario no prueba nada: los dos numeros coinciden")
        with open(os.path.join(skill, "references", "mapa.md"), encoding="utf-8") as f:
            mapa = f.read()
        self.assertIn(f"y {n_suites} suites de tests", mapa,
                      "el encabezado del mapa cuenta SUITES, no archivos")
        with open(os.path.join(repo, "README.md"), encoding="utf-8") as f:
            readme = f.read()
        self.assertIn(f"+ {n_archivos} in _tests/ ", readme,
                      "el desglose del README cuenta ARCHIVOS en _tests/")
        # y el guard acepta lo que escribio la herramienta
        rc, out = _audita(skill)
        self.assertEqual(rc, 0, f"el guard no acepta lo que escribe la herramienta:\n{out}")

    def test_una_suite_nueva_no_revienta_la_herramienta(self):
        # anadir una suite es justo cuando se usa esta herramienta. si el
        # informe reventara al desempaquetar el cambio de la lista, el fallo
        # saldria con traceback y no diria nada: el que lo ve tendria que
        # leer el traceback para saber que hacer.
        skill = _copia_skill(os.path.join(self.dir, "instalada"))
        with open(os.path.join(skill, "scripts", "_tests", "test_nueva_suite.py"), "w",
                  encoding="utf-8") as f:
            f.write("import unittest\n")
        r = subprocess.run([sys.executable, os.path.join(skill, "scripts", "actualizar_conteos.py"),
                            "--check"], capture_output=True, text=True, timeout=300)
        self.assertEqual(r.returncode, 0, f"la herramienta revento:\n{r.stderr}")
        self.assertNotIn("Traceback", r.stderr, "un fallo con traceback no dice que hacer")
        self.assertIn("SKILL.md", r.stdout, "la lista de suites del SKILL.md esta vieja")
        self.assertIn("dira:", r.stdout, "el informe tiene que decir cual sera la lista")
        self.assertIn("test_nueva_suite.py", r.stdout,
                      "el informe tiene que decir QUE suite falta, no la lista entera")

    def test_la_reescritura_no_secome_el_resto_del_archivo(self):
        # una reescritura que se come la cola (la seccion de ejemplos, los
        # pasos que van despues) es un fallo silencioso y DESTRUCTIVO: el
        # archivo queda mas corto, el --check dice "nada" (ya no encuentra
        # nada que cambiar) y nadie se entera. Le pasa a esta herramienta.
        repo, skill = self._repo()
        ruta = os.path.join(skill, "SKILL.md")
        with open(ruta, encoding="utf-8") as f:
            antes = f.read()
        # el fragmento que reescribe la herramienta, con SU patron (en el
        # SKILL.md hay mas de un "pass via": no vale cortarr por el primero)
        mt = re.search(r"(unit tests in )(.+?)( pass via)", antes)
        self.assertIsNotNone(mt, "el SKILL.md tiene que traer la lista de suites")
        pre = antes[:mt.start()]
        post = antes[mt.end():]
        # una suite nueva: el CANONICO tiene que cambiarla. El SKILL.md ya no
        # enumera las suites (esa lista se movio de sitio: era ruido para el
        # agente y una bomba de relojería para el limite de palabras).
        with open(os.path.join(skill, "scripts", "_tests", "test_nueva_suite.py"), "w",
                  encoding="utf-8") as f:
            f.write("import unittest\n")
        r = _ejecuta(skill)
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(ruta, encoding="utf-8") as f:
            despues = f.read()
        self.assertTrue(despues.startswith(pre), "la reescritura se come el principio")
        self.assertTrue(despues.endswith(post), "la reescritura se come la cola")
        self.assertNotIn("`scripts/_tests/test_", despues,
                         "el SKILL.md no debe enumerar las suites: la lista vive "
                         "en el canonico (scripts/data/suites.json)")
        with open(os.path.join(skill, "scripts", "data", "suites.json"),
                  encoding="utf-8") as f:
            suites = (json.load(f) or {}).get("suites") or []
        self.assertIn("test_nueva_suite.py", suites,
                      "la suite nueva tiene que aparecer en el canonico")

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
