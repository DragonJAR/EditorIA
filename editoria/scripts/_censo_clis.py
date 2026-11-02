#!/usr/bin/env python3
"""_censo_clis.py — que CLI ejecuta DE VERDAD la suite, medido, no declarado.

Por que existe: el mapa de CLIs verificadas (scripts/data/cli_verificadas.json)
decia que un test cubria una CLI. Eso es una DECLARACION: si el test existe
pero ha dejado de ejecutar la CLI (alguien lo edito, o la CLI cambio de
nombre), el mapa sigue mintiendo y el guard no se entera. La unica manera de
que el mapa sea verdad es medirlo.

Y la medicion sale gratis: `validate_skill.py` YA corre la suite entera en
cada corrida. Con este modulo, esa misma corrida ademas deja registrado que
scripts se ejecutaron de verdad, y el guard contrasta el mapa declarado con
el mapa medido.

Que NO sirve para medir (y por que):
  · escanear los tests por el nombre del script: un nombre en un comentario
    no ejecuta nada, y una asercion que menciona un script lo hace pasar
    por ejecutado. Ahi se esconden cuatro CLIs que nunca se ejecutaron.
  · este modulo instrumenta `subprocess.run`/`Popen` durante la suite
    REAL: lo que se registra es lo que se ejecuta.

Uso:
    python3 scripts/_censo_clis.py --salida mapa.json   # corre la suite y mide
    python3 scripts/_censo_clis.py --escribir             # regenera el mapa
    python3 scripts/_censo_clis.py --comparar             # contrasta con el mapa
    python3 scripts/_censo_clis.py --test-dir carpeta      # mide solo esa carpeta
"""
import json
import os
import subprocess
import sys
import unittest

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(BASE, "scripts")
TESTS = os.path.join(SCRIPTS, "_tests")
MAPA = os.path.join(SCRIPTS, "data", "cli_verificadas.json")


def _scripts_de_la_skill():
    """Las rutas relativas de los scripts de la skill (con su carpeta)."""
    salida = set()
    for raiz, _dirs, files in os.walk(SCRIPTS):
        if "__pycache__" in raiz:
            continue
        for f in files:
            if f.endswith(".py"):
                salida.add(os.path.relpath(os.path.join(raiz, f), BASE).replace("\\", "/"))
    return salida


def _normaliza(ruta, scripts):
    """La ruta de la skill a la que pertenece un script ejecutado (puede
    ser una COPIA en un directorio temporal: los tests montan la skill
    en un temporal y ejecutan la copia)."""
    r = ruta.replace("\\", "/")
    for s in scripts:
        if r.endswith(s):
            return s
    return None


def _fichero_del_test(test):
    """El FICHERO real del test, no su nombre de modulo.

    El mapa dice que test ejecuto cada CLI, y ese dato tiene que servir para
    algo: localizar el fichero. Un nombre inventado (un fichero de test que no
    existe en ningun sitio) es un puntero a nada, que es justo lo que este
    modulo existe para evitar. Si el test vive fuera de la skill, se devuelve
    None y se cae al nombre por defecto.

    Y un detalle que parece de estilo y no lo es: aqui no se escribe
    NINGUNA ruta de ejemplo que no exista de verdad. El guard de enlaces
    rotos lee tambien los .py, y una ruta inventada en un comentario es un
    enlace roto: el que la lea buscara un fichero que no esta.
    """
    mod = sys.modules.get(test.__class__.__module__)
    fichero = getattr(mod, "__file__", None)
    if not fichero:
        return None
    rel = os.path.relpath(os.path.abspath(fichero), BASE).replace("\\", "/")
    return None if rel.startswith("..") else rel


