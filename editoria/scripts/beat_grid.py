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

Importable: analizar(ruta) → {bpm, beat0, compas0, duracion, compases,
secciones} (render_plan lo usa con "musica" en el plan). compas0 = primer
tiempo fuerte (el "uno" del compás: la fase de 4 con más kick).

Secciones: la música manda la dirección creativa. Se agrupan los compases en
frases de 4 y se corta donde la energía media cambia de verdad (umbral en
dB); cada sección lleva su nivel relativo (baja/media/alta), un rol (intro,
subida, pico, valle, outro) y `cortes_cada_beats` sugerido: no todo beat
pide un corte — en lo bajo se respira (8), en lo alto se corta más (2).
Mismo formato que las secciones de beat_file.py ({nombre, inicio, fin}).

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


def _percentil_std(vals, q):
    if not vals:
        return 0.0
    s = sorted(vals)
    pos = (q / 100.0) * (len(s) - 1)
    lo = int(pos)
    hi = min(len(s) - 1, lo + 1)
    frac = pos - lo
    return s[lo] * (1.0 - frac) + s[hi] * frac


def maximum_filter1d(x, k):
    """Máximo local centrado de ancho k (lo que se usaba de scipy, en numpy o stdlib).
    Devuelve el mismo tipo de contenedor que recibe: ndarray→ndarray (con numpy),
    list/tuple→list (con numpy o sin él). Los callers internos ya pasan ndarrays
    en la rama numpy, así que la ruta rápida no se ve afectada."""
    if np is not None and isinstance(x, np.ndarray):
        if k <= 1 or len(x) == 0:
            return x
        m = k // 2
        pad = np.pad(x, (m, k - 1 - m), mode="edge")
        return np.lib.stride_tricks.sliding_window_view(pad, k).max(axis=1)
    xs = list(x)
    n = len(xs)
    if k <= 1 or n == 0:
        return xs
    m = k // 2
    return [max(xs[max(0, i - m):min(n, i + k - m)]) for i in range(n)]


SR = 11025
HOP = 128
FPS = SR / HOP


for _extra_bin in ("/opt/homebrew/bin", "/usr/local/bin"):
    if Path(_extra_bin).is_dir() and _extra_bin not in sys.modules["os"].environ.get("PATH", "").split(sys.modules["os"].pathsep):
        sys.modules["os"].environ["PATH"] = _extra_bin + sys.modules["os"].pathsep + sys.modules["os"].environ.get("PATH", "")


def decodificar(ruta, af):
    """Decodifica audio a f32le mono a SR Hz aplicando el filtro af."""
    if not Path(ruta).is_file():
        sys.exit(f"No existe el archivo: {ruta}")
    try:
        r = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(ruta), "-af", af, "-ac", "1",
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


def rms_por_frame(x):
    n = len(x) // HOP
    if np is not None:
        return np.sqrt((x[: n * HOP].reshape(n, HOP) ** 2).mean(axis=1) + 1e-12)
    out = []
    for i in range(n):
        seg = x[i * HOP:(i + 1) * HOP]
        out.append(math.sqrt(sum(v * v for v in seg) / HOP + 1e-12))
    return out


def onset(x):
    rms = rms_por_frame(x)
    if np is not None:
        e = np.log(rms + 1e-5)
        return np.maximum(0, np.diff(e, prepend=e[0]))
    logs = [math.log(r + 1e-5) for r in rms]
    if not logs:
        return []
    return [0.0] + [max(0.0, logs[i] - logs[i - 1]) for i in range(1, len(logs))]


