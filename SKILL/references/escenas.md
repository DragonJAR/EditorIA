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

## Ideas de escenas futuras (NO implementadas — no usar como `tipo`)

⚠️ Estos nombres **no existen** en `SCENES` (`scripts/render_plan.py`): usar uno
en `plan.json` produce `KeyError`. Son ideas para implementar, no tipos válidos.
`orbOpen` · `lineup` · `revealStat` (cifra + fuente obligatoria) · `rise` ·
`orbChips` · `dissolve` · `outro` · `bars` (barras + fuente) · `broll` ·
`callout` · `lowerThird` · `tituloDetras` · `index` · `subscribe` ·
`notificacion` · `buscador` · `pasos` · `comentario`
