# Arquitectura EditorIA

```
plan.json ──▶ render_plan.py ──▶ frames PNG ──▶ ffmpeg ──▶ video.mp4
     │                │
     │                ├── motor de fluidez (resortes, easings, transiciones según pack/tono)
     │                ├── 13 escenas (references/escenas.md)
     │                └── identidad: del brand pack (o modo libre)
     │
     └── formato en references/plan-video.md (tiempos absolutos, at:{})
```

## Componentes
- **scripts/render_plan.py** — renderizador de referencia. Lee un plan.json,
  renderiza cada escena con física de resortes, fondo vivo continuo,
  transiciones según el brand pack o el tono (mancha opt-in por escena) y
  salidas anticipadas. 1080×1920, 30fps.
- **scripts/demo_plan.json** — plan demo de 6 escenas (~30s) sobre EditorIA.
- **scripts/voz_off.py** — voz en off con ElevenLabs: lee el campo "voz" de cada
  escena del plan, genera un segmento por escena y los mezcla en sus tiempos.
  Modelo `eleven_v3` (audio tags de dirección: `[excited]`, `[whisper]`,
  `[slowly]`, `[long pause]`...). Voces por defecto según el idioma del usuario:
  español → Fernanda Sanmiguel, inglés → Brian (`--voz`/`--idioma` para cambiar).
  La API key sale de `$ELEVENLABS_API_KEY` (ver `~/.secrets.env`, nunca en el skill).
  Dirección completa en `references/sonido.md`.
- **scripts/ffmpeg_tools/** — kit ffmpeg portado (stdlib-only):
  `scripts/ffmpeg_tools/silence.py` (jump-cuts por silencios),
  `scripts/ffmpeg_tools/loudness.py` (normalización LUFS),
  `scripts/ffmpeg_tools/scenes.py` (detección de escenas + highlights),
  `scripts/ffmpeg_tools/speedramp.py` (rampas de velocidad),
  `scripts/ffmpeg_tools/look.py` (contact sheets para QA visual),
  `scripts/ffmpeg_tools/caption.py` (subtítulos burn/mux, `--phrase-aware`,
  `--brand` con brand pack, fit-size `--max-lines`/`--min-size`),
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
  fundido, transicion, pip, marca-agua, audio, gif, pase, rotar, voltear,
  bucle, escala, color, velocidad, reversa, limpiar-audio, chroma
  — ver `references/montaje.md`),
  `scripts/ffmpeg_tools/variantes.py` (batch hook×body para A/B),
  `scripts/ffmpeg_tools/_comun.py` (utilidades compartidas: probe, runners,
  puente ASR `transcribir_medio`).
- **scripts/beat_grid.py** — estima BPM, fase y energía por compás de un MP3
  (para cortes al beat). **scripts/beat_sync.py** — ajusta tiempos de corte
  o bordes de EDL a la rejilla de beats. **scripts/medir_mezcla.py** — QA
  numérico del ducking: RMS música vs voz en habla y gaps (ver
  `references/audio.md`). **scripts/chapters.py** — capítulos de YouTube
  desde plan.json o shorts-plan.json.
- **scripts/retakes.py** — detección de retakes/false-starts sobre segmentos
  transcritos (regla "la última toma gana", fillers ES/EN, margen 0.3s, nunca
  corta dentro de una palabra). Completa el quick-cut v2 con `silence.py`.
- **scripts/auditar_plan.py** — audita un plan.json (solapes, duraciones,
  escenas vacías, voz sin texto, huecos, coherencia con `duracion`).
  Correr antes de renders largos.
- **scripts/audio_viz.py** — visualización de audio (waves/spectrum/freqs,
  overlay sobre video) en rojo de marca.
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
- **references/cine.md** — recetas cinematográficas (`scripts/film_marca.py`,
  `scripts/film_marca_v2.py`: v2 con coreografía del isotipo — macro → tercio →
  centro → final asimétrico — y keyhole como ancla compositiva).
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
