#!/usr/bin/env python3
"""Recetas clone-on-demand de motores externos de animación/ilustración.

NO es un catálogo paralelo. La elección del agente vive en repertorio.py
(opciones `motor=tecnica`: manim, handraw-estilo, pintura-cpu). Este módulo
PRODUCE: valida el JSON y `receta` imprime clone→setup→usar→rm en /tmp.

Detalle: scripts/data/motores_externos.json
Doctrina: references/motores-externos.md

Uso:
  python3 scripts/repertorio.py sugerir --pedido "explicar un algoritmo con manim"
  python3 scripts/repertorio.py resolver --id manim
  python3 scripts/motores_externos.py receta --id manim
  python3 scripts/motores_externos.py validar [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
DATOS = os.path.join(BASE, "data", "motores_externos.json")


def cargar(ruta=DATOS):
    with open(ruta, encoding="utf-8") as fh:
        return json.load(fh)


def _por_id(datos):
    return {m["id"]: m for m in datos.get("motores", [])}


def _aliases(datos):
    out = {}
    for m in datos.get("motores", []):
        out[m["id"]] = m["id"]
        for a in m.get("aliases", []):
            out[str(a).strip().lower().replace("_", "-")] = m["id"]
    return out


def resolver(nombre, datos=None):
    """Normaliza nombre o alias → id canónico (o None)."""
    datos = datos or cargar()
    clave = (nombre or "").strip().lower().replace("_", "-")
    return _aliases(datos).get(clave)


def validar(datos=None):
    """Problemas del registro (lista vacía = sano)."""
    datos = datos or cargar()
    malos = []
    motores = datos.get("motores", [])
    if len(motores) != int(datos.get("conteo", 0)):
        malos.append(
            f"conteo={datos.get('conteo')} pero hay {len(motores)} motores"
        )
    if datos.get("entrada") != "references/motores-externos.md":
        malos.append("entrada debe apuntar a references/motores-externos.md")
    ids = set()
    for m in motores:
        mid = m.get("id")
        if not mid:
            malos.append("motor sin id")
            continue
        if mid in ids:
            malos.append(f"id repetido: {mid}")
        ids.add(mid)
        for campo in (
            "firma", "ocasion", "no_usar", "repo", "licencia",
            "clon_tmp", "setup", "clone_root", "usar", "limpiar", "doc",
        ):
            if not m.get(campo):
                malos.append(f"{mid}: falta '{campo}'")
        if mid == "handraw-estilo":
            atr = (m.get("atribucion") or "")
            if "yang0" not in atr or "handraw-style" not in atr:
                malos.append(
                    "handraw-estilo: atribución debe citar yang0 y handraw-style"
                )
        doc = m.get("doc") or ""
        if doc and not doc.startswith("references/"):
            malos.append(f"{mid}: doc debe vivir bajo references/")
    for bloque in ("ya_cubierto", "descartado_a_proposito"):
        for fila in datos.get(bloque) or []:
            if not fila.get("repo") or not fila.get("motivo"):
                malos.append(f"{bloque}: fila sin repo/motivo")
    return malos


def listar(datos=None):
    return list((datos or cargar()).get("motores", []))


def receta(motor_id, datos=None):
    """Comandos copiables: clone → setup → usar → limpiar."""
    datos = datos or cargar()
    mid = resolver(motor_id, datos)
    if not mid:
        raise SystemExit(f"motor desconocido: {motor_id}")
    m = _por_id(datos)[mid]
    lineas = [
        f"# motor externo: {mid}",
        f"# firma: {m['firma']}",
        f"# ocasión: {m['ocasion']}",
        f"# no usar: {m['no_usar']}",
        f"# repo: {m['repo']} ({m['licencia']}"
        + (f", {m['autor']}" if m.get("autor") else "")
        + ")",
        f"# doctrina: {m['doc']}",
    ]
    if m.get("atribucion"):
        lineas.append(f"# ATRIBUCIÓN OBLIGATORIA: {m['atribucion']}")
    lineas.extend([
        m["clon_tmp"],
        m["setup"],
        m["usar"],
        m["limpiar"],
    ])
    return "\n".join(lineas)


def _cmd_listar(args):
    datos = cargar()
    filas = listar(datos)
    if args.json:
        json.dump(filas, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return 0
    for m in filas:
        print(f"{m['id']:<16} {m['firma']}")
        print(f"  {m['repo']} · {m['licencia']}")
        if m.get("atribucion"):
            print(f"  atribución: {m['atribucion']}")
    print(f"\n{len(filas)} motores · fuente: {DATOS}")
    ya = len(datos.get("ya_cubierto") or [])
    desc = len(datos.get("descartado_a_proposito") or [])
    print(f"ya_cubierto={ya} · descartado_a_proposito={desc}")
    return 0


def _cmd_receta(args):
    texto = receta(args.id)
    print(texto)
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
            print(f"ERROR: {m}", file=sys.stderr)
        return 1
    print("OK: motores_externos.json válido")
    return 0


def _cmd_resolver(args):
    mid = resolver(args.nombre)
    if not mid:
        print(f"desconocido: {args.nombre}", file=sys.stderr)
        return 1
    m = _por_id(cargar())[mid]
    if args.json:
        json.dump(m, sys.stdout, ensure_ascii=False, indent=2)
        print()
    else:
        print(mid)
        print(m["doc"])
        print(f"python scripts/motores_externos.py receta --id {mid}")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Recetas clone-on-demand de motores externos (vía repertorio)"
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pl = sub.add_parser("listar", help="Lista los motores adoptados")
    pl.add_argument("--json", action="store_true")
    pl.set_defaults(func=_cmd_listar)

    pr = sub.add_parser("receta", help="Imprime clone→setup→usar→rm")
    pr.add_argument("--id", required=True, help="manim | handraw-estilo | pintura-cpu")
    pr.set_defaults(func=_cmd_receta)

    pv = sub.add_parser("validar", help="Valida el JSON")
    pv.add_argument("--json", action="store_true")
    pv.set_defaults(func=_cmd_validar)

    pres = sub.add_parser("resolver", help="Alias → id canónico")
    pres.add_argument("nombre")
    pres.add_argument("--json", action="store_true")
    pres.set_defaults(func=_cmd_resolver)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
