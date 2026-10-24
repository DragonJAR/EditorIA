# Mapa de EditorIA — el índice de la skill

61 referencias, 45 scripts, 19 herramientas de ffmpeg y 42 suites de tests. Este
archivo dice **dónde está cada cosa**, **cuál es la fuente canónica** de cada
idea y **por dónde se entra** según la tarea. Sin este mapa, la skill es un
archivo con piezas sueltas; con el mapa, es un sistema.

Cada referencia lleva al pie a quién pertenece y a sus vecinos:

```
→ Canónico: `references/animacion.md` · Dominio: movimiento · Vecinos: ...
```

Navegar es entonces siempre en los dos sentidos: de cualquier archivo a su
canónico, y del canónico a sus hermanos. `scripts/auditar_mapa.py` verifica
estas tres cosas en cada corrida: que todo sea alcanzable desde `SKILL.md`,
que todo pie apunte a archivos que existen, y que el mapa y los pies no se
contradigan.

## 1. Los dominios y su fuente canónica

| dominio | canónico | qué resuelve | cuándo lo lees |
|---|---|---|---|
| **movimiento** | `animacion.md` | los 12 principios, overshoot medido, curvas, coreografía, cámara, tipografía en movimiento | siempre que algo se mueva |
| **estructura** | `principios.md` | la idea, el arco, la dirección, el tono, los lenguajes visuales | antes de escribir el guion |
| **plan** | `plan-video.md` | el schema de `plan.json`, el bloque `datos`, los límites del motor | al escribir el plan |
| **escenas** | `escenas.md` | el catálogo de 39 tipos de escena y sus parámetros | al elegir escena |
| **sonido** | `sonido.md` | voz, música y SFX; el ritmo musical vive en `audio.md`, la capa de efectos en `sfx.md` | al mezclar |
| **copy** | `copy.md` | el texto en pantalla, la aritmética del rótulo, la prueba sin inventarla | al escribir el copy |
| **qa** | `qa-entrega.md` | la puerta de entrega; el loop y sus causas en `auto-qa.md`, la lista humana en `checklist-qa.md`, el gate de premios en `rubrica-premios.md` | antes de entregar |
| **marca** | `brand-packs.md` | cómo se declara una identidad y cómo se aplica a una pieza | cuando hay marca |
| **color** | `paleta.md` | el catálogo de paletas del modo libre y cómo elegir una según el brief | antes de renderizar, si no hay marca |
| **produccion** | `formatos.md` | qué sostiene cada tipo de pieza y los workflows para hacerlas | al elegir el formato |
| **operacion** | `instalacion.md` | instalar, el contrato de las CLIs, los idiomas, el protocolo de mejora | al arrancar o al mantener |
| **herramienta** | `capacidades.md` | con qué cuenta la skill, qué capacidades externas puede necesitar la pieza (3D, Remotion, HyperFrames, trazos a mano) y qué hay que instalar si faltan | al arrancar, y en cuanto una pieza las pida |
| **indice** | `mapa.md` | este índice: dónde está cada cosa y por dónde se entra | cuando no sepas dónde está algo |
| **vocabulario** | `glosario.md` | qué significa cada palabra propia de la skill | cuando una instrucción usa jerga |

## 2. Rutas de lectura por tarea

- **"quiero CREAR un video"** → Step 1-5 de `SKILL.md` (entorno, memoria del
  proyecto, plan, render, audio, puerta) → `formatos.md` (qué formato) →
  `principios.md` (la idea) → `copy.md` (el texto) → `intencion-escena.md` (qué
  escena) → `plan-video.md` (el schema) → `qa-entrega.md` (la puerta).
- **"quiero EDITAR un video que ya tengo"** → Step 6 o 7 de `SKILL.md` →
  `video-real.md` (el oficio de la edicion) → `montaje.md` (las 19 operaciones)
  → `ritmo.md` (el encadenamiento) → `qa-entrega.md`.
- **"no entiendo esta instruccion"** → `glosario.md` (la palabra) → `escenas.md` (la escena)
  → `plan-video.md` (el parámetro).
