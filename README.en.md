# EditorIA

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.9.0-green.svg)](editoria/SKILL.md)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org)
[![Platforms](https://img.shields.io/badge/Win%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](#installation)

> **AI video editing Swiss army knife**, packaged as a Claude *skill*.
> Create, edit, summarize and improve videos (`.mp4`): animated meeting summaries, kinetic typography, plan-based ads, cinematic films, and vertical pieces for social media — for any brand or none.

🇪🇸 [Versión en español](README.md)

## 🎯 What this skill does

EditorIA turns an agent into a complete video editor. It can:

- **Plan-driven render** (`plan.json` → `mp4`) with **39 scene types** — `apertura`, `canales`, `chat`, `leads`, `handoff`, `pago`, `listo`, `pildoras`, `hoy`, `recupera`, `remate`, `final`, `medianoche`, `oferta`, `countdown`, `demo`, `rotulo_inferior`, `bars`, `gauge`, `ranking`, `stats`, `timeline`, `quote`, `versus`, `confetti`, `typewriter`, `kenburns`, `pasos`, `hero`, `bento`, `buscador`, `notificacion`, `comentario`, `pie`, `orbita`, `audiowave`, `callout`, `index` and `orbOpen`.
- **Visual composition**: scene with `--datos` (CSV), scene on template × table, audiograms, word-level karaoke, exact BT.709 color, alpha overlays and rotation.
- **Animation craft**: fluidity motor (springs, live background, anticipated exits), 180° shutter motion blur on delivery (`--blur 5`), **20 DRY primitives** (`barra_h`, `cuenta_up`, `arco`, `particulas`, `cuadricula`, `linewrap`, `tarjeta_cristal`, `boton_halo`, `insignia_3d`, etc.) that compose all 39 scenes.
- **Voice-over and music with AI**: ElevenLabs TTS with content-addressed cache, music with sidechain ducking, word-level alignment (`alinear.py`) on local Whisper (whisper.cpp / faster-whisper / openai-whisper cascade).
- **White-label brand packs**: identity lives in `brand/*.json` (DragonJAR included as example). Without a pack, free mode with pure cinematic criteria. Identity NEVER hardcoded in the code.
- **Automated QA**: machine (`auto_qa.py` detects black frames, frozen, flashes, audio) + agent visual review on contact sheet. 8-axis award rubric (none below 4/5).
- **Delivery verification**: `delivery_check.py` validates codec, LUFS, aspect against YouTube/TikTok/Reels.
- **Clone or adapt a reference video** (method inspired by Hypit): ingest a file or link (`clonar_video.py analizar` / `referencia.py`, yt-dlp), word-timed transcript, frame grids with the spoken words under each tile (`contact_sheet.py --palabras --alrededor "phrase"`), project memory (`proyecto.py`: BRIEF, TREATMENT, PROGRESS, TIMELINE) and transformation lenses (`references/referencia-video.md`); variants with `clonar_video.py variar`.
- **Formats**: two-person podcast, street interview, ranking, talking head, presenter-led explainer, narration and short drama (`references/formatos.md`), with split screen (`montaje.py dividir`) and speaker-colored captions (`caption.py --hablantes`).
- **Voice duration by syllables** before paying for TTS (`speech_estimate.py`: numbers counted as spoken, es/en, calibratable against a real voice), the single source for `auditar_plan.py`.
- **Art direction instead of defaults**: `direccion_arte.py` deals 3 directions from a library (WCAG-checked palette, typography, motion personality, matching scenes, what to avoid); the agent picks the one that can carry something only the subject has (competitor test) and `elegir` writes `SISTEMA.md` + a style pack usable with `--brand`. `auditar_plan.py` warns about generated-look «tells» (jargon, emoji as icons, placeholders, invented proof, repeated scenes, metronome cadence). Process in `references/direccion-de-arte.md`.
- **Scoped refinement passes** (bolder, calmer, distill, polish, animate, adapt...) and **a fifteen-pass critique** with caps in the rubric: look before measuring (`references/pasadas.md`, `references/auto-qa.md`).
- **Optional Remotion** (Node 22+, React 19) when programmatic HTML/CSS/JS animation is needed.
- **Optional HyperFrames** (Node 22+) for deterministic HTML templates.

> **Important:** the Python motor code (PIL + ffmpeg) **does NOT require Node** — runs on any machine with ffmpeg. Remotion/HyperFrames are opt-in for specific cases.

## 📦 Installation

> **Why the skill lives in `editoria/` instead of the repo root (`Skill-for-Claude.txt`)**: the official Claude Skills guide prohibits placing `README.md` inside the skill folder and requires the skill folder name to be in `kebab-case` matching `name: editoria` with no capital letters. Therefore, the repository root (`EditorIA/`) hosts the GitHub READMEs while the installable skill folder lives in `editoria/` (and packaged as `editoria.zip`).

### Option 1 — Upload to Claude.ai (ready-made ZIP)

1. Open **Claude.ai > Settings > Capabilities > Skills**.
2. Click **Upload skill** and select `editoria.zip` from this repository (or zip the `editoria/` folder).

### Option 2 — Install in Claude Code / OpenCode

```bash
git clone https://github.com/DragonJAR/EditorIA.git
mkdir -p ~/.claude/skills/
cp -R EditorIA/editoria ~/.claude/skills/editoria
# For OpenCode / ~/.agents:
# mkdir -p ~/.agents/skills/ && cp -R EditorIA/editoria ~/.agents/skills/editoria
```

### Verification

```bash
python3 editoria/scripts/check_env.py
```

Expected output: `ENTORNO LISTO`. If anything critical is missing, the script reports it and suggests the fix.

## ⚙️ Prerequisites

| Tool | Min version | Purpose |
|---|---|---|
| Python | 3.9+ | All engines (`render_plan.py`, `voz_off.py`, `musica.py`) |
| FFmpeg | 4.4+ | Render, mixing, encoding. Better with libvpx-vp9 / prores_ks |
| Pillow | 10+ | PIL rendering (Python motor) |
| NumPy | 1.26+ | Audio mix and processing |
| Local Whisper | optional | `alinear.py` (word-level alignment) — whisper.cpp / faster-whisper / openai-whisper cascade |
| ElevenLabs API key | optional | TTS and music — `$ELEVENLABS_API_KEY` (never in the skill) |
| Remotion 4 | optional | Programmatic HTML/CSS/JS animation (requires Node 22+, React 19) |
| HyperFrames | optional | Deterministic HTML templates (requires Node 22+) |

OS-specific install details: `editoria/references/instalacion.md`.

## 🎬 Usage examples

### Example 1 — Ad by plan (main flow)

**User:**
```
Make me a 30-second ad for my product
```

**Agent:**
```
I'll produce an ad by plan. Need to know:
1. Brand or no brand? (If brand, pass its brand pack)
2. What does the script say?
3. Target platform? (YouTube Shorts / TikTok / Reels)

[Plan] write plan.json with 5 scenes ("apertura" + "canales" + "listo" type)
[Render] python scripts/render_plan.py plan.json -o ad.mp4 --blur 5
[Voice-over] python scripts/voz_off.py plan.json -o voz.mp3
[Music] python scripts/musica.py gen --prompt "modern upbeat" --dur 30 -o mus.mp3
[Mix] python scripts/musica.py mix -v ad.mp4 -a voz.mp3 -m mus.mp3 -o final.mp4
[QA] python scripts/auto_qa.py final.mp4

Done: final.mp4 (1080x1920 @30fps, H.264, voice + music with ducking)
```

### Example 2 — Meeting summary from transcript

**User:**
```
Summarize this meeting transcript into a vertical video
```

**Agent:**
```
[Ingest] read the transcript (.txt / .srt / Whisper JSON)
[Plan] 6-8 strong moments verified against the source
        using references/scoring-shorts.md
[Style] pick from references/estilos.md (resumen-animado)
[Build] pipeline-resumen.md + tecnicas-video.md (which technique to use)
[QA] contact_sheet.py + auto_qa.py

Vertical summary ready. No invented text (zero confabulation).
```

### Example 3 — Improve an existing video

**User:**
```
Improve this video and make it more cinematic
```

**Agent:**
```
[Diagnostics] auto_qa.py --video existing.mp4
              detect black frames, frozen, flashes
[Plan] improvement plan (springs, motion blur, audio, color)
[Composition] grade preset (subtle / neutral_punch / warm_cinematic)
[QA] re-render and verify on contact sheet
```

### Example 5 — Clone a reference video

**User:**
```
Make one like this https://www.tiktok.com/@x/video/123 but for my app
```

**Agent:**
```
[Project] proyecto.py ~/videos/app --referencia "https://..."
[Ingest]  clonar_video.py analizar --url ... → alinear.py (word timings)
[Read]    contact_sheet.py --cada 1 --palabras ... → ANALYSIS.md + TIMELINE.md
[Adapt]   TRATAMIENTO.md: keep each system's role, recreate its form for the app
[Make]    plan.json anchored to the new script's words → render → compare by function
```

### Example 4 — Vertical shorts from a long video

**User:**
```
Make me 3 vertical shorts for TikTok from my 1h podcast
```

**Agent:**
```
[Pipeline A] shorts_plan.py with 3 memorable segments
[Pipeline B] verticalize and burn word-karaoke subtitles
[Pipeline C] per-clip QA + safe zone for TikTok

Result: 3 shorts at 1080x1920 @30fps, with karaoke subtitles.
```

## 🛠️ Skill capabilities

### Plan-driven render (`scripts/render_plan.py`)

| Capability | Description |
|---|---|
| Declarative plan | `plan.json` with 39 scene types, absolute times, `at` per element, `voz` per scene |
| Unified catalog | 39 scenes composed with 20 DRY primitives (zero duplicated logic) |
| `--blur 5` | 180° shutter motion blur on final delivery |
| `--force` | Re-render everything (without it resumes where it left off) |
| `--datos` | CSV-driven (auto-fit font, wrap, line break) |
| `--jobs N` | Multi-process rendering with automatic sandbox fallback |
| Resumes incremental | Continues interrupted renders |
| `-r` recolor | Exact BT.709 color, not BT.601 |
| Safe zone | Cropping for Reels dimensions / safe zones per platform |
| Multi-image | Supports `image` (PIL) and `video` (ffmpeg overlay with PTS) |

### Voice-over and music (`scripts/voz_off.py`, `scripts/musica.py`, `scripts/alinear.py`)

| Capability | Description |
|---|---|
| ElevenLabs TTS | 12 voices by language (`es`, `en`); default per user's writing language |
| Content-addressed cache | md5(text+voice+model) — no re-synth for identical |
| Sidechain ducking | Music lowers during voice; measurable with `medir_mezcla.py` |
| Word-level alignment | `alinear.py` (Whisper + SequenceMatcher + energy) |
| Procedural music | Generate or use YouTube Audio Library bands |
| Procedural SFX | `sfx.py` synthesizes click, pop, drop, whoosh, fade_out, ding, thud, tick, swell |
| Audiograms | With waveform and peaks |
| Karaoke subtitles | Per word, with active-word animation |

### Brand packs (white-label) — `brand/*.json`

- DragonJAR is **one example pack**, not the default brand
- Without a pack, free mode with pure cinematic criteria
- Identity NEVER hardcoded in code
- `aplicar_brand()` injects color, fonts, isotipo, voices from the pack

### QA and validation

| Capability | Description |
|---|---|
| Machine auto-QA | `auto_qa.py` detects black_frame, frozen, flash, clipping |
| Contact sheet | `contact_sheet.py` builds grids by range/interval/every frame, with the spoken words under each tile (`--palabras`, `--alrededor "phrase"`) |
| Animation metrics | `medir_animacion.py` scores 9 axes, logs to `metricas/historial.jsonl` |
| Award rubric | 8 axes (idea, dramaturgy, animation, composition, visual system, sound, truth, finish) |
| Delivery check | `delivery_check.py` validates codec, LUFS, aspect against YouTube/TikTok/Reels |
| Loudness check | `loudness.py` two-pass linear — `-14 LUFS / -1.5 dBTP` |
| Photosensitivity QA | Counts flashes, peaks, prevents triggers |

### Post-production (`ffmpeg_tools/` kit)

| Capability | Description |
|---|---|
| Montaje | 19 operations (join, cut, fade, PiP, split screen, etc.) — `montaje.py` |
| Subtitles | `caption.py` burn-in SRT/ASS with karaoke, safe zone and per-speaker color (`--hablantes`) |
| Color | `grade.py` with presets (subtle, neutral_punch, warm_cinematic, none) + HDR→SDR |
| EDL | `aplicar_edl.py` lossless concat + 30ms fades + PTS shifts |
| Loudness | `loudness.py` two passes |
| Beat sync | `beat_grid.py` (BPM, bars and energy-based song sections: one visual language per section) + `beat_sync.py` align cuts to beat grid |
| Chapters | `chapters.py` generates YouTube chapters |
| Rhythm | `verificar_ritmo.py` measures cadence, pauses, bursts |

### Remotion / multimedia

- **Remotion 4** optional (`references/remotion.md`): React composition → MP4 with `npx remotion render`. Needs Node 22+, React 19.
- **HyperFrames** optional (`references/hyperframes.md`): deterministic HTML templates → MP4. Needs Node 22+.
- **Manim** optional: math graphics, state machines, equations.

## 📂 Skill structure

```
EditorIA/
├── README.md                          # Spanish README
├── README.en.md                       # This file (English)
├── LICENSE                            # MIT
├── editoria.zip                       # Ready-to-upload package for Claude.ai
├── editoria/                          # Skill folder (kebab-case == name: editoria)
│   ├── SKILL.md                       # Definition + YAML frontmatter + main workflow
│   ├── scripts/                       # 38 root + 19 in ffmpeg_tools/ + 28 in _tests/ = 85 scripts
│   │   ├── render_plan.py             # Main plan renderer (39 scenes)
│   │   ├── voz_off.py                 # ElevenLabs TTS
│   │   ├── musica.py                  # ElevenLabs Music + ducking
│   │   ├── alinear.py                 # Word-level voice alignment (Whisper)
│   │   ├── check_env.py               # Preflight (validates environment)
│   │   ├── auto_qa.py                 # Machine QA
│   │   ├── contact_sheet.py           # Filmstrip contact sheet
│   │   ├── medir_animacion.py         # Animation metrics (9 axes)
│   │   ├── medir_mezcla.py            # Numeric QA of ducking
│   │   ├── verificar_ritmo.py         # Anti-slideshow
│   │   ├── poster_frame.py            # Frame 0 poster
│   │   ├── sfx.py                     # Procedural SFX (9 types)
│   │   ├── beat_grid.py               # Beat detection
│   │   ├── beat_sync.py               # Cut at beats
│   │   ├── beat_file.py               # Low-level audio helper
│   │   ├── chapters.py                # YouTube chapters
│   │   ├── audio_viz.py               # Waveform visualization and audiograms
│   │   ├── retakes.py                 # False start detection
│   │   ├── registrar_aprendizaje.py   # Learning logs
│   │   ├── auditar_plan.py            # Plan.json audit
│   │   ├── speech_estimate.py         # Spoken duration by syllables (pre-TTS)
│   │   ├── referencia.py              # Reference ingestion (file or link)
│   │   ├── clonar_video.py            # Analyze and vary reference videos
│   │   ├── proyecto.py                # Project memory (brief, treatment, progress)
│   │   ├── direccion_arte.py          # Deal, choose and verify the visual direction
│   │   ├── data/direcciones.json      # Library of 17 art directions
│   │   ├── film_marca.py              # Cinematic brand film v1
│   │   ├── film_marca_v2.py           # Cinematic brand film v2
│   │   ├── _film.py                   # Shared film utilities
│   │   ├── galeria.py                 # Visual suite for all 39 scenes
│   │   ├── validate_skill.py          # Deterministic skill validator
│   │   ├── demo_plan.json             # Sample plan
│   │   ├── escenas_muestra.json       # Canonical samples for all 39 scenes
│   │   ├── _tests/                    # Unit test suite (unittest)
│   │   │   ├── test_chapters.py
│   │   │   ├── test_core_and_scenes.py
│   │   │   ├── test_speech_estimate_cifras.py
│   │   │   ├── test_caption_hablantes.py
│   │   │   ├── test_referencia.py
│   │   │   ├── test_beat_secciones.py
│   │   │   └── test_direccion_arte.py
│   │   └── ffmpeg_tools/              # 19 post-production modules
│   │       ├── montaje.py             # 19 editing operations
│   │       ├── caption.py             # Subtitle burn-in and karaoke
│   │       ├── grade.py               # Color grading + presets
│   │       ├── loudness.py            # -14 LUFS / -1.5 dBTP
│   │       ├── delivery_check.py      # Platform verification
│   │       ├── _delivery.py           # Platform specification table
│   │       ├── aplicar_edl.py         # EDL → MP4
│   │       ├── shorts_plan.py         # Vertical shorts generator
│   │       ├── thumbnail.py           # Typography thumbnail
│   │       ├── verticalizar.py        # Horizontal → vertical
│   │       ├── artesanal.py           # Tactile finish (grain, paper, flicker)
│   │       ├── scenes.py              # Scene detection
│   │       ├── variantes.py           # Hook × body A/B variants
│   │       ├── look.py                # QA contact sheets
│   │       ├── speedramp.py           # Speed ramps
│   │       ├── silence.py             # Silence removal
│   │       ├── transcribir.py         # Local ASR → SRT + JSON
│   │       ├── _comun.py              # Shared DRY helpers
│   │       └── _plataforma.py         # OS abstractions
│   ├── references/                    # 55 references in kebab-case.md
│   │   ├── instalacion.md             # Per OS (Win/macOS/Linux)
│   │   ├── escenas.md                 # Catalog of 39 scenes
│   │   ├── escenas-extendidas.md      # Portable concepts
│   │   ├── plan-video.md              # plan.json schema
│   │   ├── shorts-plan-schema.md      # shorts-plan.json schema
│   │   ├── estilos.md                 # Visual styles catalog
│   │   ├── tecnicas-video.md          # 2025-2026 techniques catalog
│   │   ├── scoring-shorts.md          # Moment selection rubric
│   │   ├── fluidez.md                 # Fluidity rules
│   │   ├── animacion.md               # Animation craft (12 principles)
│   │   ├── coherencia-espacial.md     # Alignment and safe zones
│   │   ├── montaje.md                 # 19 operations
│   │   ├── referencia-video.md        # Clone/adapt a reference
│   │   ├── formatos.md                # What carries each format
│   │   ├── direccion-de-arte.md       # Idea from the subject, modes, dealt directions, tells
│   │   ├── pasadas.md                 # Scoped refinements
│   │   ├── cine.md                    # Cinematic recipes
│   │   ├── modos-rapidos.md           # Quick recipes (kinetic, montage, cut)
│   │   ├── modos-produccion.md        # Real / animated / hybrid modes
│   │   ├── brand-packs.md             # Brand pack spec
│   │   ├── pipeline-resumen.md        # Summary pipeline
│   │   ├── sonido.md                  # Sound design and TTS voices
│   │   ├── tonos.md                   # 6 tones (demo, resumen, anuncio, trailer, parodia, caos)
│   │   ├── audio.md                   # Beat grid + SFX
│   │   ├── sfx.md                     # SFX doctrine
│   │   ├── thumbnails.md              # Conceptual thumbnails
│   │   ├── share-copy.md              # Canonical caption
│   │   ├── principios.md              # 3 visual pillars
│   │   ├── direccion.md               # Direction with metrics
│   │   ├── dramaturgia.md             # Dramatic structure
│   │   ├── ritmo.md                   # Anti-slideshow
│   │   ├── checklist-qa.md            # QA checklist
│   │   ├── auto-mejora.md             # Self-improvement protocol
│   │   ├── auto-qa.md                 # QA loop
│   │   ├── lecciones-produccion.md    # Lessons from the original system
│   │   ├── reglas-tecnicas.md         # Technical rendering rules
│   │   ├── capacidades.md             # Capability inventory and fallbacks
│   │   ├── remotion.md                # Remotion integration (optional)
│   │   ├── hyperframes.md             # HyperFrames integration (optional)
│   │   ├── prompt-motion-graphics.md  # Prompts for motion graphics
│   │   ├── recetas-ai-video.md        # Operational AI video recipes
│   │   ├── tecnicas-reutilizables.md  # Reusable techniques
│   │   ├── cli-contract.md            # CLI contract
│   │   ├── arquitectura.md            # Script map
│   │   ├── i18n.md                    # Language policy (Language Rule)
│   │   ├── media-hard-rules.md        # Mapping of Hard Rules from media-tooling
│   │   ├── scene-patterns-from-internet.md # External sources catalog
│   │   ├── rubrica-premios.md         # 8-axis award rubric
│   │   └── video-real.md              # Recording → post (camera-first flow)
│   ├── assets/
│   │   └── fonts/                     # Plus Jakarta Sans + Montserrat (OFL)
│   ├── brand/                         # White-label: packs live here only
│   │   ├── dragonjar.json             # Example pack
│   │   └── assets/                    # Brand assets (logos, etc.)
│   ├── film/                          # Sample music for brand film
│   │   ├── musica_film.mp3
│   │   ├── musica_film_v2.mp3
│   │   └── musica_demo.mp3
│   └── metricas/                      # Skill metrics and regression benchmarks
│       └── historial.jsonl
└── .gitignore                         # Restrict repo to editoria/ and READMEs
```

## 🎯 Trigger phrases

The skill activates when the user says:

- "make me a video"
- "summarize this meeting"
- "edit this ad"
- "improve this video"
- "add music to it"
- "create me a reel"
- "I need a piece for social"
- "turn this transcript into a video"
- "the video is bland, give it life"
- "make it more dynamic"
- "I want a brand bumper"
- "make one like this video"

Should NOT activate on: "edit this document", "improve this text",
"make me an image", "summarize this PDF in text", "what video camera do you recommend".

## ⚠️ Technical limitations

1. **Local rendering dependencies**: the Python engine requires `ffmpeg`/`ffprobe`, `Pillow`, and `NumPy` installed in the active Python interpreter (`python3 editoria/scripts/check_env.py` diagnoses any missing requirement).
2. **Transparency codecs (`libvpx-vp9` / `prores_ks`)**: if the local `ffmpeg` build lacks these encoders, `.webm` or `.mov` alpha overlays emit a warning without affecting standard `.mp4` deliverables.
3. **Optional AI voice, music, and transcription services**: ElevenLabs synthesis requires `$ELEVENLABS_API_KEY` in the environment; word-level alignment (`alinear.py`) uses local Whisper when installed and falls back to character/energy-weighted alignment otherwise.
4. **Optional web engines**: Remotion 4 and HyperFrames are opt-in for programmatic HTML/CSS/React animations and require Node.js 18+/22+.

## 🔁 Source of truth

This repository (`main` branch) is the **canonical source** of the skill. If
you keep copies in skill directories (e.g.
`~/.claude/skills/editoria/` or `~/.config/opencode/skills/editoria/`),
resync them from the `editoria/` subfolder after pulling:

```bash
git -C /path/to/EditorIA pull
rsync -a --delete --exclude '__pycache__' --exclude '.pytest_cache' \
  /path/to/EditorIA/editoria/ ~/.claude/skills/editoria/
```

Unsynchronized copies will silently drift out of date.

## 🤝 Contributing

Contributions are welcome. Areas that need expansion:

- **Technique catalog** (`references/tecnicas-video.md`): new production-validated techniques
- **Additional scenes**: if you need a new pattern, follow `references/scene-patterns-from-internet.md`
- **Voice roster** (`scripts/voz_off.py VOCES`): add ElevenLabs voices for new languages
- **Brand packs** (`brand/`): new example packs
- **Validator** (`scripts/validate_skill.py`): new quality checks

## 🙏 Credits and sources

EditorIA distills methods from open projects and rewrites them for video with
its own tools (it does not copy their code):

- [Hypit](https://github.com/hypit-ai/hypit): reference reading, project memory, formats and voice estimation (own license with conditions; only ideas were taken).
- [tasteskill](https://github.com/Leonxlnx/taste-skill) (MIT): dealt directions, idea from the subject, tells registry and pass-based critique.
- [Impeccable](https://github.com/pbakaus/impeccable) (Apache 2.0): scoped refinements, craft floor, and independent judgment/detector assessment.
- [UI/UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) (MIT): chart-choice criteria, sector reasoning and contrast.

## 📄 License

MIT — See [`LICENSE`](LICENSE) for details.

## 👨💻 Author

**Jaime Andrés Restrepo** — [DragonJAR SAS](https://www.DragonJAR.org)

---

**⚠️ Privacy note**: scripts use `$ELEVENLABS_API_KEY` from your environment. **Never**
include credentials in `plan.json`, `brand/*.json`, or project files.
The skill does no confabulation: numbers, names and quotes come from the
source or are marked `[PENDING]` for you to fill in.