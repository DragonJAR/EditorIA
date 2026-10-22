#!/usr/bin/env python3
"""Dirección de arte: repartir, elegir y verificar la dirección visual de una pieza.

Un modelo al que se le pide "invéntate un look" elige siempre el default de la
categoría. Aquí las direcciones se REPARTEN desde una biblioteca (scripts/data/
direcciones.json) y el agente elige entre ellas la que pueda llevar algo que
solo este sujeto tiene (references/direccion-de-arte.md). Después se adopta
tal cual: sin mezclarla con el layout de siempre.

  repartir   reparte N direcciones para un brief (determinista: el mismo brief
             da la misma mano; --semilla 1 pide otra). Filtra por lo que el
             motor soporta y por los assets que de verdad existen.
  ficha      imprime la hoja completa de una dirección.
  elegir     escribe SISTEMA.md (decisiones visuales durables del proyecto) y
             estilo.json (style pack compatible con --brand; solo lienzo oscuro).
  verificar  contrastes WCAG de un brand pack o style pack (informativo).
  listar     sectores, direcciones, tonos o modos disponibles.

Marca-blanca: una dirección es un style pack de ESTILO, no una identidad de
marca; con brand pack manda el pack (references/brand-packs.md).

Ejemplos:
  python3 scripts/direccion_arte.py repartir --brief "demo de un editor de video con IA" \\
      --sector tecnologia --tono demo --modo demostrar --tiene capturas
  python3 scripts/direccion_arte.py ficha producto_actuando
  python3 scripts/direccion_arte.py elegir producto_actuando --out ~/videos/lanzamiento
  python3 scripts/direccion_arte.py verificar brand/mi_pack.json
"""
import argparse
import hashlib
import json
import os
import random
import sys

KIT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(KIT, "ffmpeg_tools"))
from _comun import contraste, die, leer_json, leer_pack  # noqa: E402
from _plataforma import FUENTES_SKILL  # noqa: E402

DATOS = os.path.join(KIT, "data", "direcciones.json")
TONOS = ("demo", "resumen", "anuncio", "trailer", "parodia", "caos")                # references/tonos.md
MODOS = ("persuadir", "explicar", "demostrar", "experiencia")                       # references/direccion-de-arte.md
ENERGIAS = ("baja", "media", "alta")
ASSETS = ("fotos", "footage", "capturas")
PERSONALIDADES = ("baja+serio", "baja+lúdico", "alta+serio", "alta+lúdico")         # columnas de references/fluidez.md
FAMILIAS_EMPAQUETADAS = ("Plus Jakarta Sans", "Montserrat")
# Pisos de contraste (references/checklist-qa.md: WCAG AA): tinta sobre lienzo,
# texto de apoyo y acento (que también tiñe palabras, no solo formas).
PISO_TINTA, PISO_APOYO, PISO_ACENTO = 7.0, 4.5, 4.5


def cargar():
    return leer_json(DATOS, "la biblioteca de direcciones")


def validar_biblioteca(datos, tipos_escena=None):
    """Problemas de la biblioteca (lista vacía = sana): esquema, personalidades de
    fluidez.md, sectores/tonos/modos conocidos, escenas que existen y contraste de
    cada paleta contra sus pisos. La corre test_direccion_arte.py."""
    malos, ids = [], set()
    for d in datos["direcciones"]:
        i = d.get("id", "?")
        if i in ids:
            malos.append(f"{i}: id repetido")
        ids.add(i)
        for clave in ("nombre", "idea", "composicion", "sectores", "tonos", "modos", "energia", "necesita",
                      "lienzo", "motor", "paleta", "proporciones", "tipos", "movimiento", "escenas", "fondo",
                      "sonido", "evitar", "caption"):
            if clave not in d:
                malos.append(f"{i}: falta {clave}")
        if d.get("energia") not in ENERGIAS:
            malos.append(f"{i}: energía '{d.get('energia')}'")
        if d.get("movimiento", {}).get("personalidad") not in PERSONALIDADES:
            malos.append(f"{i}: personalidad '{d.get('movimiento', {}).get('personalidad')}' no es una columna de fluidez.md")
        malos += [f"{i}: sector '{x}' desconocido" for x in d.get("sectores", []) if x not in datos["sectores"]]
        malos += [f"{i}: tono '{x}' desconocido" for x in d.get("tonos", []) if x not in TONOS]
        malos += [f"{i}: modo '{x}' desconocido" for x in d.get("modos", []) if x not in MODOS]
        malos += [f"{i}: necesita '{x}' desconocido" for x in d.get("necesita", []) if x != "nada" and x not in ASSETS]
        if tipos_escena is not None:
            malos += [f"{i}: la escena '{e}' no existe" for e in d.get("escenas", []) if e not in tipos_escena]
        if d.get("motor", {}).get("plan") and d.get("lienzo") != "oscuro":
            malos.append(f"{i}: motor.plan exige lienzo oscuro")
        if d.get("motor", {}).get("plan") and not d.get("escenas"):
            malos.append(f"{i}: una dirección de plan necesita escenas afines")
        for rol, fg, bg, c, piso in (tabla_contraste(d) if "paleta" in d else []):
            if c < piso:
                malos.append(f"{i}: {rol} {fg} sobre {bg} = {c:.1f}:1 (piso {piso:g}:1)")
    return malos


