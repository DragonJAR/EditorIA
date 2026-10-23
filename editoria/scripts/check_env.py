#!/usr/bin/env python3
"""check_env.py — valida las capacidades disponibles antes de trabajar.
Revisa: herramientas locales (ffmpeg, python, libs), assets del skill
(fuentes, logos de los brand packs), API keys (ElevenLabs) y reporta qué puede y qué no
puede hacer EditorIA en este entorno. Sale 0 si lo esencial está, 1 si
falta algo crítico. Uso: python scripts/check_env.py
"""
import glob, json, os, shutil, sys, subprocess, platform

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg_tools"))
from _comun import ffmpeg_con_texto  # noqa: E402  # mismo resolver que usan las herramientas
ok_critico = True
SO = {"Windows": "Windows", "Darwin": "macOS", "Linux": "Linux"}.get(platform.system(), platform.system())

HINTS_INSTALACION = {
    "Windows": "winget install Gyan.FFmpeg  (o https://ffmpeg.org/download.html y agregarlo al PATH)",
    "macOS": "brew install ffmpeg",
    "Linux": "sudo apt install ffmpeg  (Debian/Ubuntu)  |  sudo dnf install ffmpeg  (Fedora)",
}

# El ffmpeg de Homebrew NO trae libass/libfreetype: por eso faltan drawtext,
# subtitles y ass. `brew install ffmpeg` no lo arregla (ya esta instalado y es
# el mismo binario sin esos filtros). La fórmula que sí los trae es ffmpeg-full.
HINTS_FILTROS = {
    "macOS": ("brew install ffmpeg-full  (incluye libass+freetype; es keg-only, "
              "pero las herramientas lo encuentran solas)"),
    "Windows": ("winget install Gyan.FFmpeg  (build con libass: 'ffmpeg -filters' debe "
                "listar drawtext, subtitles y ass)"),
    "Linux": ("sudo apt install ffmpeg  (Debian/Ubuntu: paquete con libass; en Fedora "
              "sudo dnf install ffmpeg)"),
}

def rep(nombre, ok, detalle="", critico=False):
    global ok_critico
    marca = "OK  " if ok else ("FAIL" if critico else "WARN")
    print(f"{marca} {nombre}" + (f" — {detalle}" if detalle else ""))
    if critico and not ok:
        ok_critico = False

def cmd_ver(cmd, args):
    try:
        r = subprocess.run([cmd] + list(args),
                           capture_output=True, text=True, timeout=10)
        if r.returncode != 0:
            return False, "no instalado"
        linea = (r.stdout or r.stderr).strip().split("\n")[0][:60]
        return True, linea
    except Exception:
        return False, "no encontrado"

print(f"== Sistema operativo: {SO} ==")
print("== Herramientas locales ==")
ok_ffmpeg = False
for binario, flag in [("ffmpeg", "-version"), ("ffprobe", "-version")]:
    ok, det = cmd_ver(binario, [flag])
    if binario == "ffmpeg":
        ok_ffmpeg = ok
    if not ok:
        det = HINTS_INSTALACION.get(SO, "ver https://ffmpeg.org/download.html")
    rep(binario, ok, det, critico=True)
# Filtros de FFmpeg: caption.py (ass/subtitles), shorts_plan.py (hook overlay),
# look.py/scenes.py (timecode) los requieren. Un ffmpeg compilado sin
# libfreetype/libass los omite y solo se descubre al fallar un render.
print("== Filtros de FFmpeg ==")
# Las herramientas eligen solas un ffmpeg con libass (ffmpeg_texto): si el del
# PATH no los trae, se busca ffmpeg-full, que Homebrew deja keg-only (sin
# symlink, fuera del PATH). Este bloque debe mirar ESE binario, no el del
# PATH: si no, avisa de una falta que las herramientas ya no tienen.
_texto = ffmpeg_con_texto()
_filtros = set()
if _texto:
    try:
        _r = subprocess.run([_texto, "-hide_banner", "-filters"],
                            capture_output=True, text=True, timeout=10)
        for ln in (_r.stdout or "").splitlines():
            partes = ln.split()
            # Formato de cada filtro: "<flags> <nombre> <origen>-><destino> <desc>".
            # Cabeceras ("Filters:") y leyenda ("T.. = ...") no tienen "->" en la 3a col.
            if len(partes) >= 3 and "->" in partes[2]:
                _filtros.add(partes[1])
    except Exception:
        _filtros = set()
if _texto and _texto != shutil.which("ffmpeg"):
    print(f"INFO ffmpeg con libass: {_texto} (el del PATH no los trae; "
          f"las herramientas lo eligen solas)")
