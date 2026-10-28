# Estilos en código (catálogos externos)

Los motores de la skill hacen **escenas**, no **estilos de película**: hay 45 tipos de
escena y ninguno es "óleo al thick" ni "ukiyo-e". Los catálogos externos de estilos
hechos en código cubren ese hueco, y son las dos cosas a la vez: un **vocabulario de
LOOKS** (para elegir el aire de la pieza antes de escribir el plan), **material** (un
render de ese estilo entra como overlay con alfa, ver `references/3d.md`) y **cocina de
técnicas** (las técnicas con números que ya sabes usar en cualquier motor).

Aquí viven los dos catálogos, cada uno con su fuente declarada:

| catálogo | fuente | licencia | qué aporta |
|---|---|---|---|
| Cine | `lemomo-ai/lemo-opuscar` | MIT | 59 estilos de cine renderizados en código (óleo al thick, acuarela, ukiyo-e, briefing de satélite, desmontaje de producto, documental de archivo…), con Node y Three.js y su propio flujo de dirección |
| Motion design | `Vincentwei1021/mg-styles-15` | MIT | 15 películas de motion design de 10 s, una por estilo, y con cada una su receta: rasgos, técnicas con números, prompt y código |

**La frontera**: son otro motor (Node + Three.js; Node + Canvas) con su propio director.
No se integra su código en el motor de esta skill ni se copian sus demos: se declara la
fuente, se usa como referencia y como material, y lo que se copia son los **rasgos y las
técnicas**. Las piezas de mg-styles-15 son de otra escala (10 s exactos, una marca
inventada): el valor está en la firma y en las técnicas, no en la pieza.

## Los 15 estilos de motion design (firma + técnicas + motor)

Cada fila dice **qué hace reconocible el estilo a primera vista** (la firma), **las
técnicas con números** (no un prompt entero) y **qué motor de la skill lo sirve**. El
copy, la marca y el arco salen del brief y del pack; aquí solo vive la firma.