def por_id(datos, ident):
    for d in datos["direcciones"]:
        if d["id"] == ident:
            return d
    ids = ", ".join(d["id"] for d in datos["direcciones"])
    die(f"no existe la dirección '{ident}'. Disponibles: {ids}", kind="input")


def soporta(d, tiene):
    """Una dirección es viable si no necesita assets o si existe alguno de los que usa."""
    nec = d.get("necesita", ["nada"])
    return "nada" in nec or any(a in tiene for a in nec)


def filtrar(datos, motor, sector, tono, modo, energia, tiene, excluir):
    """Elegibles según filtros; si quedan pocos, relaja en orden energía → tono →
    modo → sector (nunca motor ni assets: son hechos, no gustos) y lo informa."""
    base = [d for d in datos["direcciones"]
            if d["id"] not in excluir and soporta(d, tiene)
            and (motor == "libre" or d["motor"]["plan"])]
    filtros = [("energia", lambda d: not energia or d["energia"] == energia),
               ("tono", lambda d: not tono or tono in d["tonos"]),
               ("modo", lambda d: not modo or modo in d["modos"]),
               ("sector", lambda d: not sector or sector == "otro" or sector in d["sectores"])]
    return base, filtros


def elegibles(datos, args, minimo):
    base, filtros = filtrar(datos, args.motor, args.sector, args.tono, args.modo,
                            args.energia, set(args.tiene or []), set(args.excluir or []))
    aplicados, relajados = list(filtros), []
    while True:
        pool = [d for d in base if all(f(d) for _, f in aplicados)]
        if len(pool) >= minimo or not aplicados:
            return pool, relajados, len(base)
        nombre, _ = aplicados.pop(0)       # primero se suelta el que menos pesa: energía → tono → modo → sector
        if getattr(args, nombre, None):
            relajados.append(nombre)


def repartir(datos, args):
    pool, relajados, n_base = elegibles(datos, args, args.opciones)
    semilla = hashlib.sha256("|".join(
        [args.brief or "", args.sector or "", args.tono or "", args.modo or "", str(args.semilla)]
    ).encode("utf-8")).hexdigest()
    rng = random.Random(int(semilla[:16], 16))
    mano = rng.sample(pool, min(args.opciones, len(pool)))
    return mano, pool, relajados, n_base


def swatches(d):
    p = d["paleta"]
    if "campos" in p:
        return " · ".join(f"campo {c['fondo']} / tinta {c['tinta']}" for c in p["campos"])
    return f"negro {p['negro']} · blanco {p['blanco']} · gris {p['gris']} · acento {p['acento']}"


def resumen(i, d):
    mov = d["movimiento"]
    motor = "motor: render_plan" if d["motor"]["plan"] else "motor: composición libre / Remotion / HyperFrames"
    return (f"{i}. {d['id']} — {d['nombre']}  [energía {d['energia']} · necesita: {', '.join(d['necesita'])} · {motor}]\n"
            f"   Idea: {d['idea']}\n"
            f"   Movimiento: {mov['personalidad']} · {mov['transiciones']} · firma: {mov['firma']}\n"
            f"   Paleta: {swatches(d)}")


