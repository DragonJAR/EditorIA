#!/usr/bin/env python3
"""Cierra un tip: mide, compara y dice en UNA linea si se puede publicar.

POR QUE EXISTE
  Cerrar un tip son tres mediciones y una mirada manual:

    1. la PUERTA del repo (scripts/validate_skill.py), que es el superset:
       contenido, historial y la suite entera;
    2. el ENTORNO: la misma suite sin repo, en una copia aislada. Si los dos
       veredictos coinciden, la suite es honesta con el entorno y UNA sola
       puerta basta; si no, hacen falta dos (scripts/_guard_entorno.py);
    3. la COPIA INSTALADA: que lo que usa el agente sea lo que se publico
       (scripts/sincronizar_instalada.py --check).

  Tres comandos, tres logs y una mirada es donde se cuelan los errores: el log
  equivocado (todos se llaman igual y todos terminan en "SKILL VALIDO"), la
  puerta corrida en el arbol COMPARTIDO (mide lo que la otra sesion esta
  escribiendo por debajo) y el paso que se olvido.

  Aqui no hay ninguno de esos tres fallos posibles: cada medicion va a SU
  log, con el commit medido en la cabecera, y el veredicto sale en una sola
  linea que dice que surfaces se midieron.

QUE NO HACE (y lo dice)
  · NO publica: no hace push ni toca el remoto. Publicar es de quien publica.
  · NO mide en el arbol de trabajo: mide un COMMIT, en un worktree AISLADO
    (con su propio .git), para que otra sesion escribiendo en el arbol no
    pueda mover lo que se mide. Si el arbol tiene cambios sin commitear, se
    dice: el tip medido es el commit, no el arbol.
  · NO mide en paralelo con otra puerta: dos validaciones a la vez se pisan
    y el fallo sale como si fuera del producto. Si hay otra puerta corriendo,
    esto se para y lo dice.
  · NO toca la copia instalada: la comprueba (--check), no la escribe.

COMO SE USA
  python3 scripts/_cerrar_tip.py                  # cierra HEAD
  python3 scripts/_cerrar_tip.py --tip <sha>      # cierra ese commit
  python3 scripts/_cerrar_tip.py --json           # salida para maquinas
  python3 scripts/_cerrar_tip.py --no-limpiar     # deja el worktree para mirar

Sale 0 si el tip esta cerrado, 1 si no.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(SCRIPTS)

sys.path.insert(0, SCRIPTS)
import _guard_entorno as _GE  # noqa: E402


def _correr(cmd, cwd=None, timeout=3600):
    """(codigo, salida) de un comando. Un timeout NO es un crash: es un fallo."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout, cwd=cwd)
        return r.returncode, r.stdout + r.stderr
    except subprocess.TimeoutExpired:
        return 2, f"TIMEOUT: {' '.join(cmd)} no termino en {timeout}s"
    except OSError as ex:
        return 3, f"no se pudo ejecutar {cmd[0]}: {ex}"


