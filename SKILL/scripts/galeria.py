#!/usr/bin/env python3
"""galeria.py — el ciclo crear → validar de TODO lo que anima la skill.

Renderiza cada escena del catálogo (muestras de scripts/escenas_muestra.json,
la misma fuente que el smoke test) y cada herramienta animada (overlay con
alfa, transición mancha, plantilla × tabla, 16:9, captions, pase, audiograma,
films de marca, thumbnail), pasa auto_qa a cada video, arma un resumen visual
y deja un reporte PASS/FAIL. Lo que la skill promete queda probado en la
práctica, no solo compilado.

Modo libre por defecto (paleta neutra); con --brand, la misma galería en la
identidad del pack: así se prueba que la marca entra SOLO cuando se pide.

Uso:
  python scripts/galeria.py -o /tmp/galeria                 # todo, modo libre
  python scripts/galeria.py -o /tmp/galeria_marca --brand brand/mi_marca.json
  python scripts/galeria.py -o /tmp/g --solo stats,quote --sin-herramientas

Después: MIRAR resumen.png y los *_qa.png (auto_qa no ve legibilidad ni
solapes). Exit 0 = todo PASS, 1 = algún FAIL. Ver references/auto-qa.md.
"""
import argparse
import json
import math
import shutil
import os
import subprocess
import sys
import time

from PIL import Image, ImageDraw, ImageFont

AQUI = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(AQUI)
sys.path.insert(0, os.path.join(AQUI, "ffmpeg_tools"))
from _comun import NEUTRO, colores_marca, probe  # noqa: E402
sys.path.insert(0, AQUI)
from render_plan import QUIETAS  # noqa: E402

PY = sys.executable
# una escena aislada entra desde negro y sale fundida a negro (en un plan real
# la siguiente la cubre): esos bordes no son defectos
QA_BORDES = ["--ignorar-inicio", "0.3", "--ignorar-fin", "0.6"]


def correr(cmd, log):
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True)
    with open(log, "a", encoding="utf-8") as f:
        f.write("$ " + " ".join(cmd) + "\n" + r.stdout + r.stderr + "\n")
    return r.returncode, r.stdout + r.stderr, time.time() - t0


def qa(video, log, extra=(), quieta=False):
    """auto_qa del video → (ok, defectos, sheet). `quieta`: la pieza se queda
    quieta POR DISEÑO mientras se lee (render_plan.QUIETAS): su hold no es un
    defecto `frozen`."""
    sheet = os.path.splitext(video)[0] + "_qa.png"
    rep = os.path.splitext(video)[0] + "_qa.json"
    correr([PY, os.path.join(AQUI, "auto_qa.py"), video, "--sheet", sheet, "--json", rep,
            *extra], log)
    if not os.path.isfile(rep):
        return False, [{"tipo": "error", "detalle": "auto_qa no produjo reporte"}], None
    defectos = json.load(open(rep, encoding="utf-8"))["defectos"]
    if quieta:
        defectos = [d for d in defectos if d["tipo"] != "frozen"]
    return not defectos, defectos, sheet


def video_ok(path, dur_min=0.5):
    if not os.path.isfile(path):   # probe() muere ante un archivo ausente: no aquí
        return False
    try:
        m = probe(path)
        return bool(m.get("video")) and (m.get("duration") or 0) >= dur_min
    except (Exception, SystemExit):
        return False


