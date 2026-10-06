# RSI_LOG — mejora recursiva de EditorIA

Registro del proceso de mejora recursiva (RSI) sobre la skill. Cada ciclo:
hipótesis → una intervención pequeña y reversible → medición definida ANTES →
validación completa → se conserva (commit propio) o se revierte (y se anota).

## 1. Alcance y restricciones

- **Proyecto**: skill de edición y creación de video con agentes (Python +
  PIL + ffmpeg). Código en `SKILL/scripts/` (44 módulos, ~11.4 k líneas),
  documentación en `SKILL/references/` y `SKILL/SKILL.md`.
- **Instrucciones del repositorio**: no hay CLAUDE.md/AGENTS.md/CONTRIBUTING.
  `.gitignore` es una lista blanca: solo `SKILL/` y los dos README van al
  repositorio (por eso este registro vive en `SKILL/metricas/`).
- **Restricciones del autor**: autoría única de Jaime Andrés Restrepo, sin
  atribuciones de terceros en commits ni archivos; todo funciona en 9:16 y
  16:9; marca blanca (ninguna identidad de marca sin pedirla); DRY.
- **Cambios locales preexistentes**: ninguno (árbol limpio en `e70fe4a`,
  referencia `v1.5.0`). Trabajo a medio camino: `beat_sync.sincronizar_escenas`
  existe pero `render_plan` aún no lo usa (pedido del usuario: animación
  sincronizada con la música).
- **Fuera de alcance sin aprobación**: CI en `.github/` (lo excluye la lista
  blanca), borrar ramas o etiquetas remotas (el proxy de la sesión lo
  rechaza: HTTP 403), cambios de formato del plan que rompan planes viejos.

## 2. Proyectos de referencia (verificados en sus repositorios)

| Proyecto | Objetivo comparable | Criterio aplicable (no se copia la decisión) |
|---|---|---|
| MoviePy (github.com/Zulko/moviepy) | edición de video en Python | suite automática en CI y **cobertura medida** (Coveralls) |
| auto-editor (github.com/WyattBlue/auto-editor) | edición automática por análisis de audio | **umbrales explícitos y configurables** (`--edit audio:threshold=0.04`), documentados |
| Remotion (github.com/remotion-dev/remotion) | video programático | **documentación para agentes** (Agent Skills) y render determinista |

Aplicación: medir cobertura (nunca se había medido); mantener los umbrales del
banco explícitos y versionados; el render ya es determinista (se verifica
repitiendo el banco). CI queda como decisión pendiente del autor.

## 3. Entorno

Linux, Python 3.11.15, ffmpeg 6.1.1, 4 núcleos, 15 GB RAM. Instrumentos
instalados solo en el entorno (no son dependencias de la skill): coverage
7.16.2, ruff 0.16.10, bandit 1.9.4, radon 6.0.1.

## 4. Comandos de la línea base (reproducibles)

```
python3 SKILL/metricas/rsi_metricas.py --json base.json        # estáticas (instrumento v1)
python3 SKILL/scripts/validate_skill.py                        # suite de validación (tests)
COVERAGE_PROCESS_START=.coveragerc coverage run SKILL/scripts/validate_skill.py   # cobertura (+ subprocesos)
python3 SKILL/scripts/medir_animacion.py                       # banco de animación (28 escenas × 2 formatos)
python3 SKILL/scripts/medir_animacion.py --cortes              # 27 cortes × 2 formatos
python3 SKILL/scripts/galeria.py -o /tmp/g                     # 83 piezas reales + auto_qa
```

## 5. Línea base (commit e70fe4a)

