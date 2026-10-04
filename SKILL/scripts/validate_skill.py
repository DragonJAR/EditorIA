#!/usr/bin/env python3
"""Validador determinista del skill EditorIA.
Verifica: frontmatter válido, name == carpeta, archivos requeridos,
referencias enlazadas existen (en SKILL.md y en toda referencia),
scripts enlazados existen, sin archivos huérfanos, sin README.md,
sin angle brackets en frontmatter ni markdown, SKILL.md < 5000 palabras,
TODOS los scripts compilan y las 13 escenas renderizan.
Sale 0 si todo pasa, 1 si algo falla.
"""
import os, sys, re, ast, subprocess, tempfile

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
check(name and name.group(1) == os.path.basename(BASE),
      f"name == carpeta ({name.group(1) if name else '?'})")
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

# 2. archivos requeridos
req = ["SKILL.md", "brand/dragonjar.json", "references/brand-packs.md", "references/estilos.md",
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

# 5. las 13 escenas renderizan (smoke test con params mínimos)
try:
    import render_plan as R
    ctx = R.Ctx()
    escenas_ok = 0
    ats = {"apertura": {"cambio": 2, "p1": [0.5, 1], "p2": [2.5, 3]},
           "canales": {"marca": 0.5, "junta": 2, "rotulo": 3},
           "chat": {"rotulo": 0.5},
           "leads": {"rotulo": 1, "Caliente": 2, "Tibio": 3, "Frío": 4},
           "handoff": {"rotulo": 1, "persona": 2, "contexto": 3},
           "pago": {"rotulo": 1, "comprobante": 2, "cursor": 3, "toque": 4},
           "listo": {"listo": 1},
           "pildoras": {"palabras": [1, 2]},
           "hoy": {"rotulo": 1, "cuenta": 2},
           "recupera": {"rotulo": 1, "cursor": 2, "recupera": 3, "pagado": 4},
           "remate": {"palabras": [1], "gigante": 3},
           "final": {"lema": 1, "boton": 2},
           "medianoche": {}}
    for nombre, fn in R.SCENES.items():
        e = {"tipo": nombre, "from": 0, "to": 5, "at": ats.get(nombre, {}),
             "marca": "T", "rotulo": "R", "texto1": ["A"], "texto2": ["B"],
             "texto": "¡Listo!" if nombre == "listo" else ["A"],
             "lineas": ["A"], "gigante": "1", "lema": "L",
             "boton": "B", "cliente": "C", "iniciales": "AB", "monto": "$1",
             "detalle": "D", "resumen": "R", "hace": "hace 1 h", "nota": "N",
             "temp": "Caliente", "total": "1", "fecha": "hoy", "cuenta": 1,
             "hora": "12:00",
             "canales": [{"canal": "whatsapp", "nombre": "N",
                          "texto": "T", "at": 1}],
             "notificaciones": [{"canal": "w", "titulo": "T",
                                 "texto": "X", "at": 1}],
             "mensajes": [{"de": "cliente", "texto": "Hola", "at": 1},
                          {"de": "ia", "texto": "Listo", "at": 2}],
             "link": {"titulo": "T", "monto": "$1", "at": 9},
             "filas": [{"nombre": "N", "etapa": "E", "puntaje": 90,
                        "temp": "Caliente"}],
             "contexto": [{"k": "K", "v": "V"}],
             "tarjetas": [{"titulo": "T", "detalle": "D"}]}
        try:
            for t in [0.5, 2.5, 4.5]:
                fn(ctx, e, t)
            escenas_ok += 1
        except Exception as ex:
            check(False, f"escena {nombre}: {type(ex).__name__}: {ex}")
    check(escenas_ok == 13, f"13/13 escenas renderizan ({escenas_ok}/13)")
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

print()
if fails:
    print(f"{len(fails)} FALLO(S)")
    sys.exit(1)
print("SKILL VALIDO")
