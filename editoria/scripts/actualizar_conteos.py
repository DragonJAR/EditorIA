#!/usr/bin/env python3
"""Recalcula los conteos que los documentos de la skill enuncian.

Cuatro numeros envejecen cada vez que se anade un script o una suite:
referencias, scripts raiz, herramientas de ffmpeg y suites de tests.
Viven en varios sitios a la vez (el encabezado de `references/mapa.md`, la
lista de suites del `SKILL.md` y los README del repo) y actualizarlos a
mano es justo lo que se olvida: el documento acaba diciendo una cosa que
ya no es, y el arbol publicado lleva enlaces rotos o cifras falsas.

La herramienta cuenta con la MISMA fuente que el guard
(`scripts/auditar_mapa.py`), asi que los dos no pueden discrepar, y
funciona en las DOS topologias:

- en el repo (donde hay `README.md` y `README.en.md`): reescribe los
  documentos de la skill y los README;
- en la copia instalada (que no tiene README): reescribe solo lo de la
  skill, sin fallar.

Uso:
    python scripts/actualizar_conteos.py           # reescribe lo que este mal
    python scripts/actualizar_conteos.py --check   # solo informa (no escribe)
"""
import argparse
import os
import re
import shutil
import sys
import tempfile

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(SCRIPTS)                      # .../editoria
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import auditar_mapa as AM  # noqa: E402  una sola fuente de verdad para contar


def cuentas():
    """(referencias, scripts raiz, ffmpeg_tools, suites) — las del guard."""
    refs = AM._n_publicados("references", lambda p: p.endswith(".md"))
    root = AM._n_publicados("scripts", lambda p: p.endswith(".py") and p.count("/") == 1)
    fft = AM._n_publicados("scripts/ffmpeg_tools", lambda p: p.endswith(".py"))
    suites = len(AM._suites_publicadas())
    return refs, root, fft, suites


def _lista_de_suites(nombres):
    """La misma forma que usa el SKILL.md: comas y "and" antes de la ultima."""
    nombres = sorted(nombres)
    if not nombres:
        return "(ninguna)"
    if len(nombres) == 1:
        return f"`scripts/_tests/{nombres[0]}`"
    return (", ".join(f"`scripts/_tests/{n}`" for n in nombres[:-1])
            + f" and `scripts/_tests/{nombres[-1]}`")


def _sustituye(texto, patron, nuevo, etiqueta, cambios):
    """Sustituye la primera coincidencia y anota el archivo si cambio."""
    mt = re.search(patron, texto)
    if not mt or mt.group(0) == nuevo:
        return texto
    cambios.append(etiqueta)
    return texto[:mt.start()] + nuevo + texto[mt.end():]


def _transforma_mapa(texto, refs, root, fft, suites, cambios):
    nuevo = (f"{refs} referencias, {root} scripts, {fft} herramientas de ffmpeg "
             f"y {suites} suites de tests")
    return _sustituye(texto, r"\d+ referencias, \d+ scripts, \d+ herramientas de ffmpeg y \d+ suites de tests",
                      nuevo, "references/mapa.md", cambios)


def _transforma_lista_de_suites(texto, suites, cambios):
    mt = re.search(r"(unit tests in )(.+?)( pass via)", texto)
    if not mt:
        return texto
    nuevo = mt.group(1) + _lista_de_suites(suites) + mt.group(3)
    if mt.group(2) == nuevo[len(mt.group(1)):len(nuevo) - len(mt.group(3))]:
        return texto
    cambios.append("SKILL.md")
    return texto[:mt.start()] + nuevo + texto[mt.end():]


