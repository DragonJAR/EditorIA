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

# código limpio: sin imports ni variables muertas, sin nombres indefinidos
# (el lint encontró aquí un ease aplicado dos veces y lógica a medio hacer)
try:
    from pyflakes import api as _pf, reporter as _rep
    import io as _io
    _out = _io.StringIO()
    _n = _pf.checkRecursive([os.path.join(BASE, "scripts")], _rep.Reporter(_out, _out))
    check(_n == 0, f"pyflakes limpio en scripts/ ({_n} avisos{': ' + _out.getvalue().splitlines()[0] if _n else ''})")
except ImportError:
    print("AVISO pyflakes no instalado: pip install pyflakes para revisar código muerto")

# toda CLI arranca: --help sin traceback (una dependencia opcional ausente se
# avisa con un mensaje claro, nunca un ModuleNotFoundError crudo)
crudas, mudas = [], []
for _dir in (os.path.join(BASE, "scripts"), os.path.join(BASE, "scripts", "ffmpeg_tools")):
    for _f in sorted(os.listdir(_dir)):
        if not _f.endswith(".py") or _f.startswith("_") or _f == "validate_skill.py":
            continue
        _ruta = os.path.join(_dir, _f)
        if "argparse" not in open(_ruta, encoding="utf-8").read():
            continue
        _r = subprocess.run([sys.executable, _ruta, "--help"], capture_output=True, text=True, timeout=60)
        if "Traceback" in _r.stderr:
            crudas.append(f"{_f}: {_r.stderr.strip().splitlines()[-1]}")
            continue
        # un agente aprende la herramienta por --help: ninguna opción ni
        # subcomando sin explicar (ffmpeg_tools/_comun.ayudar completa las comunes)
        _subs = re.findall(r"^\s+\{([\w\-]+(?:,[\w\-]+)+)\}", _r.stdout, re.M)
        _textos = [_r.stdout]
        for _sc in (_subs[0].split(",") if _subs else []):
            if not re.search(rf"^\s{{4}}{re.escape(_sc)}\s+\S", _r.stdout, re.M):
                mudas.append(f"{_f} {_sc} (subcomando)")
            _textos.append(subprocess.run([sys.executable, _ruta, _sc, "--help"], capture_output=True,
                                          text=True, timeout=60).stdout)
        for _t in _textos:
            _ls = _t.splitlines()
            _en = False
            for _i, _l in enumerate(_ls):
                if re.match(r"^(options|optional arguments|positional arguments)", _l, re.I):
                    _en = True
                    continue
                _m = re.match(r"^  (\S.*?)(\s{2,}\S.*)?$", _l)
                if not _en or not _m or _l.startswith("   ") or _m.group(1).startswith(("-h, --help", "{")):
                    continue
                _sig = _ls[_i + 1] if _i + 1 < len(_ls) else ""
                if not _m.group(2) and not re.match(r"^\s{6,}\S", _sig):
                    mudas.append(f"{_f} {_m.group(1).split(',')[0].split()[0]}")
check(not crudas, f"toda CLI arranca con --help ({'; '.join(crudas) or 'todas'})")
check(not mudas, f"toda opción y subcomando de toda CLI se explica en --help ({', '.join(mudas[:8]) or 'todas'})")
# una entrada que no existe (el error más común de un agente) se responde con un
# mensaje claro, nunca con un traceback (render_plan, retakes y voz_off lo
# hacían). Se excluyen las CLIs donde la sonda tendría efectos o costo: el banco
# completo, el registro de aprendizajes, la galería y check_env (sin entrada)
_sin_sonda = {"validate_skill.py", "medir_animacion.py", "registrar_aprendizaje.py", "galeria.py", "check_env.py"}
_tmp10 = tempfile.mkdtemp(prefix="editoria_sonda_")
_crudas10 = []
for _dir in (os.path.join(BASE, "scripts"), os.path.join(BASE, "scripts", "ffmpeg_tools")):
    for _f in sorted(os.listdir(_dir)):
        _ruta = os.path.join(_dir, _f)
        if (not _f.endswith(".py") or _f.startswith("_") or _f in _sin_sonda
                or "argparse" not in open(_ruta, encoding="utf-8").read()):
            continue
        _r = subprocess.run([sys.executable, _ruta, os.path.join(_tmp10, "no_existe.mp4"),
                             "-o", os.path.join(_tmp10, "salida.mp4")],
                            capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL)
        if "Traceback" in _r.stderr:
            _crudas10.append(f"{_f}: {_r.stderr.strip().splitlines()[-1][:70]}")
