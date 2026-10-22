# Dirección de arte — decisiones en lugar de defaults

Una pieza hecha por un modelo tiende a parecerse al promedio de todo lo que el
modelo ha visto: un titular centrado sobre tres tarjetas con icono, un
degradado suave, un rótulo en mono sobre cada título. Nada de eso está mal y
nada de eso fue decidido. Este documento sustituye defaults por decisiones, de
cuatro maneras:

1. **Se reparten direcciones y se elige entre ellas.** Si se le pide a un
   modelo que invente un look, elige siempre el default de su categoría.
   `scripts/direccion_arte.py` reparte unas pocas direcciones de una biblioteca;
   el agente elige la que pueda llevar algo que solo este sujeto tiene y la
   adopta sin mezclarla con el layout de siempre.
2. **La idea sale del sujeto**, no del estilo. Lo que separa una pieza memorable
   de una olvidable es un concepto tomado de la cosa misma.
3. **Un registro de «tells»** (más abajo), medible en parte con
   `scripts/auditar_plan.py`: lo que hace que algo se lea como generado.
4. **Se mira lo que se hizo**: crítica por pasadas (`references/auto-qa.md`) y
   refinamiento con alcance (`references/pasadas.md`).

Método destilado de tasteskill (Leonxlnx, MIT), Impeccable (pbakaus, Apache 2.0)
y UI/UX Pro Max (nextlevelbuilder, MIT), reescrito para video con las
herramientas de EditorIA. **El brief manda; el brand pack manda sobre la
dirección; la dirección manda sobre el gusto del agente.** Una estética que el
usuario fijó se respeta aunque aquí aparezca como «tell»: redirigir un brief
claro hacia el gusto propio es un fallo.

## El orden de trabajo

1. **Brief** (entrevista corta, abajo) → `BRIEF.md` (`scripts/proyecto.py`).
2. **Inventario del sujeto**: 8-12 cosas que son de este cliente y de ningún
   competidor. Su nombre y lo que significa; sus cifras (asientos, minutos,
   precio, año); la restricción con la que vive (un lote al mes, cerrado en
   invierno); sus materiales y colores; sus rituales y horarios; lo impreso de
   su mundo (un horario, una etiqueta, un ticket). De aquí sale la idea (paso 5)
   y también la búsqueda de imágenes: cada lugar, material u objeto de la lista
   es una consulta.
3. **El argumento**: la pieza como afirmaciones con su prueba, una línea por
   escena («Es un taburete de roble hecho por encargo → el taburete, grande»).
   Una escena sin afirmación es relleno: se borra. Así se evita el orden de
   plantilla (gancho, logos, tres funciones, testimonio, precio, CTA): el orden
   de la pieza es el orden del argumento.
4. **Modo** de la pieza (abajo) y **dirección**:
   `python scripts/direccion_arte.py repartir --brief "..." --sector S --tono T --modo M --tiene fotos capturas`
   reparte tres; se elige una; `elegir ID --out CARPETA` escribe `SISTEMA.md` y,
   si el motor la compone, `estilo.json` (usable con `--brand`).
5. **La idea** (abajo). No se construye hasta llenar los dos huecos.
6. **Plan y guion**: el guion se escribe completo antes del plan
   (`references/plan-video.md`); `auditar_plan.py` antes de renderizar.
7. **Mirar y refinar**: `references/auto-qa.md` (pasadas) y `references/pasadas.md`.

## Entrevista corta del brief

Cuando el pedido es vago, decidir y declarar la lectura en una línea en lugar de
preguntar; preguntar solo cuando falta un hecho que bloquea (el nombre del
producto, el idioma, el presupuesto).

- **Cadencia**: dos o tres preguntas relacionadas por ronda, una ronda por
  defecto; una segunda solo si las respuestas abren un hueco material. Nunca un
  cuestionario, nunca repetir lo ya resuelto, nunca convertir lo obvio en un
  menú: afirma la lectura más probable e invita a corregirla.
- **Ronda 1**: ¿para qué es la pieza y qué problema resuelve? ¿quién la ve, en
  qué situación y con qué ánimo? ¿qué debe entender o hacer, y cómo se vería el
  éxito? ¿qué es verdad aquí que un vecino genérico no podría afirmar?
- **Ronda 2 (solo si hace falta)**: ¿qué contenido, evidencia y assets reales
  existen (mínimo, típico, máximo)? ¿qué fidelidad y alcance se espera
  (borrador, pieza final, serie)? ¿qué no debe tocarse? ¿qué restricciones de
  plataforma, duración, idioma o presupuesto son vinculantes?
