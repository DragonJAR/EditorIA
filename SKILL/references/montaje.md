# Montaje — navaja suiza de edición (`scripts/ffmpeg_tools/montaje.py`)

18 operaciones de cirugía de clips en un solo script. Para composición
creativa usar `scripts/render_plan.py`; esto es cortar, unir, transformar
y convertir clips existentes.

## Cuándo usar cada operación

| Necesidad | Comando |
|---|---|
| Unir varios clips en uno | `unir a.mp4 b.mp4 -o final.mp4` (`--rapido` si mismo codec) |
| Recortar un tramo | `cortar v.mp4 --inicio 5 --fin 12 -o tramo.mp4` (`--rapido` = stream copy: cae en keyframe, puede empezar antes; sin `--rapido` el corte es exacto; VFR se conforma a CFR solo) |
| Fade in/out | `fundido v.mp4 --dentro 0.5 --fuera 1 -o out.mp4` |
| Transición entre 2 clips | `transicion a.mp4 b.mp4 --tipo dissolve --duracion 0.5 -o out.mp4` |
| Video sobre video | `pip base.mp4 overlay.mp4 --posicion abajo-derecha -o out.mp4` |
| Logo/marca de agua | `marca-agua v.mp4 logo.png --opacidad 0.7 -o out.mp4` |
| Sacar el audio | `audio extraer v.mp4 -o audio.m4a` |
| Quitar el audio | `audio quitar v.mp4 -o out.mp4` |
| Cambiar el audio | `audio reemplazar v.mp4 --fuente nuevo.m4a -o out.mp4` |
| GIF animado | `gif v.mp4 --fps 12 --ancho 480 -o anim.gif` |
| Fotos → video | `pase ./fotos --duracion 3 --zoom -o pase.mp4` |
| Rotar / voltear | `rotar v.mp4 --grados 90` · `voltear v.mp4 --eje horizontal` |
| Repetir | `bucle v.mp4 --veces 2 -o loop.mp4` |
| Llevar a 1080×1920 | `escala v.mp4 --tamano 1080x1920 -o vert.mp4` |
| Brillo/contraste/saturación | `color v.mp4 --brillo 0.1 --contraste 1.2 -o out.mp4` |
| Cámara rápida/lenta | `velocidad v.mp4 --factor 2 -o out.mp4` (0.25–4.0) |
| Al revés | `reversa v.mp4 -o out.mp4` |
| Limpiar voz (denoise) | `limpiar-audio v.mp4 -o out.mp4` |
| Chroma key | `chroma sujeto.mp4 fondo.png -o out.mp4` |

## Reglas

- Todas aceptan `-o` (default: sufijo automático) y `--crf`.
- `--dry-run` imprime el comando ffmpeg sin ejecutar; `--json` emite resultado máquina.
- Nunca sobrescriben el input; el output se verifica antes de reportar OK.
- Tiempos: segundos o `mm:ss` (`--inicio 1:30`).
- `transicion --tipo`: fade, dissolve, wipeleft, wiperight, wipeup, wipedown,
  circlecrop, radial, smoothleft, etc. (cualquiera de `ffmpeg -h filter=xfade`).
- `pip --hasta T`: el overlay solo aparece hasta el segundo T.
- `pase`: la carpeta se ordena alfabéticamente; `--zoom` agrega Ken Burns sutil.