check(not _crudas10, f"una entrada inexistente da un error claro, sin traceback ({'; '.join(_crudas10) or 'todas'})")

# check_env (paso 0 del agente) declara EXACTAMENTE las librerías de terceros que
# importan los scripts: reportaba scipy, que nadie usa ya (mandaba a instalarla),
# y no reportaba faster_whisper, que sí se usa
_locales9 = {f_[:-3] for d_ in ("", "ffmpeg_tools") for f_ in os.listdir(os.path.join(BASE, "scripts", d_))
             if f_.endswith(".py")}
_terceros9 = set()
for d_ in ("", "ffmpeg_tools"):
    for f_ in os.listdir(os.path.join(BASE, "scripts", d_)):
        if not f_.endswith(".py") or f_ == "validate_skill.py":   # pyflakes: solo para validar
            continue
        for n_ in ast.walk(ast.parse(open(os.path.join(BASE, "scripts", d_, f_), encoding="utf-8").read())):
            mods_ = [a_.name for a_ in n_.names] if isinstance(n_, ast.Import) else (
                [n_.module] if isinstance(n_, ast.ImportFrom) and n_.module and n_.level == 0 else [])
            _terceros9 |= {m_.split(".")[0] for m_ in mods_} - set(sys.stdlib_module_names) - _locales9
_declaradas9 = set()
for n_ in ast.parse(open(os.path.join(BASE, "scripts", "check_env.py"), encoding="utf-8").read()).body:
    if isinstance(n_, ast.Assign) and getattr(n_.targets[0], "id", "") in ("LIBS_CRITICAS", "LIBS_OPCIONALES"):
        _declaradas9 |= set(ast.literal_eval(n_.value))
check(_terceros9 == _declaradas9,
      f"check_env declara exactamente las librerías que se importan (fantasma: "
      f"{sorted(_declaradas9 - _terceros9) or 'ninguna'}; sin declarar: {sorted(_terceros9 - _declaradas9) or 'ninguna'})")

# subtítulos sin marca: la tipografía de las escenas (Montserrat empaquetada,
# instancia estática para libass), no DejaVu del sistema
_vcap = os.path.join(tempfile.mkdtemp(prefix="editoria_cap_"), "v.mp4")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=black:s=320x180:d=1", _vcap])
_cap = subprocess.run([sys.executable, os.path.join(BASE, "scripts", "ffmpeg_tools", "caption.py"),
                       _vcap, "--text", "hola", "--dry-run"], capture_output=True, text=True, timeout=60)
check("FontName=Montserrat" in _cap.stdout + _cap.stderr and "fontsdir=" in _cap.stdout + _cap.stderr,
      "subtítulos sin marca en la tipografía empaquetada (Montserrat Bold estática, fontsdir del kit)")
# pop/slide: saltos de línea FIJOS (\N + \q2) — con el wrap de libass, el
# sobrepaso a 108 % re-envolvía 2 líneas en 3 durante un frame — y alfa con
# ease (\t con accel), no \fad lineal (arranca a velocidad plena)
_ass = os.path.join(os.path.dirname(_vcap), "pop.ass")
_vv = os.path.join(os.path.dirname(_vcap), "v916.mp4")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=black:s=1080x1920:d=1", _vv])
subprocess.run([sys.executable, os.path.join(BASE, "scripts", "ffmpeg_tools", "caption.py"), _vv,
                "--text", "Un lugar para volver cuando el mundo va demasiado rápido", "--animate", "pop",
                "--size", "60", "--write-ass", _ass, "--dry-run"], capture_output=True, text=True, timeout=60)
