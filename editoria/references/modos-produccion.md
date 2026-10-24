# Modos de producción — real, animado e híbrido

EditorIA produce en tres modos. Las técnicas son las mismas (`tecnicas-video.md`);
lo que cambia es **dónde vive cada efecto** y cómo se cose la costura entre modos.
La regla de oro del híbrido: el espectador nunca debe sentir el cambio de modo.

## Modo 1 — Video real (personas grabadas)

El material manda. Ver `references/video-real.md` (pipeline completo).
Los efectos aquí son **corrección y realce**, no invención:
- Grade hacia marca (gradient map sutil, film emulation) para que el footage
  rime con la identidad.
- Punch-ins, speed ramps y J/L cuts para ritmo; nada que rompa la credibilidad
  de la persona en cámara.
- Captions y lower-thirds animados como única capa gráfica.

## Modo 2 — Animación / 100% IA

Construcción total: `render_plan.py`, films de marca, kinetic typography.
Aquí los efectos son **el material**: resortes, fondos vivos, dataviz,
partículas, transiciones de mancha. Ver `references/plan-video.md`,
`references/fluidez.md`, `references/cine.md`.

## Modo 3 — Híbrido (real + animación, el modo por defecto cuando hay ambos)

El video real y la animación se complementan: la persona cuenta, la animación
explica. La integración debe ser coherente, confiable y orgánica.

### Footage generado: revisa los clips ANTES de componer

Un generador de video por IA no entrega solo imagenes: **inventa**. En la
practica ha metido una tarjeta de presentacion con un nombre y una foto, un
rostro reconocible y un monitor quemado a blanco. Todo eso parece material
real de marca y no lo es: si compone sobre el, la pieza afirma cosas que
nunca dijeron el cliente.

Por eso, antes de componer, **mira una hoja de contactos de TODOS los clips
generados** (`scripts/contact_sheet.py --video clip.mp4 --cada 1 -o hoja.png`)
y descarta el clip que tenga texto inventado, credenciales, un rostro
identificable o una marca de agua. Si hay que regenerar, se regenera con el
prompt corregido ("sin objetos sobre la mesa", "el rostro nunca visible",
"sin pantallas ni monitores"), no se disimula con un recorte.

Es el mismo principio que aplica a las capturas de producto: **no se dibuja
lo que no existe**; se usa lo real, o se deja hueco.

### Puentes visuales (la costura invisible)

- **Match cut real→animado**: el gesto o la forma del plano real continúa en la
  animación (una mano que señala → una flecha animada que nace del dedo; un
  giro de cámara → un wipe en la misma dirección).
- **Zoom-through**: la cámara "entra" por un punto del footage (una pantalla,
  el hueco de una letra del lower-third) y emerge en la escena animada.
- **Máscara con elemento real**: un objeto del plano (puerta, persona que pasa)
  barre el cuadro y revela la animación detrás.
- **Color como pegamento**: el mismo grade en ambos lados del corte. Si la
  animación usa los colores del brand pack, el footage lleva ese grade antes del corte —
  nunca un salto de look. `scripts/ffmpeg_tools/grade.py` aplica el grade de
  marca determinista (misma receta = mismo look).

### Capas de animación sobre footage (sin salir del plano real)

- Lower-thirds, name pills y callouts con entrada por resorte.
- Dataviz anclada a lo que la persona dice: la barra crece mientras la menciona;
  el número aterriza en la palabra exacta (ver `references/audio.md`: anchors).
- Annotation pins sobre producto/pantalla que la persona muestra.
- Subrayados y círculos dibujados (draw-on) sobre el footage para señalar.

### Componer la animación sobre el footage (el paso automático)

Lo anterior es para cuando **otra persona** edita la pieza. Cuando la
compone el agente, el overlay se mete con una cadena de filtros: la
mascara del desenfoque sale del **ALFA** del overlay (no de un rectangulo),
asi que el fondo se desenfoca SOLO detras de la tipografia y el resto del
cuadro queda nitido.

1. Render del overlay con alfa: `render_plan.py plan.json -o capa.mov`
   (ProRes 4444 ✓) y el footage base **a la misma tasa** (24 fps si el
   footage es de 24: convertirlo a 30 duplica cuadros y el medidor los lee
   como tirones ✗).
2. Composicion (ffmpeg, un solo comando):

```bash
ffmpeg -v error -y -i base.mp4 -i capa.mov -i velo.png -i audio.wav \
  -filter_complex "\
[0:v]split=2[sh][fb];\
[fb]boxblur=luma_radius=24:luma_power=2,eq=saturation=0.40:brightness=-0.20:contrast=0.9[bl];\
[1:v]split=2[ov][ovs];\
[ovs]format=rgba,alphaextract,format=gray[al];\
[al]boxblur=luma_radius=45:luma_power=2[ab];\
[ab]lut=y='if(gt(val,28),min(1,(val-28)/130),0)'[mk];\
[sh][bl][mk]maskedmerge[mm];\
[mm][ov]overlay=0:0:format=auto[ov2];\
[ov2][2:v]overlay=0:0:format=auto,format=yuv420p[v]" \
  -map "[v]" -map 3:a -t DUR -r 24 \
  -c:v libx264 -preset slow -crf 19 -profile:v high -level 4.1 \
  -pix_fmt yuv420p -movflags +faststart -c:a aac -b:a 192k -ar 48000 -shortest out.mp4
```

