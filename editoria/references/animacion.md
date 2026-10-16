# Animación — el oficio que separa un video de premio de "un video con IA"

`fluidez.md` dice *que* todo debe moverse con resortes. Este documento dice
*cómo* se anima para que el movimiento tenga peso, intención y acabado de
estudio. Se aplica a todos los motores (plan, composición libre, Remotion,
HyperFrames). Ante conflicto: el brand pack fija identidad, `fluidez.md` fija
el motor, y este documento fija el oficio.

## 1. Los 12 principios, traducidos a motion graphics

Cada principio con su regla aplicable y su valor por defecto. Un render que
viole uno sin motivo está sin terminar.

| Principio | Regla en EditorIA | Valor por defecto |
|---|---|---|
| **Squash & stretch** | Solo en piezas lúdicas o de alta energía, nunca en texto institucional. Conserva el volumen: si estira en Y, encoge en X. | 0% serio · 4–8% cálido · 18–40% lúdico (tabla de `fluidez.md`) |
| **Anticipación** | Antes de un movimiento grande, un contra-movimiento pequeño: retroceso de 3–6% o 8–20 px en dirección opuesta. | 80–200 ms antes del golpe |
| **Puesta en escena (staging)** | Un protagonista por plano (`principios.md`). Antes de animar, el frame quieto debe leerse en 1 s. | 1 foco, ≤2 apoyos |
| **Pose a pose + directo** | Las poses clave (llegada, golpe, salida) se fijan en el plan con `at`; el intermedio lo genera el resorte. | Llaves en los beats del audio |
| **Follow-through y overlapping action** | Las partes no se detienen a la vez: el contenedor llega, su contenido llega 60–120 ms después y asienta con un rebote menor. Sombras, glows y partículas arrastran detrás del objeto. | Desfase 60–120 ms entre capas |
| **Slow in / slow out** | Nunca lineal. Entradas con ease-out o resorte; desplazamientos largos con ease-in-out; salidas con ease-in (acelera al irse). | Ver §3 |
| **Arcos** | Lo que viaja más de ~200 px lo hace en arco (curva cuadrática, flecha del arco 6–12% de la distancia), no en línea recta. Solo la UI precisa (cursor, tabla) viaja recta. | Flecha 8% |
| **Acción secundaria** | Un segundo movimiento pequeño que apoya al principal: el glow pulsa cuando cae la cifra, la tarjeta se inclina 1–2° al aterrizar. Nunca compite con el foco. | Amplitud ≤25% del principal |
| **Timing** | El peso se comunica con frames: objetos pesados (logo, cifra gigante) tardan más y rebotan menos; ligeros (chips, partículas) rápidos y vivos. | Pesado 600–900 ms · ligero 250–400 ms |
| **Exageración** | Solo en el momento firma de la pieza (uno). En el resto, contención. | Overshoot ≤8%, 10% en el foco |
| **Dibujo sólido** | Volumen y perspectiva consistentes: si algo rota en 3D, su sombra y su perspectiva acompañan. Nada de rotaciones planas que delatan el 2D. | — |
| **Atractivo (appeal)** | Formas simples, siluetas claras, espaciado generoso. Si un frame congelado no se podría publicar como póster, falta appeal. | Check de frame 0 / medio / final |

## 2. Motion blur — obligatorio en la entrega final

El ojo lee el movimiento sin desenfoque como "renderizado por computador". El
cine graba con obturador de 180° (expone medio frame): ese es el look.

- **Motor de planes**: `render_plan.py --blur 5` (5 sub-frames por frame,
  obturador 0.5 = 180°). Borradores con `--blur 1`; la entrega, con 4–6.
- **Composición propia en PIL**: componer el frame en `n` instantes repartidos
  en `t ± obturador/(2·fps)` y promediar en float (patrón de
  `frame_con_blur` en `render_plan.py`). Coste ≈ n veces el render.
- **Remotion / HyperFrames**: `@remotion/motion-blur` (`CameraMotionBlur`,
  samples 5–10, shutterAngle 180) o render a 120 fps y luego
  `ffmpeg -vf "tmix=frames=4:weights='1 1 1 1',fps=30"`.
- **Video real**: nunca se añade blur a footage ya grabado (ya lo trae).
- Excepciones deliberadas: texto que debe leerse *mientras* se mueve
  rápido (subtítulos karaoke) va sin blur; glitches van sin blur (su
  estética es el corte duro).

## 3. Curvas de easing (biblioteca canónica)

