#!/usr/bin/env python3
"""Tests del envoltorio que cierra un tip: una linea, tres mediciones.

Cerrar un tip son tres mediciones (la puerta del repo, el entorno sin repo y
la copia instalada) y una mirada manual. La mirada manual es donde se cuelan
los errores: el log equivocado, la puerta corrida en el arbol COMPARTIDO
(mide lo que otra sesion esta escribiendo por debajo) y el paso olvidado.

El envoltorio existe para que eso no dependa de la memoria. Su MUTACION es
exactamente eso: si dice "esta cerrado" cuando algo fallo, es peor que no
decir nada, porque el verde falso se publica.

Aqui no se paga la puerta de verdad: las tres mediciones se inyectan. Lo que
se comprueba de verdad es la MECANICA del envoltorio: que mide en un worktree
aislado, que no publica, que se para si hay otra puerta corriendo, y que una
medicion roja IMPIDE el cierre.

Run with: python3 -m unittest discover -s SKILL/scripts/_tests
"""

import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
BASE = os.path.dirname(SCRIPTS)
CERRAR = os.path.join(SCRIPTS, "_cerrar_tip.py")

sys.path.insert(0, SCRIPTS)
import _cerrar_tip as C  # noqa: E402


def _git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args],
                          capture_output=True, text=True, timeout=60)


def _puerta(ok=True, veredicto_suite=0, linea_suite=None):
    """Una puerta de mentira: verde con la linea de la suite, o roja.

    La linea se escribe EXACTA como la escribe la puerta de verdad ("OK" mas
    tres espacios, porque su `check` pone "OK  " y anade otro): un fixture
    que no se parece al original es un fixture que no prueba nada (asi se
    colaron 14 fallos falsos en la primera medicion).

    `linea_suite` permite los tres casos: con la linea y el veredicto (lo
    normal), sin veredicto pero CON linea (el envoltorio lo lee del log), y
    sin linea (el log no dice nada: entonces no se puede cerrar).
    """
    if linea_suite is None:
        linea_suite = veredicto_suite is not None

    def _f(ruta_skill, log):
        with open(log, "w", encoding="utf-8") as fh:
            if ok:
                fh.write("commit medido: abc1234 (main)\n")
                if linea_suite:
                    fh.write("OK   tests unitarios de scripts/_tests (589 OK)\n")
                fh.write("SKILL VALIDO\n")
            else:
                fh.write("commit medido: abc1234 (main)\n"
                         "FAIL  tests unitarios de scripts/_tests (2 fallos)\n"
                         "2 FALLO(S)\n")
        return {"ok": ok, "rc": 0 if ok else 1, "fallos": 0 if ok else 2,
                "detalle": "sin fallos" if ok else "2 FALLO(S)",
                "segundos": 0.1, "log": log, "veredicto_suite": veredicto_suite}
    return _f


def _entorno(ok=True):
    def _f(ruta_skill, veredicto_suite, log):
        with open(log, "w", encoding="utf-8") as fh:
            fh.write("OK  la suite es honesta con el entorno\n" if ok else
                     "FALLA  la suite no es honesta con el entorno: 1 test cae\n")
        return {"ok": ok, "detalle": ("la suite es honesta con el entorno" if ok else
                                      "1 test cae sin repo"),
                "segundos": 0.1, "log": log}
    return _f


def _copia(ok=True):
    def _f(raiz, log):
        with open(log, "w", encoding="utf-8") as fh:
            fh.write("la copia coincide con lo publicado\n" if ok else
                     "la copia se diferencia de lo publicado\n")
        return {"ok": ok, "rc": 0, "detalle": ("coincide" if ok else
                                               "la copia NO coincide con lo publicado"),
                "segundos": 0.1, "log": log}
    return _f


