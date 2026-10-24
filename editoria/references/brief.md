# Brief — el encargo de una parte

Un brief es el encargo que recibe quien construye **una parte** de una pieza:
una escena, un bloque de escenas, un tramo de trabajo. Se escribe **antes** de
ejecutar: redactado después describe lo que salió, no lo que se pidió.

## Qué es y qué no es

- **No es el plan.** `plan.json` es la partitura (tipo, `from`/`to`, `at`,
  `datos`): el contrato de máquina. El brief es el encargo humano: lectura,
  presupuesto, revisión, propiedad de los ficheros.
- **No es el `BRIEF.md` del proyecto.** Ese lo escribe `scripts/proyecto.py`
  con lo que pidió el usuario; solo el usuario lo cambia.
- **No sustituye al storyboard.** El storyboard dice qué pasa y por qué; el
  plan dice cuándo; el brief dice quién hace qué y cómo se revisa.

Un plan sin briefs se ejecuta igual; un brief sin plan no se puede integrar.

## Las seis cosas que un brief tiene que decir

**1. QUÉ: la parte exacta y su FIN.** Una frase que nombra la parte, y el FIN:
qué tiene que conseguir el espectador en ese trozo. Sin el FIN, dos partes
repiten la misma idea.

**2. DÓNDE: la ventana y el formato de salida.** La ventana en segundos
absolutos (`from`/`to`), la escena del catálogo que la resuelve, sus instantes
(`at`) y el formato exacto de la entrega: nombre del fichero, qué campos lleva,
en qué forma. Con dos partes en paralelo el resultado vuelve por su nombre.

**3. CON QUÉ: el vocabulario y las referencias.** Los tipos de escena del
catálogo, la forma de `at` (número, lista o dict, anclado a palabra, beat o
pico), el bloque `datos` con su `fuente`, `transicion`, y las referencias que
hay que leer antes de escribir. La intención hay que leerla: no se adivina.

**4. PRESUPUESTO: duración, entradas y coste.** Cuánto dura la ventana,
cuántas entradas o tomas tiene y qué cuesta (el motor compone a 30 fps por
defecto: X segundos son 30X cuadros en `salida.frames/`). Y, sobre todo, qué
se hace si no cabe: se quitan elementos (pasos, rótulos, cues de sonido),
nunca se acorta el hold de lectura ni se pisa la voz.

**5. CÓMO SE REVISA: la auto-revisión obligatoria.** Antes de dar la parte por
buena, en este orden:

1. Hoja de contactos con `scripts/contact_sheet.py` sobre el clip de la parte
   (`--video parte.mp4 -n 20 -o hoja.png`; `--cada` para el movimiento fino,
   `--palabras` para leer lo dicho bajo cada tile).
2. Qué se mira en ella: el primer y el último cuadro de cada toma (los bordes
   muestran el pop y el texto cortado), la lectura (de un vistazo), el contraste
   (texto contra fondo) y la zona segura (`scripts/auto_qa.py --safe reels`).
3. Medición con `scripts/medir_animacion.py --plan plan.json`: pops, tirones,
   hold muerto, densidad, letra real, zona segura y coste por cuadro.
4. Puerta con `scripts/qa_entrega.py video.mp4`, y con `--plan plan.json`
   cuando la parte ya está integrada.

Lo que no se mira no existe: compilar no es validar (el detalle de cada
comprobación, en `references/qa-entrega.md` y `references/checklist-qa.md`).

**6. QUÉ SE DEVUELVE: el fichero y un informe corto.** El fichero que produce
la parte y un informe de un párrafo: qué se cambió respecto al brief y qué
quedó fuera. Lo que quedó fuera es lo que otra parte puede reclamar.

## La regla de propiedad

Esta es la regla que hace que las partes se hablen entre sí; cada punto lleva
el fallo que evita:

1. **Si falta un helper, se escribe PRIVADO dentro de la parte**, en su
   propio fichero y con un nombre que no choque con nada. No se toca el
   fichero compartido. El fallo que evita: un cambio silencioso en un fichero
   compartido hace que la otra parte deje de funcionar sin que nadie lo sepa.
   En EditorIA el fichero compartido es el motor (`scripts/render_plan.py`):
   tocarlo desde una parte rompe todas las escenas que no estabas mirando.
2. **Si encuentras un bug en un fichero compartido, lo REPORTAS con fichero y
   línea; no lo arreglas en silencio.** El fallo que evita: un arreglo mezclado
   con tu trabajo llega al ensamble sin que nadie sepa qué versión del fichero
   compartido es la buena, y si estaba mal se pierde el diagnóstico original.