# ---------- assets sintéticos (sin binarios en el repo) ----------
def assets(dst, acento):
    """Foto de paisaje y dos capturas de una app: suficiente textura para que
    Ken Burns, zoom y recortes se vean de verdad."""
    os.makedirs(dst, exist_ok=True)
    foto = Image.new("RGB", (1800, 1400))
    d = ImageDraw.Draw(foto)
    for y in range(1400):   # cielo de atardecer
        k = y / 1400
        d.line([(0, y), (1800, y)], fill=(int(40 + 180 * k), int(60 + 70 * k), int(120 - 40 * k)))
    d.ellipse([1150, 380, 1450, 680], fill=(255, 214, 150))
    import random as _r
    rnd = _r.Random(7)
    for _ in range(140):   # estrellas: una foto real tiene detalle fino, no solo degradés
        x, y = rnd.randrange(1800), rnd.randrange(700)
        b_ = rnd.randint(150, 255)
        d.ellipse([x, y, x + 3, y + 3], fill=(b_, b_, b_))
    for i, (amp, base, col) in enumerate(((90, 900, (60, 70, 90)), (70, 1050, (35, 45, 60)),
                                           (50, 1200, (20, 25, 35)))):
        pts = [(x, base + amp * math.sin(x / (180 + 60 * i) + i)) for x in range(0, 1801, 20)]
        d.polygon(pts + [(1800, 1400), (0, 1400)], fill=col)
        for _ in range(40):   # árboles en cada loma
            x = rnd.randrange(1800)
            y = base + amp * math.sin(x / (180 + 60 * i) + i)
            h_ = rnd.randint(30, 90)
            d.polygon([(x, y - h_), (x - h_ * 0.3, y + 4), (x + h_ * 0.3, y + 4)],
                      fill=tuple(max(0, c - 18) for c in col))
    # grano de película (textura real, determinista)
    import numpy as _np
    arr = _np.asarray(foto, _np.int16) + _np.random.default_rng(7).integers(-9, 10, (1400, 1800, 1))
    foto = Image.fromarray(_np.clip(arr, 0, 255).astype(_np.uint8))
    foto.save(os.path.join(dst, "foto_muestra.png"))

    def captura(nombre, filas, resaltada):
        im = Image.new("RGB", (1600, 1000), (246, 247, 249))
        c = ImageDraw.Draw(im)
        c.rectangle([0, 0, 300, 1000], fill=(30, 33, 40))
        for i in range(6):
            c.rounded_rectangle([30, 120 + i * 70, 270, 160 + i * 70], 10,
                                fill=acento if i == 0 else (55, 60, 70))
        c.rounded_rectangle([1240, 60, 1540, 130], 16, fill=acento)
        for i in range(filas):
            y = 200 + i * 120
            c.rounded_rectangle([360, y, 1540, y + 96], 14,
                                fill=(255, 236, 225) if i == resaltada else (255, 255, 255),
                                outline=(225, 228, 232), width=2)
            c.rectangle([390, y + 30, 390 + 300 + 80 * (i % 3), y + 50], fill=(70, 75, 85))
            c.rectangle([390, y + 62, 590, y + 74], fill=(170, 175, 185))
        im.save(os.path.join(dst, nombre))
    captura("captura_muestra.png", 4, -1)
    captura("captura_muestra_2.png", 6, 0)
    logo = Image.new("RGBA", (600, 400), (0, 0, 0, 0))   # logo NO cuadrado (prueba el pad)
    ImageDraw.Draw(logo).polygon([(300, 20), (560, 380), (40, 380)], fill=acento + (255,))
    ImageDraw.Draw(logo).ellipse([240, 200, 360, 320], fill=(250, 248, 246, 255))
    logo.save(os.path.join(dst, "logo_muestra.png"))


# ---------- escenas ----------
def plan_de(escenas, dur, **extra):
    return dict({"duracion": dur, "escenas": escenas}, **extra)


