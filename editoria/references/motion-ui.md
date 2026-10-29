# Motion UI — detalle interno de gestos de interfaz (Zajno destilado)

**No es un catálogo paralelo.** La elección del agente es
`scripts/repertorio.py` (misma superficie que las escenas y los overlays).
Este documento y `scripts/data/motion_ui.json` son el **detalle de producción**
cuando la opción resuelta tiene `motor=gesto`.

Fuente: [motion.zajno.com](https://motion.zajno.com/) (Zajno Digital Studio,
Motion.ED). Guía educativa de técnicas de animación de interfaz — no repo de
código ni look de película. Aquí no se copian demos ajenas: se destilan las
**ocho técnicas**, con números y con el motor EditorIA que las sirve.

Ante conflicto: el brand pack fija identidad, `fluidez.md` fija el motor de
resortes, `animacion.md` fija el oficio, y el catálogo único decide *qué*
opción; **este documento** solo concreta *cómo* producir el gesto.

## 0. Para qué se mueve la interfaz (antes de la técnica)

Zajno agrupa el movimiento de UI en cinco empleos. Si no puedes nombrar
cuál, el movimiento sobra (`animacion.md` §1, staging):

| empleo | en la pieza significa | técnica que lo carga |
|---|---|---|
| **Atención** | el ojo va al detalle que importa | delay/offset, scale pop, spotlight |
| **Mood de marca** | el ritmo transmite el carácter (fitness = pump; estudio = calma) | easing + densidad de stagger |
| **Invitar a explorar** | se intuye cómo se usa (slider, cards, scroll) | dimension, parallax, hint de gesto |
| **Guiar el ojo** | de un elemento clave al siguiente | fade+posición, zoom continuo, morph |
| **Desplegar información** | lo complejo se revela en capas, no de golpe | delay en cascada, mask reveal, parallax |

## 1. Las ocho técnicas → motor EditorIA

Cada fila: **firma** (cómo se reconoce), **números** (para no inventar),
**dónde se pide** en esta skill. Un video, una técnica dominante; como
máximo un acento técnico de otra fila (`estilos-codigo.md` tiene la misma
regla para looks).

| # | técnica | firma | números / receta | motor EditorIA |
|---|---|---|---|---|
| 1 | **Easing** | nunca lineal: acelera al salir, frena al llegar | Entrada: `ease_out` / rol `MOVIMIENTO`. Viaje largo: `ease_in_out`. Aterrizaje con peso: rol `pop` o `bloque`. Prohibido lineal salvo UI de cursor preciso (`demo`) | Plan (`entra`, §3b de `animacion.md`); HyperFrames/Remotion con las mismas curvas |
| 2 | **Offset & delay** | varios objetos no llegan a la vez: hay viscosidad y jerarquía | Stagger **40–90 ms** entre hermanos; contenedor → contenido **+60–120 ms**; salida más rápida (60–70 % de la entrada). En el plan: `at` distintos por elemento | Plan (`at.item0..n`, `at.p1[]`); HyperFrames `animation-delay` |
| 3 | **Fade in / out** | aparece/desaparece por alfa, casi siempre **combinado** con posición o escala | Solo-alfa: apoyos. Alfa+Y (elevación `ELEV` ≈ 30 px) o alfa+scale: protagonistas. Varios a la vez → sumar delay. Salida cruzada: desde el corte, 0,32 s sobre la entrante (`capa_salida`, `SOLAPE`) | Plan (entrada con fade+resorte, `capa_salida`); HyperFrames opacity |
| 4 | **Transform & morph** | un objeto se convierte en otro y arrastra la atención entre pantallas | Mismo nº de vértices / first-vertex alineado; puente A→cápsula→B en **8–12 frames** por tramo; squash 10–15 % en el instante. Continuidad narrativa > efecto | **HyperFrames** (MorphSVG/flubber) o **Remotion**. El plan no morphéa paths: usa transiciones `mancha`/`iris`/`dissolve` o zoom de `demo`/`kenburns` |
| 5 | **Masking** | la forma actúa de máscara; la foto/texto se mueve **dentro** | Reveal de texto por clip (máscara horizontal); foto en contenedor con pan/scale interno 3–8 %; nunca “aparece” el bitmap entero de golpe | Plan: revelado tipográfico (`animacion.md` §6), `text_reveal`. Foto-en-máscara con pan: **HyperFrames** o `kenburns` dentro de caja |
| 6 | **Dimension** (floating) | sensación de volumen / espacio sin pasar a 3D full | Push-in de cámara 6 % (`EMPUJE`, a lo largo de la escena); capas a distinta velocidad; objetos que se alejan (scale↓ + Y); cards que se hojean. Un movimiento de cámara por plano | Plan: global `camara`, escena `camino`, `medianoche` (teléfono 3D), push-in de `final`/`componer`. 3D real → `3d.md` overlay |
| 7 | **Parallax** | capas en X/Y: lo lejano se mueve menos | Fondo 0,2× · medio 0,5× · foco 1× · primer plano 1,4× del desplazamiento de cámara. No mezclar con otro movimiento de cámara en el mismo plano | Plan: receta de `animacion.md` §5; `kenburns` + overlay. Interactivo (mouse): solo HyperFrames/web, no el motor de planes |
| 8 | **Zoom** | continuidad entre “páginas” / destinos; profundidad | Zoom de escena 1,00→1,08 (contemplación) o foco de `demo` ≤2×; transición zoom entre planos = un solo viaje de cámara, no un corte. Span orbital de producto → 3D o HyperFrames | Plan: `camara`, `kenburns`, `demo` (zoom al clic). Continuidad multipágina → HyperFrames o Remotion |

