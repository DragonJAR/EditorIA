---
name: editoria
description: EditorIA, navaja suiza de creación y edición de video con IA, en vertical (Reels, TikTok, Shorts) u horizontal (YouTube), para cualquier marca o sin marca. Anuncios por escenas, resúmenes animados de reuniones, tipografía cinética, films de marca, rótulos y overlays con transparencia, subtítulos animados y karaoke, pases de fotos, audiogramas, thumbnails, shorts desde videos largos, voz en off y música con ducking; mide y corrige su propia animación antes de entregar. Úsalo cuando pidan "hazme un video", "un reel", "resume esta reunión en video", "ponle subtítulos", "ponle música", "edita/corta/mejora este video", "un lower third", "make a video", "add captions" o "edit this clip".
metadata: { "author": "Jaime Andrés Restrepo", "version": "1.4.0" }
---

# EditorIA

Navaja suiza para crear videos dinámicos y profesionales de cualquier tipo,
para cualquier marca — o sin marca. El listón es cine: cada pieza debe verse
fluida, intencional y digna de un festival, no "un video con IA".
Produce resúmenes animados, tipografía cinética, anuncios, films
cinematográficos y verticales para redes.

**Plataformas**: Windows 10/11, macOS (Intel y Apple Silicon) y Linux.
Instalación por SO: `references/instalacion.md`. Los scripts resuelven
fuentes, temporales y binarios según el sistema operativo.

## Marca: pack o modo libre (leer primero)

EditorIA es marca-blanca. La identidad nunca está hardcodeada: vive en un
**brand pack** (`brand/*.json`, spec en `references/brand-packs.md`).

- **El usuario nombra una marca** → cargar su pack (`brand/dragonjar.json`
  es el ejemplo incluido). El pack fija colores, tipografías, logos, voces
  y reglas; el brief aporta el contenido.
- **El usuario no nombra marca** → **modo libre**: ignorar toda identidad
  de marca y diseñar con criterio cinematográfico puro — paleta, tipografía
  e idioma de transición se eligen según el brief, el tono y lo que la
  pieza pida. El único límite es que se vea intencional y premium.

Regla de oro: **el pack manda sobre el preset; el brief manda sobre todo**.
Nunca inventar identidad de marca (colores, logos, slogans): sin pack,
diseño libre; con pack, fidelidad total.

## Selector de motor (leer primero)

| Brief | Motor |
|---|---|
| Anuncio con escenas y narración | **Plan**: `plan.json` + `scripts/render_plan.py` (28 escenas en `references/escenas.md`, incl. `oferta`, `demo`, `countdown`, `quote`; conceptos extendidos portables en `references/escenas-extendidas.md`) |
| El mismo video para N personas/productos/variantes | **Plantilla × tabla**: `render_plan.py plan.json --datos tabla.csv -o "x_{id}.mp4"` (verificar una con `--fila 1`; `references/plan-video.md`) |
| Rótulos, títulos o gráficos para el editor / OBS (sin fondo) | **Overlay con alfa**: `render_plan.py plan.json -o capa.mov` (ProRes 4444) o `.webm` (VP9); escena `rotulo_inferior`; uso por herramienta en `references/modos-produccion.md` |
| Carpeta de fotos → video | `scripts/ffmpeg_tools/montaje.py pase ./fotos -o pase.mp4` (`--bpm` para cambiar al compás) |
| Clip de podcast/voz para redes | **Audiograma**: `scripts/audio_viz.py audio.mp3 --modo audiograma --titulo "..." --portada cover.jpg` + subtítulos con `caption.py` |
| Resumen de reunión/transcripción | **Composición**: `references/pipeline-resumen.md` + estilos de `references/estilos.md` |
| Film cinematográfico (16:9 o 9:16) | **Cine**: recetas en `references/cine.md` (film de marca de cualquier pack: `scripts/film_marca_v2.py --brand`, `--formato 9:16` para vertical) |
| Tarjeta cinética rápida (una frase) | **Quick**: receta `quick-kinetic` en `references/modos-rapidos.md` |
| Montaje de clips con música | **Quick**: receta `quick-montage` en `references/modos-rapidos.md` |
| Recorte/adaptación de un video existente | **Quick**: receta `quick-cut` en `references/modos-rapidos.md` |
| Short vertical desde un video largo | **Shorts**: `shorts-plan.json` (schema en `references/shorts-plan-schema.md`) + `scripts/ffmpeg_tools/shorts_plan.py` |
| Video real + animación que lo complementa | **Híbrido**: `references/modos-produccion.md` (puentes, capas, continuidad) |
| Video existente + música de fondo | `scripts/musica.py musiconly -v video.mp4 -m mus.mp3 -o final.mp4` |
| Video + voz en off + música con ducking | `scripts/musica.py gen` → `mix` (la música respira bajo la voz) |
| Edición de clips (unir, cortar, fundidos, PiP, GIF, etc.) | **Montaje**: `scripts/ffmpeg_tools/montaje.py` — 18 operaciones (ver `references/montaje.md`) |
| Verificar un entregable contra el spec de la plataforma (codec, LUFS, aspecto…) | **Delivery**: `scripts/ffmpeg_tools/delivery_check.py final.mp4 --platform reels` (specs canónicos en `scripts/ffmpeg_tools/_delivery.py`; contrato CLI en `references/cli-contract.md`) |
| Animación programática compleja (data-driven, componentes) | **Remotion** (opcional): `references/remotion.md` — solo si el motor Python no alcanza |
| Pieza HTML determinista / re-render con datos cambiantes | **HyperFrames** (opcional): `references/hyperframes.md` — `npx hyperframes skills update` |
| Film de motion graphics en una toma (launch, showreel, talking head agresivo) | **Prompts**: `references/prompt-motion-graphics.md` (biblioteca verbatim: showreel viral, launch con variables, SaaS 30 s, batch podcast, costo/tiempo honestos) · **Recetas**: `references/recetas-ai-video.md` (pipeline de 3 agentes, contact-sheet pre-render, beat file compartido, real-assets-first) |

