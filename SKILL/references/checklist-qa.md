# Checklist QA (obligatorio antes de entregar)

**Loop cerrado primero**: `python scripts/auto_qa.py video.mp4` y mirar el
contact sheet — ver `references/auto-qa.md`. La máquina detecta, tus ojos
confirman, tú corriges. Nada llega al usuario sin pasar el loop.

**Capas**: L1 técnica (Base + specs) · L2 diálogo/boundaries · L3 visual/marca
(Pilares + Fluidez + Referencias y framing + Thumbnail).

## Pilares (ver `principios.md`)
11. **Coherencia visual**: un solo acento de color, un solo sistema tipográfico,
    un solo sistema de componentes en todo el video.
12. **Armonía espacial**: retícula vertical consistente entre bloques; sin solapes
    entre elementos que comunican; jerarquía kicker → titular → visualización → caption.
13. **Efectos acordes**: cada efecto presenta información; el fondo no compite;
    entradas con fade + elevación, revelados secuenciales en datos que se cuentan.

## Fluidez (ver `fluidez.md`)
14. **Resortes**: toda entrada usa resorte o easeOutBack; nada aparece lineal.
15. **Fondo vivo**: el fondo se mueve en cada escena; verificar a 0.5x que no haya
    fotogramas congelados ni apariciones bruscas.
16. **Transiciones**: el idioma de transición lo fija el brand pack o el tono
    (ver `references/brand-packs.md`); salidas anticipadas 0.5s.
16b. **Oficio de animación** (`animacion.md`): overlapping entre capas
    (60–120 ms), arcos en recorridos largos, anticipación en los golpes y
    **motion blur en la entrega final** (frame en pleno movimiento
    desenfocado, frame asentado nítido).
16c. **Rúbrica de premios** (`rubrica-premios.md`): ocho ejes puntuados sobre
    el render final; ningún eje bajo 4, media ≥ 4.3. Si no pasa, no se entrega.

## Base
1. **Fuente**: cada cifra/nombre/cita verificada contra el material fuente. Nada inventado.
   Los badges de ponente se re-auditan en cada versión: ningún asset de texto se
   hereda sin volver a verificarlo (el "Agidra" sobrevivió 3 versiones por esto).
2. **Ortografía**: tildes y mayúsculas en español. Leer cada tarjeta en voz alta una vez.
3. **Texto desbordado**: ningún texto sale de su tarjeta/píldora (revisar en PNG antes de ensamblar).
4. **Márgenes**: todo dentro del 8% de margen seguro en 1080×1920.
5. **Fotogramas**: extraer ≥1 por segmento y mirarlos (`ffmpeg -ss T -frames:v 1`).
6. **Ritmo**: cada tarjeta 2,5–3 s (cinético) u 8–13 s por bloque (resumen animado).
7. **Cortes**: según `reglas.transiciones` del brand pack (default: corte que cruza — la saliente se va debajo de la entrante, sin frames vacíos — con micro-fade de 30 ms en la entrada contra pops)
   (ver `reglas-tecnicas.md`); fades largos (0,3–0,45 s) solo en entradas/
   salidas de elementos.
8. **Color**: neutro oscuro dominante; el acento del brand pack (o el elegido
   en modo libre); texto en el neutro claro.
9. **Logo**: solo PNG oficiales, sin redibujar ni deformar.
10. **Técnico**: `ffprobe` → 1080×1920 (o 1920×1080), 30 fps (24 fps en piezas de cine), duración esperada ±0,5 s.
11. **Pitfalls ffmpeg** (L1): `-atempo` causa drift A/V por segmento; `concat
    -c copy` rompe timestamps de audio; un overlay sin `-map` pierde el audio;
    `-shortest` trunca el audio final.
12. **Ducking verificado** (L1, piezas con voz): `scripts/medir_mezcla.py` →
    música ~15 dB bajo la voz durante el habla. Sin medición, no hay entrega.
13. **Gate de verificación** (L1, piezas con persona): `ffprobe` → 9:16, h264,
    yuv420p, audio presente; contact sheet de frames; face check en cada frame
    con persona (cara nunca cortada).
14. **Unidades ASS** (L1, captions quemados): karaoke `\k` en centisegundos,
    `\t` en milisegundos — no mezclar unidades. Tiempos monótonos, sin solapes.
