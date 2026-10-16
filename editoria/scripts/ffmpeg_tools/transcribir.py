#!/usr/bin/env python3
"""Transcribe un video/audio a SRT + JSON de segmentos usando ASR 100% local.

Puente (en orden): whisper-cli/main (whisper.cpp), faster-whisper (python),
whisper (CLI de openai-whisper). Todo corre offline; si no hay motor
instalado, muere con instrucciones claras de instalación.

El JSON [{start, end, text}] es el formato que consume retakes.py, asi la
cadena transcribir -> retakes --edl -> aplicar_edl.py queda cerrada.

Ejemplos:
  python3 transcribir.py charla.mp4 --language es
      # charla.srt + charla_segmentos.json
  python3 transcribir.py charla.mp4 --language es --model small -o subs
      # subs.srt + subs_segmentos.json
  python3 transcribir.py charla.mp4 --language es --solo-srt
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _comun import (add_common, apply_common, die, emit, info,
                    transcribir_medio, write_segmentos_json)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="video o audio a transcribir")
    ap.add_argument("-o", "--output",
                    help="base de salida (default: <input> sin extension). "
                         "Genera <base>.srt y <base>_segmentos.json")
    ap.add_argument("--language", default=None,
                    help="codigo de idioma (ej. es, en; default: autodetectar)")
    ap.add_argument("--model", default="base",
                    help="modelo whisper (tiny/base/small/medium/large; default base). "
                         "Para whisper.cpp tambien acepta ruta a un .bin")
    ap.add_argument("--audio-stream", type=int, default=0,
                    help="indice del stream de audio a usar (default 0)")
    ap.add_argument("--solo-srt", action="store_true",
                    help="solo genera el SRT, sin el JSON de segmentos")
    add_common(ap)
    args = ap.parse_args()
    apply_common(args)

    if not os.path.isfile(args.input):
        die(f"no existe el archivo: {args.input}")

    base = args.output or os.path.splitext(args.input)[0]
    srt_path = base + ".srt"
    seg_path = base + "_segmentos.json"

    cues = transcribir_medio(args.input, srt_path, args.language, args.model,
                             args.audio_stream)
    info(f"escribi {srt_path} ({len(cues)} segmentos)")
    salidas = [srt_path]
    if not args.solo_srt:
        write_segmentos_json(cues, seg_path)
        info(f"escribi {seg_path} (formato retakes.py)")
        salidas.append(seg_path)

    dur = max((e for _, e, _ in cues), default=0.0)
    info(f"OK {salidas[0]}")
    emit(salidas[0], salidas=salidas, segmentos=len(cues),
         duracion_s=round(dur, 2))


if __name__ == "__main__":
    main()