_dlg = [l_ for l_ in open(_ass, encoding="utf-8-sig") if l_.startswith("Dialogue")] if os.path.isfile(_ass) else []
check(_dlg and all("\\q2" in l_ and "\\N" in l_ and "\\fad" not in l_ and ",2,\\alpha" in l_ for l_ in _dlg),
      "subtítulos pop: saltos fijos (no re-envuelven al escalar) y fundido con ease")

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
    # la doc dice cuántas escenas hay: debe coincidir con el código (las cuentas se pudren)
    malas = []
    for doc in ("SKILL.md", "references/escenas.md", "references/plan-video.md"):
        txt_ = open(os.path.join(BASE, doc), encoding="utf-8").read()
        for m_ in re.finditer(r"(\d+) tipos (?:de escena|del plan)", txt_):
            if int(m_.group(1)) != n_total:
                malas.append(f"{doc}: {m_.group(0)}")
    check(not malas, f"la doc cuenta {n_total} escenas como el código ({'; '.join(malas) or 'coincide'})")
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
        # sin destellos al entrar: una superficie clara que entra de golpe salta la
        # luminancia (demo en 16:9 saltaba 80 en 0.2 s); mismo umbral que auto_qa
        saltos = []
        for nombre in R.SCENES:
            e = dict(muestras[nombre], tipo=nombre)
            if "imagen" in e:
                e["imagen"] = foto
            R._ESCALA.clear()
            lum = [float(_np.asarray(R.componer(ctx, [e], e["to"], t, set()).convert("L")
                                     .resize((_QA.ANCHO, int(_QA.ANCHO * alto / ancho)))).mean())
                   for t in _np.arange(0.0, min(1.75, e["to"] - 0.6), 1 / _QA.FPS_MUESTREO)]
            sal = max((abs(a_ - b_) for a_, b_ in zip(lum, lum[1:])), default=0)
            if sal > _QA.FLASH_JUMP:
                saltos.append(f"{nombre} {sal:.0f}")
        check(not saltos, f"{ancho}x{alto}: entradas sin destello (salto ≤ {_QA.FLASH_JUMP}) "
                          f"({', '.join(saltos) or 'todas suaves'})")
        # composición: ningún texto visible pisa a otro con la escena asentada
        # (55 % y 80 %; una sola implementación: medir_animacion.solapes). El 00
        # bajo «¡EN VIVO!» o «24 leads hoy» sobre su rótulo pasaban todas las
        # métricas de movimiento. Y lo mismo con COPY LARGO (cada texto ×2): un
        # agente escribe marcas, montos y títulos más largos que la muestra; la
        # escena debe encoger o partir su texto, no salirse ni pisarse
        import medir_animacion as _MAs
        _NO = {"canal", "de", "tipo", "captura", "imagen", "url", "formato", "transicion",
               "moneda", "fecha", "hora", "codigo"}

        def _x2(n_, k_=""):
            if isinstance(n_, dict):
                return {a_: (b_ if a_ in _NO else _x2(b_, a_)) for a_, b_ in n_.items()}
            if isinstance(n_, list):
                return [_x2(x_, k_) for x_ in n_]
            if isinstance(n_, str) and len(n_) > 1 and not n_.endswith((".png", ".jpg")) \
                    and not n_.startswith("#"):
                return n_ + " " + n_.replace("*", "")
            return n_
        pisados, largos = set(), []
        for nombre in R.SCENES:
            for copia in ("", "x2"):
                e = dict(muestras[nombre], tipo=nombre)
                if copia:
                    e = dict(_x2(e), tipo=nombre)
                if "imagen" in e:
                    e["imagen"] = foto
                R._ESCALA.clear()
                try:
                    pisados.update(f"{x_}{' (copy x2)' if copia else ''}"
                                   for x_ in _MAs.solapes(R, ctx, [e], e["to"] + 5))
                    if copia and R.escala_segura(ctx, e, 0) < 0.9:
                        largos.append(nombre)
                except Exception as ex:
                    largos.append(f"{nombre} {type(ex).__name__}: {ex}")
        # plan de agente: SIN `at` toda escena compone (tiempos desde la muestra,
        # escalados a su duración); un campo de contenido que falta da un error
        # claro con ejemplo (nunca un KeyError crudo tras minutos de render)
        sin_at, crudos = [], []
        for nombre in R.SCENES:
            e = {k_: v_ for k_, v_ in muestras[nombre].items() if k_ != "at"}
            e.update(tipo=nombre, to=e["to"] * 1.6)   # otra duración: los tiempos se estiran
            if "imagen" in e:
                e["imagen"] = foto
            try:
                R._ESCALA.clear()
                for t in (0.5, e["to"] / 2, e["to"] - 0.3):
                    R.componer(ctx, [R.completar_escena(e)], e["to"], t, set())
            except Exception as ex:
                sin_at.append(f"{nombre} {type(ex).__name__}: {ex}")
        try:
            R.preparar_escenas(ctx, {"escenas": [{"tipo": "pago", "from": 0, "to": 4}]})
            crudos.append("pago sin monto no falló")
        except SystemExit as ex:
            if "falta el campo `" not in str(ex) or "Ejemplo completo" not in str(ex):
                crudos.append(str(ex)[:80])
        check(not sin_at and not crudos, f"{ancho}x{alto}: plan sin `at` compone (tiempos desde la muestra) y "
                                         f"un campo faltante da error claro ({', '.join(sin_at + crudos) or 'sí'})")
        check(not largos, f"{ancho}x{alto}: con copy x2 cada escena encoge o parte su texto "
                          f"(sin red bajo x0.90, sin errores) ({', '.join(largos) or 'todas'})")
        check(not pisados, f"{ancho}x{alto}: ningún texto pisa a otro con la escena asentada "
                           f"({', '.join(sorted(pisados)) or 'limpio'})")
    R.formato(1080, 1920)
    ctx = R.Ctx()
    # cortes sin parpadeo: al cambiar de escena la anterior termina de irse DEBAJO
    # de la nueva (antes quedaban frames de fondo vacío en cada corte)
    R.formato(1080, 1920)
    ctx = R.Ctx()
    e1 = dict(muestras["stats"], tipo="stats")
    e2 = dict(muestras["quote"], tipo="quote", **{"from": e1["to"], "to": e1["to"] + 6},
              at={k_: v_ + e1["to"] for k_, v_ in muestras["quote"]["at"].items()})
    _alfa_prev, R.ALFA = R.ALFA, True
    try:
        R._ESCALA.clear()
        _cob = lambda tc: float(_np.asarray(R.componer(ctx, [e1, e2], e2["to"], tc, set()).split()[3]).mean())  # noqa: E731
        antes = _cob(e1["to"] - 0.6)
        hueco = min(_cob(e1["to"] + dt_) for dt_ in (0.0, 0.1, 0.2, 0.3))
    finally:
        R.ALFA = _alfa_prev
    check(hueco > 0.2 * antes, f"corte sin parpadeo: el contenido nunca cae a vacío en el corte "
                               f"(mínimo {hueco:.1f} vs {antes:.1f} antes)")
    # toda escena SALE: al final del solape su capa ya no se ve (una escena que se
    # creía la última desaparecía de golpe si le seguía otra)
    sin_salida = []
    for nombre, fn in R.SCENES.items():
        e = dict(muestras[nombre], tipo=nombre)
        antes = float(_np.asarray(fn(ctx, e, e["to"] - 0.6).split()[3]).mean())
        despues = float(_np.asarray(fn(ctx, e, e["to"] + R.SOLAPE - 0.02).split()[3]).mean())
        if antes > 1 and despues > 0.1 * antes:
            sin_salida.append(f"{nombre} ({despues:.1f}/{antes:.1f})")
    check(not sin_salida, f"toda escena sale al cruzar el corte ({', '.join(sin_salida) or 'todas'})")
    # cifras tabulares: un número que cuenta no tiembla de lado (nativo y sin raqm)
    from PIL import ImageDraw as _ID, Image as _IMG
    _f = R.Ctx().fT(150, 800)
    for _tnum in (R.TNUM, None):
        _orig, R.TNUM = R.TNUM, _tnum
        bordes = set()
        for v_ in ("$142.332", "$141.511", "$111.111"):
            im_ = _IMG.new("L", (1400, 300))
            R.cifra(_ID.Draw(im_), (700, 150), v_, _f, 255, "mm")
            bordes.add(im_.getbbox()[0])
        R.TNUM = _orig
        check(len(bordes) == 1, f"cifra tabular {'tnum' if _tnum else 'celdas'}: borde fijo al contar ({sorted(bordes)})")
    # cifras: los intermedios llevan los decimales del valor final (nunca 3.4999…)
    cu = [R.cuenta_up(0, 3.5, 0.3, 0), R.cuenta_up(0, 3.5, 9, 0), R.cuenta_up(0, 1500, 9, 0)]
    check(cu[1] == "3.5" and len(cu[0]) == 3 and cu[2] == "1,500", f"cuenta_up con decimales ({cu})")
