#!/usr/bin/env python3
"""qa_entrega.py — la puerta de entrega de EditorIA, en un solo comando.

Ejecuta, en orden, todas las comprobaciones deterministas que debe pasar
una pieza antes de entregarse y devuelve UN veredicto:

  1. auditar_plan.py   estructura y tiempos del plan (si se pasa --plan)
  2. lint_copy.py      copy: longitudes, tells de genero, cifras sin fuente
  3. auto_qa.py        el render: frames negros, congelados, flashes, audio
  4. delivery_check.py el spec de la plataforma (reels, linkedin, youtube...)
  5. medir_animacion.py  coherencia de movimiento: nota, pops, tirones,
                         cuadro congelado sin grano y ocupacion de la zona segura
  6. medir_animacion.py --plan  composicion: letra real, zona segura, solapes
  7. subtitulos declarados en piezas narradas para reels/tiktok/shorts
     (con --plan: "subtitulos" en el plan o --subtitulos archivo)

Uso:
    python3 scripts/qa_entrega.py final.mp4
    python3 scripts/qa_entrega.py final.mp4 --plan plan.json
    python3 scripts/qa_entrega.py final.mp4 --plataforma linkedin --json

El motor cierra SIEMPRE con un fundido a negro (render_plan.py: el ultimo
frame es negro por diseno), asi que el chequeo de frames negros se hace con
--ignorar-fin 0.5 por defecto: sin ese margen, toda pieza de la skill
rechazaria su propio cierre. Ponlo en 0 para exigir que ni el ultimo
medio segundo tenga negro.

Sale 0 si todo pasa, 1 si algo falla, 2 si la entrada no existe.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(BASE, "scripts")
NOTA_MINIMA = 90.0     # nota de movimiento minima para dar la pieza por buena
LETRA_MIN = 26         # px: por debajo, el texto no se lee en un telefono (mismo LETRA_MIN del motor)
ZONA_MIN = 0.70        # el motor escala hasta 0.70: si toca el piso, el texto sale de la zona segura
QUIETO_MAX = 1.0       # s: racha congelada maxima (= auto_qa.FROZEN_MAX; checklist-qa.md:
                       # "ningun hold > 0.6 s salvo el CTA final", frozen <= 1 s por cada 30 s)
OCUPACION_MIN = 0.20   # caja de contenido / zona segura (= medir_animacion.OCUPACION_MIN)


def _correr(args):
    p = subprocess.run([sys.executable] + args, capture_output=True, text=True, timeout=3600)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def _paso_plan(plan, extra):
    rc, out = _correr([os.path.join(SCRIPTS, "auditar_plan.py"), plan] + extra)
    ok = rc == 0
    detalle = ""
    for linea in out.strip().splitlines():
        if linea.startswith("OK") or linea.startswith("FALLO") or "errores" in linea.lower():
            detalle = linea.strip()
            break
    return {"nombre": "plan", "ok": ok, "detalle": detalle or out.strip().splitlines()[-1:]}


def _paso_copy(plan, extra):
    rc, out = _correr([os.path.join(SCRIPTS, "lint_copy.py"), plan] + extra)
    m = re.search(r"COPY: (\d+) fallos, (\d+) avisos", out)
    detalle = m.group(0) if m else out.strip().splitlines()[-1:]
    return {"nombre": "copy", "ok": rc == 0, "detalle": detalle}


def _paso_autoqa(video, ignorar_inicio=0.0, ignorar_fin=0.0):
    rc, out = _correr([os.path.join(SCRIPTS, "auto_qa.py"), video,
                       "--ignorar-inicio", str(ignorar_inicio),
                       "--ignorar-fin", str(ignorar_fin)])
    limpio = "LIMPIO" in out
    m = re.search(r'"total":\s*(\d+)', out)
    n = m.group(1) if m else "?"
    return {"nombre": "auto_qa", "ok": rc == 0 and limpio,
            "detalle": f"{n} defectos" if n != "?" else out.strip()[-120:]}


def _paso_delivery(video, plataforma):
    rc, out = _correr([os.path.join(SCRIPTS, "ffmpeg_tools", "delivery_check.py"),
                       video, "--platform", plataforma])
    return {"nombre": f"delivery:{plataforma}", "ok": rc == 0,
            "detalle": "cumple el spec" if rc == 0 else out.strip().splitlines()[-1:]}


def _paso_medir(video):
    # La nota se lee del JSON estructurado, no de un regex sobre la salida
    # de consola: el regex exigia un basename sin espacios acabado en .mp4
    # y declaraba "no se pudo medir" piezas perfectamente medibles.
    with tempfile.TemporaryDirectory(prefix="editoria_qa_medir_") as tmp:
        ruta_json = os.path.join(tmp, "medidas.json")
        rc, out = _correr([os.path.join(SCRIPTS, "medir_animacion.py"),
                           "--video", video, "--json", ruta_json])
        if rc != 0 or not os.path.exists(ruta_json):
            return {"nombre": "movimiento", "ok": False, "detalle": "no se pudo medir"}
        with open(ruta_json, encoding="utf-8") as f:
            res = json.load(f)
    if not res:
        return {"nombre": "movimiento", "ok": False, "detalle": "no se pudo medir"}
    nota = float(res[0].get("nota", 0))
    pops = len(res[0].get("pops") or [])
    tirones = int(res[0].get("tirones") or 0)
    quieto_max, ocup = res[0].get("quieto_max"), res[0].get("ocupacion")
    fallos = _defectos_movimiento(quieto_max, ocup)
    ok = nota >= NOTA_MINIMA and pops == 0 and not fallos
    detalle = f"nota {nota} (min {NOTA_MINIMA:g}) · {pops} pops · {tirones} tirones"
    if quieto_max is not None and ocup is not None:
        detalle += f" · congelado max {quieto_max} s (max {QUIETO_MAX:g}) · ocupacion {ocup} (min {OCUPACION_MIN:g})"
    if fallos:
        detalle += " — " + "; ".join(fallos)
    return {"nombre": "movimiento", "ok": ok, "detalle": detalle}


def _defectos_movimiento(quieto_max, ocupacion):
    """Congelado largo y banda chica, con su motivo. Puro: sin video.

    `quieto_max` es la racha congelada medida SIN grano (medir_animacion
    `quietud`): auto_qa la mide con la diff de cuadro entero y el grano del
    MP4 la tapa. `ocupacion` es la caja del contenido sobre la zona segura.
    Una medicion vieja sin las claves no falla (no se inventa el defecto).
    """
    fallos = []
    if quieto_max is not None and quieto_max > QUIETO_MAX:
        fallos.append(f"cuadro congelado {quieto_max} s (> {QUIETO_MAX:g} s sin nada que se mueva: "
                      "fondo vivo o camara, fluidez.md)")
    if ocupacion is not None and ocupacion < OCUPACION_MIN:
        fallos.append(f"el contenido ocupa {ocupacion:.2f} de la zona segura (< {OCUPACION_MIN:g}): "
                      "banda chica en un lienzo grande, componer para llenar (animacion.md)")
    return fallos


def _fps(video):
    p = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0", video],
                       capture_output=True, text=True, timeout=120)
    try:
        num, den = (p.stdout.strip().split("/") + ["1"])[:2]
        return int(round(int(num) / max(1, int(den))))
    except (ValueError, IndexError):
        return 30


def _defectos_composicion(letra, zona, solapes, culpables_letra=None, culpables_zona=None):
    """Los fallos de composicion, con su motivo Y su dueno. Puro: sin video ni plan.

    Un «2 textos se pisan» sin escena ni instante no es accionable: obligaba
    a correr medir_animacion aparte (minutos) para saber QUE se pisa. El
    detalle ya lo trae la medicion (`escena@t: «a»/«b»`, letra por escena):
    la puerta lo transporta al veredicto, no lo resume a un conteo.
    """
    fallos = []
    if letra and letra < LETRA_MIN:
        f = f"letra mínima {letra} px (< {LETRA_MIN}: no se lee en un teléfono)"
        if culpables_letra:
            f += " — " + "; ".join(
                f"escena {d['escena']} «{d['texto']}» {d['letra_px']} px"
                for d in culpables_letra[:3])
        fallos.append(f)
    if zona <= ZONA_MIN:
        f = (f"la escena tocó el piso de la zona segura (x{zona:.3f}): "
             "el texto sale debajo de la UI")
        if culpables_zona:
            f += " — " + "; ".join(
                f"escena {d['escena']} x{d['zona']:.3f}" for d in culpables_zona[:3])
        fallos.append(f)
    if solapes:
        fallos.append(f"{len(solapes)} textos se pisan: " +
                        "; ".join(str(s) for s in solapes[:4]) +
                        ("; …" if len(solapes) > 4 else ""))
    return fallos


def _defecto_plan_desincronizado(ruta_plan, ruta_video):
    """El plan es posterior al video: el MP4 no puede contener ese plan.

    Puro en tiempos (mtime). La puerta mide la composicion SOBRE EL PLAN:
    si el plan se edito despues del render (una fuente retirada, un copy
    acortado) y no se volvio a renderizar, la puerta aprueba un plan que
    no es el video entregado. Eso paso: el video llevaba una fuente que
    el plan ya no tenia, pisada con un hito, y la puerta dijo 0 solapes.
    """
    try:
        if os.path.getmtime(ruta_plan) > os.path.getmtime(ruta_video) + 1:
            return ("el plan es posterior al video: el MP4 no se renderizo "
                    "desde este plan (edicion sin re-render); vuelve a "
                    "renderizar y a quemar subtitulos desde el plan actual")
    except OSError:
        return None
    return None


PLATAFORMAS_SOCIALES = ("reels", "tiktok", "shorts")


def _defecto_subtitulos(plan, plataforma, ruta_plan=None, archivo=None):
    """El defecto de subtitulos de una pieza narrada para redes, o None.

    Puro (sin video): quemar subtitulos deja pixeles que ninguna medicion
    distingue del resto de la imagen, asi que la puerta no puede VERLOS;
    lo que si puede es no dejar pasar el silencio: una pieza con voz para
    reels/tiktok/shorts tiene que DECLARAR sus subtitulos (el campo
    `subtitulos` del plan, o el archivo con --subtitulos) o la exencion.
    Sin declaracion, la replica del reel salio sin el subtitulo karaoke
    que era la firma del referente y nadie lo echo en falta.
    """
    if plataforma not in PLATAFORMAS_SOCIALES or not isinstance(plan, dict):
        return None
    escenas = plan.get("escenas") or []
    if not any(isinstance(e, dict) and str(e.get("voz") or "").strip() for e in escenas):
        return None
    if archivo:
        return None if os.path.exists(archivo) else f"el archivo de subtitulos no existe: {archivo}"
    subs = plan.get("subtitulos")
    if subs is True:
        return None
    if isinstance(subs, str) and subs.strip():
        ruta = subs if os.path.isabs(subs) else os.path.join(
            os.path.dirname(os.path.abspath(ruta_plan or "")), subs)
        return None if os.path.exists(ruta) else f"el plan declara subtitulos en {subs} pero el archivo no existe"
    return ("pieza narrada para " + plataforma + " sin subtitulos declarados: "
            "genera el SRT/karaoke desde la voz (alinear.py -> caption.py "
            "--palabras voz.palabras.json --karaoke) y declara \"subtitulos\": true "
            "en el plan, o pasa --subtitulos <archivo>; si la pieza no los lleva "
            "a proposito, dilo al usuario (nunca menos en silencio)")


def _paso_subtitulos(plan_path, plataforma, archivo=None):
    try:
        with open(plan_path, encoding="utf-8") as f:
            plan = json.load(f)
    except (OSError, ValueError) as ex:
        return {"nombre": "subtitulos", "ok": False, "detalle": f"no se pudo leer el plan: {ex}"}
    defecto = _defecto_subtitulos(plan, plataforma, plan_path, archivo)
    return {"nombre": "subtitulos", "ok": defecto is None,
            "detalle": defecto or "declarados para la pieza narrada"}


def _paso_composicion(plan, video):
    """Mide el plan con el motor: letra real, zona segura y solapes.

    Es la MISMA medicion que usa `puntuar.py` para el eje 4. Si las dos
    puertas midieran cosas distintas, una aprobaria lo que la otra rechaza:
    eso es exactamente lo que pasaba (el gate de entrega no miraba la letra,
    y la rubrica si).
    """
    tmp = tempfile.mkdtemp(prefix="editoria_qa_")
    try:
        salida = os.path.join(tmp, "medidas.json")
        rc, out = _correr([os.path.join(SCRIPTS, "medir_animacion.py"),
                           "--plan", plan, "--fps", str(_fps(video)),
                           "--json", salida])
        if rc != 0 or not os.path.exists(salida):
            # el motor explica por que no se pudo medir: se pasa su motivo,
            # no un "no se pudo" opaco
            motivo = ""
            for linea in reversed(out.strip().splitlines()):
                if linea.strip().startswith("ERROR"):
                    motivo = linea.strip()[:160]
                    break
            return {"nombre": "composicion", "ok": False,
                    "detalle": motivo or "no se pudo medir el plan"}
        with open(salida, encoding="utf-8") as f:
            res = json.load(f)
        if not res:
            return {"nombre": "composicion", "ok": False, "detalle": "el plan no midió nada"}
        letra = min((r.get("letra_min") or 0) for r in res)
        zona = min(float(r.get("zona", 1.0)) for r in res)
        solapes = [x for r in res for x in (r.get("solapes") or [])]
        # La pasada con alcance necesita la ESCENA culpable, no solo la
        # cifra global: medir_animacion ya la trae por escena y por solape.
        culpables_letra = [d for r in res for d in (r.get("letra_por_escena") or [])
                           if d.get("letra_px", 999) < LETRA_MIN]
        culpables_zona = [{"escena": r.get("escena", "?"), "zona": float(r.get("zona", 1.0))}
                          for r in res if float(r.get("zona", 1.0)) <= ZONA_MIN]
        fallos = _defectos_composicion(letra, zona, solapes,
                                       culpables_letra, culpables_zona)
        detalle = f"letra {letra or '?'} px (min {LETRA_MIN}) · zona x{zona:.3f} · {len(solapes)} solapes"
        if fallos:
            detalle = "; ".join(fallos)
        return {"nombre": "composicion", "ok": not fallos, "detalle": detalle}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(
        description="Puerta de entrega: ejecuta todas las comprobaciones "
                    "deterministas de una pieza y devuelve un veredicto unico.",
        epilog="Sale 0 si todo pasa, 1 si algo falla, 2 si la entrada no existe.")
    ap.add_argument("video", help="ruta del MP4 final a verificar")
    ap.add_argument("--plan", help="ruta del plan.json (opcional: añade el chequeo de plan y de copy)")
    ap.add_argument("--plataforma", default="reels",
                    help="destino de entrega: reels, linkedin, youtube, tiktok, shorts (def. reels)")
    ap.add_argument("--json", action="store_true",
                    help="devuelve el informe en JSON por stdout en vez de texto")
    ap.add_argument("--subtitulos", default=None,
                    help="archivo de subtitulos de la pieza (SRT/ASS): en piezas "
                         "narradas para reels/tiktok/shorts la puerta exige "
                         "subtitulos declarados (o \"subtitulos\": true en el plan)")
    ap.add_argument("--sin-medir", action="store_true",
                    help="no ejecuta medir_animacion (mas rapido; no mide los pops ni los "
                         "tirones, ni la composicion del plan)")
    ap.add_argument("--ignorar-inicio", type=float, default=0.0,
                    help="segundos iniciales a ignorar en el chequeo de negro (fade-in "
                         "intencional; def. 0)")
    ap.add_argument("--ignorar-fin", type=float, default=0.5,
                    help="segundos finales a ignorar en el chequeo de negro (el motor cierra "
                         "con fundido a negro por diseno; def. 0.5, pon 0 para exigirlos)")
    args = ap.parse_args()

    if not os.path.exists(args.video):
        print(f"ERROR: no existe el video '{args.video}'", file=sys.stderr)
        return 2
    if args.plan and not os.path.exists(args.plan):
        print(f"ERROR: no existe el plan '{args.plan}'", file=sys.stderr)
        return 2

    # Cada paso se anuncia ANTES de correr y se cierra con su tiempo: en una
    # VM modesta la puerta de una pieza de ~60 s tarda minutos (medir el
    # video y el plan son lo caro), y sin esto un timeout mata el proceso
    # sin dejar ni el veredicto parcial ni que paso estaba corriendo.
    import time as _time
    pasos = []

    def _ejecutar(nombre, fn):
        if not args.json:
            print(f"… {nombre} (puede tardar minutos en piezas de ~60 s; "
                  f"no es un cuelgue)", flush=True)
        t0 = _time.time()
        paso = fn()
        paso["segundos"] = round(_time.time() - t0, 1)
        if not args.json:
            print(f"  {nombre}: {paso['segundos']}s", flush=True)
        return paso

    if args.plan:
        pasos.append(_ejecutar("plan", lambda: _paso_plan(args.plan, [])))
        pasos.append(_ejecutar("copy", lambda: _paso_copy(args.plan, [])))
        desync = _defecto_plan_desincronizado(args.plan, args.video)
        pasos.append({"nombre": "plan-vs-video", "ok": desync is None,
                      "detalle": desync or "el plan no es posterior al video",
                      "segundos": 0.0})
    pasos.append(_ejecutar("auto_qa", lambda: _paso_autoqa(args.video, args.ignorar_inicio, args.ignorar_fin)))
    pasos.append(_ejecutar("delivery", lambda: _paso_delivery(args.video, args.plataforma)))
    if args.plan:
        pasos.append(_ejecutar("subtitulos", lambda: _paso_subtitulos(args.plan, args.plataforma, args.subtitulos)))
    if not args.sin_medir:
        pasos.append(_ejecutar("movimiento", lambda: _paso_medir(args.video)))
        if args.plan:
            pasos.append(_ejecutar("composicion", lambda: _paso_composicion(args.plan, args.video)))

    todo_ok = all(p["ok"] for p in pasos)
    if args.json:
        print(json.dumps({"video": args.video, "plataforma": args.plataforma,
                          "ok": todo_ok, "pasos": pasos}, ensure_ascii=False, indent=1))
    else:
        for p in pasos:
            print(("OK   " if p["ok"] else "FALLO") + f" {p['nombre']:22} {p['detalle']}")
        print("ENTREGA: " + ("aprobada" if todo_ok else "NO APROBADA"))
    return 0 if todo_ok else 1


if __name__ == "__main__":
    sys.exit(main())
