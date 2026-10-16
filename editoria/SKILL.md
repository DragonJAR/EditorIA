---
name: editoria
description: 'Creates, edits, summarizes, and improves videos (.mp4, .mov, .webm, .srt) including animated meeting summaries, kinetic typography, plan-driven ads, cinematic films, and vertical social clips for any brand or in free mode. Use when the user asks to "make me a video", "summarize this meeting", "edit this ad", "improve this video", "create a reel", or "add music to it". Do NOT use for static images, text-only PDF summaries, or document editing.'
license: MIT
compatibility: 'Python 3.9+, FFmpeg, Pillow, NumPy; optional ElevenLabs API and Node 18+ for Remotion or HyperFrames'
metadata:
  author: Jaime Andrés Restrepo
  version: 1.7.0
  category: video-editing
  tags: [video-editing, motion-graphics, ffmpeg, animation]
---

# EditorIA

Swiss Army knife for creating dynamic, professional videos of any kind, for any brand or in free mode. Every deliverable must look fluid, intentional, and festival-grade. Produces animated summaries, kinetic typography, plan-driven ads, cinematic films, and vertical social pieces across Windows 10/11, macOS (Intel and Apple Silicon), and Linux (see `references/instalacion.md`).

## Critical

- **Language rule**: Documentation, code, comments, and identifiers are written in English. Respond to the user in the exact language the user writes in. Skill content (transcripts, captions, voice-overs) works in any source language, and the default TTS voice matches the user's language (`es` for Spanish, `en` for English). Full policy in `references/i18n.md`.
- **White-label brand rule**: Identity is never hardcoded in code; it lives in a brand pack (`brand/*.json`, spec in `references/brand-packs.md`).
  - When the user names a brand, load its pack (`brand/dragonjar.json` is the included example). The pack fixes colors, fonts, logos, voices, and rules; the brief provides the content.
  - When the user does not name a brand, use free mode with pure cinematic criteria: palette, typography, and transition language chosen from the brief and tone. Never invent brand identity.
- **Pre-render validation**: CRITICAL: Before calling `scripts/render_plan.py`, verify:
  - Environment capabilities pass via `python scripts/check_env.py` (`references/capacidades.md`).
  - Every scene `from`/`to` window and `voz` duration passes `python scripts/auditar_plan.py plan.json`.
  - No credentials or API keys appear in `plan.json` or `brand/*.json` (`$ELEVENLABS_API_KEY` is read from `~/.secrets.env`).

## Motor Selector

| Brief | Motor |
|---|---|
| Ad with scenes and narration | **Plan**: `plan.json` + `scripts/render_plan.py` (30 scene types in `references/escenas.md`; portable concepts in `references/escenas-extendidas.md`) |
| Meeting or transcript summary | **Composition**: `references/pipeline-resumen.md` + styles from `references/estilos.md` |
| Cinematic film 16:9 | **Cine**: recipes in `references/cine.md` (with brand pack: `scripts/film_marca_v2.py` or `scripts/film_marca.py`) |
| Quick kinetic card (one phrase) | **Quick**: recipe `quick-kinetic` in `references/modos-rapidos.md` |
| Clip assembly with music | **Quick**: recipe `quick-montage` in `references/modos-rapidos.md` |
| Trim or adapt an existing video | **Quick**: recipe `quick-cut` in `references/modos-rapidos.md` |
| Vertical short from a long video | **Shorts**: `shorts-plan.json` (schema in `references/shorts-plan-schema.md`) + `scripts/ffmpeg_tools/shorts_plan.py` |
| Real video + animation complementing it | **Hybrid**: `references/modos-produccion.md` (bridges, layers, continuity) |
| Existing video + background music | `scripts/musica.py musiconly -v video.mp4 -m mus.mp3 -o final.mp4` |
| Video + voice-over + music with ducking | `scripts/musica.py gen` then `mix` (music breathes under voice) |
| Clip editing (join, cut, fade, PiP, GIF, etc.) | **Montaje**: `scripts/ffmpeg_tools/montaje.py` (18 operations in `references/montaje.md`) |
| Verify deliverable against platform spec | **Delivery**: `scripts/ffmpeg_tools/delivery_check.py final.mp4 --platform reels` (specs in `scripts/ffmpeg_tools/_delivery.py`; CLI contract in `references/cli-contract.md`) |
| Complex programmatic animation | **Remotion** (optional): `references/remotion.md` |
| Deterministic HTML piece or data re-render | **HyperFrames** (optional): `references/hyperframes.md` |
| One-shot motion graphics film | **Prompts**: `references/prompt-motion-graphics.md` and `references/recetas-ai-video.md` |

Complete skill architecture map: `references/arquitectura.md`.

## Instructions

### Step 1: Validate Environment and Capabilities

Check available binaries, fonts, and Python libraries before planning or rendering (`references/capacidades.md`).

```bash
python scripts/check_env.py
```