def render(plan, nombre, carpeta, log, brand=None, ext=".mp4", extra=()):
    ruta_plan = os.path.join(carpeta, nombre + ".plan.json")
    json.dump(plan, open(ruta_plan, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    out = os.path.join(carpeta, nombre + ext)
    cmd = [PY, os.path.join(AQUI, "render_plan.py"), ruta_plan, "-o", out, "--force", *extra]
    if brand:
        cmd += ["--brand", brand]
    rc, txt, seg = correr(cmd, log)
    shutil.rmtree(out + ".frames", ignore_errors=True)   # ~50 MB por escena
    return out, rc, txt, seg


FORMATOS = {"v": "1080x1920", "h": "1920x1080"}   # todo se prueba en 9:16 Y 16:9


def escenas(a, out, log, filas, muestras):
    tipos = [t for t in muestras if not a.solo or t in a.solo]
    for f in a.formatos:
        for tipo in tipos:
            e = dict(muestras[tipo], tipo=tipo)
            nombre = f"{tipo}_{f}"
            v, rc, txt, seg = render(plan_de([e], e["to"]), nombre, out, log, a.brand,
                                     extra=["--tamano", FORMATOS[f]])
            if rc or not video_ok(v):
                filas.append(("escena", nombre, False, f"render rc={rc}: {txt.strip()[-200:]}",
                              None, None, seg))
                print(f"  FAIL escena {nombre}: rc={rc}", flush=True)
                continue
            ok, defectos, sheet = qa(v, log, QA_BORDES, quieta=tipo in QUIETAS)
            det = "; ".join(f"{d['tipo']} {d.get('t0', '')}-{d.get('t1', '')}s" for d in defectos)
            escala = [ln.split("escalada ")[-1] for ln in txt.splitlines() if "zona segura: escena" in ln]
            if escala:   # la red de seguridad actuó: dato para mirar, no un fallo
                det = (det + "; " if det else "") + f"encogida {escala[0]}"
            filas.append(("escena", nombre, ok, det or "limpio", v, sheet, seg))
            print(f"  {'PASS' if ok else 'FAIL'} escena {nombre:18s} {seg:5.1f}s {det}", flush=True)


# ---------- herramientas ----------
def herramientas(a, out, log, filas, muestras):
    def anota(nombre, ok, det, archivo=None, seg=0.0, sheet=None):
        filas.append(("herramienta", nombre, ok, det, archivo, sheet, seg))
        print(f"  {'PASS' if ok else 'FAIL'} {nombre:30s} {seg:5.1f}s {det}", flush=True)

    def con_qa(nombre, video, rc, txt, seg, extra=QA_BORDES):
        if rc or not video_ok(video):
            return anota(nombre, False, f"rc={rc}: {txt.strip()[-200:]}", None, seg)
        ok, defectos, sheet = qa(video, log, extra)
        anota(nombre, ok, "; ".join(f"{d['tipo']} {d.get('t0', '')}-{d.get('t1', '')}s"
                                    for d in defectos) or "limpio", video, seg, sheet)

    m = lambda t: dict(muestras[t], tipo=t)   # noqa: E731
    marca = ["--brand", a.brand] if a.brand else []
    # audio sintético con dinámica de voz (audiograma / ondas)
    audio = os.path.join(out, "voz_sintetica.wav")
    correr(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
            "aevalsrc=0.5*sin(2*PI*180*t)*(0.55+0.45*sin(2*PI*3*t))*(0.6+0.4*sin(2*PI*0.4*t)):s=44100:d=6",
            audio], log)
    cues = os.path.join(out, "cues.txt")
    open(cues, "w", encoding="utf-8").write("0:00.4-0:02.2 Un lugar para volver\n"
                                            "0:02.3-0:04.4 cada temporada\n")
    palabras = os.path.join(out, "voz.palabras.json")
    pal = [("Un", .4, .6), ("lugar", .6, 1.0), ("para", 1.0, 1.2), ("volver", 1.2, 1.9),
           ("cada", 2.4, 2.8), ("temporada", 2.8, 3.8)]
    json.dump({"palabras": [{"texto": t, "inicio": i, "fin": f, "confianza": 1.0} for t, i, f in pal]},
              open(palabras, "w", encoding="utf-8"))
    fotos = os.path.join(out, "fotos")
    os.makedirs(fotos, exist_ok=True)
    src = Image.open(os.path.join(out, "foto_muestra.png"))
    for i, caja in enumerate(((0, 0, 1200, 1400), (300, 100, 1800, 1100), (500, 300, 1300, 1400))):
        src.crop(caja).save(os.path.join(fotos, f"{i + 1:02d}.png"))

    for f in a.formatos:
        tam = ["--tamano", FORMATOS[f]]
        # overlay con alfa (lower third para NLE/OBS): el alfa sobrevive al códec
        for ext in (".webm", ".mov"):
            v, rc, txt, seg = render(plan_de([m("rotulo_inferior")], 5), f"overlay_alfa_{f}", out, log,
                                     a.brand, ext, extra=tam)
            ok = rc == 0 and "alfa verificado" in txt and "AVISO overlay" not in txt
            anota(f"overlay alfa {ext} {f}", ok, "alfa verificado" if ok else txt.strip()[-200:], v, seg)
        # transición mancha entre dos escenas
        e1, e2 = m("stats"), m("quote")
        e2 = dict(e2, transicion="mancha", **{"from": 5, "to": 11},
                  at={k: v + 5 for k, v in e2["at"].items()})
        v, rc, txt, seg = render(plan_de([e1, e2], 11), f"transicion_mancha_{f}", out, log, a.brand,
                                 extra=tam)
        con_qa(f"transición mancha {f}", v, rc, txt, seg)
        # captions animados sobre una toma limpia (sin texto quemado que pisar)
        base = os.path.join(out, f"base_captions_{f}.mp4")
        if not video_ok(base):
            render(plan_de([dict(m("kenburns"), titulo="", subtitulo="")], 5), f"base_captions_{f}",
                   out, log, a.brand, extra=tam)
        for modo, args in (("fade", ["--text", cues, "--animate", "fade"]),
                           ("pop", ["--text", cues, "--animate", "pop"]),
                           ("slide", ["--text", cues, "--animate", "slide"]),
                           ("karaoke", ["--palabras", palabras, "--animate", "pop", "--karaoke"])):
            v = os.path.join(out, f"caption_{modo}_{f}.mp4")
            rc, txt, seg = correr([PY, os.path.join(AQUI, "ffmpeg_tools", "caption.py"), base,
                                   *args, *marca, "-o", v], log)
            con_qa(f"caption {modo} {f}", v, rc, txt, seg)
        # pase de fotos (slideshow con Ken Burns distinto por foto)
        v = os.path.join(out, f"pase_{f}.mp4")
        rc, txt, seg = correr([PY, os.path.join(AQUI, "ffmpeg_tools", "montaje.py"), "pase", fotos,
                               "--duracion", "3", "--transicion", "0.5", *tam, "-o", v], log)
        con_qa(f"pase de fotos {f}", v, rc, txt, seg, extra=[])
        for modo, extra in (("audiograma", ["--titulo", "Episodio 12", "--subtitulo", "Cómo empezar",
                                            "--portada", os.path.join(out, "foto_muestra.png")]),
                            ("waves", [])):
            v = os.path.join(out, f"audio_{modo}_{f}.mp4")
            rc, txt, seg = correr([PY, os.path.join(AQUI, "audio_viz.py"), audio, "-o", v,
                                   "--modo", modo, "-s", FORMATOS[f], *extra, *marca], log)
            con_qa(f"audio_viz {modo} {f}", v, rc, txt, seg, extra=[])
        # thumbnail (imagen: basta que exista con el tamaño del formato)
        formato, dims = {"v": ("9:16", (1080, 1920)), "h": ("16:9", (1280, 720))}[f]
        v = os.path.join(out, f"thumbnail_{f}.png")
        rc, txt, seg = correr([PY, os.path.join(AQUI, "ffmpeg_tools", "thumbnail.py"),
                               os.path.join(out, "foto_muestra.png"), "--texto", "UN LUGAR ÚNICO",
                               "--resaltar", "ÚNICO", "--formato", formato, *marca, "-o", v], log)
        ok = rc == 0 and os.path.isfile(v) and Image.open(v).size == dims
        anota(f"thumbnail {formato}", ok, "ok" if ok else txt.strip()[-200:], v, seg)

    # plantilla × tabla: la fila 2 sale con SUS datos (lógica, no formato)
    tabla = os.path.join(out, "ponentes.csv")
    open(tabla, "w", encoding="utf-8").write("nombre,rol\nAna Gómez,Diseño\nLuis Peña,Ingeniería\n")
    v, rc, txt, seg = render(plan_de([dict(m("rotulo_inferior"), nombre="{nombre}", rol="{rol}")], 5),
                             "plantilla", out, log, a.brand, extra=["--datos", tabla, "--fila", "2"])
    plan_fila = v + ".plan.json"
    ok = rc == 0 and os.path.isfile(plan_fila) and \
        "Luis Peña" in open(plan_fila, encoding="utf-8").read()
    anota("plantilla × tabla (--datos)", ok, "fila 2 sustituida" if ok else txt.strip()[-200:], v, seg)
    # films de marca (9:16 y 16:9): con --brand el logo del pack; sin pack, un logo dado
    ident = ["--brand", a.brand] if a.brand else \
        ["--logo", os.path.join(out, "logo_muestra.png"), "--nombre", "Tu Marca",
         "--lema", "Edita menos, *crea más*"]
    for f in a.formatos:
        for film in ("film_marca_v2", "film_marca"):
            v = os.path.join(out, f"{film}_{f}.mp4")
            rc, txt, seg = correr([PY, os.path.join(AQUI, f"{film}.py"), "-o", v, *ident,
                                   "--formato", {"v": "9:16", "h": "16:9"}[f]], log)
            shutil.rmtree(v + ".frames", ignore_errors=True)
            con_qa(f"{film} {f}", v, rc, txt, seg, extra=["--ignorar-inicio", "0.5", "--ignorar-fin", "0.8"])


# ---------- resumen visual ----------
def frame_en(video, t, ancho):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", video, "-frames:v", "1",
                          "-vf", f"scale={ancho}:-2,format=rgb24", "-f", "image2pipe",
                          "-vcodec", "png", "-"], capture_output=True).stdout
    if not raw:
        return None
    import io
    return Image.open(io.BytesIO(raw)).convert("RGB")