- No se pregunta por valores de color ni por «estilos»: eso es del agente. Se
  pregunta por verdades que solo el usuario conoce.
- El resultado es un `BRIEF.md` de la menor extensión útil: trabajo y público,
  resultado y prueba, alcance y límites, hechos que no pueden fallar.

## Modo de la pieza

El modo nombra cómo se ve el éxito del espectador y escala la ambición. Se
elige por lo que la pieza pide, no por el producto (el anuncio de una
herramienta de edición sigue siendo persuadir). No sustituye al **tono**
(`references/tonos.md`: energía, voz, ritmo): el tono es cómo suena; el modo,
para qué sirve.

| Modo | Éxito del espectador | Ambición y cuidado |
|---|---|---|
| **Persuadir** | decide y actúa (anuncio, lanzamiento, campaña) | compromiso total: punto de vista claro, un momento firma, material real; la dirección elegida se lleva hasta el final |
| **Explicar** | entiende algo (resumen, tutorial, explainer, informe) | estructura para la comprensión primero; una idea por escena, el piso de lectura de `ritmo.md` y la prueba de silencio; la ambición se muestra como precisión |
| **Demostrar** | ve el producto o proceso hacer su trabajo | la acción real de punta a punta, datos que suman, cursor y cámara que siguen el trabajo; la marca vive en los detalles exactos |
| **Experiencia** | está dentro de la obra (film, showreel, videoclip, portafolio) | el material lidera desde el primer plano y la interfaz se retira; música y silencio como recursos |

## La idea

La dirección es una manera de componer; la idea es lo que hace que la pieza
pertenezca a este sujeto y a ningún otro. Antes de construir, completar:

> En este video, **[algo que pertenece al sujeto]** se convierte en **[el dispositivo que pide la dirección]**.

Dónde buscar el primer hueco:

- **Su producción**: ¿qué produce la cosa? Poner la salida real en pantalla como material (una cámara que imprime poemas entrega su texto como tiras de papel).
- **Su objeto o forma**: cómo se ve en corte o en silueta. Agrandarla, recortarla, hacerla marco o motivo único.
- **Su nombre**: ¿las letras pueden contener una foto, apilarse como muro, partirse a dos esquinas?
- **Su lugar**: ¿hay una vista que hace querer estar ahí?
- **Su ritual**: ¿hay una secuencia que la pieza pueda ejecutar?
- **Su artefacto**: ¿qué objeto impreso ya existe en su mundo? Ticket, menú, etiqueta, recibo, invitación, manual.
- **Su opuesto**: ¿qué otra categoría posee el sentimiento que a esta le falta?

**Prueba del competidor**: poner el nombre del competidor más cercano en la
frase. Si todavía funciona, la idea es de la categoría («una hogaza es todo
panadero»; las siete puertas de la calle que da nombre a esta panadería solo son
de esta). «Limpio y moderno» no es una idea. Lo mismo vale para cada escena:
**cubre el logo**: ¿podría ser de otra marca cambiando el nombre y el sustantivo
del titular? Entonces no tiene idea. Y después: ¿llega la idea al precio, al
cierre y a los créditos, o la pieza se vuelve bloques de stock tras el primer
plano? Lo más común, incluso en buenas piezas, es un gancho distintivo seguido
de plantilla.

El **momento firma** (`references/direccion.md`) sale de la idea: lo que alguien
describiría una hora después.

## Material: orden de preferencia

Se planea con las imágenes que de verdad existen, no con las que se desearía
tener (`direccion_arte.py --tiene fotos footage capturas` reparte solo lo que se
puede cumplir). Orden de preferencia para cada hueco de imagen:

1. **El material propio del cliente** (sus fotos, su producto, su interfaz real, su proceso). Si existe, el primer plano lo muestra grande.
2. **Imágenes generadas**, si hay una herramienta para ello y el brief las permite.
3. **Imágenes reales del mundo del sujeto en archivos abiertos** (su calle en postales antiguas, un mapa del barrio, su material de cerca, su oficio en grabados, un objeto de museo de su especie), usadas grandes y con intención, solo con licencias que permiten uso comercial, registrando fuente y licencia y poniendo el crédito pequeño al cierre. Una imagen de archivo muestra el mundo alrededor del cliente: **nunca se presenta como su producto, su sala, su plato, su persona o su equipo**.
4. **Dibujado en código desde el sujeto** para lo que no existe una imagen honesta (sus objetos, sus azulejos, la interfaz de su producto), en un solo lenguaje gráfico plano con los colores reales de la paleta.
5. **Solo tipografía y color** (`solo_texto`): la respuesta honesta cuando nada de lo anterior es verdad.

