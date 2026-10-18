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

Requiere: ffmpeg (usa numpy si está disponible; fallback determinista en stdlib).
"""
import argparse
import json
import math
import struct
import subprocess
import sys
from pathlib import Path

try:
    import numpy as np
except ImportError:
    np = None

SR = 8000
TARGET_DB = 15.0
TOLERANCIA_DB = 2.0


for _extra_bin in ("/opt/homebrew/bin", "/usr/local/bin"):
    if Path(_extra_bin).is_dir() and _extra_bin not in sys.modules["os"].environ.get("PATH", "").split(sys.modules["os"].pathsep):
        sys.modules["os"].environ["PATH"] = _extra_bin + sys.modules["os"].pathsep + sys.modules["os"].environ.get("PATH", "")


def decodificar(ruta):
    """Decodifica audio a f32le mono a SR Hz."""
    try:
        r = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(ruta), "-ac", "1",
             "-ar", str(SR), "-f", "f32le", "-"],
            capture_output=True,
        )
    except FileNotFoundError:
        sys.exit("ERROR: no se encontró 'ffmpeg' en el PATH")
    if r.returncode != 0:
        sys.exit(f"ERROR: ffmpeg no pudo leer {ruta}")
    crudo = r.stdout
    if np is not None:
        return np.frombuffer(crudo, dtype=np.float32)
    n = len(crudo) // 4
    return struct.unpack(f"<{n}f", crudo[:n * 4])


def rms_db(x, mascara):
    if np is not None:
        seg = x[mascara]
        return float(10 * np.log10(np.mean(seg ** 2) + 1e-12)) if seg.size else None
    vals = [v * v for v, m in zip(x, mascara) if m]
    if not vals:
        return None
    return 10.0 * math.log10(sum(vals) / len(vals) + 1e-12)


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
        if not Path(a.ventanas).is_file():
            sys.exit(f"No existe el archivo de ventanas: {a.ventanas}")
        try:
            ventanas = json.loads(Path(a.ventanas).read_text(encoding="utf-8"))
        except (OSError, ValueError) as ex:
            sys.exit(f"ERROR: JSON inválido en {a.ventanas}: {ex}")
    inicio_idx = max(0, int(a.inicio * SR))
    fin_idx = min(n, int((a.fin if a.fin is not None else n / SR) * SR))
    if fin_idx <= inicio_idx:
        sys.exit("El rango --inicio/--fin no cubre ningún audio")

    if np is not None:
        habla = np.zeros(n, bool)
        for ini_v, fin_v in ventanas:
            habla[max(0, int(ini_v * SR)): min(n, int(fin_v * SR))] = True
        if not habla.any():
            habla[:] = True
        cuerpo = np.zeros(n, bool)
        cuerpo[inicio_idx:fin_idx] = True
        musica_bajo_habla = rms_db(musica, habla & cuerpo)
        musica_en_gaps = rms_db(musica, cuerpo & ~habla)
        nivel_voz = rms_db(voz, habla & cuerpo)
        pct_gaps = float(100 * np.mean(~habla[cuerpo]))
    else:
        habla = [False] * n
        for ini_v, fin_v in ventanas:
            for idx in range(max(0, int(ini_v * SR)), min(n, int(fin_v * SR))):
                habla[idx] = True
        if not any(habla):
            habla = [True] * n
        cuerpo = [inicio_idx <= idx < fin_idx for idx in range(n)]
        mask_habla = [h and c for h, c in zip(habla, cuerpo)]
        mask_gaps = [(not h) and c for h, c in zip(habla, cuerpo)]
        musica_bajo_habla = rms_db(musica, mask_habla)
        musica_en_gaps = rms_db(musica, mask_gaps)
        nivel_voz = rms_db(voz, mask_habla)
        pct_gaps = 100.0 * sum(1 for m in mask_gaps if m) / max(1, fin_idx - inicio_idx)

    if musica_bajo_habla is None or nivel_voz is None:
        sys.exit("Las ventanas de voz no se solapan con el rango --inicio/--fin: "
                 "nada que medir")
    diferencia = nivel_voz - musica_bajo_habla

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
