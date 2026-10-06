#!/usr/bin/env python3
"""medir_animacion.py — banco de métricas objetivas de la animación.

Compone cada escena del catálogo (muestras de escenas_muestra.json) a fps
completo, en 9:16 y 16:9, sin codificar, y mide sobre los frames reales:

  pop        un bloque de la imagen cambia de golpe en UN frame (algo
             aparece sin entrada: viola "nada aparece de golpe")
  tirones    jerk de la curva de movimiento + frames muertos en mitad de un
             movimiento (animación entrecortada)
  muerto     % del hold con movimiento bajo el umbral de auto_qa
  densidad   eventos de movimiento por segundo (doctrina: uno cada 0.8–1.5 s)
  letra      tamaño mínimo de texto dibujado (px sobre el lado corto 1080)
  zona       factor de escala_segura (1 = compuesta dentro de la zona segura)
  costo      segundos por frame

Cada escena recibe una nota 0–100 (penalizaciones documentadas abajo, una
sola fórmula) y la skill una nota global. Con --historial agrega la corrida
a metricas/historial.jsonl: cada mejora se compara con la anterior.

Uso:
  python scripts/medir_animacion.py                     # todo, 9:16 y 16:9
  python scripts/medir_animacion.py --solo stats,quote --formato v
  python scripts/medir_animacion.py --historial --nota "fix pops oferta"
"""
import argparse
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(AQUI)
sys.path.insert(0, AQUI)
sys.path.insert(0, os.path.join(AQUI, "ffmpeg_tools"))

LADO = 180             # lado CORTO de análisis (misma escala en 9:16 y 16:9: 1080 → 180)
BLOQUE = 10            # px del bloque para detectar pops
POP_SALTO = 70.0       # luma media de un bloque que cambia en UN frame = pop
TEXTURA = 12.0         # desvío de luma de un bloque con contenido (no fondo liso)
MOV_RADIO = 10         # px de análisis (≈ 60 px a 1080, 1800 px/s): lo que se mueve más rápido
                       # que esto se lee como teletransporte (aparición), no como movimiento
LETRA_MIN = 26         # px (sobre lado corto 1080) bajo los cuales no se lee en un teléfono
FORMATOS = {"v": (1080, 1920), "h": (1920, 1080)}

_W = {}


def _init():
    import render_plan as R
    _W["R"] = R
    _W["ctx"] = {}


def _ctx(f):
    R = _W["R"]
    R.formato(*FORMATOS[f])
    if f not in _W["ctx"]:
        _W["ctx"][f] = R.Ctx()
    return _W["ctx"][f]


def _movido(prev, cur, y, x, radio=MOV_RADIO):
    """¿El bloque nuevo ya estaba en el frame anterior, desplazado ≤ radio px?
    Un objeto que se MUEVE rápido (un slam, un barrido) cambia bloques de golpe
    pero su contenido existía al lado; lo que APARECE no estaba en ningún lado."""
    blq = cur[y:y + BLOQUE, x:x + BLOQUE]
    mejor = 1e9
    for dy in range(-radio, radio + 1):          # paso 1: con paso 2 los desplazamientos
        for dx in range(-radio, radio + 1):      # impares (3 px/frame) no se encontraban
            yy, xx = y + dy, x + dx
            if 0 <= yy and 0 <= xx and yy + BLOQUE <= prev.shape[0] and xx + BLOQUE <= prev.shape[1]:
                mejor = min(mejor, float(np.abs(prev[yy:yy + BLOQUE, xx:xx + BLOQUE] - blq).mean()))
    return mejor < POP_SALTO * 0.4   # margen para el remuestreo sub-píxel del movimiento


