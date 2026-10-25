#!/usr/bin/env python3
"""auditar_mapa.py — que EditorIA siga siendo un sistema y no un archon.

Comprueba las TRES condiciones que hacen de la skill un todo y no una bolsa
de archivos:

  1. ALCANZABLE: todo archivo de contenido se llega desde SKILL.md.
  2. SIN PIES PERDIDOS: cada referencia declara su canonico, su dominio y sus
     vecinos, y todo lo que declara existe.
  3. SIN CONTRADICCION: el mapa y los pies coinciden en el canonico de cada
     archivo, y el mapa menciona a todos.

Y, ademas, que no queden enlaces rotos hacia archivos de la propia skill
(las rutas que son ejemplos, artefactos de runtime o atribuciones a otro
proyecto se declaran aparte, con su motivo).

Uso:
    python3 scripts/auditar_mapa.py
    python3 scripts/auditar_mapa.py --json informe.json

Sale 0 si todo esta bien, 1 si hay islas, 2 si la skill no se encuentra.
"""
import argparse
import json
import os
import re
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFS = os.path.join(BASE, "references")


def _raiz_git():
    """La raiz del repo donde vive la skill, o None si no hay repo."""
    try:
        r = subprocess.run(["git", "-C", BASE, "rev-parse", "--show-toplevel"],
                           capture_output=True, text=True, timeout=10)
        if r.returncode != 0 or not r.stdout.strip():
            return None
        # git devuelve la ruta CANONICA (en macOS /tmp es un symlink a
        # /private/tmp): sin canonizar, relpath entre las dos rutas da
        # una ruta hacia arriba y nada cuadra
        return os.path.realpath(r.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        return None


def _contenido_publicado(rel):
    """El contenido de un archivo de la skill, tal cual esta en el arbol.

    El guard compara el documento contra el codigo, y los dos viven en el
    arbol de trabajo. Lo que se compara contra el HISTORICO (el commit
    anterior) es otra cosa, y va a git explicitamente.
    """
    ruta = os.path.join(BASE, rel)
    if os.path.exists(ruta):
        with open(ruta, encoding="utf-8") as fh:
            return fh.read()
    return ""


def _paths_publicados(subruta):
    """Las rutas (relativas a `subruta`) de los archivos de esa carpeta.

    Se cuenta el ARBOL, no lo commiteado: el guard compara el documento
    contra el codigo, y los dos viven en el arbol de trabajo. Compararlos
    contra HEAD (una tercera cosa) haria que el guard marcara documentos
    que estan bien para lo publicado. Lo que si se vigila contra el
    historico es el commit que arrastra trabajo en vuelo: ese lo mira
    `_chequear_commit_que_arrastra_trabajo`, que va a git explicitamente.
    """
    base = os.path.join(BASE, subruta)
    if not os.path.isdir(base):
        return []
    out = []
    for d, _, fs in os.walk(base):
        if "__pycache__" in d:
            continue
        for f in fs:
            # el prefijo es el de la RAMA GIT ("scripts/render_plan.py"), no el
            # de la carpeta ("render_plan.py"): las dos ramas tienen que contar
            # igual, o el conteo raiz se lleva los archivos de las subcarpetas
            out.append(os.path.relpath(os.path.join(d, f), BASE).replace(os.sep, "/"))
    return out


def _n_publicados(subruta, filtro):
    """Cuantos archivos hay en esa carpeta del ARBOL."""
    return len([p for p in _paths_publicados(subruta) if filtro(p)])

MAPA = "references/mapa.md"
PIE = re.compile(r"^→ Canónico: `(?P<can>[^`]+)` · Dominio: (?P<dom>[^·]+?) · "
                  r"Vecinos: (?P<vec>[^\n]+)$", re.M)
REF = re.compile(r"(?:references|scripts|film|metricas|assets|brand)/[A-Za-z0-9_./-]+\.(?:md|py|json|png|mp4|mp3|ttf)")
MEDIA = (".mp3", ".mp4", ".png", ".ttf")
SCRIPT_REF = re.compile(r"scripts/[A-Za-z0-9_./-]+\.py")

# La prosa de la skill esta en español/ingles: un ideograma, un kana o un
# hangul son BASURA de una generacion, y publicar eso es publicar un texto
# roto que nadie caza: se lee como un fallo de tipografia y se asume que es
# una decision.
#
# UNA sola definicion para los dos sitios donde puede colarse: el ARBOL (lo
# lee validate_skill.py) y el HISTORIAL (lo lee este fichero). Dos
# definiciones serian dos reglas que se pueden divergir.
#
# Los rangos van en ESCAPES, no literales: si el fuente de este fichero
# contuviera los caracteres, el guard se marcaria a si mismo.
RANGOS_BASURA = [(0x3000, 0x303F), (0x3040, 0x30FF), (0x3400, 0x4DBF),
                 (0x4E00, 0x9FFF), (0xF900, 0xFAFF), (0xAC00, 0xD7AF)]
RE_BASURA = re.compile(
    "[" + "".join(chr(a) + "-" + chr(b) for a, b in RANGOS_BASURA) + "]")

# Rutas que NO son archivos de la skill: se declaran con su motivo para que
# la auditoria no marque ruido real.
EXCEPCIONES = {
    "metricas/historial.json": "artefacto de runtime: lo crea --historial al medir",
    "brand/mi_pack.json": "ejemplo del pack propio del usuario (references/brand-packs.md)",
    "assets/isotipo.png": "ejemplo de la plantilla de un brand pack (references/brand-packs.md)",
    "assets/logotipo.png": "ejemplo de la plantilla de un brand pack (references/brand-packs.md)",
    "assets/mono.ttf": "ejemplo de la plantilla de un brand pack (references/brand-packs.md)",
    "assets/texto.ttf": "ejemplo de la plantilla de un brand pack (references/brand-packs.md)",
    "assets/titular.ttf": "ejemplo de la plantilla de un brand pack (references/brand-packs.md)",
    "scripts/_platforms.py": "atribucion al proyecto de origen (kajisho5/ffmpeg-skill)",
    "scripts/check.py": "atribucion al proyecto de origen (kajisho5/ffmpeg-skill)",
    # packs de ejemplo: el nombre del pack del cliente, no un archivo de la skill
    "brand/mi_marca.json": "ejemplo: el pack del cliente, que se crea al vuelo",
    "brand/mi-marca.json": "ejemplo: el pack del cliente, que se crea al vuelo",
    "brand/nuevo.json": "ejemplo: el pack del cliente, que se crea al vuelo",
    "brand/otro.json": "ejemplo: el pack del cliente, que se crea al vuelo",
    "brand/tu-marca.json": "ejemplo: el pack del cliente, que se crea al vuelo",
    "brand/x.json": "ejemplo: el pack del cliente, que se crea al vuelo",
}

# ── reglas con UN SOLO valor ───────────────────────────────────────────
# Una regla que la skill enseña con un numero no puede enunciarse con otro
# numero en otro archivo: quien lea el segundo creeria lo que dice ahi.
# Estas se comparan contra el valor del motor (render_plan.py / _delivery.py).
#   patron : regex con un grupo = el valor enunciado
#   tipo   : "exacto" | "minimo" | "maximo"
#   valor  : el valor que dice el motor
#: los numeros que la prosa enuncia EN PALABRAS. Solo estos: cualquier otra
#: palabra delante de "comprobaciones" ("todas las", "ambas") no es una cifra.
NUMEROS_EN_PALABRAS = {
    "un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
    "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10,
}

LOG_FECHA = re.compile(r"^\s*-\s*\d{4}-\d{2}-\d{2}\s*·")   # entrada de log: registro, no regla

#: Convenciones que el CODIGO le pide al usuario (en un aviso o en un
#: mensaje) y que tienen que estar ESCRITAS en las referencias. Un puntero a
#: una convencion que no esta escrita en ningun lado no sirve de nada: el
#: que recibe el aviso no puede saber que escribir. Ya ha pasado dos veces
#: (la convencion de atribucion y la de "voz de marca").
CONVENCIONES_QUE_EXIGEN_DOC = (
    ("voz de marca", "references/copy.md"),
    ("sesion-", "references/mapa.md"),
)
REGLAS_UNICAS = [
    {"nombre": "margen lateral en vertical", "tipo": "minimo", "valor": 151,
     "patron": r"[Mm]árgenes? laterales[\s\S]{0,120}?(\d{2,4})\s*px"},
    {"nombre": "ancho de la zona segura", "tipo": "exacto", "valor": 778,
     "patron": r"zona segura de (\d{3})\s*px|(\d{3})\s*px de (?:la )?zona segura"},
    {"nombre": "techo general de overshoot", "tipo": "exacto", "valor": 8,
     "patron": r"techo general (\d+)\s?%"},
    # la densidad de cues: "8-12 cues/min", "8-12 por minuto", "entre 8 y 12
    # cues por minuto". El patron exige la unidad (por minuto / per minute):
    # sin ella engancharia la cantidad TOTAL de cues de una variante de tono
    # ("2-3 cues secos" en sfx.md), que es otra magnitud.
    {"nombre": "densidad de cues", "tipo": "exacto", "valor": (8, 12),
     "patron": r"(\d+)\s*(?:[-–]|\s+y\s*)\s*(\d+)\s+"
               r"(?:cues\s*(?:/\s*min\b|por\s+minuto|per\s+minute)|por\s+minuto)"},
    # la densidad: el motor penaliza fuera de 0.5-2.0 eventos/s. El patron
    # exige que el bloque ATRIBUYA la cifra al motor: hay dos cosas distintas
    # y no se pueden mezclar. Lo que el motor VIGILA (una cifra) y el ritmo
    # que se considera comodo (otra, mas estrecha) son reglas diferentes, y
    # el enunciado que dice "el motor pide" tiene que decir la del motor.
    {"nombre": "densidad de movimiento", "tipo": "exacto", "valor": (0.5, 2.0),
     "patron": r"[Mm]otor[^.\n]{0,60}?cada\s+(\d[.,]\d)\s*[-–]\s*(\d[.,]\d)"
               r"|[Mm]otor[^.\n]{0,60}?(\d[.,]\d)\s*[-–]\s*(\d[.,]\d)\s*(?:eventos|s\b)"},
    {"nombre": "piso de letra", "tipo": "exacto", "valor": 26,
     "patron": r"(?:[Pp]iso de letra|letra m[ií]nima|m[ií]nimo de tama[ñn]o de texto|"
               r"tama[ñn]o m[ií]nimo de texto|letra que no se lee)[^.\n]{0,120}?(\d{2})\s*px"},
    # la escala tipografica del motor: un rol = un tamano, en todo el catalogo.
    # El valor vive aqui y lo ata al motor un test (como el piso de letra).
    {"nombre": "escala tipografica", "tipo": "exacto", "valor": (120.0, 44.0, 36.0, 32.0, 28.0),
     "patron": r"`titular`\s*(\d+)\s*·\s*`rotulo`\s*(\d+)\s*·\s*`dato`\s*(\d+)\s*·\s*"
               r"`secundario`\s*(\d+)\s*·\s*`nota`\s*(\d+)"},
    # el target de sonoridad de la skill: -14 enérgico / -16 calmo. son DOS
    # valores legitimos y ninguno mas: un "-16/-15 para calmado" deja a quien
    # mezcla sin saber a donde apuntar el loudnorm, y el patron engancha el
    # numero que PRECEDE al calificador ("-16 LUFS (calmo)", "-15 para
    # calmado") o al que lo sigue cuando no hay otro entre medias.
    {"nombre": "target de sonoridad enérgico", "tipo": "exacto", "valor": -14.0,
     "patron": r"([−\-]?\d{1,2})\s*(?:LUFS\s*)?[^\w]{0,3}(?:para\s+|de\s+)?en[ée]rg\w*"},
    {"nombre": "target de sonoridad calmo", "tipo": "exacto", "valor": -16.0,
     "patron": r"([−\-]?\d{1,2})\s*(?:LUFS\s*)?[^\w]{0,3}(?:para\s+|de\s+)?calm\w*"},
    # el aire de voz: la voz entra en `from + 0,40`, asi que el fin de la voz
    # es la duracion CRUDA del wav MAS 0,40. Sin esta regla, la prosa puede
    # quedarse con el numero viejo si el codigo cambia el aire (y quien lea
    # la prosa cuenta mal y depura el reloj a mano). El valor lo ata al
    # codigo un test, como el piso de letra con LETRA_MIN.
    {"nombre": "aire de voz", "tipo": "exacto", "valor": 0.40,
     "patron": r"duración CRUDA del wav[^.\n]{0,80}?\+\s*(\d+[.,]\d+)"},
    # el coeficiente de variacion minimo de las duraciones de toma: el
    # metronomo. Mismo motivo que el aire: si el codigo cambia el umbral, la
    # prosa se queda con el numero viejo y nadie lo dice.
    {"nombre": "cadencia minima (CV de duraciones)", "tipo": "exacto", "valor": 0.25,
     "patron": r"variaci[oó]n de duraciones de toma[^.\n]{0,20}?(\d+[.,]\d+)"},
    # la banda de error de la estimacion silabica: el margen del reloj de la
    # voz es proporcional al hueco (un 25 % del hueco, con un minimo de 0,3 s).
    # Mismo motivo que el aire: si el codigo cambia la banda, la prosa se
    # queda con el numero viejo y quien la lea deduce una tolerancia que no
    # es la real. Los dos valores los atan al codigo sendos tests.
    {"nombre": "banda de la estimación (% del hueco)", "tipo": "exacto", "valor": 25.0,
     "patron": r"(\d{1,2})\s*%\s*del hueco"},
    {"nombre": "margen mínimo de la estimación", "tipo": "exacto", "valor": 0.30,
     "patron": r"m[ií]nimo de (\d+[.,]\d+)\s*s"},
    # el numero de referencias: lo cuenta el arbol. Las dos menciones sueltas
    # en prosa (la del indice y la del SKILL.md) tienen que decir el mismo
    # numero, o quien las lee cuenta mal. Mismo motivo que las demas reglas:
    # si el numero cambia, la prosa se queda con el viejo y nadie lo dice.
    {"nombre": "numero de referencias", "tipo": "exacto", "valor": 63,
     "patron": r"index of this skill: (\d+) references|contra las (\d+) referencias"},
]


def _prosa(texto):
    """El texto SIN las entradas de log fechadas.

    Una entrada de log es un REGISTRO de una decision pasada (y puede citar
    un valor que ya no aplica); una regla es prosa que dice lo que hay que
    hacer HOY. Solo la prosa se compara con los valores del motor.
    """
    out, saltando = [], False
    for ln in texto.splitlines():
        if LOG_FECHA.match(ln):
            saltando = True
            continue
        if saltando:
            if not ln.strip() or ln.startswith((" ", "\t")):
                continue      # continuacion de la entrada
            saltando = False
        out.append(ln)
    return "\n".join(out)


def _numero(texto):
    """El numero de la prosa, listo para float().

    La prosa escribe los decimales con coma ("0,5") y el menos con el signo
    tipografico U+2212 ("-14"), que float() no entiende: sin normalizar,
    float() reventaria, la regla se compararia NUNCA y el numero equivocado
    pasaria sin que nadie lo viera. Un guard que se salta la mitad de sus
    reglas no es un guard: es una costumbre.
    """
    return texto.replace(",", ".").replace("−", "-").replace("–", "-")


def _regla_de_este_estado(regla):
    """¿La regla existe tambien en el archivo de guardas de ESTE estado?

    La auditoria corre dos veces: contra lo publicado (HEAD) y contra el
    arbol de trabajo. En la pasada de lo publicado, las REGLAS que corren
    son las del arbol de trabajo (el codigo no se recarga), asi que una
    regla que se acaba de escribir todavia no existe en el estado
    publicado: sin esta comprobacion, esa regla se buscaria en la prosa de
    HEAD, no lo encontraria (su prosa va sin commitear todavia) y
    fallaria por algo que todavia no esta publicado.
    """
    ruta = os.path.join(BASE, "scripts", "auditar_mapa.py")
    if not os.path.exists(ruta):
        return True
    try:
        with open(ruta, encoding="utf-8") as fh:
            texto = fh.read()
    except OSError:
        return True
    return f'"{regla["nombre"]}"' in texto


def _chequear_reglas(problemas):
    """Que una regla con un valor unico no se enuncie con otro valor."""
    for regla in REGLAS_UNICAS:
        valores = {}
        for f in sorted(os.listdir(REFS)):
            if not f.endswith(".md"):
                continue
            with open(os.path.join(REFS, f), encoding="utf-8") as fh:
                texto = _prosa(fh.read())
            # por BLOQUES (parrafos), no por lineas: una regla puede estar
            # partida en dos lineas y el numero caerse en la segunda
            for bloque in re.split(r"\n\s*\n", texto):
                # TODOS los enunciados del bloque, no solo el primero: un
                # bloque puede decir el valor bueno y el malo a la vez (la
                # forma "-16 LUFS (calmo) ... -15 para calmado"), y con un
                # solo enunciado el guard no veria el segundo
                for m in re.finditer(regla["patron"], bloque):
                    grupos = [g for g in m.groups() if g]
                    if not grupos:
                        continue
                    # el decimal puede venir con coma ("0,5-2 s") o con punto:
                    # sin normalizar, float() reventa y la regla NUNCA se compara
                    # (un numero con coma se escapa del guard por mucho que se
                    # enuncie en la prosa). y el menos de la prosa es el U+2212
                    # ("-14"), que float() tampoco entiende: una regla con
                    # valor NEGATIVO se compararia sola si no se normaliza
                    try:
                        if isinstance(regla["valor"], tuple):
                            v = tuple(float(_numero(g)) for g in grupos)
                        else:
                            v = float(_numero(grupos[0]))
                    except ValueError:
                        continue
                    valores.setdefault(v, set()).add(f)
        if not valores:
            # Una regla cuyo patron deja de casar se APAGA en silencio: no
            # encuentra ningun numero que comparar y el guard dice "todo
            # bien" sin mirar. Un guard que no encuentra su objeto tiene que
            # decirlo (la misma regla que el encabezado de conteos).
            #
            # Pero solo si la regla existe en ESTE estado: la pasada de lo
            # publicado corre con las reglas del arbol de trabajo (el codigo
            # no se puede cambiar en caliente), y una regla nueva con su prosa
            # todavia sin commitear no puede fallar alli. Es trabajo en
            # vuelo, que la segunda pasada ya marca como aviso.
            if not _regla_de_este_estado(regla):
                continue
            problemas.append({
                "tipo": "guard sin objeto",
                "archivo": "references/",
                "msg": f"la regla '{regla['nombre']}' no encuentra su objeto en la prosa: "
                       f"el patron {regla['patron']!r} ya no casa y esta regla no comprueba nada",
            })
            continue
        esperado = regla["valor"]
        for v, fs in sorted(valores.items()):
            if isinstance(v, tuple):
                ok = v == esperado
            elif regla["tipo"] == "exacto":
                ok = v == esperado
            elif regla["tipo"] == "minimo":
                ok = v >= esperado
            else:
                ok = v <= esperado
            if not ok:
                problemas.append({"tipo": "valor divergente", "archivo": ", ".join(sorted(fs)),
                                  "msg": f"la regla '{regla['nombre']}' dice {v} y el motor usa {esperado}"})


def _chequear_conteos(problemas):
    """Que los numeros del encabezado de mapa.md coincidan con la realidad.

    Ese encabezado ("52 referencias, 36 scripts, ...") es la tarjeta de
    presentacion de la skill: si envejece, miente sobre lo que contiene. No
    es un problema cosmético: es la unica linea que resume el alcance.
    """
    encabezado = os.path.join(REFS, "mapa.md")
    if not os.path.exists(encabezado):
        return
    with open(encabezado, encoding="utf-8") as fh:
        texto = fh.read()
    m = re.search(r"(\d+)\s+referencias,\s*(\d+)\s+scripts,\s*(\d+)\s+herramientas"
                  r"\s+de\s+ffmpeg\s+y\s*(\d+)\s+suites", texto)
    if not m:
        # el encabezado se rewordio y el patron dejo de casar: el guard se
        # apagaba en silencio y decia "todo bien" sin mirar el resumen de la
        # skill. un guard que no encuentra su objeto tiene que decirlo
        problemas.append({
            "tipo": "guard sin objeto", "archivo": "references/mapa.md",
            "msg": "no encuentro el encabezado de conteos ('N referencias, N scripts, "
                   "N herramientas de ffmpeg y N suites'): este guard no comprueba nada "
                   "hasta que la frase vuelva"})
        return
    n_refs = _n_publicados("references", lambda p: p.endswith(".md"))
    scripts_dir = os.path.join(BASE, "scripts")
    fft_dir = os.path.join(scripts_dir, "ffmpeg_tools")
    tests_dir = os.path.join(scripts_dir, "_tests")
    # un arbol parcial (tests, copias de trabajo) no tiene todos los directorios:
    # el conteo solo se puede verificar sobre la skill completa
    if not (os.path.isdir(fft_dir) and os.path.isdir(tests_dir)):
        return
    n_scripts = _n_publicados("scripts", lambda p: p.endswith(".py")
                               and p.count("/") == 1)
    n_fft = _n_publicados("scripts/ffmpeg_tools", lambda p: p.endswith(".py"))
    # DOS cifras que no se pueden confonder:
    # - SUITES: los modulos que son de verdad una suite (test_*.py). es lo que
    #   dice el encabezado del mapa y lo que enumera el SKILL.md.
    # - ARCHIVOS: todo .py que vive en _tests/. es lo que dice el desglose del
    #   README ("N en _tests/") y lo que suma el total de scripts.
    # un modulo de apoyo (apoyo.py) NO es una suite: si se contara como tal,
    # el guard exigiria una suite que no existe y la herramienta —que escribe
    # el numero de suites— no podria satisfacerlo: el bucle "corre la
    # herramienta y vuelve a fallar" no tendria salida.
    n_suites = len(_suites_publicadas())
    n_archivos = _n_publicados("scripts/_tests", lambda p: p.endswith(".py")
                                and p != "__init__.py")
    for declarado, real, que in ((int(m.group(1)), n_refs, "referencias"),
                                 (int(m.group(2)), n_scripts, "scripts"),
                                 (int(m.group(3)), n_fft, "herramientas de ffmpeg"),
                                 (int(m.group(4)), n_suites, "suites de tests")):
        if declarado != real:
            problemas.append({"tipo": "conteo obsoleto", "archivo": "references/mapa.md",
                              "msg": f"dice {declarado} {que} y hay {real}"
                                     " -> corre `python scripts/actualizar_conteos.py` para reescribirlo"})
    _chequear_conteos_readme(problemas, n_refs, n_fft, n_archivos)


#: rutas de lectura que terminan en un entregable: tienen que acabar en la puerta
RUTAS_CON_ENTREGABLE = ("CREAR", "EDITAR", "clonar", "resumen",
                        "video grabado", "hecho con IA")


def _chequear_verticales(problemas):
    """Las CUATRO verticales de la skill tienen que estar de verdad.

    Las verticales estan declaradas como DATOS (scripts/data/verticales.json),
    no como prosa: en la prosa una lista se queda vieja en silencio (nadie
    dice "falta la del sonido"), y como dato el guard la recorre.

    Y cada vertical tiene que estar completa de verdad:
      · con su RUTA de lectura en el mapa (si no, el agente recibe "quiero
        poner voz en off" y el mapa no le dice donde mirar: es una isla);
      · acabando en la PUERTA (si no, entrega sin medir);
      · llegando a comandos que alguien EJECUTA de verdad, segun el censo
        (si no, es documentacion, no un camino de trabajo);
      · sin comandos que nadie copia ni justifica (el guard de comandos
        copiados lo mide por comando; aqui se ve por vertical).
    """
    import json
    ruta = os.path.join(BASE, "scripts", "data", "verticales.json")
    if not os.path.exists(ruta):
        problemas.append({"tipo": "verticales sin declarar",
                          "archivo": "scripts/data/verticales.json",
                          "msg": "no existe el ficheiro de verticales: la skill no puede "
                                 "comprobar que es una navaja suiza"})
        return
    try:
        with open(ruta, encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError) as _e:
        problemas.append({"tipo": "verticales ilegibles",
                          "archivo": "scripts/data/verticales.json",
                          "msg": f"no se pudieron leer las verticales: {_e}"})
        return
    verticales = doc.get("verticales") or []
    if not verticales:
        problemas.append({"tipo": "verticales vacias",
                          "archivo": "scripts/data/verticales.json",
                          "msg": "no hay verticales declaradas"})
        return

    # las rutas de lectura del mapa
    mapa_p = os.path.join(REFS, "mapa.md")
    rutas = {}
    if os.path.exists(mapa_p):
        with open(mapa_p, encoding="utf-8") as fh:
            mapa_txt = fh.read()
        sec = re.search(r"##\s*2\.\s*Rutas de lectura.*?(?=\n##\s|\Z)", mapa_txt, re.S)
        if sec:
            for bloque in re.split(r"\n(?=- \*\*)", sec.group(0)):
                m = re.match(r"- \*\*\"?(.+?)\"?\*\*", bloque.strip())
                if m:
                    rutas[m.group(1)] = bloque

    # los comandos MEDIDOS por el censo (alguien los ejecuta de verdad)
    medidos = set()
    mapa_clis = os.path.join(BASE, "scripts", "data", "cli_verificadas.json")
    if os.path.exists(mapa_clis):
        try:
            with open(mapa_clis, encoding="utf-8") as fh:
                medidos = set((json.load(fh) or {}).get("verificadas") or {})
        except (OSError, ValueError):
            medidos = set()

    # la clasificacion del guard de comandos copiados (copiado / con motivo)
    copiados, con_motivo = set(), set()
    try:
        import _comandos_copiables as _CC
        copiados = set(_CC.EJECUTABLES)
        for _prefijo, (_m, _exc) in _CC.FUERA.items():
            con_motivo.add(_prefijo)
    except Exception:                       # noqa: BLE001
        pass

    # los scripts de la skill
    scripts = set()
    for dp, _dn, fn in os.walk(os.path.join(BASE, "scripts")):
        if "__pycache__" in dp:
            continue
        for f in fn:
            if not f.endswith(".py"):
                continue
            rel = os.path.relpath(os.path.join(dp, f), BASE).replace("\\", "/")
            if rel.startswith("scripts/_tests/"):
                continue          # los tests no son CLIs: son quien las ejecuta
            scripts.add(rel)

    for v in verticales:
        nombre = v.get("nombre", "?")
        clave = v.get("ruta", "")
        bloque = rutas.get(clave)
        if bloque is None:
            problemas.append({"tipo": "vertical sin ruta", "archivo": "references/mapa.md",
                              "msg": f'la vertical "{nombre}" no tiene ruta de lectura en el '
                                     f'mapa (se busca "{clave}")'})
            continue
        if "qa-entrega" not in bloque:
            problemas.append({"tipo": "vertical sin puerta", "archivo": "references/mapa.md",
                              "msg": f'la ruta de la vertical "{nombre}" no acaba en qa-entrega.md'})
        # la ENTRADA: el SKILL.md es lo primero que lee el agente. Una
        # vertical con ruta en el mapa pero sin nombre en la entrada tampoco
        # se encuentra.
        entrada = v.get("entrada") or []
        if entrada:
            skill_p = os.path.join(BASE, "SKILL.md")
            if os.path.exists(skill_p):
                with open(skill_p, encoding="utf-8") as fh:
                    entrada_txt = fh.read().lower()
                faltan = [w for w in entrada if w.lower() not in entrada_txt]
                if faltan:
                    problemas.append({"tipo": "vertical sin entrada",
                                      "archivo": "SKILL.md",
                                      "msg": f'la vertical "{nombre}" no se nombra en la '
                                             f'entrada (faltan: {", ".join(faltan)}): el '
                                             f'agente lee el SKILL.md primero, y una '
                                             f'vertical que no aparece ahi no se encuentra'})
        claves = v.get("claves") or []
        de_vertical = [sc for sc in scripts
                       if any(k in os.path.basename(sc) for k in claves)]
        if not de_vertical:
            problemas.append({"tipo": "vertical sin herramientas", "archivo": "scripts/data/verticales.json",
                              "msg": f'la vertical "{nombre}" no llega a ningun script'})
            continue
        ejecutados = [sc for sc in de_vertical if sc in medidos]
        if not ejecutados:
            problemas.append({"tipo": "vertical sin herramientas verificadas",
                              "archivo": "scripts/data/verticales.json",
                              "msg": f'ningun script de la vertical "{nombre}" lo ejecuta un test '
                                     f'(el censo no los mide): es documentacion, no un camino de trabajo'})
        # lo que no ejecuta ningun test tiene que llevar su motivo AL LADO
        motivos = v.get("sin_test") or {}
        sin_verificar = [sc for sc in de_vertical
                         if sc not in medidos and sc not in motivos]
        for sc in sin_verificar:
            problemas.append({"tipo": "vertical con herramientas sin verificar",
                              "archivo": "scripts/data/verticales.json",
                              "msg": f'el script {sc} de la vertical "{nombre}" no lo ejecuta '
                                     f'ningun test y no tiene motivo declarado: es un puntero a nada'})
        # y un motivo que ya no aplica (el script se ha medido) es ruido
        for sc, motivo in motivos.items():
            if sc in medidos:
                problemas.append({"tipo": "motivo obsoleto en vertical",
                                  "archivo": "scripts/data/verticales.json",
                                  "msg": f'la vertical "{nombre}" declara un motivo para {sc}, pero '
                                         f'ya hay un test que lo ejecuta: el motivo sobra'})


def _chequear_puerta(problemas):
    """Todo camino que produce un entregable tiene que acabar en la puerta.

    Sin la puerta, el agente entrega sin medir: la tipografia ilegible, el
    spec de plataforma mal o un frame congelado tambien "salen". La puerta
    es lo que hace de esta skill una navaja suiza y no una caja de
    herramientas sueltas. Se verifica en los dos lugares donde un agente
    decide el camino: el indice (`mapa.md`) y los pasos del `SKILL.md`.
    """
    mapa = os.path.join(REFS, "mapa.md")
    if os.path.exists(mapa):
        with open(mapa, encoding="utf-8") as fh:
            texto = fh.read()
        # la seccion de rutas: desde el titulo hasta el siguiente titulo
        sec = re.search(r"##\s*2\.\s*Rutas de lectura.*?(?=\n##\s|\Z)", texto, re.S)
        if sec:
            cuerpo = sec.group(0)
            # cada ruta: "- **"nombre"** → ... "  (puede ocupar varias lineas)
            for bloque in re.split(r"\n(?=- \*\*)", cuerpo):
                m = re.match(r"- \*\*\"?(.+?)\"?\*\*", bloque.strip())
                if not m:
                    continue
                nombre = m.group(1)
                if not any(k in nombre for k in RUTAS_CON_ENTREGABLE):
                    continue
                if "qa-entrega" not in bloque:
                    problemas.append({
                        "tipo": "ruta sin puerta", "archivo": "references/mapa.md",
                        "msg": f'la ruta "{nombre}" produce un entregable y no acaba '
                               "en qa-entrega.md"})

    skill = os.path.join(BASE, "SKILL.md")
    if os.path.exists(skill):
        with open(skill, encoding="utf-8") as fh:
            texto = fh.read()
        paso6 = re.search(r"###\s*Step 6.*?(?=\n###\s|\Z)", texto, re.S)
        if paso6 and "qa_entrega" not in paso6.group(0):
            problemas.append({
                "tipo": "ruta sin puerta", "archivo": "SKILL.md",
                "msg": "el paso de edicion (Step 6) no nombra la puerta: la pieza "
                       "editada se entregaria sin medir"})


def _strings_impresos():
    """Los textos que los scripts pueden imprimir (solo los print, no los
    comentarios): lo que el agente ve de verdad en la terminal."""
    import ast
    out = []
    base = os.path.join(BASE, "scripts")
    for dp, dn, fn in os.walk(base):
        dn[:] = [d for d in dn if d != "__pycache__"]
        for f in fn:
            if not f.endswith(".py"):
                continue
            try:
                with open(os.path.join(dp, f), encoding="utf-8") as fh:
                    arbol = ast.parse(fh.read())
            except (OSError, SyntaxError, ValueError):
                continue
            for nodo in ast.walk(arbol):
                if not (isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Name)
                        and nodo.func.id == "print"):
                    continue
                for sub in ast.walk(nodo):
                    if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                        out.append(sub.value)
    return "\n".join(out).lower()