- **"¿esta pieza está lista?"** → `qa-entrega.md` (defectos) → `puntuar.py` (los ocho
  ejes de la rúbrica) → `rubrica-premios.md` (el listón).
- **"quiero clonar este video"** → `referencia-video.md` → `formatos.md` → `copy.md` →
  `qa-entrega.md`.
- **"tengo un video grabado"** → `video-real.md` → `modos-produccion.md` → `montaje.md` →
  `qa-entrega.md`.
- **"necesito un resumen de una reunion"** → `scoring-shorts.md` (elegir los momentos) →
  `estilos.md` (el lenguaje visual) → `qa-entrega.md`. El pipeline v2 con scripts
  propios (`pipeline-resumen.md`) es legacy: para piezas nuevas va el motor.
- **"quiero VOZ en off, música o sonido"** → `sonido.md` (la voz, la música y los
  efectos) → `audio.md` (el ensamblado y la mezcla, con el ducking) →
  `plan-video.md` (el campo `voz` de cada escena) → `qa-entrega.md` (la puerta).
  Es el camino del Step 4 cuando la pieza se está haciendo, y el de los
  pasos 3 y 6 cuando el sonido se le añade a una que ya existe.
- **"el video no se siente bien"** → `qa-entrega.md` (que falla) → `auto-qa.md` (la causa) →
  `fluidez.md` (el motor) → `ritmo.md` (el encadenamiento) → `copy.md` (el texto).
- **"quiero un thumbnail"** → `thumbnails.md` → `checklist-qa.md`.
- **"mi marca"** → `brand-packs.md` → `principios.md` → `copy.md`.
- **"sin marca"** → `paleta.md` (se elige una paleta según el brief) → `principios.md`.
- **"un video hecho con IA"** → `recetas-ai-video.md` → `prompt-motion-graphics.md` →
  `modos-produccion.md` → `qa-entrega.md`.
- **"se me descuadra el tiempo"** → `ritmo.md` → `sonido.md` (el timing de la voz) →
  `audio.md` (el beat grid).

**Las cuatro verticales, como dato y no como prosa.** La skill sirve para
cuatro cosas, y estan declaradas en `scripts/data/verticales.json` para que
no se puedan quedar viejas en silencio (en la prosa, una lista se queda
vieja y nadie dice "falta la del sonido"): **crear y animar**, **editar**,
**clonar y resumir**, y **el sonido** (voz, música, efectos). El guard
(`scripts/auditar_mapa.py`) comprueba en cada corrida que cada vertical
tiene su ruta de lectura (la de arriba), acaba en la puerta, llega a
herramientas que **alguien ejecuta de verdad** (según el censo), y que lo
que no se puede medir lo lleva con su motivo **al lado** (un motivo sin
escribir es un tapón).

## 3. El mapa completo

