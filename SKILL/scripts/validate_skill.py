#!/usr/bin/env python3
"""Validador determinista del skill EditorIA.
Verifica: frontmatter válido, name == carpeta, archivos requeridos,
referencias enlazadas existen (en SKILL.md y en toda referencia),
scripts enlazados existen, sin archivos huérfanos, sin README.md,
sin angle brackets en frontmatter ni markdown, SKILL.md < 5000 palabras,
TODOS los scripts compilan y las 13 escenas renderizan.
Sale 0 si todo pasa, 1 si algo falla.
"""
import os, sys, re, ast, glob, json, subprocess, tempfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fails = []
def check(cond, msg):
    print(("OK  " if cond else "FAIL") + " " + msg)
    if not cond: fails.append(msg)

# 1. frontmatter
sk = open(os.path.join(BASE, "SKILL.md"), encoding="utf-8").read()
m = re.match(r"^---\n(.*?)\n---\n", sk, re.S)
check(bool(m), "frontmatter presente")
fm = m.group(1) if m else ""
check("name:" in fm, "frontmatter tiene name")
name = re.search(r"name:\s*(\S+)", fm)
if name and name.group(1) == os.path.basename(BASE):
    check(True, f"name == carpeta ({name.group(1)})")
elif name and os.path.basename(BASE) == "SKILL":
    # Layout de repositorio: la skill vive en SKILL/ y se instala con su nombre.
    print(f"AVISO name '{name.group(1)}' != carpeta 'SKILL' (layout del repo): "
          f"al instalar, copiar como ~/.claude/skills/{name.group(1)}/")
else:
    check(False, f"name == carpeta ({name.group(1) if name else '?'})")
check(name and "claude" not in name.group(1) and "anthropic" not in name.group(1),
      "name sin 'claude'/'anthropic' (reservados)")
desc = re.search(r"description:\s*(.*)", fm)
check(bool(desc), "frontmatter tiene description")
check(desc and len(desc.group(1)) < 1024,
      f"description < 1024 chars ({len(desc.group(1)) if desc else '?'})")
check(desc and ("cuando" in desc.group(1).lower() or "use when" in desc.group(1).lower()),
      "description incluye WHEN (condición de uso)")
check(not re.search(r"<[^/!][^>]*>", fm), "sin angle brackets en frontmatter")
# guía: sin XML tags en ningún .md del skill (los placeholders usan {…})
md_files = [os.path.join(BASE, "SKILL.md")] + \
    [os.path.join(BASE, "references", f) for f in os.listdir(os.path.join(BASE, "references"))
     if f.endswith(".md")]
bad_tags = []
for mf in md_files:
    for i, line in enumerate(open(mf, encoding="utf-8"), 1):
        if re.search(r"<[A-Za-z/!][^>]*>", line):
            bad_tags.append(f"{os.path.basename(mf)}:{i}")
check(not bad_tags, f"sin angle brackets en markdown ({len(bad_tags)} hallados)")
for b in bad_tags[:5]:
    print("      ", b)
check(len(sk.split()) < 5000, f"SKILL.md < 5000 palabras ({len(sk.split())})")
# autoría única: el autor del frontmatter es el de la LICENSE; ningún archivo
# de la skill lleva atribuciones de terceros (agentes, co-autores, "generado con")
lic = open(os.path.join(os.path.dirname(BASE), "LICENSE"), encoding="utf-8").read() \
    if os.path.exists(os.path.join(os.path.dirname(BASE), "LICENSE")) else ""
autor = re.search(r'"author":\s*"([^"]+)"', fm)
check(bool(autor) and (not lic or autor.group(1) in lic),
      f"author del frontmatter = titular de la LICENSE ({autor.group(1) if autor else '?'})")
ajenas = []
for dp, dn, fn in os.walk(BASE):
    if "__pycache__" in dp:
        continue
    for f in fn:
        if f.endswith((".md", ".py", ".json")) and f != "validate_skill.py":
            txt = open(os.path.join(dp, f), encoding="utf-8", errors="ignore").read()
            if re.search(r"co-authored-by|generated with|generado con claude|\bmuse\b", txt, re.I):
                ajenas.append(os.path.relpath(os.path.join(dp, f), BASE))
