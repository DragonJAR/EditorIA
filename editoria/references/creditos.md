# Créditos de terceros

EditorIA es de Jaime Andrés Restrepo (DragonJAR), con licencia MIT. Este
archivo lista el material de terceros que la skill **estudió, adaptó o
cita**, con su licencia y lo que se tomó.

Regla de la casa: de las fuentes se toman **técnicas, reglas y números**, no
se copian sus demos, sus medios ni sus prompts enteros; cuando una línea de
código se adapta, conserva el aviso de su licencia.

Solo se listan aquí las fuentes de material que **vive hoy en esta skill**.

## Fuentes del material adaptado

| fuente | licencia | qué se adaptó | dónde vive en la skill |
|---|---|---|---|
| [pdoom-video](https://github.com/mexicat/pdoom-video) (Copyright 2026 Giacomo Magnanini) | MIT (código). La canción, la letra y las fuentes conservan sus propias licencias y **no** se usaron | muestreo adaptativo del obturador; `frameIdx` constante en el obturador; pulsos que decaen desde onsets; reglas del karaoke por palabra; alineación de letra cantada con voz separada y anclas | `render_plan.py --blur auto`, `assets/js/tiempo.mjs`, `references/tiempo-html.md`, `references/formatos.md` |
| [ClaudeAnimationBase](https://github.com/JohnHeibel/ClaudeAnimationBase) (Copyright 2026 John Heibel) | MIT | `ring`, `keys`, sostener dibujos "a doses", la disciplina de lecturas y transiciones | `assets/js/tiempo.mjs`; ya estaba citada en `references/canvas.md` |
| [lemo-opuscar](https://github.com/lemomo-ai/lemo-opuscar) (Copyright 2026 LemoLab) | MIT | el método de dirección: referente, tres estructuras candidatas, momento nativo, silencios medidos, sonido como transición, "que no se parezca a la muestra", hoja de hechos, cambiar un estilo sin romperlo, créditos del proyecto | `references/metodo-direccion.md`, `scripts/medir_silencios.py`, `scripts/proyecto.py` |
| [mg-styles-15](https://github.com/Vincentwei1021/mg-styles-15) (Copyright 2026 Vincentwei1021) | MIT | los 15 estilos (ya integrados antes) | `references/estilos-codigo.md`, `references/prompt-motion-graphics.md` |
| [awesome-opus5-5-videos](https://github.com/yihui-dev/awesome-opus5-5-videos) (Copyright 2026 yihui-dev) | MIT (la colección); cada prompt pertenece a su autor | patrones medidos sobre 703 prompts públicos (resorte crítico, aterrizar antes del beat, transiciones por objeto, lista de prohibidos) | `references/prompt-motion-graphics.md` (Familia 8) |
| [awesome-claude-5-5-videos](https://github.com/athemeroy/awesome-claude-5-5-videos) | CC BY 4.0 | las tres puertas de aceptación y la prueba de determinismo por orden de salto; el criterio de pedir el efecto por su prueba de aceptación | `references/tiempo-html.md`, `references/prompt-motion-graphics.md` |
| [opus-video-prompts](https://github.com/joeseesun/opus-video-prompts) | sin fichero LICENSE; el repo declara que cada prompt es de su autor | solo **estructura e ideas parafraseadas** (prompt por bloques, trampas de CSS 3D, sub-frames con tmix); nada verbatim | `references/prompt-motion-graphics.md`, `references/tiempo-html.md` |

## Otras fuentes citadas por la skill

Este archivo es el **único** sitio donde se nombran estos repositorios; el
resto de la skill habla de técnicas, no de quién las publicó. Los patrones de
`references/prompt-motion-graphics.md` y `references/estilos-codigo.md`
mantienen la atribución de su fuente original (la regla 13 de
`references/mapa.md`).

---

→ Canónico: `references/instalacion.md` · Dominio: operacion · Vecinos: `references/auto-mejora.md`, `references/canvas.md`, `references/estilos-codigo.md`
