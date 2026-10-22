#!/usr/bin/env python3
"""puntuar.py — la rubrica de premios como puerta VERIFICABLE.

`references/rubrica-premios.md` define el liston: ocho ejes de 1 a 5, y no se
entrega si un eje baja de 4 o la media baja de 4.3. Ese liston era solo
prosa: el agente puntuaba ocho ejes a ojo y calculaba la media a mano.

Cuatro de los ocho ejes se MEDEN con herramientas que la skill ya tiene
(animacion, composicion, sonido y acabado tecnico). Los otros cuatro son
JUICIO (idea, dramaturgia, sistema visual y verdad/marca) y los responde el
agente mirando el render. Este script mide lo medible, pregunta lo que no,
y aplica el gate.

Uso:
    python scripts/puntuar.py final.mp4
    python scripts/puntuar.py final.mp4 --plan plan.json --plataforma reels
    python scripts/puntuar.py final.mp4 --ejes "1=4,2=5,5=3,7=4"

Salida: 0 si la pieza pasa el gate, 1 si no lo pasa, 2 si falta el juicio
(ejes 1, 2, 5 y 7) o si la entrada no existe.
"""
import argparse
import json
import os
import sys

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(SCRIPTS)
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, os.path.join(SCRIPTS, "ffmpeg_tools"))

import auto_qa            # noqa: E402
import delivery_check     # noqa: E402
import medir_animacion    # noqa: E402

# ── la rubrica, en codigo ───────────────────────────────────────────────
# (numero, nombre, ambito, pregunta para el juicio del agente)
EJES = [
    (1, "Idea y hook", "juicio",
     "Cual es la UNA cosa que alguien recordara manana? Si no hay respuesta, el eje no pasa de 3."),
    (2, "Dramaturgia", "juicio",
     "Hay arco (marco, tension, giro, resonancia)? O es una lista de cosas?"),
    (3, "Animacion", "medido", ""),
    (4, "Composicion y tipografia", "medido", ""),
    (5, "Sistema visual", "juicio",
     "Una paleta, una familia de curvas, un idioma de transicion y un momento firma? O se mezclan estilos?"),
    (6, "Sonido", "medido", ""),
    (7, "Verdad y marca", "juicio",
     "Cero confabulacion? Cada claim con su fuente? La marca con fidelidad total?"),
    (8, "Acabado tecnico", "medido", ""),
]
JUICIO = [1, 2, 5, 7]
UMBRAL_EJE = 4
UMBRAL_MEDIA = 4.3
DENSIDAD_OK = (0.8, 1.5)
LETRA_OK = 26            # el mismo LETRA_MIN del motor


def _puntuar_animacion(m):
    """Eje 3: nada se detiene en seco, el movimiento no es un metronomo.

    La densidad NO se puntua aqui: es un problema de ritmo (eje 2) y el motor
    ya la mide en su nota. Aqui va lo que rompe el movimiento.
    """
    pops, tiron = len(m.get("pops") or []), m.get("tirones", 0)
    arr = len(m.get("arranques") or [])
    muerto = float(m.get("muerto", 0) or 0)
    s = 5.0
    s -= min(3.0, pops * 1.0)
    s -= min(1.5, tiron * 0.5)
    s -= min(1.0, arr * 0.25)
    s -= min(2.0, muerto * 25)
    return max(1.0, round(s, 1)), (
        f"{pops} pops · {tiron} tirones · {arr} arranques · "
        f"hold congelado {muerto:.0%} · densidad {m.get('densidad', 0)}/s")


def _puntuar_composicion(plan_m):
    """Eje 4: cada frame es un poster; zona segura, letra y solapes."""
    if not plan_m:
        return None, "pasa --plan para medir letra, zona segura y solapes"
    solapes = len(plan_m.get("solapes") or [])
    zona = float(plan_m.get("zona", 1.0))
    letra = int(plan_m.get("letra_min", 0) or 0)
    s = 5.0
    s -= min(2.5, solapes * 1.5)
    if zona < 1.0:
        s -= round((1.0 - zona) * 5, 1)
    if letra and letra < LETRA_OK:
        s -= round((LETRA_OK - letra) * 0.2, 1)
        # el piso de letra es una REGLA DURA: si el texto no se lee en un
        # telefono, la tipografia no puede recibir un 4. La puerta de entrega
        # falla esta misma pieza; las dos no pueden decir cosas distintas.
        s = min(s, 3.5)
    return max(1.0, round(s, 1)), (
        f"{solapes} solapes · zona segura x{zona} · letra minima {letra or '?'} px"
        + (" (bajo el piso de 26)" if letra and letra < LETRA_OK else ""))