check(not ajenas, f"sin atribuciones de terceros ({', '.join(ajenas) or 'ninguna'})")
# marca blanca: ninguna marca concreta vive en el código; los packs solo en brand/
packs = glob.glob(os.path.join(BASE, "brand", "*.json"))
check(bool(packs), f"al menos un brand pack de ejemplo en brand/ ({len(packs)})")
marcas = [os.path.splitext(os.path.basename(x))[0] for x in packs]
colores = []
for x in packs:
    c = (json.load(open(x, encoding="utf-8")).get("colores") or {}).get("acento")
    if isinstance(c, str):
        colores.append(c.lstrip("#"))
literal = re.compile("|".join(re.escape(m) for m in marcas + colores) or r"$^", re.I)
quemadas = []
for dp, dn, fn in os.walk(os.path.join(BASE, "scripts")):
    for f in fn:
        if f.endswith((".py", ".json")):
            if literal.search(open(os.path.join(dp, f), encoding="utf-8", errors="ignore").read()):
                quemadas.append(f)
check(not quemadas, f"sin marcas quemadas en scripts/ ({', '.join(quemadas) or 'ninguna'})")

# 2. archivos requeridos
req = ["SKILL.md", "references/brand-packs.md", "references/estilos.md",
       "references/pipeline-resumen.md", "references/checklist-qa.md",
       "references/reglas-tecnicas.md", "references/plan-video.md",
       "references/escenas.md", "references/fluidez.md",
       "references/coherencia-espacial.md", "references/cine.md",
       "references/arquitectura.md", "references/principios.md",
       "references/tecnicas-reutilizables.md",
       "references/capacidades.md", "references/sonido.md",
       "references/ritmo.md", "references/video-real.md",
       "references/modos-produccion.md", "references/modos-rapidos.md",
       "references/scoring-shorts.md", "references/audio.md",
       "references/direccion.md", "references/thumbnails.md",
       "references/tecnicas-video.md",
       "scripts/render_plan.py", "scripts/voz_off.py", "scripts/musica.py",
       "scripts/film_marca.py", "scripts/film_marca_v2.py",
       "scripts/check_env.py", "scripts/beat_grid.py",
       "scripts/medir_mezcla.py", "scripts/retakes.py",
       "scripts/audio_viz.py", "scripts/auditar_plan.py",
       "scripts/verificar_ritmo.py", "scripts/sfx.py", "scripts/auto_qa.py",
       "scripts/poster_frame.py", "references/remotion.md",
       "references/hyperframes.md", "references/instalacion.md",
       "references/dramaturgia.md", "references/auto-qa.md",
       "references/montaje.md",
       "scripts/ffmpeg_tools/_plataforma.py",
       "scripts/ffmpeg_tools/_comun.py", "scripts/ffmpeg_tools/silence.py",
       "scripts/ffmpeg_tools/loudness.py", "scripts/ffmpeg_tools/scenes.py",
       "scripts/ffmpeg_tools/speedramp.py", "scripts/ffmpeg_tools/look.py",
       "scripts/ffmpeg_tools/caption.py", "scripts/ffmpeg_tools/transcribir.py",
       "scripts/ffmpeg_tools/aplicar_edl.py", "scripts/ffmpeg_tools/shorts_plan.py",
       "scripts/ffmpeg_tools/thumbnail.py", "scripts/ffmpeg_tools/verticalizar.py",
       "scripts/ffmpeg_tools/grade.py", "scripts/ffmpeg_tools/variantes.py",
       "scripts/ffmpeg_tools/artesanal.py",
       "scripts/ffmpeg_tools/montaje.py",
       "scripts/beat_sync.py", "scripts/chapters.py",
       "references/shorts-plan-schema.md",
       "scripts/demo_plan.json", "scripts/validate_skill.py"]
for f in req:
    check(os.path.exists(os.path.join(BASE, f)), f"existe {f}")
