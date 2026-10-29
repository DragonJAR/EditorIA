# Trazos a mano / Hand Draw (capacidad)

Material de **trazo dibujado a mano** para piezas que lo piden: pizarra,
anotación sobre footage, doodle cinético o captura por gestos. El motor
Python no gana un canvas interactivo nuevo: gana **utilidades de dominio**
(suavizado, segmentos, viewport, histéresis) y un CLI que pinta overlays
con alfa listos para `montaje.py` / el EDL.

La app de referencia [HandDraw](https://github.com/davbachman/HandDraw)
(MIT) es un lienzo en el navegador controlado por la cámara (MediaPipe):
pinch = dibujar/borrar, puño = pan, dos manos = zoom. **No se vende como
dependencia de la skill.** Se adoptó solo la lógica pura; la UI, el CSS y
el runtime de tracking se quedan fuera (ver qué se descartó abajo).

## Cuándo usarla (y declararla si falta)

- La pieza pide **trazo a mano** legible (pizarra, underline dibujado,
  doodle) y el path crudo tiembla: suavizar antes de pintar.
- Hay un JSON de puntos/trazos (de una captura, de Remotion, de un
  storyboard) y hay que **hornearlo a PNG con alfa** para montarlo sobre
  el video.
- Se reconstruye un lienzo interactivo en Remotion / HyperFrames / canvas
  pictórico y hacen falta las mismas reglas de histéresis y viewport.

Si la pieza pide **captura en vivo por cámara**, eso es el app HandDraw
(o un clon): Node + `@mediapipe/tasks-vision`. Se declara en la primera
respuesta con su comando (`npm i` en el clon) — nunca se entrega el
overlay vacío en silencio (ver `references/capacidades.md`). Pillow ya
cubre el camino offline de la skill (`pintar`).

## Qué aporta el script

`scripts/hand_draw.py` (stdlib + Pillow solo al pintar):

| Operación | Qué hace |
|---|---|
| `suavizar` | EMA + snap sobre puntos o trazos JSON (quita jitter; salta en cambios bruscos) |
| `pintar` | Trazos → PNG RGBA; `--suavizar` aplica el filtro antes de dibujar |

```bash
python scripts/hand_draw.py suavizar puntos.json -o limpio.json
python scripts/hand_draw.py pintar trazos.json -o overlay.png --ancho 1080 --alto 1920 --suavizar
```

Formato mínimo de trazo:

```json
{
  "strokes": [
    {"color": "#FAF8F6", "width": 6, "points": [[120, 200], [180, 240], [260, 220]]},
    {"kind": "eraser", "width": 34, "points": [[200, 210], [220, 210]]}
  ]
}
```

Colores y anchos los pone la pieza (brand pack / modo libre). Los defaults
del script son neutros: el lápiz va en la tinta de la paleta neutra
(`NEUTRO["blanco"]`, 6 px; el `#101827` de antes no se veía sobre video
oscuro) y el borrador mide 34 px; no copiar la paleta demo de HandDraw a
una marca.

## Constantes útiles (DRY con el origen)

| Constante | Valor | Uso |
|---|---|---|
| suavizado idle | α=0.26, snap=170 | puntero en reposo / tracking |
| suavizado dibujo | α=0.42, snap=170 | mientras se pinta (más responsivo) |
| pinch | entra bajo 0.24, sale desde 0.34 | histéresis: no parpadea el trazo |
| puño | entra bajo 1.18, sale desde 1.38 | histéresis del pan |
| zoom viewport | 0.25–6× | cámara sobre el mundo dibujado |

Las funciones viven en el mismo módulo (`suavizar_punto`,
`avanzar_herramienta`, `punto_viewport_a_mundo`, `siguiente_pinch`,
`siguiente_puno`, …) para no duplicar magia en Remotion ni en el motor
pictórico.

## Cómo convive con EditorIA

- **Motor Python**: el PNG con alfa entra como overlay (mismo patrón que
  3D / canvas pre-renderizado). La puerta sigue siendo
  `references/qa-entrega.md`.
- **Draw-on de pizarra** (`references/tecnicas-video.md`): velocidad
  constante en el dash; el suavizado de *puntos de captura* es otra
  capa — se aplica a la polilínea de entrada, no al easing del reveal.
- **Canvas pictórico** (`references/canvas.md`): acuarela y pincel van
  por p5; este módulo es el camino ligero cuando basta tinta + alfa.
- **Remotion / HyperFrames**: reutilizar las constantes y el modelo de
  segmento (`from`/`to` + brocha); no reimplementar la histéresis a ojo.

## Qué se descartó (a propósito)

| Pieza de HandDraw | Por qué no entra |
|---|---|
| App Vite + `main.ts` + UI sidebar | Stack distinto; la skill no es un SPA |
| `styles.css` / look de la demo | Conflicto con el trabajo paralelo de estilos de EditorIA; la identidad la marca el brand pack |
| `@mediapipe/tasks-vision` + `tracking.ts` | Dependencia pesada y opt-in; solo si la pieza captura en vivo |
| Preview de cámara / pills de status | Diagnóstico de la demo, no del entregable |
| Paleta fija rojo/verde/azul/negro | Colores de demo; en EditorIA el color sale del pack o del modo libre |
| Submodule / vendor del repo entero | Basta adoptar el dominio; no hay dependencia permanente |

## Licencia del origen

HandDraw es MIT (Copyright 2026 David Bachman). El módulo
`scripts/hand_draw.py` conserva el aviso de procedencia en su docstring
porque el MIT lo exige sobre porciones sustanciales. No se añade como
submodule ni como dependencia npm.

---

→ Canónico: `references/capacidades.md` · Dominio: herramienta · Vecinos: `references/canvas.md`, `references/tecnicas-video.md`, `references/remotion.md`
