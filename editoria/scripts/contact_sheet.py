#!/usr/bin/env python3
"""Mosaico de revision: un corte entero, o un pasaje de una referencia, de un
vistazo (metodo l3d1c / coleccion Opus 5.5).

Toma una carpeta de stills PNG o extrae frames de un video y los mosaica en
contact sheets etiquetados con tiempo (y nombre/numero). Dos usos:

1. Revisar el CORTE antes de pagar el render completo (stills de
   Remotion/HyperFrames, o N frames de un borrador). Los cambios se piden en
   lenguaje natural sobre el sheet.
2. Leer una REFERENCIA (references/referencia-video.md): con --palabras cada
   tile lleva debajo las palabras dichas en su intervalo, asi se lee que
   cambia en el cuadro EN que palabra. El rango, el muestreo y el tamaño se
   ajustan a la pregunta: el pasaje entero para el argumento; un tramo corto
   con --cada 0.1 o --todos-los-frames para una entrada, un cambio o un
   relevo. Las palabras van DEBAJO del cuadro: los subtitulos y graficas
   originales quedan a la vista. (Grilla con transcript, idea de Hypit,
   hypit-ai/hypit; implementacion propia.)

Uso:
  python3 scripts/contact_sheet.py --dir stills/ -o sheet.png
  python3 scripts/contact_sheet.py --video corte.mp4 -n 20 -o sheet.png
  python3 scripts/contact_sheet.py --video ref.mp4 --inicio 0 --fin 12 --cada 1 \\
      --palabras ref.palabras.json -o evidencia/apertura.png
  python3 scripts/contact_sheet.py --video ref.mp4 --alrededor "cuatro cosas" \\
      --palabras ref.palabras.json --cada 0.1 --cols 4 --ancho 480 -o evidencia/lista.png
  python3 scripts/contact_sheet.py --video ref.mp4 --inicio 6.8 --fin 8.4 \\
      --todos-los-frames --cols 4 --filas 3 -o evidencia/movimiento.png
      # pagina: movimiento_01.png, movimiento_02.png...

El palabras.json sale de scripts/alinear.py (sin guion = transcripcion con
tiempos por palabra) o de Whisper/WhisperX. Diferencia con auto_qa.py: ese
hace QA de un render terminado; esto es para mirar y razonar.
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile
import unicodedata

try:
    from PIL import Image, ImageDraw, ImageFont
except ModuleNotFoundError as _e_dep:
    if "-h" not in sys.argv and "--help" not in sys.argv:
        sys.exit(f"ERROR: falta dependencia ({_e_dep.name}): pip install pillow")
    Image = ImageDraw = ImageFont = None

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg_tools"))
from _comun import die, leer_palabras, parse_time, probe, require_tool  # noqa: E402
from _plataforma import FUENTES_SKILL  # noqa: E402

MAX_FRAMES = 600   # una grilla de miles de tiles no se lee: acotar el rango


def duracion(video):
    meta = probe(video)
    if not meta.get("video"):
        die(f"{video}: no tiene stream de video", kind="input")
    return float(meta.get("duration") or 0.0)


def extraer_frames(video, tiempos, tmpdir):
    """Un frame por tiempo (seek preciso). Devuelve [(ruta, t)]."""
    ffmpeg = require_tool("ffmpeg")
    out = []
    for i, t in enumerate(tiempos):
        ruta = os.path.join(tmpdir, f"frame_{i:04d}.png")
        subprocess.run([ffmpeg, "-y", "-v", "error", "-nostdin", "-ss", f"{t:.3f}", "-i", video,
                        "-frames:v", "1", ruta], check=True)
        if os.path.exists(ruta):          # mas alla del ultimo frame, ffmpeg no escribe nada
            out.append((ruta, t))
    return out


def extraer_todos(video, inicio, fin, tmpdir):
    """Cada frame original de [inicio, fin] en una sola decodificacion, con su
    timestamp REAL de la fuente (sirve tambien para video de fps variable)."""
    ffmpeg = require_tool("ffmpeg")
    r = subprocess.run([ffmpeg, "-hide_banner", "-nostdin", "-ss", f"{max(0.0, inicio - 2):.3f}", "-copyts",
                        "-i", video, "-vf", f"select='between(t,{inicio:.4f},{fin:.4f})',showinfo",
                        "-fps_mode", "passthrough", os.path.join(tmpdir, "todo_%05d.png")],
                       capture_output=True, text=True)
    tiempos = [float(x) for x in re.findall(r"pts_time:\s*([0-9.]+)", r.stderr)]
    rutas = sorted(f for f in os.listdir(tmpdir) if f.startswith("todo_"))
    if r.returncode != 0 or not rutas:
        die(f"no pude extraer frames de {video} en [{inicio}, {fin}]: "
            f"{(r.stderr.strip().splitlines() or ['?'])[-1][:200]}", kind="ffmpeg")
    return [(os.path.join(tmpdir, f), t) for f, t in zip(rutas, tiempos)]


def _norm(w):
    w = unicodedata.normalize("NFD", w.lower())
    return re.sub(r"[^\w']", "", "".join(c for c in w if unicodedata.category(c) != "Mn"))


def buscar_frase(palabras, frase, ocurrencia=1):
    """(inicio, fin) de la N-esima aparicion de la frase en el transcript,
    sin importar mayusculas, tildes ni puntuacion."""
    objetivo = [_norm(w) for w in frase.split() if _norm(w)]
    toks = [_norm(p["texto"]) for p in palabras]
    halladas = [i for i in range(len(toks) - len(objetivo) + 1)
                if objetivo and toks[i:i + len(objetivo)] == objetivo]
    if len(halladas) < ocurrencia:
        die(f"'{frase}' aparece {len(halladas)} vez/veces en el transcript "
            f"(pediste la ocurrencia {ocurrencia})", kind="input")
    i = halladas[ocurrencia - 1]
    return palabras[i]["inicio"], palabras[i + len(objetivo) - 1]["fin"]


def palabras_en(palabras, a, b):
    """Texto dicho en [a, b): toda palabra que se solapa con el intervalo."""
    return " ".join(p["texto"] for p in palabras if p["inicio"] < b and p["fin"] > a)


def _fuente(px):
    for f in ("Montserrat-Bold.ttf", "Montserrat-wght.ttf"):
        if (FUENTES_SKILL / f).exists():
            return ImageFont.truetype(str(FUENTES_SKILL / f), px)
    return ImageFont.load_default()


def _envolver(texto, font, ancho, max_lineas=2):
    lineas, actual = [], ""
    for w in texto.split():
        prueba = f"{actual} {w}".strip()
        if font.getlength(prueba) <= ancho or not actual:
            actual = prueba
        else:
            lineas.append(actual)
            actual = w
    if actual:
        lineas.append(actual)
    if len(lineas) > max_lineas:
        lineas = lineas[:max_lineas]
        while lineas[-1] and font.getlength(lineas[-1] + "…") > ancho:
            lineas[-1] = lineas[-1][:-1]
        lineas[-1] += "…"
    return lineas


def mosaico(tiles, cols, ancho_tile, salida, con_palabras=False):
    """tiles: [(ruta, etiqueta, texto_dicho)]. Mosaica en cols columnas."""
    thumbs = []
    for ruta, etiqueta, dicho in tiles:
        im = Image.open(ruta).convert("RGB")
        alto = round(im.height * ancho_tile / im.width)
        thumbs.append((im.resize((ancho_tile, alto), Image.LANCZOS), etiqueta, dicho))

    px = max(12, ancho_tile // 22)
    font, font_p = _fuente(px), _fuente(max(12, round(px * 1.1)))
    lh = round(px * 1.35)
    barra = lh + 12 + (2 * round(px * 1.5) if con_palabras else 0)
    alto_tile = max(t.size[1] for t, _, _ in thumbs)
    pad = 6
    filas = (len(thumbs) + cols - 1) // cols
    W = cols * (ancho_tile + pad) + pad
    H = filas * (alto_tile + barra + pad) + pad
    sheet = Image.new("RGB", (W, H), (18, 18, 18))
    d = ImageDraw.Draw(sheet)

    for i, (th, etiqueta, dicho) in enumerate(thumbs):
        r, c = divmod(i, cols)
        x = pad + c * (ancho_tile + pad)
        y = pad + r * (alto_tile + barra + pad)
        sheet.paste(th, (x, y + (alto_tile - th.size[1])))
        yb = y + alto_tile
        d.rectangle([x, yb, x + ancho_tile, yb + barra], fill=(40, 40, 40))
        d.text((x + 6, yb + 6), etiqueta, fill=(220, 220, 220), font=font)
        num = f"#{i + 1}"
        d.text((x + ancho_tile - 6 - font.getlength(num), yb + 6), num, fill=(150, 150, 150), font=font)
        if con_palabras and dicho:
            for k, ln in enumerate(_envolver(dicho, font_p, ancho_tile - 12)):
                d.text((x + 6, yb + 6 + lh + k * round(px * 1.5)), ln, fill=(255, 214, 102), font=font_p)

    sheet.save(salida)
    print(f"OK {salida}: {len(thumbs)} tiles en {cols}x{filas} "
          f"({sheet.size[0]}x{sheet.size[1]})")


def tiempos_pedidos(a, inicio, fin):
    """Instantes a muestrear segun -n / --cada / --en, dentro de [inicio, fin)."""
    if a.en:
        return [parse_time(t.strip()) for t in a.en.split(",") if t.strip()]
    if a.cada:
        if a.cada <= 0:
            die("--cada debe ser > 0", kind="input")
        n = int((fin - inicio) / a.cada + 1e-6)
        return [round(inicio + k * a.cada, 4) for k in range(max(1, n))]
    # i/n (no i/(n-1)): nunca pide t=fin exacto, que ffmpeg no sirve
    return [inicio + (fin - inicio) * i / a.n for i in range(a.n)]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--dir", help="carpeta con stills PNG")
    src.add_argument("--video", help="video del que extraer frames")
    sel = ap.add_argument_group("que frames (con --video)")
    sel.add_argument("-n", type=int, default=20,
                     help="frames equidistantes en el rango (default 20)")
    sel.add_argument("--cada", type=float, help="un frame cada S segundos (en vez de -n)")
    sel.add_argument("--en", help="instantes exactos separados por coma: 6.9,7.3,0:07.8")
    sel.add_argument("--todos-los-frames", action="store_true",
                     help="cada frame original del rango (movimiento fino; acota el rango)")
    sel.add_argument("--inicio", default="0", help="inicio del rango (s o mm:ss; default 0)")
    sel.add_argument("--fin", help="fin del rango (default: el final del video)")
    sel.add_argument("--alrededor", metavar="FRASE",
                     help="el rango es donde se dice esta frase (requiere --palabras)")
    sel.add_argument("--margen", type=float, default=1.0,
                     help="segundos antes y despues de la frase de --alrededor (default 1.0)")
    sel.add_argument("--ocurrencia", type=int, default=1,
                     help="que aparicion de la frase de --alrededor usar (default 1)")
    ap.add_argument("--palabras", help="palabras.json del MISMO video (alinear.py / Whisper): "
                                       "pone bajo cada tile lo dicho en su intervalo")
    ap.add_argument("--cols", type=int, default=4, help="columnas (default 4)")
    ap.add_argument("--filas", type=int, help="filas por hoja: pagina en salida_01.png, salida_02.png...")
    ap.add_argument("--ancho", type=int, default=320,
                    help="ancho de cada tile en px (default 320; 480+ para leer tipografia)")
    ap.add_argument("-o", "--salida", required=True, help="PNG de salida")
    a = ap.parse_args()

    palabras = leer_palabras(a.palabras) if a.palabras else None
    if a.alrededor and not palabras:
        die("--alrededor necesita --palabras (el transcript con tiempos por palabra)", kind="input")
    if a.cols < 1 or (a.filas is not None and a.filas < 1) or a.n < 1:
        die("--cols, --filas y -n deben ser >= 1", kind="input")

    with tempfile.TemporaryDirectory() as tmp:
        if a.dir:
            if not os.path.isdir(a.dir):
                die(f"no existe la carpeta: {a.dir}", kind="input")
            pngs = sorted(f for f in os.listdir(a.dir) if f.lower().endswith(".png"))
            if not pngs:
                die(f"sin PNG en {a.dir}", kind="input")
            tiles = [(os.path.join(a.dir, f), f, "") for f in pngs]
        else:
            if not os.path.isfile(a.video):
                die(f"no existe el video: {a.video}", kind="input")
            dur = duracion(a.video)
            inicio, fin = parse_time(a.inicio), parse_time(a.fin) if a.fin else dur
            if a.alrededor:
                f0, f1 = buscar_frase(palabras, a.alrededor, a.ocurrencia)
                inicio, fin = max(0.0, f0 - a.margen), min(dur, f1 + a.margen)
            if not 0 <= inicio < fin:
                die(f"rango vacio o invertido: [{inicio}, {fin}]", kind="input")
            if a.todos_los_frames:
                frames = extraer_todos(a.video, inicio, fin, tmp)
            else:
                tiempos = tiempos_pedidos(a, inicio, fin)
                if len(tiempos) > MAX_FRAMES:
                    die(f"{len(tiempos)} frames: acota el rango o sube --cada (max {MAX_FRAMES})", kind="input")
                frames = extraer_frames(a.video, tiempos, tmp)
            if len(frames) > MAX_FRAMES:
                die(f"{len(frames)} frames: acota el rango (max {MAX_FRAMES})", kind="input")
            if not frames:
                die(f"sin frames en [{inicio:.2f}, {fin:.2f}] de {a.video}", kind="input")
            ts = [t for _, t in frames]
            # cada tile representa lo que pasa hasta el siguiente instante
            ends = ts[1:] + [min(fin, ts[-1] + (ts[-1] - ts[-2] if len(ts) > 1 else fin - ts[-1]))]
            tiles = [(ruta, f"t={t:.2f}s", palabras_en(palabras, t, e) if palabras else "")
                     for (ruta, t), e in zip(frames, ends)]

        por_hoja = a.cols * a.filas if a.filas else len(tiles)
        hojas = [tiles[k:k + por_hoja] for k in range(0, len(tiles), por_hoja)]
        base, ext = os.path.splitext(a.salida)
        os.makedirs(os.path.dirname(os.path.abspath(a.salida)), exist_ok=True)
        for k, hoja in enumerate(hojas, 1):
            salida = a.salida if len(hojas) == 1 else f"{base}_{k:02d}{ext or '.png'}"
            mosaico(hoja, a.cols, a.ancho, salida, con_palabras=bool(palabras))


if __name__ == "__main__":
    main()