def medir_suite(test_dir=None, verbosity=0):
    """Corre la suite instrumentando subprocess. Devuelve (codigo, salida, mapa).

    El mapa es {script de la skill: [fichero de test que lo ejecuto]}.
    """
    test_dir = test_dir or TESTS
    scripts = _scripts_de_la_skill()
    registro = {}
    _actual = [None]
    _run, _popen = subprocess.run, subprocess.Popen

    def _nota(cmd):
        try:
            if not isinstance(cmd, (list, tuple)) or not cmd:
                return
            if "python" not in os.path.basename(str(cmd[0])):
                return
            for a in cmd[1:]:
                a = str(a)
                if not a.endswith(".py"):
                    continue
                rel = _normaliza(a, scripts)
                if rel:
                    registro.setdefault(_actual[0], set()).add(rel)
        except Exception:
            pass

    def run(cmd, *a, **k):
        _nota(cmd)
        return _run(cmd, *a, **k)

    def Popen(cmd, *a, **k):
        _nota(cmd)
        return _popen(cmd, *a, **k)

    subprocess.run = run
    subprocess.Popen = Popen

    class _Espia(unittest.TextTestResult):
        def startTest(self, test):
            _actual[0] = _fichero_del_test(test) or (
                "scripts/_tests/" + test.id().split(".")[0] + ".py")
            return super().startTest(test)

    try:
        loader = unittest.TestLoader()
        suite = loader.discover(test_dir)
        runner = unittest.TextTestRunner(resultclass=_Espia, verbosity=verbosity)
        res = runner.run(suite)
        codigo = 0 if res.wasSuccessful() else 1
    finally:
        subprocess.run = _run
        subprocess.Popen = _popen

    mapa = {}
    for test, scripts_ejecutados in registro.items():
        for s in scripts_ejecutados:
            mapa.setdefault(s, set()).add(test)
    mapa = {k: sorted(v) for k, v in sorted(mapa.items()) if v}
    return codigo, mapa


def _leer_mapa(ruta=MAPA):
    if not os.path.exists(ruta):
        return {}
    try:
        with open(ruta, encoding="utf-8") as fh:
            return (json.load(fh) or {}).get("verificadas") or {}
    except (OSError, ValueError):
        return {}


def _diferencias(declarado, medido):
    """(declaradas que no se ejecutan, ejecutadas que no estan declaradas)."""
    dec = {k: set(v) for k, v in declarado.items()}
    med = {k: set(v) for k, v in medido.items()}
    sin_ejecutar = {k: sorted(v) for k, v in dec.items() if k not in med}
    sin_declarar = {k: sorted(v) for k, v in med.items() if k not in dec}
    return sin_ejecutar, sin_declarar


def main():
    import argparse
    ap = argparse.ArgumentParser(description="censo de CLIs ejecutadas de verdad")
    ap.add_argument("--salida", default=None,
                    help="escribe aqui el mapa medido (JSON)")
    ap.add_argument("--escribir", action="store_true",
                    help="regenera scripts/data/cli_verificadas.json con lo medido")
    ap.add_argument("--comparar", action="store_true",
                    help="contrasta el mapa declarado con el medido")
    ap.add_argument("--verbosidad", type=int, default=0)
    ap.add_argument("--test-dir", default=None,
                    help="mide solo los tests de esta carpeta (por defecto, "
                         "scripts/_tests). Sirve para que un test pueda ejecutar "
                         "este modulo de verdad, sin correr la suite entera: la "
                         "mecanica es la misma, en pequena.")
    a = ap.parse_args()

    test_dir = a.test_dir
    if test_dir and not os.path.isabs(test_dir):
        test_dir = os.path.join(BASE, test_dir)
    codigo, medido = medir_suite(test_dir=test_dir, verbosity=a.verbosidad)

    if a.salida:
        with open(a.salida, "w", encoding="utf-8") as fh:
            json.dump(medido, fh, indent=1, sort_keys=True)

    if a.escribir:
        doc = {
            "_que_es": "Que CLI se EJECUTA de verdad, y en que test. Se mide "
                       "instrumentando subprocess durante la suite real (leer los "
                       "tests no vale: un nombre en un comentario no ejecuta nada). "
                       "El guard (auditar_mapa.py) exige que toda CLI documentada "
                       "este aqui o tenga un motivo declarado en "
                       "MOTIVOS_SIN_EJECUCION.",
            "_el_test_debe_existir": "Si el test nombrado desaparece, la CLI se "
                                     "queda sin verificar y el guard lo dice: es el "
                                     "'guard sin objeto' aplicado a las CLIs.",
            "_como_se_regenera": "python3 scripts/_censo_clis.py --escribir",
            "verificadas": medido,
        }
        with open(MAPA, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=1, ensure_ascii=False)
        print(f"escrito {MAPA} ({len(medido)} CLIs)")

    if a.comparar:
        sin_ejecutar, sin_declarar = _diferencias(_leer_mapa(), medido)
        if sin_ejecutar or sin_declarar:
            for k, v in sin_ejecutar.items():
                print(f"  el mapa declara {k} ({', '.join(v)}) pero la suite NO la ejecuta")
            for k in sin_declarar:
                print(f"  la suite ejecuta {k} y el mapa no la declara")
            return 1
        print(f"el mapa coincide con lo medido: {len(medido)} CLIs")

    return codigo


if __name__ == "__main__":
    sys.exit(main())
