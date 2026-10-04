#!/usr/bin/env python3
"""montaje.py — navaja suiza de edición de video de EditorIA.

18 operaciones de edición en un solo script, todas con las mismas
convenciones (--dry-run, --json, nunca sobrescribir el input, verificar
el output). Para composición creativa (escenas, motion graphics) usar
scripts/render_plan.py; esto es cirugía de clips.

Operaciones:
  unir        concatena N videos en uno
  cortar      recorta un tramo (inicio/fin o inicio/duración)
  fundido     fade in/out de video y audio
  transicion  xfade entre dos clips (fundido, cortinillas, etc.)
  pip         picture-in-picture (un video sobre otro)
  marca-agua  logo/imagen superpuesta con opacidad
  audio       extraer | quitar | reemplazar la pista de audio
  gif         exporta GIF animado (paleta optimizada)
  pase        slideshow: carpeta de imágenes -> video
  rotar       rota 90/180/270 grados
  voltear     espejo horizontal / vertical
  bucle       repite el video N veces o hasta una duración
  escala      escala + pad a un tamaño exacto
  color       ajustes genéricos (brillo/contraste/saturación)
  velocidad   cambia la velocidad constante (video+audio)
  reversa     reproduce al revés (video+audio)
  limpiar-audio  denoise + filtro de graves para voz
  chroma      chromakey: sujeto sobre fondo/imagen

Ejemplos:
  python scripts/ffmpeg_tools/montaje.py unir a.mp4 b.mp4 c.mp4 -o final.mp4
  python scripts/ffmpeg_tools/montaje.py cortar video.mp4 --inicio 5 --fin 12 -o tramo.mp4
  python scripts/ffmpeg_tools/montaje.py fundido video.mp4 --dentro 0.5 --fuera 1 -o out.mp4
  python scripts/ffmpeg_tools/montaje.py audio extraer video.mp4 -o audio.m4a
  python scripts/ffmpeg_tools/montaje.py gif video.mp4 --fps 12 --ancho 480 -o anim.gif
"""
import argparse
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _comun import (add_common, apply_common, cfr_args, default_output, die,
                    emit, info, probe, run, verify_output, ffmpeg_base,
                    video_args, parse_time)
from _plataforma import dir_temp


def _vargs(meta, args):
    # cfr_args: si la fuente es VFR (telefono/grabacion de pantalla), conforma
    # a CFR para que el corte no desincronice; en CFR no agrega nada.
    return video_args(meta, crf=getattr(args, "crf", 18)) + cfr_args(meta)


def cmd_unir(a):
    for v in a.videos:
        if not os.path.isfile(v):
            die(f"no existe: {v}")
    out = a.output or default_output(a.videos[0], "_unido", ext=".mp4")
    if a.rapido:
        # concat demuxer con stream copy (mismo codec/parámetros)
        lst = os.path.join(dir_temp(), "editoria_concat.txt")
        with open(lst, "w", encoding="utf-8") as f:
            for v in a.videos:
                f.write(f"file '{os.path.abspath(v)}'\n")
        cmd = ffmpeg_base() + ["-f", "concat", "-safe", "0", "-i", lst,
                               "-c", "copy", out]
        run(cmd)
        os.remove(lst)
    else:
        inputs = []
        for v in a.videos:
            inputs += ["-i", v]
        n = len(a.videos)
        fc = "".join(f"[{i}:v]settb=AVTB,fps=30[{i}v];[{i}:a]aformat=sample_rates=48000:channel_layouts=stereo[{i}a];" for i in range(n))
        fc += "".join(f"[{i}v][{i}a]" for i in range(n))
        fc += f"concat=n={n}:v=1:a=1[v][a]"
        cmd = ffmpeg_base() + inputs + ["-filter_complex", fc, "-map", "[v]", "-map", "[a]"]
        cmd += _vargs(probe(a.videos[0]), a) + ["-c:a", "aac", "-b:a", "128k", out]
        run(cmd)
    verify_output(out)
    info(f"OK {out} ({len(a.videos)} clips unidos)")
    emit(out, clips=len(a.videos))