check(not os.path.exists(os.path.join(BASE, "README.md")), "sin README.md")

# 3. referencias enlazadas existen (en SKILL.md y en toda referencia)
all_md = [os.path.join(BASE, "SKILL.md")] + \
    [os.path.join(BASE, "references", f) for f in os.listdir(os.path.join(BASE, "references"))
     if f.endswith(".md")]
corpus = "\n".join(open(mf, encoding="utf-8").read() for mf in all_md)
mencionadas = set(re.findall(r"references/([\w\-.]+\.(?:md|json))", corpus))
for r in sorted(mencionadas):
    check(os.path.exists(os.path.join(BASE, "references", r)),
          f"referencia enlazada existe: references/{r}")
scripts_mencionados = set(re.findall(r"scripts/([\w\-./]+\.py)", corpus))
for s in sorted(scripts_mencionados):
    check(os.path.exists(os.path.join(BASE, "scripts", s)),
          f"script enlazado existe: scripts/{s}")

# 3b. sin huérfanos: todo archivo del skill debe ser encontrable desde algún .md
mencionados_todos = set(re.findall(r"(?:references|scripts|film|demo)/[\w\-./]+\.(?:md|json|py|mp4|mp3|png)", corpus))
huerfanos = []
for dp, dn, fn in os.walk(BASE):
    if "__pycache__" in dp:
        continue
    for f in fn:
        p = os.path.relpath(os.path.join(dp, f), BASE)
        if not (p.startswith("references/") or p.startswith("scripts/")
                or p.startswith("film/") or p.startswith("demo/")):
            continue
        if not p.endswith((".md", ".json", ".py", ".mp4", ".mp3", ".png")):
            continue
        if p not in mencionados_todos and p != "scripts/validate_skill.py":
            huerfanos.append(p)
check(not huerfanos, f"sin archivos huérfanos ({len(huerfanos)})")
for h in huerfanos[:8]:
    print("      huérfano:", h)

# 4. TODOS los scripts compilan
sys.path.insert(0, os.path.join(BASE, "scripts"))
n_py = 0
for dp, dn, fn in os.walk(os.path.join(BASE, "scripts")):
    if "__pycache__" in dp:
        continue
    for f in sorted(fn):
        if not f.endswith(".py"):
            continue
        n_py += 1
        p = os.path.join(dp, f)
        rel = os.path.relpath(p, BASE)
        try:
            ast.parse(open(p, encoding="utf-8").read())
            check(True, f"compila {rel}")
        except SyntaxError as e:
            check(False, f"compila {rel}: {e}")
check(n_py > 0, f"scripts compilados: {n_py}")

