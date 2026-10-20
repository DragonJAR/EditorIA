#!/usr/bin/env python3
"""Quema subtitulos SRT/ASS en un video, los muxea como stream blando
(activable), o genera un SRT desde texto plano.

El estilo (fuente, tamano, color, borde, posicion) aplica al input SRT via
force_style de libass. Los ASS traen sus propios estilos y se renderizan
tal cual. Estilo y animacion solo aplican a --mode burn (default):
renderizan pixeles, asi que no tienen sentido para un stream blando.

--mode mux copia video y audio sin tocarlos y agrega el SRT como stream de
subtitulo separado que el reproductor puede activar/desactivar. Solo toma
un SRT plano (--srt, --text o --transcribe), no --ass: el estilo ASS no
tiene equivalente blando entre contenedores. El codec se elige segun el
contenedor: mov_text para .mp4/.m4v/.mov, srt para .mkv, webvtt para .webm.

Formato del input de texto (un cue por linea, lineas vacias ignoradas):
  0:00-0:03 Hola y bienvenidos
  00:00:03.500 --> 00:00:06 Segunda linea | con salto manual
  00:00:03:15 --> 00:00:06:00 Timecode SMPTE non-drop-frame (hh:mm:ss:ff, requiere --fps)
  Texto sin tiempo se auto-tiempea despues del cue anterior (--auto-seconds)

Con --phrase-aware el texto se reagrupa en chunks frase-conscientes: ningun
cue termina en "leader word" (articulos, preposiciones, conjunciones,
posesivos... ES/EN), negacion ("no | funciona") ni cantidad sin su unidad
("30 | segundos"), salvo que esa palabra cierre la oracion; si el chunk
candidato terminaria en una, se encoge para que esa palabra abra el
siguiente caption. Tambien limpia puntuacion (. , ! ? ; : salvo decimales,
% y contracciones) y deja tiempos monotonos.

Con --hablantes (podcast, entrevista) cada hablante lleva su color: el
hablante sale del prefijo del cue ("ANA: hola") o del campo hablante/speaker
de --palabras (WhisperX con diarizacion). Un cue nunca mezcla dos hablantes.

Ejemplos:
  python3 caption.py video.mp4 --srt subs.srt
  python3 caption.py video.mp4 --text cues.txt --animate pop --karaoke
  python3 caption.py video.mp4 --palabras voz.palabras.json --animate pop --karaoke
  python3 caption.py video.mp4 --srt subs.srt --font "DejaVu Sans" --size 28 --position top
  python3 caption.py --text cues.txt --write-srt cues.srt
  python3 caption.py --text cues.txt --write-srt cues.srt --phrase-aware --phrase-words 5
  python3 caption.py video.mp4 --text cues.txt
  python3 caption.py podcast.mp4 --text cues.txt --hablantes "ANA=FFD400,LUIS=4FC3F7" --karaoke
"""
import argparse
import os
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _comun import (STATE, color_hex, load_brand, video_args, add_common, apply_common, emit,
                    aac_args, cfr_args, default_output, die, escape_filter_path, ffmpeg_base,
                    info, leer_palabras, MissingFpsError, parse_time, parse_srt, probe, require_tool, run,
                    transcribir_medio, write_srt, colores_marca)

ALIGN = {"bottom": 2, "top": 8, "center": 5, "bottom-left": 1, "bottom-right": 3,
         "top-left": 7, "top-right": 9}

TIME_RE = re.compile(r"^\s*(?P<a>[\d:.,]+)\s*(?:-->|-|–|to)\s*(?P<b>[\d:.,]+)\s+(?P<text>.+)$")

# "Leader words": articulos, preposiciones, conjunciones, posesivos,
# demostrativos... un chunk frase-consciente nunca termina en una de estas:
# si el candidato terminaria ahi, se encoge para que la palabra abra el
# siguiente caption. Tecnica portada de synced-captions
# (vishalmotionwork-lang/claude-code-windows-setup): solo el heuristico.
LEADERS_ES = frozenset(
    "el la los las lo un una unos unas de del en y o que se su sus mi tu "
    "mis tus este esta estos estas ese esa esos esas aquel aquella al para "
    "con por como pero mas muy sin sobre entre hasta desde".split())
LEADERS_EN = frozenset(
    "the a an of in and or to his her their this that these those my your "
    "our its for with on at from as by".split())
# La negación va con su verbo ("no | funciona" se lee al revés en dos
# pantallas) y una cantidad con su unidad ("30 | segundos"): mismo trato que
# un artículo. Criterio de agrupación de Hypit (hypit-ai/hypit, caption craft).
NEGACIONES = frozenset("no ni nunca jamas not never".split())
LEADERS = LEADERS_ES | LEADERS_EN | NEGACIONES
NUMERO_RE = re.compile(r"\d+(?:[.,]\d+)*")
FIN_FRASE = (".", "!", "?", "…", ";", ":")

PUNCT = "¡!¿?.,;:«»\"'()[]"


def _bare(word):
    """Palabra en minusculas, sin tildes ni puntuacion en los bordes,
    para comparar contra las listas de leader words."""
    w = unicodedata.normalize("NFD", word.lower())
    w = "".join(c for c in w if unicodedata.category(c) != "Mn")
    return re.sub(r"^[^a-z0-9%]+|[^a-z0-9%]+$", "", w)


