# Video real — editar grabaciones con personas

Workflow para cuando el material fuente es un video real grabado (talking head,
entrevista, conferencia, demo): cómo cortarlo, limpiarlo, reencuadrarlo y
vestirlo sin que se note el bisturí.

## Pipeline

1. **Probe**: `ffprobe` (o `scripts/ffmpeg_tools/_comun.py: probe()`): duración,
   resolución, fps, audio presente. Nunca asumir.
2. **Rough-cut** (quick-cut v2, ver `references/modos-rapidos.md`):
   `scripts/ffmpeg_tools/silence.py` (quita silencios) → `retakes.py` (corta falsas tomas, "la última
   toma gana", fillers ES/EN, margen 0.3s, nunca dentro de una palabra) →
   **revisión humana** antes de renderizar.
3. **Take-selection** (elegir la mejor toma por frase): numerar las frases del
   guion y etiquetar cada segmento; elegir por frase con la redacción más viva
   (no la más literal); later-over-earlier (la gente calienta: las últimas
   tomas suelen ser mejores); tomar la racha como un segmento para continuidad;
   cut points desde word-times con márgenes (inicio = primera palabra −0.10/
   0.15s, fin = última +0.20/0.30s); pausas >1s se cortan, <0.5s se quedan
   (respetan el ritmo del hablante). Criterios: energía, dicción, mirada a
   cámara — en ese orden.
4. **Validación de cortes**: ningún corte dentro de una palabra (margen 0.3s,
   expandir boundaries, re-verificar). Ver checklist L2 en
   `references/checklist-qa.md`.
5. **Reencuadre a 9:16** (si el destino es vertical): crop centrado en la cara
   con **face-safe framing** — ojos en el tercio superior, la costura nunca
   corta la cara. Verificar en el contact sheet (`look.py`), no a ciegas.
6. **Relleno de saltos**: donde el jump-cut se nota, cubrir con B-roll, foto con
   movimiento (ver "Fotos → dinámicas" en `references/tecnicas-video.md`),
   captura de pantalla o gráfica. Regla: el B-roll se corta sobre el audio del
   A-roll, no en silencio.
7. **Captions**: palabra por palabra, agrupación frase-consciente (nunca
   terminar en leader words), banda central.
   `scripts/ffmpeg_tools/caption.py --phrase-aware --brand brand/tu-marca.json`
   (aplica fuente, colores y posición de marca automáticamente). Con dos o
   más personas (podcast, entrevista): `--hablantes "ANA=FFD400,LUIS=4FC3F7"`
   y cues con prefijo `ANA:` (o un palabras.json con `speaker` de WhisperX):
   cada voz con su color, ningún cue mezcla hablantes (`references/formatos.md`).
8. **Audio**: `scripts/ffmpeg_tools/loudness.py` (−14 LUFS) → cadena de mastering
   (highpass → acompressor → loudnorm → alimiter, ver `references/sonido.md`).
   Si hay música: `musica.py mix` con ducking.
9. **QA**: read-back — transcribir el RENDER y leerlo (detecta repeticiones y
   cortes malos que el plan no revela). Final Frame Contract. Ver
   `references/checklist-qa.md` capas L1/L2/L3.

## Ingesta de referencias y clonación viral

Cuando se parte de un video de referencia o se quiere modelar una estructura viral probada:
1. **Ingesta y separación**: `python scripts/referencia.py --video clip.mp4` (o `--url "..."` vía yt-dlp) extrae metadatos, pistas de audio en 48kHz (edición máster) y 16kHz (transcripción) y contact sheet para revisión visual rápida.
2. **Clonación de estructura y ritmo**: `python scripts/clonar_video.py analizar --video ref.mp4` descompone la pieza en `plantilla.json` y `ANALYSIS.md` (gancho, retención, clímax, CTA).
3. **Generación de variantes**: `python scripts/clonar_video.py variar --plantilla plantilla.json --variantes 3 --tema "Acme"` genera planes listos auditando tiempos de habla con `scripts/speech_estimate.py`.

## Reglas editoriales (grabación cruda)

- In-points 0.2s antes del onset acústico (el ASR llega tarde).
- Comedy air: 0.4–0.6s de beat tras un punchline antes del siguiente corte.
- Cold open: la línea más fuerte ANTES del ident/intro.
- Escalar dispositivos: el efecto/takeover mayor va sobre el beat de la tesis,
  ~al 66% del video. No gastar el efecto más fuerte temprano.
- Fade de 5ms por defecto en cada corte de diálogo (declickeado); dip solo como
  beat deliberado. Para empalmes de segmentos renderizados, la regla es 30ms
  (ver `reglas-tecnicas.md`).
- En videos dev: la pantalla es el héroe, la cara es el PiP.
- Un solo elemento "loud" por pieza; cortes no-metronómicos (la energía del
  guion dicta la granularidad, hasta 0.2s).

## Qué no hacer

- No estirar ni deformar la imagen para llenar el cuadro: crop o blur-pillars.
- No aplicar beauty filters que cambien la cara de la persona.
- No cortar una frase por la mitad para "apretar el ritmo": se reescribe el
  guion o se deja el aire.
- No poner música con letra bajo una voz hablando.

---

→ Canónico: `references/formatos.md` · Dominio: produccion · Vecinos: `references/modos-produccion.md`, `references/tecnicas-reutilizables.md`, `references/montaje.md`
