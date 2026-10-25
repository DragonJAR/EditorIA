#!/usr/bin/env python3
"""Recalcula los conteos que los documentos de la skill enuncian.

Cuatro numeros envejecen cada vez que se anade un script o una suite:
referencias, scripts raiz, herramientas de ffmpeg y suites de tests.
Viven en varios sitios a la vez (el encabezado de `references/mapa.md`, el
numero de suites del `SKILL.md` y los README del repo) y actualizarlos a
mano es justo lo que se olvida: el documento acaba diciendo una cosa que
ya no es, y el arbol publicado lleva enlaces rotos o cifras falsas.

Ademas escribe el CANONICO de las suites (`scripts/data/suites.json`): la
lista que `scripts/auditar_mapa.py` compara con el arbol. Antes esa lista
vivia enumerada en el `SKILL.md`, y ahi era ruido para el agente (se la leia
en cada peticion) y una bomba de relojería para el limite de 5000 palabras.

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
import json
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

#: El CANONICO de las suites: la lista que el guard compara con el arbol.
#:
#: La lista vivia en el `SKILL.md`, y ahi era dos problemas a la vez:
#: CONTENIDO que el agente se leia en cada peticion (46 rutas de test que no
#: usa) y CONTENIDO que el limite de 5000 palabras del `SKILL.md` podia tumbar
#: por una palabra (cada suite nueva sumaba una). Aqui vive donde pertenece:
#: los datos de la herramienta, junto a `verticales.json` y
#: `cli_verificadas.json`.
RUTA_SUITES = os.path.join("scripts", "data", "suites.json")


def cuentas():
    """(referencias, scripts raiz, ffmpeg_tools, suites, archivos en _tests/).

    Las dos ultimas NO son la misma cifra y no se pueden cambiar:
    - `suites`: los modulos que son de verdad una suite (test_*.py). es lo
      que dice el encabezado del mapa y lo que enumera el SKILL.md.
    - `archivos`: todo .py que vive en _tests/. es lo que dice el desglose
      del README ("N en _tests/") y lo que suma el total de scripts.
    un modulo de apoyo (apoyo.py) cuenta como archivo, pero no como suite.

    Las dos cifras salen del GUARD (`scripts/auditar_mapa.py`), que es su
    unico dueno: si esta cuenta distinto, la herramienta escribiria un numero
    que el guard rechaza, y el bucle "corre la herramienta y vuelve a fallar"
    no tendria salida.
    """
    refs = AM._n_publicados("references", lambda p: p.endswith(".md"))
    root = AM._n_publicados("scripts", lambda p: p.endswith(".py") and p.count("/") == 1)
    fft = AM._n_publicados("scripts/ffmpeg_tools", lambda p: p.endswith(".py"))
    suites = len(AM._suites_publicadas())
    archivos = AM._n_publicados("scripts/_tests", lambda p: p.endswith(".py")
                                 and p != "__init__.py")
    return refs, root, fft, suites, archivos


def _sustituye(texto, patron, nuevo, etiqueta, cambios):
    """Sustituye la primera coincidencia y anota el detalle del cambio.

    `cambios` guarda (archivo, lo que decia, lo que dira): el --check
    imprime eso, para que el que pregunta sepa QUE esta desfasado y no
    solo en que archivo.
    """
    mt = re.search(patron, texto)
    if not mt or mt.group(0) == nuevo:
        return texto
    cambios.append((etiqueta, mt.group(0).strip(), nuevo.strip()))
    return texto[:mt.start()] + nuevo + texto[mt.end():]


def _transforma_mapa(texto, refs, root, fft, suites, cambios):
    nuevo = (f"{refs} referencias, {root} scripts, {fft} herramientas de ffmpeg "
             f"y {suites} suites de tests")
    texto = _sustituye(texto, r"\d+ referencias, \d+ scripts, \d+ herramientas de ffmpeg y \d+ suites de tests",
                       nuevo, "references/mapa.md", cambios)
    # el mapa tambien se cuenta a si mismo en su prosa ("las N referencias").
    # Si la herramienta no reescribe esa mencion, el numero se queda viejo en
    # silencio y el guard lo ve, pero el que tiene que arreglarlo es esto.
    texto = _sustituye(texto, r"las \d+ referencias", f"las {refs} referencias",
                       "references/mapa.md", cambios)
    return texto


def _lee_suites_de_canonico(dest_skill):
    """Las suites que declara el canonico (set), o None si no esta."""
    ruta = os.path.join(dest_skill, RUTA_SUITES)
    if not os.path.exists(ruta):
        return None
    try:
        with open(ruta, encoding="utf-8") as fh:
            doc = json.load(fh) or {}
    except (OSError, ValueError):
        return None
    suites = doc.get("suites")
    if not isinstance(suites, list):
        return None
    return set(suites)


def _escribe_suites(dest_skill, nombres, cambios):
    """Escribe el canonico de suites y dice QUE cambia.

    El informe es por NOMBRE: lo que se necesita saber es que suite falta o
    sobra, no el fichero entero. Y el canonico se escribe SIEMPRE aunque
    nada haya cambiado, para que exista (un canonico que no esta, no es un
    canonico: es un hole).
    """
    ruta = os.path.join(dest_skill, RUTA_SUITES)
    antes = _lee_suites_de_canonico(dest_skill) or set()
    lista = sorted(nombres)
    if antes == set(lista) and os.path.exists(ruta):
        return
    faltan = sorted(set(lista) - antes)
    sobran = sorted(antes - set(lista))
    partes = []
    if faltan:
        partes.append("faltan " + ", ".join(faltan))
    if sobran:
        partes.append("sobran " + ", ".join(sobran))
    cambios.append((RUTA_SUITES, "; ".join(partes) if partes else "la lista de suites cambia",
                    f"{len(lista)} suites"))
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    doc = {
        "_que_es": "La lista CANONICA de suites de la skill. La escribe "
                   "`scripts/actualizar_conteos.py` y la compara "
                   "`scripts/auditar_mapa.py` con el arbol: si aqui falta una "
                   "suite que existe, o sobra una que no, la promesa del "
                   "SKILL.md envejece en silencio. Vive aqui (y no en el "
                   "SKILL.md) porque es dato de la herramienta, no prosa que "
                   "el agente tenga que leerse en cada peticion.",
        "_como_se_regenera": "python3 scripts/actualizar_conteos.py",
        "suites": lista,
    }
    with open(ruta, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")


def _transforma_frase_de_suites(texto, suites, cambios):
    """El SKILL.md deja de ENUMERAR las suites: dice cuantas hay y donde.

    La lista completa vive en `scripts/data/suites.json`. En el SKILL.md, 46
    rutas de test eran ruido para el agente (las lee en cada peticion) y una
    bomba de relojería para el limite de palabras: cada suite nueva sumaba
    una palabra y la puerta caia por una palabra.

    OJO con la cola: todo lo que viene DESPUES del fragmento tiene que
    seguir ahi. Una reescritura que se come el resto del archivo (la seccion
    de ejemplos, los pasos que van despues) es un fallo silencioso y
    destructivo: el archivo queda mas corto, el "--check" dice "nada" (ya no
    encuentra nada que cambiar) y nadie se entera.
    """
    mt = re.search(r"(unit tests in )(.+?)( pass via)", texto)
    if not mt:
        return texto
    antes = mt.group(2)
    lista = f"`scripts/_tests/` ({len(suites)} suites)"
    if antes == lista:
        return texto
    cambios.append(("SKILL.md", antes, lista))
    return texto[:mt.start()] + mt.group(1) + lista + mt.group(3) + texto[mt.end():]


def _transforma_readme(texto, refs, root, fft, suites, archivos, etiqueta, cambios):
    total = root + fft + archivos
    texto = _sustituye(
        texto, r"# \d+ motores raíz \+ \d+ en ffmpeg_tools/ \+ \d+ en _tests/ = \d+ scripts",
        f"# {root} motores raíz + {fft} en ffmpeg_tools/ + {archivos} en _tests/ = {total} scripts",
        etiqueta, cambios)
    texto = _sustituye(
        texto, r"# \d+ root \+ \d+ in ffmpeg_tools/ \+ \d+ in _tests/ = \d+ scripts",
        f"# {root} root + {fft} in ffmpeg_tools/ + {archivos} in _tests/ = {total} scripts",
        etiqueta, cambios)
    texto = _sustituye(texto, r"\d+ referencias en kebab-case\.md",
                       f"{refs} referencias en kebab-case.md", etiqueta, cambios)
    texto = _sustituye(texto, r"\d+ references in kebab-case\.md",
                       f"{refs} references in kebab-case.md", etiqueta, cambios)
    return texto


def _transforma_skill(texto, refs, nombres, cambios):
    """El SKILL.md tambien enuncia el numero de referencias (lo que hace de
    indice). Si la herramienta no lo reescribe, el numero se queda viejo en
    silencio: el guard lo ve, pero el que tiene que arreglarlo es esto."""
    texto = _transforma_frase_de_suites(texto, nombres, cambios)
    texto = _sustituye(texto, r"\d+ references with one canonical source",
                       f"{refs} references with one canonical source",
                       "SKILL.md", cambios)
    return texto


def _raiz_del_repo():
    """La raiz del repo, o None si la skill corre instalada (sin repo)."""
    return AM._raiz_git()


def main():
    ap = argparse.ArgumentParser(description="Recalcula los conteos de la skill")
    ap.add_argument("--check", action="store_true",
                    help="solo informa de lo que esta desfasado (no escribe)")
    args = ap.parse_args()

    refs, root, fft, suites, archivos = cuentas()
    total = root + fft + archivos
    print(f"referencias {refs} · scripts raiz {root} · ffmpeg_tools {fft} · "
          f"suites {suites} · archivos en _tests/ {archivos} · scripts en total {total}")

    raiz_repo = _raiz_del_repo()
    cambios = []

    def _informe(cambios):
        if not cambios:
            print("desfasado en: nada")
            return
        print("desfasado en:")
        for etiqueta, antes, despues in cambios:
            print(f"  {etiqueta}")
            print(f"      dice:  {antes}")
            print(f"      dira:  {despues}")
        print("  (corre `python scripts/actualizar_conteos.py` para reescribirlo)")

    if args.check:
        # se trabaja sobre una COPIA: el modo "solo informar" no puede
        # escribir en el arbol real (un --check que escribe es peor que
        # no tener --check)
        with tempfile.TemporaryDirectory() as tmp:
            copia = os.path.join(tmp, "editoria")
            shutil.copytree(BASE, copia, ignore=shutil.ignore_patterns("__pycache__"))
            _aplica(copia, None, refs, root, fft, suites, archivos, cambios)
            if raiz_repo:
                for nombre in ("README.md", "README.en.md"):
                    origen = os.path.join(raiz_repo, nombre)
                    if os.path.exists(origen):
                        # en --check los README se transforman EN MEMORIA:
                        # un modo de solo informar que escribe es peor que
                        # no tenerlo (y el test lo vigila)
                        texto = open(origen, encoding="utf-8").read()
                        _transforma_readme(texto, refs, root, fft, suites, archivos,
                                            nombre, cambios)
        _informe(cambios)
        return 0

    _aplica(BASE, raiz_repo, refs, root, fft, suites, archivos, cambios)
    _informe(cambios)
    return 0


def _aplica(dest_skill, dest_repo, refs, root, fft, suites, archivos, cambios):
    """Aplica los cambios a la copia de la skill indicada."""
    nombres = AM._suites_publicadas()
    # el canonico primero: si el SKILL.md dice cuantas suites hay, ese numero
    # tiene que salir de la misma lista que se acaba de escribir
    _escribe_suites(dest_skill, nombres, cambios)
    ruta = os.path.join(dest_skill, "references", "mapa.md")
    if os.path.exists(ruta):
        texto = open(ruta, encoding="utf-8").read()
        nuevo = _transforma_mapa(texto, refs, root, fft, suites, cambios)
        if nuevo != texto:
            open(ruta, "w", encoding="utf-8").write(nuevo)
    ruta = os.path.join(dest_skill, "SKILL.md")
    if os.path.exists(ruta):
        texto = open(ruta, encoding="utf-8").read()
        nuevo = _transforma_skill(texto, refs, nombres, cambios)
        if nuevo != texto:
            open(ruta, "w", encoding="utf-8").write(nuevo)
    if dest_repo:
        for nombre in ("README.md", "README.en.md"):
            origen = os.path.join(dest_repo, nombre)
            if os.path.exists(origen):
                _aplica_readme(origen, refs, root, fft, suites, archivos, cambios)


def _aplica_readme(ruta, refs, root, fft, suites, archivos, cambios):
    texto = open(ruta, encoding="utf-8").read()
    nuevo = _transforma_readme(texto, refs, root, fft, suites, archivos,
                                os.path.basename(ruta), cambios)
    if nuevo != texto:
        open(ruta, "w", encoding="utf-8").write(nuevo)


if __name__ == "__main__":
    sys.exit(main())
