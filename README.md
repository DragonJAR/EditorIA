# EditorIA

[![Licencia](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Versión](https://img.shields.io/badge/version-1.5.0-green.svg)](editoria/SKILL.md)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org)
[![Plataformas](https://img.shields.io/badge/Win%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](#instalación)

> **Navaja suiza de edición de video con IA**, empaquetada como *skill* para Claude.
> Crea, edita, resume y mejora videos (`.mp4`): resúmenes animados de reuniones, tipografía cinética, anuncios por plan, films cinematográficos y piezas verticales para redes — para cualquier marca o sin marca.

🇬🇧 [English version](README.en.md)

## 🎯 Qué hace esta skill

EditorIA convierte un agente en un editor de video completo. Puede:

- **Renderizar por plan** declarativo (`plan.json` → `mp4`) con 28 tipos — `apertura`, `canales`, `chat`, `leads`, `handoff`, `pago`, `listo`, `pildoras`, `hoy`, `recupera`, `remate`, `final`, `medianoche`, `oferta`, `countdown`, `demo`, `rotulo_inferior` (13 originales de ad-explainers) más `bars`, `gauge`, `ranking`, `stats`, `timeline`, `quote`, `versus`, `confetti`, `typewriter`, `kenburns`, `pasos` (15 unificadas de fuentes MIT validadas).
- **Componer visualmente**: escena con `-datos` (CSV), escena sobre plantilla × tabla, audiogramas, karaoke por palabra, color BT.709 exacto, alfa overlay y rotación.
- **Animar con oficio**: motor de fluidez (resortes, fondo vivo, salidas anticipadas), motion blur de obturador 180° en entregas (`--blur 5`), 6 primitivas DRY (`barra_h`, `cuenta_up`, `arco`, `particulas`, `cuadricula`, `linewrap`) que componen las 28 escenas.
- **Voz en off y música con IA**: ElevenLabs TTS con cache content-addressed, música con ducking sidechain, alineación palabra-a-palabra (`alinear.py`) sobre Whisper local (whisper.cpp / faster-whisper / openai-whisper en cascada).
- **Brand packs marca-blanca**: la identidad vive en `brand/*.json` (DragonJAR incluido como ejemplo). Sin pack, modo libre con criterio cinematográfico puro. Nunca identidad hardcoded en el código.
- **QA automatizado**: máquina (`auto_qa.py` detecta negros, congelados, flashes, audio) + revisor visual del agente sobre contact sheet. Rúbrica de premios de 8 ejes (ninguno bajo 4/5).
- **Verificación de delivery**: `delivery_check.py` valida codec, LUFS, aspecto contra YouTube/TikTok/Reels.
- **Remotion opcional** (Node 22+, React 19) cuando se necesita animación HTML/CSS/JS programática.
- **HyperFrames opcional** (Node 22+) para plantillas HTML deterministas.

> **Importante**: el código del motor Python (PIL + ffmpeg) **NO requiere Node** — funciona en cualquier máquina con ffmpeg. Remotion/HyperFrames son opt-in para casos específicos.

## 📦 Instalación

### Opción 1 — Clonar al directorio de skills

```bash
# Para Claude Code / OpenCode
cd ~/.agents/skills/
git clone https://github.com/DragonJAR/EditorIA editoria

# Para otros agentes, adapta al path de skills correspondiente
```

### Opción 2 — Instalar globalmente

```bash
git clone https://github.com/DragonJAR/EditorIA.git
# La skill vive en editoria/. Apunta el path de tu agente allí.
```

### Verificación

```bash
python3 editoria/scripts/check_env.py
```

Salida esperada: `ENTORNO LISTO`. Si falta algo crítico, el script lo reporta y sugiere el fix.

## ⚙️ Prerrequisitos

| Herramienta | Versión mínima | Propósito |
|---|---|---|
| Python | 3.9+ | Todos los motores (`render_plan.py`, `voz_off.py`, `musica.py`) |
| FFmpeg | 4.4+ | Render, mezcla, codificación. Mejor con libvpx-vp9 / prores_ks |
| Pillow | 10+ | Renderizado PIL (motor Python) |
| NumPy | 1.26+ | Mezcla y procesado de audio |
| Whisper local | opcional | `alinear.py` (word-level alignment) — whisper.cpp / faster-whisper / openai-whisper en cascada |
| ElevenLabs API key | opcional | TTS y música con IA — `$ELEVENLABS_API_KEY` (nunca en la skill) |
| Remotion 4 | opcional | Animación HTML/CSS/JS programática (requiere Node 22+, React 19) |
| HyperFrames | opcional | Plantillas HTML deterministas (requiere Node 22+) |

Instalación detallada por SO: `editoria/references/instalacion.md`.

## 🎬 Ejemplos de uso

### Ejemplo 1 — Anuncio por plan (flujo principal)

**Usuario:**
```
Hazme un anuncio de 30 segundos para mi producto
```

**Agente:**
```
Voy a producir un anuncio por plan. Necesito saber:
1. ¿Marca o sin marca? (Si marca, paso su brand pack)
2. ¿Qué debe decir el guion?
3. ¿Plataforma objetivo? (YouTube Shorts / TikTok / Reels)

[Plan] escribo plan.json con 5 escenas tipo "apertura" + "canales" + "listo"
[Render] python scripts/render_plan.py plan.json -o anuncio.mp4 --blur 5
[Voice-over] python scripts/voz_off.py plan.json -o voz.mp3
[Music] python scripts/musica.py gen --prompt "modern upbeat" --dur 30 -o mus.mp3
[Mix] python scripts/musica.py mix -v anuncio.mp4 -a voz.mp3 -m mus.mp3 -o final.mp4
[QA] python scripts/auto_qa.py final.mp4

Listo: final.mp4 (1080x1920 @30fps, H.264, voice + música con ducking)
```

### Ejemplo 2 — Resumen de reunión a partir de transcripción

**Usuario:**
```
Resume esta transcripción de la reunión en un video vertical
```

**Agente:**
```
[Ingest] leo la transcripción (.txt / .srt / JSON de Whisper)
[Plan] 6-8 momentos fuertes verificados contra la fuente
        usando references/scoring-shorts.md
[Estilo] elegir de references/estilos.md (resumen-animado)
[Build] pipeline-resumen.md + tecnicas-video.md (qué técnica usar)
[QA] contact_sheet.py + auto_qa.py

Resumen vertical listo. Sin texto inventado (cero confabulation).
```

### Ejemplo 3 — Mejorar un video existente

**Usuario:**
```
Mejora este video y hazlo más cinematográfico
```

**Agente:**
```
[Diagnóstico] auto_qa.py --video existing.mp4
              detectaré frames negros, congelados, flashes
[Plan] plan de mejoras (resortes, motion blur, audio, color)
[Composición] aplicar grade preset (subtle / neutral_punch / warm_cinematic)
[QA] re-renderizar y verificar en contact sheet
```

### Ejemplo 4 — Shorts verticales desde un video largo

**Usuario:**
```
Sácame 3 shorts verticales para TikTok de mi podcast de 1h
```

**Agente:**
```
[Pipeline A] shorts_plan.py con 3 segmentos memorables
[Pipeline B] verticalizar y quemar subtítulos karaoke
[Pipeline C] QA por plano + safe zone para TikTok

Resultado: 3 shorts en 1080x1920 @30fps, con subtítulos karaoke.
```

## 🛠️ Capacidades de la skill

### Render por plan (`scripts/render_plan.py`)

| Capacidad | Descripción |
|---|---|
| Plan declarativo | `plan.json` con 28 tipos de escena, tiempos absolutos, `at` por elemento, `voz` por escena |
| Catálogo unificado | 28 escenas compuestas con primitivas DRY (cero lógica duplicada) |
| `--blur 5` | Motion blur de obturador 180° en la entrega final |
| `--force` | Re-renderiza todo (sin él retoma donde iba) |
| `--datos` | CSV-driven (auto-fit de fuente, wrap, line break) |
| `--jobs N` | Render multi-thread |
| `mancha`-friendly | Resume incremental de renders interrumpidos |
| `-r` aicolor | Color BT.709 exacto, no BT.601 |
| Safe zone | `vela:` recorte para Reels dimensiones / Safe zones por plataforma |
| Multi-image | Soporta `image` (PIL) y `video` (ffmpeg overlay con PTS) |

### Voz en off y música (`scripts/voz_off.py`, `scripts/musica.py`, `scripts/alinear.py`)

| Capacidad | Descripción |
|---|---|
| TTS ElevenLabs | 12 voces por idioma (`es`, `en`); default según idioma del usuario |
| Cache content-addressed | md5(text+voice+model) — no re-sintetiza idénticos |
| Ducking sidechain | Música baja cuando hay voz; medible con `medir_mezcla.py` |
| Alineación palabra-a-palabra | `alinear.py` (Whisper + SequenceMatcher + energía) |
| Música procedural | Genera o usa la banda de YouTube Audio Library |
| SFX procedural | `sfx.py` sintetiza click, pop, drop, whoosh, fade_out, ding, thud, tick, swell |
| Audiogramas | Con waveform y peaks |
| Subtítulos karaoke | Por palabra, con animación de la activa |

### Brand packs (marca-blanca) — `brand/*.json`

- DragonJAR es **un pack de ejemplo**, no la marca por defecto
- Sin pack, modo libre con criterio cinematográfico puro
- La identidad NUNCA está hardcoded en el código
- `-r` `aplly_brand()` inyecta color, fuentes, isotipo, voces según pack

### QA y validación

| Capacidad | Descripción |
|---|---|
| Auto-QA máquina | `auto_qa.py` detecta black_frame, frozen, flash, clipping |
| Contact sheet | `contact_sheet.py` genera filmstrips + waveform para revisión visual |
| Métricas de animación | `medir_animacion.py` puntúa 9 ejes, log a `metricas/historial.jsonl` |
| Rúbrica de premios | 8 ejes (idea, dramaturgia, animación, composición, sistema visual, sonido, verdad, acabado) |
| Delivery check | `delivery_check.py` valida codec, LUFS, aspect contra YouTube/TikTok/Reels |
| Loudness check | `loudness.py` dos pasadas, dos-paso linear — `-14 LUFS / -1.5 dBTP` |
| QA de fotosensibilidad | Cuenta flashes, picos, evita disparadores |

### Post-producción (kit `ffmpeg_tools/`)

| Capacidad | Descripción |
|---|---|
| Montaje | 18 operaciones (join, cut, fade, PiP, etc.) — `montaje.py` |
| Subtítulos | `caption.py` burn-in SRT/ASS con karaoke y safe zone |
| Color | `grade.py` con presets (subtle, neutral_punch, warm_cinematic, none) + HDR→SDR |
| EDL | `aplicar_edl.py` lossless concat + 30ms fades + PTS shifts |
| Loudness | `loudness.py` dos pasadas |
| Beat sync | `beat_grid.py` + `beat_sync.py` ajustan cortes a la rejilla |
| Chapters | `chapters.py` genera capítulos YouTube |
| Hardlinks | `verificar_ritmo.py` mide cadencia, pausas, ráfagas |

### Remotion / multimedia

- **Remotion 4** opcional (`references/remotion.md`): composición React → MP4 con `npx remotion render`. Requiere Node 22+, React 19.
- **HyperFrames** opcional (`references/hyperframes.md`): plantillas HTML deterministas → MP4. Requiere Node 22+.
- **Manim** opcional: gráficos matemáticos, state machines, ecuaciones.

## 📂 Estructura de la skill

```
EditorIA/
├── README.md                          # Este archivo
├── README.en.md                       # English version
├── LICENSE                             # MIT
├── editoria/                             # Contenido de la skill (todo aquí)
│   ├── SKILL.md                       # Definición + Language Rule + selector
│   ├── scripts/                       # 25 motores raíz + 19 en ffmpeg_tools/
│   │   ├── render_plan.py             # Motor principal de render por plan
│   │   ├── voz_off.py                 # ElevenLabs TTS
│   │   ├── musica.py                  # ElevenLabs Music + ducking
│   │   ├── alinear.py                 # Word-level voice alignment (Whisper)
│   │   ├── check_env.py               # Preflight (valida el entorno)
│   │   ├── auto_qa.py                 # QA máquina
│   │   ├── contact_sheet.py           # Contact sheet filmstrip
│   │   ├── medir_animacion.py          # Métricas de animación (9 ejes)
│   │   ├── medir_mezcla.py            # QA numérico del ducking
│   │   ├── verificar_ritmo.py         # Anti-slideshow
│   │   ├── poster_frame.py            # Frame 0 poster
│   │   ├── sfx.py                     # SFX procedural (9 tipos)
│   │   ├── beat_grid.py                # Beat detection
│   │   ├── beat_sync.py               # Cortar en beats
│   │   ├── beat_file.py               # Bajo nivel para audio
│   │   ├── chapters.py                # YouTube chapters
│   │   ├── sfx.py                     # (ver arriba)
│   │   ├── audio_viz.py               # Waveform visualization
│   │   ├── retakes.py                  # Detección de false starts
│   │   ├── registrar_aprendizaje.py   # Log de learnings (RSI)
│   │   ├── auditar_plan.py            # Audita un plan.json
│   │   ├── scripts/                   # (legacy, mantener)
│   │   ├── ffmpeg_tools/              # 19 módulos de post-producción
│   │   │   ├── montaje.py             # 18 operaciones de edición
│   │   │   ├── caption.py             # Subtítulos burn-in
│   │   │   ├── grade.py               # Color grading + presets
│   │   │   ├── loudness.py            # -14 LUFS / -1.5 dBTP
│   │   │   ├── delivery_check.py      # Verificar plataforma
│   │   │   ├── alinear.py             # (igual a raíz)
│   │   │   ├── aplicar_edl.py         # EDL → MP4
│   │   │   ├── shorts_plan.py         # Generar shorts verticales
│   │   │   ├── grade.py               # (igual al upper)
│   │   │   ├── caption.py             # (igual al upper)
│   │   │   ├── beat_grid.py           # (igual al upper)
│   │   │   ├── beat_sync.py           # (igual al upper)
│   │   │   ├── chapters.py            # (igual al upper)
│   │   │   ├── thumbnail.py           # Thumbnail con tipografía
│   │   │   ├── verticalizar.py        # Vertical desde horizontal
│   │   │   ├── artesanal.py           # Modo artesanal (cards + imágenes)
│   │   │   ├── scenes.py              # Editor de escenas
│   │   │   ├── variants.py            # Variantes (diferentes aspect ratios)
│   │   │   ├── look.py                # Look LUT
│   │   │   ├── speedramp.py           # Time-lapse
│   │   │   ├── silencio.py            # Quitar silencios
│   │   │   ├── _comun.py              # Helpers DRY compartidos
│   │   │   └── _plataforma.py         # Abstracciones de SO
│   │   └── validate_skill.py          # Validador de la skill
│   ├── references/                    # 45 referencias
│   │   ├── instalacion.md             # Por SO (Win/macOS/Linux)
│   │   ├── escenas.md                 # Catálogo de 28 escenas
│   │   ├── escenas-extendidas.md      # Conceptos portables
│   │   ├── plan-video.md              # Schema del plan.json
│   │   ├── estilos.md                 # Catálogo de estilos visuales
│   │   ├── tecnicas-video.md          # Catálogo 2025-2026 de técnicas (FRESH/STANDARD/TIRED)
│   │   ├── scoring-shorts.md          # Rúbrica de selección de momentos
│   │   ├── fluidez.md                 # Reglas de fluidez
│   │   ├── animacion.md               # Oficio de animación (12 principios)
│   │   ├── coherencia-espacial.md     # Alineación y safe zones
│   │   ├── montaje.md                 # 18 operaciones
│   │   ├── cine.md                    # Recetas cinematográficas
│   │   ├── modos-rapidos.md           # Quick recipes (kinetic, montage, cut)
│   │   ├── modos-produccion.md        # Modos Real / producto / hybrid
│   │   ├── brand-packs.md             # Spec del brand pack
│   │   ├── pipeline-resumen.md        # Pipeline de resumen
│   │   ├── sound.md / sonido.md       # Diseño sonoro
│   │   ├── tonos.md / tonos.md        # 6 tonos (demo, resumen, trailer, parodia, caos)
│   │   ├── musica.md                   # Música de fondo
│   │   ├── audio.md                   # Beat grid + SFX
│   │   ├── sfx.md                      # Doctrina SFX (tono→energía, momento→sonido, timing)
│   │   ├── thumbnails.md              # Thumbnails conceptuales
│   │   ├── share-copy.md              # Caption canónico
│   │   ├── principios.md              # 3 pilares: coherencia, armonía, efectos deslumbrantes
│   │   ├── directión.md / direccion.md # Dirección con métricas
│   │   ├── dramaturgia.md             # Estructura de fábula
│   │   ├── ritmo.md                   # Anti-slideshow
│   │   ├── checklist-qa.md            # QA checklist
│   │   ├── auto-mejora.md             # Protocolo de self-improvement
│   │   ├── auto-qa.md                 # Loop de QA
│   │   ├── lecciones-produccion.md    # Lecciones del sistema original
│   │   ├── remotion.md                # Integración Remotion (opcional)
│   │   ├── hyperframes.md             # Integración HyperFrames (opcional)
│   │   ├── prompt-motion-graphics.md  # Prompts verbatim para motion graphics
│   │   ├── recetas-ai-video.md        # Recetas de IA (2 comentarios)
│   │   ├── scoring-shorts.md          # (ver arriba)
│   │   ├── tecnicas-reutilizables.md  # Técnicas reutilizables
│   │   ├── cli-contract.md            # Contrato CLI de las herramientas
│   │   ├── instalacion.md             # (ver arriba)
│   │   ├── brand-packs.md             # (ver arriba)
│   │   ├── arquitectura.md              # Mapa de scripts
│   │   ├── i18n.md                    # Política de idioma (Language Rule)
│   │   ├── media-hard-rules.md        # Mapeo de Hard Rules de media-tooling
│   │   ├── scene-patterns-from-internet.md # Catálogo de fuentes externas
│   │   ├── rubrica-premios.md         # Rúbrica de premios 8 ejes
│   │   ├── video-real.md              # Grabación → post (flujo camera-first)
│   │   └── thumbnails.png                # Thumbnail sample
│   ├── references/schemas/             # 2 JSON schemas
│   │   ├── plan-schema.json
│   │   └── shorts-plan-schema.json
│   ├── assets/
│   │   └── fonts/                     # Plus Jakarta Sans + Montserrat (OFL)
│   ├── brand/                         # Marca-blanca: packs solo aquí
│   │   ├── dragonjar.json             # Pack de ejemplo
│   │   └── assets/                    # Assets de marca (logos, etc.)
│   ├── film/                          # Música de ejemplo para film de marca
│   │   ├── musica_film.mp3
│   │   ├── musica_film_v2.mp3
│   │   └── musica_demo.mp3
│   └── metricas/                      # Métricas de la skill (RSI)
│       └── historial.jsonl
└── .gitignore                         # Restringe el repo a editoria/ y READMEs
```

## 🎯 Frases trigger

La skill se activa cuando el usuario dice:

- «hazme un video» / «create me a video»
- «resume esta reunión» / «summarize this meeting»
- «edita este anuncio» / «edit this ad»
- «mejora este video» / «improve this video»
- «ponle música» / «add music»
- «créame un reel» / «create me a reel»
- «necesito una pieza para redes» / «I need a piece for social»
- «convierte esta transcripción en video» / «turn this transcript into a video»
- «el video está soso, dale vida» / «the video is bland, give it life»
- «hazlo más dinámico» / «make it more dynamic»
- «quiero un bumper de marca» / «I want a brand bumper»

NO debe activarse con: «edita este documento», «mejora este texto»,
«hazme una imagen», «resume este PDF en texto», «qué video me recomiendas».

## ⚠️ Limitaciones

1. **WhatsApp API**: el cliente de WhatsApp Business tiene rate limits; respeta `--cooldown=120` en mensajes.
2. **Localización ES + client-side hooks**: el bypass es client-side; server-side attestation (Play Integrity, SafetyNet, ApprovRoot) requiere un test tenant autorizado o mock verifier.
3. **FFmpeg capabilities**: si `libvpx-vp9` o `prores_ks` no están disponibles, el validator avisa pero no falla (es el equipo, no la skill).
4. **Línea de rojos intencional**: sin librerías externas (Remotion / HyperFrames) se utilizan React+CSS, no dependencias más allá del sistema.

> **Disclaimer**: Esta skill está pensada para uso legítimo. **Nota:** los hooks
> client-side no falsifican veredictos de attestation server-side. Para ApprovRoot,
> Play Integrity, SafetyNet, o controles backend-enforced, usa un test tenant
> autorizado, mock verifier o configuración de laboratorio aprobada.

## 🔁 Source of truth

Este repositorio (rama `main`) es la **fuente canónica** de la skill. Si
mantienes copias en directorios de skills (por ejemplo
`~/.claude/skills/editoria/` o `~/.config/opencode/skills/editoria/`),
resincronízalas después de un pull:

```bash
git -C /path/to/EditorIA pull
rsync -a --delete --exclude '.git' --exclude '__pycache__' --exclude '.pytest_cache' \
  /path/to/EditorIA/ ~/.claude/skills/editoria/
```

Las copias no sincronizadas se quedan desactualizadas en silencio.

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Áreas que necesitan expansión:

- **Catálogo de técnicas** (`references/tecnicas-video.md`): nuevas técnicas validadas en producción
- **Scenes adicionales**: si necesitas un patrón nuevo, sigue `references/scene-patterns-from-internet.md`
- **Voice roster** (`scripts/voz_off.py VOCES`): añade voces ElevenLabs para nuevos idiomas
- **Brand packs** (`brand/`): nuevos packs de ejemplo
- **Validator** (`scripts/validate_skill.py`): nuevos checks de calidad

## 📄 Licencia

MIT — Ver [`LICENSE`](LICENSE) para detalles.

## 👨💻 Autor

**Jaime Andrés Restrepo** — [DragonJAR SAS](https://www.DragonJAR.org)

---

**⚠️ Nota de privacidad**: los scripts usan `$ELEVENLABS_API_KEY` desde tu entorno. **Nunca**
incluyas credenciales en `plan.json`, `brand/*.json`, ni en archivos del proyecto.
La skill no hace confabulación: las cifras, nombres y citas vienen de la fuente
o se marcan como `[PENDIENTE]` para que las completes.