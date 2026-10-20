#!/usr/bin/env python3
"""Sintetiza un pack de SFX procedural (sin assets externos).

Genera WAV 44.1kHz mono de 16 bits solo con numpy, determinista (seed fijo)
para que los builds sean reproducibles. Pensado para la capa de SFX de
`references/sfx.md`: efectos suaves que se mezclan bajo la musica.

Uso:
    python scripts/sfx.py -o assets/sfx/            # pack completo
    python scripts/sfx.py -o assets/sfx/ --only pop,ding
    python scripts/sfx.py --list
"""
import argparse
import os
import sys
try:
    import numpy as np
except ModuleNotFoundError as _e_dep:
    if "-h" not in sys.argv and "--help" not in sys.argv:
        sys.exit(f"ERROR: falta dependencia ({_e_dep.name}): pip install numpy")
    np = None

SR = 44100
SEED = 7


def _filtro(x, bajo=None, alto=None, orden=4):
    """Butterworth en frecuencia (|H| = 1/sqrt(1+(f/fc)^2n)), fase cero, solo
    numpy: `bajo` = pasa-altos desde bajo Hz, `alto` = pasa-bajos hasta alto Hz
    (ambos = pasa-banda). Sin scipy, que en una instalación mínima no está."""
    n = len(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    h = np.ones_like(f)
    if alto:
        h /= np.sqrt(1 + (f / alto) ** (2 * orden))
    if bajo:
        with np.errstate(divide="ignore"):
            h /= np.sqrt(1 + (bajo / np.maximum(f, 1e-9)) ** (2 * orden))
    return np.fft.irfft(np.fft.rfft(x) * h, n)


def _env(n, attack=0.005, decay=None):
    t = np.arange(n) / SR
    a = np.minimum(1.0, t / attack)
    d = np.exp(-t / (decay or (n / SR / 3)))
    return a * d


def _wav(x, path):
    x = np.clip(x, -1.0, 1.0)
    import wave
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def click(rng):
    n = int(0.07 * SR)
    x = rng.standard_normal(n) * _env(n, attack=0.001, decay=0.012)
    return _filtro(x, bajo=2500) * 0.33   # 0.5 saturaba (pico 1.0)


def pop(rng):
    n = int(0.14 * SR)
    t = np.arange(n) / SR
    f = 620 * np.exp(-t * 18) + 180
    ph = np.cumsum(2 * np.pi * f / SR)
    x = np.sin(ph) * _env(n, attack=0.002, decay=0.03)
    return x * 0.7


def drop(rng):
    n = int(0.22 * SR)
    t = np.arange(n) / SR
    f = 300 * np.exp(-t * 10) + 110
    ph = np.cumsum(2 * np.pi * f / SR)
    x = np.sin(ph) * _env(n, attack=0.004, decay=0.07)
    return _filtro(x, alto=900) * 0.6


def whoosh(rng):
    n = int(0.45 * SR)
    x = rng.standard_normal(n)
    # barrido de bandpass 400Hz -> 4kHz
    out = np.zeros(n)
    steps = 24
    seg = n // steps
    for i in range(steps):
        fc = 400 * (4000 / 400) ** (i / (steps - 1))
        s = slice(i * seg, (i + 1) * seg if i < steps - 1 else n)
        out[s] = _filtro(x[s], bajo=fc * 0.7, alto=min(fc * 1.4, SR * 0.49), orden=2)
    env = np.sin(np.pi * np.arange(n) / n) ** 1.5
    return out * env * 0.45


def ding(rng):
    n = int(0.9 * SR)
    t = np.arange(n) / SR
    partials = [(1.0, 1.0), (2.76, 0.5), (5.40, 0.28), (8.93, 0.15)]
    x = np.zeros(n)
    for ratio, amp in partials:
        x += amp * np.sin(2 * np.pi * 660 * ratio * t) * np.exp(-t * (3 + ratio))
    return x * _env(n, attack=0.002, decay=0.25) * 0.5


def thud(rng):
    n = int(0.32 * SR)
    t = np.arange(n) / SR
    f = 95 * np.exp(-t * 12) + 42
    ph = np.cumsum(2 * np.pi * f / SR)
    body = np.sin(ph) * _env(n, attack=0.003, decay=0.09)
    nz = rng.standard_normal(n) * _env(n, attack=0.001, decay=0.02) * 0.3
    return _filtro(body + nz, alto=500) * 0.8


def tick(rng):
    n = int(0.035 * SR)
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * 2500 * t) * _env(n, attack=0.001, decay=0.006) * 0.4


def swell(rng):
    n = int(1.2 * SR)
    t = np.arange(n) / SR
    nz = rng.standard_normal(n)
    nz = _filtro(nz, alto=1200)
    cresc = (np.arange(n) / n) ** 2.2
    tone = np.sin(2 * np.pi * 110 * t) * cresc * 0.5
    return (nz * cresc * 0.35 + tone) * np.minimum(1.0, np.exp(-(t - 1.0) * 8))


GENERADORES = {
    "click": ("Tap seco de UI; pasos, botones, toggles.", click),
    "pop": ("Pop redondo; chips y tarjetas que entran.", pop),
    "drop": ("Aterrizaje suave; reveals amables.", drop),
    "whoosh": ("Barrido de aire; transiciones.", whoosh),
    "ding": ("Campana metalica; exito, cifra heroica, outro.", ding),
    "thud": ("Golpe grave; reveals grandes, bloques.", thud),
    "tick": ("Blip agudo; tipeo por caracter (variar pitch).", tick),
    "swell": ("Crescendo 1.2s; heroes, momentos epicos.", swell),
}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("-o", help="directorio de salida (no hace falta con --list)")
    ap.add_argument("--only", default="", help="solo estos, separados por coma")
    ap.add_argument("--list", action="store_true", help="lista el pack y sale")
    args = ap.parse_args()

    if args.list:
        for name, (desc, _) in GENERADORES.items():
            print(f"{name:8s} {desc}")
        return

    if not args.o:
        ap.error("falta -o DIRECTORIO (o usar --list)")
    os.makedirs(args.o, exist_ok=True)
    sel = [s.strip() for s in args.only.split(",") if s.strip()] or list(GENERADORES)
    rng = np.random.default_rng(SEED)
    for name in sel:
        if name not in GENERADORES:
            raise SystemExit(f"SFX desconocido: {name} (ver --list)")
        desc, gen = GENERADORES[name]
        _wav(gen(rng), os.path.join(args.o, f"{name}.wav"))
        print(f"OK {name}.wav — {desc}")


if __name__ == "__main__":
    main()
