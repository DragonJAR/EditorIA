#!/usr/bin/env python3
"""mezclar_audio.py — el ensamblado final del audio: voz + música + SFX.

La doctrina de `references/audio.md` ya decia COMO se ancla un SFX
(palabra, beat, pico, absoluta, escena+at) y `scripts/sfx.py` ya generaba el
pack de efectos. Faltaba el paso del medio: colocar cada efecto en su
instante y mezclarlo con la voz y la música. Sin esto, la pieza tiene una
cama de musica debajo pero ningun golpe de sonido: suena a video con
fondo, no a pieza disenada.

Los cues se declaran en el propio plan:

    "sfx": [
      {"escena": 2, "ancla": "palabra", "palabra": 3, "sonido": "click"},
      {"escena": 4, "ancla": "beat",   "beat": 12,  "sonido": "whoosh"},
      {"escena": 6, "ancla": "pico",   "pico": 3,   "sonido": "ding"},
      {"escena": 7, "ancla": "absoluta", "t": 12.4,  "sonido": "thud"},
      {"escena": 8, "ancla": "escena", "at": 0.3,   "sonido": "pop"}
    ]

Uso:
    python scripts/mezclar_audio.py plan.json --video out.mp4 \\
        --voz voz.mp3 --voz-palabras voz.palabras.json \\
        --grid grid.json --pack assets/sfx --musica mus.mp3 -o final.mp4

La voz se ducks (se baja ~15 dB) bajo el habla, igual que `musica.py mix`.
"""
import argparse
import json
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, os.path.join(SCRIPTS, "ffmpeg_tools"))

SONIDOS = ("click", "pop", "drop", "whoosh", "ding", "thud", "tick", "swell")
CUES_MIN_MIN = 8      # la doctrina: max 8-12 cues por minuto
CUES_MIN_MAX = 12
OFFSET_VOZ = 0.4      # la voz de cada escena entra en from + 0.4 s (voz_off.py)


def _escenas(plan):
    return sorted([e for e in plan.get("escenas") or [] if isinstance(e, dict)],
                  key=lambda e: e.get("from", 0))


def _indice_palabras_por_escena(plan):
    """Para cada escena con voz: (indice global de su primera palabra, numero de
    palabras). El indice global sigue el MISMO orden con que `voz_off.py`
    concatena los segmentos."""
    idx = {}
    n = 0
    for i, e in enumerate(_escenas(plan)):
        voz = e.get("voz")
        if not voz:
            continue
        palabras = len([p for p in str(voz).split() if p])
        idx[i] = (n, palabras)
        n += palabras
    return idx


def _instante_palabra(plan, palabras_json, num_escena, m):
    """Onset de la palabra m (1-based) de la voz de la escena num_escena.

    `num_escena` es 1-based, como en el plan; el indice de palabras por escena
    es 0-based. La voz de cada escena entra en `from + 0.4 s` (voz_off.py), y
    las palabras de todas las escenas van en el mismo orden en el archivo de
    tiempos.
    """
    if not palabras_json or not os.path.exists(palabras_json):
        return None
    with open(palabras_json, encoding="utf-8") as f:
        datos = json.load(f)
    palabras = datos.get("palabras") or []
    idx = _indice_palabras_por_escena(plan)
    clave = num_escena - 1 if num_escena >= 1 else num_escena
    if clave not in idx:
        return None
    primero, _cuantas = idx[clave]
    g = primero + (m - 1)
    if g < 0 or g >= len(palabras):
        return None
    return float(palabras[g].get("inicio", 0))


def _instante_beat(grid, n):
    if not grid:
        return None
    bpm = grid.get("bpm")
    beat0 = grid.get("beat0", 0.0)
    if not bpm:
        return None
    return float(beat0) + (n - 1) * (60.0 / float(bpm))


def _instante_pico(grid, n):
    if not grid:
        return None
    picos = grid.get("picos") or []
    if n < 1 or n > len(picos):
        return None
    return float(picos[n - 1].get("t", 0.0))


