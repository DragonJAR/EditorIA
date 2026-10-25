#!/usr/bin/env python3
"""Guard de entorno: la suite tiene que dar el MISMO veredicto sin repo.

POR QUE EXISTE
  La skill vive en dos sitios y se mide en dos entornos:

    · el REPO, donde esta el historial y donde se desarrolla;
    · la COPIA INSTALADA (el artefacto), que NO tiene repo.

  Un test que asume el repo - da igual un `git rev-parse` que exista, que el
  arbol tenga `.git` - PASA en el repo y CAE en la copia. Entonces el verde de
  la puerta del repo es verde de un sitio donde la skill no vive, y el
  veredicto no dice lo que parece que dice.

  Ya paso (el test de la cabecera, antes de un parche). El parche lo arreglo,
  pero el patron no se ha ido: el siguiente test que lo repita vuelve a
  romper la copia sin que nadie se entere. Por eso esto se MIDE en vez de
  recordarse: la memoria no es un guard.

QUE MIDE
  La MISMA suite en DOS entornos, y compara los veredictos:

    · con repo: la suite tal cual;
    · sin repo: una COPIA AISLADA de la skill (sin `.git`, sin caches), con la
      suite corrida DENTRO de la copia, desde su propia carpeta.

  Si los dos veredictos son verdes, la suite es HONESTA con el entorno: el
  mismo contenido da el mismo resultado en los dos sitios, y por tanto una
  sola puerta (la del repo) basta para cerrar un tip. Si no, este guard FALLA
  y dice que test cambia de veredicto: ese test es el que obliga a medir las
  dos superficies.

  No adivina que depende del entorno: lo ejecuta. Un test que "quiza" depende
  del entorno no se detecta leyendo el fuente; se detecta corriendolo en el
  otro entorno y comparando.

LO QUE NO MIRA (y lo dice)
  · NO comprueba la COPIA INSTALADA de verdad: esa es otra superficie, la que
    usa el agente, y se mide con su propia puerta. Aqui se mide una copia
    AISLADA, que se puede tirar sin danar nada.
  · NO mide el resto de la puerta (renders, mapa, censo): solo la suite. Que
    la suite sea honesta NO dice que el render sea igual en los dos sitios.
  · NO dice que el repo y la copia tengan el mismo contenido: eso lo dice el
    check de sincronizacion (`scripts/sincronizar_instalada.py --check`).
  · NO se puede lanzar en paralelo con otra puerta: dos suites a la vez se
    pisan, y el fallo sale como si fuera del producto.

COMO SE USA
  python3 scripts/_guard_entorno.py                    # mide los dos entornos
  python3 scripts/_guard_entorno.py --solo-copia       # solo el entorno sin repo
  python3 scripts/_guard_entorno.py --base DIR         # mide otro arbol
  python3 scripts/_guard_entorno.py --json             # salida para maquinas

Sale 0 si la suite es honesta con el entorno, 1 si no lo es (o si la medicion
no se pudo hacer: un verde que no se midio no es un verde).
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: Lo que NO se copia a la copia aislada: el bytecode fantasma puede ganar al
#: codigo nuevo (ver `scripts/sincronizar_instalada.py`), y la basura del
#: sistema no es de la skill.
IGNORADOS = shutil.ignore_patterns("__pycache__", ".ruff_cache", ".pytest_cache",
                                   "*.pyc", ".DS_Store")

#: Una linea de fallo de unittest: "FAIL: test_x (mod.Clase)".
#:
#: El parentesis es lo que la distingue de la salida de las HERRAMIENTAS: una
#: herramienta que falla imprime "ERROR: --hablantes: 'ANA' no es NOMBRE=RRGGBB"
#: por stderr, y esa linea no es un test caido. Sin exigir el "(mod.Clase)" el
#: guard contaria como fallos lo que las herramientas dicen al probar, y el
#: numero de "tests que no son honestos" seria mentira.
FALLO = re.compile(r"^(FAIL|ERROR): ([^\s(]+) \(([^\s(]+)\)$", re.M)

#: El nombre de la carpeta de la skill dentro de la copia: la copia instalada
#: tambien se llama `editoria`, y un test que mirase el nombre de su carpeta
#: tiene que ver el mismo nombre en los dos entornos.
NOMBRE_SKILL = os.path.basename(BASE)


def _correr(cmd, cwd=None, timeout=900):
    """(codigo, stdout, stderr) de un comando. Un timeout NO es un crash."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout, cwd=cwd)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return 2, "", f"TIMEOUT: {' '.join(cmd)} no termino en {timeout}s"
    except OSError as ex:
        return 3, "", f"no se pudo ejecutar {cmd[0]}: {ex}"


