#!/usr/bin/env python3
"""medir_animacion.py — banco de métricas objetivas de la animación.

Compone cada escena del catálogo (muestras de escenas_muestra.json) a fps
completo, en 9:16 y 16:9, sin codificar, y mide sobre los frames reales:

  pop        un bloque de la imagen cambia de golpe en UN frame (algo
             aparece sin entrada: viola "nada aparece de golpe")
  tirones    jerk de la curva de movimiento + frames muertos en mitad de un
             movimiento (animación entrecortada)
  muerto     % del hold con movimiento bajo el umbral de auto_qa
  quieto     % del tiempo activo con el cuadro congelado (nada se mueve en
             toda la imagen) medido sin el grano, y la racha más larga en s
  ocupacion  fracción de la zona segura que cubre la caja del contenido
             (una banda chica en un lienzo enorme), por escena y media
  densidad   eventos de movimiento por segundo (banda del motor: 0.5–2.0
             eventos/s; ritmo cómodo: uno cada 0.8–1.5 s)
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
import shutil
import sys
import time
from multiprocessing import Pool

try:
    import numpy as np
except ModuleNotFoundError as _e_dep:
    if "-h" not in sys.argv and "--help" not in sys.argv:
        sys.exit(f"ERROR: falta dependencia ({_e_dep.name}): pip install numpy")
    np = None

AQUI = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(AQUI)
sys.path.insert(0, AQUI)
sys.path.insert(0, os.path.join(AQUI, "ffmpeg_tools"))

from _plataforma import dir_temp  # noqa: E402

LADO = 180             # lado CORTO de análisis (misma escala en 9:16 y 16:9: 1080 → 180)
BLOQUE = 10            # px del bloque para detectar pops
POP_SALTO = 70.0       # luma media de un bloque que cambia en UN frame = pop
TEXTURA = 12.0         # desvío de luma de un bloque con contenido (no fondo liso)
CELDA_MOV = 1.0      # niveles de gris/frame: una celda que se mueve de verdad (la respiración no llega)
POP_PROPORCION = 0.35  # fracción de bloques abruptos sin origen para llamarlo aparición
MOV_RADIO = 10         # px de análisis (≈ 60 px a 1080, 1800 px/s): lo que se mueve más rápido
                       # que esto se lee como teletransporte (aparición), no como movimiento
LETRA_MIN = 26         # px (sobre lado corto 1080) bajo los cuales no se lee en un teléfono
QUIETO_SIGMAS = 4      # un bloque se movió si cambia más que 4 veces el piso de grano medido
OCUPACION_MIN = 0.20   # fracción de la zona segura bajo la cual la pieza es una banda chica:
                       # medido en HEAD, las escenas más angostas POR DISEÑO (apertura,
                       # cartel: solo tipo) ocupan 0.17–0.23; las de datos 0.50–0.86
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


def _suave(a):
    from PIL import Image, ImageFilter
    return np.asarray(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
                      .filter(ImageFilter.GaussianBlur(1.5)), np.float32)


def _sin_origen(prev, cur, bloques):
    """Bloques que cambian de golpe y cuyo contenido NO estaba cerca en el frame
    anterior, ni exacto ni suavizado (lo suavizado absorbe un escalado leve)."""
    resto = [(by, bx) for by, bx in bloques if not _movido(prev, cur, by * BLOQUE, bx * BLOQUE)]
    if not resto:
        return []
    ps, cs = _suave(prev), _suave(cur)
    return [(by, bx) for by, bx in resto if not _movido(ps, cs, by * BLOQUE, bx * BLOQUE)]


def _es_pop(prev, cur, bloques):
    """Un objeto que APARECE deja casi todos sus bloques sin origen; uno que se
    mueve o escala, solo unos pocos en su borde. Pop = ≥35 % sin origen."""
    if not bloques:
        return False
    return len(_sin_origen(prev, cur, bloques)) >= POP_PROPORCION * len(bloques)


def _letra_en_reposo(tamanos, ultimos=None):
    """El tamaño de cada texto EN REPOSO, no el más pequeño que pasó por la pantalla.

    Un elemento que entra con resorte pasa por muchos tamaños (un boton que
    crece de 0 a 40 px dibuja su texto a 21 px a mitad de camino). Medir
    "el más chico que se vio" castigaba la ANIMACION, no la tipografia: 10 de
    10 piezas de la demo caian por debajo del piso de letra con un texto que
    en reposo va a 40 px. Lo que vale es el tamaño con el que el texto SE
    QUEDA.

    Y "se queda" se mide por su ULTIMO dibujo, no por la mediana de la
    ventana: la mediana era una aproximacion que fallaba cuando la ventana
    de reposo (la segunda mitad de la escena) cae ENTERA dentro de la
    animacion de entrada de un texto que entra tarde (un boton al final de
    una escena corta). Ahi la mediana cae en mitad de camino y el texto se
    juzga por un tamaño que no es el suyo. El ultimo dibujo es el estado en
    el que el texto se queda.

    Un texto visto menos de 3 frames se ignora: entra justo al final de la
    ventana y nunca llegó a asentar.
    """
    fuera = []
    for texto, cnt in tamanos.items():
        # un simbolo ("✓", "·") no es una letra: no se juzga su tamaño
        if not any(ch.isalnum() for ch in texto):
            continue
        total = sum(cnt.values())
        if total < 3:
            continue
        if ultimos and texto in ultimos:
            elegido = ultimos[texto]
        else:
            acum = 0
            elegido = max(cnt)
            for tam, n in sorted(cnt.items()):
                acum += n
                if acum * 2 >= total:
                    elegido = tam
                    break
        fuera.append(elegido)
    return min(fuera) if fuera else 0


def medir(job):
    """Mide una escena (o un plan entero: escenas en secuencia, cortes y
    transiciones) en un formato. Devuelve el dict de métricas."""
    nombre, f, escenas, dur, fps = job[:5]
    ventana = job[5] if len(job) > 5 else None   # (t0, t1): medir solo un tramo (un corte)
    R = _W["R"]
    R.aplicar_globales(job[6] if len(job) > 6 else {})   # numeros, banda de subtítulos del plan
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
    from collections import Counter
    tamanos = {}        # texto -> Counter{tamaño: frames en que se dibuja así}
    ultimos = {}        # texto -> el tamaño de su ULTIMO dibujo (el que se queda)
    ultimos_escena = {}  # (nº escena, tipo, texto) -> tamaño en reposo en ESA escena
    escena_hold = [None]  # (nº escena, tipo) en hold en el frame que se compone
    original = ImageDraw.ImageDraw.text

    def espia(self, xy, text, fill=None, font=None, *a, **k):
        if font is not None and str(text).strip() and en_hold[0]:
            if self.im.size == (R.W, R.H):   # solo lo que va al cuadro, no capas auxiliares
                t = str(text)
                # un simbolo no es una letra: el "✓" de una tarjeta dibujado a
                # 14 px no es "texto ilegible", es un check. Los numeros si
                # cuentan (son datos), los signos sueltos no.
                if any(ch.isalnum() for ch in t):
                    _tam = int(getattr(font, "size", 0))
                    tamanos.setdefault(t, Counter())[_tam] += 1
                    ultimos[t] = _tam    # el estado en el que el texto se queda
                    if escena_hold[0] is not None:
                        ultimos_escena[(escena_hold[0][0], escena_hold[0][1], t)] = _tam
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
    i0, i1 = (int(ventana[0] * fps), int(ventana[1] * fps)) if ventana else (0, int(e["to"] * fps))
    n = i1 - i0
    try:
        for i in range(i0, i1):
            if n >= 100 and i % max(1, n // 4) == 0:
                print(f"  componiendo {nombre} ({f}): frame {i - i0}/{n}", flush=True)
            ti = i / fps
            en_hold[0] = any(s_["from"] + (s_["to"] - s_["from"]) * 0.5 <= ti <= s_["to"] - 0.6
                             for s_ in escenas)
            escena_hold[0] = next(
                ((j + 1, s_.get("tipo", "?")) for j, s_ in enumerate(escenas)
                 if s_["from"] + (s_["to"] - s_["from"]) * 0.5 <= ti <= s_["to"] - 0.6),
                None)
            zonas_cifra.append([])
            im = R.componer(ctx, escenas, dur, ti, manchas).convert("L").resize((ancho_a, alto_a))
            frames.append(np.asarray(im, dtype=np.float32))
    finally:
        ImageDraw.ImageDraw.text = original
        R.cifra = cifra_orig
    costo = (time.time() - t0) / max(1, n)
    F = np.stack(frames)
    m = metricas(F, fps, (n / fps + 0.6) if ventana else dur, zonas_cifra, k_, caja=R.caja_segura())
    if not ventana and len(escenas) > 1:   # la escena chica, con su nombre: la media la diluye
        m["ocupacion_escena"] = ocupacion_por_escena(
            F, fps, [(j + 1, s_.get("tipo", "?"), s_["from"], s_["to"]) for j, s_ in enumerate(escenas)],
            R.caja_segura())
    letra = int(_letra_en_reposo(tamanos, ultimos) * 1080 / min(w, h)) if tamanos else 0
    # La letra culpable, CON su escena y su texto: un «21 px» global obliga a
    # inspeccionar frame a frame hasta dar con la escena (dos ciclos de
    # render en la replica del reel). Esto es lo que la pasada con alcance
    # de qa-entrega.md necesita para corregir sin mirar toda la pieza.
    letra_por_escena = sorted(
        ({"escena": f"{num}:{tipo}", "texto": texto[:40],
          "letra_px": int(tam * 1080 / min(w, h))}
         for (num, tipo, texto), tam in ultimos_escena.items()),
        key=lambda d: d["letra_px"])
    pisan = [] if ventana else solapes(R, ctx, escenas, dur)
    if len(escenas) == 1 and escenas[0]["tipo"] in R.QUIETAS:   # se LEE quieta (render_plan.QUIETAS)
        # su flotación (render_plan.vida) no llega al umbral de `muerto` (diff de
        # cuadro entero); `quieto` (por bloque) sí la ve y se mide como en todas
        m["muerto"] = 0.0
        m["quieta"] = True   # ni la densidad la juzga: entra una vez y se queda para leerse
    return dict({"escena": nombre, "formato": f}, **m, letra_min=letra, zona=round(zona, 3), solapes=pisan,
                letra_por_escena=letra_por_escena, costo=round(costo, 3))


def _rejilla(A):
    """(n, alto, ancho) -> (n, hb, BLOQUE, wb, BLOQUE): la grilla de bloques de
    pops, textura, quietud y ocupación (una sola)."""
    hb, wb = A.shape[1] // BLOQUE, A.shape[2] // BLOQUE
    return A[:, :hb * BLOQUE, :wb * BLOQUE].reshape(len(A), hb, BLOQUE, wb, BLOQUE)


def _rachas(v):
    """[(i0, i1)] de las rachas de True de un vector booleano (i1 exclusivo)."""
    out, i0 = [], None
    for i, x in enumerate(list(v) + [False]):
        if x and i0 is None:
            i0 = i
        elif not x and i0 is not None:
            out.append((i0, i))
            i0 = None
    return out


def _muestreo(F, fps, dur):
    """Muestras a la cadencia de auto_qa y la ventana activa (desde 0.5 s hasta
    la salida común): la misma ventana para `muerto` y `quieto`.
    Devuelve (muestras, paso, t de cada par, máscara activa por par)."""
    import auto_qa as QA
    paso = max(1, int(fps / QA.FPS_MUESTREO))
    muestras = F[::paso]
    t_m = np.arange(1, len(muestras)) * paso / fps
    return muestras, paso, t_m, (t_m > 0.5) & (t_m < dur - 0.6)


def quietud(F, fps, dur):
    """Cuadro CONGELADO sin la influencia del grano (checklist-qa.md: frozen =
    nada se mueve en toda la imagen; un elemento quieto sobre fondo vivo no
    lo es).

    La diff de cuadro entero no sirve en un MP4: medido en el video real del
    catálogo, el grano + el códec dejan un piso de ~0.42 niveles (percentil 5),
    por encima de FROZEN_DIFF (0.35); auto_qa vio 1.75 s de un congelado de
    3.0 s y ninguno de los cortos. El grano es de media cero: promediado por
    bloque (la grilla de BLOQUE) se va; el movimiento no. Un par de muestras
    está quieto si NINGÚN bloque cambia más que max(CELDA_MOV, QUIETO_SIGMAS ×
    piso): el piso es el ruido por bloque MEDIDO en la pieza (desvío robusto
    en sus muestras más calmas; 0.10 en el video real, 0.015 en un render sin
    grano), así que el umbral solo sube con un grano pesado y lo compuesto
    (sin grano) y lo decodificado dan la misma respuesta.

    Cuenta solo la quietud sostenida (≥ 0.5 s, como `muerto`) en la ventana
    activa, y no la racha que llega hasta el final: es el CTA de cierre, la
    excepción de la doctrina. Devuelve {"quieto": fracción, "quieto_max": s}."""
    import auto_qa as QA
    muestras, paso, t_m, activo = _muestreo(F, fps, dur)
    if len(muestras) < 2:
        return {"quieto": 0.0, "quieto_max": 0.0}
    cambio = np.abs(np.diff(_rejilla(muestras).mean(axis=(2, 4)), axis=0))   # (pares, hb, wb)
    ruido = 1.4826 * np.median(cambio, axis=(1, 2))      # desvío robusto por par (fondo = mayoría)
    piso = float(np.percentile(ruido, 10))
    quieto = ((cambio > max(CELDA_MOV, QUIETO_SIGMAS * piso)).sum(axis=(1, 2)) == 0) & activo
    ultimo = int(np.nonzero(activo)[0][-1]) if activo.any() else -1
    racha = max(2, int(round(0.5 * QA.FPS_MUESTREO)))
    largas = [(a, b) for a, b in _rachas(quieto) if b - a >= racha and b - 1 < ultimo]
    s_par = paso / fps
    return {"quieto": round(sum(b - a for a, b in largas) / max(1, int(activo.sum())), 3),
            "quieto_max": round(max((b - a for a, b in largas), default=0) * s_par, 2)}


def _caja_de(ancho_a, alto_a, caja=None):
    """La zona segura en px de análisis. `caja` es la del motor (x0, y0, x1,
    y1 a lado corto 1080, render_plan.caja_segura); sin ella (un video) se
    le pide al motor la de ese aspecto."""
    k_ = min(ancho_a, alto_a) / 1080
    if caja is None:
        import render_plan as R
        w, h = round(ancho_a / k_), round(alto_a / k_)
        if (R.W, R.H) != (w, h):
            R.formato(w, h)
        caja = R.caja_segura()
    return tuple(v * k_ for v in caja)


def ocupacion(F, caja=None):
    """Fracción media de la zona segura que cubre la caja del contenido: los
    bloques con textura (desvío > TEXTURA: tinta, no fondo liso ni manchas
    difusas) dentro de la zona segura, su rectángulo envolvente sobre el área
    de la zona. Una banda chica en un lienzo enorme da poco aunque se mueva
    bien. `caja` en px a lado corto 1080 (None = la del motor)."""
    if not len(F):
        return 0.0
    x0, y0, x1, y1 = _caja_de(F.shape[2], F.shape[1], caja)
    tex = _rejilla(F).std(axis=(2, 4)) > TEXTURA                 # (n, hb, wb)
    yc = (np.arange(tex.shape[1]) + 0.5) * BLOQUE
    xc = (np.arange(tex.shape[2]) + 0.5) * BLOQUE
    filas, cols = (yc >= y0) & (yc <= y1), (xc >= x0) & (xc <= x1)
    area = max(1, int(filas.sum()) * int(cols.sum()))
    tex = tex & filas[None, :, None] & cols[None, None, :]
    fr = []
    for t in tex:
        yy, xx = np.nonzero(t)
        fr.append(0.0 if not len(yy) else (np.ptp(yy) + 1) * (np.ptp(xx) + 1) / area)
    return round(float(np.mean(fr)), 3)


def ocupacion_por_escena(F, fps, escenas, caja=None):
    """[{escena, ocupacion}] en el reposo de cada escena (de su mitad hasta
    0.6 s antes del final, la ventana de la letra). `escenas` = [(nº, tipo,
    from, to)] como `_escenas_del_plan`."""
    import auto_qa as QA
    paso = max(1, int(fps / QA.FPS_MUESTREO))
    out = []
    for num, tipo, f0, f1 in escenas:
        i0, i1 = int((f0 + (f1 - f0) * 0.5) * fps), int((f1 - 0.6) * fps)
        if i1 > i0:
            out.append({"escena": f"{num}:{tipo}", "ocupacion": ocupacion(F[i0:i1:paso], caja)})
    return out


def _digito_nuevo(candidatos, cambia):
    """(n, hb, wb) bool: los candidatos a pop que son el DÍGITO NUEVO de un
    contador. Un contador que suma un dígito ("8" -> "11") deja bloques que
    pasan de fondo a tinta pegados en la misma fila a bloques con tinta que
    cambian de golpe a otra tinta (las cifras que cuentan). Con el motor eso
    lo dicen las zonas de cifra; en un video no hay motor, y el gauge del plan
    de muestra marcaba un pop en 20.43 s que la medición por escena no ve.
    Un objeto que aparece lejos de una cifra que cuenta sigue siendo pop."""
    out = np.zeros_like(candidatos)
    for i, y in zip(*np.nonzero((candidatos & ~cambia).any(axis=2))):
        fila = candidatos[i, y] | cambia[i, y]
        for a, b in _rachas(fila):   # tramos contiguos de la fila: si uno trae cifra, es contador
            if cambia[i, y, a:b].any():
                out[i, y, a:b] = candidatos[i, y, a:b]
    return out


def metricas(F, fps, dur, zonas_cifra=None, k_=1.0, caja=None):
    """Las métricas de movimiento sobre frames en gris (n, alto, ancho) a la
    escala de análisis. Una sola implementación para escenas, planes y videos.
    `caja`: zona segura del motor (px a lado corto 1080); None = la del aspecto."""
    alto_a, ancho_a = F.shape[1], F.shape[2]
    d = np.abs(np.diff(F, axis=0))                       # (n-1, h, w)
    energia = d.mean(axis=(1, 2))
    # pops: bloque que cambia mucho en un frame, fuera de la salida (fade común)
    hb, wb = alto_a // BLOQUE, ancho_a // BLOQUE
    bloques = _rejilla(d).mean(axis=(2, 4))
    # textura del bloque: contenido que cambia a OTRO contenido (dígitos que
    # cuentan, texto que se desplaza) no es una aparición; un pop es fondo o
    # superficie lisa que pasa a algo (o al revés) en un solo frame
    std = _rejilla(F).std(axis=(2, 4))
    contenido = (std[:-1] > TEXTURA) & (std[1:] > TEXTURA)
    candidatos = (bloques > POP_SALTO) & ~contenido
    for i in range(len(candidatos)):   # zonas de cifras que cuentan (con un bloque de margen)
        zs = zonas_cifra[i + 1] if zonas_cifra and i + 1 < len(zonas_cifra) else []
        for x0_, y0_, x1_, y1_ in zs:
            by0, by1 = int(y0_ * k_ / BLOQUE) - 1, int(y1_ * k_ / BLOQUE) + 2
            bx0, bx1 = int(x0_ * k_ / BLOQUE) - 1, int(x1_ * k_ / BLOQUE) + 2
            candidatos[i, max(0, by0):by1, max(0, bx0):bx1] = False
    if zonas_cifra is None:   # un video: sin el motor, las zonas de cifra se infieren
        candidatos &= ~_digito_nuevo(candidatos, (bloques > POP_SALTO) & contenido)
    fin_activo = int((dur - 0.6) * fps)
    pops = []
    for i in range(min(len(candidatos), fin_activo - 1)):
        if _es_pop(F[i], F[i + 1], list(zip(*np.nonzero(candidatos[i])))):
            pops.append(round((i + 1) / fps, 2))
    tir_t = []   # un frame quieto entre dos que se mueven: salto o congelado de un frame
    for i in range(1, len(energia) - 1):
        # movimiento a AMBOS lados (min, no promedio): un frame quieto antes de que
        # algo arranque es el inicio de un movimiento, no un tirón
        vec = min(energia[i - 1], energia[i + 1])
        if vec > 1.0 and energia[i] < 0.15 * vec:
            tir_t.append(round((i + 1) / fps, 2))
        # salto: UN frame con mucho más movimiento que sus dos vecinos (algo se
        # teletransporta: p. ej. notificaciones que bajaban 170 px de golpe)
        elif energia[i] > 2.0 and energia[i] > 4 * max(energia[i - 1], energia[i + 1]):
            tir_t.append(round((i + 1) / fps, 2))
    # arranque brusco: de casi quieto a movimiento fuerte en UN frame y SOSTENIDO
    # (no vuelve a bajar: no es un salto) = algo arranca a velocidad plena, sin
    # ease-in. La animación con oficio acelera (fluidez.md, animacion.md).
    arr_t = []
    for i in range(1, len(energia) - 2):
        if (energia[i] > 1.5 and energia[i - 1] < 0.25 * energia[i]
                and min(energia[i + 1], energia[i + 2]) > 0.6 * energia[i]):
            arr_t.append(round((i + 1) / fps, 2))
    jerk = float(np.mean(np.abs(np.diff(energia, 2)))) / max(1e-6, float(np.mean(energia))) \
        if len(energia) > 2 else 0.0
    # tiempo muerto en el hold (desde 0.5 s hasta la salida), ventana de auto_qa
    import auto_qa as QA
    muestras, paso, t_m, hold = _muestreo(F, fps, dur)
    dm = np.abs(np.diff(muestras, axis=0)).mean(axis=(1, 2))
    # tiempo muerto = quietud SOSTENIDA (≥ 0.5 s seguidos bajo el umbral de auto_qa):
    # el punto de giro de una flotación (velocidad 0 un instante) es easing, no un cuadro congelado
    bajo = (dm < QA.FROZEN_DIFF) & hold
    muertas = np.zeros_like(bajo)
    racha = max(2, int(round(0.5 * QA.FPS_MUESTREO)))
    for a_, b_ in _rachas(bajo):
        if b_ - a_ >= racha:
            muertas[a_:b_] = True
    muerto = float(muertas[hold].mean()) if hold.any() else 0.0
    # congelado SIN grano y ocupación de la zona segura, en la misma ventana activa
    quieto = quietud(F, fps, dur)
    ocup = ocupacion(muestras[1:][hold], caja) if hold.any() else ocupacion(muestras, caja)
    # densidad: eventos = ARRANQUES de movimiento en una zona del cuadro. Una
    # celda de la grilla que empieza a moverse (> CELDA_MOV niveles/frame) tras
    # ≥ 0.3 s quieta es algo NUEVO que pasa; arranques a < 0.35 s son el mismo
    # evento. Solo la parte activa: la salida común no es un evento. (Contar
    # picos de energía global fallaba: barras escalonadas se funden en una sola
    # loma y la salida sumaba un evento falso en cada escena.)
    G = 8
    ch, cw = max(1, alto_a // G), max(1, ancho_a // G)
    celdas = d[:, :ch * G, :cw * G].reshape(len(d), G, ch, G, cw).mean(axis=(2, 4))
    k = max(1, int(0.1 * fps))
    celdas = np.apply_along_axis(lambda v: np.convolve(v, np.ones(k) / k, mode="same"), 0, celdas)
    mov = celdas > CELDA_MOV
    calma = max(1, int(0.3 * fps))
    fin = max(1, int((dur - 0.6) * fps))
    arr_celda = sorted(i for i in range(1, min(len(mov), fin))
                       for gy, gx in zip(*np.nonzero(mov[i] & ~mov[max(0, i - calma):i].any(axis=0))))
    eventos = []
    for i in arr_celda:
        if not eventos or (i - eventos[-1]) / fps > 0.35:
            eventos.append(i)
    densidad = len(eventos) / max(0.5, dur - 0.6)
    return {"pops": pops, "tirones": len(tir_t), "t_tirones": tir_t, "arranques": arr_t,
            "jerk": round(jerk, 3),
            "muerto": round(muerto, 3), "densidad": round(densidad, 2), **quieto, "ocupacion": ocup}


def solapes(R, ctx, escenas, dur, fracs=(0.55, 0.8)):
    """Textos visibles que se pisan con cada escena ASENTADA (a 55 % y 80 % de
    su duración). Caja de TINTA real (la tipográfica de “ abarca aire), alfa
    > 60, solape > 20 % del menor. Las métricas de movimiento no ven
    composición: el 00 bajo «¡EN VIVO!» o un total sobre su rótulo sacaban
    99/100. Devuelve ["escena@t: «a»/«b»", ...]."""
    from PIL import Image, ImageDraw
    original = ImageDraw.ImageDraw.text
    cajas = []

    def espia(self, xy, text, fill=None, font=None, *a, **k):
        al = fill[3] if isinstance(fill, tuple) and len(fill) == 4 else 255
        if font is not None and str(text).strip() and al > 60 and self.im.size == (R.W, R.H):
            x0, y0, x1, y1 = (int(v) for v in self.textbbox(xy, text, font=font, anchor=k.get("anchor")))
            m = Image.new("L", (max(1, x1 - x0 + 4), max(1, y1 - y0 + 4)))
            ImageDraw.Draw(m).text((xy[0] - x0 + 2, xy[1] - y0 + 2), text, font=font, fill=255,
                                   anchor=k.get("anchor"))
            b = m.getbbox()
            if b:
                cajas.append(((x0 - 2 + b[0], y0 - 2 + b[1], x0 - 2 + b[2], y0 - 2 + b[3]), str(text)))
        return original(self, xy, text, fill, font, *a, **k)
    hallados = []
    ImageDraw.ImageDraw.text = espia
    try:
        for s_ in escenas:
            for fr in fracs:
                t = s_["from"] + (s_["to"] - s_["from"]) * fr
                R.componer(ctx, escenas, dur, t, set())   # calienta escala_segura (dibuja otros instantes)
                cajas.clear()
                R.componer(ctx, escenas, dur, t, set())
                for i, ((a0, b0, a1, b1), ta) in enumerate(cajas):
                    for (c0, d0, c1, d1), tb in cajas[i + 1:]:
                        iw, ih = min(a1, c1) - max(a0, c0), min(b1, d1) - max(b0, d0)
                        menor = max(1, min((a1 - a0) * (b1 - b0), (c1 - c0) * (d1 - d0)))
                        if iw > 0 and ih > 0 and iw * ih > 0.2 * menor:
                            par = f"{s_.get('tipo')}@{t:.1f}s: «{ta[:14]}»/«{tb[:14]}»"
                            if par not in hallados:
                                hallados.append(par)
    finally:
        ImageDraw.ImageDraw.text = original
    return hallados


def frames_de_video(ruta, fps=None):
    """Frames de un video ya renderizado, en gris a la escala de análisis
    (lado corto = LADO), a SU fps (remuestrear 24 → 30 duplica un frame de
    cada 4 y la métrica lo leería como tirones). Para medir captions, films,
    pases, audiogramas o una entrega final con la misma vara que las escenas.
    Devuelve (frames, duración, fps)."""
    import subprocess
    from _comun import probe
    meta = probe(ruta)
    v = meta["video"]
    fps = fps or round(meta.get("fps") or v.get("fps") or 30)
    w, h = v["width"], v["height"]
    k_ = LADO / min(w, h)
    aw, ah = int(w * k_) // 2 * 2, int(h * k_) // 2 * 2
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", ruta, "-vf",
                          f"fps={fps},scale={aw}:{ah},format=gray", "-f", "rawvideo", "-"],
                         capture_output=True).stdout
    F = np.frombuffer(raw, np.uint8).reshape(-1, ah, aw).astype(np.float32)
    return F, len(F) / fps, fps


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
    abruptos = [(by, bx) for by in range(int(h * k_) // BLOQUE) for bx in range(int(w * k_) // BLOQUE)
                if d[by * BLOQUE:(by + 1) * BLOQUE, bx * BLOQUE:(bx + 1) * BLOQUE].mean() > POP_SALTO]
    for by, bx in _sin_origen(pa, pb, abruptos):
        x0, y0 = (w + 20) + bx * BLOQUE / k_, by * BLOQUE / k_
        dr.rectangle([x0, y0, x0 + BLOQUE / k_, y0 + BLOQUE / k_], outline=(255, 40, 40), width=4)
    lienzo.thumbnail((1600, 1600))
    lienzo.save(salida)
    print("diagnóstico:", salida)


def _desplazar(nodo, d, es_tiempo=False):
    """Corre d segundos los tiempos de una muestra para encadenarla: solo lo que
    vive bajo una clave `at` (un dict de `at`, una lista de tiempos o un `at`
    escalar); x, y, zoom, valores… no se tocan."""
    if isinstance(nodo, dict):
        return {k: _desplazar(v, d, es_tiempo or k == "at") for k, v in nodo.items()}
    if isinstance(nodo, list):
        return [_desplazar(v, d, es_tiempo) for v in nodo]
    if es_tiempo and isinstance(nodo, (int, float)) and not isinstance(nodo, bool):
        return nodo + d
    return nodo


def nota(m):
    """Una sola fórmula, explícita: 100 menos penalizaciones."""
    p = 0.0
    p += 12 * min(3, len(m["pops"]))                       # cada pop: algo aparece de golpe
    p += 4 * min(5, m["tirones"])                          # movimiento entrecortado
    p += 2 * min(5, len(m.get("arranques", [])))           # arranca sin ease-in (mecánico)
    # hold congelado: `muerto` (diff de cuadro entero) y `quieto` (sin grano)
    # miden el mismo defecto; se cobra una vez, el mayor: en un MP4 con grano
    # `muerto` queda ciego y `quieto` lo ve
    p += 25 * max(m["muerto"], m.get("quieto", 0.0))
    ocup = m.get("ocupacion")
    if ocup is not None and ocup < OCUPACION_MIN:         # banda chica en un lienzo enorme
        p += 20 * (OCUPACION_MIN - ocup) / OCUPACION_MIN
    p += 10 * min(3, len(m.get("solapes", [])))           # un texto pisa a otro (composición)
    dens = m["densidad"]
    if m.get("quieta"):                                    # quieta por diseño (lower third)
        pass
    elif dens < 0.5:                                       # menos de un evento cada 2 s: aburre
        p += 20 * (0.5 - dens) / 0.5
    elif dens > 2.0:                                       # más de 2 eventos/s: abruma
        p += min(10, 8 * (dens - 2.0))
    if m["letra_min"] and m["letra_min"] < LETRA_MIN:      # letra que no se lee en un teléfono
        p += min(15, (LETRA_MIN - m["letra_min"]) * 1.5)
    if m["zona"] < 0.999:                                  # la red de seguridad tuvo que encoger
        p += 30 * (1 - m["zona"])
    return round(max(0.0, 100 - p), 1)


def _escenas_del_plan(ruta_plan):
    """[(indice, tipo, from, to)] del plan, para ubicar un defecto en su escena."""
    if not ruta_plan:
        return []
    try:
        with open(ruta_plan, encoding="utf-8") as f:
            plan = json.load(f)
    except (OSError, ValueError):
        return []
    out = []
    for i, e in enumerate(plan.get("escenas") or []):
        if not isinstance(e, dict):
            continue
        try:
            out.append((i + 1, str(e.get("tipo", "?")), float(e.get("from", 0)), float(e.get("to", 0))))
        except (TypeError, ValueError):
            continue
    return out


def _escena_en(t, escenas):
    """A que escena pertenece el instante t (numero de escena y tipo).

    Si el defecto cae justo sobre un corte, lo que importa es el CORTE, no
    la escena: se reporta "corte 1->2".
    """
    for j in range(len(escenas) - 1):
        if abs(t - escenas[j][3]) < 0.05:
            i1, t1 = escenas[j][0], escenas[j][1]
            i2, t2 = escenas[j + 1][0], escenas[j + 1][1]
            return f"corte {i1}:{t1}->{i2}:{t2}"
    for i, tipo, f0, f1 in escenas:
        if f0 - 1e-6 <= t <= f1 + 1e-6:
            return f"{i}:{tipo}"
    return "?"


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
    ap.add_argument("--plan", help="medir un plan.json entero (secuencia, cortes, transiciones) antes de renderizar; "
                                   "junto a --video, ubica cada defecto en su escena")
    ap.add_argument("--video", nargs="+", help="medir videos YA renderizados (captions, films, pases, entregas)")
    ap.add_argument("--cortes", action="store_true", help="medir el corte entre cada par consecutivo del catálogo")
    import os as _os, sys as _sys
    _sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "ffmpeg_tools"))
    from _comun import ayudar
    ayudar(ap, {'--formato': 'v (9:16), h (16:9) o ambos', '--fps': 'cuadros por segundo del análisis (30 = el del render)'})
    a = ap.parse_args()
    if a.historial and (a.solo or a.formato != "ambos" or a.plan or a.video):
        sys.exit("ERROR: --historial solo registra corridas del catálogo completo (o --cortes) en los dos "
                 "formatos: una corrida parcial falsea la nota global de la historia")
    muestras = json.load(open(os.path.join(AQUI, "escenas_muestra.json"), encoding="utf-8"))["escenas"]
    solo = set(a.solo.split(",")) if a.solo else None
    fmts = ["v", "h"] if a.formato == "ambos" else [a.formato]
    # fotos y capturas sintéticas: las mismas de la galería (una sola fuente)
    import tempfile
    import galeria
    import render_plan as R
    from _comun import NEUTRO, asegurar_padre
    medios = tempfile.mkdtemp(prefix="editoria_medir_")
    try:
        galeria.assets(medios, NEUTRO["acento"])
        for e in muestras.values():
            R.resolver_medios(e, medios)
        if a.video:   # misma vara para cualquier video (sin letra ni zona: no hay plan que leer)
            res = []
            escenas = _escenas_del_plan(a.plan) if a.plan else []
            for ruta in a.video:
                F, dur, fps_v = frames_de_video(ruta)
                r = dict({"escena": os.path.basename(ruta), "formato": f"{fps_v}fps"}, **metricas(F, fps_v, dur),
                         letra_min=0, zona=1.0, costo=0.0)
                r["nota"] = nota(r)
                extra = ""
                if escenas:
                    # EL CRITICO: un defecto sin escena es un defecto sin dueño.
                    # "pop en 12.4 s" -> "pop en 12.4 s, escena 3 (bento)"
                    r["pops_escena"] = [f"{_escena_en(t, escenas)}@{t}s" for t in r["pops"]]
                    r["tirones_escena"] = [f"{_escena_en(t, escenas)}@{t}s" for t in r["t_tirones"]]
                    r["ocupacion_escena"] = ocupacion_por_escena(F, fps_v, escenas)
                    extra = (f" pops_escena={r['pops_escena'][:6]}"
                             f" tirones_escena={r['tirones_escena'][:6]}")
                res.append(r)
                print(f"{r['nota']:5.1f}  {r['escena']}  pops={r['pops'][:6]} tirones={r['t_tirones'][:6]} "
                      f"muerto={r['muerto']} quieto={r['quieto']} (racha {r['quieto_max']} s) "
                      f"ocupacion={r['ocupacion']} densidad={r['densidad']}{extra}")
            if a.json:
                asegurar_padre(a.json)
                json.dump(res, open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            return 0
        if a.ver:
            n_, f_, t_ = a.ver.split(":")
            ver(dict(muestras[n_], tipo=n_), f_, float(t_), a.fps,
                os.path.join(dir_temp(), f"pop_{n_}_{f_}_{t_}.png"))
            return 0
        if a.cortes:   # cada par consecutivo del catálogo: la ventana alrededor del corte
            tipos = list(muestras)
            jobs = []
            for f in fmts:
                for x, y in zip(tipos, tipos[1:]):
                    e1 = dict(muestras[x], tipo=x)
                    d_ = e1["to"]
                    e2 = dict(_desplazar(muestras[y], d_), tipo=y, **{"from": d_, "to": d_ + muestras[y]["to"]})
                    jobs.append((f"{x}→{y}", f, [e1, e2], e2["to"], a.fps, (d_ - 1.0, d_ + 1.5)))
        elif a.plan:
            plan = json.load(open(a.plan, encoding="utf-8"))
            R.resolver_medios(plan, os.path.dirname(os.path.abspath(a.plan)))
            nombre = os.path.splitext(os.path.basename(a.plan))[0]
            fmts_plan = fmts if a.formato != "ambos" else (
                ["h"] if str(plan.get("tamano", "")).startswith("1920") else ["v"])
            _init()
            globales = {k: plan[k] for k in ("numeros", "subtitulos") if k in plan}
            _W["R"].aplicar_globales(globales)
            for f in fmts_plan:   # misma puerta que render_plan: tiempos por defecto y error claro
                plan["escenas"] = R.preparar_escenas(_ctx(f), plan)
            jobs = [(nombre, f, plan["escenas"], plan["duracion"], a.fps, None, globales) for f in fmts_plan]
        else:
            jobs = [(n, f, [dict(e, tipo=n)], e["to"], a.fps) for f in fmts for n, e in muestras.items()
                    if not solo or n in solo]
        # progreso visible: componer minutos de frames sin una sola linea
        # parece un cuelgue y mata corridas sanas por timeout. Se anuncia
        # cada trabajo al lanzarlo y al cerrarlo (imap_unordered + contador).
        print(f"midiendo {len(jobs)} trabajo(s) "
              f"({', '.join(sorted({j[1] for j in jobs}))})…", flush=True)
        res = []
        with Pool(a.jobs, initializer=_init) as pool:
            for r in pool.imap_unordered(medir, jobs, chunksize=1):
                res.append(r)
                print(f"  medido {len(res)}/{len(jobs)}: {r['escena']} ({r['formato']})",
                      flush=True)
        for r in res:
            if a.cortes:   # en una ventana de 2.5 s la densidad no dice nada: se juzgan pops, saltos y quietud
                r["densidad"] = 1.0
            r["nota"] = nota(r)
        res.sort(key=lambda r: r["nota"])
        print(f"{'escena':18s} f  nota  pops tir  jerk  muerto quieto ocup dens letra zona  s/frame")
        for r in res:
            print(f"{r['escena']:18s} {r['formato']}  {r['nota']:5.1f} {len(r['pops']):4d} {r['tirones']:3d} "
                  f"{r['jerk']:5.2f} {r['muerto']:6.2f} {r['quieto_max']:5.2f}s {r['ocupacion']:4.2f} "
                  f"{r['densidad']:4.2f} {r['letra_min']:5d} {r['zona']:5.2f} {r['costo']:6.3f}")
        for r in res:
            for x in r.get("solapes", []):
                print(f"  SOLAPE {r['formato']} {x}")
            for d in (r.get("ocupacion_escena") or []):
                if d["ocupacion"] < OCUPACION_MIN:
                    print(f"  OCUPACION {r['formato']} escena {d['escena']}: {d['ocupacion']:.2f} de la zona "
                          f"segura (< {OCUPACION_MIN}) — banda chica en un lienzo grande")
            for d in (r.get("letra_por_escena") or []):
                if d["letra_px"] < LETRA_MIN:
                    print(f"  LETRA {r['formato']} escena {d['escena']}: «{d['texto']}» "
                          f"{d['letra_px']} px (< {LETRA_MIN}) — acorta ese texto o alarga su escena")
        global_ = round(float(np.mean([r["nota"] for r in res])), 2)
        minima = min(res, key=lambda r: r["nota"])
        if a.plan and plan.get("musica"):   # edición al ritmo: tiempos reales del plan vs la rejilla
            import beat_grid
            import beat_sync
            s_ = beat_sync.medir_sincronia(plan["escenas"], beat_grid.analizar(plan["musica"]), plan["duracion"], a.fps)
            print(f"SINCRONÍA con la música ({s_['bpm']} BPM): entradas en medio beat {s_['entradas_pct']} % "
                  f"de {s_['entradas']} (azar ≈ {s_['azar_pct']} %) · cortes en el uno del compás "
                  f"{s_['cortes_compas_pct']} % de {s_['cortes']}")
        print(f"\nNOTA GLOBAL {global_} · mínima {minima['nota']} ({minima['escena']} {minima['formato']}) · "
              f"pops {sum(len(r['pops']) for r in res)} · tirones {sum(r['tirones'] for r in res)}")
        if a.json:
            asegurar_padre(a.json)
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
    finally:
        shutil.rmtree(medios, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