def medir(job):
    """Mide una escena (o un plan entero: escenas en secuencia, cortes y
    transiciones) en un formato. Devuelve el dict de métricas."""
    nombre, f, escenas, dur, fps = job
    R = _W["R"]
    ctx = _ctx(f)
    R._ESCALA.clear()
    escenas = sorted(escenas, key=lambda s_: s_["from"])
    import io
    import contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        zona = min(R.escala_segura(ctx, s_, i) for i, s_ in enumerate(escenas))
        manchas = R.presupuesto_manchas(escenas, 1 if R.TRANSICIONES == "corte_seco" else 2, avisar=False)
    e = {"to": dur}
    # tamaños de letra REALES: se instrumenta ImageDraw.text durante el render
    from PIL import ImageDraw
    tamanos = []
    original = ImageDraw.ImageDraw.text

    def espia(self, xy, text, fill=None, font=None, *a, **k):
        if font is not None and str(text).strip() and en_hold[0]:
            if self.im.size == (R.W, R.H):   # solo lo que va al cuadro, no capas auxiliares
                tamanos.append(getattr(font, "size", 0))
        return original(self, xy, text, fill, font, *a, **k)
    ImageDraw.ImageDraw.text = espia
    en_hold = [False]   # la letra se juzga ASENTADA: en una entrada todo pasa por tamaños chicos
    # cifras que cuentan: cambian de golpe POR DISEÑO (un contador no se funde);
    # sus zonas no cuentan como pop
    zonas_cifra = []
    cifra_orig = R.cifra

    def cifra_espia(d, xy, texto, font, fill, anchor="mm", final=None):
        try:
            zonas_cifra[-1].append(d.textbbox(xy, final or texto, font=font, anchor=anchor))
        except Exception:
            pass
        return cifra_orig(d, xy, texto, font, fill, anchor, final)
    R.cifra = cifra_espia
    w, h = FORMATOS[f]
    k_ = LADO / min(w, h)
    ancho_a, alto_a = int(w * k_), int(h * k_)
    frames, t0 = [], time.time()
    n = int(e["to"] * fps)
    try:
        for i in range(n):
            ti = i / fps
            en_hold[0] = any(s_["from"] + (s_["to"] - s_["from"]) * 0.5 <= ti <= s_["to"] - 0.6
                             for s_ in escenas)
            zonas_cifra.append([])
            im = R.componer(ctx, escenas, dur, ti, manchas).convert("L").resize((ancho_a, alto_a))
            frames.append(np.asarray(im, dtype=np.float32))
    finally:
        ImageDraw.ImageDraw.text = original
        R.cifra = cifra_orig
    costo = (time.time() - t0) / max(1, n)
    F = np.stack(frames)
    d = np.abs(np.diff(F, axis=0))                       # (n-1, h, w)
    energia = d.mean(axis=(1, 2))
    # pops: bloque que cambia mucho en un frame, fuera de la salida (fade común)
    hb, wb = alto_a // BLOQUE, ancho_a // BLOQUE
    bloques = d[:, :hb * BLOQUE, :wb * BLOQUE].reshape(len(d), hb, BLOQUE, wb, BLOQUE).mean(axis=(2, 4))
    # textura del bloque: contenido que cambia a OTRO contenido (dígitos que
    # cuentan, texto que se desplaza) no es una aparición; un pop es fondo o
    # superficie lisa que pasa a algo (o al revés) en un solo frame
    std = F[:, :hb * BLOQUE, :wb * BLOQUE].reshape(len(F), hb, BLOQUE, wb, BLOQUE).std(axis=(2, 4))
    contenido = (std[:-1] > TEXTURA) & (std[1:] > TEXTURA)
    candidatos = (bloques > POP_SALTO) & ~contenido
    for i in range(len(candidatos)):   # zonas de cifras que cuentan (con un bloque de margen)
        for x0_, y0_, x1_, y1_ in zonas_cifra[i + 1] if i + 1 < len(zonas_cifra) else []:
            by0, by1 = int(y0_ * k_ / BLOQUE) - 1, int(y1_ * k_ / BLOQUE) + 2
            bx0, bx1 = int(x0_ * k_ / BLOQUE) - 1, int(x1_ * k_ / BLOQUE) + 2
            candidatos[i, max(0, by0):by1, max(0, bx0):bx1] = False
    fin_activo = int((e["to"] - 0.6) * fps)
    pops = []
    for i in range(min(len(candidatos), fin_activo - 1)):
        for by, bx in zip(*np.nonzero(candidatos[i])):
            if not _movido(F[i], F[i + 1], by * BLOQUE, bx * BLOQUE):
                pops.append(round((i + 1) / fps, 2))
                break
    # tirones: frame casi quieto entre dos que se mueven (movimiento entrecortado)
    tir_t = []   # un frame quieto entre dos que se mueven: salto o congelado de un frame
    for i in range(1, len(energia) - 1):
        vec = (energia[i - 1] + energia[i + 1]) / 2
        if vec > 1.0 and energia[i] < 0.15 * vec:
            tir_t.append(round((i + 1) / fps, 2))
    tir = len(tir_t)
    jerk = float(np.mean(np.abs(np.diff(energia, 2)))) / max(1e-6, float(np.mean(energia)))
    # tiempo muerto en el hold (desde 0.5 s hasta la salida), ventana de 0.25 s
    import auto_qa as QA
    paso = max(1, int(fps / QA.FPS_MUESTREO))
    muestras = F[::paso]
    escala_qa = 1.0   # diferencia media de luma: no depende del tamaño de análisis
    dm = np.abs(np.diff(muestras, axis=0)).mean(axis=(1, 2)) * escala_qa
    t_m = np.arange(1, len(muestras)) * paso / fps
    hold = (t_m > 0.5) & (t_m < e["to"] - 0.6)
    muerto = float((dm[hold] < QA.FROZEN_DIFF).mean()) if hold.any() else 0.0
    # densidad: picos de movimiento (eventos) por segundo, energía suavizada 0.2 s
    k = max(1, int(0.2 * fps))
    sua = np.convolve(energia, np.ones(k) / k, mode="same")
    umbral = max(0.4, float(np.percentile(sua, 60)))
    picos = [i for i in range(1, len(sua) - 1)
             if sua[i] > umbral and sua[i] >= sua[i - 1] and sua[i] > sua[i + 1]]
    eventos = []
    for p in picos:   # dos picos a menos de 0.4 s son el mismo evento
        if not eventos or (p - eventos[-1]) / fps > 0.4:
            eventos.append(p)
    densidad = len(eventos) / max(0.5, e["to"] - 0.6)
    letra = int(min(tamanos) * 1080 / min(w, h)) if tamanos else 0
    if len(escenas) == 1 and escenas[0]["tipo"] in R.QUIETAS:   # quieta POR DISEÑO mientras se lee
        muerto = 0.0
    return {"escena": nombre, "formato": f, "pops": pops, "tirones": tir, "t_tirones": tir_t,
            "jerk": round(jerk, 3), "muerto": round(muerto, 3), "densidad": round(densidad, 2),
            "letra_min": letra, "zona": round(zona, 3), "costo": round(costo, 3)}


