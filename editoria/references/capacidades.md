# Capacidades — con qué cuenta EditorIA

Antes de arrancar cualquier build: `python scripts/check_env.py`.
La skill adapta el plan a lo disponible; nunca promete lo que no puede verificar.

## Herramientas locales (verificadas por `check_env.py`)

| Capacidad | Herramienta | Si falta |
|---|---|---|
| Render frame a frame | Python + PIL + numpy | Crítico: instalar (`pip install pillow numpy`) |
| Encode / mux / cortes | ffmpeg + ffprobe | Crítico: instalar ffmpeg |
| **Rotular sobre video existente** | filtros `drawtext` / `subtitles` / `ass` de ffmpeg (libass + libfreetype) | No hay que declararlo ni degradar nada: el motor propio (`render_plan.py`) dibuja el texto con PIL y no depende de ffmpeg; lo que se rompe es `caption.py` (subtítulos quemados), el `hook_overlay` de `shorts_plan.py` y el timecode de `look.py`/`scenes.py`. El ffmpeg de Homebrew NO trae libass: la fórmula que sí es `brew install ffmpeg-full` (keg-only, no entra al PATH). **Las herramientas lo eligen solas**: `caption.py`, `look.py`, `scenes.py` y `shorts_plan.py` buscan un ffmpeg que traiga los filtros (en el PATH, en el keg de `ffmpeg-full` o en cualquier versión instalada) y lo usan solo para el comando que quema texto; el resto de comandos siguen con el ffmpeg normal. No hay que exportar nada a mano: en un agente cada llamada de shell es un proceso nuevo y un `export PATH` no persiste entre llamadas. `check_env.py` avisa al arrancar y dice qué binario va a usarse |
| Voz en off, música IA | ElevenLabs (`$ELEVENLABS_API_KEY`) | **Declarar**: si la pieza lleva voz, se dice en la primera respuesta que falta la key (con su precio) y se ofrece la voz del sistema (`scripts/voz_local.py`) como borrador, anotando que no lleva direccion emocional |
| Tipografía de marca | la del brand pack (ver `brand-packs.md`) | **Declarar**: se avisa de que la fuente del pack no esta instalada, se usa la del sistema **y se anota la diferencia** (una pieza con otra voz tipografica no es la misma pieza) |
| Isotipo oficial | el del brand pack (`logos.isotipo`) | Pedirlo al usuario; nunca redibujar el logo |

## Capacidades que la pieza puede necesitar

Estas **no son requisitos del motor**: el motor Python renderiza, mezcla y
mide sin ellas. Son **capacidades que una pieza concreta puede necesitar**, y
que levantan el listón del resultado. Por eso la regla de esta tabla no es
"opcional" ni "degradar": es **declarar**.

| Capacidad | Herramienta | Si falta |
|---|---|---|
| Transcripción propia local (sin API de pago) | whisper.cpp (`whisper-cli`, modelo ~1.6GB) | **Declarar**: el flujo de retakes (`retakes.py`) consume segmentos transcritos de cualquier fuente; si el usuario no la trae, se le dice que se puede instalar (`brew install whisper-cpp`) y mientras tanto la transcripción la provee el usuario o un ASR externo |
| Descargar una referencia desde un enlace | yt-dlp (`scripts/referencia.py --url`, `scripts/clonar_video.py`) | **Declarar**: `pip install -U yt-dlp`; mientras tanto, el usuario exporta el video del sitio y se usa como archivo local |
| Transcripción con tiempo por palabra (leer referencias, karaoke) | whisper.cpp / faster-whisper / openai-whisper (`scripts/alinear.py`) | **Declarar**: sin ASR, la lectura de la referencia usa mosaicos por tiempo (`scripts/contact_sheet.py --cada`) sin palabras |
| Animación programática en React | Remotion (`npx remotion`, Node 18+) | **Declarar**: `npx create-video@latest`. Si la pieza es de animación paramétrica o de datos, es la via que da el mejor resultado: se pide la instalación (ver `references/remotion.md`) |
| Video determinista desde HTML | HyperFrames (`npx hyperframes`, Node 22+) | **Declarar**: `npx hyperframes skills update`. Es la via cuando la composicion es HTML (ver `references/hyperframes.md`) |
| 3D modelado y encuadre | Blender + servidor MCP (`uvx mcp-for-blender`) | **Declarar**: se instala Blender (https://www.blender.org). Ver `references/3d.md` |
| 3D desde imagen de referencia | Node + `img2threejs` | **Declarar**: Node 18+ y el repo (Apache-2.0). Ver `references/3d.md` |
| Diagramas como HTML+SVG | ninguno (es metodo, no binario) | No falta nada: la guia de estilo es el brand pack (ver `references/diagramas.md`) |
| Trazos a mano / pizarra (overlay) | `scripts/hand_draw.py` (Pillow) | Offline: suavizar y pintar PNG con alfa. Captura en vivo por cámara: declarar Node + MediaPipe (ver `references/hand-draw.md`); no entregar el overlay vacío en silencio |

**Que "declarar" quiere decir exactamente:** cuando una pieza necesita una
capacidad que no esta, **se le dice al usuario en la primera respuesta** que
falta, que se necesita para que la pieza salga como tiene que salir, y con
que comando se instala. **No se entrega menos en silencio.** La pieza sale
como se puede, pero con la declaracion delante: "para el plano del producto
en 3D hace falta Blender; instalo con X y te lo dejo, o te lo entrego en 2D
y lo rehacemos en 3D cuando lo tengas".

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

## Degradación declarada

Degradar **esta bien**: no todo el mundo tiene Blender, ni Node, ni
Whisper. Lo que no esta bien es degradar **sin decirlo**. Por eso cada
degradacion lleva su declaracion delante, y por eso el orden es: **primero
intentar la mejor salida posible; si no se puede, declararlo y explicar la
alternativa.**

1. **Falta API key** → video silencioso, **se avisa EN LA PRIMERA
   RESPUESTA** (no en la entrega, que es tarde), y se ofrece reintentar
   cuando haya key.
2. **Falta una capacidad que sostiene la mejor salida** (3D, Remotion,
   HyperFrames) → **no se degrada en silencio**: se pide la instalacion con
   su comando, y se entrega la mejor version que se pueda hacer mientras
   tanto. Ver la tabla de arriba.
3. **Falta una fuente** → sustituir temporalmente, **anotar en la entrega**
   qué cambio y por que.
4. **Render pesado sin RAM** → bajar a `--fps` menor o resolucion de
   preview, validar, y re-render final cuando haya recursos.
5. **Tecnica no implementada** → la biblioteca (`tecnicas-video.md`)
   describe QUE hacer; si no hay script, se implementa con PIL/ffmpeg o se
   propone alternativa honesta. Nunca fingir que se hizo.

## Regla de oro

Validar primero, prometer despues. `check_env.py` al inicio de cada proyecto
nuevo; si algo critico falta, se dice en la primera respuesta, no despues del
tercer re-render.

Y el listón es **la calidad del resultado**, no la comodidad del entorno:
si una capacidad falta, se declara y se pide, **nunca se entrega menos en
silencio**. Una pieza entregada sin su 3D, sin su Remotion o con un
degradado sin avisar no es una pieza economica: es una pieza que nadie dijo
que era provisional.

---

→ Canónico: `references/capacidades.md` · Dominio: herramienta · Vecinos: `references/instalacion.md`, `references/remotion.md`, `references/hyperframes.md`, `references/hand-draw.md`
