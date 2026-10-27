#!/usr/bin/env python3
"""Audita un plan.json de EditorIA antes de renderizar.
Uso: python auditar_plan.py plan.json [--json] [--tol 0.05]
Verifica: solapes de tiempos entre escenas, duraciones negativas o cero,
escenas vacías (sin texto ni voz), campos "voz" presentes pero vacíos,
desorden temporal (from > to, escenas fuera de orden), escena final muy
corta (< 2s), coherencia con plan["duracion"] y que cada voz quepa en su
escena sin pisar la siguiente (sílabas habladas con cifras expandidas al
ritmo del idioma: speech_estimate.py, la fuente única de la estimación).
La tolerancia del reloj de la voz es PROPORCIONAL al hueco disponible, no
un número plano: la estimación silábica se desvía entre un 9% y un 24% del
tiempo real (medido con audio real), y un margen fijo menor que ese error
rechazaba planes cuya narración cabía de verdad.
Además detecta «tells» de pieza generada (jerga de marketing, emoji como
icono, placeholders, prueba social sin fuente, titulares largos, la misma
escena tres veces, cadencia de metrónomo...): siempre AVISO, nunca ERROR,
porque una excepción deliberada es legítima. Se silencian con `"tells_ok":
["codigo"]` en el plan o con --sin-tells (references/direccion-de-arte.md).
Reporta cada hallazgo con su timestamp. Solo stdlib.
"""
import argparse, json, os, re, statistics, sys

from speech_estimate import (AIRE_VOZ, RITMOS, auditar_plan_voces, detectar_idioma,
                             estimar_duracion, silabas)
import repertorio as REP

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg_tools"))
from _comun import CV_MIN_CADENCIA  # noqa: E402


def tipos_validos():
    """Los tipos salen del dict SCENES de render_plan.py (fuente única): una
    lista copiada aquí quedaba vieja en cuanto se añadía una escena."""
    ruta_rp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "render_plan.py")
    with open(ruta_rp, encoding="utf-8") as fh:
        src = fh.read()
    bloque = re.search(r"^SCENES\s*=\s*\{(.*?)\}\s*$", src, re.S | re.M).group(1)
    return set(re.findall(r'"(\w+)"\s*:\s*sc_', bloque))


TIPOS_VALIDOS = tipos_validos()


