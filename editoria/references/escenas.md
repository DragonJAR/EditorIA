# Catálogo de escenas (45 tipos del plan)

Cada escena es una función `(ctx, e, t)` donde `e` es su bloque del plan y `t`
el tiempo absoluto del video (ver `scripts/render_plan.py`, `SCENES`).
Todas comparten: fondo vivo, salida cruzada desde el corte (0,32 s, `SOLAPE`), transición `mancha`
opcional al entrar. Tiempos `at` en segundos absolutos del video.

## 1. `apertura` — gancho
Fondo que nace de un punto, crece y se encoge con el cambio de titular, más
objetos flotantes + titular cinético en dos fases (`texto1` → `texto2` en
`at.cambio`). Palabras con tiempos `at.p1/p2`.
- **El fondo es la MARCA**: si el pack trae isotipo, se dibuja su silueta en el
  color de la marca (con su resplandor difuso); sin isotipo, cae al blob
  orgánico de siempre. El gesto no depende de que la marca tenga isotipo.
- Params: `texto1[]`, `texto2[]`, `at{cambio, p1[], p2[]}`

## 2. `canales` — "todos tus canales, un lugar"
Marca grande al centro que sube y se encoge; tarjetas de canal que entran volando
con resorte y se juntan en una bandeja (filas que crecen). Rótulo al final.
- Params: `marca`, `rotulo`, `canales[{canal, nombre, texto, at, icono?}]`, `at{marca, junta, rotulo}`
- `icono`: letra(s) del círculo (default: inicial del `nombre`; úsalo cuando dos
  canales empiezan igual, p. ej. WhatsApp/Web).

## 3. `medianoche` — teléfono 3D
Teléfono que rota en 3D al entrar (perspectiva, rotateY de -70° a -12°). Pantalla
con fecha/hora y notificaciones que caen con resorte y empujan a las anteriores.
- Params: `rotulo`, `hora`, `fecha`, `notificaciones[{canal, titulo, texto, at}]`

## 4. `chat` — conversación con IA
Burbujas de chat (cliente izq, IA der) que aparecen con resorte, un mensaje a
la vez; la IA "escribe" (tres puntos que laten) antes de responder. La última
burbuja de cada racha lleva cola. Hilos largos hacen auto-scroll con resorte:
lo nuevo queda sobre la banda segura y lo viejo se desvanece bajo el rótulo.
Link de pago como tarjeta final.
- Params: `rotulo`, `mensajes[{de, texto, at?, pausa?, escribe?}]`, `link{titulo, monto, at}`
- Sin `at`, el tiempo se deriva del mensaje anterior: `pausa` de lectura
  (0.6 s) + `escribe` (0.7 s en la IA). Ritmo: respuestas ágiles 0.3–0.5 s de
  pausa; antes del remate, `escribe` 1.5–2.5 s (el suspenso vende el remate).

## 5. `leads` — tabla priorizada
Filas de tabla que entran en cascada; resaltado por temperatura (Caliente/Tibio/Frío =
`ACENTO`/`AVISO`/`GRIS`, `references/paleta.md`) sincronizado con `at`. Puntaje como barra.
- Params: `rotulo`, `total`, `filas[{nombre, canal, etapa, puntaje, temp}]`, `at{rotulo, Caliente, Tibio, Frío}`

## 6. `handoff` — traspaso con contexto
Tarjeta de persona + lista de contexto (clave/valor) que se revela línea por línea.
Nota de aviso ("Te avisa al instante").
- Params: `rotulo`, `cliente`, `iniciales`, `temp`, `nota`, `contexto[{k, v}]`, `at{rotulo, persona, contexto}`

## 7. `pago` — comprobante
Comprobante que sube con resorte; cursor que se mueve y "pulsa" (escala + onda).
Monto grande.
- Params: `rotulo`, `cliente`, `monto`, `detalle`, `boton?` ("Pagar"), `hecho?`
  ("Pagado"), `at{rotulo, comprobante, cursor, toque}`. El toque CAMBIA el
  botón a su estado `hecho` (fundido cruzado de 0.25 s): un clic sin
  consecuencia no vende.

## 8. `listo` — check con estallido
"¡Listo!" gigante con estallido de partículas en anillo + onda expansiva.
- Params: `texto`, `at{listo}`

## 9. `pildoras` — columnas + frase
Columnas de píldoras que caen/rotan al fondo; frase palabra por palabra al frente.
- Params: `texto[]`, `at{palabras[]}`

## 10. `hoy` — panel del día
Contador que sube + tarjetas de tareas en grilla que entran en cascada.
- Params: `rotulo`, `fecha`, `cuenta`, `tarjetas[{titulo, detalle, n, boton, alerta}]`, `at{rotulo, cuenta}`