# 5. las N escenas renderizan con su muestra realista (escenas_muestra.json)
#    en 9:16 y 16:9, compuestas DENTRO de la zona segura (sin que escala_segura las encoja)
try:
    import numpy as _np
    import render_plan as R
    n_total = len(R.SCENES)
    # muestras realistas: fuente única con galeria.py (scripts/escenas_muestra.json)
    muestras = json.load(open(os.path.join(BASE, "scripts", "escenas_muestra.json"),
                              encoding="utf-8"))["escenas"]
    sin_muestra = sorted(set(R.SCENES) - set(muestras))
    check(not sin_muestra, f"cada escena tiene muestra en escenas_muestra.json "
                           f"({', '.join(sin_muestra) or 'todas'})")
    sobran = sorted(set(muestras) - set(R.SCENES))
    check(not sobran, f"escenas_muestra.json sin tipos inexistentes ({', '.join(sobran) or 'ninguno'})")
    # 9:16 y 16:9: toda escena funciona en los dos formatos
    for ancho, alto in ((1080, 1920), (1920, 1080)):
        R.formato(ancho, alto)
        ctx = R.Ctx()
        fuera, escenas_ok = [], 0
        for nombre, fn in R.SCENES.items():
            e = dict(muestras.get(nombre, {"from": 0, "to": 5, "at": {}}), tipo=nombre)
            try:
                # además de 3 instantes, CADA entrada del plan (at + 0/16/33/100 ms):
                # ahí los resortes son diminutos y nacen las geometrías inválidas
                ats = []
                def _ats(nodo, clave=""):
                    if isinstance(nodo, dict):
                        for k_, v_ in nodo.items():
                            _ats(v_, k_)
                    elif isinstance(nodo, list):
                        for v_ in nodo:
                            _ats(v_, clave)
                    elif isinstance(nodo, (int, float)) and clave in ("at", "palabras") or \
                            (isinstance(nodo, (int, float)) and clave.startswith(("item", "bar", "card"))):
                        ats.append(float(nodo))
                _ats(e.get("at", {}), "at")
                _ats([m_.get("at") for m_ in (e.get("mensajes", []) + e.get("pasos", []) + e.get("items", [])
                                              + e.get("canales", []) + e.get("notificaciones", []))
                      if isinstance(m_, dict) and m_.get("at") is not None], "at")
                tiempos = {0.5, e["to"] / 2, e["to"] - 0.3}
                tiempos |= {a_ + d_ for a_ in ats for d_ in (0.0, 0.016, 0.033, 0.1) if 0 <= a_ + d_ < e["to"]}
                for t in sorted(tiempos):
                    fn(ctx, e, t)
                if nombre == "chat":   # sin `at`: tiempos derivados + escribiendo
                    fn(ctx, dict(e, mensajes=[{"de": "cliente", "texto": "Hola"},
                                              {"de": "ia", "texto": "Listo"}] * 4), 4.0)
                R._ESCALA.clear()
                f = R.escala_segura(ctx, e, 0)
                # escala_segura es la red (encoge hasta x0.70); bajo x0.75 el diseño
                # ignora la zona segura y en el tope el contenido queda bajo la UI
                if f < 0.75:
                    fuera.append(f"{nombre} x{f:.2f}")
                escenas_ok += 1
            except Exception as ex:
                check(False, f"escena {nombre} {ancho}x{alto}: {type(ex).__name__}: {ex}")
        check(escenas_ok == n_total,
              f"{ancho}x{alto}: {n_total}/{n_total} escenas renderizan ({escenas_ok}/{n_total})")
        check(not fuera, f"{ancho}x{alto}: muestras caben en la zona segura sin encogerse "
                         f"bajo x0.75 ({', '.join(fuera) or 'todas'})")
        # fondo vivo: en el hold asentado la imagen cambia lo que auto_qa exige
        # (mismo umbral, mismo ancho de análisis): ningún plano queda congelado
        import auto_qa as _QA
        from PIL import Image as _Im
        foto = os.path.join(tempfile.mkdtemp(prefix="editoria_foto_"), "foto.png")
        _Im.linear_gradient("L").resize((1600, 1200)).convert("RGB").save(foto)
        congeladas = []
        for nombre in sorted(set(R.SCENES) - R.QUIETAS):
            e = dict(muestras[nombre], tipo=nombre)
            if "imagen" in e:
                e["imagen"] = foto
            R._ESCALA.clear()
            dt = 1 / _QA.FPS_MUESTREO

            def _vivo(t0):   # dos pares: congelado = TODO el tramo quieto
                difs = []
                for ta in (t0, t0 + 2 * dt):
                    fr = [R.componer(ctx, [e], e["to"], t, set()).convert("L")
                          .resize((_QA.ANCHO, int(_QA.ANCHO * alto / ancho))) for t in (ta, ta + dt)]
                    difs.append(float(_np.abs(_np.asarray(fr[0], _np.int16)
                                              - _np.asarray(fr[1], _np.int16)).mean()))
                return max(difs)
            # a media escena y en el último hold antes de la salida (donde todo ya asentó)
            dif = min(_vivo(e["to"] * 0.55), _vivo(e["to"] - 0.6 - 3 * dt))
            if dif < _QA.FROZEN_DIFF:
                congeladas.append(f"{nombre} {dif:.2f}")
        check(not congeladas, f"{ancho}x{alto}: ningún hold congelado (umbral auto_qa "
                              f"{_QA.FROZEN_DIFF}) ({', '.join(congeladas) or 'todos vivos'})")
    R.formato(1080, 1920)
    ctx = R.Ctx()
    # cifras: los intermedios llevan los decimales del valor final (nunca 3.4999…)
    cu = [R.cuenta_up(0, 3.5, 0.3, 0), R.cuenta_up(0, 3.5, 9, 0), R.cuenta_up(0, 1500, 9, 0)]
    check(cu[1] == "3.5" and len(cu[0]) == 3 and cu[2] == "1,500", f"cuenta_up con decimales ({cu})")
