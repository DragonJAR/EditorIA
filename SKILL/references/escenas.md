# Catálogo de escenas (13 tipos del plan)

Cada escena es una función `(ctx, e, t)` donde `e` es su bloque del plan y `t`
el tiempo absoluto del video (ver `scripts/render_plan.py`, `SCENES`).
Todas comparten: fondo vivo, salida anticipada 0.5s, transición `mancha`
opcional al entrar. Tiempos `at` en segundos absolutos del video.

## 1. `apertura` — gancho
Mancha orgánica que se infla tras el titular + objetos flotantes + titular cinético
en dos fases (`texto1` → `texto2` en `at.cambio`). Palabras con tiempos `at.p1/p2`.
- Params: `texto1[]`, `texto2[]`, `at{cambio, p1[], p2[]}`

## 2. `canales` — "todos tus canales, un lugar"
Marca grande al centro que sube y se encoge; tarjetas de canal que entran volando
con resorte y se juntan en una bandeja (filas que crecen). Rótulo al final.
- Params: `marca`, `rotulo`, `canales[{canal, nombre, texto, at}]`, `at{marca, junta, rotulo}`

## 3. `medianoche` — teléfono 3D
Teléfono que rota en 3D al entrar (perspectiva, rotateY de -70° a -12°). Pantalla
con fecha/hora y notificaciones que caen con resorte y empujan a las anteriores.
- Params: `rotulo`, `hora`, `fecha`, `notificaciones[{canal, titulo, texto, at}]`

## 4. `chat` — conversación con IA
Burbujas de chat (cliente izq, IA der) que aparecen con resorte; la IA "escribe"
(puntos suspensivos) antes de responder. Link de pago como tarjeta final.
- Params: `rotulo`, `cliente`, `iniciales`, `mensajes[{de, texto, at}]`, `link{titulo, monto, at}`

## 5. `leads` — tabla priorizada
Filas de tabla que entran en cascada; resaltado por temperatura (Caliente/Tibio/Frío)
sincronizado con `at`. Puntaje como barra.
- Params: `rotulo`, `total`, `filas[{nombre, canal, etapa, puntaje, temp}]`, `at{rotulo, Caliente, Tibio, Frío}`

## 6. `handoff` — traspaso con contexto
Tarjeta de persona + lista de contexto (clave/valor) que se revela línea por línea.
Nota de aviso ("Te avisa al instante").
- Params: `rotulo`, `cliente`, `iniciales`, `temp`, `nota`, `contexto[{k, v}]`, `at{rotulo, persona, contexto}`

## 7. `pago` — comprobante
Comprobante que sube con resorte; cursor que se mueve y "pulsa" (escala + onda).
Monto grande.
- Params: `rotulo`, `cliente`, `monto`, `detalle`, `at{rotulo, comprobante, cursor, toque}`

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
Cursor que arrastra una barra de progreso; al completarse, tarjeta "pagado" con
cambio de color.
- Params: `rotulo`, `resumen`, `cliente`, `hace` (ej. "hace 2 horas"),
  `monto`, `at{rotulo, cursor, recupera, pagado}`

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

## Catálogo unificado de escenas (24 tipos del plan)

A partir de 2026-10-04, el catálogo integra las 13 escenas originales más 11
escenas de datos/UI/tipo/cinemática validadas externamente (ver
`references/scene-patterns-from-internet.md`). Cada nueva escena se compone
con las primitivas DRY de `render_plan.py` (`barra_h`, `cuenta_up`, `arco`,
`particulas`, `cuadricula`, `linewrap`, `text_reveal`, `kenburns`).
**Marca-blanca**: el color viene del brand pack (`brand/*.json`); sin pack,
se usa el `ACENTO` neutro del renderer.

### 14-21. Catálogo extendido (DataAnimations + UI + Theme)

Fuentes: `lifeprompt-team/remotion-scenes` (DataAnimations, Theme, ListAnimations)
y `ali-abassi/remotion-templates` (Charts & Data, Stat Counter, Quote Card).

