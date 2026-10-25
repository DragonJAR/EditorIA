#!/usr/bin/env python3
"""Quita silencios / dead air (jump-cut editing) o solo los lista.

Detecta tramos silenciosos con el filtro silencedetect de ffmpeg, deja un
margen a cada lado para no cortar palabras, ignora huecos mas cortos que
--min-silence y re-encodea en una sola pasada (select/aselect).

Ejemplos:
  python3 silence.py charla.mp4
  python3 silence.py charla.mp4 --threshold -40 --min-silence 1 --margin 0.25
  python3 silence.py charla.mp4 --list          # solo muestra silencios y cortes, no genera nada
  python3 silence.py charla.mp4 --edl cortes.txt
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _comun import (video_args, aac_args, add_common, apply_common, cfr_args, audio_codec_for,
                    asegurar_padre, default_output, die, emit, ffmpeg_base, info, print_json, probe,
                    require_tool, run)

SIL_RE = re.compile(r"silence_(start|end): ([0-9.]+)")


def detect(path, threshold, min_silence):
    """Lista de tuplas (inicio, fin) de silencio en segundos."""
    ffmpeg = require_tool("ffmpeg")
    proc = run([ffmpeg, "-hide_banner", "-nostdin", "-i", path, "-vn", "-af",
                f"silencedetect=noise={threshold}dB:d={min_silence}", "-f", "null", "-"],
               quiet=True, check=False)
    if proc.returncode != 0:
        die(f"silencedetect fallo:\n{proc.stderr.strip()[-800:]}")
    silences = []
    start = None
    for kind, val in SIL_RE.findall(proc.stderr):
        if kind == "start":
            start = float(val)
        elif start is not None:
            silences.append((start, float(val)))
            start = None
    if start is not None:  # el silencio sigue hasta el final
        silences.append((start, float("inf")))
    return silences


def keep_ranges(silences, duration, margin, min_keep):
    """Rangos a conservar, con margen alrededor de cada silencio."""
    keeps = []
    cursor = 0.0
    for s, e in silences:
        s_adj = max(cursor, s + margin)
        if s_adj - cursor >= min_keep:
            keeps.append((cursor, s_adj))
        cursor = min(duration, e - margin) if e != float("inf") else duration
    if duration - cursor >= min_keep:
        keeps.append((cursor, duration))
    return keeps


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="video/audio a procesar")
    ap.add_argument("-o", "--output", help="archivo de salida (default: <nombre>_tight.<ext>)")
    ap.add_argument("--threshold", type=float, default=-35.0,
                    help="nivel de silencio en dBFS (default -35; usa -40..-45 para cuartos silenciosos)")
    ap.add_argument("--min-silence", type=float, default=0.6,
                    help="solo quita huecos de al menos estos segundos (default 0.6)")
    ap.add_argument("--margin", type=float, default=0.15,
                    help="segundos de silencio a conservar a cada lado del habla (default 0.15)")
    ap.add_argument("--min-keep", type=float, default=0.2,
                    help="descarta fragmentos conservados mas cortos que esto (default 0.2)")
    ap.add_argument("--list", action="store_true",
                    help="solo muestra los silencios y los rangos conservados, no genera output")
    ap.add_argument("--edl", help="guarda los rangos conservados (una linea START-END por linea)")
    ap.add_argument("--crf", type=int, default=18, help="CRF de x264 (default 18)")
    ap.add_argument("--preset", default="medium", help="preset de x264 (default medium)")
    add_common(ap)
    args = ap.parse_args()
    apply_common(args)

    meta = probe(args.input)
    if not meta.get("audio"):
        die("el input no tiene stream de audio para analizar")
    duration = meta.get("duration") or 0.0
    silences = detect(args.input, args.threshold, args.min_silence)
    keeps = keep_ranges(silences, duration, args.margin, args.min_keep)
    kept = sum(e - s for s, e in keeps)
    removed = max(0.0, duration - kept)
    summary = {
        "silences": [[round(s, 3), None if e == float("inf") else round(e, 3)] for s, e in silences],
        "keep": [[round(s, 3), round(e, 3)] for s, e in keeps],
        "input_duration": round(duration, 3),
        "kept_duration": round(kept, 3),
        "removed_seconds": round(removed, 3),
    }
    info(f"{len(silences)} silencios, conservando {len(keeps)} rangos: "
         f"{kept:.2f}s de {duration:.2f}s (quitando {removed:.2f}s)")

    if args.edl:
        asegurar_padre(args.edl)
        with open(args.edl, "w", encoding="utf-8") as fh:
            for s, e in keeps:
                fh.write(f"{s:.3f}-{e:.3f}\n")
        info(f"guarde {args.edl}")

    if args.list:
        if args.json:
            emit(None, **summary)
        else:
            print_json(summary)
        return 0
    if not keeps:
        die("nada quedaria conservado; sube --threshold (ej. -45) o revisa el audio")
    if not silences or removed < 0.05:
        info("no se encontro silencio removible; el output seria igual al input")

    output = args.output or default_output(args.input, "tight")
    expr = "+".join(f"between(t,{s:.3f},{e:.3f})" for s, e in keeps)
    vf = f"select='{expr}',setpts=N/FRAME_RATE/TB"
    af = f"aselect='{expr}',asetpts=N/SR/TB"
    cmd = ffmpeg_base() + ["-i", args.input]
    if meta.get("video"):
        cmd += ["-vf", vf] + video_args(meta, args.crf, args.preset) + cfr_args(meta)
        cmd += ["-af", af] + aac_args() + [output]
    else:  # output solo-audio: codec segun el contenedor (wav->pcm, mp3->mp3, ...)
        cmd += ["-vn", "-af", af] + audio_codec_for(output) + [output]
    run(cmd)
    r = probe(output, role="output")
    info(f"escribi {output} ({r['duration']:.3f}s, esperado ~{kept:.3f}s)")
    if args.json:
        emit(output, **summary)
    else:
        print(f"OK {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
