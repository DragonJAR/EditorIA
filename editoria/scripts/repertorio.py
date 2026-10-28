#!/usr/bin/env python3
"""Repertorio: la única fuente intención→escena, su rotación y su cobertura.

El catálogo del motor (claves de SCENES en render_plan.py) es alcanzable
entero desde las intenciones, pero el flujo normal llegaba siempre a las
mismas 6-8: el índice por intención daba UNA escena por intención, el
ejemplo del SKILL y demo_plan.json anclaban el resto, y las familias para
rotar vivían solo en clonar_video.py (con un nombre fantasma y escenas
fuera). Este módulo es el mecanismo único que faltaba:

  listar     las intenciones y sus familias (y con --todo, el resto de
             dimensiones del repertorio derivadas de SU fuente: paletas de
             _comun.PALETAS, direcciones/sectores de direcciones.json,
             tonos/modos de direccion_arte.py, SFX de sfx.GENERADORES)
  sugerir    dada una lista de intenciones, elige UNA escena por intención
             rotando de forma determinista (misma semilla = misma mano) y
             evitando los tipos de las piezas anteriores (--anterior)
  cobertura  qué usa un plan (o varios), qué intenciones quedan sin tocar
             y cuáles están declaradas no_aplica en el plan y cuáles no:
             lo no usado queda explícito, no olvidado
  validar    que ninguna escena del motor quede huérfana de intención ni
             ninguna familia nombre una escena que no existe

La relación intención→escena vive SOLO en scripts/data/repertorio.json.
auditar_plan.py y clonar_video.py la consumen; nadie la copia a mano.

Uso:
  python3 scripts/repertorio.py listar [--todo] [--json]
  python3 scripts/repertorio.py sugerir --intenciones gancho,dato,cierre --anterior plan_viejo.json [--semilla 1] [--json]
  python3 scripts/repertorio.py cobertura plan.json [--anterior plan_viejo.json] [--json]
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


def cargar(ruta=DATOS):
    with open(ruta, encoding="utf-8") as fh:
        return json.load(fh)


def catalogo():
    """Los tipos salen del dict SCENES de render_plan.py (fuente única)."""
    with open(os.path.join(BASE, "render_plan.py"), encoding="utf-8") as fh:
        src = fh.read()
    bloque = re.search(r"^SCENES\s*=\s*\{(.*?)\}\s*$", src, re.S | re.M).group(1)
    return set(re.findall(r'"(\w+)"\s*:\s*sc_', bloque))


def familias(datos=None):
    """{intencion: [escenas]} en el orden declarado (el orden es la mano base)."""
    datos = datos or cargar()
    return {i["id"]: list(i["escenas"]) for i in datos["intenciones"]}


def intencion_de(tipo, datos=None):
    """A qué intenciones sirve una escena (puede ser más de una)."""
    return [k for k, v in familias(datos).items() if tipo in v]


def validar(datos=None, tipos=None):
    """Problemas del repertorio (lista vacía = sano): huérfanas y fantasmas."""
    datos = datos or cargar()
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
    return malos


def _rotar(lista, semilla, clave):
    """Rota la familia de forma determinista según (semilla, clave)."""
    if not lista:
        return []
    h = int(hashlib.sha256(f"{semilla}:{clave}".encode()).hexdigest()[:8], 16)
    k = h % len(lista)
    return lista[k:] + lista[:k]


def elegir(intenciones, evitar=(), semilla=0, datos=None):
    """Una escena por intención: rota y evita lo ya usado si puede.

    Devuelve [{intencion, escena, reutilizada}] — reutilizada=True cuando
    TODA la familia estaba en `evitar` o ya elegida en esta misma mano:
    se dice, no se esconde (el argumento puede pedir justo esa escena).
    """
    fams = familias(datos)
    evitar, elegidas, mano = set(evitar), set(), []
    for inten in intenciones:
        if inten not in fams:
            raise ValueError(f"intención desconocida: {inten} "
                             f"(válidas: {', '.join(fams)})")
        orden = _rotar(fams[inten], semilla, inten)
        libre = [e for e in orden if e not in evitar and e not in elegidas]
        escena = libre[0] if libre else orden[0]
        mano.append({"intencion": inten, "escena": escena,
                     "reutilizada": not libre})
        elegidas.add(escena)
    return mano


def tipos_de(plan):
    return [e.get("tipo") for e in plan.get("escenas", []) if isinstance(e, dict)]


def dominante(plan):
    tipos = tipos_de(plan)
    return Counter(tipos).most_common(1)[0][0] if tipos else None


def resumen(planes, datos=None):
    """Cobertura conjunta de uno o más planes contra el catálogo entero."""
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
    """La tabla §2b: una fila por intención, en el orden del JSON."""
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
        # id canónico = lo que hay antes de "/" (social/testimonio → social)
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
    except Exception as ex:  # se dice, no se esconde
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


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("listar", help="intenciones y familias (con --todo, todo el repertorio)")
    p.add_argument("--todo", action="store_true", help="añade paletas, direcciones, tonos, modos y SFX derivados de su fuente")
    p.add_argument("--json", action="store_true", help="salida en JSON, para maquinas")
    p = sub.add_parser("sugerir", help="una escena por intención, rotando y evitando piezas anteriores")
    p.add_argument("--intenciones", required=True, help="lista separada por comas, p. ej. gancho,dato,proceso,cierre")
    p.add_argument("--anterior", action="append", default=[], help="plan.json de una pieza anterior (repetible): sus tipos se evitan si la familia da otra opción")
    p.add_argument("--evitar", default="", help="tipos a evitar además, separados por comas")
    p.add_argument("--semilla", type=int, default=0, help="otra semilla = otra mano (default: 0)")
    p.add_argument("--json", action="store_true", help="salida en JSON, para maquinas")
    p = sub.add_parser("cobertura", help="qué usa el plan, qué intenciones quedan sin tocar y si están declaradas no_aplica")
    p.add_argument("planes", nargs="+", help="plan.json (uno o más)")
    p.add_argument("--json", action="store_true", help="salida en JSON, para maquinas")
    p = sub.add_parser("validar", help="ninguna escena huérfana ni fantasma en las familias")
    p.add_argument("--json", action="store_true", help="salida en JSON, para maquinas")
    a = ap.parse_args()

    if a.cmd == "validar":
        malos = validar()
        if a.json:
            print(json.dumps({"problemas": malos}, ensure_ascii=False, indent=1))
        elif malos:
            print("REPERTORIO CON PROBLEMAS:")
            for m in malos:
                print(f"  - {m}")
        else:
            print(f"REPERTORIO VALIDO: {len(catalogo())} escenas del motor, "
                  f"todas alcanzables desde alguna intención")
        return 1 if malos else 0

    if a.cmd == "listar":
        fams = familias()
        salida = {"intenciones": fams, "n_escenas_catalogo": len(catalogo())}
        if a.todo:
            salida["otras_dimensiones"] = _otras_dimensiones()
        if a.json:
            print(json.dumps(salida, ensure_ascii=False, indent=1))
        else:
            for k, v in fams.items():
                print(f"{k}: {', '.join(v)}")
            print(f"catálogo del motor: {salida['n_escenas_catalogo']} escenas")
            for k, v in salida.get("otras_dimensiones", {}).items():
                print(f"{k}: {v if isinstance(v, str) else ', '.join(map(str, v))}")
        return 0

    if a.cmd == "sugerir":
        evitar = {t for t in a.evitar.split(",") if t}
        doms = []
        for ruta in a.anterior:
            viejo = _leer_plan(ruta)
            evitar.update(t for t in tipos_de(viejo) if t)
            doms.append(dominante(viejo))
        try:
            mano = elegir([s.strip() for s in a.intenciones.split(",") if s.strip()],
                          evitar=evitar, semilla=a.semilla)
        except ValueError as ex:
            print(f"ERROR: {ex}")
            return 1
        if a.json:
            print(json.dumps({"mano": mano, "evitados": sorted(evitar),
                              "dominantes_anteriores": doms}, ensure_ascii=False, indent=1))
        else:
            for m in mano:
                extra = " (reutilizada: toda la familia se evitaba; si el argumento no la pide, sube la semilla)" if m["reutilizada"] else ""
                print(f"{m['intencion']}: {m['escena']}{extra}")
            if doms:
                print(f"evitando tipos de la(s) pieza(s) anterior(es); dominante(s): {', '.join(d or '?' for d in doms)}")
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