def ajustar_rejilla(env, dur, min_bpm, max_bpm):
    """Devuelve (bpm, beat0): la rejilla constante cuyos beats acumulan más energía de onset."""
    n = len(env)
    if n == 0:
        return float(min_bpm), 0.0
    mejor = None
    if np is not None:
        for bpm in np.arange(min_bpm, max_bpm + 0.01, 0.02):
            beat = 60 / bpm
            nb = int((dur - beat) / beat)
            if nb <= 0:
                continue
            b0s = np.arange(0, beat, 0.004)
            k = np.arange(nb)
            idx = np.clip(np.round((b0s[:, None] + beat * k[None, :]) * FPS).astype(int), 0, n - 1)
            s = env[idx].mean(axis=1)
            j = int(s.argmax())
            if mejor is None or s[j] > mejor[0]:
                mejor = (float(s[j]), float(bpm), float(b0s[j]))
        return (mejor[1], mejor[2]) if mejor is not None else (float(min_bpm), 0.0)

    env_list = list(env)
    n_1 = n - 1
    steps_bpm = int(round((max_bpm - min_bpm) / 0.02)) + 1
    for ib in range(steps_bpm):
        bpm = min_bpm + ib * 0.02
        beat = 60.0 / bpm
        nb = int((dur - beat) / beat)
        if nb <= 0:
            continue
        step_f = beat * FPS
        k_offs = [k * step_f for k in range(nb)]
        nb_b0 = int(math.ceil(beat / 0.004))
        for j0 in range(nb_b0):
            b0 = j0 * 0.004
            base_f = b0 * FPS + 0.5
            s = 0.0
            for ko in k_offs:
                idx = int(base_f + ko)
                if idx > n_1:
                    idx = n_1
                s += env_list[idx]
            mean_s = s / nb
            if mejor is None or mean_s > mejor[0]:
                mejor = (mean_s, bpm, b0)
    return (mejor[1], mejor[2]) if mejor is not None else (float(min_bpm), 0.0)


CORTES_POR_NIVEL = {"baja": 8, "media": 4, "alta": 2}   # beats entre cortes sugeridos


def secciones(compases, duracion, umbral_db=3.0, frase=4):
    """Compases [{t, db}] → secciones por energía. Frases de `frase` compases
    (la unidad de la música pop); una frontera solo donde la energía (mediana)
    de la frase cambia >= umbral_db respecto de la sección en curso, así un
    golpe aislado no parte la canción. Determinista y sin dependencias."""
    if not compases:
        return []
    frases = [compases[i:i + frase] for i in range(0, len(compases), frase)]
    # mediana por frase: un golpe aislado (un compás fuerte) no mueve la frase
    medias = [_percentil_std([c["db"] for c in f], 50) for f in frases]
    grupos = [[0]]
    for i in range(1, len(frases)):
        actual = sum(medias[j] for j in grupos[-1]) / len(grupos[-1])
        if abs(medias[i] - actual) >= umbral_db:
            grupos.append([i])
        else:
            grupos[-1].append(i)
    energia = [sum(medias[j] for j in g) / len(g) for g in grupos]
    lo, hi = min(energia), max(energia)
    tercio = (hi - lo) / 3 if hi - lo >= umbral_db else None

    def nivel(e):
        if tercio is None:
            return "media"
        return "baja" if e < lo + tercio else ("alta" if e > hi - tercio else "media")

    out = []
    for k, g in enumerate(grupos):
        niv = nivel(energia[k])
        ini = 0.0 if k == 0 else frases[g[0]][0]["t"]
        fin = frases[grupos[k + 1][0]][0]["t"] if k + 1 < len(grupos) else duracion
        if niv == "alta":
            rol = "pico"
        elif k == 0:
            rol = "intro"
        elif k == len(grupos) - 1:
            rol = "outro"
        elif k + 1 < len(grupos) and energia[k + 1] > energia[k]:
            rol = "subida"
        else:
            rol = "valle"
        out.append({"nombre": f"{rol}{k + 1}", "rol": rol, "inicio": round(ini, 3), "fin": round(fin, 3),
                    "energia": niv, "db": round(energia[k], 1), "cortes_cada_beats": CORTES_POR_NIVEL[niv]})
    return out


