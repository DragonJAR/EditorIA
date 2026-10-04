# Prompts de motion graphics (biblioteca verbatim)

Patrones destilados de decenas de piezas virales hechas con Opus 5.5 +
HyperFrames/Remotion (skillry.dev/ai-videos/opus-5-5, extracción 2026-10-04).
Son plantillas verbatim listas para copiar: sustituye las {{VARIABLES}}
con el contenido real del proyecto. El copy real manda; el prompt es el
punto de partida, no el entregable (el loop de QA sigue siendo obligatorio).

## Familia 1 — Showreel viral one-shot (el prompt que lo empezó todo)

Verbatim (variantes de @jesscaroline7, @thayto_dev, @elliot_garreffa):

```
make a dynamic 15-second motion graphics video that shows what an
incredible motion designer you are, like it's your showreel for a résumé.
go all out.
```

El truco que lo hace funcionar: **referenciar la carpeta del proyecto**.
Lo que había en ella marcó la diferencia (@jesscaroline7, motion reel de
una app real, Opus 5.5 effort max):

- app real: el modelo navegó el simulador de iOS y grabó las pantallas
- datos reales: escribió las queries, el humano las corrió en la BD real
- 3D: dioramas generados con IA y animados por el modelo
- música generada + SFX de librería

Variantes que funcionan:

- Con contexto explícito: `...go all out. use todo o contexto do projeto`
  (@danilowm, vía skill hyperframes en terminal).
- Como hero asset: `make a dynamic 15-second motion graphics video that
  shows what an incredible motion designer you are, and can be the hero
  asset for the course landing page` (@TheViableEdge, eligió Remotion
  teniendo HyperFrames instalado).

Cuándo usarlo: arranque rápido, prueba de concepto, demo interna.
Nunca como entregable final sin pasar por `references/auto-qa.md`.

## Familia 2 — Film de lanzamiento 15 s con variables (ik_builds, verbatim)

El caso: le cotizaron USD 3000 por el video; Opus 5.5 (medium) lo hizo de
una sola pasada con este prompt. Verbatim:

```
Create a 15s motion-graphics film explaining {{PRODUCT}}. HyperFrames + GSAP,
no voiceover, no footage.
Style: paper-light canvas, marker notes that draw on, real physics, huge
kinetic type, hard light/dark switches, a new idea every 1.5–2 s, a sound
on every hit.

COPY: read {{POSITIONING_DOCS}} first. {{ONE_LINER}} For {{AUDIENCE}}.
{{WHAT_IT_DOES}} Name what the product learns, never the abstraction.

RULES
- No chrome (scrubber, timecode, fps, headers). No animator jargon on screen
  ("squash", "stagger", "easing"...). Every word speaks to the buyer.
- No invented results: no %, multipliers, customer names or figures.
- Never use: {{BANNED_WORDS}}.
- Logo: real mark {{LOGO_FILE}} + "{{PRODUCT}}" in {{WORDMARK_FONT}}; never
  a boxed logo file.

CRAFT
- Colours {{COLOR_CANVAS}} / {{COLOR_INK}} / {{COLOR_ACCENT_1}} /
  {{COLOR_ACCENT_2}}; notes in the accents; dark mode = charcoal matching
  the palette.
- Fonts {{BRAND_FONTS}}; Anton for kinetic type; Caveat handwriting via
  stroke-dashoffset.
- Real easing, squash/stretch, stagger, overlap, onion skin, smear,
  follow-through. Check the HyperFrames registry first. Set every from-state
  at t=0 (seek-safe); never cover an exit. One primary move per transition;
  no generic push/slide/rotate-swing.
- Music in sections: drums drop on the dark switch and while the ball is
  airborne, slam back on the type and the logo. SFX: pops, pen scribbles,
  whooshes, logo sub-hit. CC0 or generated only; log sources. Master
  -14 LUFS, -2 dBTP, re-measured after AAC encode.
```

Qué poner en cada variable:

| Variable | Contenido |
|---|---|
| {{PRODUCT}} | nombre del producto, sin adornos |
| {{POSITIONING_DOCS}} | ruta al doc de posicionamiento (el modelo lo lee primero) |
| {{ONE_LINER}} / {{AUDIENCE}} / {{WHAT_IT_DOES}} | copy real, una línea cada uno |
| {{BANNED_WORDS}} | palabras prohibidas del proyecto |
| {{LOGO_FILE}} / {{WORDMARK_FONT}} | marca real, nunca placeholder |
| {{COLOR_*}} / {{BRAND_FONTS}} | del brand pack (`references/brand-packs.md`) |

