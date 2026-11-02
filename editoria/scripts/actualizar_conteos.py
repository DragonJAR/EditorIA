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
import repertorio as REP  # noqa: E402  tabla §2b = repertorio.json

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
    escenas = AM._n_escenas_publicadas()
    root = AM._n_publicados("scripts", lambda p: p.endswith(".py") and p.count("/") == 1)
    fft = AM._n_publicados("scripts/ffmpeg_tools", lambda p: p.endswith(".py"))
    suites = len(AM._suites_publicadas())
    archivos = AM._n_publicados("scripts/_tests", lambda p: p.endswith(".py")
                                 and p != "__init__.py")
    return refs, root, fft, suites, archivos, escenas


def _sustituye(texto, patron, nuevo, etiqueta, cambios, todas=False):
    """Sustituye la coincidencia y anota el detalle del cambio.

    `cambios` guarda (archivo, lo que decia, lo que dira): el --check
    imprime eso, para que el que pregunta sepa QUE esta desfasado y no
    solo en que archivo.

    `todas=True` reescribe TODAS las apariciones: una cifra que enuncia el
    tamaño de una cosa va en mas de un sitio (el resumen, la tabla, el arbol
    de ficheros) y si solo se cambia el primero, el numero se queda viejo en
    los demas y el guard sigue diciendo que esta desfasado.
    """
    mt = re.search(patron, texto)
    if not mt:
        return texto
    if todas:
        m_ref = re.search(r"\d+", nuevo)
        nuevo_re = int(m_ref.group(0)) if m_ref else 0
        # solo es un CAMBIO si la CIFRA difiere: el texto encontrado puede
        # ser ya correcto y reportarlo como desfasado haria que el --check
        # se quejara de algo que esta bien (y el bucle no tendria salida)
        #
        # La cifra se saca del TEXTO QUE ENCONTRO, no de un grupo: los
        # patrones de esta lista ("40 escenas compuestas", "Catálogo de 40
        # escenas") no tienen grupo de captura, y buscarlo hacia que el
        # conjunto saliera VACIO: la herramienta no sustituia NADA y
        # reportaba "desfasado en: nada" mientras el guard seguia diciendo
        # que el numero estaba viejo (medido en la ronda 12: el catalogo
        # paso de 40 a 41 escenas y las tres prosa se quedaron en 40).
        numeros = set()
        for m in re.finditer(patron, texto):
            dm = re.search(r"\d+", m.group(0))
            if dm:
                numeros.add(int(dm.group(0)))
        if not numeros or numeros == {int(nuevo_re)}:
            return texto
        for numero in sorted(numeros):
            cambios.append((etiqueta, str(numero), str(nuevo_re)))

        def _cifras(mt):
            # se cambian SOLO las cifras de lo encontrado: el resto del
            # texto (con sus escapes y sus parentesis) se queda como esta
            return re.sub(r"\d+", str(nuevo_re), mt.group(0))
        return re.sub(patron, _cifras, texto)
    if mt.group(0) == nuevo:
        return texto
    cambios.append((etiqueta, mt.group(0).strip(), nuevo.strip()))
    return texto[:mt.start()] + nuevo + texto[mt.end():]


#: Los MISMOS sitios, pero escritos como PLACEHOLDER ("\d+ escenas"): el
#: patron de arriba no los pilla (busca DIGITOS, no el texto del patron) y el
#: README leia "\d+ escenas compuestas" al que lo abria (medido en la ronda
#: 12: cuatro sitios con el placeholder a la vista, en los dos README).
_PLACEHOLDERS_DE_ESCENAS = (
    (r"\\d\+ escenas compuestas", "{} escenas compuestas"),
    (r"\\d\+ scenes composed", "{} scenes composed"),
    (r"Suite visual de las \\d\+ escenas", "Suite visual de las {} escenas"),
    (r"Visual suite for all \\d\+ scenes", "Visual suite for all {} scenes"),
    (r"Muestras canónicas de las \\d\+ escenas", "Muestras canónicas de las {} escenas"),
    (r"Canonical samples for all \\d\+ scenes", "Canonical samples for all {} scenes"),
)


