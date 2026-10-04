#!/usr/bin/env python3
"""Aplica un EDL (lista de rangos a conservar) a un video: lo corta y
re-ensambla en una sola pasada de ffmpeg, con corte preciso a nivel de frame.

Es el eslabon que cierra la cadena:
  transcribir.py -> retakes.py --edl cortes.edl -> aplicar_edl.py video.mp4 --edl cortes.edl
  silence.py --edl cortes.edl -------------------> aplicar_edl.py video.mp4 --edl cortes.edl

Formato EDL: una linea "START-END" por linea, en segundos (ej. 12.500-18.200).
Rangos fuera de la duracion se recortan con aviso; solapes se fusionan;
lineas vacias o con # se ignoran.

Por defecto aplica micro-fundidos de 0.03s en cada union (suficiente para
evitar clicks de audio y saltos digitales, invisible al ojo: el corte sigue
sintiendose seco, como manda la skill). --suavizar 0 lo desactiva.

Ejemplos:
  python3 aplicar_edl.py charla.mp4 --edl cortes.edl -o charla_cortada.mp4
  python3 aplicar_edl.py charla.mp4 --edl cortes.edl --suavizar 0 --fast -o draft.mp4
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _comun import (add_common, apply_common, default_output, die, emit, info,
                    probe, run, verify_output, video_args,
                    aac_args, ffmpeg_base)

EDL_LINE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*$")


def leer_edl(path):
    """Lee el EDL -> [(start, end)] ordenados y fusionados."""
    segs = []
    with open(path, encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            m = EDL_LINE.match(line)
            if not m:
                die(f"{path}:{n}: linea EDL invalida: {line!r} (se esperaba START-END)")
            s, e = float(m.group(1)), float(m.group(2))
            if e <= s:
                die(f"{path}:{n}: rango invertido o vacio: {line!r}")
            segs.append((s, e))
    if not segs:
        die(f"{path}: el EDL no tiene rangos a conservar")
    segs.sort()
    fusionados = [segs[0]]
    for s, e in segs[1:]:
        ps, pe = fusionados[-1]
        if s <= pe + 1e-6:
            fusionados[-1] = (ps, max(pe, e))
        else:
            fusionados.append((s, e))
    return fusionados


def filtro_concat(segs, suavizar):
    """filter_complex: trim+setpts por segmento, micro-fundidos opcionales, concat."""
    parts = []
    for i, (s, e) in enumerate(segs):
        d = e - s
        f = min(suavizar, d / 2) if suavizar > 0 else 0.0
        vf = f"[0:v]trim=start={s:.3f}:end={e:.3f},setpts=PTS-STARTPTS"
        af = f"[0:a]atrim=start={s:.3f}:end={e:.3f},asetpts=PTS-STARTPTS"
        if f > 0:
            vf += f",fade=t=in:st=0:d={f:.3f},fade=t=out:st={d - f:.3f}:d={f:.3f}"
            af += f",afade=t=in:st=0:d={f:.3f},afade=t=out:st={d - f:.3f}:d={f:.3f}"
        vf += f"[v{i}]"
        af += f"[a{i}]"
        parts.append(vf + ";" + af)
    n = len(segs)
    # concat espera los streams intercalados por segmento: [v0][a0][v1][a1]...
    intercalado = "".join(f"[v{i}][a{i}]" for i in range(n))
    parts.append(f"{intercalado}concat=n={n}:v=1:a=1[v][a]")
    return ";".join(parts)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="video a cortar")
    ap.add_argument("--edl", required=True,
                    help="EDL con rangos a conservar (una linea START-END por linea)")
    ap.add_argument("-o", "--output", help="video de salida (default: <input>_edl.mp4)")
    ap.add_argument("--suavizar", type=float, default=0.03,
                    help="micro-fundido en cada union, en segundos (default 0.03; 0 = corte seco total)")
    ap.add_argument("--fast", action="store_true",
                    help="modo borrador: cortes en keyframes con -c copy (rapido, menos preciso)")
    ap.add_argument("--crf", type=int, default=18, help="CRF de salida (default 18)")
    add_common(ap)
    args = ap.parse_args()
    apply_common(args)

    if not os.path.isfile(args.input):
        die(f"no existe el archivo: {args.input}")
    if not os.path.isfile(args.edl):
        die(f"no existe el EDL: {args.edl}")
    if args.suavizar < 0:
        die("--suavizar no puede ser negativo")

    meta = probe(args.input)
    if not meta.get("video"):
        die("el input no tiene stream de video")
    if not meta.get("audio"):
        die("el input no tiene stream de audio (el EDL conserva A/V juntos)")
    dur = meta.get("duration") or 0.0
    if dur <= 0:
        die("no se pudo medir la duracion del input")

    segs = leer_edl(args.edl)
    recortados = 0
    final = []
    for s, e in segs:
        if s >= dur:
            recortados += 1
            continue
        if e > dur:
            recortados += 1
            e = dur
        if e - s > 0.04:  # menos de ~1 frame a 24fps no aporta
            final.append((s, e))
    if recortados:
        info(f"aviso: {recortados} rango(s) quedaban fuera de la duracion "
             f"({dur:.2f}s) y se recortaron/ignoraron")
    if not final:
        die("ningun rango del EDL cae dentro del video")
    segs = final

    dur_in = sum(e - s for s, e in segs)
    output = args.output or default_output(args.input, "_edl")
    info(f"{len(segs)} segmentos, {dur_in:.2f}s de {dur:.2f}s "
         f"({dur_in / dur * 100:.1f}% conservado)")

    if args.fast:
        # Borrador: corta cada rango con -c copy y concatena (cortes en keyframes).
        import shutil
        import tempfile
        tmpdir = tempfile.mkdtemp(prefix="editoria_edl_")
        try:
            partes = []
            for i, (s, e) in enumerate(segs):
                p = os.path.join(tmpdir, f"p{i:03d}.mp4")
                run(ffmpeg_base() + ["-ss", f"{s:.3f}", "-to", f"{e:.3f}",
                                     "-i", args.input, "-c", "copy", "-y", p],
                    quiet=True)
                partes.append(p)
            lista = os.path.join(tmpdir, "lista.txt")
            with open(lista, "w", encoding="utf-8") as fh:
                for p in partes:
                    fh.write(f"file '{p}'\n")
            run(ffmpeg_base() + ["-f", "concat", "-safe", "0", "-i", lista,
                                 "-c", "copy", "-y", output], quiet=True)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    else:
        fc = filtro_concat(segs, args.suavizar)
        cmd = (ffmpeg_base() + ["-i", args.input, "-filter_complex", fc,
                                "-map", "[v]", "-map", "[a]"]
               + video_args(meta, crf=args.crf) + aac_args() + [output])
        run(cmd)

    v = verify_output(output)
    info(f"OK {output} ({v.get('duration', 0):.2f}s, "
         f"{v.get('video', {}).get('width', '?')}x{v.get('video', {}).get('height', '?')})")
    emit(output, segmentos=len(segs), duracion_in_s=round(dur, 2),
         duracion_out_s=round(v.get("duration", 0), 2),
         suavizar_s=args.suavizar, modo="fast" if args.fast else "preciso")


if __name__ == "__main__":
    main()