#: recetas del Motor Selector: son caminos de produccion, no notas
RECETAS = ("quick-kinetic", "quick-montage", "quick-cut", "quick-short")


def _arbol_completo():
    """True si esta copia tiene el motor entero.

    Los guards que comparan el codigo con la doc (promesas, catalogo de
    escenas) solo tienen sentido sobre la skill completa: en una copia
    parcial (un test, un arbol de trabajo) faltarian scripts y todo
    pareceria roto.
    """
    return os.path.isfile(os.path.join(BASE, "scripts", "render_plan.py"))


def _tipos_de_escena():
    """Los tipos de escena que el motor renderiza de verdad."""
    ruta = os.path.join(BASE, "scripts", "render_plan.py")
    if not os.path.exists(ruta):
        return set()
    with open(ruta, encoding="utf-8") as fh:
        texto = fh.read()
    return set(re.findall(r'"(\w+)":\s*sc_\w+', texto))


def _chequear_escenas(problemas):
    """Que el catalogo documentado sea el catalogo del motor, POR NOMBRE.

    El conteo no basta: si una escena se renombra o se anade, el numero
    puede seguir cuadrando mientras el nombre que el agente copia del
    documento ya no existe en el motor (`KeyError` al renderizar). Y al
    reves: una lista de "escenas futuras" que ya se implementaron manda al
    agente a un tipo que funciona, creyendo que no.
    """
    if not _arbol_completo():
        return
    tipos = _tipos_de_escena()
    if not tipos:
        return
    plan = os.path.join(REFS, "plan-video.md")
    if os.path.exists(plan):
        with open(plan, encoding="utf-8") as fh:
            texto = fh.read()
        sec = re.search(r"##\s*Tipos de escena.*?(?=\n##\s|\Z)", texto, re.S)
        if sec:
            bloque = sec.group(0)
            m = re.search(r"Tipos de escena\s*\((\d+)\)", bloque)
            if m and int(m.group(1)) != len(tipos):
                problemas.append({
                    "tipo": "catalogo divergente", "archivo": "references/plan-video.md",
                    "msg": f"dice {m.group(1)} tipos y el motor tiene {len(tipos)}"})
            faltan = sorted(t for t in tipos if not re.search(rf"`{re.escape(t)}`", bloque))
            if faltan:
                problemas.append({
                    "tipo": "escena sin documentar", "archivo": "references/plan-video.md",
                    "msg": f"el motor las tiene y la lista no: {', '.join(faltan)}"})
    cat = os.path.join(REFS, "escenas.md")
    if os.path.exists(cat):
        with open(cat, encoding="utf-8") as fh:
            texto = fh.read()
        faltan = sorted(t for t in tipos if not re.search(rf"`{re.escape(t)}`", texto))
        if faltan:
            problemas.append({
                "tipo": "escena sin documentar", "archivo": "references/escenas.md",
                "msg": f"el motor las tiene y el catalogo no: {', '.join(faltan)}"})
        # las "ideas futuras" no pueden ser tipos que ya existen. La lista es
        # la corrida de nombres unidos por " · " (las primitivas van con
        # comas). Se descartan antes los parrafos que no son la lista: la nota
        # "Ya implementadas" tambien une nombres con " · ".
        sec = re.search(r"##\s*Ideas de escenas futuras.*?(?=\n##\s|\Z)", texto, re.S)
        if sec:
            futuras = set()
            for par in re.split(r"\n\s*\n", sec.group(0)):
                if "Ya implementadas" in par or "primitivas DRY" in par:
                    continue
                plano = re.sub(r"\s*\n\s*", " ", par)
                for m in re.finditer(r"(?:`\w+`)(?:\s*·\s*`\w+`)+", plano):
                    futuras |= set(re.findall(r"`(\w+)`", m.group(0)))
            implementadas = sorted(t for t in tipos if t in futuras)
            if implementadas:
                problemas.append({
                    "tipo": "escena futura ya existe", "archivo": "references/escenas.md",
                    "msg": f"listadas como NO implementadas pero el motor las tiene: "
                           f"{', '.join(implementadas)}"})