**`bars`** — Barras verticales de comparación. `barras[{etiqueta, valor, max, acento?}]`,
`at{rotulo, bar0..n, fuente}`. Toda cifra lleva su `fuente` en pantalla.
Fuente: `DataBarChart` de `lifeprompt-team/remotion-scenes` (MIT).

**`gauge`** — Indicador circular (270°) con cuenta animada al centro.
`valor`, `max`, `etiqueta`, `at{rotulo, gauge, etiqueta}`.
Fuente: `DataGauge` (MIT).

**`ranking`** — Ranking horizontal con barras proporcionales, #1 lleva acento.
`items[{etiqueta, valor, fecha?}]`, `at{rotulo, item0..n, fuente}`.
Fuente: `DataRanking` (MIT).

**`stats`** — Grid de stat cards (cifra grande + etiqueta). `cards[{valor, etiqueta, acento?}]`,
`at{rotulo, card0..n, fuente}`. Auto-layout cols según `n`.
Fuente: `DataStatsCards` (MIT).

**`timeline`** — Timeline horizontal con puntos pulsantes. `items[{etiqueta, fecha?}]`,
`at{rotulo, item0..n}`.
Fuente: `DataTimeline` (MIT).

**`quote`** — Quote card con autor y fuente. `texto`, `autor`, `fuente`,
`at{card, texto, autor, fuente}`. Word-wrap automático.
Fuente: `ThemeAnimations › quote` (MIT).

**`versus`** — Comparación lado a lado. `izquierda{etiqueta, items[]}`,
`derecha{etiqueta, items[]}`, `at{rotulo, izq, der}`.
Fuente: `ListAnimations › versus` (MIT).

**`confetti`** — Celebración con confeti determinista (seed) + texto.
`texto`, `subtexto?`, `at{particulas, texto, subtexto, timestamp_seed?}`.
Fuente: `ParticleAnimations` (MIT).

### 22-24. Ronda 2 — Texto, Cinemática y Pasos (reactvideoeditor/remotion-templates, MIT)

**`typewriter`** — Texto que aparece carácter a carácter con cursor parpadeante.
`texto`, `tam?` (auto-fit), `at{rotulo, cursor, fuente}`. Útil para hooks, intros
y subtítulos animados. Fuente: `typewriter-subtitle.tsx` (MIT).

**`kenburns`** — Ken Burns sobre una imagen: zoom + paneo progresivo. Ideal para
galerías, openings sobre foto, documentales. `imagen` (ruta), `titulo`,
`subtitulo?`, `zoom_from?` (1.0), `zoom_to?` (1.15), `pan_x?`, `pan_y?`,
`dur_kb?` (4.0s), `at{rotulo, kenburns, texto, subtitulo}`.
Fuente: `ken-burns.tsx` (MIT).

**`pasos`** — Ruta de N pasos (1-5) en fila (16:9) o columna (9:16), con el
paso activo brillando y los demás atenuados. `titulo?`, `items[{titulo, texto, at}]`,
`at{rotulo, item0..n}`. Fuente: `progress-steps.tsx` (MIT).

## Ideas de escenas futuras (NO implementadas — no usar como `tipo`)

⚠️ Estos nombres **no existen** en `SCENES` (`scripts/render_plan.py`): usar uno
en `plan.json` produce `KeyError`. Son ideas para implementar, no tipos válidos.
`orbOpen` · `lineup` · `rise` · `orbChips` · `dissolve` · `outro` · `broll` ·
`callout` · `lowerThird` · `tituloDetras` (requiere Robust Video Matting) ·
`index` · `subscribe` · `notificacion` · `buscador` · `comentario`

Para añadir una nueva escena: composer con las primitivas DRY (`barra_h`,
`cuenta_up`, `arco`, `cuadricula`, `linewrap`, `particulas`, `text_reveal`,
`kenburns`) — NO duplicar lógica. Ver `references/scene-patterns-from-internet.md`
para portar escenas validadas de las fuentes MIT documentadas allí.
