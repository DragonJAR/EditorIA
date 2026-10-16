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
  "lema": "Lo que hacemos, con *la palabra clave* en acento.",
  "colores": {
    "acento": "#E8480C",
    "blanco": "#FAF8F6",
    "negro": "#0A0A0A"
  },
  "tipografias": {
    "titulares": {"familia": "Mi Fuente Titular", "archivo": "assets/titular.ttf", "pesos": [700, 800]},
    "texto":     {"familia": "Mi Fuente Texto", "archivo": "assets/texto.ttf", "pesos": [400, 600]},
    "etiquetas_mono": {"familia": "Mi Fuente Mono", "archivo": "assets/mono.ttf"}
  },
  "logos": {
    "isotipo": "assets/isotipo.png",
    "logotipo": "assets/logotipo.png",
    "ancla": [512, 480]
  },
  "voces": {"es": "Fernanda Sanmiguel", "en": "Brian"},
  "caption": {"position": "center", "size": 28, "bold": true, "karaoke": true},
  "reglas": {
    "transiciones": "corte_seco | crossfade | libre",
    "rejillas_decorativas": false,
    "isotipo_con_protagonista": false,
    "efectos_glitch": false
  }
}
```

Rutas de archivos (`archivo`, `isotipo`, `logotipo`): absolutas, con `~`,
o **relativas a la carpeta del JSON** (recomendado: el pack viaja con sus
assets, ej. `brand/assets/`). Si un archivo no existe, se intenta por
`familia` en las fuentes del sistema y en las empaquetadas
(`assets/fonts/`: Plus Jakarta Sans y Montserrat, OFL).

Campos obligatorios: `nombre`, `colores.acento`. Todo lo demás es opcional;
lo que falte lo decide el agente con criterio (y lo documenta en el brief).
`lema`: frase de cierre de las piezas de marca (`*énfasis*` en acento).
`logos.ancla`: punto de interés del isotipo en px del PNG original (el ancla
compositiva de los films); sin él se usa el centro de masa del logo.

Todas las herramientas leen el pack con las mismas funciones
(`scripts/ffmpeg_tools/_comun.py`: `colores_marca`, `fuente_marca`,
`ruta_de_pack`, `identidad_pieza`). Sin `--brand` (ni `"brand"` en el plan)
TODAS usan la paleta neutra del modo libre (`NEUTRO`): ninguna herramienta
carga una marca por defecto. Un pack sin `colores.acento` (ni
`colors.primary`) es un error explícito, no un default silencioso.

Claves `reglas` reconocidas:
- `transiciones`: idioma de transición por defecto de la marca.
  `corte_seco` = cortes editoriales secos, crossfades solo como excepción
  motivada. `libre` = el tono de la pieza elige.
- `rejillas_decorativas`: si la marca prohíbe rejillas/líneas como fondo.
- `efectos_glitch`: si la marca admite RGB split, shake, strobe o hue shift
  sin que el brief los pida (`false` = solo a pedido).
- `isotipo_con_protagonista`: si el isotipo puede compartir plano con un
  protagonista grande (casi siempre `false`: o no aparece, o tiene un rol
  claro y recurrente).

## Crear un pack nuevo

1. Copiar `brand/dragonjar.json` (el pack de ejemplo) como plantilla.
2. Rellenar colores, tipografías (rutas reales a .ttf/.otf), logos (PNG con
   alfa) y voces.
3. Declarar `reglas` solo si la marca las tiene; no inventar restricciones.
4. Probar: `scripts/ffmpeg_tools/caption.py --brand brand/nuevo.json ...`
   y un render de `scripts/render_plan.py` con el style pack correspondiente.

## En los scripts

- `render_plan.py --brand` (o `"brand"` en el plan): colores, tipografías,
  logos y reglas.
- `caption.py`, `thumbnail.py`, `audio_viz.py`, `shorts_plan.py` con
  `--brand`: acento, fuente y defaults de subtítulos del pack.
- `film_marca_v2.py --brand pack.json` (o `--logo`, `--nombre`, `--lema`):
  film de marca de 15 s sobre el logo del pack; sin logo no hay film.