def repo_de(base):
    """La raiz del repo que contiene `base`, o '' si no hay ninguno."""
    rc, out, _ = _correr(["git", "-C", base, "rev-parse", "--show-toplevel"], timeout=30)
    return out.strip() if rc == 0 else ""


def fallos_de(salida):
    """Los tests que fallan en la salida de unittest ('FAIL:' / 'ERROR:').

    Solo cuenta lineas con la forma de unittest (nombre + clase entre
    parentesis): la salida de una herramienta que falla no es un test caido.
    El id sale completo (modulo.Clase.metodo) para que el nombre apunte al
    fichero donde hay que ir a mirar.
    """
    return [f"{tipo}: {modulo}.{metodo}"
            for tipo, metodo, modulo in FALLO.findall(salida or "")]


def copiar_sin_repo(base, destino):
    """Copia la skill a `destino`, sin caches ni basura.

    `.git` no se copia nunca: vive en la raiz del repo, fuera de la skill, y
    ademas se excluye por si la skill viviera dentro de un repo propio. Y no
    se da por hecho que la copia quedo SIN repo: eso lo comprueba el guard
    despues (si la carpeta de temporales estuviera dentro de un repo, la
    medicion mediria dos veces lo mismo y daria un verde falso).
    """
    shutil.copytree(base, destino, ignore=IGNORADOS, symlinks=True)
    return destino


def correr_suite(base, timeout=900):
    """Corre la suite dentro de `base`. Devuelve (codigo, salida, fallos).

    Se corre DESDE la propia carpeta de la skill: asi, en el repo y en la
    copia, la suite ve el mismo entorno relativo. La diferencia entre las dos
    es exactamente la que se quiere medir (hay repo o no hay repo).
    """
    rc, out, err = _correr([sys.executable, os.path.join(base, "scripts", "_censo_clis.py")],
                           cwd=base, timeout=timeout)
    return rc, out + err, fallos_de(err)


def medir(base=BASE, timeout=900, destino=None, veredicto_base=None,
          medir_base=True):
    """Mide la suite con repo y sin repo. Devuelve el informe (dict).

    `veredicto_base` es (codigo, salida) de una suite YA corrida en `base`:
    si se pasa, no se vuelve a correr (la puerta del repo la corre ya).
    `medir_base=False` mide SOLO el entorno sin repo: entonces no hay
    comparacion, y el veredicto queda None con el motivo (un verde sin
    comparar no es un verde).
    `destino` es donde se hace la copia aislada; si es None, se usa un
    temporal que se borra al terminar.
    """
    base = os.path.abspath(base)
    tmp = None
    if destino is None:
        tmp = tempfile.mkdtemp(prefix="editoria_entorno_")
        destino = os.path.join(tmp, NOMBRE_SKILL)
    informe = {"base": {"ruta": base, "repo": repo_de(base)},
               "copia": {"ruta": destino, "repo": ""},
               "honesta": None, "motivo": ""}
    try:
        if not os.path.isdir(destino):
            copiar_sin_repo(base, destino)
        informe["copia"]["repo"] = repo_de(destino)
        if informe["copia"]["repo"]:
            # la copia quedo DENTRO de un repo: los dos entornos serian el
            # mismo y el verde no probaria nada. No se informa un verde falso.
            informe["motivo"] = (f"la copia quedo dentro de un repo "
                                 f"({informe['copia']['repo']}): la medicion no vale")
            return informe

        if veredicto_base is None:
            if medir_base:
                rc, salida, fallos = correr_suite(base, timeout)
            else:
                rc, salida, fallos = None, "", []
        else:
            rc, salida = veredicto_base[0], veredicto_base[1]
            fallos = fallos_de(salida)
        informe["base"].update({"rc": rc, "fallos": fallos})

        rc_c, salida_c, fallos_c = correr_suite(destino, timeout)
        informe["copia"].update({"rc": rc_c, "fallos": fallos_c})

        if rc is None:
            # solo se midio un lado: no hay comparacion que hacer
            informe["honesta"] = None
            informe["motivo"] = ("solo se midio el entorno sin repo: no hay "
                                 "comparacion, y un verde sin comparar no es un verde")
        elif rc == 0 and rc_c == 0:
            informe["honesta"] = True
            informe["motivo"] = ("el mismo contenido da el mismo veredicto con repo "
                                 "y sin repo")
        elif rc == 0 and rc_c != 0:
            informe["honesta"] = False
            informe["motivo"] = (f"{len(fallos_c)} test(s) pasan con repo y CAEN sin "
                                 f"repo: la suite no es honesta con el entorno")
        elif rc != 0 and rc_c == 0:
            informe["honesta"] = False
            informe["motivo"] = (f"{len(fallos)} test(s) CAEN con repo y pasan sin "
                                 f"repo: la suite no es honesta con el entorno")
        else:
            informe["honesta"] = False
            informe["motivo"] = ("la suite falla en los dos entornos: el fallo no es "
                                 "del entorno, pero la comparacion no es concluyente")
        return informe
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)


