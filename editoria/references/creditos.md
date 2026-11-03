# Créditos de terceros

EditorIA es de Jaime Andrés Restrepo (DragonJAR), con licencia MIT. Esta
referencia lista el material de terceros que la skill **estudió, adaptó o
cita**, con su licencia y lo que se tomó. Regla de la casa: de las fuentes se
toman **técnicas, reglas y números**, no se copian sus demos, sus medios ni
sus prompts enteros; cuando una línea de código se adapta, conserva el aviso
de su licencia.

## Repositorios estudiados en la ronda 1.11

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

Este archivo es el ÚNICO sitio donde se nombran estos repositorios; el resto
de la skill los cita como "ver `references/creditos.md`".

| fuente | licencia | qué se tomó | dónde vive en la skill |
|---|---|---|---|
| [claude-video-effects](https://github.com/Vibha-Ramprakash/claude-video-effects) (Vibha Ramprakash) | MIT | inventario de 45 overlays talking-head con face-track; se clona en `/tmp` cuando se usa, no se vendoriza | `scripts/data/efectos_talking_head.json`, `references/efectos-talking-head.md` |
| [synced-captions](https://github.com/vishalmotionwork-lang/claude-code-windows-setup) | según el repo | solo el heurístico de cortes de caption frase-conscientes | `scripts/ffmpeg_tools/caption.py` |
| [PDoomVideo](https://github.com/JohnHeibel/PDoomVideo) (John Heibel) | declara ISC en `package.json`, sin LICENSE | ideas de pincel y glow para el motor canvas (sin código copiado) | `references/canvas.md` |

Atribución CC BY 4.0 (awesome-claude-5-5-videos): material adaptado y resumido
en español; se indicó qué se cambió; licencia en
https://creativecommons.org/licenses/by/4.0/.

Los avisos MIT completos están en los `LICENSE` de cada repositorio enlazado.
Las fuentes tipográficas, músicas y vídeos de esos repositorios no se
incluyen en la skill.

---

→ Canónico: `references/instalacion.md` · Dominio: operacion · Vecinos: `references/auto-mejora.md`, `references/canvas.md`, `references/estilos-codigo.md`
