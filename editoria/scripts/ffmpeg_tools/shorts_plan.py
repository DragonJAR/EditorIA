#!/usr/bin/env python3
"""Valida y ejecuta un shorts-plan.json: el contrato del short.

Cadena (cada paso reusa una herramienta del kit, sin duplicar logica):
  1. validar el plan contra references/shorts-plan-schema.md
  2. aplicar_edl.py  -> corta y concatena los segmentos
  3. verticalizar    -> recorte central al formato (si la fuente no coincide)
  4. hook overlay    -> drawtext con fuente de marca sobre el primer segmento
  5. caption.py      -> captions quemados con identidad de marca
  6. mezcla musica   -> pista ~15 dB bajo la voz, con fade de salida
  7. loudness.py     -> normaliza al LUFS objetivo
  8. portada         -> extrae el frame de portada

Ejemplo:
  python3 shorts_plan.py mi_short.json
  python3 shorts_plan.py mi_short.json --dry-run   # muestra los pasos sin ejecutar
  python3 shorts_plan.py mi_short.json --solo-validar
"""
import argparse
import json
import os
import shutil
import sys
import tempfile

KIT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, KIT)
from _comun import (add_common, apply_common, die, emit, info, probe,  # noqa: E402
                    verify_output, ffmpeg_base, run, escape_drawtext, escape_filter_path,
                    default_font_file, parse_srt, write_srt,
                    fuente_marca, resolver_pack, tokens_efectivos, texto_sobre, rgb_a_hex)


def retimear_srt(srt_path, segmentos, tmpdir):
    """Re-mapea un SRT con tiempos de la FUENTE al timeline del short
    (segmentos concatenados en orden). Los cues fuera de los segmentos se
    descartan; un cue que cruza un borde se recorta al segmento donde nace."""
    cues = parse_srt(srt_path)
    bounds, off = [], 0.0
    for s in sorted(segmentos, key=lambda x: float(x["from"])):
        f, t = float(s["from"]), float(s["to"])
        bounds.append((f, t, off))
        off += t - f
    nuevas = []
    for cs, ce, txt in cues:
        for f, t, o in bounds:
            if f <= cs < t:
                ns = o + (cs - f)
                ne = o + min(ce, t) - f
                if ne > ns + 1e-6:
                    nuevas.append((ns, ne, txt))
                break
    out = os.path.join(tmpdir, "captions_retime.srt")
    write_srt(nuevas, out)
    return out, len(nuevas), len(cues)



def validar(plan, dur_fuente):
    errores, avisos = [], []
    for campo in ("fuente", "segmentos"):
        if campo not in plan:
            errores.append(f"falta el campo requerido {campo!r}")
    segs = plan.get("segmentos") or []
    if not isinstance(segs, list) or not segs:
        errores.append("'segmentos' debe ser una lista no vacia")
        segs = []
    vistos = set()
    total = 0.0
    malos = set()  # indices con from/to invalidos: se excluyen del chequeo de solapes
    for i, s in enumerate(segs):
        tag = f"segmentos[{i}]"
        for c in ("id", "from", "to"):
            if c not in s:
                errores.append(f"{tag}: falta {c!r}")
                malos.add(i)
        if s.get("id") in vistos:
            errores.append(f"{tag}: id duplicado {s.get('id')!r}")
        vistos.add(s.get("id"))
        try:
            f, t = float(s["from"]), float(s["to"])
        except (TypeError, ValueError, KeyError):
            errores.append(f"{tag}: from/to deben ser numeros")
            malos.add(i)
            continue
        if not (0 <= f < t):
            errores.append(f"{tag}: se requiere 0 <= from < to")
            malos.add(i)
        if dur_fuente and t > dur_fuente + 1e-6:
            errores.append(f"{tag}: to={t}s excede la duracion de la fuente ({dur_fuente:.2f}s)")
        total += max(0.0, t - f)
    sanos = [s for i, s in enumerate(segs) if i not in malos]
    ordenados = sorted(sanos, key=lambda s: float(s["from"]))
    for a, b in zip(ordenados, ordenados[1:]):
        if float(b["from"]) < float(a["to"]) - 1e-6:
            errores.append(f"solape entre {a.get('id')!r} y {b.get('id')!r}")
    if total > 180:
        avisos.append(f"duracion total {total:.1f}s > 180s: ya no es formato short")
    if segs and segs[0].get("hook_overlay"):
        d_hook = float(segs[0]["to"]) - float(segs[0]["from"])
        if not (1.0 <= d_hook <= 3.0):
            avisos.append(f"el hook dura {d_hook:.1f}s; la receta pide 1-3s")
    formato = plan.get("formato", "1080x1920")
    if formato not in ("1080x1920", "1920x1080"):
        errores.append(f"formato {formato!r}: solo 1080x1920 o 1920x1080")
    return errores, avisos, total


