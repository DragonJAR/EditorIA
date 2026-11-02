#!/usr/bin/env python3
"""medir_silencios.py — cuenta los silencios de una mezcla y dice si alcanzan.

Una pieza con sonido a un solo nivel se oye plana: el silencio justo antes del
giro es lo que hace que el primer sonido que vuelve pese (references/sonido.md,
"Silencios"). Aquí un silencio no es "cero digital": es una caída de al menos
`--caida` dB bajo el nivel típico de la pieza, sostenida `--minimo` segundos.

  python3 scripts/medir_silencios.py mezcla.wav
  python3 scripts/medir_silencios.py final.mp4 --caida 15 --minimo 0.4 --json

Qué cuenta: el nivel de referencia es la mediana de las ventanas que suenan (no
la media, que un solo golpe fuerte inflaría). Los silencios dentro de los
primeros y últimos `--borde` segundos no cuentan: el arranque y el cierre de
una pieza no son silencios dramáticos. Después de cada silencio se mide qué tan
fuerte vuelve el sonido (el primer sonido tras el silencio debe ser de los más
importantes de la pieza).

Exit 0 siempre que mida; con `--exigir` sale 1 si no alcanzan (piezas de 20 s o
más piden 2; las más cortas, 1).

Requiere: ffmpeg (decodifica con la misma función que medir_mezcla.py).
"""
import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import medir_mezcla as MM  # noqa: E402  (única decodificación de audio del kit)

VENTANA = 0.05            # s por ventana de nivel
PISO_DB = -70.0           # por debajo de esto una ventana es silencio digital
CAIDA_DB = 18.0           # cuánto debe caer bajo la referencia para contar
MINIMO_S = 0.4            # duración mínima de un silencio
BORDE_S = 0.5             # arranque y cierre no cuentan
LARGA_S = 20.0            # desde aquí se piden 2 silencios, no 1


def niveles_db(x, sr, ventana=VENTANA):
    """Nivel RMS en dB de cada ventana de `ventana` s (lista de floats)."""
    paso = max(1, int(sr * ventana))
    sal = []
    for i in range(0, len(x) - paso + 1, paso):
        seg = x[i:i + paso]
        if MM.np is not None and hasattr(seg, "dtype"):
            ms = float(MM.np.mean(seg.astype("float64") ** 2))
        else:
            ms = sum(float(v) * float(v) for v in seg) / len(seg)
        sal.append(10.0 * math.log10(ms + 1e-12))
    return sal


def referencia_db(niv):
    """Mediana de las ventanas que suenan; None si todo es silencio."""
    vivas = sorted(v for v in niv if v > PISO_DB)
    return vivas[len(vivas) // 2] if vivas else None


def silencios(niv, ventana=VENTANA, caida=CAIDA_DB, minimo=MINIMO_S, borde=BORDE_S):
    """Silencios interiores: [{inicio, fin, duracion, vuelve_db}] (segundos, dB
    relativos a la referencia). `vuelve_db` es el pico de la ventana siguiente
    (+0.3 s) menos la referencia: >= 0 es un retorno que pesa."""
    ref = referencia_db(niv)
    if ref is None:
        return [], None
    umbral = ref - caida
    total = len(niv) * ventana
    salida, i = [], 0
    while i < len(niv):
        if niv[i] > umbral:
            i += 1
            continue
        j = i
        while j < len(niv) and niv[j] <= umbral:
            j += 1
        ini, fin = i * ventana, j * ventana
        if fin - ini >= minimo and ini >= borde and fin <= total - borde:
            sig = niv[j:j + int(0.3 / ventana)]
            salida.append({"inicio": round(ini, 2), "fin": round(fin, 2),
                           "duracion": round(fin - ini, 2),
                           "vuelve_db": round(max(sig) - ref, 1) if sig else None})
        i = j
    return salida, round(ref, 1)


def requeridos(duracion):
    return 2 if duracion >= LARGA_S else 1


def main():
    ap = argparse.ArgumentParser(
        description="Cuenta los silencios de una mezcla (caídas sostenidas bajo "
                    "el nivel típico) y dice si alcanzan para la duración.",
        epilog="Ejemplo: python3 scripts/medir_silencios.py mezcla.wav --exigir")
    ap.add_argument("audio", help="audio o video a medir")
    ap.add_argument("--caida", type=float, default=CAIDA_DB,
                    help=f"dB bajo la referencia para contar como silencio (def: {CAIDA_DB:g})")
    ap.add_argument("--minimo", type=float, default=MINIMO_S,
                    help=f"duración mínima de un silencio en s (def: {MINIMO_S:g})")
    ap.add_argument("--borde", type=float, default=BORDE_S,
                    help=f"s del arranque y del cierre que no cuentan (def: {BORDE_S:g})")
    ap.add_argument("--exigir", action="store_true",
                    help="salir con 1 si los silencios no alcanzan (2 desde 20 s, 1 antes)")
    ap.add_argument("--json", action="store_true", help="salida JSON")
    a = ap.parse_args()

    if not os.path.isfile(a.audio):
        sys.exit(f"ERROR: no existe {a.audio}")
    if a.caida <= 0 or a.minimo <= 0 or a.borde < 0:
        sys.exit("ERROR: --caida y --minimo deben ser positivos y --borde, 0 o más")
    x = MM.decodificar(a.audio)
    duracion = len(x) / MM.SR
    if duracion < 2 * a.borde + a.minimo:
        sys.exit(f"ERROR: el audio dura {duracion:.1f} s: es demasiado corto para medir silencios")
    lista, ref = silencios(niveles_db(x, MM.SR), caida=a.caida, minimo=a.minimo, borde=a.borde)
    pide = requeridos(duracion)
    ok = len(lista) >= pide
    if a.json:
        print(json.dumps({"duracion": round(duracion, 2), "referencia_db": ref, "silencios": lista,
                          "requeridos": pide, "ok": ok}, ensure_ascii=False))
    else:
        print(f"{'OK' if ok else 'AVISO'} silencios: {len(lista)} de {pide} necesarios "
              f"({duracion:.1f} s, referencia {ref} dB)")
        for s in lista:
            peso = "" if s["vuelve_db"] is None else f" · el sonido vuelve a {s['vuelve_db']:+.1f} dB de la referencia"
            print(f"  {s['inicio']:.2f}–{s['fin']:.2f} s ({s['duracion']:.2f} s){peso}")
        if not ok:
            print("→ Abre un silencio (o casi) justo antes del giro: corta la música y el ambiente "
                  "0.4–1.2 s; el primer sonido que vuelve debe ser de los más importantes.")
        if any(s["vuelve_db"] is not None and s["vuelve_db"] < -6 for s in lista):
            print("→ AVISO: algún sonido vuelve débil tras el silencio: súbelo o mueve el silencio.")
    if a.exigir and not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