15. **PSNR-vs-control** (L1, fuentes burneadas): libass hace fallback silencioso
    si la fuente no existe. Validar: renderizar una versión con nombre de fuente
    inexistente y comparar PSNR (15–20dB ⇒ la fuente sí se aplicó). Si el PSNR
    es ~0, el render usó la fuente de fallback, no la de marca.
16. **Self-check post-corte** (L1): median cut y % de compresión contra el
    objetivo del modo; en material retake-heavy, juzgar por compresión, no por
    median. Si la compresión se desvía >15% del objetivo, revisar boundaries.
17. **Pops scan** (L1): buscar spikes de frame-diff >3× los vecinos — cazan
    flashes/pops accidentales en el render.
18. **Loop seam check** (L1, piezas con loop): comparar frame 0 vs último frame
    (misma composición, posición y color). Si no empalman, el loop se nota.

## L2 — Diálogo y boundaries

1. **Boundary check en cada corte de diálogo**: palabras cortadas al inicio/fin,
   frases duplicadas en la unión, aire muerto en la costura, clics de empalme
   (butt-splice), cobertura de captions en todo el corte.
2. **Read-back QC**: transcribir el RENDER y leerlo — detecta repeticiones,
   cortes a mitad de palabra y hooks truncados que la lectura del source no
   revela. No basta con revisar el plan.
3. **Decodificador independiente**: verificar el render con un decodificador
   distinto al que codificó (solo-ffmpeg no basta; hay renders que pasan QA
   en ffmpeg y se congelan en otro player).
4. **tooFast** (L2, captions): si un cue tiene demasiado texto para su duración,
   es un defecto — recortar el texto o dividir el cue.
5. **Transcript ≠ display** (L2): el subtítulo se edita para legibilidad, pero
   nunca se añaden palabras no dichas. Solo corregir, nunca inventar.
6. **Captions LAST** (L2): los captions se queman DESPUÉS de todos los overlays,
   para que nada los tape.
7. **Self-eval en boundaries + waveform final** (L2): revisar cada boundary de
   corte y el waveform del archivo final (no de las fuentes).
8. **Doble pasada de crítica** (L2/L3): motion critic + design critic como
   lecturas separadas; default: rechazar. Dos ojos distintos cazan defectos
   distintos.

## Renders versionados

Guardar cada render como `final_v1…vN`; nunca sobrescribir. No re-experimentar
con patrones ya aprobados por el usuario.

## Referencias y framing
- **Disciplina de referencias**: de una referencia solo se toma lo que el usuario
  nombró (color XOR ritmo XOR efecto); si dice "hazlo como este" sin nombrar
  el aspecto, preguntar cuál (¿color? ¿contraste? ¿ritmo? ¿efectos?) antes de
  copiar más de uno. Una referencia no es un pedido de clonar el look.
- **Face-safe framing**: en todo crop de personas, la cara queda centrada en el
  área visible del panel, ojos en el tercio superior. El crop 50%/50% por
  defecto casi siempre corta cabezas: corregir el crop por panel antes de
  aprobar. Cara fuera de centro o cortada = gate fallido.
- **Final Frame Contract** (L3): el último frame del render debe coincidir con
  el asset de marca verificado (logo lockup, end card). Probar el easing
  aplicado en 2–3 timestamps — el linear-por-accidente no se ve en reproducción
  casual.

## Thumbnail (ver `thumbnails.md`)
- Texto ≤4 palabras, legible a tamaño de móvil, entre otros thumbnails
  (test en mockup de homepage). Sin sticker blanco, sin glow blanco; fondo
  negro/charcoal o glow radial del acento; sujeto cinematográfico + un
  solo elemento gráfico; tipografía de titulares del brand pack (ExtraBold).
- Composición en rule of thirds: cara en un tercio, texto en otro, héroe en
  una línea.

## Specs de export por plataforma (verificación pre-entrega)

Valores canónicos en `scripts/ffmpeg_tools/_delivery.py` — la única
tabla que leen las herramientas. `delivery_check.py` los verifica
automáticamente contra el archivo final (esta tabla es el resumen
humano, no una segunda fuente).

