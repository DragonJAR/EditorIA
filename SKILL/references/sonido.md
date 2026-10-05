# Sonido — voz, música y efectos

El apartado de sonido de EditorIA: dirección de voz, proveedores, voces por
idioma, música y SFX. **La voz por defecto es el idioma en que
le hable el usuario**, salvo que pida otro idioma explícitamente para la voz.

## Proveedores

| Proveedor | Uso | Cómo |
|---|---|---|
| **ElevenLabs** (primario) | Voz en off, música, dirección emocional | `scripts/voz_off.py`, `scripts/musica.py`; key en `$ELEVENLABS_API_KEY` |
| Sin TTS | Si ElevenLabs no está disponible | `voz_off.py` lo dice claro y se sale; no hay fallback automático. Se avisa al usuario: trabajar sin voz o reprogramar. |

## Dirección de voz (cuándo hablar cómo)

La voz se dirige como a un actor: el texto del plan lleva las marcas.

| Situación | Dirección | Marca |
|---|---|---|
| Dato clave / cifra héroe | Más lento, pausa antes | `[slowly]`, `...` antes de la cifra |
| Urgencia / CTA | Más rápido, más alto | `[rushed]`, `!`, MAYÚSCULAS en la palabra clave |
| Confianza / cierre premium | Calmo, grave, pausado | `[calm]`, frases cortas con `.` |
| Emoción / celebración | Energía alta | `[excited]`, `[cheerfully]` |
| Ternura / confidencia | Susurro | `[whisper]` / `[whispers]` |
| Drama / revelación | Tono dramático + pausa larga | `[dramatic tone]`, `[long pause]` |
| Ironía / humor | Sarcasmo | `[sarcastic]` (el texto ya debe inclinarse a eso) |
| Humanidad | No-verbales | `[sighs]`, `[chuckles]`, `[clears throat]` — uno por pieza, no por frase |

**Puntuación como ingeniería** (modelos v3): `,` = micro-pausa ~200ms; `.` = parada
~500ms; `...` = duda/suspenso; `—` = corte abrupto; `?` = entonación ascendente;
`!` = más volumen; MAYÚSCULAS = énfasis.

**Reglas de tags** (eleven_v3):
- Un tag claro por beat emocional; no apilar tags densos (desestabiliza).
- El tag debe rimar con la voz: no esperar `[shout]` de una voz suave.
- Sin tags de cierre; van inmediatamente antes de la frase que afectan.
- v3 NO soporta SSML ni `{tags}` XML — solo `[corchetes]`.

**Stability** (v2): 0.30–0.35 = expresivo/dinámico; 0.75+ = monótono/estable.
En v3: `Creative` (expresivo) / `Natural` (balanceado, default) / `Robust`
(consistente pero sordo a las marcas).

## Voces (probadas con audio real, 2026-10-03)

Tres femeninas + tres masculinas por idioma, todas generadas y verificadas.
Default: la del idioma en que hable el usuario, salvo pedido explícito.

**Español:**
| Nombre | voice_id | Perfil |
|---|---|---|
| **Fernanda Sanmiguel** (default ES) | `1aJyZpkt0vxhGPBnPyrs` | Femenina, latinoamericana neutra, seria |
| Gabriela | `hHjbwzYZW17oh0p05AKv` | Femenina, cálida (mexicana) |
| Camila | `e84cwhnrHVYn1KRUiXMG` | Femenina, español neutro |
| Johan | `4uvQjLPvqApx1dVzpNfM` | Masculina, colombiana |
| Fran | `NZ2TecpKTOZyf4AUxLxx` | Masculina, latinoamericana |
| Velez | `ytEyaKD9tSq2dWAVjRQr` | Masculina, español neutro |

**English:**
| Name | voice_id | Profile |
|---|---|---|
| **Brian** (default EN) | `nPczCjzI2devNBz1zQrb` | Deep, resonant, comforting (US) |
| Sarah | `EXAVITQu4vr4xnSDxMaL` | Mature, reassuring, confident (US) |
| Alice | `Xb7hH8MSUJpSbSDYk0k2` | Clear, engaging educator (UK) |
| Bella | `hpp4J3VqNfWAUOO0d1Us` | Professional, bright, warm (US) |
| George | `JBFqnCBsd6RMkjVDRZzb` | Warm storyteller (UK) |
| Daniel | `onwK4e9ZLuTAKqWW03F9` | Steady broadcaster (UK) |

