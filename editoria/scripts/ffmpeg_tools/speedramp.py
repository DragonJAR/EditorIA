#!/usr/bin/env python3
"""Recorre distintas velocidades constantes a lo largo del timeline (speed ramp).

Toma una lista de piezas --segment INICIO-FIN:FACTOR que cubren el clip de
principio a fin sin huecos ni traslapes, cada una reproducida a su propia
velocidad constante (audio conservando el tono), y las concatena de nuevo:
el clasico "acelera, luego baja la velocidad para el momento fuerte, luego
acelera de nuevo". Es una serie de segmentos constantes, no una curva
continua: donde la rampa debe entrar o salir es decision del que edita,
expresada aqui como limites de segmentos.

Ejemplos:
  python3 speedramp.py accion.mp4 --segment 0-3:1.0 --segment 3-4:0.25 --segment 4-8:2.0
  python3 speedramp.py clip.mp4 --segment 0-2:2.0 --segment 2-6:1.0
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _comun import (add_common, apply_common, aac_args, default_output, die,
                    emit, ffmpeg_base, info, probe, run, video_args)

MAX_SPEED = 20.0
MIN_SPEED = 0.05


def atempo_chain(factor):
    """atempo acepta 0.5..100 por instancia; encadena para factores fuera de ese rango."""
    parts = []
    remaining = factor
    while remaining < 0.5:
        parts.append("atempo=0.5")
        remaining /= 0.5
    while remaining > 100.0:
        parts.append("atempo=100.0")
        remaining /= 100.0
    parts.append(f"atempo={remaining:.6f}")
    return ",".join(parts)


def parse_segment(raw):
    """'INICIO-FIN:FACTOR' -> (inicio, fin, factor), con validaciones."""
    try:
        span, factor_s = raw.split(":")
        start_s, end_s = span.split("-")
        start, end, factor = float(start_s), float(end_s), float(factor_s)
    except ValueError:
        die(f"--segment debe verse como INICIO-FIN:FACTOR, recibido '{raw}'")
    if end <= start:
        die(f"--segment {raw}: el FIN debe ser mayor que el INICIO")
    if not MIN_SPEED <= factor <= MAX_SPEED:
        die(f"--segment {raw}: FACTOR debe estar en {MIN_SPEED}..{MAX_SPEED}")
    return start, end, factor


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="video a procesar")
    ap.add_argument("-o", "--output", help="archivo de salida (default: <nombre>_ramp.<ext>)")
    ap.add_argument("--segment", action="append", required=True, dest="segments",
                    help=f"INICIO-FIN:FACTOR, repetible; los segmentos deben cubrir 0..duracion "
                         f"sin huecos ni traslapes, en orden. FACTOR en {MIN_SPEED}..{MAX_SPEED} "
                         f"(2.0 = doble de rapido, 0.5 = mitad de velocidad)")
    ap.add_argument("--crf", type=int, default=18, help="CRF de x264 (default 18)")
    ap.add_argument("--preset", default="medium", help="preset de x264 (default medium)")
    add_common(ap)
    args = ap.parse_args()
    apply_common(args)

    segments = [parse_segment(s) for s in args.segments]
    segments.sort(key=lambda s: s[0])
    meta = probe(args.input)
    if not meta.get("video"):
        die("el input no tiene stream de video")
    dur = meta.get("duration") or 0.0
    if abs(segments[0][0] - 0.0) > 0.01:
        die(f"los segmentos deben empezar en 0, el primero empieza en {segments[0][0]:g}")
    if abs(segments[-1][1] - dur) > 0.5:
        die(f"los segmentos deben cubrir todo el clip (0..{dur:.3f}), "
            f"el ultimo termina en {segments[-1][1]:g}")
    for i in range(len(segments) - 1):
        if abs(segments[i][1] - segments[i + 1][0]) > 0.01:
            die(f"los segmentos deben ser continuos sin hueco ni traslape: el segmento {i} "
                f"termina en {segments[i][1]:g}, el segmento {i + 1} empieza en {segments[i + 1][0]:g}")
    has_audio = bool(meta.get("audio"))
    output = args.output or default_output(args.input, "ramp")

    vparts, aparts, labels = [], [], []
    for i, (start, end, factor) in enumerate(segments):
        vlabel, alabel = f"v{i}", f"a{i}"
        end_expr = f"{end:.3f}" if i < len(segments) - 1 else None
        trim = f"trim=start={start:.3f}" + (f":end={end_expr}" if end_expr else "")
        vparts.append(f"[0:v]{trim},setpts=(PTS-STARTPTS)/{factor:.6f}[{vlabel}]")
        labels.append(f"[{vlabel}]")
        if has_audio:
            atrim = f"atrim=start={start:.3f}" + (f":end={end_expr}" if end_expr else "")
            aparts.append(f"[0:a]{atrim},asetpts=PTS-STARTPTS,{atempo_chain(factor)}[{alabel}]")

    if has_audio:
        concat_inputs = "".join(f"[v{i}][a{i}]" for i in range(len(segments)))
        fc = ";".join(vparts + aparts) + f";{concat_inputs}concat=n={len(segments)}:v=1:a=1[outv][outa]"
        maps = ["-map", "[outv]", "-map", "[outa]"]
    else:
        concat_inputs = "".join(f"[v{i}]" for i in range(len(segments)))
        fc = ";".join(vparts) + f";{concat_inputs}concat=n={len(segments)}:v=1:a=0[outv]"
        maps = ["-map", "[outv]"]

    cmd = ffmpeg_base() + ["-i", args.input, "-filter_complex", fc] + maps
    cmd += video_args(meta, args.crf, args.preset)
    cmd += ["-fps_mode", "cfr", "-r", f"{meta['video'].get('fps') or 30.0:g}"]
    cmd += aac_args() if has_audio else ["-an"]
    cmd.append(output)
    run(cmd)

    result = probe(output, role="output")
    v = result["video"]
    info(f"escribi {output} ({result['duration']:.3f}s, {v['width']}x{v['height']}, "
         f"{len(segments)} segmentos de velocidad)")
    if args.json:
        emit(output)
    else:
        print(f"OK {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
