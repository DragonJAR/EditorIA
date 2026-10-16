# RSI (Recursive Self-Improvement) — EditorIA v1.7.0

## Alcance (scope)

- **Proyecto**: EditorIA — skill de edición de video con IA (`editoria/`, 30 escenas, 44 scripts Python + 2 suites de tests, 45 referencias en kebab-case, marca-blanca con pack DragonJAR de ejemplo).
- **Tecnologías**: Python 3.9+, PIL/Pillow, ffmpeg, NumPy, ElevenLabs API; opcional Remotion/Node, HyperFrames.
- **Tamaño**: ~107 archivos tracked en git (rama `main`); `editoria/SKILL.md` 240 líneas (1.682 palabras); 45 references; 25 scripts raíz + 19 en `ffmpeg_tools/` + 2 en `_tests/`.
- **Estado inicial**: HEAD previo = `e2ea726`. Versión actualizada a `1.7.0`.
- **Lo que NO se toca**: trabajo ajeno, la arquitectura marca-blanca, el API público de scripts, el JSON schema existente de `plan.json`/`shorts-plan.json`, los IDs de las 28 escenas previas, `editoria/assets/`, `editoria/film/`, `LICENSE`.

## Proyectos y sitios de referencia evaluados

1. **Guía oficial de Claude Skills (`Skill-for-Claude.txt`)**:
   - **Reglas críticas de nombres (Cap. 2, pág. 10, 25 y Ref. A/B, pág. 30–31)**:
     - Carpeta de la skill en `kebab-case` estricto (`editoria/`, sin mayúsculas, sin espacios, sin guiones bajos) y coincidiendo exactamente con `name: editoria` en el frontmatter (`SKILL/` y `EditorIA.zip` incumplían esta regla).
     - Archivo principal exactamente `SKILL.md` (case-sensitive).
     - Prohibido incluir cualquier `README.md` dentro de la carpeta de la skill (`brand/README.md` eliminado; toda documentación vive en `SKILL.md` o `references/`).
     - Referencias en `references/` nombradas en `kebab-case.md`.
   - **Frontmatter YAML y estructura de `SKILL.md` (pág. 10–13, 25–27, 30–31)**:
     - `name`, `description` (< 1024 chars, QUÉ hace + CUÁNDO usarla + triggers negativos `Do NOT use for...`), `license: MIT`, `compatibility` (1–500 chars) y `metadata` en bloque YAML estándar (`author`, `version`, `category`, `tags`).
     - Cero tags XML (`< >`), `< 5.000` palabras y `< 500` líneas.
     - Secciones canónicas: `## Critical`, `## Instructions` (con pasos numerados y `Expected output:`), `## Examples` (`User says:` / `Actions:` / `Result:`), `## Troubleshooting` (`Error:` / `Cause:` / `Solution:`) y `## Performance Notes`.
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
python3 -m py_compile editoria/scripts/*.py editoria/scripts/ffmpeg_tools/*.py editoria/scripts/_tests/*.py

# Suite de tests unitarios (29 tests)
python3 -m unittest discover -s editoria/scripts/_tests -v

# Validador determinista de la skill
python3 editoria/scripts/validate_skill.py
```

## Evolución de métricas (Baseline → Final v1.7.0)

| Métrica | Baseline (Ciclo 0) | Final (v1.7.0) | Estado |
|---|---|---|---|
| **Nombre de carpeta de la skill == `name` en `kebab-case`** | FAIL (`SKILL/` en mayúsculas != `editoria` + `EditorIA.zip` con mayúsculas) | PASS (`editoria/` == `name: editoria` en `kebab-case` estricto) | Mejorado |
| **Sin `README.md` ni `.zip` dentro de la carpeta de la skill** | FAIL (`SKILL/brand/README.md` y `SKILL/EditorIA.zip` presentes) | PASS (0 `README.md` y 0 `.zip` en todo el árbol `editoria/`) | Mejorado |
| **Frontmatter YAML válido (`js-yaml`/strict + bloque `metadata`)** | FAIL (error en línea 3 col 115 por `: ` sin comillas) | PASS (`description` limpia + `metadata` en bloque YAML estándar) | Mejorado |
| **Cumplimiento checklist `Skill-for-Claude.txt` (Ref. A y B)** | 10/18 (55.6%) | 18/18 (100% — incluye `## Instructions`, `## Examples`, `## Troubleshooting`, `## Performance Notes`, `< 500` líneas) | Mejorado |
| **Compatibilidad Python 3.9 en `validate_skill.py`** | FAIL (`AttributeError: sys.stdlib_module_names` en Python 3.9) | PASS (fallback explícito de stdlib para Python 3.9+) | Mejorado |
| **Paridad conteo de escenas doc (ES/EN) vs `SCENES`** | Desincronizado (`SKILL.md` decía `24`, código tenía `28`) | 100% sincronizado (`30` en `SCENES`, `escenas_muestra.json` y docs ES/EN) | Mejorado |
| **CLIs que arrancan con `--help` sin traceback (sin PIL/numpy)** | 18/26 PASS (8 FAIL con `ModuleNotFoundError` crudo) | 26/26 PASS (0 tracebacks) | Mejorado |
| **CLIs ante entrada inexistente sin traceback (sin PIL/numpy)** | 15/21 PASS (6 FAIL con `ModuleNotFoundError` crudo) | 21/21 PASS (0 tracebacks) | Mejorado |
| **Subtítulos `pop` con saltos fijos (`\N` + `\q2`) sin PIL** | FAIL (caía a texto sin partir) | PASS (`_FontEst` fallback determinista) | Mejorado |
| **Catálogo de escenas (`SCENES` + `escenas_muestra.json`)** | 28 escenas / 14 primitivas DRY | 30 escenas (`+hero`, `+bento`) / 17 primitivas DRY (`+tarjeta_cristal`, `+boton_halo`, `+insignia_3d`) | Mejorado |
| **Tests unitarios (`unittest`)** | 19 tests (`test_chapters.py`) | 29 tests (`test_chapters.py` + `test_core_and_scenes.py`, 0.09s) | Mejorado |
| **Compilación AST (`ast.parse` / `py_compile`)** | 45/45 archivos OK | 46/46 archivos OK (0 errores) | En verde |
| **Archivos huérfanos / tags XML / marcas quemadas** | 0 / 0 / 0 | 0 / 0 / 0 | En verde |
| **Render en píxeles (`PIL`/`numpy`) y `pyflakes`** | 28/28 en `RSI_LOG_baseline.txt` | No evaluado en sandbox (dependencias `PIL`/`numpy` ausentes en sandbox) | No evaluado |

## Registro de Ciclos

### Ciclo 1 (2026-10-16) — Cumplimiento inicial YAML Frontmatter y Paridad AST ES/EN
- **Hipótesis**: Entrecomillar `description` en `SKILL.md`, añadir `license: MIT`, `compatibility` y negative triggers (`Do NOT use for...`), corregir los conteos obsoletos (`24` → `28`) y agregar validación determinista YAML + AST bilingüe en `validate_skill.py` eliminará el fallo de carga de frontmatter y la desincronización doc↔código.
- **Resultado pre → post**: YAML frontmatter FAIL → PASS; desincronizaciones de conteo en `SKILL.md` 4 → 0.
- **Decisión**: KEEP (commit `7c685a7`).

### Ciclo 2 (2026-10-16) — Arranque limpio de CLIs (`--help` y entradas inexistentes) y Fallback en `caption.py`
- **Hipótesis**: Proteger los imports de `numpy`/`PIL` en los 8 scripts CLI y `_film.py` para permitir `--help` y emitir un error limpio sin `Traceback` cuando falten librerías, más añadir el estimador proporcional `_FontEst` en `caption.py`, hará pasar los 3 checks de CLI y subtítulos en entornos mínimos.
- **Resultado pre → post**: `--help` sin traceback 18/26 → 26/26; sonda de entrada inexistente 15/21 → 21/21; `subtítulos pop` con saltos fijos FAIL → OK.
- **Decisión**: KEEP (commit `862f96f`).

### Ciclos 3 y 4 (2026-10-16) — Integración coherente de los 8 sitios de referencia + Suite de pruebas unitarias
- **Hipótesis**: Incorporar las primitivas DRY `tarjeta_cristal`, `boton_halo` e `insignia_3d`, las escenas `sc_hero` y `sc_bento`, sus muestras en `escenas_muestra.json`, el mapeo `DESIGN.md` en `references/` y la suite `test_core_and_scenes.py` ampliará el catálogo de 28 a 30 escenas con cobertura unitaria determinista.
- **Resultado pre → post**: Escenas 28 → 30; primitivas DRY 14 → 17; tests unitarios 19 → 28.
- **Decisión**: KEEP (commit `a54c94f`).

### Ciclo 5 (2026-10-16) — Cumplimiento estricto de nombres y estructura según `Skill-for-Claude.txt` (v1.7.0)
- **Hipótesis**: Renombrar la carpeta de la skill de `SKILL/` (mayúsculas) a `editoria/` (`kebab-case` estricto idéntico a `name: editoria`), eliminar `brand/README.md` y `EditorIA.zip` dentro de la carpeta de la skill, estructurar `metadata` en bloque YAML estándar y `SKILL.md` con las secciones canónicas (`## Critical`, `## Instructions`, `## Examples`, `## Troubleshooting`, `## Performance Notes` < 500 líneas), corregir el crash de `sys.stdlib_module_names` en Python 3.9 dentro de `validate_skill.py` y auditar estas reglas con un nuevo test unitario eliminará todos los rechazos de subida/nombre en Claude.
- **Resultado pre → post**: `name == carpeta` en `kebab-case` FAIL (`SKILL`) → PASS (`editoria`); `README.md`/`.zip` internos 2 → 0; compatibilidad Python 3.9 en `validate_skill.py` FAIL → PASS; tests unitarios 28 → 29 (100% OK).
- **Decisión**: KEEP.