def _chequear_recetas(problemas):
    """Toda receta tiene que traer un comando: sin comando es una descripcion.

    El Motor Selector enruta a estas recetas ("tarjeta cinetica", "montaje de
    clips", "recorte de un video"). Si la receta no dice que correr, el agente
    no tiene nada que ejecutar: se queda escribiendo codigo a mano o
    devolviendo una descripcion en vez de una pieza.
    """
    ruta = os.path.join(REFS, "modos-rapidos.md")
    if not os.path.exists(ruta):
        return
    with open(ruta, encoding="utf-8") as fh:
        texto = fh.read()
    secciones = re.split(r"\n## ", texto)
    for sec in secciones[1:]:
        nombre = sec.split("\n")[0].strip()
        clave = nombre.split()[0] if nombre.split() else ""
        if clave not in RECETAS:
            continue
        tiene = re.search(r"scripts/[A-Za-z0-9_./-]+\.py|\bpython3?\s+\S|\bffmpeg\s+\S", sec)
        if not tiene:
            problemas.append({
                "tipo": "receta sin comando", "archivo": "references/modos-rapidos.md",
                "msg": f"'{nombre}' no dice que correr: el Motor Selector enruta ahi"})


def _chequear_promesas(problemas):
    """Que lo que el SKILL.md promete que se ve, exista en el codigo.

    `Expected output: PLAN VALIDO` es un contrato: el agente busca esa
    palabra para saber que el plan esta listo y puede pasar al paso
    siguiente. Si el script imprime otra cosa ("OK plan limpio"), la
    promesa es falsa: el agente no sabe cuando seguir, o peor, cree que
    algo fallo.

    Se miran SOLO los textos que los scripts imprimen (via `ast`), no todo
    el codigo: una palabra en un comentario no es una promesa cumplida.
    De cada token se comparan sus palabras, porque una salida formateada
    ("COPY: 0 fallos") se compone en tiempo de ejecucion.
    """
    skill = os.path.join(BASE, "SKILL.md")
    if not os.path.exists(skill):
        return
    with open(skill, encoding="utf-8") as fh:
        texto = fh.read()
    if not _arbol_completo():
        return
    impreso = _strings_impresos()
    if not impreso:
        return
    vistas = set()
    for linea in re.findall(r"Expected output:[^\n]*", texto):
        for tok in re.findall(r"`([^`]+)`", linea):
            # un token de salida: empieza en mayuscula y son palabras
            if not re.fullmatch(r"[A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ0-9 :_·-]{2,45}", tok):
                continue
            if (tok, linea[:50]) in vistas:
                continue
            vistas.add((tok, linea[:50]))
            faltan = [w for w in re.findall(r"[A-Za-zÁÉÍÓÚÑáéíóúñ]{3,}", tok)
                      if w.lower() not in impreso]
            if faltan:
                problemas.append({
                    "tipo": "promesa inexistente", "archivo": "SKILL.md",
                    "msg": f"'{tok}': ningun script imprime {', '.join(faltan)}"})


