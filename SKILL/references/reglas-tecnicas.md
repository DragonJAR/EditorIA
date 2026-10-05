# Reglas técnicas (se amplía con cada build)

## Heredadas del sistema original (probadas en producción)
- QA: mirar SIEMPRE los fotogramas en los tiempos clave antes del render completo.
- Dos escenas a pantalla completa seguidas: solapar la siguiente ~0,4s; si no,
  asoma el fondo entre ambas.
- Salida anticipada: cada escena empieza a salir 0,5s antes de su fin.
- Titular cinético: las palabras de énfasis seguidas van en UN grupo (no partir
  el bloque de color con un salto de línea).
- Cifra protagonista: grande, en acento, con impacto desde el fotograma 0
  (no "aparece a los 16 fotogramas": en un anuncio no da tiempo).
- Renders largos como proceso en segundo plano con log; nunca bloquear el chat.
- No procesar video dentro de carpetas sincronizadas (Drive): solo copiar.
- Sincronía: anticiparse a la palabra hasta 0,45s es estilo; llegar >0,12s tarde es error.
- Toda cifra de un estudio lleva su fuente en pantalla.
- Outro: tarda ~1,2s en mostrar el titular → darle ≥3,4s de duración.

## Propias (2026-10-03)
- 2026-10-03 · **ffmpeg: duraciones — nada se auto-ajusta**. Un pad de filtro
  (`[vox]`) solo se consume UNA vez: para sidechain Y amix, `asplit=2`.
  `-shortest` recorta el video al audio mas corto: usar duracion explicita
  (`apad=whole_dur=D`, `atrim=0:D`, D = duracion del video por ffprobe).
  `sidechaincompress` termina con el input mas corto: padear el sidechain a la
  duracion total (`[voz]apad=whole_dur=TOTAL[vozpad]`). Al mezclar voz_off con
  el video, NUNCA `-shortest` si el audio es mas corto.
