# QA de entrega — la puerta unica

Todas las comprobaciones deterministas, en orden, y un solo veredicto. Ninguna
depende de un modelo ni de la red: si el comando dice que pasa, pasa.

```bash
python3 scripts/qa_entrega.py final.mp4 --plan plan.json
python3 scripts/qa_entrega.py final.mp4 --plataforma linkedin --json
```

Sale 0 si todo pasa, 1 si algo falla, 2 si la entrada no existe.

## Los dos modos: con plan y sin plan

| | con `--plan plan.json` | sin `--plan` |
|---|---|---|
| quien lo usa | la pieza animada (se renderiza desde un plan) | la pieza editada (un montaje no tiene plan) |
| que mide | todo lo de abajo **mas** la composicion del plan: letra real, zona segura, solapes | el render, el spec y el movimiento |
| eje 4 de la rubrica | medido | **juzgado a ojo** (`--ejes "1=4,2=4,4=4,5=4,7=4"`) |

La puerta es la misma en los dos casos: sin `--plan` no se inventa un plan,
solo se deja de medir lo que no existe. Un montage sin puerta es un video sin
juzgar: el spec de plataforma, la sonoridad y los frames congelados siguen
sin mirarse.

```bash
# pieza animada
python3 scripts/qa_entrega.py final.mp4 --plan plan.json
# pieza editada
python3 scripts/qa_entrega.py final.mp4
```

**El cierre en negro no es un defecto.** El motor cierra SIEMPRE con un
fundido a negro (el ultimo frame es negro por diseno), asi que la puerta
pasa `--ignorar-fin 0.5` a `auto_qa`: sin ese margen, toda pieza hecha con
`render_plan.py` rechazaria su propio cierre. Si lo que quieres es exigir
que ni el ultimo medio segundo tenga negro, ponlo en 0:

```bash
python3 scripts/qa_entrega.py final.mp4 --plan plan.json --ignorar-fin 0
```

Tambien acepta `--ignorar-inicio` para un fade-in intencional.

## Que comprueba cada paso

| paso | que busca | que NO ve |
|---|---|---|
| `auditar_plan` | solapes de escenas, duraciones vacias, voz vacia, orden temporal | el copy, el render |
| `lint_copy` | texto que no entra, tells de genero, cifras sin fuente, copy de muestra | el render |
| `auto_qa` | frames negros, congelados, flashes, fotosensibilidad, audio | el copy, el movimiento fino |
| `delivery_check` | el spec de la plataforma: resolucion, fps, duracion, bitrate, sonoridad, true peak | la composicion |
| `medir_animacion` | coherencia de movimiento: pops, tirones, arranques, densidad, cuadro congelado sin grano (`quieto`), ocupacion de la zona segura | el copy, la narrativa |
| `medir_animacion --plan` | composicion: letra real en reposo, zona segura, textos que se pisan (cada solape con su escena, su instante y los dos textos) | el copy, el movimiento fino |
| `plan-vs-video` | que el plan no sea posterior al MP4: un plan editado despues del render (una fuente retirada, un copy acortado) deja a la puerta aprobando un plan que no es el video entregado | el contenido, si el render es posterior |
| `subtitulos` | en una pieza **narrada** para reels/tiktok/shorts, que los subtitulos esten declarados (`"subtitulos": true` o la ruta en el plan, o `--subtitulos archivo`) | si el quemado se ve bien (eso se mira en los frames) |

Quemar subtitulos deja pixeles indistinguibles del resto de la imagen, asi
que este paso no puede VERLOS: lo que impide es el silencio. Sin
declaracion, la puerta falla con el comando para generarlos
(`alinear.py` → `caption.py --palabras voz.palabras.json --karaoke --plan plan.json`: ningun cue cruza un corte de escena y el karaoke cae en la banda inferior que el motor reservo, nunca en el centro que componen las escenas).
Con plan, cada hallazgo de composicion trae su **escena y su texto**
(«escena 6:versus "…" 21 px»): la pasada con alcance corrige ahi, sin
inspeccionar la pieza frame a frame.

**Tiempos**: en una VM modesta, la puerta de una pieza de ~60 s tarda
minutos (medir el video y el plan es lo caro) y el render `--blur 5`
varios minutos mas. La puerta anuncia cada paso antes de correrlo y lo
cierra con su tiempo, y el render imprime progreso con ETA: corre la
puerta en segundo plano o con un timeout generoso, no con el de un
comando corto.

**`medir_contraste` NO es un paso de la puerta**: no mira la pieza que
entregas, sino el CATALOGO de escenas del motor (el texto de cada escena
contra la superficie que tapa). Se corre cuando se toca el motor o una
paleta, no en cada entrega.

**Por que `auto_qa` y `medir_animacion` van juntos**: `auto_qa` mira el render con ojos
maquina (luminosidad, congelamiento, destellos) y no ve un corte seco entre
dos planos ni unaConversion de fps que inventa cuadros. `medir_animacion`
si los ve, pero no juzga el copy. Ninguno de los dos ve el otro: por eso la
puerta corre las dos.

**Por que el plan se mide aparte**: la letra, la zona segura y los solapes
no se leen de los pixeles del MP4 (un render no dice de que tamano es un
texto). Se miden con el motor sobre el plan, y esa es **la misma medicion**
que usa la rubrica de premios (`scripts/puntuar.py`, eje 4). Si las dos
puertas midieran cosas distintas, una aprobaria lo que la otra rechaza:
por eso comparten la medicion y no dos implementaciones.

## Los umbrales