def cmd_repartir(args, datos):
    if args.opciones < 1:
        die("--opciones debe ser >= 1", kind="input")
    mano, pool, relajados, n_base = repartir(datos, args)
    if not mano:
        die("ninguna dirección es viable con esos assets y ese motor: usa --motor libre o declara "
            "con --tiene los assets que de verdad existen", kind="input")
    if args.json:
        print(json.dumps({"brief": args.brief, "semilla": args.semilla, "elegibles": len(pool),
                          "relajados": relajados, "direcciones": mano}, ensure_ascii=False, indent=2))
        return
    print(f"Brief: {args.brief or '(sin brief)'}  |  sector: {args.sector or '-'}  tono: {args.tono or '-'}  "
          f"modo: {args.modo or '-'}  energía: {args.energia or '-'}  |  motor: {args.motor}  "
          f"assets: {', '.join(args.tiene) if args.tiene else 'ninguno'}  |  semilla: {args.semilla}")
    print(f"Viables: {len(pool)} de {n_base}" +
          (f"  (se relajó: {', '.join(relajados)})" if relajados else ""))
    print()
    for i, d in enumerate(mano, 1):
        print(resumen(i, d))
        print()
    print("Siguiente paso: elige la que pueda llevar algo que SOLO este sujeto tiene.")
    print("Prueba del competidor: pon el nombre del competidor más cercano en la frase de la idea;")
    print("si la frase sigue valiendo, es la idea de la categoría y no la del sujeto.")
    print("Adóptala sin mezclarla con el layout de siempre. Otra mano: --semilla "
          f"{args.semilla + 1}. Luego: direccion_arte.py elegir {mano[0]['id']} --out CARPETA_DEL_PROYECTO")


def tabla_contraste(d):
    p = d["paleta"]
    if "campos" in p:
        filas = [(f"campo {c['fondo']}", c["tinta"], c["fondo"], PISO_TINTA) for c in p["campos"]]
    else:
        filas = [("tinta (blanco)", p["blanco"], p["negro"], PISO_TINTA),
                 ("apoyo (gris)", p["gris"], p["negro"], PISO_APOYO),
                 ("acento", p["acento"], p["negro"], PISO_ACENTO)]
    return [(rol, fg, bg, contraste(fg, bg), piso) for rol, fg, bg, piso in filas]


def ficha_md(d, brief=None, semilla=0):
    mov, tipos = d["movimiento"], d["tipos"]
    lineas = [f"# Sistema visual — {d['nombre']}", "",
              f"Dirección: **{d['nombre']}** (`{d['id']}`)" + (f" · Brief: {brief}" if brief else "") +
              (f" · semilla {semilla}" if semilla else ""),
              "Generado por `scripts/direccion_arte.py`. Es la fuente de las decisiones visuales DURABLES del "
              "proyecto: se reescribe cuando cambia el diseño, no cuando un render falla "
              "(`references/direccion-de-arte.md`).", "",
              "## La idea", "",
              "> En este video, **[algo que pertenece al sujeto]** se convierte en **[el dispositivo de esta dirección]**.", "",
              f"Dispositivo de la dirección: {d['idea']}", "",
              "- Prueba del competidor: pon el nombre del competidor más cercano en la frase de arriba. "
              "Si sigue valiendo, la idea es de la categoría: cámbiala.",
              "- Inventario del sujeto (8-12 cosas que son de este cliente y de ningún competidor: su nombre y "
              "lo que significa, sus cifras, su restricción, sus materiales, sus rituales, sus objetos impresos):",
              "  - _por completar_", "",
              "## Composición", "", d["composicion"], "",
              "## Paleta", ""]
    if "campos" in d["paleta"]:
        lineas += ["Lienzo claro: se compone en libre / Remotion / HyperFrames (`render_plan.py` usa lienzo oscuro).", "",
                   "| Campo | Tinta | Contraste |", "|---|---|---|"]
        lineas += [f"| `{r[2]}` | `{r[1]}` | {r[3]:.1f}:1 |" for r in tabla_contraste(d)]
    else:
        lineas += ["| Rol | Color | Contraste sobre el lienzo | Piso |", "|---|---|---|---|",
                   f"| lienzo (`negro`) | `{d['paleta']['negro']}` | - | - |"]
        lineas += [f"| {rol} | `{fg}` | {c:.1f}:1 | {piso:g}:1 |" for rol, fg, _, c, piso in tabla_contraste(d)]
    lineas += ["", f"Proporciones: {d['proporciones']}", "",
               "## Tipografía", "",
               f"- Titulares: {tipos['titulares']}", f"- Texto: {tipos['texto']}", f"- {tipos['nota']}", "",
               "## Movimiento", "",
               f"- Personalidad: **{mov['personalidad']}** (columna de `references/fluidez.md`, tabla "
               "«Personalidad → parámetros»).",
               f"- Transiciones: {mov['transiciones']}",
               f"- Momento firma: {mov['firma']}", "",
               "## Escenas afines", ""]
    lineas.append(", ".join(f"`{e}`" for e in d["escenas"]) if d["escenas"]
                  else "Ninguna del catálogo de `render_plan.py`: " + d["motor"].get("nota", ""))
    lineas += ["", "## Fondo y sonido", "", f"- Fondo: {d['fondo']}", f"- Sonido: {d['sonido']}", "",
               "## Evitar en esta dirección", ""] + [f"- {x}" for x in d["evitar"]]
    lineas += ["", "## Vigilar siempre", "",
               "Los «tells» de pieza generada (`references/direccion-de-arte.md`, sección Tells) y "
               "`python scripts/auditar_plan.py plan.json`, que los detecta en el plan. Una excepción "
               "deliberada se anota abajo y en `tells_ok` del plan.", "",
               "## Excepciones por escena", "",
               "Si una escena se desvía de este sistema, anótala aquí con el motivo: mientras esté escrita, "
               "la regla de la escena manda sobre el sistema; lo demás hereda de arriba.", "",
               "- _ninguna por ahora_", ""]
    return "\n".join(lineas)


