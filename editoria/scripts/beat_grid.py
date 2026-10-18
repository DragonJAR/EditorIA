#!/usr/bin/env python3
"""beat_grid.py — estima BPM, fase (beat0) y perfil de energía/kick por compás de un MP3.

Uso:
  python3 beat_grid.py musica.mp3
  python3 beat_grid.py musica.mp3 --min-bpm 90 --max-bpm 140 --json grid.json

Decodifica con ffmpeg (banda completa + banda <150 Hz), ajusta una rejilla
de tempo constante sobre los onsets y muestra un compás por línea:
marca K donde hay kick en cada beat y nivel RMS del compás.
El BPM/BEAT0 resultantes sirven para alinear cortes, zooms y captions
con el ritmo de la música en el video.

Importable: analizar(ruta) → {bpm, beat0, compas0, duracion, compases}
(render_plan lo usa con "musica" en el plan). compas0 = primer tiempo
fuerte (el "uno" del compás: la fase de 4 con más kick).

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
    np = None


def maximum_filter1d(x, k):
    """Máximo local centrado de ancho k (lo que se usaba de scipy, en numpy)."""
    x = np.asarray(x, dtype=np.float64)
    if k <= 1 or len(x) == 0:
        return x
    m = k // 2
    pad = np.pad(x, (m, k - 1 - m), mode="edge")
    return np.lib.stride_tricks.sliding_window_view(pad, k).max(axis=1)

SR = 11025
HOP = 128
FPS = SR / HOP


def decodificar(ruta, af):
    """Decodifica audio a f32le mono a SR Hz aplicando el filtro af."""
    crudo = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(ruta), "-af", af, "-ac", "1",
         "-ar", str(SR), "-f", "f32le", "-"],
        capture_output=True, check=True,
    ).stdout
    return np.frombuffer(crudo, dtype=np.float32)


def rms_por_frame(x):
    n = len(x) // HOP
    return np.sqrt((x[: n * HOP].reshape(n, HOP) ** 2).mean(axis=1) + 1e-12)


def onset(x):
    e = np.log(rms_por_frame(x) + 1e-5)
    return np.maximum(0, np.diff(e, prepend=e[0]))


def ajustar_rejilla(env, dur, min_bpm, max_bpm):
    """Devuelve (bpm, beat0): la rejilla constante cuyos beats acumulan más energía de onset."""
    n = len(env)
    mejor = None
    for bpm in np.arange(min_bpm, max_bpm + 0.01, 0.02):
        beat = 60 / bpm
        b0s = np.arange(0, beat, 0.004)
        k = np.arange(int((dur - beat) / beat))
        idx = np.clip(np.round((b0s[:, None] + beat * k[None, :]) * FPS).astype(int), 0, n - 1)
        s = env[idx].mean(axis=1)
        j = int(s.argmax())
        if mejor is None or s[j] > mejor[0]:
            mejor = (float(s[j]), float(bpm), float(b0s[j]))
    return mejor[1], mejor[2]


def analizar(ruta, min_bpm=90, max_bpm=140):
    """Rejilla de la música: bpm, beat0 (primer beat), compas0 (primer tiempo
    fuerte: de las 4 fases del compás, la de más kick) y compases con su
    marca de kicks y nivel. Sin efectos de consola: la usa render_plan."""
    banda_completa = decodificar(ruta, "anull")
    banda_baja = decodificar(ruta, "lowpass=f=150,lowpass=f=150")
    dur = len(banda_completa) / SR
    on_baja, on_full, rms = onset(banda_baja), onset(banda_completa), rms_por_frame(banda_completa)
    n = min(len(on_baja), len(on_full))
    env = maximum_filter1d(
        on_baja[:n] / (on_baja.max() + 1e-9) + 0.5 * on_full[:n] / (on_full.max() + 1e-9), 3)
    bpm, b0 = ajustar_rejilla(env, dur, min_bpm, max_bpm)
    beat = 60 / bpm
    nb = max(1, int((dur - b0) / beat))
    lo = maximum_filter1d(on_baja, 5)
    kick = np.array([lo[min(len(lo) - 1, int(round((b0 + i * beat) * FPS)))] for i in range(nb)])
    fase = int(np.argmax([kick[f::4].mean() if len(kick[f::4]) else 0 for f in range(4)]))
    c0 = b0 + fase * beat
    umbral = np.percentile(kick, 70) * 0.4
    compases = []
    for c in range((nb - fase) // 4):
        ks = kick[fase + c * 4: fase + c * 4 + 4]
        t = c0 + c * 4 * beat
        i0_, i1_ = int(t * FPS), int((t + 4 * beat) * FPS)
        db = 20 * np.log10(rms[i0_:i1_].mean() + 1e-9)
        compases.append({"compas": c, "t": round(t, 3), "kick": "".join("K" if k > umbral else "." for k in ks),
                         "db": round(float(db), 1)})
    return {"bpm": round(float(bpm), 2), "beat0": round(float(b0), 3), "compas0": round(float(c0), 3),
            "duracion": round(dur, 2), "compases": compases}


def main():
    ap = argparse.ArgumentParser(
        description="Estima BPM, fase (beat0), primer tiempo fuerte y energía/kick por compás de un MP3.",
        epilog="Ejemplo: python3 beat_grid.py musica.mp3 --min-bpm 90 --max-bpm 140",
    )
    ap.add_argument("archivo", help="archivo de música (mp3, wav, ...)")
    ap.add_argument("--min-bpm", type=float, default=90, help="BPM mínimo a buscar (def: 90)")
    ap.add_argument("--max-bpm", type=float, default=140, help="BPM máximo a buscar (def: 140)")
    ap.add_argument("--json", dest="salida_json", default=None,
                    help="guarda {bpm, beat0, compas0, duracion, compases} en este archivo JSON")
    a = ap.parse_args()
    if np is None:
        sys.exit("Falta numpy: python -m pip install numpy")
    if not Path(a.archivo).is_file():
        sys.exit(f"No existe el archivo: {a.archivo}")
    g = analizar(a.archivo, a.min_bpm, a.max_bpm)
    print(f"OK {a.archivo}\n duración {g['duracion']:.2f}s  rejilla: BPM {g['bpm']:.2f} · "
          f"BEAT0 {g['beat0']:.3f}s · primer tiempo fuerte {g['compas0']:.3f}s")
    for c in g["compases"]:
        print(f" compás {c['compas']:3d} {c['t']:7.2f}s  {c['kick']}  {c['db']:6.1f} dB  {'#' * max(0, int(c['db'] + 40))}")
    print("Usa BPM y BEAT0 para alinear cortes, zooms y captions con la música.")
    if a.salida_json:
        Path(a.salida_json).write_text(json.dumps(g, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"OK rejilla guardada en {a.salida_json}")


if __name__ == "__main__":
    main()