Uso: `python scripts/voz_off.py plan.json -o voz.mp3 --voz fernanda`
(nombres: fernanda, gabriela, camila, johan, fran, velez, brian, sarah,
alice, bella, george, daniel) o `--voz {voice_id}` directo.

## Parámetros de la API ElevenLabs (cómo se controlan tono, velocidad, emoción)

Endpoint: `POST /v1/text-to-speech/{voice_id}`. Modelos: `eleven_v3`
(dirección por tags, default en EditorIA), `eleven_multilingual_v2`,
`eleven_turbo_v2_5`, `eleven_flash_v2_5`.

| Parámetro | Rango | Default | Qué controla |
|---|---|---|---|
| `stability` | 0.0–1.0 | 0.5 | Tono: bajo = más variación emocional/expresivo (puede errático); alto = estable, predecible, casi monótono |
| `similarity_boost` | 0.0–1.0 | 0.75 | Fidelidad a la voz original; >0.85 puede amplificar artefactos |
| `style` | 0.0–1.0 | 0.0 | Exagera el estilo del hablante (solo v2+/v3); más "carácter", menos estabilidad |
| `speed` | 0.25–4.0 | 1.0 | Velocidad: 0.7 = 30% más lento, 1.2 = 20% más rápido |
| `use_speaker_boost` | bool | true | Claridad post-proceso (no disponible en v3) |
| `language_code` | ISO-639-1 | — | `es`, `en`, etc. (v3/turbo) |
| `seed` | int | — | Salida reproducible en pruebas |
| `apply_text_normalization` | auto/on/off | auto | Normaliza números/fechas |

**Recetas:**
- Narración corporativa estable: `stability 0.75`, `similarity_boost 0.75`, `style 0.0`.
- Actuación emocional con tags: `stability 0.35–0.5`, `style 0.2–0.4` (v3).
- Urgencia/energía: `speed 1.1–1.15` + tag `[rushed]`.
- Solemnidad/dato héroe: `speed 0.85–0.9` + `[slowly]` o `...` antes de la cifra.
- Susurro/confidencia: tag `[whisper]` (no bajar `stability` a 0: se vuelve errático).

## Timing de la VO para explainers (matemática de voz)

Antes de timar escenas: la duración de la escena se deriva de la VO, no al revés.

- **Ritmo**: 2.3 palabras/s (~140 wpm) para narración clara y amable; 2.0 en
  pasajes técnicos.
- **Duración de escena**: `segundos = palabras / ritmo + 0.4` (el 0.4 es aire
  de respiro). Una escena sin VO (beat puramente visual) necesita ≥1.0s para
  registrar. **La narración manda el reloj**: `auditar_plan.py` estima con
  esta fórmula si cada voz cabe en su escena antes de pagar TTS, y
  `voz_off.py` mide la voz real y falla si una pisa a la siguiente (dirá
  cuántos segundos alargar). Si la voz no cabe, se alarga la escena o se
  recorta el texto; nunca se acelera la voz.
- **Budgets de palabras** (ritmo 2.3): 30s ≈ 69 palabras · 60s ≈ 138 palabras
  · 90s ≈ 207 palabras.
- **Fórmula de guion** (reparto del runtime): problema 20% → solución 15% →
  cómo 45% → payoff + CTA 20%.
- **Captions**: máx 2 líneas, ≤42 caracteres por línea, ≥1.0s en pantalla,
  corte en cláusulas gramaticales (nunca a mitad de frase).

### Test de decisión de diálogo

Antes de poner una línea en voz, preguntar: **¿esta línea mueve la historia
o solo informa?** Si solo informa (dato, fecha, cifra, disclaimer), no va a
voz: va a caption, gráfica o lower third. La voz se reserva para lo que
necesita *interpretación* — misterio, stakes, humanidad, giro. Regla: si la
línea funciona igual leída en silencio, no necesita voz.

