# Efectos talking-head — detalle interno (face tracking)

**No es un catálogo paralelo.** La elección del agente es
`scripts/repertorio.py` (misma superficie que las 45 escenas y los gestos UI).
Este documento y `scripts/data/efectos_talking_head.json` son el **detalle de
producción** cuando la opción resuelta tiene `motor=efecto` o `nativo`.

Fuente: [claude-video-effects](https://github.com/Vibha-Ramprakash/claude-video-effects)
(MIT). Overlays que siguen la cara (YuNet + MediaPipe Selfie Segmenter) sobre
talking-head vertical. **No se añaden a `SCENES`.**

```bash
# elección (catálogo único)
python scripts/repertorio.py sugerir --pedido "palabra gigante detrás de mi cara"
python scripts/repertorio.py resolver --id orbit

# producción (motor interno)
python scripts/efectos_talking_head.py receta --fx orbit --start 3 --end 6
python scripts/efectos_talking_head.py validar
```

## 0. Cuándo produce este motor (no cuándo “entra a otro catálogo”)

Se produce por aquí cuando `resolver` devolvió `motor=efecto` (o `nativo`) y:

- Hay **video real con persona a cámara** y el brief pide un overlay anclado
  a la cara / detrás de la cabeza, **o**
- La opción marca `preferir=nativo` → se usa el motor EditorIA indicado
  (`grade.py`, `chat`, `constancia`…) sin clonar CVE.

Si el material es gráfica pura sin cara, `resolver` / `preferir` ya apuntan
al equivalente nativo. Soft-UI de producto → opción `motor=gesto` del mismo
repertorio. Escena de plan → `motor=escena`.

`preferir` en el JSON:

| valor | significa |
|---|---|
| `externo` | Face-track CVE en `/tmp` |
| `nativo` | EditorIA ya lo cubre sin CVE |
| `ambos` | Con cara → CVE; sin cara → nativo indicado |

## 1. Cómo se produce

1. Ya elegiste con `repertorio.py sugerir` / `resolver` (no con un menú aparte).
2. Si la vía es externa: **declarar** clone en `/tmp` + `.venv` CVE
   (`capacidades.md`). Nunca degradar a un fade en silencio.
3. `efectos_talking_head.py receta --fx` imprime clone→setup→render→rm.
4. Ventanas **1.5–4 s**. Zoom ≤ 2×. Copy/cifras/color: brief / pack.
5. Limpiar `/tmp/claude-video-effects`. No submodule. No vendorizar.
6. Puerta: `qa_entrega.py` (`video-real.md`).

## 2. Relación con el resto del mapa

| ya existe | qué aporta este detalle |
|---|---|
| `repertorio.py` | la **elección**; aquí la receta CVE / nativo |
| `video-real.md` / `formatos.md` | oficio de editar talking-head |
| `modos-produccion.md` | híbrido footage+animación |
| `grade.py` / `look.py` | `moody` → nativo |
| `hand-draw.md` | doodle offline; scribble/pause-point con cara usan CVE |
| `escenas.md` | equivalentes sin face-track (no tipos nuevos) |
| `motion-ui.md` | gesto de interfaz (también vía repertorio) |

## 3. Qué NO se trae (a propósito)

Inventario en el JSON (`descartado_a_proposito`): no vendorizar `fx.py` ni
modelos; no submodule; no hinchar `SCENES`; SFX/captions en `sfx.md` /
`caption.py`; marca demo fuera. Looks nombrados = mismo fx con `look=…`.

El efecto CVE `timeline` se expone en el catálogo único como `edit-timeline`
(colisión con la escena `timeline` del plan); `receta` usa el nombre CVE.

## 4. Stack del motor externo (referencia)

- Python 3.12 venv del clone: `numpy`, `opencv-python`, `pillow`, `mediapipe`.
- `words.py` del clone para anclar a “cuando digo X”; o `alinear.py` /
  `transcribir.py` nativos si solo hace falta el timing.

---

→ Canónico: `references/animacion.md` · Dominio: movimiento · Vecinos: `references/video-real.md`, `references/modos-produccion.md`, `references/capacidades.md`, `references/hand-draw.md`, `references/motion-ui.md`
