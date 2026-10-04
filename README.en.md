# EditorIA

**AI video editing Swiss army knife**, packaged as a Claude *skill*.

Create, edit, summarize and improve videos (`.mp4`): animated meeting summaries, kinetic typography, plan-based ads, cinematic films and vertical pieces for social media — for any brand or none.

🇪🇸 [Versión en español](README.md)

## Version

`v1.0.0` — first release.

## Structure

All skill content lives in the [`SKILL/`](SKILL/) folder:

| Path | Contents |
|---|---|
| `SKILL/SKILL.md` | Skill definition and engine selector |
| `SKILL/scripts/` | Engines and tools (plan renderer, music, voice-over, QA, `ffmpeg_tools/` kit) |
| `SKILL/references/` | Reference docs (installation, scenes, cinema, editing, sound, etc.) |
| `SKILL/brand/` | Brand packs (white-label; `dragonjar.json` included as an example) |
| `SKILL/film/`, `SKILL/demo/` | Sample assets |

## Installation

1. Copy or link the `SKILL/` folder into Claude's skills directory, named `editoria`.
2. Install dependencies for your OS (Windows, macOS or Linux): see `SKILL/references/instalacion.md` (in Spanish).
3. Check your environment capabilities: `python SKILL/scripts/check_env.py`.

## Quick use

Ask Claude things like: "make me a video", "summarize this meeting", "edit this ad", "improve this video" or "add music to it".

## License

See [LICENSE](LICENSE).