def cmd_cortar(a):
    if not os.path.isfile(a.video):
        die(f"no existe: {a.video}")
    meta = probe(a.video)
    ini = parse_time(a.inicio) if a.inicio else 0.0
    if a.duracion:
        dur = parse_time(a.duracion)
    elif a.fin:
        dur = parse_time(a.fin) - ini
    else:
        die("indicar --duracion o --fin")
    if dur <= 0:
        die("la duración debe ser positiva")
    out = a.output or default_output(a.video, "_corte")
    if a.rapido:
        cmd = ffmpeg_base() + ["-ss", str(ini), "-i", a.video, "-t", str(dur),
                               "-c", "copy", out]
    else:
        cmd = ffmpeg_base() + ["-ss", str(ini), "-i", a.video, "-t", str(dur)]
        if meta.get("audio"):
            cmd += ["-map", "0:v", "-map", "0:a"]
        else:
            cmd += ["-map", "0:v", "-an"]
        cmd += _vargs(meta, a) + [out]
    run(cmd)
    verify_output(out)
    info(f"OK {out} ({ini:.2f}s +{dur:.2f}s)")
    emit(out, inicio=ini, duracion=dur)


def cmd_fundido(a):
    if not os.path.isfile(a.video):
        die(f"no existe: {a.video}")
    meta = probe(a.video)
    dur = meta.get("duration") or 0
    out = a.output or default_output(a.video, "_fundido")
    vf = []
    if a.dentro > 0:
        vf.append(f"fade=t=in:st=0:d={a.dentro}")
    if a.fuera > 0 and dur:
        vf.append(f"fade=t=out:st={max(0, dur - a.fuera):.3f}:d={a.fuera}")
    af = []
    if meta.get("audio"):
        if a.dentro > 0:
            af.append(f"afade=t=in:st=0:d={a.dentro}")
        if a.fuera > 0 and dur:
            af.append(f"afade=t=out:st={max(0, dur - a.fuera):.3f}:d={a.fuera}")
    cmd = ffmpeg_base() + ["-i", a.video]
    maps = []
    if vf:
        cmd += ["-vf", ",".join(vf)]
    maps += ["-map", "0:v"]
    if af:
        cmd += ["-af", ",".join(af)]
    if meta.get("audio"):
        maps += ["-map", "0:a"]
    else:
        maps += ["-an"]
    cmd += maps + _vargs(meta, a) + [out]
    run(cmd)
    verify_output(out)
    info(f"OK {out} (fundido dentro={a.dentro}s fuera={a.fuera}s)")
    emit(out)


def cmd_transicion(a):
    for v in (a.video1, a.video2):
        if not os.path.isfile(v):
            die(f"no existe: {v}")
    m1, m2 = probe(a.video1), probe(a.video2)
    d1 = m1.get("duration") or 0
    offset = max(0, d1 - a.duracion)
    out = a.output or default_output(a.video1, "_xfade")
    fc = (f"[0:v][1:v]xfade=transition={a.tipo}:duration={a.duracion}:"
          f"offset={offset:.3f}[v]")
    maps = ["-map", "[v]"]
    if m1.get("audio") and m2.get("audio"):
        fc += f";[0:a][1:a]acrossfade=d={a.duracion}[a]"
        maps += ["-map", "[a]"]
    else:
        maps += ["-an"]
    cmd = (ffmpeg_base() + ["-i", a.video1, "-i", a.video2,
                            "-filter_complex", fc] + maps +
           _vargs(m1, a) + [out])
    run(cmd)
    verify_output(out)
    info(f"OK {out} (transición {a.tipo} de {a.duracion}s)")
    emit(out, transicion=a.tipo)


