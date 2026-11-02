#!/usr/bin/env python3
"""componer.py — mete la tipografia ENCIMA del footage, con profundidad.

QUE RESUELVE
  La tipografia renderizada por `render_plan.py` sale como una capa CON ALFA
  (`.mov` ProRes 4444 o `.webm` VP9): es una capa, no una pieza. Alguien tiene
  que montarla sobre el video y decides como se ve el texto. Hasta ahora esa
  receta vivia en DOS sitios que no se hablaban: la prosa
  (`references/modos-produccion.md`) con el comando ffmpeg escrito a mano, y el
  script del demo (`demo/_build/build_reel.py`) con el MISMO comando copiado.
  Dos copias de la misma idea: una prosa que hay que traducir a mano y un
  script de trabajo que no viaja con la skill.

  Aqui vive UNA vez, y hace las dos cosas que la receta hacia a mano:

  1. el FONDO se desenfoca SOLO detras de la letra (la mascara sale del ALFA
     del overlay, no de un rectangulo): el resto del cuadro queda nitido. Sin
     esto la tipografia flota encima del video y la pieza parece un collage;
  2. el VELO (la capa negra suave) se puede generar aqui, con la misma receta
     que usaba el demo, para que la caja blanca lea sobre cualquier foto.

  Ademas avisa de lo que rompe el resultado:
  · el fondo y la capa TIENEN que ir a la misma tasa (30 vs 24 = tirones, que
    el medidor de movimiento cuenta y la puerta rechaza);
  · la capa tiene que LLEVAR ALFA (un `.mp4` no lo lleva: el texto sale con
    fondo negro en vez de desvanecido).

  Y tiene DOS layouts:
  · A SANGRE (por defecto): el video ocupa el cuadro y la tipografia va encima;
  · ENMARCADO (`--marco x,y,w,h`): el video entra en una CAJA con esquinas
    redondeadas sobre el lienzo negro y la tipografia va ENCIMA de todo. Es el
    layout del reel de "cara": el clip enmarcado arriba y el copy debajo, en
    su propia zona (la zona segura de las plataformas NO llega al borde: el
    texto del reel vive en la franja baja, que es zona de UI de Instagram).

LO QUE NO HACE (y lo dice)
  · NO inventa la tipografia: la capa sale de `render_plan.py`.
  · NO decide el arte: el velo es una herramienta (fuerte arriba y abajo por
    defecto, como el del demo) y se puede apagar con `--velo 0`.
  · NO toca el video de entrada: escribe un fichero nuevo.

Uso:
    python3 scripts/ffmpeg_tools/componer.py base.mp4 capa.mov -o final.mp4
    python3 scripts/ffmpeg_tools/componer.py base.mp4 capa.mov --audio mezcla.mp4 -o final.mp4
    python3 scripts/ffmpeg_tools/componer.py base.mp4 capa.mov --marco "60,250,960,947" -o final.mp4
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _comun import (add_common, apply_common, die, emit, ffmpeg_base, info,
                    probe, run, verify_output, x264_args)

#: La mascara del desenfoque sale del ALFA de la capa. Estos numeros son los
#: de la receta documentada (references/modos-produccion.md): el radio del
#: desenfoque de la mascara, el radio del fondo y el umbral que decide que
#: pixel cuenta como letra.
W=1080
H=1920
RADIO_MASCARA = 45
RADIO_FONDO = 24
UMBRAL = 28


def _fps_de(ruta):
    """(fps, ancho, alto) del fichero, o (None, None, None) si no se puede."""
    meta = probe(ruta) or {}
    v = meta.get("video") or {}
    fps = v.get("fps")
    try:
        fps = float(fps)
    except (TypeError, ValueError):
        fps = None
    return fps, v.get("width"), v.get("height")


def _tiene_alfa(ruta):
    """True si el fichero LLEVA canal alfa (una capa, no un video opaco).

    OJO con el VP9 (.webm): el decoder NATIVO de ffmpeg descarta el alfa, y
    el stream se ve como `yuv420p` aunque el contenedor lo traiga (la
    etiqueta `alpha_mode=1`). MEDIDO: una capa .webm con alfa de verdad
    (88 % transparente al decodificar con libvpx-vp9) salia con "NO lleva
    canal alfa" y el clip de debajo se tapaba con un rectangulo negro. Para
    el .webm hay que mirar la ETIQUETA, igual que hace
    `_comun.verificar_alfa` (que si la mira).
    """
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=pix_fmt:stream_tags=alpha_mode",
             "-of", "default=nw=1", ruta],
            capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    salida = (r.stdout or "").strip().lower()
    if not salida:
        return None
    if "alpha_mode=1" in salida:
        return True
    pix = salida.splitlines()[-1].strip()
    return any(m in pix for m in ("rgba", "yauva", "yuva", "argb", "abgr", "bgra"))


def velo_png(destino, ancho=1080, alto=1920, fuerza=1.0):
    """El velo: la capa negra suave que hace que la caja blanca lea sobre la foto.

    La misma receta que usaba el script del demo (fuerte arriba y abajo, y una
    viñeta en los bordes), pero aqui es una HERRAMIENTA: cualquier proyecto
    puede pedirla y el resultado es el mismo siempre.

    Devuelve la ruta del PNG (con alfa) o None si Pillow no esta.
    """
    try:
        from PIL import Image
    except ImportError:
        return None
    velo = Image.new("L", (ancho, alto), 0)
    px = velo.load()
    for y in range(alto):
        f = y / alto
        if f < 0.26:
            a = 210 * (1 - f / 0.26) ** 1.4
        elif f > 0.62:
            a = 225 * min(1.0, ((f - 0.62) / 0.38) ** 1.3)
        else:
            a = 0
        if 0.16 < f < 0.78:
            e = min(1.0, (f - 0.16) / 0.12, (0.78 - f) / 0.12)
            a = max(a, 52 * min(1.0, e))
        for x in range(ancho):
            px[x, y] = int(min(255, a * fuerza))
    for x in range(ancho):
        d = min(x, ancho - 1 - x) / (ancho * 0.22)
        if d < 1:
            a = 60 * (1 - d) ** 1.6 * fuerza
            for y in range(alto):
                px[x, y] = min(255, int(px[x, y] + a))
    img = Image.new("RGBA", (ancho, alto), (10, 10, 10, 0))
    img.putalpha(velo)
    os.makedirs(os.path.dirname(os.path.abspath(destino)) or ".", exist_ok=True)
    img.save(destino)
    return destino


def _verifica_entradas(base, capa, fps_esperado=None, marco=None):
    """Los errores que ROMPEN la pieza se dicen ANTES de renderizar.

    · las tasas distintas: el medidor de movimiento lo cuenta como tirones;
    · una capa sin alfa: el texto sale con fondo negro en vez de desvanecido;
    · un marco fuera del lienzo: el clip se sale del cuadro (ffmpeg recorta y
      avisa por su cuenta, pero el aviso explica cuál de los cuatro números
      es el que no cuadra).
    """
    avisos = []
    fps_b, w_b, h_b = _fps_de(base)
    fps_c, w_c, h_c = _fps_de(capa)
    if fps_b and fps_c and abs(fps_b - fps_c) > 0.5:
        avisos.append(f"el fondo va a {fps_b:g} fps y la capa a {fps_c:g}: "
                      f"la pieza sale con tirones (el medidor de movimiento los "
                      f"cuenta). Renderiza la capa a la misma tasa.")
    if fps_esperado and fps_b and abs(fps_b - fps_esperado) > 0.5:
        avisos.append(f"el fondo va a {fps_b:g} fps y se pidio {fps_esperado:g}: "
                      f"misma tasa para los dos.")
    alfa = _tiene_alfa(capa)
    if alfa is False:
        avisos.append(f"la capa {os.path.basename(capa)} NO lleva canal alfa: "
                      f"el texto saldra con fondo negro en vez de desvanecido. "
                      f"Renderiza la capa a .mov (ProRes 4444) o .webm.")
    if w_b and w_c and (w_b, h_b) != (w_c, h_c) and not marco:
        # con marco NO es un problema: el video entra escalado en la caja y
        # la capa se escala al lienzo del kit
        avisos.append(f"el fondo es {w_b}x{h_b} y la capa {w_c}x{h_c}: "
                      f"se componen desajustados.")
    if marco:
        mx, my, mw, mh = (int(v) for v in marco)
        # el lienzo del layout enmarcado es el del KIT (no el del video: el
        # video entra en una caja DENTRO del lienzo)
        if mx < 0 or my < 0 or mx + mw > W or my + mh > H:
            avisos.append(f"el marco {mx},{my},{mw},{mh} no cabe en el lienzo "
                          f"de {W}x{H}: el clip se sale del cuadro.")
    return avisos


def cadena_mascara():
    """El filtro que convierte el ALFA de la capa en la mascara del desenfoque.

    LA ESCALA DE LA LUT: el filtro `lut` trabaja en 0-255, asi que la mascara
    tiene que salir en esa escala. La receta que circulaba (en la prosa, en
    el script del demo y aqui) era `min(1,(val-28)/130)`: devuelve 0-1, y en
    0-255 eso es CERO. La mascara salia VACIA y el fondo NO se desenfocaba
    detras de la letra.

    Medido (fondo rayado de 1 px, nitidez de la mitad con letra contra la
    mitad sin letra):
      · la receta vieja: 126,70 contra 126,89 -> ratio 1,00: NO desenfocaba;
      · esta:           83,54 contra 126,90 -> ratio 1,52: desenfoca detras
        de la letra y deja el resto nitido.

    La pieza se veia bien con la receta vieja porque el velo y el texto
    tapaban lo que faltaba, y NADIE lo midio: eran tres copias de lo mismo
    (prosa, demo y script) y ninguna ejecutada. Esta vez la mide un test.
    """
    return (f"[ab]lut=y='if(gt(val,{UMBRAL}),"
            f"min(255,(val-{UMBRAL})*255/130),0)'[mk];")


def marco_mascara(destino, ancho, alto, radio):
    """La mascara del marco: un rectángulo de esquinas redondeadas (blanco).

    Se genera con PIL en vez de con `geq`: `geq` reevalua la imagen pixel a
    pixel (lento) y sobre un video con color plano deja el clip en NEGRO
    (medido). Aqui solo se necesita la forma.
    """
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return None
    img = Image.new("L", (ancho, alto), 0)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, ancho - 1, alto - 1], radius=int(radio), fill=255)
    img.save(destino)
    return destino


def componer(base, capa, salida, audio=None, velo="auto", fps=24,
             duracion=None, crf=19, preset="slow", marco=None):
    """Compone la capa sobre el fondo y devuelve (avisos, comando).

    `velo` puede ser: "auto" (generar el velo por defecto), "0"/None (sin
    velo), 0.0..1.0 (la fuerza del velo generado) o una ruta a un PNG.

    `marco` es "x,y,w,h": el video entra en una CAJA con esquinas
    redondeadas sobre el lienzo negro y la tipografia va ENCIMA (el layout
    del reel de "cara": el clip enmarcado arriba, el copy debajo).

    Los avisos se AVISAN ANTES de correr ffmpeg: si la composicion falla, el
    motivo suele estar en uno de ellos (unas tasas que no casan, una capa sin
    alfa) y un aviso que sale despues del fallo no explica nada.
    """
    avisos = _verifica_entradas(base, capa, fps_esperado=fps, marco=marco)

    velo_ruta = None
    temporal = None
    if velo not in (None, "0", 0, 0.0, "no"):
        if isinstance(velo, str) and velo not in ("auto",):
            velo_ruta = velo
            if not os.path.isfile(velo_ruta):
                avisos.append(f"el velo {velo_ruta} no existe: se compone sin velo")
                velo_ruta = None
        else:
            fuerza = 1.0 if velo == "auto" else float(velo)
            _, w, h = _fps_de(base)
            temporal = tempfile.mkdtemp(prefix="componer_velo_")
            velo_ruta = velo_png(os.path.join(temporal, "velo.png"),
                                 w or 1080, h or 1920, fuerza)
            if velo_ruta is None:
                avisos.append("Pillow no esta: se compone sin velo")

    # la mascara del marco: un rectangulo de esquinas redondeadas (blanco)
    mx = my = mw = mh = 0
    mascara = None
    if marco:
        mx, my, mw, mh = (int(v) for v in marco)
        radio = int(min(mw, mh) * 0.031)          # las esquinas del marco
        if temporal is None:
            temporal = tempfile.mkdtemp(prefix="componer_marco_")
        mascara = marco_mascara(os.path.join(temporal, "marco.png"), mw, mh, radio)
        if mascara is None:
            avisos.append("Pillow no esta: el clip va SIN esquinas redondeadas")
            mascara = None

    for a in avisos:
        info(f"AVISO: {a}")

    # ---- las entradas, con su indice CONOCIDO -----------------------------
    # 0=base, 1=capa, y despues las imagenes de apoyo y el audio. El indice
    # se lleva la cuenta: antes se escribia a mano y un dia el audio quedo
    # descolocado (el "-map 2:a" apuntaba a la mascara).
    # el VP9 (.webm) solo entrega su alfa si se le FUERZA el decoder: el
    # nativo lo descarta y la capa llega opaca (medido: el clip de debajo
    # salia tapado por un rectangulo negro, y el aviso decia que la capa no
    # tenia alfa cuando si la tenia).
    _dec_capa = ["-c:v", "libvpx-vp9"] if capa.lower().endswith(".webm") else []
    entradas = ["-i", base, *_dec_capa, "-i", capa]
    n_entradas = 2
    i_velo = i_mascara = None
    if velo_ruta:
        i_velo = n_entradas
        entradas += ["-i", velo_ruta]
        n_entradas += 1
    if mascara:
        i_mascara = n_entradas
        entradas += ["-i", mascara]
        n_entradas += 1

    if marco:
        # EL CLIP ENMARCADO. El lienzo es el del KIT (1080x1920) y el clip
        # entra en una caja dentro de el; la capa de tipografia va sobre ese
        # lienzo (si no mide eso, se escala: la mascara del desenfoque se
        # recorta a la caja y una capa de otro tamaño no se puede recortar).
        #
        # El orden importa:
        #   1. la capa va al lienzo;
        #   2. el video se recorta al tamaño de la caja;
        #   3. la mascara de la LETRA se recorta a la caja, para que el
        #      desenfoque de profundidad solo afecte al video (y no a la
        #      esquina, donde el desenfoque del negro se comeria el borde);
        #   4. el velo se escala a la caja: el velo pertenece a la IMAGEN,
        #      no al lienzo (puesto sobre el lienzo ennegrece el negro);
        #   5. `alphamerge` mete la mascara de esquinas: el clip sale con las
        #      esquinas redondeadas y el resto del lienzo queda en negro.
        fc = (f"[1:v]scale={W}:{H}[ov0];"
              "[ov0]split=2[ov][ovs];"
              "[ovs]format=rgba,alphaextract,format=gray[al];"
              f"[al]boxblur=luma_radius={RADIO_MASCARA}:luma_power=2[ab];"
              + cadena_mascara() +
              f"[mk]crop={mw}:{mh}:{mx}:{my}[mkc];"
              f"[0:v]scale={mw}:{mh}:force_original_aspect_ratio=increase,"
              f"crop={mw}:{mh}[rec];"
              "[rec]split=2[shc][fbc];"
              f"[fbc]boxblur=luma_radius={RADIO_FONDO}:luma_power=2,"
              "eq=saturation=0.40:brightness=-0.20:contrast=0.9[blc];"
              "[shc][blc][mkc]maskedmerge[clip];")
        if i_velo is not None:
            fc += f"[{i_velo}:v]scale={mw}:{mh}[vl];"
            fc += "[clip][vl]overlay=0:0:format=auto[clipv];"
            base_clip = "clipv"
        else:
            base_clip = "clip"
        if i_mascara is not None:
            fc += (f"[{base_clip}][{i_mascara}:v]alphamerge[recortado];"
                   f"color=c=black:s={W}x{H}:r={fps}:d=1[negro];"
                   f"[negro][recortado]overlay={mx}:{my}:format=auto[campo];")
        else:
            fc += (f"color=c=black:s={W}x{H}:r={fps}:d=1[negro];"
                   f"[negro][{base_clip}]overlay={mx}:{my}:format=auto[campo];")
        fc += "[campo][ov]overlay=0:0:format=auto[ov2];"
        fc += "[ov2]format=yuv420p[v]"
    else:
        # A SANGRE: el video ocupa el cuadro y la tipografia va encima.
        fc = ("[0:v]split=2[sh][fb];"
              f"[fb]boxblur=luma_radius={RADIO_FONDO}:luma_power=2,"
              "eq=saturation=0.40:brightness=-0.20:contrast=0.9[bl];"
              "[1:v]split=2[ov][ovs];"
              "[ovs]format=rgba,alphaextract,format=gray[al];"
              f"[al]boxblur=luma_radius={RADIO_MASCARA}:luma_power=2[ab];"
              + cadena_mascara() +
              "[sh][bl][mk]maskedmerge[mm];"
              "[mm][ov]overlay=0:0:format=auto[ov2]")
        if i_velo is not None:
            fc += f";[ov2][{i_velo}:v]overlay=0:0:format=auto,format=yuv420p[v]"
        else:
            fc += ";[ov2]format=yuv420p[v]"

    mapa = ["-map", "[v]"]
    if audio:
        i_audio = n_entradas
        entradas += ["-i", audio]
        mapa += ["-map", f"{i_audio}:a"]
    else:
        mapa += ["-an"]

    cmd = ffmpeg_base() + entradas + ["-filter_complex", fc] + mapa
    if duracion:
        cmd += ["-t", f"{duracion:.3f}"]
    cmd += ["-r", str(fps)] + x264_args(crf=crf, preset=preset)
    cmd += ["-profile:v", "high", "-level", "4.1"]
    if audio:
        # el audio entra al SPEC de la plataforma (48 kHz, 192 kbps). Sin
        # esto la pieza sale con la tasa de la fuente (medido: 44.100 Hz)
        # y la puerta de entrega la rechaza en `delivery:reels`. La receta
        # que esta herramienta reemplaza lo:"-ar 48000" a mano.
        cmd += ["-c:a", "aac", "-b:a", "192k", "-ar", "48000"]
    cmd += [salida]

    try:
        run(cmd)
    finally:
        # el velo generado y la mascara son de trabajo: no se quedan junto a la pieza
        if temporal:
            shutil.rmtree(temporal, ignore_errors=True)
    return avisos, cmd


def main():
    ap = argparse.ArgumentParser(
        description="Compone la tipografia (capa con alfa) sobre el footage, "
                    "con el fondo desenfocado solo detras de la letra")
    ap.add_argument("base", help="el video de fondo (el footage)")
    ap.add_argument("capa", help="la capa con alfa (render_plan.py a .mov/.webm)")
    ap.add_argument("-o", "--output", required=True, help="la pieza final")
    ap.add_argument("--audio", default=None,
                    help="la pista de audio ya mezclada (si no, la capa va sin sonido)")
    ap.add_argument("--velo", default="auto",
                    help="'auto' (velo por defecto), '0' (sin velo), un numero "
                         "0-1 (la fuerza) o la ruta de un PNG")
    ap.add_argument("--marco", default=None,
                    help="'x,y,w,h': el video entra en una CAJA con esquinas "
                         "redondeadas y el resto del lienzo queda en negro (el "
                         "layout del reel de 'cara': el clip enmarcado arriba y "
                         "la tipografia abajo, en su propia zona)")
    ap.add_argument("--fps", type=int, default=24, help="la tasa de la pieza (24 nativo)")
    ap.add_argument("--duracion", type=float, default=None,
                    help="cortar la pieza a estos segundos")
    ap.add_argument("--crf", type=int, default=19,
                    help="calidad x264: menos es mejor (19 = alto, 23 = bajo)")
    ap.add_argument("--preset", default="slow",
                    help="esfuerzo x264: slow = mejor y mas lento, veryfast = rapido")
    add_common(ap)
    args = ap.parse_args()
    apply_common(args)

    for ruta in (args.base, args.capa):
        if not os.path.isfile(ruta):
            die(f"no existe: {ruta}")
    if args.audio and not os.path.isfile(args.audio):
        die(f"no existe: {args.audio}")

    marco = None
    if args.marco:
        try:
            vals = [int(v) for v in str(args.marco).replace(" ", "").split(",")]
        except ValueError:
            die("--marco quiere 'x,y,w,h' (cuatro numeros)")
        if len(vals) != 4 or vals[2] <= 0 or vals[3] <= 0:
            die("--marco quiere 'x,y,w,h' con ancho y alto positivos")
        marco = vals
    avisos, cmd = componer(args.base, args.capa, args.output, audio=args.audio,
                           velo=args.velo, fps=args.fps, duracion=args.duracion,
                           crf=args.crf, preset=args.preset, marco=marco)
    for a in avisos:
        info(f"AVISO: {a}")
    if not os.path.isfile(args.output):
        die("la composicion no produjo el fichero")
    ver = verify_output(args.output)
    emit(args.output, avisos=avisos, verificacion=ver)


if __name__ == "__main__":
    main()
