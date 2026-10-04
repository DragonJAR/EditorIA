#!/usr/bin/env python3
"""Normalizacion de sonoridad EBU R128 en dos pasadas (ffmpeg loudnorm).

Pasada 1: mide sonoridad integrada, true peak, LRA y umbral. Pasada 2:
aplica loudnorm en modo lineal con esas mediciones, asi el resultado llega
al objetivo sin el "bombeo" del modo de una sola pasada. El video se copia
sin re-encodear.

Objetivos comunes: -14 LUFS (YouTube/Spotify), -16 (Apple Podcasts),
-23 (broadcast EBU).

Ejemplos:
  python3 loudness.py video.mp4
  python3 loudness.py podcast.wav -I -16 --tp -1.5 -o podcast_norm.wav
  python3 loudness.py video.mp4 --measure-only
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _comun import (STATE, add_common, apply_common, emit, AUDIO_CODECS,
                    audio_codec_for, default_output, die, ffmpeg_base, info,
                    probe, require_tool, run)


def measure(path, I, tp, lra):
    """Mide la sonoridad con loudnorm; devuelve el dict JSON de ffmpeg."""
    if STATE.dry_run:
        return {"input_i": "-20.0", "input_tp": "-3.0", "input_lra": "8.0",
                "input_thresh": "-30.0", "target_offset": "0.0", "silent": False}
    ffmpeg = require_tool("ffmpeg")
    cmd = [ffmpeg, "-hide_banner", "-nostdin", "-i", path, "-vn", "-af",
           f"loudnorm=I={I}:TP={tp}:LRA={lra}:print_format=json", "-f", "null", "-"]
    proc = run(cmd, check=False)
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", proc.stderr, re.S)
    if proc.returncode != 0 or not m:
        die(f"la medicion de sonoridad fallo:\n{proc.stderr.strip()[-1500:]}")
    data = json.loads(m.group(0))
    for k in ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset"):
        if data.get(k) in (None, "-inf", "inf", "nan"):
            data["silent"] = True
            return data
    data["silent"] = False
    return data


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="video/audio a normalizar")
    ap.add_argument("-o", "--output", help="archivo de salida (default: <nombre>_loudnorm.<ext>)")
    ap.add_argument("-I", "--lufs", type=float, default=-14.0,
                    help="objetivo de sonoridad integrada en LUFS (default -14)")
    ap.add_argument("--tp", type=float, default=-1.0,
                    help="techo de true peak en dBTP (default -1)")
    ap.add_argument("--lra", type=float, default=11.0,
                    help="objetivo de rango de sonoridad en LU (default 11)")
    ap.add_argument("--measure-only", action="store_true",
                    help="muestra las estadisticas medidas en JSON y sale")
    ap.add_argument("--force", action="store_true",
                    help="normaliza aunque el input parezca ambiente/silencio")
    ap.add_argument("--audio-bitrate", default="192k",
                    help="bitrate AAC cuando el contenedor es video (default 192k)")
    ap.add_argument("--sample-rate", type=int,
                    help="sample rate de salida (default: la del input)")
    add_common(ap)
    args = ap.parse_args()
    apply_common(args)

    meta = probe(args.input)
    if not meta.get("audio"):
        die("el input no tiene stream de audio")

    stats = measure(args.input, args.lufs, args.tp, args.lra)
    if stats.get("silent"):
        info("el audio esta en silencio (sonoridad integrada -inf); no hay nada que normalizar")
        if args.measure_only:
            print(json.dumps({"silent": True, "input_i": "-inf"}, indent=2))
            return 0
        die("el audio del input esta en silencio; la normalizacion no tiene sentido")
    info(f"medido: {float(stats['input_i']):.1f} LUFS, TP {float(stats['input_tp']):.1f} dBTP, "
         f"LRA {float(stats['input_lra']):.1f} LU")
    # Ambiente, no voz: subir 25 dB un room tone solo sube el ruido.
    # Se deja el nivel como esta salvo --force explicito.
    if float(stats["input_i"]) < -40.0 and not args.force:
        die("el input mide menos de -40 LUFS: parece ambiente/ruido de fondo, no voz. "
            "Normalizarlo al target solo subiria el ruido. Si es intencional, usa --force.",
            kind="input")
    if args.measure_only:
        print(json.dumps({k: stats[k] for k in
                          ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset")}, indent=2))
        return 0

    output = args.output or default_output(args.input, "loudnorm")
    af = (f"loudnorm=I={args.lufs}:TP={args.tp}:LRA={args.lra}"
          f":measured_I={stats['input_i']}:measured_TP={stats['input_tp']}:measured_LRA={stats['input_lra']}"
          f":measured_thresh={stats['input_thresh']}:offset={stats['target_offset']}:linear=true:print_format=summary")
    sr = args.sample_rate or meta["audio"].get("sample_rate") or 48000
    ext = os.path.splitext(output)[1].lower()
    cmd = ffmpeg_base() + ["-i", args.input, "-af", af, "-ar", str(sr)]
    if ext in AUDIO_CODECS or not meta.get("video"):
        cmd += ["-vn"] + audio_codec_for(output, args.audio_bitrate)
    else:
        cmd += ["-map", "0:v:0", "-map", "0:a:0", "-c:v", "copy",
                "-c:a", "aac", "-b:a", args.audio_bitrate]
    cmd.append(output)
    run(cmd)

    after = measure(output, args.lufs, args.tp, args.lra)
    if not after.get("silent"):
        info(f"resultado: {float(after['input_i']):.1f} LUFS, "
             f"TP {float(after['input_tp']):.1f} dBTP (objetivo {args.lufs} LUFS)")
    info(f"escribi {output}")
    if args.json:
        emit(output, result={k: after[k] for k in
                             ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset", "silent")})
    else:
        print(f"OK {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