**Placement patterns** (dónde cae cada línea):
- **Cold open**: la línea más fuerte abre, antes de cualquier ident.
- **Pre-drop**: la línea que prepara el impacto cae 0.2–0.6s antes del golpe
  visual/sonoro — el oído anticipa lo que el ojo va a ver.
- **Memory line**: la frase que debe recordarse se dice una vez, despacio,
  y se sostiene con silencio después.
- **Button line**: la última línea cierra el beat con una sola idea; nada
  después salvo el CTA.

## Música

`scripts/musica.py`: `gen` (ElevenLabs Music, prompt describe arco y energía) →
`mix` (con voz: ducking sidechain) o `musiconly` (sin voz, con fade-out).
La música sigue el arco visual: hook con pulso, build en el desarrollo,
resolución en el cierre. Ver `references/reglas-tecnicas.md` (lecciones ffmpeg).

### Sound brief (escribir ANTES de generar)

Antes de tocar `musica.py gen`, escribir el brief en el README del proyecto.
Obliga a elegir en vez de aceptar defaults:

- Feel/género — por qué (personalidad de marca, audiencia, ritmo del edit).
- Tempo y key — elegidos, no el hábito por defecto; compás = 240/BPM segundos.
- Energía por escena (baja/media/alta): de las palabras del brief del usuario.
- Rol: music-led (la música lleva los cortes) o voice-led (la voz manda, la
  música se sienta ligera debajo).
- Groove: kick en cada beat / backbeat / half-time / sin kick — por qué este.
- Hook sonoro: motivo de 2–4 notas que aparece con el logo, siempre el mismo
  timbre (la firma sonora de la pieza).
- Mapa de energía: escena → intro/build/drop/break/outro; qué entra y qué
  sale en cada una; cambios cada 2–4 compases para que no suene a loop.
- Transiciones: risers, silencios, stops — en qué cues.
- Mix: LUFS target (−14 default; −14 (el canon de la skill es −14 enérgico / −16 calmo; ver `checklist-qa.md`); −16/−15 para calmado),
  qué hace ducking bajo qué (voz al frente; música ~15 dB bajo la voz).
- Diferente del último video porque: género/tempo/key/kit/groove distintos.
  Un nuevo acorde sobre el mismo kit, groove y tempo ES la misma canción para
  el oído: cambiar el groove primero.

**Regla de originalidad**: cuando el usuario traiga una referencia, se toman su
energía y su ritmo de cortes, nunca su melodía, su hook ni un riff
reconocible (ver disciplina de referencias en `checklist-qa.md`).

## Efectos sonoros (SFX)

- **Densidad**: máx ~8–12 cues/min; el momento firma de cada beat lleva sonido,
  no cada sub-frame. Ver `tecnicas-video.md` → Audio.
- **Sync al frame**: el pico del whoosh cae EXACTO en el corte (pre-roll 2–3
  frames antes). 100ms de desfase se lee descuidado.
- **Jerarquía** (orden, no targets absolutos): diálogo al frente > spot FX >
  foley > música (~15 dB bajo la voz, verificado con `medir_mezcla.py`).
  Nada pica por encima de la narración.
- **Tipos**: whooshes en transiciones, risers solo en 2–3 beats héroe,
  ticks 2400–2800Hz en números, sub-bass 50–80Hz bajo el hook del frame 0,
  **silencio** como herramienta antes/después del impacto.
- Los tags v3 (`[applause]`, `[explosion]`) sirven para demos; en producción
  preferir SFX dedicados.

**Denoise local** (offline, sin API de pago): RNNoise vía ffmpeg antes de
cualquier mezcla con voz grabada ruidosa:

```
ffmpeg -i voz-ruidosa.wav -af "arnndn=m=modelos/rnnoise.rnnn" voz-limpia.wav
```

Aplicar el denoise ANTES de loudnorm y del ducking — el ruido amplificado por
el compresor ya no se quita.

**SFX library-first**: la biblioteca de SFX es un asset durable cross-proyecto,
con catálogo versionado (`catalog.json`: nombre, duración, banda, nivel). Nunca
regenerar lo que ya existe — buscar primero en la biblioteca, sintetizar solo
lo que falta, y catalogar lo nuevo. No re-facturar dos veces el mismo whoosh.