¿No encaja en la tabla? Usar el motor más cercano y componer: los motores son
capas, no silos (un film de marca puede llevar un `quick-kinetic` encima).

Mapa completo del skill: `references/arquitectura.md` — qué hace cada script
(incluido el kit `scripts/ffmpeg_tools/`) y cada referencia.

## Workflow

**A. Por plan (anuncios y piezas con escenas)** — el flujo principal:
0. **Capacidades**: `python scripts/check_env.py` (`references/capacidades.md`).
   Validar primero, prometer después; degradar con honestidad si algo falta.
1. **Plan**: escribir `plan.json` según `references/plan-video.md` (28 tipos de escena,
   en 9:16 o 16:9, tiempos absolutos, `at` por elemento, campo `voz` por escena si
   hay narración). Ver `scripts/demo_plan.json` como ejemplo.
   **Medir antes de renderizar**: `python scripts/medir_animacion.py --plan plan.json`
   (pops, saltos en los cortes, tiempo muerto, letra, zona segura y **textos que
   se pisan** con TU copy; nota 0–100 en ~2 min sin codificar; cada `SOLAPE` sale
   con escena, segundo y los dos textos). Bajo 90, `--ver escena:v:segundo`
   muestra el defecto. Leer también los `AVISO` de campos (un nombre de campo
   equivocado deja la escena vacía sin error) y fijar `"numeros": "es"` si el
   público es hispano y `"subtitulos": true` si se quemarán subtítulos.
2. **Render**: `python scripts/render_plan.py plan.json -o salida.mp4`
   (motor de fluidez: resortes, fondo vivo, transiciones según el brand pack
   o el tono; `--force` para re-renderizar, sin él retoma donde iba).
   Borradores con `--blur 1`; **entrega final con `--blur 5`** (motion blur
   de obturador 180°, ver `references/animacion.md`).
3. **Voz en off** (si se pide): `python scripts/voz_off.py plan.json -o voz.mp3`
   (ElevenLabs, campo `voz` por escena; la narración manda el reloj: falla si
   una voz pisa a la siguiente — `auditar_plan.py` lo estima antes de pagar). **Apartado de sonido**:
   `references/sonido.md` — dirección de voz (tags `[excited]`, `[whisper]`...),
   voces por idioma (la voz por defecto es el idioma en que hable el usuario),
   música y SFX. **Alineación palabra-a-palabra** (opcional, para escenas con
    `at:` por palabra): `python scripts/alinear.py voz.mp3 guion.txt -o
    voz.palabras.json` (whisper local + emparejamiento + refinamiento por
    energía; el plan.json lee los tiempos para anclar animaciones a la palabra
    exacta que se oye).
4. **Música**: `python scripts/musica.py gen --prompt "..." --dur 30 -o mus.mp3`.
   Con voz: `mix -v video.mp4 -a voz.mp3 -m mus.mp3 -o final.mp4` (ducking
   sidechain). Sin voz: `musiconly -v video.mp4 -m mus.mp3 -o final.mp4`.