except Exception as ex:
    check(False, f"smoke test escenas: {ex}")

# 6. nuevos módulos de post-producción (smoke tests con datos sintéticos)
sys.path.insert(0, os.path.join(BASE, "scripts", "ffmpeg_tools"))
try:
    import beat_sync as BS
    beats, bd = BS.beats_hasta({"bpm": 120.0, "beat0": 0.25}, 5.0)
    check(abs(bd - 0.5) < 1e-9 and abs(beats[0] - 0.25) < 1e-9, "beat_sync: rejilla 120 BPM")
    ta, b, d = BS.ajustar(0.30, beats, 0.125)
    check(b == 0.25 and ta == 0.25, "beat_sync: ajuste al beat cercano")
    ta2, b2, _ = BS.ajustar(2.0, beats, 0.01)
    check(b2 is None and ta2 == 2.0, "beat_sync: fuera de ventana queda intacto")
except Exception as ex:
    check(False, f"smoke beat_sync: {ex}")

try:
    import chapters as CH
    check(CH.fmt_tiempo(65) == "01:05", "chapters: fmt 65s")
    check(CH.fmt_tiempo(3661) == "1:01:01", "chapters: fmt con horas")
    caps = CH.capitulos_desde_plan({"escenas": [
        {"tipo": "apertura", "from": 0, "titulo": "Intro"},
        {"tipo": "chat", "from": 65}]})
    check(caps == [(0.0, "Intro"), (65.0, "Chat")], "chapters: desde plan")
    caps2 = CH.capitulos_desde_shorts({"segmentos": [
        {"id": "hook", "from": 10.0, "to": 13.0},
        {"id": "cuerpo", "from": 40.0, "to": 46.0, "titulo": "El dato"}]})
    # timeline de SALIDA (concatenado en orden de archivo), no from de la fuente
    check(caps2 == [(0.0, "Hook"), (3.0, "El dato")],
          "chapters: desde shorts-plan (timeline acumulativo)")
except Exception as ex:
    check(False, f"smoke chapters: {ex}")

try:
    import aplicar_edl as AE
    edl_tmp = os.path.join(tempfile.gettempdir(), "editoria_val_edl.txt")
    open(edl_tmp, "w", encoding="utf-8").write("5.000-7.000\n# comentario\n1.000-3.000\n2.500-4.000\n\n")
    segs = AE.leer_edl(edl_tmp)
    check(segs == [(1.0, 4.0), (5.0, 7.0)], f"aplicar_edl: ordena y fusiona ({segs})")
    fc = AE.filtro_concat([(0.0, 2.0), (5.0, 9.0)], 0.08)
    check("[v0][a0][v1][a1]concat=n=2:v=1:a=1" in fc, "aplicar_edl: concat intercalado")
    check("afade=t=in" in fc, "aplicar_edl: micro-fundidos")
    os.remove(edl_tmp)
except Exception as ex:
    check(False, f"smoke aplicar_edl: {ex}")

try:
    import shorts_plan as SP
    import tempfile as _tf
    _srt = _tf.mktemp(suffix=".srt")
    open(_srt, "w", encoding="utf-8").write(
        "1\n00:00:11,000 --> 00:00:12,000\nHola\n\n"
        "2\n00:00:50,000 --> 00:00:51,000\nFuera\n\n")
    _td = _tf.mkdtemp()
    _out, _ok, _tot = SP.retimear_srt(
        _srt, [{"id": "a", "from": 10.0, "to": 13.0},
               {"id": "b", "from": 40.0, "to": 46.0}], _td)
    _txt = open(_out, encoding="utf-8").read()
    check(_ok == 1 and _tot == 2 and "00:00:01,000 --> 00:00:02,000" in _txt,
          "shorts_plan: retimea SRT al timeline de salida")
    import shutil as _sh
    _sh.rmtree(_td, ignore_errors=True)
    os.remove(_srt)