- **movimiento**: nota minima 90 sobre 100, y cero pops. La nota descuenta
  los pops (12 puntos cada uno), los tirones (4 cada uno, hasta 20) y los
  arranques sin ease-in (2 cada uno, hasta 10). Ademas falla con un cuadro
  congelado de mas de 1 s (`quieto_max`, el FROZEN_MAX de `auto_qa` y de
  `checklist-qa.md`; la racha que llega al final es el cierre y no cuenta)
  o con una `ocupacion` media bajo 0.20 (la caja del contenido sobre la zona
  segura). `quieto` se mide por bloques porque el grano del MP4 tapa el
  congelado a `auto_qa`: medido en un video real del catalogo, el piso de
  diff de cuadro entero es ~0.42 (> 0.35, su umbral) y vio 1.75 s de un
  congelado de 3.0 s. La nota cobra el mayor de `muerto` y `quieto` (25 por
  fraccion) y hasta 20 por la ocupacion bajo el piso.
- **copy**: los fallos son texto que el motor no puede colocar; los avisos
  son copy que se lee como generado o que se encoge de mas. Un plan con
  avisos es entregable; un plan con fallos, no.
- **plataforma**: se comprueba la que dice `--plataforma` (por defecto
  `reels`). Para una pieza que sale en varios sitios, correr la puerta una
  vez por destino.
- **composicion**: la letra real, en reposo, tiene que llegar a **26 px**; la
  escena no puede tocar el piso de la zona segura (0,70) y los textos no se
  pueden pisar. La letra se mide con el tamano con el que el texto **se
  queda**: si un boton entra con resorte y pasa por 21 px a mitad de camino,
  eso no cuenta (ver `references/coherencia-espacial.md`). Y el texto tiene
  que **contrastar** con lo que tapa: un color de acento sobre una banda del
  mismo color de acento es ilegible, y eso no se ve leyendo el codigo, se
  ve midiendo (`scripts/medir_contraste.py`). Ese check mide el CATALOGO del
  motor, no esta pieza: el contraste de un texto que pinta una herramienta
  con ffmpeg se garantiza al construirlo (el texto sigue al fondo), no en la
  puerta.

## Orden recomendado de trabajo

1. `auditar_plan.py plan.json` — si el plan tiene tiempos malos, el render
   ya sale mal: no lo renderices todavia.
2. `lint_copy.py plan.json` — el copy se arregla en el texto, no en el
   render. Corrige aqui y vuelve a renderizar.
3. `render_plan.py plan.json -o final.mp4 --blur 5`
4. `qa_entrega.py final.mp4 --plan plan.json` — si algo falla, el paso que
   fallo dice donde mirar.
5. Corregir y volver a renderizar. No parchear el MP4: el render es
   reproducible desde el plan, y el plan es la fuente.

## Cuando algo falla

- **plan**: el fallo dice el par de escenas que se solapan o la duracion
  vacia. Se corrige en el JSON.
- **copy**: el linter da la ruta exacta (`escenas[2].items[0].titulo`) y el
  numero que el motor va a usar. Se acorta el texto, no se sube el tamano.
- **auto_qa**: casi siempre es un frame negro por un plano demasiado oscuro
  o una congelacion por un clip que no avanza. Ver
  `references/auto-qa.md`. Si el negro es el fundido de cierre (el ultimo
  frame), no es un defecto: la puerta ya lo ignora, y con
  `--ignorar-fin 0` se vuelve a contar.
- **delivery**: el spec de la plataforma. Casi siempre la sonoridad: el
  audio recien mezclado cae justo en el borde del true peak. Normalizar con
  `scripts/ffmpeg_tools/loudness.py final.mp4 -I -14 --tp -1.5 --force`
  (escribe `final_loudnorm.mp4`; hay que renombrarlo sobre el original).
- **movimiento**: pops o tirones. Las dos causasmas comunes son convertir
  el footage a una tasa que no es la suya (duplica cuadros) y cortar dos
  planos en seco. Ver `references/lecciones-produccion.md`. Un congelado
  largo es casi siempre una escena sin camara ni fondo vivo (un rotulo
  inferior sostenido); una ocupacion baja, escenas de solo tipo en un
  lienzo grande: la medicion `--plan` dice cual (`ocupacion_escena`).
- **composicion**: la letra se queda pequena porque el copy es largo. Se
  acorta el texto del plan, no se sube el tamano a mano: el motor vuelve a
  calcular el tamano y el ajuste a mano se pierde en el siguiente render.

## Lo que la puerta no cubre

La puerta no juzga si la pieza **cuenta** algo: que el argumento sea del
sujeto y no de la categoria, que el ritmo tenga respiracion, que el copy
diga lo que el brief pedia, ni si el liston de premios esta alcanzado.
Eso se juzga mirando el video (la hoja de contactos de
`scripts/contact_sheet.py` ayuda) y leyendo el copy contra el brief, con
`references/copy.md` como contrato.

Para el liston, despues de la puerta:

```bash
python scripts/puntuar.py final.mp4 --plan plan.json --ejes "1=4,2=5,5=4,7=4"
```

`scripts/puntuar.py` mide cuatro de los ocho ejes de
`references/rubrica-premios.md` (animacion, composicion, sonido y acabado
tecnico) y te pide los otros cuatro (idea, dramaturgia, sistema visual y
verdad/marca), que son juicio. El gate: ningun eje por debajo de 4 y media
de 4,3 o mas.

---

→ Canónico: `references/qa-entrega.md` · Dominio: qa · Vecinos: `references/auto-qa.md`, `references/checklist-qa.md`, `references/rubrica-premios.md`