Nota EditorIA: el template pide -2 dBTP; el canónico del skill es
-1.5 dBTP (`scripts/ffmpeg_tools/_delivery.py`). Lo que importa es la
disciplina: **re-medir después del encode AAC**.

## Familia 3 — Launch SaaS 30 s en Remotion (aschapmann, verbatim)

El caso: video de lanzamiento de RedShip, +1h de Opus 5.5. Verbatim
("save it and try it for your SaaS"):

```
Act as a senior motion designer and build a 30-second launch video for
[product] in Remotion, entirely in code so I can edit and re-render it:
first read my landing page and codebase to pull the real story, copy,
colors, font and logo file (trace the logo to SVG so it stays sharp and
can be animated), then write the video as one story (why the market
matters, why it's painful today, how [product] fixes it, what you get)
in 4 to 5 scenes with one short title each, animate everything like a
premium product film (kinetic typography word by word, spring easing,
smooth camera pushes and pans, depth and glow, elements that build in on
the beat instead of just appearing), keep each scene on screen long enough
to read, add one soft sound effect for every element that appears and
silence otherwise, and end on a memorable animated logo reveal with the
tagline and URL, then render it, check the frames yourself and fix
anything that overlaps, clips or feels rushed before showing me the result.
```

Las tres claves que lo separan del resto:

1. **Real-assets-first**: lee la landing y el codebase para sacar historia,
   copy, colores, fuente y logo reales; traza el logo a SVG.
2. **Un SFX por elemento y silencio si no**: el sonido diseña el ritmo,
   no decora.
3. **Auto-revisión del generador**: "check the frames yourself and fix
   anything that overlaps, clips or feels rushed before showing me the
   result" — el modelo mira sus propios frames antes de entregar
   (ver `references/recetas-ai-video.md`, pipeline de 3 agentes).

## Familia 4 — Talking head agresivo / batch de podcast (stokebuilder, verbatim)

El caso: 50 animaciones de podcast para conceptos difíciles de visualizar
(LegalQuants). Verbatim:

```
Go through the entire [episode] cut and add full-screen animations and
graphics wherever they help. Be aggressive and over-inclusive: 35–50
moments, at least 2 per chapter. The goal is to fill empty talking-head
time, explain ideas, and create visual hooks.

Style. Pick an aesthetic that's genuinely interesting and very, very cool,
built in JavaScript with HyperFrames and assembled in Tesseract.
Inspiration (all JS, no image assets):
[paper, typewriter-tape labels, hand-drawn marks]
[halftone, manga and pixel print, kinetic data type]

Stay inside the LegalQuants brand (read brands/legalquants/): charcoal,
white and black only, Arial, and the supplied lockup top-right, static.
Write a shared style bible and a component kit first, so every animation
looks like the same show.

Moments I definitely want:
[LIST]

Rules
Whenever anything goes full-screen (animation, screen share or still), one
of us is in a corner picture-in-picture, bottom-right, following whoever
is talking.
No punch-ins or zooming on the cameras. Keep each speaker relatively centered.
Copy must be verbatim or faithful to what's said. Never invent facts,
numbers or quotes.
Sync each animation's beats to the spoken words.
Keep each graphic inside one uncut stretch of audio, and leave a few
seconds of faces between graphics.

Process
An Opus 5.5 agent at extra-high effort finds every timestamp where an
animation could fill space and hook the viewer, with a concept for each.
Opus 5.5 at medium effort builds each animation.
Opus 5.5 at extra-high effort judges each one once on brand consistency
with the others, visual interest, relevance to the narrative and creative
judgment.
Only cues the judge considers egregiously bad go back for a fix. No
blanket redo loops.
Assemble the full cut with PiP baked into every full-screen visual, and
give me a folder of the individual animations.
```

Doctrina EditorIA (ya vigente): en resúmenes y piezas con talking head,
mínimo **2 gráficos full-screen por capítulo/sección**. El silencio visual
es el enemigo; cada gráfico debe explicar o enganchar, no decorar.
El pipeline de 3 agentes (finder/builder/judge) está operativizado en
`references/recetas-ai-video.md`.

