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


def _cerca(t, rejilla):
    """El punto de la rejilla (ordenada) más cercano a t."""
    import bisect
    i = bisect.bisect_left(rejilla, t)
    cand = [rejilla[j] for j in (i - 1, i) if 0 <= j < len(rejilla)]
    return min(cand, key=lambda b: abs(b - t)) if cand else t


def mapear_at(nodo, f, es_at=False):
    """Aplica f a todo número que viva bajo una clave `at` (también dentro de
    listas y dicts anidados: mensajes, pasos, link…). Un solo recorrido para
    sincronizar y para medir: nunca cuentan entradas distintas."""
    if isinstance(nodo, dict):
        return {k: mapear_at(v, f, es_at or k == "at") for k, v in nodo.items()}
    if isinstance(nodo, list):
        return [mapear_at(v, f, es_at) for v in nodo]
    if es_at and isinstance(nodo, (int, float)) and not isinstance(nodo, bool):
        return f(nodo)
    return nodo


def sincronizar_escenas(escenas, grid, duracion, mover_cortes=True):
    """Edición al ritmo de la música, sobre escenas ya completas (con `at`):
    - cada CORTE entre escenas cae en el "uno" del compás más cercano si está
      a ≤ 1 beat; si no, en el beat más cercano (el inicio y el final del
      video no se tocan);
    - cada ENTRADA (todo número bajo una clave `at`, también dentro de listas
      de mensajes, pasos o notificaciones) cae en el medio beat más cercano:
      corcheas, no negras, para no fundir entradas escalonadas en un mismo
      golpe. El orden se conserva y toda entrada queda dentro de su escena.
    Con mover_cortes=False (hay voz en off ubicada por los tiempos originales
    de cada escena) solo se ajustan las entradas.
    Devuelve (escenas nuevas, informe {cortes, entradas, desvio_max})."""
    beat = 60.0 / grid["bpm"]
    b0 = grid["beat0"]
    c0 = grid.get("compas0", b0)
    n = int((duracion - b0) / beat) + 2
    beats = [b0 + i * beat for i in range(-1, n)]
    medios = [b0 + i * beat / 2 for i in range(-2, 2 * n)]
    compases = [c0 + i * 4 * beat for i in range(-1, n // 4 + 2)]
    escenas = sorted((dict(e) for e in escenas), key=lambda e: e["from"])
    # cortes: el mismo instante para el `to` de una y el `from` de la siguiente
    cortes = sorted({round(e["from"], 3) for e in escenas[1:]}) if mover_cortes else []
    mapa = {}
    for t in cortes:
        uno = _cerca(t, compases)
        nuevo = uno if abs(uno - t) <= beat else _cerca(t, beats)
        mapa[t] = round(nuevo, 3)
    for e in escenas:
        for k in ("from", "to"):
            e[k] = mapa.get(round(e[k], 3), e[k])
    desvio = [abs(mapa[t] - t) for t in cortes]
    entradas = [0]

    def ajustar(e):
        def f(t0):
            t = min(max(_cerca(t0, medios), e["from"]), e["to"] - 0.05)
            desvio.append(abs(t - t0))
            entradas[0] += 1
            return round(t, 3)
        return f
    escenas = [dict(mapear_at({k: v for k, v in e.items() if k not in ("from", "to")}, ajustar(e)),
                    **{"from": e["from"], "to": e["to"]}) for e in escenas]
    return escenas, {"cortes": len(cortes), "entradas": entradas[0], "bpm": grid["bpm"],
                     "desvio_max": round(max(desvio, default=0.0), 3)}


def medir_sincronia(escenas, grid, duracion, fps=30):
    """Qué tan editado al ritmo está un plan, sobre sus tiempos REALES (exactos,
    no detectados en el video: la detección de movimiento llega unos frames
    tarde por los resortes). Tolerancia: ±1 frame.
    - entradas_pct: % de entradas (todo número bajo `at`) en un medio beat;
    - cortes_compas_pct: % de cortes entre escenas en el "uno" de un compás;
    - azar_pct: lo que daría el azar (ventana de ±1 frame cada medio beat).
    Versión de la métrica: 1."""
    beat = 60.0 / grid["bpm"]
    tol = 1.0 / fps
    b0, c0 = grid["beat0"], grid.get("compas0", grid["beat0"])

    def en_rejilla(t, origen, paso):
        k = round((t - origen) / paso)
        return abs(t - (origen + k * paso)) <= tol + 1e-9

    ats = []
    for e in escenas:
        mapear_at({k: v for k, v in e.items() if k not in ("from", "to")},
                  lambda t: ats.append(float(t)) or t)
    cortes = sorted({float(e["from"]) for e in escenas} - {min(float(e["from"]) for e in escenas)})
    ent = sum(en_rejilla(t, b0, beat / 2) for t in ats)
    cmp_ = sum(en_rejilla(t, c0, 4 * beat) for t in cortes)
    return {"entradas": len(ats), "entradas_pct": round(100 * ent / max(1, len(ats)), 1),
            "cortes": len(cortes), "cortes_compas_pct": round(100 * cmp_ / max(1, len(cortes)), 1),
            "azar_pct": round(100 * min(1.0, 2 * tol / (beat / 2)), 1), "bpm": grid["bpm"]}


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