5. **QA**: `references/checklist-qa.md` + `references/coherencia-espacial.md`.
   Mirar frames en los tiempos clave (`scripts/auto_qa.py`: también
   fotosensibilidad y sobresaltos). Puntuar con
   `references/rubrica-premios.md`: ningún eje bajo 4 o no se entrega.
6. **Iterar y documentar**: cada fix → `python scripts/registrar_aprendizaje.py`
   (protocolo en `references/auto-mejora.md`).

**B. Por composición (resúmenes, piezas libres)**:
0. **Capacidades**: `python scripts/check_env.py` (`references/capacidades.md`).
1. **Brief**: qué pieza, duración objetivo, formato, y qué debe decir.
   Si falta el material fuente, pedirlo — no inventar contenido.
2. **Marca**: ¿el usuario nombró una marca? → cargar su brand pack de `brand/`
   (ver sección "Marca: pack o modo libre" arriba). Si no, modo libre:
   diseñar la identidad visual desde cero según el brief y el tono.
3. **Estilo**: elegir el lenguaje visual en `references/estilos.md`.
4. **Guion visual**: 6–10 momentos fuertes verificados contra la fuente.
   Elegirlos con la rúbrica de `references/scoring-shorts.md` (puntuar 8–12
   candidatos, tabla al usuario si hay que elegir).
5. **Construir**: oficio de animación en `references/animacion.md` (12
   principios, motion blur, cámara, coreografía). `references/pipeline-resumen.md`, técnicas de `references/estilos.md`
   y `references/tecnicas-reutilizables.md`. Para elegir QUÉ técnica usar y cuándo:
   `references/tecnicas-video.md` (catálogo 2025–2026 con estado fresca/estándar/cansada).
   Dirección con métricas: `references/direccion.md`.
6. **QA y entrega**: igual que el flujo A.

## Output Contract

- 1080×1920 @30fps para vertical; 1920×1080 @30fps para horizontal (24fps en
  piezas de cine). H.264, yuv420p, CRF 18–22, **BT.709 convertido y
  etiquetado** (todo frame RGB pasa por `_comun.codificar_frames`: sin eso el
  color de marca se desplaza en navegadores y players). Overlays: `.mov`
  ProRes 4444 / `.webm` VP9 con alfa verificado.
- Audio: voz en off (`scripts/voz_off.py`) y música (`scripts/musica.py`) cuando se pidan;
  con voz siempre hay ducking; sin voz, `musiconly` con fade de salida.
  La API key sale de `$ELEVENLABS_API_KEY` (`~/.secrets.env`) — nunca en el skill,
  en memoria ni en logs.
- Coherencia espacial: `references/coherencia-espacial.md` antes de entregar.
- Delivery: `scripts/ffmpeg_tools/delivery_check.py` contra la plataforma de destino antes de entregar (veredicto PASS; specs y presets en `scripts/ffmpeg_tools/_delivery.py`).
- Piezas premium 16:9: recetas en `references/cine.md`.
- Thumbnails: `references/thumbnails.md` (concepto → review-gate con el usuario → generar).
- Poster: `scripts/poster_frame.py` hornea el frame asentado más fuerte como
  frame 0 del mp4 (lo que capturan los thumbnail-grabbers) + `*_poster.jpg`.
- Share copy: `references/share-copy.md` — caption canónico en `share-copy.txt`.
- Tono: `references/tonos.md` — elegir el tono (demo/resumen/anuncio/trailer/
  parodia/caos) en el brief, antes del guion; el tono manda sobre la técnica.
- Dramaturgia: `references/dramaturgia.md` — estructura de fábula para piezas
  narrativas (lo que premian los festivales) + acabado táctil.
- Audio avanzado: `references/audio.md` + `scripts/beat_grid.py` (beat grid) y
  `scripts/medir_mezcla.py` (QA numérico del ducking).
- SFX: `references/sfx.md` (doctrina: tono→energía, momento→sonido, timing) +
  `scripts/sfx.py` (sintetiza el pack procedural: click, pop, drop, whoosh,
  ding, thud, tick, swell).
- Post-producción (cadenas cerradas, sin pasos manuales sueltos):
  transcribir → retakes/silence → EDL → `scripts/ffmpeg_tools/aplicar_edl.py`;
  `scripts/ffmpeg_tools/shorts_plan.py` valida y ejecuta un `shorts-plan.json`
  (schema en `references/shorts-plan-schema.md`); `scripts/beat_sync.py` ajusta
  cortes a la rejilla de beats; `scripts/chapters.py` genera capítulos de YouTube.
- Ritmo anti-slideshow: `references/ritmo.md` + `scripts/verificar_ritmo.py`
  (cadencia, pausas, ráfagas — el render final no debe leer como PPT).
