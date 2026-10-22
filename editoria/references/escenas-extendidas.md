# Escenas extendidas (conceptos portables)

Conceptos de escena del catálogo del sistema original, portables al motor
de planes (`scripts/render_plan.py`). Ninguno depende de marca.

**Estado real**: `notificacion`, `buscador`, `comentario` y `pasos` YA están
implementadas (Ronda 5, en `references/escenas.md`); `orbOpen` se implementó en
la Ronda 6. Los que siguen son **conceptos pendientes**: se implementan bajo
demanda siguiendo `references/escenas.md` y `references/reglas-tecnicas.md`.

## `notificacion` — notificaciones que caen (IMPLEMENTADA)

Notificaciones de móvil que caen desde arriba; la nueva empuja a las demás.
`items[{app, nombre, titulo, texto, hora, at}]`. Sirve para "el problema"
(mientras no contestas…), alertas, mensajes. Timing: la caída dura ~0.4s
con overshoot leve; cada item entra en su `at`.

## `buscador` — barra que se escribe sola (IMPLEMENTADA)

Barra de búsqueda que se escribe sola (`query`, `typeAt`, `speed`) y
despliega `results` (`accent` en el bueno). Ideal para preguntas, comparativas,
"la gente busca…". La consulta puede ocupar 2 líneas en 9:16.

## `comentario` — chat / comentarios (IMPLEMENTADA)

Dos estilos: `"chat"` (burbujas, "yo" a la derecha, indicador
«escribiendo…») o `"comentarios"` (avatar + texto + me gusta). Para
testimonios, objeciones y respuestas, prueba social.

## `pasos` — ruta de 2–5 pasos (IMPLEMENTADA)

Fila en 16:9, columna en vertical. `items[{title, text, logo, at}]`;
el paso activo brilla, los demás atenuados. Para procesos, tutoriales,
"cómo funciona".

## `tituloDetras` — titular detrás de la persona

Titular gigante DETRÁS de la cabeza del presentador (requiere persona con
alfa). El presentador queda delante del gráfico. Máx. 2–3 por video;
gráficos que el cuerpo no tape (titulares y cifras a un lado, nunca
centrados detrás de la cara).

## `iris` — apertura en círculo desde la cara (IMPLEMENTADA: transicion `iris`)

Transición sin corte: la escena a pantalla completa se abre en círculo
desde la cara del presentador. Curva propia (no reutilizar easeOut: a los
5 fotogramas ya cubría casi todo — medir la curva).

## `orbOpen` — esfera de partículas + titular (IMPLEMENTADA, Ronda 6)

Apertura de capítulo o tesis: esfera de partículas que se forma y titular.
`figure: chat|robot` u otro motivo según el tema.

## Reglas comunes (del sistema original)

- Toda cifra de un estudio lleva su **fuente en pantalla**.
- En vertical, textos de escena ≤ 17 letras por línea en rótulos grandes.
- Las escenas a pantalla completa se adaptan a 16:9, 9:16 y 4:5.
- Dos escenas a pantalla completa seguidas: solapar la siguiente ~0,4 s
  (la salida dura ~16 fotogramas); si no, asoma el fondo entre ambas.

---

→ Canónico: `references/escenas.md` · Dominio: escenas · Vecinos: `references/scene-patterns-from-internet.md`, `references/prompt-motion-graphics.md`, `references/copy.md`
