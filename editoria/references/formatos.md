# Formatos — qué sostiene cada tipo de pieza

Un **formato** es una relación de pieza entera que se repite: quién carga el
argumento, cómo se mueve la atención y qué revelación o payoff la sostiene.
No es una categoría que el plan deba declarar: una pieza puede combinar
varios o inventar uno. Leer el formato cuya relación aparece en el brief o en
la referencia (`references/referencia-video.md`); el oficio local vive en
sus referencias (subtítulos en `references/video-real.md`, sonido en
`references/sonido.md`, ritmo en `references/ritmo.md`).

Destilado de los playbooks de formato de Hypit (hypit-ai/hypit), traducido
a material grabado o animado con las herramientas de EditorIA (Hypit los
orienta a generar video con modelos; aquí la toma la pone el usuario o el
motor de escenas).

## Talking head / UGC — una persona le habla al espectador

- **La actitud carga la pieza**; subtítulos, prueba y gráficas solo ayudan a
  seguirla. Elegir tomas por energía, dicción y mirada (`references/video-real.md`).
- **Cortes naturales son parte del resultado**: jump-cuts de pausa
  (`scripts/ffmpeg_tools/silence.py`, `scripts/retakes.py`) se leen como un
  creador que editó su grabación, no como un defecto. Un pequeño cambio de
  pose entre pasajes está bien; la misma cara congelada en cada costura no.
- **Voz y gráficas hacen trabajos distintos**: el número exacto va en
  gráfica o subtítulo; la mano hace un gesto legible. El B-roll cubre la
  imagen y la voz SIGUE sonando debajo.
- Dejar espacio en el encuadre para lo que vendrá (el ícono a un lado, el
  tablero abajo) al reencuadrar (`scripts/ffmpeg_tools/verticalizar.py`).

## Podcast de dos — la relación entre dos personas carga el argumento

- Una pregunta invita una afirmación, una reacción cambia su sentido, una
  respuesta la paga. **Cortar hacia quien importa ahora**, no por reloj: la
  reacción que cambia el sentido merece su plano.
- **Apertura con los dos a la vez**: pantalla dividida
  (`scripts/ffmpeg_tools/montaje.py dividir host_a.mp4 host_b.mp4`) presenta
  la pareja antes de que termine la primera pregunta; luego planos individuales.
- **Subtítulos con color por hablante** (`caption.py --hablantes
  "ANA=FFD400,LUIS=4FC3F7"`): siguen identificando quién habla incluso con
  B-roll a pantalla completa. Elegir colores para ESTA pareja, en armonía
  con la paleta.
- **La cobertura sigue un pensamiento, no cada sustantivo**: un montaje de
  B-roll sobre toda la idea, con tiempo para terminar a velocidad nativa;
  la voz del otro puede entrar antes de que vuelva su imagen (J-cut,
  `references/tecnicas-video.md`).
- La utilería tiene dueño legible: si alguien pasa el producto, los planos
  siguientes lo reflejan.

## Entrevista callejera — un encuentro con alguien que tiene su propia vida

- **El invitado carga la historia**; el entrevistador ayuda a descubrirla.
  Respuestas → plano del invitado; pregunta neutra → plano compartido;
  incredulidad o un desafío importante → plano del entrevistador.
- **Un antes y un después**: abrir con el invitado ocupado en algo
  plausible y cerrar cuando empieza a irse; implican vida fuera del clip.
- **Una revelación es UN evento en varias capas**: la gráfica que se
  revela, el SFX (`scripts/sfx.py`) y el destello de color comparten el mismo
  instante de la palabra (mismo `at` en el plan, anclado con
  `scripts/alinear.py`). Así, si cambia la entrega, todo sigue cayendo junto.
  Las respuestas previas quedan visibles; las futuras, como incógnita.
- Subtítulo del invitado con su color y el del entrevistador neutro.

## Ranking y listicle — un tablero cuyo estado cambia con el argumento

- **El tablero recuerda los juicios previos** mientras la voz explica el
  siguiente. Decidir qué está ya establecido al abrir (estado inicial) y qué
  se decide ahora (activación en la palabra del veredicto): escena `ranking`
  o `versus` con `at` por ítem (`references/escenas.md`).