Nunca se escribe en el plano una frase sobre de dónde vienen las imágenes ni
lo que *no* muestran («ninguna de estas es nuestro local»): un pie dice qué es
la imagen y el crédito va pequeño al final. Una pieza con material real
(fotos, tomas, archivo) y un movimiento propio de ese material se lee como
terminada junto a otra hecha solo de dibujos o de texto.

## Refinar conserva, rediseñar reemplaza

- **Refinar** (más audaz, más calmo, pulir...) conserva la identidad, el
  comportamiento, el copy y todo lo que está fuera del alcance. Preguntar antes
  de reemplazar copy factual o añadir afirmaciones.
- **Rediseñar** conserva la verdad del producto, el contenido y las
  restricciones, y trata el look anterior como evidencia y antireferencia: elige
  un mundo nuevo y reescribe `SISTEMA.md`. Nunca partir la diferencia con un
  pulido sobre el look descartado.
- La evidencia visual es autoridad, no un nombre de archivo: sin `SISTEMA.md`
  no hay necesariamente un proyecto nuevo; se documenta la identidad que ya hay
  antes de inventar otra.
- Símbolos cargados (militarismo, supremacismo, odio) no se usan como motivo ni
  adorno aunque el mundo del sujeto los roce: se busca la forma neutra de ese
  mundo. Lo que documenta un símbolo como hecho, se queda como está.

## Tells — el registro fechado

Un tell es un recurso que hace que una pieza se lea como generada. Casi todos
empezaron como buenas ideas en buenas piezas y se volvieron tells al producirse
por defecto, en todas partes, sin razón. Por eso el registro está **fechado
(2026-10)** y **nunca nombra una tipografía, un color o un componente de
reemplazo**: toda lista «usa esto en su lugar» se ha convertido en la siguiente
ola de tells en meses. Los reemplazos son procedimientos (repartir de la
biblioteca, derivar del sujeto), no productos.

`Código` = el aviso de `scripts/auditar_plan.py`; «ojo» = solo se ve mirando el
frame. Todo es **AVISO** (una excepción deliberada es legítima): se declara en
`SISTEMA.md` y en `"tells_ok": ["codigo"]` del plan. Con brand pack o dirección
elegida que lo declare, vale.

### Texto

| Tell | Código | En su lugar |
|---|---|---|
| Verbos y adjetivos de la categoría: desbloquea, revoluciona, sin esfuerzo, todo en uno, de vanguardia, world-class... | `jerga` | el sustantivo específico y la cifra real («se entrega en una semana», no «entrega rápida») |
| La corrección: «no es solo X, es Y», «No es una herramienta. Es un equipo.» | `correccion` | decir lo que es, una vez |
| Titular que es una oración larga (más de ~42 caracteres) | `titular-largo` | un título de 4-6 palabras; el resto, a una línea de apoyo |
| Emoji o glifo como icono (en video salen como tofu o inconsistentes) | `emoji` | letras en `icono`, o una forma dibujada |
| Numeración por costumbre: «Paso 01», «01 /» | `numeracion` | el orden lo da la posición o las palabras |
| Prueba social inventada: «10.000+ clientes», citas sin autor, logos de relleno | `prueba-inventada` | prueba real o ninguna; la cifra con `fuente` o `[PENDIENTE]` |
| Placeholders y `[PENDIENTE]` sin resolver | `placeholder` | resolver desde la fuente antes del render |
| El tricolon de adjetivos abstractos («Rápido. Simple. Seguro.») | ojo | los statements paralelos de `direccion.md` están bien con palabras específicas del sujeto; el tell es el trío genérico |
| Una frase que narra el diseño («un layout limpio y moderno para...») | ojo | decir lo que muestra el plano |

### Estructura de la pieza