def _t_num(v):
    """Convierte int/float (no bool) a float; devuelve None si no es numérico."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return float(v)


def es_vacia(e):
    """Sin contenido propio: ningún campo (texto, datos, imagen, voz) más allá
    del tipo, los tiempos y la transición. Cada escena usa campos distintos."""
    for k, v in e.items():
        if k in ("tipo", "from", "to", "transicion", "transicionX", "transicionY"):
            continue
        if isinstance(v, str) and v.strip():
            return False
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return False
        if isinstance(v, (list, dict)) and v:
            return False
    return True


def at_fuera(at, fr, to):
    """Tiempos at: fuera de la ventana [from, to] de la escena."""
    mal = []
    if fr is None or to is None:
        return mal

    def walk(v):
        if isinstance(v, bool):
            return
        if isinstance(v, (int, float)):
            if not (fr - 0.01 <= v <= to + 0.01):
                mal.append(v)
        elif isinstance(v, list):
            for x in v:
                walk(x)
        elif isinstance(v, dict):
            for x in v.values():
                walk(x)
    walk(at)
    return mal


def auditar_estructura(plan, tol=0.05, min_final=2.0):
    """Audita un diccionario de plan ya cargado y devuelve lista de hallazgos."""
    if not isinstance(plan, dict):
        return [{"nivel": "ERROR", "t": 0.0, "msg": "el plan raíz debe ser un objeto JSON"}]
    escenas = plan.get("escenas", [])
    if not isinstance(escenas, list):
        return [{"nivel": "ERROR", "t": 0.0, "msg": "el campo 'escenas' debe ser una lista"}]
    if not escenas:
        # Un plan sin escenas no es una pieza: TODOS los chequeos de abajo
        # viven dentro de bucles sobre las escenas, asi que con cero el plan
        # pasaba la auditoria entero ("PLAN VALIDO: 0 escenas auditadas") y
        # el motor reventaba despues con un IndexError sin mensaje. Un guard
        # que no mira nada no puede decir "todo bien".
        return [{"nivel": "ERROR", "t": 0.0,
                 "msg": "el plan no tiene escenas: un plan sin escenas no es una pieza"}]
    hallazgos = []

    def add(nivel, t, msg):
        hallazgos.append({"nivel": nivel, "t": round(float(t or 0.0), 2), "msg": msg})

    pares_validos = []
    for idx, e in enumerate(escenas):
        if not isinstance(e, dict):
            add("ERROR", 0.0, f"escena {idx}: debe ser un objeto JSON")
            continue
        pares_validos.append((idx, e))

    ordenadas = sorted(pares_validos, key=lambda p: _t_num(p[1].get("from")) or 0.0)
    prev_to_val = None
    prev_idx = None
    for idx, e in ordenadas:
        fr_raw, to_raw = e.get("from"), e.get("to")
        fr, to = _t_num(fr_raw), _t_num(to_raw)
        tipo = e.get("tipo", "?")
        if tipo not in TIPOS_VALIDOS:
            add("ERROR", fr if fr is not None else 0.0,
                f"escena {idx} ({tipo}): tipo desconocido — "
                f"válidos: {', '.join(sorted(TIPOS_VALIDOS))}")
        if fr is None or to is None:
            add("ERROR", fr if fr is not None else 0.0,
                f"escena {idx} ({tipo}): falta from/to numérico")
            continue
        for donde, sub in (("at", e.get("at")),):
            for v in at_fuera(sub, fr, to):
                add("AVISO", fr,
                    f"escena {idx} ({tipo}): {donde}={v} fuera de la ventana "
                    f"[{fr},{to}] — el elemento nunca aparece")
        for lista_k in ("mensajes", "canales", "pasos", "items", "notificaciones"):
            items_l = e.get(lista_k)
            if not isinstance(items_l, list):
                continue
            for j, m in enumerate(items_l):
                if isinstance(m, dict) and "at" in m:
                    for v in at_fuera(m["at"], fr, to):
                        add("AVISO", fr,
                            f"escena {idx} ({tipo}): sub-elemento {j} at={v} "
                            f"fuera de [{fr},{to}]")
        if to <= fr:
            add("ERROR", fr, f"escena {idx} ({tipo}): duración no positiva (from={fr}, to={to})")
        if to - fr < 0.4:
            add("AVISO", fr, f"escena {idx} ({tipo}): muy corta ({to-fr:.2f}s)")
        if es_vacia(e):
            add("AVISO", fr, f"escena {idx} ({tipo}): escena vacía (sin texto ni voz)")
        if "voz" in e and isinstance(e["voz"], str) and not e["voz"].strip():
            add("AVISO", fr, f"escena {idx} ({tipo}): campo voz presente pero vacío")
        if prev_to_val is not None:
            if fr < prev_to_val - tol:
                add("ERROR", fr, f"escena {idx} ({tipo}): solapa con la anterior "
                                 f"(from={fr} < to_previo={prev_to_val})")
            elif fr - prev_to_val > 1.0:
                add("AVISO", prev_to_val, f"hueco de {fr-prev_to_val:.2f}s entre escena "
                                          f"{prev_idx} y {idx}")
        prev_to_val = to
        prev_idx = idx

    # La narración manda el reloj: la voz estimada debe caber en su escena y,
    # sobre todo, no pisar la voz siguiente (voz_off mezcla con amix: dos
    # voces a la vez). Estimación antes de pagar TTS; voz_off mide la real.
    con_voz = [(idx, e) for idx, e in ordenadas
               if isinstance(e.get("voz"), str) and e["voz"].strip()
               and _t_num(e.get("from")) is not None]
    # idioma: plan["idioma"], luego plan["numeros"], luego el texto de las voces
    idioma = plan.get("idioma") if plan.get("idioma") in RITMOS else (
        plan.get("numeros") if plan.get("numeros") in RITMOS
        else detectar_idioma(" ".join(e["voz"] for _, e in con_voz)))
    ritmo = plan.get("ritmo_voz", "normal")
    if ritmo not in RITMOS[idioma]:
        add("AVISO", 0.0, f"ritmo_voz '{ritmo}' desconocido ({', '.join(RITMOS[idioma])}); uso normal")
        ritmo = "normal"
    # LA REGLA DEL RELOJ, en un solo sitio: `speech_estimate.auditar_plan_voces`
    # (la fuente). Antes cada script tenia la suya: esta midia contra la voz
    # siguiente, `auditar_plan_voces` (que usa `clonar_video.py`) exigia que
    # la voz terminase dentro de su PROPIA escena — un criterio mas estricto
    # que el del resto de la skill. Se contradecian en los 10 planes de la
    # demo (una decia "cabe" y la otra "no cabe", cuando la narracion real
    # si cabia) y el clonado recortaba copy de mas por nada.
    #
    # El margen es proporcional al hueco (BANDA_ESTIMACION, en
    # speech_estimate.py): la estimacion silabica NO es exacta. Medida contra
    # audio real (50 frases de la voz del sistema, Paulina es-MX a 178 ppm),
    # overestimate el tiempo real entre un 9% y un 24% (mediana 12%). Un
    # margen fijo de 0.3s es MENOR que ese error: el plan cuya narracion
    # cabe de verdad se rechaza (falso positivo) y el agente recorta copy
    # que no sobra. Por debajo de la banda es AVISO, y quien decide es el
    # TTS real (voz_off.py / voz_local.py), que mide el audio sintetizado y
    # FALLA si se pisan.
    reloj = auditar_plan_voces(plan, idioma=idioma, aire_inicial=AIRE_VOZ, ritmo=ritmo)
    por_indice = {idx: e for idx, e in con_voz}
    for a in reloj["alertas"]:
        idx = a["escena_index"]
        n, dur = a["silabas"], a["tiempo_estimado"]
        fr_v = _t_num(por_indice[idx].get("from"))
        if a["contra_final"]:
            add("ERROR", fr_v, f"escena {idx}: la voz ({n} sílabas ≈ {dur:.1f}s) "
                f"se sale del final del video en {a['exceso_segundos']:.1f}s — "
                f"acortar el texto o alargar el video")
        else:
            add("ERROR", fr_v, f"escena {idx}: la voz ({n} sílabas ≈ "
                f"{dur:.1f}s) pisaría la voz siguiente en {a['exceso_segundos']:.1f}s — "
                f"alargar la escena o recortar el texto")
    for a in reloj["avisos"]:
        idx = a["escena_index"]
        n, dur = a["silabas"], a["tiempo_estimado"]
        fr_v = _t_num(por_indice[idx].get("from"))
        if a["contra_final"]:
            # La voz que se sale del FINAL DEL VIDEO no tiene otra imagen que
            # la tape: se corta contra el borde. Con la estimacion no se
            # puede PROBAR el corte, asi que sale como aviso; el que falla
            # es el TTS real.
            dur_video = _t_num(plan.get("duracion"))
            add("AVISO", fr_v, f"escena {idx}: la voz puede salirse del final del video "
                f"(estimada hasta {fr_v + AIRE_VOZ + dur:.1f}s, el video dura {dur_video:.1f}s) — "
                f"verificar con voz_off.py / voz_local.py (miden el audio real)")
        else:
            add("AVISO", fr_v, f"escena {idx}: la voz ({n} sílabas ≈ "
                f"{dur:.1f}s) roza la voz siguiente — verificar con "
                f"voz_off.py / voz_local.py (miden el audio real)")
    # La voz que se pasa del final de SU escena no es un defecto (una
    # locucion que cruza el corte es normal): se dice, pero no se falla, y
    # solo si esa escena no tiene ya un aviso del reloj (si "roza" a la voz
    # siguiente, ese es el aviso que importa: dos avisos por escena son
    # ruido).
    con_roce = {a["escena_index"] for a in reloj["avisos"]} | {
        a["escena_index"] for a in reloj["alertas"]}
    for idx, e in con_voz:
        if idx in con_roce:
            continue
        fr_v = _t_num(e.get("from"))
        to_v = _t_num(e.get("to"))
        if to_v is None:
            continue
        fin = fr_v + AIRE_VOZ + estimar_duracion(e["voz"], idioma, ritmo)
        if fin > to_v:
            add("AVISO", fr_v, f"escena {idx}: la voz ({silabas(e['voz'], idioma)} sílabas ≈ "
                f"{estimar_duracion(e['voz'], idioma, ritmo):.1f}s) se sale de la escena "
                f"en {fin - to_v:.1f}s")

    ordenadas_con_t = [(idx, e) for idx, e in ordenadas
                       if _t_num(e.get("from")) is not None and _t_num(e.get("to")) is not None]
    if ordenadas_con_t:
        idx, e = ordenadas_con_t[-1]
        dur_fin = _t_num(e.get("to")) - _t_num(e.get("from"))
        if dur_fin < min_final:
            add("AVISO", _t_num(e.get("from")),
                f"escena final {idx} ({e.get('tipo','?')}): dura {dur_fin:.2f}s "
                f"(mínimo {min_final}s para tarjeta final)")

    dur_plan = _t_num(plan.get("duracion"))
    if dur_plan is not None and ordenadas_con_t:
        fin = max(_t_num(e.get("to")) for _, e in ordenadas_con_t)
        if abs(fin - dur_plan) > 0.5:
            add("AVISO", fin, f"plan['duracion']={plan['duracion']}s pero la última "
                              f"escena termina en {fin:.2f}s")

    for msg in credenciales_en(plan):
        add("ERROR", 0.0, msg)

    return hallazgos


#: como se ve una credencial. El plan va al repo y al guion: una key pegada
#: ahi se publica. La regla del SKILL.md ("no credentials or API keys appear
#: in plan.json or brand/*.json") era una promesa sin ningun check: ahora la
#: cumple el mismo comando que el agente corre antes de renderizar.
_PATRONES_CRED = (
    (re.compile(r"sk-[A-Za-z0-9_\-]{12,}"), "una key con formato sk-..."),
    (re.compile(r"(?i)\b(eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.)"), "un JWT"),
    (re.compile(r"(?i)\b(?:api[_\-]?key|apikey|secret|token|password|passwd|bearer|authorization)\b\s*[:=]"),
     "una clave o un token"),
    (re.compile(r"(?i)\b[A-Z][A-Z0-9_]{4,}(?:API[_\-]?KEY|SECRET|TOKEN|PASSWORD)\b"),
     "el nombre de una variable de entorno con una key"),
)

#: el nombre del campo es la senal: "secret", "api_key", "token"...
_NOMBRE_CRED = re.compile(
    r"(?i)^(api[_\-]?key|apikey|secret|secret[_\-]?key|access[_\-]?token|auth[_\-]?token|"
    r"token|password|passwd|pwd|bearer|authorization|credential[s]?)$")

#: valores que NO son una credencial (placeholders de un pack o de un ejemplo)
_PLACEHOLDER = re.compile(r"(?i)^(x{3,}|\.{3,}|<[^>]*>|null|none|todo|changeme|placeholder|"
                          r"your[_\-]?\w*|mi[_\-]?\w*|aqu[ií]|xxx+|\$\{.*\}|%.*%)$")


def credenciales_en(datos, ruta=""):
    """Mensajes con las credenciales que aparecen en un JSON (plan o pack)."""
    hallados = []
    if isinstance(datos, dict):
        for k, v in datos.items():
            donde = f"{ruta}.{k}" if ruta else str(k)
            if isinstance(v, str):
                for pat, que in _PATRONES_CRED:
                    if pat.search(v):
                        hallados.append(f"posible credencial en '{donde}' ({que}): "
                                        f"quitalo — el plan se publica en el repo")
                        break
            else:
                hallados += credenciales_en(v, donde)
            # el NOMBRE del campo tambien delata: una clave llamada "secret"
            # o "api_key" en un plan significa que alguien la pego ahi
            if isinstance(v, str) and v.strip() and not _PLACEHOLDER.search(v):
                if _NOMBRE_CRED.search(str(k)):
                    hallados.append(f"el campo '{donde}' parece una credencial "
                                    f"(nombre de campo sensible): quitalo — el plan "
                                    f"se publica en el repo")
    elif isinstance(datos, list):
        for i, v in enumerate(datos):
            hallados += credenciales_en(v, f"{ruta}[{i}]")
    return hallados



# ───────────────────────── tells de pieza generada ─────────────────────────
# Un «tell» es un recurso que hace que una pieza se lea como generada: casi
# todos fueron buenas ideas hasta que se produjeron por defecto, sin razón.
# El registro fechado vive en references/direccion-de-arte.md; aquí solo lo
# que se puede medir en el plan. Siempre AVISO: la marca o la dirección elegida
# mandan, y una excepción deliberada se declara en plan["tells_ok"].
JERGA = re.compile(
    r"\b(desbloque\w+|revoluciona\w*|de vanguardia|de última generación|sin esfuerzo|sin fisuras|"
    r"todo[- ]en[- ]uno|al siguiente nivel|solución integral|experiencia única|a la velocidad de la luz|"
    r"con un solo clic|unlock\w*|unleash\w*|supercharg\w+|elevate|empower\w*|streamline\w*|seamless\w*|"
    r"effortless\w*|cutting[- ]edge|next[- ]generation|world[- ]class|all[- ]in[- ]one|blazing[- ]fast|"
    r"game[- ]changer|revolutioni[sz]e\w*|next level|best[- ]in[- ]class|enterprise[- ]grade|future[- ]proof|"
    r"industry[- ]leading|mission[- ]critical|de clase mundial|líder (del sector|de la industria))\b", re.I)
CORRECCION = re.compile(
    r"\bno es (solo|sólo|simplemente|únicamente) [^,.;!?]{1,40}[,;.]? (es|sino)\b|"
    r"\bno (es|son) (una?|el|la|los|las) [^,.;!?]{1,40}[.!]\s+(es|son) \w|"
    r"\bnot just [^,.;!?]{1,40}[,;.]? (it'?s|but)\b|\bnot an? [a-z][^.!?]{1,40}[.!]\s+[A-Z]", re.I)
EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF\u2B50]")
# «TODO:» y «XXX» distinguen mayúsculas y forma: «todo» es una palabra española de uso diario
PLACEHOLDER = re.compile(r"lorem ipsum|texto aqu[ií]|tu texto|your text|placeholder|(?-i:\bTODO\s*:)|(?-i:\bXXX+\b)|"
                         r"\[PENDIENTE\]|\[TBD\]", re.I)
NUMERACION = re.compile(r"^\s*((paso|step|fase|phase|etapa)\s*0?\d+\b|0\d\s*[/·.\-–—])", re.I)
PRUEBA = re.compile(r"\b\d[\d.,]*\s?(?:k|m|mil|millones)?\+?\s+(clientes|usuarios|equipos|empresas|marcas|"
                    r"descargas|reseñas|customers|users|teams|companies|downloads|reviews)\b|"
                    r"\bm[aá]s de \d[\d.,]*\s+\w+", re.I)
NO_COPY = {"tipo", "transicion", "transicionX", "transicionY", "lado", "at", "from", "to", "respira", "color"}
TITULARES = ("titulo", "titular", "rotulo")
TITULAR_MAX = 42        # ~32-42 caracteres caben en dos líneas a tamaño de titular (9:16)
REPETIBLES = {"kenburns", "rotulo_inferior"}   # tres fotos o tres rótulos seguidos son normales


def _textos(v, clave=""):
    """Textos de una escena con la clave de su campo (recorre listas y dicts)."""
    if isinstance(v, str):
        yield clave, v
    elif isinstance(v, list):
        for x in v:
            yield from _textos(x, clave)
    elif isinstance(v, dict):
        for k, x in v.items():
            if k not in NO_COPY:
                yield from _textos(x, k)


def auditar_tells(plan, anteriores=None):
    """Tells medibles del plan → [{nivel:'AVISO', t, codigo, msg}] (siempre AVISO).

    `anteriores`: planes de piezas anteriores del mismo proyecto. Sin ellos
    solo se puede medir la variedad DENTRO de la pieza; con ellos, también
    que esta pieza no repita la ruta de la anterior (`ruta-repetida`). El
    CLI lo expone como --anterior (repetible)."""
    if not isinstance(plan, dict) or not isinstance(plan.get("escenas"), list):
        return []
    ok = set(plan.get("tells_ok") or [])
    out = []

    def add(codigo, t, msg):
        if codigo not in ok:
            out.append({"nivel": "AVISO", "t": round(float(t or 0.0), 2), "codigo": codigo, "msg": f"[{codigo}] {msg}"})

    escenas = [(i, e) for i, e in enumerate(plan["escenas"]) if isinstance(e, dict)]
    for i, e in escenas:
        t, tipo = _t_num(e.get("from")) or 0.0, e.get("tipo", "?")
        donde = f"escena {i} ({tipo})"
        vistos = set()
        for clave, txt in _textos({k: v for k, v in e.items() if k not in NO_COPY}):
            limpio = txt.replace("*", "")
            for codigo, rx, que in (
                    ("jerga", JERGA, "vocabulario de marketing de la categoría"),
                    ("correccion", CORRECCION, "la corrección «no es solo X, es Y»"),
                    ("emoji", EMOJI, "emoji o glifo como icono: en video se dibuja con la fuente y sale tofu o inconsistente; usa `icono` (letras) o una forma dibujada"),
                    ("placeholder", PLACEHOLDER, "texto de relleno o pendiente sin resolver")):
                m = rx.search(limpio)
                if m and (codigo, m.group(0)) not in vistos:
                    vistos.add((codigo, m.group(0)))
                    add(codigo, t, f"{donde}: «{m.group(0)}» — {que}")
            if NUMERACION.search(limpio):
                add("numeracion", t, f"{donde}: «{limpio[:24]}» numera por costumbre; el orden lo da la posición o las palabras")
            if PRUEBA.search(limpio) and "fuente" not in e:
                add("prueba-inventada", t, f"{donde}: «{PRUEBA.search(limpio).group(0)}» sin `fuente`: verifica contra el brief o márcalo [PENDIENTE] (cero confabulación)")
            if clave in TITULARES and len(limpio) > TITULAR_MAX:
                add("titular-largo", t, f"{donde}: {clave} de {len(limpio)} caracteres (> {TITULAR_MAX}): el auto-fit lo encoge hasta que deja de ser titular; recorta o pasa el resto a una línea de apoyo")

    # Poco repertorio: la pieza entera con dos o tres tipos de escena (o un
    # tipo en la mitad de las escenas) se lee como la plantilla de siempre,
    # aunque ninguna escena se repita tres veces seguidas. El catalogo tiene
    # 39 tipos y el indice por intencion (references/intencion-escena.md)
    # da la escena por ARGUMENTO: este aviso mide el sintoma, la eleccion
    # sigue siendo del argumento, no de una cuota.
    tipos = [e.get("tipo") for _, e in escenas]
    n_tipos = len(tipos)
    if n_tipos >= 6:
        distintos = sorted(set(tipos))
        dominante, veces = max(((t_, tipos.count(t_)) for t_ in distintos),
                               key=lambda p: p[1], default=(None, 0))
        if len(distintos) <= 3 or veces >= 0.5 * n_tipos:
            fams = REP.familias()
            resumen_fams = "; ".join(f"{k}={'/'.join(v[:3])}…" for k, v in list(fams.items())[:5])
            add("poco-repertorio", 0.0,
                f"solo {len(distintos)} tipos de escena en {n_tipos} escenas "
                f"({', '.join(distintos)}; «{dominante}» x{veces}): la pieza se lee "
                "como la plantilla de siempre. Elige cada escena por su intencion "
                f"(scripts/data/repertorio.json, la fuente única: {resumen_fams}) "
                "— repertorio.py sugerir rota la familia evitando la pieza anterior — "
                "y, entre dos piezas, no repitas el tipo dominante de la anterior si el "
                "argumento no lo pide. Si esta sobriedad es deliberada, decláralo en "
                "\"tells_ok\": [\"poco-repertorio\"]")

    # Ruta repetida ENTRE piezas: el dominante de esta es el de la anterior,
    # o casi todos sus tipos ya salían en ella. Antes esto no lo medía nadie:
    # cada pieza, auditada sola, parecía variada y el proyecto entero era la
    # misma ruta. La familia para rotar sale de repertorio.json (REP), la
    # misma que consume repertorio.py sugerir --anterior.
    if anteriores:
        actuales = set(tipos)
        dom_actual = max(((t_, tipos.count(t_)) for t_ in actuales),
                         key=lambda p: p[1], default=(None, 0))[0]
        for viejo in anteriores:
            tipos_viejos = REP.tipos_de(viejo)
            if not tipos_viejos:
                continue
            dom_viejo = REP.dominante(viejo)
            if dom_actual and dom_actual == dom_viejo:
                add("ruta-repetida", 0.0,
                    f"el tipo dominante de esta pieza («{dom_actual}») ya era el de la "
                    "anterior: entre piezas también se repite la ruta. Rota dentro de "
                    "su familia (scripts/data/repertorio.json) con "
                    "`repertorio.py sugerir --anterior <plan anterior>`, o decláralo en "
                    "\"tells_ok\": [\"ruta-repetida\"] si el argumento lo pide")
                break
            viejos = set(tipos_viejos)
            if actuales and len(actuales & viejos) >= 0.8 * len(actuales):
                add("ruta-repetida", 0.0,
                    f"{len(actuales & viejos)} de {len(actuales)} tipos de esta pieza ya "
                    "salían en la anterior: la ruta es casi la misma aunque el dominante "
                    "cambie. Pide otra mano con `repertorio.py sugerir --anterior "
                    "<plan anterior>` o decláralo en \"tells_ok\": [\"ruta-repetida\"]")
                break

    # Intenciones declaradas: si el plan declara qué intenciones persigue
    # ("intenciones") o qué descarta ("no_aplica"), se verifica contra la
    # fuente única. Sin ninguna de las dos claves, plan heredado: no se
    # inventa un aviso que el plan nunca prometió.
    if "intenciones" in plan or "no_aplica" in plan:
        fams = REP.familias()
        cubiertas = {i for t in set(tipos) for i in REP.intencion_de(t)}
        declaradas = [i for i in (plan.get("intenciones") or [])]
        no_aplica = plan.get("no_aplica") or {}
        for inten in declaradas:
            if inten not in fams:
                add("intencion-sin-escena", 0.0,
                    f"la intención «{inten}» no existe en scripts/data/repertorio.json "
                    f"(válidas: {', '.join(fams)}): corrige el nombre, no la escena")
            elif inten not in cubiertas:
                add("intencion-sin-escena", 0.0,
                    f"la intención declarada «{inten}» no la cubre ninguna escena: "
                    f"su familia es {'/'.join(fams[inten])} — elige una por el "
                    "argumento o mueve la intención a \"no_aplica\" con su porqué")
        olvidadas = [i for i in fams
                     if i not in cubiertas and i not in declaradas and i not in no_aplica]
        if olvidadas:
            add("intencion-olvidada", 0.0,
                f"intenciones ni usadas ni declaradas: {', '.join(olvidadas)}: lo no "
                "usado queda explícito, no olvidado — cubre la que el argumento pida "
                "o declara en el plan \"no_aplica\": {\"<intencion>\": \"<por qué>\"} "
                "(repertorio.py cobertura las lista con su familia)")
    n = len(escenas)
    if n >= 5 and sum(1 for _, e in escenas if e.get("rotulo")) >= 0.8 * n:
        add("rotulo-en-todas", 0.0, f"{sum(1 for _, e in escenas if e.get('rotulo'))} de {n} escenas llevan rótulo (kicker): es el reflejo de plantilla; resérvalo a donde aporta (si es la firma deliberada de la dirección, decláralo en tells_ok)")
    ordenadas = sorted(escenas, key=lambda p: _t_num(p[1].get("from")) or 0.0)
    racha = 1
    for k in range(1, len(ordenadas)):
        tipo = ordenadas[k][1].get("tipo")
        racha = racha + 1 if tipo == ordenadas[k - 1][1].get("tipo") and tipo not in REPETIBLES else 1
        if racha == 3:
            add("escena-repetida", _t_num(ordenadas[k][1].get("from")) or 0.0,
                f"tres escenas `{tipo}` seguidas (hasta la {ordenadas[k][0]}): la plantilla se nota; alterna la familia de composición")
    durs = [_t_num(e.get("to")) - _t_num(e.get("from")) for _, e in ordenadas
            if _t_num(e.get("from")) is not None and _t_num(e.get("to")) is not None]
    durs = [d for d in durs if d > 0]
    if len(durs) >= 5 and statistics.mean(durs) > 0:
        cv = statistics.pstdev(durs) / statistics.mean(durs)
        if cv < CV_MIN_CADENCIA:
            con_voz = sum(1 for _, e in ordenadas
                          if isinstance(e.get("voz"), str) and e["voz"].strip())
            if con_voz >= 0.8 * len(durs):
                # La duracion la manda la voz (cada escena = su frase): no es
                # un metronomo elegido, es el reloj de la narracion. Se
                # DECLARA la excepcion, no se ignora en silencio (ritmo.md).
                add("cadencia-uniforme", 0.0,
                    f"las {len(durs)} escenas duran casi lo mismo (CV {cv:.2f} < {CV_MIN_CADENCIA}), "
                    f"pero {con_voz} llevan voz: la duracion la manda la narracion (cada escena = su "
                    "frase). Si es deliberado, decláralo en el plan con \"tells_ok\": "
                    "[\"cadencia-uniforme\"] y anota el porqué en el proyecto; si no, adelgaza el "
                    "texto de las escenas largas y reparte el aire (ritmo.md)")
            else:
                add("cadencia-uniforme", 0.0, f"las {len(durs)} escenas duran casi lo mismo (CV {cv:.2f} < {CV_MIN_CADENCIA}): se lee como metrónomo (ritmo.md); varía las duraciones o decláralo en \"tells_ok\": [\"cadencia-uniforme\"] si es deliberado")
    return out

def _aviso_caption_central(plan, caption_position):
    """AVISO si el pack pide subtitulos en el centro y el plan quema
    subtitulos sobre escenas del motor: las escenas componen su texto en
    el centro, asi que el karaoke central se pisa con cada plano (medido:
    ningun frame con caption era legible del todo).
    La banda del motor es la inferior reservada; caption.py --plan la usa.
    Puro: recibe la posicion ya leida del pack."""
    if not isinstance(plan, dict) or not plan.get("subtitulos"):
        return None
    if str(caption_position or "").strip().lower() != "center":
        return None
    return {"nivel": "AVISO", "t": 0.0,
            "msg": "el brand pack pide caption en el centro (position=center) y el plan "
                   "quema subtitulos sobre escenas del motor, que componen en el centro: "
                   "el karaoke pisara cada escena. Quema con caption.py --plan "
                   "(banda inferior reservada) o cambia el caption del pack a bottom"}


def main():
    ap = argparse.ArgumentParser(
        description="Audita un plan.json: solapes, duraciones, escenas vacías, voz vacía, orden temporal y tells de pieza generada.")
    ap.add_argument("plan", help="plan.json a auditar")
    ap.add_argument("--json", action="store_true", help="salida en JSON")
    ap.add_argument("--tol", type=float, default=0.05,
                    help="tolerancia en segundos para solapes (default: 0.05)")
    ap.add_argument("--min-final", type=float, default=2.0,
                    help="duración mínima de la escena final (default: 2.0s)")
    ap.add_argument("--sin-tells", action="store_true",
                    help="no busca «tells» de pieza generada (jerga, emoji, repeticiones...)")
    ap.add_argument("--anterior", action="append", default=[], metavar="PLAN",
                    help="plan.json de la pieza anterior del proyecto (repetible): "
                         "activa el tell ruta-repetida entre piezas")
    a = ap.parse_args()

    if not os.path.isfile(a.plan):
        msg = f"ERROR: no existe el archivo de plan: {a.plan}"
        if a.json:
            print(json.dumps({"errores": 1, "hallazgos": [{"nivel": "ERROR", "t": 0.0, "msg": msg}]},
                             ensure_ascii=False, indent=1))
            sys.exit(1)
        sys.exit(msg)
    try:
        with open(a.plan, encoding="utf-8") as fh:
            plan = json.load(fh)
    except (OSError, ValueError) as ex:
        msg = f"ERROR: JSON inválido en {a.plan}: {ex}"
        if a.json:
            print(json.dumps({"errores": 1, "hallazgos": [{"nivel": "ERROR", "t": 0.0, "msg": msg}]},
                             ensure_ascii=False, indent=1))
            sys.exit(1)
        sys.exit(msg)

    hallazgos = auditar_estructura(plan, tol=a.tol, min_final=a.min_final)
    if isinstance(plan, dict) and isinstance(plan.get("brand"), str):
        ruta_brand = plan["brand"]
        if not os.path.isabs(ruta_brand):
            ruta_brand = os.path.join(os.path.dirname(os.path.abspath(a.plan)), ruta_brand)
        try:
            with open(ruta_brand, encoding="utf-8") as fh:
                pack = json.load(fh)
            aviso = _aviso_caption_central(plan, (pack.get("caption") or {}).get("position"))
            if aviso:
                hallazgos.append(aviso)
        except (OSError, ValueError):
            pass   # un pack ilegible lo reporta el render; aqui no se inventa
    if not a.sin_tells:
        anteriores = []
        for ruta in a.anterior:
            try:
                with open(ruta, encoding="utf-8") as fh:
                    anteriores.append(json.load(fh))
            except (OSError, ValueError) as ex:
                sys.exit(f"ERROR: no pude leer el plan anterior {ruta}: {ex}")
        hallazgos += auditar_tells(plan, anteriores=anteriores)
    escenas = plan.get("escenas", []) if isinstance(plan, dict) and isinstance(plan.get("escenas"), list) else []
    errores = sum(1 for h in hallazgos if h["nivel"] == "ERROR")
    if a.json:
        print(json.dumps({"errores": errores, "hallazgos": hallazgos},
                         ensure_ascii=False, indent=1))
    else:
        if not hallazgos:
            # el string importa: el SKILL.md promete "PLAN VALIDO" y el agente
            # busca esa palabra para saber que el plan esta listo
            print(f"OK · PLAN VALIDO: {len(escenas)} escenas auditadas")
        else:
            print(f"{errores} error(es), {len(hallazgos)-errores} aviso(s) "
                  f"en {len(escenas)} escenas:")
            for h in sorted(hallazgos, key=lambda x: x["t"]):
                print(f"[{h['nivel']}] t={h['t']:.2f}s — {h['msg']}")
    sys.exit(1 if errores else 0)


if __name__ == "__main__":
    main()
