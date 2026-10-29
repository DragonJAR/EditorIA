#!/usr/bin/env python3
"""Selector del repertorio talking-head (claude-video-effects destilado).

Fuente ÚNICA: scripts/data/efectos_talking_head.json
Doctrina: references/efectos-talking-head.md

No vendoriza el motor CVE. Lista, sugiere y valida el catálogo; `receta`
imprime los comandos para clonar en /tmp y renderizar (el agente los ejecuta).

Uso:
  python3 scripts/efectos_talking_head.py listar [--preferir externo|nativo|ambos] [--json]
  python3 scripts/efectos_talking_head.py sugerir --pedido "orbit detrás de la cara" [--json]
  python3 scripts/efectos_talking_head.py validar [--json]
  python3 scripts/efectos_talking_head.py receta --fx orbit [--start 3 --end 6]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
DATOS = os.path.join(BASE, "data", "efectos_talking_head.json")


def cargar(ruta=DATOS):
    with open(ruta, encoding="utf-8") as fh:
        return json.load(fh)


def _por_id(datos):
    return {e["id"]: e for e in datos.get("efectos", [])}


def _aliases(datos):
    out = {}
    for e in datos.get("efectos", []):
        out[e["id"]] = e["id"]
        for a in e.get("aliases", []):
            out[a] = e["id"]
    for look in datos.get("looks_nombrados", []):
        out[look["id"]] = look["de"]
    return out


def resolver(nombre, datos=None):
    """Normaliza nombre o alias → id canónico (o None)."""
    datos = datos or cargar()
    clave = (nombre or "").strip().lower().replace("_", "-")
    return _aliases(datos).get(clave)


def validar(datos=None):
    """Problemas del catálogo (lista vacía = sano)."""
    datos = datos or cargar()
    malos = []
    efectos = datos.get("efectos", [])
    if len(efectos) != int(datos.get("conteo", 45)):
        malos.append(
            f"conteo={datos.get('conteo')} pero hay {len(efectos)} efectos"
        )
    ids = set()
    for e in efectos:
        eid = e.get("id")
        if not eid:
            malos.append("efecto sin id")
            continue
        if eid in ids:
            malos.append(f"id repetido: {eid}")
        ids.add(eid)
        for campo in ("firma", "ocasion", "preferir", "adaptar", "ruta"):
            if not e.get(campo):
                malos.append(f"{eid}: falta '{campo}'")
        if e.get("preferir") not in ("externo", "nativo", "ambos"):
            malos.append(f"{eid}: preferir inválido '{e.get('preferir')}'")
        if e.get("preferir") in ("nativo", "ambos") and not e.get("nativo"):
            malos.append(f"{eid}: preferir={e['preferir']} sin 'nativo'")
        if e.get("preferir") == "externo" and e.get("nativo"):
            # permitido como pista, no error
            pass
    if datos.get("entrada") != "references/efectos-talking-head.md":
        malos.append("entrada debe apuntar a references/efectos-talking-head.md")
    for req in ("fuente", "clon_tmp", "setup", "clone_root", "fx_module",
                "words_module"):
        if not datos.get(req):
            malos.append(f"falta meta '{req}'")
    return malos


def listar(datos=None, preferir=None):
    datos = datos or cargar()
    filas = []
    for e in datos.get("efectos", []):
        if preferir and e.get("preferir") != preferir:
            continue
        filas.append(e)
    return filas


def sugerir(pedido, datos=None, limite=5):
    """Empareja el pedido del usuario con efectos por id/alias/keywords/firma."""
    datos = datos or cargar()
    texto = (pedido or "").strip().lower()
    if not texto:
        return []
    tokens = set(re.findall(r"[a-z0-9áéíóúñü+-]+", texto, re.I))
    scored = []
    for e in datos.get("efectos", []):
        score = 0
        eid = e["id"]
        if eid in texto or eid.replace("-", " ") in texto:
            score += 50
        for a in e.get("aliases", []):
            if a in texto or a.replace("-", " ") in texto:
                score += 40
        blob = " ".join(
            [
                e.get("firma", ""),
                e.get("ocasion", ""),
                " ".join(e.get("keywords", [])),
            ]
        ).lower()
        for t in tokens:
            if len(t) < 3:
                continue
            if t in eid or t in blob:
                score += 3
            for kw in e.get("keywords", []):
                if t in kw.lower():
                    score += 5
        if score:
            scored.append((score, e))
    scored.sort(key=lambda x: (-x[0], x[1]["n"]))
    return [e for _, e in scored[:limite]]


def _binario_cve(datos, modulo):
    """Python del venv CVE + módulo (sin literales scripts/*.py en el JSON)."""
    root = datos["clone_root"]
    py = os.path.join(root, datos.get("venv_python", ".venv/bin/python"))
    # join por partes (evita un literal scripts + slash + módulo en el fuente)
    script = os.path.join(root, "scripts", modulo)
    return f"{py} {script}"


def receta(fx, start=None, end=None, video="entrada.mp4", datos=None):
    """Comandos copiables para clonar (tmp) y renderizar un efecto."""
    datos = datos or cargar()
    eid = resolver(fx, datos)
    if not eid:
        raise SystemExit(f"efecto desconocido: {fx}")
    e = _por_id(datos)[eid]
    look = None
    for L in datos.get("looks_nombrados", []):
        if (fx or "").strip().lower() == L["id"]:
            look = L
            eid = L["de"]
            break
    render = _binario_cve(datos, datos["fx_module"])
    words = _binario_cve(datos, datos["words_module"])
    lineas = [
        f"# efecto: {eid}" + (f" look={look['look']}" if look else ""),
        f"# ocasión: {e['ocasion']}",
        f"# preferir: {e['preferir']}"
        + (f" · nativo: {e['nativo']}" if e.get("nativo") else ""),
        f"# adaptar: {e['adaptar']}",
        datos["clon_tmp"],
        datos["setup"],
    ]
    if e["preferir"] == "nativo":
        lineas.append(
            f"# Preferir nativo: {e['nativo']} — solo usa CVE si ya estás en su pipeline"
        )
    st = f" --start {start}" if start is not None else " --start 0"
    en = f" --end {end}" if end is not None else " --end 4"
    opt = f" --opt look={look['look']}" if look else ""
    lineas.append(
        f"{render} {eid} {video} {os.path.splitext(video)[0]}_{eid}.mp4"
        f"{st}{en}{opt}"
    )
    lineas.append(
        f"# check frame: {render} --plan plan_fx.json {video} check.png --still 2.0"
    )
    lineas.append(f"# palabras: {words} {video}")
    lineas.append(f"rm -rf {datos['clone_root']}")
    return "\n".join(lineas)


def _cmd_listar(args):
    datos = cargar()
    filas = listar(datos, preferir=args.preferir)
    if args.json:
        json.dump(filas, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return 0
    for e in filas:
        nat = f" → {e['nativo']}" if e.get("nativo") else ""
        print(f"{e['n']:2}. {e['id']:<24} [{e['preferir']}]{nat}")
        print(f"    ocasión: {e['ocasion']}")
    print(f"\n{len(filas)} efectos · fuente: {DATOS}")
    return 0


def _cmd_sugerir(args):
    datos = cargar()
    hits = sugerir(args.pedido, datos, limite=args.limite)
    if args.json:
        json.dump(hits, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return 0 if hits else 1
    if not hits:
        print("sin coincidencias; prueba listar o un fx name del catálogo",
              file=sys.stderr)
        return 1
    for e in hits:
        print(f"{e['id']}\t{e['preferir']}\t{e['ocasion']}")
        print(f"  ruta: {e['ruta']}")
        if e.get("nativo"):
            print(f"  nativo: {e['nativo']}")
    return 0


def _cmd_validar(args):
    malos = validar()
    if args.json:
        json.dump({"ok": not malos, "problemas": malos}, sys.stdout,
                  ensure_ascii=False, indent=2)
        print()
        return 0 if not malos else 1
    if malos:
        for m in malos:
            print(f"FALLO: {m}", file=sys.stderr)
        return 1
    datos = cargar()
    print(f"OK · {len(datos['efectos'])} efectos · {DATOS}")
    return 0


def _cmd_receta(args):
    print(receta(args.fx, start=args.start, end=args.end, video=args.video))
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Selector de efectos talking-head (fuente: data/efectos_talking_head.json)"
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pl = sub.add_parser("listar", help="lista el catálogo")
    pl.add_argument("--preferir", choices=("externo", "nativo", "ambos"))
    pl.add_argument("--json", action="store_true")
    pl.set_defaults(func=_cmd_listar)

    ps = sub.add_parser("sugerir", help="empareja un pedido en prosa")
    ps.add_argument("--pedido", required=True)
    ps.add_argument("--limite", type=int, default=5)
    ps.add_argument("--json", action="store_true")
    ps.set_defaults(func=_cmd_sugerir)

    pv = sub.add_parser("validar", help="integridad del JSON")
    pv.add_argument("--json", action="store_true")
    pv.set_defaults(func=_cmd_validar)

    pr = sub.add_parser("receta", help="comandos para clonar en /tmp y renderizar")
    pr.add_argument("--fx", required=True)
    pr.add_argument("--start", type=float, default=None)
    pr.add_argument("--end", type=float, default=None)
    pr.add_argument("--video", default="entrada.mp4")
    pr.set_defaults(func=_cmd_receta)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
