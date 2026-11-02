#!/usr/bin/env python3
"""auto_qa.py — ojos máquina de EditorIA: barrido automático de defectos en un
video renderizado, antes de la revisión visual del agente.

Detecta sin visión (métricas sobre frames decodificados):
  - black_frame: luminancia ~0 sostenida (frame negro no intencional)
  - frozen: imagen idéntica >1s (viola "fondo vivo"; ver checklist-qa.md)
  - flash: salto brusco de luminancia entre muestras (glitch/pop)
  - silencio largo / clipping en el audio (si lo hay)
  - fotosensible: >3 destellos en 1 s (WCAG 2.3.1), medido a fps completo
  - sobresalto: el audio salta >6 dB al entrar un corte (asusta, no edita)
  - loop (--loop): el último frame no empalma con el primero

Salida: JSON con defectos (t0, t1, detalle) + contact sheet PNG con los
momentos marcados, listo para que el agente los mire y confirme.

Uso:
  python scripts/auto_qa.py video.mp4 [--sheet salida.png] [--json reporte.json]
  python scripts/auto_qa.py video.mp4 --ignorar-inicio 0.5  # fade-in intencional

Exit: 0 = limpio, 1 = defectos, 2 = error.
Ver references/auto-qa.md (el loop cerrado de corrección).
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg_tools"))
from _comun import asegurar_padre, die, info, probe

FPS_MUESTREO = 4          # muestras por segundo para el análisis
ANCHO = 320               # ancho de análisis (rápido)
BLACK_LUMA = 5.0          # luminancia media bajo la cual es "negro"
BLACK_MIN_DUR = 0.25      # segundos sostenidos para reportar
FROZEN_DIFF = 0.35        # diff media bajo la cual dos cuadros son "idénticos"
FROZEN_MAX = 1.0          # segundos congelados permitidos (ver checklist-qa.md)
FLASH_JUMP = 50.0         # salto de luminancia entre muestras = posible glitch
SILENCIO_DB = -45         # umbral de silencio
SILENCIO_MIN = 1.5        # segundos de silencio para reportar
# Fotosensibilidad (WCAG 2.3.1, "tres destellos"): un destello es un par de
# cambios opuestos de luminancia relativa >=10% con el lado oscuro <0.80;
# mas de 3 en cualquier segundo es un defecto (en pantalla completa o en un
# cuadrante = 25% del cuadro). Se mide a fps COMPLETO: a 4 fps no se ve.
FLASH_DELTA = 0.10
FLASH_OSCURO = 0.80
FLASH_MAX_SEG = 3
# Sobresalto: salto de sonoridad al entrar en un corte vs el segundo previo.
# Medido con usuarios: +7..+10 dB asusta; +3..+5 con cambio armonico = limpio.
SOBRESALTO_DB = 6.0
CORTE_DIFF = 28.0         # diff media (0-255, a 64px) que cuenta como corte
LOOP_DIFF = 6.0           # frame 0 vs ultimo: por encima, el loop se nota


def muestras_video(video):
    """Decodifica a gris 320px @ FPS_MUESTREO; devuelve lista de (t, luma_media, frame)."""
    import numpy as np
    cmd = ["ffmpeg", "-v", "error", "-i", video,
           "-vf", f"scale={ANCHO}:-1,fps={FPS_MUESTREO}",
           "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        die(f"ffmpeg no pudo leer {video}")
    raw = r.stdout
    meta = probe(video)
    h = max(1, round(meta["video"]["height"] * ANCHO / meta["video"]["width"]))
    frame_bytes = ANCHO * h
    nframes = len(raw) // frame_bytes
    arr = np.frombuffer(raw[:nframes * frame_bytes], dtype=np.uint8).reshape(nframes, h, ANCHO)
    return [(i / FPS_MUESTREO, float(arr[i].mean()), arr[i]) for i in range(nframes)]


def detectar(muestras, dur, ignorar_inicio=0.0, ignorar_fin=0.0):
    defectos = []
    diffs = []
    for i in range(1, len(muestras)):
        import numpy as np
        d = float(np.abs(muestras[i][2].astype(int) - muestras[i - 1][2].astype(int)).mean())
        diffs.append(d)
        salto_luma = abs(muestras[i][1] - muestras[i - 1][1])
        t = muestras[i][0]
        if salto_luma > FLASH_JUMP and ignorar_inicio < t < dur - ignorar_fin:
            defectos.append({"tipo": "flash", "t0": round(t, 2), "t1": round(t, 2),
                             "detalle": f"salto de luminancia {salto_luma:.0f} en una muestra"})

    # rachas de negro y de congelado
    def rachas(cond):
        out, ini = [], None
        for i, (t, luma, _) in enumerate(muestras):
            d = diffs[i - 1] if i > 0 else 999
            if cond(t, luma, d):
                if ini is None:
                    ini = t
            else:
                if ini is not None:
                    out.append((ini, muestras[i - 1][0] + 1 / FPS_MUESTREO))
                    ini = None
        if ini is not None:
            out.append((ini, muestras[-1][0] + 1 / FPS_MUESTREO))
        return out

    for t0, t1 in rachas(lambda t, luma, d: luma < BLACK_LUMA):
        if t1 - t0 >= BLACK_MIN_DUR and t0 >= ignorar_inicio and t1 <= dur - ignorar_fin:
            defectos.append({"tipo": "black_frame", "t0": round(t0, 2), "t1": round(t1, 2),
                             "detalle": f"luminancia ~0 durante {t1 - t0:.2f}s"})
    for t0, t1 in rachas(lambda t, luma, d: d < FROZEN_DIFF):
        if t1 - t0 > FROZEN_MAX:
            defectos.append({"tipo": "frozen", "t0": round(t0, 2), "t1": round(t1, 2),
                             "detalle": f"imagen idéntica durante {t1 - t0:.2f}s (máx {FROZEN_MAX}s)"})
    return sorted(defectos, key=lambda x: x["t0"])


def frames_finos(video):
    """Todos los frames a 64x36 en gris (uint8: 1 h de video = ~250 MB, no 1 GB)."""
    import numpy as np
    meta = probe(video)
    fps = meta["video"].get("fps") or 30.0
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vf", "scale=64:36",
                        "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True)
    arr = np.frombuffer(r.stdout, dtype=np.uint8)
    return fps, arr[: len(arr) // 2304 * 2304].reshape(-1, 36, 64)


def _por_bloques(fr, fn, bloque=4096):
    """Aplica fn a bloques de frames y concatena: memoria acotada en videos largos."""
    import numpy as np
    return np.concatenate([fn(fr[i:i + bloque]) for i in range(0, len(fr), bloque)])


def destellos(fr, fps):
    """Ventanas de 1 s con mas de FLASH_MAX_SEG destellos (pantalla o cuadrante)."""
    import numpy as np
    fr = np.asarray(fr)
    if fr.dtype != np.uint8:
        fr = np.clip(fr, 0, 255).astype(np.uint8)
    g = np.arange(256, dtype=np.float32) / 255     # luminancia relativa (sRGB lineal)
    lut = np.where(g <= 0.04045, g / 12.92, ((g + 0.055) / 1.055) ** 2.4).astype(np.float32)
    cuadrantes = [_por_bloques(fr[:, a:a + 18, b:b + 32], lambda q: lut[q].mean(axis=(1, 2)))
                  for a in (0, 18) for b in (0, 32)]
    regiones = [sum(cuadrantes) / 4] + cuadrantes   # pantalla completa = media de los 4
    malos = []
    for serie in regiones:
        trans, ext, sube = [], serie[0], None   # transiciones entre extremos
        for i in range(1, len(serie)):
            v = serie[i]
            if sube is not None and ((sube and v > ext) or (not sube and v < ext)):
                ext = v                     # sigue en la misma direccion: el extremo avanza
            elif abs(v - ext) >= FLASH_DELTA and min(v, ext) < FLASH_OSCURO:
                trans.append(i / fps)
                sube, ext = v > ext, v
        for k in range(len(trans)):
            j = k
            while j < len(trans) and trans[j] - trans[k] < 1.0:
                j += 1
            if (j - k) / 2 > FLASH_MAX_SEG:
                malos.append((trans[k], trans[j - 1], (j - k) / 2))
    return malos


def cortes(fr, fps):
    import numpy as np
    d = _por_bloques(np.arange(1, len(fr)), lambda ix: np.abs(
        fr[ix].astype(np.int16) - fr[ix - 1].astype(np.int16)).mean(axis=(1, 2)))
    return [(i + 1) / fps for i in np.nonzero(d > CORTE_DIFF)[0]]


def sobresaltos(video, tiempos, dur):
    """Cortes donde el audio salta mas de SOBRESALTO_DB sobre el segundo previo."""
    import numpy as np
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vn", "-ac", "1", "-ar", "8000",
                        "-f", "s16le", "-"], capture_output=True)
    x = np.frombuffer(r.stdout, dtype=np.int16).astype(np.float32) / 32768
    if len(x) < 8000:
        return []
    def db(a, b):
        seg = x[int(a * 8000):int(b * 8000)]
        return 20 * np.log10(np.sqrt((seg ** 2).mean()) + 1e-9) if len(seg) else -120
    out = []
    for t in tiempos:
        if t < 1.0 or t > dur - 1.0:      # sin "antes" que comparar / fade final
            continue
        antes, despues = db(t - 1.0, t - 0.05), db(t, t + 0.3)
        if despues > -40 and despues - antes > SOBRESALTO_DB:
            out.append((t, despues - antes))
    return out


def analisis_fino(video, dur, loop=False, con_audio=True):
    defectos = []
    fps, fr = frames_finos(video)
    if len(fr) < 2:
        return defectos
    tramos = []   # ventanas solapadas (y de varias regiones) = un solo tramo
    for t0, t1, n in sorted(destellos(fr, fps)):
        if tramos and t0 <= tramos[-1][1] + 0.05:
            tramos[-1] = [tramos[-1][0], max(tramos[-1][1], t1), max(tramos[-1][2], n)]
        else:
            tramos.append([t0, t1, n])
    for t0, t1, n in tramos:
        defectos.append({"tipo": "fotosensible", "t0": round(t0, 2), "t1": round(t1, 2),
                         "detalle": f"hasta {n:.0f} destellos por segundo (máx {FLASH_MAX_SEG}, "
                                    "WCAG 2.3.1): espaciar a ≥1/3 s o bajar el contraste"})
    if con_audio:
        for t, salto in sobresaltos(video, cortes(fr, fps), dur):
            defectos.append({"tipo": "sobresalto", "t0": round(t, 2), "t1": round(t, 2),
                             "detalle": f"+{salto:.1f} dB al entrar el corte (máx +{SOBRESALTO_DB:.0f})"})
    if loop:
        dif = float(abs(fr[0].astype(float) - fr[-1].astype(float)).mean())
        if dif > LOOP_DIFF:
            defectos.append({"tipo": "loop", "t0": 0.0, "t1": round(dur, 2),
                             "detalle": f"último frame ≠ primero (diff {dif:.1f}): la costura se nota"})
    return defectos


def analizar_audio(video, dur):
    defectos = []
    # silencios largos
    cmd = ["ffmpeg", "-v", "info", "-i", video,
           "-af", f"silencedetect=noise={SILENCIO_DB}dB:d={SILENCIO_MIN}",
           "-f", "null", "-"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    for m in re.finditer(r"silence_start: ([\d.]+)", r.stderr):
        t0 = float(m.group(1))
        m2 = re.search(rf"silence_start: {re.escape(m.group(1))}.*?silence_end: ([\d.]+)",
                       r.stderr, re.S)
        t1 = float(m2.group(1)) if m2 else dur
        # ignorar fade-out final
        if t1 < dur - 0.3:
            defectos.append({"tipo": "silencio", "t0": round(t0, 2), "t1": round(t1, 2),
                             "detalle": f"silencio ≥{SILENCIO_MIN}s"})
    # clipping: pico real
    cmd = ["ffmpeg", "-v", "error", "-i", video, "-af", "astats=metadata=0",
           "-f", "null", "-"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    m = re.search(r"Peak level dB:\s*(-?[\d.]+)", r.stderr)
    if m and float(m.group(1)) > -1.0:
        defectos.append({"tipo": "clipping", "t0": 0, "t1": round(dur, 2),
                         "detalle": f"pico {m.group(1)} dB (posible clipping)"})
    return defectos


def contact_sheet(video, defectos, dur, salida, n_muestras=12, safe=None,
                  video_w=None, video_h=None, end_screen=None):
    """Sheet PIL: muestras uniformes + un tile por defecto (borde rojo).

    Con safe="<plataforma>", dibuja la zona segura en cada tile (amarillo)
    para verificar de un vistazo que captions y texto no caen bajo la UI.
    """
    from PIL import Image, ImageDraw
    safe_px = None
    if safe:
        from _delivery import safe_margins_px
        safe_px = safe_margins_px(safe, video_w, video_h)
    tmpd = tempfile.mkdtemp(prefix="qa_")
    try:
        tiempos = sorted(set(
            [round(dur * (i + 0.5) / n_muestras, 2) for i in range(n_muestras)] +
            [d["t0"] for d in defectos] +
            ([round(dur - end_screen / 2, 2), round(dur - 0.5, 2)] if end_screen else [])
        ))
        zonas_es = None
        if end_screen and video_w and video_h:
            from _delivery import end_screen_px
            zonas_es = end_screen_px(video_w, video_h)
        tiles = []
        for t in tiempos:
            fp = os.path.join(tmpd, f"f_{t:.2f}.png")
            subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", video,
                            "-vf", "scale=270:-2", "-frames:v", "1", fp],
                           capture_output=True)
            if os.path.exists(fp):
                tiles.append((t, Image.open(fp).convert("RGB")))
        if not tiles:
            die("no se pudo extraer ningún frame")
        tw, th = tiles[0][1].size
        cols = 4
        rows = (len(tiles) + cols - 1) / cols
        rows = int(rows + 0.999)
        sheet = Image.new("RGB", (cols * tw, rows * (th + 22)), (20, 20, 20))
        dr = ImageDraw.Draw(sheet)
        defect_ts = {d["t0"] for d in defectos}
        # rectangulo de zona segura escalado al tamano del tile
        safe_rect = None
        if safe_px and video_w and video_h:
            sx, sy = tw / video_w, th / video_h
            safe_rect = (int(safe_px["left"] * sx), int(safe_px["top"] * sy),
                         int(tw - safe_px["right"] * sx) - 1,
                         int(th - safe_px["bottom"] * sy) - 1)
        for i, (t, im) in enumerate(tiles):
            x, y = (i % cols) * tw, (i // cols) * (th + 22)
            es_defecto = any(abs(t - dt) < 0.3 for dt in defect_ts)
            color = (220, 60, 50) if es_defecto else (90, 90, 90)
            dr.rectangle([x, y, x + tw - 1, y + th + 21], outline=color, width=3 if es_defecto else 1)
            sheet.paste(im, (x, y))
            if safe_rect:
                dr.rectangle([safe_rect[0] + x, safe_rect[1] + y,
                              safe_rect[2] + x, safe_rect[3] + y],
                             outline=(255, 200, 0), width=2)
            if zonas_es and t >= dur - end_screen:   # elementos de YouTube: deben caer en zona quieta
                sx, sy = tw / video_w, th / video_h
                for nombre, (zx, zy, zw, zh) in zonas_es.items():
                    col = (80, 200, 255) if nombre != "marca" else (120, 255, 120)
                    dr.rectangle([x + zx * sx, y + zy * sy, x + (zx + zw) * sx, y + (zy + zh) * sy],
                                 outline=col, width=2)
            dr.text((x + 6, y + th + 4), f"{t:.2f}s", fill=(255, 255, 255))
        sheet.save(salida)
    finally:
        shutil.rmtree(tmpd, ignore_errors=True)
    return salida


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video", help="video renderizado a auditar")
    ap.add_argument("--sheet", help="PNG del contact sheet (default: <video>_qa.png)")
    ap.add_argument("--json", help="guardar reporte JSON en archivo")
    ap.add_argument("--ignorar-inicio", type=float, default=0.0,
                    help="segundos iniciales a ignorar (fade-in intencional)")
    ap.add_argument("--ignorar-fin", type=float, default=0.0,
                    help="segundos finales a ignorar (fade-out intencional)")
    ap.add_argument("--end-screen", type=float, metavar="SEG",
                    help="dibuja las zonas de la pantalla final de YouTube en los últimos SEG s")
    ap.add_argument("--loop", action="store_true",
                    help="la pieza es un loop: el último frame debe empalmar con el primero")
    ap.add_argument("--safe", metavar="PLATAFORMA",
                    help="dibuja la zona segura de la plataforma en cada tile "
                         "(reels, tiktok, shorts, youtube, x, linkedin, facebook)")
    a = ap.parse_args()

    if not os.path.isfile(a.video):
        die(f"no existe {a.video}")
    meta = probe(a.video)
    if not meta.get("video"):
        die("el input no tiene stream de video")
    dur = meta.get("duration") or 0

    info(f"analizando {a.video} ({dur:.1f}s)…")
    muestras = muestras_video(a.video)
    defectos = detectar(muestras, dur, a.ignorar_inicio, a.ignorar_fin)
    if meta.get("audio"):
        defectos += analizar_audio(a.video, dur)
    defectos += analisis_fino(a.video, dur, loop=a.loop, con_audio=bool(meta.get("audio")))
    defectos = sorted(defectos, key=lambda x: x["t0"])

    sheet = a.sheet or os.path.splitext(a.video)[0] + "_qa.png"
    asegurar_padre(sheet)
    vw = meta["video"].get("width") or 0
    vh = meta["video"].get("height") or 0
    contact_sheet(a.video, defectos, dur, sheet, safe=a.safe,
                  video_w=vw, video_h=vh, end_screen=a.end_screen)

    reporte = {"video": a.video, "duracion": round(dur, 2),
               "defectos": defectos,
               "resumen": {"total": len(defectos),
                           "por_tipo": {t: sum(1 for d in defectos if d["tipo"] == t)
                                        for t in set(d["tipo"] for d in defectos)}}}
    if a.json:
        asegurar_padre(a.json)
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(reporte, f, ensure_ascii=False, indent=1)
        info(f"reporte: {a.json}")
    print(json.dumps(reporte, ensure_ascii=False, indent=1))
    info(f"sheet: {sheet} — MIRARLO antes de entregar (ver references/auto-qa.md)")
    if defectos:
        print(f"\n{len(defectos)} DEFECTO(S) — corregir y re-verificar", file=sys.stderr)
        return 1
    print("\nLIMPIO — sin defectos máquina; sigue la revisión visual", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