- 2026-10-03 · **Música con cadencia**: ElevenLabs Music (`music_v1`) genera
  underscores por prompt (ej. "dark cinematic underscore, deep pulsing synth
  bass, steady 100 BPM pulse"). En el mix: musica a 0.12 + sidechaincompress
  (threshold 0.015, ratio 12, attack 15, release 600) para ~15 dB bajo la voz
  (verificado con `scripts/medir_mezcla.py`; iterar `volume=` hasta converger).
- 2026-10-03 · **ffmpeg: fades de 30ms en cada empalme de segmento**. `afade=t=in:st=0:d=0.03,
  afade=t=out:st={dur-0.03}:d=0.03` en cada segmento contra pops de empalme.
  Barato, invisible, obligatorio. (En cortes de diálogo dentro de video real,
  5ms bastan para declickear — ver `video-real.md`.)
  `aplicar_edl.py --suavizar` usa 0.03 por defecto para alinearse con esta leccion.
- 2026-10-03 · **Auditoría de alineación** (render_plan.py): los detalles minúsculos
  que hacen ver profesional un video: iconos centrados al píxel (centro = h/2 del
  contenedor), bloques de texto centrados verticalmente en su tarjeta, columnas
  decorativas con centro matemático en W/2 (7 columnas: x=135+ci*135, no 90+ci*135),
  centro de la mancha = centro del titular. Márgenes laterales unificados (90px).
  Revisar cada escena con esta lupa antes de entregar.
- 2026-10-03 · **Flotación idle**: `flota(t,t0,amp,freq)` — respiración sutil (±4-6px)
  en elementos ya asentados (tarjetas, burbujas). Nada se queda totalmente quieto.
- 2026-10-03 · **Voz en off con ElevenLabs** (`scripts/voz_off.py`): campo "voz" por
  escena en el plan → un segmento por escena → mezcla con `adelay` en (from+0.4s).
  Voz recomendada ES: Fernanda Sanmiguel (latinoamericano, neutra).
- 2026-10-03 · **Coherencia visual y armonia espacial**: ver
  `references/coherencia-espacial.md` (canonico). Resumen: un componente = un
  estilo en todo el video; rotulos a la misma altura (y=H*0.20); margenes
  laterales unificados; fondo sin rejillas/lineas decorativas (en video se ven
  mucho mas fuertes que en un frame estatico: blobs a la deriva + vineta).
  (v5 rompio la regla del fondo con una grilla en perspectiva en el bloque de
  Brian: la regla existia, no se aplico.)
- 2026-10-03 · **API keys**: nunca en el skill ni en memoria. Patrón: `~/.secrets.env`
  (chmod 600) con `export NOMBRE_API_KEY=...`, cargado desde `~/.bashrc`. En memoria
  solo se anota DÓNDE está, jamás el valor.
- 2026-10-03 · Interlineado en PIL: usar `font.getmetrics()` (ascent+descent) para la altura
  de línea; `textbbox` subestima y las líneas se solapan (visto en "145 ms / DE RESPUESTA").
- 2026-10-03 · Al componer un PNG con varias partes (cifra + caption), el ancho del lienzo
  debe cubrir la parte más ancha; si no, el caption sale recortado (visto en "35M" y gauge).
- 2026-10-03 · `ImageDraw.rounded_rectangle` falla si la altura (o ancho) es menor que
  2×radius aunque y1>=y0: dibujar `rectangle` normal (o saltar) cuando h < 2×radio.
- 2026-10-03 · Tipografía cinética: auto-fit — medir la línea más ancha y reducir el
  tamaño hasta que quepa (`render_plan.py`: ≤980px; demo reel: ≤1000px en 1080).
  Los kickers mono con letterspacing también se auto-ajustan (reducir si >1000px).
  Verificado en el demo reel EditorIA.
- 2026-10-03 · En `paste_center(base,img,cx,cy)`, cx es el CENTRO: para centrar en el
  frame usar W/2, no W (pasar W pone el centro en el borde derecho y el texto sale
  cortado; le pasó a 3 kickers del demo reel).
- 2026-10-03 · `zoompan` a 2160×3840 sobre 900 fotogramas es inviable (>6 min sin terminar):
  para push-in usar concat de tarjetas estáticas o pre-renderizar el zoom por tarjeta.
- 2026-10-03 · En `filter_complex_script`, escapar las comas dentro de expresiones `y='...'`
  con `\,` o el filtro falla al parsear.
- 2026-10-03 · `overlay` sincroniza los streams por PTS: un PNG en loop con stream 0→dur
  NO aparece en la ventana global [a,b] si a>dur (el `eof_action=repeat` repite el último
  frame, que es transparente por el fade-out). Solución: `setpts=PTS-STARTPTS+{a}/TB`
  para desplazar los PTS del elemento a su ventana global. Los `fade st` van relativos
  al stream (in: `st=0`, out: `st=(b-a)-0.35`). Bug encontrado en el QA del v2
  (line-up y segmentos vacíos a partir de t=8).
- 2026-10-03 · Rutas en playlists de concat (`-f concat`) se resuelven relativas al archivo
  de lista: usar nombres base dentro de la misma carpeta.
- 2026-10-03 · `remote-storage upload-file` requiere aprobación del usuario en la app; si expira,
  entregar el MP4 como adjunto directo en el chat (funciona, 249 KB probado).
- 2026-10-03 · Nombres propios y TODO texto en badges/tarjetas: verificar siempre
  contra la transcripcion/fuente ("Agidra" se colo en un badge desde v2 y sobrevivio
  3 versiones sin que el QA lo atrapara: el checklist dice "leer cada tarjeta en voz
  alta" y no se hizo). Causa raiz: los PNG se heredan entre versiones sin re-auditar.
  Regla: ningun asset se hereda sin pasar el QA de texto de nuevo.
- 2026-10-03 · Composicion vertical: balancear el peso visual del frame completo.
  Un kicker + 4 cards arriba y 600px muertos abajo se ve roto en movil. Si el
  bloque no llena el alto, bajar el grupo o anclar marca (logo/isotipo) abajo.
- 2026-10-03 · **Diagramas vivos**: si un diagrama se dibuja en ~1s y su bloque
  dura 10-15s, NO puede quedarse congelado despues: viola "nada se queda
  totalmente quieto" (flotacion idle). Patron: fase de dibujo (drawp) + movimiento
  idle continuo (nodos que respiran +-3px / flotan +-4px con fases distintas,
  dots viajando por las conexiones, ECG/pulsos avanzando). Las aristas se
  re-dibujan cada frame siguiendo los centros flotantes.
- 2026-10-03 · **Auto-fit en nodos**: medir `textlength` de cada linea contra el
  diametro del nodo ANTES de renderizar; reducir fuente hasta que quepa
  (margen 20px). "ORQUESTADOR" desbordo su nodo en v5 por no medirlo.
- 2026-10-03 · **Conexiones al borde, no al centro**: las lineas/tentaculos
  terminan en el borde del nodo (centro + direccion*radio), nunca sobre el texto.
  Calcular el punto final restando el radio del satelite a lo largo de la direccion.
- 2026-10-03 · **ffmpeg: concat exige specs idénticas**. Mismo codec, fps,
  resolución, SAR (`setsar=1`), sample rate y layout de audio. Un SAR distinto
  rompe el concat en silencio. Segmentos mudos: `anullsrc` por segmento o el
  concat pierde el audio.
- 2026-10-03 · **Captions: quemar LAST y en el timeline de salida**. Quemar captions
  despues de todos los overlays para que nada los tape; self-eval en cada boundary
  de corte + waveform del archivo final (no de las fuentes). Si el video se
  re-ordena/concatena, re-mapear cada cue al timeline de salida (offset acumulado
  por segmento; descartar cues fuera de rango): un SRT con tiempos de la fuente
  quemado sobre un video re-ordenado sale desfasado.
- 2026-10-03 · **voz_off.py: cache por hash, no por índice**. El cache por
  índice (`s00.mp3`) reutilizaba audio viejo si cambiaba el texto de una
  escena. Ahora el path es `~/.cache/editoria/voz/vo_{md5(texto|voz|modelo)[:12]}.mp3`
  y se salta la síntesis si existe y supera 1500 bytes: no se re-paga un
  segmento idéntico entre proyectos.
- 2026-10-03 · **ffmpeg concat: streams intercalados por segmento**. Con
  `concat=n=N:v=1:a=1` el orden es `[v0][a0][v1][a1]...`, NO todos los video
  primero. Agruparlos (`[v0][v1][a0][a1]`) falla con "Media type mismatch".
- 2026-10-03 · **EDL = contrato entre herramientas**. Una línea `START-END`
  por línea, rangos a conservar, `#` para comentarios. Lo generan `silence.py`
  y `retakes.py`; lo consumen `aplicar_edl.py` y `beat_sync.py --edl`. Nunca
  inventar otro formato de EDL.
- 2026-10-03 · **ASR: una sola casa**. El puente a whisper (cpp/faster/CLI)
  vive en `_comun.transcribir_medio()`; `scripts/ffmpeg_tools/caption.py --transcribe` y
  `transcribir.py` lo reusan. No duplicar la detección de motores.
- 2026-10-03 · **shorts-plan.json se valida antes de renderizar**.
  `shorts_plan.py --solo-validar` falla rápido con errores específicos
  (solapes, ids duplicados, timestamps fuera de rango) en vez de fallar a
  mitad del render.
- 2026-10-03 · **No redefinir flags de add_common**. `_comun.add_common()`
  ya agrega `--dry-run` y `--json`; redefinirlos rompe argparse con
  "conflicting option string".
- 2026-10-03 · **drawtext: escapar `: , ' [ ]`**. Todo caracter especial del
  texto va con backslash (`\:` `\,` `\'` `\[` `\]`); si no, el parser de
  filtros rompe el comando. El texto ya va entre comillas simples dentro del
  filtro.
- 2026-10-03 · **Validar excluyendo lo invalido**. En `shorts_plan.validar()`,
  los segmentos con from/to no numericos se marcan y se excluyen del chequeo
  de solapes: un plan con 2 errores no debe crashear el validador con un
  tercero (ValueError en el sort).
- 2026-10-03 · **Thumbnail: la herramienta no diseña**. `thumbnail.py`
  ejecuta el craft determinista (≤4 palabras, marca, tercios); el brief
  creativo (tension, open loop) lo hace el agente con el usuario en el
  review-gate. No automatizar el gusto.
- 2026-10-03 · **mkdtemp no se limpia solo**. Encontrado en DOS lugares la
  misma clase de bug: `shorts_plan.py` y `_comun.transcribir_medio()`
  creaban tmpdir con `mkdtemp` sin `try/finally` + `shutil.rmtree`. Regla:
  todo temporal va con `TemporaryDirectory` o `try/finally`; un `return`
  temprano o un `die()` no eximen de limpiar.
- 2026-10-03 · **Capitulos de shorts = timeline de salida**. El short final
  concatena segmentos en orden de archivo: `chapters.py` calcula los tiempos
  acumulando duraciones, no usando los `from` de la fuente (que apuntan al
  video largo original).
- 2026-10-03 · **Los smoke tests codifican el comportamiento CORRECTO, no el
  actual**. El test de chapters validaba el bug (from de fuente); al corregir
  el script hubo que corregir el test. Un test que congela un bug es peor
  que no tener test.
  Regla general: todo overlay temporizado se expresa en el timeline donde
  se quema, nunca en el de la fuente. (Ver tambien "Captions: quemar LAST y en
  el timeline de salida" mas arriba.)
- 2026-10-03 · **Rutas relativas = relativas al plan**. `shorts_plan.py`
  resuelve fuente/musica/srt contra el directorio del plan, no contra el
  CWD. Un contrato debe ejecutarse igual se invoque desde donde se invoque.
- 2026-10-03 · **Integración brag (latent-spaces/brag)**: sistema de 6 tonos
  (`references/tonos.md`) elegido en el brief antes del guion; piso de lectura
  en `ritmo.md` (0.8s etiqueta asentada, 0.3s/palabra, fast-in + hold — el ritmo
  nunca sale de retirar texto temprano); disciplina de beats (strong cues 1–3
  por pieza ±0.15s para momentos mayores, grilla ±0.10s para secuencias;
  texto legible NO va en cada beat a 110+ BPM); capa SFX procedural
  (`scripts/sfx.py`: 8 sonidos deterministas, seed fijo) mezclada como una
  pieza con la música (`references/sfx.md`); poster horneado como frame 0
  (`scripts/poster_frame.py`: overlay enable='eq(n,0)', duración y audio
  intactos — es lo único que controla el thumbnail en Slack/X/Discord);
  share copy canónico por tono (`references/share-copy.md`); línea de
  grounding en `principios.md` (afirmar = fuente; inventar = oficio); gate
  creativo L4 en `checklist-qa.md`.
- 2026-10-03 · **SFX procedural con scipy**: `signal.butter` + envolventes
  exponenciales bastan para un pack usable (click/pop/drop/whoosh/ding/thud/
  tick/swell); picos 0.3–0.9 sin clipping, RMS 0.06–0.21. Determinista con
  seed para reproducibilidad. Los whoosh con bandpass barrido por segmentos
  necesitan `min(fc*1.4/(SR/2), 0.99)` para no exceder Nyquist.
- 2026-10-03 · **loudnorm JSON en ffmpeg >= 7**: las claves son `input_i`,
  `input_tp`, `input_lra`, `input_thresh`, `target_offset` (no `measured_*`).
  El pass 2 las recibe como `measured_I=` etc. Ademas, el single-pass subestima
  con contenido muy dinamico (voz + musica duckeada): medir el resultado e
  iterar (`volume=+XdB,alimiter`) hasta converger al target.
- 2026-10-03 · **blend en YUV desplaza el croma**. `blend=all_mode='screen'`
  sobre yuv420p NO es identidad con negro: el screen en los planos U/V
  (0.5) tiñe todo de magenta. Para overlays luminosos: `format=gbrp` en
  ambas entradas antes del blend y `format=yuv420p` despues. (En este ffmpeg
  la opcion es `all_mode`, no `all`.)
- 2026-10-03 · **Grafos gigantes -> SIGKILL**. ~40 inputs con overlays y
  trims en un solo `-filter_complex` mato el proceso (OOM). Patron: pre-
  renderizar capas pesadas (particulas) a su propio mp4 y mezclar en 2 pasos.
- 2026-10-03 · **verificar_ritmo como senal creativa real**. Particulas sobre
  todo el video dieron 0% cuadros quietos y FAIL de ritmo — no era un falso
  positivo: el movimiento constante compite con los diagramas. Doctrina:
  capas de ambiente solo en intro/transiciones/outro; el contenido necesita
  calma (ritmo.md: el silencio visual le da peso a lo que se mueve).
- 2026-10-04 · **Remotion: licencia real y pin de versiones**. No es MIT:
  gratis para individuos y equipos de hasta 3 personas; organizaciones de
  4+ requieren licencia (ver remotion.dev/docs/license/faq antes de
  proponerlo en empresa grande). Todos los `@remotion/*` en la misma
  version exacta, sin `^`. `npx tsc --noEmit` sin `typescript` instalado
  descarga el obsoleto `tsc@2.0.4` y no valida nada: usar
  `./node_modules/.bin/tsc --noEmit`.
- 2026-10-04 · **Remotion: browser-executable reutilizable**. El render
  descarga chromium-headless-shell desde remotion.media; si la descarga
  falla, `--browser-executable RUTA` acepta un headless-shell existente
  (verificado con el cacheado por HyperFrames en
  `~/.cache/hyperframes/chrome/chrome-headless-shell/linux-*/.../chrome-headless-shell`).
  Render verificado: 8s 1080x1920@30 -> 371.9 kB H.264 en 54s, QA limpio.
- 2026-10-04 · **HyperFrames: flags y comandos reales**. `npx skills add
  heygen-com/hyperframes` sin flags abre selector interactivo (cuelga sin
  TTY): usar `-y ... --agent '*' -y`. `hyperframes validate` esta deprecado,
  usar `hyperframes check`. `hyperframes render` NO admite `--non-interactive`.
  `/remotion-to-hyperframes` si existe oficialmente (instalar con
  `--skill remotion-to-hyperframes`). El render local no exige login.
- 2026-10-04 · **HyperFrames: gate de disco en /tmp**. `render` aborta con
  ~0.5 GB libres en /tmp aunque haya 468 MB libres reales. Workaround
  verificado: `export TMPDIR=$HOME/tmp-hyperframes` + `--frames-cache-dir ./cache`
  (la env var `HYPERFRAMES_EXTRACT_CACHE_DIR` sola no basta). Render
  verificado: 8s 1080x1920@30 -> 525 kB H.264 en 1m04s, captura screenshot
  por software GL (~58s), static-dedup 26%, GSAP local con timeline en
  `window.__timelines["main"]`, lint 0/0, 0 console errors.
- 2026-10-04 · **Benchmark honesto de los tres motores**. Misma composicion
  8s 1080x1920@30: Remotion 371.9 kB/54s, HyperFrames 525 kB/64s; ambos QA
  limpio salvo flags de auto_qa en tramos casi estaticos (umbral, no defecto).
  Selector: HTML/GSAP -> HyperFrames; React/data-driven -> Remotion;
  montaje/post/QA -> FFmpeg. Los tres son opcionales y complementarios.
- 2026-10-04 · **HyperFrames exige Node 22+** (no 18+): requisito oficial
  del README de heygen-com/hyperframes, verificado en la fuente. El check
  de entorno refleja "Remotion 18+ / HyperFrames 22+". Via oficial
  no-interactiva para skills: `npx hyperframes skills update` (core set
  desde el main actual; el blob de skills.sh puede ir horas atrasado);
  `--all` instala las 21 publicadas saltando el picker. `/remotion-to-
  hyperframes` es one-way y valida con SSIM escribiendo
  TRANSLATION_NOTES.md; rechaza useState/useEffect y UI kits de terceros.
- 2026-10-04 · **Remotion: anillo SVG que se dibuja sin gaps**: Circle con strokeDasharray=C y strokeDashoffset animado por interpolate es determinista; r debe quedar fijo y la respiracion va en scale del grupo g (cambiar r con dasharray fijo abre un gap). Verificado en still a full-res: el gap del contact sheet era artefacto del thumbnail.
- 2026-10-04 · **Auditoria: barrer la clase de error completa**: Tras cada correccion, buscar la misma clase en toda la skill: el requisito Node 22+ de HyperFrames vivia en 3 archivos (hyperframes.md corregido, capacidades.md e instalacion.md pendientes) y el comando interactivo de skills en 2. Un fix puntual sin barrido deja la skill inconsistente.
- 2026-10-04 · **Diagramas: el hold del ultimo frame los congela**: Patron diagrama(): secuencia viva de 5s + hold del ultimo PNG hasta t1 generaba tramos congelados de 5-10s (auto_qa los marco, contact sheet lo confirmo). Fix: loopear el tramo idle con -start_number 40 -stream_loop -1 en vez de sostener f_149.png. El idle con flotacion de +-4px solo existe si sigue corriendo.
- 2026-10-04 · **Baches negros entre bloques: solapar visuales**: Los bloques terminaban en el mismo segundo que empezaba la voz del siguiente, dejando 1.5-2s de solo fondo entre bloques (auto_qa los marco como frozen). Fix: adelantar los visuales del bloque siguiente 1-1.5s (anticipacion visual, la voz no se mueve) y extender el hold del bloque anterior para un crossfade. Mover tambien los SFX y ventanas de particulas con el mismo delta.
- 2026-10-04 · **Mastering: correccion de loudness en loop**: El dual-pass de loudnorm subestima con dinamica alta y el alimiter recorta picos al aplicar la ganancia residual, dejando I y TP fuera de objetivo (medido: -15.0 LUFS, TP -1.0 dBFS vs -14/-1.5). Fix: loop de correccion (max 3): medir I/TP del master, aplicar volume=ganancia dB + alimiter limit=0.79 (-2.0 dB deja headroom para el overshoot del AAC), repetir hasta I=-14+-0.5 y TP<=-1.5.
- 2026-10-04 · **Auto-fit de nodos: constreñir alto y centrar bloque**: El auto-fit de node() solo controlaba el ancho del texto; con 2 lineas el bloque quedaba anclado arriba (cy-fs*0.7) y desbordaba por abajo ('MISMO AGENTE' recortado por el borde del circulo, visible a full-res). Fix: el loop tambien exige (n-1)*fs*1.25+fs <= 2r-24 y el bloque se centra verticalmente (y0=cy-bloque/2). Revisar la misma clase en todos los diagramas con labels multilinea.
- 2026-10-04 · **ffmpeg scale no acepta expresiones por frame**: El filtro scale evalua w/h una sola vez al inicio (en este ffmpeg 8.1.2 no existe eval_mode para scale); un push-in por expresion con t falla. Para zoom animado por filtro usar otro mecanismo o pre-render. El bob/xbob por overlay si funciona (x/y del overlay se evaluan por frame).
- 2026-10-04 · **Poster frame: el primer frame es el thumbnail**: El video abria con fade-in desde negro: el frame t=0 (el que usan las plataformas como thumbnail/poster) quedaba casi vacio. Fix: los elementos de apertura (kicker + isotipo) con a negativo (-0.35 = duracion del fade-in) para que esten a opacidad completa en t=0. Verificar siempre el primer y ultimo frame a full-res.
- 2026-10-04 · **Kicker/texto full-frame: fijar la posicion del texto DENTRO del PNG**: Un PNG de texto de 1080x1920 con el texto centrado (H/2) obliga a hacer overlay en y negativo para llevarlo arriba/abajo, y es facil equivocarse: el kicker quedo a mitad de frame chocando con el titular. Patron: text_png(..., y=100) fija la posicion dentro del PNG y el overlay va en (0,0). Verificado en teaser EditorIA 2026-10-04.
- 2026-10-04 · **Ritmo: umbrales de verificar_ritmo calibrados para resumenes, no para piezas cortas**: En un teaser cinetico de 12s, verificar_ritmo marco FAIL (21% quietud vs 25% minimo, pausa maxima 0.7s vs 1s) aunque la pieza cumple la intencion de la doctrina: variacion de beats, sin metronomo, micro-idle continuo. Densidad deliberada en formato corto no es defecto. Para piezas <=15s rige la intencion (variacion + encadenamiento), no los umbrales numericos de resumenes. Verificado en teaser EditorIA 2026-10-04.
- 2026-10-04 · **Delivery: una sola tabla canonica de plataformas (_delivery.py)**: Integrado de kajisho5/ffmpeg-skill (MIT): el mismo destino se describia en tres lugares (spec en checklist-qa.md, flags de encode dispersos, safe zones sin dato). Ahora scripts/ffmpeg_tools/_delivery.py es la unica tabla: spec de compliance + preset de encode + safe zones por borde, con aliases y helpers (spec_of, safe_margins_px, resolve). La leen delivery_check.py y futuros exports; checklist-qa.md la referencia como canonica. Valores: los verificados de EditorIA donde existian, los de ffmpeg-skill donde no.
- 2026-10-04 · **Errores con taxonomia en _comun.die (kind + JSON)**: die(msg, kind=...) con kinds input/ffmpeg/output/missing_tool/timeout/verification/interrupted; con --json sale {status:failed, error:{kind,message}} en stdout. probe() ya marca kind=input/kind=ffmpeg. Sin --json el comportamiento no cambia (stderr + exit 1). Patron de kajisho5/ffmpeg-skill (MIT), adaptado a _comun existente.
- 2026-10-04 · **Corte stream copy cae en keyframes**: montaje cortar --rapido documenta que el corte cae en el keyframe mas cercano (puede empezar antes o en frame congelado); el corte exacto es sin --rapido (re-encode). Verificado en codigo.
- 2026-10-04 · **VFR se conforma a CFR en montaje**: _vargs ahora suma cfr_args(meta); fuentes VFR (telefono, grabacion de pantalla) ya no desincronizan en cortar/unir/fundido. En CFR no agrega nada.
- 2026-10-04 · **HDR en grade**: sin --to-sdr el HDR se gradea en 10-bit y sale HEVC Main10 con etiquetas; con --to-sdr hay tonemap a BT.709 antes del grade. Nunca se aplana HDR a 8-bit sin tonemap (verificado con archivo PQ real).
- 2026-10-04 · **Fit-size en captions**: caption.py --max-lines/--min-size encoge la fuente por cue (override ASS fs) hasta que quepa; nunca reescribe el texto. Solo el path ASS (animate/karaoke); el burn SRT directo usa el wrap de libass.
- 2026-10-04 · **Captions: primero el frame, despues el texto**: Quemar captions antes de crop/resize/verticalizar los deja fuera de cuadro; quemar a tamano intermedio y escalar despues los ablanda. Orden: encuadre final, luego texto.
- 2026-10-04 · **Loudness: no normalizar ambiente a target de voz**: loudness.py rechaza inputs bajo -40 LUFS (parece room tone, no voz; subirlo solo sube el ruido) salvo --force. Verificado con ruido a -69.4 LUFS.
- 2026-10-04 · **Look con zona segura dibujada en el sheet**: auto_qa.py --safe plataforma dibuja el rectangulo de zona segura en cada tile del contact sheet; el paso Look verifica de un vistazo que captions y texto no caen bajo la UI (en la prueba ya atrapo captions bajo la zona de Reels).
- 2026-10-04 · **Captions largos tapan el motion: chunkeo a frase corta**: Captions quemados de frases completas (7 lineas) tapaban subtitulo y protagonista aunque el fit-size los encogiera. Patron: re-chunkear el SRT a cues de frase corta (<=9 palabras, tiempos proporcionales al nro de palabras, texto concatenado identico al VO) antes de quemar. Verificado en reel real 2026-10-04.
- 2026-10-04 · **Fit de titulo: medir el ancho TOTAL, no por palabra**: fit_font por palabra dejaba 'PENTESTING MOVIL' cortado en los bordes: cada palabra cabia pero la suma no. Patron: tras el fit por palabra, si el ancho total > max, reescalar todas las fuentes por max/total. Tambien aplicar fit a subtitulos largos.
- 2026-10-04 · **Protagonista y captions: reservar bandas verticales sin solape**: En layout vertical con captions en banda central, el protagonista (diagrama) y el isotipo del CTA deben vivir en cy>=1260 y tamano compacto; si no, los captions los tapan. Verificado con sheet --safe reels en reel real.
- 2026-10-04 · **Densidad de hooks visuales en talking head**: En resumenes y piezas con talking head, minimo 2 graficos full-screen por capitulo/seccion (patron de prompts virales Opus 5.5/HyperFrames). El silencio visual es el enemigo; cada grafico explica o engancha, no decora.
- 2026-10-04 · **Contexto real en motion graphics**: Los prompts de motion graphics rinden cuando referencian la carpeta del proyecto: datos reales, pantallas reales, nada de placeholders. Verificado en piezas virales (skillry.dev/ai-videos/opus-5-5).
- 2026-10-04 · **Prompts de motion graphics en una toma**: Nueva referencia prompt-motion-graphics.md: plantillas launch 15s, showreel y talking head agresivo, con reglas (sin chrome, sonido en cada golpe, cambios duros luz/oscuridad, fisica real). El motion va en HyperFrames; ensamble, mezcla y QA en FFmpeg.
- 2026-10-04 · **contact_sheet.py --video: distribuir frames como i/n, nunca t=duracion exacta**: ffmpeg con -ss antes de -i no devuelve frame al pedir t=duracion exacta (seek al final del archivo): extraer_frames fallaba en el ultimo frame con FileNotFoundError. Fix verificado: t = dur * i / n en vez de dur * i / (n-1). Regla: ningun extractor de frames debe pedir el timestamp exacto de fin de archivo.
- 2026-10-04 · **Loudness: nunca loudnorm de una pasada sobre el master final**: loudnorm single-pass (dinamico) subio el true peak de -0.9 a +0.2 dBTP y delivery_check reels dio FAIL. Patron: usar scripts/ffmpeg_tools/loudness.py (dos pasadas, lineal) con --tp -1.5; resultado -14.3 LUFS / -1.4 dBTP, PASS. Verificado en reel real 2026-10-04.
- 2026-10-04 · **Fuentes de marca sin Google Fonts: fontsource via npm**: Con la red bloqueando github/jsdelivr, npm pack @fontsource-variable/FAMILIA trae el woff2 variable; fontTools (pip fonttools brotli) lo convierte a TTF (flavor=None) y PIL respeta el eje wght. Verificado con Plus Jakarta Sans y Montserrat 2026-10-04.
- 2026-10-04 · **Zona segura reels: maxw de titulares 780px centrado**: Titulares con maxw 960 y reloj mono 210px invadian el margen derecho de Reels (botones) en auto_qa --safe reels; banners a H*0.80 caian bajo la UI inferior. Patron: maxw hasta 780 centrado en W/2, tarjetas de hasta 780 de ancho, nada por debajo de H*0.77. Verificado en reel real 2026-10-04.
- 2026-10-04 · **Motion blur por submuestreo en render_plan**: render_plan.py --blur 5 promedia 5 sub-frames en la ventana del obturador (0.5 = 180 grados); con --jobs en paralelo el demo de 30 s rinde en ~2 min. Borradores --blur 1, entrega --blur 5. Verificado con el plan demo 2026-10-04.
- 2026-10-04 · **Zona segura automatica por escena en render_plan**: Las escenas del motor (tarjetas de 880 px, burbujas a 90 px del borde, lema sin auto-fit) se salian de la zona segura de Reels. Patron: medir el bbox del contenido opaco (alfa mayor a 110, la decoracion translucida no cuenta) en 6 instantes de la escena y escalarla con un factor FIJO por escena (no por frame: bombearia). Margenes desde _delivery.py (union reels/tiktok/shorts, laterales simetricos). Verificado con auto_qa --safe reels.
- 2026-10-04 · **Rotulos y end cards: nada aparece de golpe ni queda congelado**: rotulo() calculaba el resorte pero dibujaba sin alfa ni elevacion (aparicion de golpe); el end card quedaba 5 s identico (auto_qa frozen). Fix: rotulo con fade + elevacion 24 px por resorte; lockup final con flotacion, halo que late en el boton y push-in de camara 3.5 por ciento; titulares asentados con micro-idle de 4-5 px. auto_qa LIMPIO tras el fix.
- 2026-10-04 · **AAC del mp3 de voz: el "priming" del codec retrasa la pista ~45 ms respecto a la imagen**: cuando se mete una voz generada con codificador AAC (mp3) en un contenedor mp4, los primeros ~45 ms del audio son un silenciador del codec, no voz real; la pista empieza TARDE respecto a la imagen. Patrón en `scripts/voz_off.py`: emitir la voz como wav (sin priming) y dejar que el muxer de ffmpeg la meta a mp4 con el retardo exacto del rango de impacto. Si se observa desfase audio→video > 30 ms al montar, casi siempre es esto; la fix es re-emitir el segmento en wav y recomprimir. Verificado en reel real 2026-10-04.
- 2026-10-04 · **Whisper miente en los finales de frase y en las pausas DENTRO de palabra**: Whisper suele dar `duración = 0` a las palabras de apertura (salen tarde), truncar la última sílaba de frase ("respuest-", "promet-") y meter pausas internas en palabras largas (4 s en "fuera"). Patrón en `scripts/alinear.py`: aceptar marcas con `confianza` baja si las vecinas son fiables; palabras "en silencio" se anclan al vecino más cercano con energía alta (la energía del audio no miente). Verificado en guion de 30 s con `alinear.py` 2026-10-04.
- 2026-10-04 · **Cortar canción a voz: normalizar música al MISMO LUFS que la voz**: la música debe terminar normalizada al LUFS objetivo de la voz (tipicamente -14 a -16 LUFS) antes de medir `volumen`/`db_bajo_voz` en el plan; si una pista está a -22 LUFS y otra a -12 LUFS, el mismo `db` produce resultados muy distintos. Patrón: `scripts/ffmpeg_tools/loudness.py --target -14 mus.mp3 mus.norm.m4a` y referenciar la normalizada en `plan.json`. Verificado en reel real 2026-10-04.
- 2026-10-04 · **alinear.py: anclar animaciones a la palabra exacta, no al offset global de la escena**: la skill (15 clases de error en at: de palabra) viene de aproximar el tiempo de cada palabra con el offset del inicio de la escena. `scripts/alinear.py voz.mp3 guion.txt -o voz.palabras.json` resuelve el tiempo de cada palabra del guion contra el audio generado; el plan.json puede leer `palabras.json` y poblar `at.p1/p2` o `at.palabra` por palabra. Sin esto, las animaciones tipo "titular cinético palabra-a-palabra" (`sc_apertura`) y los hooks de palabra (`sc_chat`) llegan tarde y rompen el ritmo.
- 2026-10-05 · **Frames RGB a H.264: convertir a BT.709, no solo etiquetar**: PNG de PIL a yuv420p sin out_color_matrix usa la matriz BT.601 y sale sin etiqueta; los players tratan el HD como BT.709 y el color se desplaza: el acento neutro (232,72,12) se decodificaba (244,82,6); el gris 128 no cambia, por eso nadie lo vio. Fix unico: _comun.codificar_frames / VF_RGB_A_BT709 (scale=out_color_matrix=bt709:out_range=tv + tags bt709) -> fiel ±2. Extraer un JPG de un video BT.709 pasa por -vf format=rgb24 o hereda el desplazamiento. validate_skill lo verifica midiendo un parche decodificado.
- 2026-10-05 · **zoompan sobre un stream multiplica la duracion**: montaje.py pase aplicaba zoompan d=90 despues del concat a 30 fps: cada frame de entrada genera d frames, 3 fotos x 1 s dieron 273 s (90x) y 87 s de render. zoompan va sobre UNA imagen por entrada (-i foto, sin -loop) con d = frames del clip y z/x/y en funcion de on; sobremuestrear x2 antes evita el temblor del paneo. Verificado: 3 x 1.5 s = 4.500 s exactos en 7 s.
- 2026-10-05 · **ImageDraw con alfa reemplaza pixeles, no mezcla**: En PIL, d.rectangle(..., fill=(0,0,0,130)) sobre una capa con contenido REEMPLAZA esos pixeles por negro semitransparente: el velo de sc_kenburns borraba la foto y un marcador translucido abria un hueco en la tarjeta. Lo translucido sobre contenido se compone en su propia capa (alpha_composite) o con un color ya mezclado y opaco.
- 2026-10-05 · **VP9 con alfa: leer con -c:v libvpx-vp9**: El decoder nativo vp9 de ffmpeg descarta el canal alfa de un WebM (alpha_mode=1): un frame decodificado sale opaco aunque el archivo este bien. Para verificar o convertir (WebM -> ProRes 4444) forzar -c:v libvpx-vp9 ANTES de -i. ProRes 4444 lleva el alfa en pix_fmt yuva444p10le. _comun.verificar_alfa hace ambas comprobaciones.
- 2026-10-05 · **Excepcion silenciada = escena rota sin aviso**: sc_kenburns componia una imagen RGB sobre una capa RGBA (alpha_composite exige RGBA), el error se tragaba en un except y el aviso llamaba a info() sin importarlo: la escena nunca mostro la imagen y salia negra. Regla: un except en una escena debe avisar con una funcion importada y probada; el validador debe ejercitar el camino con datos reales cuando el camino feliz depende de un archivo.
- 2026-10-05 · **Listas copiadas de SCENES se pudren**: auditar_plan.py tenia su propia lista de 13 tipos: tras sumar 11 escenas marcaba ERROR tipo desconocido en bars, gauge, etc. Los tipos validos se leen ahora del dict SCENES de render_plan.py (fuente unica, por regex: sin importar PIL). Cualquier catalogo que otra herramienta necesite se deriva, no se copia.
- 2026-10-05 · **Un import roto en _comun tumba todo el kit**: v1.2.0 anoto hex_a_rgb con Tuple sin importarlo: NameError al importar _comun y 14 FALLOS en validate_skill (render_plan, montaje, caption, thumbnail, variantes...). Correr python scripts/validate_skill.py antes de cada commit; un SKILL VALIDO es la condicion minima para publicar.
- 2026-10-05 · **Compilar no es validar: renderizar cada escena y mirarla**: El smoke test (llamar la escena a 3 tiempos) pasaba 28/28 mientras stats solapaba cifras, versus desbordaba el cuadro, hoy pisaba rótulo y fecha, el confeti y la oferta se pisaban en 16:9 y pago tocaba bajo la UI. Patrón: scripts/galeria.py renderiza cada escena y herramienta en 9:16 y 16:9, pasa auto_qa y arma resumen.png; validate_skill exige además que cada muestra quepa en la zona segura (escala_segura >= x0.75) y que ningún hold quede congelado (umbral de auto_qa) en los dos formatos. Verificado 2026-10-05.
- 2026-10-05 · **Letra en unidad() y pilas medidas: el mismo diseño en 9:16 y 16:9**: Posiciones en fracciones de H con letra fija en px (o en W) se pisan al cambiar de formato: W*0.055 = 59 px en 9:16 y 105 px en 16:9. Patrón: tamaños en unidad() (lado corto), bloques apilados con pila() que encoge todo junto si no cabe, contenido dentro de caja_segura(), escenas de lectura en COLUMNA centrada a 1080 px en 16:9. Verificado con hojas de las 28 escenas en ambos formatos 2026-10-05.
- 2026-10-05 · **Push-in centrado no descongela lo que está en su centro**: La respiración de cámara solo con push-in (1 %/s) dejaba frozen en auto_qa a listo, hoy y handoff: el zoom casi no mueve lo que está cerca de su ancla. Fix único en componer: push-in + flotación vertical de 6 px (afín sub-píxel, mueve todos los bordes). Medido: validate_skill pasa 'ningún hold congelado' en 9:16 y 16:9. Verificado 2026-10-05.
