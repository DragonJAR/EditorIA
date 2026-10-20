#!/usr/bin/env python3
"""Convierte un video horizontal a vertical 1080x1920 (o el formato que se pida).

Dos modos (receta de quick-cut en references/modos-rapidos.md):
  crop   : recorte central al formato objetivo (default; pierde los bordes)
  blur   : el video escalado y difuminado detras, el original nitido al frente
           (pillarbox vivo; no se pierde nada del cuadro)

Ejemplos:
  python3 verticalizar.py charla.mp4 -o charla_v.mp4
  python3 verticalizar.py charla.mp4 --modo blur -o charla_v.mp4
  python3 verticalizar.py charla.mp4 --formato 1080x1920 --crop-y 0.3 -o v.mp4
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _comun import (add_common, apply_common, default_output, die, emit, info,
                    probe, run, verify_output, ffmpeg_base, video_args, aac_args)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="video horizontal de origen")
    ap.add_argument("-o", "--output", help="video de salida (default: <input>_v.mp4)")
    ap.add_argument("--modo", choices=["crop", "blur"], default="crop",
                    help="crop: recorte central (default); blur: fondo difuminado")
    ap.add_argument("--formato", default="1080x1920",
                    help="formato objetivo WxH (default 1080x1920)")
    ap.add_argument("--crop-y", type=float, default=0.5,
                    help="posicion vertical del recorte en modo crop: 0.0 arriba, "
                         "0.5 centro, 1.0 abajo (default 0.5). Util para no "
                         "decapitar al hablante")
    ap.add_argument("--crf", type=int, default=18, help="CRF de salida (default 18)")
    add_common(ap)
    args = ap.parse_args()
    apply_common(args)

    if not os.path.isfile(args.input):
        die(f"no existe el archivo: {args.input}")
    try:
        tw, th = map(int, args.formato.lower().split("x"))
    except ValueError:
        die(f"formato invalido: {args.formato!r} (se esperaba WxH)")
    if not (0.0 <= args.crop_y <= 1.0):
        die("--crop-y debe estar entre 0.0 y 1.0")

    meta = probe(args.input)
    if not meta.get("video"):
        die("el input no tiene stream de video")
    vw, vh = meta["video"]["width"], meta["video"]["height"]
    if (vw, vh) == (tw, th):
        die(f"el video ya esta en {args.formato}")

    output = args.output or default_output(args.input, "_v")
    cmd = ffmpeg_base() + ["-i", args.input]
    if args.modo == "crop":
        # scale para cubrir + crop; crop-y desplaza la ventana vertical
        vf = (f"scale={tw}:{th}:force_original_aspect_ratio=increase,"
              f"crop={tw}:{th}:0:'(in_h-{th})*{args.crop_y}',format=yuv420p")
        cmd += ["-vf", vf, "-map", "0:v"]
        info(f"recorte central a {args.formato} (crop-y={args.crop_y})")
    else:
        # fondo: cubrir + blur + oscurecer; frente: encajar sin recortar
        fc = (f"[0:v]scale={tw}:{th}:force_original_aspect_ratio=increase,"
              f"crop={tw}:{th},gblur=sigma=40,eq=brightness=-0.25[bg];"
              f"[0:v]scale={tw}:-2[fg];"
              f"[bg][fg]overlay=(W-w)/2:(H-h)/2,format=yuv420p[v]")
        cmd += ["-filter_complex", fc, "-map", "[v]"]
        info(f"pillarbox vivo (blur) a {args.formato}")
    if meta.get("audio"):
        cmd += ["-map", "0:a"] + aac_args()
    else:
        cmd += ["-an"]
    cmd += video_args(meta, crf=args.crf) + [output]
    run(cmd)
    v = verify_output(output)
    vv = v.get("video", {})
    info(f"OK {output} ({vv.get('width', '?')}x{vv.get('height', '?')})")
    emit(output, formato=args.formato, modo=args.modo)


if __name__ == "__main__":
    main()
