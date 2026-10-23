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
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFS = os.path.join(BASE, "references")
MAPA = "references/mapa.md"
PIE = re.compile(r"^→ Canónico: `(?P<can>[^`]+)` · Dominio: (?P<dom>[^·]+?) · "
                  r"Vecinos: (?P<vec>[^\n]+)$", re.M)
REF = re.compile(r"(?:references|scripts|film|metricas|assets|brand)/[A-Za-z0-9_./-]+\.(?:md|py|json|png|mp4|mp3|ttf)")
MEDIA = (".mp3", ".mp4", ".png", ".ttf")
SCRIPT_REF = re.compile(r"scripts/[A-Za-z0-9_./-]+\.py")

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
LOG_FECHA = re.compile(r"^\s*-\s*\d{4}-\d{2}-\d{2}\s*·")   # entrada de log: registro, no regla
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
                m = re.search(regla["patron"], bloque)
                if not m:
                    continue
                grupos = [g for g in m.groups() if g]
                if not grupos:
                    continue
                # el decimal puede venir con coma ("0,5-2 s") o con punto:
                # sin normalizar, float() revienta y la regla NUNCA se compara
                # (un numero con coma se escapa del guard por mucho que se
                # enuncie en la prosa)
                try:
                    if isinstance(regla["valor"], tuple):
                        v = tuple(float(g.replace(",", ".")) for g in grupos)
                    else:
                        v = float(grupos[0].replace(",", "."))
                except ValueError:
                    continue
                valores.setdefault(v, set()).add(f)
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
        return
    n_refs = len([f for f in os.listdir(REFS) if f.endswith(".md")])
    scripts_dir = os.path.join(BASE, "scripts")
    fft_dir = os.path.join(scripts_dir, "ffmpeg_tools")
    tests_dir = os.path.join(scripts_dir, "_tests")
    # un arbol parcial (tests, copias de trabajo) no tiene todos los directorios:
    # el conteo solo se puede verificar sobre la skill completa
    if not (os.path.isdir(fft_dir) and os.path.isdir(tests_dir)):
        return
    n_scripts = len([f for f in os.listdir(scripts_dir)
                      if f.endswith(".py") and os.path.isfile(os.path.join(scripts_dir, f))])
    n_fft = len([f for f in os.listdir(fft_dir) if f.endswith(".py")])
    n_tests = len([f for f in os.listdir(tests_dir)
                   if f.endswith(".py") and f != "__init__.py"])
    for declarado, real, que in ((int(m.group(1)), n_refs, "referencias"),
                                 (int(m.group(2)), n_scripts, "scripts"),
                                 (int(m.group(3)), n_fft, "herramientas de ffmpeg"),
                                 (int(m.group(4)), n_tests, "suites de tests")):
        if declarado != real:
            problemas.append({"tipo": "conteo obsoleto", "archivo": "references/mapa.md",
                              "msg": f"dice {declarado} {que} y hay {real}"})
    _chequear_conteos_readme(problemas, n_refs, n_fft, n_tests)


#: rutas de lectura que terminan en un entregable: tienen que acabar en la puerta
RUTAS_CON_ENTREGABLE = ("CREAR", "EDITAR", "clonar", "resumen",
                        "video grabado", "hecho con IA")


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


def _chequear_conteos_readme(problemas, n_refs, n_fft, n_tests):
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
            n_root = len([f for f in os.listdir(scripts_dir)
                          if f.endswith(".py") and os.path.isfile(os.path.join(scripts_dir, f))])
            for declarado, real, que in ((r_, n_root, "scripts root"), (f_, n_fft, "ffmpeg_tools"),
                                         (t_, n_tests, "suites de tests"),
                                         (s_, n_root + n_fft + n_tests, "scripts en total")):
                if declarado != real:
                    problemas.append({"tipo": "conteo obsoleto", "archivo": etiqueta,
                                      "msg": f"dice {declarado} {que} y hay {real}"})


def _n_primitivas_dry(scripts_dir):
    """Cuantas primitivas DRY declara el motor (las que el README cuenta)."""
    import ast
    ruta = os.path.join(scripts_dir, "render_plan.py")
    with open(ruta, encoding="utf-8") as fh:
        arbol = ast.parse(fh.read())
    nombres = {n.name for n in arbol.body if isinstance(n, ast.FunctionDef)}
    conocidas = {"barra_h", "cuenta_up", "arco", "particulas", "cuadricula", "linewrap",
                 "tarjeta_cristal", "boton_halo", "insignia_3d", "tarjeta", "texto_que_cabe",
                 "fuente_que_cabe", "grupo", "fundir", "check", "onda_clic", "flota", "entra",
                 "elipse_se_dibuja", "placa_texto"}
    return len(conocidas & nombres)


