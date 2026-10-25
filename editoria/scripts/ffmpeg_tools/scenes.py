#!/usr/bin/env python3
"""Encuentra cambios de escena y momentos fuertes, y propone candidatos a
highlights para planear una edicion o un resumen sin ver el archivo completo.

Los cortes vienen del scdet de ffmpeg; los picos de energia, de una
envolvente RMS del audio cada 0.5 s. Los candidatos a highlights son escenas
ordenadas por --rank-by: "audio" (default, las mas fuertes primero) o
"duration" (las mas largas primero). Ambas son aproximaciones, no un juicio
de lo que importa: "audio" puede pasar por alto un momento silencioso pero
importante, y "duration" solo encuentra tomas largas. Ninguna reemplaza
mirar el contact sheet (--sheet) antes de comprometerse con un corte.

Ejemplos:
  python3 scenes.py charla.mp4
  python3 scenes.py evento.mp4 --highlights 5 --target 60
  python3 scenes.py evento.mp4 --highlights 4 --edl cortes.txt
  python3 scenes.py evento.mp4 --sheet escenas.png
  python3 scenes.py charla.mp4 --highlights 5 --rank-by duration
"""
import argparse
import math
import os
import re
import struct
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _comun import (add_common, apply_common, default_font_file, die, emit,
                    escape_filter_path, ffmpeg_base, info, print_json, probe,
                    require_tool, run)

SCORE_RE = re.compile(r"frame:(\d+)\s+pts:\d+\s+pts_time:([0-9.]+)")


def _asegurar_padre(ruta):
    """Crea la carpeta destino de una salida si no existe.

    Sin esto, ffmpeg muere con un codigo opaco (251) porque no puede abrir
    el archivo: el fallo es de la ruta, no del video.
    """
    padre = os.path.dirname(os.path.abspath(ruta))
    try:
        os.makedirs(padre, exist_ok=True)
    except OSError as ex:
        die(f"no se pudo crear la carpeta de salida {padre}: {ex}")