| archivo | qué resuelve | dominio |
|---|---|---|
| `mapa.md` | este índice | indice |
| `glosario.md` | el vocabulario de la skill: qué es cada palabra propia | vocabulario |
| `principios.md` | los principios permanentes (3 pilares, el gusto, la marca) | estructura |
| `dramaturgia.md` | el arco: marco, tensión, giro, resonancia | estructura |
| `direccion.md` | el listón medido, los 10 patrones, la dirección de energía | estructura |
| `direccion-de-arte.md` | la dirección de arte: la idea del sujeto, las direcciones repartidas, el registro de tells | estructura |
| `tonos.md` | la energía creativa de la pieza | estructura |
| `estilos.md` | los lenguajes visuales aprendidos | estructura |
| `scene-patterns-from-internet.md` | patrones de escena validados | estructura |
| `plan-video.md` | el schema de `plan.json` y el bloque `datos` | plan |
| `arquitectura.md` | cómo encaja la skill por dentro | plan |
| `shorts-plan-schema.md` | el contrato de `shorts-plan.json` | plan |
| `media-hard-rules.md` | las reglas duras del media-tooling | plan |
| `escenas.md` | el catálogo de 39 tipos de escena | escenas |
| `escenas-extendidas.md` | los conceptos portables del catálogo | escenas |
| `animacion.md` | los 12 principios del movimiento | movimiento |
| `fluidez.md` | el motor: resortes, continuidad, ritmo, personalidad | movimiento |
| `reglas-tecnicas.md` | las reglas duras y los problemas ya resueltos | movimiento |
| `coherencia-espacial.md` | dónde se compone: zona segura, alineación, solapes | movimiento |
| `intencion-escena.md` | el índice inverso: intención → escena → receta | movimiento |
| `ritmo.md` | el ritmo y el encadenamiento (anti-slideshow) | movimiento |
| `tecnicas-video.md` | el catálogo de técnicas 2025-2026 | movimiento |
| `sonido.md` | voz, música y SFX | sonido |
| `audio.md` | el ritmo musical: beat grid, anchors, compases | sonido |
| `sfx.md` | la capa de efectos de sonido | sonido |
| `copy.md` | el texto que decide si un video se lee como diseñado | copy |
| `share-copy.md` | el texto que acompaña al video al publicarlo | copy |
| `qa-entrega.md` | la puerta de entrega: seis comprobaciones con plan (tres sin), un veredicto | qa |
| `auto-qa.md` | el loop de ver, detectar y corregir | qa |
| `checklist-qa.md` | la lista de verificación humana | qa |
| `pasadas.md` | las pasadas de refinamiento: corregir lo nombrado, sin tocar el resto | qa |
| `rubrica-premios.md` | el gate de premios: los 8 ejes | qa |
| `brand-packs.md` | cómo se declara y se aplica una identidad | marca |
| `formatos.md` | qué sostiene cada tipo de pieza | produccion |
| `modos-produccion.md` | real, animado e híbrido | produccion |
| `modos-rapidos.md` | recetas para piezas simples | produccion |
| `prompt-motion-graphics.md` | la biblioteca de prompts | produccion |
| `recetas-ai-video.md` | video con IA por código | produccion |
| `cine.md` | films de marca | produccion |
| `video-real.md` | editar grabaciones con personas | produccion |
| `pipeline-resumen.md` | el pipeline del resumen animado | produccion |
| `tecnicas-reutilizables.md` | analizar un video que ya existe | produccion |
| `scoring-shorts.md` | elegir los momentos fuertes | produccion |
| `montaje.md` | la navaja suiza de edición | produccion |
| `thumbnails.md` | craft y workflow de miniaturas | produccion |
| `referencia-video.md` | leer, adaptar y recrear una referencia | produccion |
| `instalacion.md` | instalar en Windows, macOS y Linux | operacion |
| `cli-contract.md` | el contrato de las CLIs | operacion |
| `i18n.md` | los idiomas de la skill | operacion |
| `auto-mejora.md` | el protocolo de mejora de la propia skill | operacion |
| `lecciones-produccion.md` | las lecciones aprendidas en producción | operacion |
| `paleta.md` | el color en modo libre: catálogo y regla de elección | color |
| `capacidades.md` | con qué cuenta la skill y qué falta | herramienta |
| `remotion.md` | la integración con Remotion | herramienta |
| `hyperframes.md` | la integración con HyperFrames | herramienta |
| `3d.md` | el 3D como material: Blender por MCP y objeto de referencia a Three.js | herramienta |
| `diagramas.md` | diagramas como HTML+SVG con la marca de la pieza | herramienta |
| `canvas.md` | el motor pictórico (p5.js): acuarela, pincel y doodle generativo | herramienta |
| `hand-draw.md` | trazos a mano: suavizado, overlay con alfa y gestos (sin MediaPipe en la skill) | herramienta |
| `herramientas-agente.md` | las herramientas conectadas del agente y su handoff | herramienta |
| `brief.md` | el contrato de trabajo cuando se delega una parte | plan |

## 4. Las reglas que sostienen el sistema

1. **Una idea, un canonico.** Cada concepto tiene una fuente: el resto de los
   archivos la apuntan, no la repiten. Si dos archivos discrepan, el canonico
   gana; si el canonico esta mal, se cambia el canonico.
2. **Nada es una isla.** Todo archivo se alcanza desde `SKILL.md` y todo
   archivo tiene pie. `scripts/auditar_mapa.py` lo verifica.
