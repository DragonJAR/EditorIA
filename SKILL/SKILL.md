---
name: editoria
description: EditorIA, the Swiss Army knife for AI video editing. Create, edit, summarize or improve videos (.mp4): animated meeting summaries, kinetic typography, plan-driven ads, cinematic films, and vertical social pieces — for any brand or no brand at all. Use when the user asks "make me a video", "summarize this meeting", "edit this ad", "improve this video", or "add music to it".
metadata: { "author": "Jaime Andrés Restrepo", "version": "1.3.0" }
---

# EditorIA

**Language rule (read first):** EditorIA's documentation, code, comments and
identifiers are written in English. **The agent MUST respond to the user in the
language the user writes in.** The skill's *content* (transcripts, captions,
voice-overs) understands and works in any language the source provides; the
default voice for TTS matches the language the user is writing in (`es` for
Spanish, `en` for English, etc.). Full policy in `references/i18n.md`.

Swiss Army knife for creating dynamic, professional videos of any kind,
for any brand — or no brand. The bar is cinema: every piece must look fluid,
intentional and festival-grade, not "an AI video". Produces animated summaries,
kinetic typography, ads, cinematic films, and vertical social pieces.

**Platforms**: Windows 10/11, macOS (Intel and Apple Silicon), and Linux.
OS-specific install: `references/instalacion.md`. Scripts resolve fonts,
temp dirs and binaries according to the host OS.

## Brand: pack or free mode (read first)

EditorIA is white-label. Identity is never hardcoded — it lives in a
**brand pack** (`brand/*.json`, spec in `references/brand-packs.md`).

- **User names a brand** → load its pack (`brand/dragonjar.json` is the
  included example). The pack fixes colors, fonts, logos, voices and rules;
  the brief provides the content.
- **User does not name a brand** → **free mode**: ignore all brand identity
  and design with pure cinematic criteria — palette, typography and
  transition language chosen from the brief, the tone, and what the piece
  needs. The only limit is that it must look intentional and premium.

Golden rule: **the pack rules over the preset; the brief rules over everything**.
Never invent brand identity (colors, logos, slogans): no pack → free design;
pack present → total fidelity.

## Motor selector (read first)

| Brief | Motor |
|---|---|
| Ad with scenes and narration | **Plan**: `plan.json` + `scripts/render_plan.py` (24 scene types in `references/escenas.md`; portable concepts in `references/escenas-extendidas.md`) |
| Meeting / transcript summary | **Composition**: `references/pipeline-resumen.md` + styles from `references/estilos.md` |
| Cinematic film 16:9 | **Cine**: recipes in `references/cine.md` (with brand pack: `scripts/film_marca_v2.py` for DragonJAR) |
| Quick kinetic card (one phrase) | **Quick**: recipe `quick-kinetic` in `references/modos-rapidos.md` |
| Clip assembly with music | **Quick**: recipe `quick-montage` in `references/modos-rapidos.md` |
| Trim / adapt an existing video | **Quick**: recipe `quick-cut` in `references/modos-rapidos.md` |
| Vertical short from a long video | **Shorts**: `shorts-plan.json` (schema in `references/shorts-plan-schema.md`) + `scripts/ffmpeg_tools/shorts_plan.py` |
| Real video + animation complementing it | **Hybrid**: `references/modos-produccion.md` (bridges, layers, continuity) |
| Existing video + background music | `scripts/musica.py musiconly -v video.mp4 -m mus.mp3 -o final.mp4` |
| Video + voice-over + music with ducking | `scripts/musica.py gen` → `mix` (music breathes under voice) |
| Clip editing (join, cut, fade, PiP, GIF, etc.) | **Montaje**: `scripts/ffmpeg_tools/montaje.py` — 18 operations (see `references/montaje.md`) |
| Verify a deliverable against the platform spec (codec, LUFS, aspect...) | **Delivery**: `scripts/ffmpeg_tools/delivery_check.py final.mp4 --platform reels` (canonical specs in `scripts/ffmpeg_tools/_delivery.py`; CLI contract in `references/cli-contract.md`) |
| Complex programmatic animation (data-driven, components) | **Remotion** (optional): `references/remotion.md` — only if the Python motor is not enough |
| Deterministic HTML piece / re-render with changing data | **HyperFrames** (optional): `references/hyperframes.md` — `npx hyperframes skills update` |
| One-shot motion graphics film (launch, showreel, aggressive talking head) | **Prompts**: `references/prompt-motion-graphics.md` (verbatim library) · **Recipes**: `references/recetas-ai-video.md` (3-agent pipeline) |

