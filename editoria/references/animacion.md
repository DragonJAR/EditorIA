# Animación — el oficio que separa un video de premio de "un video con IA"

`fluidez.md` dice *que* todo debe moverse con resortes. Este documento dice
*cómo* se anima para que el movimiento tenga peso, intención y acabado de
estudio. Se aplica a todos los motores (plan, composición libre, Remotion,
HyperFrames). Ante conflicto: el brand pack fija identidad, `fluidez.md` fija
el motor, y este documento fija el oficio.

## 0. Qué técnica cuándo — el selector de animación

Antes del oficio, la elección: cada técnica entra por un sitio distinto y
pide una cosa distinta. Si la que la pieza necesita no está instalada, se
dice en la primera respuesta con su comando (`references/capacidades.md`);
nunca se sustituye en silencio por otra que "se parece".

| La pieza pide | Técnica | Cómo se pide | Dónde vive |
|---|---|---|---|
| Qué poner en cada parte (escena, overlay con cara, gesto de interfaz) | **Catálogo único** de elección | `repertorio.py sugerir` (--intenciones / --pedido) → `resolver --id`; el motor es metadato de la opción, no un menú A/B | `scripts/repertorio.py` · `references/intencion-escena.md` |
| Escenas con texto, datos, cifras, tarjetas (opción `motor=escena`) | Motor de planes | Un `plan.json`: escena + `at` por elemento + gesto con nombre (§3b) | `references/escenas.md` → `references/plan-video.md` |
| Animar un elemento suelto (logo, titular, cifra) dentro de una pieza de planes | El mismo motor: una escena o una pasada acotada sobre la pieza | La pasada nombra solo lo que cambia; el resto no se toca | `references/pasadas.md` |
| Movimiento pictórico: acuarela, pincel, doodle, lyric video | Canvas (p5.js): cada frame es función pura de `t` | Un sketch con `renderAt(t)` determinista; el trazo se autora como dato, no como grabación | `references/canvas.md` |
| Trazo a mano: pizarra, anotación dibujada, doodle cinético | Trazo suavizado horneado a overlay con alfa | Un JSON de puntos/trazos; el suavizado va antes de pintar, el PNG entra por montaje | `references/hand-draw.md` |
| Animación programática compleja: estado, datos que cambian, componentes reutilizables | Remotion | Componentes React con la misma disciplina de resortes y blur de este documento | `references/remotion.md` |
| Pieza HTML determinista que se re-renderiza con datos nuevos | HyperFrames | HTML+CSS con seek determinista; mismo HTML, datos nuevos | `references/hyperframes.md` |
| Un objeto, producto o escena 3D como material | 3D como capa con alfa sobre el motor que componga la pieza | El objeto entra renderizado con alfa; el motor de la pieza no cambia | `references/3d.md` |
| Animar sobre video real (rótulos, gráficas, PiP que siguen a la acción) | Híbrido: el footage manda y la animación complementa | La capa animada se ancla a palabras o instantes del footage, no a segundos sueltos | `references/modos-produccion.md` |
| Un diagrama que se dibuja a sí mismo | HTML+SVG con la marca de la pieza | Un solo fichero autocontenido; el trazo se anima por longitud de path | `references/diagramas.md` |
| Una pieza que sea UN recorrido (una idea, muchas funciones) y no una tanda de planos | El camino: una línea de luz que corre, la cámara vuela con la cabeza y cada estación se enciende al paso | La escena `camino` del catálogo: las estaciones van en `estaciones` y el trazo lo dibuja UNA función | `references/escenas.md` → `references/plan-video.md` |
| Sensación de producto / sitio / app (cascada, morph, máscara, parallax, zoom) | Misma elección: opción `motor=gesto` del catálogo único | `repertorio.py sugerir --pedido "…"`; una técnica dominante; el detalle de números vive aparte | Detalle interno: `references/motion-ui.md` · `scripts/data/motion_ui.json` |
| Overlays que siguen la cara (orbit, spotlight, glass, LED, grid…) | Misma elección: opción `motor=efecto` (o `nativo`) | `repertorio.py sugerir --pedido "…"` → `resolver` → `efectos_talking_head.py receta` si hace falta CVE en `/tmp` | Detalle interno: `references/efectos-talking-head.md` · JSON de fx |
| Captions / subtítulos tipográficos (karaoke, slam, matte detrás de cara…) | Misma elección: opción `motor=caption` | `repertorio.py sugerir --pedido "…"` → `resolver` → `caption.py` o `captions_identidades.py receta` | Flujo: `flujo-talking-head.md` · detalle: `captions-identidades.md` |

