---
name: editoria
description: 'Creates, edits, summarizes, and improves videos (.mp4, .mov, .webm, .srt) including animated meeting summaries, kinetic typography, plan-driven ads, cinematic films, and vertical social clips for any brand or in free mode. Also designs the sound: voice-over, music and sound effects, mixed and measured. Use when the user asks to "make me a video", "summarize this meeting", "edit this ad", "improve this video", "create a reel", "make one like this video", "add music to it", "add a voice-over", "dub it", "add sound effects", to write the on-screen copy or script of a video, or to check a rendered video before delivery. Do NOT use for static images, text-only PDF summaries, or document editing.'
license: MIT
compatibility: 'Python 3.9+, FFmpeg, Pillow, NumPy; optional ElevenLabs API and Node 18+ for Remotion or HyperFrames'
metadata:
  author: Jaime Andrés Restrepo
  version: 1.10.2
  category: video-editing
  tags: [video-editing, motion-graphics, ffmpeg, animation]
---

# EditorIA

Swiss Army knife for creating dynamic, professional videos of any kind, for any brand or in free mode. Every deliverable must look fluid, intentional, and festival-grade. Produces animated summaries, kinetic typography, plan-driven ads, cinematic films, and vertical social pieces across Windows 10/11, macOS (Intel and Apple Silicon), and Linux (see `references/instalacion.md`).

## Critical

- **Language rule**: Respond to the user in the exact language the user writes in. `SKILL.md` is written in English for global routing, while `plan.json` schema keys (`escenas`, `duracion`, `rotulo`, `tamano`), `references/*.md`, and CLI scripts preserve their canonical Spanish identifiers as defined in the codebase. Skill content (transcripts, captions, voice-overs) works in any source language, and the default TTS voice matches the user's language (`es` for Spanish, `en` for English). Full policy in `references/i18n.md`.
- **White-label brand rule**: Identity is never hardcoded in code; it lives in a brand pack (`brand/*.json`, spec in `references/brand-packs.md`).
  - When the user names a brand, load its pack (`brand/dragonjar.json` is the included example). The pack fixes colors, fonts, logos, voices, and rules; the brief provides the content.
  - When the user does not name a brand, use free mode: **choose the palette, don't inherit one**. Pick one from the catalog in `references/paleta.md` according to the brief (topic, sector, emotion) and color theory, and declare it in the plan (`"paleta": "menta"`) or with `--paleta`. The free-mode fallback is a cold, identity-free blue — a piece without a brand must not look like one (notably: not like the example pack's red).
  - Brand pack always wins over a palette. Never invent brand identity.
- **Pre-render validation**: CRITICAL: Before calling `scripts/render_plan.py`, verify:
  - Environment capabilities pass via `python scripts/check_env.py` (`references/capacidades.md`).
  - Every scene `from`/`to` window and `voz` duration passes `python scripts/auditar_plan.py plan.json`.
  - The copy passes `python scripts/lint_copy.py plan.json`: text that the engine cannot place is a render defect, and copy that reads as generated is a quality defect (`references/copy.md`).
  - No credentials or API keys appear in `plan.json` or `brand/*.json` (`$ELEVENLABS_API_KEY` is read from `~/.secrets.env`): `auditar_plan.py` fails with an ERROR if it finds one — the plan ships with the piece.
- **Paid work rule**: Agree TTS or AI-music work and its expected cost with the user before calling a paid API, record it in the project's `BRIEF.md` (`scripts/proyecto.py`), and treat anything beyond that agreement as the user's decision. After an interruption, resume from the project files and produced material; never pay twice for the same voice or music.

## Motor Selector

