# Remotion (integración opcional)

Remotion (remotion.dev) es el framework de video programático en React:
las composiciones son componentes, el video se renderiza con
`npx remotion render`. EditorIA **no depende** de Remotion — el motor
Python (`render_plan.py` + ffmpeg) cubre la mayoría de piezas y es más
rápido de iterar. Esta referencia existe para saber cuándo Remotion
es la mejor herramienta y cómo usarlo bien.

## Cuándo sugerir su instalación

- Animaciones complejas data-driven (gráficos que dependen de datos
  externos, timelines con lógica condicional).
- Escenas reutilizables como componentes (un sistema de diseño en código).
- El equipo del usuario ya trabaja en React/Next.js.
- Piezas que van a re-renderizarse muchas veces con distintos datos.

Si Node 18+ no está instalado: `check_env.py` lo reporta; instalar Node
LTS y luego `npm i remotion @remotion/cli` en la carpeta del proyecto.

## Mejores pautas (verificadas 2026-10-04, Remotion 4.0.532, Node 24, React 19)

- **Licencia (no es MIT)**: gratis para individuos y equipos de hasta 3
  personas; organizaciones de 4+ requieren licencia. Consultar
  `remotion.dev/docs/license/faq` antes de proponerlo en una empresa
  grande — el costo es real, no asumir gratuidad universal.
- **Versiones fijadas**: todos los paquetes `@remotion/*` deben quedar en
  la misma versión exacta, sin `^` (ej. `4.0.532`). El scaffolder oficial
  `npx create-video@latest` ya lo deja así. Ojo: `npx remotion@latest new`
  **no funciona** — el paquete `remotion` no declara ningún binario (el CLI
  vive en `@remotion/cli`), así que npm responde "could not determine
  executable to run". Verificado contra el registro de npm.
- **`tsc` correcto**: `npx tsc --noEmit` sin el paquete `typescript`
  instalado descarga el obsoleto `tsc@2.0.4` (NO valida nada). Después de
  `npm install`, usar `./node_modules/.bin/tsc --noEmit` o `npm run lint`.
- **Browser del render**: `npx remotion render` descarga
  `chromium-headless-shell` desde remotion.media al primer render. Si la
  descarga falla o no hay red, `--browser-executable RUTA` reutiliza un
  headless-shell existente (verificado reutilizando el de HyperFrames:
  `~/.cache/hyperframes/chrome/chrome-headless-shell/linux-*/.../chrome-headless-shell`).
- **Render verificado**: composición 8s 1080×1920@30 (letras animadas,
  anillo, count-up, tagline, fade) → 371.9 kB H.264 en 54s con el
  headless-shell reutilizado; QA limpio (auto_qa: solo flags en tramos
  casi estáticos + fade final intencional). Determinista frame a frame
  si se respetan las reglas (sin `Math.random()`, wall clocks, timeouts
  ni CSS transitions).
- **publicDir ligero**: Remotion copia la carpeta pública entera en cada
  bundle. Solo lo que el render lee (cortes finales, JSON, música, logos);
  los brutos e intermedios pesados van fuera.
- **QA por frames**: `npx remotion still {composicion} --frame=N` para mirar
  momentos clave antes del render completo. Mucho más barato que renderizar.
- **Renders largos**: `--timeout` alto (el primer frame de un video largo
  tarda), `--hardware-acceleration` cuando aplique; los renders se lanzan
  como proceso independiente, no bloqueando el chat.
- **`delayRender`/`continueRender`**: para assets asíncronos (fuentes,
  imágenes remotas). Sin esto, frames con assets sin cargar.
- **Física**: `spring()` de Remotion para entradas con resorte (equivale
  al motor de fluidez de `render_plan.py`: overshoot ≤8%, un solo rebote).
- **FPS fijos y dimensiones fijas** por composición; no mezclar 24/30 fps
  en el mismo proyecto sin conversión explícita.
- **Audio**: `staticFile()` para rutas; verificar que cada clip con pista
  de audio la conserve en el montaje (un clip sin audio rompe mezclas
  que asumen `[k:a]`).

## Cómo convive con EditorIA

- EditorIA puede **generar los assets** (PNG con alfa, JSON de tiempos,
  guion) y Remotion componerlos — o al revés: Remotion renderiza una
  escena compleja y `aplicar_edl.py`/ffmpeg la integra al montaje.
- **`/remotion-to-hyperframes` confirmado (one-way)**. Migra mecánicamente
  ~80% de una composición típica (`useCurrentFrame`/`interpolate` →
  tweens, `Sequence` → clips, frames → segundos) y valida con SSIM
  frame-por-frame escribiendo `TRANSLATION_NOTES.md`. Se niega a traducir
  state machines React (`useState`/`useEffect`) y UI kits de terceros
  (MUI/Chakra/shadcn): ahí sugiere interop, no migración.
- Regla: si la pieza se resuelve en <10 escenas del plan, el motor Python
  suele ser más rápido. Remotion brilla a partir de lógica que Python
  expresaría con dificultad.

---

→ Canónico: `references/capacidades.md` · Dominio: opcional · Vecinos: `references/hyperframes.md`, `references/instalacion.md`, `references/prompt-motion-graphics.md`