## 11. `recupera` — pago recuperado
Cursor que arrastra una barra de progreso; al completarse, tarjeta "pagado" en
el token `EXITO` (verde de la paleta, `references/paleta.md`).
- Params: `rotulo`, `resumen`, `cliente`, `hace` (ej. "hace 2 horas"),
  `monto`, `hecho?` ("PAGADO", en el idioma de la pieza), `at{rotulo, cursor, recupera, pagado}`

## 12. `remate` — frases + cifra gigante
Frases cinéticas palabra por palabra + cifra gigante que entra con slam y glow.
- Params: `lineas[]`, `gigante`, `at{palabras[], gigante}`

## 13. `final` — cierre de marca
Logo + lema + botón. Entrada elegante con resorte suave, hold, salida fundida.
- Params: `marca`, `lema`, `boton`, `at{lema, boton}`

## Transición `mancha`
Barrido orgánico: un blob con borde ondulado que crece desde un punto
(`transicionX/Y`) con un agujero central, cubre la escena anterior y revela la
nueva. Implementación: polígono de 72 puntos con radio modulado por senos.

## Transición `iris`
Apertura en círculo desde un punto: la escena nueva se revela como un iris
que crece desde (`transicionX/Y`) — el corte firma del video con presentador
(abre desde la cara). Comparte el presupuesto de la `mancha`: las dos piden
atención, y un plan no llena de transiciones. Implementación: máscara de
círculo con radio en `ease_out`.

## Transición `dissolve`
Fundido cruzado de 0.40 s: la escena nueva aparece encima de la anterior con
alfa creciente (`smoothstep`). Es el corte más neutro del catálogo: no pide
atención como la `mancha` ni deja formas orgánicas en el encuadre. Se declara
en la escena entrante: `"transicion": "dissolve"`.

## Catálogo unificado de escenas (45 tipos del plan)

El catálogo integra las 13 escenas originales más 32 escenas de
datos/UI/tipo/cinemática/oferta/social/interactivas validadas externamente (ver
`references/scene-patterns-from-internet.md`). Cada escena nueva se compone
con las primitivas DRY de `render_plan.py` (lista al final de este archivo).
Cada tipo tiene una muestra realista en `scripts/escenas_muestra.json`: el
validador la renderiza en cada corrida y exige que quepa en la zona segura
9:16 sin encogerse; `scripts/galeria.py` la renderiza de verdad y le pasa
`auto_qa`. Toda escena nueva necesita su muestra.

**Componer en cualquier formato (9:16 y 16:9)** — primitivas de layout:
- `caja_segura()`: el rectángulo útil de la plataforma; el contenido se
  compone DENTRO (escala_segura es la red, no el diseño).
- `unidad()`: lado corto del cuadro; los tamaños de letra van en ella, nunca
  en `W` (W*0.055 son 59 px en 9:16 y 105 px en 16:9).
- `pila(alturas, y0, y1)`: apila bloques medidos y, si no caben, encoge todo
  junto en vez de dejar que se pisen (oferta, cita).
- `fuente_que_cabe()`: encoge cifras y etiquetas a su caja; el tamaño lo
  fija el valor FINAL (no salta mientras cuenta).
- `columnas_grilla()` / `cuadricula()`: 1 columna en 9:16 hasta 3 tarjetas.
- `pie_fuente()`: la fuente del dato en el borde inferior de la zona segura.
- **Copy largo**: todo texto encoge para caber en su caja (`fuente_que_cabe`)
  y el rótulo, si ni a 30 px cabe, se parte en dos líneas equilibradas
  (`partir_segs`, conserva el énfasis). El validador renderiza cada escena con
  cada texto ×2 en los dos formatos: sin solapes y sin que la red encoja bajo
  x0.90. Las temperaturas de `leads` aceptan sinónimos (caliente/hot,
  tibio/warm, frío/cold) o `color` explícito.
- `vy(f)` / `vk()`: posición y desplazamiento de diseño (fracción de H)
  re-mapeados a la caja segura actual; con banda de subtítulos la escena sube
  y se comprime en vez de que la red la encoja entera. Sin banda: H*f.
- `bajo_rotulo(y)`: primer y libre bajo un rótulo; lo que va debajo se mide
  desde ahí, nunca con una fracción fija de H (en 16:9 H*0.04 son 43 px y el
  rótulo mide ~55: «24 leads hoy» y la ventana de `demo` lo pisaban).
- `check()`: check dibujado (el glifo ✓ no existe en todas las fuentes).
- `COLUMNA` (chat, leads, handoff): en 16:9 se componen a 1080 px de ancho,
  centradas — una conversación de 1920 px no se lee.