Expected output: `ENTORNO LISTO` (or a clear diagnostic listing any missing optional dependency and its fallback).

### Step 2: Author and Audit the Declarative Plan

Write `plan.json` following `references/plan-video.md` (30 scene types, absolute times, optional `at` per element, `voz` field per scene when narrated). Pick the tone first (`references/tonos.md`) and structure the dramatic arc (`references/dramaturgia.md`). See `scripts/demo_plan.json` and `scripts/escenas_muestra.json` for complete examples.

```bash
python scripts/auditar_plan.py plan.json
```

Expected output: `PLAN VALIDO` with zero overlapping voice segments or missing required scene fields.

### Step 3: Render Video with Fluidity Motor

Render the plan with spring physics, live backgrounds, and 180-degree shutter motion blur (`references/animacion.md`, `references/fluidez.md`). Use `--blur 1` for fast drafts and `--blur 5` for final delivery. Re-running without `--force` resumes interrupted renders incrementally.

```bash
python scripts/render_plan.py plan.json -o out.mp4 --blur 5
```

Expected output: `out.mp4` rendered at 1080x1920 @30fps (vertical) or 1920x1080 @30fps (horizontal), H.264 `yuv420p`.

### Step 4: Synthesize Voice-Over, SFX, and Music

When the brief includes narration, synthesize voice-over (`references/sonido.md`), align words if needed, generate or select music, and mix with sidechain ducking (`references/audio.md`, `references/sfx.md`).

```bash
python scripts/voz_off.py plan.json -o voz.mp3
python scripts/alinear.py voz.mp3 script.txt -o voz.palabras.json
python scripts/musica.py gen --prompt "modern upbeat electronic" --dur 30 -o mus.mp3
python scripts/musica.py mix -v out.mp4 -a voz.mp3 -m mus.mp3 -o final.mp4
python scripts/medir_mezcla.py final.mp4
```

Expected output: `final.mp4` with voice on top and music ducked ~15 dB under active speech.

### Step 5: Run Quality Assurance and Verify Delivery

Run automated QA (`references/auto-qa.md`, `references/checklist-qa.md`, `references/coherencia-espacial.md`), verify rhythm (`references/ritmo.md`), score against the 8-axis awards rubric (`references/rubrica-premios.md`), and validate platform compliance.

```bash
python scripts/auto_qa.py final.mp4
python scripts/verificar_ritmo.py plan.json
python scripts/ffmpeg_tools/delivery_check.py final.mp4 --platform reels
```

Expected output: `PASS` verdict with zero black frames, frozen holds, photosensitivity flashes, or clipped text.

### Step 6: Composition Workflow for Transcripts and Free Pieces

When summarizing meetings or editing camera-first footage (`references/video-real.md`, `references/pipeline-resumen.md`):

1. Extract 6 to 10 verified moments from the transcript using `references/scoring-shorts.md`.
2. Choose the visual language in `references/estilos.md` and camera direction in `references/direccion.md`.
3. Apply post-production tools as needed: transcribe (`scripts/ffmpeg_tools/transcribir.py`), remove retakes and silence (`scripts/retakes.py`, `scripts/ffmpeg_tools/silence.py`), apply EDL (`scripts/ffmpeg_tools/aplicar_edl.py`), burn captions (`scripts/ffmpeg_tools/caption.py`), sync cuts to beats (`scripts/beat_grid.py`, `scripts/beat_sync.py`), generate chapters (`scripts/chapters.py`), and bake poster/thumbnails (`scripts/poster_frame.py`, `scripts/ffmpeg_tools/thumbnail.py`, `references/thumbnails.md`).
4. Prepare companion caption in `share-copy.txt` per `references/share-copy.md` and log new production findings via `python scripts/registrar_aprendizaje.py` (`references/auto-mejora.md`, `references/lecciones-produccion.md`).

## Output Contract and Success Criteria

- **Resolution and codec**: 1080x1920 @30fps for vertical; 1920x1080 @30fps for horizontal (24fps for cinema pieces). H.264, `yuv420p`, CRF 18-22.
- **Three visual pillars**: Every piece obeys `references/principios.md` (visual coherence, spatial harmony, special effects), `references/tecnicas-video.md`, and `references/tecnicas-reutilizables.md`.
- **Audio and SFX**: Procedural SFX via `scripts/sfx.py` (`click`, `pop`, `drop`, `whoosh`, `ding`, `thud`, `tick`, `swell`), waveform visualization via `scripts/audio_viz.py`, loudness via `scripts/ffmpeg_tools/loudness.py`.
- **Post-production kit**: `scripts/ffmpeg_tools/verticalizar.py`, `scripts/ffmpeg_tools/grade.py`, `scripts/ffmpeg_tools/variantes.py`, `scripts/ffmpeg_tools/artesanal.py`, `scripts/ffmpeg_tools/scenes.py`, `scripts/ffmpeg_tools/look.py`, `scripts/ffmpeg_tools/speedramp.py`, `scripts/ffmpeg_tools/_comun.py`, `scripts/ffmpeg_tools/_plataforma.py`.
- **Clean workspace**: Save final deliverables in the user-requested output folder, never inside the skill folder.
- **Metrics and validation**:
  - Triggering: >=90% on relevant video requests, 0% on unrelated tasks.
  - Execution: 0 failed tool calls per workflow.
  - Consistency: `python scripts/validate_skill.py` exits 0 (30/30 scenes render, scripts compile, references exist) and unit tests in `scripts/_tests/test_chapters.py` and `scripts/_tests/test_core_and_scenes.py` pass via `python3 -m unittest discover -s scripts/_tests`.

