# HyperFrames (integración opcional)

HyperFrames (hyperframes.heygen.com) es el framework open-source de HeyGen
(Apache 2.0, sin fees por render) que convierte **HTML en video de forma
determinista**: la misma entrada produce el mismo MP4 siempre. Un agente
escribe la composición; HyperFrames la renderiza frame por frame con
headless Chrome + FFmpeg. EditorIA **no depende** de HyperFrames — el
motor Python cubre la mayoría de piezas. Esta referencia existe para saber
cuándo es la mejor herramienta y cómo usarla bien.

## Cuándo sugerir su instalación

- El brief pide motion graphics "estilo web" (tipografía cinética,
  diagramas, data-viz, product tours): el agente escribe HTML con
  fluidez y el resultado es editable.
- Se necesita **determinismo**: la pieza se va a re-renderizar cuando
  cambien datos (precios, cifras, SOPs) — la revisión ocurre en el
  archivo fuente, no en un timeline.
- Presupuesto cero en renders y stack web en el equipo.
- Migración desde Remotion (`/remotion-to-hyperframes`).

Instalación: Node 22+ (requisito oficial del README; no 18+), luego en la
carpeta del proyecto la vía oficial no-interactiva es
`npx hyperframes skills update` (instala el core set desde el `main`
actual; el blob de skills.sh puede ir horas atrasado) o, para las 21
skills publicadas, `npx -y skills add heygen-com/hyperframes --all -y`
(verificado 2026-10-04: `--agent '*' -y` también evita el selector
interactivo, que sin flags cuelga sin TTY). Quedan instaladas localmente
al proyecto (`agent/skills/`). Requiere headless Chrome + FFmpeg. El
render local **no exige login ni cuenta** (verificado 2026-10-04). El
router es `/hyperframes`: lee primero, instala cada workflow on demand.

## Cómo funciona

- La composición es un `index.html`: los elementos declaran timing con
  `data-start`, `data-duration` y `data-track-index`.
- La animación usa el runtime que ya conozcas: GSAP, CSS keyframes,
  Lottie, Three.js, Anime.js o Web Animations API.
- CLI: `init` (proyecto), `lint` (estructura estática), `check`
  (runtime en headless Chrome — atrapa errores JS y assets faltantes;
  `validate` está deprecado), `preview` (vista local), `render` (MP4
  final). Nota: `render` **no admite** `--non-interactive`.
- Skills del agente: `/hyperframes` (router/orientación — leer primero),
  `/hyperframes-cli` (dev loop), `/hyperframes-media` (TTS, transcripción,
  remoción de fondo), `/product-launch-video` (URL → video de lanzamiento),
  `/faceless-explainer` (texto → explainer sin cámara),
  `/embedded-captions` (MP4 existente + subtítulos sin tocar el footage).
  (Verificar la lista vigente en https://hyperframes.heygen.com/llms.txt
  antes de invocar un workflow por nombre.)

## Mejores pautas (verificadas 2026-10-04, CLI 0.8.117)

- **`/tmp` y el gate de disco**: `render` aborta si `/tmp` reporta ~0.5 GB
  libres (un tmpfs de 512 MB con 468 MB libres NO pasa). Workaround
  verificado: `export TMPDIR=$HOME/tmp-hyperframes` y
  `--frames-cache-dir ./cache` (la variable
  `HYPERFRAMES_EXTRACT_CACHE_DIR` sola no basta).
- **GSAP local + timeline registrada**: servir `gsap.min.js` como asset
  local y registrar la timeline en `window.__timelines["main"]`; `lint`
  pasó 0 errores/0 warnings y el runtime headless (software rendering,
  sin WebGL) reportó 0 console errors.
- **Render verificado**: composición 8s 1080×1920@30 (letras, anillo,
  count-up 0→18, tagline, fade) → 525 kB H.264 en 1m04s; captura en modo
  screenshot (BeginFrame no corrió sin chrome-headless-shell), con
  static-dedup reutilizando 26% de frames. Sin GPU el capture es lento:
  ~58s de los 64s totales.
- **`lint` + `check` antes de `preview`**: ambos deben pasar; el
  check atrapa lo que el lint no ve (JS roto, assets 404).
- **Determinismo como disciplina**: versionar el HTML; si el render de
  hoy difiere del de ayer, el diff está en el fuente, no en el motor.
- **Assets locales**: nada de URLs remotas en el render (una caída de
  red a mitad de render = video corrupto). Descargar primero.
- **Fuentes**: embeberlas o servirlas localmente; el headless Chrome
  del render no tiene las fuentes del sistema del diseñador.
- **Timing declarativo**: preferir `data-*` sobre `setTimeout` encadenados;
  el framework hace seek por frame y los timeouts no sobreviven al seek.
- **QA**: mirar el preview una vez completo (historia, datos, texto
  legible, sonido) — el primer render no es el corte final.
- **Docs máquina**: https://hyperframes.heygen.com/llms.txt indexa toda
  la documentación para el agente.

## Cómo convive con EditorIA

- EditorIA (Python) para piezas rápidas y motion con física de resortes;
  HyperFrames cuando el proyecto **vive en HTML** o el equipo itera en web.
- El audio de EditorIA (`musica.py`, `medir_mezcla.py`, `sfx.py`) se puede
  mezclar sobre un render de HyperFrames con ffmpeg — los criterios de
  niveles y ducking (`references/audio.md`) aplican igual.
- Handoff (concepto, no implementado): un `plan.json` de EditorIA se
  traduciría 1:1 a una composición HyperFrames (escena → sección HTML
  con `data-start`/`data-duration`).

---

→ Canónico: `references/capacidades.md` · Dominio: opcional · Vecinos: `references/remotion.md`, `references/instalacion.md`, `references/recetas-ai-video.md`
