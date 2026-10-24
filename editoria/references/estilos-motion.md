# Catálogo de estilos MG (firma reconocible)

Quince lenguajes de motion graphics canónicos. Cada entrada fija **qué
hace reconocible el estilo a primera vista** y **técnicas con números**,
no un prompt entero ni una demo. El copy, la marca y el arco salen del
brief y del brand pack; aquí solo vive la firma.

Origen destilado: catálogo público de quince films de 10 s hechos en
código (SVG / Canvas / WebGL / Three.js / Blender). Se adoptan firmas y
rutas técnicas; no se importa el repo, ni demos, ni samples de audio.

## Cómo usarlo (DRY)

1. Elegir **un** estilo de la tabla. Un video, una firma (`estilos.md`:
   style pack distinto → look distinto).
2. Escribir el one-shot con la plantilla de cuatro bloques en
   `references/prompt-motion-graphics.md` (Familia 7): Output, ruta
   técnica, Creative seed, Signature features. Las signature features
   salen de la fila elegida aquí; no se inventan.
3. Mapear la ruta al motor de EditorIA (columna «Motor»). Si falta
   (Chrome, Blender, Remotion), declararlo en la primera respuesta
   (`capacidades.md`).
4. Tras el render: puerta `qa-entrega.md` + rúbrica de 8 ejes. Para
   films one-shot de estilo, una ronda de jurado independiente
   (`recetas-ai-video.md` §7) antes de la rúbrica final.

No sustituye `estilos.md` (lenguajes ya aprendidos en producción) ni el
catálogo de escenas del motor Python. Complementa cuando el brief pide
«hazlo flat vector / Bauhaus / pixel / HUD cyberpunk» como look global.

## Los 15 estilos

| # | Estilo | Firma (debe leerse al instante) | Técnicas clave (números) | Motor EditorIA |
|---|---|---|---|---|
| 1 | **Flat / Vector 2D** | Bloques planos saturados, personajes geométricos, casi sin gradientes, elasticidad | Overshoot `cubic-bezier(0.34,1.56,0.64,1)`; stagger 2–4 frames; squash/stretch ~10 %; un héroe en movimiento a la vez; shape wipe o elemento que se lleva el corte | HyperFrames / Remotion (SVG+GSAP); o plan Python si basta con formas planas |
| 2 | **Line art** | Trazo continuo de grosor fijo que se dibuja y se convierte en el siguiente gráfico | `stroke-dashoffset` / Trim Paths; línea 2–4 px constante; ease `cubic-bezier(0.65,0,0.35,1)` en esquinas; cap redondo; fill que nace del mismo path | HyperFrames / SVG |
| 3 | **Isométrico 2.5D** | Proyección 30°, sin punto de fuga, ciudad/oficina en miniatura que crece | SSR: scaleY 86.6 % → skew ±30° → rotate ∓30°; pendiente 2:1; edificios: base → scaleY → techo +2–3 frames; parallax 1 : 0.8 : 0.6; cámara = traslación de grupo | Plan (`tecnicas-reutilizables.md` iso) o HyperFrames; 3D ortogonal si hace falta |
| 4 | **3D render (soft product)** | Material PBR, DOF suave, cloner, paleta candy | SSS + AO + HDRI; ease de cola larga (80 % del viaje en el 20 % inicial); 24/25 fps; f/1.8-ish; producto como eje | `references/3d.md` (Blender) → overlay alfa; Three.js solo si el brief lo pide |
| 5 | **Cel / line boil** | Línea que «respira», onionskin, smear, papel | On twos a 24 fps (12 efectivos); boil: 3–4 dibujos en ciclo o turbulent displace 2–5 cada 2 frames; smear 150–300 % **un** frame; grain multiply 10–15 % | Canvas (`canvas.md`) o HyperFrames con posterize |
| 6 | **Collage / cut-out** | Fotos recortadas con borde blanco, halftone, proporciones rotas, stop-motion | Borde blanco 2–4 px; 12 o 6 fps deliberado; jitter ±2 px; capas: papel → mancha → recorte → doodle → grain | HyperFrames + fotos CC0; montaje si el material es real |
| 7 | **Liquid motion** | Bordes ondulados, metaballs, hilos que se rompen y rebotan | Metaball: blur ≥20 px + umbral de alfa; ease `cubic-bezier(0.22,1,0.36,1)`; follow-through de gotas +2–3 frames; squash al aterrizar | HyperFrames / SVG filters; primitiva afín si solo es wipe |
| 8 | **Shape morph** | Un contorno se convierte en otro sin salto | Mismo nº de vértices y first vertex alineado; puente A→círculo/cápsula→B (8–12 frames cada tramo); squash 10–15 % + rotación leve; ease `cubic-bezier(0.7,0,0.3,1)` | HyperFrames (MorphSVG / flubber); Remotion |
| 9 | **Bauhaus geométrico** | Círculo/triángulo/rectángulo en rejilla, RGB+negro, sin overshoot | Desplazamientos = múltiplos de la malla; easeInOutQuad o lineal; un golpe por beat; ejes: centro / vértice / centro de cuadro | HyperFrames / Remotion / p5 en Canvas |
| 10 | **Synthwave / VHS / Y2K** | Grid en perspectiva, sol, neón, scanlines, chrome | Glow interno 4 px + externo 30 px; RGB split 1–2 px; scanline 2 px @10 %; glitch 1–2/s; chrome = gradiente metálico + bevel; tramos a 15 fps a propósito | HyperFrames / Canvas; no confundir con HUD (fila 15) |
| 11 | **Aurora + glass** | Manchas gaussianas lentas + tarjetas frosted | 3–5 blobs blur 80–150 px, ciclo 20–40 s; glass: blur 20–40 px + fill blanco 5–10 % + borde 1 px @30 %; ruido 3–5 % anti-banding; solo ease sine/respiración; texto: opacity + 8 px | `tarjeta_cristal` en plan; HyperFrames WebGL si hay lente de refracción |
| 12 | **Variety captions (hanazi)** | Tipografía gruesa multi-borde que hace pop con el gag | Fill + stroke blanco + sombra de color; scale 0→1.15→1 en ~8 frames; stagger 2 frames; aparece 2–3 frames **después** del audio; wiggle leve si permanece | `caption.py` + SFX; Remotion/HyperFrames para decoradores |
| 13 | **Sticker explainer (paperclip)** | Fotos-sticker + iconos flat + charts en lienzo enorme con cámara | Borde blanco 8–12 px; pan/zoom de cámara con ease largo; charts que crecen; 2–3 colores fríos; una idea visual por frase de VO | Plan (`kenburns`, `stats`, `bars`) + stickers; HyperFrames si el lienzo es HTML |
| 14 | **Pixel art** | Píxeles duros, paleta 8–32, sprites a 8–12 fps | `image-rendering: pixelated` / nearest; `steps()` no smooth; walk 6–8 frames, idle 2–4; parallax en enteros de píxel; CRT opcional | Canvas / HyperFrames; nunca escalar con bicubic |
| 15 | **Cyberpunk HUD / FUI** | Wireframe neón, brackets de lock, radar, mono data | Stroke-dash draw-on escalonado; radar conic-gradient en loop; dígitos scramble 3–5 frames; lock 1.4→1.0; glow + aberración + scanline | Ya en `estilos.md` (HUD); plan con `callout`/`index` o HyperFrames |