3. **El fichero compartido se cambia solo cuando el trabajo es del motor, no
   del montaje.** Si el defecto está en el motor (una escena del catálogo no
   compone un campo que todos leen) se hace con su revisión y su puerta, y se
   avisa a las partes que dependían de él; si el defecto es de la parte (un
   texto que no cabe en su ventana) se arregla en la parte.

Esto **no cambia el diseño por defecto**: EditorIA es de un hilo por diseño
(regla 10 de `references/media-hard-rules.md`). Delegar es una excepción
consciente, y su condición es el alcance disjunto: cada parte toca solo sus
ficheros. Si dos partes tocan el mismo fichero, ningún brief lo salva.

## El bucle que funciona

**Plan por escrito, construir parte a parte, revisar con hojas de contactos,
corregir, y solo entonces integrar.** La regla que lo sostiene: no se integra
lo que no se ha mirado. Un cuadro que nadie ha mirado no está revisado.

**Storyboard antes del código.** Si la pieza tiene más de un bloque, el plano
se escribe primero: tiempo, intención, qué se ve y cómo se sale de cada plano.
El plano tiene dos versiones y ninguna sustituye a la otra: la humana va
antes, porque el plan dice CUÁNDO y el storyboard dice QUÉ PASA Y POR QUÉ. Un
plan de doce escenas sin storyboard son doce clips: cada uno bien hecho y,
juntos, sin hilo. El hilo se decide antes de dibujar y la columna "cómo se
sale" no es decorativa: es el corte y la `transicion` del plan.

## Un brief mínimo (escena `pasos`)

```
QUÉ
  Resumen del bloque 2: los tres pasos del alta, en una sola escena.
  FIN: que el espectador salga sabiendo que el alta son tres pasos y los
  pueda contar. No es la escena que explica el alta paso a paso.

DÓNDE
  Ventana 12.40 - 20.40 (8.0 s del video). Escena del catálogo: `pasos`.
  Instantes (absolutos): at = {"rotulo": 12.90, "item0": 13.80, "item1": 16.00,
  "item2": 18.20}. Salida: bloque2/pasos.json, un objeto de escena con los
  campos que la escena lee: tipo, from, to, titulo, items, at.

CON QUÉ
  Tipo `pasos`; `titulo` (el rótulo), `items[{titulo, texto}]` y el dict `at`
  con rotulo e item0..item2. Ningún campo fuera de esos: la escena avisa de
  lo que no lee. Lectura: references/escenas.md, references/plan-video.md,
  references/direccion.md.

PRESUPUESTO
  8.0 s, 3 pasos, 4 entradas, 240 cuadros a 30 fps.
  Si no cabe: fuera un paso; nunca un hold de lectura más corto.

CÓMO SE REVISA
  1. Mini-plan de la parte (la escena en su propia ventana: from 0, to 8.0 y los
     at corridos a esa base) y render:
       python3 scripts/render_plan.py bloque2/pasos.plan.json -o bloque2/pasos.mp4
  2. Hoja de contactos (mirar: primer y último cuadro, lectura de un vistazo,
     contraste, zona segura):
       python3 scripts/contact_sheet.py --video bloque2/pasos.mp4 -n 20 -o evidencia/pasos.png
  3. Medir: python3 scripts/medir_animacion.py --plan bloque2/pasos.plan.json
  4. Puerta: python3 scripts/qa_entrega.py bloque2/pasos.mp4
     (con --plan plan.json cuando ya está integrada).

QUÉ SE DEVUELVE
  bloque2/pasos.json, evidencia/pasos.png y un informe de tres líneas: qué se
  cambió respecto al brief y qué quedó fuera de la parte.
```

## Dónde vive el brief

- **El brief de proyecto** vive en `BRIEF.md`, en la carpeta del proyecto: lo
  escribe `scripts/proyecto.py` con lo que pidió el usuario. No es el brief de
  parte, que vive en el sitio de trabajo de la parte, junto a lo que produce:
  ni dentro de `plan.json` (ahí va el contrato de máquina) ni pegado en
  `BRIEF.md` (ahí manda el usuario).
- **El resultado de la parte vuelve al plan**, y el plan es la única fuente de
  verdad del TIEMPO. El bloque `datos` manda sobre lo que una escena escriba
  a mano.
- **El brief no puede contradecir al plan.** Si el brief dice una ventana y el
  plan otra, gana el plan y el brief se corrige, nunca al revés: si el plan
  dice 8 s y el brief dice 12, la parte hecha para 12 no encaja en nada. Si el
  encargo cambia durante la ejecución, se escribe una versión nueva del brief
  en el mismo sitio; el anterior no se corrige en silencio.

---

→ Canónico: `references/brief.md` · Dominio: plan · Vecinos: `references/plan-video.md`, `references/media-hard-rules.md`, `references/direccion.md`
