#!/usr/bin/env python3
"""Repertorio: la ÚNICA superficie de elección del agente.

Flujo: brief → sugerir del catálogo único → producir según el motor
interno de la opción. El agente NO elige entre «catálogo A vs B»:
escenas del plan, overlays talking-head y gestos de interfaz son la
misma familia por intención. El motor (plan / efecto CVE / gesto UI /
HyperFrames / Remotion / grade…) es metadato de producción, no un menú.

Fuentes de detalle (DRY, no menús paralelos):
  scripts/data/repertorio.json          intención → escenas (SCENES)
  scripts/data/efectos_talking_head.json overlays (motor efecto)
  scripts/data/motion_ui.json            gestos de interfaz (motor gesto)

  listar     intenciones y opciones (escena+efecto+gesto); --todo añade
             paletas/direcciones/tonos/SFX derivados de SU fuente
  sugerir    --intenciones: una opción por intención (por defecto rota
             escenas del plan; con --pedido puntúa toda la familia;
             --completo rota también efectos/gestos)
             --pedido solo: top-N del catálogo entero (sustituye el
             sugerir paralelo de efectos_talking_head)
  resolver   id → motor + cómo producir (receta / escena / gesto)
  cobertura  qué usa un plan, intenciones sin tocar / no_aplica
  validar    escenas huérfanas/fantasmas + efectos/gestos alcanzables

auditar_plan.py y clonar_video.py consumen las familias de ESCENAS;
nadie copia la relación a mano.

Uso:
  python3 scripts/repertorio.py listar [--todo] [--json]
  python3 scripts/repertorio.py sugerir --intenciones gancho,dato,cierre [--pedido "..."] [--anterior plan.json] [--semilla 1] [--json]
  python3 scripts/repertorio.py sugerir --pedido "reels orbitando mi cara" [--json]
  python3 scripts/repertorio.py resolver --id orbit [--json]
  python3 scripts/repertorio.py cobertura plan.json [--json]
  python3 scripts/repertorio.py validar [--json]
"""
import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter

BASE = os.path.dirname(os.path.abspath(__file__))
DATOS = os.path.join(BASE, "data", "repertorio.json")
DATOS_EFECTOS = os.path.join(BASE, "data", "efectos_talking_head.json")
DATOS_GESTOS = os.path.join(BASE, "data", "motion_ui.json")

# Motores internos (metadato). El agente no los elige como menú.
MOTOR_ESCENA = "escena"       # render_plan.SCENES
MOTOR_EFECTO = "efecto"       # CVE en /tmp vía efectos_talking_head.receta
MOTOR_GESTO = "gesto"         # motion UI sobre escena u otro motor
MOTOR_NATIVO = "nativo"       # grade/hand_draw/… cuando el fx lo declara


def cargar(ruta=DATOS):
    with open(ruta, encoding="utf-8") as fh:
        return json.load(fh)


def _cargar_efectos():
    with open(DATOS_EFECTOS, encoding="utf-8") as fh:
        return json.load(fh)


def _cargar_gestos():
    with open(DATOS_GESTOS, encoding="utf-8") as fh:
        return json.load(fh)


def catalogo():
    """Los tipos salen del dict SCENES de render_plan.py (fuente única)."""
    with open(os.path.join(BASE, "render_plan.py"), encoding="utf-8") as fh:
        src = fh.read()
    bloque = re.search(r"^SCENES\s*=\s*\{(.*?)\}\s*$", src, re.S | re.M).group(1)
    return set(re.findall(r'"(\w+)"\s*:\s*sc_', bloque))


def familias(datos=None):
    """{intencion: [escenas]} — subset del plan; compat con auditar/clonar."""
    datos = datos or cargar()
    return {i["id"]: list(i["escenas"]) for i in datos["intenciones"]}


def intencion_de(tipo, datos=None):
    """A qué intenciones sirve una escena (puede ser más de una)."""
    return [k for k, v in familias(datos).items() if tipo in v]


def _opciones_efecto(efectos=None):
    """id → fila efecto (con intenciones)."""
    efectos = efectos if efectos is not None else _cargar_efectos()
    return {e["id"]: e for e in efectos.get("efectos", [])}


