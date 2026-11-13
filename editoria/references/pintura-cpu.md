# Pintura CPU — stills y draw-on con numpy+Pillow (capacidad)

Ilustración por código **sin Node ni Chrome**: biblioteca Python
(numpy + Pillow) con decenas de estilos y guardado por etapas (GIF «se va
pintando»). Fuente clone-on-demand:
[cloveric/claude-drawing-skill](https://github.com/cloveric/claude-drawing-skill)
(MIT).

## Cuándo usarla (y declararla si falta)

- Still o secuencia de etapas en CPU; el entorno no tiene (o no quiere) p5.
- El brief pide un look de tinta / acuarela / pixel / etc. como **imagen** o
  reveal por etapas, no como personaje animado.

## Frontera con lo que ya hay

| técnica | diferencia |
|---|---|
| `canvas` | p5 + Chrome; frame = f(t) vivo; lyric/videoclip |
| `dibujado` | poses redibujadas, rotoscopio, arena |
| `hand-draw` | polilínea → PNG overlay |
| `handraw-estilo` | prompt IA + índice de estilos (no pinta en código) |
| `pintura-cpu` | **esta**: Python CPU, estilos del clone, stages/ |

## Cómo se pide (catálogo único)

```bash
python scripts/repertorio.py sugerir --pedido "ilustración draw-on sin node"
python scripts/repertorio.py resolver --id pintura-cpu
python scripts/motores_externos.py receta --id pintura-cpu
```

## Cómo se produce

1. Clonar + `pip install -r requirements.txt` (receta).
2. Correr un `examples/<estilo>.py out.png --stages stages/` o la API `lib/`.
3. Montar PNG/GIF en el EDL; la puerta es la de siempre.
4. Limpiar `/tmp/claude-drawing-skill`. No vendorizar ejemplos ni thumbs.

## Qué se descartó

| pieza | por qué |
|---|---|
| Los ~320 MB de ejemplos/thumbs en la skill | Clone-on-demand basta |
| Sustituir `canvas` por defecto | p5 sigue siendo la vía pictórica viva |
| Menú «83 estilos» paralelo al repertorio | Un id `pintura-cpu`; el estilo es perilla |

## Licencia

MIT (ver LICENSE del clone). Créditos: `references/creditos.md`.

---

→ Canónico: `references/motores-externos.md` · Dominio: herramienta · Vecinos: `references/canvas.md`, `references/hand-draw.md`, `references/capacidades.md`, `references/creditos.md`
