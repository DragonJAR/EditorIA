# Audio — beat grid, anchors de SFX y arreglo por compases

El workflow de audio de EditorIA con sync musical: la grilla de beats guía
cortes visuales y SFX; los anchors sobreviven al re-timing; el arreglo se
compone por compases.

## Beat grid

La grilla de beats (BPM + offset del primer beat) se fija antes de planear
cortes o música: cortes en beats fuertes, picos de energía y drops. Los SFX y
los momentos firma se colocan sobre la grilla, no sobre segundos absolutos —
así sobreviven si el plan cambia de duración. En `sonido.md` está el flujo de
voz + música; aquí, el sync rítmico.

Herramientas: `scripts/beat_grid.py musica.mp3 --json grid.json` estima la
grilla; `scripts/beat_sync.py grid.json --cortes ...` (o `--edl`) ajusta
tiempos de corte a los beats cercanos.

- Mapear la música del video a su grilla: BPM, beat 0, y dónde están las
  caídas (donde entra el bajo) y los valles.
- Planear las escenas en compases completos (múltiplos de 4 beats): la frase
  musical se mantiene coherente y los cortes caen en downbeats.
- Las líneas de voz energéticas se pueden acelerar ~8% en el mix (`atempo`,
  verificar drift A/V por segmento — ver pitfalls en `checklist-qa.md` L1);
  las líneas de cierre mantienen su ritmo natural.
- Cada línea de voz se corta entre su primera y última palabra con pre-roll de
  0.08s y cola de 0.15s, nunca más allá del punto medio con la línea vecina.

## Anchors de SFX

Cada SFX tiene una decisión de placement y un ancla. Preferir anclas que
sobreviven al re-timing:

| Ancla | Qué significa | Uso |
|---|---|---|
| palabra | onset de la palabra hablada indicada (en escena N, palabra M) | la palabra clave cae sobre un golpe de la música |
| beat | quarter note n de la grilla musical | hits, impacts, flashes de downbeat |
| absoluta | segundos exactos | solo cuando nada más funciona |
| escena + at | segundos después del corte de escena | entrances amarradas al corte |

Reglas del mapa de SFX (ver `tecnicas-video.md` → Audio para tipos y niveles):
- Todo evento visible de la escena tiene una decisión: suena o un silencio
  deliberado. Nunca dos whooshes en el mismo momento.
- El pico del whoosh cae EXACTO en el frame del corte (pre-roll 2–3 frames).
- Lo pequeño suena quieto y corto; lo grande suena grande. Densidad: máx ~8–12
  cues/min.

## Arreglo por compases (bar-splice)

Cuando la música generada no cae en los momentos del video, se re-arregla por
compases en vez de regenerar:

- Copiar compases completos (múltiplos de 4 beats) para que el fraseo siga
  musical; cada drop destino se toma de un compás fuente donde un build
  resuelve en drop.
- Un hueco entre segmentos (ej. beats 38–40 vacíos) es un **silent stop**: el
  lugar clásico para una línea de impacto justo antes del drop.
- Empalmes con crossfades cortos (30ms, ver `reglas-tecnicas.md`) que terminan exactamente en el
  downbeat destino; el primer segmento arranca en 0s.
- Mezcla de referencia: música ~15 dB bajo la voz mientras habla, sube en los
  huecos sin tapar la entrada de la voz. Target de plataforma: −14 LUFS
  (enérgico) / −16 LUFS (calmo), TP −1.5, LRA 11 (ver `checklist-qa.md`).

### Beat-sync: music mapping y visual matching

Para edición sincronizada al beat (trailers, montajes):

- **Music mapping**: marcar downbeats, intervalos, acentos y secciones de
  energía de la pista (con `beat_grid.py`). 6–12 hit points por pieza.
- **Timeline**: los cambios visuales fuertes caen en los hits fuertes; los
  suaves, en hits débiles.
- **Visual matching**: en cada corte al beat, cambiar escala, dirección,
  brillo o color — el corte se siente como música, no como costura.

## Checks

- La voz tiene per-scene gain para −14 LUFS (enérgico) / −16 LUFS (calmo),
  picos ≤ −1 dBFS.
- El fade-out final ≥1.5s de cola; nada nuevo después del último hit.
- Medir el balance música/voz numéricamente (RMS en voz y en huecos), no solo
  a oído: la música puede "desaparecer" si queda demasiado bajo el mix.
