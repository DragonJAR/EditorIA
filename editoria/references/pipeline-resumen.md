# Pipeline: resumen animado (estilo v2 — LEGACY)

> LEGACY: documenta el pipeline del v2 (2026-10-03). Para piezas nuevas, la
> doctrina vigente está en `principios.md`, `coherencia-espacial.md` y
> `ritmo.md` — en caso de conflicto, mandan ellos (ej. sin rejillas
> decorativas, música ~15 dB bajo la voz).

Probado en un resumen real de 62 s, 1080×1920, 30 fps.

## 0. Plan antes de render (contrato intermedio)

Ninguna pieza multi-etapa se renderiza sin un plan escrito que actúe como
contrato. El plan fija qué, cuándo y dónde de cada escena; el render solo lo
ejecuta. Si el material se re-edita, el plan se reescribe, no se parchea el
render. Para shorts, el contrato es un `shorts-plan.json` (segmento,
timestamps, hook overlay, captions, música/SFX por beat). Para piezas con
narración, los campos `voz` del plan llevan las marcas de dirección
(ver `sonido.md`). Patrón review-gate: proponer → aprobar → renderizar.

## 0b. Narration-first (piezas con deck/audio)

La duración de cada escena = la duración real de su audio, medida con
`ffprobe` (o el reporte de `voz_off.py`). Flujo: generar la VO primero, medir
cada segmento, y el plan/escena se estira o recorta a esa medida — nunca se
timan las escenas a ojo y se espera que la voz encaje.

> Los tres scripts de este pipeline (`gen_bg.py`, `gen_elements.py`,
> `build_v2.py`) son **del proyecto**: se escriben por pieza en la carpeta de
> trabajo, siguiendo esta receta. No vienen en la skill.

## 1. Fondo animado (`gen_bg.py`)
- 1080×1920, N fotogramas PNG (`bg_%04d.png`).
- Ondas sinusoidales: 5–8 trazos con `ImageDraw.line(..., joint="curve")` sobre capa RGBA,
  alfa 20–35, colores del acento en tonos profundos. Fase animada con el tiempo.
- ~0,2 s/fotograma en PIL → 1860 fotogramas ≈ 6 min. Lanzar en segundo plano.

## 2. Elementos (`gen_elements.py`)
- Un PNG con alfa por elemento (`el/`). Helpers: `kicker()` (mono + letterspacing),
  `pill()`, `center_text_img()`, tarjetas, badges, iconos geométricos simples.
- Grillas que se encienden: PNG base + un PNG por celda encendida + `grid_pos.json`
  con las coordenadas.
- Secuencias (filas de teléfono, proveedores): un PNG por paso + JSON de posiciones.
- Revisar SIEMPRE los PNG en pantalla antes de ensamblar: buscar texto desbordado
  (el header del badge se salió una vez: bajar tamaño/letterspacing), iconos rotos,
  cubos isométricos desproporcionados.

## 3. Ensamblaje (`build_v2.py`)
- Genera el comando ffmpeg: fondo como input 0 (`-framerate 30 -i bg_%04d.png`),
  cada elemento con `-loop 1 -framerate 30 -t {dur}`.
- Por elemento: `format=rgba, fade in/out (alpha=1), setpts=PTS-STARTPTS`.
- Overlay encadenado con `enable='between(t,a,b)'`. Entrada con elevación:
  `y='{Y}+50*max(0,1-(t-{A})/0.45)'` (escapar comas con `\` en filter_complex_script).
- Escribir el filtro en `filter.txt` y usar `-filter_complex_script`.
- Salida: `libx264 -crf 20 -preset medium -r 30 -pix_fmt yuv420p`, `-t {DUR}`.
- ~55–65 overlays es manejable para ffmpeg.

## 4. QA y entrega
- `ffprobe`: duración, 1080×1920, 30 fps.
- Fotogramas con `ffmpeg -ss {t} -frames:v 1`: verificar ≥1 por segmento
  (intro, cada ponente, outro): texto legible, sin solapes, sin desbordes.
- Para entregas long-form de YouTube, generar capítulos desde las secciones
  del plan + sus duraciones acumuladas (`scripts/chapters.py plan.json`):
  una línea `m:ss Título` por sección.
- Entregar el MP4 adjunto en el chat.

## Lecciones del sistema original (`sistema-editor-videos-ia.zip`)
Adaptadas de su `CLAUDE.md` (Windows/Remotion; lo portable a este entorno Linux):
- Catálogo de escenas reutilizable: `revealStat` (cifra heroica), `bars` (comparativa),
  `lineup` (fichas), `pasos`, `notificacion`, `buscador`, `comentario`, `outro`.
- Música ~15 dB bajo la voz (verificado con `medir_mezcla.py`); SFX sutiles alineados al fotograma del golpe.
- Miniatura: cara a la derecha, izquierda vacía y oscura, texto ≤4 palabras
  (ver `references/thumbnails.md` — el QA de thumbnails manda sobre esta nota).
- Vertical: gancho en los primeros 2,8 s; subtítulos en zona segura (y≈1420 en 1920).
- Regla de oro: mirar los fotogramas antes del render completo, siempre.

---

→ Canónico: `references/formatos.md` · Dominio: produccion · Vecinos: `references/scoring-shorts.md`, `references/modos-rapidos.md`, `references/video-real.md`