def _opciones_gesto(gestos=None):
    gestos = gestos if gestos is not None else _cargar_gestos()
    return {t["id"]: t for t in gestos.get("tecnicas", [])}


def opciones(intencion, datos=None, efectos=None, gestos=None):
    """Lista unificada de opciones para una intención (orden: escena→efecto→gesto).

    Cada fila: {id, motor, firma?, producir?} — motor es metadato interno.
    """
    datos = datos or cargar()
    fams = familias(datos)
    if intencion not in fams:
        raise ValueError(f"intención desconocida: {intencion} "
                         f"(válidas: {', '.join(fams)})")
    out = []
    for e in fams[intencion]:
        out.append({
            "id": e,
            "motor": MOTOR_ESCENA,
            "intencion": intencion,
            "firma": f"escena del plan `{e}`",
            "producir": f"plan.json tipo={e} · references/escenas.md",
        })
    for eid, fila in _opciones_efecto(efectos).items():
        if intencion not in (fila.get("intenciones") or []):
            continue
        preferir = fila.get("preferir", "externo")
        motor = MOTOR_NATIVO if preferir == "nativo" else MOTOR_EFECTO
        out.append({
            "id": eid,
            "motor": motor,
            "intencion": intencion,
            "firma": fila.get("firma", ""),
            "preferir": preferir,
            "nativo": fila.get("nativo"),
            "producir": (
                fila.get("nativo") if preferir == "nativo"
                else f"python scripts/efectos_talking_head.py receta --fx {eid}"
            ),
            "aliases": fila.get("aliases", []),
            "keywords": fila.get("keywords", []),
            "ocasion": fila.get("ocasion", ""),
        })
    for gid, fila in _opciones_gesto(gestos).items():
        if intencion not in (fila.get("intenciones") or []):
            continue
        motor_prod = fila.get("motor", "plan")
        out.append({
            "id": gid,
            "motor": MOTOR_GESTO,
            "intencion": intencion,
            "firma": fila.get("firma", ""),
            "motor_produccion": motor_prod,
            "motores_alt": fila.get("motores_alt", []),
            "producir": fila.get("adaptar", f"gesto `{gid}` sobre la escena elegida"),
            "aliases": fila.get("aliases", []),
            "keywords": fila.get("keywords", []),
            "empleo": fila.get("empleo", []),
        })
    return out


def familias_opciones(datos=None, efectos=None, gestos=None):
    """{intencion: [ids de opción]} — catálogo único por intención."""
    datos = datos or cargar()
    efectos = efectos if efectos is not None else _cargar_efectos()
    gestos = gestos if gestos is not None else _cargar_gestos()
    return {
        i["id"]: [o["id"] for o in opciones(i["id"], datos, efectos, gestos)]
        for i in datos["intenciones"]
    }


def catalogo_opciones(datos=None, efectos=None, gestos=None):
    """Todas las opciones indexadas por id (primera ocurrencia gana el detalle)."""
    datos = datos or cargar()
    efectos = efectos if efectos is not None else _cargar_efectos()
    gestos = gestos if gestos is not None else _cargar_gestos()
    out = {}
    for i in datos["intenciones"]:
        for o in opciones(i["id"], datos, efectos, gestos):
            if o["id"] not in out:
                out[o["id"]] = o
            else:
                # pertenencia múltiple: acumula intenciones
                prev = out[o["id"]]
                ints = prev.setdefault("intenciones", [prev.get("intencion")])
                if o["intencion"] not in ints:
                    ints.append(o["intencion"])
    return out