- **Componer persona y argumento juntos**: presentador a un lado, ícono del
  sujeto activo al otro, tablero abajo; un tablero que sigue entendible
  aunque entren y salgan inserts.
- **Cada imagen tiene su rol de información**: el ícono IDENTIFICA al sujeto
  (exacto, recortado y legible al tamaño final); el B-roll INTERPRETA el
  chiste o la comparación con su propio lenguaje visual.
- Si el tablero ya suena al moverse, no duplicar el golpe con otra pista.

## Explainer con presentador — actuación + demostraciones que evolucionan

- **Los objetos que persisten son la memoria del argumento**: dos
  alternativas siguen en pantalla mientras se examina cada una y cambian su
  relación cuando aparece la tercera. Importan su entrada, su movimiento,
  su estado asentado y su salida.
- **El presentador cambia de presencia sin cortar su voz**: pantalla
  completa → ventana (`scripts/ffmpeg_tools/montaje.py pip`) → cubierto por
  la demostración → vuelve para la reacción. Lo motiva el evento del guion,
  no el reloj; el corte, el movimiento o el fundido siguen el ritmo de la pieza.
- Simplificar sin vaciar: quitar un título redundante cambia el layout; una
  carpeta sigue necesitando contenido legible; una terminal, actividad.

## Narración — una voz independiente organiza imágenes, manos, pantallas o gráficas

- **Un solo hilo de voz, muchas respuestas visuales**: un ángulo nuevo, un
  estado de pantalla o una revelación son respuestas DENTRO de la misma
  narración, no razones para cortarla.
- Cada imagen se elige por lo que aporta: **contexto** (quién, dónde),
  **prueba** (la afirmación hecha visible por uso, resultado o comparación),
  **B-roll** (acción, objeto, contrapunto), **pantalla** (detalle literal que
  importa), **gráfica** (estructura, acumulación, transformación).
- **Evidencia, no ilustración de sustantivos**: una imagen genérica por cada
  palabra produce actividad sin prueba.
- Todo tramo tiene una imagen deliberada (sin bordes heredados ni vacíos);
  la música y los efectos unen cortes mientras la voz se entiende.
- El subtítulo es la voz; pasos, cifras, rótulos y CTA son tipografía propia.

## Drama corto — personajes, deseos y consecuencias

- Cada pasaje tiene un **trabajo dramático**: alguien quiere algo, otro
  cambia su sentido, una acción tiene una consecuencia, una revelación
  cambia lo que el espectador entiende (`references/dramaturgia.md`).
- El fondo cuenta: intimidad, estatus, por qué están juntos, un objeto
  plantado. Planos del mismo lugar comparten atmósfera y paleta pero cada
  cámara ve su parte.
- Revisar por **causalidad**: el espectador sabe quién actúa, qué cambió y
  por qué sigue el plano siguiente.

## Videoclip y lyric video — la música manda la dirección

- **Primero el audio**: `scripts/beat_grid.py cancion.mp3 --json grid.json`
  da BPM, compases y `secciones` por energía (intro, subida, pico, valle,
  outro). Cada sección recibe su lenguaje visual en `TRATAMIENTO.md` y la
  intensidad crece con la energía de la pista; el clímax visual va en el
  pico, no al principio.
- **No todo beat pide un corte ni todo momento un efecto**: la sección
  sugiere `cortes_cada_beats` (8 en lo bajo, 4 en lo medio, 2 en lo alto);
  los efectos se reservan para los golpes que marcan la sección.
  `"musica"` en el plan lleva entradas al medio beat y cortes al «uno»
  (`references/plan-video.md`); `scripts/beat_sync.py` hace lo mismo con un EDL.
- **La tipografía es parte de la composición**, no un subtítulo encima:
  tipografía cinética de las escenas (`typewriter`, `apertura`, `remate`) y
  `references/animacion.md`; los subtítulos de `caption.py` son para el habla.