except Exception as ex:
    check(False, f"smoke shorts_plan retime: {ex}")

try:
    errores, avisos, total = SP.validar(
        {"fuente": "x.mp4", "formato": "1080x1920",
         "segmentos": [{"id": "a", "from": 1.0, "to": 5.0, "hook_overlay": "HOLA"},
                       {"id": "b", "from": 10.0, "to": 12.0}]}, 30.0)
    check(not errores and abs(total - 6.0) < 1e-9, "shorts_plan: plan valido")
    errores2, _, _ = SP.validar(
        {"fuente": "x.mp4", "segmentos": [{"id": "a", "from": 1.0, "to": 5.0},
                                          {"id": "a", "from": 4.0, "to": 6.0}]}, 30.0)
    check(len(errores2) >= 2, f"shorts_plan: rechaza duplicados/solapes ({len(errores2)})")
    errores3, _, _ = SP.validar({"fuente": "x.mp4", "segmentos": []}, 30.0)
    check(errores3, "shorts_plan: rechaza segmentos vacios")
    # segmento con from no numerico no debe romper el chequeo de solapes
    errores4, _, _ = SP.validar(
        {"fuente": "x.mp4",
         "segmentos": [{"id": "a", "from": "x", "to": 5.0},
                       {"id": "b", "from": 1.0, "to": 2.0}]}, 30.0)
    check(errores4 and not any("solape" in e for e in errores4),
          "shorts_plan: from invalido no rompe solapes")
except Exception as ex:
    check(False, f"smoke shorts_plan: {ex}")

try:
    import grade as GR
    f1 = GR.filtro_grade(0.6, True)
    f0 = GR.filtro_grade(0.0, False)
    check("vignette" in f1 and "vignette" not in f0, "grade: vineta opcional")
    check("colorbalance" in f1 and "eq=" in f1, "grade: filtros de marca")
    check("contrast=1.000" in f0, "grade: intensidad 0 = neutro")
except Exception as ex:
    check(False, f"smoke grade: {ex}")

try:
    import variantes as VA
    hv = {"video": {"codec": "h264", "width": 1280, "height": 720, "fps": 30.0},
          "audio": {"codec": "aac"}}
    bv = {"video": {"codec": "h264", "width": 1280, "height": 720, "fps": 30.0},
          "audio": {"codec": "aac"}}
    check(VA.compatibles(hv, bv), "variantes: detecta join stream-copy")
    bv2 = {"video": {"codec": "h264", "width": 1920, "height": 1080, "fps": 30.0},
           "audio": {"codec": "aac"}}
    check(not VA.compatibles(hv, bv2), "variantes: detecta re-encode necesario")
    # medir_lufs sobre un tono sintetico
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
         "-i", "sine=frequency=440:d=1", "-c:a", "aac", os.path.join(tempfile.gettempdir(), "editoria_val_lufs.m4a")],
        capture_output=True, timeout=60)
    if r.returncode == 0:
        lufs = VA.medir_lufs(os.path.join(tempfile.gettempdir(), "editoria_val_lufs.m4a"))
        check(-40 < lufs < 0, f"variantes: medir_lufs ({lufs:.1f} LUFS)")
        os.remove(os.path.join(tempfile.gettempdir(), "editoria_val_lufs.m4a"))
    else:
        check(False, "variantes: no se pudo sintetizar audio de prueba")
except Exception as ex:
    check(False, f"smoke variantes: {ex}")

