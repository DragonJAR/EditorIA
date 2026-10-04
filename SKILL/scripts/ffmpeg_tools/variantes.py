#!/usr/bin/env python3
"""Batch hook x body: un body x N hooks -> N variantes para A/B test.

Sigue la receta de references/modos-rapidos.md (seccion "Hook x body batch"):

1. Preflight por hook: geometria, fps y timebase contra el body.
2. Join: stream-copy sin perdida si los parametros coinciden; si no,
   re-encode del hook a los parametros del body.
3. Loudness-match: el hook se gana hasta el LUFS integrado del body
   (el hook no puede sonar distinto al cuerpo).
4. Nombres: {proyecto}_hook{n}_{body}.mp4 (solo cambia el numero).

Ejemplos:
  python3 variantes.py hooks/ cuerpo.mp4 --proyecto anuncio
  python3 variantes.py h1.mp4 h2.mp4 h3.mp4 cuerpo.mp4 --proyecto anuncio -o variantes/
"""
import argparse
import glob
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _comun import (add_common, apply_common, default_output, die, emit, info,
                    probe, require_tool, run, verify_output, ffmpeg_base,
                    video_args, aac_args)


def expandir_hooks(args_hooks):
    rutas = []
    for h in args_hooks:
        if os.path.isdir(h):
            rutas += sorted(glob.glob(os.path.join(h, "*.mp4")))
        elif os.path.isfile(h):
            rutas.append(h)
        else:
            die(f"hook no encontrado: {h}")
    if not rutas:
        die("no hay hooks para procesar")
    return rutas


def medir_lufs(path):
    """LUFS integrado via ebur128 (solo medicion, rapido)."""
    ffmpeg = require_tool("ffmpeg")
    cmd = [ffmpeg, "-hide_banner", "-nostdin", "-i", path,
           "-map", "0:a", "-af", "ebur128=peak=true", "-f", "null", "-"]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          text=True)
    m = re.search(r"Integrated loudness:\s*I:\s*(-?\d+(?:\.\d+)?)\s*LUFS",
                  proc.stderr)
    if not m:
        die(f"no se pudo medir LUFS de {path}")
    return float(m.group(1))


def compatibles(hook_meta, body_meta):
    """True si se puede unir con stream-copy (mismo codec, dims, fps)."""
    hv, bv = hook_meta.get("video") or {}, body_meta.get("video") or {}
    return (hv.get("codec") == bv.get("codec")
            and hv.get("width") == bv.get("width")
            and hv.get("height") == bv.get("height")
            and abs((hv.get("fps") or 0) - (bv.get("fps") or 0)) < 0.01
            and bool(hook_meta.get("audio")) == bool(body_meta.get("audio")))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("entradas", nargs="+",
                    help="hooks (archivos o directorios .mp4) y el body como "
                         "ULTIMO argumento")
    ap.add_argument("--proyecto", required=True,
                    help="nombre del proyecto para los outputs")
    ap.add_argument("-o", "--salida-dir", default=".",
                    help="directorio de salida (default: .)")
    ap.add_argument("--crf", type=int, default=18, help="CRF si hay re-encode")
    add_common(ap)
    args = ap.parse_args()
    apply_common(args)

    if len(args.entradas) < 2:
        die("se necesita al menos 1 hook y el body (ultimo argumento)")
    *hooks_in, body = args.entradas
    hooks = expandir_hooks(hooks_in)
    if not os.path.isfile(body):
        die(f"body no encontrado: {body}")
    if body in hooks:
        die("el body tambien aparece como hook")

    body_meta = probe(body)
    if not body_meta.get("video"):
        die("el body no tiene stream de video")
    body_lufs = medir_lufs(body)
    info(f"body: {os.path.basename(body)} ({body_lufs:.1f} LUFS)")
    body_stem = os.path.splitext(os.path.basename(body))[0]
    os.makedirs(args.salida_dir, exist_ok=True)

    resultados = []
    for n, hook in enumerate(hooks, 1):
        hook_meta = probe(hook)
        if not hook_meta.get("video"):
            info(f"hook{n}: sin video, se omite ({hook})")
            continue
        hook_lufs = medir_lufs(hook)
        ganancia = body_lufs - hook_lufs
        info(f"hook{n}: {os.path.basename(hook)} ({hook_lufs:.1f} LUFS -> "
             f"ganancia {ganancia:+.1f} dB)")

        salida = os.path.join(
            args.salida_dir, f"{args.proyecto}_hook{n}_{body_stem}.mp4")
        if args.dry_run:
            print(f"$ join {hook} + {body} -> {salida} "
                  f"(ganancia hook {ganancia:+.1f} dB)")
            resultados.append(salida)
            continue

        if compatibles(hook_meta, body_meta) and abs(ganancia) < 0.5:
            # Join sin perdida: concat demuxer + stream copy.
            lista = salida + ".lst"
            with open(lista, "w", encoding="utf-8") as fh:
                fh.write(f"file '{os.path.abspath(hook)}'\n"
                         f"file '{os.path.abspath(body)}'\n")
            cmd = ffmpeg_base() + ["-f", "concat", "-safe", "0", "-i", lista,
                                   "-c", "copy", "-movflags", "+faststart", salida]
            try:
                run(cmd)
            finally:
                if os.path.exists(lista):
                    os.remove(lista)
            info(f"hook{n}: join stream-copy (sin re-encode)")
        else:
            # Re-encode: hook a parametros del body + ganancia de loudness.
            bv = body_meta["video"]
            af = f"volume={ganancia:.2f}dB" if abs(ganancia) >= 0.1 else "anull"
            vf = (f"scale={bv['width']}:{bv['height']},"
                  f"fps={bv['fps']:.3f},format=yuv420p")
            fc = (f"[0:v]{vf}[hv];[1:v]format=yuv420p[bv];"
                  f"[0:a]{af}[ha];[1:a]anull[ba];"
                  f"[hv][ha][bv][ba]concat=n=2:v=1:a=1[v][a]")
            cmd = (ffmpeg_base() + ["-i", hook, "-i", body,
                                    "-filter_complex", fc,
                                    "-map", "[v]", "-map", "[a]"]
                   + video_args(body_meta, crf=args.crf) + aac_args()
                   + [salida])
            run(cmd)
            info(f"hook{n}: re-encode a parametros del body + loudness-match")
        verify_output(salida)
        resultados.append(salida)

    info(f"OK {len(resultados)} variante(s)")
    for r in resultados:
        print(r)


if __name__ == "__main__":
    main()
