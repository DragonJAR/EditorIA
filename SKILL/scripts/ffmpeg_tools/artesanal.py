#!/usr/bin/env python3
"""Acabado artesanal: el "pegamento" táctil que acerca el video digital al
look hecho a mano que premian los festivales (tendencia 2026: el jurado
premia lo táctil — ver references/dramaturgia.md).

Aplica grano de película temporal, textura de papel, parpadeo sutil de
luminancia y viñeta orgánica. Todo sutil y parametrizable: la idea es que
el ojo sienta material, no filtro.

Ejemplos:
  python scripts/ffmpeg_tools/artesanal.py entrada.mp4 -o salida.mp4
  python scripts/ffmpeg_tools/artesanal.py entrada.mp4 --grano 12 --papel mi_papel.png -o salida.mp4
  python scripts/ffmpeg_tools/artesanal.py entrada.mp4 --sin-parpadeo --sin-papel -o salida.mp4
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _comun import (add_common, apply_common, default_output, die, emit, info,
                    probe, run, verify_output, ffmpeg_base, video_args)
from _plataforma import dir_temp


def generar_papel(w, h, destino):
    """Genera una textura de papel neutra (grano de fibra sutil)."""
    import numpy as np
    from PIL import Image
    rng = np.random.default_rng(7)
    base = np.full((h, w), 128.0)
    fibra = rng.normal(0, 10, (h, w))
    # vetas diagonales cada 7 px
    yy, xx = np.mgrid[0:h, 0:w]
    veta = np.where(((xx + yy) % 7 == 0), rng.normal(0, 6, (h, w)), 0)
    arr = np.clip(base + fibra + veta, 0, 255).astype("uint8")
    Image.fromarray(arr, mode="L").save(destino)
    return destino


def filtro_artesanal(grano, opacidad_papel, parpadeo, vineta, con_papel):
    if con_papel:
        # la textura ya viene al tamaño exacto del video (segundo input)
        inicio = (f"[0:v]noise=alls={grano}:allf=t,format=rgba[bg];"
                  f"[1:v]format=rgba[tx];"
                  f"[bg][tx]blend=all_mode=overlay:all_opacity={opacidad_papel:.2f}")
    else:
        inicio = f"[0:v]noise=alls={grano}:allf=t,format=rgba"
    cola = []
    if parpadeo > 0:
        cola.append(f"eq=brightness='{parpadeo:.3f}*sin(2*PI*t*2.3)'")
    if vineta:
        cola.append("vignette=PI/5")
    cola.append("format=yuv420p")
    return inicio + "," + ",".join(cola) + "[v]"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="video a tratar")
    ap.add_argument("-o", "--output", help="video de salida (default: <input>_artesanal.mp4)")
    ap.add_argument("--grano", type=int, default=8,
                    help="intensidad del grano 0-30 (default 8)")
    ap.add_argument("--papel", default=None,
                    help="textura de papel PNG (default: se genera una neutra)")
    ap.add_argument("--opacidad-papel", type=float, default=0.10,
                    help="opacidad de la textura 0.0-0.5 (default 0.10)")
    ap.add_argument("--parpadeo", type=float, default=0.015,
                    help="amplitud del parpadeo de luminancia (default 0.015; 0 lo apaga)")
    ap.add_argument("--sin-parpadeo", action="store_true")
    ap.add_argument("--sin-papel", action="store_true")
    ap.add_argument("--sin-vineta", action="store_true")
    ap.add_argument("--crf", type=int, default=18, help="CRF de salida (default 18)")
    add_common(ap)
    args = ap.parse_args()
    apply_common(args)

    if not os.path.isfile(args.input):
        die(f"no existe el archivo: {args.input}")
    if not (0 <= args.grano <= 30):
        die("--grano debe estar entre 0 y 30")
    if not (0.0 <= args.opacidad_papel <= 0.5):
        die("--opacidad-papel debe estar entre 0.0 y 0.5")

    meta = probe(args.input)
    if not meta.get("video"):
        die("el input no tiene stream de video")
    vw, vh = meta["video"].get("width", 1080), meta["video"].get("height", 1920)

    papel_path = None
    papel_tmp = None
    if not args.sin_papel:
        if args.papel:
            if not os.path.isfile(args.papel):
                die(f"no existe la textura: {args.papel}")
            papel_path = args.papel
        else:
            papel_tmp = os.path.join(dir_temp(), "editoria_papel.png")
            generar_papel(vw, vh, papel_tmp)
            papel_path = papel_tmp

    output = args.output or default_output(args.input, "_artesanal")
    dur = meta.get("duration") or 0
    cmd = ffmpeg_base() + ["-i", args.input]
    if papel_path:
        # la textura como imagen fija: -t la capa a la duración del video
        # (evita el loop infinito del filtro movie)
        cmd += ["-loop", "1", "-framerate", str(meta["video"].get("fps", 30)),
                "-t", f"{dur:.3f}", "-i", papel_path]
    fc = filtro_artesanal(args.grano, args.opacidad_papel,
                          0 if args.sin_parpadeo else args.parpadeo,
                          not args.sin_vineta, bool(papel_path))
    cmd += ["-filter_complex", fc, "-map", "[v]"]
    if meta.get("audio"):
        cmd += ["-map", "0:a", "-c:a", "copy"]
    else:
        cmd += ["-an"]
    cmd += video_args(meta, crf=args.crf) + [output]
    run(cmd)
    verify_output(output)
    if papel_tmp and os.path.exists(papel_tmp):
        os.remove(papel_tmp)
    info(f"OK {output} (acabado artesanal: grano {args.grano})")
    emit(output, grano=args.grano)


if __name__ == "__main__":
    main()
