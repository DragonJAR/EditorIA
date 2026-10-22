# Rúbrica de premios — el gate antes de entregar

Una pieza no se entrega por estar "bien". Se entrega cuando un jurado de
motion design o un festival de cortos la tomaría en serio. Esta rúbrica
convierte ese listón en una puntuación verificable. La aplica el agente
sobre el render final (frames mirados, audio escuchado), no sobre el plan.

## Cómo puntuar

Ocho ejes, de 1 a 5. **Gate de entrega: ningún eje por debajo de 4 y media
≥ 4.3.** Si no pasa, se nombra el eje que falla, se corrige la causa y se
vuelve a renderizar. Con el usuario se comparte la tabla en una línea por
eje solo si la pide o si algo no se pudo resolver.

| # | Eje | 5 — premio | 3 — correcto (no basta) | 1 — amateur |
|---|---|---|---|---|
| 1 | **Idea y hook** | Una sola idea fuerte; los primeros 2 s obligan a seguir mirando | Se entiende, pero el arranque es genérico | Sin idea central; arranca con logo o relleno |
| 2 | **Dramaturgia** | Arco completo (marco → tensión → giro → resonancia); el final recontextualiza el inicio | Hay orden, pero sin tensión ni giro | Lista de cosas sin arco |
| 3 | **Animación** | Los 12 principios aplicados (`animacion.md`); motion blur en la entrega; overlapping y arcos; nada se detiene en seco | Resortes y easing correctos, pero todo entra igual | Fades lineales, apariciones de golpe |
| 4 | **Composición y tipografía** | Cada frame congelado es un póster; un foco por plano; zona segura respetada; jerarquía impecable | Ordenado pero plano; algún frame lleno | Solapes, texto cortado, tamaños arbitrarios |

El eje 4 se mide con el motor (`scripts/puntuar.py` con `--plan`): letra real
en reposo, factor de la zona segura y solapes. **El piso de letra (26 px) es
una regla dura**: si el texto no se lee en un teléfono, el eje 4 no puede
llegar a 4 aunque el resto de la composición sea impecable. Es la misma regla
que hace fallar la puerta de entrega (`scripts/qa_entrega.py`), con la misma
medición: las dos no pueden decir cosas distintas.
| 5 | **Sistema visual** | Una paleta, una familia de curvas, un idioma de transición y un momento firma memorable | Coherente, sin momento firma | Estilos mezclados |
| 6 | **Sonido** | Música con intención, cada golpe visual con su sonido, silencio usado como recurso; mezcla medida (LUFS y true peak en spec) | Música de fondo correcta, sin diseño sonoro | Música genérica, picos, voz tapada |
| 7 | **Verdad y marca** | Cero confabulación; marca con fidelidad total (o modo libre con identidad propia y consistente) | Algún texto genérico o claim sin fuente marcado `[PENDIENTE]` | Claims inventados o logo deformado |
| 8 | **Acabado técnico** | `auto_qa.py` limpio, `delivery_check.py` PASS, sin bandas, grano y dither, entrega en spec | Pasa QA con avisos menores | Frames negros, clipping, formato erróneo |

## Preguntas de jurado (respóndelas antes de puntuar)

1. ¿Cuál es la **una** cosa que alguien recordará mañana? Si no hay
   respuesta, el eje 5 no pasa de 3.
2. Sin audio, ¿se entiende la historia? Sin imagen, ¿el audio tiene arco?
3. Congela 5 frames al azar: ¿los publicarías? (eje 4)
4. ¿Hay algún movimiento que exista solo "para que se mueva"? Quítalo.
5. ¿El final se sostiene quieto 1–2 s como imagen de cierre?

## Topes (anulan la aritmética)

Un tope fija el máximo de un eje por mucho que lo demás brille. Se aplica el
menor. Se anotan en la crítica (`auto-qa.md`). Es el mecanismo que impide que
una pieza con un defecto visible compense con otros ejes.

| Si pasa esto | Tope |
|---|---|
| `auto_qa.py` con un defecto sin descartar, o `delivery_check.py` en FAIL | eje 8 ≤ 2 |
| Emoji convertido en tofu, texto cortado o fuera de la zona segura, banda o clipping visible | eje 8 ≤ 3 |
| Placeholder visible (caja gris, «Imagen aquí», lorem, `[PENDIENTE]`) | eje 7 ≤ 2 |
| Cifra o claim sin fuente que se pasó por verificado | eje 7 ≤ 3 |
| La pasada 3 de `auto-qa.md` falla (podría ser de cualquiera) o la idea pasa la prueba del competidor | eje 1 ≤ 3 |
| Sin momento firma (pregunta de jurado 1 sin respuesta) | eje 5 ≤ 3 |
| Todas las entradas son la misma, o hay movimiento que solo existe para moverse | eje 3 ≤ 3 |
| Algo pisa un titular o una cifra en algún instante | eje 4 ≤ 2 |
| Dos o más planos casi vacíos (suelo muerto), texto pequeño y gris, márgenes desiguales o un hueco accidental | eje 4 ≤ 3 |
| Sin material real del sujeto (solo dibujos o stock genérico) cuando el brief lo permitía | eje 4 ≤ 3 |

**Calibración**: un 5 es raro. Si la primera nota que el agente se pone a su
propia obra es 5 en casi todo, la vuelve a puntuar como el jurado que no la
construyó, con los topes delante.

## Lo que la rúbrica no negocia

- Un 5 en animación no compensa un 2 en verdad (eje 7): sin grounding no
  se entrega.
- El gate se aplica también a piezas rápidas (`modos-rapidos.md`); lo
  único que cambia es la ambición del eje 2 (una tarjeta cinética no
  necesita arco de fábula, pero sí intención y remate).
- Honestidad sobre límites (`dramaturgia.md`): si el brief pide algo que
  EditorIA no puede llevar a 4 (actuación de personajes, lip-sync), se dice
  antes de producir y se propone la alternativa que sí puede.

---

→ Canónico: `references/qa-entrega.md` · Dominio: qa · Vecinos: `references/checklist-qa.md`, `references/auto-qa.md`, `references/direccion.md`