| Spec | YouTube Shorts | TikTok | Instagram Reels |
|---|---|---|---|
| Resolución | 1080×1920 | 1080×1920 | 1080×1920 |
| Codec video | H.264 High L4.2 | H.264 | H.264 High L4.2 |
| Bitrate | 12 Mbps (máx 14) | CRF 18 (equiv. ~10 Mbps) | 4,5 Mbps (máx 5) |
| Audio | AAC 192k / 48 kHz | AAC 128k / 44,1 kHz | AAC 128k / 44,1 kHz |
| Loudness | −14 LUFS, TP −1.5, LRA 11 | −14 LUFS, TP −1.5, LRA 11 | −14 LUFS, TP −1.5, LRA 11 |
| Duración máx | 180 s | 600 s | 180 s |
| `movflags` | `+faststart` | `+faststart` | `+faststart` |

Zonas seguras de UI por plataforma (`safe_margins_px()` en `_delivery.py`;
en 1080×1920 TikTok ≈ sup ≥192px, inf ≥422px, izq ≥54px, der ≥151px —
los valores legacy ≥210/≥450/≥60/≥150 siguen siendo válidos como
aproximación). Captions de narración en la banda central, nunca abajo
donde las pisa la UI.

## Quality bar medible (antes de entregar)

Números, no sensaciones:

- **Frozen time**: ≤1s por cada 30s de video (frozen = frame idéntico al
  anterior: nada se mueve en toda la imagen; un elemento estático sobre fondo
  vivo no es frozen); ningún hold >0.6s salvo el CTA final.
- **Loudness**: −14 LUFS (enérgico) / −16 LUFS (calmo), TP −1.5 dB (tolerancia hasta −1), LRA 11 objetivo (mínimo ~3 LU).
  SFX −18…−12 dB bajo la voz, nunca por encima de la narración.
- **Contraste de texto**: WCAG AA en todo texto sobre video.
- **Fotosensibilidad**: ≤3 destellos por segundo (WCAG 2.3.1); sin strobe de
  pantalla completa. `auto_qa.py` lo mide (defecto `fotosensible`).
- **Sin sobresaltos**: ningún corte entra con más de +6 dB sobre el segundo
  previo (`auto_qa.py`, defecto `sobresalto`).
- **Color de marca**: muestrear el acento — debe ser exactamente el del
  brand pack (o el del modo libre), no una aproximación.
- **Frame 0 terminado**: composición completa desde el primer frame, sin
  elementos a medio entrar. Sin colisiones de texto.
- **Sujeto**: 60–85% del cuadro en piezas con persona.
- **En mute se entiende**: qué hace/habla el video + CTA legible a tamaño
  teléfono ≥1.5s.
- **Saturación** (ver "Saturación: dinámico ≠ lleno" en `principios.md`):
  titular + protagonista + máximo 2 apoyos por escena; si el plano tiene un
  protagonista grande, el isotipo no compite con él; si el isotipo aparece,
  lo hace con rol y recurre con el mismo rol en la pieza.

## L4 — Creative gate (antes de entregar)

De `/brag`: la estructura puede pasar QA técnico y aun así fallar como pieza.
Verificar con el plan en mano:

1. **Hook primero**: el hook se planeó antes que el resto y cae en los primeros
   2 s. Sin hook deliberado, no hay video.
2. **Piso de lectura**: cada texto legible cumple el piso de `ritmo.md`
   (0.8 s etiqueta, 0.3 s/palabra). Ninguna escena carga más texto del que su
   duración permite.
3. **Beat locks**: 1–3 momentos mayores enganchados a strong cues (±0.15 s),
   marcados `// beat-lock`; eventos secuenciales en la grilla (±0.10 s),
   marcados `// beat-grid`. O timing natural justificado por legibilidad.
4. **Grounding**: cada afirmación (nombres, cifras, claims) rastreada a la
   fuente; lo inventado es solo oficio (tono, chistes, transiciones).
5. **Poster**: `scripts/poster_frame.py` — frame asentado más fuerte extraído
   y horneado como frame 0 (`*_poster.jpg` junto al mp4).
6. **Share copy**: `share-copy.txt` escrito con la plantilla de `share-copy.md`.
7. **En mute se entiende** (ya en Quality bar): re-verificar con el gate creativo.

## Protocolo Gauntlet (revisión independiente)

El que construye no es el que juzga:

1. **Crítico fresco por ronda** — alguien (o una pasada) que no vio el build.
2. **Juzga píxeles y mediciones**, no intenciones.
3. **Arreglar el gap más grande primero** — un defecto grande antes que diez
   pequeños.
4. **Verificar con crítico nuevo**: FIXED / PARTLY / STILL PRESENT.
5. **Ledger de rondas**: registrar qué se encontró y qué cambió, ronda por ronda.