except Exception as ex:
    check(False, f"smoke test escenas: {ex}")

# 5b. el detector de pops distingue aparición de movimiento y escalado (con casos
#     sintéticos conocidos: si el banco miente, toda la mejora recursiva miente)
try:
    import medir_animacion as _MA
    from PIL import Image as _I5, ImageDraw as _D5
    def _cuadro(dib):
        im = _I5.new("L", (180, 320), 12)
        dib(_D5.Draw(im))
        return _np.asarray(im, _np.float32)
    def _pop(a_, b_):
        d_ = _np.abs(b_ - a_)
        B_ = _MA.BLOQUE
        blq = [(by, bx) for by in range(320 // B_) for bx in range(180 // B_)
               if d_[by * B_:(by + 1) * B_, bx * B_:(bx + 1) * B_].mean() > _MA.POP_SALTO]
        return _MA._es_pop(a_, b_, blq)
    vacio = _cuadro(lambda d_: None)
    caja = _cuadro(lambda d_: d_.rectangle([50, 100, 130, 180], fill=240))
    movida = _cuadro(lambda d_: d_.rectangle([55, 100, 135, 180], fill=240))
    txt_a = _cuadro(lambda d_: d_.text((90, 160), "Hola", font=R.Ctx().fT(40, 800), fill=245, anchor="mm"))
    txt_b = _cuadro(lambda d_: d_.text((90, 160), "Hola", font=R.Ctx().fT(43.2, 800), fill=245, anchor="mm"))
    def _seq(salto_en=None):   # caja que se mueve 3 px/frame; opcionalmente se teletransporta
        xs, x_ = [], 20
        for i_ in range(14):
            x_ += 60 if i_ == salto_en else 3
            xs.append(_cuadro(lambda d_, x0=x_: d_.rectangle([x0, 100, x0 + 60, 160], fill=240)))
        return _np.stack(xs)
    casos = {"aparece de golpe = pop": _pop(vacio, caja), "se mueve 30 px = no": not _pop(caja, movida),
             "escala 8 % = no": not _pop(txt_a, txt_b),
             "movimiento parejo = sin tirones": _MA.metricas(_seq(), 30, 14 / 30 + 1)["tirones"] == 0,
             "teletransporte = salto": _MA.metricas(_seq(7), 30, 14 / 30 + 1)["tirones"] >= 1}
    def _arranque(curva):   # caja quieta 4 frames y luego se mueve según la curva
        xs = [20] * 4 + [20 + curva(i_) for i_ in range(1, 14)]
        return _np.stack([_cuadro(lambda d_, x0=x0: d_.rectangle([x0, 100, x0 + 60, 160], fill=240))
                          for x0 in xs])
    casos["arranca a velocidad plena = arranque"] = bool(
        _MA.metricas(_arranque(lambda i_: 9 * i_), 30, 2)["arranques"])
    casos["acelera (ease-in) = no"] = not _MA.metricas(
        _arranque(lambda i_: 9 * i_ * min(1, i_ / 6) ** 2), 30, 2)["arranques"]
    # densidad: 3 cajas que entran (fundido 0.2 s) en 0.5/1.5/2.5 s = 3 eventos;
    # una flotación de 1 px (respiración) = 0 eventos
    def _entradas(n_, t_):
        fr = []
        for i_ in range(int(3.6 * 30)):
            def dib(d_, i_=i_):
                for j_ in range(n_):
                    a_ = min(1, max(0, (i_ / 30 - (0.5 + j_)) / 0.2))
                    if a_ > 0:
                        d_.rectangle([20, 20 + j_ * 100, 160, 100 + j_ * 100], fill=int(12 + 228 * a_))
                    d_.rectangle([70, 300 + round(_np.sin(i_ / 30 * 3)), 110, 310], fill=60)
            fr.append(_cuadro(dib))
        return _MA.metricas(_np.stack(fr), 30, t_)["densidad"]
    casos["3 entradas = 3 eventos"] = abs(_entradas(3, 3.6) * 3.0 - 3) < 0.01
    casos["solo respiración = 0 eventos"] = _entradas(0, 3.6) == 0
    check(all(casos.values()), f"detector de pops calibrado ({casos})")
except Exception as ex:
    check(False, f"detector de pops: {ex}")

# 5c. plan de agente, de punta a punta: render REAL multiproceso de un plan sin
#     `at` (los workers recargaban el plan sin completar: KeyError solo en el
#     render de verdad), campos mal escritos avisados con sugerencia y cifras
#     con los separadores del idioma del plan
try:
    import subprocess as _sp5
    _d5 = tempfile.mkdtemp(prefix="editoria_e2e_")
    _p5 = os.path.join(_d5, "plan.json")
    json.dump({"duracion": 2.0, "numeros": "es", "escenas": [
        {"tipo": "stats", "from": 0, "to": 2.0, "titulo": "Prueba",
         "cards": [{"valor": 1240, "etiqueta": "a"}, {"valor": 4.8, "etiqueta": "b"}]}]},
        open(_p5, "w", encoding="utf-8"))
    _r5 = _sp5.run([sys.executable, os.path.join(BASE, "scripts", "render_plan.py"), _p5, "-o",
                    os.path.join(_d5, "e2e.mp4"), "--fps", "10", "--jobs", "2"], capture_output=True, text=True)
    check(_r5.returncode == 0 and os.path.isfile(os.path.join(_d5, "e2e.mp4")),
          f"render real multiproceso de un plan sin `at` ({(_r5.stderr or 'ok').strip().splitlines()[-1][:90]})")
    # con "musica" (sin voz) el entregable lleva esa música, del largo exacto del
    # video y normalizada a -14 LUFS (antes salía mudo: la sincronía no se oía)
    _p5m = os.path.join(_d5, "plan_musica.json")
    json.dump(dict(json.load(open(_p5, encoding="utf-8")),
                   musica=os.path.join(BASE, "film", "musica_demo.mp3")), open(_p5m, "w", encoding="utf-8"))
    _v5m = os.path.join(_d5, "e2e_musica.mp4")
    _r5m = _sp5.run([sys.executable, os.path.join(BASE, "scripts", "render_plan.py"), _p5m, "-o", _v5m,
                     "--fps", "10", "--jobs", "2"], capture_output=True, text=True)
    _dur5 = _sp5.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,duration", "-of", "csv=p=0",
                      _v5m], capture_output=True, text=True).stdout.split()
    _ds5 = {l_.split(",")[0]: float(l_.split(",")[1]) for l_ in _dur5 if "," in l_}
    import loudness as _LN5
    _lufs5 = float(_LN5.measure(_v5m, -14, -1.5, 11)["input_i"]) if "audio" in _ds5 else None
    check(_r5m.returncode == 0 and "audio" in _ds5 and abs(_ds5["audio"] - _ds5["video"]) <= 0.05
          and abs(_lufs5 + 14) <= 1.0,
          f"plan con \"musica\": el MP4 sale con ella, del largo del video y a -14 LUFS ({_ds5}, {_lufs5} LUFS)")
    import render_plan as _R5
    _m5 = json.load(open(os.path.join(BASE, "scripts", "escenas_muestra.json"), encoding="utf-8"))["escenas"]
    _ruido = [a_ for t_, e_ in _m5.items() for a_ in _R5.avisos_de_campos(dict(e_, tipo=t_))]
    _typo = _R5.avisos_de_campos({"tipo": "pasos", "from": 0, "to": 4, "pasos": [{"titulo": "x"}]})
    check(not _ruido and _typo and "`items`" in _typo[0],
          f"campos mal escritos: avisados con sugerencia, 0 avisos en las muestras ({len(_ruido)} ruido)")
    _R5.aplicar_globales({"numeros": "es"})
    _n5 = (_R5.cuenta_up(0, 1240, 9, 0), _R5.cuenta_up(0, 4.8, 9, 0))
    _R5.aplicar_globales({})
    check(_n5 == ("1.240", "4,8") and _R5.cuenta_up(0, 1240, 9, 0) == "1,240",
          f"\"numeros\": \"es\" separa 1.240 y 4,8 (default 1,240) ({_n5})")
    # "subtitulos": true reserva la banda; las 28 escenas siguen cabiendo encima
    _apret = []
    _R5.aplicar_globales({"subtitulos": True})
    try:
        for _w5, _h5 in ((1080, 1920), (1920, 1080)):
            _R5.formato(_w5, _h5)
            _base5 = _R5.caja_segura()[3]
            _c5 = _R5.Ctx()
            for t_, e_ in _m5.items():
                _R5._ESCALA.clear()
                if _R5.escala_segura(_c5, dict(e_, tipo=t_), 0) < 0.85:
                    _apret.append(f"{t_} {_w5}x{_h5}")
    finally:
        _R5.aplicar_globales({})
        _R5.formato(1080, 1920)
    check(_base5 < _R5.caja_segura()[3] and not _apret,
          f"\"subtitulos\": true sube el borde seguro y las escenas caben encima (≥ x0.85) "
          f"({', '.join(_apret) or 'todas'})")