| estilo | su firma | técnicas clave (números) | motor de la skill |
|---|---|---|---|
| **Flat / Vector 2D** | bloques de color plano, personajes geométricos, sin degradados (o muy pocos), aire limpio, paleta de marca saturada, entradas y salidas elásticas | Overshoot `cubic-bezier(0.34,1.56,0.64,1)`; stagger 2–4 frames; squash/stretch ~10 %; un héroe en movimiento a la vez; shape wipe o elemento que se lleva el corte | HyperFrames / Remotion (SVG+GSAP); o plan Python si basta con formas planas |
| **Line Art** | línea fina de un solo trazo, uno o dos colores, mucho espacio negativo, la línea crece de forma continua, el instante línea→plano | `stroke-dashoffset` / Trim Paths; línea 2–4 px constante; ease `cubic-bezier(0.65,0,0.35,1)` en esquinas; cap redondo; fill que nace del mismo path | HyperFrames / SVG |
| **Isometric 2.5D** | proyección isométrica de 30°, sin punto de fuga, escena en miniatura, edificios que crecen, cámara en raíl paralelo | SSR: scaleY 86.6 % → skew ±30° → rotate ∓30°; pendiente 2:1; edificios: base → scaleY → techo +2–3 frames; parallax 1 : 0.8 : 0.6; cámara = traslación de grupo | Plan (`tecnicas-reutilizables.md` iso) o HyperFrames; 3D ortogonal si hace falta |
| **3D Render (C4D/Blender)** | materiales PBR reales, poca profundidad de campo, luz suave de estudio, arrays de clonadores, colisión de Blandings, aspecto de goma blanda | SSS + AO + HDRI; ease de cola larga (80 % del viaje en el 20 % inicial); 24/25 fps; f/1.8-ish; producto como eje | `references/3d.md` (Blender) → overlay alfa; Three.js solo si el brief lo pide |
| **Cel Animation / Line Boil** | la línea hierve de continuo, a dos o tres imágenes por segundo, smear en los arranques, fumo y agua dibujados a mano, textura de papel | On twos a 24 fps (12 efectivos); boil: 3–4 dibujos en ciclo o turbulent displace 2–5 cada 2 frames; smear 150–300 % **un** frame; grain multiply 10–15 % | Canvas (`canvas.md`) o HyperFrames con posterize |
| **Collage / Cutout** | fotos recortadas con contorno blanco, semitono de trama, textura de diario, collage surrealista a escalas dispares, movimiento a fotogramas fijos | Borde blanco 2–4 px; 12 o 6 fps deliberado; jitter ±2 px; capas: papel → mancha → recorte → doodle → grain | HyperFrames + fotos CC0; montaje si el material es real |
| **Liquid Motion** | bordes ondulados en las transiciones, hilos y gotas, fusión metaball, gotas secundarias que siguen, curvas orgánicas (nunca rectas) | Metaball: blur ≥20 px + umbral de alfa; ease `cubic-bezier(0.22,1,0.36,1)`; follow-through de gotas +2–3 frames; squash al aterrizar | HyperFrames / SVG filters; primitiva afín si solo es wipe |
| **Morphing** | el contorno pasa de una forma a otra sin salto, formas intermedias que hacen de puente, el morphing con desplazamiento y rotación, y el aplastamiento del instante | Mismo nº de vértices y first vertex alineado; puente A→círculo/cápsula→B (8–12 frames cada tramo); squash 10–15 % + rotación leve; ease `cubic-bezier(0.7,0,0.3,1)` | HyperFrames (MorphSVG / flubber); Remotion |
| **Geometric Bauhaus** | formas geométricas básicas, paleta limitada (rojo, amarillo, azul, negro), rejilla estricta, rotaciones sobre el centro geométrico, movimiento modular al beat | Desplazamientos = múltiplos de la malla; easeInOutQuad o lineal; un golpe por beat; ejes: centro / vértice / centro de cuadro | HyperFrames / Remotion / p5 en Canvas |
| **Synthwave / Y2K** | brillo neón, rejilla en perspectiva hasta el horizonte, scanlines y separación RGB, letras cromadas, colores ácidos, UI skeuomórfica | Glow interno 4 px + externo 30 px; RGB split 1–2 px; scanline 2 px @10 %; glitch 1–2/s; chrome = gradiente metálico + bevel; tramos a 15 fps a propósito | HyperFrames / Canvas; no confundir con HUD (fila 15) |
| **Aurora & Glassmorphism** | manchas de color grandes desenfocadas y a la deriva, tarjetas de cristal esmerilado, borde de luz de 1 px, paleta de tonos cercanos de bajo contraste, ritmo de respiración lento | 3–5 blobs blur 80–150 px, ciclo 20–40 s; glass: blur 20–40 px + fill blanco 5–10 % + borde 1 px @30 %; ruido 3–5 % anti-banding; solo ease sine/respiración; texto: opacity + 8 px | `tarjeta_cristal` en plan; HyperFrames WebGL si hay lente de refracción |
| **Variety Show (hanazi)** | tipografía redonda o gruesa con contorno múltiple, color saturado con borde blanco y sombra, entrada pop elástica, despliegue con el efecto sonoro, adornos dibujados a mano | Fill + stroke blanco + sombra de color; scale 0→1.15→1 en ~8 frames; stagger 2 frames; aparece 2–3 frames **después** del audio; wiggle leve si permanece | `caption.py` + SFX; Remotion/HyperFrames para decoradores |
| **Sticker Explainer** | fotos convertidas en stickers de contorno blanco grueso, fondo frío, iconos planos y datos exactos, travelling de cámara en lienzo grande, densidad alta con beats | Borde blanco 8–12 px; pan/zoom de cámara con ease largo; charts que crecen; 2–3 colores fríos; una idea visual por frase de VO | Plan (`kenburns`, `stats`, `bars`) + stickers; HyperFrames si el lienzo es HTML |
| **Pixel Art / 8-bit** | grano grande de píxel y bordes duros, paleta limitada (8–32 colores), sprites a 8–12 fps, dithering, filtro CRT de scanlines | `image-rendering: pixelated` / nearest; `steps()` no smooth; walk 6–8 frames, idle 2–4; parallax en enteros de píxel; CRT opcional | Canvas / HyperFrames; nunca escalar con bicubic |
| **Cyberpunk HUD / FUI** | líneas de neón cian y naranja, cajas de bloqueo de objetivo y retícula, radar o barrido circular en bucle, flujo de datos en monoespaciada y efecto máquina de escribir, rejilla hexagonal con resplandor | Stroke-dash draw-on escalonado; radar conic-gradient en loop; dígitos scramble 3–5 frames; lock 1.4→1.0; glow + aberración + scanline | Ya en `estilos.md` (HUD); plan con `callout`/`index` o HyperFrames |