Regla de cierre de la elección: la técnica se verifica como el resto de la
pieza — preview de instantes antes de pagar el render, y la puerta al final
(`references/qa-entrega.md`). Lo que se mueve se mide
(`scripts/medir_animacion.py`): un movimiento que no se puede medir es un
movimiento que no se puede corregir. Mide también lo que la pieza NO hace:
`quieto` (el cuadro congelado, medido sin el grano: por bloques, con un
umbral que solo sube si el grano medido de la pieza lo exige) y `ocupacion`
(cuánto de la zona segura cubre el contenido: la banda chica en un lienzo
enorme tiene número). La puerta falla un congelado de más de 1 s que no sea
el cierre, o una pieza que ocupa menos de 0.20 de la zona segura.

### 0b. Catálogo único: cuándo, cómo pedir, cómo adaptar

Una sola superficie. El agente no elige «repertorio vs talking-head vs Zajno».

| Paso | Dónde | Qué hace el agente |
|---|---|---|
| Brief → opción | `repertorio.py sugerir` (`--intenciones` y/o `--pedido`) | Una opción por intención (o top-N del pedido); rota y evita la pieza anterior |
| Opción → motor | `repertorio.py resolver --id …` | Metadato interno: `escena` / `efecto` / `gesto` / `nativo` + cómo producir |
| Pedido vago → nombre | `references/intencion-escena.md` §2 | El cliente habla; el índice nombra la opción de plan |
| Params (si `motor=escena`) | `references/escenas.md` + `scripts/escenas_muestra.json` | Schema y muestra; no hay una segunda lista |
| Adaptar copy/tiempos/look | `intencion-escena.md` §2c | Parametriza; gesto UI = opción `gesto` o rol `MOVIMIENTO`; look = pack |
| Cobertura / no olvidar | `repertorio.py cobertura` + `auditar_plan.py` | Lo no usado se declara `no_aplica` |
| Verificar | preview del motor elegido · `medir_animacion.py` · puerta | Preview barato antes del render caro |

Globales del plan (`cabecera`, `grano`, `camara`) no son tipos de `SCENES`.
Si la pieza pide otro oficio (trazo a mano, HTML determinista, React, 3D),
vuelve a la tabla §0 — no estires una escena plana hasta que parezca otra
técnica, y no abras un «segundo catálogo».

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
| **Acción secundaria** | Un segundo movimiento pequeño que apoya al principal: el glow pulsa cuando cae la cifra, la tarjeta se inclina 1–2° al aterrizar. Nunca compite con el foco. Todo glow se pinta con `resplandor` (`render_plan.py`): lienzo acolchado 3σ, sin el cuadrado de un blur recortado. | Amplitud ≤25% del principal |
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
que quiere que lo mires; todo lo demás se asienta con calma. El gesto vale
también para lo que se REVELA: `titular` y `rotulo` entran por máscara
(`_revela_clip`, §6) con el resorte de su rol, no con una curva propia; una
lista entra en cascada a paso `STAGGER` (`escalonado`, §4). Un elemento
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
  el foco hacia afuera. En el motor es UNA cifra, `STAGGER` (0.06 s), y un
  helper, `escalonado(at, "item", i, base)`: el `at` explícito del plan
  manda, y si el plan solo fija `item0` el resto lo sigue a paso `STAGGER`.
  Los beats que se LEEN (hitos de `timeline`, pasos, notificaciones) no son
  cascada: llevan su propio tiempo con nombre.
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
  contemplación: añade tensión sin que se note. En el motor es `EMPUJE`
  (6 %) a lo largo de toda la escena con `ease_in_out` (antes 1 %/s con
  tope 5 %: en una escena de 3 s, un 3 % que no se veía). El push-in
  TERMINA donde el contenido llena la zona segura: si no hay sitio, la toma
  arranca un poco más abierta y llega a su encaje, así que nunca se sale.
  Exentas: `CAMARA_PROPIA`, overlays y `respira: false`. Las que se leen
  quietas (`QUIETAS`: el rótulo inferior) no empujan pero tampoco se
  congelan: llevan la **vida en reposo** (`vida`), la misma flotación de la
  cámara (`FLOTA_CAM` = 6 px a `FLOTA_HZ` = 0.3 Hz), también como overlay.
  Medido sobre fondo quieto: un hold de 3 s pasó de `quieto_max` 3.27 s a
  0.47 s. `final`, `kenburns` y `demo` ya se mueven solas y no la llevan.
- **Paralaje 2.5D**: separar en 3–4 capas (fondo, medio, foco, partículas
  delante). Al mover la cámara, cada capa se desplaza en proporción a su
  profundidad (fondo 0.2×, medio 0.5×, foco 1×, primer plano 1.4×).
- **Rack focus**: desenfocar el fondo (gaussiano 6–14 px) cuando entra el
  foco; devolverlo al salir.
- **Camera shake**: solo en impactos, 2–4 frames, amplitud 4–10 px, decae
  exponencial. Nunca continuo.