3. **Un numero, un valor.** Una regla que la skill enseña con un numero
   (el margen lateral, el ancho de la zona segura, el techo de overshoot, la
   densidad de movimiento, el piso de letra) no puede enunciarse con otro
   numero en otro archivo: quien lea el segundo creeria lo que dice ahi. El
   auditor compara cada enunciacion contra el valor del motor y avisa de la
   divergencia. (Los logs fechados quedan fuera: son registros de una
   decision pasada.)
4. **Lo que la doc promete se puede correr.** Cada comando que el `SKILL.md`
   documenta se comprueba sin ejecutarlo: si a `argparse` le falta un
   argumento, el agente se queda parado con un error que no esta en la doc.
   Lo verifica `scripts/_comandos_doc.py`.
5. **Lo que se debe saber, se sabe.** Si una tarea necesita un dato (el
   overshoot maximo, el ancho de la zona segura, el formato de la VO), ese
   dato esta en UN archivo, no repartido en trece.
6. **Lo verificable es automatico.** Si una regla se puede medir, hay un
   script que la mide: `auto_qa`, `medir_animacion`, `lint_copy`,
   `delivery_check`, `qa_entrega`, `auditar_mapa`.
7. **Todo entregable pasa por la puerta.** Cualquier camino que termine en un
   video —crear, editar, clonar, resumir, grabar— acaba en `qa-entrega.md`.
   Sin la puerta, el motor no se puede juzgar: un video con la tipografia
   ilegible, el spec mal o un frame congelado tambien "sale". El indice lo
   verifica: cada ruta que produce un entregable tiene que acabar en
   `qa-entrega.md`, y el paso de edicion del `SKILL.md` tiene que nombrarla.
8. **La prosa es para el juicio, el codigo para el hecho.** Un numero que se
   puede calcular no se escribe a mano en la referencia: se calcula.