- `A_SANGRE` (kenburns, confeti): el fondo cubre el cuadro a propósito; no
  se encogen y su texto va en la zona segura.
- Respiración de cámara común en `componer` (push-in 1 %/s hasta 5 % +
  flotación de 6 px): ningún hold queda congelado. Exentas las de
  `CAMARA_PROPIA`; `QUIETAS` (rótulo inferior) se queda quieta mientras se
  lee; `"respira": false` la apaga por escena.
**Marca-blanca**: el color viene del brand pack (`brand/*.json`); sin pack,
se usa el `ACENTO` neutro del renderer.

### 14-21. Catálogo extendido (DataAnimations + UI + Theme)

Fuentes: `lifeprompt-team/remotion-scenes` (DataAnimations, Theme, ListAnimations)
y `ali-abassi/remotion-templates` (Charts & Data, Stat Counter, Quote Card).

**`bars`** — Barras verticales de comparación. `barras[{etiqueta, valor, max, acento?}]`,
`at{rotulo, bar0..n, fuente}`. Toda cifra lleva su `fuente` en pantalla.
Fuente: `DataBarChart` de `lifeprompt-team/remotion-scenes` (MIT).

**`gauge`** — Indicador circular con cuenta animada al centro. Dos formas de
la misma idea: el arco de 270° (sin `forma`) y el **anillo** de marcas
radiales (`forma: "anillo"`). `valor`, `max`, `etiqueta`,
`at{rotulo, gauge, etiqueta}`. Fuente: `DataGauge` (MIT).

**`gauge` con `forma: "anillo"`** — El dial de marcas: un anillo completo de
`n` marcas finas que se llenan con el valor, con la cifra y el sufijo
(`sufijo: "/50"`) dentro y la etiqueta pequeña encima. Es lo que sirve para
una MAGNITUD leida de un vistazo (un panel de control, un velocimetro, el
estado de un aprendizaje). Params: `valor`, `max`, `ticks` (50), `sufijo`,
`etiqueta`, `color?`, `radio?`, `cy?`, `boton?`, y `frase?` (la frase
cinetica va ENCIMA, en la misma escena: el motor compone una escena a la vez
y si el copy fuera otra, en el corte el dial desaparecia).
`at{rotulo, gauge, etiqueta, boton}`.

**`frase`** — La frase cinematica: el copy entra PALABRA a PALABRA y el
bloque se recompone centrado (teleprompter). Es la escena del copy que se
LEE, no del titular que golpea.

El ESTADO DE CADA PALABRA (el sistema del reel de referencia):
  · la que AUN NO se ha alcanzado: se ve, pero en GRIS y mas CHICA (0,66);
  · la alcanzada: BLANCA, a su tamano, y se apaga con la edad;
  · la ACTIVA (la ultima alcanzada): blanca, con el SUBRAYADO ROJO debajo.
El resalte de una palabra: `*clave*` la pone en blanco y en negrita sobre
el gris; `~clave~` la mete en una CAJA ROJA (texto blanco) y `^clave^` en una
CAJA BLANCA (texto oscuro); `seleccion` le pone el recuadro azul. El mismo
markup (`segmentos_resalte` en `_comun`) lo leen también los titulares
cinéticos (`apertura`, `remate`, `pildoras`…): no hay un parser por escena.

Params: `frase`, `clave?`, `seleccion?`, `cps?` (palabras por segundo, 1.6),
`tam?`, `y?` (fraccion del alto donde queda la ultima palabra), `ventana?`
(5), `itálica?` (usa el display en italica si el pack la trae), `at{rotulo}`.

El copy se ENCOGE solo hasta el piso de letra (26 px de tinta) y, si aun
así no cabe, se ACORTA el copy: la letra no baja de 26 px (no se lee en un
telefono). El bloque NO se recompone al anadir palabra (medido: hacerlo
hacia que el bloque saltase de sitio y el medidor lo contara como 10 pops).

**`ranking`** — Ranking horizontal con barras proporcionales, #1 lleva acento.
`items[{etiqueta, valor, fecha?}]`, `at{rotulo, item0..n, fuente}`.
La columna de la etiqueta se mide con las etiquetas y la que no cabe se
**parte en dos líneas** a la misma letra (nunca "WhatsA…"); en 9:16 las filas
reparten el alto que sobra (`pila`, con tope `REPARTO_MAX`).
Fuente: `DataRanking` (MIT).

**`stats`** — Grid de stat cards (cifra grande + etiqueta). `cards[{valor, etiqueta, acento?}]`,
`at{rotulo, card0..n, fuente}`. Auto-layout cols según `n`.
Fuente: `DataStatsCards` (MIT).

