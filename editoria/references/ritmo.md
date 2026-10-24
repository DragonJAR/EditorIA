# Ritmo y encadenamiento — anti-slideshow

Movimiento suave no basta: un video puede ser fluido y aun así leerse como
presentación de diapositivas. Esto pasa por dos fallas distintas, y cada una
tiene su prueba.

## Deconstruir la referencia antes de tocar nada

Regla dura: antes de diseñar una pieza, medir la referencia (o el footage)
con `scripts/verificar_ritmo.py`. Anotar los números que la pieza tiene que
igualar: porcentaje de cuadros casi quietos, número de cortes duros, dónde
están las ráfagas, cuánto aire blanco. Una pieza construida sin medir sale
con cadencia uniforme — siempre.

## Falla 1: la cadencia (el metrónomo)

Tomas de la misma duración con la misma forma (corte, zoom, etiqueta,
corte, zoom, etiqueta) son diapositivas aunque cada una se mueva. La cura
es la variación medible. Jerarquía canónica de cadencia (tres relojes):

- **Micro-idle continuo**: respiración ±4–6px en elementos asentados; algo
  se mueve en cada frame sin que se note como "evento".
- **Idea nueva por beat (2–4 s)**: un dato o componente nuevo por beat;
  nunca más de una idea por beat.
- **Reset sensorial mayor (3–5 s)**: cambio de ángulo, B-roll, sting, zoom.
  Variar el TIPO; el zoom mecánico cada 3s se lee amateur.

- **Coeficiente de variación de duraciones de toma ≥ 0.25.** Si las tomas
  duran todas ~1.5s, es un metrónomo. Medido con
  `scripts/verificar_ritmo.py --cortes t0,t1,...`.
- **Al menos 25% de cuadros casi quietos** (diferencia media por cuadro
  mínima) y **al menos una pausa ≥ 1s** bajo el umbral. El silencio visual
  le da peso a lo que se mueve.
  **Salvedad por concepto**: una pieza sobre planos reales que siempre se
  mueven (footage vivo) no tiene ese silencio: no es un defecto de la pieza,
  es que el mínimo no le aplica. Mismo caso que la ráfaga, que tampoco es un
  defecto si el concepto no la pide.
  Se declara en el **plan** de la pieza, con el HECHO y no con la exención:

  ```json
  {"sobre_footage_vivo": true}
  ```

  El plan es el documento de la pieza: ahí queda **registrado** por qué el
  mínimo no aplica, y dentro de un año quien la mida lo ve. Un flag de CLI
  no deja constancia de nada: el siguiente que lo corra lee «plana» sin
  contexto. Y el campo declara un hecho comprobable («esta pieza se compone
  sobre planos que siempre se mueven»), no una exención que el verificador
  no puede comprobar: si el día de mañana cambia el criterio, el campo sigue
  diciendo la verdad y el verificador deduce de ahí.
  Con el plan delante, `verificar_ritmo.py` toma además los **cortes** de los
  tiempos de las escenas (los beats que percibe el espectador; los fundidos
  del footage no son cortes que `scene-select` vea) y **sigue midiendo igual
  la cadencia y la ráfaga**: el silencio visual no es la excusa para no
  tener ritmo.
  Para medir un video suelto, sin plan, está el equivalente
  `--sobre-footage-vivo` en la CLI.
- **Al menos una ráfaga** si el concepto tiene impactos: ≥3 cambios grandes
  dentro de 1.5s. Un concepto sin impactos (un elemento que se transforma,
  una cámara continua) no necesita ráfaga — no es un defecto.
- **Nunca terminar una toma igual dos veces seguidas**: alternar salidas
  (resorte hacia afuera, desenfoque, corte duro, deriva).

## Falla 2: la falta de encadenamiento

Cada beat puede tener buen ritmo y aun así la pieza lee como PPT si cada
beat es su propia escena que reemplaza a la anterior. La regla:

- **Cada beat nace del beat anterior.** Un personaje aterriza sobre el
  titular y lo desarma; la página crece desde la tarjeta; la cámara empuja
  hacia el ancla que ya está en pantalla. Nada aparece en un vacío nuevo;
  nada desaparece sin transformarse en lo siguiente.
