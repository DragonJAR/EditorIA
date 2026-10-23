#!/usr/bin/env python3
"""Deja la copia instalada de la skill en el estado PUBLICADO, sin bytecode fantasma.

Copiar la skill con `tar` o `git archive` NO la deja sincronizada: esas
herramientas conservan el mtime del commit (en el pasado), asi que un
`__pycache__` que ya estaba en la copia queda MAS NUEVO que su `.py` y
python ejecuta ese bytecode en vez del codigo actual. La copiainstalled
acaba corriendo un motor que ya no existe, y los checks que se corren
contra ella mienten: un FAIL que no se reproduce en el repo.

Esta herramienta hace las dos cosas que faltaban:
1. si hay repo, extrae HEAD a la copia instalada (lo publicado, no el
   arbol de trabajo);
2. borra el `__pycache__` y el `.ruff_cache` de la copia: sin cache, no
   hay bytecode fantasma que pueda ganar.

Y en la copia instalada (que no es repo) sirve para lo otro: comprobar
que no hay bytecode fantasma, que es como se detecta que la copia va
desfasada.

`scripts/check_env.py` COMPRUEBA el bytecode fantasma comparando el
contenido compilado; esta herramienta lo PREVIENE (lo borra) y sincroniza.

Uso:
    python scripts/sincronizar_instalada.py             # sincroniza y limpia
    python scripts/sincronizar_instalada.py --check     # solo informa
    python scripts/sincronizar_instalada.py --destino /ruta
"""
import argparse
import os
import shutil
import subprocess
import sys

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(SCRIPTS)                      # .../editoria
DESTINO_POR_DEFECTO = os.path.expanduser("~/.minimax/skills")


def _raiz_git():
    """La raiz del repo donde vive la skill, o None si no hay repo."""
    try:
        r = subprocess.run(["git", "-C", BASE, "rev-parse", "--show-toplevel"],
                           capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else None
    except (OSError, subprocess.SubprocessError):
        return None


def _caches(base):
    """Las carpetas de cache de la copia."""
    out = []
    for d, dirs, _ in os.walk(base):
        for sub in list(dirs):
            if sub in ("__pycache__", ".ruff_cache"):
                out.append(os.path.join(d, sub))
                dirs.remove(sub)
    return out


def _bytecode_fantasma(base):
    """Los .pyc MAS NUEVOS que su .py: python ejecutara ese codigo, no el actual.

    Es exactamente el caso del bug: `git archive` deja el .py con el mtime
    del commit (pasado) y el .pyc compilado antes queda mas nuevo.
    """
    for d, _dirs, files in os.walk(base):
        if os.path.basename(d) != "__pycache__":
            continue
        for f in files:
            if not f.endswith(".pyc"):
                continue
            pyc = os.path.join(d, f)
            py = os.path.join(os.path.dirname(d), f.split(".")[0] + ".py")
            if os.path.exists(py) and os.path.getmtime(pyc) > os.path.getmtime(py):
                yield pyc, py


def _borrar_cache(base, escribir):
    """Borra el cache de la copia (recuperable)."""
    rutas = _caches(base)
    for r in rutas:
        if escribir:
            shutil.rmtree(r, ignore_errors=True)
    return rutas


def _extraer_head(destino, raiz, escribir):
    """Extrae el estado PUBLICADO (HEAD) a la copia instalada."""
    import io
    import tarfile
    rel = os.path.relpath(os.path.realpath(BASE), raiz).replace(os.sep, "/")
    r = subprocess.run(["git", "-C", raiz, "archive", "HEAD", rel],
                       capture_output=True)
    if r.returncode != 0:
        return None, []
    if not escribir:
        # en --check no se escribe: se compara en un temporal
        import tempfile
        tmp = tempfile.mkdtemp(prefix="editoria_sync_")
        with tarfile.open(fileobj=io.BytesIO(r.stdout)) as tar:
            tar.extractall(tmp)
        return os.path.join(tmp, rel), [tmp]
    with tarfile.open(fileobj=io.BytesIO(r.stdout)) as tar:
        tar.extractall(destino)
    return os.path.join(destino, rel), []


def _comparar(base_head, base_copia):
    """Los archivos que difieren entre lo publicado y la copia."""
    head, copia = set(), set()
    for d, _dirs, files in os.walk(base_head):
        for f in files:
            head.add(os.path.relpath(os.path.join(d, f), base_head))
    for d, _dirs, files in os.walk(base_copia):
        for f in files:
            if f == ".DS_Store" or "__pycache__" in d:
                continue
            copia.add(os.path.relpath(os.path.join(d, f), base_copia))
    solo_head = sorted(head - copia)
    solo_copia = sorted(copia - head)
    distintos = []
    for rel in sorted(head & copia):
        a = os.path.join(base_head, rel)
        b = os.path.join(base_copia, rel)
        try:
            if os.path.getsize(a) != os.path.getsize(b) or \
               open(a, "rb").read() != open(b, "rb").read():
                distintos.append(rel)
        except OSError:
            pass
    return solo_head, solo_copia, distintos


def main():
    ap = argparse.ArgumentParser(description="Sincroniza la copia instalada con lo publicado")
    ap.add_argument("--check", action="store_true", help="solo informa (no escribe)")
    ap.add_argument("--destino", default=DESTINO_POR_DEFECTO,
                    help="donde vive la copia instalada (def: ~/.minimax/skills)")
    args = ap.parse_args()
    escribir = not args.check
    destino = os.path.abspath(os.path.expanduser(args.destino))
    copia = os.path.join(destino, os.path.basename(BASE))

    print(f"copia instalada: {copia}")
    raiz = _raiz_git()
    if raiz:
        print(f"repo: {raiz}")
        base_head, temps = _extraer_head(destino, raiz, escribir)
        if base_head:
            solo_head, solo_copia, distintos = _comparar(base_head, copia)
            if solo_head or solo_copia or distintos:
                print(f"la copia se diferencia de lo publicado:")
                for rel in solo_head:
                    print(f"  falta en la copia:   {rel}")
                for rel in solo_copia:
                    print(f"  sobra en la copia:   {rel}")
                for rel in distintos:
                    print(f"  distinto:            {rel}")
            else:
                print("la copia coincide con lo publicado")
        for t in temps:
            shutil.rmtree(t, ignore_errors=True)
    else:
        print("sin repo: la copia ES lo publicado; solo se comprueba y se limpia")

    fantasmas = list(_bytecode_fantasma(copia))
    caches = _borrar_cache(copia, escribir)
    if fantasmas:
        print(f"bytecode fantasma ({len(fantasmas)}): python ejecutaria codigo que ya no existe")
        for pyc, py in fantasmas:
            print(f"  {os.path.relpath(pyc, copia)} es mas nuevo que {os.path.relpath(py, copia)}")
    else:
        print("sin bytecode fantasma")
    if caches:
        verb = "borrado" if escribir else "pendiente de borrar"
        print(f"cache ({len(caches)}) {verb}")
    return 1 if (fantasmas and args.check) else 0


if __name__ == "__main__":
    sys.exit(main())
