# RSI (Recursive Self-Improvement) — EditorIA (Rondas 1 y 2)

## 1. Alcance, Restricciones y Trabajo Preexistente

- **Proyecto**: EditorIA — skill de edición de video con IA (`editoria/`, 30 escenas declarativas, 17 primitivas DRY, 44 scripts de producción + 2 suites de tests = 46 archivos `.py`, 45 referencias en `kebab-case.md`, arquitectura marca-blanca con pack `dragonjar.json` de ejemplo).
- **Tecnologías**: Python 3.9+ (probado en 3.14.8), FFmpeg / FFprobe 9.0.2, Pillow (`PIL`), NumPy, ElevenLabs API (`requests`), Whisper local opcional (`whisper.cpp` / `faster-whisper` / `openai-whisper`), Node.js v26.10.0 opcional para Remotion / HyperFrames.
- **Tamaño auditado**: 46 archivos Python (`14.275` LOC Iniciales → `14.588` LOC Finales, `517` funciones), 45 archivos `.md` en `editoria/references/`, `editoria/SKILL.md` (240 líneas, 1.703 palabras).
- **Trabajo ajeno y cambios locales preexistentes preservados**:
  - Al iniciar la Ronda 2 sobre `HEAD = d76ce18`, existían modificaciones locales sin commitear en 6 archivos (`README.md`, `README.en.md`, `editoria/SKILL.md`, `editoria/references/i18n.md`, `editoria/scripts/render_plan.py`, `editoria/scripts/validate_skill.py`).
  - Se preservaron íntegramente todas las modificaciones preexistentes: los 4 archivos de documentación/i18n (`README.md`, `README.en.md`, `editoria/SKILL.md`, `editoria/references/i18n.md`) se mantuvieron intactos en el árbol de trabajo sin mezclarlos en commits de código, y las mejoras preexistentes en `render_plan.py` y `validate_skill.py` se conservaron al 100%.
- **Restricciones duras**:
  - No romper la arquitectura marca-blanca (`brand/*.json`), ni el esquema de `plan.json` / `shorts-plan.json`, ni los IDs de las 30 escenas, ni el contrato CLI (`references/cli-contract.md`).
  - No introducir `README.md`, `.zip` ni `.DS_Store` dentro de `editoria/` (`Skill-for-Claude.txt`).

## 2. Proyectos de Referencia y Criterios de Calidad Extraídos