def picos_transitorios(on_full, rms, dur, delta=0.5, wait_ms=120):
    """Picos de ataque de la banda completa: los instantes donde la musica
    PEGA (un golpe, un stab, un golpe de bajo) y no solo donde cae el beat.

    La grilla dice DONDE hay un compás; los picos dicen DONDE hay un
    impacto. Un SFX de golpe, click o impacto pegado a un transitorio real
    suena pegado a la musica; pegado al beat, se nota el retraso.

    `delta` es cuanto tiene que standout el pico sobre su entorno (multiplos
    de la desviacion local) y `wait_ms` el silencio minimo entre picos.
    """
    n = len(on_full)
    if n < 3 or np is None:
        return []
    env = np.asarray(on_full[:n], dtype=float)
    if env.max() <= 0:
        return []
    env = env / env.max()
    ventana = max(3, int(0.05 * FPS))     # ~50 ms antes/despues para comparar
    largo_ventana = max(3, int(0.25 * FPS))
    salida = []
    ultimo = -10 ** 9
    min_sep = max(1, int(wait_ms / 1000.0 * FPS))
    for i in range(ventana, n - ventana):
        if env[i] <= env[max(0, i - ventana):i + ventana + 1].max() - 1e-12:
            continue
        zona = env[max(0, i - largo_ventana):i + largo_ventana + 1]
        if env[i] < zona.mean() + delta * (zona.std() + 1e-9):
            continue
        if i - ultimo < min_sep:
            continue
        ultimo = i
        t = round(i / FPS, 3)
        if t > dur:
            break
        salida.append({"t": t, "fuerza": round(float(env[i]), 3),
                       "db": round(float(20 * math.log10((rms[i] if i < len(rms) else 0.0) + 1e-9)), 1)})
    return salida


