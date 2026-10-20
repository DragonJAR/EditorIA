#!/usr/bin/env python3
"""Chequeo de compliance pre-entrega: cumple este archivo el spec de la plataforma?

Verifica duracion, aspecto/resolucion, fps, codec de video, pixel format,
tamano, sonoridad integrada (LUFS) y true peak contra la tabla canonica de
scripts/ffmpeg_tools/_delivery.py e imprime PASS/WARN/FAIL por fila.
Sale con codigo 1 si algo falla (FAIL).

Cada fila FAIL/WARN trae `fix` (el comando que lo resuelve, con las
herramientas de esta skill) y las menos obvias traen `reason` en lenguaje
llano: para quien recibe el reporte sin saber por que el spec dice lo que dice.

Concepto tomado de kajisho5/ffmpeg-skill (MIT), scripts/check.py.

Ejemplos:
  python3 delivery_check.py final.mp4 --platform reels
  python3 delivery_check.py corto.mp4 --platform tiktok --json
  python3 delivery_check.py voz.mp3 --platform podcast --lufs -16
  python3 delivery_check.py --list-platforms
"""
import argparse
import os
import sys
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _comun import (add_common, apply_common, die, emit, probe)
from _delivery import (ALIASES, END_SCREEN_YOUTUBE, PLATFORMS, PLATFORM_CHOICES,
                       resolve, spec_of, title_of)
from loudness import measure as measure_loudness


def aspect_of(w, h):
    try:
        f = Fraction(w, h).limit_denominator(20)
        return f"{f.numerator}:{f.denominator}"
    except Exception:
        return "?"


def check_file(path, platform, lufs=None, tp=None, end_screen=None):
    name = resolve(platform)
    if name not in PLATFORMS:
        die(f"plataforma desconocida: {platform} "
            f"(opciones: {', '.join(sorted(PLATFORMS))})", kind="input")
    spec = spec_of(name)
    tgt_lufs = spec["lufs"] if lufs is None else lufs
    tgt_tp = spec["tp"] if tp is None else tp
    pr = probe(path)
    v, a = pr.get("video"), pr.get("audio")
    rows = []

    def row(nombre, estado, medido, esperado, fix="", reason=""):
        rows.append({"row": nombre, "status": estado, "measured": medido,
                     "expected": esperado, "fix": fix, "reason": reason})

    # --- duracion ---
    dur = pr.get("duration")
    if spec["max_duration"] and dur is not None and dur > spec["max_duration"]:
        row("duracion", "FAIL", f"{dur:.1f}s", f"<= {spec['max_duration']}s",
            fix="recorta con scripts/ffmpeg_tools/montaje.py (cut)",
            reason="la plataforma corta o rechaza el exceso")
    else:
        row("duracion", "PASS", f"{dur:.1f}s" if dur else "?",
            f"<= {spec['max_duration']}s" if spec["max_duration"] else "sin limite")

    # --- pantalla final de YouTube (solo si se planea) ---
    if end_screen is not None:
        es = END_SCREEN_YOUTUBE
        if dur is not None and dur < es["min_video"]:
            row("end screen", "FAIL", f"video de {dur:.1f}s", f">= {es['min_video']:.0f}s",
                fix="alargar el video o renunciar a la pantalla final",
                reason="YouTube solo permite elementos de pantalla final en videos de 25 s o mas")
        elif not es["min_seg"] <= end_screen <= es["max_seg"]:
            row("end screen", "FAIL", f"{end_screen:.0f}s", f"{es['min_seg']:.0f}-{es['max_seg']:.0f}s",
                fix="ajustar el tramo final", reason="fuera de ese rango YouTube no la acepta")
        else:
            row("end screen", "PASS", f"ultimos {end_screen:.0f}s",
                "tercio der. quieto; revisar zonas con auto_qa.py --end-screen")

    # --- video ---
    if v and spec["aspects"] is not None:
        asp = aspect_of(v["width"], v["height"])
        if asp not in spec["aspects"]:
            row("aspecto", "FAIL", f"{v['width']}x{v['height']} ({asp})",
                f"uno de {spec['aspects']}",
                fix="scripts/ffmpeg_tools/verticalizar.py o crop con montaje.py",
                reason="el aspecto equivocado se publica con bandas o recorte automatico")
        elif v["height"] < spec["min_height"]:
            row("resolucion", "FAIL", f"{v['width']}x{v['height']}",
                f"altura >= {spec['min_height']}",
                fix="re-escala con el preset de _delivery.py",
                reason="por debajo del minimo la plataforma lo rechaza o lo ve borroso")
        else:
            row("aspecto", "PASS", f"{v['width']}x{v['height']} ({asp})",
                f"uno de {spec['aspects']}")
        fps = v.get("fps")
        if spec["fps_max"] and fps and fps > spec["fps_max"]:
            row("fps", "WARN", f"{fps}", f"<= {spec['fps_max']}",
                fix="re-encode conformando a 30fps")
        elif v.get("variable_frame_rate_suspected"):
            row("fps", "WARN", f"{fps} (VFR sospechado)", "CFR",
                fix="re-encode conformando a fps constante",
                reason="el VFR de telefono/grabacion de pantalla desincroniza audio y efectos")
        else:
            row("fps", "PASS", f"{fps}", f"<= {spec['fps_max']}")
        if spec["codecs"] and (v["codec"] or "") not in spec["codecs"]:
            row("video codec", "FAIL", v["codec"], f"uno de {spec['codecs']}",
                fix="re-encode con el preset de _delivery.py",
                reason="el codec equivocado lo rechaza la app o no lo reproduce el telefono")
        else:
            row("video codec", "PASS", v["codec"], f"uno de {spec['codecs']}")
        if spec["sdr_only"] and v["pix_fmt"] != "yuv420p":
            row("pixel format", "FAIL", v["pix_fmt"], "yuv420p",
                fix="re-encode con -pix_fmt yuv420p",
                reason="QuickTime e iOS rechazan video que no sea 8-bit 4:2:0")
        else:
            row("pixel format", "PASS", v["pix_fmt"], "yuv420p")
    elif not v and spec["aspects"] is not None:
        row("video", "FAIL", "sin stream de video", "se requiere video",
            fix="revisa el input: el video se perdio en algun paso")

    # --- tamano ---
    size = pr.get("size_bytes")
    if spec["max_bytes"] and size and size > spec["max_bytes"]:
        row("tamano", "FAIL", f"{size / 1024 ** 2:.0f} MB",
            f"<= {spec['max_bytes'] / 1024 ** 2:.0f} MB",
            fix="baja el CRF o recorta duracion")
    else:
        row("tamano", "PASS",
            f"{size / 1024 ** 2:.1f} MB" if size else "?",
            f"<= {spec['max_bytes'] / 1024 ** 2:.0f} MB" if spec["max_bytes"] else "sin limite")

    # --- audio / loudness ---
    if a and tgt_lufs is not None:
        m = measure_loudness(path, tgt_lufs, tgt_tp, 11.0)
        try:
            li, tpv = float(m["input_i"]), float(m["input_tp"])
            if abs(li - tgt_lufs) > spec["lufs_tol"]:
                row("loudness", "FAIL", f"{li:.1f} LUFS",
                    f"{tgt_lufs} +/- {spec['lufs_tol']}",
                    fix=f"scripts/ffmpeg_tools/loudness.py {path} -I {tgt_lufs} --tp -1.5",
                    reason="la plataforma renormaliza por su cuenta y puede aplastar la dinamica")
            else:
                row("loudness", "PASS", f"{li:.1f} LUFS",
                    f"{tgt_lufs} +/- {spec['lufs_tol']}")
            if tpv > tgt_tp:
                row("true peak", "FAIL", f"{tpv:.1f} dBTP", f"<= {tgt_tp}",
                    fix=f"scripts/ffmpeg_tools/loudness.py {path} -I {tgt_lufs} --tp -1.5",
                    reason="picos por encima del techo clippean en la conversion a AAC")
            else:
                row("true peak", "PASS", f"{tpv:.1f} dBTP", f"<= {tgt_tp}")
        except (KeyError, ValueError, TypeError):
            row("loudness", "WARN", "no medible", f"{tgt_lufs} LUFS",
                fix="revisa que el audio no este corrupto")
    elif not a:
        row("audio", "WARN", "sin pista de audio", "se espera audio",
            fix="musica.py musiconly o audio.py para agregar pista")

    fails = sum(1 for r in rows if r["status"] == "FAIL")
    warns = sum(1 for r in rows if r["status"] == "WARN")
    verdict = "FAIL" if fails else ("WARN" if warns else "PASS")
    return {"platform": name, "title": title_of(name), "rows": rows,
            "verdict": verdict, "fails": fails, "warns": warns}