- **Un movimiento por plano** (`direccion.md`): push-in *o* paneo *o*
  paralaje, no los tres.
- **El lienzo se llena**: la medición de `escala_segura` también hace
  crecer una escena chica (tope `LLENA_MAX` = 1.35, dejando sitio al
  push-in) y la centra en la zona segura (`llenado`). No crecen las
  escenas a sangre, los overlays, las de zona declarada ni las de
  trayectoria global de cámara. El crecimiento amplía el raster: la letra
  legible se gana subiendo la escala de la escena, no solo creciendo. Red,
  llenado y cámara se aplican en UNA transformación (`encuadrar`). Medido
  sobre la muestra: casi todo el catálogo ya llega al ancho seguro, así que
  el llenado solo hace crecer las escenas angostas (stats ×1.10); las de
  solo tipo (apertura, cartel) siguen siendo una banda (ocupación 0.17–0.18
  frente a 0.50–0.86 de las de datos) y `medir_animacion` las señala.
- **Composición vertical**: en la misma transformación, una escena que es
  una banda (alto ≤ `BANDA_MAX` = 0.5 de la zona segura), crezca o no, lleva
  el centro de su bbox medido al **centro óptico** de la zona
  (`CENTRO_OPTICO` = 0.46 de su altura, un poco sobre el geométrico), sin
  salirse. Es función pura del bbox: el mismo desplazamiento en toda la
  escena. No se mueven las que tienen sitio propio (`SITIO_PROPIO`: a
  sangre, overlays y `ANCLADAS` abajo por su rol —constancia, cadena,
  cartel—) ni las de `y` o `zona` declaradas; una escena más alta que media
  zona ya la compone y tampoco se toca. El centrado deja sitio al push-in
  y a la flotación (una escena crecida no queda pegada arriba) y la holgura
  del push-in se mide sobre el bbox ya colocado y descuenta `FLOTA_CAM`. Lo que NO arregla: la
  ocupación de una escena de solo tipo limitada por el ancho (apertura) no
  sube al centrarla; eso es copy o escala de la escena.
- **Vuelo continuo (una pieza, un solo recorrido)**: la cámara no salta de
  plano en plano: viaja. En 2D eso es un **dolly con paneo**: el mundo se
  escala y se desliza mientras la cámara se queda con el punto de interés
  (la cabeza del trazo). Es lo que hace que una pieza se lea como una sola
  idea y no como una tanda de planos, y es lo que mantiene los cuadros
  VIVOS: un trazo que se arrastra despacio cambia tan pocos píxeles que el
  medidor lo lee como cuadro congelado (medido: 37 % de la pieza "muerta"
  con la cámara quieta; 0 % con la cámara volando). La escena `camino` lo
  hace de serie.
- **Un solo trazo para todo**: cuando un elemento hace de muchas cosas
  (una línea que revela el logotipo, llena la barra, se enrosca, baja bajo
  el lema...), se dibuja con UNA función compartida (`trazado`) y cada uso
  cambia solo sus puntos. Un trazo dibujado de cinco maneras son cinco
  trazos que se desincronizan.

## 6. Tipografía en movimiento

- **Tracking animado**: kickers que entran con letterspacing amplio (+20%)
  y se cierran a su valor final: elegancia sin coste.
- **Revelado por máscara**: el texto sube desde detrás de una línea
  invisible (clip), no aparece por fade. Es la firma de los títulos de cine.
  En el motor lo hace UN helper, `_revela_clip`, con el resorte del rol que
  entra (sin curva nueva): lo usan `titular` (palabra a palabra) y `rotulo`
  (línea a línea). La línea de clip es la base de la línea (base +
  descendente) y el fundido acompaña al resorte (alfa = k): con un fundido
  corto (k·3) la tinta que el clip destapa en un frame de un titular de
  124 px era un pop según la altura de la escena (3 de 5 alturas medidas;
  con alfa = k, 0 de 11).
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
4. `scripts/medir_animacion.py --video final.mp4 --plan plan.json`: además
   de pops y tirones, `quieto` (racha congelada sin grano, en s) y
   `ocupacion` por escena. Un congelado > 1 s fuera del cierre es un fondo
   o una cámara que se pararon; una escena bajo 0.20 es una banda chica.
   En un video no hay zonas de cifra del motor: el dígito nuevo de un
   contador ("8" → "11") pegado a las cifras que cuentan se infiere
   (`_digito_nuevo`) y no es pop; un objeto que aparece lejos, sí.
5. Puntuar con `rubrica-premios.md`. Si algún eje queda por debajo de 4, se
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

→ Canónico: `references/animacion.md` · Dominio: movimiento · Vecinos: `references/fluidez.md`, `references/reglas-tecnicas.md`, `references/intencion-escena.md`, `references/motion-ui.md`, `references/efectos-talking-head.md`