## Reglas que evitan basura

- **Firma > seed.** Cambiar historia, marca y copy está bien; borrar o
  diluir las signature features es fallar el estilo.
- **Un protagonista por plano** sigue vigente (`principios.md`), salvo
  estilos que exigen coro geométrico (Bauhaus) o lluvia de stickers
  (paperclip): ahí el «protagonista» es el gesto de cámara o el beat.
- **Paleta del pack manda.** Los hex de ejemplo de un seed son
  orientación de contraste, no identidad. Con brand pack, remapear; en
  modo libre, elegir de `paleta.md`.
- **Determinismo.** Cada frame = f(t). Misma regla que Canvas/HyperFrames:
  sin relojes de pared ni CSS transitions disparadas por estado.
- **No traer el catálogo entero a una pieza.** Quince estilos en un
  video = cero estilo. Si el usuario pide «mezcla», elegir uno dominante
  y como máximo un acento técnico de otro (p. ej. flat + un morph de
  transición).

## Qué no se integra de la fuente (a propósito)

- Demos HTML, MP4, texturas, HDRI y samples de instrumentos: peso y
  marcas inventadas; EditorIA ya tiene motores, SFX (`sfx.py`) y música
  (`musica.py`).
- Biblioteca `mgaudio` completa: solapa con el stack de audio de la
  skill; adoptar patrones de cue sheet compartido picture/sound, no el
  paquete.
- Showcase web y prompts bilingües verbatim: la skill ya tiene
  `prompt-motion-graphics.md` y i18n propio.
- Rúbrica 1–10 de la fuente: no sustituye los 8 ejes de
  `rubrica-premios.md`; solo alimenta la pasada de jurado en
  `recetas-ai-video.md` §7.

---

→ Canónico: `references/estilos.md` · Dominio: estructura · Vecinos: `references/prompt-motion-graphics.md`, `references/recetas-ai-video.md`, `references/direccion-de-arte.md`