**Cómo se pide un estilo** (firma verificable + beats por segundo, no adjetivos):
`references/prompt-motion-graphics.md`.

## Cómo usarlo (DRY)

1. Elegir **un** estilo de la tabla. Un video, una firma: los lenguajes ya aprendidos
   en producción viven en `references/estilos.md` (style pack distinto, look distinto).
2. Escribir el one-shot con la plantilla de cuatro bloques de
   `references/prompt-motion-graphics.md` (Output, ruta técnica, Creative seed,
   Signature features). Las signature features salen de la fila elegida aquí; no se
   inventan.
3. Mapear la ruta al motor que dice la columna «motor». Si falta (Chrome, Blender,
   Remotion), declararlo en la primera respuesta (`references/capacidades.md`).
4. Tras el render: puerta `references/qa-entrega.md` + rúbrica de 8 ejes. Para films
   one-shot de estilo, una ronda de jurado independiente
   (`references/recetas-ai-video.md`) antes de la rúbrica final.

No sustituye al catálogo de escenas del motor Python: complementa cuando el brief pide
«hazlo flat vector / Bauhaus / pixel / HUD cyberpunk» como look global.

## Reglas que evitan basura

- **Firma > seed.** Cambiar historia, marca y copy está bien; borrar o diluir las
  signature features es fallar el estilo.
- **Un protagonista por plano** sigue vigente (`references/principios.md`), salvo estilos
  que exigen coro geométrico (Bauhaus) o lluvia de stickers (paperclip): ahí el
  «protagonista» es el gesto de cámara o el beat.
- **Paleta del pack manda.** Los hex de ejemplo de un seed son orientación de contraste,
  no identidad. Con brand pack, remapear; en modo libre, elegir de
  `references/paleta.md`.
- **Determinismo.** Cada frame = f(t). Misma regla que el motor Python y los motores
  externos: sin relojes de pared ni transiciones disparadas por estado.
- **No traer el catálogo entero a una pieza.** Quince estilos en un video = cero estilo.
  Si el usuario pide «mezcla», elegir uno dominante y como máximo un acento técnico de
  otro (por ejemplo flat + un morph de transición).

## Qué no se integra de las fuentes (a propósito)

- Demos HTML, MP4, texturas, HDRI y samples de instrumentos: peso y marcas inventadas;
  la skill ya tiene motores, SFX (`scripts/sfx.py`) y música (`scripts/musica.py`).
- La biblioteca de audio completa del catálogo de motion design: se solapa con el stack
  de audio de la skill; se adopta el patrón de cue sheet compartido picture/sound, no
  el paquete.
- Showcase web y prompts bilingües verbatim: la skill ya tiene
  `references/prompt-motion-graphics.md` e i18n propio.
- La rúbrica 1–10 de la fuente: no sustituye los 8 ejes de
  `references/rubrica-premios.md`; solo alimenta la pasada de jurado.

---

→ Canónico: `references/estilos-codigo.md` · Dominio: estructura · Vecinos: `references/estilos.md`, `references/canvas.md`, `references/prompt-motion-graphics.md`
