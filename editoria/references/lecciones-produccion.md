# Lecciones de producción (portadas del sistema original)

Lecciones universales del sistema marca-blanca original (`sistema-editor-videos-ia`,
probado en producción real con series de YouTube). Son independientes de la
marca y del stack: aplican a cualquier pipeline ffmpeg/Python. Las específicas
de Windows/Remotion se omiten; el detalle completo vive en el ZIP original.

## Audio

- **Priming del AAC**: los MP4 traen ~45 ms de priming AAC como audio real —
  la voz queda ~45 ms TARDE respecto a la imagen. Medir el desfase contra
  una referencia y recortar con `atrim`. Si la voz "no empalma" con los
  labios o los cortes, mirar aquí primero.
- **`loudnorm` lineal que no es lineal**: con `linear=true`, si la ganancia
  calculada lleva el pico por encima de TP, ffmpeg pasa a modo dinámico
  **sin avisar** (solo aparece en el JSON como `normalization_type`).
  Receta segura: aplicar la ganancia con `volume` y un `alimiter` solo
  para picos, en vez de confiar en el modo lineal.
- **`apad` sin `whole_dur` no termina**: en una pasada a `-f null` genera
  audio infinito. Acotar siempre la duración.
- **Umbral de voz relativo**: el umbral de silencio debe ser relativo al
  nivel de la voz (voz − 24 dB), no un valor absoluto contra el ruido.
  El ruido que roza el umbral trocea los silencios.
- **Finales de frase comidos**: la última sílaba se dice flojo, bajo el
  umbral. Colas con umbral suave (umbral − 7 dB), salvando caídas ≤ 60 ms;
  fundido de salida de 20 ms. Si un corte cae sobre voz clara, se avisa.
- **Música que no tapa**: elegir pistas con poca energía en 300–3400 Hz
  (banda de la voz) y nivel estable (σ < 2 dB, sin saltos > 7 dB).
  Entrada 1–1,5 s, salida 2–3 s con fundido.

## Video

- **VFR**: el móvil graba con framerate variable. Normalizar a fps fijo
  antes de cortar y comprobar que vídeo y audio tienen el mismo número
  de fotogramas.
- **Cámara frontal = espejo**: aplicar `hflip` siempre; comprobar con un
  texto en cuadro (sudadera, póster) antes de procesar.
- **Rotación del móvil**: comprobar `ffprobe` (puede venir a −180°) y un
  fotograma del bruto antes de cortar; ffmpeg la aplica al recodificar.
- **`select` con cientos de tramos falla** ("Cannot allocate memory"):
  codificar por bloques (~40 tramos, `-ss` + `-copyts`) y unir con concat
  sin recodificar.
- **Verificar con decodificador independiente**: hay renders que pasan QA
  en ffmpeg y se congelan en otro player. (También en `checklist-qa.md`.)

## Transcripción y corte

- **No fiarse de los tiempos de palabra para cortar**: Whisper mete pausas
  dentro de palabras y se salta repeticiones. Decidir los cortes con la
  **energía del audio**; los tiempos de palabra solo anclan subtítulos.
- **Palabras cortas al inicio de frase** salen con duración 0 y tarde:
  retroceder el inicio hasta 250 ms mientras haya voz.
- **Palmada en agudos** (2–7 kHz), no en la envolvente de voz; el móvil
  empieza con silencio digital que confunde a los detectores de inicio.

## Formato y entrega

- **Números en español YouTube**: «85,6 mil», «1,23 M» — nunca «K».
- **Procesar en disco local**: los servicios en la nube con streaming
  cuelgan ffmpeg en lecturas aleatorias; copiar lineal, procesar local,
  subir al final.
