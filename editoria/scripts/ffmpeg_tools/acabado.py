#!/usr/bin/env python3
"""acabado.py — acabados de ESTILO para video con ffmpeg (sin dependencias).

Cada operación es una técnica con parámetros concretos de un lenguaje de
motion graphics (references/estilos.md, biblioteca de lenguajes): se aplica
sobre cualquier video (un render del motor, una grabación, una toma).

  escalonado  poses sostenidas «a unos / a doses / a treses» (stop-motion,
              collage, cel): baja el ritmo de movimiento sin cambiar el fps.
  pixelar     pixel art: baja a una resolución interna, limita la paleta,
              tramado ordenado y vuelve a escalar por vecino más cercano.
  vhs         cinta: separación RGB, líneas de barrido, ruido y blando.
  crt         tubo: barril, líneas de barrido, resplandor y viñeta.
  resplandor  doble glow: uno cerrado (~4 px) y uno amplio (~30 px) sobre las
              luces (neón, HUD, synthwave).
  aberracion  aberración cromática: rojo y azul desplazados en sentido opuesto.

Los radios están pensados a 1080 px de lado corto y se escalan solos al
tamaño real. Con --dry-run se imprime el comando sin ejecutar. El audio se
copia sin tocarlo. Para el grano, el papel y el parpadeo de proyector:
artesanal.py.

Ejemplos:
  python3 acabado.py escalonado video.mp4 --cada 2 -o hecho_a_mano.mp4
  python3 acabado.py pixelar video.mp4 --ancho 160 --colores 32 -o pixel.mp4
  python3 acabado.py vhs video.mp4 --intensidad 1.2 -o cinta.mp4
  python3 acabado.py resplandor video.mp4 --fuerza 0.7 -o neon.mp4
  python3 acabado.py crt --dry-run video.mp4
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _comun import (add_common, apply_common, cfr_args, default_output, die, emit,  # noqa: E402
                    ffmpeg_base, info, probe, run, verify_output, video_args)

BASE_LADO = 1080.0      # los radios y desplazamientos de esta guía se piensan a 1080 px de lado corto


def escala(w, h):
    """Factor para llevar un valor pensado a 1080 px de lado corto al tamaño real."""
    return min(w, h) / BASE_LADO


def px(valor, w, h, minimo=1):
    return max(minimo, int(round(valor * escala(w, h))))


# ───────────────────────── constructores de filtro (puros) ─────────────────────────

def filtro_escalonado(fps_src, cada=None, fps_pose=None):
    """Poses sostenidas. `cada` = cuadros que dura cada pose (2 = «a doses»);
    `fps_pose` = poses por segundo. Se vuelve al fps de origen duplicando poses."""
    if (cada is None) == (fps_pose is None):
        die("usa --cada o --fps-pose (uno solo)", kind="input")
    pose = fps_src / cada if cada else fps_pose
    if cada is not None and cada < 2:
        die("--cada debe ser >= 2 (1 es el movimiento normal)", kind="input")
    if not 0 < pose < fps_src:
        die(f"las poses por segundo ({pose:g}) deben ser menores que el fps del video ({fps_src:g})", kind="input")
    return f"fps={pose:.6g}:round=down,fps={fps_src:.6g}"


def filtro_pixelar(w, h, ancho=320, colores=32, tramado="bayer"):
    """Pixel art: resolución interna `ancho`, paleta de `colores`, escalado entero por vecino."""
    if not 2 <= colores <= 256:
        die("--colores debe estar entre 2 y 256", kind="input")
    if not 8 <= ancho < w:
        die(f"--ancho debe estar entre 8 y {w - 1} (el ancho del video es {w})", kind="input")
    ih = max(2, int(round(h * ancho / w)))
    dither = {"bayer": "dither=bayer:bayer_scale=3", "floyd": "dither=floyd_steinberg",
              "ninguno": "dither=none"}[tramado]
    return (f"scale={ancho}:{ih}:flags=area,split[a][b];"
            f"[a]palettegen=max_colors={colores}:stats_mode=diff[p];"
            f"[b][p]paletteuse={dither},scale={w}:{h}:flags=neighbor,format=yuv420p")


def cadena_resplandor(w, h, radio_cerrado=4.0, radio_amplio=30.0, umbral=0.55, fuerza=0.6):
    """Doble glow sobre las luces. Devuelve la lista de filtros (el segundo
    resplandor pesa ~80 % del primero: cerrado = brillo, amplio = atmósfera)."""
    if not 0.0 <= fuerza <= 1.5:
        die("--fuerza debe estar entre 0 y 1.5", kind="input")
    if not 0.0 <= umbral < 1.0:
        die("--umbral debe estar entre 0 y 1 (sin incluir 1)", kind="input")
    e = escala(w, h)
    s1, s2 = max(0.5, radio_cerrado * e / 2), max(1.0, radio_amplio * e / 2)   # sigma = radio / 2
    alto = f"curves=all='0/0 {umbral:g}/0 1/1'"                                   # solo pasan las luces
    return ["split=3[a][b][c]",
            f"[b]{alto},gblur=sigma={s1:.2f}[g1]",
            f"[c]{alto},gblur=sigma={s2:.2f}[g2]",
            f"[a][g1]blend=all_mode=screen:all_opacity={min(1.0, fuerza):.2f}[x]",
            f"[x][g2]blend=all_mode=screen:all_opacity={min(1.0, fuerza * 0.8):.2f}"]


def filtro_resplandor(w, h, **kw):
    return ";".join(cadena_resplandor(w, h, **kw)) + ",format=yuv420p"


def lineas_de_barrido(oscuridad, paso=2):
    """Líneas horizontales cada `paso` px oscureciendo `oscuridad` (0-1)."""
    return f"drawgrid=w=iw:h={paso}:t=1:c=black@{oscuridad:.2f}"


def filtro_aberracion(w, h, desplazamiento=2.0):
    d = px(desplazamiento, w, h)
    return f"rgbashift=rh=-{d}:bh={d},format=yuv420p"


def filtro_vhs(w, h, intensidad=1.0):
    """Cinta: separación RGB 1-2 px, barrido de 2 px al 10 %, ruido y blando."""
    if not 0.0 < intensidad <= 3.0:
        die("--intensidad debe estar entre 0 (sin incluir) y 3", kind="input")
    d = px(2 * intensidad, w, h)
    return ",".join([f"rgbashift=rh=-{d}:bh={d}",
                     f"gblur=sigma={0.7 * intensidad * escala(w, h):.2f}",
                     lineas_de_barrido(min(0.6, 0.10 * intensidad), paso=2),
                     f"noise=alls={int(round(10 * intensidad))}:allf=t+u",
                     "eq=saturation=1.15:contrast=1.05",
                     "format=yuv420p"])


def filtro_crt(w, h, curvatura=0.12, barrido=0.25, **kw):
    """Tubo: barril (k negativo: sin esquinas negras), barrido, resplandor y viñeta."""
    if not 0.0 <= curvatura <= 0.4:
        die("--curvatura debe estar entre 0 y 0.4", kind="input")
    pre = []
    if curvatura:
        pre.append(f"lenscorrection=k1=-{curvatura:g}:k2=-{curvatura:g}")
    pre.append(lineas_de_barrido(barrido, paso=max(2, px(3, w, h))))
    glow = cadena_resplandor(w, h, **kw)
    return ",".join(pre) + "," + ";".join(glow) + ",vignette=PI/4,format=yuv420p"


# ───────────────────────── ejecución común ─────────────────────────

def aplicar(args, construir):
    if not os.path.isfile(args.input):
        die(f"no existe el archivo: {args.input}", kind="input")
    meta = probe(args.input)
    v = meta.get("video")
    if not v:
        die("el input no tiene stream de video", kind="input")
    w, h, fps = v.get("width") or 1080, v.get("height") or 1920, v.get("fps") or 30.0
    vf = construir(w, h, fps)
    salida = args.output or default_output(args.input, args.op)
    cmd = ffmpeg_base() + ["-i", args.input, "-vf", vf, "-map", "0:v:0"]
    cmd += ["-map", "0:a:0", "-c:a", "copy"] if meta.get("audio") else ["-an"]
    cmd += video_args(meta, crf=args.crf) + cfr_args(meta) + [salida]
    run(cmd)
    verify_output(salida)
    info(f"OK {salida} (acabado: {args.op})")
    emit(salida, acabado=args.op)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="op", required=True)

    def comun(p, crf=18):
        add_common(p)
        p.add_argument("input", help="video a tratar")
        p.add_argument("-o", "--output", help="video de salida (default: <input>_<operación>.mp4)")
        p.add_argument("--crf", type=int, default=crf,
                       help=f"calidad x264, menor = mejor y más pesado (default {crf})")

    p = sub.add_parser("escalonado", help="poses sostenidas (stop-motion, collage, cel)")
    comun(p)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--cada", type=int, help="cuadros que dura cada pose: 2 = «a doses», 3 = «a treses»")
    g.add_argument("--fps-pose", type=float, help="poses por segundo (p. ej. 12); menor que el fps del video")

    p = sub.add_parser("pixelar", help="pixel art: resolución interna, paleta limitada y tramado")
    comun(p, crf=14)
    p.add_argument("--ancho", type=int, default=320,
                   help="ancho de la resolución interna en px (default 320; que divida el ancho del video da píxeles iguales)")
    p.add_argument("--colores", type=int, default=32, help="tamaño de la paleta, 2-256 (default 32)")
    p.add_argument("--tramado", choices=["bayer", "floyd", "ninguno"], default="bayer",
                   help="bayer = tramado ordenado (default, el look de 8 bits), floyd = difuso, ninguno = planos")

    p = sub.add_parser("vhs", help="cinta: separación RGB, barrido, ruido y blando")
    comun(p)
    p.add_argument("--intensidad", type=float, default=1.0, help="fuerza del efecto, 0-3 (default 1.0)")

    p = sub.add_parser("crt", help="tubo: barril, barrido, resplandor y viñeta")
    comun(p)
    p.add_argument("--curvatura", type=float, default=0.12, help="abombado de la pantalla, 0-0.4 (default 0.12; 0 = plana)")
    p.add_argument("--barrido", type=float, default=0.25, help="oscuridad de las líneas de barrido, 0-1 (default 0.25)")
    p.add_argument("--fuerza", type=float, default=0.5, help="fuerza del resplandor, 0-1.5 (default 0.5)")

    p = sub.add_parser("resplandor", help="doble glow sobre las luces (neón, HUD, synthwave)")
    comun(p)
    p.add_argument("--radio-cerrado", type=float, default=4.0, help="radio del glow cerrado en px a 1080 (default 4)")
    p.add_argument("--radio-amplio", type=float, default=30.0, help="radio del glow amplio en px a 1080 (default 30)")
    p.add_argument("--umbral", type=float, default=0.55, help="brillo (0-1) desde el que algo brilla (default 0.55)")
    p.add_argument("--fuerza", type=float, default=0.6, help="fuerza del glow, 0-1.5 (default 0.6)")

    p = sub.add_parser("aberracion", help="aberración cromática: rojo y azul en sentido opuesto")
    comun(p)
    p.add_argument("--px", type=float, default=2.0, help="desplazamiento en px a 1080 (default 2; 1-2 es sutil)")

    args = ap.parse_args()
    apply_common(args)

    if args.op == "escalonado":
        aplicar(args, lambda w, h, fps: filtro_escalonado(fps, args.cada, args.fps_pose))
    elif args.op == "pixelar":
        aplicar(args, lambda w, h, fps: filtro_pixelar(w, h, args.ancho, args.colores, args.tramado))
    elif args.op == "vhs":
        aplicar(args, lambda w, h, fps: filtro_vhs(w, h, args.intensidad))
    elif args.op == "crt":
        aplicar(args, lambda w, h, fps: filtro_crt(w, h, args.curvatura, args.barrido, fuerza=args.fuerza))
    elif args.op == "resplandor":
        aplicar(args, lambda w, h, fps: filtro_resplandor(w, h, radio_cerrado=args.radio_cerrado,
                                                           radio_amplio=args.radio_amplio, umbral=args.umbral,
                                                           fuerza=args.fuerza))
    else:
        aplicar(args, lambda w, h, fps: filtro_aberracion(w, h, args.px))


if __name__ == "__main__":
    main()