9. **"Que se encuentre" tiene cuatro capas, y cada una necesita su guard.** Que
   una herramienta este enlazada en algun sitio no basta: puede existir, estar
   enlazada y seguir siendo invisible. Por eso hay cuatro preguntas y cuatro
   guards:
   - *¿Existe y esta enlazada de ALGO?* -> el check de huerfanos
     (`scripts/validate_skill.py`): un archivo que ninguna referencia
     encuentra es un archivo que nadie usa.
   - *¿Esta en la ENTRADA que el agente lee primero?* -> el guard del indice
     del `SKILL.md` (`scripts/auditar_mapa.py`): una CLI enlazada solo en una
     referencia es media invisible. El caso: `galeria.py` (las 39 escenas del
     catalogo) y `beat_file.py` (el camino inverso a `beat_grid.py`: el beat se
     autora primero y la musica nace de el) estaban enlazadas en una
     referencia y no en el indice: el agente no las encontraba.
   - *¿La doc que la describe dice la verdad?* -> los guards de cifras y de
     reglas: un numero que no coincide con el motor es una promesa rota, por
     muy bien enlazada que este la pagina.
   - *¿Alguien la EJECUTA?* -> el guard de cobertura de CLIs
     (`scripts/auditar_mapa.py`, con el mapa en
     `scripts/data/cli_verificadas.json`): una CLI documentada que nadie
     ejecuta ni vigila por argumentos es un puntero a nada. El mapa se midio
     instrumentando `subprocess` durante la suite real (leer los tests no
     vale: un nombre en un comentario no ejecuta nada) y se valida: si el
     test nombrado desaparece, la CLI se queda sin verificar y el guard lo
     dice.
   - Y el mapa no lo escribe nadie a mano: lo MIDE la misma corrida de la
     suite que la validacion ya hacia (`scripts/_censo_clis.py`, que
     instrumenta `subprocess` y deja registrado que scripts se ejecutaron
     de verdad). El fichero es solo su foto: se regenera con
     `python3 scripts/_censo_clis.py --escribir` y se contrasta con
     `--comparar`. Asi el mapa es un HECHO y no una declaracion que
     envejece en silencio.
   - Y que la EJECUTEN no basta: el agente copia el comando de la prosa, y
     lo que copia tiene que funcionar. `argparse` no puede ver ese defecto
     (un `plan.json` donde va el video es una cadena valida: el comando
     revienta mas tarde, cuando ya no hay nadie mirando). Por eso hay un
     guard que COPIA cada comando documentado, lo CORRE con assets reales
     (el plan de muestra de la skill, un video y un audio minimos, una
     plantilla de clonado) y separa lo que es un veredicto de la
     herramienta de lo que es el comando roto: `scripts/_comandos_copiables.py`.
     Y su lista tiene que ser COMPLETA — todo comando documentado o se
     copia, o tiene el motivo de por que no — porque un puntero a nada
     tambien es un puntero a nada.
     **La unidad es el COMANDO, no el script.** Un script puede necesitar
     la red y aun asi tener una forma que solo necesita un fichero local
     (`clonar_video.py`: `variar` es local, `analizar --url` baja el video).
     Por eso el motivo se declara POR FORMA: si la forma no necesita lo
     que el motivo dice, el comando se copia y se ejecuta. Sin esa
     precision, excluir un script entero se lleva por delante comandos
     que si funcionan, y la cobertura de una vertical se cae sin que nadie
     lo note. Y los saltos se NOMBRAN: un numero de saltados sin motivo
     es un tapon.
     Y hay una capa que lee la PROSA, porque una doctrina se puede deshacer
     por escritura: basta con que alguien llame "opcional" a una capacidad
     en una referencia y la skill vuelve a entregar menos en silencio,
     mientras el mapa, los conteos y los enlaces siguen en verde.
     `scripts/_guard_doctrina.py` lee las frases y falla si la palabra
     prohibida aparece pegada a una capacidad; la negacion que la gobierna
     (la doctrina dicha en voz alta) no es una falta.
   Pasar la primera capa no dice nada de las otras tres, y cada una
   encuentra cosas que la anterior daba por buenas.
   Y la ENTRADA tiene que llevar al camino vigente, no solo a una pagina que
   existe: una entrada correcta que apunta a un documento que se declara
   LEGACY es PEOR que una entrada ausente, porque parece funcionar. El
   caso: el router mandaba "resumen de una reunion" a `pipeline-resumen.md`,
   que se declara legacy en su primera linea, cuando el v2 es el antecesor de
   las escenas del motor y no su camino actual. Por eso, un banner legacy
   tiene que senalar el camino vigente (no decir que doctrina manda: eso es
   doctrina, y el que llega con una tarea no puede elegir entre tres docs).
10. **Un fallo que sale en un sitio y no en otro no es del codigo: es del
    entorno.** Si un check falla en la copia instalada y no en el repo, el
    motor puede estar perfecto y el sintoma —una escena que no se comporta, un
    recorte que no cuadra— apuntar al sitio equivocado. Se REPRODUCE A MANO
    antes de culpar al codigo: primero en el repo, luego el entorno
    (`check_env.py` para el bytecode fantasma; `sincronizar_instalada.py
    --check` para la copia). El orden importa: al reves, se "arregla" lo que
    no estaba roto. El procedimiento, en `references/instalacion.md`.
11. **Un guard que no puede verificar lo que dice, lo dice; y un guard que
    nunca ha fallado es una hipotesis.** Un patron que deja de casar con la
    prosa —una palabra, una barra, una negrita— hace que el check salga en
    silencio diciendo "todo bien" sin mirar nada; lo mismo con un contador
    que lee el archivo equivocado y devuelve 0. Por eso los guards que
    verifican un numero avisan cuando no encuentran la frase que vigilan, y
    por eso cada guard nuevo se prueba INYECTANDO el defecto en el sitio
    exacto donde mira: un guard que no se ha visto fallar no esta
    verificado, esta supuesto. Y cuando un guard se reactiva, puede
    destapar un numero falso que llevaba tiempo publicado: ese es el precio
    de haber tenido el guard apagado, y el numero PUBLICO tiene que quedar
    cierto, no solo detectable.
