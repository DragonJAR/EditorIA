#!/usr/bin/env python3
"""_comandos_doc.py — los comandos que dice el SKILL.md, ¿se pueden ejecutar?

La skill le pide al agente que corra comandos literales. Si uno de esos
comandos esta mal (le falta un argumento obligatorio), el agente se queda
parado con un error de argparse que no esta en ningun sitio de la doc. Este
modulo extrae los comandos del SKILL.md y los valida SIN ejecutarlos: se
intercepta `ArgumentParser.parse_args`, se comprueba que los argumentos
documentados esten completos y se sale antes de que el script haga nada.

No se ejecuta ninguna acion: el script no llega a su main().
"""
import os
import re
import shlex
import subprocess
import sys

# La linea que se mete en el script para interceptar el parser. Va antes del
# runpy: el script ve un argparse normal y no se entera de nada.
_INTERCEPTAR = r'''
import argparse, sys, runpy
_Real = argparse.ArgumentParser.parse_args
_RealK = argparse.ArgumentParser.parse_known_args
_dentro = [False]
def _parse(self, args=None, namespace=None):
    _dentro[0] = True
    try:
        _Real(self, args, namespace)
    except SystemExit as e:
        if e.code == 2:
            sys.stderr.write("\n__ARGPARSE_ERROR__\n")
        raise
    finally:
        _dentro[0] = False
    sys.stderr.write("\n__ARGPARSE_OK__\n")
    sys.exit(0)
def _parsek(self, args=None, namespace=None):
    # `parse_args` llama por dentro a `parse_known_args`: si este saliera
    # aqui, el error de "unrecognized arguments" (que se detecta DESPUES de
    # que parse_known_args vuelve) nunca llegaria. Solo se corta cuando el
    # script llama a parse_known_args por su cuenta.
    res = _RealK(self, args, namespace)
    if not _dentro[0]:
        sys.stderr.write("\n__ARGPARSE_OK__\n")
        sys.exit(0)
    return res
argparse.ArgumentParser.parse_args = _parse
argparse.ArgumentParser.parse_known_args = _parsek
sys.argv = [SCRIPT] + ARGV
runpy.run_path(SCRIPT, run_name="__main__")
'''

# el comando de la doc: "python un-script.py args..." o "python3 ..."
# los README del repo usan el prefijo "editoria/scripts/...": se acepta igual
_CMD = re.compile(r"\bpython3?\s+((?:[\w.-]+/)?scripts/[A-Za-z0-9_./-]+\.py(?:\s+[^\n`#]+)?)")


def _unir_continuaciones(txt):
    """Un comando partido con barra invertida es UN comando.

    Sin esto, el bloque de `mezclar_audio.py` se leia como tres comandos y
    el primero se comprobaba sin su `-o`: un fallo falso.
    """
    lineas, buf = [], ""
    for ln in txt.splitlines():
        if buf:
            buf = buf + " " + ln.strip()
        else:
            buf = ln
        if buf.rstrip().endswith("\\"):
            # primero la barra, despues los espacios: al reves, el rstrip se
            # come el caracter de antes y el comando queda mutilado
            buf = buf.rstrip()[:-1].rstrip()
            continue
        lineas.append(buf)
        buf = ""
    if buf:
        lineas.append(buf)
    return "\n".join(lineas)


def _bloques_bash(txt):
    return re.findall(r"```bash\n(.*?)```", txt, re.S)


def comandos_documentados(skill_dir):
    """[(cmd, linea)] con los comandos python que el SKILL.md documenta."""
    with open(os.path.join(skill_dir, "SKILL.md"), encoding="utf-8") as f:
        txt = f.read()
    return _comandos_de_texto(txt)


