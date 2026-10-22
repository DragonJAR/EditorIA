# Modos rápidos — recetas para piezas simples

Para trabajos que no justifican un plan completo ni una composición libre.
Cada receta es un procedimiento, no un motor nuevo: usa ffmpeg + PIL +
`scripts/musica.py`.

## quick-kinetic — tarjeta cinética (una frase, 3-6s)

Una frase que entra palabra por palabra sobre fondo vivo. Ideal para claims,
bumpers y CTAs.

**Es una escena `apertura` de un plan**, no un render suelto: el titular
entra PALABRA por palabra (un tiempo por palabra en `at.p1`) y `texto2` toma
el relevo en `at.cambio`.

```json
{"tipo": "apertura", "from": 0, "to": 4,
 "texto1": ["Ya se acaba el reto", "EditorIA en un click"],
 "texto2": ["EditorIA en un click"],
 "at": {"cambio": 2.4, "p1": [0.3, 0.6, 0.9, 1.2, 1.5, 2.0], "p2": [2.6]}}
```

```bash
python scripts/auditar_plan.py plan.json
python scripts/lint_copy.py plan.json
python scripts/render_plan.py plan.json -o carta.mp4 --blur 5
python scripts/qa_entrega.py carta.mp4 --plan plan.json
```

- `at.p1` lleva **un tiempo por palabra** de `texto1`, no por línea: las
  palabras que falten siguen la cadencia sola.
- `texto1` admite **2 líneas como máximo** (el linter de copy falla con
  más: "N lineas para un titular").
- Salida: fade de 0,3 s. Duración 3-6 s según la longitud.
- Tipografía: la de titulares del brand pack (ExtraBold; en modo libre, una
  sans geométrica de peso alto). Fondo: el vivo del motor, con el acento del
  pack o de la paleta elegida (`references/paleta.md`).

## quick-montage — montaje de clips con música (15-60s)

Varios clips unidos con ritmo, para resúmenes y reels.

```bash
# 1. la música primero: es la que dicta los cortes
python scripts/musica.py gen --prompt "energia alta, percusion, 120 bpm" --dur 45 -o mus.mp3
python scripts/beat_grid.py mus.mp3 --json grid.json      # la rejilla para cortar en el beat

# 2. normalizar los clips al mismo formato (vertical)
python scripts/ffmpeg_tools/montaje.py escala c1.mp4 --tamano 1080x1920 -o c1v.mp4
python scripts/ffmpeg_tools/montaje.py escala c2.mp4 --tamano 1080x1920 -o c2v.mp4

# 3. unir (el orden lo decide la energía: gancho primero, cierre con CTA)
python scripts/ffmpeg_tools/montaje.py unir c1v.mp4 c2v.mp4 -o montaje.mp4

# 4. la música debajo, con su fade de salida
python scripts/musica.py musiconly -v montaje.mp4 -m mus.mp3 -o final.mp4

# 5. la puerta
python scripts/qa_entrega.py final.mp4
```

1. **Normalizar clips**: misma resolución/fps
   (`--tamano 1080x1920` para vertical; `montaje.py escala` no reescala fps,
   así que si los clips vienen a tasas distintas, conviene convertirlos antes).
2. **Ordenar por energía**: gancho primero, cierre con CTA.
3. **Cortes al beat**: marcar los beats de la música con `beat_grid.py`
   (o cada 2-4s) y cortar ahí; `scripts/beat_sync.py` mide la sincronía del
   montage contra la rejilla.
4. **Transiciones**: según `reglas.transiciones` del brand pack (corte seco o
   libres: mancha/blur); sin pack, según el tono.
5. **Música**: `musica.py gen` con prompt de energía acorde + `musiconly`.
6. **Texto overlay mínimo**: kicker + cifra por clip, nunca párrafos.

## quick-cut — recorte/adaptación de un video existente

1. **Recortar**: `-ss INICIO -to FIN -c copy` (rápido) o re-encode si el corte
   no cae en keyframe.
2. **Verticalizar** un horizontal: `scripts/ffmpeg_tools/verticalizar.py`
   (`--modo crop` con `--crop-y` para no decapitar al hablante, o `--modo blur`
   para pillarbox vivo). Ver `scripts/ffmpeg_tools/verticalizar.py --help`
   si se necesita control fino.
