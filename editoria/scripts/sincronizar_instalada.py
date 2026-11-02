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


def _codigo_del_pyc(ruta):
    """El objeto de codigo que guarda un .pyc."""
    import marshal
    with open(ruta, "rb") as f:
        f.read(16)          # magic + flags + mtime + tamaño
        return marshal.load(f)


def _bytecode_fantasma(base):
    """Los .pyc cuyo codigo NO es el del .py actual (codigo fantasma).

    Un .pyc mas nuevo que su .py NO es prueba de nada: al compilar, el
    .pyc nace con la hora de ahora y el .py puede tener el mtime del
    commit (pasado), que es justo el caso de una copia recien
    sincronizada. Con fechas daria falsos positivos.

    La comprobacion fiable es de CONTENIDO: se compila el .py actual y se
    compara su objeto de codigo con el que guarda el .pyc (el nombre del
    archivo no cuenta: el .pyc guardo el de cuando se compilo).
    """
    for d, _dirs, files in os.walk(base):
        if os.path.basename(d) != "__pycache__":
            continue
        for f in files:
            if not f.endswith(".pyc"):
                continue
            pyc = os.path.join(d, f)
            py = os.path.join(os.path.dirname(d), f.split(".")[0] + ".py")
            if not os.path.exists(py):
                continue
            try:
                guardado = _codigo_del_pyc(pyc)
                actual = compile(open(py, encoding="utf-8").read(),
                                 os.path.basename(py), "exec")
            except (OSError, ValueError, EOFError, SyntaxError):
                continue
            if guardado.replace(co_filename="") != actual.replace(co_filename=""):
                yield pyc, py


def _borrar_cache(base, escribir):
    """Borra el cache de la copia (recuperable)."""
    rutas = _caches(base)
    for r in rutas:
        if escribir:
            shutil.rmtree(r, ignore_errors=True)
    return rutas


def _exportar_head(destino, raiz):
    """Exporta el estado PUBLICADO (HEAD) a un directorio.

    Se exporta SIEMPRE a un temporal: la comparacion tiene que ser entre
    lo publicado y la copia, no entre la copia y si misma.
    """
    import io
    import tarfile
    rel = os.path.relpath(os.path.realpath(BASE), raiz).replace(os.sep, "/")
    r = subprocess.run(["git", "-C", raiz, "archive", "HEAD", rel],
                       capture_output=True)
    if r.returncode != 0:
        return None
    with tarfile.open(fileobj=io.BytesIO(r.stdout)) as tar:
        tar.extractall(destino)
    return os.path.join(destino, rel)


def _dirs_de(base):
    """Los directorios (relativos) de un arbol. Las caches no cuentan.

    Los directorios importan por una razon concreta: `git archive` NO guarda
    los directorios vacios (git no los puede versionar), pero `copytree` SI
    copia los que hay. Un directorio que se quedo en la copia de una
    sincronizacion antigua sobrevive a todas las siguientes, porque el
    sincronizador solo borra ficheros que sobran. Y el check de ficheros no lo
    ve: el directorio no es un fichero.
    """
    out = set()
    for d, dirs, _files in os.walk(base):
        dirs[:] = [x for x in dirs
                   if x not in ("__pycache__", ".ruff_cache", ".pytest_cache")]
        rel = os.path.relpath(d, base)
        if rel != ".":
            out.add(rel.replace(os.sep, "/"))
    return out


def _comparar(base_head, base_copia):
    """Los archivos que difieren entre lo publicado y la copia, y los
    directorios que sobran o faltan."""
    head, copia = set(), set()
    for d, _dirs, files in os.walk(base_head):
        for f in files:
            # el .DS_Store es basura del sistema: el .gitignore lo excluye, y
            # que este en un lado y no en otro no es una diferencia real
            if f == ".DS_Store":
                continue
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
    dirs_head = _dirs_de(base_head)
    dirs_copia = _dirs_de(base_copia)
    solo_dirs_head = sorted(dirs_head - dirs_copia)
    solo_dirs_copia = sorted(dirs_copia - dirs_head)
    return solo_head, solo_copia, distintos, solo_dirs_head, solo_dirs_copia


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
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            base_head = _exportar_head(tmp, raiz)
            if base_head:
                solo_head, solo_copia, distintos, solo_dirs_head, solo_dirs_copia = \
                    _comparar(base_head, copia)
                if solo_head or solo_copia or distintos or solo_dirs_copia or solo_dirs_head:
                    print("la copia se diferencia de lo publicado:")
                    for rel in solo_head:
                        print(f"  falta en la copia:   {rel}")
                    for rel in solo_copia:
                        print(f"  sobra en la copia:   {rel}")
                    for rel in distintos:
                        print(f"  distinto:            {rel}")
                    for rel in solo_dirs_head:
                        print(f"  falta el directorio: {rel}")
                    for rel in solo_dirs_copia:
                        print(f"  sobra el directorio: {rel} "
                              f"(vacio: git archive no guarda directorios vacios, "
                              f"pero copytree si)")
                else:
                    print("la copia coincide con lo publicado")
                if escribir:
                    for rel in solo_copia:
                        ruta = os.path.join(copia, rel)
                        if os.path.isfile(ruta):
                            os.remove(ruta)
                    shutil.copytree(base_head, copia, dirs_exist_ok=True)
                    # los directorios que sobran ya estan vacios (sus ficheros
                    # se acaban de borrar): se pueden quitar. Solo si estan
                    # vacios de verdad: un directorio con contenido no se
                    # toca, porque ahi puede haber algo que el usuario puso.
                    for rel in solo_dirs_copia:
                        ruta = os.path.join(copia, rel)
                        if os.path.isdir(ruta):
                            try:
                                os.rmdir(ruta)
                            except OSError:
                                pass
                    print("copia actualizada con lo publicado")
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
