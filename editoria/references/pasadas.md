# Pasadas de refinamiento — mejorar sin romper

Una pasada es un refinamiento con alcance: se nombra qué se toca, se evalúa, se
mueve lo mínimo que hace falta y se verifica mirando el frame. Sirven cuando el
usuario (o la crítica de `auto-qa.md`) pide «más audaz», «más calmo», «está
cargado», «se ve barato», o cuando una pieza ya funciona y hay que llevarla al
listón. `direccion.md` traduce una nota vaga a palancas («Feedback vago →
palancas concretas»); esta guía dice cómo ejecutar cada palanca sin tocar lo que
no se pidió.

Destilado de los comandos de refinamiento de Impeccable (pbakaus, Apache 2.0),
reescrito para video; las cifras y curvas viven en sus guías canónicas y aquí
solo se enlazan.

## Reglas comunes

1. **El alcance es soberano.** «Todo lo demás se queda» es una instrucción
   literal: se toca solo lo nombrado (una escena, un tramo, un eje). No se
   restilan los vecinos, no se añaden colores, tipografías ni primitivas que el
   sistema (`SISTEMA.md`, el brand pack) no tenga. Si el sistema no puede
   expresar lo pedido, se nombra la adición exacta y se pregunta.
2. **Refinar conserva, rediseñar reemplaza** (`direccion-de-arte.md`). Si el
   concepto es el que falla, se dice y se propone rediseñar; no se esconde un
   rediseño dentro de un pulido.
3. **Una pasada, un eje.** Mezclar ejes (color, ritmo y texto a la vez) impide
   saber qué mejoró. Orden si hay que encadenar: idea → jerarquía → composición →
   tipografía → imagen → color → detalle → movimiento (`auto-qa.md`).
4. **Se verifica con el frame y el audio**, a los tamaños de entrega y en lote:
   corregir lo que una mirada muestra antes de mirar de nuevo, no un render por
   cada retoque. Los detectores (`auto_qa.py`, `auditar_plan.py`,
   `medir_animacion.py`) son evidencia de defectos, no prueba de calidad.
5. **Cada pasada deja rastro**: qué se cambió y por qué en `PROGRESO.md`; si el
   hallazgo es repetible y verificado, `registrar_aprendizaje.py`.
6. **Termina con el diff limpio**: ningún render intermedio ni archivo
   temporal junto a los entregables; los cambios accidentales se revierten.

## Más audaz

*Cuando la pieza es segura, plana o anónima. El reflejo de «más efectos» es lo contrario de audaz.*

- **Por qué se lee plano**: casi siempre una escena opta por no usar los movimientos más fuertes que sus vecinas ya usan (la tipografía a escala plena, el dispositivo que carga el significado, el motivo firma, la densidad y el ritmo). La pasada más fiable sube el objetivo al nivel expresivo que el resto de la pieza ya alcanza, **en el vocabulario del propio sistema**.
- **Movimientos**: amplificar lo que el sistema ya posee (su motivo, su escala tipográfica a pleno) en vez de inventar; **comprometerse con UN movimiento decisivo y callar lo de alrededor** para que se lea (si todo se vuelve más fuerte, la escena queda más plana); darle su propio ritmo (que sea un pico respecto a lo que la rodea, no más de lo mismo); mantener el contenido verdadero (no se añaden claims).
- **Prueba del esqueleto**: quitar mentalmente el texto y mirar la estructura desnuda. ¿Dice qué es la escena y por qué importa solo con jerarquía y recursos del sistema? Si solo funciona con las palabras, la audacia está en el tamaño del texto, no en el diseño.
- **Verificar**: lo de fuera del alcance no cambió; no apareció color, fuente o primitiva nueva; es inconfundiblemente la misma marca, pero más segura de sí misma.

## Más calmo

*Cuando la pieza abruma, grita o cansa. Calmo no es genérico: la contención necesita punto de vista.*

- **Fuentes de intensidad**: saturación, contrastes extremos, peso visual (muchos elementos pesados), exceso de movimiento, complejidad, escala (todo grande y ruidoso sin jerarquía).
- **Movimientos**: bajar la saturación al 70-85 %; dejar que los neutros trabajen y el color sea acento (regla del 10 %); grises con matiz en vez de gris puro; **nunca gris sobre color** (tinta derivada del campo); pesos 900 → 600 y 700 → 500 mirando el frame comprimido; quitar degradados, halos y sombras que no sirven; distancias de entrada más cortas (10-20 px en vez de 40 px) y curva de salida suave sin rebote (`animacion.md`); menos saltos de escala; más aire.
- **Evitar**: igualar todo en tamaño y peso (la jerarquía sigue importando), quitar todo el color (calmo ≠ gris), eliminar la personalidad, volverlo todo pequeño y ligero (hace falta algún ancla).
- **Verificar**: ¿sigue siendo distintivo?, ¿se lee mejor durante más tiempo?, ¿el punto de vista sobrevive a los recortes? Con el tono `trailer`/`caos` el brief puede pedir lo contrario: manda el brief.