3. **Subtítulos**: si se piden, palabra por palabra, en la banda central
   (nunca abajo: la UI de la plataforma los pisa — ver `checklist-qa.md`),
   con fondo semitransparente — nunca queman la cara del hablante.
4. **Remaster**: `musiconly` para cambiar la música sin tocar el video
   (`-c:v copy`).
5. **Validación de cortes contra transcripción**: ningún corte puede caer
   dentro de una palabra — cruzar los timestamps del corte con la
   transcripción (segmentos start/end/text); si un corte cae dentro, auto-
   expandir el boundary con margen 0.3s y re-verificar antes del render.

## quick-cut v2 — rough-cut con retakes

Para grabaciones con muletillas, silencios y tomas falsas:

1. `scripts/ffmpeg_tools/transcribir.py video.mp4 --language es`: ASR local →
   SRT + JSON de segmentos (si no hay transcripción previa).
2. `scripts/ffmpeg_tools/silence.py`: elimina silencios largos — con **umbral calibrado al
   piso de ruido**: medir el piso F y usar umbral = F+6dB, nunca −30dB fijo.
   Guard de rango dinámico: si S−F<8dB, no confiar en silencedetect.
   `--edl cortes.edl` guarda los rangos a conservar.
3. `scripts/retakes.py segmentos.json`: detección de retakes/false-starts sobre los segmentos
   transcritos — filtros de muletillas y lead-ins ES/EN; regla "la última toma
   gana" (si una isla de sonido es el comienzo de lo que viene después, es un
   false start: se va la primera, queda la última); reporte de "revisar en X.Xs".
   `--edl cortes.edl` guarda los rangos a conservar.
4. `scripts/ffmpeg_tools/aplicar_edl.py video.mp4 --edl cortes.edl -o rough.mp4`:
   aplica el EDL en una sola pasada (corte preciso a frame, micro-fundidos de
   0.03s en las uniones para evitar clicks).
5. **Stretched-word alarm**: una palabra del ASR de duración ≥1s esconde una
   pausa o un retake — revisarla a mano.
6. **Verificación cruzada**: en ventanas dudosas, un segundo ASR independiente
   como detector de tartamudeos antes de renderizar.
7. **Revisión humana** de las tomas marcadas antes de render — el algoritmo
   propone, el usuario dispone.
8. Render final + self-check post-corte (ver `checklist-qa.md`).

## Receta GIF preview (para compartir avances)

GIF de 1–5s del momento clave, two-pass con paleta (solo codifica píxeles
cambiados):

```
ffmpeg -ss {T} -t 3 -i video.mp4 -vf "fps=15,scale=540:-1:flags=lanczos,palettegen=stats_mode=diff" paleta.png
ffmpeg -ss {T} -t 3 -i video.mp4 -i paleta.png -lavfi "fps=15,scale=540:-1:flags=lanczos[x];[x][1:v]paletteuse=diff_mode=rectangle" preview.gif
```

## Variantes A/B (disciplina)

- **Una sola variable por variante**: si cambian dos cosas, el ganador no
  enseña nada.
- **Message-match**: el hook promete exactamente lo que el CTA cumple.
- Convención de nombres que registre qué cambió en cada variante.

## Anatomía de ad 15–30s

hook 0–3s → contexto 3–8s → payoff 8–18s → proof 18–25s → CTA ≥2s.
Arco launch: hook → tease → reveal (al drop) → feature-montage → end-card.

## Notas de ElevenLabs Music

- Mínimo ~42s por generación aunque se pida menos: pedir 45s+ y recortar.
- Nunca nombrar marcas/artistas en el prompt ("al estilo de X" falla) —
  describir el sonido: género, tempo, instrumentación, energía.

## Cache de voz por hash (implementado en `voz_off.py`)

Antes de sintetizar, el path se deriva del hash de texto+voz+modelo
(`~/.cache/editoria/voz/vo_{hash12}.mp3`); si existe y supera ~1500 bytes,
se reutiliza — no se re-paga un segmento idéntico aunque cambie el plan.
El cache por índice se eliminó porque reutilizaba audio viejo si cambiaba
el texto de una escena.

## Editar grabación cruda (cámara/pantalla)

Receta editorial para grabar y cortar footage de cámara o pantalla:

- **In-points**: 0.2s antes del onset acústico (el ASR llega tarde al marcar el
  inicio real de la frase).
- **Comedy air**: tras un punchline, un beat de 0.4–0.6s antes del siguiente
  corte — el silencio vende el chiste.
