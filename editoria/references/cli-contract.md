# Contrato CLI de los scripts (SPEC-lite)

Convención de las herramientas de `scripts/ffmpeg_tools/`: flags
compartidos, errores con taxonomía, probe primero. Lo que está aquí no se
repite en cada script.

## Flags compartidos

Las CLIs de `ffmpeg_tools/` usan `add_common(ap)` + `apply_common(args)`
de `_comun.py` y terminan con `emit(output, ...)`. 16 de las 17 cumplen el
contrato entero; la excepcion es `variantes.py`: usa los flags compartidos,
pero produce N variantes en un directorio y por eso imprime sus rutas en vez
de emitir un JSON.

**Alcance**: el contrato es de `ffmpeg_tools/`. Las CLIs de `scripts/` —las
de análisis, render y medir— tienen su propia salida y sus propios errores, y
todavía no pasan por `add_common`/`emit`: cuando se muevan, el contrato es
este.

| Flag | Efecto |
|---|---|
| `--dry-run` | muestra los comandos ffmpeg que se ejecutarían, sin ejecutar nada |
| `--json` | última línea de stdout: documento JSON en vez de la ruta |

Reservados (no inventar variantes con otro nombre): `--fast` (preview),
`--progress` (porcentaje/ETA), `--timeout` (matar ffmpeg colgado),
`--overwrite` (permiso explícito para reemplazar un output existente).

## Errores con taxonomía

`die(msg, kind=...)` — con `--json` el error sale estructurado:

```json
{"status": "failed", "error": {"kind": "input", "message": "..."}}
```

| kind | Cuándo |
|---|---|
| `input` | el archivo/argumento no existe o es inválido |
| `ffmpeg` | falló ffmpeg/ffprobe |
| `output` | no se escribió el resultado esperado |
| `missing_tool` | falta un binario (con línea de instalación) |
| `timeout` / `interrupted` | se mató el proceso / Ctrl-C |
| `verification` | el output no pasa su propia verificación |

Sin `--json`: `ERROR: mensaje` en stderr + exit != 0 (comportamiento actual,
sin cambios).

## Probe primero

Ningún script decide desde el nombre del archivo: `probe()` de `_comun.py`
mide duración, fps (con detección de VFR), resolución, pix_fmt, HDR y audio
antes de planificar. El `--json` de cada herramienta ya puede llevar el probe
del output — no hacer un probe separado antes de cada paso.

## Reporte de un trabajo

Al terminar, cinco líneas con números medidos (del `--json` o del probe),
nunca de memoria:

```
Done: final.mp4 — 59.98 s, 1080x1920, 30 fps, H.264, AAC stereo, -14.1 LUFS
Steps: cut 0:12-1:12 -> fit 9:16 -> captions pop -> loudness -14 -> delivery reels PASS
Check: reels — 8/8 filas PASS (delivery_check.py)
Look: sheet.png (captions en zona segura, logo arriba-derecha)
Notes: la fuente era VFR, se conformó a 30 fps
```

Si falla: `Done:` se vuelve `Failed:` con el `error.message` citado, no
parafraseado. `Look: not needed` solo en trabajos sin cambio de imagen.

---

→ Canónico: `references/instalacion.md` · Dominio: operacion · Vecinos: `references/capacidades.md`, `references/arquitectura.md`, `references/mapa.md`