class CerrarTip(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="editoria_cerrar_")
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.raiz = os.path.join(self.dir, "repo")
        os.makedirs(self.raiz)
        _git(self.raiz, "init", "-q")
        # el repo necesita un commit: sin HEAD no hay tip que cerrar
        with open(os.path.join(self.raiz, "SKILL.md"), "w", encoding="utf-8") as fh:
            fh.write("---\nname: editoria\ndescription: fixture\n---\n")
        _git(self.raiz, "add", "-A")
        _git(self.raiz, "-c", "user.email=t@t.t", "-c", "user.name=t",
             "commit", "-q", "-m", "base")
        # un remoto de verdad, para comprobar que el envoltorio NO publica
        self.remoto = os.path.join(self.dir, "remoto.git")
        subprocess.run(["git", "init", "--bare", "-q", self.remoto],
                       capture_output=True, text=True, timeout=60)
        _git(self.raiz, "remote", "add", "origin", self.remoto)
        _git(self.raiz, "push", "-q", "origin", "HEAD:refs/heads/main")
        self.log_dir = os.path.join(self.dir, "logs")

    def _cerrar(self, **kw):
        # El guard de concurrencia se INYECTA, como las tres mediciones: si
        # dependiera del estado real de la maquina, el verde de la suite
        # dependeria de si otra sesion esta midiendo a la vez. Y el fallo
        # salia como un ROJO DE PUERTA (la suite del gate veia a la puerta
        # de la otra sesion y se negaba a cerrar), no como "no se mide en
        # paralelo": un fallo de entorno disfrazado de fallo del producto.
        original = C._puertas_vivas
        C._puertas_vivas = kw.pop("puertas_vivas", lambda: [])
        self.addCleanup(lambda: setattr(C, "_puertas_vivas", original))
        kw.setdefault("raiz", self.raiz)
        kw.setdefault("log_dir", self.log_dir)
        kw.setdefault("puerta", _puerta())
        kw.setdefault("entorno", _entorno())
        kw.setdefault("copia", _copia())
        return C.cerrar(**kw)

    # --- la mutacion: un verde falso es peor que no decir nada ---------------

    def test_las_tres_mediciones_en_verde_cierran_el_tip(self):
        """El camino bueno: todo verde y una sola linea que lo dice."""
        v = self._cerrar()
        self.assertTrue(v["cerrado"], f"todo verde tiene que cerrar: {v}")
        self.assertIn("repo verde", v["motivo"])

    def test_la_puerta_roja_impide_el_cierre(self):
        """La MUTACION: si la puerta falla, NO se puede cerrar."""
        v = self._cerrar(puerta=_puerta(ok=False))
        self.assertFalse(v["cerrado"], f"una puerta roja no cierra nada: {v}")
        self.assertIn("puerta", v["motivo"])

    def test_el_entorno_dishonesto_impide_el_cierre(self):
        """La MUTACION: si la suite no es honesta con el entorno, NO se cierra."""
        v = self._cerrar(entorno=_entorno(ok=False))
        self.assertFalse(v["cerrado"], f"un entorno dishonesto no cierra nada: {v}")
        self.assertIn("honesta", v["motivo"])

    def test_la_copia_desfasada_impide_el_cierre(self):
        """La MUTACION: si la copia instalada no es lo publicado, NO se cierra."""
        v = self._cerrar(copia=_copia(ok=False))
        self.assertFalse(v["cerrado"], f"una copia desfasada no cierra nada: {v}")
        self.assertIn("copia", v["motivo"])

    def test_el_veredicto_de_la_suite_se_lee_del_log_real(self):
        """La linea de la puerta tiene TRES espacios, no dos.

        El `check` de la puerta escribe "OK  " y anade un espacio mas. Un
        `startswith` de dos espacios NO casa, y el envoltorio se queda sin
        veredicto: no cierra. Asi que el envoltorio lee el log con un regex.
        """
        rc, _ = C._veredicto_suite_desde_puerta(
            "commit medido: abc (main)\n"
            "OK   tests unitarios de scripts/_tests (609 OK)\n"
            "SKILL VALIDO\n")
        self.assertEqual(rc, 0, "el veredicto de la suite tiene que leerse del log real")
        rc, _ = C._veredicto_suite_desde_puerta(
            "FAIL  tests unitarios de scripts/_tests (2 fallos)\n2 FALLO(S)\n")
        self.assertEqual(rc, 1, "una suite que cae se lee como caida")
        self.assertIsNone(C._veredicto_suite_desde_puerta("nada de esto\n")[0],
                          "si no hay linea, no se inventa el veredicto")

    def test_el_veredicto_cae_del_log_cuando_la_puerta_no_lo_da(self):
        """El log es la fuente: si la puerta no trae el veredicto, se lee de alli."""
        v = self._cerrar(puerta=_puerta(ok=True, veredicto_suite=None,
                                        linea_suite=True))
        self.assertTrue(v["cerrado"],
                        f"el veredicto se lee del log de la puerta: {v}")

    def test_un_veredicto_de_suite_ilegible_impide_el_cierre(self):
        """Si no se puede leer el veredicto de la suite, no se mide el entorno.

        Y no se dice "cerrado": no se sabe si el entorno es honesto.
        """
        v = self._cerrar(puerta=_puerta(ok=True, veredicto_suite=None,
                                        linea_suite=False))
        self.assertFalse(v["cerrado"],
                         f"sin veredicto de suite no se puede cerrar: {v}")
        self.assertIn("suite", v["motivo"])

    # --- el aislamiento: la puerta no se mide en el arbol compartido -----------

    def test_la_medicion_no_toca_el_arbol_compartido(self):
        """La puerta se corre en un WORKTREE AISLADO, no en el arbol de trabajo.

        Medir en el arbol compartido es medir lo que otra sesion esta
        escribiendo por debajo: el veredicto no es de nada.
        """
        vistas = {}

        def _puerta_que_mira(ruta_skill, log):
            vistas["ruta"] = ruta_skill
            return _puerta()(ruta_skill, log)

        v = self._cerrar(puerta=_puerta_que_mira)
        self.assertTrue(v["cerrado"])
        self.assertNotIn(os.path.realpath(self.raiz), os.path.realpath(vistas["ruta"]),
                         "la puerta se ha corrido en el arbol compartido")
        self.assertIn(os.path.join("wt", "editoria"), vistas["ruta"],
                      "la puerta se ha corrido en el worktree aislado")

    def test_no_publica_nada(self):
        """El envoltorio mide: NO publica. Publicar es de quien publica."""
        remoto_antes = subprocess.run(["git", "--git-dir", self.remoto,
                                       "rev-parse", "refs/heads/main"],
                                      capture_output=True, text=True, timeout=60).stdout.strip()
        self._cerrar()
        remoto_despues = subprocess.run(["git", "--git-dir", self.remoto,
                                         "rev-parse", "refs/heads/main"],
                                        capture_output=True, text=True, timeout=60).stdout.strip()
        self.assertEqual(remoto_antes, remoto_despues,
                         "el envoltorio no puede publicar nada")

    def test_se_para_si_hay_otra_puerta_corriendo(self):
        """Dos validaciones a la vez se pisan: el fallo sale como del producto."""
        v = self._cerrar(puertas_vivas=lambda: [4242])
        self.assertFalse(v["cerrado"], f"con otra puerta corriendo no se mide: {v}")
        self.assertIn("puerta", v["motivo"])
        self.assertIn("4242", v["motivo"], "el motivo tiene que decir que puerta")

    def test_un_comando_que_mentione_la_puerta_no_cuenta_como_puerta(self):
        """Un guard que se dispara con su propio sentinel no vigila nada.

        `pgrep -f validate_skill.py` (sin ancla) casa con CUALQUIER linea de
        comandos que mencione ese nombre: y los comandos de inspeccion que
        uno escribe para mirar si hay una puerta corriendo son justamente
        esos. O sea: el guard se disparaba solo con el comando que lo vigila
        (y el envoltorio se negaba a cerrar sin motivo).
        """
        senuelo = subprocess.Popen(
            ["/bin/bash", "-c", "echo validate_skill.py; sleep 30"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.addCleanup(senuelo.kill)
        time.sleep(0.3)
        vivos = C._puertas_vivas()
        self.assertNotIn(senuelo.pid, vivos,
                         "un comando que solo MENCIONA la puerta no es una puerta")

    def test_la_puerta_que_me_lanzo_no_es_otra_puerta(self):
        """La puerta que nos corre NO cuenta como medicion ajena: somos parte de ella.

        Si contara, la suite de una puerta llamaria a este envoltorio, el
        envoltorio veria "otra puerta corriendo" y se negaria a cerrar: el
        fallo salia como un ROJO DE PUERTA en vez de como "no se mide en
        paralelo". Es el fallo de entorno disfrazado de fallo del producto.
        """
        self.assertNotIn(os.getpid(), C._ancestros(),
                         "un proceso no es su propio ancestro")
        # el padre de este proceso es un ancestro: la puerta que nos lanzo
        # (o el shell) esta en la cadena
        padre = os.getppid()
        self.assertIn(padre, C._ancestros(),
                      "el padre tiene que estar en la cadena de ancestros")

    # --- el tip que no existe -------------------------------------------------

    def test_un_tip_que_no_existe_no_cierra_nada(self):
        v = self._cerrar(tip="deadbeefdeadbeefdeadbeefdeadbeefdeadbeef")
        self.assertFalse(v["cerrado"])
        self.assertIn("no existe", v["motivo"])

    # --- la CLI ----------------------------------------------------------------

    def test_la_cli_con_un_tip_inexistente_sale_con_error(self):
        """La CLI tiene que poder FALLAR, no solo informar."""
        r = subprocess.run([sys.executable, CERRAR, "--raiz", self.raiz,
                            "--tip", "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"],
                           capture_output=True, text=True, timeout=300)
        self.assertEqual(r.returncode, 1,
                         f"con un tip inexistente la CLI sale con 1 (salio {r.returncode})")
        self.assertIn("NO ESTA CERRADO", r.stdout)
        self.assertNotIn("Traceback", r.stderr,
                         "la CLI no puede reventar con un traceback: es lo que ve el agente")

    def test_la_cli_tiene_ayuda(self):
        """`--help` no puede reventar: es lo primero que un agente ejecuta."""
        r = subprocess.run([sys.executable, CERRAR, "--help"],
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0)
        self.assertIn("--tip", r.stdout)


if __name__ == "__main__":
    unittest.main()