## Familia 5 — Zero-shot puro código (@henritoivar)

Sin prompt elaborado: video zero-shot donde el modelo usa código puro
para SFX, música y animación (CSS/HTML/JS), **cero assets de imagen o
video**. Útil para explainers detallados donde se necesita control fino
de infografías y salida determinista. Es la prueba de que el "motor" no
es un generador de video: es un programador con criterio de motion
designer.

## Expectativas honestas: costo y tiempo reales

"One-shot" describe el prompt, no el proceso. Datos reales de la colección:

| Caso | Duración pieza | Tiempo / costo |
|---|---|---|
| @jayjohnsonai, motion graphics 15 s | 0:15 | ~5 min, Opus 5.5 effort máximo |
| @thayto_dev, showreel 15 s | 0:15 | 5% del límite de 5 h |
| @Javi_llofriu, video agencia de IA | 0:56 | 20 min, 20% del consumo de 5 h (plan Max) |
| @vince_builds, motion graphics | 0:56 | 8 h 15 min, Opus 5.5 Max |
| @wustep, trailer Notion en Remotion | 0:32 | 2 días, ~90 mensajes, 33 tomas, ~$400 en créditos |

El rango real va de 5 minutos a 2 días según ambición. Presupuesta
iteración; el que promete "una sola toma y listo" vende humo.

## Reglas de copy honesto (de ik_builds, aplican a todas las familias)

- No invented results: ni %, ni multiplicadores, ni nombres de clientes,
  ni cifras inventadas. (En EditorIA: `references/checklist-qa.md`, Base 1.)
- {{BANNED_WORDS}}: cada proyecto define su lista de palabras prohibidas.
- Cada palabra en pantalla le habla al comprador; nada de jerga de
  animador en pantalla.
- Logo: marca real + wordmark en la fuente de marca; nunca un logo
  enmarcado genérico.

## Técnicas que estos prompts exigen (y dónde viven)

| Técnica | Qué es | En la skill |
|---|---|---|
| Draw-on de marcador | Notas que se dibujan solas (stroke-dashoffset) | `references/tecnicas-video.md` (Underline/Marker draw-on) |
| Física real | Inercia, rebote, resortes en el motion | HyperFrames + GSAP (`references/hyperframes.md`); `spring()` en Remotion (`references/remotion.md`) |
| Cambio duro luz/oscuridad | Alternar canvas claro/oscuro como ritmo entre ideas | Cortes editoriales secos (brand packs); úsalo como beat, no como filtro |
| Sonido en cada golpe | Un SFX por beat visual | `references/sonido.md` (el hit cae sobre la palabra exacta); `scripts/sfx.py` |
| Tipografía cinética enorme | Titulares que son el plano | `references/tecnicas-video.md` (timing de reveals) |
| Sin chrome | Nada de UI de reproductor/sistema | Regla de composición: si no es contenido, no se renderiza |
| Contexto real | Carpeta del proyecto, datos y pantallas reales | Doctrina real-assets-first (`references/recetas-ai-video.md`) |
| Seek-safe | Todo from-state fijado en t=0; nada depende de timeouts | `references/hyperframes.md` (timing declarativo); Remotion sin `Math.random()` ni wall clocks |
| Música por secciones | La música cambia con la estructura (drums en el dark switch) | `scripts/musica.py gen`; beat file compartido (`references/recetas-ai-video.md`) |
| Master medido | -14 LUFS, TP según plataforma, re-medir tras AAC | `scripts/ffmpeg_tools/delivery_check.py`; `scripts/medir_mezcla.py` |

## Lo que NO se trae

- Voces/SFX generados sin provenance cuando el proyecto exige derechos
  claros: EditorIA usa ElevenLabs (voz/música) o SFX sintetizados
  deterministas (`references/sonido.md`).
- "Una sola toma y listo": el loop de QA (`auto_qa.py` + mirar el sheet)
  sigue siendo obligatorio. El prompt genera el borrador; el agente lo
  convierte en entregable.
- Promesas de tiempo/costo de la tabla de arriba como garantía: son datos
  de terceros, no un SLA.
