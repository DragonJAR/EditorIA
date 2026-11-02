#!/usr/bin/env python3
"""Genera capitulos de YouTube (MM:SS titulo) desde un plan de EditorIA.

Lee plan.json (render_plan.py: {escenas: [{tipo, from, to, ...}]}) o
shorts-plan.json ({segmentos: [{id, from, to, ...}]}) y emite el texto listo
para pegar en la descripcion del video.

El titulo de cada capitulo sale del campo `titulo`/`capitulo` si existe;
si no, del `tipo` (plan) o `id` (shorts) humanizado. Reglas de YouTube que
valida: el primero en 00:00, minimo 3 capitulos, cada uno de al menos 10s.

Ejemplos:
  python3 chapters.py plan.json -o capitulos.txt
  python3 chapters.py shorts-plan.json --tipo shorts
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg_tools"))
from _comun import asegurar_padre, leer_json  # noqa: E402


def fmt_tiempo(s):
    """Convierte segundos a formato YouTube `H:MM:SS` o `MM:SS`.

    YouTube exige el primer capítulo en `00:00`. Si `s` es negativo o
    no-numérico, se redondea a 0.
    """
    s = max(0, int(round(s)))
    h, r = divmod(s, 3600)
    m, sec = divmod(r, 60)
    if h:
        return f"{h}:{m:02d}:{sec:02d}"
    return f"{m:02d}:{sec:02d}"


def humanizar(txt):
    """Convierte un identificador `snake_case` o `kebab-case` en un título legible.

    - Reemplaza `_` y `-` por espacio
    - Quita espacios al borde
    - Capitaliza la primera letra
    """
    return str(txt).replace("_", " ").strip().capitalize()


def capitulos_desde_plan(plan):
    """Extrae capítulos de un `plan.json` (formato render_plan).

    Lee `plan.escenas[]` y devuelve `[(tiempo_seg, titulo), ...]`.
    El título sale de `titulo`/`capitulo` si existe; si no, del `tipo`
    de la escena humanizado (ej. `apertura` → `Apertura`).
    """
    escenas = plan.get("escenas") or []
    caps = []
    for i, e in enumerate(escenas):
        titulo = e.get("titulo") or e.get("capitulo") or humanizar(e.get("tipo", f"escena {i+1}"))
        try:
            t = float(e.get("from", 0))
        except (TypeError, ValueError):
            t = 0.0
        caps.append((t, titulo))
    return caps


def capitulos_desde_shorts(plan):
    """Extrae capítulos de un `shorts-plan.json`.

    El short final concatena los segmentos EN ORDEN DE ARCHIVO: los tiempos
    de capítulo son acumulativos sobre la salida, no los `from` de la fuente.
    """
    segs = plan.get("segmentos") or []
    caps = []
    t = 0.0
    for i, s in enumerate(segs):
        titulo = s.get("titulo") or humanizar(s.get("id", f"segmento {i+1}"))
        caps.append((t, titulo))
        try:
            dur = float(s.get("to", 0)) - float(s.get("from", 0))
        except (TypeError, ValueError):
            dur = 0.0
        t += max(0.0, dur)
    return caps


def main():
    """CLI: lee un plan, emite capítulos de YouTube a stdout o a archivo.

    Reglas validadas (YouTube):
    - El primer capítulo debe ser `00:00` (se fuerza si arranca después).
    - Mínimo 3 capítulos para que YouTube los muestre.
    - Cada capítulo debe durar al menos 10s (se avisa si no).
    """
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan", help="plan.json o shorts-plan.json")
    ap.add_argument("--tipo", choices=["plan", "shorts", "auto"], default="auto",
                    help="tipo de plan (default: autodetectar)")
    ap.add_argument("-o", "--output", help="archivo de salida (default: stdout)")
    args = ap.parse_args()

    plan = leer_json(args.plan, "el plan")

    tipo = args.tipo
    if tipo == "auto":
        tipo = "shorts" if "segmentos" in plan else "plan"
    caps = (capitulos_desde_shorts(plan) if tipo == "shorts"
            else capitulos_desde_plan(plan))
    if not caps:
        sys.exit("el plan no trae escenas/segmentos con tiempos")

    # Normalizar: el primer capitulo siempre arranca en 00:00.
    if caps[0][0] > 0.5:
        print(f"aviso: el primer capitulo arranca en {fmt_tiempo(caps[0][0])}; "
              "YouTube exige 00:00 -> se fuerza a 00:00", file=sys.stderr)
        caps[0] = (0.0, caps[0][1])

    avisos = []
    if len(caps) < 3:
        avisos.append("YouTube necesita minimo 3 capitulos para mostrarlos")
    for (t1, _), (t2, _) in zip(caps, caps[1:]):
        if t2 - t1 < 10:
            avisos.append(f"capitulo de menos de 10s entre {fmt_tiempo(t1)} y {fmt_tiempo(t2)}")
    for a in avisos:
        print(f"aviso: {a}", file=sys.stderr)

    lineas = [f"{fmt_tiempo(t)} {titulo}" for t, titulo in caps]
    out = "\n".join(lineas) + "\n"
    if args.output:
        asegurar_padre(args.output)
        open(args.output, "w", encoding="utf-8").write(out)
        print(f"escribi {args.output} ({len(caps)} capitulos)", file=sys.stderr)
    else:
        print(out, end="")


if __name__ == "__main__":
    main()