def _chequear_conteos_readme(problemas, n_refs, n_fft, n_archivos_tests):
    """Que las cifras no envejezcan: READMEs, SKILL.md y referencias.

    Los README del repo son la puerta de entrada del proyecto: si dicen "45
    referencias" cuando hay 53, el que los lee (o el agente que los usa como
    mapa) cuenta con una realidad que no existe. `mapa.md` ya tiene guarda
    para su encabezado; los README no tenian ninguna.

    Y lo mismo dentro de la skill: el SKILL.md decia "36 escenas" cuando el
    catalogo ya tenia 39, y nadie lo noto porque el chequeo vivia fuera del
    arbol de la skill (en la copia instalada no encuentra los README y se
    salta entero). Ahora el conteo se mira tambien DENTRO, que es donde el
    agente lee.
    """
    raiz = os.path.dirname(BASE)          # el README vive un nivel arriba
    scripts_dir = os.path.join(BASE, "scripts")
    # un arbol parcial (tests, copias de trabajo) no tiene el motor ni los
    # README: el conteo de primitivas y escenas solo se puede verificar sobre
    # la skill completa
    if not (os.path.isdir(scripts_dir)
            and os.path.isfile(os.path.join(scripts_dir, "render_plan.py"))):
        return
    n_prim = _n_primitivas_dry(scripts_dir)
    n_escenas = _n_escenas(scripts_dir)
    n_root = len([f for f in os.listdir(scripts_dir)
                  if f.endswith(".py") and os.path.isfile(os.path.join(scripts_dir, f))])
    patrones = (
        # "N primitivas DRY" solo se vigila en los README: en las referencias
        # es una cifra historica ("la ronda 4 aporto 3 primitivas DRY")
        (r"(\d+)\s+referencias\s+en\s+kebab-case", n_refs, "referencias"),
        (r"(\d+)\s+references\s+in\s+kebab-case", n_refs, "referencias"),
        # el tamaño del CATALOGO, no un ejemplo de plan ("plan demo de 6
        # escenas" ni "las 13 escenas originales"): solo las formas que SI
        # son una afirmacion del tamaño del catalogo
        (r"(\d+)\s+escenas\s+compuestas", n_escenas, "escenas del catalogo"),
        (r"(\d+)\s+scenes\s+composed", n_escenas, "escenas del catalogo"),
        (r"\((\d+)\s+escenas\)", n_escenas, "escenas del catalogo"),
        (r"\((\d+)\s+scenes\)", n_escenas, "escenas del catalogo"),
        (r"catálogo\s+de\s+(\d+)\s+escenas", n_escenas, "escenas del catalogo"),
        (r"[Cc]atalog of\s+(\d+)\s+scenes", n_escenas, "escenas del catalogo"),
        (r"componen\s+las\s+(\d+)\s+escenas", n_escenas, "escenas del catalogo"),
        (r"compose\s+all\s+(\d+)\s+scenes", n_escenas, "escenas del catalogo"),
        (r"Suite visual de las\s+(\d+)\s+escenas", n_escenas, "escenas del catalogo"),
        (r"Visual suite for all\s+(\d+)\s+scenes", n_escenas, "escenas del catalogo"),
        (r"Muestras canónicas de las\s+(\d+)\s+escenas", n_escenas, "escenas del catalogo"),
        (r"Canonical samples for all\s+(\d+)\s+scenes", n_escenas, "escenas del catalogo"),
        (r"(\d+)\s+scene\s+types", n_escenas, "escenas del catalogo"),
        # "13 tipos de escena" en arquitectura.md es historico (el sistema
        # original tenia 13): el patron del total es "con N tipos" / "con N tipos
        # de escena" en el README
        (r"con\s+(\d+)\s+tipos\s+de\s+escena", n_escenas, "escenas del catalogo"),
        (r"con\s+(\d+)\s+tipos\s+—", n_escenas, "escenas del catalogo"),
        (r"with\s+(\d+)\s+types\s+—", n_escenas, "escenas del catalogo"),
        (r"with\s+(\d+)\s+scene\s+types", n_escenas, "escenas del catalogo"),
        (r"(\d+)/(\d+)\s+scenes\s+render", n_escenas, "escenas del catalogo"),
        (r"(\d+)\s+m[óo]dulos\s+de\s+post-producci[óo]n", n_fft, "modulos de post-produccion"),
        # los scripts raiz, contados de tres formas distintas: el desglose
        # en ingles, el desglose en espanol y la forma corta del encabezado
        # del mapa. Antes solo se cubria la primera: un README en espanol
        # ("37 motores raiz + ... = 79 scripts") podia envejecer en silencio
        (r"(\d+)\s+motores\s+ra[ií]z", n_root, "scripts root"),
        (r"(\d+)\s+scripts,\s*\d+\s+herramientas\s+de\s+ffmpeg", n_root, "scripts root"),
        (r"(\d+)\s+scripts,\s*\d+\s+ffmpeg\s+tools", n_root, "scripts root"),
    )
    # donde mirar: los README (si existen) y TODO lo de dentro de la skill
    archivos = []
    for nombre in ("README.md", "README.en.md"):
        ruta = os.path.join(raiz, nombre)
        if os.path.exists(ruta):
            archivos.append((nombre, ruta))
    archivos.append(("SKILL.md", os.path.join(BASE, "SKILL.md")))
    for f in sorted(os.listdir(REFS)):
        if f.endswith(".md"):
            archivos.append((f"references/{f}", os.path.join(REFS, f)))
    for etiqueta, ruta in archivos:
        if not os.path.exists(ruta):
            continue
        with open(ruta, encoding="utf-8") as fh:
            texto = _prosa(fh.read())
        _pat = patrones
        if etiqueta.startswith("README") or etiqueta == "SKILL.md":
            # el total de primitivas solo se afirma en la puerta de entrada
            _pat = _pat + (
                (r"(\d+)\s+primitivas\s+DRY", n_prim, "primitivas DRY"),
                (r"(\d+)\s+DRY\s+primitives", n_prim, "primitivas DRY"),
            )
        if etiqueta.startswith("README") or etiqueta == "SKILL.md" \
                or etiqueta.endswith("mapa.md"):
            # en la puerta de entrada, "N references" es SIEMPRE el total: no
            # hay cifras historicas ahi. Y hace falta porque el SKILL.md esta
            # en ingles: los patrones de arriba solo buscan la forma "en
            # kebab-case", asi que un "53 references" se escapaba del guard
            # entero y el numero se agingaba sin que nadie lo viera.
            _pat = _pat + (
                (r"(\d+)\s+references\b", n_refs, "referencias"),
                (r"(\d+)\s+referencias\b", n_refs, "referencias"),
            )
        for patron, real, que in _pat:
            for mt in re.finditer(patron, texto):
                grupos = [g for g in mt.groups() if g]
                if not grupos:
                    continue
                for g in grupos:
                    if int(g) != real:
                        problemas.append({
                            "tipo": "conteo obsoleto", "archivo": etiqueta,
                            "msg": f"dice {que} {g} y hay {real}"})
                        break
        # el desglose de scripts: "N root + N in ffmpeg_tools/ + N in _tests/ = N scripts"
        # y su forma en espanol ("N motores raiz + N en ffmpeg_tools/ + N en _tests/")
        for mt in re.finditer(r"(\d+)\s+(?:root|motores\s+ra[ií]z)\s*\+\s*(\d+)\s+"
                              r"(?:in\s+|en\s+)ffmpeg_tools/?\s*\+\s*"
                              r"(\d+)\s+(?:in\s+|en\s+)_tests/?\s*=\s*(\d+)\s+scripts", texto):
            r_, f_, t_, s_ = (int(x) for x in mt.groups())
            n_root = _n_publicados("scripts", lambda p: p.endswith(".py")
                                   and p.count("/") == 1)

            for declarado, real, que in ((r_, n_root, "scripts root"), (f_, n_fft, "ffmpeg_tools"),
                                         (t_, n_archivos_tests, "archivos en _tests/"),
                                         (s_, n_root + n_fft + n_archivos_tests, "scripts en total")):
                if declarado != real:
                    problemas.append({"tipo": "conteo obsoleto", "archivo": etiqueta,
                                      "msg": f"dice {declarado} {que} y hay {real}"
                                             " -> corre `python scripts/actualizar_conteos.py` para reescribirlo"})


def _n_primitivas_dry(scripts_dir):
    """Cuantas primitivas DRY declara el motor (las que el README cuenta)."""
    import ast
    arbol = ast.parse(_contenido_publicado("scripts/render_plan.py"))
    nombres = {n.name for n in arbol.body if isinstance(n, ast.FunctionDef)}
    conocidas = {"barra_h", "cuenta_up", "arco", "particulas", "cuadricula", "linewrap",
                 "tarjeta_cristal", "boton_halo", "insignia_3d", "tarjeta", "texto_que_cabe",
                 "fuente_que_cabe", "grupo", "fundir", "check", "onda_clic", "flota", "entra",
                 "elipse_se_dibuja", "placa_texto"}
    return len(conocidas & nombres)


def _n_escenas(scripts_dir):
    """Cuantas escenas declara el motor (SCENES)."""
    import ast
    arbol = ast.parse(_contenido_publicado("scripts/render_plan.py"))
    for n in arbol.body:
        if isinstance(n, ast.Assign) and any(getattr(x, "id", "") == "SCENES" for x in n.targets):
            return len(n.value.keys)
    return 0


def _rels_de_texto(txt, base_rel=""):
    """Rutas citadas en un texto, normalizadas respecto a la raiz de la skill."""
    out = set()
    prefijos = ("references/", "scripts/", "film/", "metricas/", "assets/", "brand/")
    for m in REF.finditer(txt):
        p = m.group(0).rstrip(".,;:)`")
        if base_rel.startswith("brand/"):
            # dentro de un pack: primero relativa al pack (como ruta_de_pack del
            # motor) y, si no existe ahi, relativa a la raiz de la skill
            cand = os.path.normpath(os.path.join(os.path.dirname(base_rel), p))
            p = cand if os.path.exists(os.path.join(BASE, cand)) else p
        elif not p.startswith(prefijos):
            p = os.path.normpath(os.path.join(os.path.dirname(base_rel), p))
        out.add(p)
    return out


def _normalizar(txt):
    """El nombre de un eje sin acentos, sin mayusculas y sin puntuacion."""
    import unicodedata
    t = unicodedata.normalize("NFKD", txt)
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "", t.lower())


def _ejes_de_rubrica(scripts_dir):
    """[(numero, nombre, ambito)] de la rubrica, leidos del codigo."""
    import ast
    ruta = os.path.join(scripts_dir, "puntuar.py")
    if not os.path.exists(ruta):
        return []
    with open(ruta, encoding="utf-8") as fh:
        arbol = ast.parse(fh.read())
    for n in arbol.body:
        if isinstance(n, ast.Assign) and any(getattr(x, "id", "") == "EJES" for x in n.targets):
            salida = []
            for el in n.value.elts:
                if not isinstance(el, ast.Tuple) or len(el.elts) < 3:
                    continue
                try:
                    num = int(ast.literal_eval(el.elts[0]))
                    nombre = ast.literal_eval(el.elts[1])
                    ambito = ast.literal_eval(el.elts[2])
                except (ValueError, SyntaxError):
                    continue
                salida.append((num, nombre, ambito))
            return salida
    return []


def _pasos_de_la_puerta(scripts_dir):
    """(pasos siempre, pasos solo con plan) de `qa_entrega.py`, del codigo.

    Se cuenta el AST, no el docstring: el docstring dice "cinco" y el
    codigo hace otra cosa (que es justo lo que hay que detectar).
    """
    import ast
    ruta = os.path.join(scripts_dir, "qa_entrega.py")
    txt = _contenido_publicado("scripts/qa_entrega.py")
    if not txt:
        return None
    arbol = ast.parse(txt)
    main_fn = next((n for n in arbol.body
                    if isinstance(n, ast.FunctionDef) and n.name == "main"), None)
    if main_fn is None:
        return None
    siempre = con_plan = 0

    def cuenta(bloque, en_plan):
        nonlocal siempre, con_plan
        for st in bloque:
            if isinstance(st, ast.If):
                test = ast.dump(st.test)
                es_plan = "plan" in test
                # un `if not args.sin_medir` no añade pasos: solo los salta
                if "sin_medir" in test:
                    cuenta(st.body, en_plan)
                    continue
                cuenta(st.body, en_plan or es_plan)
                continue
            if isinstance(st, ast.Expr) and isinstance(st.value, ast.Call):
                func = st.value.func
                nombre = getattr(func, "attr", "")
                if nombre == "append" and isinstance(st.value.func, ast.Attribute):
                    src = ast.dump(st.value.func.value)
                    if "pasos" in src:
                        if en_plan:
                            con_plan += 1
                        else:
                            siempre += 1
    cuenta(main_fn.body, False)
    return siempre, con_plan