def comandos_de_referencias(skill_dir):
    r"""Los comandos python que documentan las REFERENCIAS.

    El verificador solo miraba SKILL.md, y ahi se escondian comandos rotos:
    un flag opcional escrito como `[--destino a|b]` (argparse lo rechaza), un
    comando partido en dos lineas sin `\` (se copia roto) y una CLI sin su
    argumento obligatorio. Las referencias son donde el agente busca el
    comando exacto: es el mismo fallo de clase, en el sitio donde mas duele.
    """
    refs = os.path.join(skill_dir, "references")
    if not os.path.isdir(refs):
        return []
    salida = []
    for nombre in sorted(os.listdir(refs)):
        if not nombre.endswith(".md"):
            continue
        with open(os.path.join(refs, nombre), encoding="utf-8") as f:
            txt = f.read()
        for cmd in _comandos_de_texto(txt):
            salida.append(cmd)
    return salida


def comandos_de_readme(skill_dir):
    r"""Los comandos python que documentan los README del repo.

    Los README (ES y EN) son la puerta de entrada del proyecto: un comando
    roto ahi lo copia el usuario entero. Viven FUERA del arbol de la skill
    (un nivel arriba), asi que en la copia instalada no existen: el
    verificador los mira solo si estan.
    """
    raiz = os.path.dirname(skill_dir)
    salida = []
    for nombre in ("README.md", "README.en.md"):
        p = os.path.join(raiz, nombre)
        if not os.path.exists(p):
            continue
        with open(p, encoding="utf-8") as f:
            txt = f.read()
        for cmd in _comandos_de_texto(txt):
            salida.append(cmd)
    return salida


def _comandos_de_texto(txt):
    """Los comandos python de un texto, sin repetir."""
    txt = _unir_continuaciones(txt)
    vistos, salida = set(), []
    for bloque in _bloques_bash(txt):
        for linea in bloque.splitlines():
            linea = linea.split("#")[0].strip()
            m = _CMD.search(linea)
            if not m:
                continue
            completo = m.group(1).strip()
            if completo not in vistos:
                vistos.add(completo)
                salida.append(completo)
    # ademas, los comandos citados en prosa (con acentos graves)
    for m in _CMD.finditer(txt):
        completo = m.group(1).strip()
        if completo not in vistos:
            vistos.add(completo)
            salida.append(completo)
    return salida


def _partir(cmd):
    """Los argumentos de un comando, sin romper comillas ni placeholders.

    `shlex` deja intacto `--prompt "modern upbeat electronic"`, y los
    placeholders de la doc (`{file or url}`) se sustituyen por una palabra
    sin espacios: si no, el placeholder se parte en tres palabras y el
    comando parece roto cuando no lo esta.
    """
    limpio = re.sub(r"\{[^{}]*\}", "PLACEHOLDER", cmd)
    return shlex.split(limpio)