**`timeline`** — Timeline horizontal con puntos pulsantes. `items[{etiqueta, fecha?}]`,
`at{rotulo, item0..n}`.
Fuente: `DataTimeline` (MIT).

**`quote`** — Testimonio / cita: la confianza antes que el movimiento. Las
líneas entran en orden de lectura (0.22 s entre líneas); la frase clave va
entre `*asteriscos*` (UNA por cita) y su marcador barre DESPUÉS de que su línea
asienta; `estrellas` se llenan al puntaje real (4.5 se ve 4.5) después de la
cita; el autor firma último y queda quieto. `texto` (verbatim, nunca
parafrasear), `autor`, `rol?`, `estrellas?`, `estrellas_max?` (5), `fuente?`,
`at{card, texto, enfasis, estrellas, autor, fuente}`.
Fuente: `ThemeAnimations › quote` (MIT) + testimonial-video (iart-ai, MIT).

**`versus`** — Comparación lado a lado. `izquierda{etiqueta, items[]}`,
`derecha{etiqueta, items[]}`, `at{rotulo, izq, der}`.
Fuente: `ListAnimations › versus` (MIT).

**`confetti`** — Celebración con confeti determinista (seed) + texto.
`texto`, `subtexto?`, `at{particulas, texto, subtexto, timestamp_seed?}`.
Fuente: `ParticleAnimations` (MIT).

### 22-24. Ronda 2 — Texto, Cinemática y Pasos (reactvideoeditor/remotion-templates, MIT)

**`typewriter`** — Texto que se escribe carácter a carácter a ritmo constante
(cada carácter nace con un fundido corto), en líneas dentro de la zona segura;
el cursor acompaña la escritura y parpadea al terminar. `texto`, `tam?`,
`cps?` (caracteres por segundo, 12.5), `at{rotulo, cursor, fuente}`. Útil para
hooks, intros y subtítulos animados. Fuente: `typewriter-subtitle.tsx` (MIT).

**`kenburns`** — Ken Burns sobre una imagen: zoom + paneo progresivo. Ideal para
galerías, openings sobre foto, documentales. `imagen` (ruta), `titulo`,
`subtitulo?`, `zoom_from?` (1.0), `zoom_to?` (1.15), `pan_x?`, `pan_y?`,
`dur_kb?` (4.0s), `at{rotulo, kenburns, texto, subtitulo}`.
Fuente: `ken-burns.tsx` (MIT).

**`pasos`** — Ruta de N pasos (1-5) en fila (16:9) o columna (9:16), con el
paso activo brillando y los demás atenuados. `titulo?`, `items[{titulo, texto, at}]`,
`at{rotulo, item0..n}`. Fuente: `progress-steps.tsx` (MIT).

### 25-28. Ronda 3 — Ofertas, demos, cuentas y rótulos (iart-ai/motion-skills, MIT)

**`countdown`** — Cuenta regresiva exacta: el número es función del tiempo
(nunca un contador acumulado) y marca `00` en el frame exacto
`at.inicio + segundos`. Dígitos de ancho fijo que ruedan tipo odómetro en el
último cuarto de su segundo. `segundos`, `formato?` (ss | mm:ss | hh:mm:ss;
default según duración), `rotulo?`, `final?` ("¡EN VIVO!"), `at{rotulo, inicio}`.
Para "empezamos en 5 min" de streams, lanzamientos y ofertas con plazo real.

**`oferta`** — UN descuento, un código, un CTA. `ahora` y el % se CALCULAN
de `antes` (dar `ahora` o `descuento`, no ambos): un precio incoherente rompe
el render antes de mentir en pantalla. Orden: el descuento aterriza (lo más
grande) → se tacha el precio viejo → DESPUÉS el nuevo cuenta hacia abajo →
código quieto (chip punteado, se lee y se captura) → vencimiento → CTA.
`antes`, `ahora|descuento`, `moneda` ($), `moneda_despues?`, `decimales?`,
`miles?`/`decimal?`, `mostrar?` (porcentaje | monto; default monto si el
ahorro es < 10), `codigo?`, `vence?` (solo una fecha REAL), `cta?`, `rotulo?`,
`at{rotulo, descuento, tachado, precio, codigo, vence, cta}`.