## Destilar

*Cuando hay demasiado: elementos, variantes, texto, pasos.*

- **Esencia**: ¿cuál es la UNA cosa que la pieza debe lograr? ¿qué es el 20 % que da el 80 % del valor? ¿qué se puede quitar, combinar o contar después?
- **Movimientos**: una acción principal (el CTA), el resto terciario o fuera; quitar la redundancia (si el titular ya dice el estado, la línea de apoyo aporta algo nuevo o desaparece; ni encabezados que repiten la intro ni explicaciones repetidas); **recortar cada frase a la mitad y volver a hacerlo**; voz activa y sustantivos específicos; 1-2 colores más neutros; una familia tipográfica con 3-4 tamaños; quitar contenedores que el espacio reemplaza; **sin tarjetas dentro de tarjetas**; quitar un paso del flujo si se puede; si algo se saca de la pieza, anotar por qué.
- **Evitar**: quitar lo necesario para decidir, sacrificar accesibilidad (subtítulos, contraste), volverlo tan simple que no se entienda (misterio no es minimalismo), eliminar toda la jerarquía.
- **Verificar**: ¿se entiende más rápido?, ¿la jerarquía es más clara?, ¿sigue completa para lo que el espectador necesita?

## Pulir

*La pasada final antes de entregar. Es refinamiento, nunca un rediseño escondido.*

- **Establecer el sistema**: leer `SISTEMA.md` y el brand pack. Clasificar cada desvío antes de arreglarlo: **token faltante** (el sistema necesita un valor reutilizable), **implementación suelta** (un componente existente debería reemplazarla), **desajuste conceptual** (el flujo o la jerarquía difiere de piezas comparables de la serie) o **defecto local**. Arreglar la causa al nivel correcto más estrecho.
- **Triage**: 1) lo roto o engañoso (dato falso, texto cortado, audio que pisa); 2) estados que faltan (frame 0 terminado, final que se sostiene, silencios); 3) flujo, jerarquía y deriva del sistema; 4) incoherencias visuales y de movimiento; 5) limpieza. No perfeccionar una esquina y dejar el resto bajo el mismo listón.
- **Recorrer la pieza entera**: composición y zona segura en cada formato de entrega; tipografía consistente por rol; contraste en cada estado; marca exacta (color muestreado, logo sin deformar); terminología y mayúsculas coherentes; cifras con el formato del idioma (`numeros` del plan).
- **Verificar**: `checklist-qa.md` completo, `auto_qa.py` limpio **y** el sheet visto, `delivery_check.py` PASS, la rúbrica de `rubrica-premios.md`.

## Animar

*Cuando falta vida o continuidad. El movimiento explica estado, relación y jerarquía, o crea un momento que la pieza se ganó; decoración sin propósito es deuda de animación.*

- **Encontrar el trabajo**: solo donde el movimiento hace legible un cambio, preserva la continuidad entre planos, dirige la atención a un momento que importa o encarna el mundo elegido. No se anima un área estática solo porque existe.
- **Tesis de movimiento**, por escrito antes de tocar nada: el **momento focal** (la secuencia que merece autoría, si la hay), la **continuidad** (qué cambios necesitan explicación), el **feedback** (qué eventos piden confirmación visual o sonora) y el **presupuesto** (qué efectos pueden ser caros y cuántas veces corren). El momento focal sale del sujeto, no de un fade-and-rise genérico.
- **Material por significado**: continuidad y relación → movimiento espacial deliberado, morphs de un elemento; foco y profundidad → desenfoque o luz acotados; revelado y composición → máscaras y recortes; energía → color, textura, distorsión; estado → el cambio más pequeño que haga inequívoca la causa. No apilar técnicas por espectáculo: una idea material fuerte, llevada por la secuencia focal, y el resto callado.
- **Tiempo**: expresa distancia y consecuencia. Salida más rápida que entrada (~70 %). Curvas y duraciones canónicas en `animacion.md` y la tabla de personalidad en `fluidez.md`. La escalonada se usa cuando una lista aparece como lista; nunca se reinterpreta cada escena como lista escalonada.
- **Cuidado del espectador**: respetar fotosensibilidad (`auto_qa.py`) y movimiento de cámara brusco; un bucle no esencial debe poder verse completo sin cansar.
- **Verificar**: ¿el momento focal es específico de esta pieza?, ¿cada animación de apoyo explica estado o relación?, ¿quitar una animación perdería significado o carácter, y no solo decoración?

## Tipografía

*Cuando la jerarquía de texto no se lee o el texto se rompe.*