except Exception as ex:
    check(False, f"plan de agente de punta a punta: {type(ex).__name__}: {ex}")

# 5d. ningún comando fallido borra lo que LEE: _comun.run limpiaba cmd[-1] tras
#     un fallo, y en ffprobe ese es la ENTRADA (un probe sobre un .json borró
#     scripts/demo_plan.json). Solo se limpia la salida parcial de ffmpeg.
try:
    sys.path.insert(0, os.path.join(BASE, "scripts", "ffmpeg_tools"))
    import _comun as _C5
    _d6 = tempfile.mkdtemp(prefix="editoria_borra_")
    _f6 = os.path.join(_d6, "plan.json")
    open(_f6, "w").write('{"no": "es video"}')
    _C5.run(["ffprobe", "-v", "error", _f6], quiet=True, check=False)
    _C5.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "nullsrc", "-i", _f6, _f6], quiet=True, check=False)
    check(os.path.isfile(_f6), "un ffprobe/ffmpeg fallido no borra su entrada (solo la salida parcial de ffmpeg)")
except SystemExit:
    check(os.path.isfile(_f6), "un ffprobe/ffmpeg fallido no borra su entrada (solo la salida parcial de ffmpeg)")
except Exception as ex:
    check(False, f"limpieza de salidas parciales: {type(ex).__name__}: {ex}")