def pack_json(d, nombre=None):
    """Style pack compatible con --brand (render_plan, caption, thumbnail...). Solo
    familias empaquetadas: resuelven por nombre sin rutas de la máquina."""
    p, cap = d["paleta"], d["caption"]

    def familia(texto, defecto):
        return next((f for f in FAMILIAS_EMPAQUETADAS if f in texto), defecto)
    fam_t = familia(d["tipos"]["titulares"], "Plus Jakarta Sans")
    fam_x = familia(d["tipos"]["texto"], "Montserrat")
    return {
        "_nota": (f"Style pack generado por scripts/direccion_arte.py (dirección «{d['nombre']}»). Es un estilo, "
                  "no una marca: con un brand pack del usuario, manda el pack. Se usa con --brand."),
        "nombre": nombre or f"estilo-{d['id']}",
        "version": "1.0.0",
        "estilo": {"direccion": d["id"], "personalidad_movimiento": d["movimiento"]["personalidad"]},
        "colores": {"acento": p["acento"], "blanco": p["blanco"], "gris": p["gris"], "negro": p["negro"]},
        "colors": {"outline": p["negro"].lstrip("#"), "primary": p["acento"].lstrip("#"),
                   "text": p["blanco"].lstrip("#")},
        "font": fam_x,
        "fonts_dir": str(FUENTES_SKILL),
        "tipografias": {"titulares": {"familia": fam_t}, "texto": {"familia": fam_x}},
        "caption": dict(cap, outline=2),
        "reglas": {"transiciones": d["movimiento"]["transiciones"]},
    }


def cmd_ficha(args, datos):
    d = por_id(datos, args.id)
    print(ficha_md(d, args.brief))


