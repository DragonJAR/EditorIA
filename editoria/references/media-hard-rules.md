# Media-tooling Hard Rules & Anti-patterns — EditorIA mapping

EditorIA inherits the **12 Hard Rules and 13 Anti-patterns** of
[media-tooling](https://github.com/kumanday/media-tooling) (battle-tested in
production by EditorIA, Skill-Editor-IA, and the HyperFrames wrapper).
This doc maps each rule to where EditorIA enforces it, and which don't
apply (because EditorIA is animation-first, not camera-first).

## Hard Rules

| # | Rule | Status in EditorIA | Where |
|---|-------|--------------------|-------|
| 1 | Subtitles applied **last** in filter chain | **OK** | `scripts/ffmpeg_tools/caption.py` and the "first the frame, then the text" rule in `reglas-tecnicas.md` |
| 2 | Per-segment extract + lossless concat (never single-pass filtergraph) | **OK** | `scripts/ffmpeg_tools/01_cut_silences` and `aplicar_edl.py` (concat demuxer, no recode) |
| 3 | 30ms audio fades at every segment boundary | **OK** | `scripts/ffmpeg_tools/aplicar_edl.py` (30ms micro-fade in each cut; verified in reglas-tecnicas) |
| 4 | Overlay PTS shift (`setpts=PTS-STARTPTS+T/TB`) | **OK** | `scripts/ffmpeg_tools/aplicar_edl.py` (Hard Rule 4 explicit in the code) |
| 5 | Master SRT uses output-timeline offsets | **OK** | `scripts/ffmpeg_tools/caption.py` (master SRT re-mapped to the output timeline) |
| 6 | Never cut inside a word | **OK** | `scripts/alinear.py` (aligns exact words; cuts at word boundaries) |
| 7 | Pad cut edges 30-200 ms (working window) | **OK** | `scripts/ffmpeg_tools/aplicar_edl.py` (working window configurable) |
| 8 | Word-level verbatim ASR only (never SRT phrase-mode) | **OK** | `scripts/alinear.py` returns `[{texto, inicio, fin, confianza}]`; never Whisper SRT round-trip |
| 9 | Cache transcripts (never re-transcribe unchanged sources) | **OK** | `scripts/voz_off.py` content-addressed cache (md5 of text+voice+model) |
| 10 | Workers/subagents with disjoint scope for animation slots | **Partial** | EditorIA is single-threaded by design; long renders run as independent background processes instead of workers. Cuando se delega una parte, el encargo se escribe con el brief (`references/brief.md`) |
| 11 | **Confirm strategy with the user before executing** | **OK** | `SKILL.md` workflow A and B: the agent proposes and confirms before rendering |
| 12 | Outputs in the project directory, never clobber source | **OK** | `render_plan.py` uses output.frames (regenerable temp dir) and output.mp4 (never touches inputs) |

## Anti-patterns

| # | Anti-pattern | Status in EditorIA | Where / Fix |
|---|--------------|--------------------|-------------|
| 1 | Hierarchical pre-computed codec formats (ProRes, etc.) | **OK** | `render_plan.py` uses H.264 directly |
| 2 | Hand-tuned moment-scoring functions | **OK** | El scoring no se escribe a mano: `scripts/ffmpeg_tools/scenes.py` mide los cortes, la envolvente RMS y los picos, y el clon (`clonar_video.py analizar`) usa esa medicion en vez de suponer por posicion |
| 3 | Whisper SRT output (loses sub-second gap data) | **OK** | `alinear.py` consumes word_timestamps; never uses SRT from Whisper as input |
| 4 | Running Whisper locally on CPU | **OK** | `check_env.py` reports Whisper as optional; default is to use the cloud via voz_off (ElevenLabs) |
| 5 | Burning subtitles before compositing overlays | **OK** | reglas-tecnicas.md: "first the frame, then the text" |
| 6 | Single-pass filtergraph with multiple sources | **OK** | `aplicar_edl.py` uses concat demuxer (lossless) |
| 7 | **Linear animation easing (always use cubic)** | **OK** | `render_plan.py` `ease_in_out` and `ease_out` are cubic; no linear easing in the code |
| 8 | Hard audio cuts with no fade | **OK** | `aplicar_edl.py` applies 30ms fades on both edges |
| 9 | **Typing text centered on partial string** | **Known** | `sc_typewriter` currently draws left-anchored. Future polish; current behavior works (chat-style) |
| 10 | Using workers for parallel media processing | **OK** | EditorIA is single-threaded; long renders run as independent background processes |
| 11 | Editing before confirming strategy with the user | **OK** | `SKILL.md` workflow A: step 0 validate, step 1 plan, step 2 confirm, step 3 render |
| 12 | Cutting inside a spoken word | **OK** | `alinear.py` only returns VERBATIM word-level times |
| 13 | Assuming content type (always generalize) | **OK** | The EditorIA trigger is "video" generic, not "ad" or "podcast" |

## Summary

**Compliance: 11 OK / 1 partial (rule 10) / 1 future improvement (anti-pattern 9).**

Rules 1-9 and 11-12 are **production-critical** and EditorIA complies.
Rule 10 (workers) is **partial** because EditorIA is single-threaded by design.
Anti-pattern 9 (typewriter) is a **polish improvement** known.

## What the model can do with this doc

When the model makes a change to EditorIA, it can use this table to verify
that it does not break any Hard Rule. The doc also serves as a **quick
reference** of where each rule lives, so the model can read the relevant code.

---

→ Canónico: `references/plan-video.md` · Dominio: plan · Vecinos: `references/reglas-tecnicas.md`, `references/modos-produccion.md`, `references/qa-entrega.md`