12. **El historial dice quien escribio cada commit, porque el campo 'autor'
    no lo dice.** Las sesiones de trabajo comparten la misma identidad de git,
    asi que "autor" no distingue nada. Cada commit lleva en el mensaje el
    sufijo de la sesion que lo escribio (`[sesion-a153]`, `[sesion-524d]`): un
    id unico, estable y greppable (`git log --grep=sesion-524d`), que no
    promete una semantica que se pueda cumplir mal —un "[mia]" solo significa
    algo con la conversacion a la vista, y por eso los commits mas antiguos
    lo llevan—. El aviso de `scripts/auditar_mapa.py` sale cuando el
    historial no dice quien escribio cada commit; es un AVISO y no un fallo:
    romper la puerta por higiene del historial seria la forma correcta de que
    la gente aprendiera a odiar la puerta.
13. **El patron de un guard puede ser estrecho, y debe serlo.** Un patron
    ancho —cualquier cifra suelta de la prosa— no distingue el numero que
    verifica de un numero cualquiera, asi que termina marcando cosas que
    estan bien, y un detector que llora se desactiva. Lo que permite el
    patron estrecho es llevar la UNIDAD y el CALIFICADOR: la unidad y la
    palabra que dice que variante es. Solo asi el patron distingue lo que
    tiene que distinguir. Y hay que MEDIRLO: los falsos positivos de un
    guard nuevo se cuentan contra las 61 referencias, no se estiman.
    Y al escribir la prosa, OJO: un ejemplo literal que parezca una
    afirmacion es una afirmacion para el guard (esto looyo en la regla
    misma: un ejemplo con la cifra equivocada hacia saltar al guard que
    escribe las reglas).

## 5. Los scripts

| script | para que |
|---|---|
| `scripts/check_env.py` | que se puede hacer aqui y que falta |
| `scripts/auditar_plan.py` | que el plan sea valido antes de renderizar |
| `scripts/lint_copy.py` | que el copy entre, no se lea como generado y no contradiga al modelo |
| `scripts/render_plan.py` | componer el video desde el plan |
| `scripts/voz_off.py` | la voz en off |
| `scripts/voz_local.py` | la voz en off con la voz del sistema (sin API: maqueta) |
| `scripts/musica.py` | musica y mezcla con ducking |
| `scripts/auto_qa.py` | los defectos de maquina del render |
| `scripts/medir_animacion.py` | los pops, los tirones y la coherencia de movimiento |
| `scripts/qa_entrega.py` | la puerta: las seis comprobaciones con plan (tres sin), un veredicto |
| `scripts/actualizar_conteos.py` | reescribir los conteos que enuncian este mapa y el SKILL.md (`--check` solo informa) |
| `scripts/sincronizar_instalada.py` | dejar la copia instalada en lo publicado y sin bytecode fantasma |
| `scripts/mezclar_audio.py` | el ensamblado del audio: voz + música (duckeada) + SFX en su instante |
| `scripts/puntuar.py` | la rúbrica de premios como puerta: ocho ejes, cuatro medidos |
| `scripts/ffmpeg_tools/delivery_check.py` | el spec de la plataforma |
| `scripts/ffmpeg_tools/loudness.py` | la sonoridad de entrega |
| `scripts/contact_sheet.py` | la hoja de contactos (el ojo) |
| `scripts/galeria.py` | el render de todo el catalogo, con QA |
| `scripts/auditar_mapa.py` | que la skill siga siendo un sistema y no islas |
| `scripts/validate_skill.py` | que la skill entera siga valida |
| `scripts/_comandos_doc.py` | que los comandos que dice el SKILL.md se puedan correr |
| `scripts/_comandos_copiables.py` | que el comando que dice la prosa, COPIADO Y PEGADO con assets reales, funcione (el argumento del tipo equivocado no lo ve argparse) |
| `scripts/_guard_doctrina.py` | que la prosa no vuelva a llamar "opcional" a una capacidad que la pieza puede necesitar (se DECLARA al usuario, no se degrada en silencio) |

---

→ Canónico: `references/mapa.md` · Dominio: indice · Vecinos: `references/plan-video.md`, `references/arquitectura.md`, `references/qa-entrega.md`
