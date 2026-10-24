# Instalación — Windows, macOS y Linux

EditorIA funciona en los tres sistemas operativos. Los scripts son Python
puro (solo stdlib + `Pillow`/`numpy`) y llaman a `ffmpeg`/`ffprobe` del PATH.
La detección de fuentes, rutas temporales y binarios se adapta al SO
automáticamente (`scripts/ffmpeg_tools/_plataforma.py`).

## Instalar la skill

La skill son dos cosas: la carpeta `editoria/` (los scripts y las
referencias) y los README del repo. Se instala copiándola a la carpeta
donde el agente carga las skills (en MCode, `~/.minimax/skills/`):

```bash
git clone URL_DEL_REPO editoria-repo
python editoria-repo/editoria/scripts/sincronizar_instalada.py --destino ~/.minimax/skills
```

**Usa ese script y no un `cp` a pelo.** `tar` y `git archive` conservan el
mtime del commit, y si la carpeta de destino ya tenía un `__pycache__`, sus
`.pyc` quedan **más nuevos** que sus `.py`: python ejecuta ese bytecode y la
copia corre un motor que ya no existe. Los checks dan entonces fallos que
no se reproducen en el repo — y lo peor es que un fallo así no se ve como
fallo, se ve como un defecto del código.

El script extrae lo publicado, borra la caché y comprueba archivo por
archivo que la copia coincide.

Para **verificar** que no hay bytecode fantasma (compara el contenido
compilado, no las fechas: un commit posterior no convierte a un `.pyc` en
fantasma):

```bash
python scripts/check_env.py
```

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

## Capacidades que la pieza puede necesitar (los tres SO)

El motor no las necesita. **Una pieza concreta puede sí**, y por eso su
instalación se declara al usuario en vez de omitirse en silencio (ver
`references/capacidades.md`).

- **Voz y música IA**: variable de entorno `ELEVENLABS_API_KEY` (`voz_off.py`, `musica.py`).
- **Transcripción local**: `whisper-cli` en el PATH (o segmentos de cualquier fuente para `retakes.py`).
- **Remotion**: Node.js 18+ (`npx create-video@latest`) — `references/remotion.md`.
- **HyperFrames**: Node.js 22+ (`npx hyperframes skills update`) — `references/hyperframes.md`.
- **3D**: Blender (`uvx mcp-for-blender`, blender.org) — `references/3d.md`.

`check_env.py` detecta las que se pueden detectar, dice si faltan y **con
qué comando se instalan**.

## Si un check falla en un sitio y no en el otro

**Reproducirlo a mano ANTES de culpar al código.** Un check que falla en la
copia instalada y no en el repo no está señalando un defecto del motor:
está señalando el entorno. El motor puede estar perfecto y, aun así, el
síntipo (una escena que no se comporta, un recorte que no cuadra) apunta
al sitio equivocado — y por eso el fallo se busca donde no está.

El orden, de arriba abajo:

1. **¿Falla también en el repo?** Si sí, es el código: búscalo ahí.
2. **¿Falla solo en la copia instalada?** Lo primero que se mira es el
   bytecode fantasma: `python scripts/check_env.py` (compara el contenido
   compilado, no las fechas). Un `.pyc` más nuevo que su `.py` hace que
   python ejecute un motor que ya no existe.
3. **¿La copia coincide con lo publicado?** `python scripts/sincronizar_instalada.py --check`
   (compara archivo por archivo, por contenido).

El orden importa: sin el paso 1, el paso 2 se aplica a un defecto de
código real y se "arregla" lo que no estaba roto.

## Notas de portabilidad

- Nunca se asume `/tmp`: los temporales usan el directorio del SO.
- Nunca se asume `python3` como binario: `check_env.py` usa el intérprete en ejecución.
- `ffmpeg`/`ffprobe` se buscan en el PATH con mensajes de instalación por SO si faltan.
- Rutas con `~` se expanden con `os.path.expanduser` (funciona en los tres SO).

---

→ Canónico: `references/instalacion.md` · Dominio: operacion · Vecinos: `references/capacidades.md`, `references/auto-mejora.md`, `references/mapa.md`
