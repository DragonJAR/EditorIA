#!/usr/bin/env python3
"""check_env.py — valida las capacidades disponibles antes de trabajar.
Revisa: herramientas locales (ffmpeg, python, libs), assets del skill
(fuentes, logos de los brand packs), API keys (ElevenLabs) y reporta qué puede y qué no
puede hacer EditorIA en este entorno. Sale 0 si lo esencial está, 1 si
falta algo crítico. Uso: python scripts/check_env.py
"""
import glob, json, os, sys, subprocess, platform

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ok_critico = True
SO = {"Windows": "Windows", "Darwin": "macOS", "Linux": "Linux"}.get(platform.system(), platform.system())

HINTS_INSTALACION = {
    "Windows": "winget install Gyan.FFmpeg  (o https://ffmpeg.org/download.html y agregarlo al PATH)",
    "macOS": "brew install ffmpeg",
    "Linux": "sudo apt install ffmpeg  (Debian/Ubuntu)  |  sudo dnf install ffmpeg  (Fedora)",
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
_filtros = set()
if ok_ffmpeg:
    try:
        _r = subprocess.run(["ffmpeg", "-hide_banner", "-filters"],
                            capture_output=True, text=True, timeout=10)
        for ln in (_r.stdout or "").splitlines():
            partes = ln.split()
            # Formato de cada filtro: "<flags> <nombre> <origen>-><destino> <desc>".
            # Cabeceras ("Filters:") y leyenda ("T.. = ...") no tienen "->" en la 3a col.
            if len(partes) >= 3 and "->" in partes[2]:
                _filtros.add(partes[1])
    except Exception:
        _filtros = set()
for filtro, para in (("drawtext", "textos sobre vídeo (shorts_plan.py hook, look.py/scenes.py timecode)"),
                     ("subtitles", "subtítulos SRT (caption.py)"),
                     ("ass", "subtítulos ASS animados/karaoke (caption.py)")):
    rep(f"filtro ffmpeg {filtro}", filtro in _filtros,
        "disponible" if filtro in _filtros else
        f"falta — {para} fallará; reinstalar ffmpeg con libfreetype/libass "
        f"({HINTS_INSTALACION.get(SO, 'ver https://ffmpeg.org/download.html')})",
        critico=False)
if ok_ffmpeg and any(f not in _filtros for f in ("drawtext", "ass")):
    print("INFO el motor central de composición gráfica por píxeles (PIL -> libx264) "
          "sigue 100% funcional; solo los subtítulos quemados directos "
          "(caption.py, shorts_plan.py) requieren libfreetype/libass en ffmpeg")
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