def resolver(nombre, datos=None, efectos=None, gestos=None):
    """Normaliza nombre/alias → opción del catálogo único (o None)."""
    datos = datos or cargar()
    efectos = efectos if efectos is not None else _cargar_efectos()
    gestos = gestos if gestos is not None else _cargar_gestos()
    clave = (nombre or "").strip().lower().replace("_", "-")
    if not clave:
        return None
    # escenas: ids del motor (pueden ser camelCase: orbOpen)
    tipos = catalogo()
    if nombre in tipos:
        ints = intencion_de(nombre, datos)
        return {
            "id": nombre,
            "motor": MOTOR_ESCENA,
            "intenciones": ints,
            "firma": f"escena del plan `{nombre}`",
            "producir": f"plan.json tipo={nombre} · references/escenas.md",
        }
    # efectos + looks + aliases
    for e in efectos.get("efectos", []):
        ids = {e["id"]} | {a.lower() for a in e.get("aliases", [])}
        if clave in ids or clave == e["id"]:
            preferir = e.get("preferir", "externo")
            return {
                "id": e["id"],
                "motor": MOTOR_NATIVO if preferir == "nativo" else MOTOR_EFECTO,
                "intenciones": e.get("intenciones", []),
                "firma": e.get("firma", ""),
                "preferir": preferir,
                "nativo": e.get("nativo"),
                "producir": (
                    e.get("nativo") if preferir == "nativo"
                    else f"python scripts/efectos_talking_head.py receta --fx {e['id']}"
                ),
                "ocasion": e.get("ocasion", ""),
            }
    for look in efectos.get("looks_nombrados", []):
        if clave == look["id"]:
            base = resolver(look["de"], datos, efectos, gestos)
            if base:
                base = dict(base)
                base["look"] = look.get("look")
                base["firma"] = look.get("firma", base.get("firma"))
            return base
    for t in gestos.get("tecnicas", []):
        ids = {t["id"]} | {a.lower().replace("_", "-") for a in t.get("aliases", [])}
        if clave in ids:
            return {
                "id": t["id"],
                "motor": MOTOR_GESTO,
                "intenciones": t.get("intenciones", []),
                "firma": t.get("firma", ""),
                "motor_produccion": t.get("motor", "plan"),
                "motores_alt": t.get("motores_alt", []),
                "producir": t.get("adaptar", ""),
                "empleo": t.get("empleo", []),
            }
    return None


def _score_opcion(texto, tokens, op):
    """Puntúa una opción contra un pedido en prosa."""
    score = 0
    oid = op["id"]
    oid_sp = oid.replace("-", " ")
    if oid in texto or oid_sp in texto:
        score += 50
    for a in op.get("aliases") or []:
        if a in texto or a.replace("-", " ") in texto:
            score += 40
    blob = " ".join([
        op.get("firma", ""),
        op.get("ocasion", ""),
        op.get("producir", "") if isinstance(op.get("producir"), str) else "",
        " ".join(op.get("keywords") or []),
        " ".join(op.get("empleo") or []),
        " ".join(op.get("intenciones") or ([op.get("intencion")] if op.get("intencion") else [])),
    ]).lower()
    for t in tokens:
        if len(t) < 3:
            continue
        if t in oid or t in blob:
            score += 3
        for kw in op.get("keywords") or []:
            if t in kw.lower():
                score += 5
    return score


def sugerir_pedido(pedido, datos=None, efectos=None, gestos=None, limite=5,
                   intencion=None):
    """Top-N del catálogo único emparejando el pedido (sustituye el CLI paralelo)."""
    datos = datos or cargar()
    efectos = efectos if efectos is not None else _cargar_efectos()
    gestos = gestos if gestos is not None else _cargar_gestos()
    texto = (pedido or "").strip().lower()
    if not texto:
        return []
    tokens = set(re.findall(r"[a-z0-9áéíóúñü+-]+", texto, re.I))
    candidatas = []
    if intencion:
        candidatas = opciones(intencion, datos, efectos, gestos)
    else:
        seen = set()
        for i in datos["intenciones"]:
            for o in opciones(i["id"], datos, efectos, gestos):
                key = (o["id"], o["motor"])
                if key in seen:
                    continue
                seen.add(key)
                candidatas.append(o)
    scored = []
    for o in candidatas:
        s = _score_opcion(texto, tokens, o)
        if s:
            scored.append((s, o))
    scored.sort(key=lambda x: (-x[0], x[1]["id"]))
    return [o for _, o in scored[:limite]]


