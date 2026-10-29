# Flujo talking-head → entrega (navaja suiza)

**Una sola ruta** para el reel vertical con persona a cámara: del bruto al
MP4 publicable. No es un skill paralelo ni un menú aparte: cablea Step 6
(editar), la vertical **editar**, el catálogo único (`repertorio.py`) y la
vertical **publicar**.

Origen destilado (clone-on-demand, sin vendorizar): IT Reelsmaker, HyperFrames
captions/media-use, Remotion skills. Lo que EditorIA ya cubre mejor se
reutiliza; lo nuevo entra como doctrina + identidades en el repertorio.

## Cadena (siempre en este orden)

```text
footage → probe → corte/pause → captions (rail/embed) → motion → master → puerta → publicar
```

| Paso | Qué | Herramienta EditorIA | Cuándo escalar |
|---|---|---|---|
| 1. Probe | duración, fps, rotación, audio | `ffprobe` / `referencia.py` | — |
| 2. Corte / pause | silencios + retakes; sin saltos “hacia atrás” | `silence.py` → `retakes.py` → EDL (`aplicar_edl.py`) | palabra estirada >1 s = toma fusionada (revisar a mano) |
| 3. Captions | modelo **drop / rail / embed**; una identidad visual | `repertorio.py sugerir --pedido "…"` → `resolver` → `caption.py` o `captions_identidades.py receta` | matte detrás de cara / tipografía HF → HyperFrames on-demand |
| 4. Motion | overlay cara o gesto UI (misma superficie) | `repertorio.py` → efecto CVE / gesto / escena | Remotion solo si la gráfica es kit React; declarar Node |
| 5. Master | −14 LUFS, true peak | `loudness.py` (después de quemar captions) | cadena highpass→acompressor en `sonido.md` |
| 6. Puerta | defectos + ejes | `qa_entrega.py` + `puntuar.py` | — |
| 7. Publicar | copy, poster, variantes | `share-copy.md` + `poster_frame.py` / `thumbnail.py` | — |

Comandos típicos (pieza narrada vertical):

```bash
python scripts/ffmpeg_tools/silence.py bruto.mp4 -o sin_sil.mp4
python scripts/retakes.py segmentos.json   # tras transcribir / alinear
python scripts/ffmpeg_tools/aplicar_edl.py …
python scripts/alinear.py corte.mp4 -o palabras.json
python scripts/repertorio.py sugerir --pedido "karaoke vertical talking head"
python scripts/repertorio.py resolver --id cap-rail-karaoke
python scripts/ffmpeg_tools/caption.py corte.mp4 --palabras palabras.json \
  --karaoke --phrase-aware --animate pop -o con_sub.mp4
# motion opcional:
python scripts/repertorio.py sugerir --pedido "spotlight en mi cara"
python scripts/efectos_talking_head.py receta --fx spotlight --start 2 --end 5
python scripts/ffmpeg_tools/loudness.py con_sub.mp4 -o final.mp4 -I -14 --tp -1.5
python scripts/qa_entrega.py final.mp4
python scripts/puntuar.py final.mp4 --ejes "1=4,2=4,4=4,5=4,7=4"
# publicar: references/share-copy.md
```

## Modelo de caption (drop / rail / embed)

Doctrina (HyperFrames captions-overlay + oficio converzzo), **no** un
segundo catálogo:

| Rol | Qué | Cómo en EditorIA |
|---|---|---|
| **drop** | fillers / reinicios | fuera del transcript o fuera de cues; `retakes.py` ya corta tomas |
| **rail** | default verbatim lower-third | identidades `cap-rail-*` / `cap-hablantes` → `caption.py` |
| **embed** | pico tipográfico detrás del sujeto | `cap-embed-matte` (+ slam HF si el brief lo pide); cobertura matte 30–55 % |

Una identidad visual por pieza. Elegir con el **mismo** `repertorio.py` que
escenas y efectos. Detalle: `references/captions-identidades.md`.

## Face-aware (sin menú aparte)

- Texto **nunca** sobre la cara; subtítulos bajo el mentón medido cuando hay
  detector, si no: banda inferior / `--plan` safe zone.
- Zoom / reencuadre: `verticalizar.py` + face-safe en `video-real.md`; cámara
  virtual Remotion solo si el brief pide kit React (declarar).
- Overlays anclados a la cara: opción `motor=efecto` del repertorio (CVE en
  `/tmp`), no un skill Reelsmaker paralelo.

## Media (ledger, sin menú Media-Use)

Doctrina Media Use de HyperFrames, aplicada a lo nativo:

- Assets locales antes del render; no fetch a mitad de encode.
- Música / SFX / VO: `musica.py`, `sfx.py`, `voz_off.py` / `voz_local.py`.
- Grades: `grade.py` / `look.py` (no CSS filter como “look” final).
- Ofrecer huecos de media **una vez**; no añadir B-roll de pago en silencio.
  Stock/IA online (Reelsmaker-online): solo si el brief lo nombra y hay “sí”
  con precio — no se cablea por defecto.

## Remotion / HyperFrames / Reelsmaker

| Capacidad | Rol en este flujo | Cómo |
|---|---|---|
| Motor Python + ffmpeg | camino por defecto | `caption.py`, montaje, loudness, puerta |
| HyperFrames | HTML seekable, matte embed, registry captions | `captions_identidades.py receta` / `hyperframes.md` |
| Remotion | kit React / skills oficiales on-demand | `npx skills add remotion-dev/skills` cuando la pieza es Remotion (`remotion.md`) |
| IT Reelsmaker | oficio + números verificados | destilado aquí y en `video-real.md`; **no** instalar el plugin como menú |

## Qué no hacer

- No abrir “skill Reelsmaker” / “skill Media Use” / “skill Captions HF” como
  rutas paralelas al repertorio o a Step 6.
- No vendorizar repos en el árbol; `/tmp` o `npx` on-demand, luego limpiar.
- No quemar captions **después** del loudness ni gatear un intermedio.
- No tocar `render_plan.SCENES` para meter captions (son overlays de editar).

---

→ Canónico: `references/formatos.md` · Dominio: produccion · Vecinos: `references/video-real.md`, `references/captions-identidades.md`, `references/share-copy.md`, `references/efectos-talking-head.md`, `references/hyperframes.md`
