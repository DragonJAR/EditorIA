# Capacidades — con qué cuenta EditorIA

Antes de arrancar cualquier build: `python scripts/check_env.py`.
La skill adapta el plan a lo disponible; nunca promete lo que no puede verificar.

## Herramientas locales (verificadas por `check_env.py`)

| Capacidad | Herramienta | Si falta |
|---|---|---|
| Render frame a frame | Python + PIL + numpy | Crítico: instalar (`pip install pillow numpy`) |
| Encode / mux / cortes | ffmpeg + ffprobe | Crítico: instalar ffmpeg |
| **Rotular sobre video existente** | filtros `drawtext` / `subtitles` / `ass` de ffmpeg (libass + libfreetype) | Degradar: el motor propio (`render_plan.py`) dibuja el texto con PIL y no depende de ffmpeg; lo que se rompe es `caption.py` (subtítulos quemados), el `hook_overlay` de `shorts_plan.py` y el timecode de `look.py`/`scenes.py`. El ffmpeg de Homebrew NO trae libass: la fórmula que sí es `brew install ffmpeg-full` (keg-only, no entra al PATH). **Las herramientas lo eligen solas**: `caption.py`, `look.py`, `scenes.py` y `shorts_plan.py` buscan un ffmpeg que traiga los filtros (en el PATH, en el keg de `ffmpeg-full` o en cualquier versión instalada) y lo usan solo para el comando que quema texto; el resto de comandos siguen con el ffmpeg normal. No hay que exportar nada a mano: en un agente cada llamada de shell es un proceso nuevo y un `export PATH` no persiste entre llamadas. `check_env.py` avisa al arrancar y dice qué binario va a usarse |
| Voz en off, música IA | ElevenLabs (`$ELEVENLABS_API_KEY`) | Degradar: entregar sin audio + avisar; música libre solo si el usuario la provee |
| Tipografía de marca | la del brand pack (ver `brand-packs.md`) | Degradar: sans del sistema + anotar la diferencia |
| Isotipo oficial | el del brand pack (`logos.isotipo`) | Pedirlo al usuario; nunca redibujar el logo |

## Dependencias externas opcionales

| Capacidad | Herramienta | Si falta |
|---|---|---|
| Transcripción propia local (sin API de pago) | whisper.cpp (`whisper-cli`, modelo ~1.6GB) | Opcional: el flujo de retakes (`retakes.py`) consume segmentos transcritos de cualquier fuente; sin whisper.cpp, la transcripción la provee el usuario o un ASR externo |
| Descargar una referencia desde un enlace | yt-dlp (`scripts/referencia.py --url`, `scripts/clonar_video.py`) | Opcional: el usuario exporta el video del sitio y se usa como archivo local |
| Transcripción con tiempo por palabra (leer referencias, karaoke) | whisper.cpp / faster-whisper / openai-whisper (`scripts/alinear.py`) | Opcional: sin ASR, la lectura de la referencia usa mosaicos por tiempo (`scripts/contact_sheet.py --cada`) sin palabras |
| Animación programática en React | Remotion (`npx remotion`, Node 18+) | Opcional: ver `references/remotion.md`; el motor Python cubre la mayoría de piezas |
| Video determinista desde HTML | HyperFrames (`npx hyperframes`, Node 22+) | Opcional: ver `references/hyperframes.md`; `npx hyperframes skills update` |

## Capacidades multimodales del modelo

| Capacidad | Uso en el skill |
|---|---|
| **Visión** | QA cuadro por cuadro: extraer frames (`ffmpeg -ss {t}`) y mirarlos antes de entregar. Obligatorio (Success Criteria #6). |
| **Generación de imágenes** | Crear assets (fondos, texturas, mockups) vía el pipeline de medios cuando el brief los necesite. |
| **Browser / search** | Investigar referencias, verificar datos y cifras, buscar técnicas. |
| **Audio** | No generar SFX sintéticos que suenen falsos; preferir librerías o síntesis simple verificada. |

## MCP / integraciones

Si hay un MCP conectado (Drive, Gmail, etc.), la skill lo usa para traer material
fuente (transcripciones, assets) en vez de pedirlo por chat. El material que llega
por MCP se trata como **fuente a verificar**, no como verdad absoluta (nombres y
cifras se confirman contra la fuente primaria).

## Degradación elegante

1. **Falta API key** → video silencioso, se avisa en la entrega, se ofrece
   reintentar cuando haya key.
2. **Falta una fuente** → sustituir temporalmente, anotar en la entrega qué
   cambió y por qué.
3. **Render pesado sin RAM** → bajar a `--fps` menor o resolución de preview,
   validar, y re-render final cuando haya recursos.
4. **Técnica no implementada** → la biblioteca (`tecnicas-video.md`) describe
   QUÉ hacer; si no hay script, se implementa con PIL/ffmpeg o se propone
   alternativa honesta. Nunca fingir que se hizo.

## Regla de oro

Validar primero, prometer después. `check_env.py` al inicio de cada proyecto
nuevo; si algo crítico falta, se dice en la primera respuesta, no después del
tercer re-render.

---

→ Canónico: `references/capacidades.md` · Dominio: opcional · Vecinos: `references/instalacion.md`, `references/remotion.md`, `references/hyperframes.md`
