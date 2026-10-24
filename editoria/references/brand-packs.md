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
  **La paleta no se hereda: se elige** del catálogo de `references/paleta.md`
  según la teoría del color y el brief (tema, sector, emoción). El respaldo
  del modo libre es un azul frío sin identidad, deliberadamente distinto del
  rojo del pack de ejemplo: una pieza sin marca no debe parecerse a ninguna.

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

`colores.blanco` y `colores.negro` son la **TINTA** de la marca: el color del
texto de la pieza. El motor la instala (`BLANCO`) y el verificador de
dirección de arte le exige 7:1 sobre el fondo. Todo lo que lleve texto la
viste, incluido el titular del hook de un short (`shorts_plan.py`), que la
elige por contraste contra el acento. Si la tinta de la marca no llegara al
piso de 4.5:1 sobre ese acento, se usaría la neutra de la skill: la
legibilidad no se negocia.

Todas las herramientas leen el pack con las mismas funciones
(`scripts/ffmpeg_tools/_comun.py`: `colores_marca`, `fuente_marca`,
`ruta_de_pack`, `identidad_pieza`). Sin `--brand` (ni `"brand"` en el plan)
TODAS usan la paleta del modo libre: la que se declara con `--paleta` (o con
el campo `"paleta"` del plan), y si no, la neutra de respaldo (`NEUTRO`).
Ninguna herramienta carga una marca por defecto. Un pack sin `colores.acento` (ni
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
  claro y recurrente). El fondo de la `apertura` ES un rol claro y recurrente:
  la silueta de la marca crece y se encoge detrás del titular, siempre en el
  color de la marca y siempre de fondo, nunca como firma.

## Crear un pack nuevo

1. Copiar `brand/dragonjar.json` (el pack de ejemplo) como plantilla.
2. Rellenar colores, tipografías (rutas reales a .ttf/.otf), logos (PNG con
   alfa) y voces.
3. Declarar `reglas` solo si la marca las tiene; no inventar restricciones.
4. Verificar el contraste de los colores sobre el lienzo:
   `python scripts/direccion_arte.py verificar brand/nuevo.json` (tinta ≥ 7:1,
   apoyo ≥ 4.5:1, acento ≥ 4.5:1; un acento entre 3 y 4.5 solo sirve en texto
   grande, no en subtítulos ni cifras pequeñas).
5. Probar: `scripts/ffmpeg_tools/caption.py --brand brand/nuevo.json ...`
   y un render de `scripts/render_plan.py` con el style pack correspondiente.

Sin marca, `scripts/direccion_arte.py elegir` genera un **style pack** (estilo,
no marca) con el mismo formato, listo para `--brand`; con un pack del usuario
manda el pack (`references/direccion-de-arte.md`).

## En los scripts

- `render_plan.py --brand` (o `"brand"` en el plan): colores, tipografías,
  logos y reglas.
- `caption.py`, `thumbnail.py`, `audio_viz.py`, `shorts_plan.py` con
  `--brand`: acento, fuente y defaults de subtítulos del pack.
- `film_marca_v2.py --brand pack.json` (o `--logo`, `--nombre`, `--lema`):
  film de marca de 15 s sobre el logo del pack; sin logo no hay film.

## De dónde sale el pack

Hoy, de un JSON escrito a mano (`brand/mi_marca.json`). **También de un
fichero de diseño**: Figma o su alternativa open source **Penpot**
(MPL-2.0, con servidor MCP para que el agente lea los ficheros de diseño),
y el skill `/figma` de HyperFrames para lo mismo.

Por qué importa: el pack es la **fuente de verdad de la marca** y de ahí
salen los tokens de todo lo que acompaña a la pieza —el diagrama
(`references/diagramas.md`), los subtítulos, el thumbnail, el HTML que se
entrega. Si el proyecto tiene un fichero de diseño, el JSON tiene que **derivar
de él** y no ser un segundo sitio donde vive la marca.

La regla: **un pack, una fuente**. Si hay fichero de diseño, se deriva el
JSON de ahí y se declara cuál manda; si no, se escribe el JSON a mano y se
declara que es la fuente. Lo que no puede pasar es tener las dos cosas y que
se contradigan.

---

→ Canónico: `references/brand-packs.md` · Dominio: marca · Vecinos: `references/principios.md`, `references/copy.md`, `references/mapa.md`
