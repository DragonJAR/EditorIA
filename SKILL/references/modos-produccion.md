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