| Brief | Motor |
|---|---|
| "What color should this be?" / no brand named | **Palette**: `references/paleta.md` (the free-mode color catalog, the color-theory rules and how to pick one from the brief; declare it as `"paleta"` in the plan or `--paleta`) |
| "Where is X documented?" / what does this word mean | **Map**: `references/mapa.md` (the index of this skill: one canonical source per idea, the reading path per task, and the rule that no file is an island) and `references/glosario.md` (the skill's own vocabulary) |
| Resume, continue, or pick up a video project | **Memory**: `python scripts/proyecto.py {carpeta}` (BRIEF, TRATAMIENTO, PROGRESO, TIMELINE; never overwrites) |
| "Is this piece good enough to ship?" | **Awards gate**: `python scripts/puntuar.py final.mp4 --plan plan.json` (four axes measured, four of judgment, gate: no axis under 4 and mean 4.3) |
| "Which scene fits this idea?" | **Index**: `references/intencion-escena.md` (vague request → scene → motion recipe) |
| Write or check the on-screen copy | **Copy**: `references/copy.md` + `scripts/lint_copy.py` (the copy is authored before the plan and checked against the engine's own auto-fit) |
| Check the piece before delivering | **Gate**: `scripts/qa_entrega.py` (plan, copy, render, spec and motion in one verdict; `references/qa-entrega.md`) |
| Ad with scenes and narration | **Plan**: `plan.json` + `scripts/render_plan.py` (39 scene types in `references/escenas.md`; portable concepts in `references/escenas-extendidas.md`) |
| Meeting or transcript summary | **Composition**: pick the moments (`references/scoring-shorts.md`) + styles from `references/estilos.md`, then the create path (Step 1→5) or the edit path (Step 6); the v2 pipeline with its own scripts (`references/pipeline-resumen.md`) is legacy |
| Cinematic film 16:9 | **Cine**: recipes in `references/cine.md` (with brand pack: `scripts/film_marca_v2.py` or `scripts/film_marca.py`) |
| See what the engine can draw (the 39 scene types) | **Gallery**: `scripts/galeria.py` (renders every scene of the catalog: `references/escenas.md`) |
| Keep the counts of the skill true | **Counts**: `scripts/actualizar_conteos.py` (rewrites the numbers the map and this file publish; `--check` only reports) |
| Keep the installed copy in sync | **Install**: `scripts/sincronizar_instalada.py` (extracts what is published and deletes the bytecode cache, so the copy never runs code that no longer exists) |
| Quick kinetic card (one phrase) | **Quick**: recipe `quick-kinetic` in `references/modos-rapidos.md` |
| Clip assembly with music | **Quick**: recipe `quick-montage` in `references/modos-rapidos.md` |
| Trim or adapt an existing video | **Quick**: recipe `quick-cut` in `references/modos-rapidos.md` |
| Vertical short from a long video | **Shorts**: `shorts-plan.json` (schema in `references/shorts-plan-schema.md`) + `scripts/ffmpeg_tools/shorts_plan.py` |
| Real video + animation complementing it | **Hybrid**: `references/modos-produccion.md` (bridges, layers, continuity) |
| Existing video + background music | `scripts/musica.py musiconly -v video.mp4 -m mus.mp3 -o final.mp4` |
| Video + voice-over + music with ducking | `scripts/musica.py gen` then `mix` (music breathes under voice) |
| Clip editing (join, cut, fade, PiP, split screen, GIF, etc.) | **Montaje**: `scripts/ffmpeg_tools/montaje.py` (19 operations in `references/montaje.md`) |
| "Make one like this video" / clone or adapt a reference (file or link) | **Reference**: Step 7 below + `references/referencia-video.md` (project memory, ingestion, word-labeled grids, ANALYSIS/TIMELINE, transformation lenses) |
| Podcast, street interview, ranking, talking head, explainer, narration, short drama, music or lyric video | **Formats**: `references/formatos.md` (what carries each format and which tool serves it), combined with the motor that renders it |
| New piece with no brand pack, or a piece that looks generic / "AI-made" | **Art direction**: Step 2 + `references/direccion-de-arte.md` (idea from the subject, dealt directions, tells registry) |
| "Make it bolder / calmer / simpler", polish, animate, retype, recolor, adapt | **Passes**: `references/pasadas.md` (scoped refinements that change only what was named) |
| Verify deliverable against platform spec | **Delivery**: `scripts/ffmpeg_tools/delivery_check.py final.mp4 --platform reels` (specs in `scripts/ffmpeg_tools/_delivery.py`; CLI contract in `references/cli-contract.md`) |
| Complex programmatic animation | **Remotion** (optional): `references/remotion.md` |
| Deterministic HTML piece or data re-render | **HyperFrames** (optional): `references/hyperframes.md` |
| One-shot motion graphics film | **Prompts**: `references/prompt-motion-graphics.md` and `references/recetas-ai-video.md` |

Complete skill architecture map: `references/arquitectura.md`.

**Every row above ends at the gate.** Whichever row you pick, the deliverable
goes through `scripts/qa_entrega.py` and the awards rubric before it ships:
Step 5 for an animated piece (with `--plan`), Step 6 for an edited one
(without).

## Instructions

`references/mapa.md` is the index of this skill: 55 references with one canonical source per idea, the reading path for each kind of task, and the rule that no file is an island. Read it before anything else, and when a rule seems to live in two places. The skill's own vocabulary (mancha, spot, remate, hold, pack, gate) is in `references/glosario.md`.

**Two paths. Pick one before you touch a file:**

| the user wants | go to |
|---|---|
| **create** a video (ad, explainer, resumen, short, film) | **Step 1 → Step 5** below: environment, project memory, plan, render, audio, QA |
| **edit** footage they already have (trim, captions, music, remix, clone a reference) | **Step 6** (footage and transcripts) or **Step 7** (clone a reference) — the plan of Steps 2-4 is only for the parts you *animate*, and `scripts/ffmpeg_tools/montaje.py` does the rest |

Both paths end at the **gate**: nothing ships without `scripts/qa_entrega.py` and the awards rubric. The create path measures composition from the plan (`--plan`); the edit path has no plan, so the gate runs on the render and axis 4 is judged by eye.

### Step 1: Validate Environment and Capabilities

Check available binaries, fonts, and Python libraries before planning or rendering (`references/capacidades.md`).

```bash
python scripts/check_env.py
```

Expected output: `ENTORNO LISTO` (or a clear diagnostic listing any missing optional dependency and its fallback).

### Step 2: Open the Project Memory, Then Author the Plan

A project is a folder with a memory: `BRIEF.md` (what was asked, the facts, the limits, the agreed budget), `TRATAMIENTO.md` (the creative answer), `PROGRESO.md` (where we are now) and `TIMELINE.md` (what happens when). It is what lets the work resume in another conversation without redoing it or paying twice for the same voice.

```bash
python scripts/proyecto.py {carpeta}
```

Run it before writing the plan and again whenever the brief changes. It never overwrites (`references/auto-mejora.md`).

Before the plan, decide the look instead of defaulting to it (`references/direccion-de-arte.md`): inventory what only this subject has, write the argument as claims with proof (a scene with no claim is deleted), pick the mode (persuade, explain, demonstrate, experience), then deal directions and choose one. `python scripts/direccion_arte.py repartir --brief "video de ciberseguridad" --sector ciberseguridad --tono demo --modo explicar --tiene capturas` deals three; `elegir ID --out FOLDER` writes `SISTEMA.md` (the durable visual decisions) and, when the motor composes it, `estilo.json` (a style pack usable with `--brand`). Fill in the idea sentence and pass the competitor test before building. The user's brief and any brand pack always win over the dealt direction.

Then author the plan: write `plan.json` following `references/plan-video.md` (39 scene types, absolute times, optional `at` per element, `voz` field per scene when narrated). Pick the tone first (`references/tonos.md`) and structure the dramatic arc (`references/dramaturgia.md`). See `scripts/demo_plan.json` and `scripts/escenas_muestra.json` for complete examples.

Before writing the scenes, write the argument: one claim per scene with the proof that carries it, in plain text (`references/copy.md` §1). The order of that list is the order of the video, and it is what keeps a piece from falling into the stock sequence.

Then pick the scenes by **intent, not by name**: `references/intencion-escena.md` is the reverse index of the catalog (what the client asks for → which scene → which motion recipe), and it opens with the question every moving element must answer: *what is this movement for?*

```bash
python scripts/auditar_plan.py plan.json
python scripts/speech_estimate.py plan.json
python scripts/lint_copy.py plan.json
```

Expected output: `PLAN VALIDO` with zero overlapping voice segments or missing required scene fields, and `COPY: 0 fallos` (warnings are deliverable; failures mean the engine cannot place the text, or that the plan asks for more than the engine draws). `auditar_plan.py` also warns about generated-look tells (marketing jargon, emoji as icons, placeholders, uncited social proof, long headlines, repeated scenes, uniform cadence); a deliberate exception is declared in the plan's `tells_ok`.


### Step 3: Render Video with Fluidity Motor

Render the plan with spring physics, live backgrounds, and 180-degree shutter motion blur (`references/animacion.md`, `references/fluidez.md`). Use `--blur 1` for fast drafts and `--blur 5` for final delivery. Re-running without `--force` resumes interrupted renders incrementally.

```bash
python scripts/render_plan.py plan.json -o out.mp4 --blur 5
```

Expected output: `out.mp4` rendered at 1080x1920 @30fps (vertical) or 1920x1080 @30fps (horizontal), H.264 `yuv420p`.

### Step 4: Synthesize Voice-Over, SFX, and Music

When the brief includes narration, synthesize voice-over (`references/sonido.md`), align words if needed, generate or select music, and **place the sound effects**. The plan declares the SFX cues (`references/plan-video.md`); `scripts/mezclar_audio.py` resolves each anchor to its instant and mixes voice + ducked music + SFX into the final track (`references/audio.md`).

```bash
python scripts/sfx.py -o assets/sfx/                          # pack de efectos (una vez)
python scripts/voz_off.py plan.json -o voz.mp3 --guion guion.txt   # un segmento por escena + el guion hablado
python scripts/alinear.py voz.mp3 guion.txt -o voz.palabras.json
python scripts/musica.py gen --prompt "modern upbeat electronic" --dur 30 -o mus.mp3
python scripts/beat_grid.py mus.mp3 --json grid.json          # para anclar por beat y por pico
# el camino inverso: si el BEAT se autora primero, la musica nace de el
python scripts/beat_file.py --bpm 120 --duracion 30 -o beat.json  # el beat se autorea primero
python scripts/mezclar_audio.py plan.json --video out.mp4 \
    --voz voz.mp3 --voz-palabras voz.palabras.json \
    --grid grid.json --pack assets/sfx --musica mus.mp3 -o mezclado.mp4
python scripts/ffmpeg_tools/loudness.py mezclado.mp4 -o final.mp4 -I -14 --tp -1.5
python scripts/medir_mezcla.py -v voz.mp3 -m mus.mp3
```

Expected output: `final.mp4` with voice on top, music ducked ~15 dB under active speech, every SFX cue placed at its anchor, and the mix at the delivery loudness (-14 LUFS, true peak -1.5 dBTP). A piece with music but no SFX reads as a video with a background, not as a designed piece.

**The loudness step is part of the mix, not an extra**: the mixer only sums voices, music and cues — it does not normalize. A mix left at the mixer's own level lands around -18 LUFS and the delivery gate rejects it (`delivery:reels`), so `loudness.py` closes the pipeline. Run it before the gate, not after.

**Without an API key**: `python scripts/voz_off.py` stops and says so; there is no silent fallback to a robotic voice. If the user asks for the system voice, `scripts/voz_local.py` does the same job with the same contract (plan in, one audio track out, `--guion` written, the voice placed at `from + 0.4 s`, and a hard failure if two voices overlap): `python scripts/voz_local.py plan.json -o voz.wav --guion guion.txt`. It is a **draft** voice — no emotional direction, since the system voice cannot read `[slowly]` — and that is said to the user. See `references/sonido.md`.

### Step 5: Run Quality Assurance and Verify Delivery

Run the delivery gate: it executes every deterministic check in order and returns one verdict (`references/qa-entrega.md`, `references/auto-qa.md`, `references/checklist-qa.md`, `references/coherencia-espacial.md`). Then verify rhythm (`references/ritmo.md`) and score against the 8-axis awards rubric (`references/rubrica-premios.md`).

```bash
python scripts/qa_entrega.py final.mp4 --plan plan.json
```

Expected output: `ENTREGA: aprobada` with zero defects, zero pops, a motion note of 90 or more, the platform spec met, and the composition measured on the plan (letter at rest ≥ 26 px, safe zone not at its floor, no overlapping text).

The gate ignores the last 0.5 s when checking for black frames: the engine always closes with a fade to black (the last frame is black by design), so without that margin every piece would reject its own ending. Pass `--ignorar-fin 0` to demand that even the last half second has no black.

The awards gate scores the piece on the rubric's eight axes. Four are measured from the render and the plan; four are judgment and the agent answers them by looking at the piece:

```bash
python scripts/puntuar.py final.mp4 --plan plan.json --ejes "1=4,2=5,5=4,7=4"
```

Expected output: the eight axes with their scores, and `GATE: PASA` only when no axis is under 4 and the mean is 4.3 or more.

The delivery gate and the awards gate measure the composition with the **same** engine call (`medir_animacion --plan`), so they cannot disagree about the letter, the safe zone or the overlaps.

The individual checks, when a step fails and you need to look closer:

fix each finding with a scoped pass (`references/pasadas.md`) rather than touching the render with a vague note.
.

```bash
python scripts/auto_qa.py final.mp4
python scripts/verificar_ritmo.py plan.json
python scripts/ffmpeg_tools/delivery_check.py final.mp4 --platform reels
python scripts/medir_animacion.py --video final.mp4
python scripts/medir_animacion.py --plan plan.json
python scripts/medir_contraste.py
```

`medir_contraste.py` is the exception: it does not look at your piece, it walks the engine's scene **catalog** (the text of each scene against the surface under it). Run it when you touch the engine or a palette, not on every delivery.

### Step 6: Edit Footage You Already Have (transcripts, free pieces, post-production)

When summarizing meetings or editing camera-first footage (`references/video-real.md`; the v2 pipeline in `references/pipeline-resumen.md` is legacy):

1. Extract 6 to 10 verified moments from the transcript using `references/scoring-shorts.md`.
2. Choose the visual language in `references/estilos.md` and camera direction in `references/direccion.md`.
3. Apply post-production tools as needed: transcribe (`scripts/ffmpeg_tools/transcribir.py`), remove retakes and silence (`scripts/retakes.py`, `scripts/ffmpeg_tools/silence.py`), apply EDL (`scripts/ffmpeg_tools/aplicar_edl.py`), burn captions (`scripts/ffmpeg_tools/caption.py`), sync cuts to beats (`scripts/beat_grid.py`, `scripts/beat_sync.py`), generate chapters (`scripts/chapters.py`), and bake poster/thumbnails (`scripts/poster_frame.py`, `scripts/ffmpeg_tools/thumbnail.py`, `references/thumbnails.md`).
4. Prepare companion caption in `share-copy.txt` per `references/share-copy.md` and log new production findings via `python scripts/registrar_aprendizaje.py --titulo "Que aprendimos" --detalle "Lo que se vio y por que"` (`references/auto-mejora.md`, `references/lecciones-produccion.md`).
5. **Close at the gate**, like the create path. An edited piece ships on the same terms as an animated one:

```bash
python scripts/qa_entrega.py final.mp4
python scripts/puntuar.py final.mp4 --ejes "1=4,2=4,4=4,5=4,7=4"
```

Without `--plan` the gate checks the render (black frames, freeze, flashes), the platform spec (resolution, fps, duration, loudness, true peak) and the motion coherence (pops, jerks); with `--plan` it also measures letter size, safe zone and overlaps. An edit has no plan, so **axis 4 is judged by eye** — pass it in `--ejes` (`4=4`), don't leave it out.

### Step 7: Clone or Adapt a Reference Video

This is the other half of the editing path: the user brings a video (file or link) and wants "one like this" (`references/referencia-video.md`):

1. Open the project memory: `python scripts/proyecto.py {folder} --referencia {file or url}` creates `BRIEF.md`, `TRATAMIENTO.md`, `PROGRESO.md` and a `TIMELINE.md` per reference (never overwrites) and prints the next commands.
2. Ingest: `python scripts/clonar_video.py analizar --url "{url}" -o referencias/{name}` (download via `scripts/referencia.py`, metadata, audio, cuts, draft `ANALYSIS.md`, `plantilla.json`).
3. Make time visible: `python scripts/alinear.py fuente.mp4 -o fuente.palabras.json` (no script = word-timed transcript), then `python scripts/contact_sheet.py --video fuente.mp4 --cada 1 --palabras fuente.palabras.json --filas 4 -o hoja.png` (spoken words under each tile; `--alrededor "{phrase}"` for a passage, `--todos-los-frames` for motion).
4. Read the whole piece and each visual/sound system (content, placement, entry, behavior, persistence, exit, what it does for the viewer) into `ANALYSIS.md` and `TIMELINE.md`.
5. Transform: keep each element's role, recreate its form for the new person, product or language; anchor events to the new script's words, not the old seconds. Then build with Steps 2-5 and compare source and result by function at corresponding words.

## Output Contract and Success Criteria

- **Resolution and codec**: 1080x1920 @30fps for vertical; 1920x1080 @30fps for horizontal (24fps for cinema pieces). H.264, `yuv420p`, CRF 18-22.
- **Three visual pillars**: Every piece obeys `references/principios.md` (visual coherence, spatial harmony, special effects), `references/tecnicas-video.md`, and `references/tecnicas-reutilizables.md`.
- **Audio and SFX**: Procedural SFX via `scripts/sfx.py` (`click`, `pop`, `drop`, `whoosh`, `ding`, `thud`, `tick`, `swell`), waveform visualization via `scripts/audio_viz.py`, loudness via `scripts/ffmpeg_tools/loudness.py`, pre-TTS duration estimation via `scripts/speech_estimate.py`, voice-over via `scripts/voz_off.py` (ElevenLabs) or `scripts/voz_local.py` (the system voice, no API, a draft).
- **Post-production & Viral Cloning kit**: `scripts/clonar_video.py`, `scripts/referencia.py`, `scripts/ffmpeg_tools/verticalizar.py`, `scripts/ffmpeg_tools/grade.py`, `scripts/ffmpeg_tools/variantes.py`, `scripts/ffmpeg_tools/artesanal.py`, `scripts/ffmpeg_tools/scenes.py`, `scripts/ffmpeg_tools/look.py`, `scripts/ffmpeg_tools/speedramp.py`, `scripts/ffmpeg_tools/_comun.py`, `scripts/ffmpeg_tools/_plataforma.py`.
- **Captions and conversation formats**: `scripts/ffmpeg_tools/caption.py --hablantes "ANA=FFD400,LUIS=4FC3F7"` colors each speaker (prefix `ANA:` in cues or `speaker` from WhisperX) and never mixes speakers in a cue; `scripts/ffmpeg_tools/montaje.py dividir` builds split screens (`references/formatos.md`).
- **Clean workspace**: Save final deliverables in the user-requested output folder, never inside the skill folder.
- **Metrics and validation**:
  - Triggering: >=90% on relevant video requests, 0% on unrelated tasks.
  - Execution: 0 failed tool calls per workflow.
  - Consistency: `python scripts/validate_skill.py` exits 0 (39/39 scenes render, scripts compile, references exist) and unit tests in `scripts/_tests/test_actualizar_conteos.py`, `scripts/_tests/test_auditar_mapa.py`, `scripts/_tests/test_auditar_plan.py`, `scripts/_tests/test_beat_secciones.py`, `scripts/_tests/test_cache_fantasma.py`, `scripts/_tests/test_caption_hablantes.py`, `scripts/_tests/test_chapters.py`, `scripts/_tests/test_comandos_doc.py`, `scripts/_tests/test_core_and_scenes.py`, `scripts/_tests/test_datos_y_critico.py`, `scripts/_tests/test_direccion_arte.py`, `scripts/_tests/test_escala_tipografica.py`, `scripts/_tests/test_escenas_ronda6.py`, `scripts/_tests/test_letra_y_composicion.py`, `scripts/_tests/test_libass.py`, `scripts/_tests/test_lint_copy.py`, `scripts/_tests/test_marca_fondo.py`, `scripts/_tests/test_medir_contraste.py`, `scripts/_tests/test_mezclar_audio.py`, `scripts/_tests/test_movimiento.py`, `scripts/_tests/test_paleta.py`, `scripts/_tests/test_piso_legible.py`, `scripts/_tests/test_puerta_entrega.py`, `scripts/_tests/test_puntuar.py`, `scripts/_tests/test_recorte_de_copy.py`, `scripts/_tests/test_referencia.py`, `scripts/_tests/test_reglas_del_pack.py`, `scripts/_tests/test_sincronizar_instalada.py`, `scripts/_tests/test_speech_estimate_cifras.py`, `scripts/_tests/test_tmp_unico.py`, `scripts/_tests/test_track_y_picos.py` and `scripts/_tests/test_voz_local.py` pass via `python3 -m unittest discover -s scripts/_tests`.

## Examples

### Example 1: Plan-Driven Product Ad

User says: "Make me a 30-second vertical ad for my SaaS product launch"

Actions:

1. Run `python scripts/check_env.py` to confirm environment capabilities.
2. Author `plan.json` using scenes `hero`, `bento`, `stats`, and `final` per `references/plan-video.md` and `references/scene-patterns-from-internet.md`.
3. Audit timing and voice fit with `python scripts/auditar_plan.py plan.json`.
4. Render with `python scripts/render_plan.py plan.json -o ad.mp4 --blur 5`.
5. Run the gate: `python scripts/qa_entrega.py ad.mp4 --plan plan.json`, then `python scripts/puntuar.py ad.mp4 --plan plan.json --ejes "1=4,2=5,5=4,7=4"`.

Result: `ad.mp4` (30s, 1080x1920 @30fps, H.264 `yuv420p`) passing visual and delivery QA.

### Example 2: Animated Meeting Summary

User says: "Summarize this meeting transcript into a vertical video"

Actions:

1. Extract 6 to 10 verified highlights from the transcript (`references/scoring-shorts.md`) with zero invented text.
2. Select the `resumen-animado` style from `references/estilos.md`.
3. Build the sequence per `references/pipeline-resumen.md` and inspect key frames with `scripts/contact_sheet.py`.
4. Close at the gate: `python scripts/qa_entrega.py resumen.mp4` and `python scripts/puntuar.py resumen.mp4 --ejes "1=4,2=4,4=4,5=4,7=4"` (axis 4 by eye: an edit has no plan to measure).

Result: Vertical summary video highlighting verified moments with spring transitions and clean safe zones, approved by the gate.

### Example 3: Add Background Music to an Existing Video

User says: "Add background music to this video"

Actions:

1. Generate music with `python scripts/musica.py gen --prompt "cinematic warm ambient" --dur 30 -o mus.mp3`.
2. Mix with fade-out using `python scripts/musica.py musiconly -v video.mp4 -m mus.mp3 -o final.mp4`.
3. Close at the gate: `python scripts/qa_entrega.py final.mp4` (it checks the platform spec and the loudness of the new mix) and deliver `final.mp4`.

Result: `final.mp4` with balanced background music and smooth fade-out, approved by the gate.

### Example 4: Iterate on a QA Defect

User says: "Fix the clipped title in scene 2"

Actions:

1. Adjust the scene copy or renderer layout (`references/reglas-tecnicas.md`) and re-run `python scripts/render_plan.py plan.json -o ad.mp4`.
2. Record the lesson with `python scripts/registrar_aprendizaje.py --titulo "Que aprendimos" --detalle "Lo que se vio y por que"`.
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
- "make one like this video, but for my product"
- "turn this podcast into a split-screen clip with colored captions"
- "write the copy for this video"
- "check this video before I send it to the client"
- "this video looks generic, make it feel designed"
- "make this scene bolder but keep everything else"

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

### Error: Text renders smaller than the scene next to it

Cause: the line is wider than the safe zone, so the engine shrinks it. With a kinetic title all lines share one size, so the longest line shrinks every line (`references/copy.md` §2).

Solution:

1. Run `python scripts/lint_copy.py plan.json` and read the size it reports for the offending field.
2. Cut words in the copy, not in the font: a nine-word title at 60 px reads worse than five words at 120 px.
3. Re-render. The engine shrinks, it never rewrites, so the fix belongs in the plan.

### Error: Large `.frames` cache directories

Cause: Uncompressed intermediate PNG frames remain on disk after interrupted renders.

Solution:

1. Delete temporary `.frames` directories after final delivery; never store them inside the skill folder.

## Performance Notes

- Take your time to do this thoroughly.
- Quality is more important than speed.
- Do not skip validation steps (`scripts/check_env.py`, `scripts/auditar_plan.py`, `scripts/lint_copy.py`, `scripts/qa_entrega.py`, and `scripts/validate_skill.py`).