for filtro, para in (("drawtext", "textos sobre vídeo (shorts_plan.py hook, look.py/scenes.py timecode)"),
                     ("subtitles", "subtítulos SRT (caption.py)"),
                     ("ass", "subtítulos ASS animados/karaoke (caption.py)")):
    rep(f"filtro ffmpeg {filtro}", filtro in _filtros,
        "disponible" if filtro in _filtros else
        f"falta — {para} fallará; instalar un ffmpeg con libass: "
        f"{HINTS_FILTROS.get(SO, 'ver https://ffmpeg.org/download.html')}",
        critico=False)
if ok_ffmpeg and any(f not in _filtros for f in ("drawtext", "ass")):
    print("INFO el motor central de composición gráfica por píxeles (PIL -> libx264) "
          "sigue 100% funcional; solo los subtítulos quemados directos "
          "(caption.py, shorts_plan.py) requieren libfreetype/libass en ffmpeg")
    print("INFO sin esos filtros, el camino alterno es el motor propio: las piezas "
          "compuestas con render_plan.py traen el texto ya dibujado (PIL) y no "
          "dependen de ffmpeg para rotular")
# Python: en Windows el binario se llama 'python', no 'python3'
ok_py = sys.version_info >= (3, 9)
rep("python", ok_py,
    f"{platform.python_version()} ({sys.executable})" if ok_py else "se requiere Python 3.9+ (https://www.python.org/downloads/)",
    critico=True)

# Exactamente las librerías de terceros que importan los scripts (validate_skill
# compara ambas listas: ni dependencias fantasma ni dependencias sin declarar)
LIBS_CRITICAS = {"PIL": "pillow", "numpy": "numpy"}
LIBS_OPCIONALES = {"requests": ("requests", "voz y música IA (voz_off.py, musica.py gen)"),
                   "faster_whisper": ("faster-whisper", "transcripción local en Python (alinear.py, transcribir.py)")}
print("== Librerías Python ==")
for lib, pip in LIBS_CRITICAS.items():
    try:
        __import__(lib)
        rep(lib, True, "importable", critico=True)
    except ImportError:
        rep(lib, False, f"pip install {pip}", critico=True)
for lib, (pip, para) in LIBS_OPCIONALES.items():
    try:
        __import__(lib)
        rep(lib, True, f"importable — {para}")
    except ImportError:
        rep(lib, False, f"pip install {pip} — solo para {para}")

print("== Assets del skill ==")
for fam, arch in (("Plus Jakarta Sans", "PlusJakartaSans-wght.ttf"), ("Montserrat", "Montserrat-wght.ttf")):
    p = os.path.join(BASE, "assets", "fonts", arch)
    rep(f"fuente {fam} (empaquetada, OFL)", os.path.exists(p), f"assets/fonts/{arch}", critico=False)
for pack in sorted(glob.glob(os.path.join(BASE, "brand", "*.json"))):
    try:
        with open(pack, encoding="utf-8") as fh:
            logos = (json.load(fh).get("logos") or {})
    except ValueError as e:
        rep(f"pack {os.path.basename(pack)}", False, f"JSON inválido: {e}"); continue
    rutas = [v for v in logos.values() if isinstance(v, str) and v.lower().endswith((".png", ".svg", ".jpg"))]
    faltan = [r for r in rutas if not os.path.exists(os.path.join(os.path.dirname(pack), r))
              and not os.path.exists(os.path.join(BASE, r))]
    rep(f"pack {os.path.basename(pack)}", not faltan,
        f"{len(rutas)} logo(s) OK" if not faltan else "faltan: " + ", ".join(faltan))