def print_table(res):
    print(f"{res['title']} ({res['platform']}): {res['verdict']}")
    w = max(len(r["row"]) for r in res["rows"])
    for r in res["rows"]:
        mark = {"PASS": "OK  ", "WARN": "WARN", "FAIL": "FAIL"}[r["status"]]
        print(f"  [{mark}] {r['row']:<{w}}  {r['measured']}  (esperado: {r['expected']})")
        if r["fix"]:
            print(f"         fix: {r['fix']}")
        if r["reason"]:
            print(f"         por que: {r['reason']}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("input", nargs="?",
                    help="archivo a verificar")
    ap.add_argument("--platform", default="reels", choices=PLATFORM_CHOICES,
                    help="destino de entrega (default: reels)")
    ap.add_argument("--lufs", type=float, default=None,
                    help="objetivo LUFS (default: el de la plataforma; -16 para piezas calmas)")
    ap.add_argument("--tp", type=float, default=None,
                    help="techo de true peak en dBTP (default: el de la plataforma)")
    ap.add_argument("--end-screen", type=float, metavar="SEG",
                    help="segundos finales reservados a la pantalla final de YouTube (5-20)")
    ap.add_argument("--list-platforms", action="store_true",
                    help="lista los destinos y sus specs, sin verificar nada")
    add_common(ap)
    args = ap.parse_args()
    apply_common(args)

    if args.list_platforms:
        for n in sorted(set(PLATFORMS) - set(ALIASES)):
            s = spec_of(n)
            fr = PLATFORMS[n]["frame"]
            fstr = f"{fr['w']}x{fr['h']}" if fr else "audio"
            mx = f"{s['max_duration']}s" if s['max_duration'] else "sin limite"
            print(f"{n:<10} {fstr:<12} LUFS {s['lufs']} TP {s['tp']}  max {mx}")
        return 0
    if not args.input:
        die("falta el archivo a verificar", kind="input")
    res = check_file(args.input, args.platform, args.lufs, args.tp, args.end_screen)
    if getattr(args, "json", False):
        emit(None, platform=res["platform"], title=res["title"],
             rows=res["rows"], verdict=res["verdict"],
             fails=res["fails"], warns=res["warns"])
    else:
        print_table(res)
    return 1 if res["verdict"] == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