1. **Anthropic Agent Skills (`anthropics/skills` y guía `Skill-for-Claude.txt`)** — [Repositorio GitHub](https://github.com/anthropics/skills):
   - *Criterios aplicables*: carpeta de la skill en `kebab-case` idéntica a `name: editoria`; `SKILL.md` `< 500` líneas y `< 5.000` palabras con frontmatter YAML estricto (`name`, `description` con triggers positivos y negativos, `license`, `compatibility`, `metadata`); cero `README.md` o `.zip` internos; cero archivos huérfanos.
2. **Remotion (`remotion-dev/remotion` / `lifeprompt-team/remotion-scenes`)** — [Repositorio GitHub](https://github.com/remotion-dev/remotion):
   - *Criterios aplicables*: validación determinista previa al render (`auditar_plan.py` y `preparar_escenas` antes de rasterizar frames); separación entre primitivas DRY y escenas; tolerancia a campos omitidos (`at` derivado desde muestras canónicas `escenas_muestra.json`) y rechazo temprano de campos malformados o tipos inválidos sin tracebacks crudos.
3. **FFmpeg Python & Media Tooling CLIs (`kkroening/ffmpeg-python` / `kajisho5/ffmpeg-skill`)** — [Repositorio GitHub](https://github.com/kkroening/ffmpeg-python):
   - *Criterios aplicables*: toda CLI debe responder `--help` con código de salida `0` y bloque `usage:` incluso si faltan librerías opcionales o de render (`PIL`/`numpy`); toda entrada inexistente o corrupta debe producir un diagnóstico limpio sin `Traceback`; ninguna invocación fallida de `ffmpeg`/`ffprobe` debe borrar su archivo de entrada.

## 3. Entorno, Limitaciones y Presupuesto Explícito

- **Entorno**: macOS (Darwin), Python `3.14.8` (`/opt/homebrew/bin/python3`), FFmpeg / FFprobe `9.0.2` (`/opt/homebrew/bin/ffmpeg`), Ruff (`ruff`), Pytest / Unittest, Node `v26.10.0`.
- **Limitaciones del sandbox (declaradas explícitamente como No evaluado)**:
  - `PIL` (Pillow), `numpy`, `pyflakes`, `coverage` y `mypy` **no están instalados** en el `site-packages` accesible desde el sandbox actual (`check_env.py` lo diagnostica explícitamente).
  - Por tanto, el renderizado píxel a píxel de las 30 escenas con `PIL`/`numpy`, el detector de pops sobre matrices `numpy`, el lint con `pyflakes`, el tipado con `mypy` y la cobertura con `coverage.py` se marcan como **No evaluado en sandbox** (nunca como satisfactorio sin comprobarlo).
  - En su lugar, la cobertura de líneas se mide de forma determinista con el módulo estándar `trace` de Python (`python3 -m trace --count`), el análisis estático con `ruff`, y las pruebas de audio/color/alfa/montaje con `ffmpeg` real + stdlib (`struct`, `math`, `zlib`).
- **Umbrales de aceptación por ciclo**:
  - Mejora cuantificable y reproducible en al menos una métrica objetivo sin ninguna regresión en compilación (`46/46`), tests unitarios (`100% PASS`), `validate_skill.py` (`exit 0`), seguridad (`0` vulnerabilidades) o compatibilidad Python 3.9+.
  - Para mediciones de tiempo (variables), se exige la **mediana de 3 repeticiones** en condiciones equivalentes y una mejora `>= 15%` (o `>= 20%` en micro-benchmarks) con paridad numérica exacta (`0.0` deriva en BPM/`beat0`).
- **Presupuesto explícito**:
  - Máximo **8 ciclos** de iteración en Ronda 2 (presupuesto de tiempo `< 15 min` de cómputo total, `< 120s` por validación completa).
  - Criterio de parada: **3 ciclos consecutivos** explorando oportunidades distintas sin encontrar mejoras aceptables que superen el umbral, con toda la validación obligatoria en verde.

## 4. Comandos Reproducibles de Validación

```bash
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

# 1. Compilación determinista de los 46 scripts
python3 -m py_compile editoria/scripts/*.py editoria/scripts/ffmpeg_tools/*.py editoria/scripts/_tests/*.py

# 2. Análisis estático de defectos reales (Pyflakes F, Syntax E9, Imports E402, Whitespace W291/W292, Bugbear B007/B023)
ruff check --select F,E9,E402,W291,W292,B007,B023 editoria/scripts/

# 3. Suite de pruebas unitarias (41 tests)
python3 -m unittest discover -s editoria/scripts/_tests -v

# 4. Validador determinista integral de la skill
python3 editoria/scripts/validate_skill.py
```

## 5. Evolución Comparable de Métricas (Ronda 1 → Línea Base Ronda 2 → Final Ronda 2)

| Dimensión / Métrica | Ronda 1 Base (Ciclo 0) | Ronda 2 Base (Pre-Ciclo 1) | Ronda 2 Final (Post-Ciclo 7) | Estado |
|---|---|---|---|---|
| **Compilación (`py_compile` / `ast.parse`)** | 45/45 OK | 46/46 OK | **46/46 OK (0 errores)** | En verde |
| **CLIs con `--help` exit 0 + `usage:` (criterio v1.1)** | 18/26 (sin traceback) | 34/38 PASS (4 FAIL: `alinear`, `beat_grid`, `medir_mezcla`, `thumbnail`) | **38/38 PASS (100%, 0 crudas, 0 mudas)** | Mejorado |
| **CLIs con argumentos reales ante entrada inexistente (sin traceback)** | 15/21 (sonda simple `-o`) | 17/21 PASS (4 FAIL con `Traceback`: `auditar_plan`, `musica mix/musiconly`, `poster_frame`) | **21/21 PASS (0 tracebacks)** | Mejorado |
| **Validador `validate_skill.py` (checks verificables en entorno)** | FAIL (frontmatter/estructura) | FAIL (`rc=1`: 275 OK, 8 FAIL por acoplamiento a `PIL`/`numpy`, `sys.path` de `loudness` y `--help thumbnail.py`) | **PASS (`rc=0`: 290 OK, 0 FAIL; 5 bloques de píxeles declarados `AVISO [no evaluado sin PIL/numpy]`)** | Mejorado |
| **Detección de ritmo `beat_grid.analizar` y `medir_mezcla` sin `numpy`** | FAIL (`SystemExit: Falta numpy`) | FAIL (`SystemExit: Falta numpy`) | **PASS (fallback stdlib `struct`/`math`: `100.0 BPM`, `beat0=0.052s` en `0.96s`)** | Mejorado |
| **Tests unitarios (`unittest`)** | 19 tests (`0.05s`) | 29 tests (`0.09s`) | **41 tests (`1.71s`, 100% OK)** | Mejorado |
| **Cobertura de líneas stdlib (`trace`) en 9 módulos core** | No medida (~5%) | **5.6% (46/818 líneas ejecutables)** | **50.6% (437/863 líneas ejecutables, +45.0 pp)** | Mejorado |
| **Análisis estático `ruff` (reglas `F,E9,E402,W291,W292,B007,B023`)** | No evaluado | **25 errores** (closures en bucle `B023`, vars muertas `B007`, imports `E402`, `W291/W292`) | **0 errores (`All checks passed!`)** | Mejorado |
| **Seguridad estática (`shell=True`, `eval`/`exec`, `mktemp`, secretos)** | 0 hallazgos | 0 hallazgos | **0 hallazgos** | En verde |
| **Complejidad ciclomática AST (517–523 funciones)** | Media 5.8 | Media 5.83 (máx 95 en `caption.py:main`) | **Media 5.81 (sin incremento de complejidad)** | En verde |
| **Paridad `editoria.zip` ↔ carpeta `editoria/` (SHA-256)** | FAIL (`EditorIA.zip` interno) | 115/115 archivos sincronizados | **115/115 archivos sincronizados (0 diferencias SHA-256)** | En verde |
| **Render en píxeles (`PIL`/`numpy`), `pyflakes`, `coverage.py`, `mypy`** | 28/28 en `RSI_LOG_baseline.txt` | No evaluado en sandbox | **No evaluado en sandbox** (librerías ausentes en `$HOME` aislado) | No evaluado |

## 6. Registro de Ciclos — Ronda 2

### Ciclo 1 (Ronda 2) — Arranque `--help` (exit 0 + `usage:`) en las 38 CLIs e importación modular sin `PIL`/`numpy`
- **Hipótesis**: Diferir la validación de `numpy`/`PIL` hasta después de `ap.parse_args()` en `alinear.py`, `beat_grid.py`, `medir_mezcla.py` y `ffmpeg_tools/thumbnail.py`, y restringir el `sys.exit` superior de `render_plan.py` a `__name__ == "__main__"`, permitirá que las 38 CLIs respondan `--help` con código `0` y `usage:` y que los módulos expongan sus funciones puras para pruebas unitarias sin `PIL`/`numpy`.
- **Cambio de criterio versionado (v1.1)**: En `validate_skill.py`, el chequeo de `--help` se endureció para exigir `_r.returncode == 0` y `"usage" in _r.stdout.lower()` además de ausencia de `Traceback`. Re-evaluando la línea base con el criterio v1.1: **34/38 PASS (4 FAIL)**.
- **Resultado pre → post**: CLIs con `--help` exit 0 y `usage:` **34/38 → 38/38** (`0 crudas`, `0 mudas`); `--help scripts/ffmpeg_tools/thumbnail.py` en `validate_skill.py` **FAIL → OK**; tests unitarios **29 → 31 PASS**.
- **Decisión**: **KEEP** (commit `46fc075`).

### Ciclo 2 (Ronda 2) — Blindaje ante entradas inexistentes, JSON corrupto y campos `from`/`to` nulos en `auditar_plan.py`, `musica.py`, `poster_frame.py` y `contact_sheet.py`
- **Hipótesis**: Validar explícitamente la existencia de archivos de entrada, capturar errores de JSON/FFmpeg sin `Traceback` crudo y verificar que `from`/`to` sean numéricos antes de invocar `at_fuera()` en `auditar_plan.py` (ampliando además la inspección de `at` a `pasos`, `items` y `notificaciones`) eliminará los 4 tracebacks detectados al invocar las CLIs con sus argumentos reales requeridos.
- **Resultado pre → post**: Sonda de CLIs con argumentos reales ante entradas inexistentes **17/21 → 21/21 sin traceback**; `auditar_plan.py` soporta `from: null` con `at` sin `TypeError` y audita las 5 listas de sub-elementos; tests unitarios **31 → 33 PASS**.
- **Decisión**: **KEEP** (commit `a7496c2`).

### Ciclo 3 (Ronda 2) — Fallback determinista stdlib (`struct`/`math`) en `beat_grid.py` y `medir_mezcla.py` + separación honesta de checks sin `PIL`/`numpy` en `validate_skill.py`
- **Hipótesis**: Implementar un fallback determinista en stdlib (`struct` y `math`) en `beat_grid.py` y `medir_mezcla.py`, permitir `preparar_escenas(None, plan)` en `render_plan.py`, añadir `ffmpeg_tools` a `sys.path` antes de la sección 5 en `validate_skill.py`, generar las imágenes sintéticas de prueba para `7a` (color BT.709), `7b` (alfa `.webm`/`.mov`), `7d` (`montaje.py pase`) y `6` (`thumbnail >4 palabras`) mediante `ffmpeg`/`zlib`/`struct` y reportar explícitamente como `AVISO [no evaluado sin PIL/numpy]` únicamente los 5 bloques de rasterizado PIL/numpy permitirá ejecutar y verificar todos los checks posibles en el entorno actual sin falsos fallos ni falsos positivos.
- **Resultado pre → post**: `beat_grid.analizar("editoria/film/musica_demo.mp3")` sin `numpy` detecta exactamente `100.0 BPM` y `beat0 = 0.052s` en `0.96s`; checks verificados en `validate_skill.py` **275 → 290 OK, 0 FAIL (`SKILL VALIDO`)**, con 5 avisos explícitos `AVISO [no evaluado sin PIL/numpy]`; tests unitarios **33 → 35 PASS**.
- **Decisión**: **KEEP** (commit `09b401d`).

### Ciclo 4 (Ronda 2) — Corrección de los 25 defectos de análisis estático (`ruff`) y expansión de cobertura unitaria (`trace`)
- **Hipótesis**: Enlazar por valor las variables de bucle en las closures de `caption.py`, `render_plan.py` y `validate_skill.py` (`B023`), renombrar variables de control no usadas (`B007` en `galeria.py`, `render_plan.py`, `validate_skill.py`), mover imports a nivel superior en `check_env.py` (`E402` + `with open` `SIM115`), corregir `W291`/`W292` en `film_marca.py` y `alinear.py`, y añadir pruebas unitarias para `beat_sync`, `beat_file`, `aplicar_edl`, `grade`, `shorts_plan`, `auditar_plan` y `registrar_aprendizaje` reducirá a `0` los defectos de `ruff` y elevará la cobertura `trace` de los 9 módulos core de `5.6%` a `> 50%`.
- **Resultado pre → post**: Errores `ruff --select F,E9,E402,W291,W292,B007,B023` **25 → 0 (`All checks passed!`)**; tests unitarios **35 → 41 PASS**; cobertura de líneas `trace` en los 9 módulos core **5.6% (46/818) → 50.6% (437/863)**.
- **Decisión**: **KEEP** (commit `80d2a81`).

### Ciclo 5 (Ronda 2 — Convergencia 1/3) — Deduplicación de desplazamientos `b0` por frame entero en `beat_grid.ajustar_rejilla`
- **Hipótesis**: En el modo stdlib de `beat_grid.ajustar_rejilla`, pre-redondear `b_idx = int(round(b0 * FPS))` y `ko = int(round(k * step_f))` para omitir valores de `b0` que caen en el mismo frame inicial reducirá el tiempo de `beat_grid.analizar(musica_demo.mp3)` en `>= 20%` manteniendo paridad numérica exacta `(bpm=100.0, beat0=0.052, compas0=0.052)`.
- **Medición (3 repeticiones)**: Tiempo mediano `0.964s` (`[1.028, 0.964, 0.879]`) → `0.588s` (`[0.588, 0.582, 0.594]`, `-39.0%`), **pero** al redondear `b0 * FPS` y `k * step_f` por separado antes de sumarlos se acumula error de cuantización que desplaza el resultado de `(100.0, 0.052, 0.052)` a `(99.96, 0.032, 0.032)`, rompiendo la paridad exacta con `numpy`.
- **Decisión**: **DISCARD** (revertido íntegramente; la precisión del beat grid tiene prioridad sobre 0.37s de CPU).

### Ciclo 6 (Ronda 2 — Convergencia 2/3) — Unificación de `chapters.fmt_tiempo` con `ffmpeg_tools/_comun.fmt_srt_time`
- **Hipótesis**: Delegar `chapters.fmt_tiempo` en `_comun.fmt_srt_time` reducirá duplicación y líneas de código en `chapters.py` sin aumentar la complejidad ciclomática ni acoplar rutas.
- **Medición**: `chapters.py` tiene `138` LOC y `17` ramas AST; `fmt_tiempo` ocupa solo 6 líneas porque YouTube exige `MM:SS` (sin horas cuando `< 3600s` y redondeo al segundo `int(s + 0.5)`), mientras que `fmt_srt_time` produce `HH:MM:SS,mmm`. Unificar ambos requiere insertar `sys.path` hacia `ffmpeg_tools` y añadir condicionales de recorte y redondeo (+5 LOC netas, +2 ramas AST).
- **Decisión**: **DISCARD** (no reduce duplicación real y empeora acoplamiento y complejidad).

### Ciclo 7 (Ronda 2 — Convergencia 3/3) — Paralelización con `ThreadPoolExecutor` del bucle `--help` en `validate_skill.py`
- **Hipótesis**: Ejecutar el bucle de verificación `--help` en `validate_skill.py` con `ThreadPoolExecutor(max_workers=2)` reducirá el tiempo total de `validate_skill.py` en `>= 15%`.
- **Medición (3 repeticiones)**: Aunque el sub-bucle `--help` aislado baja de mediana `2.318s` (`[2.567, 2.175, 2.318]`) a `1.267s` (`[1.278, 1.242, 1.267]`), el ahorro de `1.05s` sobre el tiempo total de `validate_skill.py` (`~13.8s`, dominado por las pruebas de `ffmpeg` `loudnorm`, `.webm`/`.mov` y `montaje.py pase`) representa solo un `~7.6%` (inferior al umbral del `15%`) y complica la traza secuencial determinista del validador.
- **Decisión**: **DISCARD** (no supera el umbral del 15% en el tiempo total del validador; se alcanza el criterio de parada de 3 ciclos consecutivos explorando oportunidades distintas sin mejoras adicionales aceptables).

- **RESULTADO**:
  - **7a**: `validate_skill.py` pasa de `0` fugas temporales garantizadas mediante `atexit` (`_mkdtemp`), `beat_grid.ajustar_rejilla` soporta entradas vacías o sub-beat sin `TypeError`, `medir_mezcla.py` valida la existencia y el JSON de `--ventanas`, `_comun.py`/`beat_grid.py`/`medir_mezcla.py` normalizan `/opt/homebrew/bin` y `/usr/local/bin` en `PATH` incluso desde subshells mínimos, y se registra el aprendizaje verificado en `references/reglas-tecnicas.md` mediante `registrar_aprendizaje.py`.

---

## Anexo: Registro Histórico Ronda 1 (v1.7.0 — Ciclos 1 a 5 previos)

- **Ciclo 1 (2026-10-16, `7c685a7`)**: Frontmatter YAML válido + campos Claude Skill (`license`, `compatibility`, negative triggers) y paridad AST de conteo de escenas ES/EN.
- **Ciclo 2 (2026-10-16, `862f96f`)**: Arranque limpio inicial de CLIs y fallback determinista `_FontEst` de saltos fijos en `caption.py`.
- **Ciclos 3 y 4 (2026-10-16, `c567c8e`, `297660a`, `a54c94f`)**: 3 primitivas DRY (`tarjeta_cristal`, `boton_halo`, `insignia_3d`), 2 escenas nuevas (`hero`, `bento` → 30 escenas) y suite `test_core_and_scenes.py`.
- **Ciclo 5 (2026-10-16, `d76ce18`)**: Cumplimiento estricto de nombres y estructura según `Skill-for-Claude.txt` (carpeta `editoria/` en `kebab-case == name`, sin `brand/README.md` ni zips internos, bloque `metadata` YAML, secciones canónicas en `SKILL.md` y fix Python 3.9 en `validate_skill.py`).