# 5e. sincronía con la música (métrica v1, beat_sync.medir_sincronia): calibrada
#     con casos conocidos — alineado a mano = 100 %, al azar ≈ el azar teórico —
#     y la rejilla detectada en la música de ejemplo (100 BPM)
try:
    import beat_sync as _BS
    import beat_grid as _BG
    import random as _rnd
    _g7 = {"bpm": 120.0, "beat0": 0.0, "compas0": 0.0}
    _al = [{"from": 0, "to": 4, "at": {"a": 0.25, "b": [0.5, 1.0]}},
           {"from": 4, "to": 8, "at": {"a": 4.75}, "items": [{"at": 6.0}]}]
    _rnd.seed(7)
    _az = [{"from": 0, "to": 8, "at": {str(k): _rnd.uniform(0, 8) for k in range(400)}}]
    _m7a, _m7b = _BS.medir_sincronia(_al, _g7, 8), _BS.medir_sincronia(_az, _g7, 8)
    _bpm7 = _BG.analizar(os.path.join(BASE, "film", "musica_demo.mp3"))["bpm"]
    check(_m7a["entradas_pct"] == 100 and _m7a["entradas"] == 5 and _m7a["cortes_compas_pct"] == 100
          and abs(_m7b["entradas_pct"] - _m7b["azar_pct"]) < 6 and abs(_bpm7 - 100) <= 1,
          f"sincronía con la música calibrada (alineado {_m7a['entradas_pct']} %, azar "
          f"{_m7b['entradas_pct']} % vs teórico {_m7b['azar_pct']} %, rejilla {_bpm7} BPM)")
    # el plan con "musica" se edita al ritmo en la puerta única (preparar_escenas):
    # entradas al medio beat y cortes al compás; "ritmo": false no toca nada;
    # con voz en off los cortes no se mueven (la voz va por los tiempos originales)
    import render_plan as _R7
    _R7.formato(1080, 1920)
    _c7 = _R7.Ctx()
    _mus7 = os.path.join(BASE, "film", "musica_demo.mp3")
    _m7 = json.load(open(os.path.join(BASE, "scripts", "escenas_muestra.json"), encoding="utf-8"))["escenas"]
    _p7 = {"duracion": 10.0, "musica": _mus7, "escenas": [
        dict(_m7["stats"], tipo="stats", **{"from": 0, "to": 4.1}),
        dict(_BS.mapear_at(_m7["bars"], lambda t: t + 4.1), tipo="bars", **{"from": 4.1, "to": 10.0})]}
    _g8 = _BG.analizar(_mus7)
    _con = _BS.medir_sincronia(_R7.preparar_escenas(_c7, _p7), _g8, 10.0)
    _sin = _BS.medir_sincronia(_R7.preparar_escenas(_c7, dict(_p7, ritmo=False)), _g8, 10.0)
    _voz = _R7.preparar_escenas(_c7, dict(_p7, escenas=[dict(e, voz="hola") for e in _p7["escenas"]]))
    check(_con["entradas_pct"] == 100 and _sin["entradas_pct"] < 60
          and sorted(e["from"] for e in _voz) == [0, 4.1],
          f"plan con \"musica\" editado al ritmo (entradas {_sin['entradas_pct']} → {_con['entradas_pct']} %; "
          f"\"ritmo\": false intacto; con voz los cortes no se mueven)")