def ver(e, f, t, fps, salida):
    """Diagnóstico de un pop: frame anterior y actual lado a lado, con los
    bloques que cambian de golpe marcados en rojo. Para mirar, no adivinar."""
    from PIL import Image, ImageDraw
    _init()
    R = _W["R"]
    ctx = _ctx(f)
    R._ESCALA.clear()
    t1 = round(t * fps) / fps
    a_, b_ = (R.componer(ctx, [e], e["to"], x, set()) for x in (t1 - 1 / fps, t1))
    w, h = FORMATOS[f]
    k_ = LADO / min(w, h)
    pa = np.asarray(a_.convert("L").resize((int(w * k_), int(h * k_))), np.float32)
    pb = np.asarray(b_.convert("L").resize((int(w * k_), int(h * k_))), np.float32)
    d = np.abs(pb - pa)
    lienzo = Image.new("RGB", (w * 2 + 20, h), (40, 40, 40))
    lienzo.paste(a_, (0, 0))
    lienzo.paste(b_, (w + 20, 0))
    dr = ImageDraw.Draw(lienzo)
    for by in range(int(h * k_) // BLOQUE):
        for bx in range(int(w * k_) // BLOQUE):
            y, x = by * BLOQUE, bx * BLOQUE
            if d[y:y + BLOQUE, x:x + BLOQUE].mean() > POP_SALTO and not _movido(pa, pb, y, x):
                x0, y0 = (w + 20) + x / k_, y / k_
                dr.rectangle([x0, y0, x0 + BLOQUE / k_, y0 + BLOQUE / k_], outline=(255, 40, 40), width=4)
    lienzo.thumbnail((1600, 1600))
    lienzo.save(salida)
    print("diagnóstico:", salida)


def nota(m):
    """Una sola fórmula, explícita: 100 menos penalizaciones."""
    p = 0.0
    p += 12 * min(3, len(m["pops"]))                       # cada pop: algo aparece de golpe
    p += 4 * min(5, m["tirones"])                          # movimiento entrecortado
    p += 25 * m["muerto"]                                  # hold congelado
    dens = m["densidad"]
    if dens < 0.5:                                         # menos de un evento cada 2 s: aburre
        p += 20 * (0.5 - dens) / 0.5
    elif dens > 2.0:                                       # más de 2 eventos/s: abruma
        p += min(10, 8 * (dens - 2.0))
    if m["letra_min"] and m["letra_min"] < LETRA_MIN:      # letra que no se lee en un teléfono
        p += min(15, (LETRA_MIN - m["letra_min"]) * 1.5)
    if m["zona"] < 0.999:                                  # la red de seguridad tuvo que encoger
        p += 30 * (1 - m["zona"])
    return round(max(0.0, 100 - p), 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--solo", help="escenas separadas por coma")
    ap.add_argument("--formato", choices=["v", "h", "ambos"], default="ambos")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2)))
    ap.add_argument("--json", help="guardar el detalle en este archivo")
    ap.add_argument("--historial", action="store_true", help="agregar la corrida a metricas/historial.jsonl")
    ap.add_argument("--nota", default="", help="qué cambió en esta corrida (para el historial)")
    ap.add_argument("--ver", metavar="ESCENA:F:SEG", help="diagnosticar un pop: guarda el par de frames marcado")
    ap.add_argument("--plan", help="medir un plan.json entero (secuencia, cortes, transiciones) antes de renderizar")
    a = ap.parse_args()
    muestras = json.load(open(os.path.join(AQUI, "escenas_muestra.json"), encoding="utf-8"))["escenas"]
    solo = set(a.solo.split(",")) if a.solo else None
    fmts = ["v", "h"] if a.formato == "ambos" else [a.formato]
    # fotos y capturas sintéticas: las mismas de la galería (una sola fuente)
    import tempfile
    import galeria
    import render_plan as R
    from _comun import NEUTRO
    medios = tempfile.mkdtemp(prefix="editoria_medir_")
    galeria.assets(medios, NEUTRO["acento"])
    for e in muestras.values():
        R.resolver_medios(e, medios)
    if a.ver:
        n_, f_, t_ = a.ver.split(":")
        ver(dict(muestras[n_], tipo=n_), f_, float(t_), a.fps,
            os.path.join(tempfile.gettempdir(), f"pop_{n_}_{f_}_{t_}.png"))
        return 0
    if a.plan:
        plan = json.load(open(a.plan, encoding="utf-8"))
        R.resolver_medios(plan, os.path.dirname(os.path.abspath(a.plan)))
        nombre = os.path.splitext(os.path.basename(a.plan))[0]
        fmts_plan = fmts if a.formato != "ambos" else (
            ["h"] if str(plan.get("tamano", "")).startswith("1920") else ["v"])
        jobs = [(nombre, f, plan["escenas"], plan["duracion"], a.fps) for f in fmts_plan]
    else:
        jobs = [(n, f, [dict(e, tipo=n)], e["to"], a.fps) for f in fmts for n, e in muestras.items()
                if not solo or n in solo]
    with Pool(a.jobs, initializer=_init) as pool:
        res = pool.map(medir, jobs, chunksize=1)
    for r in res:
        r["nota"] = nota(r)
    res.sort(key=lambda r: r["nota"])
    print(f"{'escena':18s} f  nota  pops tir  jerk  muerto dens letra zona  s/frame")
    for r in res:
        print(f"{r['escena']:18s} {r['formato']}  {r['nota']:5.1f} {len(r['pops']):4d} {r['tirones']:3d} "
              f"{r['jerk']:5.2f} {r['muerto']:6.2f} {r['densidad']:4.2f} {r['letra_min']:5d} "
              f"{r['zona']:5.2f} {r['costo']:6.3f}")
    global_ = round(float(np.mean([r["nota"] for r in res])), 2)
    minima = min(res, key=lambda r: r["nota"])
    print(f"\nNOTA GLOBAL {global_} · mínima {minima['nota']} ({minima['escena']} {minima['formato']}) · "
          f"pops {sum(len(r['pops']) for r in res)} · tirones {sum(r['tirones'] for r in res)}")
    if a.json:
        json.dump(res, open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if a.historial:
        os.makedirs(os.path.join(SKILL, "metricas"), exist_ok=True)
        with open(os.path.join(SKILL, "metricas", "historial.jsonl"), "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"fecha": time.strftime("%Y-%m-%d %H:%M"), "nota": a.nota,
                                 "global": global_, "minima": minima["nota"],
                                 "pops": sum(len(r["pops"]) for r in res),
                                 "tirones": sum(r["tirones"] for r in res),
                                 "escenas": {f"{r['escena']}_{r['formato']}": r["nota"] for r in res}},
                                ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