def validar(datos=None, tipos=None, efectos=None, gestos=None):
    """Problemas del repertorio unificado (lista vacía = sano)."""
    datos = datos or cargar()
    efectos = efectos if efectos is not None else _cargar_efectos()
    gestos = gestos if gestos is not None else _cargar_gestos()
    tipos = catalogo() if tipos is None else set(tipos)
    malos, cubiertas = [], set()
    ids = set()
    for i in datos.get("intenciones", []):
        if i["id"] in ids:
            malos.append(f"intención repetida: {i['id']}")
        ids.add(i["id"])
        if not i.get("escenas"):
            malos.append(f"{i['id']}: familia vacía")
        for e in i.get("escenas", []):
            if e not in tipos:
                malos.append(f"{i['id']}: '{e}' no es una escena del motor")
            cubiertas.add(e)
    for h in sorted(tipos - cubiertas):
        malos.append(f"'{h}' está en el motor pero en ninguna intención: "
                     "es inalcanzable desde el flujo normal; añádela a una familia")
    for rol, inten in datos.get("roles_clonar", {}).items():
        if inten not in ids:
            malos.append(f"roles_clonar.{rol}: intención desconocida '{inten}'")

    # efectos: cada uno declara intenciones válidas; todos alcanzables
    fx_ids = set()
    for e in efectos.get("efectos", []):
        eid = e.get("id")
        if not eid:
            malos.append("efecto sin id")
            continue
        if eid in fx_ids:
            malos.append(f"efecto repetido: {eid}")
        fx_ids.add(eid)
        ints = e.get("intenciones") or []
        if not ints:
            malos.append(f"efecto '{eid}': sin intenciones (inalcanzable "
                         "desde el catálogo único)")
        for inten in ints:
            if inten not in ids:
                malos.append(f"efecto '{eid}': intención desconocida '{inten}'")
    if efectos.get("conteo") and len(fx_ids) != int(efectos["conteo"]):
        malos.append(f"efectos: conteo={efectos.get('conteo')} pero hay {len(fx_ids)}")

    # gestos: igual
    g_ids = set()
    for t in gestos.get("tecnicas", []):
        gid = t.get("id")
        if not gid:
            malos.append("gesto sin id")
            continue
        if gid in g_ids:
            malos.append(f"gesto repetido: {gid}")
        g_ids.add(gid)
        ints = t.get("intenciones") or []
        if not ints:
            malos.append(f"gesto '{gid}': sin intenciones")
        for inten in ints:
            if inten not in ids:
                malos.append(f"gesto '{gid}': intención desconocida '{inten}'")
    if gestos.get("conteo") and len(g_ids) != int(gestos["conteo"]):
        malos.append(f"gestos: conteo={gestos.get('conteo')} pero hay {len(g_ids)}")

    # colisiones de id entre capas (rompería resolver)
    choque = (tipos & fx_ids) | (tipos & g_ids) | (fx_ids & g_ids)
    for c in sorted(choque):
        malos.append(f"id '{c}' choca entre capas del catálogo único "
                     "(escena/efecto/gesto deben ser disjuntos)")

    return malos


def _rotar(lista, semilla, clave):
    """Rota la familia de forma determinista según (semilla, clave)."""
    if not lista:
        return []
    h = int(hashlib.sha256(f"{semilla}:{clave}".encode()).hexdigest()[:8], 16)
    k = h % len(lista)
    return lista[k:] + lista[:k]