def _chequear_cifras_del_codigo(problemas):
    """Que las cifras que la prosa enuncia sean las que el codigo tiene.

    Dos numeros de la skill viven en el codigo y se enuncian en la prosa:
    los ejes de la rubrica (`puntuar.py`) y los pasos de la puerta
    (`qa_entrega.py`). Un documento que dice "cinco comprobaciones"
    cuando la puerta corre seis (o tres, sin plan) no es un error de
    redaccion: es una afirmacion que el sistema no cumple.
    """
    scripts_dir = os.path.join(BASE, "scripts")
    if not os.path.isdir(scripts_dir):
        return

    # ---- los ejes de la rubrica -------------------------------------
    ejes = _ejes_de_rubrica(scripts_dir)
    if ejes:
        doc = os.path.join(REFS, "rubrica-premios.md")
        if os.path.exists(doc):
            texto = open(doc, encoding="utf-8").read()
            filas = {}
            for mt in re.finditer(r"^\|\s*(\d)\s*\|\s*\*\*(.+?)\*\*\s*\|", texto, re.M):
                filas[int(mt.group(1))] = mt.group(2)
            if filas:
                codigo = {n for n, _, _ in ejes}
                documento = set(filas)
                if codigo != documento:
                    faltan = sorted(codigo - documento)
                    sobran = sorted(documento - codigo)
                    problemas.append({
                        "tipo": "rubrica descuadrada", "archivo": "references/rubrica-premios.md",
                        "msg": f"el codigo tiene los ejes {sorted(codigo)} y el documento {sorted(documento)}"
                               + (f" (faltan {faltan})" if faltan else "")
                               + (f" (sobran {sobran})" if sobran else "")})
                for n, nombre, _ in ejes:
                    if n in filas and _normalizar(nombre) != _normalizar(filas[n]):
                        problemas.append({
                            "tipo": "rubrica descuadrada", "archivo": "references/rubrica-premios.md",
                            "msg": f"el eje {n} se llama '{nombre}' en el codigo y '{filas[n]}' en el documento"})

    # ---- los pasos de la puerta --------------------------------------
    pasos = _pasos_de_la_puerta(scripts_dir)
    if pasos:
        siempre, solo_con_plan = pasos
        total_plan = siempre + solo_con_plan
        # DONDE se enuncia el numero: la ficha del mapa y el doc de la puerta.
        # antes solo se miraba qa-entrega.md, donde la prosa dice "todas las
        # comprobaciones" (que el patron se salta): el numero vivia en
        # mapa.md y el guard no lo miraba nunca. Un guard que no mira donde
        # esta el numero es un guard que no mira.
        for etiqueta, doc in (("references/mapa.md", os.path.join(REFS, "mapa.md")),
                              ("references/qa-entrega.md", os.path.join(REFS, "qa-entrega.md"))):
            if not os.path.exists(doc):
                continue
            texto = _prosa(open(doc, encoding="utf-8").read())
            for mt in re.finditer(r"\b([a-zA-ZáéíóúñÁÉÍÓÚÑ]+|\d+)\s+comprobaciones\b", texto):
                palabra = mt.group(1).lower()
                if palabra in NUMEROS_EN_PALABRAS:
                    n = NUMEROS_EN_PALABRAS[palabra]
                elif palabra.isdigit():
                    n = int(palabra)
                else:
                    continue    # "todas las comprobaciones": no es una cifra
                if n == total_plan:
                    continue
                if siempre != total_plan:
                    msg = (f"afirma '{mt.group(1)} comprobaciones', pero la puerta corre "
                           f"{siempre} sin plan y {total_plan} con plan: un numero fijo en "
                           f"la prosa es un numero falso")
                else:
                    msg = f"afirma '{mt.group(1)} comprobaciones' y la puerta corre {siempre}"
                problemas.append({"tipo": "cifra falsa", "archivo": etiqueta, "msg": msg})


def _suites_publicadas():
    """Las suites de test que hay en el ARBOL.

    La usa el guard (para comparar con la lista del SKILL.md) y la
    herramienta que reescribe esa lista: si cuentas distinto, los dos
    pueden discrepar.
    """
    return {os.path.basename(p) for p in _paths_publicados("scripts/_tests")
            if os.path.basename(p).startswith("test_")
            and os.path.basename(p).endswith(".py")}


#: El CANONICO de las suites: la lista que el guard compara con el arbol.
#:
#: La lista vivia en el `SKILL.md`, y ahi era dos cosas a la vez: prosa que el
#: agente se leia en cada peticion (46 rutas de test que no usa) y una bomba
#: de relojería para el limite de 5000 palabras (cada suite nueva sumaba una
#: y la puerta caia por una palabra). Ahora es dato de la herramienta, con
#: `verticales.json` y `cli_verificadas.json`. Lo que no cambia es el guard:
#: la lista sigue siendo una copia de la verdad y sigue habiendo alguien que
#: la compare con el arbol.
RUTA_SUITES = os.path.join("scripts", "data", "suites.json")


def _suites_declaradas():
    """Las suites que declara el canonico (set), o None si no se ha podido leer.

    None NO es "no hay suites": es "no se ha podido mirar". Un guard que no
    dice que no mira, no dice nada.
    """
    ruta = os.path.join(BASE, RUTA_SUITES)
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


def _canonico_en(raiz, commit, rel_skill):
    """El canonico de suites existia en ese commit?"""
    try:
        rr = subprocess.run(["git", "-C", raiz, "cat-file", "-e",
                             f"{commit}:{rel_skill}/scripts/data/suites.json"],
                            capture_output=True, text=True, timeout=20)
        return rr.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _chequear_lista_de_suites(problemas):
    """Que la lista de suites del canonico sea el conjunto real.

    El SKILL.md enumera las suites que tienen que pasar: si esa lista no es
    el conjunto real, la promesa envejece en silencio. Y al reves, una suite
    listada que ya no existe hace fallar la validacion por un archivo que no
    esta.

    La lista vive en `scripts/data/suites.json` (la escribe
    `scripts/actualizar_conteos.py`). El SKILL.md solo dice cuantas hay.
    """
    tests_dir = os.path.join(BASE, "scripts", "_tests")
    if not os.path.isdir(tests_dir):
        return
    listadas = _suites_declaradas()
    if listadas is None:
        # sin canonico no hay lista que comparar. NO es un fallo por si solo:
        # el canonico es NUEVO, y mientras no este publicado (o mientras se
        # mira una copia que no lo tiene) la proteccion simplemente no se
        # puede aplicar. Lo que si es un fallo es que el canonico
        # DESAPAREZCA: eso lo caza el check del commit, que compara HEAD~1
        # con HEAD. Aqui solo se avisa de que no se ha podido mirar.
        return
    reales = _suites_publicadas()
    for f in sorted(reales - listadas):
        problemas.append({
            "tipo": "suite sin enlistar", "archivo": RUTA_SUITES,
            "msg": f"existe scripts/_tests/{f} y el canonico no la lista: "
                   f"la lista de suites tiene que ser el conjunto real"})
    for f in sorted(listadas - reales):
        problemas.append({
            "tipo": "suite listada que no existe", "archivo": RUTA_SUITES,
            "msg": f"el canonico lista scripts/_tests/{f} y ese archivo no existe"})


# los scripts que leen el PLAN DE VIDEO. `shorts_plan.py` y `chapters.py`
# leen OTRO plan (el de un shorts y el de un capitulado): sus claves no son
# del plan de video y no se comparan.
_SCRIPTS_DEL_PLAN = ["render_plan.py", "auditar_plan.py", "medir_animacion.py",
                     "mezclar_audio.py", "voz_off.py", "lint_copy.py", "_copy.py"]


def _chequear_claves_del_plan(problemas):
    """Que toda clave del plan que el motor lee este en algun documento.

    El plan es el contrato entre el que escribe y el que dibuja. El motor
    lee claves del nivel raiz; cada una tiene que estar explicada en
    algun sitio, o el agente que escribe el plan no la conoce, la pieza
    sale con el default, y nadie sabe por que.
    """
    refs = os.path.join(BASE, "references")
    if not os.path.isdir(refs):
        return
    docs = [os.path.join(BASE, "SKILL.md")]
    docs += [os.path.join(refs, f) for f in sorted(os.listdir(refs)) if f.endswith(".md")]
    texto = "\n".join(open(d, encoding="utf-8").read() for d in docs if os.path.exists(d))
    if not texto.strip():
        return
    leidas = {}
    for f in _SCRIPTS_DEL_PLAN:
        t = _contenido_publicado(os.path.join("scripts", f))
        if not t:
            continue
        for pat in (r'\bplan\[\s*["\']([a-zA-Z_]+)["\']',
                    r'\bplan\.get\(\s*["\']([a-zA-Z_]+)["\']',
                    r'\bplan\.setdefault\(\s*["\']([a-zA-Z_]+)["\']'):
            for k in re.findall(pat, t):
                leidas.setdefault(k, set()).add(f)
    for k in sorted(leidas):
        if re.search(r'["`]%s["`]' % re.escape(k), texto) or \
           re.search(r'\b%s\b' % re.escape(k), texto):
            continue
        problemas.append({
            "tipo": "clave del plan sin documentar", "archivo": "references/plan-video.md",
            "msg": f"el motor lee plan['{k}'] ({', '.join(sorted(leidas[k]))}) "
                   f"y ningun documento la menciona"})


def _n_subcomandos(ruta):
    """Cuantos subcomandos declara una CLI (los `add_parser` de argparse)."""
    import ast
    txt = _contenido_publicado("scripts/ffmpeg_tools/montaje.py")
    if not txt:
        return None
    arbol = ast.parse(txt)
    subs = set()
    for n in ast.walk(arbol):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) \
                and n.func.attr == "add_parser":
            if n.args and isinstance(n.args[0], ast.Constant) \
                    and isinstance(n.args[0].value, str):
                subs.add(n.args[0].value)
    return len(subs)


def _chequear_cifras_de_cli(problemas):
    """Que el numero de operaciones que dice la prosa sea el de la CLI.

    El SKILL.md dice "montaje.py (19 operations)" y montaje.md dice "19
    operaciones de cirugia de clips": el codigo tiene 19 subcomandos. Si
    anaden uno, los dos numeros envejecen en silencio.
    """
    ruta = os.path.join(BASE, "scripts", "ffmpeg_tools", "montaje.py")
    n = _n_subcomandos(ruta)
    if not n:
        return
    for etiqueta, ruta_doc, patron in (
        ("SKILL.md", os.path.join(BASE, "SKILL.md"), r"(\d+)\s+operations\b"),
        ("references/montaje.md", os.path.join(REFS, "montaje.md"), r"(\d+)\s+operaciones\b"),
    ):
        if not os.path.exists(ruta_doc):
            continue
        with open(ruta_doc, encoding="utf-8") as fh:
            texto = _prosa(fh.read())
        for mt in re.finditer(patron, texto):
            g = mt.group(1)
            if int(g) != n:
                problemas.append({
                    "tipo": "conteo obsoleto", "archivo": etiqueta,
                    "msg": f"dice {g} operaciones de montage.py y la CLI tiene {n}"})


#: un texto con color FIJO (literal) y una caja de acento (variable): el
#: texto se pinta sobre un fondo que el usuario elige, y el color no lo
#: sigue. con blanco fijo, el hook de un short quedaba a 2:1 en menta.
COLOR_DE_TEXTO_FIJO = re.compile(r"fontcolor=(#[0-9A-Fa-f]{6}|white|black)\b")
#: la caja de acento se reconoce por el NOMBRE de su color, no por su forma:
#: la regla es "el color de la caja menciona el acento". un patron que exijera
#: frontera de palabra despues de "acento" (acento2, acento_2) se escapaba
#: por un detalle de la forma del nombre, no por la regla.
CAJA_DE_COLOR = re.compile(r"boxcolor=\{?[A-Za-z_][A-Za-z0-9_.]*")


