# RSI (Recursive Self-Improvement) — EditorIA v1.6.0

## Alcance (scope)

- **Proyecto**: [EditorIA](file:///Users/jaimearestrepo/Proyectos/EditorIA) — skill de edición de video con IA (30 escenas, 46 scripts Python incl. tests, 45 referencias, marca-blanca con pack DragonJAR de ejemplo).
- **Tecnologías**: Python 3.9+, PIL/Pillow, ffmpeg, NumPy, ElevenLabs API; opcional Remotion/Node, HyperFrames.
- **Tamaño**: ~109 archivos tracked en git (rama `main`); `SKILL/SKILL.md` ~260 líneas; 45 references; 25 scripts raíz + 19 en `ffmpeg_tools/` + 2 suites en `scripts/_tests/`.
- **Restricciones respetadas**: se preserva todo trabajo preexistente, la arquitectura marca-blanca, el contrato CLI de los scripts, el esquema de `plan.json` y `shorts-plan.json`, y el catálogo de primitivas DRY.

## Entorno (env) y limitaciones de evaluación

- **OS**: macOS (Darwin, Apple Silicon)
- **Python en sandbox**: Python 3.14.8 (`/opt/homebrew/bin/python3`) y Python 3.9.6 (`/usr/bin/python3`)
- **FFmpeg / FFprobe**: 9.0.2 (`/opt/homebrew/bin/ffmpeg`)
- **Node / npx**: v26.10.0 (`/opt/homebrew/bin/node`)
- **Limitación explícita (no evaluado en sandbox)**: en el entorno sandboxed del agente (`$HOME` aislado), `PIL` (Pillow), `numpy` y `pyflakes` no están instalados en el `site-packages` global de `/opt/homebrew/lib/python3.14`. Siguiendo las reglas de rigor del proceso RSI, **el render en píxeles de las escenas (`validate_skill.py` secciones 5/7 y `medir_animacion.py`) y el lint `pyflakes` se declaran explícitamente como NO EVALUADOS en vivo dentro del sandbox** (la línea base previa en host con `PIL`+`numpy` consta en `RSI_LOG_baseline.txt` con 28/28 escenas en verde), mientras que todas las comprobaciones deterministas de AST, compilación, frontmatter YAML, especificación `Skill-for-Claude.txt`, paridad documental ES/EN, arranque CLI (`--help`), sondas de entrada inexistente, subtítulos ASS (`caption.py`) y tests unitarios (`unittest`) se evalúan y verifican al 100% en cada ciclo.

## Proyectos y sitios de referencia analizados

### A. Guía oficial de referencia (`Skill-for-Claude.txt`)
- *The Complete Guide to Building Skills for Claude* (Anthropic): estructura de 3 niveles de revelación progresiva, frontmatter YAML estricto (`name` kebab-case, `description` < 1024 chars con QUÉ + CUÁNDO + tipos de archivo + **negative triggers** `Do NOT use for...`, `license`, `compatibility` 1–500 chars, `metadata`), cero etiquetas XML (`< >`), < 5.000 palabras en `SKILL.md` y validación determinista por código.

### B. Proyectos comparables de referencia
1. **[lifeprompt-team/remotion-scenes](https://github.com/lifeprompt-team/remotion-scenes)** y **[ali-abassi/remotion-templates](https://github.com/ali-abassi/remotion-templates)** (MIT): composición modular por primitivas y catálogo tipado para agentes.
2. **[iart-ai/motion-skills](https://github.com/iart-ai/motion-skills)** (MIT): bucle cerrado de validación determinista, sincronía audio-visual y subtítulos karaoke.
3. **[kumanday/media-tooling](https://github.com/kumanday/media-tooling)**: reglas duras de producción FFmpeg/BT.709/LUFS y anti-patrones.

### C. Los 8 sitios de diseño y animación auditados e integrados
1. **[scrolltide.co](https://scrolltide.co)** ([componentes](https://www.scrolltide.co/components)): `Glow Ring Button` / `Send Halo`, `Service Bento` / `Ledger Bento`, `Focus Reveal` y fondos de malla suave → portados como primitiva `boton_halo`, escenas `hero` y `bento`, y plantilla Familia 6 en `references/prompt-motion-graphics.md`.
2. **[navbar.gallery](https://www.navbar.gallery)**: `Announcement Bar` (píldora superior de lanzamiento) y `Hover Tabs` → portado como píldora superior `badge` en `sc_hero` (descartando mega-menús y dropdowns que ensucian el video).
3. **[footer.design](https://www.footer.design)**: `Wordmark Bleed` y cierres tipográficos audaces → portado como banda `pie` en `sc_bento` y cierres de marca (descartando footers multicolumna SEO).
4. **[cta.gallery](https://www.cta.gallery)**: jerarquía de conversión (métrica de prueba social + píldora CTA con halo pulsante) → integrado en `boton_halo` y `sc_hero`.
5. **[styles.refero.design](https://styles.refero.design)** ([refero.design](https://refero.design)): 2.000+ sistemas de diseño reales expuestos como `DESIGN.md` → documentado el mapeo exacto `DESIGN.md` → `brand/*.json` y style packs en `references/estilos.md`.
6. **[supahero.io](https://supahero.io)**: anatomía de apertura Hero SaaS (`badge` → titular con keyword en acento → subtítulo → tarjeta central → CTA) → implementada en la escena `sc_hero`.
7. **[3dicons.co](https://3dicons.co)** ([GitHub realvjy/3dicons](https://github.com/realvjy/3dicons), CC0): 1.440+ iconos 3D open-source → implementada la primitiva determinista `insignia_3d` (volumen extruido con sombra de contacto, bisel y brillo especular en PIL) y documentado el uso de PNGs CC0 con `flota()`.
8. **[glass.samasante.com](https://glass.samasante.com)** (`@samasante/liquid-glass`, MIT): Liquid Glass óptico con esmerilado, tinte sutil y borde especular (`liseré spéculaire`) → implementada la primitiva `tarjeta_cristal` en PIL (`render_plan.py`) y receta para HyperFrames/Remotion.

## Presupuesto y criterios de parada

- **Presupuesto**: máximo 8 ciclos o 30 minutos de validación activa.
- **Umbral de aceptación**: mejora medible y reproducible en al menos una métrica objetivo, 0 regresiones en compilación AST, tests unitarios y checks deterministas de `validate_skill.py`, manteniendo el principio marca-blanca y DRY.
- **Criterio de parada**: 3 ciclos consecutivos explorando oportunidades distintas sin encontrar nuevas mejoras aceptables, con toda la validación ejecutable en verde.

## Evolución comparable de métricas (Línea Base → Post-Ciclo 4)

| Métrica | Línea Base (Ciclo 0) | Post-Ciclo 1 | Post-Ciclo 2 | Post-Ciclo 3 | Post-Ciclo 4 (Final) | Estado |
|---|---|---|---|---|---|---|
| **Frontmatter YAML válido (`js-yaml` / PyYAML)** | FAIL (error l.3 col.115 `: `) | **PASS (OK)** | **PASS (OK)** | **PASS (OK)** | **PASS (OK)** | Mejorado |
| **Checklist `Skill-for-Claude.txt` (14 ítems)** | 11/14 (78.6%) | **14/14 (100%)** | **14/14 (100%)** | **14/14 (100%)** | **14/14 (100%)** | Mejorado (+21.4%) |
| **Paridad conteo escenas doc (ES+EN) vs código** | Desincronizado (`SKILL.md` decía 24 vs 28) | **28/28 (100%)** | **28/28 (100%)** | **30/30 (100%)** | **30/30 (100%)** | Mejorado |
| **CLIs que arrancan con `--help` sin traceback** | 18/26 (8 fallaban sin PIL/numpy) | 18/26 | **26/26 (100%)** | **26/26 (100%)** | **26/26 (100%)** | Mejorado (+8 CLIs) |
| **Sonda entrada inexistente sin traceback** | 15/21 (6 fallaban sin PIL/numpy) | 15/21 | **21/21 (100%)** | **21/21 (100%)** | **21/21 (100%)** | Mejorado (+6 CLIs) |
| **Subtítulos `pop` con saltos fijos (`\N` + `\q2`)** | FAIL sin PIL | FAIL sin PIL | **PASS (con y sin PIL)** | **PASS** | **PASS** | Mejorado |
| **Escenas en catálogo (`SCENES` + `escenas_muestra.json`)** | 28 | 28 | 28 | **30 (+`hero`, +`bento`)** | **30** | Mejorado (+2 escenas) |
| **Primitivas DRY en `render_plan.py`** | 14 | 14 | 14 | **17 (+`tarjeta_cristal`, +`boton_halo`, +`insignia_3d`)** | **17** | Mejorado (+3 primitivas) |
| **Scripts que compilan (`py_compile` + `ast.parse`)** | 45/45 (100%) | 45/45 (100%) | 45/45 (100%) | 45/45 (100%) | **46/46 (100%)** | Sin regresión |
| **Tests unitarios (`unittest`)** | 19 tests (0.07s) | 19 tests | 19 tests | 19 tests | **32 tests (0.08s, 100% OK)** | Mejorado (+13 tests) |
| **Archivos huérfanos / angle brackets XML** | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | **0 / 0** | Sin regresión |
| **Render en píxeles PIL/NumPy y `pyflakes`** | 28/28 en `RSI_LOG_baseline.txt` | No evaluado en sandbox | No evaluado en sandbox | No evaluado en sandbox | **No evaluado en sandbox** | Declarado honestamente |

## Registro de Ciclos

### Ciclo 1 — Cumplimiento de `Skill-for-Claude.txt`, corrección de YAML frontmatter y paridad AST de conteo de escenas (ES/EN)
- **Hipótesis**: Entrecomillar `description` en `SKILL/SKILL.md`, añadir `license: MIT`, `compatibility` y *negative triggers* (`Do NOT use for...`), corregir los 4 conteos obsoletos (`24` → `28`) en `SKILL/SKILL.md` y añadir validación determinista YAML + AST bilingüe en `SKILL/scripts/validate_skill.py` eliminará el error de parseo YAML y elevará el cumplimiento de `Skill-for-Claude.txt` al 100%.
- **Métrica objetivo**: validez YAML frontmatter (FAIL → PASS), checklist `Skill-for-Claude.txt` (11/14 → 14/14) y paridad documental ES/EN (4 discrepancias → 0).
- **Cambio**: commit `7c685a7` en `SKILL/SKILL.md` y `SKILL/scripts/validate_skill.py`.
- **Resultado pre → post**: Frontmatter válido (`OK`), `license`/`compatibility`/`negative triggers` verificados (`OK`), paridad documental ES/EN `28 == 28` (`OK`).
- **Decisión**: **KEEP** (`7c685a7`).

### Ciclo 2 — Arranque limpio de CLIs (`--help` y entradas inexistentes sin `ModuleNotFoundError`) y fallback determinista en `caption.py`
- **Hipótesis**: Proteger la importación inicial de `numpy`/`PIL` en los 8 scripts CLI que las importaban antes de `argparse` (`contact_sheet.py`, `film_marca.py`, `film_marca_v2.py`, `galeria.py`, `medir_animacion.py`, `render_plan.py`, `sfx.py`, `verificar_ritmo.py`) y en `_film.py`, más añadir el estimador proporcional `_FontEst` en `caption.py` cuando `PIL` no esté instalado, permitirá que las 26 CLIs respondan `--help` sin traceback, que las 21 sondas de archivo inexistente den un error limpio sin traceback y que `caption.py --animate pop` genere siempre saltos de línea fijos (`\N` + `\q2`).
- **Métrica objetivo**: `toda CLI arranca con --help` (18/26 → 26/26), `una entrada inexistente da un error claro, sin traceback` (15/21 → 21/21) y `subtítulos pop: saltos fijos` (FAIL → OK).
- **Cambio**: commit `862f96f` en 10 archivos bajo `SKILL/scripts/`.
- **Resultado pre → post**: Las 3 comprobaciones pasaron de `FAIL` a `OK` en `validate_skill.py`, conservando intacta la paridad de `check_env.py`.
- **Decisión**: **KEEP** (`862f96f`).

### Ciclo 3 — Integración de primitivas DRY y escenas de los 8 sitios de referencia (`hero`, `bento`, `tarjeta_cristal`, `boton_halo`, `insignia_3d`)
- **Hipótesis**: Incorporar las 3 primitivas DRY (`tarjeta_cristal` de `glass.samasante.com`, `boton_halo` de `scrolltide.co` y `cta.gallery`, `insignia_3d` de `3dicons.co`) y 2 escenas nuevas (`sc_hero` inspirada en `supahero.io`/`navbar.gallery`/`scrolltide.co` y `sc_bento` inspirada en `3dicons.co`/`glass.samasante.com`/`footer.design`), junto con sus muestras en `escenas_muestra.json` y el mapeo `DESIGN.md` (`styles.refero.design`) en `references/estilos.md`, ampliará el catálogo de 28 a 30 escenas y de 14 a 17 primitivas DRY sin romper ninguna regla marca-blanca ni de compilación.
- **Métrica objetivo**: escenas validadas en catálogo y muestras (28 → 30), primitivas DRY (14 → 17), sitios de referencia integrados y documentados (0/8 → 8/8).
- **Cambio**: commit `c567c8e` en 9 archivos (`render_plan.py`, `escenas_muestra.json`, `SKILL.md`, `escenas.md`, `plan-video.md`, `arquitectura.md`, `scene-patterns-from-internet.md`, `estilos.md`, `prompt-motion-graphics.md`).
- **Resultado pre → post**: 30/30 escenas sincronizadas entre `SCENES`, `escenas_muestra.json` y los 4 documentos principales (`OK la doc (ES/EN) cuenta 30 escenas como el código (coincide)`), 0 angle brackets, 0 marcas quemadas.
- **Decisión**: **KEEP** (`c567c8e`).

### Ciclo 4 — Ampliación de la suite de tests unitarios (`test_core_and_scenes.py`)
- **Hipótesis**: Añadir `SKILL/scripts/_tests/test_core_and_scenes.py` cubriendo validación de frontmatter YAML, `_comun.py`, `_delivery.py`, `caption.py` y la paridad AST de las 30 escenas y 17 primitivas DRY elevará la cobertura de tests unitarios rápidos sin dependencias externas.
- **Métrica objetivo**: tests unitarios ejecutables con `unittest` (19 → 32 tests), tiempo de ejecución < 0.2s, 0 archivos huérfanos.
- **Cambio**: commit en `SKILL/scripts/_tests/test_core_and_scenes.py` y `SKILL/SKILL.md`.
- **Resultado pre → post**: 32/32 tests unitarios en verde (0.08s), 46/46 scripts compilados, 0 archivos huérfanos en `validate_skill.py`.
- **Decisión**: **KEEP**.

### Ciclos 5, 6 y 7 — Exploración de oportunidades adicionales y criterio de parada (3 ciclos sin cambios)
- **Ciclo 5 (Higiene de seguridad, secretos, emails y rutas absolutas)**: Se escanearon los 46 scripts y 46 archivos Markdown buscando claves API, correos personales, rutas `/Users/` o llamadas inseguras `tempfile.mktemp()`. Resultado: 0 hallazgos en todo el repositorio. **Decisión**: NO-OP (0 cambios necesarios).
- **Ciclo 6 (Cobertura de `--help` en opciones y subcomandos de las 26 CLIs)**: Se verificó el detector `mudas` de `validate_skill.py` sobre todas las CLIs y subcomandos (`montaje.py`, `musica.py`, etc.). Resultado: 100% de opciones y subcomandos ya explicados (`todas`). **Decisión**: NO-OP (0 cambios necesarios).
- **Ciclo 7 (Integridad de enlaces cruzados y detección de huérfanos)**: Se verificaron las 45 referencias y 46 scripts frente al grafo de enlaces de `SKILL.md` y `references/*.md`. Resultado: 0 enlaces rotos y 0 archivos huérfanos. **Decisión**: NO-OP (0 cambios necesarios).
- **Conclusión de parada**: Cumplido el criterio de finalización tras 3 ciclos consecutivos explorando dimensiones distintas sin requerir nuevas intervenciones.