- **La letra nunca se inventa**: se usa la letra que da el usuario y se
  alinea contra la voz cantada (`scripts/alinear.py cancion.mp3 letra.txt`);
  si no se puede identificar con confianza, va `[PENDIENTE]` y se pregunta.
  El canto engaña al ASR más que el habla: verificar el timing de la letra
  contra la voz en un mosaico (`scripts/contact_sheet.py --palabras`).
- **Transiciones antes que efectos**: pulir primero la continuidad entre
  secciones (`references/fluidez.md`); un efecto no salva un corte malo.
- **Revisar la pista completa**: un buen arranque no arregla un medio
  repetitivo ni un final sin cerrar. Mosaico por sección con
  `contact_sheet.py --inicio/--fin`, `scripts/auto_qa.py` (parpadeo,
  fotosensibilidad), consistencia de tipografía y estilo entre secciones,
  jerarquía visual, y la apertura y el cierre juzgados por separado.
- Material de terceros solo con permiso; las referencias se estudian.

## Charla vertical con gráficas kinetic (estilo DragonJAR / referente Notepad++)

Pieza vertical (9:16) donde **la tipografía carga el argumento** y el
footage del orador, si existe, es una ventana: no el plano entero. El
referente típico (`El hackeo a Notepad++`) es un stage HTML 720×1280 con
ventana de talking-head, karaoke con cajas y paneles inferiores; al
entregar, se escala a 1080×1920 salvo que el brief pida otra cosa.

**Sistemas del referente → qué ya sabe la skill (no reinventar):**

| Sistema del referente | Dónde vive en EditorIA |
|---|---|
| Palabra a palabra + caja roja/blanca (`\|r`/`\|b`) | Escena `frase` y titulares (`apertura`/`remate`/`pildoras`) con `~clave~` / `^clave^` (`segmentos_resalte`) |
| Subrayado de la palabra activa | `frase` (barra de acento bajo la activa) |
| Lower-third (barra roja + nombre + rol) | `rotulo_inferior` |
| Hook apilado (kicker mono + titular + caja) | `apertura` / `frase` / `pildoras` con el markup de cajas |
| Panel inferior (kicker + tarjetas / nodos) | `hoy`, `bento`, `versus`, `pildoras`, `canales` |
| Sello a sangre («SIN CONTRATO») | `frase` o titular con `~SELLO~` a pantalla; hold corto |
| Cierre CTA (título + caja + botón) | `final` (+ `boton`); el lema puede llevar `*…*` |
| Tipografía sobre footage con profundidad | `scripts/ffmpeg_tools/componer.py` (`references/modos-produccion.md`) |
| Karaoke quemado sobre el corte | `caption.py --karaoke` (resalte de color; las cajas de bloque son de `frase`/titular) |

**Reglas al clonar este estilo:**

1. **Leer el pack antes que el referente.** Si `reglas.rejillas_decorativas`
   es `false` (DragonJAR), el fondo de puntos del referente **no** se copia:
   el pack manda (`references/brand-packs.md`).
2. **Sin footage del orador** → motor de plan solo-texto (dirección
   `solo_texto`): `frase` + paneles + `final`. No inventar un talking-head.
3. **Con footage** → híbrido: ventana/`pip` + overlays con alfa
   (`rotulo_inferior`, sellos) + `frase` o captions; ensamblar con
   `componer.py` / `montaje.py` (`references/modos-produccion.md`).
4. **No inventar claims.** Servicios y cifras solo si constan en el pack,
   el brief o una fuente citada; si no, declarar el supuesto en
   `BRIEF.md` / `no_aplica`.
5. Rotar repertorio frente a la pieza anterior
   (`repertorio.py sugerir --anterior`).

## Combinar formatos

Un UGC puede cargar un ranking; un podcast, una revelación de entrevista;
una narración, un pasaje con presentador. Escribir en el `TRATAMIENTO.md`
del proyecto (`scripts/proyecto.py`) qué relación organiza cada pasaje:
eso decide cómo se juzga la actuación, la cobertura y la prueba en la
revisión.

---

→ Canónico: `references/formatos.md` · Dominio: produccion · Vecinos: `references/modos-rapidos.md`, `references/dramaturgia.md`, `references/prompt-motion-graphics.md`