try:
    from PIL import Image as _I
    _base = os.path.join(tempfile.gettempdir(), "editoria_val_thumb.png")
    _I.new("RGB", (640, 360), (30, 30, 40)).save(_base)
    r = subprocess.run(
        [sys.executable, os.path.join(BASE, "scripts/ffmpeg_tools/thumbnail.py"),
         _base, "--texto", "PRUEBA UNO", "-o", os.path.join(tempfile.gettempdir(), "editoria_val_thumb_out.png")],
        capture_output=True, timeout=60)
    ok_thumb = r.returncode == 0 and os.path.exists(os.path.join(tempfile.gettempdir(), "editoria_val_thumb_out.png"))
    if ok_thumb:
        im = _I.open(os.path.join(tempfile.gettempdir(), "editoria_val_thumb_out.png"))
        ok_thumb = im.size == (1280, 720)
    check(ok_thumb, "thumbnail: compone 1280x720")
    r2 = subprocess.run(
        [sys.executable, os.path.join(BASE, "scripts/ffmpeg_tools/thumbnail.py"),
         _base, "--texto", "una dos tres cuatro cinco"],
        capture_output=True, timeout=60)
    check(r2.returncode != 0, "thumbnail: rechaza >4 palabras")
    for p in (_base, os.path.join(tempfile.gettempdir(), "editoria_val_thumb_out.png")):
        if os.path.exists(p):
            os.remove(p)
except Exception as ex:
    check(False, f"smoke thumbnail: {ex}")

# 6b. los nuevos CLIs responden --help
for cli in ["scripts/beat_sync.py", "scripts/chapters.py",
            "scripts/registrar_aprendizaje.py",
            "scripts/ffmpeg_tools/transcribir.py",
            "scripts/ffmpeg_tools/aplicar_edl.py",
            "scripts/ffmpeg_tools/shorts_plan.py",
            "scripts/ffmpeg_tools/thumbnail.py",
            "scripts/ffmpeg_tools/verticalizar.py",
            "scripts/ffmpeg_tools/grade.py",
            "scripts/ffmpeg_tools/variantes.py"]:
    r = subprocess.run([sys.executable, os.path.join(BASE, cli), "--help"],
                       capture_output=True, timeout=30)
    check(r.returncode == 0, f"--help {cli}")

