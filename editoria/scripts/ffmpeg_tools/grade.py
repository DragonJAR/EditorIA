#!/usr/bin/env python3
"""Aplica el grade de marca a un footage: el "pegamento" de color que unifica
ambos lados de un corte (ver references/modos-produccion.md: "Color como pegamento").

Marca-blanca: este modulo define SOLO la paleta base del grade (neutra,
sutil y determinista). La tinta de marca se aplica desde el brand pack que
recibe el script que llama (ver aplicar_brand en render_plan.py o
load_brand en _comun). Ningún pack se asume si no se pide.

El grade es sutil: negros con cuerpo, contraste suave, calidez leve en
sombras. La misma receta siempre da el mismo look, asi el footage y la
animacion de marca cortan sin salto. No es un look agresivo de cine.

Ejemplos:
  python3 grade.py toma.mp4 -o toma_grade.mp4
  python3 grade.py toma.mp4 --intensidad 0.4 -o toma_grade.mp4
  python3 grade.py toma.mp4 --sin-vineta -o toma_grade.mp4
  python3 grade.py hdr_iphone.mov --to-sdr -o toma_sdr.mp4
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _comun import (add_common, apply_common, default_output, die, emit, info,
                    probe, run, verify_output, ffmpeg_base, video_args)


def filtro_tosdr():
    # HDR (PQ/HLG/BT.2020) -> SDR BT.709. Sin esto, gradear un HDR por el
    # path SDR aplana los colores: el tonemap es obligatorio, no opcional.
    return ("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,"
            "tonemap=hable:desat=0,zscale=t=bt709:m=bt709:range=tv,format=yuv420p")


def filtro_grade(intensidad, vineta, hdr=False):
    k = max(0.0, min(1.0, intensidad))
    contraste = 1.0 + 0.10 * k
    saturacion = 1.0 + 0.12 * k
    brillo = -0.02 * k
    # calidez leve en sombras/medios (tinta de marca, sutil)
    rs, gs, bs = 0.08 * k, -0.02 * k, -0.05 * k
    rm, gm, bm = 0.03 * k, 0.0, -0.02 * k
    vf = (f"eq=contrast={contraste:.3f}:saturation={saturacion:.3f}:brightness={brillo:.3f},"
          f"colorbalance=rs={rs:.3f}:gs={gs:.3f}:bs={bs:.3f}:"
          f"rm={rm:.3f}:gm={gm:.3f}:bm={bm:.3f}")
    if vineta:
        vf += ",vignette=PI/5"
    # HDR se gradea en 10-bit con sus etiquetas de color intactas (video_args
    # lo saca como HEVC Main10); jamas se aplana a 8-bit sin tonemap.
    return vf + (",format=yuv420p10le" if hdr else ",format=yuv420p")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="video a gradear")
    ap.add_argument("-o", "--output", help="video de salida (default: <input>_grade.mp4)")
    ap.add_argument("--intensidad", type=float, default=0.6,
                    help="fuerza del grade 0.0-1.0 (default 0.6)")
    ap.add_argument("--sin-vineta", action="store_true",
                    help="desactiva la vineta sutil")
    ap.add_argument("--to-sdr", action="store_true",
                    help="si el input es HDR, lo convierte a SDR BT.709 (tonemap) "
                         "antes de gradear; sin esto el HDR se conserva en 10-bit")
    ap.add_argument("--crf", type=int, default=18, help="CRF de salida (default 18)")
    add_common(ap)
    args = ap.parse_args()
    apply_common(args)

    if not os.path.isfile(args.input):
        die(f"no existe el archivo: {args.input}")
    if not (0.0 <= args.intensidad <= 1.0):
        die("--intensidad debe estar entre 0.0 y 1.0")

    meta = probe(args.input)
    if not meta.get("video"):
        die("el input no tiene stream de video")

    output = args.output or default_output(args.input, "_grade")
    hdr = bool(meta["video"].get("hdr"))
    vf = ""
    if args.to_sdr:
        if hdr:
            vf = filtro_tosdr() + ","
            info("HDR detectado: tonemap a SDR BT.709 antes del grade")
            hdr = False
        else:
            info("el input no es HDR; --to-sdr no cambia nada")
    vf += filtro_grade(args.intensidad, not args.sin_vineta, hdr=hdr)
    cmd = ffmpeg_base() + ["-i", args.input, "-vf", vf, "-map", "0:v"]
    if meta.get("audio"):
        cmd += ["-map", "0:a", "-c:a", "copy"]
    else:
        cmd += ["-an"]
    # si se hizo tonemap, el output es SDR aunque el input fuera HDR
    out_meta = {"video": dict(meta["video"], hdr=hdr)}
    cmd += video_args(out_meta, crf=args.crf) + [output]
    run(cmd)
    verify_output(output)
    modo = "SDR (tonemap)" if (args.to_sdr and meta["video"].get("hdr")) else ("HDR 10-bit" if hdr else "SDR")
    info(f"OK {output} (grade marca, intensidad {args.intensidad}, {modo})")
    emit(output, intensidad=args.intensidad, hdr=hdr,
         sdr=bool(args.to_sdr and meta["video"].get("hdr")))


if __name__ == "__main__":
    main()