- **Cold open**: la línea más fuerte del video va ANTES del ident/logo, no
  después.
- **Escalar los dispositivos**: no gastar el efecto más fuerte temprano — el
  takeover mayor va sobre el beat de la tesis, ~al 66% del video.
- **Fade 5ms por defecto en cada corte de diálogo**: los cortes se "declick" solos; el dip
  solo como beat deliberado. (Empalmes de segmentos: 30ms — ver `reglas-tecnicas.md`.)
- **Dev videos**: la pantalla es el héroe, la cara es el PiP.

## Recaps personalizados tipo wrapped

Un `plan.json` parametrizado × tabla de datos → N videos personalizados.

- El plan lleva placeholders `{...}` en los campos que cambian (nombre, cifras,
  highlights).
- Una tabla de datos (CSV/TSV): una fila = un video.
- Un beat por fila de datos: el render itera la tabla y produce un video por
  fila. Para recaps anuales, resúmenes por ponente, versiones por cliente.
- Implementado: `render_plan.py plan.json --datos tabla.csv -o "recap_{id}.mp4"`
  (verificar primero una fila con `--fila 1`; ver `plan-video.md`).
- Arco del recap: de la cifra más chica a la más grande (nunca abrir con la
  cifra héroe: no queda a dónde subir); todo en segunda persona ("Escuchaste
  412 artistas"); cierre = un póster quieto ≥2 s que den ganas de compartir.

## Hook×body batch (A/B de hooks)

Un body × N hooks → N variantes para testear. Herramienta:
`scripts/ffmpeg_tools/variantes.py hook1.mp4 hook2.mp4 cuerpo.mp4 --proyecto X`
(aplica los 4 pasos: preflight, join con stream-copy o re-encode,
loudness-match del hook al body, nombres `{proyecto}_hook{n}_{body}.mp4`).

1. **Preflight** obligatorio por hook: geometría, timebase, avcC match y
   loudness delta contra el body.
2. **Join**: lossless con stream-copy si coinciden parámetros; si no, re-encode
   con el preset/crf del body.
3. **Loudness-match** del hook al body (el hook no puede sonar distinto al
   cuerpo).
4. **Convención de nombres**: `{proyecto}_hook{n}_{body}.mp4` — los N variantes
   se nombran igual, cambia solo el número.
5. QA de cada variante con el gate de `checklist-qa.md` + decodificador
   independiente.

## quick-short — shorts con review-gate (longform → short vertical)

Para convertir una reunión/conferencia en shorts. El render es lo último:
primero se elige, después se edita.

1. **Candidatos**: listar 8–12 segmentos candidatos (15–55s) con timestamps.
2. **Scoring**: puntuar cada uno con la rúbrica de `scoring-shorts.md`
   (hook 0.30, coherencia 0.25, emoción 0.20, valor 0.15, payoff 0.10;
   umbral mínimo 60).
3. **Review-gate**: presentar la tabla puntuada al usuario. Él elige/ajusta.
   Nada se renderiza antes de su aprobación.
4. **Plan antes de render**: escribir `shorts-plan.json` como contrato
   intermedio (schema en `references/shorts-plan-schema.md`: segmento,
   timestamps, hook overlay, captions, música/SFX por beat).
   Ver `pipeline-resumen.md`.
5. **Render**: `scripts/ffmpeg_tools/shorts_plan.py plan.json` — valida el
   contrato y ejecuta la cadena (cortes → hook overlay → captions de marca →
   música ~15 dB bajo la voz → loudness → portada). Cortes alineados a
   fronteras de frase, hook en los primeros 1–3s, specs de plataforma de
   `checklist-qa.md`. Sin re-renderizar lo ya verificado.

## Reglas comunes

- **Todo quick cierra en la puerta**: `python scripts/qa_entrega.py final.mp4`
  (y `scripts/puntuar.py` si la pieza compite por premios), más la versión
  corta de `checklist-qa.md` (3 frames). Una pieza rápida no es una pieza sin
  medir: son las mismas reglas, sin el ritual.
- Si el quick crece (más de 3 textos, narración, escenas), migrar a plan.
- Documentar el fix en `reglas-tecnicas.md` igual que un build grande.

---

→ Canónico: `references/formatos.md` · Dominio: produccion · Vecinos: `references/modos-produccion.md`, `references/pipeline-resumen.md`, `references/scene-patterns-from-internet.md`