- Lecciones de producción: `references/lecciones-produccion.md` (audio, video,
  transcripción y entrega — portadas del sistema original).
- Archivo final en la carpeta de salida que indique el usuario (o una carpeta
  de proyecto junto a sus fuentes); nunca dentro de la carpeta de la skill.

## Success Criteria (definición de terminado)

Un video está terminado solo si cumple TODO:
1. **Brief**: dice lo que el usuario pidió, ni más ni menos. Sin texto inventado.
2. **Marca**: con brand pack, fidelidad total a sus colores, tipos y logos
   (sin deformar ni rotar). En modo libre, identidad diseñada con criterio
   y consistente en toda la pieza.
3. **Fluidez y animación**: `references/fluidez.md` — nada quieto sin propósito,
   ningún corte accidental, resortes en las entradas — y `references/animacion.md`:
   overlapping, arcos, anticipación y motion blur en la entrega final.
4. **Coherencia espacial**: `references/coherencia-espacial.md` — alineación
   quirúrgica, sin solapes ni recortes.
5. **Audio**: si lleva música, con cadencia acorde al ritmo visual; si lleva voz,
   ducking aplicado y niveles verificados con `scripts/medir_mezcla.py`
   (música ~15 dB bajo la voz durante el habla).
6. **QA visual y medido**: `scripts/medir_animacion.py --plan plan.json` con nota
   ≥ 90 y 0 pops (o cada pop justificado tras `--ver`), y frames extraídos en
   los tiempos clave y mirados. Sin defectos.
7. **Rúbrica de premios**: `references/rubrica-premios.md` puntuada sobre el
   render final — ningún eje bajo 4, media ≥ 4.3.
8. **Aprendizaje**: cada fix dejó su lección registrada según
   `references/auto-mejora.md`.

## Métricas (guía de skills de Claude)

- **Triggering**: la skill debe activarse en ≥90% de las consultas relevantes
  (probar con 10–20 queries de `Trigger Tests`) y en 0% de las no relacionadas.
- **Ejecución**: 0 llamadas API fallidas por workflow; el workflow completa sin
  que el usuario tenga que corregir el rumbo a mitad de camino.
- **Consistencia**: el mismo brief produce la misma estructura y calidad entre
  sesiones (ver `scripts/validate_skill.py`: 28/28 escenas renderizan siempre).

## Ejemplos

**Ejemplo 1 — anuncio por plan**
Usuario: "Hazme un anuncio de 30 segundos para mi producto"
1. Escribir `plan.json` (ver `references/plan-video.md` y `scripts/demo_plan.json`).
2. `python scripts/render_plan.py plan.json -o anuncio.mp4`
3. QA con `references/checklist-qa.md` (mirar frames en los tiempos clave).
4. Entregar el MP4 adjunto en el chat.
Resultado: `anuncio.mp4` de 30s, 1080×1920 @30fps, H.264, QA limpio.

**Ejemplo 2 — resumen animado de reunión**
Usuario: "Resume la transcripción de esta reunión en un video vertical"
1. Extraer 6–10 momentos verificados de la transcripción (cifras, frases, decisiones).
2. Elegir estilo en `references/estilos.md` (resumen-animado).
3. Construir con `references/pipeline-resumen.md`.
4. QA cuadro por cuadro y entregar.
Resultado: resumen vertical con los momentos clave, motion con propósito, sin texto inventado.

**Ejemplo 3 — iterar sobre un defecto**
QA muestra texto cortado en un frame:
1. Corregir el renderer o el plan.
2. Registrar la lección con `python scripts/registrar_aprendizaje.py --titulo "..." --detalle "..."`.
3. Re-renderizar y verificar el frame.
Resultado: defecto corregido, lección registrada, `SKILL VALIDO`.

**Ejemplo 4 — música a un video existente**
Usuario: "Ponle música de fondo a este video"
1. `python scripts/musica.py gen --prompt "..." --dur {seg} -o mus.mp3`
2. `python scripts/musica.py musiconly -v video.mp4 -m mus.mp3 -o final.mp4`
3. Verificar niveles y entregar.
Resultado: `final.mp4` con música de fondo y fade de salida, niveles en rango.

## Trigger Tests

El skill debe activarse con:
- Obvias: "hazme un video", "resume esta reunión", "edita este anuncio",
  "mejora este video", "ponle música", "créame un reel", "ponle subtítulos",
  "hazme un lower third para OBS", "convierte estas fotos en un video",
  "make a video", "add captions to this clip".
