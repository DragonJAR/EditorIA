# Dibujado a mano — la vía de las poses redibujadas

Hay dos oficios que se parecen en pantalla y no en el trabajo: el **motion
graphics** (tarjetas, cifras, rótulos, resortes) y el **dibujo animado** (un
personaje que se redibuja plano a plano). El motor plano de EditorIA resuelve
el primero mejor y más rápido. El segundo no lo resuelve: unas extremidades
que interpolan leen como marioneta, por muy bonita que quede la acuarela.
Esta referencia es la vía del segundo.

## Cuándo se entra en esta vía

- El brief pide trazo visible: boceto a lápiz, tinta, plumilla, riso o
  serigrafía.
- El brief pide un **personaje que se mueve** y no un elemento que entra.
- El brief pide **rotoscopio** (un animal o una persona real que se mueve),
  **animación de arena** (una toma continua, sin cortes) o **papel desplegable**
  (libro, diorama, una página que se levanta).
- El brief pide un material que no se puede simular con formas planas.

Cuando NO se entra: rótulos, cifras, tarjetas, tablas, demos de producto. Eso
es `plan-video.md` y sale más fino y más rápido. La regla de `references/canvas.md`
sigue valiendo: el motor Python es el camino por defecto y esta vía se toma
cuando la pieza la pide.

## Los dos motores (ninguno es de la skill)

| vía | qué es | requisitos | para qué |
|---|---|---|---|
| **Pictórico** | p5.js + p5.brush sobre `canvas`, Chrome headless, ffmpeg | Node 18+, Chrome | acuarela, pincel, doodle generativo, videoclip con la música mandando (`references/canvas.md`) |
| **Kit dibujado** | motor propio de Canvas 2D: tinta, lápiz, riso, serigrafía, doodle sobre foto, rotoscopio, arena y papel 3D | Node 22.12+, Chrome, ffmpeg | personaje animado, secuencia dibujada, arena, rotoscopio |

El kit dibujado es `https://github.com/alesha-pro/tools`, rama `main`, carpeta
`skills/hand-drawn-canvas-animation` (MIT, Alexey Fateev). **Se clona, no se
copia dentro de la skill**: es un motor externo, igual que el pictórico, y sus
35 MB (de ellos, 1,6 MB de assets y 3,8 MB de ejemplos) no se vendorizan aquí.
Lo que se traslada es el método (abajo), los requisitos y la lista de técnicas.

Trae su propio comprobador (`node scripts/verify.mjs`, dentro del kit clonado),
con 18 comprobaciones: exposiciones y dibujos sostenidos, IK y longitudes,
seeking reproducible, formato del render, arena, rotoscopio y los cinco
materiales. Ejecutado sobre el repo clonado el 2026-10-24: **18 PASS**. Es
prueba de que el motor funciona; no es prueba de que una película sea buena.

## El método que sí se traslada (vale para cualquier motor)

1. **Pose entera, no extremidades.** Un codo doblado es un contorno nuevo con
   pliegues y solapes. Un esqueleto o un IK pueden servir para localizar
   articulaciones y contactos, pero la silueta final la carga la pose. Las
   cápsulas que rotan leen como un títere aunque tengan contorno rugoso.
2. **La exposición la decide la acción.** Ones, twos, threes y un dibujo
   sostenido son todos válidos: un giro rápido pide unos, una pausa puede
   sostener un solo dibujo. No es un frame rate global, es una decisión de
   dirección. **No se cuantiza dos veces**: si la escena va a twos, la cámara
   va a twos; si la cámara va a unos, se revisa el movimiento combinado en
   pantalla, porque el movimiento de raíz sobre twos bajo una cámara que
   sigue en unos produce un vaivén alterno.
3. **Llaves y breakdowns antes que intermedios.** El breakdown es donde la
   cabeza guía, donde se despliega un ala, donde una mano pasa por delante.
   Los intermedios solo se añaden si mejoran el espaciado y la claridad.
   **Más intermedios no reparan una llave poco clara.**
4. **Los contactos se conservan hasta su liberación planesada.** El pie sigue
   en el suelo mientras la cadera se mueve; una mano agarra derivando del
   transform del objeto, no con una fórmula aparte. El punto de contacto
   dibujado y el punto de contacto real tienen que ser **el mismo punto**. Si
   el IK no alcanza, se corrige la pose: no se estiran huesos.
5. **La masa se transfiere antes de levantar.** Y el resorte no se aplica a
   todo: un motor gira a velocidad constante, una taza rígida no hace squash en
   cada frenada. Este es el punto donde esta vía se aparta de
   `references/animacion.md`, que gobierna el motion graphics.
6. **Las marcas se comportan como marcas.** Presión, taper, interrupciones y
   sombreado que sigue al volumen. Un campo de curvas paralelas alrededor de
   cada forma parece malla metálica; el lado iluminado va más callado. **El
   material no rescata una pose poco clara.**
