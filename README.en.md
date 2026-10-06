# EditorIA

**AI video editing Swiss army knife**, packaged as a Claude *skill*.

Create, edit, summarize and improve videos (`.mp4`): animated meeting summaries, kinetic typography, plan-based ads, cinematic films and vertical pieces for social media — for any brand or none.

🇪🇸 [Versión en español](README.md)

## Version

`v1.5.0` — **measured animation, not opinions**: a benchmark (`scripts/medir_animacion.py`) scores every scene in 9:16 and 16:9 —things popping in, stutters, motion starting without ease-in, dead time, event density, type size, safe zone and overlapping text— and logs the history in `SKILL/metricas/historial.jsonl` (catalog 80 → 99.35/100, 0 pops). Agent-proof plans: optional `at` (timing derived from each scene's sample), misspelled fields flagged with a suggestion, clear errors in < 1 s, long copy that shrinks or wraps to two lines. Locale-aware numbers (`"numeros": "es"`), a reserved subtitle band (`"subtitulos": true`) and subtitles in the kit's own typeface. Every option of every CLI explained in `--help`.

Previously, `v1.3.0`: 28 scenes (`oferta`, `demo`, `countdown`, `rotulo_inferior`), alpha overlays, template × table, audiograms, word-level karaoke, exact BT.709 color and photosensitivity QA.

## Structure

All skill content lives in the [`SKILL/`](SKILL/) folder:

| Path | Contents |
|---|---|
| `SKILL/SKILL.md` | Skill definition and engine selector |
| `SKILL/scripts/` | Engines and tools (plan renderer, music, voice-over, QA, `ffmpeg_tools/` kit) |
| `SKILL/references/` | Reference docs (installation, scenes, cinema, editing, sound, etc.) |
| `SKILL/brand/` | Brand packs (white-label; `dragonjar.json` included as an example, with its assets in `brand/assets/`) |
| `SKILL/assets/fonts/` | Plus Jakarta Sans and Montserrat (variable fonts, OFL license in `OFL.txt`) |
| `SKILL/film/` | Sample music for the brand film |

## Quality bar

Every piece is scored against an 8-axis award rubric (`SKILL/references/rubrica-premios.md`): idea and hook, dramaturgy, animation, composition, visual system, sound, truthfulness and technical finish. No axis may score below 4/5. Animation craft (the 12 principles applied to motion graphics, 180° shutter motion blur, virtual camera, choreography) lives in `SKILL/references/animacion.md`.

## Installation

1. Copy or link the `SKILL/` folder into Claude's skills directory, named `editoria` (e.g. `~/.claude/skills/editoria/`).
2. Install dependencies for your OS (Windows, macOS or Linux): see `SKILL/references/instalacion.md` (in Spanish).
3. Check your environment capabilities: `python SKILL/scripts/check_env.py`.
4. Optional, for AI voice-over and music: set `ELEVENLABS_API_KEY` in your environment (never inside the skill).

## Quick use

Ask Claude things like: "make me a video", "summarize this meeting", "edit this ad", "improve this video" or "add music to it".

## License

See [LICENSE](LICENSE).
