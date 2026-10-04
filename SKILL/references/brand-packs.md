# Brand packs (sistema marca-blanca)

EditorIA es marca-blanca: la doctrina no hardcodea identidad — vive en un
**brand pack**: un JSON en `brand/` (ej. `brand/dragonjar.json`). Los scripts
exponen `--brand` (o `--color`/`--font`) para sobreescribir sus defaults.
El agente carga el pack al inicio del proyecto y el pack manda sobre los
defaults creativos.

## Los dos modos

- **Con brand pack**: el pack fija identidad y reglas. El brief aporta el
  contenido; el pack, los límites. (Ej. `brand/dragonjar.json`.)
- **Modo libre** (sin pack): no hay límites de marca. El agente elige paleta,
  tipografías, idioma de transición y voz según el brief y el tono, con el
  único criterio de que la pieza se vea intencional y premium. Este es el
  modo por defecto cuando el usuario no nombra una marca.

Regla de oro: **el pack manda sobre el preset; el brief manda sobre todo**.
Nunca inventar identidad de marca (colores, logos, slogans): si el usuario
pide una marca sin pack, pedir el pack o los assets antes de producir.

## Spec del pack

```json
{
  "nombre": "MiMarca",
  "version": "1.0.0",
  "colores": {
    "acento": "#E8480C",
    "blanco": "#FAF8F6",
    "negro": "#0A0A0A"
  },
  "tipografias": {
    "titulares": {"familia": "Mi Fuente Titular", "archivo": "/ruta/a/fuente.ttf", "pesos": [700, 800]},
    "texto":     {"familia": "Mi Fuente Texto", "archivo": "/ruta/a/fuente.ttf", "pesos": [400, 600]},
    "etiquetas_mono": {"familia": "Mi Fuente Mono", "archivo": "/ruta/a/fuente.ttf"}
  },
  "logos": {
    "isotipo": "/ruta/a/isotipo.png",
    "logotipo": "/ruta/a/logotipo.png"
  },
  "voces": {"es": "Fernanda Sanmiguel", "en": "Brian"},
  "caption": {"position": "center", "size": 28, "bold": true, "karaoke": true},
  "reglas": {
    "transiciones": "corte_seco | crossfade | libre",
    "rejillas_decorativas": false,
    "isotipo_con_protagonista": false
  }
}
```

Campos obligatorios: `nombre`, `colores.acento`. Todo lo demás es opcional;
lo que falte lo decide el agente con criterio (y lo documenta en el brief).
Nota: `load_brand` no valida el schema — si falta el acento, los scripts usan
sus defaults en silencio. Verificar el pack a ojo antes del primer render.

Claves `reglas` reconocidas:
- `transiciones`: idioma de transición por defecto de la marca.
  `corte_seco` = cortes editoriales secos, crossfades solo como excepción
  motivada. `libre` = el tono de la pieza elige.
- `rejillas_decorativas`: si la marca prohíbe rejillas/líneas como fondo.
- `isotipo_con_protagonista`: si el isotipo puede compartir plano con un
  protagonista grande (casi siempre `false`: o no aparece, o tiene un rol
  claro y recurrente).

## Crear un pack nuevo

1. Copiar `brand/dragonjar.json` como plantilla.
2. Rellenar colores, tipografías (rutas reales a .ttf/.otf), logos (PNG con
   alfa) y voces.
3. Declarar `reglas` solo si la marca las tiene; no inventar restricciones.
4. Probar: `scripts/ffmpeg_tools/caption.py --brand brand/nuevo.json ...`
   y un render de `scripts/render_plan.py` con el style pack correspondiente.

## En los scripts

- `caption.py --brand pack.json`: aplica fuente, colores y defaults de
  subtítulos del pack.
- `render_plan.py`: el style pack del plan puede referenciar colores del
  brand pack (ver `references/plan-video.md`).
- `film_marca*.py`: piezas de ejemplo atadas a la marca DragonJAR; con otra
  marca, usar `references/cine.md` como receta y el pack correspondiente.