**`demo`** — Demo de producto desde capturas, sin grabar pantalla: ventana con
barra y URL; el cursor viaja con smoothstep al objetivo; la onda del clic y
el cambio de pantalla caen en el MISMO frame; zoom al foco (≤2×) con
spotlight y un beneficio por paso (frase nominal: "Exporta con un clic").
Cámara O cursor, nunca los dos a la vez. `captura` (idealmente a 2× para que
el zoom quede nítido), `url?`, `rotulo?`, `aspecto?`,
`pasos[{x, y (0..1 sobre la captura), at (clic), zoom?, texto?, captura?}]`,
`at{rotulo, ventana}`. Ritmo: 15 s = 3–4 pasos; 30 s = 5–7. Para acelerar,
quitar pasos, nunca acortar los holds de lectura.

**`rotulo_inferior`** — Lower third: nombre + rol sobre panel, anclado a la
izquierda (o `lado: der`) dentro del title-safe y elevado sobre la banda de
UI en 9:16. Entra barra → nombre → rol (máscara que barre, stagger 0.12 s),
queda quieto mientras se lee (3–5 s) y sale más rápido de lo que entró; el
primer y el último frame quedan vacíos. Un nombre largo se encoge, nunca se
sale del panel. `nombre`, `rol?`, `lado?`, `at{entra}`. Con `-o rotulo.mov`
(o `.webm`) sale como overlay con alfa para el NLE u OBS; con `--datos` se
renderiza uno por ponente (ver `plan-video.md`).

### 29-30. Ronda 4 — Hero SaaS, Bento 3D, Liquid Glass y CTAs con halo (supahero.io, scrolltide.co, glass.samasante.com, 3dicons.co, cta.gallery, navbar.gallery, footer.design)

**`hero`** — Apertura estilo Hero SaaS / lanzamiento de producto: píldora de
anuncio superior en cristal (`badge`, inspirada en `navbar.gallery` Announcement
y `supahero.io`), titular cinético con palabra clave en acento (`titulo`) y
subtítulo (`subtitulo`), tarjeta central Liquid Glass (`tarjeta_cristal`,
`glass.samasante.com`) con métrica destacada (`metrica`, `etiqueta_metrica`) y
botón CTA en píldora con anillo de halo pulsante (`boton_halo`, `cta.gallery` +
`scrolltide.co` Glow Ring Button). `badge?`, `titulo`, `subtitulo?`,
`metrica?`, `etiqueta_metrica?`, `cta?`, `at{badge, titulo, card, cta}`.

**`bento`** — Grilla Bento de 2–4 tarjetas Liquid Glass (`tarjeta_cristal`),
cada una con insignia 3D táctil extruida (`insignia_3d` con sombra de contacto,
bisel y brillo especular, inspirada en `3dicons.co` CC0), título y beneficio
conciso en cascada con resorte, más firma/wordmark tipográfico al pie (`pie`,
inspirado en `footer.design` Wordmark Bleed y `scrolltide.co` Service/Ledger
Bento). `rotulo?`, `items[{icono?, titulo, texto, acento?, at?}]`, `pie?`,
`at{rotulo, item0..n, pie}`.

### 31-36. Ronda 5 — Interactivos, Métricas, Social Proof, Audio y 3D (Spotlight, Push Stacks, Testimonios, Donut Charts, Órbitas y Waveforms)

**`buscador`** — Barra de búsqueda estilo Spotlight/Raycast: píldora de cristal con lupa vectorial de acento, cursor intermitente y consulta tipeada en tiempo real (`text_reveal`) + lista de resultados en tarjetas translúcidas con punto indicador y acento opcional. `query`, `resultados[{texto, desc?, acento?}]`, `rotulo?`, `at{rotulo, query, res0..n}`.

**`notificacion`** — Cascada de notificaciones flotantes (estilo iOS/macOS push-down): entran desde arriba con resorte físico y desplazan a las anteriores hacia abajo sin colisión. Cada tarjeta incluye ícono de app, titular en negrita, texto descriptivo en wrap seguro y marca temporal ("ahora", "hace 2 min"). `rotulo?`, `items[{app, titulo, texto, hora?, icono?}]`, `at{rotulo, item0..n}`. `icono`: letra(s) del cuadro (default: inicial de `app`); **nunca emoji**: la tipografía del motor no los tiene y salen como cuadro de tofu (`auditar_plan.py` lo avisa como `[emoji]`).

**`comentario`** — Tarjeta de prueba social / testimonio (Tweet / LinkedIn / Review): avatar circular con iniciales automáticas, titular de autor con insignia de verificación ("✓"), usuario/handle secundario, calificación de estrellas interactiva (`estrellas`), cuerpo con wrap y énfasis por palabras (`*...*`), contador animado de me gusta ("❤️ 1.420 Me gusta") y fecha de publicación. `autor`, `usuario?`, `iniciales?`, `verificado?`, `estrellas?`, `texto`, `likes?`, `fecha?`, `rotulo?`, `at{rotulo, card, texto, likes}`.