def _chequear_tests_que_no_se_ejecutan(problemas):
    """Que todo metodo que se llama test_ se ejecute de verdad.

    unittest solo recoge los metodos `test_*` de una clase que herede de
    TestCase, en el NIVEL SUPERIOR del modulo. Un metodo de test metido
    dentro de una funcion es codigo muerto: no corre, no falla, y no cambia
    ninguna cifra publicada (el numero de suites no cambia), asi que nadie
    se entera nunca.

    Se mira el AST y NO se importan los modulos: importar 30 suites de test
    arrastra numpy, PIL y el motor, y un guard tiene que ser barato y sin
    efectos.
    """
    import ast
    d = os.path.join(BASE, "scripts", "_tests")
    if not os.path.isdir(d):
        return

    def _hijos(nodo, padre):
        for hijo in ast.iter_child_nodes(nodo):
            yield hijo, nodo
            yield from _hijos(hijo, nodo)

    for f in sorted(os.listdir(d)):
        if not (f.startswith("test_") and f.endswith(".py")):
            continue
        ruta = os.path.join(d, f)
        try:
            with open(ruta, encoding="utf-8") as fh:
                arbol = ast.parse(fh.read())
        except (OSError, SyntaxError, ValueError) as e:
            # un fichero de test que no se puede leer no es un test que no
            # corre: es un test ROTO. saltarselo en silencio deja el hueco
            # sin vigilar (y el guard pareceria que todo esta bien)
            problemas.append({
                "tipo": "test que no se ejecuta",
                "archivo": f"scripts/_tests/{f}",
                "msg": f"el fichero no se puede leer ({type(e).__name__}): "
                       f"un test roto no vigila nada"})
            continue
        # que clases heredan (directa o indirectamente) de TestCase, y cuales
        # NO se pueden resolver SIN IMPORTAR (una base definida en otro
        # modulo: no se acusa, porque no se puede saber, y un detector que
        # llora se desactiva)
        definidos_en_modulo = {c.name for c in arbol.body
                               if isinstance(c, ast.ClassDef)}
        clases_test = set()
        clases_desconocidas = set()
        for _ in range(len(arbol.body) + 1):
            for c in arbol.body:
                if not isinstance(c, ast.ClassDef) or c.name in clases_test:
                    continue
                if c.name in clases_desconocidas:
                    continue
                base_fuera = False
                for b in c.bases:
                    nb = ast.unparse(b)
                    if "TestCase" in nb or nb in clases_test:
                        clases_test.add(c.name)
                        break
                    if nb not in definidos_en_modulo:
                        base_fuera = True
                else:
                    if base_fuera:
                        clases_desconocidas.add(c.name)
        # los metodos que unittest recoge: en una clase de primer nivel
        ids_recogidos = set()
        for c in arbol.body:
            if isinstance(c, ast.ClassDef) and c.name in clases_test:
                for m in c.body:
                    if isinstance(m, ast.FunctionDef) and m.name.startswith("test"):
                        ids_recogidos.add(id(m))
        # un metodo REPETIDO en la misma clase: Python conserva el ultimo y
        # el primero es codigo muerto. no se ve: el nombre sigue ahi, con el
        # mismo aspecto, y el segundo parece el unico.
        for c in arbol.body:
            if not isinstance(c, ast.ClassDef):
                continue
            visto = {}
            for m in c.body:
                if not (isinstance(m, ast.FunctionDef) and m.name.startswith("test")):
                    continue
                if m.name in visto:
                    problemas.append({
                        "tipo": "test que no se ejecuta",
                        "archivo": f"scripts/_tests/{f}",
                        "msg": f"'{m.name}' esta definido dos veces en la clase "
                               f"'{c.name}' (lineas {visto[m.name]} y {m.lineno}): Python "
                               f"conserva el ultimo y el primero no se ejecuta"})
                visto[m.name] = m.lineno
        for nodo, padre in _hijos(arbol, None):
            if not (isinstance(nodo, ast.FunctionDef) and nodo.name.startswith("test")):
                continue
            if id(nodo) in ids_recogidos:
                continue
            if isinstance(padre, ast.FunctionDef):
                caso = "esta dentro de una funcion: unittest no la recoge"
            elif isinstance(padre, ast.ClassDef):
                if padre.name in clases_desconocidas:
                    # su base esta en otro modulo: no se puede saber sin
                    # importarla, y acusar a ciegas es peor que callar
                    continue
                caso = (f"la clase '{padre.name}' no hereda de TestCase: "
                        f"unittest no la recoge")
            else:
                caso = "no esta en una clase de TestCase: unittest no la recoge"
            problemas.append({
                "tipo": "test que no se ejecuta",
                "archivo": f"scripts/_tests/{f}",
                "msg": f"'{nodo.name}' {caso}. Un test que no corre es codigo muerto."})


def _chequear_convenciones_escritas(problemas):
    """Que las convenciones que el codigo pide esten ESCRITAS en las referencias.

    El codigo le dice al usuario que use una convencion ("marca que es voz de
    marca", "el sufijo [sesion-XXXX]"). Si esa convencion no esta escrita en
    ningun doc, el aviso es un puntero a la nada: el que lo recibe no puede
    saber que escribir. Se ha pasado dos veces.
    """
    for convencion, doc in CONVENCIONES_QUE_EXIGEN_DOC:
        ruta = os.path.join(BASE, doc)
        if not os.path.exists(ruta):
            problemas.append({
                "tipo": "convencion sin escribir", "archivo": doc,
                "msg": f"el codigo pide la convencion '{convencion}' y no hay donde "
                       f"escribirla: el aviso seria un puntero a la nada"})
            continue
        with open(ruta, encoding="utf-8") as fh:
            texto = fh.read()
        if convencion.lower() not in texto.lower():
            problemas.append({
                "tipo": "convencion sin escribir", "archivo": doc,
                "msg": f"el codigo pide la convencion '{convencion}' y {doc} no la "
                       f"explica: quien lea el aviso no puede saber que escribir"})


def _chequear_texto_fijo_sobre_acento(problemas):
    """Que ningun texto con color fijo se pinte sobre una caja de acento.

    El hook de un short pone el titular sobre un box del ACENTO de la marca,
    y el acento lo elige el usuario. Con el color de texto fijo, el titular
    quedaba a 2:1 en menta (ilegible) y por debajo del piso en las 8
    paletas del catalogo. El color tiene que seguir al fondo: `texto_sobre`
    (scripts/ffmpeg_tools/_comun.py) elige el claro o el oscuro.

    Se mira el AST, no el texto crudo: un filtro de ffmpeg se arma con
    varias cadenas pegadas y el color y la caja caen en literales distintos.
    """
    import ast
    for sub in ("scripts", "scripts/ffmpeg_tools"):
        d = os.path.join(BASE, sub)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if not f.endswith(".py") or f.startswith("_"):
                continue
            ruta = os.path.join(d, f)
            try:
                with open(ruta, encoding="utf-8") as fh:
                    arbol = ast.parse(fh.read())
            except (OSError, SyntaxError, ValueError):
                continue
            for n in ast.walk(arbol):
                if isinstance(n, ast.Constant) and isinstance(n.value, str):
                    texto = n.value
                elif isinstance(n, ast.JoinedStr):
                    # un f-string pegado a otro forma un solo nodo: el color y
                    # la caja caen en literales distintos pero la cadena final
                    # es una. ast.unparse deja el codigo con sus llaves, que
                    # es justo lo que buscan los patrones ({acento}).
                    texto = ast.unparse(n)
                else:
                    continue
                m_fc = COLOR_DE_TEXTO_FIJO.search(texto)
                m_box = CAJA_DE_COLOR.search(texto)
                # la caja es de acento si su color lo menciona (el acento lo
                # elige el usuario); una caja negra o blanca no lo es
                if m_box and "acento" not in m_box.group(0).lower():
                    m_box = None
                if not (m_fc and m_box):
                    continue
                problemas.append({
                    "tipo": "texto fijo sobre acento",
                    "archivo": os.path.relpath(ruta, BASE).replace(os.sep, "/"),
                    "msg": f"el texto se pinta con '{m_fc.group(1)}' fijo sobre una caja de "
                           f"acento: el acento lo elige el usuario y el color fijo no se "
                           f"lee. usa texto_sobre(acento)"})


def _chequear_clis_del_sk(problemas):
    """Que toda CLI de la skill se pueda encontrar desde el SKILL.md.

    El check de huerfanos exige que un script este enlazado desde ALGUN
    .md. Pero el .md que el agente lee primero es el SKILL.md: una CLI
    enlazada solo en una referencia es una herramienta que el agente no
    va a descubrir. Los modulos privados (los que empiezan por "_") no
    son CLIs y quedan fuera.
    """
    skill = os.path.join(BASE, "SKILL.md")
    scripts_dir = os.path.join(BASE, "scripts")
    if not (os.path.exists(skill) and os.path.isdir(scripts_dir)):
        return
    with open(skill, encoding="utf-8") as fh:
        texto = fh.read()
    for f in sorted(os.listdir(scripts_dir)):
        if not f.endswith(".py") or f.startswith("_"):
            continue
        if f not in texto:
            problemas.append({
                "tipo": "CLI fuera del SKILL.md", "archivo": "SKILL.md",
                "msg": f"scripts/{f} no aparece en el SKILL.md: el agente entra "
                       f"por ahi y no la encuentra"})


