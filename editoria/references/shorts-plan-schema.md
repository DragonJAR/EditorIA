# shorts-plan.json — contrato del short

El plan es el contrato: fija qué, cuándo y dónde antes de renderizar.
`shorts_plan.py` lo valida contra este schema y lo ejecuta paso a paso
(cortes → hook overlay → captions → música → loudness → portada).

```json
{
  "fuente": "charla.mp4",
  "salida": "short_final.mp4",
  "formato": "1080x1920",
  "segmentos": [
    {"id": "hook", "from": 12.5, "to": 15.5, "hook_overlay": "ESTO LO CAMBIA TODO"},
    {"id": "cuerpo", "from": 45.0, "to": 75.0, "titulo": "El dato clave"}
  ],
  "captions": {"srt": "subs.srt", "phrase_aware": true},
  "musica": {"archivo": "musica.mp3", "db_bajo_voz": 15},
  "loudness_lufs": -14,
  "portada": {"at": 1.0}
}
```

## Campos

| Campo | Requerido | Default | Notas |
|---|---|---|---|
| `fuente` | sí | — | video largo de origen (ruta relativa = relativa al plan) |
| `salida` | no | `{fuente}_short.mp4` | |
| `formato` | no | `1080x1920` | `1080x1920` o `1920x1080`; si la fuente no coincide se recorta al centro |
| `segmentos` | sí (≥1) | — | lista ordenada de rangos a conservar |
| `segmentos[].id` | sí | — | identificador único |
| `segmentos[].from` / `.to` | sí | — | segundos, dentro de la duración de la fuente |
| `segmentos[].hook_overlay` | no | — | texto quemado sobre el segmento (típico en el primero, 1–3s) |
| `segmentos[].titulo` | no | — | título para `chapters.py` |
| `captions.srt` | no | — | SRT a quemar con identidad de marca. Los tiempos
van en la **fuente**; `shorts_plan.py` los re-mapea automáticamente al
timeline del short (los cues fuera de los segmentos se descartan) |
| `captions.phrase_aware` | no | `true` | agrupación frase-consciente |
| `musica.archivo` | no | — | pista a mezclar bajo la voz |
| `musica.db_bajo_voz` | no | `15` | la música queda ~15 dB bajo la voz (regla de la skill) |
| `loudness_lufs` | no | `-14` | `-14` enérgico / `-16` calmado |
| `portada.at` | no | — | segundo del frame de portada (`{salida}_portada.png`) |

## Reglas de validación

- `from < to`, ambos ≥ 0 y dentro de la duración de la fuente.
- Los segmentos no se solapan (se ordenan por `from`).
- La duración total SHOULD ser ≤ 180s (formato short); si la excede, aviso.
- El hook (`hook_overlay` en el primer segmento) SHOULD durar 1–3s.

---

→ Canónico: `references/plan-video.md` · Dominio: plan · Vecinos: `references/modos-rapidos.md`, `references/formatos.md`, `references/mapa.md`