7. **La semilla es del dibujo, no del cuadro.** Un dibujo sostenido sostiene
   también sus marcas. Cambiar la semilla es un dibujo nuevo, no un cuadro más
   vivo.

## Los cinco looks y su puerta

| look | material | qué se rechaza |
|---|---|---|
| **Tinta** | contorno con presión, sombreado por forma | contornos uniformemente peludos, el mismo ángulo de trama en cada parte, líneas de búsqueda por todas partes, identidades de trama que parpadean |
| **Lápiz** | pasadas estrechas e interrumpidas, con presión | contorno grueso y ruidoso; el lápiz como simple depósito sobre una cinta rellena no es un boceto abierto |
| **Riso** | 2 a 4 separaciones de tinta registradas | convertir al personaje en masas geométricas limpias; shaking independiente por punto; la trama no pertenece a la hoja |
| **Serigrafía** | masas planas, tinta opaca, bordes de pincel conservados | textura que tapa el dibujo, bordes con ruido arbitrario, todas las capas en multiplicar |
| **Doodle sobre foto** | trazo dibujado que interactúa con la foto | manos que resbalan, pies flotantes, halo, decoración que nunca toca el objeto |

La prueba de cada look es una acción, no una tabla de estilo: un giro de
cabeza y un brazo levantando peso, vistos en silueta y en acabado.

## Las tres técnicas que eran nuevas

- **Rotoscopio** (el trazador `roto.py` del kit): una secuencia real (Muybridge
  1893 en dominio público, Marey, o un video del usuario) se traza a vectores y
  la película la redibuja con el pincel del motor. El movimiento es un hecho;
  cada línea de pantalla está dibujada por código. Límite real: el umbral da
  siluetas externas, no anatomía ni rasgos, y no es seguimiento semántico. El
  defecto típico es una pose re-centrada a mano, que hace que la figura flote
  sobre un suelo plano.
- **Arena**: la cama de arena recuerda lo que tenía. Una mano vierte, barra,
  peina; lo apartado forma cordones y conos. Una imagen sale de la anterior
  sin corte. Es la vía de la toma continua.
- **Papel 3D**: cada hoja es una malla de triángulos con su propio transform
  afín, del orden de 200 triángulos por hoja. Es la vía del libro desplegable,
  la página que se levanta y el diorama con cámara alrededor.

## Lo que el brief de una pieza dibujada tiene que decir además

El brief normal (`references/brief.md`) no basta aquí. Estos campos son los
que solo importan cuando la pieza está dibujada:

- **Look y material por plano**, y la razón narrativa de cada cambio de look.
- **Lenguaje de marcas**: dónde va la presión, qué trazos se abren, en qué
  dirección se trama, qué zonas quedan calladas.
- **Reparto**: siluetas, expresiones, vistas necesarias y dibujos de
  sustitución.
- **Hoja de exposición**: identificadores de dibujo y número de cuadros de cada
  uno, con los cambios de contacto y de topología.
- **La acción más difícil**: llaves, breakdowns, contactos y el cuadro en que
  cada contacto se libera.
- **Unión de la marca con el cambio de material**: la acción, la posición o el
  objeto físico que cruza el cambio. Un cambio de paleta no abre un look
  nuevo.

## Cómo se revisa (con las herramientas de la skill)

No se añade un visor nuevo: se revisa con lo que ya hay.

| qué se mira | con qué |
|---|---|
| la tira completa de un plano | `scripts/contact_sheet.py --video corte.mp4 -n 20 -o hoja.png` |
| el movimiento cuadro a cuadro | `scripts/contact_sheet.py --video corte.mp4 --inicio 12 --fin 14 --cada 0.1 -o tira.png` (o `--todos-los-frames` acotado a un tramo corto) |
| el detalle a resolución completa | `scripts/contact_sheet.py --video corte.mp4 --en 13.4 -o detalle.png` |
| la pieza entera | `scripts/qa_entrega.py final.mp4 --plan plan.json` |

**Una hoja de contactos estática es un chequeo de composición, no de
movimiento.** El movimiento se juzga en reproducción a velocidad normal y en
tiras de cuadros consecutivos alrededor de un contacto o de un giro rápido; la
hoja estática solo dice si la composición funciona. Y se mira una vez con el
sonido apagado: la música esconde un timing torpe.

## Lo que no se hace aquí

- **No se vendoriza el kit.** Ni su motor, ni sus ejemplos, ni sus assets. Se
  clona y se declara (ver `references/capacidades.md`).
- **No se reescribe `references/animacion.md`.** Ese documento gobierna el
  motion graphics; aquí solo queda declarada la excepción del punto 5.
- **No se promete calidad de estudio.** Que el motor pase sus 18 comprobaciones
  no dice que una película sea buena: eso se juzga contra la referencia visual
  elegida.

---

→ Canónico: `references/dibujado.md` · Dominio: herramienta · Vecinos: `references/canvas.md`, `references/animacion.md`, `references/estilos.md`
