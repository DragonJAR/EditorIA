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


def decodificar_estereo(ruta):
    """(L, R) en f32le a SR Hz.

    Para la compatibilidad con mono: el destino de una pieza es un telefono, y
    un telefono reproduce en mono (suma los dos canales). Lo que va en
    contrafase se anula al sumar.
    """
    try:
        r = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(ruta), "-ac", "2",
             "-ar", str(SR), "-f", "f32le", "-"],
            capture_output=True,
        )
    except FileNotFoundError:
        return None, None
    if r.returncode != 0:
        return None, None
    crudo = r.stdout
    if np is not None:
        a = np.frombuffer(crudo, dtype=np.float32)
        if a.size < 2:
            return None, None
        return a[0::2], a[1::2]
    n = len(crudo) // 4
    vals = struct.unpack(f"<{n}f", crudo[:n * 4])
    return vals[0::2], vals[1::2]


def correlacion(L, R):
    """Correlacion entre los dos canales (-1..1).

    >0.3 se sigue oyendo en un telefono (mono). <0 significa contrafase: lo
    que suena en un altavoz desaparece en el telefono.
    """
    if L is None or R is None or len(L) == 0:
        return None
    if np is not None and isinstance(L, np.ndarray) and isinstance(R, np.ndarray):
        den = float(np.sqrt(float(np.sum(L ** 2)) * float(np.sum(R ** 2))))
        if den <= 0:
            return None
        return float(np.sum(L * R) / den)
    num = sum(l * r for l, r in zip(L, R))
    den = math.sqrt(sum(l * l for l in L) * sum(r * r for r in R))
    return num / den if den > 0 else None


def rms_db(x, mascara):
    # Rama rápida NumPy solo si numpy está disponible Y ambas entradas son ndarrays
    # (los callers internos ya pasan ndarrays en presencia de numpy; los callers
    # externos con listas caen a la rama stdlib, que tolera listas nativas).
    if np is not None and isinstance(x, np.ndarray) and isinstance(mascara, np.ndarray):
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

    # Compatibilidad con mono: el destino es un teléfono, que reproduce en
    # mono sumando los canales. Lo que va en contrafase se anula al sumar.
    L, R = decodificar_estereo(a.musica)
    corr = correlacion(L, R)
    if corr is None:
        print(" mono: no se pudo medir la correlación de la música")
    else:
        print(f" mono: correlación estéreo {corr:+.2f} "
              f"(>0.3 se sigue oyendo en mono)")
        if corr < 0:
            print("→ AVISO: la música tiene canales en contrafase: en un "
                  "teléfono desaparece. Ensancha con M/S (L=y+s, R=y-s), "
                  "nunca con una copia retardada en un canal (Haas).")


if __name__ == "__main__":
    main()
