#!/usr/bin/env python3
"""check_env.py — valida las capacidades disponibles antes de trabajar.
Revisa: herramientas locales (ffmpeg, python, libs), assets del skill
(fuentes, isotipo), API keys (ElevenLabs) y reporta qué puede y qué no
puede hacer EditorIA en este entorno. Sale 0 si lo esencial está, 1 si
falta algo crítico. Uso: python scripts/check_env.py
"""
import os, sys, shutil, subprocess, platform

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
for binario, flag in [("ffmpeg", "-version"), ("ffprobe", "-version")]:
    ok, det = cmd_ver(binario, [flag])
    if not ok:
        det = HINTS_INSTALACION.get(SO, "ver https://ffmpeg.org/download.html")
    rep(binario, ok, det, critico=True)
# Python: en Windows el binario se llama 'python', no 'python3'
ok_py = sys.version_info >= (3, 9)
rep("python", ok_py,
    f"{platform.python_version()} ({sys.executable})" if ok_py else "se requiere Python 3.9+ (https://www.python.org/downloads/)",
    critico=True)

print("== Librerías Python ==")
for lib in ["PIL", "numpy", "requests"]:
    try:
        __import__(lib)
        rep(lib, True, "importable", critico=(lib != "requests"))
    except ImportError:
        rep(lib, False, "pip install " + ("pillow" if lib == "PIL" else lib.lower()),
            critico=(lib != "requests"))
try:
    __import__("scipy")
    rep("scipy", True, "importable (beat_grid.py)")
except ImportError:
    rep("scipy", False, "pip install scipy — solo necesario para beat_grid.py")

print("== Assets del skill ==")
for fam, arch in (("Plus Jakarta Sans", "PlusJakartaSans-wght.ttf"), ("Montserrat", "Montserrat-wght.ttf")):
    p = os.path.join(BASE, "assets", "fonts", arch)
    rep(f"fuente {fam} (empaquetada, OFL)", os.path.exists(p), f"assets/fonts/{arch}", critico=False)
rep("isotipo del pack de ejemplo", os.path.exists(os.path.join(BASE, "brand", "assets", "dragonjar-isotipo.png")),
    "brand/assets/dragonjar-isotipo.png", critico=False)

print("== APIs ==")
key = os.environ.get("ELEVENLABS_API_KEY")
rep("ELEVENLABS_API_KEY", bool(key),
    "voz en off + música disponibles" if key else "sin voz/música IA (degradar a entrega silenciosa)",
    critico=False)

print("== Dependencias opcionales ==")
ok, det = cmd_ver("whisper-cli", ["--version"])
rep("whisper-cli", ok,
    det if ok else "transcripción local no disponible (retakes.py acepta segmentos de cualquier fuente)",
    critico=False)

print("== Motores opcionales (no requeridos) ==")
ok_node, det_node = cmd_ver("node", ["--version"])
rep("node/npx", ok_node,
    det_node if ok_node else "Remotion requiere Node 18+; HyperFrames Node 22+ (ver references/remotion.md)",
    critico=False)
if ok_node:
    ok_r, det_r = cmd_ver("npx", ["--no-install", "remotion", "--version"])
    rep("remotion", ok_r,
        det_r if ok_r else "animación programática en React — ver references/remotion.md",
        critico=False)
    ok_h, det_h = cmd_ver("npx", ["--no-install", "hyperframes", "--version"])
    rep("hyperframes", ok_h,
        det_h if ok_h else "HTML→video determinista (HeyGen, Apache 2.0) — ver references/hyperframes.md",
        critico=False)

print("== Capacidades del modelo (asumidas, verificar en sesión) ==")
print("INFO visión multimodal — QA cuadro por cuadro (extraer frames y mirarlos)")
print("INFO generación de imágenes — assets vía pipeline de medios si se necesitan")
print("INFO browser/search — investigación web para referencias y datos")

print()
if ok_critico:
    print("ENTORNO LISTO")
else:
    print("FALTA ALGO CRÍTICO — instalar antes de renderizar")
    sys.exit(1)
