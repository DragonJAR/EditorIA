# RSI (Recursive Self-Improvement) — EditorIA v1.6.0

## Alcance (scope)

- **Proyecto**: EditorIA — skill de edición de video con IA (30 escenas, 44 scripts Python + 2 suites de tests, 45 referencias, marca-blanca con pack DragonJAR de ejemplo).
- **Tecnologías**: Python 3.9+, PIL/Pillow, ffmpeg, NumPy, ElevenLabs API; opcional Remotion/Node, HyperFrames.
- **Tamaño**: ~108 archivos tracked en git (rama `main`); SKILL.md ~260 líneas; 45 references; 25 scripts raíz + 19 en `ffmpeg_tools/` + 2 en `_tests/`.
- **Estado inicial**: HEAD previo = `e2ea726`. Versión actualizada a `1.6.0`.
- **Lo que NO se toca**: trabajo ajeno, la arquitectura marca-blanca, el API público de scripts, el JSON schema existente de `plan.json`/`shorts-plan.json`, los IDs de las 28 escenas previas, `SKILL/assets/`, `SKILL/film/`, `README*.md`, `LICENSE`.

## Proyectos y sitios de referencia evaluados

1. **Guía oficial de Claude Skills (`Skill-for-Claude.txt`)**: estructura de tres niveles (progressive disclosure), requisitos de YAML frontmatter (`name`, `description` < 1024 chars sin `: ` sin entrecomillar, `license`, `compatibility` 1–500 chars, `metadata`, triggers positivos y negativos `Do NOT use for...`), cero tags XML (`< >`), validación determinista en script.
2. **Bibliotecas open-source de video programático**: `lifeprompt-team/remotion-scenes` (MIT), `reactvideoeditor/remotion-templates` (MIT), `iart-ai/motion-skills` (MIT).
3. **8 sitios de referencia de UI, Hero, CTA, Glass, 3D Icons y Design Systems**:
   - `scrolltide.co` (Glow Ring Button / Send Halo, Service/Ledger Bento, Focus Reveal, malla suave)
   - `navbar.gallery` (Announcement Bar / píldora superior de lanzamiento y Hover Tabs minimalistas)
   - `footer.design` (Wordmark Bleed y firma tipográfica audaz al pie)
   - `cta.gallery` (jerarquía de conversión con métrica de prueba social + CTA con halo)
   - `styles.refero.design` (2.000+ sistemas de diseño reales expuestos como `DESIGN.md` → mapeo a `brand/*.json` y style packs)
   - `supahero.io` (anatomía de apertura SaaS: badge → titular con keyword → tarjeta central → CTA)
   - `3dicons.co` (1.440+ iconos 3D CC0 de Vijay Verma → primitiva `insignia_3d` extruida con sombra de contacto y bisel)
   - `glass.samasante.com` (`@samasante/liquid-glass` MIT → primitiva `tarjeta_cristal` con borde especular `liseré spéculaire`)

## Entorno (env) y limitaciones

- **OS**: macOS (Darwin)
- **Python**: 3.14.8 (`/opt/homebrew/bin/python3`) y 3.9.6 (CommandLineTools)
- **FFmpeg / FFprobe**: 9.0.2 (`/opt/homebrew/bin/ffmpeg`)
- **Node / npx**: v26.10.0
- **Limitación del sandbox actual**: `PIL` (Pillow), `numpy` y `pyflakes` no están instalados en el `site-packages` accesible desde el `$HOME` aislado del sandbox (`check_env.py` lo reporta explícitamente). Por tanto, las pruebas de renderizado píxel a píxel con `PIL`/`numpy` y `pyflakes` se declaran como **No evaluado en sandbox** (evaluadas mediante `ast.parse`, paridad AST, CLI `--help`/sondas de entrada y `unittest`; línea base histórica de render en `RSI_LOG_baseline.txt`).

## Comandos de referencia (commands)