### SFX sintetizados con ffmpeg (rights-free)

Generar el SFX es determinista: sin licencias, sin provenance. Un wav por cue
en `assets/sfx/`:

**Whoosh** (corte / movimiento de cámara) — ruido rosa filtrado con envolvente
rápida:

```sh
ffmpeg -f lavfi -i "anoisesrc=duration=0.45:color=pink:sample_rate=48000:amplitude=0.5" \
  -af "afade=t=in:st=0:d=0.05,afade=t=out:st=0.2:d=0.25,highpass=f=300,lowpass=f=6000" \
  assets/sfx/whoosh.wav
```

**Click** (entrada de texto/UI) — blip senoidal corto y alto:

```sh
ffmpeg -f lavfi -i "sine=frequency=2200:duration=0.04:sample_rate=48000" \
  -af "afade=t=out:st=0.01:d=0.03" assets/sfx/click.wav
```

**Riser** (build hacia un reveal) — sweep ascendente, 0.6–1.0s, fade in:

```sh
ffmpeg -f lavfi -i "aevalsrc='0.4*sin(2*PI*(400*t+875*t*t))':d=0.8:s=48000" \
  -af "afade=t=in:st=0:d=0.6" assets/sfx/riser.wav
```

**Impact** (golpe gráfico / aterrizaje) — sine bajo + burst corto de ruido con
decaimiento rápido:

```sh
ffmpeg -f lavfi -i "sine=frequency=90:duration=0.3:sample_rate=48000" \
  -f lavfi -i "anoisesrc=duration=0.15:color=brown:sample_rate=48000:amplitude=0.5" \
  -filter_complex "[0]afade=t=out:st=0:d=0.25,lowpass=f=400[b]; \
   [1]afade=t=out:st=0:d=0.1,highpass=f=500[n];[b][n]amix=inputs=2:normalize=0" \
  assets/sfx/impact.wav
```

**Regla de nivel**: SFX **−18 a −12dB bajo la voz**. Puntúan; no compiten.

**Disciplina de pista maestra única**: premezclar VO + todos los SFX en UNA sola
pista antes de codificar (varias pistas simultáneas = echo, drift y desync).
Colocar cada SFX en su tiempo de corte con `adelay` en milisegundos por canal y
mezclar con `amix`:

```sh
ffmpeg -i vo.wav -i assets/sfx/whoosh.wav -i assets/sfx/click.wav \
  -i assets/sfx/riser.wav -i assets/sfx/impact.wav \
  -filter_complex "[1]adelay=2200|2200,volume=0.5[w];[2]adelay=3200|3200,volume=0.4[c]; \
   [3]adelay=7000|7000,volume=0.45[r];[4]adelay=7600|7600,volume=0.6[i]; \
   [0][w][c][r][i]amix=inputs=5:duration=longest:normalize=0[mix]" \
  -map "[mix]" -ar 48000 -ac 2 assets/master_audio.wav
```

`normalize=0` impide que el mezclador atenúe la VO. Luego codificar a AAC
(`-c:a aac -b:a 192k`) y esa es la única pista de audio que entra al render.

### Números de mezcla validados

El orden de operaciones importa — cada número asume la VO ya normalizada.

1. **Normalizar la VO primero**, antes de fijar cama o SFX:
   `ffmpeg -i vo.wav -af loudnorm=I=-14:TP=-1.5:LRA=11 -ar 48000 vo-norm.wav`
   Mezclar contra una VO sin normalizar invalida todo lo que sigue.
2. **Cama musical**: volumen de pista **0.12** (ganancia lineal 0–1) — valor
   verificado: ~15 dB bajo la voz con `medir_mezcla.py` (ver `scripts/musica.py`).
   Contra una VO normalizada, no pasar de 0.12 sin re-medir.
3. **SFX**: volumen base por tipo (0.28–0.5) × **un solo master gain del kit**,
   con tope en 0.8 para que ningún golpe entierre la voz. Valor probado para un
   kit normalizado a −3dB contra VO normalizada: ×1.95. El gain único es el
   punto: "todo un poco más alto/bajo" = un solo número.