def _git(raiz, *args, timeout=120):
    """(codigo, stdout, stderr) de un git. Separados a proposito: el error de
    git va a stderr, y mezclarlo con stdout convierte un "fatal: ..." en un
    valor que parece una respuesta."""
    try:
        r = subprocess.run(["git", "-C", raiz, *args], capture_output=True,
                           text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return 2, "", f"TIMEOUT: git {' '.join(args)} no termino en {timeout}s"
    except OSError as ex:
        return 3, "", f"no se pudo ejecutar git: {ex}"


def _puertas_vivas():
    """Los PIDs de otras puertas corriendo ahora mismo (o []).

    La puerta que nos ha lanzo (nuestra ancestra) NO cuenta: somos parte de
    ella, no una medicion en paralelo. Las demas si: dos sesiones midiendo a
    la vez se pisan (y el fallo sale como si fuera del producto).

    El patron va ANCLADO al final de la linea de comandos (`validate_skill.py$`):
    sin ancla, `pgrep -f` casa con CUALQUIER linea que mencione ese nombre,
    incluidos los comandos de inspeccion que uno escribe para mirar si hay una
    puerta corriendo (que es justo lo que hace el que vigila). Un guard que se
    dispara con su propio sentinel no vigila nada.
    """
    try:
        r = subprocess.run(["pgrep", "-f", r"validate_skill\.py$"],
                           capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return []
    pids = []
    for linea in r.stdout.split():
        try:
            pids.append(int(linea))
        except ValueError:
            continue
    ancestros = _ancestros()
    return [p for p in pids if p != os.getpid() and p not in ancestros]


def _ancestros(pid=None):
    """Los PIDs de la cadena que nos lanzo (el que nos lanzo, y el de el).

    Se usa para NO contar como "otra puerta" a la puerta que nos esta
    corriendo: cuando la suite de una puerta llama a este envoltorio, esa
    puerta es nuestra ANCESTRA, no una medicion ajena. Contarla como ajena
    hacia que la propia puerta se cayera a si misma: el guard se negaba a
    cerrar, y el fallo salia como un ROJO DE PUERTA, no como un "no se mide
    en paralelo".
    """
    pid = pid or os.getpid()
    cadena = set()
    for _ in range(12):
        try:
            r = subprocess.run(["ps", "-o", "ppid=", "-p", str(pid)],
                               capture_output=True, text=True, timeout=10)
        except (OSError, subprocess.SubprocessError):
            break
        ppid = (r.stdout or "").strip()
        if not ppid.isdigit():
            break
        pid = int(ppid)
        if pid <= 1 or pid in cadena:
            break
        cadena.add(pid)
    return cadena


def _crear_worktree(raiz, tip, destino):
    """Worktree AISLADO del tip. Tiene su propio .git: medir ahi es medir el
    commit, no lo que otra sesion este escribiendo en el arbol."""
    rc, out, err = _git(raiz, "worktree", "add", "--detach", destino, tip)
    return rc == 0, out + err


def _quitar_worktree(raiz, destino):
    """Retira el worktree. Si no se puede, se dice: un worktree vivo es un
    arbol que otro agente puede pisar."""
    rc, out, err = _git(raiz, "worktree", "remove", "--force", destino)
    if rc != 0:
        rc2, out2, err2 = _git(raiz, "worktree", "prune")
        return rc2 == 0, out + err + out2 + err2
    return True, out + err


#: La linea de la puerta que dice como salio la suite. El prefijo es "OK  " o
#: "FAIL" MAS un espacio (el `check` de la puerta anade uno mas), asi que se
#: busca con un regex y no con un `startswith` de espacios exactos: un
#: `startswith` que no casa NO es un fallo de la puerta, es un envoltorio que
#: se queda sin veredicto... y que se niega a cerrar. Que es lo que hizo.
_LINEA_SUITE = re.compile(r"^(OK|FAIL)\s+tests unitarios de scripts/_tests\b")


def _veredicto_suite_desde_puerta(salida):
    """(codigo, () ) del veredicto de la suite, leido de la puerta.

    La puerta corre la suite por dentro y no expone su codigo: lo deja
    escrito en una linea. Si esa linea no esta, no se inventa el veredicto:
    se devuelve None y el envoltorio dice que no lo pudo leer (y NO cierra).
    """
    for linea in (salida or "").splitlines():
        mt = _LINEA_SUITE.match(linea)
        if mt:
            return (0 if mt.group(1) == "OK" else 1), ()
    return None, ()


def _medir_puerta(ruta_skill, log_puerta):
    """Corre la puerta del repo en el worktree. Log con su cabecera."""
    inicio = time.time()
    rc, salida = _correr([sys.executable, os.path.join(ruta_skill, "scripts",
                                                       "validate_skill.py")],
                          cwd=ruta_skill, timeout=3600)
    with open(log_puerta, "w", encoding="utf-8") as fh:
        fh.write(salida)
    fallos = salida.count("\nFAIL ") + (1 if salida.startswith("FAIL ") else 0)
    veredicto_suite, _ = _veredicto_suite_desde_puerta(salida)
    return {"ok": rc == 0, "rc": rc, "fallos": fallos,
            "detalle": (f"{fallos} FALLO(S)" if fallos else "sin fallos"),
            "segundos": time.time() - inicio, "log": log_puerta,
            "veredicto_suite": veredicto_suite}


def _medir_entorno(ruta_skill, veredicto_suite, log_entorno):
    """La misma suite SIN repo, en una copia aislada (scripts/_guard_entorno.py)."""
    inicio = time.time()
    if veredicto_suite is None:
        info = {"honesta": None,
                "motivo": "no se pudo leer el veredicto de la suite en la puerta: "
                          "no se mide el entorno sin repo"}
        texto = f"FALLA  la medicion no vale: {info['motivo']}\n"
    else:
        info = _GE.medir(ruta_skill, veredicto_base=(veredicto_suite, ""),
                         timeout=1800)
        texto = _GE._informe_texto(info) + "\n"
    with open(log_entorno, "w", encoding="utf-8") as fh:
        fh.write(texto)
    return {"ok": info.get("honesta") is True,
            "info": info, "detalle": info.get("motivo", ""),
            "segundos": time.time() - inicio, "log": log_entorno}


def _comprobar_copia(raiz, log_copia):
    """Que la copia instalada sea lo publicado. Solo LEE: no escribe."""
    inicio = time.time()
    rc, salida = _correr([sys.executable, os.path.join(raiz, "editoria", "scripts",
                                                       "sincronizar_instalada.py"),
                           "--check"], cwd=raiz, timeout=600)
    with open(log_copia, "w", encoding="utf-8") as fh:
        fh.write(salida)
    coincide = "la copia coincide con lo publicado" in salida
    return {"ok": coincide, "rc": rc, "detalle": ("coincide" if coincide else
                                                   "la copia NO coincide con lo publicado"),
            "segundos": time.time() - inicio, "log": log_copia}


def cerrar(tip=None, raiz=None, log_dir=None, puerta=None, entorno=None, copia=None,
           limpiar=True):
    """Cierra un tip y devuelve el veredicto (dict).

    `puerta`, `entorno` y `copia` son las tres mediciones; se pueden inyectar
    (los tests lo hacen, para no pagar 14 minutos por test).
    """
    raiz = os.path.abspath(raiz or os.path.dirname(BASE))
    rc, out, _err = _git(raiz, "rev-parse", "--short", "HEAD")
    head = out.strip()
    tip = tip or head
    rc, out, _err = _git(raiz, "rev-parse", "--verify", f"{tip}^{{commit}}")
    if rc != 0:
        return {"cerrado": False, "motivo": f"el tip {tip} no existe en este repo",
                "tip": tip, "mediciones": {}}
    rc, out, _err = _git(raiz, "rev-parse", "--short", tip)
    sha = out.strip() or tip

    rc, sucio, _err = _git(raiz, "status", "--porcelain")
    arbol_sucio = bool(sucio.strip())

    if log_dir is None:
        log_dir = os.path.join(raiz, ".val", f"{sha}_{os.getpid()}")
    os.makedirs(log_dir, exist_ok=True)

    destino = tempfile.mkdtemp(prefix=f"editoria_wt_{sha}_")
    worktree = os.path.join(destino, "wt")
    log_puerta = os.path.join(log_dir, "repo.txt")
    log_entorno = os.path.join(log_dir, "entorno.txt")
    log_copia = os.path.join(log_dir, "copia.txt")

    vivo = _puertas_vivas()
    if vivo:
        return {"cerrado": False, "motivo": f"ya hay una puerta corriendo (PIDs "
                                           f"{', '.join(str(p) for p in vivo)}): "
                                           f"no se mide en paralelo",
                "tip": sha, "mediciones": {}}

    mediciones = {}
    try:
        ok, salida_wt = _crear_worktree(raiz, sha, worktree)
        if not ok:
            return {"cerrado": False, "motivo": f"no se pudo crear el worktree "
                                               f"aislado: {salida_wt.strip()[:200]}",
                    "tip": sha, "mediciones": {}}
        ruta_skill = os.path.join(worktree, "editoria")

        med_puerta = (puerta or _medir_puerta)(ruta_skill, log_puerta)
        mediciones["puerta"] = med_puerta
        veredicto_suite = med_puerta.get("veredicto_suite")
        if veredicto_suite is None:
            # una puerta inyectada puede no traer el veredicto: se lee del log
            veredicto_suite, _ = _veredicto_suite_desde_puerta(_leer(log_puerta))
        if not med_puerta["ok"]:
            return {"cerrado": False, "motivo": f"la puerta del repo dio "
                                               f"{med_puerta.get('detalle')}",
                    "tip": sha, "arbol_sucio": arbol_sucio,
                    "mediciones": mediciones, "log_dir": log_dir}
        if veredicto_suite is None:
            mediciones["entorno"] = {"ok": False, "detalle": "no se pudo leer el "
                                                            "veredicto de la suite",
                                    "log": log_entorno}
            return {"cerrado": False, "motivo": "no se pudo leer el veredicto de la "
                                               "suite en la puerta: el entorno no se midio",
                    "tip": sha, "arbol_sucio": arbol_sucio,
                    "mediciones": mediciones, "log_dir": log_dir}

        med_entorno = (entorno or _medir_entorno)(ruta_skill, veredicto_suite,
                                                  log_entorno)
        mediciones["entorno"] = med_entorno
        if not med_entorno["ok"]:
            return {"cerrado": False, "motivo": f"la suite no es honesta con el "
                                               f"entorno: {med_entorno.get('detalle')}",
                    "tip": sha, "arbol_sucio": arbol_sucio,
                    "mediciones": mediciones, "log_dir": log_dir}

        med_copia = (copia or _comprobar_copia)(raiz, log_copia)
        mediciones["copia"] = med_copia
        if not med_copia["ok"]:
            return {"cerrado": False, "motivo": f"la copia instalada "
                                               f"{med_copia.get('detalle')}",
                    "tip": sha, "arbol_sucio": arbol_sucio,
                    "mediciones": mediciones, "log_dir": log_dir}

        return {"cerrado": True, "tip": sha, "arbol_sucio": arbol_sucio,
                "mediciones": mediciones, "log_dir": log_dir,
                "motivo": "repo verde, entorno honesto, copia sincronizada"}
    finally:
        if os.path.isdir(worktree):
            if limpiar:
                ok, salida_rm = _quitar_worktree(raiz, worktree)
                if not ok:
                    print(f"AVISO  no se pudo retirar el worktree {worktree}: "
                          f"{salida_rm.strip()[:200]}", file=sys.stderr)
            else:
                print(f"worktree conservado para mirar: {worktree}", file=sys.stderr)
        if limpiar:
            shutil.rmtree(destino, ignore_errors=True)


def _leer(ruta):
    try:
        with open(ruta, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


def _minutos(seg):
    return f"{seg / 60:.1f} min"


def main():
    ap = argparse.ArgumentParser(
        description="Cierra un tip: mide repo, entorno y copia, y lo dice en una linea")
    ap.add_argument("--tip", default=None,
                    help="commit a cerrar (def: HEAD)")
    ap.add_argument("--raiz", default=None, help="raiz del repo (def: la del propio)")
    ap.add_argument("--log-dir", default=None,
                    help="donde dejar los logs (def: <repo>/.val/<sha>_<pid>)")
    ap.add_argument("--json", action="store_true", help="salida en JSON")
    ap.add_argument("--no-limpiar", action="store_true",
                    help="deja el worktree aislado para poder mirarlo")
    a = ap.parse_args()

    veredicto = cerrar(tip=a.tip, raiz=a.raiz, log_dir=a.log_dir,
                       limpiar=not a.no_limpiar)

    if a.json:
        print(json.dumps(veredicto, ensure_ascii=False, indent=1))
    else:
        for nombre, med in (veredicto.get("mediciones") or {}).items():
            print(f"  {nombre:9s} {'OK  ' if med.get('ok') else 'FALLA'} "
                  f"{med.get('detalle', '')}"
                  + (f"  ({_minutos(med['segundos'])})" if "segundos" in med else ""))
        if veredicto.get("cerrado"):
            print(f"el tip {veredicto['tip']} ESTA CERRADO: {veredicto['motivo']}")
        else:
            print(f"el tip {veredicto.get('tip', '?')} NO ESTA CERRADO: "
                  f"{veredicto.get('motivo')}")
        if veredicto.get("arbol_sucio"):
            print("AVISO  el arbol de trabajo tiene cambios sin commitear: se ha "
                  "medido el COMMIT, no el arbol")
        if veredicto.get("log_dir"):
            print(f"logs: {veredicto['log_dir']}")
    return 0 if veredicto.get("cerrado") else 1


if __name__ == "__main__":
    sys.exit(main())
