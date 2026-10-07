# EditorIA

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.5.0-green.svg)](SKILL/SKILL.md)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org)
[![Platforms](https://img.shields.io/badge/Win%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](#installation)

> **AI video editing Swiss army knife**, packaged DragonJAR-IA *skill*.
> Create, edit, summarize and improve videos (`.mp4`): animated meeting summaries, kinetic typography, plan-based ads, cinematic films, and vertical pieces for social media — for any brand or none.

🇪🇸 [Versión en español](README.md)

## 🎯 What this skill does

EditorIA turns an agent into a complete video editor. It can:

- **Plan-driven render** (`plan.json` → `mp4`) with **28 scene types** — `apertura`, `canales`, `chat`, `leads`, `handoff`, `pago`, `listo`, `pildoras`, `hoy`, `recupera`, `remate`, `final`, `medianoche`, `oferta`, `countdown`, `demo`, `rotulo_inferior` (13 original ad-explainers) plus `bars`, `gauge`, `ranking`, `stats`, `timeline`, `quote`, `versus`, `confetti`, `typewriter`, `kenburs`, `pasos` (15 unified from validated MIT sources).
- **Visual composition**: scene with `-datos` (CSV), scene on template × table, audiograms, word-level karaoke, exact BT.709 color, alpha overlays and rotation.
- **Animation craft**: fluidity motor (springs, live background, anticipated exits), 180° shutter motion blur on delivery (`--blur 5`), **6 DRY primitives** (`barra_h`, `cuenta_up`, `arco`, `particulas`, `cuadricula`, `linewrap`) that compose all 28 scenes.
- **Voice-over and music with AI**: ElevenLabs TTS with content-addressed cache, music with sidechain ducking, word-level alignment (`alinear.py`) on local Whisper (whisper.cpp / faster-whisper / openai-whisper cascade).
- **White-label brand packs**: identity lives in `brand/*.json` (DragonJAR included as example). Without a pack, free mode with pure cinematic criteria. Identity NEVER hardcoded in the code.
- **Automated QA**: machine (`auto_qa.py` detects black frames, frozen, flashes, audio) + agent visual review on contact sheet. 8-axis award rubric (none below 4/5).
- **Delivery verification**: `delivery_check.py` validates codec, LUFS, aspect against YouTube/TikTok/Reels.
- **Optional Remotion** (Node 22+, React 19) when programmatic HTML/CSS/JS animation is needed.
- **Optional HyperFrames** (Node 22+) for deterministic HTML templates.

> **Important:** the Python motor code (PIL + ffmpeg) **does NOT require Node** — runs on any machine with ffmpeg. Remotion/HyperFrames are opt-in for specific cases.

## 📦 Installation

### Option 1 — Clone into skills directory

```bash
# For Claude Code / OpenCode
cd ~/.agents/skills/
git clone https://github.com/DragonJAR/EditorIA editoria

# For other agents, adapt to your agent's skills path
```

### Option 2 — Install globally

```bash
git clone https://github.com/DragonJAR/EditorIA.git
# The skill lives in SKILL/. Point your agent there.
```

### Verification

```bash
python3 SKILL/scripts/check_env.py
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

OS-specific install details: `SKILL/references/instalacion.md`.

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
| Declarative plan | `plan.json` with 28 scene types, absolute times, `at` per element, `voz` per scene |
| Unified catalog | 28 scenes composed with DRY primitives (zero duplicated logic) |
| `--blur 5` | 180° shutter motion blur on final delivery |
| `--force` | Re-render everything (without it resumes where it left off) |
| `--datos` | CSV-driven (auto-fit font, wrap, line break) |
| `--jobs N` | Multi-thread rendering |
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
| Contact sheet | `contact_sheet.py` generates filmstrips + waveform for visual review |
| Animation metrics | `medir_animacion.py` scores 9 axes, logs to `metricas/historial.jsonl` |
| Award rubric | 8 axes (idea, dramaturgy, animation, composition, visual system, sound, truth, finish) |
| Delivery check | `delivery_check.py` validates codec, LUFS, aspect against YouTube/TikTok/Reels |
| Loudness check | `loudness.py` two-pass linear — `-14 LUFS / -1.5 dBTP` |
| Photosensitivity QA | Counts flashes, peaks, prevents triggers

### Post-production (`ffmpeg_tools/` kit)

| Capability | Description |
|---|---|
| Montaje | 18 operations (join, cut, fade, PiP, etc.) — `montaje.py` |
| Subtitles | `caption.py` burn-in SRT/ASS with karaoke and safe zone |
| Color | `grade.py` with presets (subtle, neutral_punch, warm_cinematic, none) + HDR→SDR |
| EDL | `aplicar_edl.py` lossless concat + 30ms fades + PTS shifts |
| Loudness | `loudness.py` two passes |
| Beat sync | `beat_grid.py` + `beat_sync.py` align cuts to beat grid |
| Chapters | `chapters.py` generates YouTube chapters |
| Rhythm | `verificar_ritmo.py` measures cadence, pauses, bursts |

### Remotion / multimedia

- **Remotion 4** optional (`references/remotion.md`): React composition → MP4 with `npx remotion render`. Needs Node 22+, React 19.
- **HyperFrames** optional (`references/hyperframes.md`): deterministic HTML templates → MP4. Needs Node 22+.
- **Manim** optional: math graphics, state machines, equations.

## 📂 Skill structure

```
EditorIA/
├── README.md                          # This file (Spanish)
├── README.en.md                       # English version
├── LICENSE                             # MIT
├── SKILL/                             # All skill content lives here
│   ├── SKILL.md                       # Definition + Language Rule + engine selector
│   ├── scripts/                       # 25 root + 19 in ffmpeg_tools/ = 44 scripts
│   │   ├── render_plan.py             # Main plan renderer
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
│   │   ├── beat_grid.py                # Beat detection
│   │   ├── beat_sync.py               # Cut at beats
│   │   ├── chapters.py                # YouTube chapters
│   │   ├── audio_viz.py               # Waveform visualization
│   │   ├── retakes.py                 # False start detection
│   │   ├── registrar_aprendizaje.py   # Learning logs (RSI)
│   │   ├── auditar_plan.py            # Plan.json audit
│   │   └── ffmpeg_tools/              # 19 post-production modules
│   │       ├── montaje.py             # 18 editing operations
│   │       ├── caption.py             # Subtitle burn-in
│   │       ├── grade.py               # Color grading + presets
│   │       ├── loudness.py            # -14 LUFS / -1.5 dBTP
│   │       ├── delivery_check.py      # Platform verification
│   │       ├── alinear.py             # (alias to root)
│   │       ├── aplicar_edl.py         # EDL → MP4
│   │       ├── shorts_plan.py         # Vertical shorts generator
│   │       ├── thumbnail.py           # Typography thumbnail
│   │       ├── verticalizar.py        # Horizontal → vertical
│   │       ├── artesanal.py           # Cards + images mode
│   │       ├── scenes.py              # Scene editor
│   │       ├── variants.py            # Aspect ratio variants
│   │       ├── look.py                # LUT look
│   │       ├── speedramp.py           # Time-lapse
│   │       ├── silencio.py            # Silence removal
│   │       ├── _comun.py              # Shared DRY helpers
│   │       └── _plataforma.py         # OS abstractions
│   │   └── validate_skill.py          # Skill validator
│   ├── references/                    # 45 references
│   │   ├── instalacion.md             # Per OS (Win/macOS/Linux)
│   │   ├── escenas.md                 # Catalog of 28 scenes
│   │   ├── escenas-extendidas.md      # Portable concepts
│   │   ├── plan-video.md              # plan.json schema
│   │   ├── estilos.md                 # Visual styles catalog
│   │   ├── tecnicas-video.md          # 2025-2026 techniques catalog (FRESH/STANDARD/TIRED)
│   │   ├── scoring-shorts.md          # Moment selection rubric
│   │   ├── fluidez.md                 # Fluidity rules
│   │   ├── animacion.md               # Animation craft (12 principles)
│   │   ├── coherencia-espacial.md     # Alignment and safe zones
│   │   ├── montaje.md                 # 18 operations
│   │   ├── cine.md                    # Cinematic recipes
│   │   ├── modos-rapidos.md           # Quick recipes (kinetic, montage, cut)
│   │   ├── modos-produccion.md        # Real / product / hybrid modes
│   │   ├── brand-packs.md             # Brand pack spec
│   │   ├── pipeline-resumen.md        # Summary pipeline
│   │   ├── sonido.md                  # Sound design
│   │   ├── tonos.md                   # 6 tones (demo, resumen, trailer, parodia, caos)
│   │   ├── audio.md                   # Beat grid + SFX
│   │   ├── sfx.md                     # SFX doctrine (tone→energy, moment→sound, timing)
│   │   ├── thumbnails.md              # Conceptual thumbnails
│   │   ├── share-copy.md              # Canonical caption
│   │   ├── principios.md              # 3 pillars: coherence, harmony, dazzling effects
│   │   ├── direccion.md              # Direction with metrics
│   │   ├── dramaturgia.md             # Fable structure
│   │   ├── ritmo.md                   # Anti-slideshow
│   │   ├── checklist-qa.md            # QA checklist
│   │   ├── auto-mejora.md             # Self-improvement protocol
│   │   ├── auto-qa.md                 # QA loop
│   │   ├── lecciones-produccion.md    # Lessons from the original system
│   │   ├── remotion.md                # Remotion integration (optional)
│   │   ├── hyperframes.md             # HyperFrames integration (optional)
│   │   ├── prompt-motion-graphics.md     # Prompts for motion graphics
│   │   ├── recetas-ai-video.md        # AI recipes
│   │   ├── tecnicas-reutilizables.md  # Reusable techniques
│   │   ├── cli-contract.md            # CLI contract
│   │   ├── arquitectura.md              # Script map
│   │   ├── i18n.md                    # Language policy (Language Rule)
│   │   ├── media-hard-rules.md        # Mapping of Hard Rules from media-tooling
│   │   ├── scene-patterns-from-internet.md # External sources catalog
│   │   ├── rubrica-premios.md         # 8-axis award rubric
│   │   ├── video-real.md              # Recording → post (camera-first flow)
│   │   └── ...
│   ├── references/schemas/             # 2 JSON schemas
│   │   ├── plan-schema.json
│   │   └── shorts-plan-schema.json
│   ├── assets/
│   │   └── fonts/                     # Plus Jakarta Sans + Montserrat (OFL)
│   ├── brand/                         # White-label: packs live here only
│   │   ├── dragonjar.json             # Example pack
│   │   ├── assets/                    # Brand assets (logos, etc.)
│   │   └── README.md                  # How to create a new pack
│   ├── film/                          # Sample music for brand film
│   │   ├── musica_film.mp3
│   │   ├── musica_film_v2.mp3
│   │   └── musica_demo.mp3
│   └── metricas/                      # Skill metrics (RSI)
│       └── historial.jsonl
└── .gitignore                         # Restrict repo to SKILL/ and READMEs
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

Should NOT activate on: "edit this document", "improve this text",
"make me an image", "summarize this PDF in text", "what video do you recommend".

## ⚠️ Limitations

1. **WhatsApp API**: the WhatsApp Business client has rate limits; respect `--cooldown=120` on messages.
2. **Localization ES + client-side hooks**: the bypass is client-side; server-side attestation (Play Integrity, SafetyNet, ApprovRoot) requires an authorized test tenant or mock verifier.
3. **FFmpeg capabilities**: if `libvpx-vp9` or `prores_ks` are unavailable, the validator warns but does not fail (it's the team's equipment, not the skill).
4. **Red lines intentional**: without external libraries (Remotion / HyperFrames), React+CSS is used, no dependencies beyond the system.

> **Disclaimer**: This skill is intended for **legitimate use only**. Client-side
> hooks do not forge server-side attestation verdicts. For ApprovRoot,
> Play Integrity, SafetyNet, or backend-enforced controls, use an authorized test
> tenant, mock verifier or approved lab configuration.

## 🔁 Source of truth

This repository (`main` branch) is the **canonical source** of the skill. If
you keep copies in skill directories (e.g.
`~/.claude/skills/editoria/` or `~/.config/opencode/skills/editoria/`),
resync them after pulling:

```bash
git -C /path/to/EditorIA pull
rsync -a --delete --exclude '.git' --exclude '__pycache__' --exclude '.pytest_cache' \
  /path/to/EditorIA/ ~/.claude/skills/editoria/
```

Unsynchronized copies will silently drift out of date.

## 🤝 Contributing

Contributions are welcome. Areas that need expansion:

- **Technique catalog** (`references/tecnicas-video.md`): new production-validated techniques
- **Additional scenes**: if you need a new pattern, follow `references/scene-patterns-from-internet.md`
- **Voice roster** (`scripts/voz_off.py VOCES`): add ElevenLabs voices for new languages
- **Brand packs** (`brand/`): new example packs
- **Validator** (`scripts/validate_skill.py`): new quality checks

## 📄 License

MIT — See [`LICENSE`](LICENSE) for details.

## 👨💻 Author

**Jaime Andrés Restrepo** — [DragonJAR SAS](https://www.DragonJAR.org)

---

**⚠️ Privacy note**: scripts use `$ELEVENLABS_API_KEY` from your environment. **Never**
include credentials in `plan.json`, `brand/*.json`, or project files.
The skill does no confabulation: numbers, names and quotes come from the
source or are marked `[PENDING]` for you to fill in.