def cmd_pip(a):
    for v in (a.base, a.overlay):
        if not os.path.isfile(v):
            die(f"no existe: {v}")
    meta = probe(a.base)
    pos = {"abajo-derecha": "W-w-40:H-h-40", "abajo-izquierda": "40:H-h-40",
           "arriba-derecha": "W-w-40:40", "arriba-izquierda": "40:40",
           "centro": "(W-w)/2:(H-h)/2"}.get(a.posicion, a.posicion)
    fc = (f"[1:v]scale={a.ancho}:-2[pip];"
          f"[0:v][pip]overlay={pos}:format=yuv420[e]")
    if a.hasta:
        fc = (f"[1:v]scale={a.ancho}:-2,setpts=PTS-STARTPTS[pip0];"
              f"[pip0]trim=0:{a.hasta},setpts=PTS-STARTPTS[pip];"
              f"[0:v][pip]overlay={pos}:enable='between(t,0,{a.hasta})':format=yuv420[e]")
    cmd = (ffmpeg_base() + ["-i", a.base, "-i", a.overlay,
                            "-filter_complex", fc, "-map", "[e]"])
    if meta.get("audio"):
        cmd += ["-map", "0:a", "-c:a", "copy"]
    else:
        cmd += ["-an"]
    out = a.output or default_output(a.base, "_pip")
    cmd += _vargs(meta, a) + [out]
    run(cmd)
    verify_output(out)
    info(f"OK {out} (PiP {a.posicion})")
    emit(out)


def cmd_marca_agua(a):
    if not os.path.isfile(a.video):
        die(f"no existe: {a.video}")
    if not os.path.isfile(a.imagen):
        die(f"no existe: {a.imagen}")
    meta = probe(a.video)
    pos = {"abajo-derecha": "W-w-30:H-h-30", "abajo-izquierda": "30:H-h-30",
           "arriba-derecha": "W-w-30:30", "arriba-izquierda": "30:30"}.get(a.posicion, a.posicion)
    fc = (f"[1:v]format=rgba,colorchannelmixer=aa={a.opacidad}[wm];"
          f"[0:v][wm]overlay={pos}:format=yuv420[v]")
    out = a.output or default_output(a.video, "_wm")
    cmd = (ffmpeg_base() + ["-i", a.video, "-i", a.imagen,
                            "-filter_complex", fc, "-map", "[v]"])
    if meta.get("audio"):
        cmd += ["-map", "0:a", "-c:a", "copy"]
    else:
        cmd += ["-an"]
    cmd += _vargs(meta, a) + [out]
    run(cmd)
    verify_output(out)
    info(f"OK {out} (marca de agua {a.posicion})")
    emit(out)


def cmd_audio(a):
    if not os.path.isfile(a.video):
        die(f"no existe: {a.video}")
    meta = probe(a.video)
    if a.accion == "extraer":
        out = a.output or default_output(a.video, "_audio", ext=".m4a")
        cmd = ffmpeg_base() + ["-i", a.video, "-vn", "-c:a", "aac", "-b:a", "192k", out]
        run(cmd)
    elif a.accion == "quitar":
        out = a.output or default_output(a.video, "_sin_audio")
        cmd = (ffmpeg_base() + ["-i", a.video, "-map", "0:v", "-an"] +
               _vargs(meta, a) + [out])
        run(cmd)
    elif a.accion == "reemplazar":
        if not os.path.isfile(a.fuente):
            die(f"no existe el audio: {a.fuente}")
        out = a.output or default_output(a.video, "_nuevo_audio")
        cmd = (ffmpeg_base() + ["-i", a.video, "-i", a.fuente,
                                "-map", "0:v", "-map", "1:a",
                                "-c:v", "copy", "-shortest"] + [out])
        run(cmd)
    verify_output(out)
    info(f"OK {out} (audio: {a.accion})")
    emit(out, accion=a.accion)


def cmd_gif(a):
    if not os.path.isfile(a.video):
        die(f"no existe: {a.video}")
    meta = probe(a.video)
    out = a.output or default_output(a.video, "", ext=".gif")
    pal = os.path.join(dir_temp(), "editoria_pal.png")
    vf = f"fps={a.fps},scale={a.ancho}:-1:flags=lanczos"
    if a.inicio or a.duracion:
        ini = parse_time(a.inicio) if a.inicio else 0
        pre = ["-ss", str(ini)]
        if a.duracion:
            pre += ["-t", str(parse_time(a.duracion))]
    else:
        pre = []
    run(ffmpeg_base() + pre + ["-i", a.video, "-vf", f"{vf},palettegen", "-y", pal],
        quiet=True)
    run(ffmpeg_base() + pre + ["-i", a.video, "-i", pal,
                               "-lavfi", f"{vf} [x]; [x][1:v] paletteuse",
                               "-y", out], quiet=True)
    os.remove(pal)
    verify_output(out)
    info(f"OK {out} (GIF {a.fps}fps, {a.ancho}px)")
    emit(out)