def _abre_frase(word):
    """True si la palabra no debe cerrar un caption: leader word, negación o
    cantidad (que pide su unidad). Si la propia palabra cierra la oración
    ("...que no." / "...en 2024.") no arrastra nada: puede cerrar."""
    if word.rstrip("»\"')]").endswith(FIN_FRASE):
        return False
    b = _bare(word)
    return b in LEADERS or bool(NUMERO_RE.fullmatch(b))


# Hablante al inicio de un cue: "ANA: hola" o "[ANA]: hola" (nombre en
# mayúsculas, para no confundirlo con "Nota: ..."). Solo se interpreta con
# --hablantes; sin esa opción el texto queda tal cual.
HABLANTE_RE = re.compile(r"^\s*\[?([A-ZÁÉÍÓÚÑÜ][A-ZÁÉÍÓÚÑÜ0-9_]{0,23})\]?:\s+(.+)$", re.S)
PALETA_HABLANTES = ("4FC3F7", "FF6B6B", "7CE38B", "C792EA", "FFB86C")


def separar_hablante(text):
    """'ANA: hola' -> ('ANA', 'hola'); sin prefijo -> (None, text)."""
    m = HABLANTE_RE.match(text)
    return (m.group(1), m.group(2)) if m else (None, text)


def con_hablante(cues):
    """Normaliza cues a (inicio, fin, texto, duraciones|None, hablante): el
    hablante sale del campo propio (palabras.json con speaker) o del prefijo."""
    out = []
    for c in cues:
        hab = c[4] if len(c) > 4 else None
        text = c[2]
        if hab is None:
            hab, text = separar_hablante(text)
        out.append((c[0], c[1], text, c[3] if len(c) > 3 else None, hab))
    return out


def colores_hablantes(spec, cues, acento):
    """--hablantes 'ANA=FFD400,LUIS=4FC3F7' (o 'auto') -> {hablante: RRGGBB}.
    Quien no esté en el mapa recibe el acento de la marca y luego la paleta,
    en orden de aparición; así dos voces nunca comparten color sin quererlo."""
    mapa = {}
    if spec.strip().lower() != "auto":
        for par in spec.split(","):
            nombre, _, col = par.partition("=")
            if not nombre.strip() or not col.strip():
                die(f"--hablantes: '{par}' no es NOMBRE=RRGGBB (o usa --hablantes auto)")
            mapa[nombre.strip().upper()] = color_hex(col.strip())
    libres = [c for c in (acento,) + PALETA_HABLANTES if c not in mapa.values()]
    for c in cues:
        hab = c[4] if len(c) > 4 else None
        if hab and hab.upper() not in mapa:
            mapa[hab.upper()] = libres.pop(0) if libres else acento
    return mapa


def clean_word(word):
    """Quita puntuacion . , ! ? ; : en los bordes. Conserva decimales
    (3.5), porcentajes (100%) y contracciones (don't)."""
    s = word.strip(PUNCT)
    return s or word


def phrase_aware(cues, max_words=6):
    """Reagrupa cues en chunks frase-conscientes de hasta max_words palabras.

    - Ningun chunk termina en leader word, negacion o cantidad (salvo el
      ultimo, o si la palabra cierra la oracion): si el candidato terminaria
      en una, se encoge para que esa palabra abra el siguiente caption
      (minimo 2 palabras/chunk). Un cambio de hablante siempre corta.
    - Limpia puntuacion con clean_word (conserva decimales, % y contracciones).
    - Reparte el tiempo de cada cue entre sus palabras por longitud y deja
      los tiempos monotonos (fin >= inicio + 0.3s, sin solapes).
    """
    words = []  # [palabra cruda, inicio, fin, hablante]
    for c in cues:
        s, e, text = c[:3]
        hab = c[4] if len(c) > 4 else None
        ws = [w for w in text.replace("\n", " ").split() if clean_word(w).strip(PUNCT)]
        if not ws:
            continue
        weights = [max(1, len(clean_word(w))) for w in ws]
        total = sum(weights)
        acc = 0.0
        for w, wt in zip(ws, weights):
            w0 = s + (e - s) * acc / total
            acc += wt
            w1 = s + (e - s) * acc / total
            words.append([w, w0, w1, hab])
    if not words:
        return cues
    # sin tiempos reales: (inicio, fin, texto) como siempre — write_ass mide
    # por energia —, y (.., None, hablante) solo si el cue trae hablante
    return [c[:3] + ((None, c[4]) if c[4] else ()) for c in agrupar_palabras(words, max_words)]