def detect_scenes(path, threshold, min_len, duration, ratio=3.0):
    """Cortes = frames cuyo score de scdet supera `threshold` Y destaca de su
    vecindario (score > ratio x mediana de los +-12 frames cercanos). El
    movimiento sostenido, flashes y paneos rapidos suben el score en muchos
    frames seguidos y se rechazan; un corte real es un pico de un frame."""
    ffmpeg = require_tool("ffmpeg")
    proc = subprocess.run(
        [ffmpeg, "-hide_banner", "-nostdin", "-i", path, "-an", "-vf",
         "scale=320:-2,scdet=threshold=0:sc_pass=1,metadata=print:file=-",
         "-f", "null", "-"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    times, scores, cur_t = [], [], None
    for line in proc.stdout.splitlines():
        m = SCORE_RE.match(line)
        if m:
            cur_t = float(m.group(2))
            continue
        if line.startswith("lavfi.scd.score=") and cur_t is not None:
            try:
                times.append(cur_t)
                scores.append(float(line.split("=", 1)[1]))
            except ValueError:
                pass
    cuts = [0.0]
    if not scores:
        return cuts
    w = 12
    for i, sc in enumerate(scores):
        if sc < threshold:
            continue
        lo, hi = max(0, i - w), min(len(scores), i + w + 1)
        neigh = sorted(scores[lo:i] + scores[i + 1:hi])
        med = neigh[len(neigh) // 2] if neigh else 0.0
        if sc < ratio * max(med, 0.5):
            continue
        if any(scores[j] > sc for j in range(max(0, i - 2), min(len(scores), i + 3)) if j != i):
            continue
        t = times[i]
        if t - cuts[-1] >= min_len:
            cuts.append(t)
    if duration - cuts[-1] < min_len and len(cuts) > 1:
        cuts.pop()
    return cuts


def audio_envelope(path, step_s):
    """Envolvente RMS del audio, una muestra cada `step_s` segundos."""
    ffmpeg = require_tool("ffmpeg")
    proc = subprocess.run(
        [ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-i", path,
         "-vn", "-ac", "1", "-ar", "8000", "-f", "s16le", "-"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    n = len(proc.stdout) // 2
    if n == 0:
        return []
    samples = struct.unpack(f"<{n}h", proc.stdout[: n * 2])
    step = max(1, int(8000 * step_s))
    env = []
    for i in range(0, n, step):
        block = samples[i:i + step]
        env.append(math.sqrt(sum(x * x for x in block) / len(block)) / 32768.0)
    return env


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="video a analizar")
    ap.add_argument("--threshold", type=float, default=8.0,
                    help="score minimo de scdet para un corte, 0-100 (default 8)")
    ap.add_argument("--ratio", type=float, default=3.0,
                    help="el corte debe superar este multiplo de la mediana vecina (default 3; menor = mas cortes)")
    ap.add_argument("--min-scene", type=float, default=1.0,
                    help="ignora cortes a menos de estos segundos (default 1)")
    ap.add_argument("--highlights", type=int, default=0,
                    help="numero de rangos highlight a proponer")
    ap.add_argument("--rank-by", choices=["audio", "duration"], default="audio",
                    help="como ordenar escenas para --highlights: energia de audio (default) o duracion")
    ap.add_argument("--target", type=float,
                    help="con --highlights: segundos totales que deben sumar los elegidos (recorta escenas largas)")
    ap.add_argument("--max-scene", type=float, default=15.0,
                    help="maximo de segundos por rango highlight (default 15)")
    ap.add_argument("--edl", help="escribe los rangos highlight como lineas START-END")
    ap.add_argument("--sheet", help="escribe un contact sheet PNG con el primer frame de cada escena")
    ap.add_argument("--no-timecode", action="store_true",
                    help="--sheet sin el sello de timecode quemado")
    add_common(ap)
    args = ap.parse_args()
    apply_common(args)

    meta = probe(args.input)
    if not meta.get("video"):
        die("el input no tiene stream de video")
    dur = meta.get("duration") or 0.0
    cuts = detect_scenes(args.input, args.threshold, args.min_scene, dur, args.ratio)
    bounds = cuts + [dur]
    step_s = 0.5
    env = audio_envelope(args.input, step_s) if meta.get("audio") else []

    scenes = []
    for i in range(len(bounds) - 1):
        s, e = bounds[i], bounds[i + 1]
        if e - s <= 0.05:
            continue
        seg = env[int(s / step_s): max(int(s / step_s) + 1, int(e / step_s))] if env else []
        energy = (sum(seg) / len(seg)) if seg else 0.0
        peak = max(seg) if seg else 0.0
        scenes.append({"index": len(scenes), "start": round(s, 3), "end": round(e, 3),
                       "duration": round(e - s, 3), "audio_rms": round(energy, 4),
                       "audio_peak": round(peak, 4)})
    peaks = []
    if env:
        thr = sorted(env)[int(len(env) * 0.9)] if len(env) > 10 else max(env)
        for i, val in enumerate(env):
            if val >= thr and val > 0.02 and (i == 0 or env[i - 1] < val) and \
                    (i == len(env) - 1 or env[i + 1] <= val):
                peaks.append({"time": round(i * step_s, 2), "rms": round(val, 4)})
        peaks = sorted(peaks, key=lambda p: -p["rms"])[:20]
        peaks.sort(key=lambda p: p["time"])

    result = {"file": args.input, "duration": round(dur, 3), "scene_count": len(scenes),
              "scenes": scenes, "audio_peaks": peaks}
    info(f"{len(scenes)} escenas, {len(peaks)} picos de audio en {dur:.1f}s")

    if args.highlights:
        if args.rank_by == "duration":
            rank_key = lambda sc: (-sc["duration"], sc["start"])
        else:
            rank_key = lambda sc: (-sc["audio_rms"], sc["start"])
        ranked = sorted(scenes, key=rank_key)[: args.highlights]
        picks = []
        budget = args.target if args.target else None
        per = (budget / max(1, len(ranked))) if budget else args.max_scene
        for sc in ranked:
            length = min(sc["duration"], per, args.max_scene)
            best_s = sc["start"]  # toma la ventana mas fuerte dentro de la escena
            if env and length < sc["duration"]:
                best, best_s = -1.0, sc["start"]
                win = max(1, int(length / step_s))
                lo = int(sc["start"] / step_s)
                hi = max(int(sc["start"] / step_s) + 1, int(sc["end"] / step_s) - win)
                for i in range(lo, hi + 1):
                    val = sum(env[i:i + win])
                    if val > best:
                        best, best_s = val, i * step_s
            picks.append((round(best_s, 2), round(min(sc["end"], best_s + length), 2)))
        picks.sort()
        result["highlights"] = [{"start": s, "end": e, "duration": round(e - s, 2)}
                                for s, e in picks]
        result["highlights_total"] = round(sum(e - s for s, e in picks), 2)
        result["highlights_rank_by"] = args.rank_by
        info(f"propuse {len(picks)} rangos highlight que suman {result['highlights_total']:.1f}s")
        if args.edl:
            _asegurar_padre(args.edl)
            with open(args.edl, "w", encoding="utf-8") as fh:
                for s, e in picks:
                    fh.write(f"{s:.2f}-{e:.2f}\n")
            info(f"guarde {args.edl}")

    if args.sheet:
        _asegurar_padre(args.sheet)
        n = len(scenes)
        cols = min(4, max(1, n))
        rows = max(1, math.ceil(n / cols))
        tile_w = 1280 // cols // 2 * 2
        fps = meta["video"].get("fps") or 30.0
        expr = "+".join(f"eq(n\\,{int(round(sc['start'] * fps))})" for sc in scenes)
        stamp = ""
        if not args.no_timecode:
            default_font = default_font_file("DejaVu Sans")
            font_prefix = f"fontfile={escape_filter_path(default_font)}:" if default_font else ""
            stamp = (f",drawtext=text='%{{pts\\:hms}}':{font_prefix}fontcolor=white:"
                     f"fontsize=h/14:box=1:boxcolor=black@0.55:boxborderw=4:x=6:y=6")
        vf = (f"select='{expr}',scale={tile_w}:-2{stamp},"
              f"tile={cols}x{rows}:padding=2:margin=2:color=0x202020")
        run(ffmpeg_base(texto=True) + ["-i", args.input, "-vf", vf, "-frames:v", "1",
                                      "-fps_mode", "vfr", args.sheet])
        info(f"escribi {args.sheet}")
        result["sheet"] = args.sheet

    if args.json:
        emit(None, **result)
    else:
        print_json(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