## Examples

### Example 1: Plan-Driven Product Ad

User says: "Make me a 30-second vertical ad for my SaaS product launch"

Actions:

1. Run `python scripts/check_env.py` to confirm environment capabilities.
2. Author `plan.json` using scenes `hero`, `bento`, `stats`, and `final` per `references/plan-video.md` and `references/scene-patterns-from-internet.md`.
3. Audit timing and voice fit with `python scripts/auditar_plan.py plan.json`.
4. Render with `python scripts/render_plan.py plan.json -o ad.mp4 --blur 5`.
5. Run `python scripts/auto_qa.py ad.mp4` and `python scripts/ffmpeg_tools/delivery_check.py ad.mp4 --platform reels`.

Result: `ad.mp4` (30s, 1080x1920 @30fps, H.264 `yuv420p`) passing visual and delivery QA.

### Example 2: Animated Meeting Summary

User says: "Summarize this meeting transcript into a vertical video"

Actions:

1. Extract 6 to 10 verified highlights from the transcript (`references/scoring-shorts.md`) with zero invented text.
2. Select the `resumen-animado` style from `references/estilos.md`.
3. Build the sequence per `references/pipeline-resumen.md` and inspect key frames with `scripts/contact_sheet.py`.

Result: Vertical summary video highlighting verified moments with spring transitions and clean safe zones.

### Example 3: Add Background Music to an Existing Video

User says: "Add background music to this video"

Actions:

1. Generate music with `python scripts/musica.py gen --prompt "cinematic warm ambient" --dur {seconds} -o mus.mp3`.
2. Mix with fade-out using `python scripts/musica.py musiconly -v video.mp4 -m mus.mp3 -o final.mp4`.
3. Verify loudness levels and deliver `final.mp4`.

Result: `final.mp4` with balanced background music and smooth fade-out.

### Example 4: Iterate on a QA Defect

User says: "Fix the clipped title in scene 2"

Actions:

1. Adjust the scene copy or renderer layout (`references/reglas-tecnicas.md`) and re-run `python scripts/render_plan.py plan.json -o ad.mp4`.
2. Record the lesson with `python scripts/registrar_aprendizaje.py --title "..." --detail "..."`.
3. Verify with `python scripts/validate_skill.py`.

Result: Defect resolved, lesson logged, and `SKILL VALIDO` confirmed.

## Triggering and Evaluation Tests

Should trigger:

- "make me a video"
- "summarize this meeting into a reel"
- "edit this ad and make it more dynamic"
- "improve this video and add background music"
- "turn this transcript into a vertical short"
- "create a brand bumper"

Should NOT trigger:

- "edit this document"
- "improve this text"
- "make me a static image"
- "summarize this PDF in text"
- "what video camera do you recommend"

## Troubleshooting

### Error: Render stops mid-way without traceback

Cause: The render process was terminated by a command timeout or memory limit rather than a code error.

Solution:

1. Check if the process is still running with `pgrep -f render_plan`.
2. Re-run `python scripts/render_plan.py plan.json -o out.mp4` without `--force` so incremental frame caching resumes from the last rendered frame.

### Error: Clipped text at frame edges

Cause: Text bypassed auto-fit width limits or used an off-center anchor (`references/reglas-tecnicas.md`).

Solution:

1. Keep auto-fit width `<= 1000px` on 1080px canvases and center with `cx = W / 2`.
2. Verify safe-zone margins with `python scripts/medir_animacion.py` and `references/coherencia-espacial.md`.

### Error: Empty scenes after intro in FFmpeg overlays

Cause: FFmpeg `overlay` filter synchronizes streams by presentation timestamp (`PTS`).

Solution:

1. Reset clip timestamps with `setpts=PTS-STARTPTS` before chaining `overlay` filters (`references/reglas-tecnicas.md` and `references/media-hard-rules.md`).

### Error: Large `.frames` cache directories

Cause: Uncompressed intermediate PNG frames remain on disk after interrupted renders.

Solution:

1. Delete temporary `.frames` directories after final delivery; never store them inside the skill folder.

## Performance Notes

- Take your time to do this thoroughly.
- Quality is more important than speed.
- Do not skip validation steps (`scripts/check_env.py`, `scripts/auditar_plan.py`, `scripts/auto_qa.py`, and `scripts/validate_skill.py`).