If nothing in the table fits, use the closest motor and compose: motors are
layers, not silos (a brand film can have a `quick-kinetic` on top).

Complete skill map: `references/arquitectura.md` — what each script does
(including the `scripts/ffmpeg_tools/` kit) and each reference.

## Workflow

**A. By plan (ads and scene-driven pieces)** — the main flow:
0. **Capabilities**: `python scripts/check_env.py` (`references/capacidades.md`).
   Validate first, promise later; degrade honestly if something is missing.
1. **Plan**: write `plan.json` per `references/plan-video.md` (24 scene types,
   absolute times, `at` per element, `voz` field per scene if there is
   narration). See `scripts/demo_plan.json` as an example.
2. **Render**: `python scripts/render_plan.py plan.json -o out.mp4`
   (fluidity motor: springs, live background, transitions per brand pack
   or tone; `--force` to re-render everything, without it resumes where it
   left off). Drafts with `--blur 1`; **final delivery with `--blur 5`**
   (180° shutter motion blur, see `references/animacion.md`).
3. **Voice-over** (if requested): `python scripts/voz_off.py plan.json -o voz.mp3`
   (ElevenLabs, `voz` field per scene). **Sound section**:
   `references/sonido.md` — voice direction (tags `[excited]`, `[whisper]`...),
   voices per language (default voice is the language the user is writing
   in), music and SFX. **Word-level alignment** (optional, for scenes with
   `at:` per word): `python scripts/alinear.py voz.mp3 script.txt -o
   voz.palabras.json`.
4. **Music**: `python scripts/musica.py gen --prompt "..." --dur 30 -o mus.mp3`.
   With voice: `mix -v video.mp4 -a voz.mp3 -m mus.mp3 -o final.mp4`. Without
   voice: `musiconly -v video.mp4 -m mus.mp3 -o final.mp4`.
5. **QA**: `references/checklist-qa.md` + `references/coherencia-espacial.md`.
   Look at frames at key times. Score with `references/rubrica-premios.md`.
6. **Iterate and document**: every fix → `python scripts/registrar_aprendizaje.py`.

**B. By composition (summaries, free pieces)**:
0. **Capabilities**: `python scripts/check_env.py`.
1. **Brief**: what piece, target duration, format, and what it must say.
2. **Brand**: did the user name a brand? → load its brand pack.
3. **Style**: pick the visual language in `references/estilos.md`.
4. **Visual script**: 6–10 strong beats verified against the source.
5. **Build**: animation craft in `references/animacion.md`,
   `references/pipeline-resumen.md`, `references/tecnicas-video.md`.
6. **QA and delivery**: same as flow A.

## Output Contract

- 1080×1920 @30fps for vertical; 1920×1080 @30fps for horizontal (24fps for
  cinema pieces). H.264, yuv420p, CRF 18–22.
- Audio: voice-over (`scripts/voz_off.py`) and music (`scripts/musica.py`)
  when requested; with voice there is always ducking; without voice,
  `musiconly` with fade-out. API key from `$ELEVENLABS_API_KEY`
  (`~/.secrets.env`) — never in the skill.