Que hace cada trozo, porque tocarlos sin entenderlos rompe la pieza:

- `split` + `boxblur` + `eq`: el base se desenfoca, se desatura y se oscurece.
- `alphaextract`: la mascara sale del alfa del overlay (donde hay letra).
- `boxblur` + `lut`: la mascara se ablanda (el borde del desenfoque no se
  nota como borde) y se recorta para que solo la tipografia.
- `maskedmerge`: el base **nítido** vuelve donde NO hay letra.
- `overlay` dos veces: primero el overlay, luego el velo de marca (el PNG que
  oscurece arriba y abajo, donde llega la UI de la plataforma).
- `-r 24` y `-t DUR`: la tasa del footage y la duracion del plan.

### Overlays con alfa (entregar capas al editor)

Cuando el footage lo edita otra persona (o vive en OBS), el gráfico se entrega
como capa transparente, no quemado: `render_plan.py plan.json -o capa.mov`
(ProRes 4444) o `-o capa.webm` (VP9). La escena `rotulo_inferior` es el caso
típico; con `--datos` sale uno por ponente.

| Herramienta | Archivo | Detalle |
|---|---|---|
| Premiere Pro | `.mov` | no lee el alfa de WebM: lo transparente entraría negro |
| DaVinci Resolve | `.mov` | si los bordes se ven oscuros: Clip Attributes → Alpha Mode → Straight |
| Final Cut Pro | `.mov` | clip conectado sobre el footage |
| OBS Studio | `.webm` | Media Source, sin "Loop", con "Restart playback when source becomes active"; a 0,0 sin escalar |
| Web | `.webm` | Chrome/Edge leen el alfa; Safari solo HEVC con alfa (`hevc_videotoolbox`, solo macOS) |
| Editor sin alfa | `.mp4` sobre verde | chroma key en el editor; el texto fino puede orlar |

El archivo es de cuadro completo con el gráfico ya en su sitio: se coloca a
0,0 sin escalar. Empieza y termina vacío para no aparecer ni cortarse de golpe.

### Beats animados entre segmentos reales (saliendo del plano)

- Un beat animado por idea: dato, proceso, contraste, payoff. Nunca dos beats
  animados seguidos sin volver a la persona (se pierde el hilo humano).
- Duración: el beat dura lo que tarda la idea, no más (2–7s por dato).
- Entrada y salida con el mismo idioma de transición en todo el video
  (un estilo de transición por pieza).

### Chromakey: sujeto real sobre fondo animado

La técnica puente del híbrido: grabar a la persona en verde y componerla
sobre el mundo animado. Receta completa en `tecnicas-video.md` → "Chromakey /
green screen". Lo crítico para que se lea orgánico: spill suppression en
pelo y bordes, igualar luz y ruido entre sujeto y fondo (mismo grain), y
rehechas las sombras del sujeto en el fondo — nunca flotando.

### Continuidad de audio (lo que más vende la mezcla)

- Una sola voz en off o una sola persona: nunca mezclar voz sintética y humana
  en la misma pieza salvo doblaje explícito.
- Una sola cama musical con ducking en ambos modos; los SFX (whoosh en el
  corte real→animado) son el pegamento audible.
- El hit del whoosh cae exacto en el frame del cambio de modo.

### Ritmo unificado

- Una curva de energía para toda la pieza, sin importar el modo. Los beats
  animados no son "descanso": llevan la misma densidad de cortes.
- Regla: si al quitar la animación el video sigue funcionando, la animación
  sobra. Cada beat animado debe ganar su lugar (explica lo que la cámara no
  puede mostrar).

## Decidir el modo

| Caso | Modo |
|---|---|
| Testimonio, entrevista, evento grabado | Real, con capas animadas puntuales |
| Concepto abstracto, datos, marca | Animado |
| Persona explicando algo complejo | Híbrido: persona + dataviz/diagramas |
| No hay footage y no se puede grabar | Animado (o real con stock + grade) |
| Hay footage pero plano/aburrido | Híbrido: ritmo en edición + beats animados |

Ante la duda: híbrido. La persona da confianza, la animación da claridad.

## Promo de producto desde páginas reales

Cuando el producto **es** una web o una app y hay que enseñarlo: capturar
las páginas de verdad y montar la promo sobre ellas.

`Vincentwei1021/video-shotcraft` (Apache-2.0) hace exactamente ese camino:
captura tus páginas, elige de **124 recetas de plano** (movimiento 2.5D, cortes
al beat, diseño de sonido) y renderiza la promo en Remotion.

- **Las recetas de plano son un vocabulario de movimiento**: 2.5D (la
  página en perspectiva, con cámara), entradas por elemento, cortes al
  compás. Alimenta `references/animacion.md` y `references/fluidez.md`.
- **El render** es Remotion, que ya está integrado (`references/remotion.md`).
- **La plantilla validada** ("Ink Press") y su flujo son **de ese repo**: si se
  usa, se usa su camino (su SKILL.md) y no se copia aquí. La frontera es la
  misma que con las recetas: fuente, no copia.

El resto (la promo montada con el motor y con el overlay del website) sigue
siendo el camino de esta skill: el website se renderiza con alfa y se compone
como cualquier otra capa (`references/3d.md`).

---

→ Canónico: `references/formatos.md` · Dominio: produccion · Vecinos: `references/modos-rapidos.md`, `references/media-hard-rules.md`, `references/prompt-motion-graphics.md`