def analizar(ruta, min_bpm=90, max_bpm=140, delta=3.0, espera=200):
    """Rejilla de la música: bpm, beat0 (primer beat), compas0 (primer tiempo
    fuerte: de las 4 fases del compás, la de más kick), compases con su
    marca de kicks, nivel, y los picos transitorios donde la musica pega."""
    banda_completa = decodificar(ruta, "anull")
    banda_baja = decodificar(ruta, "lowpass=f=150,lowpass=f=150")
    dur = len(banda_completa) / SR
    on_baja, on_full, rms = onset(banda_baja), onset(banda_completa), rms_por_frame(banda_completa)
    n = min(len(on_baja), len(on_full))
    picos = picos_transitorios(on_full, rms, dur, delta=delta, wait_ms=espera)
    if np is not None:
        env = maximum_filter1d(
            on_baja[:n] / (on_baja.max() + 1e-9) + 0.5 * on_full[:n] / (on_full.max() + 1e-9), 3)
        bpm, b0 = ajustar_rejilla(env, dur, min_bpm, max_bpm)
        beat = 60 / bpm
        nb = max(1, int((dur - b0) / beat))
        lo = maximum_filter1d(on_baja, 5)
        kick = np.array([lo[min(len(lo) - 1, int(round((b0 + i * beat) * FPS)))] for i in range(nb)])
        fase = int(np.argmax([kick[f::4].mean() if len(kick[f::4]) else 0 for f in range(4)]))
        c0 = b0 + fase * beat
        umbral = float(np.percentile(kick, 70) * 0.4)
        compases = []
        for c in range((nb - fase) // 4):
            ks = kick[fase + c * 4: fase + c * 4 + 4]
            t = c0 + c * 4 * beat
            i0_, i1_ = int(t * FPS), int((t + 4 * beat) * FPS)
            db = 20 * np.log10(rms[i0_:i1_].mean() + 1e-9)
            compases.append({"compas": c, "t": round(t, 3), "kick": "".join("K" if k > umbral else "." for k in ks),
                             "db": round(float(db), 1)})
    else:
        max_b = max(on_baja[:n]) + 1e-9 if n else 1.0
        max_f = max(on_full[:n]) + 1e-9 if n else 1.0
        raw_env = [on_baja[i] / max_b + 0.5 * on_full[i] / max_f for i in range(n)]
        env = maximum_filter1d(raw_env, 3)
        bpm, b0 = ajustar_rejilla(env, dur, min_bpm, max_bpm)
        beat = 60.0 / bpm
        nb = max(1, int((dur - b0) / beat))
        lo = maximum_filter1d(on_baja, 5)
        kick = [lo[min(len(lo) - 1, int(round((b0 + i * beat) * FPS)))] for i in range(nb)]
        fases_m = [sum(kick[f::4]) / len(kick[f::4]) if kick[f::4] else 0.0 for f in range(4)]
        fase = max(range(4), key=lambda f: fases_m[f])
        c0 = b0 + fase * beat
        umbral = _percentil_std(kick, 70) * 0.4
        compases = []
        for c in range((nb - fase) // 4):
            ks = kick[fase + c * 4: fase + c * 4 + 4]
            t = c0 + c * 4 * beat
            i0_, i1_ = int(t * FPS), int((t + 4 * beat) * FPS)
            seg_r = rms[i0_:i1_]
            mean_r = (sum(seg_r) / len(seg_r)) if seg_r else 0.0
            db = 20.0 * math.log10(mean_r + 1e-9)
            compases.append({"compas": c, "t": round(t, 3), "kick": "".join("K" if k > umbral else "." for k in ks),
                             "db": round(float(db), 1)})
    return {"bpm": round(float(bpm), 2), "beat0": round(float(b0), 3), "compas0": round(float(c0), 3),
            "duracion": round(dur, 2), "compases": compases, "secciones": secciones(compases, round(dur, 2)),
            "picos": picos}


def main():
    ap = argparse.ArgumentParser(
        description="Estima BPM, fase (beat0), primer tiempo fuerte y energía/kick por compás de un MP3.",
        epilog="Ejemplo: python3 beat_grid.py musica.mp3 --min-bpm 90 --max-bpm 140",
    )
    ap.add_argument("archivo", help="archivo de música (mp3, wav, ...)")
    ap.add_argument("--min-bpm", type=float, default=90, help="BPM mínimo a buscar (def: 90)")
    ap.add_argument("--max-bpm", type=float, default=140, help="BPM máximo a buscar (def: 140)")
    ap.add_argument("--json", dest="salida_json", default=None,
                    help="guarda {bpm, beat0, compas0, duracion, compases, secciones, picos} en este archivo JSON")
    ap.add_argument("--delta", type=float, default=3.0,
                    help="sensibilidad de los picos transitorios: desviaciones locales sobre el entorno "
                         "que el pico debe destacar (def. 3.0; menor = mas picos, mayor = solo los "
                         "impactos mas fuertes)")
    ap.add_argument("--espera", type=int, default=200,
                    help="silencio minimo entre picos, en milisegundos (def. 200)")
    a = ap.parse_args()
    if not Path(a.archivo).is_file():
        sys.exit(f"No existe el archivo: {a.archivo}")
    g = analizar(a.archivo, a.min_bpm, a.max_bpm, a.delta, a.espera)
    print(f"OK {a.archivo}\n duración {g['duracion']:.2f}s  rejilla: BPM {g['bpm']:.2f} · "
          f"BEAT0 {g['beat0']:.3f}s · primer tiempo fuerte {g['compas0']:.3f}s")
    for c in g["compases"]:
        print(f" compás {c['compas']:3d} {c['t']:7.2f}s  {c['kick']}  {c['db']:6.1f} dB  {'#' * max(0, int(c['db'] + 40))}")
    print(" secciones (un lenguaje visual por sección; cortes sugeridos):")
    for s_ in g["secciones"]:
        print(f"  {s_['nombre']:10s} {s_['inicio']:7.2f}–{s_['fin']:7.2f}s  energía {s_['energia']:5s} "
              f"{s_['db']:6.1f} dB  corte cada {s_['cortes_cada_beats']} beats")
    print("Usa BPM y BEAT0 para alinear cortes, zooms y captions con la música.")
    if g.get("picos"):
        print(f" picos transitorios ({len(g['picos'])}): candidatos a impacto para los SFX; "
              f"elige los que casen con un evento visual (máx 8-12 cues/min)")
        for p_ in g["picos"][:24]:
            print(f"   {p_['t']:7.3f}s  fuerza {p_['fuerza']:.2f}  {p_['db']:6.1f} dB")
    if a.salida_json:
        Path(a.salida_json).write_text(json.dumps(g, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"OK rejilla guardada en {a.salida_json}")


if __name__ == "__main__":
    main()