| Uso | Curva | cubic-bezier |
|---|---|---|
| Aparición de UI, texto de apoyo | easeOutCubic | (0.33, 1, 0.68, 1) |
| Elemento focal que "aterriza" | easeOutBack suave / resorte k=120, d=13 | (0.34, 1.36, 0.64, 1) |
| Desplazamiento largo, cámara | easeInOutCubic | (0.65, 0, 0.35, 1) |
| Salida | easeInCubic | (0.32, 0, 0.67, 0) |
| Golpe de alta energía | easeOutExpo | (0.16, 1, 0.3, 1) |
| Premium lento (lujo, institucional) | easeInOutSine extendido | (0.37, 0, 0.63, 1) |

Regla: **una familia de curvas por pieza**. Mezclar expo, back y sine en la
misma pieza se percibe como incoherente aunque nadie sepa decir por qué.

## 4. Coreografía (stagger) y overlapping

- **Stagger** de listas y grillas: 40–90 ms entre elementos. Menos parece
  simultáneo; más, lento. Orden de lectura (izq→der, arriba→abajo) o desde
  el foco hacia afuera.
- **Titulares**: palabra por palabra anclada a la palabra que se oye; la
  palabra de acento llega con más energía (escala 1.16→1 con resorte) y las
  de apoyo con elevación suave.
- **Overlapping**: contenedor → contenido (+80 ms) → detalle (+160 ms). La
  salida va al revés y más rápida (60–70% del tiempo de entrada).
- **Nunca** keyframes idénticos en toda una frase o lista: varía timing o
  amplitud ±10–15% para que respire como algo vivo.

## 5. Cámara virtual

El movimiento de cámara convierte un layout plano en un espacio.

- **Push-in lento** (escala 1.00→1.04–1.08 durante la escena) en planos de
  contemplación: añade tensión sin que se note.
- **Paralaje 2.5D**: separar en 3–4 capas (fondo, medio, foco, partículas
  delante). Al mover la cámara, cada capa se desplaza en proporción a su
  profundidad (fondo 0.2×, medio 0.5×, foco 1×, primer plano 1.4×).
- **Rack focus**: desenfocar el fondo (gaussiano 6–14 px) cuando entra el
  foco; devolverlo al salir.
- **Camera shake**: solo en impactos, 2–4 frames, amplitud 4–10 px, decae
  exponencial. Nunca continuo.
- **Un movimiento por plano** (`direccion.md`): push-in *o* paneo *o*
  paralaje, no los tres.

## 6. Tipografía en movimiento

- **Tracking animado**: kickers que entran con letterspacing amplio (+20%)
  y se cierran a su valor final: elegancia sin coste.
- **Revelado por máscara**: el texto sube desde detrás de una línea
  invisible (clip), no aparece por fade. Es la firma de los títulos de cine.
- **Pesos variables**: con fuentes variables (las empaquetadas en
  `assets/fonts/` lo son) el peso puede animar 400→800 en la palabra clave.
- **Kerning y ortografía**: revisar pares problemáticos en tamaños
  gigantes (AV, To, Te, "10") y tildes/¿¡ siempre presentes.
- **Lectura**: cada línea en pantalla ≥ (palabras × 0.3 s) + 0.5 s.

## 7. Transiciones con intención

- El idioma lo fija el pack o el tono (`brand-packs.md`); dentro de él, la
  mejor transición es la que **conecta contenido**: match cut por forma
  (círculo → botón → logo), por color, por movimiento (el objeto sale por la
  derecha y el siguiente entra con la misma velocidad desde la izquierda).
- Transiciones "de efecto" (mancha, glitch, zoom-blur) como máximo 1–2 por
  pieza, y motivadas por la historia. `render_plan.py` aplica el
  presupuesto automáticamente.
- Sonido: toda transición visible lleva su evento sonoro (whoosh, golpe o
  silencio deliberado; ver `sfx.md`).

## 8. Acabado táctil

El acabado digital perfectamente limpio no es lo que se premia
(`dramaturgia.md`):
- Grano fino animado (alfa 6–10/255, cambia cada frame).
- Viñeta suave; gradientes con dither (sin bandas).
- Glow/bloom solo en el acento y en el momento firma.
- Aberración cromática / glitch: un solo golpe dramático, nunca ambiente.

## 9. Protocolo de revisión de animación

1. Mirar el render completo a velocidad real con audio.
2. Mirarlo a 0.5× (`ffplay -vf setpts=2*PTS`): todo salto, pop, aparición
   sin easing o elemento que se detiene en seco es un defecto.
3. Contact sheet (`scripts/auto_qa.py --sheet`) + frames de cada golpe a
   resolución completa: el frame en pleno movimiento debe mostrar motion
   blur y el frame asentado, nitidez total.
4. Puntuar con `rubrica-premios.md`. Si algún eje queda por debajo de 4, se
   corrige y se vuelve a renderizar antes de entregar.