**`pie`** — Gráfico circular / rosquilla (Donut Chart): barrido secuencial por sectores con resorte y micro-rotación viva continua, orificio central con cifra/porcentaje destacado, leyenda paramétrica (a la derecha en horizontal 16:9, vertical inferior en 9:16) y fuente de datos al pie. `titulo?`, `porciones[{etiqueta, valor, acento?, color?}]` (sin `color`: el acento y luego la `SERIE` de la marca), `centro?` (sin él: el % y la etiqueta de la porción del acento), `fuente?`, `at{rotulo, pie, p0..n, fuente}`.

**`orbita`** — Apertura cinemática tech / IA: núcleo central brillante con pulso y halo gaussiano suave, 3 anillos elípticos de partículas 3D en perspectiva con diferentes inclinaciones y velocidades orbitales continuas, kicker superior en acento, titular central con wrap y acento, y subtítulo descriptivo inferior. `kicker?`, `titulo`, `subtitulo?`, `at{kicker, titulo, subtitulo}`.

**`audiowave`** — Tarjeta de reproductor / interceptación de audio: botón de reproducción, indicador de estado ("REC ● 00:14"), ecualizador visual de barras armónicas multi-frecuencia en vivo, barra de progreso temporal y transcripción subtitulada sincronizada con revelación progresiva. `archivo?`, `hablante?`, `estado?`, `transcripcion?`, `rotulo?`, `at{rotulo, tarjeta, onda, texto}`.

### 37-39. Ronda 6 — Índice, resalte y apertura de partículas (catálogo de futuros, hoy implementado)

**`index`** — Índice de contenidos: lo que vamos a ver, con el paso activo en
acento. `titulo?`, `items[{texto, activo?}]`, `at{rotulo, item0..n}`. Cada
entrada entra escalonada; el último queda resaltado si ninguno lo está. Para
videos largos (3–6 min) y para prometer la estructura antes de empezar.

**`callout`** — Resalte sobre el dato clave: elipse que se dibuja sola + placa
con la etiqueta. `titulo?`, `captura?` (imagen a señalar), `objeto{x, y, r}`
(fracciones de la captura), `etiqueta`, `detalle?`, `fuente?`,
`at{rotulo, circulo, etiqueta}`. Sin `captura` la elipse flota sobre el
fondo. Con `captura` señala un punto de ella ("mira este 60 %"). El texto va
sobre placa oscura: blanco sobre captura clara no se lee.

**`orbOpen`** — Apertura de capítulo: las partículas **convergen** a una forma
y entra el titular. `titulo`, `subtitulo?`, `figura?` (`esfera`, `chat`,
`robot`), `at{titulo, subtitulo}`. Es lo contrario que `orbita` (donde
orbitan): aquí se forman. Para intros de producto, IA o capítulos.

### 40-41. Ronda 12 — El acta de lo confirmado (reel de "cara")

**`constancia`** — El **acta** de la pieza: un panel con el guion de arriba y,
dentro, N casillas con su marca (✓ lo que ya está confirmado, ○ lo que queda
pendiente) y su texto en versalitas del display en itálica. Es la escena del
reel de "cara" (`De8KNkdDT68`), medida al píxel sobre él: panel de 960 px con
el borde a 1 px; la raya del kicker 40×6 px y el kicker en monoespaciada;
casillas de 425 px con 37 de separación; el círculo lleno de 64 px de diámetro
con el ✓ DENTRO, en negro sobre blanco; el vacío es solo un aro. La casilla
confirmada lleva el borde y el texto en blanco; la pendiente, en gris.

El ✓ se **dibuja** (no es el glifo: "✓" no existe en todas las fuentes y sale
como caja vacía) y el círculo se llena en el instante en que el item se
confirma: `hecho` puede ser `true`/`false` o el segundo en que se confirma (el
✓ se dibuja entonces, en 0,28 s). `items[{texto, hecho}]`, `kicker?` (el guion
de arriba), `y?` (dónde va el panel; por defecto, el fondo de la zona segura),
`at{item0..n}` (la entrada de cada casilla).

El texto de la casilla es el rol `secundario` de la escala (32 px) y **no se
encoge**: si el copy no cabe en dos líneas lo que se acorta es el copy, no la
letra (queda anotado en `RECORTES`).

**`cartel`** — El **cartel**: el rótulo de arriba, un icono de línea GRANDE
en el acento y la afirmación al lado. Es el cartel del reel de "cara"
(`De8KNkdDT68`): "¿QUÉ ESTÁ PASANDO CON NOTEPAD++?" con la lupa al lado, y
"LO VIO DIEGO DESDE / 0 OCT" con el reloj.

