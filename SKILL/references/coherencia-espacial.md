# Coherencia espacial — checklist

Los detalles minúsculos que hacen que un video se vea profesional.
Aplicar a cada escena antes de entregar.

## Alineación

- **Centros exactos**: todo lo centrado usa W/2 (540 en 1080×1920) o H/2.
  Verificar midiendo píxeles (o con la herramienta de visual grounding del agente), no "a ojo".
- **Iconos en tarjetas**: centro del icono = centro vertical de la tarjeta
  (ej. tarjeta h=124 → icono centrado en y=62, no 66).
- **Bloques de texto**: el bloque completo (todas las líneas) centrado
  verticalmente en su contenedor, no solo la primera línea.
- **Columnas decorativas**: centro matemático en W/2
  (ej. 7 columnas de 135px: x=135+ci*135 → centro 540 ✓; x=90+ci*135 → 495 ✗).
- **Elementos relacionados**: la mancha de entrada comparte centro con el titular
  que acompaña. El punto de interés del logo es el centro geométrico de cada plano.
- **Rótulos**: misma altura en todas las escenas (y=H*0.20 en el renderer de planes).
  Un rótulo que salta de altura entre escenas rompe el ritmo.
- **Márgenes laterales**: unificados (90px en el renderer de planes).
  Burbujas de chat, tarjetas y barras comparten el mismo margen.

## Coherencia visual

- **Un componente = un estilo** en todo el video. Una tarjeta no cambia de
  blanco a oscuro a mitad de escena; un icono no cambia de radio.
- **Fondo**: prohibidas rejillas/líneas decorativas (en video se ven mucho más
  fuertes que en un frame estático; el brand pack puede habilitarlas si la
  marca las pide). Profundidad con blobs a la deriva + viñeta.
- **Paleta**: un solo color de acento (el del brand pack, o el elegido en modo
  libre). El acento comunica, no decora.

## Diagramas

- **Auto-fit en nodos**: medir `textlength` de cada línea contra el diámetro
  del nodo ANTES de renderizar; reducir la fuente hasta que quepa (margen 20px).
  Un texto que desborda el nodo se ve amateur al instante.
- **Conexiones al borde, no al centro**: líneas y tentáculos terminan en el
  borde del nodo (centro + dirección × radio), nunca dibujados sobre el texto.
- **Sin rejillas decorativas**: la regla de fondo (arriba) aplica también
  dentro de los diagramas. Una grilla "3D" de fondo compite con el contenido.
  Retículas diegéticas dentro de un HUD: permitidas; como ambiente: prohibidas,
  salvo que el brand pack las habilite.
- **Diagramas vivos**: si el diagrama se dibuja en ~1s y su bloque dura 10s+,
  necesita movimiento idle continuo (nodos que respiran/flotan, dots viajando,
  pulsos avanzando). Nada quieto más de ~2s tras aparecer. Las aristas se
  re-dibujan cada frame siguiendo los centros flotantes.

## Verificación

1. Extraer frames en t fijos de cada escena.
2. Medir: ¿los centros están en W/2? ¿los márgenes son simétricos?
3. Comparar escenas contiguas: ¿el rótulo está a la misma altura?
4. Registrar cada defecto con su causa raíz en `reglas-tecnicas.md`.