**Reglas de placement**:
- El hit cae **sobre la palabra exacta** (el whoosh sobre la palabra que nombra
  el impacto), no al inicio de la frase.
- **Whooshes solo en cortes de sección** — un whoosh por tarjeta se lee cursi.
- **Un solo swell grande por video** (el sub-drop del opener o el reveal final).
  Si todo es grande, nada lo es.

### Paleta de materiales y una sola sala

Darle a cada evento visual su propio sonido sintetizado suena barato en un
minuto. Lo que lo abarata: ondas puras (suenas a chiptune), ningún espacio
compartido (los sonidos flotan sobre la imagen en vez de estar en ella), un
sonido por evento (40 ticks + 10 pops = tragamonedas) y dinámica plana.

- **Pocos materiales, cada uno con su trabajo**: aire (whooshes, pantallas que
  vuelan), cristal (ticks que suben una escala, acordes de aprobación, toques
  de palabra), madera (teclas, clics de mouse como dos golpes a 60ms), sub
  (cortes duros, aterrizajes, el grave bajo el negro), burbuja (pop redondo
  cuando aterriza una tarjeta). Nada fuera de la paleta.
- **Una sola sala para todo**: todos los SFX pasan por la misma reverberación
  sintética (T60 ~1.1s, pre-delay ~12ms, unas pocas reflexiones tempranas,
  low-pass en el decorrelado estéreo). El envío varía según la distancia del
  objeto: una tecla 15%, un whoosh largo 60%. La sala es lo que hace que
  sonidos distintos se sientan como una sola película.
- **Los sonidos reales tienen parciales y transitorio de ruido**: un tick de
  cristal lleva fundamental + parciales inarmónicos (2.76f, 5.4f) con decaídos
  rápidos + un transitorio de ruido; una madera lleva golpe grave con caída de
  tono + snap filtrado. Nunca una senoide cruda sola.
- **Menos eventos que beats**: si dos sonidos caerían a menos de 40ms, queda
  uno. La dinámica sigue el mapa de energía de la imagen: la pausa visual es
  *silencio* tras su único respiro; los impactos son lo más fuerte de la
  película.
- **Los tiempos de los SFX salen del plan, no se reescriben a mano**: la misma
  fuente de tiempos que mueve la imagen programa los sonidos. Si un beat se
  retima, su sonido viaja con él. Nunca reescribir números en dos lugares.

## Mastering (pre-entrega)

Aplicar al audio final ya mezclado (voz + cama + SFX), como último paso antes
de muxear. Cadena, en este orden:

```sh
ffmpeg -i assets/master_audio.wav -af \
  "highpass=f=75,acompressor=threshold=-18dB:ratio=3:attack=20:release=220, \
   loudnorm=I=-16:TP=-1.5:LRA=11,alimiter=limit=0.95, \
   aformat=sample_rates=44100:channel_layouts=stereo" \
  master_final.wav
```

Targets (variante calma; enérgico: −14 LUFS): −16 LUFS integrado, −1.5 dBTP
true peak, LRA 11. (YouTube recomienda −14; la variante calma −16 deja
headroom para la cama musical. La regla canónica —−14 enérgico / −16 calmo—
está en `checklist-qa.md`.)

## Flujo de audio completo

1. Guion con marcas de dirección en los campos `voz` del plan + matemática de
   timing (ver "Timing de la VO para explainers").
2. `voz_off.py` genera segmentos por escena (con la voz del idioma).
3. `musica.py gen` con prompt del arco → `mix` o `musiconly`.
4. Mezcla: normalizar la VO primero (`loudnorm=I=-14:TP=-1.5:LRA=11`); cama
   0.12 (verificado: ~15 dB bajo la voz con `medir_mezcla.py`); SFX con el gain
   único del kit; una sola pista maestra premezclada.
5. Mastering pre-entrega: highpass → acompressor → loudnorm → alimiter
   (−14 LUFS enérgico / −16 LUFS calmo, −1.5 dBTP). Verificar niveles: voz al
   frente, sin clipping.
