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

El motor tiene **cuatro** curvas y ninguna más. Todo lo que se mueve pasa por
una de estas o por un resorte:

| Uso en el motor | Curva | cubic-bezier equivalente |
|---|---|---|
| Entrada de un elemento (`ease_out`) | easeOutCubic | (0.33, 1, 0.68, 1) |
| Transición entre escenas (`smoothstep`) | easeInOutSine | (0.37, 0, 0.63, 1) |
| Desplazamiento largo, cámara (`ease_in_out`) | easeInOutCubic | (0.65, 0, 0.35, 1) |
| El valor que "aterriza" | **resorte**, rol `pop` (ver §3b) | (0.34, 1.36, 0.64, 1) |

Regla: **una familia de curvas por pieza**. Mezclar expo, back y sine en la
misma pieza se percibe como incoherente aunque nadie sepa decir por qué.

Si necesitas una curva que no está aquí, el problema no es la curva: es que
falta un **rol de movimiento** (§3b). Una curva nueva es siempre un gesto
nuevo, y un gesto nuevo se nombra.

## 3b. Los seis gestos de la casa (`MOVIMIENTO`)

El resorte es la unidad de gesto del motor y tiene su propia física: se pasa
del objetivo (overshoot) y tarda un tiempo en calmarse. El ojo no ve los
números — ve que un plano **rebota** y el siguiente **se asienta** — y esa
diferencia se lee como "cada escena la hizo alguien distinto".

La auditoría del catálogo encontró **23 resortes distintos**: el overshoot
iba del 3 % al 20 % y la calma del 0.17 s al 0.40 s. Ahora hay seis gestos
con nombre, y el rol lo elige **lo que el elemento es**:

| Rol | Resorte | Overshoot | Calma | Para qué |
|---|---|---|---|---|
| `titular` | (150, 15) | 8.8 % | 0.23 s | la frase que abre la pieza |
| `bloque` | (120, 15) | 5.2 % | 0.29 s | una tarjeta, una ficha, un precio |
| `elemento` | (110, 14) | 6.0 % | 0.29 s | un chip, un dato, un botón, una burbuja |
| `suave` | (130, 16) | 4.5 % | 0.28 s | entra sin robar atención (pies, subtítulos) |
| `pop` | (150, 13) | 14.0 % | 0.20 s | el dato que **quiere** que lo mires (un landing) |
| `lento` | (70, 12) | 3.9 % | 0.40 s | el ritmo de los libros: abrir y cerrar sin prisa |

En el motor: `entra(t, instante, "rol")`. **No se escriben stiffness ni
amortiguación a mano**: un resorte fuera del catálogo es un gesto sin
nombre, y el guard de `scripts/_tests/test_movimiento.py` lo hace fallar.

**La regla que da forma al conjunto**: lo que rebota fuerte (`pop`) es lo
que quiere que lo mires; todo lo demás se asienta con calma. Un elemento
que aparece y desaparece sin más gesto es ruido, no información.

### Lo que se dibuja va por tiempo, no por resorte

Un trazo que se dibuja (el donut, la elipse del `callout`, una barra que se
rellena) NO puede llevar su avance atado al resorte: el resorte acelera y
se pasa de golpe, y el borde del trazo cambia de un frame al siguiente. Eso
se lee como un **pop** (y el detector de `medir_animacion.py` lo marca como
tal: el `pie` se llevaba 4 pops por girar 35° por frame).

El avance de un trazo va por **tiempo**: 360° en 0,9 s (la elipse), la porción
del donut en 0,55 s. El resorte queda para lo que *entra* (una tarjeta, un
titular), no para lo que *se dibuja*.

### Un bloque oscuro se compone en capa propia

`ImageDraw` **reemplaza** el pixel, no lo mezcla: pintar un rectángulo negro
con alfa bajo encima de una imagen **la borra** y deja un agujero. Para que
una placa (el fondo oscuro de un texto sobre una captura) pueda entrar con
su propio fundido, se compone en una capa aparte con `alpha_composite`.

Las dos reglas nacieron de medir el catálogo entero: `pie` pasó de 64,0 con
4 pops a 99,7 con 0, y `callout` de 68,0 con 2 pops y 2 tirones a 100,0 sin
ninguno.

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

## 10. La excepción: cuando el personaje está dibujado

Todo este documento gobierna el **motion graphics**: elementos que entran, se
asientan y salen. Un **personaje dibujado** es otro oficio: ahí los
intermedios no los genera el resorte sino otro dibujo, y el error típico es
justo el del resorte: extremidades que interpolan y leen como marioneta.

Cuando la pieza esté dibujada a mano, el método (poses enteras, hoja de
exposición, contactos, marcas) y los motores van en `references/dibujado.md`.
La regla que cambia aquí es una sola: **no se aplica el mismo resorte a todo**
—un motor gira a velocidad constante y una taza rígida no squash en cada
frenada— y **el contacto se conserva hasta su liberación planesada**.

---

→ Canónico: `references/animacion.md` · Dominio: movimiento · Vecinos: `references/fluidez.md`, `references/reglas-tecnicas.md`, `references/intencion-escena.md`
