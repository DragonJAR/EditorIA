# Lenguajes visuales aprendidos

Tres direcciones probadas en producción. Elegir según el brief; se pueden hibridar.

## 1. Cinético (Demo)
- Referencia: video demo de tipografía cinética (7 s).
- Neutro oscuro de fondo, kicker monoespaciado en el acento, barra de acento,
  titular gigante en la fuente de titulares (ExtraBold) en blanco.
  Una idea por tarjeta, cortes secos.
- Ideal: cifras sueltas, anuncios cortos, titulares.
- Ritmo: 2,5–3 s por tarjeta.

## 2. Resumen animado (nivel estudio)
- Referencia: video de 61 s de "otro agente" sobre AI Tinkerers #20 (no incluido).
- Estructura: intro con número de edición + grilla que se enciende → line-up numerado →
  por ponente: badge tipo lanyard (foto/inicial + nombre + tema) + 3–5 visualizaciones
  (chips, tarjetas, gauges, barras, teléfono mockup, grilla isométrica, terminal) → outro.
- Fondo: ondas/aurora animadas en el color de acento sobre negro. Elementos entran con
  fade + elevación suave (0,35–0,45 s). Nada de motion gratuito: cada animación presenta información.
- El lima del original se reemplaza 1:1 por el acento del pack (o del modo libre).
- Arquitectura del build original (no incluido en el paquete): un script de
  fondo, uno de elementos y uno de ensamblaje. Para el fondo vivo, partir de
  `mundo()` en `scripts/render_plan.py`.
- Ritmo: ~60 s para 4 bloques de ponente; 8–13 s por bloque.

## 3. Tarjeta informativa (Wapid)
- Referencia: prueba estilo Wapid (4 s). Tarjeta oscura con `BREAKING NEWS`,
  cifra heroica y chips de contexto.
- Ideal: un solo dato con contexto, alertas, comunicados.

## 4. Demo de edición IA (split original/editado)
- Referencia: Reel público de un creador, "Claude Opus 5.5 edited 100% of this
  video" (55 s, screen recording 480×1032; no incluido).
- Formato: pantalla dividida — arriba el editado (etiqueta "CLAUDE OPUS 5.5"),
  abajo el original (etiqueta "ORIGINAL"). El formato demo ideal para probar
  que la IA edita como un pro.
- Técnicas (cada una replicable, en orden de aparición):
  1. **Tipo cinética cromada**: "WATCH THIS / CLAUDE CAN FINALLY EDIT / LIKE A PRO."
     Palabras gigantes que entran una por una; textura metálica = degradado vertical
     sobre el texto (replicable: máscara de luminancia + gradiente).
  2. **HUD de visión por computador**: tinte rojo sobre el footage, cajas de detección
     con etiqueta + score en mono ("MASK 0.97", "PLANT 0.93", "CAMERA 0.98"),
     crosshairs, datos técnicos en esquinas. Estética "la IA está analizando".
  3. **Captions palabra por palabra** con la palabra activa destacada (requiere
     transcripción con tiempos de palabra).
  4. **Segmentación**: persona recortada con borde luminoso, fondo oscurecido
     (nivel avanzado: requiere segmentación real, ej. RVM del pipeline original).
  5. **Tracking 3D**: objeto 3D que sigue un punto (mano). Aproximación: keyframes manuales.
  6. **Data overlays**: callouts con datos + visualización ("1 CAN = 10 CUBES = 40g",
     barra de límite diario). Ya dominado en el v2 (gauge, barras, coin).
  7. **Transición matrix**: lluvia de código + frase "It all becomes code:
     cuts, captions, animation."
  8. **CTA final**: "COMMENT 'EDIT' FOR THE FULL GUIDE" — cierre con llamado a la acción.
- El tinte del HUD es el acento del pack; tipografía del sistema.

## 5. Demo reel EditorIA (construido 2026-10-03, técnicas propias)
- Build original de 42 s, 1080×1920, 1260 frames bakeados en PIL (no incluido;
  las técnicas se describen abajo para reimplementarlas).