- **Continuidad de causa**: cada reacción visible tiene una causa visible
  (una mano que toca, una colisión, un gesto). Sin causa, el movimiento es
  decoración.
- **La cámara persigue**: la cámara virtual sigue al elemento que cada beat
  enmarca — con retardo, inclinándose, asentándose. Nunca salta de un
  encuadre a otro sin viajar.

## Mostrar mecanismos, no miniaturas

- Cuando el movimiento de algo es demasiado pequeño para leerse a tamaño
  tarjeta, mostrar el **mecanismo como componente** (recortado, ampliado,
  vivo), no la miniatura borrosa.
- Pantallas completas solo para **pausas**, con la mano (o el agente causal)
  visible.
- **Matar todo adorno que no sea comportamiento del producto**: confeti,
  destellos, partículas decorativas *sobre el contenido*. Si no explica,
  estorba. Excepción: capas de ambiente (partículas, brasas) solo en
  intro, transiciones y outro — nunca compitiendo con el contenido
  (ver `reglas-tecnicas.md`: el ambiente va en los bordes, el contenido
  necesita calma).

## Piso de lectura (ley dura)

El ritmo alto viene del movimiento rápido, las transiciones ágiles y los
cortes ajustados — NUNCA de retirar texto antes de que se pueda leer. Todo
elemento de texto que el espectador deba leer necesita su tiempo asentado
(ya entró, aún no sale):

- Etiqueta corta o línea de 1–3 palabras: **~0.8 s asentada**.
- Titular o frase completa: **~0.3 s por palabra**, mínimo ~1.2 s. La línea
  del hook lleva el mayor hold.
- Entradas y transiciones: ágiles (0.3–0.6 s). Una línea puede ENTRAR de golpe
  y luego SOSTENERSE — fast-in + hold adecuado se lee punchy Y legible.

Dos modos de falla que se diseñan fuera en el plan:

- **Demasiado texto para la escena.** Una escena de 4 s admite 2–3 lecturas
  cortas, no 6. Si la escena carga más texto del que su duración permite,
  cortar copy o dividir la escena — no acelerarla.
- **Texto secuencial sobre beats rápidos.** Revelar una línea legible en cada
  beat a 110+ BPM (~0.5 s entre beats) es demasiado rápido para leer. Para
  TEXTO secuencial: enganchar cada dos beats, o revelar rápido y sostener el
  conjunto en pantalla. Los acentos no textuales (glows, ticks, dots) sí pueden
  ir en cada beat.

## Disciplina de beats (strong cues vs grilla)

`scripts/beat_grid.py` estima BPM, fase y energía por compás. Sobre esa salida,
dos capas distintas (doctrina de `/brag`):

- **Strong cues (1–3 por pieza):** los compases de mayor energía (drops, swells,
  acentos). Solo para **momentos mayores**: transiciones de escena, hero reveals,
  aterrizaje del logo. El reveal puede moverse hacia el cue fuerte más cercano
  dentro de **±0.15 s**. Marcarlo en el plan: `// beat-lock: 5.80s`.
- **Grilla de beats:** para **eventos secuenciales pequeños**: tarjetas que
  llegan una por una, stats que aparecen, SFX encadenados. Enganchar cada item
  al beat más cercano dentro de **±0.10 s**. Marcarlo: `// beat-grid: stat 1
  en 12.65s, stat 2 en 13.17s, stat 3 en 13.70s`.

Reglas de cordura:

- Los cues **sesgan** el timing, no lo controlan. Si enganchar un tween al beat
  daña la legibilidad, el ritmo de la escena o la historia, se usa el timing
  natural.
- No forzar cada tween al beat. 1–3 locks fuertes por pieza bastan; el resto
  respira.
- En tonos de restricción (`parodia`, piezas sobrias), los cues son raros,
  silenciosos, o se reservan para el logo final.

## Verificación

`python scripts/verificar_ritmo.py video.mp4 --cortes 0,1.6,3.0,...`:
falla la pieza si la cadencia es uniforme o si no hay pausas. La prueba de
encadenamiento es de diseño (revisar el plan: ¿cada beat nace del anterior?),
no de píxeles.

---

→ Canónico: `references/animacion.md` · Dominio: movimiento · Vecinos: `references/fluidez.md`, `references/formatos.md`, `references/direccion.md`