def escribir_nuevo(ruta, contenido, force):
    if os.path.exists(ruta) and not force:
        print(f"ya existe {ruta}: no se toca (usa --force para reescribirlo)")
        return False
    os.makedirs(os.path.dirname(os.path.abspath(ruta)), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as fh:
        fh.write(contenido)
    print(f"escrito {ruta}")
    return True


def cmd_elegir(args, datos):
    d = por_id(datos, args.id)
    out = os.path.abspath(os.path.expanduser(args.out))
    if out == os.path.dirname(KIT) or out.startswith(os.path.dirname(KIT) + os.sep):
        die("el proyecto no va dentro de la skill; elige una carpeta del usuario", kind="input")
    escribir_nuevo(os.path.join(out, "SISTEMA.md"), ficha_md(d, args.brief, args.semilla), args.force)
    if d["motor"]["plan"]:
        pack = json.dumps(pack_json(d, args.nombre), ensure_ascii=False, indent=2) + "\n"
        if escribir_nuevo(os.path.join(out, "estilo.json"), pack, args.force):
            print(f"Úsalo: python scripts/render_plan.py plan.json --brand {os.path.join(out, 'estilo.json')} -o out.mp4")
    else:
        print("Esta dirección es de lienzo claro: no genera pack para render_plan.py. "
              + d["motor"].get("nota", ""))
    print("Siguiente: completa en SISTEMA.md la frase de la idea y el inventario del sujeto "
          "antes de escribir el plan.")


def cmd_verificar(args, datos):
    pack = leer_pack(args.pack)
    col = dict(pack.get("colors") or {})
    col.update(pack.get("colores") or {})
    acento = col.get("acento") or col.get("primary") or col.get("accent")
    if not acento:
        die(f"{args.pack}: el pack no declara color de acento", kind="input")
    negro = col.get("negro") or "#0A0A0A"
    filas = [("acento", acento, PISO_ACENTO)]
    tinta, apoyo = col.get("blanco") or col.get("text"), col.get("gris")
    filas += [(rol, c, piso) for rol, c, piso in (("blanco", tinta, PISO_TINTA), ("gris", apoyo, PISO_APOYO)) if c]
    avisos = 0
    print(f"Contraste sobre el lienzo {negro} — {pack.get('nombre', args.pack)}")
    for rol, fg, piso in filas:
        c = contraste(fg, negro)
        estado = "OK  " if c >= piso else ("AVISO" if c >= 3.0 else "FALLA")
        avisos += estado != "OK  "
        nota = "" if estado == "OK  " else (
            f" — bajo el piso de {piso:g}:1" +
            ("; sirve solo en texto grande (>= 3:1), no en subtítulos ni cifras pequeñas" if estado == "AVISO" else ""))
        print(f"  {estado} {rol:7s} {fg}  {c:5.1f}:1{nota}")
    if avisos and args.estricto:
        sys.exit(1)


def cmd_listar(args, datos):
    if args.que == "sectores":
        for k, v in datos["sectores"].items():
            print(f"{k:24s} {v}")
    elif args.que == "direcciones":
        for d in datos["direcciones"]:
            print(f"{d['id']:20s} {d['nombre']}  [{d['lienzo']}, energía {d['energia']}]")
    elif args.que == "tonos":
        print("\n".join(TONOS))
    else:
        print("\n".join(MODOS))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="op", required=True)

    p = sub.add_parser("repartir", help="reparte N direcciones para un brief")
    p.add_argument("--brief", default="", help="una línea sobre el sujeto (semilla de la mano y contexto)")
    p.add_argument("--sector", help="sector del sujeto (ver `listar sectores`)")
    p.add_argument("--tono", choices=TONOS, help="tono de la pieza (references/tonos.md)")
    p.add_argument("--modo", choices=MODOS, help="qué significa el éxito del espectador: persuadir, explicar, demostrar o experiencia")
    p.add_argument("--energia", choices=ENERGIAS, help="energía deseada de la pieza")
    p.add_argument("--tiene", nargs="*", choices=ASSETS, metavar="ASSET",
                   help="assets que de verdad existen: fotos, footage, capturas (sin ellos solo se reparten direcciones que no los necesitan)")
    p.add_argument("--motor", choices=["plan", "libre"], default="plan",
                   help="plan = lo que render_plan.py compone (lienzo oscuro); libre = todas, incluidas las de lienzo claro")
    p.add_argument("--opciones", type=int, default=3, help="cuántas direcciones repartir (default 3)")
    p.add_argument("--semilla", type=int, default=0, help="otra mano para el mismo brief (default 0)")
    p.add_argument("--excluir", nargs="*", default=[], metavar="ID", help="direcciones ya descartadas")
    p.add_argument("--json", action="store_true", help="imprime la mano como JSON")

    p = sub.add_parser("ficha", help="hoja completa de una dirección")
    p.add_argument("id", help="id de la dirección (ver `listar direcciones`)")
    p.add_argument("--brief", help="línea de brief para el encabezado")

    p = sub.add_parser("elegir", help="escribe SISTEMA.md y estilo.json en la carpeta del proyecto")
    p.add_argument("id", help="id de la dirección elegida")
    p.add_argument("--out", required=True, help="carpeta del proyecto (nunca dentro de la skill)")
    p.add_argument("--brief", help="línea de brief para el encabezado")
    p.add_argument("--semilla", type=int, default=0, help="semilla de la mano de la que salió (solo para el registro)")
    p.add_argument("--nombre", help="nombre del style pack (default estilo-ID)")
    p.add_argument("--force", action="store_true", help="reescribe SISTEMA.md y estilo.json si ya existen")

    p = sub.add_parser("verificar", help="contrastes WCAG de un brand pack o style pack")
    p.add_argument("pack", help="brand pack o style pack (JSON; brand/x.json se resuelve contra la skill)")
    p.add_argument("--estricto", action="store_true", help="sale con 1 si algún contraste no llega al piso")

    p = sub.add_parser("listar", help="lista sectores, direcciones, tonos o modos")
    p.add_argument("que", choices=["sectores", "direcciones", "tonos", "modos"], help="qué listar")

    args = ap.parse_args()
    datos = None if args.op == "verificar" else cargar()
    if args.op == "repartir" and args.sector and args.sector not in datos["sectores"]:
        die(f"sector '{args.sector}' desconocido. Usa `listar sectores`.", kind="input")
    {"repartir": cmd_repartir, "ficha": cmd_ficha, "elegir": cmd_elegir,
     "verificar": cmd_verificar, "listar": cmd_listar}[args.op](args, datos)


if __name__ == "__main__":
    main()