- Técnicas implementadas y reutilizables:
  1. **Texto cromado**: degradado vertical (blanco→gris→oscuro→claro) por máscara de
     alfa del texto + sombra roja sutil. Función `chrome_word()`.
  2. **Slam cinético**: palabras que entran con escala 2.3→1.0 (ease-out) + fade,
     bakeado por frame. Auto-fit del tamaño a la línea más ancha (≤1000px).
  3. **HUD de visión**: rejilla tenue, scanline roja con glow, cajas de detección con
     esquinas blancas + etiqueta mono con score, crosshair en trayectoria lissajous,
     readouts "ANALIZANDO FRAME / FRAME nnnn / ● REC".
  4. **Lluvia matrix roja**: columnas de katakana/dígitos cayendo, cabeza blanca,
     estela roja con fade; panel central para el mensaje.
  5. **Captions palabra por palabra**: palabra activa en rojo, resto blanco→gris.
- Lección de memoria: NO acumular frames PIL en lista (1260 frames ≈ 10 GB → SIGKILL);
  guardar cada frame al generarlo (`emit()` incremental).

## 6. Catálogo AI Tinkerers #20 (analizado 2026-10-03)
Video de referencia de 61s @60fps hecho por otro agente. Catálogo completo de
técnicas en `references/tecnicas-reutilizables.md`: aurora de ondas + líneas
topográficas, kicker monoespaciado, número cinético bicolor (#20), contador con
spring, lanyard colgante con péndulo, grid que se enciende (stagger), stat
gigante + caption, gauge con aguja, barras benchmark, moneda de costo, flecha de
flujo, teléfono con sesiones, terminal macOS con cursor, grafo de nodos desde
hub, escenario isométrico 3D, beats cada 2-4s, salidas con blur. Sus colores
(lima+morado) son de AI Tinkerers — portar las técnicas, no la paleta.

## Reglas transversales
- Ortografía perfecta en español (tildes: "sesión", "próxima", "más").
- Nombres propios verificados contra la fuente (ej. "Duberney", no "Dubernei";
  si la transcripción trae un nombre dudoso, se marca [PENDIENTE], no se inventa).
- Números con formato es-CO: "1.600", "35M", "$0,02".
- Kickers en monoespaciado con letterspacing, siempre en mayúsculas.
- El acento de color marca: lo importante, lo nuevo, la cifra. El resto, los neutros del pack o del modo libre.

## Style packs (tematizar por proyecto)

Antes de diseñar una pieza que
requiera un look distinto (serie, evento, cliente), escribir un **style pack**:
la especificación visual del proyecto, no un collage de referencias.

- **Paleta**: tokens de color nombrados (fondo, tinta, acento, highlights).
- **Tipos**: cara para titulares, cara para el acento/keyword, mono para
  datos/código; roles de cada una.
- **Personalidad de movimiento**: cómo se mueve este estilo — cortes duros con
  SFX, eases suaves, física con bounce, o cámara lenta y premium. Esta
  personalidad se aplica a transiciones, entradas y cámara en todo el video.
- **Lenguaje gráfico**: dispositivos firma reutilizables (barras de acento,
  píldoras, subrayados, iconografía) con su geometría definida una vez.
- **Look de fondos**: qué fondo vivo usa este estilo (aurora, ondas, papel,
  partículas) y con qué intensidad. Sin rejillas/líneas decorativas
  (ver `coherencia-espacial.md`: en video se ven mucho más fuertes que en
  un frame estático; el brand pack puede habilitarlas si la marca las pide).

Regla: style pack distinto → look distinto. Un video, un pack; no mezclar dos
packs en la misma pieza. Con brand pack, todos los packs comparten los colores,
logos y tipografías del pack; lo que cambia es la personalidad de movimiento
y el lenguaje gráfico (ej. con un mismo pack, una pieza de comunidad puede ser
más juguetona en motion que un film de marca).
