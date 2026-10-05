# Patrones de escena validados en internet

EditorIA integra un **catálogo unificado de escenas** construido a partir de
bibliotecas externas **MIT-licensed, validadas en producción** y revisadas
para coherencia con el principio marca-blanca. Esta referencia documenta
el origen de cada escena del catálogo extendido, cómo se compone desde
las primitivas DRY, y cómo el modelo puede **integrar nuevas escenas** de
forma coherente.

## Fuentes validadas (MIT)

### 1. [lifeprompt-team/remotion-scenes](https://github.com/lifeprompt-team/remotion-scenes) — 201 escenas

Catálogo abierto con 201 escenas Remotion en 16 categorías (TextAnimations,
ShapeAnimations, TransitionAnimations, **DataAnimations**, EffectAnimations,
UIAnimations, LogoAnimations, BackgroundAnimations, ParticleAnimations,
CinematicAnimations, LayoutAnimations, DemoAnimations, **ListAnimations**,
**ThemeAnimations**, RollerAnimations, LiquidAnimations). Cada componente
es un `.tsx` con sus props documentadas; cada categoría trae un `index.tsx`
con un `Showcase` que encadena las escenas a modo de demo.

### 2. [ali-abassi/remotion-templates](https://github.com/ali-abassi/remotion-templates) — 1.000 templates

Colección curada de 1.000 templates Remotion en 100 familias reutilizables
(typed, prop defaults validados, agent recipes). Pensada explícitamente
para servir a agentes de IA: el catálogo expone `agent-catalog.json` con
rol visual, inputs, timing, composición, restricciones y ejemplos de uso.

### 3. [reactvideoeditor/remotion-templates](https://github.com/reactvideoeditor/remotion-templates) — 81 templates

81 templates Remotion auto-contenidos en 9 categorías (Charts & Data, Text,
Content Animation, Background, Cinematic, Transition, Logo & Branding,
Intro & Outro, Image & Media). MIT-licensed. El README trae descripciones
claras por template — ideal para que el modelo encuentre patrones
específicos por intención (typewriter, ken burns, progress steps, etc.).

### 4. [iart-ai/motion-skills](https://github.com/iart-ai/motion-skills) — 54 skills en 17 packs

Colección de skills de motion graphics para agentes (Remotion, canvas, web),
cada una con su bucle "renderizar → mirar → verificar". Se analizó línea por
línea, skill por skill (2026-10-05). Casi toda la doctrina ya estaba en
`tecnicas-video.md`; lo que se portó es lo que faltaba de verdad:

| Skill iart | Qué aportó a EditorIA |
|---|---|
| countdown-video | escena `countdown` + primitiva `odometro` |
| promo-video | escena `oferta` (precios calculados, fail-loud) |
| product-demo-video | escena `demo` + primitivas `cursor`/`onda_clic`/`smoothstep` |
| testimonial-video | `quote`: líneas en orden de lectura, énfasis, `estrellas` |
| text-message-animation | `chat`: "escribiendo", auto-scroll, cola, tiempos derivados |
| lower-thirds (×2) | escena `rotulo_inferior` + overlays con alfa (`.mov`/`.webm`) |
| wrapped-video / ad-creative | `render_plan.py --datos`: plantilla × tabla |
| caption-animation | `caption.py --palabras`: karaoke con tiempo real por palabra |
| photo-slideshow | `montaje.py pase` reescrito (movimiento distinto por foto) |
| audiogram | `audio_viz.py --modo audiograma` |
| presentation-video | la narración manda el reloj (`auditar_plan`, `voz_off`) |
| color-motion | encode BT.709 exacto de frames RGB (`_comun.codificar_frames`) |
| accessible-animation, soundtrack | `auto_qa.py`: fotosensible y sobresalto |
| youtube-intro-outro | zonas de pantalla final (`_delivery.py`, `--end-screen`) |

Lo que NO se portó (y por qué): reduced-motion, GSAP, Lottie, glass y
transiciones de página (web, no video renderizado); Three.js/GLSL/Manim
(otro stack; `remotion.md` y `hyperframes.md` cubren los motores opcionales);
precios de freelance (cotizar no es editar); `layout-check` por `claim()`
(exigiría instrumentar cada dibujo del renderer).

## Cómo se mapean a EditorIA (DRY)

Cada escena del catálogo extendido se compone a partir de **primitivas DRY**
que viven en `scripts/render_plan.py`:

| Primitiva | Uso | Escenas que la llaman |
|---|---|---|
| `barra_h(d, x, y, ancho, alto, fraccion, color, radio)` | barra horizontal rellenable | `bars`, `ranking`, `leads.puntaje` |
| `cuenta_up(desde, hasta, t, t0, dur, fmt)` | número animado `desde`→`hasta` (acepta strings) | `bars`, `gauge`, `ranking`, `stats`, `remate` |
| `arco(d, cx, cy, r, desde, hasta, color, grosor)` | arco de círculo | `gauge`, `pie` (futuro) |
| `particulas(d, t, t0, cx, cy, n, color, semilla)` | confeti determinista (seeded) | `confetti` |
| `cuadricula(x0, y0, ancho, alto, cols, n)` | layout en grilla | `stats`, `lineup` (futuro) |
| `linewrap(text, fnt, max_width, tmp)` | word-wrap con medida real | `quote`, `versus`, `stats` |
| `text_reveal(d, text, fnt, x, y, t, t0, dur, color)` | typewriter (carácter a carácter) | `typewriter` |
| `kenburns(img, t, t0, dur, zoom_from, zoom_to, pan_x, pan_y)` | zoom + paneo progresivo (afín sub-píxel: no tiembla) | `kenburns`, `demo` |
| `smoothstep(p)` | curva del cursor: arranca y frena como una mano | `demo` |
| `cursor(d, x, y, escala)` · `onda_clic(d, x, y, t, t_clic)` | puntero + onda del clic (devuelve el pulso) | `pago`, `demo` |
| `odometro(layer, texto, texto_prev, rodar, cx, cy, fnt, color)` | dígitos tabulares que ruedan al cambiar | `countdown` |
| `estrellas(layer, cx, cy, valor, maximo, k)` | puntaje con relleno fraccional exacto | `quote` |
| `imagen_ajustada(ruta, ancho, alto)` | carga + cubrir + recorte, cacheado por proceso | `kenburns`, `demo` |

**Regla de oro**: al añadir una escena nueva, **componer** con estas primitivas.
NO duplicar lógica de animación, NO hardcodear color (usar `ACENTO`, que el
brand pack sobreescribe), NO meter `random` en runtime (la semilla debe ser
determinista para que el render sea reproducible).

## Mapeo escena → fuente externa

| Escena EditorIA | Fuente | Categoría externa |
|---|---|---|
| `bars` | `DataBarChart.tsx` | DataAnimations (lifeprompt) |
| `gauge` | `DataGauge.tsx` | DataAnimations (lifeprompt) |
| `ranking` | `DataRanking.tsx` | DataAnimations (lifeprompt) |
| `stats` | `DataStatsCards.tsx` | DataAnimations (lifeprompt) |
| `timeline` | `DataTimeline.tsx` | DataAnimations (lifeprompt) |
| `quote` | `ThemeAnimations` › quote | ThemeAnimations (lifeprompt) |
| `versus` | `ListAnimations` › comparison | ListAnimations (lifeprompt) |
| `confetti` | `ParticleAnimations` › confetti | ParticleAnimations (lifeprompt) |
| `typewriter` | `typewriter-subtitle.tsx` | Text (reactvideoeditor) |
| `kenburns` | `ken-burns.tsx` | Cinematic (reactvideoeditor) |
| `pasos` | `progress-steps.tsx` | Content Animation (reactvideoeditor) |
| `countdown` | countdown-video | tiktok-video-skills (iart) |
| `oferta` | promo-video | ecommerce-video-skills (iart) |
| `demo` | product-demo-video | ecommerce-video-skills (iart) |
| `rotulo_inferior` | lower-thirds | lower-thirds-skills (iart) |

## Cómo portar una escena nueva (procedimiento)

Cuando el modelo (o el usuario) quiera añadir una escena del catálogo
externo que aún no está en EditorIA:

1. **Localizar el componente** en el repo externo (ej. `DataPieChart.tsx`):
   `curl -sL https://raw.githubusercontent.com/lifeprompt-team/remotion-scenes/main/src/scenes/DataAnimations/DataPieChart.tsx | head -50`
2. **Identificar las primitivas** que necesitaría en PIL/ffmpeg (no en React):
   círculos, arcos, paths, blits, blurs, transformaciones.
3. **Buscar la primitiva DRY** correspondiente en `render_plan.py`. Si no
   existe, añadirla junto a las otras (con un test rápido en
   `validate_skill.py` para que forme parte del catálogo).
