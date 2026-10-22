# Instalación — Windows, macOS y Linux

EditorIA funciona en los tres sistemas operativos. Los scripts son Python
puro (solo stdlib + `Pillow`/`numpy`) y llaman a `ffmpeg`/`ffprobe` del PATH.
La detección de fuentes, rutas temporales y binarios se adapta al SO
automáticamente (`scripts/ffmpeg_tools/_plataforma.py`).

## Paso 0: verificar

```bash
python scripts/check_env.py
```

En Windows el binario se llama `python` (no `python3`); el script lo tiene en
cuenta. Debe terminar en `ENTORNO LISTO`.

## Por sistema operativo

### Windows 10/11

```powershell
# FFmpeg (incluye ffprobe) — una de las dos:
winget install Gyan.FFmpeg
# o descargar de https://ffmpeg.org/download.html y agregar la carpeta bin al PATH

# Python 3.9+ (marcar "Add python.exe to PATH" en el instalador):
# https://www.python.org/downloads/

# Librerías:
py -m pip install pillow numpy
# Opcional (voz/música IA): py -m pip install requests
```

Notas Windows:
- Ejecutar los scripts como `py scripts\render_plan.py ...` o `python scripts\render_plan.py ...`.
- Las fuentes se resuelven desde `C:\Windows\Fonts` automáticamente.
- Los archivos de texto se leen/escriben siempre en UTF-8 explícito.

### macOS

```bash
# FFmpeg:
/opt/homebrew/bin/brew install ffmpeg   # Apple Silicon
/usr/local/bin/brew install ffmpeg       # Intel

# Python 3.9+ (suele venir con las Command Line Tools; si no):
brew install python

# Librerías:
pip3 install pillow numpy
# Opcional (voz/música IA): pip3 install requests
```

Notas macOS:
- Las fuentes se resuelven desde `/System/Library/Fonts` y `~/Library/Fonts`.
- `fc-match` no existe por defecto: la resolución usa los directorios del sistema.
- El `ffmpeg` de Homebrew **no trae libass** (faltan `drawtext`, `subtitles`, `ass`).
  Para rotular sobre video existente: `brew install ffmpeg-full`. Es **keg-only**
  (no entra al PATH), pero las herramientas lo **encuentran solas** para el
  comando que quema texto — no hace falta exportar nada a mano. Sin él, la
  creación por plan sigue funcionando (el motor dibuja el texto con PIL); solo
  fallan los subtítulos quemados. Ver `references/capacidades.md`.

### Linux (Debian/Ubuntu)

```bash
sudo apt install ffmpeg python3 python3-pip
pip3 install pillow numpy
# Opcional (voz/música IA): pip3 install requests
```

Fedora: `sudo dnf install ffmpeg python3-pip`.

## Opcionales (los tres SO)

- **Voz y música IA**: variable de entorno `ELEVENLABS_API_KEY` (`voz_off.py`, `musica.py`).
- **Transcripción local**: `whisper-cli` en el PATH (o segmentos de cualquier fuente para `retakes.py`).
- **Remotion / HyperFrames**: Remotion requiere Node.js 18+ y HyperFrames Node.js 22+ (`references/remotion.md`, `references/hyperframes.md`); `check_env.py` los detecta y sugiere instalación sin fallar si faltan.

## Notas de portabilidad

- Nunca se asume `/tmp`: los temporales usan el directorio del SO.
- Nunca se asume `python3` como binario: `check_env.py` usa el intérprete en ejecución.
- `ffmpeg`/`ffprobe` se buscan en el PATH con mensajes de instalación por SO si faltan.
- Rutas con `~` se expanden con `os.path.expanduser` (funciona en los tres SO).

---

→ Canónico: `references/instalacion.md` · Dominio: operacion · Vecinos: `references/capacidades.md`, `references/auto-mejora.md`, `references/mapa.md`
