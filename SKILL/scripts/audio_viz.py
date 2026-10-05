#!/usr/bin/env python3
"""Visualización de audio: ondas / espectro / barras de ffmpeg, o un
AUDIOGRAMA completo (clip de podcast o voz listo para redes).

Modos:
  waves | spectrum | freqs   filtros show* de ffmpeg, standalone o --overlay
  audiograma                 capas fijas: fondo · portada + título arriba ·
                             barras espejadas al centro · progreso · banda
                             libre abajo para subtítulos (caption.py)

Reglas del audiograma (references/tecnicas-video.md, "Visualización de audio"):
  - Cada barra es FUNCIÓN DEL FRAME: la energía por banda se calcula una vez,
    offline, para todo el clip (nunca un analizador en tiempo real: el
    render no corre en tiempo real y se desincroniza).
  - Graves al centro, agudos hacia los bordes (espejo).
  - Recortar al fragmento (≤90 s): mejor pieza y render más liviano.
  - Se entiende en mute: luego quemar subtítulos con caption.py.

Uso:
  python audio_viz.py audio.mp3 -o viz.mp4 [--modo waves|spectrum|freqs]
  python audio_viz.py audio.mp3 -o viz.mp4 --overlay video.mp4
  python audio_viz.py episodio.mp3 -o clip.mp4 --modo audiograma \\
      --titulo "Episodio 42" --subtitulo "DragonJAR Podcast" --portada cover.jpg \\
      --inicio 754 --duracion 45 [--brand brand/dragonjar.json]
"""
import argparse
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg_tools"))
from _comun import VF_RGB_A_BT709, codificar_frames, die, info, load_brand, probe  # noqa: E402

ACENTO_NEUTRO = "E8480C"   # el mismo acento neutro del renderer (modo libre)


def acento(brand_path, color):
    """Color del acento: --color > acento del brand pack > neutro."""
    if color:
        return color.lstrip("#").replace("0x", "")
    if brand_path:
        b = load_brand(brand_path)
        v = (b.get("colores") or {}).get("acento") or (b.get("colors") or {}).get("primary")
        if v:
            return str(v).lstrip("#")
    return ACENTO_NEUTRO


