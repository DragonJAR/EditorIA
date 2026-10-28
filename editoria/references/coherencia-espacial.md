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
- **Márgenes laterales**: unificados y tomados de la zona segura de la
  plataforma. En vertical son **151 px** (la unión de Reels, TikTok y Shorts,
  simetrizada por el lado derecho de TikTok, que es el que más invade). La
  tabla vive en `scripts/ffmpeg_tools/_delivery.py` y se recalcula por
  plataforma: **léela de ahí, no la memorices**. 90 px se sale de la zona
  segura de TikTok, que es justo donde viven sus botones.
  Burbujas de chat, tarjetas y barras comparten el mismo margen.

## Legibilidad: el piso de letra

- **Piso de letra: 26 px** sobre el lado corto (1080). Por debajo, el texto no
  se lee en un teléfono. Es el mismo número que usa el motor
  (`LETRA_MIN` en `scripts/medir_animacion.py`), no una cifra aparte.
- **La escala del catálogo** (`ESCALA` en `scripts/render_plan.py`) deja el
  texto real de la pieza en 28 px o más: `titular` 120 · `rotulo` 44 ·
  `dato` 36 · `secundario` 32 · `nota` 28. Un rol = un tamaño en todas las
  escenas. Cuando agregues un texto nuevo, usa la escala; no fijes un número
  suelto.
- **El texto que no cabe se PARTE, no se encoge** (hasta 2 líneas:
  `texto_que_cabe`). Partir conserva el tamaño de la escala y no desborda la
  caja; encogerlo lo deja ilegible. Si aun partido no cabe, entonces sí se
  acorta el copy — y eso lo dice `references/copy.md`.
- **El motor no dibuja texto por debajo de 26 px.** Ni siquiera de tamaño
  fijo: antes el catálogo tenía textos a 24, 22 y 20 px (notificaciones del
  candado, URL del navegador, hablante, fecha, estado), y con tamaño fijo
  no los arreglaba ni el auto-fit ni el copy — esas escenas NO PODÍAN pasar
  la puerta. Ahora todos pasan por la escala (el más pequeño, `nota` = 28), y
  el único por debajo es un **glifo** (el "✓" de verificado, dentro de un
  badge de 18 px): un símbolo no es una letra. La puerta `validate_skill.py`
  lo vigila sobre las 45 escenas en los dos formatos, y
  `scripts/_tests/test_piso_legible.py` lo vigila en el código.
- **El texto de un solo renglón que no cabe se RECORTA, no se encoge**:
  `recorta_para` deja el tamaño de la escala y acorta el texto con "…"
  (una URL, un nombre de archivo). Encoger hasta el piso de auto-fit (18)
  deja letra que el QA rechaza.
- **Lo que vive dentro de un mockup** (el texto de un teléfono, de una app, de
  un post) es parte de la imagen, no de la tipografía del video: se dibuja en
  una capa propia y el QA no lo mide. Aun así **tampoco baja del piso**: la
  escala de la interfaz es su mínimo, no su techo (el cuerpo de una
  notificación del candado va a 28 px, la URL del navegador también).
- **Se mide en reposo.** Un elemento que entra con resorte pasa por muchos
  tamaños (un botón que crece de 0 a 40 px dibuja su texto a 21 px a mitad de
  camino): eso es la animación, no la tipografía. El valor que cuenta es el
  tamaño con el que el texto **se queda**. La medición lo toma como la
  mediana ponderada por frames de cada texto.
- **Encoger tiene un límite.** Si una escena no cabe en la zona segura, el
  motor la escala (hasta 0,70 como piso). Un texto que hubo que encogerse es
  un texto que quedó pequeño: acorta el copy en vez de dejar que el motor lo
  encoja. La puerta de entrega falla si la escala toca el piso, porque el
  texto entonces sale debajo de la UI de la plataforma.
- **Medir, no estimar**: `python scripts/medir_animacion.py --plan plan.json`
  devuelve la letra real, la escala de la zona segura y los solapes. La
  puerta de entrega (`scripts/qa_entrega.py`) corre esa misma medición, así
  que el gate y la rúbrica de premios no pueden discrepar.

## Coherencia visual

- **Un componente = un estilo** en todo el video. Una tarjeta no cambia de
  blanco a oscuro a mitad de escena; un icono no cambia de radio.
- **Un solo botón CTA en toda la pieza** (`boton_halo`): píldora con marco
  blanco fino y halo que late. Antes cada escena se dibujaba el suyo —
  cuatro botones distintos (con halo y marco, solo halo, o nada) en la misma
  pieza. Si necesitas otro estado (el "Pagado" de un comprobante), es un
  estado **del mismo** botón, no otro botón.
- **Una sola retícula**: el rótulo de la escena cae en `y = H*0.20` en las
  45 escenas y mide lo que dice la escala (`rotulo`, 44 px). Un rótulo que
  salta de altura entre escenas rompe el ritmo, aunque no se pise nada.
- **Un solo fondo**: un mundo continuo para todo el video (semilla fija,
  viñeta común). El ambiente no salta de lugar en cada corte.
- **Fondo**: prohibidas rejillas/líneas decorativas (en video se ven mucho más
  fuertes que en un frame estático; el brand pack puede habilitarlas si la
  marca las pide). Profundidad con blobs a la deriva + viñeta.
- **Paleta**: un solo color de acento (el del brand pack, o el elegido en modo
  libre del catálogo de `references/paleta.md`). El acento comunica, no decora.
  Sin marca, la paleta se **elige** según el brief; no se hereda de ninguna
  marca.

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

---

→ Canónico: `references/animacion.md` · Dominio: movimiento · Vecinos: `references/fluidez.md`, `references/copy.md`, `references/plan-video.md`