def _n_escenas(scripts_dir):
    """Cuantas escenas declara el motor (SCENES)."""
    import ast
    ruta = os.path.join(scripts_dir, "render_plan.py")
    with open(ruta, encoding="utf-8") as fh:
        arbol = ast.parse(fh.read())
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
    if not os.path.exists(ruta):
        return None
    with open(ruta, encoding="utf-8") as fh:
        arbol = ast.parse(fh.read())
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
        doc = os.path.join(REFS, "qa-entrega.md")
        if os.path.exists(doc):
            texto = _prosa(open(doc, encoding="utf-8").read())
            for mt in re.finditer(r"\b([a-zA-ZáéíóúñÁÉÍÓÚÑ]+|\d+)\s+comprobaciones\b", texto):
                palabra = mt.group(1).lower()
                if palabra in ("una", "un", "las", "los", "estas", "esos", "sus", "todas"):
                    continue
                if siempre != total_plan:
                    problemas.append({
                        "tipo": "cifra falsa", "archivo": "references/qa-entrega.md",
                        "msg": f"afirma '{mt.group(1)} comprobaciones', pero la puerta corre "
                               f"{siempre} sin plan y {total_plan} con plan: "
                               f"un numero fijo en la prosa es un numero falso"})
                else:
                    problemas.append({
                        "tipo": "cifra falsa", "archivo": "references/qa-entrega.md",
                        "msg": f"afirma '{mt.group(1)} comprobaciones' y la puerta corre {siempre}"})


def _chequear_lista_de_suites(problemas):
    """Que la lista de suites del SKILL.md sea el conjunto real.

    El SKILL.md enumera las suites que tienen que pasar. Esa lista es una
    promesa: si alguien anade una suite y no la lista, la promesa sigue
    diciendo lo mismo y nadie se entera. Y al reves, una suite listada
    que ya no existe hace fallar la validacion por un archivo que no
    esta.
    """
    skill = os.path.join(BASE, "SKILL.md")
    tests_dir = os.path.join(BASE, "scripts", "_tests")
    if not os.path.exists(skill) or not os.path.isdir(tests_dir):
        return
    txt = open(skill, encoding="utf-8").read()
    listadas = set(re.findall(r"scripts/_tests/(test_[A-Za-z0-9_]+\.py)", txt))
    if not listadas:
        return
    reales = {f for f in os.listdir(tests_dir)
              if f.startswith("test_") and f.endswith(".py")}
    for f in sorted(reales - listadas):
        problemas.append({
            "tipo": "suite sin enlistar", "archivo": "SKILL.md",
            "msg": f"existe scripts/_tests/{f} y el SKILL.md no la lista: "
                   f"la lista de suites tiene que ser el conjunto real"})
    for f in sorted(listadas - reales):
        problemas.append({
            "tipo": "suite listada que no existe", "archivo": "SKILL.md",
            "msg": f"el SKILL.md lista scripts/_tests/{f} y ese archivo no existe"})


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
        ruta = os.path.join(BASE, "scripts", f)
        if not os.path.exists(ruta):
            continue
        t = open(ruta, encoding="utf-8").read()
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
    if not os.path.exists(ruta):
        return None
    with open(ruta, encoding="utf-8") as fh:
        arbol = ast.parse(fh.read())
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


def main():
    ap = argparse.ArgumentParser(description="Auditoria de conectividad de la skill (sin islas).",
                                 epilog="Sale 0 si todo esta bien, 1 si hay islas o contradicciones.")
    ap.add_argument("--json", help="guarda el informe en este archivo")
    args = ap.parse_args()

    if not os.path.isdir(REFS):
        print("ERROR: no se encuentra la skill", file=sys.stderr)
        return 2

    mds = sorted(f for f in os.listdir(REFS) if f.endswith(".md"))
    problemas = []

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

    # ---- informe ------------------------------------------------------
    dominios_resumen = {}
    for f, d in sorted(dominios.items()):
        dominios_resumen.setdefault(d, []).append(f)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump({"ok": not problemas, "problemas": problemas,
                       "dominios": {k: v for k, v in sorted(dominios_resumen.items())},
                       "alcanzables": len(alcance)}, f, ensure_ascii=False, indent=1)
    if problemas:
        print(f"MAPA: {len(problemas)} problemas")
        for p in problemas:
            print(f"  {p['tipo']:22} {p['archivo']:36} {p['msg']}")
    else:
        print(f"MAPA: OK · {len(mds)} referencias, {len(dominios_resumen)} dominios, "
              f"todo alcanzable desde SKILL.md")
        for d, fs in sorted(dominios_resumen.items()):
            canon = next((canonicos[f] for f in fs if f in canonicos and
                          canonicos[f].endswith("/" + f) or f == canonicos.get(f, "")), "")
            print(f"  {d:12} {len(fs):2} archivos  canonico: {canon}")
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())