- Paráfrasis: "necesito una pieza para redes", "convierte esta transcripción
  en video", "el video está soso, dale vida", "hazlo más dinámico",
  "quiero un bumper de marca".
- NO debe activarse con: "edita este documento", "mejora este texto",
  "hazme una imagen", "resume este PDF en texto", "qué video me recomiendas".

## Casos funcionales (evaluación)

1. **Plan completo**: `plan.json` de 30s con 6 escenas → MP4 1080×1920 @30fps,
   H.264 yuv420p, sin frames negros ni texto cortado.
2. **Voz + música**: `mix` produce voz al frente y música con ducking audible;
   duración final == duración del video.
3. **Solo música**: `musiconly` produce video + música con fade de salida,
   sin voz.
4. **Resume**: interrumpir `render_plan.py` a mitad y re-ejecutar sin `--force`
   retoma los frames faltantes (no re-renderiza desde 0).
5. **Validación**: `python scripts/validate_skill.py` sale 0 (28/28 escenas
   renderizan dentro de la zona segura, scripts compilan, referencias
   existen) y `python scripts/medir_animacion.py` no baja la nota global
   respecto a `metricas/historial.jsonl`, y `python scripts/galeria.py -o /tmp/galeria` sale todo PASS
   (cada escena y herramienta renderizada de verdad + auto_qa; MIRAR
   `resumen.png`).

## Troubleshooting

**El render muere a mitad (sin traceback)**
Causa probable: el proceso fue matado por timeout o por falta de RAM, no por un bug.
Verificar con `pgrep -f render_plan` si sigue vivo antes de depurar. Los frames se
guardan de forma incremental: re-ejecutar sin `--force` retoma donde iba.

**Texto cortado en el borde**
Causa: falta auto-fit o centro mal calculado. Ver reglas de `reglas-tecnicas.md`
(auto-fit ≤1000px, `cx=W/2` para centrar).

**Escenas vacías después del intro (ffmpeg)**
Causa: `overlay` sincroniza por PTS. Ver regla del `setpts` en `reglas-tecnicas.md`.

**Carpetas `.frames` gigantes**
Son caché de render (cientos de MB). Borrarlas tras entregar; se regeneran.
Nunca dentro de la carpeta de la skill ni junto a los entregables del usuario.

## Operating Rules

1. **Marca-blanca**: la identidad vive en el brand pack, nunca en el skill.
   Con pack: fidelidad total. Sin pack (modo libre): diseño cinematográfico
   puro según el brief — el listón es "digno de un festival de cine".
   Nunca inventar identidad de marca.
2. **Fluidez suprema** (`references/fluidez.md`): resortes en toda entrada, fondo
   siempre vivo y continuo, salidas que CRUZAN el corte (la escena saliente
   termina de irse debajo de la entrante: nunca un frame vacío entre escenas).
   Nada se queda quieto sin propósito; ningún corte es brusco o accidental.
   El idioma de transición lo fija el brand pack o el tono de la pieza
   (ver `references/brand-packs.md`).
3. Los tres pilares de `references/principios.md` (coherencia visual, armonía espacial,
   efectos especiales deslumbrantes y acordes) son obligatorios en cada entrega.
   El listón: el mejor video jamás creado sobre el tema.
4. **Auto-mejora continua** (`references/auto-mejora.md`): cada build que
   resuelva algo real, repetible y verificado se registra con
   `python scripts/registrar_aprendizaje.py --titulo "..." --detalle "..."`.
   El script evita duplicados y anexa en el formato canónico; el contenido
   vive en un solo lugar (DRY). Cada proyecto deja la skill mejor de lo que
   la encontró.
5. Cero confabulación: cifras, nombres y citas salen de la fuente o se marcan `[PENDIENTE]`.
6. **Autocorrección antes del usuario** (`references/auto-qa.md`): el modelo es
   multimodal — usa tus propios ojos como el control de calidad. Todo render
   pasa por `scripts/auto_qa.py` (barrido máquina: negros, congelados, flashes,
   audio) y luego MIRAS el contact sheet cuadro por cuadro. Si detectas un
   error, lo corriges tú con la solución más coherente con las reglas del skill
   y re-verificas. El usuario nunca es el que encuentra el error: lo que le
   llega es siempre la versión definitiva, profesional y terminada.
7. Los renders largos van en segundo plano; no bloquear el chat.
8. **Mandato del autor**: mejorar esta skill de forma continua hasta que sea
   la mejor skill de edición de video con IA jamás creada.
9. **El listón es de premio** (`references/rubrica-premios.md`): idea con
   hook, arco dramático, animación con oficio (`references/animacion.md`) y
   sonido diseñado. "Correcto" no es terminado.