| Tell | Código | En su lugar |
|---|---|---|
| La misma escena tres veces seguidas | `escena-repetida` | alternar la familia de composición según el argumento |
| Cadencia de metrónomo: todas las escenas duran casi lo mismo | `cadencia-uniforme` | variar duraciones (`ritmo.md`: CV ≥ 0.25) |
| Rótulo (kicker) sobre casi cada escena | `rotulo-en-todas` | reservarlo a donde aporta. *Nota*: `principios.md` usa el kicker como parte de la jerarquía y el pack puede fijarlo como firma; el tell es el reflejo en cada plano, no su uso deliberado |
| Orden de plantilla: gancho, logos, tres funciones, testimonio, precio, CTA | ojo | el orden del argumento |
| Tres tarjetas iguales con icono, título y texto como estructura | ojo | la composición de la dirección elegida; «tres» solo si el contenido tiene tres |
| La plantilla héroe-métrica: número enorme, etiqueta pequeña, stats de apoyo, acento | ojo | una cifra con su prueba y un solo apoyo |
| Todo centrado, todo con el mismo peso | ojo | un ancla a la izquierda y un solo momento centrado |
| Tarjetas dentro de tarjetas | ojo | espacio, escala y tono (`principios.md`: chrome budget 0) |

### Superficie y color

| Tell | En su lugar |
|---|---|
| Degradados violeta/índigo; texto con degradado | color plano de la dirección; la tinta es tinta |
| Cristal o desenfoque como adorno (no como efecto específico) | superficie opaca un escalón sobre el lienzo |
| Resplandor o halo de neón alrededor de un elemento | profundidad por escalón de tono; una sombra con desplazamiento y desenfoque, no un halo sin desplazamiento |
| Sombra suave bajo cada tarjeta; sombra dura desplazada fuera de un mundo neobrutalista | tono o sin caja |
| Borde lateral de color de más de 1 px en tarjetas, listas o avisos | quitarlo |
| Crema amarillenta con terracota; negro con un neón y brillo | la paleta repartida; la calidez sale de una piedra de baja saturación, una tinta profunda, una foto o un campo cálido pleno |
| El acento en diez sitios | menos del 10 % del plano: la acción y un detalle |
| Gris sobre un campo de color | la tinta del campo, o el matiz del propio campo |
| Mono como disfraz de «técnico» | mono para datos y medidas; en una dirección HUD, como firma y con tope por plano |
| Máscaras geométricas que imitan el contorno de un sujeto fotográfico | un recorte real (matte) o ninguna máscara |
| Un solo radio medio (12-16 px) en todo | cuadrado o redondo, elegido una vez |
| Nueve tamaños de letra casi iguales | cinco como máximo, muy separados |

### Movimiento, imagen y sonido

| Tell | En su lugar |
|---|---|
| La misma entrada (fade y subida) en cada bloque | un momento firma y coreografía por escena: una lista entra fila a fila, una cifra cuenta, una frase se arma por líneas |
| Rebote o elástico por reflejo | exponencial de salida (`animacion.md`); overshoot solo en el elemento focal |
| Bucles que no significan nada | movimiento que explica estado o relación |
| Dashboard de relleno hecho con barras grises y donas | un fragmento real de interfaz o ninguna imagen |
| Stock genérico de sonrisas | material propio, de archivo con crédito o dibujado desde el sujeto |
| La misma música genérica de fondo en todas las piezas | `references/sonido.md`: sound brief antes de generar |
| SFX en cada beat sin diseño | un sonido por evento que lo merece (`sfx.md`) |

### Quitar no basta

Una pieza con todos los tells quitados y nada puesto en su lugar es una pieza
vacía con buenos modales, y eso también es un tell («estética de evitación»:
cualquiera la adivinaría con la categoría más la lista de lo prohibido). Los
tells llenaban un hueco donde debía haber una idea. Por eso el orden de trabajo
empieza por la idea del sujeto, la dirección repartida y el material real; los
chequeos van al final. tasteskill lo comprobó con páginas web en pruebas
ciegas: una página rica con recursos de plantilla le ganó siempre a una limpia
pero delgada. El mismo riesgo existe en video: el paso de *sustancia* de
`auto-qa.md` está para que la pieza no pierda contenido al perder tells.

## Dónde sigue

- Crítica de lo renderizado: `references/auto-qa.md` (pasadas) y `references/rubrica-premios.md` (topes).
- Refinar con alcance: `references/pasadas.md`.
- Estilos y style packs: `references/estilos.md`; transiciones y personalidad de
  movimiento: `references/fluidez.md`; tonos: `references/tonos.md`.
- Qué escena para qué dato: `references/escenas.md` (tabla al final).
