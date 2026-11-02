# Identidades de caption — detalle interno

**No es un catálogo paralelo.** La elección del agente es
`scripts/repertorio.py` (misma superficie que escenas, efectos y gestos).
Este documento y `scripts/data/captions_identidades.json` son el **detalle de
producción** cuando la opción resuelta tiene `motor=caption`.

Fuentes destiladas (sin vendorizar): HyperFrames registry `caption-style`
(~15 componentes listados + más vía `catalog`), doctrina drop/rail/embed
(captions-overlay), oficio IT Reelsmaker (Bar/Accent/Typewriter → rail
nativo), Remotion `@remotion/captions` (JSON word-timed; solo si el render
es Remotion).

```bash
# elección (catálogo único)
python scripts/repertorio.py sugerir --pedido "karaoke vertical talking head"
python scripts/repertorio.py resolver --id cap-rail-karaoke

# producción
python scripts/captions_identidades.py receta --id cap-rail-karaoke
python scripts/captions_identidades.py validar
```

## 0. Cuándo produce este motor

- Brief de **editar** footage con habla / VO y hace falta quemar o componer
  captions, **o**
- El pedido nombra un look (neon, slam, matte detrás de la cara, hablantes…).

Si basta el motor nativo (`preferir=nativo`) → `caption.py`. Si
`preferir=hyperframes` → declarar Node 22+ y seguir la `receta` (catalog add
o matte); nunca degradar a SRT plano en silencio.

## 1. Modelo drop / rail / embed

| Rol | Uso |
|---|---|
| drop | no mostrar fillers; el corte ya los quita cuando puede |
| rail | default; identidades `cap-rail-*`, `cap-hablantes` |
| embed | pico escaso; `cap-embed-matte` (+ slam HF si aplica) |

Reglas: ≤1 embed por beat; nunca dos co-visibles; rail lleva el verbatim.
Captions son **overlay**: no desplazar el centro del cuadro a 0.42×H para
“dejar banda” (salvo safe zone ya fijada por `--plan`).

## 2. Matte / oclusión

1. Cutout: `npx hyperframes remove-background` (o vía media-use del clone HF).
2. Stack: video → palabra embed → cutout encima (`z-index`).
3. `data-layout-allow-occlusion` en el cutout; juzgar con snapshot.
4. Cobertura del word box por el matte: **30–55 %** (menos flota; más se come).
5. Primer run del modelo ~168 MB; ~2 fps 1080p CPU — declarar coste/tiempo.

## 3. Relación con el mapa

| ya existe | qué aporta este detalle |
|---|---|
| `repertorio.py` | la **elección** |
| `flujo-talking-head.md` | la cadena corte→caption→master→publicar |
| `caption.py` | rail nativo (karaoke, pop/fade/slide, hablantes) |
| `hyperframes.md` | capacidad HTML + registry |
| `video-real.md` | oficio footage |
| `share-copy.md` | publicar tras la puerta |

## 4. Qué NO se trae

Inventario en el JSON (`descartado_a_proposito`): no menús de skills HF/
Reelsmaker/Remotion; no vendorizar HTML del registry; texture/blend on-demand
vía `npx hyperframes catalog`; online B-roll de pago solo con brief + “sí”.

---

→ Canónico: `references/flujo-talking-head.md` · Dominio: produccion · Vecinos: `references/video-real.md`, `references/hyperframes.md`, `references/formatos.md`, `references/share-copy.md`
