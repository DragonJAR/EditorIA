# Técnicas cinematográficas (de `scripts/film_marca.py`)

> Caso de estudio con el pack DragonJAR (`brand/dragonjar.json`), no doctrina
> general: las recetas se portan a cualquier marca cambiando el pack; los
> valores concretos (paleta, disolves, keyhole) son de este ejemplo.

Recetas reutilizables para piezas premium 16:9. Principio: el logo nunca se
redibuja, rota ni deforma — solo escala uniforme.

**Ejemplo**: `python scripts/film_marca_v2.py` genera el film de marca del
pack de ejemplo (15 s, 1920×1080, 24 fps) con estas recetas: macro del
keyhole → trazo láser → match-cuts al beat → cierre asimétrico. Los mp4 de
salida no vienen en el paquete (se generan). En `film/` está la música de
ejemplo (`film/musica_demo.mp3`, `film/musica_film.mp3`, `film/musica_film_v2.mp3`). El
isotipo oficial del pack está en `brand/assets/dragonjar-isotipo.png`;
nunca redibujar el logo.

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

Variaciones del logo (mono blanco, rojo plano, outline, patrón de minis)
con el punto de interés (keyhole) clavado en el mismo píxel en cada corte.
Dissolves de 0.25s sobre el beat. El patrón de minis: rejilla centrada en el
punto fijo que vuelve a uno por crossfade.

## Look cinematográfico

- **Push-in**: zoom 1.00→1.06 en toda la pieza con cubic-bezier(0.2,0,0,1),
  centrado en el punto de interés (= centro del frame). OJO: el zoom recorta los
  bordes — el área segura es y < 540+540/z. Diseñar el layout para el zoom final.
- **Halo volumétrico**: radial rojo a alpha ~90, respirando ±6%.
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
