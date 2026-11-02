# El jurado independiente

La segunda opinión. Una pieza la juzga quien la hizo (el agente que compone
también es el que se relee, y ya no ve lo que hay) o no la juzga nadie.

Este documento es el encargo: **cómo pedir una lectura independiente, qué
tiene que devolver, y qué hacer con lo que devuelve**. No es una segunda
rúbrica: el listón es el de `references/rubrica-premios.md` (los ocho ejes) y
esta referencia explica cómo pedirlo y cómo actuar sobre el resultado.

## Cuándo se pide

- Antes de entregar una pieza de marca (un reel de servicios, un lanzamiento).
- Cuando la pieza pasó la puerta (`qa_entrega.py`) y aun así se siente
  "correcta pero genérica": la puerta mide lo medible, no el impacto.
- Cuando hay presupuesto para UNA ronda más de arreglo. El jurado sin ronda de
  arreglo es un informe que nadie lee.

## Qué se le da al jurado

1. **La pieza** (el MP4) y **el plan** (`plan.json`).
2. **La lista de restricciones** de la pieza: plataforma, duración, marca y lo
   que NO se puede decir (claims, cifras, nombres).
3. **El listón**: los ocho ejes de `references/rubrica-premios.md`. El jurado
   no inventa ejes: califica los que ya existen.
4. **Las herramientas**, que el jurado debe usar antes de opinar:
   - `scripts/contact_sheet.py --video VIDEO -n 12 -o hoja.jpg` — la hoja de
     contactos: la primera impresión de la pieza entera.
   - `scripts/contact_sheet.py --video VIDEO --en T0,T1 --cada 0.2` — tiras
     de frames finos alrededor del momento que se está juzgando.
   - `scripts/medir_animacion.py --video VIDEO` y `scripts/qa_entrega.py` — las
     medidas; el jurado no repite lo que una herramienta ya mide.
   - Fotogramas a resolución completa (no la hoja) para mirar los bordes, el
     ajuste de las líneas, el aliasing, el bandeado, la textura y los recortes.

## Qué tiene que devolver

**1. La tabla de los ocho ejes** con su nota y su veredicto (`rubrica-premios.md`).

**2. Los problemas CRÍTICOS**, marcados aparte: un elemento que el listón
prohíbe (una cifra sin fuente, un logo que no es del pack, una marca ajena, un
texto que no se lee, una tipografía de reserva que sale como caja vacía, una
pieza que no cumple el spec de la plataforma).

**3. Una lista de 5–10 arreglos, ordenados por impacto.** Cada arreglo tiene
cuatro cosas, y le faltan tres no es un arreglo:

| | Qué es |
|---|---|
| **Timecode** | dónde está el problema (`0:23.4`), no "por la parte de arriba" |
| **Qué se ve** | lo que hay en ese instante, en una frase |
| **Por qué importa** | el efecto en el espectador (no se lee / distrae / se ve barato) |
| **Cómo se arregla** | la instrucción concreta, con números: "baja el titular a 0.8 s de entrada", "cambia el easing a cubic-bezier(0.34, 1.56, 0.64, 1)", "saca la tercera tarjeta" |

**Al menos un arreglo tiene que subir el IMPACTO, no pulir.** Una lista de
diez retoques de color es un trabajo perdido: la pieza sigue siendo la misma.
Si no hay un arreglo de impacto, el jurado no ha entendido la pieza.

## La barra de calidad: cuándo se rechaza el propio trabajo

Antes de pedir la lectura, el autor aplica la barra sobre su propia pieza. Se
rechaza y se vuelve a empezar si la pieza se siente como:

- una plantilla: el mismo esquema de siempre (tarjeta + titular + botón) con
  las palabras cambiadas;
- "de IA": gradientes de fondo, brillos decorativos, íconos de línea sin
  función, tres capas de cristal, texto alineado al centro en todo;
- un VIDEO de stocks: se ve que nadie compuso, solo que alguien consume;

Ese veto es el mismo en todas partes: si la pieza no tiene una idea que una
plantilla no tiene, no se entrega.

## La ronda de arreglo

1. Se guarda la versión N (el archivo y el plan).
2. Se aplican **todos** los CRÍTICOS y los de **alto impacto**. Un arreglo de
   bajo impacto se puede rechazar: y se dice por qué.
3. **No se retrocede lo que ya estaba bien**: un arreglo que arregla un defecto
   y rompe la jerarquía o el ritmo es peor que el defecto.
4. Si un arreglo se sustituye por una solución mejor, se puede — pero se
   explica por qué se sustituyó.
5. Se vuelve a renderizar y se vuelve a pasar la puerta (`qa_entrega.py`).
6. Se **reporta qué se aplicó y qué se saltó, y por qué**. Un informe sin
   respuesta a "qué hiciste con lo que te dijeron" no cierra nada.

## Lo que solo hace una persona

La máquina mide; la persona ve. Una vez, la pieza se mira **a velocidad real
y con sonido**: en un móvil, con el brillo de una calle, con el audio de la
plataforma. Ahí se oyen las cosas que ninguna métrica ve (un golpe que cansa,
una voz que no se entiende, un texto que se lee pero cansa).

---

→ Canónico: `references/rubrica-premios.md` · Dominio: qa · Vecinos: `references/qa-entrega.md`, `references/checklist-qa.md`, `references/auto-qa.md`, `references/rubrica-premios.md`
