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
  caídas (donde entra el bajo) y los valles. `beat_grid.py` ya lo entrega:
  `secciones` (frases de 4 compases agrupadas por energía: intro, subida,
  pico, valle, outro) con su nivel y `cortes_cada_beats` sugerido. Mismo
  formato que `scripts/beat_file.py`, así la música analizada y la autorada
  se leen igual.
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
| **pico** | instante de un transitorio real de la música (clave `picos` de la rejilla) | el SFX pega donde la música pega, no donde cae el compás |
| absoluta | segundos exactos | solo cuando nada más funciona |
| escena + at | segundos después del corte de escena | entrances amarradas al corte |

La rejilla dice **dónde hay un compás**; los picos dicen **dónde hay un
impacto**. Un golpe de bajo, un stab o un acople en un tempo que no cae en
el beat es justo lo que un SFX de impacto debe encontrar: pegado al compás
se nota el retraso. `beat_grid.py` exporta los picos:

```bash
python scripts/beat_grid.py musica.mp3 --json grid.json
# grid.json: {bpm, beat0, compas0, duracion, compases, secciones, picos}
# picos: [{t, fuerza, db}, ...]
```

Los picos son **candidatos**, no cues: el agente elige los que casan con un
evento visible y respeta la densidad (máx 8-12 cues/min). Con `--delta` se
ajusta la sensibilidad (menor = más picos, mayor = solo los impactos más
fuertes) y con `--espera` el silencio mínimo entre ellos.

## El ensamblado: colocar y mezclar

La doctrina de arriba es el *diseño* del sonido; el ensamblado es el paso que
faltaba. Los cues se declaran en el propio plan (ver
`references/plan-video.md` § "Los SFX del plan") y `scripts/mezclar_audio.py`
los resuelve a su instante y los mezcla con la voz y la música:

```bash
# 1. el pack de efectos (una vez por proyecto)
python scripts/sfx.py -o assets/sfx/

# 2. la voz desde el plan (un segmento por escena, entra en from+0.4 s)
python scripts/voz_off.py plan.json -o voz.mp3 --guion guion.txt
python scripts/alinear.py voz.mp3 guion.txt -o voz.palabras.json

# 3. la rejilla de la música (para anclar por beat y por pico)
python scripts/beat_grid.py musica.mp3 --json grid.json

# 4. el ensamblado final: voz + música (duckeada) + SFX en su sitio
python scripts/mezclar_audio.py plan.json --video out.mp4 \
    --voz voz.mp3 --voz-palabras voz.palabras.json \
    --grid grid.json --pack assets/sfx --musica musica.mp3 -o final.mp4
```

Sin SFX la pieza tiene una cama de música debajo pero ningún golpe: suena a
video con fondo, no a pieza diseñada. Con SFX anclados, cada golpe visual
tiene su sonido y el final tiene su remate.

### El guion sale del plan, no de la cabeza

`alinear.py` necesita el guion para saber qué palabra cae en qué segundo. Si
el guion se escribe a mano, una palabra de más desplaza **todas** las anclas
de palabra en silencio: el SFX y la animación caen sobre la palabra
equivocada y nada falla. Por eso `voz_off.py --guion` escribe el guion desde
los campos `voz` del plan, en orden de escena, y **sin los tags de dirección**
(`[slowly]`, `[calm]`…): esos no se dicen, y si quedaran en el guion
`alinear.py` los contaría como palabras.

```
python scripts/voz_off.py plan.json -o voz.mp3 --guion guion.txt
```

El guion se escribe antes de llamar a la API: sirve aunque la voz todavía no
esté sintetizada (y aunque no haya key).

La salida avisa si la densidad de cues se sale de 8-12 por minuto, y salta
los cues que no puede resolver (ancla sin rejilla, palabra sin tiempos,
efecto que no está en el pack) en vez de fallar en silencio.

### El nivel de la música depende de si hay voz

| caso | nivel base | ¿ducking? | fade de salida |
|---|---|---|---|
| música **bajo** la voz | 0,12 (`--mus-vol`) | sí, por sidechain | no |
| música **sola** (sin voz) | 0,8 (`--mus-vol-solo`) | no | sí, 2 s (`--fade-out`) |

Con voz, la música es una cama: 0,12 es unos 15 dB bajo el habla. Sin voz, la
música **es** la pieza: bajarla a 0,12 la deja 16 dB más baja que en
`scripts/musica.py musiconly` y el video sale sin sonido útil. El
ensamblado elige el nivel solo según haya voz o no, y dice cuál usó:

```
OK final.mp4: 3 SFX, musica+voz (20.0s)
OK final.mp4: 3 SFX, musica sola (20.0s)
```


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

---

→ Canónico: `references/sonido.md` · Dominio: sonido · Vecinos: `references/sfx.md`, `references/ritmo.md`, `references/sonido.md`