def resumen(filas, out):
    """Una fila por pieza: 4 momentos (25/50/75/95 %) + estado. Para MIRAR."""
    videos = [f for f in filas if f[4] and os.path.isfile(f[4])]
    vistos = lambda v: v.endswith(".mp4")   # noqa: E731  (alfa y PNG se miran aparte)
    tw = 180
    fuente = ImageFont.load_default()
    alto_fila = 340
    img = Image.new("RGB", (220 + 4 * (tw + 8), max(1, len(videos)) * alto_fila), (18, 18, 18))
    d = ImageDraw.Draw(img)
    for i, (_, nombre, ok, det, video, _, _) in enumerate(videos):
        y = i * alto_fila
        d.text((10, y + 10), nombre, fill=(255, 255, 255), font=fuente)
        d.text((10, y + 30), "PASS" if ok else "FAIL", fill=(90, 220, 120) if ok else (255, 80, 80),
               font=fuente)
        if not vistos(video):
            continue
        dur = (probe(video).get("duration") or 1)
        for j, k in enumerate((0.25, 0.5, 0.75, 0.95)):
            fr = frame_en(video, dur * k, tw)
            if fr:
                fr.thumbnail((tw, alto_fila - 20))
                img.paste(fr, (220 + j * (tw + 8), y + 10))
    ruta = os.path.join(out, "resumen.png")
    img.save(ruta)
    return ruta


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--out", required=True, help="carpeta de la galería")
    ap.add_argument("--brand", help="brand pack: la misma galería en esa identidad")
    ap.add_argument("--solo", help="escenas separadas por coma (default: todas)")
    ap.add_argument("--formato", choices=["v", "h", "ambos"], default="ambos",
                    help="v = 9:16, h = 16:9 (default: ambos)")
    ap.add_argument("--sin-herramientas", action="store_true", help="solo escenas")
    ap.add_argument("--sin-escenas", action="store_true", help="solo herramientas")
    a = ap.parse_args()
    a.solo = set(a.solo.split(",")) if a.solo else None
    a.formatos = ["v", "h"] if a.formato == "ambos" else [a.formato]
    if a.brand:
        a.brand = os.path.abspath(a.brand)
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    log = os.path.join(out, "galeria.log")
    open(log, "w").close()
    acento = colores_marca(a.brand)["acento"] if a.brand else NEUTRO["acento"]
    assets(out, acento)
    filas = []
    print(f"galería en {out} ({'pack ' + os.path.basename(a.brand) if a.brand else 'modo libre'})",
          flush=True)
    muestras = json.load(open(os.path.join(AQUI, "escenas_muestra.json"),
                              encoding="utf-8"))["escenas"]
    if not a.sin_escenas:
        escenas(a, out, log, filas, muestras)
    if not a.sin_herramientas:
        herramientas(a, out, log, filas, muestras)
    hoja = resumen(filas, out)
    rep = [{"tipo": t, "nombre": n, "ok": ok, "detalle": det, "archivo": v, "sheet": s,
            "segundos": round(seg, 1)} for t, n, ok, det, v, s, seg in filas]
    json.dump(rep, open(os.path.join(out, "galeria.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    fallos = [r for r in rep if not r["ok"]]
    print(f"\n{len(rep) - len(fallos)}/{len(rep)} PASS · resumen: {hoja} · log: {log}")
    for r in fallos:
        print(f"FAIL {r['tipo']} {r['nombre']}: {r['detalle']}")
    print("MIRAR resumen.png y los *_qa.png antes de dar algo por bueno.")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
