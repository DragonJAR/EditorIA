# Arquitectura EditorIA

```
plan.json ──▶ render_plan.py ──▶ frames PNG ──▶ codificar_frames ──▶ .mp4 (BT.709)
     │  (+ tabla --datos)│                              └─▶ .mov/.webm (overlay con alfa)
     │                ├── motor de fluidez (resortes, easings, transiciones según pack/tono)
     │                ├── 39 escenas (references/escenas.md)
     │                └── identidad: del brand pack (o modo libre)
     │
     └── formato en references/plan-video.md (tiempos absolutos, at:{})
```

## Componentes
- **scripts/render_plan.py** — renderizador de referencia. Lee un plan.json,
  renderiza cada escena con física de resortes, fondo vivo continuo,
  transiciones según el brand pack o el tono (mancha opt-in por escena) y
  salidas anticipadas. 1080×1920 @30fps (o `tamano` 1920×1080). La extensión
  de `-o` decide el entregable: `.mp4` con fondo, `.mov`/`.webm` overlay con
  alfa verificado. `--datos tabla.csv` = plantilla × tabla (un video por
  fila, placeholders `{columna}` fail-loud; `--fila N` para verificar una).
- **scripts/demo_plan.json** — plan demo de 6 escenas (~30s) sobre EditorIA.
- **scripts/voz_off.py** — voz en off con ElevenLabs: lee el campo "voz" de cada
  escena del plan, genera un segmento por escena y los mezcla en sus tiempos.
  Modelo `eleven_v3` (audio tags de dirección: `[excited]`, `[whisper]`,
  `[slowly]`, `[long pause]`...). Voces por defecto según el idioma del usuario:
  español → Fernanda Sanmiguel, inglés → Brian (`--voz`/`--idioma` para cambiar).
  La API key sale de `$ELEVENLABS_API_KEY` (ver `~/.secrets.env`, nunca en el skill).
  Dirección completa en `references/sonido.md`. La narración manda el reloj:
  mide cada segmento y falla antes de mezclar si una voz pisa a la siguiente.
- **scripts/auto_qa.py** — ojos máquina sobre el render: negros, congelados,
  flashes, silencios, clipping, fotosensibilidad (≤3 destellos/s a fps
  completo), sobresaltos (+6 dB al entrar un corte), costura de loop
  (`--loop`) y contact sheet con zona segura (`--safe`) o zonas de pantalla
  final de YouTube (`--end-screen`). Ver `references/auto-qa.md`.
- **scripts/galeria.py** — el ciclo crear → validar de todo lo animable:
  renderiza las 39 escenas con `scripts/escenas_muestra.json` (la misma
  fuente que el smoke test de `validate_skill.py`) y cada herramienta
  (overlay con alfa, mancha, `--datos`, 16:9, captions, pase, audiograma,
  films, thumbnail), pasa `auto_qa` a cada video y deja `resumen.png` +
  `galeria.json` PASS/FAIL. Modo libre por defecto; `--brand` repite la
  galería con un pack. Correrla tras tocar una escena o primitiva.
- **scripts/medir_animacion.py** — banco de métricas OBJETIVAS de la animación
  (el motor de la mejora recursiva): compone cada escena a fps completo en
  9:16 y 16:9 y mide pops (algo aparece de golpe, con compensación de
  movimiento), tirones, tiempo muerto, densidad de eventos, letra mínima
  asentada, zona segura y costo por frame; nota 0–100 por escena y global.
  `--historial --nota "qué cambió"` agrega la corrida a
  `metricas/historial.jsonl`; `--ver escena:f:seg` guarda el par de frames de
  un pop con los bloques marcados. Ciclo: medir → `--ver` la peor → corregir
  en la primitiva (no en la escena) → re-medir → registrar.
- **scripts/ffmpeg_tools/delivery_check.py** — compliance contra la tabla de
  `_delivery.py` (codec, aspecto, LUFS, true peak; `--end-screen` para la
  pantalla final de YouTube).