- **Dos evaluaciones aisladas**: primero la mirada (roles, jerarquía, escala, lectura, estrés con textos largos), después la medición (`medir_animacion.py`: letra mínima asentada ≥ 26 px sobre 1080). La medición no puede anclar el juicio.
- **Fijar el sistema** antes de editar: los roles que la pieza necesita (titular, apoyo, etiqueta, cifra, subtítulo), el contraste entre ellos y qué familias y pesos son autoridad. Menos roles y familias que hagan inequívoca la jerarquía; tamaño, peso, espacio y tono juntos, no solo tamaño.
- **Saltos de línea**: autorarlos entre frases, nunca dejar una palabra huérfana en la última línea, revisarlos en cada formato (9:16 y 16:9 rompen distinto); un salto desigual puede significar (una palabra sola para dar peso), pero es raro y se declara. Subtítulos: máx. 2 líneas y ≤ 42 caracteres por línea (`sonido.md`).
- **Tinta clara sobre oscuro** se ve más gruesa y en H.264 los pesos finos vibran: ajustar interlineado (+5 %) y tracking (+0.01 em) y decidir el peso mirando el frame ya comprimido, no la fuente suelta.
- **Estrés**: nombres largos, números con separadores del idioma, traducciones que se expanden (el español suele ocupar ~15-30 % más que el inglés). `fuente_que_cabe` encoge: una cifra que se encogió mucho ya no es titular, hay que recortar el texto.
- **Verificar**: los roles se distinguen sin leer el texto; los textos largos caben en ambos formatos; la tipografía pertenece al sistema.

## Color

*Cuando el color no jerarquiza ni significa, o sobra.*

- **Roles, no una bolsa de muestras**: lienzo y superficies, tinta y apoyo, acento, estados y categorías de datos. Nombrar la estrategia antes de editar: temperatura emocional, relación dominante, rango de contraste, dosis de color. Puede ser contenida o inmersiva; la decide el brief y la dirección.
- **Aplicar a escala de sistema**: que el color más fuerte posea una región deliberada en vez de acentos diminutos; no gastar el color de la acción en decoración; tinta secundaria derivada del matiz del campo, no un gris lavado; en datos, **el color nunca es el único código** (etiqueta, forma o posición además); en lienzo oscuro, la elevación se diseña con escalones de tono, no invirtiendo mecánicamente un tema claro.
- **Verificar**: contraste real sobre el frame (texto ≥ 4.5:1, texto grande y acentos ≥ 3:1; `python scripts/direccion_arte.py verificar pack.json`), también sobre fotos y en cada estado; ¿la atención cae en la acción o el dato?; ¿es reconociblemente esta pieza y no un «colorido» genérico?

## Composición

*Cuando la jerarquía o el espacio fallan.*

- **Prueba de entrecerrar los ojos**: con el detalle difuminado, ¿se distinguen lo principal, lo secundario y los grupos mayores, en orden? Muchas masas pequeñas parecidas = todo es mediano y nada lidera.
- **Agrupar por proximidad antes de añadir contenedores**; ritmo = contraste deliberado entre intervalos apretados y generosos (más espacio sobre un titular que bajo él); un sistema de espaciado documentado (en el motor, `unidad()`), no valores sueltos.
- **Estructura según el contenido y la prioridad**, no según el default del framework: ¿las escenas repetidas son equivalentes de verdad o solo la plantilla?
- **Adaptación estructural**: 9:16, 16:9, 1:1 y 4:5 son composiciones distintas (`coherencia-espacial.md`, zona segura por plataforma en `auto_qa.py --safe`), no un reescalado.
- **Extremos**: texto largo, datos vacíos, cifras de muchos dígitos, escenas con elementos que entran tarde.
- **Verificar**: lo principal, secundario y grupos se leen en orden en cada formato; ningún hueco accidental; ningún solape.

## Deleitar

*Personalidad en los momentos que se la ganan; no una capa de ocurrencias.*

- **Una tesis de deleite en una frase**: qué debe sentir el espectador y por qué eso pertenece a esta pieza. Luego el sistema más pequeño que lo entregue: una respuesta distintiva a un momento que importa, lenguaje del propio sujeto que aclara a la vez que da voz, una transición con comportamiento material reconocible, un detalle sonoro o ambiental del mundo del sujeto.
- **Momentos que lo merecen**: un logro (un resultado, una cifra que llega), una espera que puede informar, un cierre. No se fabrica una celebración para un clic ordinario; la intensidad es proporcional a la frecuencia y la consecuencia.
- **No debe**: retrasar o tapar lo principal, añadir claims no pedidos, ocupar sonido sin el permiso del brief ni agotarse a la segunda vista. Con dinero, privacidad o pérdida, calidez sí, chistes no.
- **Verificar**: ¿otra marca podría usar este momento tal cual? Si sí, no es de esta pieza.