4. **Escribir la escena** como función `(ctx, e, t) -> Image` siguiendo el
   patrón de las existentes (ver `sc_bars`, `sc_gauge`).
5. **Defensive access**: usar `e.get("campo", default)` en TODO campo nuevo.
   La razon: el smoke test de `validate_skill.py` pasa un `e` con defaults
   genericos; cualquier `e["campo_obligatorio"]` rompe el catálogo.
6. **Añadir defaults al smoke test** de `validate_skill.py` para que la nueva
   escena se renderice sin errores con los defaults genericos.
7. **Actualizar `references/escenas.md`** con el spec completo (`params` +
   `at` esperado) — el formato canonico esta en la seccion 1-13.
8. **Verificar**: `python3 scripts/validate_skill.py` debe terminar en
   `SKILL VALIDO` con el contador de escenas actualizado.

## Ejemplo: portar `pie` desde `DataPieChart`

Si se quiere añadir `pie` (gráfico circular de porciones):

```python
# 1) ¿Hay primitiva? Sí, `arco` ya existe. Falta `wedge` (porcion cerrada).
# 2) Añadirla cerca de las otras primitivas DRY:
def wedge(d, cx, cy, radio, desde_deg, hasta_deg, color):
    """Porción circular rellena entre `desde_deg` y `hasta_deg`."""
    d.pieslice([cx - radio, cy - radio, cx + radio, cy + radio],
               start=desde_deg, end=hasta_deg, fill=color)
# 3) La escena, siguiendo el patron de sc_bars:
def sc_pie(ctx, e, t):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    at = e["at"]
    rotulo(ctx, layer, t, e.get("titulo", ""), at.get("rotulo", e["from"]), y=H*0.18)
    porciones = e.get("porciones", [])
    total = sum(p.get("valor", 0) for p in porciones) or 1
    cx, cy, r = W / 2, H * 0.55, W * 0.28
    angulo = 0
    for p in porciones:
        t_in = at.get("porcion", e["from"] + 0.3)
        k = spring(t, t_in, 110, 14)
        if k <= 0:
            continue
        fraccion = p.get("valor", 0) / total
        angulo_fin = angulo + 360 * fraccion
        col = p.get("color") or ACENTO
        wedge(d, cx, cy, r, angulo, angulo_fin, (col[0], col[1], col[2], int(255 * k)))
        angulo = angulo_fin
    return capa_salida(layer, t, e["to"])
# 4) Registrar en SCENES={...}
# 5) Añadir defaults al smoke test: "porciones": [{"valor": 70}, {"valor": 30}]
# 6) Actualizar referencias/escenas.md con el spec
```

## Coherencia con la marca-blanca

- **El color SIEMPRE** viene de `ACENTO` (slot) o de `p.get("color")` (override
  por item). Nunca quemar `(193, 27, 5)` ni cualquier otro RGB específico.
- **El idioma de transición** lo fija el brand pack o el tono de la pieza
  (`references/brand-packs.md`).
- **Toda cifra** de un estudio lleva su `fuente` en pantalla (regla de
  `references/principios.md`).
- **Sin red**: las primitivas no llaman a APIs externas; las escenas externas
  (Remotion) se documentan como recetas para cuando el usuario ya trabaja en
  React/Node (ver `references/remotion.md`).

**Trampa de PIL**: `ImageDraw` con alfa < 255 reemplaza píxeles, no mezcla
(ver `reglas-tecnicas.md`, "ImageDraw con alfa reemplaza pixeles").

## Resumen ejecutivo

- 8 escenas del catálogo extendido vienen de `lifeprompt-team/remotion-scenes` (MIT).
- 3 escenas de la ronda 2 vienen de `reactvideoeditor/remotion-templates` (MIT, 81 templates).
- 4 escenas de la ronda 3 (+ mejoras a `chat` y `quote`) vienen de `iart-ai/motion-skills` (MIT).
- Estan implementadas en `render_plan.py` (PIL/ffmpeg, sin Node).
- Compuestas con 14 primitivas DRY (no hay logica de animacion duplicada).
- Defensivas: el smoke test pasa con defaults genericos.
- Marca-blanca: el color sale del brand pack o del `ACENTO` neutro.
- Reproducibles: las particulas usan semilla determinista (no `random()` en runtime).
- **El modelo puede agregar mas**: el procedimiento de esta guia + las primitivas
  DRY permiten portar cualquier escena de las fuentes listadas en ~30 lineas.