| Métrica | Valor | Nota |
|---|---|---|
| Compilación | 44/44 | |
| Suite de validación | SKILL VALIDO, 290 OK, 0 FAIL | |
| Lint (ruff `--isolated`, E4/E7/E9/F) | 346; **F (errores lógicos) = 0** | E701/E702 (210+101) = estilo compacto deliberado del repo |
| Seguridad (bandit) | HIGH 1 (B324), MEDIUM 1 (B306), LOW 134 | |
| Complejidad (radon cc) | media 6.72, máx 96, 26 funciones > 20 | |
| Mantenibilidad (radon mi) | media 47.7, 4 módulos rango C | |
| Duplicación (bloques de 6 líneas) | 46 bloques, 0.42 % | |
| Docstrings de funciones públicas | 53.6 % de 379 | |
| Banco de animación | 99.35 (mínima 96.9), 0 pops, 0 tirones | determinista |
| Cortes | 99.57 (mínima 93.8) | |
| Galería real | 83/83 PASS | |
| Cobertura (suite + subprocesos) | **52 %** (8 693 sentencias) | render_plan 90 %, validate_skill 89 %; delivery_check 19 %, scenes 19 %, check_env 0 % |
| Rendimiento (`demo_plan.json`, 30 s 9:16) | mediana **151.05 s**, dispersión 1.3 % | 3 MP4 **idénticos bit a bit** (md5): render determinista verificado |
| Sincronía con la música | **no evaluado** | no existe aún la métrica |

## 6. Umbrales de aceptación (fijados antes del primer ciclo)

Obligatorio en verde en cada ciclo: suite SKILL VALIDO (0 FAIL), 44/44
compilan, ruff F = 0. Un cambio se conserva solo si mejora su métrica objetivo
y además:

- banco ≥ 99.35 − 0.05 y mínima ≥ 96.9, pops 0, tirones 0; cortes ≥ 99.57 − 0.05;
- bandit HIGH/MEDIUM no sube; complejidad máxima no sube; duplicación ≤ +0.10 pp;
- docstrings no baja; cobertura no baja más de 0.5 pp;
- rendimiento: mediana de 3 renders no empeora más de 10 %; una MEJORA de
  rendimiento solo cuenta si supera 4 % (≈ 3 × la dispersión medida, 1.3 %).

## 7. Presupuesto

Máximo 10 ciclos; ≤ 6 h de cómputo; ≤ 14 corridas completas de la suite; una
galería completa al final. Se detiene antes si 3 ciclos consecutivos que
exploran oportunidades distintas no encuentran mejoras aceptables.

## 8. Ciclos

### Ciclo 1 — CONSERVADO · seguridad: MD5 de caché declarado como no criptográfico
- **Hipótesis**: `voz_off.cache_path` usa MD5 como clave de caché; declararlo con
  `usedforsecurity=False` elimina el único hallazgo HIGH sin cambiar el comportamiento.
- **Medida (definida antes)**: bandit HIGH 1 → 0; digest idéntico antes/después
  (las cachés existentes siguen sirviendo); suite en verde.
- **Resultado**: HIGH 1 → 0; digest idéntico (`diff` vacío); 44/44, ruff 346 = 346,
  complejidad, duplicación y docstrings iguales; suite SKILL VALIDO 290 OK.
  Banco no corrido: `voz_off` no lo importa ni el render ni el banco (grep vacío).
- **Proceso**: la validación de un cambio que no toca el render puede omitir el
  banco si se demuestra (grep) que no hay dependencia; se registra la razón.

### Ciclo 2 — CONSERVADO · seguridad: archivo temporal sin carrera en la suite
- **Hipótesis**: `tempfile.mktemp` (validate_skill, smoke de shorts_plan) solo
  devuelve un nombre: carrera CWE-377. Una carpeta privada (`mkdtemp`) la elimina.
- **Medida (definida antes)**: bandit MEDIUM 1 → 0; el chequeo afectado sigue
  probando lo mismo y en verde; suite en verde.
- **Resultado**: MEDIUM 1 → 0 (bandit medio/alto total: 2 → 0); «shorts_plan:
  retimea SRT al timeline de salida» OK; demás métricas iguales; SKILL VALIDO 290 OK.
  Banco no corrido: solo cambia la suite, no el render.