## 2. Cómo se pide (vía el catálogo único)

1. `python scripts/repertorio.py sugerir --pedido "landing suave / cards que se expanden / cascada"`.
2. `repertorio.py resolver --id offset-delay` (u otra opción `motor=gesto`).
3. Una técnica dominante (+ acento opcional). Se declara en el tratamiento.
4. Producir con el motor de la fila (§1 / JSON). Si falta Node
   (HyperFrames/Remotion), se declara (`capacidades.md`) — no fade lineal.
5. En plan: parametriza la escena con `at` y roles `MOVIMIENTO`. No inventes
   un tipo `morph` en `SCENES`.
6. Verificar: preview · `medir_animacion.py` · puerta.

Frases típicas → técnica (también las resuelve `sugerir --pedido`):

| el usuario dice | técnica dominante |
|---|---|
| “que no entre todo a la vez / más suave / con viscosidad” | offset & delay |
| “que se sienta vivo, no robótico” | easing (roles `MOVIMIENTO`) |
| “aparición limpia / se va sin corte duro” | fade (+ posición) |
| “esta tarjeta se convierte en la captura” | transform & morph (HyperFrames) |
| “el texto sale de una línea / la foto vive en la forma” | masking |
| “quiero profundidad / espacio / que flote” | dimension |
| “capas, el fondo se mueve menos” | parallax |
| “un solo viaje, no páginas sueltas / zoom al detalle” | zoom |

## 3. Qué NO se trae de Zajno

- Las demos de Dribbble enlazadas en el sitio: son ajenas; sirven de
  ilustración, no de asset.
- Cursos y fuentes del pie de `motion.zajno.com`: ya hay oficio propio en
  `animacion.md` / `fluidez.md`; no se duplica el índice de cursos.
- Interactividad *real-time* (hover, mouse parallax): el motor de planes
  es video determinista `f(t)`. Si el entregable es un sitio, HyperFrames
  o fuera de scope — se declara.
- Sustituir o duplicar el catálogo de elección: los gestos **ya están** en
  `repertorio.py`; esto solo **compone** el gesto; no añade tipos a `SCENES`
  ni abre un menú paralelo.

## 4. Relación con el resto del mapa

| ya existe | qué aporta este detalle |
|---|---|
| `repertorio.py` | la **elección**; aquí números y motor de producción del gesto |
| `animacion.md` §1–§5 | oficio + curvas + cámara |
| `fluidez.md` | física del resorte; aquí cuándo escalonar / fundir / zoom |
| `estilos-codigo.md` | looks de película; aquí técnicas de **interfaz** |
| `intencion-escena.md` | índice del catálogo único |
| `hyperframes.md` / `remotion.md` | morph, mask foto, parallax interactivo |

---

→ Canónico: `references/animacion.md` · Dominio: movimiento · Vecinos: `references/fluidez.md`, `references/estilos-codigo.md`, `references/hyperframes.md`, `references/intencion-escena.md`