def _reescribe_catalogo(texto, escenas, etiqueta, cambios):
    """El tamaño del catalogo, con la REGLA del guard (una idea, un canonico).

    La herramienta y el guard usan la MISMA tabla (`auditar_mapa.py`): toda
    cifra que el guard senala, esta herramienta sabe arreglarla. Antes cada
    uno tenia su propia lista de frases, y una forma que el guard veia y la
    herramienta no podia tocar era un numero viejo que se agingaba en
    silencio: MEDIDO, la puerta daba verde con 18 cifras falsas en 12
    ficheros (la prosa decia 39 y 40 con un motor de 41 escenas).

    Los reemplazos se aplican DE FINAL A PRINCIPIO: al cambiar una cifra
    cambia el largo del texto, y si se aplicaran en orden las posiciones de
    las siguientes dejarian de valer (un "39" de tres digitos por un "42" de
    dos desplaza todo lo que viene despues).
    """
    reemplazos = []
    for h in AM._cifras_del_catalogo(texto):
        if h["exclusion"] or h["cifra"] == escenas:
            continue
        reemplazos.append((h["ini"], h["fin"], str(escenas),
                           f"dice {h['cifra']} escenas del catalogo",
                           f"{escenas} escenas del catalogo"))
    for d in AM._descomposiciones_del_catalogo(texto):
        nuevo = escenas - d["primera"]
        if nuevo < 0 or d["segunda"] == nuevo:
            continue
        reemplazos.append((d["ini"], d["fin"], str(nuevo),
                           f"dice {d['primera']}+{d['segunda']} escenas del catalogo",
                           f"{d['primera']}+{nuevo} escenas del catalogo"))
    for p in AM._pares_del_catalogo(texto):
        if p["primera"] == escenas and p["segunda"] == escenas:
            continue
        antes = f"dice {p['primera']}/{p['segunda']} escenas del catalogo"
        despues = f"{escenas}/{escenas} escenas del catalogo"
        reemplazos.append((p["ini"], p["fin"], str(escenas), antes, despues))
        reemplazos.append((p["ini2"], p["fin2"], str(escenas), antes, despues))
    if not reemplazos:
        return texto
    reemplazos.sort(key=lambda r: r[0], reverse=True)
    for ini, fin, nuevo, antes, despues in reemplazos:
        texto = texto[:ini] + nuevo + texto[fin:]
        cambios.append((etiqueta, antes, despues))
    return texto


def _transforma_escenas(texto, escenas, etiqueta, cambios):
    r"""El tamaño del catalogo en el texto, con la REGLA del guard.

    Son dos cosas y las dos son el MISMO numero:
    1. las cifras que la prosa enuncia ("Suite visual de las 40 escenas"):
       las reescribe la REGLA del guard (`auditar_mapa.FORMAS_CATALOGO`), la
       misma que vigila y la misma que usa `_reescribe_catalogo`. Una idea,
       un canonico: la herramienta NO tiene su propia lista de formas (cuando
       la tuvo, las dos se desincronizaron en silencio).
    2. los PLACEHOLDERS ("\d+ escenas compuestas"): sitios donde la prosa
       escribio el PATRON en vez de la cifra. El guard no los ve (no hay
       digito que contar) y se quedaban a la vista del que leia el README.
    """
    texto = _reescribe_catalogo(texto, escenas, etiqueta, cambios)
    for patron, plantilla in _PLACEHOLDERS_DE_ESCENAS:
        if not re.search(patron, texto):
            continue
        nuevo = plantilla.format(escenas)
        texto = re.sub(patron, lambda _m: nuevo, texto)
        cambios.append((etiqueta, "PLACEHOLDER (\\d+)", nuevo))
    return texto


#: La lista de escenas que enuncia la prosa (los README): el guard la compara
#: por CONJUNTO contra el catalogo del motor, no por el numero.
LISTA_DE_ESCENAS = re.compile(
    r"(?:\*)*(\d+)(?:\*)*\s+(?:tipos(?:\s+de\s+escena)?|scene\s+types|scenes)"
    r"(?:\*)*\s*[—-]\s*(.+?)(?=\n\s*[-*]\s|\n\s*\n|\Z)", re.M | re.S)