```bash
export PATH="/opt/homebrew/bin:$PATH"

# Compilación determinista de todos los scripts
python3 -m py_compile SKILL/scripts/*.py SKILL/scripts/ffmpeg_tools/*.py SKILL/scripts/_tests/*.py

# Suite de tests unitarios
python3 -m unittest discover -s SKILL/scripts/_tests -v

# Validador determinista de la skill
python3 SKILL/scripts/validate_skill.py
```

## Evolución de métricas (Baseline → Final)

| Métrica | Baseline (Ciclo 0) | Post-Ciclo 4 (Final) | Estado |
|---|---|---|---|
| **Frontmatter YAML válido (`js-yaml`/strict)** | FAIL (error en línea 3 col 115 por `: ` sin comillas) | PASS (`description` entrecomillada + `_yaml_fm_valido`) | Mejorado |
| **Cumplimiento checklist `Skill-for-Claude.txt`** | 11/14 (78.6% — faltaban `license`, `compatibility`, negative triggers) | 14/14 (100%) | Mejorado |
| **Paridad conteo de escenas doc (ES/EN) vs `SCENES`** | Desincronizado (`SKILL.md` decía `24`, código tenía `28`) | 100% sincronizado (`30` en `SCENES`, `escenas_muestra.json` y docs ES/EN) | Mejorado |
| **CLIs que arrancan con `--help` sin traceback (sin PIL/numpy)** | 18/26 PASS (8 FAIL con `ModuleNotFoundError` crudo) | 26/26 PASS (0 tracebacks) | Mejorado |
| **CLIs ante entrada inexistente sin traceback (sin PIL/numpy)** | 15/21 PASS (6 FAIL con `ModuleNotFoundError` crudo) | 21/21 PASS (0 tracebacks) | Mejorado |
| **Subtítulos `pop` con saltos fijos (`\N` + `\q2`) sin PIL** | FAIL (caía a texto sin partir) | PASS (`_FontEst` fallback determinista) | Mejorado |
| **Catálogo de escenas (`SCENES` + `escenas_muestra.json`)** | 28 escenas / 14 primitivas DRY | 30 escenas (`+hero`, `+bento`) / 17 primitivas DRY (`+tarjeta_cristal`, `+boton_halo`, `+insignia_3d`) | Mejorado |
| **Tests unitarios (`unittest`)** | 19 tests (1 archivo, `test_chapters.py`) | 28 tests (2 archivos, `+test_core_and_scenes.py`, 0.05s) | Mejorado |
| **Compilación AST (`ast.parse` / `py_compile`)** | 45/45 archivos OK | 46/46 archivos OK (0 errores) | En verde |
| **Archivos huérfanos / tags XML / marcas quemadas** | 0 / 0 / 0 | 0 / 0 / 0 | En verde |
| **Render en píxeles (`PIL`/`numpy`) y `pyflakes`** | 28/28 en `RSI_LOG_baseline.txt` | No evaluado en sandbox (dependencias `PIL`/`numpy` ausentes en sandbox) | No evaluado |

## Registro de Ciclos

### Ciclo 1 (2026-10-16) — Cumplimiento `Skill-for-Claude.txt`, YAML Frontmatter y Paridad AST ES/EN
- **Hipótesis**: Entrecomillar `description` en `SKILL/SKILL.md`, añadir `license: MIT`, `compatibility` y negative triggers (`Do NOT use for...`), corregir los conteos obsoletos (`24` → `28`) en `SKILL/SKILL.md` y agregar validación determinista YAML + AST bilingüe en `SKILL/scripts/validate_skill.py` eliminará el fallo de carga de frontmatter y la desincronización doc↔código.
- **Resultado pre → post**: YAML frontmatter FAIL → PASS; checklist `Skill-for-Claude.txt` 11/14 → 14/14; desincronizaciones de conteo en `SKILL.md` 4 → 0.
- **Decisión**: KEEP (commit `7c685a7`).

