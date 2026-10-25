#!/usr/bin/env python3
"""Crea el beat file canonico (metodo apoorvjain25 / coleccion Opus 5.5).

El beat file es la fuente de verdad que leen la musica generada por codigo
Y los visuales: cada evento en pantalla cae sobre un golpe de la musica en
el mismo frame porque ambos consumen este archivo. Es el camino inverso a
beat_grid.py (que ANALIZA musica ya hecha): aqui el beat se AUTORA primero
y todo lo demas lo consume.

Formato JSON (claves bpm/beat0 compatibles con beat_grid.py):
  {"bpm": 120.0, "beat0": 0.0, "duracion": 30.0,
   "beats": [0.0, 0.5, 1.0, ...],
   "secciones": [{"nombre": "intro", "inicio": 0.0, "fin": 8.0,
                  "beats": [0.0, 0.5, ...]}, ...],
   "picos": [{"t": 1.5, "fuerza": 1.0, "db": 0.0}, ...]}

`picos` son los instantes donde la musica PEGA: los candidatos a impacto
para los SFX (un golpe de bajo, un stab, un acople fuera del compas). En
una musica ya hecha se MEDEN con `beat_grid.py`; aqui se DECLARAN a mano
con `--pico SEGUNDOS`. Mismo formato, mismo consumidor.

Uso:
  python3 scripts/beat_file.py --bpm 120 --duracion 30 -o beats.json
  python3 scripts/beat_file.py --bpm 100 --beat0 0.25 --duracion 51 \
      --seccion "intro:0:8" --seccion "drop:24:51" -o beats.json
  python3 scripts/beat_file.py --bpm 100 --duracion 51 --pico 12.5 -o beats.json
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg_tools"))
from _comun import asegurar_padre  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bpm", type=float, required=True, help="tempo en BPM")
    ap.add_argument("--beat0", type=float, default=0.0,
                    help="tiempo del primer beat en segundos (default 0.0)")
    ap.add_argument("--duracion", type=float, required=True,
                    help="duracion total en segundos")
    ap.add_argument("--seccion", action="append", default=[], metavar="NOMBRE:INICIO:FIN",
                    help="seccion nombrada; repetir por seccion")
    ap.add_argument("--pico", action="append", default=[], metavar="SEGUNDOS",
                    help="instante de un transitorio declarado a mano; repetir por pico "
                         "(los candidatos a impacto que se miden con beat_grid.py)")
    ap.add_argument("-o", "--salida", required=True, help="JSON de salida")
    a = ap.parse_args()
    if a.bpm <= 0:
        ap.error(f"--bpm debe ser mayor que 0 (recibido: {a.bpm})")
    if a.duracion <= 0:
        ap.error(f"--duracion debe ser mayor que 0 (recibido: {a.duracion})")
    asegurar_padre(a.salida)

    paso = 60.0 / a.bpm
    beats = []
    t = a.beat0
    while t <= a.duracion + 1e-9:
        beats.append(round(t, 3))
        t += paso

    secciones = []
    for s in a.seccion:
        try:
            nombre, ini, fin = s.split(":")
            ini, fin = float(ini), float(fin)
        except ValueError:
            ap.error(f"--seccion mal formada: {s!r} (usa NOMBRE:INICIO:FIN)")
        secciones.append({
            "nombre": nombre,
            "inicio": ini,
            "fin": fin,
            "beats": [b for b in beats if ini - 1e-9 <= b <= fin + 1e-9],
        })

    picos = []
    for p in a.pico:
        try:
            t = float(p)
        except ValueError:
            ap.error(f"--pico mal formado: {p!r} (usa segundos)")
        picos.append({"t": round(t, 3), "fuerza": 1.0, "db": 0.0})

    doc = {"bpm": round(a.bpm, 2), "beat0": round(a.beat0, 3),
           "duracion": round(a.duracion, 2), "beats": beats,
           "secciones": secciones, "picos": picos}
    with open(a.salida, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
    print(f"OK {a.salida}: {len(beats)} beats a {a.bpm} BPM, "
          f"{len(secciones)} secciones, {len(picos)} picos")


if __name__ == "__main__":
    main()