def _transforma_lista_de_escenas(texto, catalogo, etiqueta, cambios):
    """La lista de escenas que enuncia la prosa: se ESCRIBE desde el motor.

    El guard la compara por CONJUNTO contra las claves de `SCENES`: una lista
    puede tener la cifra correcta y faltar una escena (asi se quedaron
    `callout`, `index` y `orbOpen` fuera del README en espanol, con el
    numero bien puesto). Aqui la lista sale del motor, asi que no se puede
    quedar vieja: lo que falta se anade al final y lo que sobra (una escena
    que ya no existe) se quita.

    El orden curado de la prosa se respeta: solo se anade al final lo que
    falta, y el conector ("y" / "and") es el que ya usa el texto.
    """
    if not catalogo:
        return texto

    def _uno(mt):
        cuerpo = mt.group(2)
        cola = ""
        mc = re.search(r"([.!?])\s*$", cuerpo)
        if mc:
            cola = mc.group(1)
            cuerpo = cuerpo[:mc.start()]
        nombres = re.findall(r"`([^`]+)`", cuerpo)
        if not nombres:
            return mt.group(0)
        conect = "and" if re.search(r"\band\s+`[^`]+`\s*$", cuerpo) else "y"
        faltan = [n for n in catalogo if n not in nombres]
        sobran = [n for n in nombres if n not in catalogo]
        if not faltan and not sobran:
            return mt.group(0)
        orden = [n for n in nombres if n in catalogo] + faltan
        nueva = ", ".join(f"`{n}`" for n in orden[:-1])
        nueva += f" {conect} `{orden[-1]}`" + cola
        cambios.append((etiqueta, f"{len(nombres)} escenas listadas",
                         f"{len(orden)} escenas listadas"))
        ini = mt.start(2) - mt.start(0)
        fin = mt.end(2) - mt.start(0)
        return mt.group(0)[:ini] + nueva + mt.group(0)[fin:]

    return LISTA_DE_ESCENAS.sub(_uno, texto)


def catalogo_de_escenas():
    """Los NOMBRES del catalogo (las claves de `SCENES`), no solo la cuenta."""
    render = os.path.join(BASE, "scripts", "render_plan.py")
    if not os.path.isfile(render):
        return []
    return sorted(AM._claves_de_escenas(render))


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


def _transforma_readme(texto, refs, root, fft, suites, archivos, escenas, etiqueta, cambios,
                       catalogo=None):
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
    # el tamaño del CATALOGO de escenas: lo vigila el guard y lo enuncian los
    # README. Sin esto, anadir una escena dejaba la cifra vieja (y el guard
    # la senalaba como conteo obsoleto: no habia forma de arreglarlo con la
    # herramienta, que es justo lo que la herramienta debe evitar)
    texto = _transforma_escenas(texto, escenas, etiqueta, cambios)
    # y la LISTA de escenas: se escribe desde el motor (no es una copia)
    texto = _transforma_lista_de_escenas(texto, catalogo or [], etiqueta, cambios)
    return texto


def _transforma_skill(texto, refs, nombres, cambios, escenas=0):
    """El SKILL.md tambien enuncia el numero de referencias (lo que hace de
    indice). Si la herramienta no lo reescribe, el numero se queda viejo en
    silencio: el guard lo ve, pero el que tiene que arreglarlo es esto."""
    texto = _transforma_frase_de_suites(texto, nombres, cambios)
    texto = _sustituye(texto, r"\d+ references with one canonical source",
                       f"{refs} references with one canonical source",
                       "SKILL.md", cambios)
    if escenas:
        texto = _transforma_escenas(texto, escenas, "SKILL.md", cambios)
    return texto


def _raiz_del_repo():
    """La raiz del repo, o None si la skill corre instalada (sin repo)."""
    return AM._raiz_git()


def main():
    ap = argparse.ArgumentParser(description="Recalcula los conteos de la skill")
    ap.add_argument("--check", action="store_true",
                    help="solo informa de lo que esta desfasado (no escribe)")
    args = ap.parse_args()

    refs, root, fft, suites, archivos, escenas = cuentas()
    catalogo = catalogo_de_escenas()
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
            _aplica(copia, None, refs, root, fft, suites, archivos, escenas, cambios,
                     catalogo)
            if raiz_repo:
                for nombre in ("README.md", "README.en.md"):
                    origen = os.path.join(raiz_repo, nombre)
                    if os.path.exists(origen):
                        # en --check los README se transforman EN MEMORIA:
                        # un modo de solo informar que escribe es peor que
                        # no tenerlo (y el test lo vigila)
                        texto = open(origen, encoding="utf-8").read()
                        _transforma_readme(texto, refs, root, fft, suites, archivos,
                                           escenas, nombre, cambios, catalogo)
        _informe(cambios)
        return 0

    _aplica(BASE, raiz_repo, refs, root, fft, suites, archivos, escenas, cambios,
             catalogo)
    _informe(cambios)
    return 0


