#!/usr/bin/env python3
"""Dale ojos al agente: extrae frames o un contact sheet de un video como PNG
para inspeccion visual (posicion de subtitulos, logo, recorte, color).

Ejemplos:
  python3 look.py final.mp4                          # contact sheet 12 cuadros con timecodes -> final_sheet.png
  python3 look.py final.mp4 --tiles 4x5 --width 1600
  python3 look.py final.mp4 --at 2.5 --at 7          # frames sueltos -> final_2.500s.png, final_7.000s.png
  python3 look.py antes.mp4 --compare despues.mp4 --at 4   # frame lado a lado
Luego mira el PNG y verifica antes de reportar.
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _comun import (add_common, apply_common, default_font_file, die, emit,
                    escape_drawtext, escape_filter_path, ffmpeg_base, info,
                    parse_time, probe, run)

FONT = "fontcolor=white:fontsize=h/18:box=1:boxcolor=black@0.55:boxborderw=6:x=8:y=8"


def fmt_hms(sec):
    h, rem = divmod(sec, 3600)
    m, s_ = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{s_:06.3f}"


def timecode_filter(font_prefix):
    return f"drawtext=text='%{{pts\\:hms}}':{font_prefix}{FONT}"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="video a inspeccionar")
    ap.add_argument("-o", "--output", help="PNG de salida (contact sheet / comparacion) o base para frames --at")
    ap.add_argument("--at", action="append",
                    help="tiempo del frame a extraer (repetible); acepta segundos, mm:ss o hh:mm:ss")
    ap.add_argument("--tiles", default="4x3",
                    help="grilla del contact sheet COLUMNASxFILAS (default 4x3)")
    ap.add_argument("--width", type=int, default=1280,
                    help="ancho total del sheet / imagen de comparacion (default 1280)")
    ap.add_argument("--compare", help="segundo video: coloca su frame junto al primero (requiere --at)")
    ap.add_argument("--no-timecode", action="store_true",
                    help="sin el sello de timecode quemado")
    add_common(ap)
    args = ap.parse_args()
    apply_common(args)

    meta = probe(args.input)
    if not meta.get("video"):
        die("el input no tiene stream de video")
    dur = meta.get("duration") or 0.0
    stem = Path(args.input).stem
    outdir = str(Path(args.output).parent) if args.output else str(Path(args.input).parent)
    default_font = default_font_file("DejaVu Sans")
    font_prefix = f"fontfile={escape_filter_path(default_font)}:" if default_font else ""
    tc = "" if args.no_timecode else "," + timecode_filter(font_prefix)
    # fuentes HDR: tone-map para el PNG, asi se juzgan colores representativos
    if meta["video"].get("hdr"):
        v = meta["video"]
        tm = (f"zscale=tin={v.get('color_transfer') or 'arib-std-b67'}"
              f":pin={v.get('color_primaries') or 'bt2020'}"
              f":min={v.get('color_space') or 'bt2020nc'}:rin=tv:t=linear:npl=1000,"
              "format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable,"
              "zscale=t=bt709:m=bt709:r=tv,format=yuv420p,")
        tc = "," + tm.rstrip(",") + tc
        info("fuente HDR: los frames se tone-mapean a SDR para visualizacion")
    outputs = []

    if args.compare:
        if not args.at:
            die("--compare requiere --at TIEMPO")
        probe(args.compare)
        for t in args.at:
            sec = parse_time(t)
            out = args.output or os.path.join(outdir, f"{stem}_vs_{Path(args.compare).stem}_{sec:.3f}s.png")
            half = args.width // 2
            stamp = "" if args.no_timecode else f",drawtext=text='{escape_drawtext(fmt_hms(sec))}':{font_prefix}{FONT}"
            tcs = tc.replace("," + timecode_filter(font_prefix), "") + stamp
            fc = (f"[0:v]scale={half}:-2{tcs}[a];[1:v]scale={half}:-2{tcs}[b];"
                  f"[a][b]scale2ref=w=iw:h=ih[a2][b2];[a2][b2]hstack=inputs=2[out]")
            cmd = ffmpeg_base(texto=True) + ["-ss", f"{sec:.3f}", "-i", args.input,
                                            "-ss", f"{sec:.3f}", "-i", args.compare,
                                            "-filter_complex", fc, "-map", "[out]", "-frames:v", "1", out]
            run(cmd)
            outputs.append(out)
    elif args.at:
        for t in args.at:
            sec = parse_time(t)
            if dur and sec > dur:
                die(f"--at {t} excede la duracion ({dur:.2f}s)")
            out = os.path.join(outdir, f"{args.output and Path(args.output).stem or stem}_{sec:.3f}s.png")
            stamp = "" if args.no_timecode else f",drawtext=text='{escape_drawtext(fmt_hms(sec))}':{font_prefix}{FONT}"
            vf = f"scale={args.width}:-2{tc.replace(',' + timecode_filter(font_prefix), '')}{stamp}"
            cmd = ffmpeg_base(texto=True) + ["-ss", f"{sec:.3f}", "-i", args.input, "-vf", vf,
                                            "-frames:v", "1", out]
            run(cmd)
            outputs.append(out)
    else:
        try:
            cols, rows = (int(x) for x in args.tiles.lower().split("x"))
        except ValueError:
            die("--tiles debe verse como 4x3")
        n = cols * rows
        if not dur:
            die("no puedo armar un contact sheet sin duracion conocida")
        step = dur / n
        tile_w = max(2, (args.width // cols) // 2 * 2)
        out = args.output or os.path.join(outdir, f"{stem}_sheet.png")
        # muestrea a mitad de cada tramo para no tomar frames negros de entrada/salida
        vf = (f"select='isnan(prev_selected_t)+gte(t-prev_selected_t\\,{step * 0.98:.6f})',"
              f"scale={tile_w}:-2{tc},"
              f"tile={cols}x{rows}:padding=2:margin=2:color=0x202020")
        cmd = ffmpeg_base(texto=True) + ["-ss", f"{step / 2:.6f}", "-i", args.input, "-vf", vf,
                                        "-frames:v", "1", out]
        run(cmd)
        outputs.append(out)
        info(f"contact sheet: {n} frames cada {step:.2f}s")

    for o in outputs:
        info(f"escribi {o}")
    if args.json:
        emit(outputs[0] if len(outputs) == 1 else None, outputs=outputs)
    else:
        print(f"OK {outputs[0] if len(outputs) == 1 else len(outputs)}")
        if len(outputs) > 1:
            for o in outputs:
                print(o)
    return 0


if __name__ == "__main__":
    sys.exit(main())