- **Rutas**: en JSON/Python usar siempre `/`, nunca `\` (se convierte en
  caracteres de control dentro de strings).
- **Subtítulos**: anticiparse a la palabra hasta 0,45 s es estilo; llegar
  más de 0,12 s tarde es error.

---

→ Canónico: `references/auto-mejora.md` · Dominio: operacion · Vecinos: `references/instalacion.md`, `references/auto-qa.md`, `references/mapa.md`

## Ejemplos de punta a punta

Movidos desde el SKILL.md (que se queda con el ejemplo 1 y el enlace).

### Ejemplo 2: Animated Meeting Summary

User says: "Summarize this meeting transcript into a vertical video"

Actions:

1. Extract 6 to 10 verified highlights from the transcript (`references/scoring-shorts.md`) with zero invented text.
2. Select the `resumen-animado` style from `references/estilos.md`.
3. Build the sequence per `references/pipeline-resumen.md` and inspect key frames with `scripts/contact_sheet.py`.
4. Close at the gate: `python scripts/qa_entrega.py resumen.mp4` and `python scripts/puntuar.py resumen.mp4 --ejes "1=4,2=4,4=4,5=4,7=4"` (axis 4 by eye: an edit has no plan to measure).

Result: Vertical summary video highlighting verified moments with spring transitions and clean safe zones, approved by the gate.

### Ejemplo 3: Add Background Music to an Existing Video

User says: "Add background music to this video"

Actions:

1. Generate music with `python scripts/musica.py gen --prompt "cinematic warm ambient" --dur 30 -o mus.mp3` (without an API key: `musica.py cama`).
2. Mix with fade-out: `python scripts/musica.py musiconly -v video.mp4 -m mus.mp3 -o mezclado.mp4`.
3. Close the mix: `python scripts/ffmpeg_tools/loudness.py mezclado.mp4 -o final.mp4 -I -14 --tp -1.5` (without this step the gate fails ~−18 LUFS).
4. Close at the gate: `python scripts/qa_entrega.py final.mp4` and `python scripts/puntuar.py final.mp4 --ejes "1=4,2=4,4=4,5=4,7=4"`.

Result: `final.mp4` with balanced background music, platform loudness, and gate approval.

### Ejemplo 4: Iterate on a QA Defect

User says: "Fix the clipped title in scene 2"

Actions:

1. Adjust the scene copy or renderer layout (`references/reglas-tecnicas.md`) and re-run `python scripts/render_plan.py plan.json -o ad.mp4`.
2. Re-gate the piece: `python scripts/qa_entrega.py ad.mp4 --plan plan.json` (and `puntuar.py` with the same axes as before).
3. Record the lesson with `python scripts/registrar_aprendizaje.py --titulo "Que aprendimos" --detalle "Lo que se vio y por que"`.

Result: Defect resolved, piece re-gated, lesson logged.

## Pruebas de activación de la skill

Should trigger:

- "make me a video"
- "summarize this meeting into a reel"
- "edit this ad and make it more dynamic"
- "improve this video and add background music"
- "turn this transcript into a vertical short"
- "create a brand bumper"
- "make one like this video, but for my product"
- "turn this podcast into a split-screen clip with colored captions"
- "check this video before I send it to the client"
- "make it viral / prepáralo para TikTok y Reels"
- "put our brand on it (here is the logo)"

Should NOT trigger:

- "edit this document"
- "improve this text"
- "make me a static image"
- "summarize this PDF in text"
- "what video camera do you recommend"

## Problemas frecuentes

### Error: Render stops mid-way without traceback

Cause: The render process was terminated by a command timeout or memory limit rather than a code error.

Solution:

1. Check if the process is still running with `pgrep -f render_plan`.
2. Re-run `python scripts/render_plan.py plan.json -o out.mp4` without `--force` so incremental frame caching resumes from the last rendered frame.

### Error: Clipped text at frame edges

Cause: Text bypassed auto-fit width limits or used an off-center anchor (`references/reglas-tecnicas.md`).

Solution:

1. Keep auto-fit width `<= 1000px` on 1080px canvases and center with `cx = W / 2`.
2. Verify safe-zone margins with `python scripts/medir_animacion.py` and `references/coherencia-espacial.md`.

### Error: Empty scenes after intro in FFmpeg overlays

Cause: FFmpeg `overlay` filter synchronizes streams by presentation timestamp (`PTS`).

Solution:

1. Reset clip timestamps with `setpts=PTS-STARTPTS` before chaining `overlay` filters (`references/reglas-tecnicas.md` and `references/media-hard-rules.md`).

### Error: Text renders smaller than the scene next to it

Cause: The scene's content is taller or wider than the safe zone, so the engine
shrinks everything to fit (`references/reglas-tecnicas.md`).

Solution:

1. Give the scene its own `zona` (the box it occupies) so the rest of the piece
   does not get shrunk with it.
2. Re-measure with `python scripts/medir_animacion.py`.

### Error: Large `.frames` cache directories

Cause: Uncompressed intermediate PNG frames (~1.5 GB per minute at 1920x1080) remain on disk after interrupted renders, or after renders run with `--conservar-frames`.

Solution:

1. `render_plan.py` deletes them when the video is encoded; the ones left are from failed renders (kept to resume) or kept on purpose. Delete those after final delivery; never store them inside the skill folder.