def _puntuar_sonido(filas):
    """Eje 6: musica con intencion y mezcla medida."""
    lufs = _fila(filas, "loudness")
    tp = _fila(filas, "true peak")
    sin_audio = _fila(filas, "audio")   # esta fila SOLO aparece si no hay pista
    if sin_audio is not None:
        return 1.0, "sin pista de audio"
    s = 5.0
    if lufs and lufs["status"] != "PASS":
        s -= 2.0
    if tp and tp["status"] != "PASS":
        s -= 1.0
    return max(1.0, round(s, 1)), (
        f"loudness {lufs['measured']} · true peak {tp['measured']}" if lufs and tp
        else "audio presente (sin medicion de loudness)")


def _puntuar_acabado(defectos, filas):
    """Eje 8: auto_qa limpio y entrega en spec."""
    fails = sum(1 for f in filas if f.get("status") == "FAIL")
    avisos = sum(1 for f in filas if f.get("status") == "WARN")
    s = 5.0
    s -= min(2.5, len(defectos) * 0.5)
    s -= min(1.5, fails * 1.0)
    s -= min(1.0, avisos * 0.5)
    return max(1.0, round(s, 1)), (
        f"{len(defectos)} defectos de render · {fails} FAIL de spec · {avisos} avisos")


def _fila(filas, nombre):
    for f in filas:
        if nombre in f.get("row", ""):
            return f
    return None


def _parse_ejes(texto):
    out = {}
    for par in (texto or "").split(","):
        par = par.strip()
        if not par:
            continue
        if "=" not in par:
            raise ValueError(f"eje mal formado: {par!r} (usa 1=4)")
        k, v = par.split("=", 1)
        try:
            out[int(k.strip())] = float(v.strip())
        except ValueError:
            raise ValueError(f"eje mal formado: {par!r} (usa 1=4)")
    return out


def _aplicar_juicio(vals, dets, juicio, medidos):
    """El juicio rellena huecos; un eje MEDIDO no se puede hablar.

    Si el texto esta bajo el piso de letra, la medida da 3,5 y la pieza no
    pasa. Si el agente pudiera escribir `--ejes "4=5"`, la regla dura se
    hablaria sola: por eso la medida gana siempre.
    """
    for n, s in sorted(juicio.items()):
        if n in medidos:
            print(f"  (el eje {n} ya esta medido: manda la medida, no el juicio)")
            continue
        vals[n] = max(1.0, min(5.0, s))
        dets[n] = "juzgado por el agente (sin medida automatica)"
    return vals, dets