def bandas_por_frame(audio, inicio, dur, fps, n):
    """Energía por banda (0..1) para cada frame, precalculada y suavizada
    (subida inmediata, caída 18%/frame): determinista y reproducible."""
    import numpy as np
    sr = 22050
    cmd = ["ffmpeg", "-v", "error", "-ss", str(inicio), "-t", str(dur), "-i", audio,
           "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"]
    x = np.frombuffer(subprocess.run(cmd, capture_output=True).stdout, dtype=np.float32)
    if len(x) < sr // 4:
        die(f"no se pudo leer audio de {audio}")
    nf = int(dur * fps)
    win = 2048
    hann = np.hanning(win).astype(np.float32)
    bordes = np.geomspace(60, 9000, n + 1)                   # bandas log
    idx = np.clip((bordes / sr * win).astype(int), 1, win // 2)
    crudo = np.zeros((nf, n), dtype=np.float32)
    for f in range(nf):
        c = int(f / fps * sr)
        seg = x[max(0, c - win // 2): c + win // 2]
        if len(seg) < win:
            seg = np.pad(seg, (0, win - len(seg)))
        mag = np.abs(np.fft.rfft(seg * hann))
        crudo[f] = [mag[idx[b]:max(idx[b] + 1, idx[b + 1])].mean() for b in range(n)]
    crudo = np.log1p(crudo)
    ref = np.percentile(crudo, 97, axis=0) + 1e-6           # por banda: agudos visibles
    norm = np.clip(crudo / ref, 0, 1)
    out = np.zeros_like(norm)
    for f in range(nf):
        out[f] = norm[f] if f == 0 else np.maximum(norm[f], out[f - 1] * 0.82)
    return out


def audiograma(a):
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/ffmpeg_tools")
    from _plataforma import resolver_fuente
    from _delivery import safe_margins_px
    W, H = (int(v) for v in a.size.lower().split("x"))
    dur_total = probe(a.audio).get("duration") or 0
    dur = a.duracion or max(0.1, dur_total - a.inicio)
    if dur > 90:
        info(f"aviso: {dur:.0f}s — un audiograma rinde mejor recortado al fragmento (≤90 s)")
    fps = a.fps
    ac = tuple(int(acento(a.brand, a.color)[i:i + 2], 16) for i in (0, 2, 4))
    plataforma = "reels" if H > W else "youtube"
    sm = safe_margins_px(plataforma, W, H)
    mx = max(sm["left"], sm["right"], int(W * 0.06))
    nb = max(4, a.barras // 2)                                 # mitad: se espeja
    energia = bandas_por_frame(a.audio, a.inicio, dur, fps, nb)
    # capa fija: fondo + portada + títulos (se compone una sola vez)
    fondo = Image.new("RGB", (W, H), (10, 10, 10))
    glow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(glow).ellipse([W * 0.1, H * 0.35, W * 0.9, H * 0.65], fill=70)
    fondo = Image.composite(Image.new("RGB", (W, H), ac), fondo,
                            glow.filter(ImageFilter.GaussianBlur(min(W, H) * 0.12)))
    d = ImageDraw.Draw(fondo)
    ft = ImageFont.truetype(resolver_fuente("Plus Jakarta Sans", generica="sans-bold"), int(W * 0.06))
    fs = ImageFont.truetype(resolver_fuente("Montserrat", generica="sans"), int(W * 0.035))
    for f_, peso in ((ft, 800), (fs, 600)):   # fuentes variables: fijar el peso
        try:
            f_.set_variation_by_axes([peso])
        except Exception:
            pass
    y = sm["top"] + int(H * 0.03)
    if a.portada and os.path.isfile(a.portada):
        lado = int(min(W * 0.36, H * 0.22))
        cov = Image.open(a.portada).convert("RGB")
        c = min(cov.size)
        cov = cov.crop(((cov.width - c) // 2, (cov.height - c) // 2,
                        (cov.width + c) // 2, (cov.height + c) // 2)).resize((lado, lado), Image.LANCZOS)
        m = Image.new("L", (lado, lado), 0)
        ImageDraw.Draw(m).rounded_rectangle([0, 0, lado, lado], radius=int(lado * 0.08), fill=255)
        fondo.paste(cov, ((W - lado) // 2, y), m)
        y += lado + int(H * 0.025)
    for txt, fnt, col in ((a.titulo, ft, (250, 248, 246)), (a.subtitulo, fs, (170, 170, 170))):
        if txt:
            while fnt.size > 18 and d.textlength(txt, font=fnt) > W - 2 * mx:
                fnt = fnt.font_variant(size=fnt.size - 2)
                try:
                    fnt.set_variation_by_axes([800 if fnt.size > W * 0.04 else 600])
                except Exception:
                    pass
            d.text((W / 2, y), txt, font=fnt, fill=col, anchor="ma")
            y += int(fnt.size * 1.35)
    # barras: banda central; abajo queda libre para subtítulos
    alto_max = H * 0.13
    cy = int(max(y + alto_max + H * 0.04, H * 0.50))
    ancho = W - 2 * mx
    paso = ancho / (2 * nb)
    grosor = max(4, int(paso * 0.62))
    yp = int(cy + alto_max + H * 0.04)
    tmpd = tempfile.mkdtemp(prefix="audiograma_")
    for f in range(len(energia)):
        im = fondo.copy()
        dr = ImageDraw.Draw(im)
        for b in range(nb):
            h = max(grosor, energia[f][b] * alto_max)
            for lado_ in (-1, 1):            # espejo: graves al centro
                xc = W / 2 + lado_ * (b + 0.5) * paso
                dr.rounded_rectangle([xc - grosor / 2, cy - h, xc + grosor / 2, cy + h],
                                     radius=grosor // 2, fill=ac)
        dr.rounded_rectangle([mx, yp, W - mx, yp + 6], radius=3, fill=(60, 60, 60))
        dr.rounded_rectangle([mx, yp, mx + (W - 2 * mx) * (f + 1) / len(energia), yp + 6],
                             radius=3, fill=(250, 248, 246))
        im.save(f"{tmpd}/f_{f:05d}.png")
    muda = os.path.join(tmpd, "muda.mp4")
    codificar_frames(f"{tmpd}/f_%05d.png", fps, muda, crf=18)
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", muda, "-ss", str(a.inicio), "-t", str(dur),
                        "-i", a.audio, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
                        "-b:a", "192k", "-af", f"afade=t=out:st={max(0, dur - 0.4):.2f}:d=0.4",
                        "-shortest", "-movflags", "+faststart", a.out])
    if r.returncode != 0:
        die("ffmpeg falló al muxear el audio del audiograma")
    print(f"OK {a.out} (audiograma, {dur:.1f}s, {nb * 2} barras) — subtítulos: "
          f"caption.py {a.out} --transcribe --animate pop (o --palabras)")


def main():
    ap = argparse.ArgumentParser(
        description="Visualiza un audio como video (ondas, espectro, barras) o arma un audiograma.")
    ap.add_argument("audio", help="archivo de audio de entrada")
    ap.add_argument("-o", "--out", required=True, help="video de salida (.mp4)")
    ap.add_argument("--modo", default="waves", choices=["waves", "spectrum", "freqs", "audiograma"],
                    help="tipo de visualización (default: waves)")
    ap.add_argument("--color", default=None,
                    help="color hex del acento, ej. C11B05 (default: acento del --brand o neutro)")
    ap.add_argument("--brand", default=None, help="brand pack (brand/*.json): el color sale de su acento")
    ap.add_argument("-s", "--size", default="1080x1920", help="tamaño (default: 1080x1920)")
    ap.add_argument("-r", "--fps", default=30, type=int, help="fps (default: 30)")
    ap.add_argument("--overlay", help="video base: la banda se superpone dentro de la zona segura")
    ap.add_argument("--altura", default=240, type=int, help="altura de la banda con --overlay")
    g = ap.add_argument_group("audiograma")
    g.add_argument("--titulo"); g.add_argument("--subtitulo")
    g.add_argument("--portada", help="imagen de portada (se recorta cuadrada)")
    g.add_argument("--barras", type=int, default=32, help="barras en total (espejadas; default 32)")
    g.add_argument("--inicio", type=float, default=0.0, help="segundo de inicio del fragmento")
    g.add_argument("--duracion", type=float, help="duración del fragmento (≤90 s recomendado)")
    a = ap.parse_args()

    if not os.path.exists(a.audio):
        sys.exit(f"ERROR: no existe {a.audio}")
    if a.modo == "audiograma":
        return audiograma(a)
    dur = probe(a.audio).get("duration") or 0
    color = "0x" + acento(a.brand, a.color)
    if a.modo == "waves":
        filtro = f"showwaves=s={a.size}:mode=line:colors={color}:rate={a.fps}"
    elif a.modo == "spectrum":   # showspectrum usa esquemas propios; fire es el más cercano a marca
        filtro = f"showspectrum=s={a.size}:color=fire:slide=scroll:mode=combined"
    else:
        filtro = f"showfreqs=s={a.size}:mode=bar:colors={color}:rate={a.fps}"
    if a.overlay:
        if not os.path.exists(a.overlay):
            sys.exit(f"ERROR: no existe {a.overlay}")
        from _delivery import safe_margins_px
        v = probe(a.overlay)["video"]
        w, h = v["width"], v["height"]
        # dentro de la zona segura: abajo en 9:16 vive la UI de la plataforma
        sm = safe_margins_px("reels" if h > w else "youtube", w, h)
        fc = (f"[0:a]{filtro},scale={w}:{a.altura}[viz];"
              f"[1:v][viz]overlay=0:H-{a.altura}-{sm['bottom']},{VF_RGB_A_BT709},format=yuv420p[v]")
        cmd = ["ffmpeg", "-y", "-v", "error", "-i", a.audio, "-i", a.overlay,
               "-filter_complex", fc, "-map", "[v]", "-map", "0:a"]
    else:
        cmd = ["ffmpeg", "-y", "-v", "error", "-i", a.audio,
               "-filter_complex", f"[0:a]{filtro},{VF_RGB_A_BT709},format=yuv420p[v]",
               "-map", "[v]", "-map", "0:a"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-colorspace", "bt709",
            "-color_primaries", "bt709", "-color_trc", "bt709", "-c:a", "aac",
            "-t", str(dur), a.out]
    if subprocess.run(cmd).returncode != 0:
        sys.exit("ERROR: ffmpeg falló generando la visualización")
    print(f"OK {a.out} ({a.modo}, {dur:.1f}s)")


if __name__ == "__main__":
    main()
