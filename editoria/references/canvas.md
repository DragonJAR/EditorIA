# Canvas pictórico (capacidad)

El motor pictórico pinta dentro de un `canvas` de navegador con p5.js y p5.brush, y
renderiza con Chrome headless (puppeteer-core) más ffmpeg. Es la vía para lo que el motor
Python (PIL, 39 escenas planas en `references/escenas.md`) no da: trazo a pincel, acuarela
con sangrado de borde, textura de pigmento, sombreado a plumilla, luz que ilumina de
verdad, doodle generativo y el formato videoclip, donde la música manda la dirección
(`references/formatos.md`).

El motor Python sigue siendo el camino por defecto: es más rápido de iterar y cubre la
mayoría de las piezas. **Pero "más rápido" no es "mejor"**: cuando la pieza pide material
pintado, el motor plano no tiene ese material. El motor pictórico no es una opción de
menú: es **la herramienta cuando la pieza lo pide**, y si falta (Node 18+ y Chrome), se
declara al usuario con su comando en la primera respuesta en vez de entregar menos en
silencio (ver `references/capacidades.md`).

## Cuándo usarla (y declararla si falta)

- La pieza pide material de acuarela o de pincel: manchas, bordes que sangran, grano de
  papel, plumilla para el sombreado.
- La pieza pide luz pintada (focos, faroles, chispas) y no degradados.
- La pieza es un videoclip o un lyric video: la dirección la marca la pista y el cuadro se
  pinta al tempo (`references/formatos.md`).
- La pieza es generativa y repetitiva: partículas, trazos, variaciones que el motor plano
  no sabe sacar.

Requisitos reales: **Node.js 18+** y **Google Chrome**. En la carpeta del proyecto,
`npm i p5 p5.brush puppeteer-core`. Versiones vistas en el registro de npm: p5 2.3.4
(LGPL-2.1) y p5.brush 2.2.3 (MIT, que declara p5 2.2 o superior como par); los lockfiles de
los dos repos clonados fijan p5 2.3.3, p5.brush 2.2.3 y puppeteer-core 25.11.0.

La comprueba `check_env.py`: esta capacidad vive en el bloque "Motores externos
(capacidades de la pieza, no requisitos del motor)", y ahí hay una línea `chrome` que dice
si está y, si no, el comando de instalación y esta referencia. La línea `node/npx` cubre el
otro requisito duro de esta vía (Node 18+).

## Licencias y atribución

| Pieza | Licencia | Fuente |
|---|---|---|
| p5.js | LGPL-2.1 | https://p5js.org , https://github.com/processing/p5.js |
| p5.brush | MIT | https://github.com/acamposuribe/p5.brush |
| puppeteer-core | Apache-2.0 | https://registry.npmjs.org/puppeteer-core |
| ClaudeAnimationBase (el kit) | MIT, Copyright 2026 John Heibel | https://github.com/JohnHeibel/ClaudeAnimationBase |
| PDoomVideo (el videoclip) | declara ISC en su `package.json` y NO trae fichero LICENSE | https://github.com/JohnHeibel/PDoomVideo |

Se cita la fuente original de cada pieza de código que se copie: si el motor pictórico se
apoya en el `paint()`, el `glow()` o el barrido de pincel del kit, esa línea conserva el
aviso de MIT del kit, con su autor y su año. PDoomVideo no trae fichero LICENSE: lo que su
`package.json` declara es ISC, y eso es lo único que se puede afirmar; no se inventa un
LICENSE que no existe.

## La disciplina que hace que funcione

Lo que separa una pieza pintada de un screensaver, según el `ANIMATION_GUIDE.md` del kit:

1. **Storyboard antes del código.** El storyboard se escribe en prosa (logline, mundo,
   motivo, arco, y plano por plano con su tiempo) antes de la primera línea de escena. Su
   parte útil es la lista de lecturas: qué tiene que entender el espectador en cada plano
   y cuánto dura cada lectura. Ese papel es la hoja de tiempos; sin ella el código se
   escribe a ojo.
2. **Una escena, un fichero.** Cada plano va en su propio archivo de `src/` con sus
   helpers privados; lo compartido (paleta, cámara, tiempos, personajes) vive aparte. En
   PDoomVideo son nueve capítulos en nueve archivos de 400 a 900 líneas cada uno, más los
   módulos comunes.
3. **La función de pintado es una función pura del tiempo.** Los frames se pintan en
   paralelo y fuera de orden: la misma escena con el mismo tiempo tiene que dar el mismo
   frame. Nada de estado entre frames, nada de contadores, nada de azar sin semilla, nada
   de física que se integra frame a frame; todo se calcula en forma cerrada a partir de t.
   Para lo que debe quedarse quieto, `hash(i)`. Para el temblor del trazo, `jit()`, que se
   resiembra 12 veces por segundo. Y cada elemento con su propia semilla
   (`boilSeed(key)`): un elemento que se mueve desplaza el azar de todo lo que se pinta
   después, y eso hace temblar al resto.
4. **Se revisa con hojas de contactos antes de pagar el render completo.** El contact
   sheet (varios tiempos en una imagen) cuesta alrededor de 0.1 a 1 s por frame, así que
   es barato. El presupuesto del guide: al menos una hoja por plano, una tira de frames
   por movimiento clave y un recorte a resolución completa por cada cara que lleva la
   historia.
