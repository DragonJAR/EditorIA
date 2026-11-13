# Handraw estilo — stills con biblioteca numerada (capacidad)

Biblioteca de **estilos y layouts para generación de imagen** (no un motor de
video). Sirve cuando la pieza necesita un still, portada o ilustración con
look de mano reconocible y un índice estable de estilos.

Fuente: [yang0/handraw-style](https://github.com/yang0/handraw-style).

## Atribución obligatoria (yang0)

El autor pide conservar el crédito. En EditorIA:

1. Este documento y `references/creditos.md` citan **yang0** y
   `https://github.com/yang0/handraw-style`.
2. `scripts/motores_externos.py receta --id handraw-estilo` imprime la línea
   de atribución en cada receta.
3. Si un entregable o doc del proyecto se basa en esa biblioteca, la entrega
   menciona al autor y el repo (no basta con un «estilo hand-drawn» genérico).

Licencia: MIT **con requisito de atribución** (ver `LICENSE` del repo).

## Cuándo usarla

- Portada, thumbnail o ilustración de apoyo con estilo numerado (FA–FI /
  001–370), layout SC/IG/SB/IP/EC y color C-01…C-36.
- El agente tiene herramienta de generación de imagen y el brief pide un look
  de mano coherente, no un frame pintado en código.

## Cuándo NO

| alternativa | cuándo gana |
|---|---|
| `hand-draw` | overlay de trazo / pizarra sobre video |
| `canvas` / `pintura-cpu` | cada marca es código (determinista), no un prompt IA |
| `dibujado` | personaje animado con poses |

## Cómo se pide (catálogo único)

```bash
python scripts/repertorio.py sugerir --pedido "portada estilo handraw numerado"
python scripts/repertorio.py resolver --id handraw-estilo
python scripts/motores_externos.py receta --id handraw-estilo
```

## Cómo se produce

1. Clonar en `/tmp/handraw-style` (receta).
2. Elegir estilo + layout + tema en `STYLES.md` / `LAYOUTS.md` del clone.
3. Generar el still con la herramienta de imagen del agente (el skill no
   trae un renderer propio: son prompts verificados).
4. Montar el PNG en el plan / EDL / thumbnail.
5. `rm -rf /tmp/handraw-style`. No vendorizar los 365 estilos dentro de
   EditorIA.

## Qué se descartó

| pieza | por qué |
|---|---|
| Skills satélite (IP designer, couple photo, tweet importer…) | Fuera del oficio de video |
| Community / WeChat / Feishu como dependencia | Operación del autor, no de la skill |
| Video `handraw-video` | El README lo separa; EditorIA ya tiene motores de video |

---

→ Canónico: `references/motores-externos.md` · Dominio: herramienta · Vecinos: `references/creditos.md`, `references/hand-draw.md`, `references/capacidades.md`, `references/thumbnails.md`
