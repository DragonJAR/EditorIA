#!/usr/bin/env python3
"""Tests de la cabecera del validador: el log dice de que commit es.

El fallo que motivo esto: un log dice "SKILL VALIDO" sin decir DE QUE
EJECUCION es. Hay docenas de logs de validate_skill de noches distintas,
todos con el mismo nombre base, y varios terminan en "SKILL VALIDO". Leer
el verde del fichero equivocado es atribuir a HOY el veredicto de AYER: es
un fallo silencioso, porque el texto verde no miente, solo responde a una
pregunta que nadie hacia.

La regla: el veredicto lleva su contexto. La cabecera va en la PRIMERA
linea del log, y dice el commit medido.

Y el caso que hace que esto no sea decorativo: la COPIA INSTALADA no tiene
`.git`, asi que ahi no hay commit que medir. Lo que no puede es inventar un
sha: dice "SIN REPO" y sigue. Un guard que se salta una superficie tiene
que DECIR que se la salta.

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
SKILL = os.path.dirname(SCRIPTS)
VALIDADOR = os.path.join(SCRIPTS, "validate_skill.py")


def _cabecera(*args, cwd=None, script=None):
    """Corre el validador en modo cabecera y devuelve su primera linea.

    Ojo: BASE sale de __file__, no del cwd. Para medir OTRO arbol hay que
    ejecutar SU copia del script: correr el del repo desde otro directorio
    seguiria midiendo el repo.
    """
    proc = subprocess.run([sys.executable, script or VALIDADOR, "--cabecera", *args],
                          capture_output=True, text=True, cwd=cwd, timeout=120)
    salida = proc.stdout.strip().splitlines()
    return (salida[0] if salida else ""), proc.returncode


def _git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True,
                          text=True, timeout=60)


class TestCabeceraCommit(unittest.TestCase):

    def test_en_el_repo_dice_el_commit_que_se_mide(self):
        """En el repo, la cabecera dice el commit REAL del tip que se midio.

        OJO: la copia instalada NO tiene `.git`, y ahi este test no puede
        hablar del commit: se salta. Lo de "SIN REPO" lo prueba el test
        siguiente, con un arbol sin repo de verdad.
        """
        esperado = subprocess.run(["git", "-C", SKILL, "rev-parse", "--short", "HEAD"],
                                   capture_output=True, text=True, timeout=30).stdout.strip()
        if not esperado:
            self.skipTest("la skill bajo prueba no tiene repo (copia instalada): "
                          "el commit lo mide el otro test, con un repo de verdad")
        linea, rc = _cabecera()
        self.assertEqual(rc, 0, f"el modo cabecera debe salir con 0: {linea}")
        self.assertIn("commit medido:", linea)
        self.assertNotIn("SIN REPO", linea,
                         f"en el repo hay repo: {linea}")
        self.assertIn(esperado, linea,
                      f"la cabecera ({linea}) no dice el commit medido ({esperado})")

    def test_sin_repo_lo_dice_y_no_inventa(self):
        """Sin `.git`, dice SIN REPO: un sha inventado seria una mentira."""
        tmp = tempfile.mkdtemp(prefix="editoria_sin_repo_")
        try:
            destino = os.path.join(tmp, "editoria", "scripts")
            os.makedirs(destino)
            copia = os.path.join(destino, "validate_skill.py")
            shutil.copy2(VALIDADOR, copia)
            linea, rc = _cabecera(cwd=tmp, script=copia)
            self.assertEqual(rc, 0)
            self.assertTrue(linea.startswith("commit medido: SIN REPO"),
                            f"sin repo la cabecera lo dice: {linea}")
            self.assertIsNone(re.search(r"\b[0-9a-f]{7,40}\b", linea),
                              f"sin repo no se inventa un sha: {linea}")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_el_arbol_sucio_lo_dice(self):
        """Con cambios sin commitear, la cabecera lo dice.

        El veredicto entonces NO es del commit: es del arbol que se midio.
        Decir solo el sha seria mentirle al que lea el log despues.
        """
        tmp = tempfile.mkdtemp(prefix="editoria_repo_sucio_")
        try:
            destino = os.path.join(tmp, "editoria", "scripts")
            os.makedirs(destino)
            copia = os.path.join(destino, "validate_skill.py")
            shutil.copy2(VALIDADOR, copia)
            _git(tmp, "init", "-q")
            _git(tmp, "add", "-A")
            _git(tmp, "-c", "user.email=t@t.t", "-c", "user.name=t", "commit",
                 "-q", "-m", "base")

            limpio, rc = _cabecera(cwd=tmp, script=copia)
            self.assertEqual(rc, 0)
            self.assertIn("commit medido:", limpio)
            self.assertNotIn("SIN REPO", limpio, f"este repo si es repo: {limpio}")
            self.assertNotIn("CAMBIOS SIN COMMITEAR", limpio,
                             f"el arbol esta limpio: {limpio}")

            with open(copia, "a", encoding="utf-8") as fh:
                fh.write("\n# un cambio sin commitear\n")

            sucio, rc = _cabecera(cwd=tmp, script=copia)
            self.assertEqual(rc, 0)
            self.assertIn("ARBOL CON CAMBIOS SIN COMMITEAR", sucio,
                          f"el arbol esta sucio y la cabecera lo dice: {sucio}")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_la_cabecera_va_primero_en_la_corrida_completa(self):
        """La primera linea del log completo es la cabecera: va al principio.

        Se lee la primera linea y se corta el proceso: la cabecera se
        imprime antes de cualquier check, asi que no hace falta pagar la
        puerta entera para comprobarlo.
        """
        proc = subprocess.Popen([sys.executable, "-u", VALIDADOR],
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                text=True)
        try:
            primera = proc.stdout.readline().strip()
        finally:
            proc.kill()
            proc.wait(timeout=30)
            proc.stdout.close()
        self.assertTrue(primera.startswith("commit medido:"),
                        f"la primera linea del log debe ser la cabecera: {primera!r}")


if __name__ == "__main__":
    unittest.main()