def elegir(intenciones, evitar=(), semilla=0, datos=None, completo=False,
           pedido=None, efectos=None, gestos=None):
    """Una opción por intención.

    Por defecto rota solo escenas del plan (compat con auditar/clonar y
    con el flujo plan.json). Con completo=True incluye efectos y gestos.
    Con pedido, puntúa la familia unificada y elige la mejor disponible.

    Devuelve [{intencion, opcion, escena, motor, reutilizada, producir}].
    `escena` se rellena cuando motor=escena (alias de opcion) para no
    romper consumidores que leen la clave antigua.
    """
    datos = datos or cargar()
    efectos = efectos if efectos is not None else _cargar_efectos()
    gestos = gestos if gestos is not None else _cargar_gestos()
    fams = familias(datos)
    evitar, elegidas, mano = set(evitar), set(), []
    for inten in intenciones:
        if inten not in fams:
            raise ValueError(f"intención desconocida: {inten} "
                             f"(válidas: {', '.join(fams)})")
        pool = opciones(inten, datos, efectos, gestos) if (completo or pedido) \
            else [{"id": e, "motor": MOTOR_ESCENA,
                   "producir": f"plan.json tipo={e} · references/escenas.md"}
                  for e in fams[inten]]
        if pedido:
            texto = pedido.strip().lower()
            tokens = set(re.findall(r"[a-z0-9áéíóúñü+-]+", texto, re.I))
            ranked = sorted(
                ((_score_opcion(texto, tokens, o), o) for o in pool),
                key=lambda x: (-x[0], x[1]["id"]),
            )
            # si nada puntúa, cae a rotación
            if ranked and ranked[0][0] > 0:
                orden_ids = [o["id"] for _, o in ranked]
            else:
                orden_ids = _rotar([o["id"] for o in pool], semilla, inten)
        else:
            orden_ids = _rotar([o["id"] for o in pool], semilla, inten)
        por_id = {o["id"]: o for o in pool}
        libre = [i for i in orden_ids if i not in evitar and i not in elegidas]
        oid = libre[0] if libre else orden_ids[0]
        meta = por_id[oid]
        fila = {
            "intencion": inten,
            "opcion": oid,
            "escena": oid if meta.get("motor") == MOTOR_ESCENA else None,
            "motor": meta.get("motor", MOTOR_ESCENA),
            "producir": meta.get("producir"),
            "reutilizada": not libre,
        }
        # compat: consumidores antiguos leen solo 'escena'
        if fila["escena"] is None and not completo and not pedido:
            fila["escena"] = oid
        elif fila["escena"] is None and meta.get("motor") == MOTOR_ESCENA:
            fila["escena"] = oid
        # si solo hay escenas en el pool (default), escena siempre = opcion
        if all(o.get("motor") == MOTOR_ESCENA for o in pool):
            fila["escena"] = oid
        mano.append(fila)
        elegidas.add(oid)
    return mano


def tipos_de(plan):
    return [e.get("tipo") for e in plan.get("escenas", []) if isinstance(e, dict)]


def dominante(plan):
    tipos = tipos_de(plan)
    return Counter(tipos).most_common(1)[0][0] if tipos else None


def resumen(planes, datos=None):
    """Cobertura conjunta de uno o más planes contra el catálogo de escenas."""
    fams = familias(datos)
    usados = Counter()
    for p in planes:
        usados.update(t for t in tipos_de(p) if t)
    cubiertas = {i for t in usados for i in intencion_de(t, datos)}
    no_aplica = {}
    for p in planes:
        for k, v in (p.get("no_aplica") or {}).items():
            no_aplica[k] = v
    return {
        "tipos_usados": dict(usados),
        "n_tipos": len(usados),
        "n_catalogo": len(catalogo()),
        "pct_catalogo": round(100.0 * len(usados) / max(1, len(catalogo())), 1),
        "intenciones_cubiertas": sorted(cubiertas),
        "intenciones_sin_tocar": [
            {"id": i, "declarada_no_aplica": i in no_aplica,
             "motivo": no_aplica.get(i),
             "familia": fams[i]}
            for i in fams if i not in cubiertas],
        "escenas_sin_usar": sorted(catalogo() - set(usados)),
    }


#: La tabla §2b de intencion-escena.md se DERIVA de repertorio.json.
#: Marcadores estables para que actualizar_conteos.py la reescriba y
#: auditar_mapa.py falle si alguien la edita a mano y se desfase.
MARCA_TABLA_INI = "<!-- REPERTORIO_TABLA_INI -->"
MARCA_TABLA_FIN = "<!-- REPERTORIO_TABLA_FIN -->"


def tabla_markdown(datos=None):
    """La tabla §2b: escenas del plan por intención (subset; el catálogo
    completo se lista con `repertorio.py listar`)."""
    datos = datos or cargar()
    lineas = [
        "| intencion | familia (rota segun el argumento y la pieza anterior) |",
        "|---|---|",
    ]
    for i in datos["intenciones"]:
        fam = ", ".join(f"`{e}`" for e in i["escenas"])
        lineas.append(f"| {i['id']} | {fam} |")
    return "\n".join(lineas) + "\n"


def parsear_tabla_prosa(texto):
    """{id: [escenas]} de la tabla marcada en intencion-escena.md, o {}."""
    if MARCA_TABLA_INI not in texto or MARCA_TABLA_FIN not in texto:
        return {}
    bloque = texto.split(MARCA_TABLA_INI, 1)[1].split(MARCA_TABLA_FIN, 1)[0]
    out = {}
    for fila in bloque.splitlines():
        fila = fila.strip()
        if not fila.startswith("|"):
            continue
        celdas = [c.strip() for c in fila.strip("|").split("|")]
        if len(celdas) < 2:
            continue
        inten, fam = celdas[0], celdas[1]
        if inten.startswith("-") or inten.lower().startswith("intencion"):
            continue
        inten = inten.split("/", 1)[0].strip()
        escenas = re.findall(r"`([^`]+)`", fam)
        if inten and escenas:
            out[inten] = escenas
    return out


