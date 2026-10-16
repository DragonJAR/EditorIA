#!/usr/bin/env python3
"""medir_mezcla.py — mide RMS de música vs voz en segmentos de habla y en gaps.

Uso:
  python3 medir_mezcla.py -v voz.wav -m musica.mp3 --ventanas ventanas.json
  python3 medir_mezcla.py -v voz.wav -m musica.mp3 --ventanas ventanas.json --inicio 2 --fin 20

ventanas.json: lista de pares [inicio, fin] en segundos donde hay voz
(ej.: [[0.5, 3.2], [4.0, 7.8]]). Si se omite, la voz se mide sobre todo el cuerpo.

Mide la música bajo el habla, la música en los silencios y el nivel de la voz.
Target de referencia: música ~15 dB por debajo de la voz durante el habla
(ver `references/audio.md`: ~15 dB bajo la voz mientras habla; sube en los
gaps sin tapar la entrada de la voz). Unos 10 dB bajo se percibe como
"no hay música".

Requiere: ffmpeg, numpy.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

try:
    import numpy as np
except ImportError:
    sys.exit("Falta numpy: python -m pip install numpy")

SR = 8000
TARGET_DB = 15.0
TOLERANCIA_DB = 2.0


def decodificar(ruta):
    """Decodifica audio a f32le mono a SR Hz."""
    crudo = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(ruta), "-ac", "1",
         "-ar", str(SR), "-f", "f32le", "-"],
        capture_output=True, check=True,
    ).stdout
    return np.frombuffer(crudo, dtype=np.float32)


def rms_db(x, mascara):
    seg = x[mascara]
    return 10 * np.log10(np.mean(seg ** 2) + 1e-12) if seg.size else None


def fmt_db(v):
    return f"{v:6.1f} dB" if v is not None else "    —    "


def main():
    ap = argparse.ArgumentParser(
        description="Mide el balance música vs voz: RMS de la música bajo el habla, "
                    "en los gaps y nivel de la voz.",
        epilog="Ejemplo: python3 medir_mezcla.py -v voz.wav -m musica.mp3 "
               "--ventanas ventanas.json",
    )
    ap.add_argument("-v", "--voz", required=True, help="audio de la voz (wav, mp3, ...)")
    ap.add_argument("-m", "--musica", required=True, help="audio de la música (wav, mp3, ...)")
    ap.add_argument("--ventanas", default=None,
                    help="JSON con [[inicio, fin], ...] en segundos donde hay voz")
    ap.add_argument("--inicio", type=float, default=1.0,
                    help="segundo inicial del cuerpo a medir (def: 1.0)")
    ap.add_argument("--fin", type=float, default=None,
                    help="segundo final del cuerpo a medir (def: fin del audio)")
    ap.add_argument("--target-db", type=float, default=TARGET_DB,
                    help=f"diferencia objetivo música bajo voz en dB (def: {TARGET_DB})")
    a = ap.parse_args()

    for etiqueta, ruta in (("voz", a.voz), ("música", a.musica)):
        if not Path(ruta).is_file():
            sys.exit(f"No existe el archivo de {etiqueta}: {ruta}")

    musica, voz = decodificar(a.musica), decodificar(a.voz)
    n = min(len(musica), len(voz))
    musica, voz = musica[:n], voz[:n]

    ventanas = []
    if a.ventanas:
        ventanas = json.loads(Path(a.ventanas).read_text(encoding="utf-8"))
    habla = np.zeros(n, bool)
    for inicio, fin in ventanas:
        habla[int(inicio * SR): int(fin * SR)] = True
    if not habla.any():
        habla[:] = True  # sin ventanas: la voz se mide sobre todo el cuerpo

    inicio, fin = a.inicio, a.fin if a.fin is not None else n / SR
    cuerpo = np.zeros(n, bool)
    cuerpo[int(inicio * SR): min(n, int(fin * SR))] = True
    if not cuerpo.any():
        sys.exit("El rango --inicio/--fin no cubre ningún audio")

    musica_bajo_habla = rms_db(musica, habla & cuerpo)
    musica_en_gaps = rms_db(musica, cuerpo & ~habla)
    nivel_voz = rms_db(voz, habla & cuerpo)
    if musica_bajo_habla is None or nivel_voz is None:
        sys.exit("Las ventanas de voz no se solapan con el rango --inicio/--fin: "
                 "nada que medir")
    diferencia = nivel_voz - musica_bajo_habla
    pct_gaps = 100 * np.mean(~habla[cuerpo])

    print(f"OK mezcla:\n"
          f" música bajo el habla {fmt_db(musica_bajo_habla)} | "
          f"música en gaps {fmt_db(musica_en_gaps)} | voz {fmt_db(nivel_voz)}")
    print(f" la música queda {diferencia:.1f} dB bajo la voz "
          f"(target {a.target_db:.1f} dB); los gaps son {pct_gaps:.0f}% del cuerpo")

    if diferencia < a.target_db - TOLERANCIA_DB:
        print("→ AVISO: la música está tapando la voz. Baja la música o sube el ducking.")
    elif diferencia > a.target_db + TOLERANCIA_DB:
        print("→ AVISO: la música casi no se oye. Sube la música (unos "
              f"{diferencia - a.target_db:.1f} dB) para que acompañe.")
    else:
        print("→ Balance OK: la música acompaña sin tapar la voz.")


if __name__ == "__main__":
    main()