def _transforma_readme(texto, refs, root, fft, suites, etiqueta, cambios):
    total = root + fft + suites
    texto = _sustituye(
        texto, r"# \d+ motores raíz \+ \d+ en ffmpeg_tools/ \+ \d+ en _tests/ = \d+ scripts",
        f"# {root} motores raíz + {fft} en ffmpeg_tools/ + {suites} en _tests/ = {total} scripts",
        etiqueta, cambios)
    texto = _sustituye(
        texto, r"# \d+ root \+ \d+ in ffmpeg_tools/ \+ \d+ in _tests/ = \d+ scripts",
        f"# {root} root + {fft} in ffmpeg_tools/ + {suites} in _tests/ = {total} scripts",
        etiqueta, cambios)
    texto = _sustituye(texto, r"\d+ referencias en kebab-case\.md",
                       f"{refs} referencias en kebab-case.md", etiqueta, cambios)
    texto = _sustituye(texto, r"\d+ references in kebab-case\.md",
                       f"{refs} references in kebab-case.md", etiqueta, cambios)
    return texto


def _raiz_del_repo():
    """La raiz del repo, o None si la skill corre instalada (sin repo)."""
    return AM._raiz_git()


def main():
    ap = argparse.ArgumentParser(description="Recalcula los conteos de la skill")
    ap.add_argument("--check", action="store_true",
                    help="solo informa de lo que esta desfasado (no escribe)")
    args = ap.parse_args()

    refs, root, fft, suites = cuentas()
    total = root + fft + suites
    print(f"referencias {refs} · scripts raiz {root} · ffmpeg_tools {fft} · "
          f"suites {suites} · scripts en total {total}")

    raiz_repo = _raiz_del_repo()
    cambios = []
    if args.check:
        # se trabaja sobre una COPIA: el modo "solo informar" no puede
        # escribir en el arbol real (un --check que escribe es peor que
        # no tener --check)
        with tempfile.TemporaryDirectory() as tmp:
            copia = os.path.join(tmp, "editoria")
            shutil.copytree(BASE, copia, ignore=shutil.ignore_patterns("__pycache__"))
            _aplica(copia, None, refs, root, fft, suites, cambios)
            if raiz_repo:
                for nombre in ("README.md", "README.en.md"):
                    origen = os.path.join(raiz_repo, nombre)
                    if os.path.exists(origen):
                        # en --check los README se transforman EN MEMORIA:
                        # un modo de solo informar que escribe es peor que
                        # no tenerlo (y el test lo vigila)
                        texto = open(origen, encoding="utf-8").read()
                        _transforma_readme(texto, refs, root, fft, suites, nombre, cambios)
        print("desfasado en:", ", ".join(cambios) if cambios else "nada")
        return 0

    _aplica(BASE, raiz_repo, refs, root, fft, suites, cambios)
    print("actualizado en:", ", ".join(cambios) if cambios else "nada")
    return 0


def _aplica(dest_skill, dest_repo, refs, root, fft, suites, cambios):
    """Aplica los cambios a la copia de la skill indicada."""
    nombres = AM._suites_publicadas()
    ruta = os.path.join(dest_skill, "references", "mapa.md")
    if os.path.exists(ruta):
        texto = open(ruta, encoding="utf-8").read()
        nuevo = _transforma_mapa(texto, refs, root, fft, suites, cambios)
        if nuevo != texto:
            open(ruta, "w", encoding="utf-8").write(nuevo)
    ruta = os.path.join(dest_skill, "SKILL.md")
    if os.path.exists(ruta):
        texto = open(ruta, encoding="utf-8").read()
        nuevo = _transforma_lista_de_suites(texto, nombres, cambios)
        if nuevo != texto:
            open(ruta, "w", encoding="utf-8").write(nuevo)
    if dest_repo:
        for nombre in ("README.md", "README.en.md"):
            origen = os.path.join(dest_repo, nombre)
            if os.path.exists(origen):
                _aplica_readme(origen, refs, root, fft, suites, cambios)


def _aplica_readme(ruta, refs, root, fft, suites, cambios):
    texto = open(ruta, encoding="utf-8").read()
    nuevo = _transforma_readme(texto, refs, root, fft, suites, os.path.basename(ruta), cambios)
    if nuevo != texto:
        open(ruta, "w", encoding="utf-8").write(nuevo)


if __name__ == "__main__":
    sys.exit(main())
