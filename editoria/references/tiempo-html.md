# Tiempo en los motores HTML (kit `assets/js/tiempo.mjs`)

Los tres motores HTML de la skill (HyperFrames, el motor pictórico de Canvas y
Remotion) y cualquier página con `window.renderAt(t)` comparten un mismo
problema: el navegador está hecho para correr en tiempo de pared y el video
necesita que **cada frame sea una función pura de t**. Esta referencia es el
sitio único de esa disciplina en HTML, y `assets/js/tiempo.mjs` su única
implementación: no se reescriben resortes, pulsos ni sub-frames en cada
proyecto.

El kit es el **espejo del motor Python** (`scripts/render_plan.py`): el mismo
resorte, los mismos seis gestos de `MOVIMIENTO` (`animacion.md` §3b), las
mismas curvas (§3) y los mismos instantes de obturador del `--blur`.
`scripts/_tests/test_tiempo_js.py` compara los números de los dos lados: una
pieza mixta (plan Python + overlay HTML) no puede tener dos físicas.

## Cómo se usa

Se copia `assets/js/tiempo.mjs` a la carpeta del proyecto (nunca desde una
CDN: el render tiene que funcionar sin red) y se importa:

```js
import { entra, retarget, frameIdx, rejilla, progresoPalabra } from './tiempo.mjs';
const grid = rejilla(await (await fetch('grid.json')).json()); // beat_grid.py --json
window.renderAt = (t) => {
  const y = 1920 - 300 * entra(t, 0.4, 'titular');      // mismo gesto que el plan
  const golpe = grid.golpe(t);                           // pulso de los picos medidos
  // ... pintar con y, golpe ... y devolver el frame
};
```

| función | qué da | de dónde lee |
|---|---|---|
| `resorte`, `entra(t, t0, rol)` | la entrada con el gesto del rol | `MOVIMIENTO` (igual que el plan) |
| `critico(t, t0, w)` | resorte sin overshoot, 1-(1+w·dt)e^(-w·dt), w 12-40 | para UI sobria, datos y barridos |
| `retarget(t, v0, [[t, v], ...])` | un valor que cambia de objetivo muchas veces, sin estado | suma de un resorte por cambio |
| `wobble`, `ring(t, eventos)` | el asentamiento tras un impacto | un bamboleo amortiguado por evento |
| `keys(t, llaves)` | llaves con curva por tramo (números o arrays) | — |
| `frameIdx(t, fps)` | el índice de frame, constante durante todo el obturador | igual que el grano del motor |
| `enDos(t, fps, n)` | dibujos sostenidos n frames (cel, stop-motion) | — |
| `subframes(t, fps, n, obturador)` | los instantes de los sub-frames del motion blur | igual que `--blur` |
| `mulberry32`, `hash` | azar con semilla y valores estables | — |
| `rejilla(grid)` | `beatAt`, `beatCercano`, `pulso`, `golpe`, `aterriza` | `scripts/beat_grid.py --json` |
| `progresoPalabra`, `palabraEn`, `caracteresDichos`, `lineaVisible` | karaoke y barridos por glifo | `scripts/alinear.py` (`inicio`/`fin`) |

## Las reglas de tiempo

1. **Nada de reloj ni estado.** Ni `Date.now()`, ni `performance.now()`, ni
   `Math.random()` sin semilla, ni `setTimeout`, ni transiciones o animaciones
   CSS sin pausar. Si hay animaciones CSS o WAAPI, se pausan y se posicionan
   en `t * 1000` ms dentro de `renderAt(t)` (`canvas.md`). Una simulación con
   estado (partículas integradas, feedback) se recalcula desde 0 en cada
   frame o se hornea antes: no se puede muestrear en sub-frames fuera de orden.
2. **Lo que salta por frame usa `frameIdx`.** Temblor, boil de línea, parpadeo
   y grano cambian una vez por frame. Con `Math.floor(t * fps)` el cambio cae
   dentro del obturador y cada frame promediado mezcla dos estados (doble
   exposición). Cada elemento con su propia semilla: un elemento que se mueve
   no debe desplazar el azar de los demás (`canvas.md`, `boilSeed`).