def agrupar_palabras(words, max_words=6):
    """[[palabra, inicio, fin, hablante?]] -> cues frase-conscientes (inicio,
    fin, texto, duraciones_cs, hablante): ningun cue termina en una palabra
    que abre frase (_abre_frase), nunca mezcla hablantes, y los tiempos
    quedan monotonos. duraciones_cs = tiempo de cada palabra hasta la
    siguiente (el \\kf del karaoke), asi el resaltado cae en la silaba real."""
    hab = [w[3] if len(w) > 3 else None for w in words]
    chunks, i, n = [], 0, len(words)
    while i < n:
        j = min(i + max_words, n)
        for k in range(i + 1, j):          # otro hablante = otro caption
            if hab[k] != hab[i]:
                j = k
                break
        while j - i > 2 and j < n and hab[j] == hab[i] and _abre_frase(words[j - 1][0]):
            j -= 1
        chunks.append((words[i:j], hab[i]))
        i = j
    out, prev_end = [], 0.0
    for ch, h in chunks:
        s = max(ch[0][1], prev_end + 0.001)
        e = max(ch[-1][2], s + 0.3)
        inicios = [max(s, w[1]) for w in ch] + [e]
        durs = [max(1, int(round((inicios[k + 1] - inicios[k]) * 100))) for k in range(len(ch))]
        out.append((round(s, 3), round(e, 3), " ".join(clean_word(w[0]) for w in ch), durs, h))
        prev_end = e
    return out


def cues_desde_palabras(path, max_words=6):
    """Tiempos REALES por palabra (cualquier formato de _comun.leer_palabras:
    alinear.py, Whisper/WhisperX, con hablante opcional) -> cues con karaoke
    exacto. Nunca se reparte un cue a partes iguales si hay tiempos reales."""
    words = [[p["texto"], p["inicio"], p["fin"], p["hablante"]] for p in leer_palabras(path)
             if clean_word(p["texto"]).strip(PUNCT)]
    if not words:
        die(f"{path}: no trae palabras con inicio/fin")
    return agrupar_palabras(words, max_words)


def parse_text_cues(path, auto_seconds, gap, fps=None):
    """Convierte el archivo de texto a lista de (inicio, fin, texto)."""
    cues = []
    cursor = 0.0
    # `--text "Hola mundo"` (texto literal) además de `--text cues.txt`: un
    # agente escribe lo primero; antes era un FileNotFoundError crudo
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as fh:
            lineas = fh.read().splitlines(True)
    else:
        lineas = str(path).replace("\\n", "\n").splitlines(True)
    for raw in lineas:
        line = raw.rstrip("\n")
        if not line.strip():
            continue
        m = TIME_RE.match(line)
        if m:
            try:
                start, end = parse_time(m.group("a"), fps), parse_time(m.group("b"), fps)
            except MissingFpsError as e:
                die(f"cue '{line}': {e} -- pasa --fps, o se usa el fps del input si se dio")
            except ValueError:
                start, end, text = cursor, cursor + auto_seconds, line.strip()
            else:
                text = m.group("text").strip()
        else:
            start, end, text = cursor, cursor + auto_seconds, line.strip()
        if end <= start:
            die(f"cue '{line}': el fin debe ser mayor que el inicio")
        text = text.replace(" | ", "\n").replace("|", "\n")
        cues.append((start, end, text))
        cursor = end + gap
    if not cues:
        die(f"no se encontraron cues en {path}")
    return cues