- Spatial coherence: `references/coherencia-espacial.md` before delivery.
- Delivery: `scripts/ffmpeg_tools/delivery_check.py` against the target
  platform (PASS verdict).
- Premium 16:9 pieces: recipes in `references/cine.md`.
- Thumbnails: `references/thumbnails.md` (concept → review-gate → generate).
- Poster: `scripts/poster_frame.py` bakes the strongest settled frame as
  frame 0 of the mp4 + `*_poster.jpg`.
- Share copy: `references/share-copy.md` — canonical caption in `share-copy.txt`.
- Tone: `references/tonos.md` — pick the tone in the brief, before the
  script; tone rules over technique.
- Dramaturgy: `references/dramaturgia.md` — story-fable structure.
- Advanced audio: `references/audio.md` + `scripts/beat_grid.py` and
  `scripts/medir_mezcla.py`.
- SFX: `references/sfx.md` + `scripts/sfx.py` (click, pop, drop, whoosh,
  ding, thud, tick, swell).
- Post-production: transcribe → retakes/silence → EDL →
  `scripts/ffmpeg_tools/aplicar_edl.py`; `scripts/ffmpeg_tools/shorts_plan.py`
  validates/executes `shorts-plan.json`; `scripts/beat_sync.py` adjusts
  cuts to the beat grid; `scripts/chapters.py` generates YouTube chapters.
- Anti-slideshow rhythm: `references/ritmo.md` + `scripts/verificar_ritmo.py`.
- Production lessons: `references/lecciones-produccion.md`.
- Final file in the output folder the user indicates; never inside the
  skill folder.

## Success Criteria (definition of done)

A video is done only if it meets ALL of the following:
1. **Brief**: says what the user asked for, no more, no less. No invented text.
2. **Brand**: with brand pack, total fidelity. In free mode, identity
   designed with criteria and consistent across the whole piece.
3. **Fluidity and animation**: `references/fluidez.md` + `references/animacion.md`:
   springs, overlapping, arcs, anticipation, motion blur on delivery.
4. **Spatial coherence**: `references/coherencia-espacial.md` — no overlaps or crops.
5. **Audio**: music with cadence matching visual rhythm; voice with
   ducking verified with `scripts/medir_mezcla.py` (music ~15 dB under voice).
6. **Visual QA**: frames extracted at key times and inspected. No defects.
7. **Awards rubric**: `references/rubrica-premios.md` — no axis below 4, average ≥ 4.3.
8. **Learning**: every fix left its lesson recorded per
   `references/auto-mejora.md`.

## Metrics (Claude skills guidance)

- **Triggering**: ≥90% on relevant queries, 0% on unrelated ones.
- **Execution**: 0 failed API calls per workflow.
- **Consistency**: same brief produces same structure across sessions
  (`scripts/validate_skill.py`: 24/24 scenes always render).

## Examples

**Example 1 — ad by plan**
User: "Make me a 30-second ad for my product"
1. Write `plan.json` (see `references/plan-video.md` and `scripts/demo_plan.json`).
2. `python scripts/render_plan.py plan.json -o ad.mp4`
3. QA with `references/checklist-qa.md` (inspect frames at key times).
4. Deliver the MP4 attached in the chat.
Result: `ad.mp4` of 30s, 1080×1920 @30fps, H.264, clean QA.

**Example 2 — animated meeting summary**
User: "Summarize this meeting transcript into a vertical video"
1. Extract 6–10 verified moments from the transcript.
2. Pick style in `references/estilos.md` (resumen-animado).
3. Build with `references/pipeline-resumen.md`.
4. QA frame by frame and deliver.
Result: vertical summary with key moments, purposeful motion, no invented text.

**Example 3 — iterate on a defect**
QA shows clipped text in a frame:
1. Fix the renderer or the plan.
2. Log the lesson with `python scripts/registrar_aprendizaje.py --title "..." --detail "..."`.
3. Re-render and verify the frame.
Result: defect fixed, lesson logged, `SKILL VALIDO`.

