#!/usr/bin/env python3
"""
verificar_ritmo.py — EditorIA: prueba anti-slideshow de un video ya renderizado.

Mide dos fallas distintas:
  1. cadencia (metrónomo): tomas de igual duración con la misma forma son
     diapositivas aunque se muevan. Requiere CV de duraciones >= 0.25.
  2. quietud: una pieza sin pausas se lee plana. Requiere >= 25% de cuadros
     casi quietos y al menos una pausa >= 1.0 s.

La ráfaga (>= 3 cambios grandes en 1.5 s) es WARN cuando falta: un concepto
sin impactos (un elemento que se transforma, una cámara continua) no es un
defecto.

Uso:
  python scripts/verificar_ritmo.py video.mp4 [--cortes 0,1.6,3.0,4.8]
  Si no se dan --cortes, se detectan con scene-select de ffmpeg.

Salida: una línea PASS/WARN/FAIL por prueba; exit 1 si alguna FAIL.
"""
import argparse, subprocess, sys
try:
    import numpy as np
except ModuleNotFoundError as _e_dep:
    if "-h" not in sys.argv and "--help" not in sys.argv:
        sys.exit(f"ERROR: falta dependencia ({_e_dep.name}): pip install numpy")
    np = None

STILL_THRESH = 0.5     # diff media (0-255, a 320px) bajo la cual el cuadro es "quieto"
BIG_THRESH = 8.0       # diff media que cuenta como "cambio grande"
CV_MIN = 0.25          # coeficiente de variación mínimo de duraciones de toma
STILL_MIN = 0.25       # fracción mínima de cuadros quietos
QUIET_STRETCH_MIN = 1.0  # segundos de la pausa más larga requerida
BURST_WIN = 1.5        # ventana de ráfaga en segundos
BURST_COUNT = 3        # cambios grandes mínimos dentro de la ventana


def frame_diffs(video):
    """Devuelve (fps_muestreo, diffs[]) entre cuadros consecutivos a 320px."""
    cmd = ["ffmpeg", "-v", "error", "-i", video,
           "-vf", "scale=320:-1,fps=6", "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        sys.exit("ERROR: ffmpeg no pudo leer " + video)
    raw = r.stdout
    # averiguar alto desde el primer intento
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                            "-show_entries", "stream=width,height",
                            "-of", "csv=p=0", video],
                           capture_output=True, text=True).stdout.strip().split(",")
    w, h = int(probe[0]), int(probe[1])
    h320 = max(1, round(h * 320 / w))
    n = len(raw) // (320 * h320)
    frames = np.frombuffer(raw[:n * 320 * h320], dtype=np.uint8).reshape(n, -1).astype(np.float32)
    diffs = np.abs(np.diff(frames, axis=0)).mean(axis=1)
    return 6.0, diffs


def auto_cortes(video):
    out = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", video,
         "-filter:v", "select='gt(scene,0.35)',showinfo",
         "-f", "null", "-"], capture_output=True, text=True)
    cortes = [0.0]
    for line in out.stderr.splitlines():
        if "pts_time:" in line:
            t = line.split("pts_time:")[1].split()[0]
            try:
                cortes.append(float(t))
            except ValueError:
                pass
    return sorted(set(cortes))


def leg(nombre, estado, detalle):
    print(f"  {estado:4}  {nombre:10} {detalle}")
    return estado != "FAIL"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--cortes", default=None,
                    help="tiempos de corte en segundos, ej. 0,1.6,3.0,4.8")
    import os as _os, sys as _sys
    _sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "ffmpeg_tools"))
    from _comun import ayudar
    ayudar(ap, {'video': 'video renderizado a verificar'})
    a = ap.parse_args()

    fps, diffs = frame_diffs(a.video)
    ok = True

    cortes = ([float(x) for x in a.cortes.split(",")] if a.cortes
              else auto_cortes(a.video))
    if len(cortes) < 2:
        ok &= leg("cadencia", "WARN",
                  "sin cortes detectados — pasar --cortes para medir cadencia")
    else:
        durs = np.diff(sorted(cortes))
        cv = float(np.std(durs) / np.mean(durs)) if np.mean(durs) > 0 else 0.0
        ok &= leg("cadencia", "PASS" if cv >= CV_MIN else "FAIL",
                  f"CV={cv:.2f} (min {CV_MIN}) en {len(durs)} tomas")

    quiet = diffs < STILL_THRESH
    still_frac = float(quiet.mean())
    ok &= leg("quietud", "PASS" if still_frac >= STILL_MIN else "FAIL",
              f"{still_frac:.0%} cuadros quietos (min {STILL_MIN:.0%})")

    # pausa más larga: racha de cuadros quietos consecutivos
    best = cur = 0
    for q in quiet:
        cur = cur + 1 if q else 0
        best = max(best, cur)
    stretch = best / fps
    ok &= leg("pausa", "PASS" if stretch >= QUIET_STRETCH_MIN else "FAIL",
              f"pausa más larga {stretch:.1f}s (min {QUIET_STRETCH_MIN:.0f}s)")

    big = diffs > BIG_THRESH
    win = max(1, int(BURST_WIN * fps))
    bursts = sum(1 for i in range(len(big) - win + 1) if big[i:i + win].sum() >= BURST_COUNT)
    leg("ráfaga", "PASS" if bursts > 0 else "WARN",
        f"{bursts} ventana(s) con ≥{BURST_COUNT} cambios grandes en {BURST_WIN}s")

    print("RESULTADO:", "PASS — no lee como slideshow" if ok
          else "FAIL — revisar cadencia/pausas (ver references/ritmo.md)")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