def word_durations_from_audio(video, start, end, n_words, audio_stream=0):
    """Reparte el tiempo de un cue entre n_words segun la energia del habla.
    Decodifica la ventana a 8 kHz mono, arma una envolvente RMS de 10 ms,
    quita el piso de ruido y corta en cuantiles de energia acumulada: las
    pausas no reciben palabras, los tramos fuertes reciben mas tiempo."""
    import struct
    total_cs = max(1, int(round((end - start) * 100)))
    if n_words <= 1:
        return [total_cs]
    ffmpeg = require_tool("ffmpeg")
    cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin",
           "-ss", f"{start:.3f}", "-i", video, "-map", f"0:a:{audio_stream}",
           "-t", f"{end - start:.3f}", "-vn", "-ac", "1", "-ar", "8000", "-f", "s16le", "-"]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    n = len(proc.stdout) // 2
    if proc.returncode != 0 or n < 800:
        per = total_cs // n_words
        return [per] * (n_words - 1) + [total_cs - per * (n_words - 1)]
    samples = struct.unpack(f"<{n}h", proc.stdout[: n * 2])
    step = 80  # 10 ms
    env = []
    for i in range(0, n - step + 1, step):
        block = samples[i:i + step]
        env.append((sum(x * x for x in block) / step) ** 0.5)
    floor = sorted(env)[len(env) // 5]
    energy = [max(0.0, e - floor) for e in env]
    total_e = sum(energy)
    if total_e <= 0:
        per = total_cs // n_words
        return [per] * (n_words - 1) + [total_cs - per * (n_words - 1)]
    bounds = []
    acc, k = 0.0, 1
    for idx, e in enumerate(energy):
        acc += e
        while k < n_words and acc >= total_e * k / n_words:
            bounds.append(idx + 1)
            k += 1
    while len(bounds) < n_words - 1:
        bounds.append(len(energy))
    prev = 0
    out = []
    for b in bounds:
        cs = max(5, int(round((b - prev) * 1.0)))  # bloques de 10 ms -> centisegundos
        out.append(cs)
        prev = b
    out.append(max(5, total_cs - sum(out)))
    scale = total_cs / max(1, sum(out))
    out = [max(5, int(round(x * scale))) for x in out]
    out[-1] += total_cs - sum(out)
    return out


def ass_color(hex_rgb, alpha=0):
    h = str(hex_rgb).lstrip("#")
    if len(h) != 6:
        die(f"el color debe ser hex RRGGBB, recibido '{hex_rgb}'")
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H{alpha:02X}{b}{g}{r}".upper()


def _envolver(ln, font, avail_w):
    """Una línea física → las líneas en que se parte, por palabras completas y
    de ancho parejo (como el wrap inteligente de libass): el MÍNIMO de líneas
    en que CADA una cabe. Una sola medida para encoger (_fit_cue_size) y para
    fijar los saltos (_partir_fijo): nunca prometen líneas distintas."""
    pal = ln.split()
    if not pal or font.getlength(ln) <= avail_w:
        return [ln]

    def en(n):   # n líneas de ancho parejo (cada corte, cerca de su parte)
        restante, lineas = pal, []
        for k in range(n, 1, -1):
            if len(restante) < 2:
                break
            meta = font.getlength(" ".join(restante)) / k
            corte = min(range(1, len(restante)),
                        key=lambda c: abs(font.getlength(" ".join(restante[:c])) - meta))
            lineas.append(" ".join(restante[:corte]))
            restante = restante[corte:]
        return lineas + [" ".join(restante)]
    n = 2
    while n < len(pal) and max(font.getlength(x) for x in en(n)) > avail_w:
        n += 1
    return en(n)


class _FontEst:
    """Estimador proporcional de ancho de fuente cuando PIL no está instalado."""
    def __init__(self, size):
        self.size = size
    def getlength(self, s):
        return len(s) * self.size * 0.56


def _cargar_fuente_medida(font_file, size):
    try:
        from PIL import ImageFont
        if font_file:
            return ImageFont.truetype(font_file, size)
    except Exception:
        pass
    return _FontEst(size)


def _fit_cue_size(text, base_size, min_size, max_lines, avail_w, font_file):
    """Tamano para que el cue quepa en avail_w px y en max_lines lineas.

    Nunca reescribe ni acorta el texto: solo encoge la fuente (cero
    confabulacion). Devuelve (tamano, encogido). Si no hay PIL, usa el
    estimador proporcional _FontEst para conservar el ajuste determinista.
    """
    plain = re.sub(r"\{[^}]*\}", "", text).replace("\\N", "\n")
    size = base_size
    while size > min_size:
        font = _cargar_fuente_medida(font_file, size)
        # líneas REALES (las mismas que fijará _partir_fijo), no ancho/área
        needed = sum(len(_envolver(ln, font, avail_w)) for ln in (plain.split("\n") or [""]))
        # solo una palabra mas ancha que el area es irrompible y fuerza encogido
        too_wide = any(font.getlength(pal) > avail_w for pal in plain.split() if pal.strip())
        if (max_lines and needed > max_lines) or too_wide:
            size -= 2
            continue
        break
    return size, (size < base_size)


def _partir_fijo(text, size, avail_w, font_file):
    """Saltos de línea FIJOS (\\N) medidos con la fuente real (_envolver) o
    con _FontEst si PIL no está disponible. Con {\\q2} libass ya no re-envuelve:
    si la animación escala el texto (pop 80 → 108 %), una línea no salta a 3
    durante un frame."""
    font = _cargar_fuente_medida(font_file, size)
    return "\n".join(x for ln in text.split("\n") for x in _envolver(ln, font, avail_w)), True


def write_ass(cues, path, args, play_w, play_h, video=None):
    """Escribe un ASS estilizado con animacion opcional y resaltado palabra por palabra."""

    def t(sec):
        cs = int(round(sec * 100))
        h, rem = divmod(cs, 360000)
        m, rem = divmod(rem, 6000)
        s_, cs = divmod(rem, 100)
        return f"{h}:{m:02d}:{s_:02d}.{cs:02d}"

    scale = play_h / 288.0
    size = int(round(args.size * scale))
    margin = int(round(args.margin * scale))
    # fit-size: encoger por cue hasta que quepa en el ancho seguro.
    # Nunca reescribe el texto; si no se puede medir, no se encoge.
    font_file = None
    if getattr(args, "max_lines", 2):
        # medir con el MISMO archivo que usará libass: en fonts_dir, el de la
        # familia pedida (la variable empaquetada se llama "Montserrat Thin" y
        # mide más angosta que la Bold estática que libass dibuja)
        if getattr(args, "fonts_dir", None) and os.path.isdir(args.fonts_dir):
            try:
                from PIL import ImageFont
                for f_ in sorted(os.listdir(args.fonts_dir)):
                    if f_.lower().endswith((".ttf", ".otf")):
                        ruta_ = os.path.join(args.fonts_dir, f_)
                        if ImageFont.truetype(ruta_, 12).getname()[0] == args.font:
                            font_file = ruta_
                            break
            except Exception:
                font_file = None
        if not font_file:
            try:
                from _plataforma import resolver_fuente
                font_file = resolver_fuente(args.font)
            except Exception:
                font_file = None
    avail_w = max(50, play_w - 2 * margin)
    fit_min = int(round(args.min_size * scale))
    fit_reducidos = 0
    primary = ass_color(args.highlight_color if args.karaoke else args.color)
    secondary = ass_color(args.color)
    outline = ass_color(args.outline_color)
    back = ass_color(args.outline_color, 0x80)
    header = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {play_w}",
        f"PlayResY: {play_h}", "WrapStyle: 0", "ScaledBorderAndShadow: yes", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
        "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Default,{args.font},{size},{primary},{secondary},{outline},{back},"
        f"{-1 if args.bold else 0},0,0,0,100,100,0,0,{3 if args.box else 1},"
        f"{args.outline * scale:.1f},{args.shadow * scale:.1f},{ALIGN[args.position]},"
        f"{margin},{margin},{margin},1",
    ]
    # un estilo por hablante: el color del hablante es SU acento — el texto
    # entero sin karaoke; con karaoke, la palabra dicha (la base sigue neutra)
    estilos_hab, base = {}, header[-1]
    for i, (hab, col) in enumerate(sorted((getattr(args, "colores_hablantes", None) or {}).items())):
        estilos_hab[hab] = f"H{i}"
        prim, sec = (ass_color(col), secondary) if args.karaoke else (ass_color(col), ass_color(col))
        header.append(base.replace("Style: Default,", f"Style: H{i},", 1)
                      .replace(f",{primary},{secondary},", f",{prim},{sec},", 1))
    header += [
        "", "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    lines = []
    for cue in cues:
        start, end, text = cue[:3]
        reales = cue[3] if len(cue) > 3 else None
        estilo = estilos_hab.get(((cue[4] if len(cue) > 4 else None) or "").upper(), "Default")
        cue_size = size
        if font_file:
            cue_size, encogido = _fit_cue_size(
                text, size, fit_min, args.max_lines, avail_w, font_file)
            if encogido:
                fit_reducidos += 1
        fijo = False
        if font_file and args.animate in ("pop", "slide"):   # escalan o se mueven: saltos fijos
            text, fijo = _partir_fijo(text, cue_size, avail_w, font_file)
        text = text.replace("\n", "\\N")
        fx = "{\\fs%d}" % cue_size if cue_size != size else ""
        if fijo:
            fx += "{\\q2}"
        def fundido(ms_in, ms_out, _start=start, _end=end):
            # alfa con ease-in (\\t con accel 2): \\fad es lineal y arranca a
            # velocidad plena (arranque en la métrica); entrar y salir empiezan suave
            dur_ms = int(round((_end - _start) * 1000))
            return ("\\alpha&HFF&\\t(0,%d,2,\\alpha&H00&)\\t(%d,%d,2,\\alpha&HFF&)"
                    % (ms_in, max(ms_in, dur_ms - ms_out), dur_ms))
        if args.animate == "fade":
            fx += "{%s}" % fundido(200, 200)
        elif args.animate == "pop":
            # pop con punch pero sin aparecer de golpe: 160 ms de fundido, 80 → 108 → 100 %
            # (80 ms y 60 → 110 % lo volcaba entero en 2 frames: pop en la métrica)
            fx += ("{%s\\fscx80\\fscy80\\t(0,160,\\fscx108\\fscy108)"
                   "\\t(160,260,\\fscx100\\fscy100)}" % fundido(160, 120))
        elif args.animate == "slide":
            fx += ("{" + fundido(150, 150) + "\\move(%d,%d,%d,%d,0,250)}"
                  % (play_w // 2, play_h - margin + int(30 * scale),
                     play_w // 2, play_h - margin))
        body = text
        if args.karaoke:
            dur_cs = max(1, int(round((end - start) * 100)))
            segments = body.split("\\N")
            words = [w for seg in segments for w in seg.split(" ") if w]
            if reales and len(reales) == len(words):
                durs = reales
            elif getattr(args, "karaoke_timing", "even") == "energy" and video:
                durs = word_durations_from_audio(video, start, end, len(words),
                                                getattr(args, "audio_stream", 0))
            else:
                per = max(1, dur_cs // max(1, len(words)))
                durs = [per] * len(words)
            it = iter(durs)
            out_segments = []
            for seg in segments:
                ws = [w for w in seg.split(" ") if w]
                out_segments.append(" ".join(f"{{\\kf{next(it)}}}{w}" for w in ws))
            body = "\\N".join(out_segments)
        lines.append(f"Dialogue: 0,{t(start)},{t(end)},{estilo},,0,0,0,,{fx}{body}")
    with open(path, "w", encoding="utf-8-sig") as fh:
        fh.write("\n".join(header + lines) + "\n")
    if fit_reducidos:
        info(f"fit-size: {fit_reducidos} cue(s) encogidos para caber en "
             f"{args.max_lines} lineas (minimo {args.min_size}); texto intacto")
    return fit_reducidos


def mux_subtitle_codec(output):
    ext = Path(output).suffix.lower()
    if ext in (".mp4", ".m4v", ".mov"):
        return "mov_text"
    if ext == ".mkv":
        return "srt"
    if ext == ".webm":
        return "webvtt"
    die(f"--mode mux: no conozco un codec de subtitulo blando para salida '{ext}' "
        "(conozco .mp4/.m4v/.mov, .mkv, .webm) -- usa --mode burn o uno de esos contenedores con -o")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", nargs="?",
                    help="video al que quemar los subtitulos (omitelo con --write-srt para solo generar)")
    ap.add_argument("-o", "--output", help="video de salida (default: <nombre>_captioned.<ext>)")
    ap.add_argument("--mode", choices=["burn", "mux"], default="burn",
                    help="'burn' renderiza los subtitulos en la imagen (default); "
                         "'mux' copia video/audio y agrega el SRT como stream blando activable")
    ap.add_argument("--audio-stream", type=int, default=0,
                    help="que stream de audio del input conservar, 0-based en orden de archivo "
                         "(default 0, el primero)")
    src = ap.add_argument_group("fuente de subtitulos")
    src.add_argument("--srt", help="archivo SRT a quemar")
    src.add_argument("--ass", help="archivo ASS a quemar (se usan los estilos del archivo)")
    src.add_argument("--text", help="archivo de texto con cues (o el texto mismo entre comillas; \\n separa cues) para convertir a SRT (formato arriba)")
    src.add_argument("--palabras", help="JSON de tiempos por palabra (scripts/alinear.py): "
                     "cues frase-conscientes y karaoke con el tiempo REAL de cada palabra")
    src.add_argument("--transcribe", action="store_true",
                     help="genera el SRT desde el audio con un motor local de voz-a-texto si hay uno "
                          "instalado (whisper-cli / whisper / faster-whisper); nunca es requerido")
    src.add_argument("--language", help="codigo de idioma para --transcribe (ej. es, en; default auto)")
    src.add_argument("--model", default="base",
                     help="modelo de whisper para --transcribe (default base)")
    src.add_argument("--write-srt", help="donde guardar el SRT generado (default: <texto>.srt)")
    src.add_argument("--auto-seconds", type=float, default=3.0,
                     help="duracion para cues sin tiempo (default 3)")
    src.add_argument("--gap", type=float, default=0.0,
                     help="pausa despues de cues auto-tiempeados en segundos")
    src.add_argument("--fps", type=float, default=None,
                     help="fps para interpretar timecodes SMPTE hh:mm:ss:ff en --text; "
                          "default: el fps del video si se dio input, requerido si no")
    sty = ap.add_argument_group("estilo (solo SRT)")
    sty.add_argument("--brand", help="brand.json: fuente, colores, defaults de subtitulos")
    sty.add_argument("--font", default=None, help="familia de fuente (default: la de la marca, o Montserrat empaquetada en assets/fonts)")
    sty.add_argument("--fonts-dir", help="directorio con fuentes extra .ttf/.otf")
    sty.add_argument("--size", type=int, default=None,
                     help="tamano de fuente en puntos ASS (relativo a un script de 288p, escala solo)")
    sty.add_argument("--color", default=None, help="color del texto RRGGBB (default FFFFFF)")
    sty.add_argument("--outline-color", default=None, help="color del borde RRGGBB")
    sty.add_argument("--outline", type=float, default=None, help="grosor del borde (default 2)")
    sty.add_argument("--shadow", type=float, default=0.0, help="profundidad de sombra (default 0)")
    sty.add_argument("--bold", action="store_true", help="negrita")
    sty.add_argument("--position", choices=sorted(ALIGN), default=None,
                     help="posicion en pantalla (default bottom)")
    sty.add_argument("--margin", type=int, default=30,
                     help="margen vertical desde el borde (default 30)")
    sty.add_argument("--box", action="store_true",
                     help="dibuja una caja opaca detras del texto en vez de borde")
    sty.add_argument("--max-lines", type=int, default=2,
                     help="maximo de lineas por cue: si un cue no cabe, se encoge "
                     "la fuente (nunca se reescribe el texto); 0 = sin limite")
    sty.add_argument("--min-size", type=int, default=14,
                     help="tamano minimo al encoger un cue para que quepa (default 14)")
    anim = ap.add_argument_group("animacion (genera ASS; requiere --text o --srt)")
    anim.add_argument("--animate", choices=["none", "fade", "pop", "slide"], default=None,
                      help="animacion de entrada por cue (default none)")
    anim.add_argument("--karaoke", action="store_true",
                      help="resaltado palabra por palabra (va de --color a --highlight-color en cada cue)")
    anim.add_argument("--highlight-color", default=None,
                      help="color de relleno del karaoke RRGGBB (default FFD200)")
    anim.add_argument("--karaoke-timing", choices=["even", "energy"], default="energy",
                      help="como tiempear las palabras dentro del cue: 'energy' sigue la sonoridad "
                           "del audio (default), 'even' reparte el tiempo por igual")
    anim.add_argument("--write-ass", help="donde guardar el ASS generado (default: junto al output)")
    anim.add_argument("--hablantes", default=None,
                      help="color por hablante (podcast, entrevista): 'ANA=FFD400,LUIS=4FC3F7' o 'auto'. "
                           "El hablante sale del prefijo del cue ('ANA: hola') o del campo "
                           "hablante/speaker de --palabras; con --karaoke colorea la palabra dicha"),
    phr = ap.add_argument_group("fraseo (reagrupa el texto en cues)")
    phr.add_argument("--phrase-aware", action="store_true",
                     help="agrupacion frase-consciente: ningun cue termina en leader word "
                          "(articulos, preposiciones, conjunciones, posesivos... ES/EN); "
                          "si el chunk candidato terminaria en una, se encoge para que esa "
                          "palabra abra el siguiente caption. Limpia puntuacion y deja "
                          "tiempos monotonos")
    phr.add_argument("--phrase-words", type=int, default=6,
                     help="maximo de palabras por cue con --phrase-aware (default 6)")
    enc = ap.add_argument_group("codificacion")
    enc.add_argument("--crf", type=int, default=18, help="CRF de x264 (default 18)")
    enc.add_argument("--preset", default="medium", help="preset de x264 (default medium)")
    add_common(ap)
    args = ap.parse_args()
    apply_common(args)

    brand = load_brand(args.brand)
    bc, bcap = brand["colors"], brand["caption"]
    # sin marca ni --font: la tipografía EMPAQUETADA del kit (la misma de las
    # escenas de render_plan), no la de sistema: un subtítulo en DejaVu sobre
    # un video en Montserrat se ve pegado encima
    # (assets/fonts/Montserrat-Bold.ttf: instancia estática; libass no lee el eje wght)
    from _plataforma import FUENTES_SKILL
    if not args.font and not args.brand and (FUENTES_SKILL / "Montserrat-Bold.ttf").exists():
        args.font, args.fonts_dir = "Montserrat", args.fonts_dir or str(FUENTES_SKILL)
    args.font = args.font or brand.get("font") or "DejaVu Sans"
    if not args.fonts_dir and brand.get("fonts_dir"):
        args.fonts_dir = os.path.expanduser(brand["fonts_dir"])
    args.size = args.size if args.size is not None else (bcap.get("size", 24) if args.brand else 24)
    args.color = color_hex(args.color or bc.get("text", "FFFFFF"))
    args.outline_color = color_hex(args.outline_color or bc.get("outline", "000000"))
    args.outline = args.outline if args.outline is not None else (float(bcap.get("outline", 2)) if args.brand else 2.0)
    args.position = args.position or (bcap.get("position", "bottom") if args.brand else "bottom")
    args.animate = args.animate or (bcap.get("animate", "none") if args.brand else "none")
    # el acento del pack (colores.acento o colors.primary, vía colores_marca);
    # sin pack, el acento NEUTRO del kit: el mismo de las escenas (el amarillo
    # FFD200 de antes no era de ningún sistema visual del video)
    args.highlight_color = color_hex(args.highlight_color or "%02X%02X%02X" % colores_marca(args.brand)["acento"])
    if args.brand and bcap.get("bold") and not args.bold:
        args.bold = True
    if args.brand and bcap.get("karaoke") and not args.karaoke:
        args.karaoke = True

    if not (args.srt or args.ass or args.text or args.transcribe or args.palabras):
        die("da una fuente: --srt, --ass, --text, --palabras o --transcribe")
    if args.mode == "mux":
        if args.ass:
            die("--mode mux toma --srt (o --text/--transcribe), no --ass -- "
                "el estilo ASS es solo para quemar; usa --mode burn para un ASS")
        if args.animate != "none" or args.karaoke or args.hablantes:
            die("--animate/--karaoke/--hablantes renderizan pixeles y requieren --mode burn")

    meta = None
    if args.input:
        meta = probe(args.input)
        if not meta.get("video"):
            die("el input no tiene stream de video")
        audio_streams = meta.get("audio_streams") or []
        if audio_streams and not (0 <= args.audio_stream < len(audio_streams)):
            die(f"--audio-stream {args.audio_stream}: el input tiene {len(audio_streams)} "
                f"stream(s) de audio, 0..{len(audio_streams) - 1}")
    fps_for_tc = args.fps
    if fps_for_tc is None and meta is not None:
        fps_for_tc = meta.get("video", {}).get("fps")

    cues = None
    srt_path = args.srt
    if args.transcribe:
        if not args.input:
            die("--transcribe necesita el video de input")
        srt_path = args.write_srt or os.path.splitext(args.input)[0] + ".srt"
        cues = transcribir_medio(args.input, srt_path, args.language, args.model, args.audio_stream)
        info(f"escribi {srt_path} ({len(cues)} cues)")
        args.text = None
    if args.text or args.palabras:
        if args.palabras:
            cues = cues_desde_palabras(args.palabras, args.phrase_words)
            info(f"{len(cues)} cues desde tiempos reales por palabra")
        else:
            cues = parse_text_cues(args.text, args.auto_seconds, args.gap, fps_for_tc)
        if args.hablantes:
            cues = con_hablante(cues)
        if args.phrase_aware and not args.palabras:
            cues = phrase_aware(cues, max_words=args.phrase_words)
            info(f"reagrupados a {len(cues)} cues frase-conscientes "
                 f"(max {args.phrase_words} palabras)")
        if args.write_srt:
            srt_path = args.write_srt
        elif args.input:
            out_guess = args.output or default_output(args.input, "captioned")
            srt_path = os.path.splitext(out_guess)[0] + ".srt"
        else:
            srt_path = os.path.splitext(args.text or args.palabras)[0] + ".srt"
        if not STATE.dry_run:
            # con --hablantes el SRT conserva "ANA: ..." (releerlo restaura el color)
            write_srt([c[:2] + ((f"{c[4]}: " if args.hablantes and len(c) > 4 and c[4] else "") + c[2],)
                       for c in cues], srt_path)
        info(f"escribi {srt_path} ({len(cues)} cues)")
        if not args.input:
            print(f"OK {srt_path}")
            return 0

    if not args.input:
        die("el video de input es requerido salvo que solo uses --text/--write-srt")

    output = args.output or default_output(args.input, "captioned")

    if args.mode == "mux":
        if not srt_path or (not os.path.exists(srt_path) and not (STATE.dry_run and args.text)):
            die(f"archivo SRT no encontrado: {srt_path}")
        codec = mux_subtitle_codec(output)
        existing_subs = meta.get("subtitle_streams") or 0
        cmd = ffmpeg_base() + ["-i", args.input, "-i", srt_path]
        maps = ["-map", "0:v:0"]
        if meta.get("audio"):
            maps += ["-map", f"0:a:{args.audio_stream}"]
        if existing_subs:
            maps += ["-map", "0:s?"]
        maps += ["-map", "1:0"]
        cmd += maps + ["-c:v", "copy"] + (["-c:a", "copy"] if meta.get("audio") else [])
        for i in range(existing_subs):
            cmd += [f"-c:s:{i}", "copy"]
        cmd += [f"-c:s:{existing_subs}", codec]
        if args.language:
            cmd += [f"-metadata:s:s:{existing_subs}", f"language={args.language}"]
        cmd += [output]
        run(cmd)
        result = probe(output, role="output")
        info(f"escribi {output} ({result.get('duration'):.3f}s, mux, codec {codec})")
        if args.json:
            emit(output)
        else:
            print(f"OK {output}")
        return 0

    fit_n = 0
    if (args.animate != "none" or args.karaoke or args.hablantes) and not args.ass:
        cues_for_ass = cues if (args.text or args.palabras) else parse_srt(srt_path)
        if args.hablantes:
            cues_for_ass = con_hablante(cues_for_ass)
            args.colores_hablantes = colores_hablantes(args.hablantes, cues_for_ass, args.highlight_color)
            info("hablantes: " + ", ".join(f"{h}={c}" for h, c in args.colores_hablantes.items()))
        if args.phrase_aware and not (args.text or args.palabras):
            cues_for_ass = phrase_aware(cues_for_ass, max_words=args.phrase_words)
        ass_path = args.write_ass or os.path.splitext(output)[0] + ".ass"
        w, h = meta["video"]["width"], meta["video"]["height"]
        if meta["video"].get("rotation") in (90, -90, 270, -270):
            w, h = h, w
        fit_n = write_ass(cues_for_ass, ass_path, args, w, h,
                          video=args.input if meta.get("audio") else None) or 0
        info(f"escribi {ass_path} ({len(cues_for_ass)} cues, animate={args.animate}, karaoke={args.karaoke})")
        args.ass = ass_path

    if args.ass:
        if not os.path.exists(args.ass):
            die(f"archivo ASS no encontrado: {args.ass}")
        vf = f"ass={escape_filter_path(args.ass)}"
        if args.fonts_dir:
            vf += f":fontsdir={escape_filter_path(args.fonts_dir)}"
    else:
        if not srt_path or (not os.path.exists(srt_path) and not (STATE.dry_run and args.text)):
            die(f"archivo SRT no encontrado: {srt_path}")
        style = [
            f"FontName={args.font}",
            f"FontSize={args.size}",
            f"PrimaryColour={ass_color(args.color)}",
            f"OutlineColour={ass_color(args.outline_color)}",
            f"BackColour={ass_color(args.outline_color, 0x80)}",
            f"BorderStyle={3 if args.box else 1}",
            f"Outline={args.outline:g}",
            f"Shadow={args.shadow:g}",
            f"Bold={-1 if args.bold else 0}",
            f"Alignment={ALIGN[args.position]}",
            f"MarginV={args.margin}",
        ]
        force = ",".join(style).replace("\\", "\\\\").replace("'", "\\'")
        vf = f"subtitles={escape_filter_path(srt_path)}:force_style='{force}'"
        if args.fonts_dir:
            vf += f":fontsdir={escape_filter_path(args.fonts_dir)}"

    cmd = ffmpeg_base() + ["-i", args.input, "-map", "0:v:0"]
    if meta.get("audio"):
        cmd += ["-map", f"0:a:{args.audio_stream}"]
    cmd += ["-vf", vf] + video_args(meta, args.crf, args.preset) + cfr_args(meta)
    cmd += (aac_args() if meta.get("audio") else ["-an"]) + [output]
    run(cmd)
    result = probe(output, role="output")
    info(f"escribi {output} ({result.get('duration'):.3f}s)")
    if args.json:
        emit(output, cues_encogidos=fit_n)
    else:
        print(f"OK {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