def _contrato_cli(dest_skill=None):
    """(cumplen, total): las CLIs de ffmpeg_tools y las que cumplen el contrato.

    Es la MISMA cuenta que hace el guard (`scripts/auditar_mapa.py`), con la
    MISMA regla: una CLI es una CLI si usa argparse, y cumple el contrato si
    usa `add_common`, `apply_common` y `emit`. Si las dos cuentas no
    coinciden, la herramienta escribiria un numero que el guard rechaza: el
    bucle "corre la herramienta y vuelve a fallar" no tendria salida.

    Se cuenta sobre `dest_skill` (la copia que se esta editando) y no sobre
    BASE: en modo --check se trabaja sobre una copia, y contar la del arbol
    real daria un numero que no es el de lo que se esta escribiendo.
    """
    fft = os.path.join(dest_skill or BASE, "scripts", "ffmpeg_tools")
    cumplen = 0
    total = 0
    if not os.path.isdir(fft):
        return cumplen, total
    for f in sorted(os.listdir(fft)):
        if not f.endswith(".py") or f.startswith("_"):
            continue
        try:
            t = open(os.path.join(fft, f), encoding="utf-8").read()
        except OSError:
            continue
        if "ArgumentParser" not in t and "argparse" not in t:
            continue          # un modulo no es una CLI
        total += 1
        if "add_common" in t and "apply_common" in t and "emit(" in t:
            cumplen += 1
    return cumplen, total


def _transforma_cli_contract(texto, cumplen, total, cambios):
    """La frase del contrato: "N de las M cumplen el contrato".

    Este numero vivia en la prosa y NADIE lo reescribia: cuando se anadia
    una herramienta nueva a `ffmpeg_tools/`, la frase se quedaba vieja y el
    guard la senalaba (conteo obsoleto). El numero es del guard, y lo
    escribe la herramienta: si no, cada CLI nueva obligaba a contar a mano.
    """
    # el `\s+` del patron salta el salto de linea: la prosa puede partir la
    # frase ("cumplen el\ncontrato") y el numero sigue siendo el mismo. El
    # patron del guard (`scripts/auditar_mapa.py`) usa `\s+` tambien, asi que
    # los dos cuentan la MISMA frase.
    #
    # La reescritura conserva COMO estaba partida: si la frase vivia en dos
    # lineas, se deja en dos lineas. Un numero que se reescribe en una sola
    # linea larga deja la prosa fea, y el proximo --check lo detectaria como
    # desfasado otra vez (el texto viejo ya no esta).
    nuevo = f"{cumplen} de las {total} cumplen el contrato"
    mt = re.search(r"\d+\s+de\s+las\s+\d+\s+cumplen\s+el\s+contrato", texto)
    if not mt:
        return texto
    # la COMPARACION ignora los espacios: la prosa puede partir la frase en
    # dos lineas y el numero sigue siendo el mismo. Si no, el --check se quejaria
    # de un texto que ya dice la verdad (y el bucle "corrige y vuelve a fallar"
    # no tendria salida).
    if re.sub(r"\s+", " ", mt.group(0)).strip() == nuevo:
        return texto
    if "\n" in mt.group(0):
        # estaba partida: se parte por el mismo punto (despues de "cumplen el")
        partes_nuevo = nuevo.split(" cumplen el contrato")
        nuevo = partes_nuevo[0] + " cumplen el\ncontrato"
    cambios.append(("references/cli-contract.md", mt.group(0).strip(), nuevo.strip()))
    return texto[:mt.start()] + nuevo + texto[mt.end():]


