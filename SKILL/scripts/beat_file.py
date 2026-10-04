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
                  "beats": [0.0, 0.5, ...]}, ...]}

Uso:
  python3 scripts/beat_file.py --bpm 120 --duracion 30 -o beats.json
  python3 scripts/beat_file.py --bpm 100 --beat0 0.25 --duracion 51 \
      --seccion "intro:0:8" --seccion "drop:24:51" -o beats.json
"""
import argparse
import json


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bpm", type=float, required=True, help="tempo en BPM")
    ap.add_argument("--beat0", type=float, default=0.0,
                    help="tiempo del primer beat en segundos (default 0.0)")
    ap.add_argument("--duracion", type=float, required=True,
                    help="duracion total en segundos")
    ap.add_argument("--seccion", action="append", default=[],
                    metavar="NOMBRE:INICIO:FIN",
                    help="seccion nombrada; repetir por seccion")
    ap.add_argument("-o", "--salida", required=True, help="JSON de salida")
    a = ap.parse_args()

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

    doc = {"bpm": round(a.bpm, 2), "beat0": round(a.beat0, 3),
           "duracion": round(a.duracion, 2), "beats": beats,
           "secciones": secciones}
    with open(a.salida, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
    print(f"OK {a.salida}: {len(beats)} beats a {a.bpm} BPM, "
          f"{len(secciones)} secciones")


if __name__ == "__main__":
    main()
