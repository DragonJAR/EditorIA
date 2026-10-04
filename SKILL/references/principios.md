# Principios permanentes

Todo video de EditorIA se juzga contra estos tres pilares. No son aspiraciones:
son reglas documentadas y verificables en el QA. El listón: digno de un
festival de cine — cada frame intencional, nada decorativo, nada accidental.

> **Marca**: los pilares son universales. Los valores concretos (qué color,
> qué tipografía, qué idioma de transición) los fija el **brand pack**
> (`brand/*.json`, ver `references/brand-packs.md`); sin pack, los elige el
> agente en modo libre según el brief. `brand/dragonjar.json` es el ejemplo.

## 1. Coherencia visual
- Un solo color de acento en todo el video (del brand pack, o el elegido en
  modo libre). El acento marca lo importante, lo nuevo y la cifra; reservado
  (~10% del plano como máximo). El resto: neutros.
- Un solo sistema tipográfico: una familia para titulares, una para texto,
  una monoespaciada para kickers/datos. Kickers siempre en mayúsculas con
  letterspacing. (Ej. pack DragonJAR: Plus Jakarta Sans / Montserrat.)
- Un solo sistema de componentes: badges, píldoras, tarjetas con radio
  consistente, iconografía geométrica simple. No mezclar estilos dentro del
  mismo video.
- Nombres propios y cifras verificados contra la fuente. Cero confabulación.

## 2. Armonía espacial
- Retícula vertical consistente entre bloques: el rótulo/titular va a la misma
  altura en todas las escenas (en el motor de planes: y=H*0.20; en composición
  libre la fija el style pack). Un rótulo que salta de altura entre escenas
  rompe el ritmo. La visualización ocupa la banda inferior con aire arriba y
  abajo; el caption cierra abajo.
- Márgenes laterales consistentes: centrado, o x en múltiplos de la retícula.
- Jerarquía estricta: kicker → titular → visualización → caption. Nada compite con el titular.
- Prohibido solapar elementos que comunican (ej. teléfono sobre el título: se detectó
  en QA del v2 y se corrigió moviendo el teléfono a y=940).
- Ritmo de respiración: 0,5–1 s de "aire" entre la salida de un bloque y la entrada del siguiente.

## 3. Efectos especiales deslumbrantes y acordes
- El fondo animado (ondas, aurora, partículas) es el *escenario*: continuo, sutil,
  en tonos profundos del acento. Nunca compite con el contenido.
- Entradas: fade + elevación 50px en 0,45s. Salidas: fade 0,35s.
- Revelados secuenciales para datos que se cuentan: grilla celda por celda (0,12s),
  filas que aparecen en cascada (0,3s), barras, providers.
- Regla de oro: **el efecto presenta información, no decora**. Si un efecto no ayuda
  a entender el dato, se quita. Deslumbrante = riqueza de motion con propósito,
  no pirotecnia gratuita.

## El listón
Cada entrega debe aspirar a ser **el mejor video jamás creado sobre el tema**:
dato verificado, ortografía perfecta, cada frame se sostiene solo, y el QA
(`checklist-qa.md`) se cumple sin excepciones antes de entregar.

## Gusto (taste)

Principios de restricción.

**Restar antes de sumar**: preferir menos objetos más fuertes a muchos
detalles decorativos. Un detalle solo es válido si mejora comprensión,
jerarquía, estado, señal de marca o ritmo de lectura. Cuando la escena se
siente genérica, primero fortalecer el sujeto focal, el espaciado, la
tipografía y los roles de color; los efectos van después de que la composición
se sostenga.

**Chrome budget = 0**: tarjetas, bordes, contenedores y divisores que el
espacio blanco y la alineación podrían reemplazar, se quitan. Una superficie
de fondo, un tratamiento de divisores (una hairline de un color, entre
columnas iguales). La jerarquía se lleva con escala, peso, brillo y
espaciado, no con chrome.

**Roles de color**: un neutro dominante, un color primario, un acento. Cada
saturado debe enseñar algo (marca, estado, categoría, comparación, foco).
Nada de arcoíris decorativos.

**Movimiento con economía**: solo el elemento focal lleva la personalidad
fuerte (overshoot, snap); el soporte usa easing calmo. Si el movimiento hace
la escena ocupada o desenfocada, simplificar la composición antes de añadir
más movimiento. Los efectos nunca compensan un layout débil.

**Saturación: dinámico ≠ lleno** (doctrina de Jaime, 2026-10-03):
dinámico no es meter muchos elementos en la pantalla. Dinámico es que los
pocos elementos presentes estén vivos, armoniosos y coherentes entre sí.
- **Un protagonista por plano**: cada escena tiene UN elemento focal; todo lo
  demás apoya o sale. Si dos elementos compiten por la atención, uno sobra.
- **Presupuesto de elementos**: titular + protagonista + máximo 2 apoyos por
  escena. Lo que no enseña algo, no va.
- **Isotipo con rol**: si el plano ya tiene un protagonista grande, el isotipo
  no entra (no compite con él). Si el isotipo aparece, aparece con función y
  recurre en otros momentos de la pieza con el mismo rol — coherencia de uso,
  no decoración suelta.
- **Aire**: ningún frame debe sentirse lleno. Ante la duda, quitar antes que
  sumar (ver "Restar antes de sumar").

**Coreografía tipográfica**: texto de apoyo tranquilo, palabra activa con el
motion fuerte; cada palabra con su propio timing (no keyframes idénticos en
toda la frase); easing y espaciado semánticos (palabras duras golpean, suaves
asientan); el orden de lectura se preserva.

**Frames como check mínimo**: el frame 0, el punto medio y el frame final se
evalúan como composiciones fijas. Si el final no se sostiene solo como
imagen, la escena no está lista.

**Leyes creativas** (doctrina de `/brag`, adaptada):

- **El hook es todo.** Los primeros 2 segundos deciden si alguien sigue viendo.
  El hook se planea antes que todo lo demás — es la primera decisión del guion.
- **Cada frame postable.** Cualquier frame congelado debería valer la pena
  compartirlo. Nada de frames de relleno.
- **Línea de grounding.** Lo que el video *afirma* (nombres, cifras, capacidades,
  citas, copy del tema) sale de la fuente o se marca `[PENDIENTE]` — recortado
  o dividido en elementos vale; inventado no. Lo que el video *inventa* (tono,
  encuadre, chistes, transiciones, narración conectora) es oficio y es libre.
  Si una línea deseada no tiene grounding, la corrección es citar lo que la
  fuente sí dice — casi siempre es más extraño y mejor que lo inventado.

**Anti-PPT** (tabla violación→arreglo):

| Violación | Arreglo |
|---|---|
| Bullet list estática | Un icono por concepto, entrando en cascada |
| El promo explica con párrafos | El promo declara: un golpe por shot |
| Fondo que cambia sin motivo | Fondo con ≥2 capas; cambios solo con trigger visible |
| Transiciones mezcladas sin criterio | Un solo idioma de transición por pieza (ver `tecnicas-video.md`); la variedad viene del contenido, no de apilar efectos |
| Plano fijo mientras se narra otra cosa | Plano hacia el elemento que narra (wide ↔ medium ↔ close-up) |

Atención en orden: frase → objeto → detalle. Nunca al revés.