# 7. regresiones de la ronda iart (cada una reprodujo un bug real; ver reglas-tecnicas.md)
try:
    import json as _json
    import numpy as _np
    from PIL import Image as _Img
    sys.path.insert(0, os.path.join(BASE, "scripts", "ffmpeg_tools"))
    import _comun as _C
    tmp = tempfile.mkdtemp(prefix="editoria_val_")
    # 7a. color de marca exacto tras H.264 (BT.709, no BT.601)
    ref = _C.NEUTRO["acento"]
    for i in range(2):
        _Img.new("RGB", (320, 180), ref).save(f"{tmp}/c_{i:04d}.png")
    _C.codificar_frames(f"{tmp}/c_%04d.png", 30, f"{tmp}/c.mp4")
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", f"{tmp}/c.mp4", "-frames:v", "1",
                          # como un player con HD: asume BT.709 (el encode viejo daba (244,82,6))
                          "-vf", "scale=in_color_matrix=bt709,format=rgb24", "-f", "rawvideo", "-"],
                         capture_output=True).stdout
    px = tuple(raw[(90 * 320 + 160) * 3:(90 * 320 + 160) * 3 + 3])
    check(all(abs(a - b) <= 4 for a, b in zip(px, ref)),
          f"color de marca fiel tras encode ({px} vs {ref})")
    # 7b. overlay con alfa: el alfa sobrevive en .webm y .mov
    for i in range(3):
        im = _Img.new("RGBA", (320, 180), (0, 0, 0, 0))
        if i == 1:
            im.paste(ref + (255,), (20, 120, 160, 160))
        im.save(f"{tmp}/a_{i:04d}.png")
    encoders = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True,
                              text=True).stdout
    for ext, enc in ((".webm", "libvpx-vp9"), (".mov", "prores_ks")):
        if enc not in encoders:   # build de ffmpeg sin ese codec: no es un defecto de la skill
            print(f"AVISO ffmpeg sin {enc}: overlays {ext} no disponibles en este equipo")
            continue
        r = _C.codificar_frames(f"{tmp}/a_%04d.png", 30, f"{tmp}/a{ext}")
        check(r.get("transparente", 0) > 0.5, f"alfa verificado en {ext} ({r.get('transparente')})")
    # 7c. kenburns muestra la imagen real (antes salía negra en silencio)
    _Img.new("RGB", (400, 300), (40, 160, 90)).save(f"{tmp}/foto.png")
    kb = R.sc_kenburns(ctx, {"tipo": "kenburns", "from": 0, "to": 5, "imagen": f"{tmp}/foto.png",
                             "at": {"kenburns": 0}}, 1.0)
    check(kb.getpixel((R.W // 2, R.H // 3))[1] > 120, "kenburns compone la imagen (no negro)")
    # 7d. pase: duración exacta (zoompan por imagen, no por stream)
    os.makedirs(f"{tmp}/fotos")
    for i in (1, 2, 10):
        _Img.new("RGB", (480, 360), (30 * i, 90, 140)).save(f"{tmp}/fotos/f{i}.jpg")
    subprocess.run([sys.executable, os.path.join(BASE, "scripts/ffmpeg_tools/montaje.py"), "pase",
                    f"{tmp}/fotos", "--duracion", "1", "--transicion", "0.4", "--tamano", "320x568",
                    "-o", f"{tmp}/pase.mp4"], capture_output=True, timeout=120)
    d_ = _C.probe(f"{tmp}/pase.mp4").get("duration") if os.path.exists(f"{tmp}/pase.mp4") else None
    check(d_ is not None and abs(d_ - 3.0) < 0.05, f"pase: 3 fotos x 1 s = 3.0 s ({d_})")
    # 7e. plantilla × tabla: tipado y fail-loud
    falt = set()
    p_ = R.sustituir({"a": "{n}", "b": "Hola {nombre}", "c": "{x}"}, {"n": "42", "nombre": "Ana"}, falt)
    check(p_["a"] == 42 and p_["b"] == "Hola Ana" and falt == {"x"},
          "plantilla: número tipado, texto sustituido y columna faltante detectada")
    # 7f. fotosensibilidad: 4 Hz falla, 1 Hz pasa
    import auto_qa as _Q
    t_ = _np.arange(90) / 30
    def tren(hz):
        on = ((t_ * hz) % 1) < 0.15
        return _np.repeat(_np.where(on, 235, 16)[:, None, None], 36 * 64, axis=1).reshape(-1, 36, 64).astype(_np.float32)
    check(bool(_Q.destellos(tren(4), 30)) and not _Q.destellos(tren(1), 30),
          "fotosensibilidad: 4 destellos/s se marca, 1/s no")
    # 7g. karaoke con tiempo real por palabra
    import caption as _K
    cues = _K.agrupar_palabras([["Hoy", 0.1, 0.35], ["vamos", 0.4, 0.7], ["a", 0.72, 0.78],
                                ["hackear", 0.8, 1.4]], 4)
    check(cues and cues[0][3] == [30, 32, 8, 60], f"karaoke: duraciones reales por palabra ({cues[0][3] if cues else '-'})")
    # 7h. la voz que no cabe se detecta antes de pagar TTS
    plan_v = {"duracion": 6, "escenas": [
        {"tipo": "quote", "from": 0, "to": 2, "voz": " ".join(["palabra"] * 20)},
        {"tipo": "quote", "from": 2, "to": 6, "voz": "fin"}]}
    _json.dump(plan_v, open(f"{tmp}/pv.json", "w"))
    r = subprocess.run([sys.executable, os.path.join(BASE, "scripts/auditar_plan.py"), f"{tmp}/pv.json"],
                       capture_output=True, text=True)
    check(r.returncode == 1 and "pisaría" in r.stdout, "auditar_plan: voz que pisa a la siguiente = ERROR")
except Exception as ex:
    check(False, f"regresiones ronda iart: {type(ex).__name__}: {ex}")

print()
if fails:
    print(f"{len(fails)} FALLO(S)")
    sys.exit(1)
print("SKILL VALIDO")