MEDIDO sobre ese reel: el panel va de x=60 a x=1019 con el borde de 1 px;
la raya del rótulo mide 40×6 px; el icono de línea mide ~100 px y va en el
acento; la afirmación es el display en negrita y la palabra que sostiene el
dato va en un **bloque rojo** (texto blanco).

El bloque acaba donde acaba la palabra: el markup es **por carácter**, así
que `~NOTEPAD++~?` deja la interrogación fuera del bloque (medido: con el
markup por palabra, la interrogación se quedaba dentro). `*clave*` pone la
palabra en el acento, `~caja~` en un bloque rojo y `^caja^` en un bloque
blanco.

Es la versión **estática** de `frase` (que escribe palabra a palabra): para
una afirmación que ya está escrita, el cartel.

**`camino`** — El **camino**: una línea de luz que corre por la pieza y va
encendiendo las estaciones que pasa. La cámara vuela con la cabeza (el mundo
se escala y se desliza) y cada estación es un nodo 3D.

Es la pieza que se lee como UNA idea y no como una tanda de planos: todo
está en el mismo camino. La línea la dibuja **una sola función** (`trazado`),
que es la misma que sirve para un barra, un subrayado o una onda: el trazo
es un elemento de la casa, no un adorno de esta escena.

MEDIDO sobre el reel de referencia: el nodo mide ~100 px de lado con el
labio oscuro debajo (el botón 3D), la línea pasa por el CENTRO de los nodos
(es la línea la que los revela, no un adorno al lado) y las estaciones se
encienden cuando la cabeza las pasa.

`estaciones[{titulo, icono?}]`, `ruta?` (recta, s), `y?`, `x0?`, `x1?`,
`grosor?`, `color?`, `colores?` (la línea se divide en ramas de colores),
`at{estacion0..n}`.

En **9:16 el camino corre en vertical** (de arriba abajo, la etiqueta a la
derecha del nodo, como el `timeline`): la misma `trazado`, los mismos
`puntos_de_ruta` (la S se abre en perpendicular al recorrido) y el mismo
encendido por la cabeza. Se queda horizontal si el plan fija `y`/`x0`/`x1`
o si vuela la cámara de la pieza (su paneo es lateral).

**`subrayado`** — El **lema con su línea de luz debajo**: la línea es la
línea base y se puede partir en varios colores. Es el cierre del reel de
referencia: "One path," / "every skill." con la línea debajo, que se abre en
los colores de los cursos y vuelve a juntarse.

La línea la dibuja la **misma función** que el camino y que cualquier otro
trazo (`trazado`): aquí lo que cambian son los puntos y los colores. Cinco
trazos dibujados de cinco maneras son cinco trazos que se desincronizan.

`texto` (el lema), `color?`, `colores?` (la línea se parte en estos colores;
`"serie"` = la `SERIE` de la marca, nunca un arcoíris a mano),
`y?`, `tam?`, `grosor?`, `itálica?`, `at{texto, linea}`.

**El vuelo es de la pieza, no de la escena**: es el global `camara` (su
paneo `x0`→`x1`) el que hace que la cámara viaje y el mundo se deslice. Si
la escena volara por su cuenta, la zona segura mediría un mundo saliéndose
del cuadro y la escena se encogería sola (medido: 0,72). Con la cámara
global, el mundo se escapa del encuadre porque la cámara se ha ido, que es
lo que pasa de verdad.

`texto` (la afirmación), `kicker?` (el rótulo de arriba), `icono?` (lupa,
reloj, alerta, globo, codigo), `tam?`, `y?`, `sobre_cara?`, `at{panel, icono, texto}`.

**`cartel`, `cadena` y `constancia` van abajo solo si hay cara debajo**: en
un overlay (la pieza se compone sobre el video) o con `sobre_cara: true` en
la escena, se quedan al pie de la zona segura, bajo la cara. Sin nada debajo
(un plan de motion puro) se colocan como el resto, en el centro óptico: al
pie dejaban el 80 % del 9:16 en negro. El predicado es uno (`sobre_cara`).

**`cadena`** — La **cadena de estados**: N nodos con icono de línea, unidos
por un conector punteado, cada uno con su etiqueta. Es la escena del reel
de "cara" (`De8KNkdDT68`): lo que vio cada quien, en fila. A diferencia de
`constancia` (una lista de casillas con ✓), aquí los nodos se **encadenan**:
el punteado dice que es una secuencia.

MEDIDO sobre ese reel: el nodo es una caja de 149×140 con las esquinas
redondeadas (radio 21) y el borde de 2 px (blanco el activo, gris el que no);
el icono de línea mide 69 px y va centrado; la etiqueta va debajo (el nombre
en negrita y debajo una línea en monoespaciada); el conector son guiones de
10 px con 12 de hueco, que arrancan a 16 px del borde del nodo (unen, no
pegan).