def diff_tabla_prosa(texto, datos=None):
    """Problemas si la prosa §2b no coincide con repertorio.json."""
    datos = datos or cargar()
    esperada = {i["id"]: list(i["escenas"]) for i in datos["intenciones"]}
    if MARCA_TABLA_INI not in texto or MARCA_TABLA_FIN not in texto:
        return ["references/intencion-escena.md: faltan los marcadores "
                f"{MARCA_TABLA_INI} / {MARCA_TABLA_FIN} alrededor de la tabla §2b"]
    hallada = parsear_tabla_prosa(texto)
    malos = []
    for k in sorted(set(esperada) - set(hallada)):
        malos.append(f"tabla §2b: falta la intención '{k}' "
                     f"(familia: {', '.join(esperada[k])})")
    for k in sorted(set(hallada) - set(esperada)):
        malos.append(f"tabla §2b: intención '{k}' no está en repertorio.json "
                     f"(¿fantasma? cabecera es global del plan, no escena)")
    for k in sorted(set(esperada) & set(hallada)):
        if hallada[k] != esperada[k]:
            malos.append(
                f"tabla §2b '{k}': prosa={hallada[k]} json={esperada[k]}")
    return malos


def reescribir_tabla_prosa(texto, datos=None):
    """Sustituye el bloque marcado por la tabla derivada del JSON."""
    if MARCA_TABLA_INI not in texto or MARCA_TABLA_FIN not in texto:
        return texto
    tabla = tabla_markdown(datos)
    pre, resto = texto.split(MARCA_TABLA_INI, 1)
    _, post = resto.split(MARCA_TABLA_FIN, 1)
    return pre + MARCA_TABLA_INI + "\n" + tabla + MARCA_TABLA_FIN + post


def _leer_plan(ruta):
    with open(ruta, encoding="utf-8") as fh:
        return json.load(fh)


def _otras_dimensiones():
    """El resto del repertorio, DERIVADO de su fuente (nada copiado aquí)."""
    out = {}
    try:
        sys.path.insert(0, os.path.join(BASE, "ffmpeg_tools"))
        from _comun import PALETAS
        out["paletas (ffmpeg_tools/_comun.PALETAS)"] = sorted(PALETAS)
    except Exception as ex:
        out["paletas"] = f"no derivable: {ex}"
    try:
        with open(os.path.join(BASE, "data", "direcciones.json"), encoding="utf-8") as fh:
            d = json.load(fh)
        out["direcciones (data/direcciones.json)"] = [x["id"] for x in d["direcciones"]]
        out["sectores (data/direcciones.json)"] = sorted(d["sectores"])
    except Exception as ex:
        out["direcciones"] = f"no derivable: {ex}"
    try:
        import direccion_arte as DA
        out["tonos (direccion_arte.TONOS)"] = list(DA.TONOS)
        out["modos (direccion_arte.MODOS)"] = list(DA.MODOS)
    except Exception as ex:
        out["tonos/modos"] = f"no derivable: {ex}"
    try:
        import sfx as SFX
        out["sfx (sfx.GENERADORES)"] = sorted(SFX.GENERADORES)
    except Exception as ex:
        out["sfx"] = f"no derivable: {ex}"
    return out


