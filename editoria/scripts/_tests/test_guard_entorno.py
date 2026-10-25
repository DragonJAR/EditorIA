#!/usr/bin/env python3
"""Tests del guard de entorno: la suite da el mismo veredicto con repo y sin repo.

El fallo que motivo esto: la copia instalada de la skill NO tiene repo (es un
artefacto), pero los tests se desarrollan en el repo. Un test que asume el repo
- que da igual un `git rev-parse` que exista - PASA en el repo y CAE en la
copia. El verde de la puerta del repo es entonces verde de un sitio donde la
skill no vive, y no dice lo que parece que dice.

Ya paso con el test de la cabecera, antes de un parche. El parche lo arreglo,
pero el patron no se ha ido: por eso esto se MIDE en vez de recordarse.

Aqui se monta un arbol de mentira: una skill falsa con la suite REAL
(`_censo_clis.py`) y un unico test. El test de la MUTACION asume el repo, asi
que pasa con repo y cae sin repo: el guard tiene que verlo y nombrarlo.

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
GUARD = os.path.join(SCRIPTS, "_guard_entorno.py")

sys.path.insert(0, SCRIPTS)
import _guard_entorno as G  # noqa: E402


#: Un test que ASUME el repo: con repo pasa, sin repo cae. Es la mutacion.
TEST_ASUME_REPO = '''\
import subprocess
import unittest


class TestAsumeRepo(unittest.TestCase):
    def test_necesita_repo(self):
        r = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0,
                         "este test asume que hay repo: por eso hay que medirlo")
'''

#: El mismo test, HONESTO: si no hay repo, se salta y lo dice.
TEST_HONESTO = '''\
import subprocess
import unittest


class TestHonesto(unittest.TestCase):
    def test_necesita_repo(self):
        r = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            self.skipTest("sin repo: este test no puede hablar del commit")
        self.assertTrue(r.stdout.strip())
'''


def _git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args],
                          capture_output=True, text=True, timeout=60)


class GuardEntorno(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="editoria_entorno_test_")
        self.addCleanup(shutil.rmtree, self.dir, True)

    def _arbol(self, contenido_test, con_repo=True):
        """Monta una skill falsa con la suite real y UN test.

        Devuelve (ruta_de_la_skill, ruta_de_la_copia). La copia se hace en una
        carpeta FUERA del repo: si la copia quedara dentro, los dos entornos
        serian el mismo y el guard no tendria nada que comparar.
        """
        raiz = os.path.join(self.dir, "arbol")
        skill = os.path.join(raiz, "editoria")
        tests = os.path.join(skill, "scripts", "_tests")
        os.makedirs(tests, exist_ok=True)
        # la suite REAL: el guard tiene que medir la suite de verdad, no una
        # imitación que haria lo que el guard quiere ver
        shutil.copy2(os.path.join(SCRIPTS, "_censo_clis.py"),
                     os.path.join(skill, "scripts", "_censo_clis.py"))
        with open(os.path.join(tests, "test_asume_repo.py"), "w", encoding="utf-8") as fh:
            fh.write(contenido_test)
        if con_repo:
            _git(raiz, "init", "-q")
        copia = os.path.join(self.dir, "copia", "editoria")
        return skill, copia

    # --- la mutacion: el test que asume el repo tiene que caer --------------

    def test_un_test_que_asume_el_repo_no_es_honesto(self):
        """La MUTACION: si el guard no ve el test que asume el repo, no prueba nada."""
        skill, copia = self._arbol(TEST_ASUME_REPO)
        info = G.medir(skill, destino=copia, timeout=300)
        self.assertIs(info["honesta"], False,
                      f"un test que asume el repo hace la suite NO honesta: {info}")
        caidas = " ".join(info["copia"]["fallos"])
        self.assertIn("test_asume_repo", caidas,
                      f"el guard tiene que NOMBRAR el test que cae: {info['copia']['fallos']}")
        self.assertEqual(info["base"]["rc"], 0,
                         "con repo el test pasa: por eso la puerta del repo verdeada")
        self.assertNotEqual(info["copia"]["rc"], 0,
                            "sin repo el test cae: ese es el fallo que se veia tarde")

    def test_la_cli_sale_con_codigo_de_error_cuando_no_es_honesto(self):
        """La puerta tiene que poder FALLAR, no solo informar."""
        skill, copia = self._arbol(TEST_ASUME_REPO)
        # el guard mide la copia; para la base se le pasa el veredicto ya medido
        rc_base, salida_base, _fallos = G.correr_suite(skill, timeout=300)
        info = G.medir(skill, destino=copia, timeout=300,
                       veredicto_base=(rc_base, salida_base))
        self.assertIs(info["honesta"], False)
        r = subprocess.run([sys.executable, GUARD, "--base", skill, "--solo-copia",
                            "--json"], capture_output=True, text=True, timeout=600)
        self.assertEqual(r.returncode, 1,
                         f"con un test que no es honesto la CLI tiene que salir con 1 "
                         f"(salio {r.returncode})")
        self.assertIn("test_asume_repo", r.stdout,
                      "la salida tiene que nombrar el test que cae")

    # --- lo que NO es una falta ------------------------------------------------

    def test_un_test_que_se_salta_sin_repo_es_honesto(self):
        """El patron correcto: si no hay repo, se salta y lo dice."""
        skill, copia = self._arbol(TEST_HONESTO)
        info = G.medir(skill, destino=copia, timeout=300)
        self.assertIs(info["honesta"], True,
                      f"un test que se salta sin repo es honesto: {info}")

    def test_un_arbol_sin_repo_no_rompe_la_comparacion(self):
        """Si la base no tiene repo, se mide igual y se DICE que no hay comparacion."""
        skill, copia = self._arbol(TEST_HONESTO, con_repo=False)
        info = G.medir(skill, destino=copia, timeout=300)
        # sin repo en la base, la copia tampoco lo tiene: los dos entornos son
        # el mismo, asi que no hay nada dishonesto, pero tampoco comparacion
        self.assertEqual(info["base"]["repo"], "")
        self.assertEqual(info["copia"]["repo"], "")
        self.assertIs(info["honesta"], True,
                      f"sin repo en ningun lado no hay dishonesty: {info}")

    # --- el guard no se fia de su propia copia ---------------------------------

    def test_si_la_copia_queda_dentro_de_un_repo_la_medicion_no_vale(self):
        """La copia tiene que quedar SIN repo: si no, se mide dos veces lo mismo.

        Y si no se puede conseguir, el guard NO da un verde: dice que la
        medicion no vale. Un verde que no se midio no es un verde.
        """
        skill, _ = self._arbol(TEST_HONESTO)
        # destino DENTRO del repo: la copia heredaria el repo
        destino = os.path.join(os.path.dirname(skill), "copia_dentro")
        info = G.medir(skill, destino=destino, timeout=300)
        self.assertIs(info["honesta"], None,
                      f"una copia dentro de un repo no mide nada: {info}")
        self.assertIn("no vale", info["motivo"])

    def test_el_guard_verifica_que_la_copia_no_tiene_repo(self):
        """La copia aislada se comprueba, no se da por hecha."""
        skill, copia = self._arbol(TEST_HONESTO)
        G.medir(skill, destino=copia, timeout=300)
        self.assertEqual(G.repo_de(copia), "",
                         "la copia tiene que quedar sin repo, y eso se comprueba")

    # --- el guard no ensucia el arbol ------------------------------------------

    def test_el_guard_no_deja_basura_en_el_arbol_que_mide(self):
        """Medir no puede ensuciar lo que mide: si no, el siguiente verde ya no vale."""
        skill, copia = self._arbol(TEST_HONESTO)
        antes = sorted(os.listdir(skill))
        G.medir(skill, destino=copia, timeout=300)
        despues = sorted(os.listdir(skill))
        self.assertEqual(antes, despues,
                         f"el guard no puede dejar ficheros en la skill: {despues}")

    # --- el arbol real ----------------------------------------------------------

    def test_el_guard_no_se_marca_a_si_mismo(self):
        """El fuente del guard no puede contener una falta que el guard busca."""
        with open(GUARD, encoding="utf-8") as fh:
            texto = fh.read()
        # el guard no busca faltas de prosa: mira VEREDICTOS. Lo que se comprueba
        # es que el fichero es legible y que la funcion de fallos existe (si no,
        # un fallo al leer la salida pasaria desapercibido)
        self.assertIn("def fallos_de", texto)
        self.assertEqual(G.fallos_de("FAIL: test_x (mod.Clase)\n"),
                         ["FAIL: mod.Clase.test_x"])

    def test_la_salida_de_una_herramienta_no_es_un_test_caido(self):
        """Una herramienta que falla escribe "ERROR: ..." por stderr.

        Eso NO es un test caido: si el guard lo contara, el numero de "tests
        que no son honestos con el entorno" seria mentira, y el guard estaria
        contando ruido como si fuera un defecto.
        """
        ruido = ("ERROR: --hablantes: 'ANA' no es NOMBRE=RRGGBB (o usa --hablantes auto)\n"
                 "ERROR: paleta desconocida: no-existe. Disponibles: ambar, coral\n"
                 "FAIL: test_de_verdad (mod.Clase)\n")
        fallos = G.fallos_de(ruido)
        self.assertEqual(fallos, ["FAIL: mod.Clase.test_de_verdad"],
                         f"el ruido de las herramientas no es un test caido: {fallos}")


if __name__ == "__main__":
    unittest.main()