`items[{icono, titulo, sub?, activo?}]`, `kicker?` (el guion de arriba),
`y?`, `at{item0..n}`.

Los iconos son **trazos dibujados**, no glifos (un glifo depende de que la
fuente lo tenga: "✓" sale como caja vacía en muchas). Los que hay:
`codigo` (los dos chevrones y la barra del signo de código), `globo`
(círculo con elipse vertical y ecuador), `alerta` (triángulo con el signo),
`lupa` (círculo con mango) y `reloj` (círculo con agujas). Un icono que no
existe se dibuja como el borde de una ficha: se ve que falta, y no es un
hole silencioso en la pieza.
## Qué escena para qué dato

Elegir la escena por la forma del dato y por lo que el plano deja leer, no por
la que se ve más vistosa. Criterios destilados de la guía de gráficos de
UI/UX Pro Max (nextlevelbuilder, MIT); los límites de elementos son
orientativos para video (cada plano vive 3-5 s y el espectador está en un
teléfono).

| El dato es... | Escena | Úsala cuando | No la uses cuando |
|---|---|---|---|
| Comparar categorías por magnitud | `bars` (pocas, verticales) o `ranking` (horizontal; el orden es el mensaje) | el mensaje es «cuál es mayor» o «cuánto más» | hay proporciones de un todo (usa `pie`), o más categorías de las que el plano deja leer (~6 barras, ~8 filas: el resto en «otros» o en un segundo plano) |
| Parte de un todo | `pie` (dona) | 2-5 porciones con diferencias visibles (menos de 5 % entre porciones no se distingue) | más de 5-6 porciones, o importan los valores exactos (usa `ranking` con los porcentajes) |
| Un valor frente a una meta | `gauge` | UN indicador con meta o máximo conocidos | no hay meta (usa `stats`) o hay varios KPI a la vez |
| Cifras sueltas con contexto | `stats` | 1-4 cifras que importan, cada una con su etiqueta y fuente | una sola cifra sin contexto: es un titular (usa `remate`) |
| Hitos en el tiempo | `timeline` | 3-6 hitos con fecha | una serie continua de muchos puntos |
| Dos opciones lado a lado | `versus` | dos alternativas con 2-4 atributos | más de dos alternativas (una secuencia de planos) |
| Pasos de un proceso | `pasos` | 1-5 pasos secuenciales | los pasos no son secuenciales (usa `bento`) |
| Un plazo o una oferta | `countdown`, `oferta` | el valor es función del tiempo | — |

**No hay escena de línea (tendencia o serie), de embudo ni de dispersión: no
inventar un `tipo`.** Con menos de 4 puntos, una tendencia es una cifra con su
delta (`stats`); una serie corta cabe en `bars` por periodo; si la serie es la
protagonista de la pieza, es composición libre o una escena futura.

Reglas de todo dato: ordenar de mayor a menor salvo que exista un orden
natural (el tiempo); etiquetas directas en lugar de leyenda; **el color nunca
es el único código** (etiqueta, posición o forma además); las cifras que
cuentan llevan su valor exacto en cada frame (`direccion.md`); y el titular
enuncia el hallazgo, no el tipo de gráfico («Las ventas se duplicaron», no
«Gráfico de ventas»).

## Ideas de escenas futuras (NO implementadas — no usar como `tipo`)

⚠️ Estos nombres **no existen** en `SCENES` (`scripts/render_plan.py`): usar uno
en `plan.json` produce `KeyError`. Son ideas para implementar, no tipos válidos.
`lineup` · `rise` · `orbChips` · `outro` · `broll` ·
`tituloDetras` (requiere Robust Video Matting) · `subscribe`

Ya implementadas (Ronda 6): `orbOpen` · `callout` · `index` · y la transición
`dissolve`.

Para añadir una nueva escena: componer con las primitivas DRY (`barra_h`,
`cuenta_up`, `arco`, `cuadricula`, `linewrap`, `particulas`, `text_reveal`,
`kenburns`, `cursor`, `onda_clic`, `smoothstep`, `odometro`, `estrellas`,
`imagen_ajustada`, `tarjeta_cristal`, `boton_halo`, `insignia_3d`) — NO duplicar lógica.
Ver `references/scene-patterns-from-internet.md` para portar escenas validadas.

---

→ Canónico: `references/escenas.md` · Dominio: escenas · Vecinos: `references/plan-video.md`, `references/intencion-escena.md`, `references/escenas-extendidas.md`
