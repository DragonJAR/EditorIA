# Motores externos (clone-on-demand)

**No es un catálogo paralelo.** La elección del agente es
`scripts/repertorio.py` (mismas opciones `motor=tecnica` que canvas o
Remotion). Este documento y `scripts/data/motores_externos.json` son el
**detalle de producción** cuando hace falta clonar un kit bajo `/tmp`, usarlo
y borrarlo — el mismo patrón que los overlays talking-head.

```bash
python scripts/repertorio.py sugerir --pedido "explicar el gradiente con manim"
python scripts/repertorio.py resolver --id manim
python scripts/motores_externos.py receta --id manim
python scripts/motores_externos.py validar
```

## 0. Qué se adoptó (y qué no)

| id | cuándo | doc | repo |
|---|---|---|---|
| `manim` | matemáticas / algoritmos / pruebas | `references/manim.md` | [Yusuke710/manim-skill](https://github.com/Yusuke710/manim-skill) (MIT) |
| `handraw-estilo` | still/portada con estilo numerado (prompts IA) | `references/handraw-estilo.md` | [yang0/handraw-style](https://github.com/yang0/handraw-style) (MIT + atribución) |
| `pintura-cpu` | still o draw-on por etapas en numpy+Pillow | `references/pintura-cpu.md` | [cloveric/claude-drawing-skill](https://github.com/cloveric/claude-drawing-skill) (MIT) |

Inventario completo de la ronda (ya cubierto / descartado) vive en el JSON
(`ya_cubierto`, `descartado_a_proposito`) y en `references/creditos.md`. No
se reabre un menú «anidoodle vs canvas» ni «huashu vs estilos-codigo».

## 1. Cómo se produce

1. Elegir con `repertorio.py sugerir` / `resolver` (no con un menú aparte).
2. **Declarar** requisitos si faltan (`capacidades.md`).
3. `motores_externos.py receta --id …` imprime clone→setup→usar→rm.
4. Montar el MP4/PNG/GIF resultante en el EDL / plan de la pieza.
5. Limpiar `/tmp/<clone>`. No submodule. No vendorizar.
6. Puerta: `qa_entrega.py`.

## 2. Relación con el resto del mapa

| ya existe | qué aporta este detalle |
|---|---|
| `repertorio.py` | la **elección**; aquí la receta de clonado |
| `canvas.md` / `dibujado.md` / `hand-draw.md` | pintura viva, personaje, overlay de trazo |
| `remotion.md` / `hyperframes.md` | React / HTML determinista |
| `animacion.md` | oficio (incluye números destilados de LottieFiles) |
| `creditos.md` | licencias y atribución (yang0 obligatorio) |

## 3. Qué NO se trae

- Vendor de anidoodle, huashu, motion-skill studies, javascript-animation packs.
- Segunda superficie de elección («skills de animación»).
- Assets, demos o prompts enteros de los repos fuente.

---

→ Canónico: `references/animacion.md` · Dominio: herramienta · Vecinos: `references/capacidades.md`, `references/creditos.md`, `references/manim.md`, `references/handraw-estilo.md`, `references/pintura-cpu.md`