def _resumen_conteos(datos=None, efectos=None, gestos=None):
    datos = datos or cargar()
    efectos = efectos if efectos is not None else _cargar_efectos()
    gestos = gestos if gestos is not None else _cargar_gestos()
    n_esc = len(catalogo())
    n_fx = len(efectos.get("efectos", []))
    n_g = len(gestos.get("tecnicas", []))
    return {
        "n_escenas": n_esc,
        "n_efectos": n_fx,
        "n_gestos": n_g,
        "n_opciones": n_esc + n_fx + n_g,
        "n_intenciones": len(datos.get("intenciones", [])),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    # El texto de las opciones se dice UNA vez: --json aparece en cinco
    # subcomandos y la puerta exige que toda opcion se explique en --help.
    ayuda_json = "salida en JSON, para leerla desde otra herramienta"

    p = sub.add_parser("listar", help="catálogo único por intención (escena+efecto+gesto)")
    p.add_argument("--todo", action="store_true",
                   help="añade paletas, direcciones, tonos, modos y SFX")
    p.add_argument("--solo-escenas", action="store_true",
                   help="solo el subset del motor de planes (compat)")
    p.add_argument("--json", action="store_true", help=ayuda_json)

    p = sub.add_parser("sugerir", help="elige del catálogo único")
    p.add_argument("--intenciones", default="",
                   help="lista separada por comas; si se omite, hace falta --pedido")
    p.add_argument("--pedido", default="",
                   help="prosa del brief: puntúa opciones; solo, top-N del catálogo")
    p.add_argument("--limite", type=int, default=5, help="top-N con --pedido sin intenciones")
    p.add_argument("--completo", action="store_true",
                   help="con --intenciones, rota también efectos y gestos (no solo escenas)")
    p.add_argument("--anterior", action="append", default=[],
                   help="plan.json de una pieza anterior; se repite y sus tipos se evitan")
    p.add_argument("--evitar", default="",
                   help="ids de tipos que no deben salir, separados por comas")
    p.add_argument("--semilla", type=int, default=0,
                   help="semilla de la rotación: la misma semilla da la misma mano")
    p.add_argument("--json", action="store_true", help=ayuda_json)

    p = sub.add_parser("resolver", help="id/alias → motor interno y cómo producir")
    p.add_argument("--id", required=True, help="apertura | orbit | offset-delay | …")
    p.add_argument("--json", action="store_true", help=ayuda_json)

    p = sub.add_parser("cobertura", help="cobertura de un plan contra escenas + no_aplica")
    p.add_argument("planes", nargs="+",
                   help="uno o mas plan.json contra los que medir la cobertura")
    p.add_argument("--json", action="store_true", help=ayuda_json)

    p = sub.add_parser("validar", help="integridad del catálogo único")
    p.add_argument("--json", action="store_true", help=ayuda_json)

    a = ap.parse_args()

    if a.cmd == "validar":
        malos = validar()
        counts = _resumen_conteos()
        if a.json:
            print(json.dumps({"problemas": malos, **counts}, ensure_ascii=False, indent=1))
        elif malos:
            print("REPERTORIO CON PROBLEMAS:")
            for m in malos:
                print(f"  - {m}")
        else:
            print(
                f"REPERTORIO VALIDO: {counts['n_opciones']} opciones "
                f"({counts['n_escenas']} escenas + {counts['n_efectos']} efectos + "
                f"{counts['n_gestos']} gestos) en {counts['n_intenciones']} intenciones "
                f"— una sola superficie de elección"
            )
        return 1 if malos else 0

    if a.cmd == "listar":
        datos = cargar()
        efectos, gestos = _cargar_efectos(), _cargar_gestos()
        counts = _resumen_conteos(datos, efectos, gestos)
        if a.solo_escenas:
            fams = familias(datos)
            salida = {"intenciones": fams, **counts}
        else:
            salida = {
                "intenciones": {
                    i["id"]: opciones(i["id"], datos, efectos, gestos)
                    for i in datos["intenciones"]
                },
                **counts,
            }
        if a.todo:
            salida["otras_dimensiones"] = _otras_dimensiones()
        if a.json:
            print(json.dumps(salida, ensure_ascii=False, indent=1))
        else:
            for inten, filas in salida["intenciones"].items():
                if a.solo_escenas:
                    print(f"{inten}: {', '.join(filas)}")
                else:
                    bits = [f"{o['id']}[{o['motor']}]" for o in filas]
                    print(f"{inten}: {', '.join(bits)}")
            print(
                f"catálogo único: {counts['n_opciones']} opciones "
                f"({counts['n_escenas']} escenas + {counts['n_efectos']} efectos + "
                f"{counts['n_gestos']} gestos)"
            )
            for k, v in salida.get("otras_dimensiones", {}).items():
                print(f"{k}: {v if isinstance(v, str) else ', '.join(map(str, v))}")
        return 0

    if a.cmd == "sugerir":
        pedido = (a.pedido or "").strip()
        ints = [s.strip() for s in a.intenciones.split(",") if s.strip()]
        if not ints and not pedido:
            print("ERROR: hace falta --intenciones y/o --pedido")
            return 1
        if not ints and pedido:
            hits = sugerir_pedido(pedido, limite=a.limite)
            if a.json:
                print(json.dumps({"hits": hits}, ensure_ascii=False, indent=1))
            else:
                if not hits:
                    print("sin coincidencias; prueba listar o un id del catálogo",
                          file=sys.stderr)
                    return 1
                for o in hits:
                    print(f"{o['id']}\t{o['motor']}\t{o.get('firma') or o.get('ocasion', '')}")
                    if o.get("producir"):
                        print(f"  producir: {o['producir']}")
            return 0 if hits else 1
        evitar = {t for t in a.evitar.split(",") if t}
        doms = []
        for ruta in a.anterior:
            viejo = _leer_plan(ruta)
            evitar.update(t for t in tipos_de(viejo) if t)
            doms.append(dominante(viejo))
        try:
            mano = elegir(ints, evitar=evitar, semilla=a.semilla,
                          completo=a.completo, pedido=pedido or None)
        except ValueError as ex:
            print(f"ERROR: {ex}")
            return 1
        if a.json:
            print(json.dumps({"mano": mano, "evitados": sorted(evitar),
                              "dominantes_anteriores": doms}, ensure_ascii=False, indent=1))
        else:
            for m in mano:
                extra = (" (reutilizada: toda la familia se evitaba; "
                         "si el argumento no la pide, sube la semilla)") if m["reutilizada"] else ""
                etiqueta = m["opcion"]
                print(f"{m['intencion']}: {etiqueta} [{m['motor']}]{extra}")
                if m.get("producir") and m["motor"] != MOTOR_ESCENA:
                    print(f"  producir: {m['producir']}")
            if doms:
                print(f"evitando tipos de la(s) pieza(s) anterior(es); "
                      f"dominante(s): {', '.join(d or '?' for d in doms)}")
        return 0

    if a.cmd == "resolver":
        r = resolver(a.id)
        if not r:
            print(f"ERROR: opción desconocida: {a.id}", file=sys.stderr)
            return 1
        if a.json:
            print(json.dumps(r, ensure_ascii=False, indent=1))
        else:
            print(f"{r['id']} · motor={r['motor']}")
            if r.get("firma"):
                print(f"  firma: {r['firma']}")
            if r.get("intenciones"):
                print(f"  intenciones: {', '.join(r['intenciones'])}")
            if r.get("producir"):
                print(f"  producir: {r['producir']}")
            if r.get("preferir"):
                print(f"  preferir: {r['preferir']}"
                      + (f" · nativo: {r['nativo']}" if r.get("nativo") else ""))
            if r.get("motor_produccion"):
                print(f"  motor_produccion: {r['motor_produccion']}"
                      + (f" / {', '.join(r['motores_alt'])}" if r.get("motores_alt") else ""))
        return 0

    if a.cmd == "cobertura":
        planes = [_leer_plan(r) for r in a.planes]
        r = resumen(planes)
        if a.json:
            print(json.dumps(r, ensure_ascii=False, indent=1))
        else:
            print(f"tipos usados: {r['n_tipos']}/{r['n_catalogo']} del catálogo "
                  f"({r['pct_catalogo']}%) — {', '.join(f'{k}×{v}' for k, v in sorted(r['tipos_usados'].items()))}")
            print(f"intenciones cubiertas: {', '.join(r['intenciones_cubiertas']) or 'ninguna'}")
            for i in r["intenciones_sin_tocar"]:
                if i["declarada_no_aplica"]:
                    print(f"sin tocar (declarado no_aplica): {i['id']} — {i['motivo']}")
                else:
                    print(f"sin tocar (SIN DECLARAR): {i['id']} — familia: {', '.join(i['familia'])}; "
                          f"si no aplica, decláralo en el plan: \"no_aplica\": {{\"{i['id']}\": \"<por qué>\"}}")
            print(f"escenas sin usar en esta(s) pieza(s): {', '.join(r['escenas_sin_usar'])}")
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
