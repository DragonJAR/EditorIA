#!/usr/bin/env python3
"""Ajusta una lista de tiempos de corte a la rejilla de beats de beat_grid.py.

Cada corte se mueve al beat mas cercano si cae dentro de la ventana
(default: +-25% de la duracion de un beat); si queda fuera, se conserva
intacto y se reporta. Asi los cortes, zooms y overlays caen en los acentos
musicales en vez de hacerlo a ojo.

Entradas de tiempos (una de):
  --cortes 2.5 7.1 12.0        (lista en la linea de comandos)
  --edl cortes.edl             (ajusta los bordes START/END de cada rango)
  --tiempos cortes.json        (JSON: {"cortes": [...]} o lista plana [...])

Salida: JSON {"cortes": [...ajustados], "movimientos": [{t, beat, delta_s}...]}
+ opcionalmente un EDL con los bordes ajustados (--edl-out).

Ejemplos:
  python3 beat_grid.py musica.mp3 --json grid.json
  python3 beat_sync.py grid.json --cortes 2.5 7.1 12.0 -o cortes_sync.json
  python3 beat_sync.py grid.json --edl cortes.edl --edl-out cortes_sync.edl
"""
import argparse
import json
import os
import re
import sys


def beats_hasta(grid, duracion):
    """Genera todos los tiempos de beat de la rejilla hasta `duracion`."""
    beat = 60.0 / grid["bpm"]
    t = grid["beat0"]
    out = []
    while t <= duracion + 1e-9:
        out.append(t)
        t += beat
    return out, beat


def ajustar(t, beats, ventana_s):
    """Devuelve (t_ajustado, beat_elegido, delta)."""
    mejor, mejor_d = None, None
    for b in beats:
        d = abs(b - t)
        if mejor_d is None or d < mejor_d:
            mejor, mejor_d = b, d
        if b > t + ventana_s:
            break
    if mejor is not None and mejor_d <= ventana_s:
        return round(mejor, 3), round(mejor, 3), round(mejor - t, 3)
    return round(t, 3), None, 0.0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("grid", help="grid.json generado por beat_grid.py")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--cortes", nargs="+", type=float,
                     help="tiempos de corte en segundos")
    src.add_argument("--edl", help="EDL (START-END por linea): ajusta sus bordes")
    src.add_argument("--tiempos", help="JSON con lista de tiempos o {'cortes': [...]}")
    ap.add_argument("--ventana", type=float, default=0.25,
                    help="ventana de ajuste como fraccion de beat (default 0.25)")
    ap.add_argument("--duracion", type=float, default=None,
                    help="duracion limite para generar beats (default: la del grid)")
    ap.add_argument("-o", "--output", help="JSON de salida (default: stdout)")
    ap.add_argument("--edl-out", help="escribe los bordes ajustados como EDL")
    args = ap.parse_args()

    if not os.path.isfile(args.grid):
        sys.exit(f"no existe el grid: {args.grid}")
    grid = json.load(open(args.grid, encoding="utf-8"))
    for k in ("bpm", "beat0"):
        if k not in grid:
            sys.exit(f"el grid no trae la clave {k!r} (¿lo genero beat_grid.py?)")
    if not grid["bpm"] > 0:
        sys.exit(f"bpm invalido en el grid: {grid['bpm']!r}")
    if not (0 < args.ventana <= 0.5):
        sys.exit("--ventana debe estar en (0, 0.5]")

    duracion = args.duracion or float(grid.get("duracion", 0)) or 3600.0
    beats, beat_dur = beats_hasta(grid, duracion)
    ventana_s = args.ventana * beat_dur

    es_edl = args.edl is not None
    if args.cortes is not None:
        tiempos = list(args.cortes)
    elif args.tiempos:
        data = json.load(open(args.tiempos, encoding="utf-8"))
        tiempos = data["cortes"] if isinstance(data, dict) else list(data)
    else:
        tiempos = []
        pares = []
        for n, line in enumerate(open(args.edl, encoding="utf-8"), 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            m = re.match(r"^\s*(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*$", line)
            if not m:
                sys.exit(f"{args.edl}:{n}: linea invalida: {line!r}")
            pares.append((float(m.group(1)), float(m.group(2))))
        tiempos = [t for par in pares for t in par]

    ajustados, movimientos = [], []
    for t in tiempos:
        ta, beat, delta = ajustar(t, beats, ventana_s)
        ajustados.append(ta)
        movimientos.append({"t": round(t, 3), "beat": beat, "delta_s": delta})

    movidos = sum(1 for m in movimientos if m["beat"] is not None)
    print(f"rejilla: {grid['bpm']:.2f} BPM, beat {beat_dur:.3f}s, ventana +-{(ventana_s):.3f}s",
          file=sys.stderr)
    print(f"{movidos}/{len(tiempos)} cortes ajustados a beat", file=sys.stderr)
    for m in movimientos:
        if m["beat"] is not None:
            print(f"  {m['t']:.3f}s -> {m['beat']:.3f}s (Δ {m['delta_s']:+.3f}s)",
                  file=sys.stderr)

    if es_edl and args.edl_out:
        its = iter(ajustados)
        caidos = 0
        with open(args.edl_out, "w", encoding="utf-8") as fh:
            for _ in pares:
                s, e = next(its), next(its)
                if e > s:
                    fh.write(f"{s:.3f}-{e:.3f}\n")
                else:
                    caidos += 1
        if caidos:
            print(f"aviso: {caidos} segmento(s) colapsaron al ajustar (fin<=inicio) "
                  "y se omitieron del EDL", file=sys.stderr)
        print(f"escribi {args.edl_out}", file=sys.stderr)

    doc = {"bpm": grid["bpm"], "beat0": grid["beat0"],
           "ventana_s": round(ventana_s, 3),
           "cortes": ajustados, "movimientos": movimientos}
    out = json.dumps(doc, ensure_ascii=False, indent=2)
    if args.output:
        open(args.output, "w", encoding="utf-8").write(out + "\n")
        print(f"escribi {args.output}", file=sys.stderr)
    else:
        print(out)


if __name__ == "__main__":
    main()
