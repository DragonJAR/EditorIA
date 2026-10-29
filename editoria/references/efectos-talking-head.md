# Efectos talking-head — face tracking sobre footage real

Fuente: [claude-video-effects](https://github.com/Vibha-Ramprakash/claude-video-effects)
(MIT). Son **45 overlays que siguen la cara** (YuNet + MediaPipe Selfie
Segmenter) sobre un talking-head vertical. No son escenas del motor de
planes: no se añaden a `SCENES` ni a `repertorio.json`.

**Fuente de verdad del catálogo** (ids, ocasiones, vía, cómo adaptar,
aliases): `scripts/data/efectos_talking_head.json`. Este documento es la
doctrina y la entrada; el JSON es el inventario. No se copia la tabla aquí.

```bash
python scripts/efectos_talking_head.py listar
python scripts/efectos_talking_head.py sugerir --pedido "palabra gigante detrás de mi cara"
python scripts/efectos_talking_head.py receta --fx orbit --start 3 --end 6
python scripts/efectos_talking_head.py validar
```

## 0. Cuándo se entra (y cuándo no)

Se entra cuando:

- El material es un **video real con persona a cámara** (talking-head,
  creator, demo hablada) y el brief pide un efecto que **se ancla a la
  cara** o se sienta *detrás* de la cabeza.
- El usuario nombra un fx del catálogo (`orbit`, `spotlight`,
  `glass-widgets`…) o describe su firma (“reels orbitando mi cabeza”,
  “apaga las luces y déjame lit”).

No se entra cuando:

- La pieza es gráfica pura (sin cara): se usa el **equivalente nativo**
  que declara cada fila (`nativo` en el JSON) — `constancia`/`pasos`,
  `chat`, `countdown`, `grade.py`, `hand_draw.py`, `tarjeta_cristal`, etc.
- El pedido es soft-UI de producto/sitio → `references/motion-ui.md`.
- El pedido es una escena del catálogo por intención →
  `repertorio.py` / `intencion-escena.md`.

`preferir` en el JSON:

| valor | significa |
|---|---|
| `externo` | Solo tiene sentido con face-track CVE |
| `nativo` | EditorIA ya lo cubre mejor sin CVE (p. ej. `moody` → `grade.py`) |
| `ambos` | Con cara → CVE; sin cara o gráfica → motor nativo indicado |

## 1. Cómo se pide (el agente elige, no adivina)

1. Confirmar que hay footage con cara (o declarar que falta).
2. `efectos_talking_head.py sugerir --pedido "..."` o el fx nombrado.
3. Leer `preferir` / `nativo` / `adaptar` de esa fila — una sola fuente.
4. Si la vía es externa: **declarar** en la primera respuesta que se clona
   el repo en `/tmp` y se usa su `.venv` (MediaPipe, OpenCV, Pillow) —
   `references/capacidades.md`. Nunca degradar a un fade en silencio.
5. Plan CVE al lado del video (`*_effects.json`), check frames
   (`--still`), luego render. Ventanas **1.5–4 s**. Zoom ≤ 2×.
6. Copy, cifras y color: brief / brand pack. No el demo “Claude”.
7. Limpiar `/tmp/claude-video-effects` al terminar. No submodule.
8. Puerta: `qa_entrega.py` como el resto de la edición de footage
   (`references/video-real.md`).

`receta --fx` imprime los comandos exactos (clone → setup → fx.py → rm).

## 2. Relación con el resto del mapa

| ya existe | qué aporta esta técnica |
|---|---|
| `video-real.md` / `formatos.md` | oficio de editar talking-head; aquí el **selector de overlays con cara** |
| `modos-produccion.md` | híbrido footage+animación; aquí el motor externo cuando el ancla es la cara |
| `grade.py` / `look.py` | grades nativos; `moody` del CVE se mapea aquí (`preferir=nativo`) |
| `hand-draw.md` | doodle offline; `scribble`/`pause-point` usan CVE solo sobre cara |
| `escenas.md` (`chat`, `countdown`, `constancia`, `pasos`, `timeline`…) | equivalentes **sin** face-track; no se duplican como tipos nuevos |
| `motion-ui.md` | gesto de interfaz en gráfica/producto; no face-track |

## 3. Qué NO se trae (a propósito)

Inventario canónico en el JSON (`descartado_a_proposito`): no se vendoriza
`fx.py` ni los modelos ONNX/TFLite ni las fonts del repo; no hay submodule;
no se hincha `SCENES`; SFX/captions siguen en `sfx.md` / `caption.py`; la
marca demo no entra (regla marca-blanca).

Looks nombrados del origen (`glitter-spotlight`, `cover-star` editorial,
`liquid-glass-graph` bento) son el **mismo** fx con `look=…`; no suman al
conteo de 45 — viven en `looks_nombrados` del JSON.

## 4. Stack del motor externo (referencia)

- Python 3.12 venv propio del clone: `numpy`, `opencv-python`, `pillow`,
  `mediapipe` (+ models YuNet / selfie segmenter en el repo).
- `words.py` del clone (bajo `/tmp/claude-video-effects/`): word-times
  (faster-whisper / mlx-whisper) para anclar a “cuando digo X”. EditorIA
  ya tiene `alinear.py` / `transcribir.py`; se usa el del clone si se está
  en su pipeline, o el nativo si solo hace falta el timing.

---

→ Canónico: `references/animacion.md` · Dominio: movimiento · Vecinos: `references/video-real.md`, `references/modos-produccion.md`, `references/capacidades.md`, `references/hand-draw.md`, `references/motion-ui.md`
