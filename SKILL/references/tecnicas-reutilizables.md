# Técnicas reutilizables — análisis del video AI Tinkerers #20

Fuente: video de 61s, 1080×1920 @60fps, hecho por otro agente para la edición
#20 de AI Tinkerers Manizales. Catálogo de todo lo reutilizable, organizado por
categoría. OJO: su sistema de color (lima + morado sobre negro) es de AI
Tinkerers, NO de DragonJAR — las técnicas se portan, los colores no.

## Fondo y ambiente

- **Aurora de ondas**: fondo vivo de ondas fluidas verde/morado sobre negro
  oscuro, con blur fuerte. Da profundidad sin distraer. Equivalente DragonJAR:
  ondas en el acento profundo del pack (punto de partida: `mundo()` en
  `scripts/render_plan.py`).
- **Líneas de contorno topográficas**: líneas finas claras sobre las ondas,
  como curvas de nivel. Añaden textura técnica con costo casi nulo.
- **Viñeta + grano**: los bordes siempre más oscuros; el sujeto respira al centro.

## Sistema tipográfico

- **Kicker monoespaciado**: etiquetas como "EDICIÓN", "MESES SEGUIDOS",
  "LINE-UP DE HOY" en mono, mayúsculas, tracking amplio, color acento.
  Van SIEMPRE arriba del titular, nunca solas.
- **Número cinético bicolor**: "#" en color acento + dígitos en blanco
  ("#20"), tamaño gigante (~300px en 1080×1920). El "#" ancla la marca del
  conteo; los dígitos cambian.
- **Contador animado**: el número sube de #17→#20 con spring (ticking).
  Técnica: interpolar el entero con easing y overshoot leve.
- **Frase cinética por palabras**: "Lo que no se ve, / no se entiende."
  Aparece palabra por palabra; la palabra clave ("entiende") en acento.
- **Comparativa cinética**: "1 visual > 100" — número + símbolo + número,
  cada parte entra con su propio spring. Ideal para claims.

## Componentes

- **Lanyard (credencial colgante)**: tarjeta de ponente colgando de una cinta
  desde arriba — foto/inicial en círculo, nombre, charla, cinta con
  "AI TINKERERS MANIZALES #20 · PONENTE". Oscila sutilmente (péndulo).
  Persiste entre segmentos del mismo ponente = continuidad.
- **Chip pill**: "AI Tinkerers Manizales" — pastilla con mini-logo + texto.
  Reutilizable como firma de serie en intros/outros.
- **Pill de dato**: "en menos de 24 h" — pastilla oscura con icono + texto.
  Para constraints y footnotes importantes.
- **Chip técnico**: "Modelo pequeño 8B" — tarjeta con icono chip + label +
  spec en acento. Para specs de modelos/herramientas.
- **Tarjetas de features**: fila de 3 (Pestañas / Subagentes / Plugins),
  cada una con icono en acento + label; entran en cascada con stagger 0.15s.
- **Filas de line-up**: lista numerada (1 Andrés · OPENCODE 2) — número en
  círculo de acento + nombre + tag a la derecha en kicker. Stagger por fila.

## Visualización de datos

- **Grid que se enciende**: 20 celdas numeradas (5×4) que se iluminan una por
  una con stagger, caption "MESES SEGUIDOS" debajo. Para conteos y streaks.
- **Stat gigante + caption**: "35M" bicolor (35 en acento, M en blanco) +
  "tokens en una sola tarea". El número es el héroe; el caption explica.
- **Gauge semicircular**: arco de acento + aguja + "1.600 / TOKENS SEGUNDO".
  La aguja barre con easing al entrar.
- **Métrica + unidad**: "145 ms" gigante + "DE RESPUESTA" en kicker.
  Unidad siempre en kicker, nunca al mismo tamaño.
- **Barras benchmark**: 8 barras que crecen con stagger + "BENCHMARK × 10".
- **Moneda**: círculo dorado "$0,02 / CENTAVOS" con glow. Para costos.
- **Grid de agentes**: N iconos robot en grid que se encienden + "18 sesiones
  a la vez". Para escala/concurrencia.

## Diagramas y mockups

- **Flecha de flujo**: "Agente → Servidor" — dos nodos + flecha en acento
  que se dibuja. Lo mínimo para explicar una arquitectura.
- **Teléfono con sesiones**: mockup de teléfono + lista de sesiones
  ("sesión · api") con dots verdes. Para CLIs y sesiones.
- **Terminal macOS**: ventana con semáforos (rojo/amarillo/verde) +
  "$ opencode" tipeado con cursor de bloque parpadeante. Para comandos.
- **Grafo de nodos**: hub "1 CONSOLA" con ramas a Antigravity/Codex/Grok/
  Claude — líneas en acento que crecen desde el hub. Para orquestadores.
- **Escenario isométrico 3D**: grid iso con zonas de color (ESCRITORIOS /
  CAFÉ / REUNIÓN) + cubos. Para spatially-explain un sistema.

## Ritmo y continuidad

- **Beat cada 2-4s**: un dato o componente nuevo por beat; nunca más de
  una idea por beat.
- **Lanyard persistente**: el badge del ponente se queda mientras dura su
  segmento — el espectador siempre sabe quién habla.
- **Stagger 0.12-0.2s**: grids, filas y barras nunca entran juntas.
- **Salidas con blur**: los segmentos salen con blur + fade, no con corte
  seco (contrasta con los cortes secos del pack DragonJAR — elegir según
  el brand pack del video).
- **Outro con CTA**: "#20" + chip de serie + "¡Y vamos por más!" en botón
  outline. Cierra con el próximo paso, no con el logo solo.

## Defectos detectados (no replicar)

- **"Agidra" / "AgyHydra"**: ninguna de las dos formas estaba en la
  transcripción — la palabra venía de una referencia de terceros sin verificar
  y se horneó en el badge de un ponente, donde sobrevivió 3 versiones. Lección:
  un nombre solo es "correcto" si aparece en la fuente; si no aparece, se
  marca [PENDIENTE], no se elige la forma "menos mala". Y ningún asset se
  hereda entre versiones sin re-auditar su texto.
- Transiciones con blur en un video cuyo brand pack fije cortes secos (ej.
  DragonJAR) romperían la regla — adaptar la técnica al pack, no copiarla tal cual.