def cmd_pase(a):
    if not os.path.isdir(a.carpeta):
        die(f"no existe la carpeta: {a.carpeta}")
    imgs = sorted(f for f in os.listdir(a.carpeta)
                  if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp")))
    if not imgs:
        die("la carpeta no tiene imágenes")
    lst = os.path.join(dir_temp(), "editoria_pase.txt")
    with open(lst, "w", encoding="utf-8") as f:
        for im in imgs:
            f.write(f"file '{os.path.join(os.path.abspath(a.carpeta), im)}'\n")
            f.write(f"duration {a.duracion}\n")
        f.write(f"file '{os.path.join(os.path.abspath(a.carpeta), imgs[-1])}'\n")
    out = a.output or os.path.join(os.path.abspath(a.carpeta), "pase.mp4")
    vf = (f"scale=1080:1920:force_original_aspect_ratio=decrease,"
          f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2,fps=30")
    if a.zoom:
        vf += (",zoompan=z='min(zoom+0.0008,1.15)':d=90:x='iw/2-(iw/zoom/2)':"
               "y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30")
    cmd = (ffmpeg_base() + ["-f", "concat", "-safe", "0", "-i", lst,
                            "-vf", vf, "-an",
                            "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
                            "-movflags", "+faststart", out])
    run(cmd)
    os.remove(lst)
    verify_output(out)
    info(f"OK {out} ({len(imgs)} imágenes x {a.duracion}s)")
    emit(out, imagenes=len(imgs))


def cmd_rotar(a):
    if not os.path.isfile(a.video):
        die(f"no existe: {a.video}")
    meta = probe(a.video)
    t = {"90": "transpose=1", "180": "transpose=1,transpose=1",
         "270": "transpose=2"}.get(a.grados)
    if not t:
        die("--grados debe ser 90, 180 o 270")
    out = a.output or default_output(a.video, f"_rot{a.grados}")
    cmd = ffmpeg_base() + ["-i", a.video, "-vf", t, "-map", "0:v"]
    if meta.get("audio"):
        cmd += ["-map", "0:a", "-c:a", "copy"]
    else:
        cmd += ["-an"]
    cmd += _vargs(meta, a) + [out]
    run(cmd)
    verify_output(out)
    info(f"OK {out} (rotado {a.grados}°)")
    emit(out)


def cmd_voltear(a):
    if not os.path.isfile(a.video):
        die(f"no existe: {a.video}")
    meta = probe(a.video)
    f = {"horizontal": "hflip", "vertical": "vflip"}.get(a.eje)
    if not f:
        die("--eje debe ser horizontal o vertical")
    out = a.output or default_output(a.video, f"_flip_{a.eje[:1]}")
    cmd = ffmpeg_base() + ["-i", a.video, "-vf", f, "-map", "0:v"]
    if meta.get("audio"):
        cmd += ["-map", "0:a", "-c:a", "copy"]
    else:
        cmd += ["-an"]
    cmd += _vargs(meta, a) + [out]
    run(cmd)
    verify_output(out)
    info(f"OK {out} (volteado {a.eje})")
    emit(out)


def cmd_bucle(a):
    if not os.path.isfile(a.video):
        die(f"no existe: {a.video}")
    meta = probe(a.video)
    out = a.output or default_output(a.video, "_bucle")
    cmd = ffmpeg_base() + ["-stream_loop", str(a.veces), "-i", a.video,
                           "-c", "copy", out]
    run(cmd)
    verify_output(out)
    info(f"OK {out} (x{a.veces + 1} en total)")
    emit(out, veces=a.veces)


def cmd_escala(a):
    if not os.path.isfile(a.video):
        die(f"no existe: {a.video}")
    meta = probe(a.video)
    w, h = a.tamano.lower().split("x")
    vf = (f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
          f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color={a.fondo},setsar=1")
    out = a.output or default_output(a.video, f"_{a.tamano}")
    cmd = ffmpeg_base() + ["-i", a.video, "-vf", vf, "-map", "0:v"]
    if meta.get("audio"):
        cmd += ["-map", "0:a", "-c:a", "copy"]
    else:
        cmd += ["-an"]
    cmd += _vargs(meta, a) + [out]
    run(cmd)
    verify_output(out)
    info(f"OK {out} ({a.tamano})")
    emit(out)


def cmd_color(a):
    if not os.path.isfile(a.video):
        die(f"no existe: {a.video}")
    meta = probe(a.video)
    vf = (f"eq=brightness={a.brillo}:contrast={a.contraste}:"
          f"saturation={a.saturacion}")
    out = a.output or default_output(a.video, "_color")
    cmd = ffmpeg_base() + ["-i", a.video, "-vf", vf, "-map", "0:v"]
    if meta.get("audio"):
        cmd += ["-map", "0:a", "-c:a", "copy"]
    else:
        cmd += ["-an"]
    cmd += _vargs(meta, a) + [out]
    run(cmd)
    verify_output(out)
    info(f"OK {out} (color b={a.brillo} c={a.contraste} s={a.saturacion})")
    emit(out)


def cmd_velocidad(a):
    if not os.path.isfile(a.video):
        die(f"no existe: {a.video}")
    meta = probe(a.video)
    if not (0.25 <= a.factor <= 4.0):
        die("--factor debe estar entre 0.25 y 4.0")
    vf = f"setpts={1 / a.factor:.4f}*PTS"
    af = f"atempo={a.factor}"
    # atempo solo acepta 0.5-2.0: encadenar si hace falta
    f = a.factor
    tempos = []
    while f > 2.0:
        tempos.append("atempo=2.0")
        f /= 2.0
    while f < 0.5:
        tempos.append("atempo=0.5")
        f /= 0.5
    tempos.append(f"atempo={f:.4f}")
    af = ",".join(tempos)
    out = a.output or default_output(a.video, f"_x{a.factor}")
    cmd = ffmpeg_base() + ["-i", a.video, "-vf", vf, "-map", "0:v"]
    if meta.get("audio"):
        cmd += ["-af", af, "-map", "0:a"]
    else:
        cmd += ["-an"]
    cmd += _vargs(meta, a) + [out]
    run(cmd)
    verify_output(out)
    info(f"OK {out} (velocidad x{a.factor})")
    emit(out)


def cmd_reversa(a):
    if not os.path.isfile(a.video):
        die(f"no existe: {a.video}")
    meta = probe(a.video)
    out = a.output or default_output(a.video, "_reversa")
    cmd = ffmpeg_base() + ["-i", a.video, "-vf", "reverse", "-map", "0:v"]
    if meta.get("audio"):
        cmd += ["-af", "areverse", "-map", "0:a"]
    else:
        cmd += ["-an"]
    cmd += _vargs(meta, a) + [out]
    run(cmd)
    verify_output(out)
    info(f"OK {out} (reversa)")
    emit(out)



def cmd_limpiar_audio(a):
    if not os.path.isfile(a.video):
        die(f"no existe: {a.video}")
    meta = probe(a.video)
    if not meta.get("audio"):
        die("el video no tiene pista de audio")
    if not (0 <= a.fuerza <= 30):
        die("--fuerza debe estar entre 0 y 30")
    # afftdn nf en dB [-80,-20]: más negativo = más agresivo
    nf = -20 - a.fuerza
    af = [f"afftdn=nf={nf}", "highpass=f=80"]
    out = a.output or default_output(a.video, "_limpio")
    cmd = (ffmpeg_base() + ["-i", a.video, "-af", ",".join(af),
                            "-map", "0:v", "-map", "0:a"] +
           _vargs(meta, a) + ["-c:a", "aac", "-b:a", "192k", out])
    run(cmd)
    verify_output(out)
    info(f"OK {out} (denoise fuerza {a.fuerza})")
    emit(out)


def cmd_chroma(a):
    if not os.path.isfile(a.video):
        die(f"no existe: {a.video}")
    if not os.path.isfile(a.fondo):
        die(f"no existe el fondo: {a.fondo}")
    meta = probe(a.video)
    mf = probe(a.fondo)
    es_video_fondo = bool(mf.get("video"))
    # fórmula del skill (ver references/tecnicas-video.md)
    ck = (f"chromakey={a.color}:{a.similitud}:{a.mezcla},"
          f"format=rgba")
    if es_video_fondo:
        fc = (f"[0:v]{ck}[fg];[1:v]scale=iw:ih[bg];[bg][fg]overlay=0:0:format=yuv420[v]")
    else:
        fc = (f"[0:v]{ck}[fg];[1:v]scale=iw:ih,format=rgba[bg];"
              f"[bg][fg]overlay=0:0:format=yuv420[v]")
    out = a.output or default_output(a.video, "_chroma")
    cmd = (ffmpeg_base() + ["-i", a.video, "-i", a.fondo,
                            "-filter_complex", fc, "-map", "[v]", "-shortest"])
    if meta.get("audio"):
        cmd += ["-map", "0:a", "-c:a", "copy"]
    else:
        cmd += ["-an"]
    cmd += _vargs(meta, a) + [out]
    run(cmd)
    verify_output(out)
    info(f"OK {out} (chroma {a.color})")
    emit(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="op", required=True)

    p = sub.add_parser("unir", help="concatena N videos")
    p.add_argument("videos", nargs="+")
    p.add_argument("-o", "--output")
    p.add_argument("--rapido", action="store_true", help="stream copy (mismo codec)")
    p.add_argument("--crf", type=int, default=18)

    p = sub.add_parser("cortar", help="recorta un tramo")
    p.add_argument("video")
    p.add_argument("--inicio", default="0", help="inicio (s o mm:ss)")
    p.add_argument("--fin", help="fin (s o mm:ss)")
    p.add_argument("--duracion", help="duración en vez de --fin")
    p.add_argument("-o", "--output")
    p.add_argument("--rapido", action="store_true",
                   help="stream copy: rapido pero el corte cae en el keyframe "
                   "mas cercano (puede empezar antes o en frame congelado); "
                   "sin --rapido el corte es exacto")
    p.add_argument("--crf", type=int, default=18)

    p = sub.add_parser("fundido", help="fade in/out")
    p.add_argument("video")
    p.add_argument("--dentro", type=float, default=0.5)
    p.add_argument("--fuera", type=float, default=0.5)
    p.add_argument("-o", "--output")
    p.add_argument("--crf", type=int, default=18)

    p = sub.add_parser("transicion", help="xfade entre dos clips")
    p.add_argument("video1")
    p.add_argument("video2")
    p.add_argument("--tipo", default="fade",
                   help="fade, dissolve, wipeleft, wiperight, wipeup, wipedown, circlecrop, ...")
    p.add_argument("--duracion", type=float, default=0.5)
    p.add_argument("-o", "--output")
    p.add_argument("--crf", type=int, default=18)

    p = sub.add_parser("pip", help="picture-in-picture")
    p.add_argument("base")
    p.add_argument("overlay")
    p.add_argument("--posicion", default="abajo-derecha",
                   help="abajo-derecha|abajo-izquierda|arriba-derecha|arriba-izquierda|centro")
    p.add_argument("--ancho", type=int, default=320)
    p.add_argument("--hasta", type=float, help="mostrar solo hasta T segundos")
    p.add_argument("-o", "--output")
    p.add_argument("--crf", type=int, default=18)

    p = sub.add_parser("marca-agua", help="logo superpuesto")
    p.add_argument("video")
    p.add_argument("imagen")
    p.add_argument("--posicion", default="abajo-derecha")
    p.add_argument("--opacidad", type=float, default=0.7)
    p.add_argument("-o", "--output")
    p.add_argument("--crf", type=int, default=18)

    p = sub.add_parser("audio", help="operaciones de audio")
    p.add_argument("accion", choices=["extraer", "quitar", "reemplazar"])
    p.add_argument("video")
    p.add_argument("--fuente", help="audio para 'reemplazar'")
    p.add_argument("-o", "--output")

    p = sub.add_parser("gif", help="exporta GIF animado")
    p.add_argument("video")
    p.add_argument("--fps", type=int, default=12)
    p.add_argument("--ancho", type=int, default=480)
    p.add_argument("--inicio", help="inicio del tramo")
    p.add_argument("--duracion", help="duración del tramo")
    p.add_argument("-o", "--output")

    p = sub.add_parser("pase", help="slideshow desde carpeta de imágenes")
    p.add_argument("carpeta")
    p.add_argument("--duracion", type=float, default=3.0, help="segundos por imagen")
    p.add_argument("--zoom", action="store_true", help="efecto Ken Burns sutil")
    p.add_argument("-o", "--output")

    p = sub.add_parser("rotar", help="rota el video")
    p.add_argument("video")
    p.add_argument("--grados", default="90", choices=["90", "180", "270"])
    p.add_argument("-o", "--output")
    p.add_argument("--crf", type=int, default=18)

    p = sub.add_parser("voltear", help="espejo horizontal/vertical")
    p.add_argument("video")
    p.add_argument("--eje", default="horizontal", choices=["horizontal", "vertical"])
    p.add_argument("-o", "--output")
    p.add_argument("--crf", type=int, default=18)

    p = sub.add_parser("bucle", help="repite el video")
    p.add_argument("video")
    p.add_argument("--veces", type=int, default=2, help="repeticiones extra")
    p.add_argument("-o", "--output")

    p = sub.add_parser("escala", help="escala + pad a tamaño exacto")
    p.add_argument("video")
    p.add_argument("--tamano", default="1080x1920", help="ej. 1080x1920")
    p.add_argument("--fondo", default="black", help="color del pad")
    p.add_argument("-o", "--output")
    p.add_argument("--crf", type=int, default=18)

    p = sub.add_parser("color", help="brillo/contraste/saturación")
    p.add_argument("video")
    p.add_argument("--brillo", type=float, default=0.0, help="-1.0 a 1.0")
    p.add_argument("--contraste", type=float, default=1.0)
    p.add_argument("--saturacion", type=float, default=1.0)
    p.add_argument("-o", "--output")
    p.add_argument("--crf", type=int, default=18)

    p = sub.add_parser("velocidad", help="cambia la velocidad (0.25x-4x)")
    p.add_argument("video")
    p.add_argument("--factor", type=float, required=True)
    p.add_argument("-o", "--output")
    p.add_argument("--crf", type=int, default=18)

    p = sub.add_parser("limpiar-audio", help="denoise para voz")
    p.add_argument("video")
    p.add_argument("--fuerza", type=int, default=12, help="0-30, default 12")
    p.add_argument("-o", "--output")
    p.add_argument("--crf", type=int, default=18)

    p = sub.add_parser("chroma", help="chroma key sobre fondo")
    p.add_argument("video")
    p.add_argument("fondo", help="imagen o video de fondo")
    p.add_argument("--color", default="0x00FF00", help="color a remover")
    p.add_argument("--similitud", type=float, default=0.3)
    p.add_argument("--mezcla", type=float, default=0.1)
    p.add_argument("-o", "--output")
    p.add_argument("--crf", type=int, default=18)

    p = sub.add_parser("reversa", help="reproduce al revés")
    p.add_argument("video")
    p.add_argument("-o", "--output")
    p.add_argument("--crf", type=int, default=18)

    add_common(ap)
    a = ap.parse_args()
    apply_common(a)
    {"unir": cmd_unir, "cortar": cmd_cortar, "fundido": cmd_fundido,
     "transicion": cmd_transicion, "pip": cmd_pip, "marca-agua": cmd_marca_agua,
     "audio": cmd_audio, "gif": cmd_gif, "pase": cmd_pase, "rotar": cmd_rotar,
     "voltear": cmd_voltear, "bucle": cmd_bucle, "escala": cmd_escala,
     "color": cmd_color, "velocidad": cmd_velocidad,
     "limpiar-audio": cmd_limpiar_audio, "chroma": cmd_chroma,
     "reversa": cmd_reversa}[a.op](a)


if __name__ == "__main__":
    main()