def _informe_texto(informe):
    """El informe, en lineas para el humano."""
    lineas = []
    b, c = informe["base"], informe["copia"]
    lineas.append(f"con repo:  {b['ruta']}")
    lineas.append(f"           {'repo' if b['repo'] else 'SIN REPO'} · "
                  f"{len(b.get('fallos', []))} fallos")
    lineas.append(f"sin repo:  {c['ruta']}")
    lineas.append(f"           {'repo' if c['repo'] else 'SIN REPO'} · "
                  f"{len(c.get('fallos', []))} fallos")
    for f in c.get("fallos", []):
        lineas.append(f"  sin repo cae: {f}")
    for f in b.get("fallos", []):
        lineas.append(f"  con repo cae:  {f}")
    lineas.append("")
    if informe["honesta"] is True:
        lineas.append("OK  la suite es honesta con el entorno: una sola puerta basta")
    elif informe["honesta"] is False:
        lineas.append(f"FALLA  la suite no es honesta con el entorno: {informe['motivo']}")
        lineas.append("      mientras siga asi, cerrar un tip exige DOS puertas "
                      "(repo y copia)")
    else:
        lineas.append(f"FALLA  la medicion no vale: {informe['motivo']}")
    return "\n".join(lineas)


def main():
    ap = argparse.ArgumentParser(
        description="Guard de entorno: la suite tiene que dar el mismo veredicto "
                    "con repo y sin repo")
    ap.add_argument("--base", default=BASE,
                    help="raiz de la skill a medir (def: la propia)")
    ap.add_argument("--json", action="store_true", help="salida en JSON")
    ap.add_argument("--timeout", type=int, default=900,
                    help="segundos que puede tardar la suite en cada entorno")
    ap.add_argument("--solo-copia", action="store_true",
                    help="mide solo el entorno sin repo (el veredicto con repo ya "
                         "se sabe: se usa cuando la puerta del repo ya corrio)")
    a = ap.parse_args()

    if a.solo_copia:
        # sin el veredicto de la base no hay comparacion: se mide la copia y se
        # DICE que no se puede concluir, en vez de dar un verde a medias.
        informe = medir(a.base, timeout=a.timeout, medir_base=False)
        informe["comparado"] = False
    else:
        informe = medir(a.base, timeout=a.timeout)
        informe["comparado"] = True

    if a.json:
        print(json.dumps(informe, ensure_ascii=False, indent=1))
    else:
        print(_informe_texto(informe))
    return 0 if informe["honesta"] is True else 1


if __name__ == "__main__":
    sys.exit(main())
