# Técnicas cinematográficas (films de marca)

> Recetas de los films de marca (`scripts/film_marca_v2.py`, y v1 como
> referencia). Funcionan con cualquier brand pack: los valores concretos
> (paleta, logo, ancla, wordmark, lema) salen del pack que se pida.

Recetas reutilizables para piezas premium en 16:9 o 9:16 (`--formato`).
Principio: el logo nunca se
redibuja, rota ni deforma — solo escala uniforme (un logo no cuadrado se
centra en un lienzo cuadrado transparente, no se estira).

**Ejemplo**: `python scripts/film_marca_v2.py --brand brand/mi_marca.json -o film.mp4`
(15 s, 1920×1080, 24 fps): macro del ancla del logo → trazo láser →
match-cuts al beat → cierre asimétrico con wordmark y lema. `--formato 9:16`
(1080×1920) recompone la coreografía: tercio superior, cierre apilado
(logo arriba, texto abajo) dentro de la zona segura de Reels/TikTok/Shorts;
el patrón de mini logos cubre el cuadro en ambos formatos. Sin pack:
`--logo logo.png --nombre "Mi marca" --lema "Frase con *énfasis*"`. Los mp4
no vienen en el paquete (se generan). En `film/` está la música de ejemplo
(`film/musica_demo.mp3`, `film/musica_film.mp3`, `film/musica_film_v2.mp3`).
Nunca redibujar el logo.

## Trazo láser del contorno

1. Tomar el alpha del logo, `FIND_EDGES`, quedarse con ~1100 puntos.
2. Ordenarlos por vecino más cercano greedy (numpy, una sola vez).
3. Dibujar progresivamente en una capa persistente (solo los segmentos nuevos
   por frame), con cabeza brillante + glow.
   - La cabeza del láser va en una capa TRANSITORIA por frame, nunca en la
     persistente (si no, deja un rastro de puntos).
   - Romper segmentos con salto >16px (el greedy-NN salta entre regiones
     desconectadas y dibuja líneas cruzando el interior).
4. El logo aparece en fade mientras el trazo se atenúa ("revelado como unidad").

## Sistemas de brasas

- **Deriva** (apertura): 20-30 partículas subiendo con sway sinusoidal,
  tamaños 2-5px, algunas con blur (profundidad de campo).
- **Órbita** (desarrollo): partículas en órbitas circulares lentas alrededor
  del punto de interés (el keyhole), `x=cx+r·cos(a+t·ω)`.
- **Asentamiento** (cierre): ω→0.15·ω y fade out. Nada se apaga de golpe.

## Match-cut sobre punto fijo

> Excepción del modo film: en piezas cinematográficas con renderer propio
> (ej. film de marca), los dissolves sobre el beat están permitidos. En el
> renderer de planes (`render_plan.py`) el corte duro es el default y
> `dissolve` no está implementado (ver `escenas.md`).

Variaciones del logo (mono blanco, acento plano, outline, patrón de minis)
con el punto de interés (keyhole) clavado en el mismo píxel en cada corte.
Dissolves de 0.25s sobre el beat. El patrón de minis: rejilla centrada en el
punto fijo que vuelve a uno por crossfade.

## Look cinematográfico

- **Push-in**: zoom 1.00→1.06 en toda la pieza con cubic-bezier(0.2,0,0,1),
  centrado en el punto de interés (= centro del frame). OJO: el zoom recorta los
  bordes — el área segura es y < 540+540/z. Diseñar el layout para el zoom final.
- **Halo volumétrico**: radial en el acento a alpha ~90, respirando ±6%.
- **Grano**: `randint(-7,8)` por frame sobre el frame final. Sutil.
- **Fundido a negro**: último 1.2s con `Image.blend`.

## Texto premium

- **Wordmark**: tracking amplio (26px), barrido con máscara izquierda→derecha
  en 0.8s con easing.
- **Tagline bicolor**: dibujar por segmentos `[(texto,color)]` midiendo cada
  palabra con `textlength` para centrar el conjunto.
- **Voz en off**: ver `scripts/voz_off.py`. **Música**: ver `scripts/musica.py`
  (ducking sidechain para que la cadencia respire con la narración).

## Trailer playbook

Para piezas tipo trailer/promo cinematográfica:

**5 spines narrativos** (elegir uno):

| Spine | Motor |
|---|---|
| Mystery | una pregunta sin respuesta hasta el final |
| Transformation | el antes y el después como promesa |
| Threat | lo que está en juego si nada cambia |
| Craft | el proceso, la maestría del hacer |
| Spectacle | la escala visual como protagonista |

**Selección de momentos**: preferir caras, ojos y manos; siluetas fuertes;
rechazar ángulos repetidos y cualquier footage que rompa el tono. Un trailer
no resume — provoca.

**Pacing de trailer**: arrancar contenido (sin setup), escalar en 3 oleadas
con silent stops entre ellas, el momento más grande al ~80%, y salir en el
pico — nunca en la resolución.

## Estilos de cine hechos en código (catálogo externo)

`lemomo-ai/lemo-opuscar` (MIT) es una biblioteca de **59 estilos de cine
renderizados en código** (óleo al thick, acuarela, ukiyo-e, briefing de
satélite, desmontaje de producto, documental de archivo…), con Node y
Three.js, y su propio flujo de dirección.

Lo que aporta aquí es un **vocabulario de LOOKS**: el motor tiene 45 tipos de
escena, que no son estilos de película. Sirve para tres cosas, y ninguna es
duplicar el motor:

1. **Referencia de intención**: elegir el aire de la pieza ("quiero que parezca
   un briefing de satélite") antes de escribir el plan.
2. **Material**: un render de ese estilo entra como overlay con alfa (ver
   `references/3d.md`).
3. **Cocina de técnicas**: su `TECHNIQUE.md` y sus estilos son material de
   estudio para el camino de cine.

Los dos catálogos de estilos hechos en código (el de cine y el de motion design)
viven en `references/estilos-codigo.md`, con sus fuentes declaradas.

**La frontera**: es otro motor (Node + Three.js) con su propio director. No
se integra en el motor de esta skill ni se copia su código; se declara la
fuente y se usa como referencia y como material.

---

→ Canónico: `references/formatos.md` · Dominio: produccion · Vecinos: `references/modos-produccion.md`, `references/brand-packs.md`, `references/tonos.md`