- **scripts/ffmpeg_tools/** — kit ffmpeg portado (stdlib-only):
  `scripts/ffmpeg_tools/silence.py` (jump-cuts por silencios),
  `scripts/ffmpeg_tools/loudness.py` (normalización LUFS),
  `scripts/ffmpeg_tools/scenes.py` (detección de escenas + highlights),
  `scripts/ffmpeg_tools/speedramp.py` (rampas de velocidad),
  `scripts/ffmpeg_tools/look.py` (contact sheets para QA visual),
  `scripts/ffmpeg_tools/caption.py` (subtítulos burn/mux, `--phrase-aware`,
  `--brand` con brand pack, fit-size `--max-lines`/`--min-size`,
  `--palabras` = karaoke con el tiempo real de cada palabra de `alinear.py`,
  `--hablantes` = color por hablante para podcast/entrevista; la agrupación
  nunca corta negación+verbo ni cantidad+unidad),
  `scripts/ffmpeg_tools/transcribir.py` (ASR local → SRT + JSON de segmentos),
  `scripts/ffmpeg_tools/aplicar_edl.py` (aplica un EDL: corta y re-ensambla),
  `scripts/ffmpeg_tools/shorts_plan.py` (valida y ejecuta un shorts-plan.json),
  `scripts/ffmpeg_tools/thumbnail.py` (compone thumbnails con marca),
  `scripts/ffmpeg_tools/verticalizar.py` (horizontal → vertical: crop o blur),
  `scripts/ffmpeg_tools/grade.py` (grade de marca para footage, `--to-sdr`
  para HDR),
  `scripts/ffmpeg_tools/artesanal.py` (acabado táctil: grano, papel, parpadeo —
  ver `references/dramaturgia.md`),
  `scripts/ffmpeg_tools/montaje.py` (navaja suiza de edición: unir, cortar,
  fundido, transicion, pip, dividir (pantalla dividida), marca-agua, audio, gif, pase, rotar, voltear,
  bucle, escala, color, velocidad, reversa, limpiar-audio, chroma
  — ver `references/montaje.md`; `pase` = fotos → video con un Ken Burns
  distinto por foto, fondo desenfocado, fundidos y cambios al compás),
  `scripts/ffmpeg_tools/variantes.py` (batch hook×body para A/B),
  `scripts/ffmpeg_tools/_comun.py` (utilidades compartidas: probe, runners,
  puente ASR `transcribir_medio`; `leer_palabras` = lector ÚNICO de tiempos
  por palabra (alinear.py, Whisper/WhisperX con hablante) para subtítulos,
  mosaicos y estimación; `codificar_frames` = ÚNICO encoder de
  frames RGB(A): H.264 BT.709 exacto o alfa ProRes 4444/VP9 con
  `verificar_alfa`; `VF_RGB_A_BT709` para cadenas de filtros; `ayudar(parser,
  propias)` completa el `--help` de toda opción y subcomando con `AYUDAS`, las
  del kit, más las propias del script: un agente aprende la CLI por `--help`).
- **scripts/beat_grid.py** — estima BPM, fase y energía por compás de un MP3
  (para cortes al beat) y `secciones` de la canción por energía (intro,
  subida, pico, valle, outro) con densidad de cortes sugerida; mismo formato
  que `scripts/beat_file.py`. **scripts/beat_sync.py** — ajusta tiempos de corte
  o bordes de EDL a la rejilla de beats. **scripts/medir_mezcla.py** — QA
  numérico del ducking: RMS música vs voz en habla y gaps (ver
  `references/audio.md`). **scripts/chapters.py** — capítulos de YouTube
  desde plan.json o shorts-plan.json.
- **scripts/retakes.py** — detección de retakes/false-starts sobre segmentos
  transcritos (regla "la última toma gana", fillers ES/EN, margen 0.3s, nunca
  corta dentro de una palabra). Completa el quick-cut v2 con `silence.py`.
- **scripts/auditar_plan.py** — audita un plan.json (solapes, duraciones,
  escenas vacías, voz sin texto, huecos, coherencia con `duracion`, tipos
  leídos de `SCENES` de render_plan y que cada voz quepa en su escena sin
  pisar la siguiente, estimada con `speech_estimate.py`: una sola fuente).
  Correr antes de renders largos y antes de pagar TTS.
- **scripts/speech_estimate.py** — estimador determinista de sílabas y duración
  de locución pre-TTS para español e inglés (`estimar_duracion_habla`,
  `auditar_plan_voces`). Cuenta las cifras como se dicen ("$142.332" son
  ocho palabras), deletrea siglas sin vocales y `--calibrar` mide el ritmo de
  una voz real con su palabras.json. Previene desbordes sin coste de API.
- **scripts/referencia.py** — ingesta y análisis de video de referencia (local o
  URL vía yt-dlp): metadatos ffprobe, separación de audio en 48kHz máster y
  16kHz Whisper, y mosaico visual pre-render con `scripts/contact_sheet.py`.
  Descarga un solo video aunque el enlace sea de playlist, H.264 ≤1080p, sin
  pisar archivos (`formato_ytdlp`).
- **scripts/clonar_video.py** — clonación y variación viral de videos (inspirado
  en Hypit): `analizar` descompone el video en `plantilla.json` y `ANALYSIS.md`;
  `variar` genera N variantes únicas de `plan.json` auditadas por `speech_estimate.py`.
- **scripts/contact_sheet.py** — mosaicos de revisión y de lectura de
  referencias: rango (`--inicio/--fin`), muestreo (`-n`, `--cada`, `--en`,
  `--todos-los-frames` con timestamps reales), `--palabras` pone bajo cada
  tile lo dicho en su intervalo, `--alrededor "frase"` ubica el pasaje,
  `--filas` pagina.
- **scripts/proyecto.py** — memoria del proyecto: BRIEF, TRATAMIENTO,
  PROGRESO y TIMELINE/evidencia por referencia; nunca sobrescribe y delega
  la ingesta en `clonar_video.py` (ver `references/referencia-video.md`).
- **scripts/alinear.py** — alineación palabra a palabra de una voz contra su
  guion; sin guion, transcripción con tiempos por palabra de un audio o video
  (archivos intermedios en temporal, nada junto al material).
- **references/referencia-video.md** — clonar/adaptar una referencia: memoria
  del proyecto, ingesta, tiempo visible (palabras, cortes, mosaicos), lectura
  del todo y sus sistemas, ANALYSIS/TIMELINE, lentes de transformación,
  revisión por función y dónde se corrige cada hallazgo.
- **references/formatos.md** — qué sostiene cada formato (talking head,
  podcast, entrevista callejera, ranking, explainer con presentador,
  narración, drama corto) y qué herramienta lo sirve.
- **scripts/audio_viz.py** — visualización de audio (waves/spectrum/freqs,
  overlay dentro de la zona segura) y `--modo audiograma` (portada, título,
  barras espejadas precalculadas por frame, progreso, banda para subtítulos)
  en el acento del pack o el neutro.
- **scripts/musica.py** — música de fondo (ElevenLabs Music `gen`) y mezcla
  profesional (`mix`): ducking sidechain para que la música baje bajo la voz.
  Lecciones ffmpeg: duración explícita del video (nunca `-shortest`), `asplit`
  si un pad se consume dos veces, `apad=whole_dur=` en ambas pistas.
- **references/modos-rapidos.md** — recetas quick: tarjeta cinética,
  montaje con música, recorte/adaptación. Para piezas simples sin plan.
- **references/capacidades.md** — inventario de capacidades: qué valida
  `scripts/check_env.py` (herramientas locales, APIs, assets), capacidades
  multimodales del modelo, MCP y tabla de degradación elegante.
- **references/tecnicas-video.md** — LA BIBLIOTECA: catálogo maestro de técnicas
  2025–2026 (investigación web, 16 secciones): transiciones, tipografía cinética,
  ritmo, cámara, efectos, dataviz animada (sección profunda), fotos→dinámicas
  estilo After Effects, gráficas conceptuales (diagramas que explican ideas),
  partículas, fondos dinámicos, efectos estilo carrusel, hooks, audio, color, IA.
  Cada técnica con qué es, cuándo usarla y estado (fresca/estándar/cansada).
- **references/tecnicas-reutilizables.md** — catálogo de técnicas extraídas del
  video AI Tinkerers #20 (61s): componentes, dataviz, diagramas, ritmo.
  Portar técnicas, no paletas ajenas.
- **scripts/_film.py** — identidad y utilidades compartidas por los films
  (logo a lienzo cuadrado sin deformar, ancla, paleta, wordmark, lema).
- **references/cine.md** — recetas cinematográficas (`scripts/film_marca.py`,
  `scripts/film_marca_v2.py`: v2 con coreografía del isotipo — macro → tercio →
  centro → final asimétrico — y keyhole como ancla compositiva).
- **references/animacion.md** — el oficio del movimiento: 12 principios
  traducidos a motion graphics, motion blur (obturador 180°), curvas de
  easing canónicas, coreografía, cámara virtual, tipografía en movimiento.
- **references/rubrica-premios.md** — gate de entrega: 8 ejes de 1 a 5
  (idea, dramaturgia, animación, composición, sistema, sonido, verdad,
  acabado); ningún eje bajo 4.
- **assets/fonts/** — Plus Jakarta Sans y Montserrat (variables, OFL),
  resueltas automáticamente por `_plataforma.resolver_fuente`.
- **references/direccion.md** — el listón en números: tempo, hits/min, un sistema
  visual por video, un momento firma, copy en statements paralelos.
- **references/scoring-shorts.md** — rúbrica de 5 dimensiones para elegir
  "momentos fuertes" en resúmenes y shorts (puntuar 8–12 candidatos, tabla al usuario).
- **references/tonos.md** — sistema de 6 tonos (demo/resumen/anuncio/trailer/
  parodia/caos): energía, voz, tipografía, ritmo, hook, transiciones y SFX por
  tono. Se elige en el brief, antes del guion.
- **references/sfx.md** — doctrina SFX (mezcla como una pieza con la música,
  tono→energía, momento→sonido, timing). **scripts/sfx.py** — sintetiza el pack
  procedural (click, pop, drop, whoosh, ding, thud, tick, swell).
- **scripts/poster_frame.py** — extrae el frame asentado más fuerte y lo hornea
  como frame 0 del mp4 (controla el thumbnail en Slack/X/Discord) + `*_poster.jpg`.
- **references/share-copy.md** — plantillas de caption por tono; el canon va en
  `share-copy.txt` junto al video.
- **references/audio.md** — beat grid, anchors de SFX, arreglo musical por
  compases (complementa `scripts/beat_grid.py` y `scripts/medir_mezcla.py`).
- **references/thumbnails.md** — craft de thumbnails: reglas, concepto
  estandarizado, calibración a la marca del pack, workflow con review-gate.
- **references/video-real.md** — editar grabaciones reales con personas:
  rough-cut (silence → retakes → revisión), reencuadre face-safe, relleno de
  saltos con B-roll, captions, audio y QA read-back.
- **references/modos-produccion.md** — los tres modos (real, animado, híbrido):
  dónde vive cada efecto y cómo coser la costura real↔animación de forma
  orgánica (puentes visuales, capas sobre footage, continuidad de audio).
- **demo/demo_plan.mp4** — render del plan demo, verificado cuadro por cuadro.

## Flujo de trabajo
1. **Plan**: escribir el plan.json (escenas, tiempos absolutos, `at` por elemento).
   Una idea por escena; tiempos `at` anclados a la palabra/beat.
2. **QA de frames**: renderizar y mirar frames en los tiempos clave
   (`ffmpeg -ss {t} -i out.mp4 -frames:v 1`). MIRAR siempre antes de entregar.
3. **Iterar**: cada defecto visual → fix en el renderer + lección en
   `references/reglas-tecnicas.md`.
4. **Entregar**: el mp4 final + el plan.json (reutilizable).

## Herencia del sistema original
El formato plan.json y los 13 tipos de escena vienen de
`sistema-editor-videos-ia` (pipeline/anuncio.py + remotion/src/promo).
Lo que se conserva: el formato del plan, el catálogo de escenas, las reglas
técnicas probadas. Lo que se recupera en v1.0.0: la arquitectura marca-blanca
del sistema original, ahora como brand packs (`brand/*.json`, ver
`references/brand-packs.md`). Lo que se descarta: Remotion como dependencia
(ver `references/remotion.md` para uso opcional) y dependencias de red.
- 2026-10-04 · **Empaquetar el skill excluyendo *.mp4 de film/ y demo/**: El ZIP portable del skill debe excluir los renders (*.mp4 en film/ y demo/): incluirlos llevo el ZIP de 1.2 MB a 271 MB. Comando canonico: zip -qr editoria-v1.0.0.zip . -x '__pycache__/*' '*.pyc' '.frames/*' '*/.frames/*' '*.mp4'. Los renders viven en las carpetas de proyecto, no en el paquete.

---

→ Canónico: `references/plan-video.md` · Dominio: plan · Vecinos: `references/mapa.md`, `references/escenas.md`, `references/qa-entrega.md`