def main():
    ap = argparse.ArgumentParser(
        description="Puntua la pieza con la rubrica de premios: cuatro ejes medidos y "
                    "cuatro de juicio, y aplica el gate de entrega.",
        epilog="Salida: 0 si pasa el gate (ningun eje bajo 4 y media >= 4.3), 1 si no lo "
               "pasa, 2 si falta el juicio de los ejes 1, 2, 5 y 7.")
    ap.add_argument("video", help="ruta del MP4 final a puntuar")
    ap.add_argument("--plan", help="ruta del plan.json (para medir composicion: letra, zona, solapes)")
    ap.add_argument("--plataforma", default="reels",
                    help="destino de la entrega (def. reels); ver scripts/ffmpeg_tools/_delivery.py")
    ap.add_argument("--ejes", default="",
                    help="puntuaciones de los ejes de juicio, ej. \"1=4,2=5,5=3,7=4\"")
    ap.add_argument("--json", help="guarda el informe en este archivo")
    args = ap.parse_args()

    if not os.path.exists(args.video):
        print(f"ERROR: no existe el video '{args.video}'", file=sys.stderr)
        return 2
    try:
        juicio = _parse_ejes(args.ejes)
    except ValueError as ex:
        print(f"ERROR: {ex}", file=sys.stderr)
        return 2

    # ── mediciones ──────────────────────────────────────────────────────
    try:
        F, dur, fps = medir_animacion.frames_de_video(args.video)
        mov = medir_animacion.metricas(F, fps, dur)
    except Exception as ex:
        print(f"ERROR: no se pudo medir el video: {ex}", file=sys.stderr)
        return 2

    try:
        defects = auto_qa.analisis_fino(args.video, dur, con_audio=True) or []
    except Exception:
        defects = []

    try:
        res = delivery_check.check_file(args.video, args.plataforma)
        filas = res.get("rows", []) if isinstance(res, dict) else []
    except Exception:
        filas = []

    plan_m = None
    if args.plan and os.path.exists(args.plan):
        try:
            plan_m = _medir_plan({"ruta": args.plan})
        except Exception:
            plan_m = None

    # ── puntuacion ─────────────────────────────────────────────────────
    vals, dets = {}, {}
    medidos = set()          # ejes con medida automatica: el juicio NO los pisa
    p3, d3 = _puntuar_animacion(mov)
    vals[3], dets[3] = p3, d3
    medidos.add(3)
    p4, d4 = _puntuar_composicion(plan_m)
    if p4 is not None:
        vals[4], dets[4] = p4, d4
        medidos.add(4)
    else:
        dets[4] = d4      # sin plan no hay medida: el gate no se puede cerrar
    p6, d6 = _puntuar_sonido(filas)
    vals[6], dets[6] = p6, d6
    medidos.add(6)
    p8, d8 = _puntuar_acabado(defects, filas)
    vals[8], dets[8] = p8, d8
    medidos.add(8)
    vals, dets = _aplicar_juicio(vals, dets, juicio, medidos)

    faltan = [n for n in JUICIO if n not in vals]
    sin_medir = [n for n, _, ambito, _ in EJES if ambito == "medido" and n not in vals]
    print("RUBRICA DE PREMIOS")
    for n, nombre, ambito, pregunta in EJES:
        if n in vals:
            print(f"  {n}. {nombre:26} {vals[n]:4.1f}/5   {dets.get(n, 'puntuado por el agente')}")
        elif n in sin_medir:
            print(f"  {n}. {nombre:26}   ?/5   no medido: {dets.get(n, '')}")
        else:
            print(f"  {n}. {nombre:26}   ?/5   falta tu juicio")
            print(f"       {pregunta}")
    if sin_medir:
        print(f"\nFaltan ejes medidos {sin_medir}: pasa --plan para medirlos.")
        if args.json:
            _volcar(args.json, vals, dets, faltan + sin_medir, None, None)
        return 2
    if faltan:
        print(f"\nFaltan los ejes de juicio {faltan}: puntualos y vuelve a correr.")
        print("  python scripts/puntuar.py %s --ejes \"1=4,2=5,5=3,7=4\"" % args.video)
        if args.json:
            _volcar(args.json, vals, dets, faltan + sin_medir, None, None)
        return 2

    media = round(sum(vals[n] for n, _, _, _ in EJES) / len(EJES), 2)
    flojo = [n for n, _, _, _ in EJES if vals[n] < UMBRAL_EJE]
    pasa = (not flojo) and media >= UMBRAL_MEDIA
    print(f"\nMEDIA {media} (min {UMBRAL_MEDIA}) · eje mas flojo: "
          f"{min(vals, key=lambda n: vals[n])} ({min(vals.values())})")
    print("GATE: " + ("PASA — la pieza tiene el liston" if pasa else
                      f"NO PASA —{' eje' if len(flojo) == 1 else ' ejes'} "
                      f"{flojo} por debajo de {UMBRAL_EJE}"
                      + ("" if media >= UMBRAL_MEDIA else f" y media {media} < {UMBRAL_MEDIA}")))
    if args.json:
        _volcar(args.json, vals, dets, [], media, pasa)
    return 0 if pasa else 1


def _medir_plan(plan):
    """Mide el plan con el motor (letra real, zona segura, solapes).

    Usa la misma puerta que `medir_animacion --plan`: preparar_escenas y
    medir() sobre la secuencia entera, no sobre cada escena suelta.
    """
    import render_plan as R
    import medir_animacion as MA
    with open(plan["ruta"], encoding="utf-8") as f:
        datos = json.load(f)
    R.resolver_medios(datos, os.path.dirname(os.path.abspath(plan["ruta"])))
    MA._init()
    f = "h" if str(datos.get("tamano", "")).startswith("1920") else "v"
    globales = {k: datos[k] for k in ("numeros", "subtitulos") if k in datos}
    R.aplicar_globales(globales)
    datos["escenas"] = R.preparar_escenas(MA._ctx(f), datos)
    job = (os.path.splitext(os.path.basename(plan["ruta"]))[0], f,
           datos["escenas"], datos.get("duracion", 20.0), 30, None, globales)
    return MA.medir(job)


def _volcar(ruta, vals, dets, faltan, media, pasa):
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump({"ejes": vals, "detalles": dets, "faltan": faltan,
                   "media": media, "pasa": pasa,
                   "rubrica": "references/rubrica-premios.md"}, f,
                  ensure_ascii=False, indent=1)


if __name__ == "__main__":
    sys.exit(main())