print("== APIs ==")
# Buscar key en entorno o en ~/.secrets.env
key = os.environ.get("ELEVENLABS_API_KEY")
if not key:
    sec = os.path.expanduser("~/.secrets.env")
    if os.path.exists(sec):
        with open(sec, encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                if line.strip().startswith("export ELEVENLABS_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
rep("ELEVENLABS_API_KEY", bool(key),
    "disponible (voz en off + música IA)" if key else "sin voz/música IA (degradar a entrega silenciosa)")

print("== Dependencias opcionales ==")
ok_w, det_w = cmd_ver("whisper-cli", ["--help"])
if not ok_w:
    ok_w, det_w = cmd_ver("whisper", ["--help"])
rep("whisper-cli", ok_w,
    "disponible (transcripción local para retakes.py)" if ok_w else
    "transcripción local no disponible (retakes.py acepta segmentos de cualquier fuente)")
ok_y, det_y = cmd_ver("yt-dlp", ["--version"])
rep("yt-dlp", ok_y,
    f"disponible ({det_y}) — referencias desde un enlace (referencia.py --url)" if ok_y else
    "sin descarga por enlace (referencia.py --url): pip install -U yt-dlp, o usar el archivo local")

print("== Motores opcionales (no requeridos) ==")
ok_node, det_node = cmd_ver("node", ["--version"])
ok_npx, _ = cmd_ver("npx", ["--version"])
rep("node/npx", ok_node and ok_npx,
    f"{det_node}" if (ok_node and ok_npx) else "necesario solo para Remotion o HyperFrames")
# Remotion: opcional, se inicializa por proyecto con npx create-video@latest
ok_rem = os.path.exists("node_modules/@remotion/cli")
rep("remotion", ok_rem,
    "instalado en este proyecto" if ok_rem else
    "animación programática en React — ver references/remotion.md")
# HyperFrames: opcional, CLI de HeyGen (npx hyperframes)
ok_hf = os.path.exists("node_modules/hyperframes") or os.path.exists("node_modules/@heygen/hyperframes")
rep("hyperframes", ok_hf,
    "instalado en este proyecto" if ok_hf else
    "HTML→video determinista (HeyGen, Apache 2.0) — ver references/hyperframes.md")

print("== Cache de bytecode ==")
# Una copia instalada puede quedar con un .pyc MAS NUEVO que su .py: python usa
# el .pyc y ejecuta un motor que ya no existe ("codigo fantasma"). Pasa al
# copiar con `tar`/`git archive` (preservan el mtime del commit) sobre una
# copia que ya tenia __pycache__. Con git se puede ver: si el .py cambio
# DESPUES de compilarse el .pyc, el .pyc es un fantasma.
import struct  # noqa: E402


def _bytecode_fantasma():
    """Los .pyc cuyo codigo NO es el del .py actual (codigo fantasma).

    Un .pyc mas nuevo que su .py hace que python ejecute un codigo que ya no
    existe. Pasa al copiar con `tar`/`git archive` (preservan el mtime del
    commit) sobre una copia que ya tenia __pycache__. La comparacion es de
    CONTENIDO: se compila el .py actual y se compara con lo que guarda el
    .pyc. Un commit posterior no importa: lo que importa es si el codigo
    compilado es el mismo.
    """
    import marshal
    import types

    def _igual(a, b):
        """Dos objetos de codigo son el mismo si coinciden sus bytes, sus
        constantes y sus nombres. El `co_filename` NO se compara: el .pyc se
        compilo con la ruta absoluta y el .py actual con la relativa, y eso
        no dice nada sobre el codigo."""
        if not isinstance(a, types.CodeType) or not isinstance(b, types.CodeType):
            return a == b
        if a.co_code != b.co_code or a.co_names != b.co_names:
            return False
        if a.co_varnames != b.co_varnames or a.co_argcount != b.co_argcount:
            return False
        if len(a.co_consts) != len(b.co_consts):
            return False
        return all(_igual(x, y) for x, y in zip(a.co_consts, b.co_consts))

    fantasmas = []
    for d, _, archivos in os.walk(os.path.join(BASE, "scripts")):
        if not d.endswith("__pycache__"):
            continue
        for a in archivos:
            if not a.endswith(".pyc"):
                continue
            mod = a.split(".")[0] + ".py"
            py = os.path.join(os.path.dirname(d), mod)
            if not os.path.exists(py):
                continue
            with open(os.path.join(d, a), "rb") as fh:
                crudo = fh.read()
            if len(crudo) < 16:
                continue
            magic, flags = struct.unpack("<4sI", crudo[:8])
            if flags & 0b1:            # pyc por hash: Python lo valida solo
                continue
            try:
                with open(py, encoding="utf-8") as fh:
                    src = fh.read()
                actual = compile(src, py, "exec")
                guardado = marshal.loads(crudo[16:])
            except Exception:
                continue
            if not _igual(actual, guardado):
                fantasmas.append(os.path.relpath(py, BASE))
    return fantasmas


_fantasmas = _bytecode_fantasma()
rep("sin codigo fantasma (bytecode vigente)", not _fantasmas,
    "" if not _fantasmas else
    f"borrar __pycache__ de la copia: {', '.join(sorted(set(_fantasmas))[:3])}",
    critico=False)
if _fantasmas:
    print("     el .pyc guarda un codigo que el .py ya no tiene: python ejecuta el VIEJO")
    print(f"     rm -rf {os.path.join(BASE, 'scripts')}/**/__pycache__")

print("== Capacidades del modelo (asumidas, verificar en sesión) ==")
print("INFO visión multimodal — QA cuadro por cuadro (extraer frames y mirarlos)")
print("INFO generación de imágenes — assets vía pipeline de medios si se necesitan")
print("INFO browser/search — investigación web para referencias y datos")

print()
if ok_critico:
    print("ENTORNO LISTO")
    sys.exit(0)
else:
    print("FALTA ALGO CRÍTICO — instalar antes de renderizar")
    sys.exit(1)
