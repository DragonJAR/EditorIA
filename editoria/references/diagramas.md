# Diagramas (capacidad)

Un diagrama es un entregable: explica una estructura (arquitectura, flujo,
estados, datos, secuencia, despliegue) mejor que un párrafo. Se entrega como
**un solo fichero HTML con el SVG dentro**, que se abre en cualquier navegador
y se exporta a PNG/PDF.

**EditorIA no dibuja diagramas**: produce video. Lo que hay aquí es cómo
usar una herramienta externa **con la marca de la pieza**, porque el fallo
típico de un diagrama no es que quede feo: es que quede genérico, con la
tipografía y los colores por defecto de la librería, en un proyecto que sí
tiene identidad.

## La herramienta

`cathrynlavery/diagram-design` (MIT): 45 tipos visuales (arquitectura,
delta de arquitectura, estado actual, flujo, secuencia, máquina de estados,
ER, línea de tiempo, swimlane, quadrant, radar, Sankey, fishbone, Wardley,
kanban, journey, service blueprint, despliegue, grafo de dependencias, UML,
story map, heatmap, waterfall, Gantt, treemap, Venn, pirámide, embudo, capas,
axonométrica, organigrama, árbol, loop, medallion, matriz de seguridad, DP,
polar, bubbles…), más semánticas de comportamiento y primitivas.

- Salida: **un HTML autocontenido** con SVG en línea.
- Importa: Mermaid, `.drawio` y Excalidraw.
- Referencia de estilo: el fichero `style-guide.md` de su carpeta de
  skills (en el repo del proyecto, no en esta skill).

## La puerta que importa: la guía de estilo

Antes de generar el primer diagrama de un proyecto, la herramienta exige
**verificar que la guía de estilo está personalizada**. Sin ese gate, el
diagrama sale con la piel de la librería: los colores y las tipografías por
defecto de una herramienta que no conoce a la marca.

En esta skill, la guía de estilo **ya existe y ya es un dato**: es el
**brand pack** (`references/brand-packs.md`). Los tokens del pack —acento,
tipografías, radios, pesos— son la guía de estilo del diagrama. La
equivalencia es directa:

| la herramienta pide | esta skill lo tiene en |
|---|---|
| paleta de marca | `brand/mi_marca.json` → `colores.acento`, `colores.neutro` |
| tipografías | `brand/mi_marca.json` → `tipografias` |
| radios, pesos, espaciado | los del pack, y `references/reglas-tecnicas.md` |
| la forma de "no enviar esto sin personalizar" | el brand pack es la **fuente**; sin pack, `references/paleta.md` elige una paleta y el diagrama declara que usa modo libre |

**Modo libre**: si la pieza no tiene marca, se elige paleta de
`references/paleta.md` y **se dice en el entregable** que va en modo libre
—igual que se dice en el video. Un diagrama sin identidad declarada es un
diagrama con la piel de otro.

## Qué se escribe en el diagrama y qué no

- **El diagrama explica una estructura; no lleva el texto de la pieza.** El
  copy del diagrama es técnico y corto (nombres de servicio, campos,
  estados), y eso lo hace legible a tamaño de pantalla.
- **La marca entra por los tokens**, no por el estilo: acento, tipografía,
  grid. Un diagrama con la paleta de la marca y con las tipografías del
  sistema sigue siendo un diagrama de otra marca.
- **Un diagrama no es una escena de vídeo.** Si la pieza explica el
  diagrama, el diagrama es el **material** de la escena (como un overlay con
  alfa, vía `references/3d.md`/`modos-produccion.md`), no un plano que se
  invente en el motor.

## Dónde encaja

`references/modos-produccion.md` es el sitio natural para el flujo (capturar
→ estructurar → generar → exportar). Este documento es la **referencia de la
capacidad**; el flujo, en su sitio.

---

→ Canónico: `references/modos-produccion.md` · Dominio: herramienta · Vecinos: `references/brand-packs.md`, `references/paleta.md`, `references/principios.md`, `references/copy.md`