def resolver(plan, cue, palabras_json, grid):
    """Devuelve (instante, motivo_de_fallo)."""
    ancla = cue.get("ancla", "absoluta")
    escena = cue.get("escena")
    escenas = _escenas(plan)
    if ancla == "absoluta":
        t = cue.get("t")
        return (float(t), None) if t is not None else (None, "falta 't'")
    if ancla == "escena":
        if escena is None or escena < 1 or escena > len(escenas):
            return None, f"escena {escena} fuera de rango"
        e = escenas[escena - 1]
        return float(e.get("from", 0)) + float(cue.get("at", 0)), None
    if ancla == "palabra":
        t = _instante_palabra(plan, palabras_json, escena or 0, cue.get("palabra", 1))
        return (t, None) if t is not None else (None, "no se pudo resolver la palabra")
    if ancla == "beat":
        t = _instante_beat(grid, cue.get("beat", 1))
        return (t, None) if t is not None else (None, "falta la rejilla (--grid)")
    if ancla == "pico":
        t = _instante_pico(grid, cue.get("pico", 1))
        return (t, None) if t is not None else (None, "falta la rejilla (--grid)")
    return None, f"ancla desconocida: {ancla}"


def _duracion(video):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", video], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return None


def main():
    ap = argparse.ArgumentParser(
        description="Ensambla el audio final: voz + musica + SFX anclados al plan.",
        epilog="Sale 0 si la mezcla quedo lista, 1 si algo fallo, 2 si falta un archivo.")
    ap.add_argument("plan", help="ruta del plan.json (declara la lista 'sfx')")
    ap.add_argument("--video", required=True, help="video renderizado (sin audio final)")
    ap.add_argument("--voz", help="voz en off ya sintetizada (mp3/wav)")
    ap.add_argument("--voz-palabras", help="timings de palabra (salida de alinear.py)")
    ap.add_argument("--grid", help="rejilla musical (salida de beat_grid.py --json)")
    ap.add_argument("--musica", help="cama musical (mp3/wav)")
    ap.add_argument("--pack", help="directorio con el pack de SFX (salida de sfx.py)")
    ap.add_argument("--mus-vol", type=float, default=0.12,
                    help="volumen base de la musica bajo la voz (def. 0.12, ~15 dB)")
    ap.add_argument("--mus-vol-solo", type=float, default=0.8,
                    help="volumen de la musica cuando NO hay voz (def. 0.8, "
                         "el mismo nivel que `musica.py musiconly`)")
    ap.add_argument("--fade-out", type=float, default=2.0,
                    help="fade de salida de la musica cuando no hay voz (def. 2s)")
    ap.add_argument("-o", "--out", required=True, dest="out",
                    help="video final con todo el audio")
    args = ap.parse_args()

    for etiqueta, ruta in (("plan", args.plan), ("video", args.video)):
        if not os.path.exists(ruta):
            print(f"ERROR: no existe el {etiqueta}: {ruta}", file=sys.stderr)
            return 2
    with open(args.plan, encoding="utf-8") as f:
        plan = json.load(f)

    cues = plan.get("sfx") or []
    grid = None
    if args.grid and os.path.exists(args.grid):
        with open(args.grid, encoding="utf-8") as f:
            grid = json.load(f)
    dur = _duracion(args.video)

    # ── resolver cada cue a su instante ───────────────────────────────
    colocados, problemas = [], []
    for i, cue in enumerate(cues):
        sonido = cue.get("sonido")
        if sonido not in SONIDOS:
            problemas.append(f"sfx[{i}]: sonido desconocido '{sonido}' "
                             f"(disponibles: {', '.join(SONIDOS)})")
            continue
        t, fallo = resolver(plan, cue, args.voz_palabras, grid)
        if t is None:
            problemas.append(f"sfx[{i}]: {fallo}")
            continue
        ruta = os.path.join(args.pack, f"{sonido}.wav") if args.pack else None
        if ruta and not os.path.exists(ruta):
            problemas.append(f"sfx[{i}]: falta el efecto {ruta} (genera el pack con sfx.py)")
            continue
        colocados.append((t, ruta or sonido, cue.get("volumen", 1.0), sonido))

    if problemas:
        for p in problemas:
            print(f"AVISO {p}", file=sys.stderr)

    # ── densidad (la doctrina: 8-12 cues por minuto) ──────────────────
    if dur and colocados:
        dens = len(colocados) / (dur / 60.0)
        if dens > CUES_MIN_MAX:
            print(f"AVISO densidad de SFX: {dens:.1f}/min (max {CUES_MIN_MAX}/min); "
                  f"la pieza se va a saturar", file=sys.stderr)
        elif dens < CUES_MIN_MIN and dur > 6:
            print(f"AVISO densidad de SFX: {dens:.1f}/min; por debajo de {CUES_MIN_MIN}/min "
                  f"puede sonar vacia", file=sys.stderr)

    if not args.voz and not args.musica and not colocados:
        print("ERROR: no hay audio que mezclar (pasa --voz, --musica o cues de SFX)",
              file=sys.stderr)
        return 2

    # ── el grafo de mezcla ───────────────────────────────────────────
    # las entradas van en orden: video, voz, musica, SFX. El numero de
    # entrada es la mitad de los argumentos ya anadidos.
    entradas = ["-i", args.video]
    idx_voz = idx_mus = None
    sfx_idx = []
    if args.voz:
        idx_voz = len(entradas) // 2
        entradas += ["-i", args.voz]
    if args.musica:
        idx_mus = len(entradas) // 2
        entradas += ["-i", args.musica]
    for _t, ruta, _v, _s in colocados:
        sfx_idx.append(len(entradas) // 2)
        entradas += ["-i", ruta]

    dur_s = dur if dur else 0
    fc, mezcla = [], []
    hay_mus = idx_mus is not None
    hay_voz = idx_voz is not None
    if hay_mus:
        # la musica va al nivel que le corresponde: bajo la voz (0.12, la cama)
        # o sola (0.8) con fade de salida, igual que `musica.py musiconly`.
        # Sin este matiz una pieza sin voz queda 16 dB demasiado baja.
        if hay_voz:
            fc.append(f"[{idx_mus}:a]volume={args.mus_vol},apad=whole_dur={dur_s}[mx]")
        else:
            fade = max(0.0, dur_s - args.fade_out)
            fc.append(f"[{idx_mus}:a]volume={args.mus_vol_solo},"
                      f"apad=whole_dur={dur_s},"
                      f"afade=t=out:st={fade}:d={args.fade_out}[mx]")
    if hay_voz:
        if hay_mus:
            # la voz se parte: una copia acciona el ducking de la musica
            fc.append(f"[{idx_voz}:a]apad=whole_dur={dur_s},asplit=2[v1][v2]")
        else:
            fc.append(f"[{idx_voz}:a]apad=whole_dur={dur_s}[v2]")
    if hay_mus and hay_voz:
        fc.append("[mx][v1]sidechaincompress=threshold=0.015:ratio=12:attack=15:"
                  "release=600:makeup=1[duck]")
        # la musica duckeada + la voz (la copia que acciona el ducking, no la voz)
        mezcla += ["duck", "v2"]
    elif hay_mus:
        mezcla.append("mx")
    elif hay_voz:
        mezcla.append("v2")
    for j, (t, _ruta, vol, _s) in enumerate(colocados):
        ms = int(round(t * 1000))
        fc.append(f"[{sfx_idx[j]}:a]volume={vol},adelay={ms}|{ms}[s{j}]")
        mezcla.append(f"s{j}")
    fc.append("".join(f"[{m}]" for m in mezcla) +
              f"amix=inputs={len(mezcla)}:normalize=0:duration=longest,"
              f"atrim=0:{dur_s}[aout]")

    cmd = ["ffmpeg", "-y", "-v", "error"] + entradas + \
          ["-filter_complex", ";".join(fc), "-map", "0:v", "-map", "[aout]",
           "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
           "-movflags", "+faststart", args.out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"ERROR: fallo la mezcla: {(r.stderr or '').strip()[-400:]}", file=sys.stderr)
        return 1
    modo_mus = ("musica+voz" if (hay_mus and hay_voz)
                else ("musica sola" if hay_mus else ""))
    print(f"OK {args.out}: {len(colocados)} SFX, "
          f"{'voz ' if args.voz else ''}"
          f"{modo_mus + ' ' if modo_mus else ''}({dur_s:.1f}s)")
    for t, _ruta, _v, s in sorted(colocados):
        print(f"   {t:7.2f}s  {s}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