## Ir más allá

*La pasada con más riesgo de fallar: nunca se ejecuta de golpe.*

1. **Proponer antes de construir**: pensar 2-3 direcciones distintas (técnica, ambición, estética) y describir de cada una cómo se vería y cuánto cuesta (tiempo de render, riesgo, dependencias).
2. **Pedir al usuario que elija** antes de producir nada; las direcciones y sus costos van dentro de la propia pregunta para que elija entre cosas que puede leer.
3. Construir solo la elegida, con degradación elegante (si el efecto falla, la pieza sigue siendo buena sin él) y sin tirones ni pops medidos (`medir_animacion.py`), también en un equipo medio.
- «Extraordinario» depende del sujeto: una partícula en un portafolio impresiona; la misma partícula en una pieza institucional es un error. Un solo momento extraordinario por pieza: dos compiten y producen ruido.
- **Nunca** usar la ambición técnica para tapar fundamentos débiles: se arreglan primero con las demás pasadas.
- **Pruebas**: la del asombro (¿alguien que no la vio reacciona?), la de quitarlo (¿alguien lo extraña o nadie lo nota?), la de dispositivos (¿sigue fluida en teléfono?) y la de contexto (¿tiene sentido para esta marca y este público?).

## Aclarar el texto

*Cuando el texto en pantalla o la voz no se entienden a la primera.*

- **Auditar el lenguaje leyendo la pieza entera**, no frases sueltas: sustantivos y verbos ambiguos, jerga interna, etiquetas vagas, falta de consecuencia o de plazo, terminología y mayúsculas inconsistentes, repeticiones (titular + intro + apoyo + confirmación diciendo lo mismo), texto que se rompe a anchos reales o al traducir, tono ciego al riesgo o la urgencia.
- **Jerarquía del mensaje** por plano: el único dato que el espectador necesita ahora, la acción siguiente, el contexto que cambia la decisión y el tono apropiado. Cada idea se dice una vez.
- **Reescribir por función**: acciones con verbo y objeto específicos («Reserva una mesa», no «Haz clic aquí»), el mismo sustantivo y verbo para el mismo concepto en toda la pieza; cifras con el sustantivo y la unidad reales; el CTA con un solo nombre en toda la pieza; errores o límites con qué falló y qué alternativa queda, sin prometer causas que no se conocen.
- **Cuidado**: se pregunta antes de cambiar afirmaciones factuales, sentido legal o un término técnico del dominio. Traducible: mensajes completos, no fragmentos concatenados; permitir que el texto se expanda.
- **Verificar**: se entiende sin conocimiento oculto del producto, se puede actuar en cada decisión, es lo más corto posible sin perder sentido.

## Blindar (casos límite)

*Antes de producir en serie, de variar con datos (`--datos`) o de entregar a alguien más.*

- **Texto**: nombres de 100+ caracteres, cifras de muchos dígitos, palabras largas del español, emoji (no se dibujan: `auditar_plan.py` los avisa), CJK o RTL si el público lo exige; una escena que encoge hasta dejar de ser legible falla aunque no se corte.
- **Datos**: lista vacía, un solo elemento, 50 elementos, valores cero o negativos, porcentajes que no suman 100.
- **Plantilla × tabla** (`--datos`): placeholders `{columna}` que fallan en voz alta, una fila de prueba (`--fila N`) con el caso más largo y el más corto.
- **Entorno**: sin API key (degradar a entrega silenciosa y avisar), sin ASR local, sin ffmpeg con un códec.
- **Reanudación**: interrumpir el render a la mitad y re-ejecutar sin `--force`.
- **Verificar**: lo anterior con evidencia (frame o salida), no con un «sí».

## Adaptar (formatos y plataformas)

*Pasar una pieza a otro formato, duración o plataforma. La trampa es escalar; el trabajo es repensar la pieza para el contexto nuevo.*

- **Identificar** el contexto de origen y de destino: formato (9:16, 1:1, 4:5, 16:9), plataforma y su UI (zona segura, pantalla final de YouTube), duración, cómo se ve (teléfono en la mano, sin sonido), qué espera el público ahí.
- **Qué no cabe, qué no funciona, qué es inapropiado**: del 16:9 al 9:16 no se recorta, se recompone (`ffmpeg_tools/verticalizar.py` para footage; `render_plan.py` con `tamano` para planes); del largo al corto se eligen los momentos fuertes (`scoring-shorts.md`) y se reordena el argumento, no se acelera.
- **Contenido**: más corto y más grande en el formato pequeño; progresión por planos en vez de todo a la vez; el sonido que se entiende en mudo (subtítulos que importan).
- **Verificar**: `delivery_check.py` contra la plataforma de destino, y el mosaico (`contact_sheet.py`) de cada formato mirado por separado.