def _probar(skill_dir, cmd, timeout=120):
    """(ok, motivo). True = los argumentos documentados bastan."""
    partes = _partir(cmd)
    if not partes:
        return True, ""
    script = partes[0]
    args = partes[1:]
    # los README escriben la ruta con el prefijo de la carpeta del repo
    # ("editoria/...") y la skill vive en ".../editoria": el script se busca
    # desde la carpeta de scripts
    if "/scripts/" in script:
        script = "scripts/" + script.split("/scripts/", 1)[1]
    ruta = os.path.join(skill_dir, script)
    if not os.path.exists(ruta):
        return False, f"no existe {script}"
    runner = (
        "SCRIPT = %r\nARGV = %r\n" % (ruta, args) + _INTERCEPTAR
    )
    try:
        p = subprocess.run([sys.executable, "-c", runner], capture_output=True,
                           text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return True, ""     # no se puede juzgar: no es un fallo de argumentos
    err = p.stderr or ""
    if "__ARGPARSE_OK__" in err:
        return True, ""
    if "__ARGPARSE_ERROR__" in err:
        faltan = [ln for ln in err.splitlines()
                  if "required" in ln or "unrecognized" in ln]
        return False, (faltan[-1].strip() if faltan else "argumentos invalidos")
    # el script no usa argparse: no se puede juzgar con este metodo
    return True, ""


def verificar(skill_dir):
    """[problema] — vacio si todos los comandos documentados se pueden correr."""
    problemas = []
    for cmd in comandos_documentados(skill_dir):
        ok, motivo = _probar(skill_dir, cmd)
        if not ok:
            problemas.append(f"{cmd}  ->  {motivo}")
    return problemas


def verificar_todo(skill_dir):
    """[problema] — SKILL.md, las referencias Y los README del repo.

    Un comando roto en una referencia es un fallo tan real como uno roto en
    SKILL.md: el agente copia el comando de la referencia, no del indice. Y
    los README son la puerta de entrada del proyecto.
    """
    problemas = verificar(skill_dir)
    for cmd in comandos_de_referencias(skill_dir):
        ok, motivo = _probar(skill_dir, cmd)
        if not ok:
            problemas.append(f"[referencia] {cmd}  ->  {motivo}")
    for cmd in comandos_de_readme(skill_dir):
        ok, motivo = _probar(skill_dir, cmd)
        if not ok:
            problemas.append(f"[README] {cmd}  ->  {motivo}")
    return problemas


# Las CLIs documentadas que la suite NO puede ejecutar de verdad, con el
# motivo. Una CLI documentada tiene que estar EJECUTADA por un test (que usa
# subprocess) o tener un motivo aqui: un comando documentado que nadie ejecuta
# ni vigila por argumentos es un puntero a nada.
#
# Los dos mecanismos de la skill vigilan fallos DISTINTOS y no se delegan:
# la intercepcion de parse_args prueba que los ARGUMENTOS del comando son
# validos para esa herramienta; la ejecucion real prueba el EFECTO (que la
# herramienta no reviente al usarla). El ImportError de look.py estaba DENTRO
# de default_font_file(): la intercepcion llego a parse_args sin despeinarse,
# porque el fallo no estaba en los argumentos sino en el efecto.
MOTIVOS_SIN_EJECUCION = {
    "scripts/validate_skill.py": "es la validacion misma: se ejecuta con esta opcion",
}


def scripts_de_los_comandos(skill_dir):
    """Los scripts que invocan los comandos documentados.

    El prefijo de la carpeta del repo se normaliza igual que en el
    verificador (que busca el script dentro de la skill instalada)."""
    cmds = (comandos_documentados(skill_dir) + comandos_de_referencias(skill_dir)
            + comandos_de_readme(skill_dir))
    scripts = set()
    for cmd in cmds:
        partes = _partir(cmd)
        if not partes:
            continue
        s = partes[0]
        if "/scripts/" in s:
            s = "scripts/" + s.split("/scripts/", 1)[1]
        if s.startswith("scripts/") and s.endswith(".py"):
            scripts.add(s)
    return scripts


def clis_ejecutadas_por_tests(skill_dir):
    """Las CLIs que ALGUN test ejecuta como proceso.

    Un test cuenta si usa subprocess Y nombra el script: se ejecuta como
    proceso, no solo lo importa. (Un nombre en un comentario no ejecuta nada,
    pero tampoco hace pasar la comprobacion por el camino feliz: lo que se
    busca es que la herramienta se pruebe de verdad.)
    """
    tests_dir = os.path.join(skill_dir, "scripts", "_tests")
    if not os.path.isdir(tests_dir):
        return set()
    ejecutadas = set()
    for f in sorted(os.listdir(tests_dir)):
        if not f.endswith(".py") or f.startswith("_"):
            continue
        with open(os.path.join(tests_dir, f), encoding="utf-8") as fh:
            txt = fh.read()
        if "subprocess" not in txt:
            continue
        for m in re.finditer(r'["\']([A-Za-z0-9_]+\.py)["\']', txt):
            nombre = m.group(1)
            for raiz in ("scripts/", "scripts/ffmpeg_tools/"):
                cand = raiz + nombre
                if os.path.exists(os.path.join(skill_dir, cand)):
                    ejecutadas.add(cand)
                    break
    return ejecutadas


def verificar_comando(skill_dir, cmd):
    """Verifica UN comando. El test usa esto: el barrido completo es lento
    (un subproceso por comando) y vive en `validate_skill.py`."""
    ok, motivo = _probar(skill_dir, cmd)
    return [] if ok else [f"{cmd}  ->  {motivo}"]


if __name__ == "__main__":
    raiz = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))
    ps = verificar(raiz)
    for p in ps:
        print("FALLO", p)
    print(f"{len(ps)} problemas")
    sys.exit(1 if ps else 0)