3. **Objetivo cambiante = suma de resortes.** Un control que cambia de valor
   varias veces (un slider, un contador, la pestaña activa) es `retarget`, no
   un resorte reiniciado: sigue siendo f(t) y nunca salta.
4. **Dos bordes, dos resortes.** Un indicador que viaja (pestaña líquida,
   perilla de un toggle) estira si su borde delantero va en un resorte más
   rígido que el trasero. Es la forma barata de squash & stretch con volumen.
5. **Arrastres directos.** Mientras el cursor arrastra, el valor es función
   de la posición del cursor; al soltar, `retarget` desde donde quedó.
6. **Aterrizar en el beat.** Un movimiento que debe llegar EN el beat empieza
   unos 0,05 s antes (`grid.aterriza(i)`); el SFX se coloca por su pico medido,
   no por el inicio del archivo (`sonido.md`). Disciplina de cues: `ritmo.md`.
7. **Post leído una vez por frame.** Shake, flash, zoom de cámara y fundidos
   globales se calculan en el instante del frame, no en cada sub-frame; el
   grano y el HUD, una vez por frame, después del blur.

## Motion blur en una captura HTML

Mismo método que el motor (`animacion.md` §2): pintar los instantes de
`subframes(t)` y promediarlos en float. Dos atajos sin código:

- `ffmpeg -vf "tmix=frames=4:weights='1 1 1 1',fps=30"` sobre una captura a 120 fps.
- Muestreo adaptativo: pintar 1, luego 3, luego 9 instantes anidados y parar
  cuando el promedio deja de cambiar. Un frame quieto cuesta poco; un
  latigazo recibe todas las muestras.

El grano se añade **después**, en ffmpeg (`scripts/ffmpeg_tools/artesanal.py`
o `noise`), no en la página: el grano pintado en cada frame hace el video
incompresible, lento de capturar y se emborrona con el blur.

## Trampas medidas

- `will-change` en algo que la cámara escala: el texto sale borroso. Quitarlo.
- `opacity` o `filter` sobre un elemento `preserve-3d` lo aplana y se ven las
  dos caras. Se funde el contenedor, no el elemento 3D.
- Bucles: el último frame tiene que ser **idéntico** al primero, incluida la
  posición y la velocidad del cursor, o el loop tartamudea.
- Texto que cambia dentro de un contenedor que se transforma necesita su
  propia entrada y salida, o los dos textos se pisan durante el morph.
- Kerning: una palabra pintada en trozos (cantado / no cantado, barrido por
  glifo) toma la posición de cada glifo del layout de la palabra entera; medir
  el trozo suelto pierde el kern entre los trozos y la palabra "baila".
- Fuentes locales, no de CDN (`canvas.md`): sin red, sale la fuente de reserva.
- Posiciones para un match cut: medirlas en tiempo de render (el layout real),
  no copiarlas a mano.

## Tres puertas antes del render completo

Con un motor externo el render completo es caro; la aceptación va en tres
pasos (adaptado de una guía de producción pública con licencia CC BY 4.0;
atribución en `references/creditos.md`):

1. **Storyboard y frames clave**: la hoja de contactos del plan
   (`scripts/contact_sheet.py`) con cada estado y su texto exacto.
2. **Los 2-4 s más difíciles**: 12-24 frames seguidos del tramo más rápido,
   mirados uno a uno (oclusiones, contactos, legibilidad, costura del loop), y
   **la prueba de determinismo**: pintar el mismo `t` después de saltar a
   otros instantes en distinto orden debe dar los mismos bytes.
3. **La pieza entera**, vista y oída de principio a fin, y la puerta de
   siempre (`references/qa-entrega.md`).

---

→ Canónico: `references/tiempo-html.md` · Dominio: herramienta · Vecinos: `references/hyperframes.md`, `references/canvas.md`, `references/remotion.md`, `references/animacion.md`
