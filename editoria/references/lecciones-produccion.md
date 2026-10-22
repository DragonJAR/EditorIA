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