def _chequear_commit_que_arrastra_trabajo(problemas):
    """Que un commit no haya arrastrado trabajo en vuelo al arbol commiteado.

    Cuando se commitea con cambios sin commitear en el arbol, el doc y el
    codigo quedan COHERENTES entre si (los dos hablan de lo mismo) pero
    no con la realidad publicada: un doc que nombra 25 suites cuando el
    commit solo tiene 23, o una lista de suites con dos enlaces rotos.

    Los guards de cifras y de lista comparan el doc contra el ARBOL, y en
    un commit asi ambos son erroneos a la vez: no se ven. Este guard
    mira el commit ANTERIOR: si una suite estaba listada y existia, y
    ahora no esta en ninguno de los dos lados, alguien se la llevo.
    """
    raiz = _raiz_git()
    if not raiz:
        return
    try:
        r = subprocess.run(["git", "-C", raiz, "diff", "--name-only", "HEAD~1", "HEAD"],
                           capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return
    if r.returncode != 0 or not r.stdout.strip():
        return
    tocados = [p for p in r.stdout.split() if p.endswith(".md") or p.endswith(".py")]
    if not tocados:
        return

    rel_skill = os.path.relpath(os.path.realpath(BASE), raiz).replace(os.sep, "/")

    def _suites_de(commit):
        """(listadas, reales) de un commit: lo que declara el canonico y lo que hay.

        El canonico es `scripts/data/suites.json` (la lista que escribe
        `scripts/actualizar_conteos.py`). Antes la lista vivia en el
        `SKILL.md`: mismo check, otra fuente.
        """
        try:
            rr = subprocess.run(["git", "-C", raiz, "show",
                                 f"{commit}:{rel_skill}/scripts/data/suites.json"],
                                capture_output=True, text=True, timeout=20)
        except (OSError, subprocess.SubprocessError):
            return set(), set()
        listadas = set()
        if rr.returncode == 0:
            try:
                doc = json.loads(rr.stdout) or {}
                listadas = set(doc.get("suites") or [])
            except ValueError:
                listadas = set()
        reales = set()
        try:
            rr2 = subprocess.run(["git", "-C", raiz, "ls-tree", "-r", "--name-only",
                                  commit, f"{rel_skill}/scripts/_tests/"],
                                 capture_output=True, text=True, timeout=20)
        except (OSError, subprocess.SubprocessError):
            return listadas, set()
        for ln in rr2.stdout.splitlines():
            b = os.path.basename(ln)
            if b.startswith("test_") and b.endswith(".py"):
                reales.add(b)
        return listadas, reales

    antes_list, antes_reales = _suites_de("HEAD~1")
    ahora_list, ahora_reales = _suites_de("HEAD")
    if not antes_list:
        return
    # el CANONICO de las suites no puede desaparecer: si se borra, la lista
    # deja de compararse con el arbol y la proteccion se apaga en silencio.
    # No es lo mismo que "todavia no se ha publicado" (aun no hay canonico
    # en HEAD~1: no hay nada que borrar).
    if antes_list and not ahora_list and _canonico_en(raiz, "HEAD~1", rel_skill):
        problemas.append({
            "tipo": "canonico de suites borrado", "archivo": RUTA_SUITES,
            "msg": "el commit borro scripts/data/suites.json: la lista de suites "
                   "deja de compararse con el arbol, y la proteccion queda apagada "
                   "en silencio (se regenera con `python scripts/actualizar_conteos.py`)"
        })
    # una suite que estaba listada Y existia, y ahora no esta en ninguno de
    # los dos lados: se ha perdido en el commit
    perdidas = (antes_list & antes_reales) - ahora_list - ahora_reales
    for s in sorted(perdidas):
        problemas.append({
            "tipo": "suite perdida en el commit", "archivo": "SKILL.md",
            "msg": f"{s} estaba listada y existia en HEAD~1, y en este commit "
                   f"no esta ni en la lista ni en el arbol: el commit se llevo "
                   f"trabajo en vuelo"})
    # y lo inverso: una suite listada que no existe en el commit (enlace roto)
    rotas = ahora_list - ahora_reales
    for s in sorted(rotas):
        problemas.append({
            "tipo": "suite listada que no existe", "archivo": "SKILL.md",
            "msg": f"este commit lista {s} y no la trae: enlace roto en lo publicado"})


def _chequear_cobertura_de_clis(problemas):
    """Que toda CLI documentada este VERIFICADA: ejecutada de verdad por un
    test, o con un motivo declarado de por que no se puede ejecutar.

    Los dos mecanismos de la skill vigilan fallos DISTINTOS y no se delegan:
    la intercepcion de parse_args prueba que los ARGUMENTOS del comando son
    validos para esa herramienta; la ejecucion real prueba el EFECTO (que la
    herramienta no revienta al usarla). El ImportError de look.py estaba
    DENTRO de default_font_file(): la intercepcion llego a parse_args sin
    despeinarse, porque el fallo no estaba en los argumentos sino en el
    efecto. Los dos hacen falta.

    Y hace falta un TERCERO: que diga cuando una herramienta se ha quedado
    sin ninguno de los dos. Un comando documentado que nadie ejecuta ni
    vigila por argumentos es un puntero a nada: el agente lo copia y no hay
    quien responda de si funciona.
    """
    try:
        import _comandos_doc as _CD
    except ImportError:
        # este repo no trae el modulo de los comandos documentados: no hay
        # cobertura que exigir (y el guard no puede reventar la auditoria)
        return
    documentadas = _CD.scripts_de_los_comandos(BASE)
    if not documentadas:
        return
    ejecutadas = _CD.clis_ejecutadas_por_tests(BASE)
    motivos = _CD.MOTIVOS_SIN_EJECUCION
    sin_verificar = sorted(documentadas - ejecutadas - set(motivos))
    for s in sin_verificar:
        problemas.append({
            "tipo": "cli sin verificar", "archivo": s,
            "msg": f"la CLI documentada {s} no la ejecuta ningun test y no tiene "
                   f"motivo declarado en MOTIVOS_SIN_EJECUCION: nadie sabe si funciona"})
    # al reves: un motivo declarado para una CLI que SI se ejecuta es ruido
    for s in sorted(set(motivos) & ejecutadas):
        problemas.append({
            "tipo": "motivo obsoleto", "archivo": s,
            "msg": f"{s} tiene un motivo declarado para no ejecutarse, pero un test "
                   f"la ejecuta de verdad: el motivo sobra"})


def _chequear_contrato_cli(problemas):
    """Que el contrato de CLI diga cuantos scripts lo cumplen, y sean esos.

    El documento declara una convencion ("las N CLIs de ffmpeg_tools usan
    add_common + apply_common + emit"). Ese N tiene que ser el real: si
    anaden una herramienta sin el contrato, o le quitan el contrato a una,
    el documento queda mintiendo sobre la skill.
    """
    doc = os.path.join(REFS, "cli-contract.md")
    fft_dir = os.path.join(BASE, "scripts", "ffmpeg_tools")
    if not (os.path.exists(doc) and os.path.isdir(fft_dir)):
        return
    n_cumplen = 0
    n_clis = 0
    for f in sorted(os.listdir(fft_dir)):
        if not f.endswith(".py") or f.startswith("_"):
            continue
        with open(os.path.join(fft_dir, f), encoding="utf-8") as fh:
            t = fh.read()
        if "ArgumentParser" not in t and "argparse" not in t:
            continue          # un modulo no es una CLI
        n_clis += 1
        if "add_common" in t and "apply_common" in t and "emit(" in t:
            n_cumplen += 1
    with open(doc, encoding="utf-8") as fh:
        texto = fh.read()
    mt = re.search(r"\*?(\d+)\s+de\s+las\s+(\d+)\s+cumplen\s+el\s+contrato", texto)
    if not mt:
        # el patron dejo de casar con la prosa (una palabra distinta, una
        # barra) y el guard se apagaba en silencio: decia "todo bien" sin
        # mirar nada. un guard que no encuentra su objeto tiene que decirlo,
        # porque su objeto es el numero que verifica
        problemas.append({
            "tipo": "guard sin objeto", "archivo": "references/cli-contract.md",
            "msg": "no encuentro la frase del contrato ('N de las M cumplen el "
                   "contrato'): este guard no comprueba nada hasta que la frase vuelva"})
        return
    # los DOS numeros de la frase: cuantas cumplen el contrato entero y
    # cuantas CLIs hay. vigilar solo el primero dejaba el segundo sin
    # vigilar (y acababa de aparecer en la prosa).
    declarado, total = int(mt.group(1)), int(mt.group(2))
    if declarado != n_cumplen:
        problemas.append({
            "tipo": "conteo obsoleto", "archivo": "references/cli-contract.md",
            "msg": f"dice {declarado} CLIs con el contrato y {n_cumplen} lo cumplen"})
    if total != n_clis:
        problemas.append({
            "tipo": "conteo obsoleto", "archivo": "references/cli-contract.md",
            "msg": f"dice que hay {total} CLIs en ffmpeg_tools/ y hay {n_clis}"})


#: La lista de escenas que enuncia la prosa. El NUMERO ya lo vigila el guard
#: de cifras; la lista que va al lado es OTRA cosa, y puede estar incompleta
#: con el numero siendo correcto. El enfasis se tolera ("**39 scene types**"
#: en el ingles, "con 39 tipos" en el espanol).
#: La lista se captura HASTA LA SIGUIENTE VIÑETA (no hasta el fin de linea):
#: asi una lista partida en varias lineas se comprueba igual, y no hace falta
#: que el guard se apague en silencio cuando alguien parte la linea.
LISTA_DE_ESCENAS = re.compile(
    r"(?:\*)*(\d+)(?:\*)*\s+(?:tipos(?:\s+de\s+escena)?|scene\s+types|scenes)"
    r"(?:\*)*\s*[\u2014-]\s*(.+?)(?=\n\s*[-*]\s|\n\s*\n|\Z)", re.M | re.S)


def _claves_de_escenas(ruta):
    """Los nombres de escena del catalogo: las claves de SCENES.

    Por AST y sin importar el modulo: un guard tiene que ser barato y no
    arrastrar el motor entero.
    """
    import ast
    try:
        with open(ruta, encoding="utf-8") as fh:
            arbol = ast.parse(fh.read())
    except (OSError, SyntaxError, ValueError):
        return set()
    for n in ast.walk(arbol):
        if not isinstance(n, ast.Assign) or not isinstance(n.value, ast.Dict):
            continue
        for t in n.targets:
            if isinstance(t, ast.Name) and t.id == "SCENES":
                return {k.value for k in n.value.keys
                        if isinstance(k, ast.Constant) and isinstance(k.value, str)}
    return set()


def _chequear_lista_de_escenas(problemas):
    """Que la lista de escenas que enuncia la prosa sea el conjunto real.

    El guard de cifras compara el NUMERO ("39 tipos") con el catalogo del
    motor: los dos dicen 39 y sale verde. La lista que va al lado es OTRA
    cosa, y ahi no miraba nadie: el README en espanol listaba 36 de las 39
    (faltaban `callout`, `index` y `orbOpen`) mientras el ingles las
    listaba todas. La cifra era la que se vigilaba y la enumeracion la que
    no.

    Se compara POR CONJUNTO contra el catalogo, no contra el numero: una
    lista puede tener el numero correcto y faltar una escena.
    """
    render = os.path.join(BASE, "scripts", "render_plan.py")
    if not os.path.isfile(render):
        return
    catalogo = _claves_de_escenas(render)
    if not catalogo:
        return
    raiz = os.path.dirname(BASE)          # los README viven un nivel arriba
    for nombre in ("README.md", "README.en.md"):
        ruta = os.path.join(raiz, nombre)
        if not os.path.exists(ruta):
            continue
        with open(ruta, encoding="utf-8") as fh:
            texto = fh.read()
        for mt in LISTA_DE_ESCENAS.finditer(texto):
            declarado = int(mt.group(1))
            nombres = re.findall(r"`([^`]+)`", mt.group(2))
            if not nombres:
                continue
            faltan = sorted(catalogo - set(nombres))
            sobran = sorted(set(nombres) - catalogo)
            if not faltan and not sobran and len(nombres) == declarado:
                continue
            partes = []
            if faltan:
                partes.append(f"no menciona {len(faltan)} escenas del catalogo: "
                              f"{', '.join(faltan)}")
            if sobran:
                partes.append(f"menciona nombres que no son escenas: {', '.join(sobran)}")
            if len(nombres) != declarado:
                partes.append(f"la lista tiene {len(nombres)} nombres y el texto dice "
                              f"{declarado}")
            problemas.append({
                "tipo": "lista de escenas desfasada", "archivo": nombre,
                "msg": ("la lista de escenas no es el catalogo: " + "; ".join(partes)
                        + ". los nombres son las claves de SCENES en scripts/render_plan.py")})


def _todos_los_checks(problemas, mds):
    """Todos los checks, sobre el arbol que este activo.

    Se corre dos veces: una sobre el arbol de trabajo y otra sobre un
    export de HEAD (lo publicado). Asi el guard distingue lo que ya
    esta publico (fallo) de lo que solo se ha desviado en el arbol
    (aviso: todavia no se ha publicado).
    """
    # ---- 1. el pie de cada referencia --------------------------------
    canonicos, dominios = {}, {}
    for f in mds:
        txt = open(os.path.join(REFS, f), encoding="utf-8").read()
        m = list(PIE.finditer(txt))
        if not m:
            problemas.append({"tipo": "pie ausente", "archivo": f,
                              "msg": "la referencia no declara su canonico, su dominio y sus vecinos"})
            continue
        m = m[-1]   # el pie real es el ULTIMO (los ejemplos van antes)
        can = m.group("can").strip()
        dom = m.group("dom").strip()
        vec = [v.strip().strip("`") for v in m.group("vec").split(",") if v.strip()]
        canonicos[f] = can
        dominios[f] = dom
        if not os.path.exists(os.path.join(BASE, can)):
            problemas.append({"tipo": "canonico inexistente", "archivo": f, "msg": can})
        for v in vec:
            if not os.path.exists(os.path.join(BASE, v)):
                problemas.append({"tipo": "vecino inexistente", "archivo": f, "msg": v})

    # ---- 2. el mapa y los pies no se contradicen ----------------------
    mapa_path = os.path.join(BASE, MAPA)
    if not os.path.exists(mapa_path):
        problemas.append({"tipo": "mapa ausente", "archivo": MAPA, "msg": "no existe el indice"})
        mapa_txt = ""
    else:
        mapa_txt = open(mapa_path, encoding="utf-8").read()
    mapa_can = {}
    for f in mds:
        # la tabla del mapa: | `x.md` | ... | dominio |
        for mt in re.finditer(r"^\| `([a-z0-9-]+\.md)` \|([^|]*)\|([^|]*)\|$", mapa_txt, re.M):
            if mt.group(1) == f:
                mapa_can[f] = mt.group(3).strip()
    for f in mds:
        if f == "mapa.md":
            continue
        if f not in mapa_can:
            problemas.append({"tipo": "fuera del mapa", "archivo": f,
                              "msg": "la referencia no aparece en la tabla del mapa"})
        elif canonicos.get(f) and mapa_can[f] and canonicos[f].split("/")[-1] != mapa_can[f]:
            # el mapa dice el canonico como nombre de dominio; compara el dominio
            pass
    # el dominio del mapa debe coincidir con el que declara el pie
    for f in mds:
        dom_mapa = mapa_can.get(f)
        dom_pie = dominios.get(f)
        if dom_mapa and dom_pie and dom_mapa != dom_pie:
            problemas.append({"tipo": "dominio contradictorio", "archivo": f,
                              "msg": f"el mapa dice '{dom_mapa}' y el pie dice '{dom_pie}'"})

    # ---- 3. alcanzable desde SKILL.md ---------------------------------
    aristas = {}
    for dp, dn, fn in os.walk(BASE):
        dn[:] = [d for d in dn if d not in ("__pycache__", ".git")]
        for f in fn:
            if f.endswith((".md", ".py", ".json")):
                ruta = os.path.join(dp, f)
                rel = os.path.relpath(ruta, BASE)
                txt = open(ruta, encoding="utf-8", errors="replace").read()
                aristas[rel] = _rels_de_texto(txt, rel)
    alcance, cola = set(), ["SKILL.md"]
    while cola:
        cur = cola.pop()
        for p in aristas.get(cur, ()):
            if p not in alcance:
                alcance.add(p)
                cola.append(p)
    for rel in sorted(aristas):
        if rel.endswith(".md") and rel != "SKILL.md" and rel not in alcance:
            problemas.append({"tipo": "isla", "archivo": rel,
                              "msg": "no se llega a este archivo desde SKILL.md"})

    # ---- 3b. medios (mp3, mp4, png, ttf) que nadie referencia ---------
    mencionados = set()
    for refs in aristas.values():
        mencionados |= refs
    for dp, dn, fn in os.walk(BASE):
        dn[:] = [d for d in dn if d not in ("__pycache__", ".git")]
        for f in fn:
            if f.lower().endswith(MEDIA):
                rel = os.path.relpath(os.path.join(dp, f), BASE)
                if rel != "metricas/historial.jsonl" and rel not in mencionados:
                    problemas.append({"tipo": "medio huerfano", "archivo": rel,
                                      "msg": "nadie lo referencia: es un archivo muerto de la skill"})

    # ---- 4. enlaces rotos --------------------------------------------
    for rel, refs in sorted(aristas.items()):
        for p in sorted(refs):
            if os.path.exists(os.path.join(BASE, p)):
                continue
            if p in EXCEPCIONES or os.path.basename(p) in EXCEPCIONES:
                continue
            problemas.append({"tipo": "enlace roto", "archivo": rel, "msg": p})

    # ---- 5. las reglas con un valor unico no pueden divergir ----------
    _chequear_reglas(problemas)

    # ---- 6. los conteos del encabezado del mapa no pueden quedar viejos --
    _chequear_conteos(problemas)

    # ---- 7. todo camino que produce un entregable acaba en la puerta ----
    _chequear_puerta(problemas)
    _chequear_verticales(problemas)

    # ---- 8. lo que el SKILL.md promete es lo que el codigo imprime ------
    _chequear_promesas(problemas)

    # ---- 9. toda receta del Motor Selector dice que correr -------------
    _chequear_recetas(problemas)

    # ---- 10. el catalogo documentado es el del motor, por nombre --------
    _chequear_escenas(problemas)

    # ---- 11. las cifras de la prosa son las del codigo -----------------
    _chequear_cifras_del_codigo(problemas)

    # ---- 12. la lista de suites del SKILL.md es el conjunto real -------
    _chequear_lista_de_suites(problemas)

    # ---- 13. toda clave del plan que el motor lee esta documentada -----
    _chequear_claves_del_plan(problemas)

    # ---- 14. las cifras de una CLI son las de sus subcomandos ---------
    _chequear_cifras_de_cli(problemas)

    # ---- 15. toda CLI se encuentra desde el SKILL.md -------------------
    _chequear_clis_del_sk(problemas)

    # ---- 15b. ningun texto fijo sobre una caja de acento -------------
    _chequear_texto_fijo_sobre_acento(problemas)

    # ---- 15b2. la lista de escenas es el conjunto real ---------------
    _chequear_lista_de_escenas(problemas)

    # ---- 15b3. las convenciones que pide el codigo, escritas ----
    _chequear_convenciones_escritas(problemas)

    # ---- 15c. todo test declarado se ejecuta --------------------------
    _chequear_tests_que_no_se_ejecutan(problemas)

    # ---- 16. el commit no arrastro trabajo en vuelo --------------------
    _chequear_commit_que_arrastra_trabajo(problemas)

    # ---- 17. el contrato de CLI dice los que lo cumplen ----------------
    _chequear_contrato_cli(problemas)
    _chequear_cobertura_de_clis(problemas)

    return dominios, canonicos, alcance


def _exportar_head(destino, raiz):
    """Exporta el estado PUBLICADO (HEAD) a un directorio.

    Se exporta la carpeta de la skill TAL COMO esta en el repo (puede ser
    "editoria/" o cualquier otra): el guard tiene que funcionar igual en
    un repo de pruebas que en el de verdad.
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


def _dos_pasadas():
    """Corre los checks dos veces: lo PUBLICADO (HEAD) y el ARBOL de trabajo.

    - Lo publicado se mide contra si mismo: si el doc de HEAD no cuadra con
      el codigo de HEAD, lo que hay en GitHub miente, y es un FALLO.
    - El arbol de trabajo se mide contra si mismo tambien, pero lo que solo
      se desvia ahi es un AVISO: todavia no se ha publicado, y lo que toca
      es correr la herramienta que actualiza los numeros.

    Asi un doc que se lleva trabajo en vuelo (el c37a417) se ve ANTES de
    commitear, y lo ya publicado no puede quedar mintiendo.
    """
    global BASE, REFS
    import tempfile
    mds = sorted(f for f in os.listdir(REFS) if f.endswith(".md"))
    problemas = []
    dominios, canonicos, alcance = _todos_los_checks(problemas, mds)

    avisos = []
    raiz = _raiz_git()
    # esto no va por las dos pasadas: es del historial, no del arbol
    _chequear_atribucion(problemas)
    if raiz:
        with tempfile.TemporaryDirectory() as tmp:
            base_head = _exportar_head(tmp, raiz)
            if base_head:
                b0, r0 = BASE, REFS
                BASE, REFS = base_head, os.path.join(base_head, "references")
                try:
                    publicados = []
                    mds_head = sorted(f for f in os.listdir(REFS) if f.endswith(".md"))
                    _todos_los_checks(publicados, mds_head)
                finally:
                    BASE, REFS = b0, r0
                # lo que esta en el arbol y no en lo publicado: todavia no
                # sale, es un aviso (y el arreglo es la herramienta)
                # lo PUBLICAADO tiene que estar bien: eso son los fallos.
                # lo que solo se ha desviado en el arbol de trabajo todavia no
                # ha salido: es un aviso, y lo que hay que hacer es correr la
                # herramienta que actualiza los numeros.
                claves_pub = {(pr["tipo"], pr["archivo"]) for pr in publicados}
                for pr in problemas:
                    if pr.get("severidad") == "aviso":
                        avisos.append(pr)
                    elif (pr["tipo"], pr["archivo"]) not in claves_pub:
                        avisos.append(pr)
                problemas = publicados
                # el HISTORIAL es de lo PUBLICADO: su basura es un FALLO, no un
                # aviso. Va aqui, despues de `problemas = publicados`, porque
                # antes caia en el cubo de los avisos (lo que solo se ha
                # desviado en el arbol) y la puerta decia "todo bien" con el
                # texto roto dentro. Un aviso que no frena nada no es un aviso:
                # es una nota.
                _chequear_mensajes_de_commit(problemas, avisos)
    return problemas, avisos, mds, dominios, canonicos, alcance


def _chequear_mensajes_de_commit(problemas, avisos):
    """Que los mensajes de commit no traigan basura de otro idioma.

    El mensaje de un commit es parte del artefacto publicado: se lee, se
    busca, se cita. Un ideograma, un kana o un hangul dentro es un fallo de
    tipografia que se asume decision. El guard del ARBOL (validate_skill.py)
    lo ve en los .md/.py/.json, pero el MENSAJE no vive en el arbol: nadie lo
    miraba. Por esa puerta se colaron dos ideogramas en un mensaje, y si ese
    commit hubiera sido el de la rama, el texto roto habria salido publicado.

    Se mira el HISTORIAL ALCANZABLE desde HEAD (lo que se publica): lo que
    queda huerfano (un commit amended) no sale, asi que no se juzga.

    Y se distinguen dos cosas: lo que AUN NO ha salido (se puede arreglar con
    'git commit --amend' y por tanto FRENA la puerta) y lo que ya salio
    (historia: avisar, porque reescribir el historial es otra decision, y una
    puerta que no se puede pasar dejaria el repo en rojo para siempre).
    """
    raiz = _raiz_git()
    if not raiz:
        return
    try:
        r = subprocess.run(["git", "-C", raiz, "log", "--format=%h%x09%B%x1e"],
                           capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return
    if r.returncode != 0:
        return
    ya_publicados = _commits_publicados(raiz)
    for bloque in r.stdout.split("\x1e"):
        bloque = bloque.strip()
        if not bloque:
            continue
        h, _, cuerpo = bloque.partition("\t")
        mt = RE_BASURA.search(cuerpo)
        if not mt:
            continue
        if h.strip() in ya_publicados:
            avisos.append({
                "tipo": "basura en el historial", "archivo": h.strip(),
                "msg": f"el mensaje del commit {h.strip()} trae '{mt.group(0)}' y ya "
                       f"salio publicado: es historia. Aviso, no fallo: arreglarlo "
                       f"exigiria reescribir el historial"})
        else:
            problemas.append({
                "tipo": "basura en el historial", "archivo": h.strip(),
                "msg": f"el mensaje del commit {h.strip()} trae '{mt.group(0)}': el "
                       f"historial es texto publicado y se lee. Si es el ultimo commit, "
                       f"se corrige con 'git commit --amend'"})


def _commits_publicados(raiz):
    """Los commits que ya estan en el remoto: los que no se pueden arreglar
    sin reescribir la historia (un amend no los toca)."""
    try:
        r = subprocess.run(["git", "-C", raiz, "rev-list", "--remotes", "--abbrev-commit"],
                           capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return set()
    if r.returncode != 0:
        return set()
    return set(r.stdout.split())


def _chequear_atribucion(problemas):
    """Que el historial diga quien escribio cada commit (o que se avise de que no).

    Dos sesiones del mismo agente sobre el mismo repo, commiteando con la
    MISMA identidad de git, hacen que el campo "autor" no distinga quien
    escribio cada commit. Es la unica parte del historial que no se puede
    recuperar despues, asi que no es un fallo (la skill es valida igual):
    es un aviso, para que quede dicho en el propio repo y no en un chat que
    se pierde.

    Pero el aviso mira tambien la SOLUCION: si los mensajes llevan un
    sufijo de sesion ("[sesion-a153]", "[sesion-524d]"), la atribucion se
    puede leer ahi y no hay nada que avisar. La convencion esta en
    references/mapa.md (regla 12).

    Arreglo: una identidad de git por sesion (`git config user.name`), o
    un sufijo en el mensaje del commit.
    """
    raiz = _raiz_git()
    if not raiz:
        return
    try:
        r = subprocess.run(["git", "-C", raiz, "log", "--format=%an%x09%s"],
                           capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return
    if r.returncode != 0 or not r.stdout.strip():
        return
    autores, sufijos = [], set()
    for linea in r.stdout.splitlines():
        if "\t" not in linea:
            continue
        autor, mensaje = linea.split("\t", 1)
        autores.append(autor)
        mt = re.search(r"\[([A-Za-z0-9_.-]{1,24})\]\s*$", mensaje)
        if mt:
            sufijos.add(mt.group(1))
    if len(autores) > 5 and len(set(autores)) == 1:
        if len(sufijos) > 1:
            # el sufijo en el mensaje YA distingue las sesiones: no hay nada
            # que avisar (y el aviso no puede quejarse de algo ya arreglado)
            return
        problemas.append({
            "tipo": "autribucion ambigua", "archivo": "historial",
            "msg": f"{len(autores)} commits y un solo autor ({autores[0]}): el campo "
                   f"'autor' no dice quien escribio cada uno. Una identidad de git por "
                   f"sesion, o un sufijo en el mensaje del commit (la convencion esta en "
                   f"references/mapa.md: [sesion-XXXX])",
            "severidad": "aviso"})


def main():
    ap = argparse.ArgumentParser(description="Auditoria de conectividad de la skill (sin islas).",
                                 epilog="Sale 0 si todo esta bien, 1 si hay islas o contradicciones.")
    ap.add_argument("--json", help="guarda el informe en este archivo")
    args = ap.parse_args()

    if not os.path.isdir(REFS):
        print("ERROR: no se encuentra la skill", file=sys.stderr)
        return 2

    problemas, avisos, mds, dominios, canonicos, alcance = _dos_pasadas()

    # lo que este guard NO ha podido mirar, se dice: un guard que no
    # encuentra su objeto tiene que decirlo, no pasar en silencio (la copia
    # instalada no tiene .git, y ahi el historial no se puede ver).
    notas = []
    if not _raiz_git():
        notas.append("sin repo: los mensajes de commit no se han podido mirar "
                     "(el historial vive en el repo; la copia instalada no lo tiene)")
        print("NOTA: " + notas[-1])
    if _suites_declaradas() is None:
        notas.append("sin canonico de suites (scripts/data/suites.json): la lista "
                     "de suites no se ha podido mirar, y la proteccion que la "
                     "compara con el arbol queda apagada")
        print("NOTA: " + notas[-1])

    # ---- informe ------------------------------------------------------
    dominios_resumen = {}
    for f, d in sorted(dominios.items()):
        dominios_resumen.setdefault(d, []).append(f)
    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump({"ok": not problemas, "problemas": problemas,
                       "avisos": avisos, "notas": notas,
                       "dominios": {k: v for k, v in sorted(dominios_resumen.items())},
                       "alcanzables": len(alcance)}, f, ensure_ascii=False, indent=1)
    if avisos:
        print(f"AVISOS ({len(avisos)}): lo que se ha desviado en el arbol de "
              f"trabajo y todavia no se ha publicado")
        for p in avisos:
            print(f"  {p['tipo']:22} {p['archivo']:36} {p['msg']}")
        if any(p.get("severidad") != "aviso" for p in avisos):
            print("  (corre `python scripts/actualizar_conteos.py` antes de commitear)")
    if problemas:
        print(f"MAPA: {len(problemas)} problemas")
        for p in problemas:
            print(f"  {p['tipo']:22} {p['archivo']:36} {p['msg']}")
    elif not avisos:
        print(f"MAPA: OK · {len(mds)} referencias, {len(dominios_resumen)} dominios, "
              f"todo alcanzable desde SKILL.md")
        for d, fs in sorted(dominios_resumen.items()):
            canon = next((canonicos[f] for f in fs if f in canonicos and
                          canonicos[f].endswith("/" + f) or f == canonicos.get(f, "")), "")
            print(f"  {d:12} {len(fs):2} archivos  canonico: {canon}")
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())