**Example 4 — music for an existing video**
User: "Add background music to this video"
1. `python scripts/musica.py gen --prompt "..." --dur {seconds} -o mus.mp3`
2. `python scripts/musica.py musiconly -v video.mp4 -m mus.mp3 -o final.mp4`
3. Verify levels and deliver.
Result: `final.mp4` with background music and fade-out, levels in range.

## Trigger Tests

The skill should activate on:
- Obvious: "make me a video", "summarize this meeting", "edit this ad",
  "improve this video", "add music", "create a reel for me".
- Paraphrases: "I need a piece for social", "turn this transcript into a video",
  "the video is bland, give it life", "make it more dynamic",
  "I want a brand bumper".
- Should NOT activate on: "edit this document", "improve this text",
  "make me an image", "summarize this PDF in text", "what video do you recommend".

## Functional cases (evaluation)

1. **Complete plan**: `plan.json` of 30s with 6 scenes → MP4 1080×1920 @30fps,
   H.264 yuv420p, no black frames or clipped text.
2. **Voice + music**: `mix` produces voice on top and music with audible
   ducking; final duration == video duration.
3. **Music only**: `musiconly` produces video + music with fade-out, no voice.
4. **Resume**: interrupt `render_plan.py` mid-way and re-run without `--force`
   resumes the missing frames.
5. **Validation**: `python scripts/validate_skill.py` exits 0 (24/24 scenes
   render, scripts compile, references exist).

## Troubleshooting

**Render dies mid-way (no traceback)**
Probable cause: the process was killed by timeout or OOM, not by a bug.
Check with `pgrep -f render_plan` if it is still alive. Frames are saved
incrementally: re-running without `--force` resumes where it left off.

**Media-tooling production rules**
EditorIA complies with 11/12 Hard Rules and 12/13 Anti-patterns from
[kumanday/media-tooling](https://github.com/kumanday/media-tooling). The
mapping rule → where it is enforced is in `references/media-hard-rules.md`.

**Clipped text at the edge**
Cause: missing auto-fit or miscalculated center. See rules in
`reglas-tecnicas.md` (auto-fit ≤1000px, `cx=W/2` to center).

**Empty scenes after the intro (ffmpeg)**
Cause: `overlay` syncs by PTS. See the `setpts` rule in `reglas-tecnicas.md`.

**Huge `.frames` folders**
Render cache (hundreds of MB). Delete after delivery; they regenerate.
Never inside the skill folder or next to the user's deliverables.

## Operating Rules

1. **White-label**: identity lives in the brand pack, never in the skill.
   With pack: total fidelity. Without pack (free mode): pure cinematic
   design per the brief — the bar is "festival-grade". Never invent brand identity.
2. **Supreme fluidity** (`references/fluidez.md`): springs on every entrance,
   always-live background, anticipated exits, 30ms micro-fade on every cut.
   The transition language is fixed by the brand pack or the tone of the piece.
3. The three pillars of `references/principios.md` (visual coherence, spatial
   harmony, dazzling special effects and harmonies) are mandatory on every delivery.
4. **Continuous self-improvement** (`references/auto-mejora.md`): every build
   that solves something real, repeatable and verified is logged with
   `python scripts/registrar_aprendizaje.py --title "..." --detail "..."`.
   The content lives in a single place (DRY).
5. Zero confabulation: numbers, names and quotes come from the source or
   are marked `[PENDING]`.
6. **Self-correction before the user** (`references/auto-qa.md`): the model
   is multimodal — use your own eyes as the QA.
7. Long renders go in the background; do not block the chat.
8. **Author's mandate**: improve this skill continuously until it is the
   best AI video editing skill ever created.
9. **The bar is award-grade** (`references/rubrica-premios.md`): idea with
   a hook, dramatic arc, animation with craft and designed sound. "Correct" is not done.
