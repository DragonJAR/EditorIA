#!/usr/bin/env python3
"""Captions: detalle de producción (no catálogo paralelo).

La elección es `repertorio.py` (misma superficie que escenas/efectos/gestos).
Este módulo PRODUCE: valida el JSON y emite la receta nativa o HyperFrames
(clone-on-demand / catalog add). No vendoriza repos.

Uso:
  python3 scripts/captions_identidades.py validar
  python3 scripts/captions_identidades.py receta --id cap-rail-karaoke
  python3 scripts/captions_identidades.py receta --id cap-kinetic-slam
  python3 scripts/captions_identidades.py listar [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
DATOS = os.path.join(BASE, "data", "captions_identidades.json")

CAMPOS = ("id", "firma", "preferir", "ocasion", "adaptar", "ruta",
          "intenciones", "keywords")


def cargar(ruta=DATOS):
    with open(ruta, encoding="utf-8") as fh:
        return json.load(fh)


def identidades(datos=None):
    datos = datos or cargar()
    return {c["id"]: c for c in datos.get("identidades", [])}


def validar(datos=None):
    datos = datos or cargar()
    malos = []
    ids = set()
    for c in datos.get("identidades", []):
        cid = c.get("id")
        if not cid:
            malos.append("identidad sin id")
            continue
        if cid in ids:
            malos.append(f"identidad repetida: {cid}")
        ids.add(cid)
        for campo in CAMPOS:
            if campo not in c or c[campo] in (None, "", []):
                malos.append(f"{cid}: falta {campo}")
        pref = c.get("preferir")
        if pref not in ("nativo", "hyperframes"):
            malos.append(f"{cid}: preferir inválido ({pref})")
        if pref == "hyperframes" and c.get("hf_component") is None and cid != "cap-embed-matte":
            # embed-matte es doctrina/matte, no un component del registry
            if "embed" not in cid:
                malos.append(f"{cid}: hyperframes sin hf_component")
        ints = c.get("intenciones") or []
        if not ints:
            malos.append(f"{cid}: sin intenciones")
    esperado = datos.get("conteo")
    if esperado is not None and len(ids) != int(esperado):
        malos.append(f"conteo={esperado} pero hay {len(ids)}")
    modelo = datos.get("modelo") or {}
    for k in ("drop", "rail", "embed"):
        if k not in modelo:
            malos.append(f"modelo: falta '{k}'")
    return malos


def receta(cid, video="entrada.mp4", datos=None):
    """Comandos copiables: nativo (caption.py) o HyperFrames on-demand."""
    datos = datos or cargar()
    fila = identidades(datos).get(cid)
    if not fila:
        raise ValueError(f"identidad desconocida: {cid}")
    lineas = [
        f"# identidad: {cid} · preferir={fila['preferir']}",
        f"# ocasión: {fila.get('ocasion', '')}",
        f"# flujo: references/flujo-talking-head.md",
    ]
    if fila["preferir"] == "nativo":
        ruta = (fila.get("ruta") or "").replace("VIDEO", video)
        lineas.append(ruta)
        lineas.append(
            "# luego: python scripts/ffmpeg_tools/loudness.py con_sub.mp4 "
            "-o final.mp4 -I -14 --tp -1.5"
        )
        return "\n".join(lineas)

    comp = fila.get("hf_component")
    lineas.extend([
        "# Declarar Node 22+ + HyperFrames (references/capacidades.md).",
        "# No vendorizar: skills/registry on-demand.",
        "npx hyperframes skills update   # o: npx -y skills add heygen-com/hyperframes --all -y",
    ])
    if comp:
        lineas.extend([
            f"npx hyperframes catalog --query \"{comp}\" --json",
            f"npx hyperframes add {comp}",
            f"# Wire transcript → composición; componente registry: {comp}",
        ])
    if cid == "cap-embed-matte" or "embed" in cid:
        lineas.extend([
            "# Matte / texto detrás del sujeto:",
            "npx hyperframes remove-background --input " + video + " --output cutout.webm",
            "# Stack: video → caption embed → cutout (z-index); data-layout-allow-occlusion",
            "# Cobertura matte objetivo 30–55 % del word box (references/captions-identidades.md)",
        ])
    lineas.extend([
        "npx hyperframes check --json && npx hyperframes render",
        "# Cierre EditorIA (obligatorio):",
        "python scripts/ffmpeg_tools/loudness.py out.mp4 -o final.mp4 -I -14 --tp -1.5",
        "python scripts/qa_entrega.py final.mp4",
        "python scripts/puntuar.py final.mp4 --ejes \"1=4,2=4,4=4,5=4,7=4\"",
    ])
    return "\n".join(lineas)


def _cmd_validar(args):
    malos = validar()
    if args.json:
        print(json.dumps({"problemas": malos, "n": len(identidades())},
                         ensure_ascii=False, indent=1))
    elif malos:
        print("CAPTIONS CON PROBLEMAS:")
        for m in malos:
            print(f"  - {m}")
    else:
        print(f"CAPTIONS VALIDO: {len(identidades())} identidades "
              f"(elección vía repertorio.py; detalle aquí)")
    return 1 if malos else 0


def _cmd_listar(args):
    datos = cargar()
    filas = list(datos.get("identidades", []))
    if args.json:
        print(json.dumps({"identidades": filas, "modelo": datos.get("modelo")},
                         ensure_ascii=False, indent=1))
    else:
        for c in filas:
            print(f"{c['id']}\t{c['preferir']}\t{c.get('firma', '')}")
    return 0


def _cmd_receta(args):
    try:
        print(receta(args.id, video=args.video))
    except ValueError as ex:
        print(f"ERROR: {ex}", file=sys.stderr)
        return 1
    return 0


def main():
    ap = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = ap.add_subparsers(dest="cmd", required=True)
    ayuda_json = "salida en JSON, para leerla desde otra herramienta"

    p = sub.add_parser("validar", help="integridad del JSON de identidades")
    p.add_argument("--json", action="store_true", help=ayuda_json)
    p.set_defaults(func=_cmd_validar)

    p = sub.add_parser("listar", help="lista identidades (detalle; elegir con repertorio)")
    p.add_argument("--json", action="store_true", help=ayuda_json)
    p.set_defaults(func=_cmd_listar)

    p = sub.add_parser("receta", help="comandos nativos o HyperFrames on-demand")
    p.add_argument("--id", required=True, help="cap-rail-karaoke | cap-kinetic-slam | …")
    p.add_argument("--video", default="entrada.mp4", help="ruta del footage de entrada")
    p.set_defaults(func=_cmd_receta)

    a = ap.parse_args()
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