def subproceso(cmd, dry):
    if dry:
        print("$ " + " ".join(cmd))
        return
    run(cmd)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan", help="shorts-plan.json")
    ap.add_argument("--solo-validar", action="store_true",
                    help="solo valida el plan, no renderiza")
    ap.add_argument("--saltar", default="",
                    help="pasos a saltar, separados por coma (ej. captions,musica)")
    ap.add_argument("--paleta", help="paleta del modo libre (references/paleta.md); "
                                    "también el campo \"paleta\" del plan. Si hay --brand, manda el pack")
    ap.add_argument("--brand", help="brand pack; también el campo \"brand\" del plan. "
                    "Sin ninguno: modo libre (paleta neutra), nunca una marca por defecto")
    add_common(ap)
    args = ap.parse_args()
    apply_common(args)

    if not os.path.isfile(args.plan):
        die(f"no existe el plan: {args.plan}")
    plan = json.load(open(args.plan, encoding="utf-8"))
    # Las rutas relativas del plan se resuelven contra el directorio del plan,
    # no contra el CWD: el plan debe funcionar igual se ejecute desde donde sea.
    base_dir = os.path.dirname(os.path.abspath(args.plan))
    pack = args.brand or plan.get("brand")
    if pack and not os.path.isabs(pack) and os.path.isfile(os.path.join(base_dir, pack)):
        pack = os.path.join(base_dir, pack)
    pack = resolver_pack(pack)   # identidad SOLO si el usuario la pidió
    # el acento: pack > paleta del plan > paleta por defecto (una sola puerta:
    # _comun.tokens_efectivos). Sin esto, un short en menta salia con el
    # hook en el azul de respaldo.
    paleta = args.paleta or plan.get("paleta")
    _tok = tokens_efectivos(pack, paleta)
    acento = rgb_a_hex(_tok["acento"])
    fuente_hook = fuente_marca(pack)

    def _ruta(p):
        return p if os.path.isabs(p) else os.path.join(base_dir, p)

    plan["fuente"] = _ruta(plan.get("fuente") or "")
    if isinstance(plan.get("musica"), dict) and plan["musica"].get("archivo"):
        plan["musica"]["archivo"] = _ruta(plan["musica"]["archivo"])
    if isinstance(plan.get("captions"), dict) and plan["captions"].get("srt"):
        plan["captions"]["srt"] = _ruta(plan["captions"]["srt"])
    fuente = plan.get("fuente")
    if not fuente or not os.path.isfile(fuente):
        die(f"fuente no encontrada: {fuente}")

    meta = probe(fuente)
    dur_fuente = meta.get("duration") or 0.0
    errores, avisos, total = validar(plan, dur_fuente)
    for a in avisos:
        info(f"aviso: {a}")
    if errores:
        for e in errores:
            print(f"error: {e}", file=sys.stderr)
        die(f"plan invalido ({len(errores)} errores)")
    info(f"plan valido: {len(plan['segmentos'])} segmentos, {total:.1f}s")
    if args.solo_validar:
        return

    saltar = {s.strip() for s in args.saltar.split(",") if s.strip()}
    dry = args.dry_run
    tmpdir = tempfile.mkdtemp(prefix="editoria_short_")
    try:
        formato = plan.get("formato", "1080x1920")
        tw, th = map(int, formato.split("x"))

        # 1. Cortes: EDL temporal -> aplicar_edl.py
        edl_path = os.path.join(tmpdir, "cortes.edl")
        with open(edl_path, "w", encoding="utf-8") as fh:
            for s in sorted(plan["segmentos"], key=lambda x: float(x["from"])):
                fh.write(f"{float(s['from']):.3f}-{float(s['to']):.3f}\n")
        base = os.path.join(tmpdir, "base.mp4")
        subproceso([sys.executable, os.path.join(KIT, "aplicar_edl.py"), fuente,
                    "--edl", edl_path, "-o", base], dry)
        actual = base

        # 2. Formato: recorte central si la fuente no coincide
        vw, vh = meta["video"]["width"], meta["video"]["height"]
        if (vw, vh) != (tw, th):
            vert = os.path.join(tmpdir, "vert.mp4")
            # scale para cubrir y crop central al formato objetivo
            vf = (f"scale={tw}:{th}:force_original_aspect_ratio=increase,"
                  f"crop={tw}:{th}")
            subproceso(ffmpeg_base() + ["-i", actual, "-vf", vf,
                                        "-c:v", "libx264", "-preset", "medium",
                                        "-crf", "18", "-pix_fmt", "yuv420p",
                                        "-c:a", "aac", "-b:a", "192k",
                                        "-y", vert], dry)
            actual = vert
            info(f"formato: recorte central a {formato}")

        # 3. Hook overlay sobre el primer segmento (drawtext, fuente de marca)
        primero = min(plan["segmentos"], key=lambda s: float(s["from"]))
        hook = primero.get("hook_overlay")
        if hook and "hook" not in saltar:
            font = fuente_hook if fuente_hook and os.path.isfile(fuente_hook) else (default_font_file("DejaVu Sans") or "")
            d_hook = min(3.0, float(primero["to"]) - float(primero["from"]))
            fp = f":fontfile={escape_filter_path(font)}" if font else ""
            txt = escape_drawtext(hook.upper())
            dt = (f"drawtext=text='{txt}'{fp}:fontcolor={texto_sobre(acento, tokens=_tok)}:fontsize=h/14:"
                  f"box=1:boxcolor={acento}@0.92:boxborderw=18:x=(w-text_w)/2:y=h*0.18:"
                  f"enable='lte(t,{d_hook:.2f})'")
            hook_out = os.path.join(tmpdir, "hook.mp4")
            subproceso(ffmpeg_base(texto=True) + ["-i", actual, "-vf", dt,
                                                 "-c:v", "libx264", "-preset", "medium",
                                                 "-crf", "18", "-pix_fmt", "yuv420p",
                                                 "-c:a", "copy", "-y", hook_out], dry)
            actual = hook_out
            info("hook overlay aplicado")

        # 4. Captions quemados con identidad de marca. El SRT trae tiempos
        # de la FUENTE: se re-mapea al timeline del short (concatenado)
        # antes de quemar, o los captions saldrian desfasados.
        caps = plan.get("captions") or {}
        if caps.get("srt") and "captions" not in saltar:
            srt = caps["srt"]
            if not os.path.isfile(srt):
                die(f"SRT de captions no encontrado: {srt}")
            srt, n_ok, n_total = retimear_srt(srt, plan["segmentos"], tmpdir)
            info(f"captions re-mapeados al timeline del short ({n_ok}/{n_total})")
            cap_out = os.path.join(tmpdir, "caps.mp4")
            cmd = [sys.executable, os.path.join(KIT, "caption.py"), actual,
                   "--srt", srt, "--mode", "burn", "-o", cap_out]
            if pack:
                cmd += ["--brand", pack]
            elif paleta:
                cmd += ["--paleta", paleta]
            if caps.get("phrase_aware", True):
                cmd.append("--phrase-aware")
            subproceso(cmd, dry)
            actual = cap_out
            info("captions quemados" + (" (marca del pack)" if pack else ""))

        # 5. Musica bajo la voz (~15 dB por regla de la skill)
        mus = plan.get("musica") or {}
        if mus.get("archivo") and "musica" not in saltar:
            if not os.path.isfile(mus["archivo"]):
                die(f"musica no encontrada: {mus['archivo']}")
            db = float(mus.get("db_bajo_voz", 15))
            mus_out = os.path.join(tmpdir, "mus.mp4")
            # voz al frente; musica atenuada con fade de salida de 1.5s
            fade_st = max(0.0, total - 1.5)
            fmus = (f"[1:a]volume={-db:.1f}dB,afade=t=out:st={fade_st:.2f}:d=1.5,"
                    f"apad[bg];[0:a][bg]amix=inputs=2:duration=first:dropout_transition=0[a]")
            subproceso(ffmpeg_base() + ["-i", actual, "-i", mus["archivo"],
                                        "-filter_complex", fmus, "-map", "0:v",
                                        "-map", "[a]", "-c:v", "copy",
                                        "-c:a", "aac", "-b:a", "192k",
                                        "-shortest", "-y", mus_out], dry)
            actual = mus_out
            info(f"musica mezclada ({db:.0f} dB bajo la voz)")

        # 6. Loudness al objetivo
        lufs = float(plan.get("loudness_lufs", -14))
        loud_out = os.path.join(tmpdir, "loud.mp4")
        subproceso([sys.executable, os.path.join(KIT, "loudness.py"), actual,
                    "-o", loud_out, "-I", str(lufs)], dry)
        actual = loud_out

        # 7. Salida final + portada
        salida = plan.get("salida") or os.path.splitext(fuente)[0] + "_short.mp4"
        if not dry:
            os.replace(actual, salida)
        else:
            print(f"$ mv {actual} {salida}")
        v = verify_output(salida) if not dry else {}
        info(f"OK {salida}" + (f" ({v.get('duration', 0):.1f}s)" if v else ""))

        portada = plan.get("portada") or {}
        if portada.get("at") is not None and "portada" not in saltar:
            png = os.path.splitext(salida)[0] + "_portada.png"
            subproceso(ffmpeg_base() + ["-ss", str(float(portada["at"])),
                                        "-i", salida, "-frames:v", "1",
                                        "-y", png], dry)
            if not dry:
                info(f"portada: {png}")

        emit(salida, segmentos=len(plan["segmentos"]), duracion_s=round(total, 1),
             formato=formato, lufs=lufs)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