### Ciclo 2 (2026-10-16) — Arranque limpio de CLIs (`--help` y entradas inexistentes) y Fallback en `caption.py`
- **Hipótesis**: Proteger los imports de `numpy`/`PIL` en los 8 scripts CLI (`contact_sheet.py`, `film_marca.py`, `film_marca_v2.py`, `galeria.py`, `medir_animacion.py`, `render_plan.py`, `sfx.py`, `verificar_ritmo.py`) y `_film.py` para permitir `--help` y emitir un error limpio sin `Traceback` cuando falten librerías, más añadir el estimador proporcional `_FontEst` en `caption.py`, hará pasar los 3 checks de CLI y subtítulos en entornos mínimos.
- **Resultado pre → post**: `--help` sin traceback 18/26 → 26/26; sonda de entrada inexistente 15/21 → 21/21; `subtítulos pop` con saltos fijos FAIL → OK.
- **Decisión**: KEEP (commit `862f96f`).

### Ciclo 3 (2026-10-16) — Integración coherente de los 8 sitios de referencia (3 primitivas DRY + 2 escenas + documentación)
- **Hipótesis**: Incorporar las primitivas DRY `tarjeta_cristal` (`glass.samasante.com`), `boton_halo` (`scrolltide.co` + `cta.gallery`) e `insignia_3d` (`3dicons.co`), junto con las escenas `sc_hero` (`supahero.io` + `navbar.gallery` + `scrolltide.co`) y `sc_bento` (`3dicons.co` + `glass.samasante.com` + `footer.design`), sus muestras en `escenas_muestra.json` y el mapeo `DESIGN.md` (`styles.refero.design`) en `references/`, ampliará el catálogo de 28 a 30 escenas manteniendo 0 huérfanos, 0 tags XML y 100% de paridad AST.
- **Resultado pre → post**: Escenas 28 → 30; primitivas DRY 14 → 17; sitios de referencia integrados 0/8 → 8/8; paridad AST 30/30 OK.
- **Decisión**: KEEP.

### Ciclo 4 (2026-10-16) — Ampliación de pruebas unitarias deterministas (`test_core_and_scenes.py`)
- **Hipótesis**: Añadir `SKILL/scripts/_tests/test_core_and_scenes.py` cubriendo validación de frontmatter YAML, campos de `Skill-for-Claude.txt`, paridad AST de las 30 escenas y primitivas de Ronda 4, utilidades de `_comun.py`/`_delivery.py` y agrupamiento `phrase_aware`/`_partir_fijo` de `caption.py` elevará la cobertura de tests automáticos rápidos sin introducir archivos huérfanos.
- **Resultado pre → post**: Tests unitarios 19 → 28 (100% OK en 0.05s); 0 archivos huérfanos en `validate_skill.py`.
- **Decisión**: KEEP.

### Ciclos 5, 6 y 7 (2026-10-16) — Exploración de convergencia (criterio de parada: 3 ciclos consecutivos sin nuevas intervenciones necesarias)
- **Ciclo 5 (Resolución de fuentes en `_plataforma.py`)**: Se inspeccionó `_plataforma.py`; ya prioriza `FUENTES_SKILL` (`PlusJakartaSans-wght.ttf` y `Montserrat-wght.ttf` empaquetadas) y maneja Windows/macOS/Linux sin hardcodear rutas. No requiere cambios (evitar refactor cosmético).
- **Ciclo 6 (Heurística de `retakes.py` y `auditar_plan.py`)**: Se revisó `auditar_plan.py`; ya lee dinámicamente `SCENES` desde `render_plan.py` y verifica que la voz no pise la escena siguiente (`validate_skill.py` check 7h en verde). No requiere cambios.
- **Ciclo 7 (Tamaño de `SKILL/SKILL.md` y progressive disclosure)**: `SKILL/SKILL.md` tiene 2.049 palabras (< 5.000 palabras recomendadas en `Skill-for-Claude.txt`) y delega el detalle técnico en `references/`. No requiere cambios.
- **Conclusión de parada**: Tres ciclos consecutivos explorando oportunidades distintas confirmaron que no hay mejoras adicionales necesarias dentro del alcance autorizado.