5. **Cada empalme lleva transición.** Entra, entre planos y sale: barrido de pincel, iris,
   fundido, corte en acción o movimiento de cámara que continúa. El corte a secas solo
   vale como golpe deliberado.

## El flujo de trabajo, en comandos

```bash
npm install
node render.mjs --sheet=0,2,4 --out=out/check/sheet.jpg   # hoja de contactos
node render.mjs --stills=1.5,3 --out=out/stills           # stills a resolución completa
node render.mjs --frames=0:156.6 --workers=4               # frames en disco
node render.mjs --encode --out=out/video.mp4               # los frames, con ffmpeg
```

Los frames se escriben **de forma atómica**: el buffer va primero a `f00000.jpg.tmp` y se
renombra encima al terminar, así que un render interrumpido no deja un JPEG a medias. Y si
el frame ya existe (y pesa más de 1 kB) se salta: por eso el render se reanuda solo,
relanzando el mismo comando. El log imprime ms por frame efectivo y el tiempo que falta.

La sintaxis del rango depende del repo: PDoomVideo toma `--frames=0:156.6` (el rango va
dentro de la flag) y el kit generalizado toma `--frames` con `--range=0:8`. `--encode`
junta `out/frames` con el audio y produce el MP4 con libx264.

Si se escribe el `studio.html` propio, `render.mjs` sólo exige tres cosas de la página:
cargar p5 y p5.brush, poner `window.ready = true` cuando todo esté listo (el render espera
ese flag con 60 s de margen) y exponer `window.renderAt(t, tipo, calidad)` que devuelva un
data URL del frame. Si además hay animaciones CSS o WAAPI, el capturador debe
**pausarlas y seekearlas a `t * 1000` ms** antes (o dentro) de `renderAt(t)`; si no,
el frame queda en el tiempo de pared y deja de ser determinista. Misma disciplina
para films MG one-shot (`estilos-motion.md`) en HyperFrames/HTML.

## Las trampas medidas

- **Sin GPU, Chrome headless va muy lento.** El README del kit lo dice de su propio color:
  sin GPU dedicada, los rellenos de acuarela de p5.brush hacen que el render tarde
  segundos por frame. El coste es el número de formas y trazos: cientos van bien, miles
  no, y el guide pide apuntar a 1.5 s por frame o menos (el log mide ms/frame).
- **En Linux hay que quitar el sandbox.** El kit lanza Chrome con `--no-sandbox`, porque
  Ubuntu 23.10 y posteriores bloquean el sandbox de Chrome en headless. Sin GPU se añade
  `--soft-gl` (WebGL por software, con SwiftShader, que Chrome sólo permite si se le pide) y
  en un nodo Linux con GPU NVIDIA, `--gpu-angle=gl-egl` o `--gpu-angle=vulkan`.
  `node gpu_probe.mjs` con la ruta de Chrome dice qué renderizador da cada juego de flags.
- **Hay que pasar la ruta de Chrome si no está donde el script la busca.** El fallo
  concreto del repo original: la ruta por defecto de PDoomVideo es de Windows, y su
  lanzador lleva además el flag de ANGLE de Windows, así que en macOS hay que pasar
  `--chrome="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"`. El kit
  generalizado sí resuelve la ruta por plataforma y acepta `CHROME_PATH`.
- **Chrome headless frena el bucle si no se le dice.** Sin
  `--disable-renderer-backgrounding` y `--disable-background-timer-throttling` la
  animación se ralentiza en segundo plano y los frames salen con tiempos raros. Y las
  tipografías del `studio.html` llegan de una CDN: un render sin red sale con la fuente de
  reserva, así que las fuentes van locales o el render no es reproducible.

## Cómo convive con EditorIA

- **Motor Python** (por defecto): las 39 escenas planas, rótulos, cifras y la animación de
  resortes. Es lo que se itera en segundos.
- **Remotion** (`references/remotion.md`): cuando la pieza es data-driven y el equipo vive
  en React.
- **HyperFrames** (`references/hyperframes.md`): cuando la composición es HTML y el equipo
  itera en web.
- **Motor pictórico** (esta): acuarela y pincel, doodle generativo, y el videoclip donde
  la música manda la dirección.

Se cruzan en los dos sentidos: EditorIA genera los assets (PNG con alfa, JSON de tiempos,
la pista) y el motor pictórico los pinta, o el motor pictórico entrega el clip y
`aplicar_edl.py` con ffmpeg lo integran en el montaje. La puerta de entrega es la misma de
siempre (`references/qa-entrega.md`) y el listón no baja por pintar de otra manera
(`references/direccion.md`). Una salvedad de método: la regla de "sin texto" del
`ANIMATION_GUIDE.md` pertenece a su propio cortometraje de personaje; en una pieza de
EditorIA el texto en pantalla lo decide `references/copy.md` y lo compone el motor, no el
pincel.

**Este motor no es de la skill**: no hay script que lo ejecute. Se clona el kit
(https://github.com/JohnHeibel/ClaudeAnimationBase) o se escribe el `studio.html` propio,
y se renderiza a mano con `node render.mjs`. Igual que con el resto de motores externos:
lo que no es de la skill se declara y se clona, no se promete.

---

→ Canónico: `references/canvas.md` · Dominio: herramienta · Vecinos: `references/remotion.md`, `references/hyperframes.md`, `references/3d.md`
