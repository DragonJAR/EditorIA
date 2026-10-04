# Capacidades — con qué cuenta EditorIA

Antes de arrancar cualquier build: `python scripts/check_env.py`.
La skill adapta el plan a lo disponible; nunca promete lo que no puede verificar.

## Herramientas locales (verificadas por `check_env.py`)

| Capacidad | Herramienta | Si falta |
|---|---|---|
| Render frame a frame | Python + PIL + numpy | Crítico: instalar (`pip install pillow numpy`) |
| Encode / mux / cortes | ffmpeg + ffprobe | Crítico: instalar ffmpeg |
| Voz en off, música IA | ElevenLabs (`$ELEVENLABS_API_KEY`) | Degradar: entregar sin audio + avisar; música libre solo si el usuario la provee |
| Tipografía de marca | la del brand pack (ver `brand-packs.md`) | Degradar: sans del sistema + anotar la diferencia |
| Isotipo oficial | el del brand pack (`logos.isotipo`) | Pedirlo al usuario; nunca redibujar el logo |

## Dependencias externas opcionales

| Capacidad | Herramienta | Si falta |
|---|---|---|
| Transcripción propia local (sin API de pago) | whisper.cpp (`whisper-cli`, modelo ~1.6GB) | Opcional: el flujo de retakes (`retakes.py`) consume segmentos transcritos de cualquier fuente; sin whisper.cpp, la transcripción la provee el usuario o un ASR externo |
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