except Exception as ex:
    check(False, f"sincronía con la música: {type(ex).__name__}: {ex}")

# 5f. delivery_check (el veredicto en que confía el agente antes de entregar),
#     contra el spec de _delivery.py con archivos sintéticos de propiedades
#     conocidas: cada fila falla por SU causa y propone su arreglo
try:
    sys.path.insert(0, os.path.join(BASE, "scripts", "ffmpeg_tools"))
    import delivery_check as _DC
    _d8 = tempfile.mkdtemp(prefix="editoria_entrega_")

    def _fixture(nombre, tam, pix="yuv420p", audio="loudnorm=I=-14:TP=-2"):
        ruta = os.path.join(_d8, nombre)
        cmd = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=s={tam}:d=2:r=30"]
        if audio:
            cmd += ["-f", "lavfi", "-i", "sine=f=330:d=2:sample_rate=48000", "-af", audio, "-shortest"]
        subprocess.run(cmd + ["-c:v", "libx264", "-pix_fmt", pix, "-c:a", "aac", ruta], check=True)
        return ruta
    def _filas(r):
        return {f_["row"]: f_ for f_ in r["rows"]}
    _ok8 = _DC.check_file(_fixture("ok.mp4", "1080x1920"), "reels")
    _bajo8 = _DC.check_file(_fixture("bajo.mp4", "1080x1920", audio="volume=0.01"), "reels")
    _h8 = _DC.check_file(_fixture("h.mp4", "1920x1080"), "reels")
    _mudo8 = _DC.check_file(_fixture("mudo.mp4", "1080x1920", audio=None), "reels")
    _444 = _DC.check_file(_fixture("p444.mp4", "1080x1920", pix="yuv444p"), "reels")
    try:
        _DC.check_file(os.path.join(_d8, "ok.mp4"), "plataforma_que_no_existe")
        _desc8 = False
    except SystemExit:
        _desc8 = True
    _casos8 = {
        "conforme = PASS": _ok8["verdict"] == "PASS",
        "audio bajo = loudness FAIL con su arreglo": _filas(_bajo8)["loudness"]["status"] == "FAIL"
        and "loudness.py" in _filas(_bajo8)["loudness"]["fix"],
        "16:9 en reels = aspecto FAIL": _filas(_h8)["aspecto"]["status"] == "FAIL",
        "sin audio = WARN": _mudo8["verdict"] == "WARN" and _filas(_mudo8)["audio"]["status"] == "WARN",
        "yuv444p = pixel format FAIL": _filas(_444)["pixel format"]["status"] == "FAIL",
        "plataforma desconocida = error claro": _desc8,
    }
    check(all(_casos8.values()), f"delivery_check: cada fila falla por su causa "
                                 f"({', '.join(k_ for k_, v_ in _casos8.items() if not v_) or 'todas'})")
    import shutil as _sh8
    _sh8.rmtree(_d8, ignore_errors=True)
except Exception as ex:
    check(False, f"delivery_check: {type(ex).__name__}: {ex}")

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
    _ti = _tf.mkdtemp()   # carpeta privada (mktemp solo devuelve un nombre: carrera CWE-377)
    _srt = os.path.join(_ti, "subs.srt")
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
    _sh.rmtree(_ti, ignore_errors=True)
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
