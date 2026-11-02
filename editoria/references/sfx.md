# SFX: capa de efectos de sonido

Doctrina adaptada de `/brag` (latent-spaces/brag). EditorIA genera la música
con `scripts/musica.py`; esta referencia cubre la capa que falta: efectos
puntuales mezclados como una pieza con la música, no pegados encima.

## Postura de mezcla

La música y los SFX se escriben como una sola pieza: los efectos van en el
mismo espacio que la música, mezclados adentro, nunca encima. Reglas:

- Los SFX van **suaves bajo la música**, nada áspero ni puntiagudo; los sonidos
  pequeños repetidos se quedan al fondo.
- Una paleta sonora coherente para todo el video vale más que una bolsa de
  sonidos simpáticos.
- En duda: menos cues con mejor timing. La música respira; los SFX puntúan.

## Generar el pack

`scripts/sfx.py` sintetiza un pack procedural (sin assets externos):

```bash
python scripts/sfx.py -o assets/sfx/
```

Produce WAV 44.1kHz mono: `click.wav`, `pop.wav`, `drop.wav`, `whoosh.wav`,
`ding.wav`, `thud.wav`, `tick.wav`, `swell.wav`. Ver el `--help` del script
para el carácter de cada uno.

## Tono → energía SFX

| Tono | Energía | Enfoque |
|---|---|---|
| `demo` | Moderada | 3–5 SFX en momentos clave. `click` en pasos, `ding` en el resultado, `thud` suave en reveals. |
| `resumen` | Moderada | `pop` por chip/tarjeta, `thud` suave por bloque de ponente, `ding` en la cifra heroica. |
| `anuncio` | Mínima pero presente | 2–3 acentos muy sutiles. `drop` en un reveal amable. Nada agresivo. |
| `trailer` | 2–3 grandes | `swell` en el hero, `thud` en el reveal, campana/`ding` grave en el outro. |
| `parodia` | Escasa pero presente | 2–3 cues secos. Un golpe seco por reveal, un acento UI. Restricción pulida. |
| `caos` | Densa | SFX en cada beat, a veces apilados. `whoosh` + `pop` + `thud` en capas. |

## Momento → sonido (heurística, no receta)

| Momento visual | Familias buenas | Notas |
|---|---|---|
| Tarjetas/chips que entran en secuencia | `pop`, `drop` | Acompañar el gesto. En secuencias densas, acentuar solo el primero, el último o los beats rítmicos. |
| Gran reveal / payoff | `swell`, `thud`, `ding` | Un solo anuncio corto cuando el reveal aterriza. Breve. |
| Texto que aparece / se tipea | `tick` (variar pitch), `drop` | Para tipeo por carácter, variar el pitch por caracter para no sonar robótico. Si el copy es denso, adelgazar o saltar. |
| Acción simulada (cursor, tap, toggle) | `click` | El sonido acompaña la acción visible: cursor, tap, botón, swipe. |
| Éxito / completado | `ding`, `pop` | Acento positivo para métricas, aprobaciones, CTAs finales. |
| Beat caótico o cómico | `whoosh`, `thud` | Reservar lo más ruidoso para tonos que lo aguantan. |

## Reglas de timing

Se aplican cuando los timings de la animación ya se conocen:

- Alinear el SFX al **inicio** de la animación, no al final.
- Entrada con pop: 0.0–0.1 s **antes** del primer frame visible del elemento.
- Transición: en el tiempo de inicio de la transición.
- Ding de éxito: cuando la métrica/cifra está **totalmente visible**.
- Elementos escalonados: acentuar el primero, el final o el beat más fuerte;
  sonorizar cada item solo cuando ese ritmo sea intencional y siga limpio.
- Notación en el plan:
  ```
  Escena 2 — Reveal — 3s
    "OPENCODE 2.0" entra con resorte en 0.3s → SFX: thud en 0.2s
    Chip 1 aparece en 0.8s                   → SFX: pop en 0.75s
    Transición en 3.0s                       → SFX: whoosh en 2.9s
  ```

## Mezcla en ffmpeg

Los SFX se mezclan con `amix`/`adelay` sobre el video final con música:

```bash
ffmpeg -i video_con_musica.mp4 -i sfx/pop.wav -i sfx/ding.wav \
  -filter_complex "[1:a]adelay=750|750,volume=0.5[s1]; \
                   [2:a]adelay=3200|3200,volume=0.6[s2]; \
                   [0:a][s1][s2]amix=inputs=3:normalize=0[a]" \
  -map 0:v -map "[a]" -c:v copy -c:a aac final.mp4
```

Niveles: ver "Regla de nivel" en `references/sonido.md` (canónico): volumen
base por tipo 0.28–0.5 × un solo master gain del kit (tope 0.8); con voz,
los SFX quedan −18 a −12 dB bajo ella. Nunca compiten con la voz. `scripts/medir_mezcla.py`
verifica la mezcla final.

---

→ Canónico: `references/sonido.md` · Dominio: sonido · Vecinos: `references/audio.md`, `references/reglas-tecnicas.md`, `references/auto-qa.md`