def _aplica(dest_skill, dest_repo, refs, root, fft, suites, archivos, escenas, cambios,
           catalogo=None):
    """Aplica los cambios a la copia de la skill indicada."""
    nombres = AM._suites_publicadas()
    # el canonico primero: si el SKILL.md dice cuantas suites hay, ese numero
    # tiene que salir de la misma lista que se acaba de escribir
    _escribe_suites(dest_skill, nombres, cambios)
    ruta = os.path.join(dest_skill, "references", "mapa.md")
    if os.path.exists(ruta):
        texto = open(ruta, encoding="utf-8").read()
        nuevo = _transforma_mapa(texto, refs, root, fft, suites, cambios)
        nuevo = _reescribe_catalogo(nuevo, escenas, "references/mapa.md", cambios)
        if nuevo != texto:
            open(ruta, "w", encoding="utf-8").write(nuevo)
    ruta = os.path.join(dest_skill, "SKILL.md")
    if os.path.exists(ruta):
        texto = open(ruta, encoding="utf-8").read()
        nuevo = _transforma_skill(texto, refs, nombres, cambios, escenas)
        nuevo = _reescribe_catalogo(nuevo, escenas, "SKILL.md", cambios)
        if nuevo != texto:
            open(ruta, "w", encoding="utf-8").write(nuevo)
    # el contrato de CLI: el numero de las que cumplen vive en la prosa y lo
    # escribe esta herramienta (si no, cada CLI nueva lo dejaba viejo)
    ruta = os.path.join(dest_skill, "references", "cli-contract.md")
    if os.path.exists(ruta):
        texto = open(ruta, encoding="utf-8").read()
        cumplen, total = _contrato_cli(dest_skill)
        nuevo = _transforma_cli_contract(texto, cumplen, total, cambios)
        if nuevo != texto:
            open(ruta, "w", encoding="utf-8").write(nuevo)
    # TODA la prosa que el guard vigila: hasta ahora la herramienta solo
    # escribia mapa.md, SKILL.md, cli-contract.md y los README, pero el guard
    # mira el TAMANO DEL CATALOGO en las 63 referencias. Una forma que el
    # guard ve y la herramienta no puede arreglar es un numero viejo que se
    # aginga en silencio (medido en la ronda 13: la puerta de af84307 fallo
    # por "la doc cuenta 41 escenas como el codigo" en escenas.md y
    # arquitectura.md, dos ficheros que la herramienta NO tocaba).
    refs_dir = os.path.join(dest_skill, "references")
    if os.path.isdir(refs_dir):
        for nombre in sorted(os.listdir(refs_dir)):
            if not nombre.endswith(".md") or nombre in ("mapa.md", "cli-contract.md"):
                continue      # mapa.md y cli-contract.md tienen su propia via
            ruta = os.path.join(refs_dir, nombre)
            texto = open(ruta, encoding="utf-8").read()
            nuevo = _transforma_escenas(texto, escenas, f"references/{nombre}", cambios)
            nuevo = _reescribe_catalogo(nuevo, escenas, f"references/{nombre}", cambios)
            nuevo = _transforma_lista_de_escenas(nuevo, catalogo or [],
                                                 f"references/{nombre}", cambios)
            if nombre == "intencion-escena.md":
                # la tabla §2b sale de repertorio.json (no se copia a mano)
                ruta_rep = os.path.join(dest_skill, "scripts", "data",
                                        "repertorio.json")
                datos_rep = REP.cargar(ruta_rep) if os.path.exists(ruta_rep) \
                    else REP.cargar()
                sincronizada = REP.reescribir_tabla_prosa(nuevo, datos_rep)
                if sincronizada != nuevo:
                    cambios.append((
                        "references/intencion-escena.md",
                        "tabla §2b desfasada respecto a repertorio.json",
                        "tabla §2b reescrita desde repertorio.json",
                    ))
                    nuevo = sincronizada
            if nuevo != texto:
                open(ruta, "w", encoding="utf-8").write(nuevo)
    if dest_repo:
        for nombre in ("README.md", "README.en.md"):
            origen = os.path.join(dest_repo, nombre)
            if os.path.exists(origen):
                _aplica_readme(origen, refs, root, fft, suites, archivos, escenas,
                               cambios, catalogo)


def _aplica_readme(ruta, refs, root, fft, suites, archivos, escenas, cambios,
                  catalogo=None):
    texto = open(ruta, encoding="utf-8").read()
    nuevo = _transforma_readme(texto, refs, root, fft, suites, archivos, escenas,
                                os.path.basename(ruta), cambios, catalogo)
    nuevo = _reescribe_catalogo(nuevo, escenas, os.path.basename(ruta), cambios)
    if nuevo != texto:
        open(ruta, "w", encoding="utf-8").write(nuevo)


if __name__ == "__main__":
    sys.exit(main())
