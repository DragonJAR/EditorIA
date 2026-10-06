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

### Ciclo 3 — CONSERVADO · medición nueva: sincronía con la música (métrica v1)
- **Hipótesis**: el pedido «animaciones sincronizadas con la música» no se puede
  mejorar sin medirlo. La métrica usa los tiempos REALES del plan (exactos y
  deterministas), no el movimiento detectado (llega unos frames tarde por los
  resortes y distorsionaría): % de entradas a ±1 frame de un medio beat y % de
  cortes en el «uno» del compás. Azar teórico = 2 × (1/fps) / (medio beat).
- **Medida (definida antes)**: separa los casos conocidos (alineado = 100 %,
  azar ≈ teórico), detecta la rejilla de `film/musica_demo.mp3` (100 BPM) y no
  altera nada más.
- **Resultado**: alineado 100 % (5/5 entradas, corte en el uno); azar 25.2 % vs
  teórico 26.7 %; rejilla 100.0 BPM. Corrección durante el ciclo: la métrica y el
  ajuste recorrían el plan distinto (33 vs 34 entradas); ahora comparten
  `beat_sync.mapear_at` (DRY). `"musica"` se resuelve relativa al plan y falla
  fuerte si no existe (MEDIOS, igual que imágenes). Banco 99.35 / 96.9
  idéntico; suite 291 OK (+1 chequeo); bandit LOW 134 → 135 (uso de `random`
  en la calibración; LOW está fuera de los umbrales fijados).
- **Línea base nueva (antes de cualquier ajuste)**: `demo_plan.json` +
  `film/musica_demo.mp3`: entradas en medio beat **11.8 %** (azar 22.2 %),
  cortes en el uno **0 %**. Peor que el azar: hoy la animación ignora la música.

### Ciclo 4 — CONSERVADO · la animación se edita al ritmo de la música
- **Hipótesis**: si el plan declara `"musica"`, ajustar en la puerta única
  (`preparar_escenas`: render, workers y banco) las entradas al medio beat y los
  cortes al «uno» del compás lleva la sincronía muy por encima del azar sin
  costo en la animación. Riesgo previsto: con voz en off, mover cortes
  desfasaría la voz (se ubica por los tiempos originales) → con voz solo
  entradas. `"ritmo": false` lo apaga.
- **Medida (definida antes)**: entradas 11.8 % → ≥ 90 %; cortes 0 % → ≥ 50 %;
  banco del plan ≥ su base (97.6); catálogo y cortes idénticos; suite en verde.
- **Resultado** (`demo_plan` sin voz + `film/musica_demo.mp3`, 100 BPM):

  | | `"ritmo": false` | al ritmo |
  |---|---|---|
  | entradas en medio beat | 11.8 % | **100 %** |
  | cortes en el uno del compás | 0 % | **60 %** |
  | banco del plan | 97.6 | **98.4** |

  Con voz (demo_plan tal cual): entradas 11.8 → 100 %, cortes intactos, banco
  97.6 → 98.9. Catálogo 99.35/96.9 y cortes 99.57 idénticos (no traen música);
  suite 292 OK (+1: «plan con "musica" editado al ritmo»). El 60 % de cortes es
  por diseño: un corte va al «uno» solo si está a ≤ 1 beat (no se deforman las
  duraciones); si no, al beat.
- **Ajuste dentro del ciclo**: ruff subió 346 → 348 por un import doble y un
  `if` en una línea míos; corregido (346 = base). Cambio solo sintáctico:
  verificado con el escenario de sincronía (mismo 100 % / 60 % / 98.4), sin
  repetir la suite completa.
- **Proceso**: medir el criterio de cortes exigió un plan sin voz; los criterios
  de éxito deben declarar de qué plan dependen.

### Ciclo 5 — CONSERVADO · el entregable lleva la música con la que se editó
- **Hipótesis**: con `"musica"` el render salía MUDO: la sincronía del ciclo 4 no
  se oía hasta mezclar a mano. Si el plan no tiene voz ni es overlay con alfa,
  el render mezcla esa música (reutiliza `musica.mix_music_only`).
- **Medida (definida antes)**: el MP4 tiene audio; audio = video ±0.05 s; pasa
  `delivery_check` (loudness y true peak); imagen idéntica bit a bit; sin
  temporales.
- **Iteraciones dentro del ciclo** (cada una por un criterio medido en falla):
  1. mezcla sola: −18.1 LUFS → falla loudness. Se extrae `loudness.normalizar()`
     de la CLI (una implementación para CLI y render) y se normaliza a −14.
  2. audio 30.1 s vs video 30.0 s (loudnorm + AAC) y true peak −1.0 justo en el
     límite → `normalizar(duracion=…)` recorta el audio; techo −1.5 dBTP.
  3. ruff +1 (dos sentencias en una línea, mía) → corregido; 346 = base.
- **Resultado** (`demo_plan` sin voz + `musica_demo`): audio 30.000 = video
  30.000; −13.9 LUFS / −1.5 dBTP: **Reels PASS, YouTube PASS**; MD5 del stream de
  video idéntico al de los mismos frames sin audio; sin temporales. Suite 293 OK
  (+1: render real con música → audio del largo del video y −14.5 LUFS ±1);
  banco 99.35/96.9 idéntico; bandit LOW 135 → 138 (subprocesos en la suite; LOW
  fuera de umbral); docstrings 53.9 → 54.0. `musica.py` ya no importa `requests`
  al cargar (solo `gen` usa la red).
- **Proceso**: comparar ruff contra la línea base REAL (346), no contra la
  medición intermedia del ciclo anterior (348, tomada antes de su corrección).

### Ciclo 6 — DESCARTADO (revertido) · rendimiento: transformar solo la caja con contenido
- **Perfil (antes de la hipótesis)**: 90 frames de `demo_plan` con cProfile:
  `encajar()` → `Image.transform` = 12.2 s de 17.1 s (**72 %** del costo del
  frame): la respiración de cámara transforma el lienzo entero aunque la capa
  es casi toda transparente.
- **Hipótesis**: transformar solo el rectángulo con contenido (alfa, mapeado a
  la salida + 3 px de soporte bicúbico) da la misma imagen mucho más rápido.
- **Medida (definida antes)**: mediana de 3 renders ≥ 4 % más rápida;
  diferencia de imagen ≤ 1 nivel por píxel; banco ±0.05.
- **Resultado**:
  - velocidad: 151.05 s → **124.52 s (−17.6 %)**, dispersión 3.2 %; los 3 MP4
    idénticos entre sí (determinista).
  - capa (336 casos, 28 escenas × 2 formatos): alfa idéntico; RGB difiere hasta
    12 solo en píxeles con alfa 0 (invisibles); compuesta sobre fondo: ≤ 1.
  - frames PNG del render (antes de codificar): 47 de 900 distintos, **máx 2
    niveles** (6 píxeles de 1 frame); en el MP4 el H.264 lo amplifica a 78 en
    puntos aislados (PSNR 56.1 dB).
- **Decisión**: el criterio fijado era ≤ 1 nivel y el resultado es 2. Causa:
  redondeo de punto flotante al reagrupar los coeficientes de la afín (no se
  puede hacer exacto). No se cambia la tolerancia después de ver el dato →
  **revertido** (solo `encajar`). Queda como **decisión pendiente del autor**:
  si acepta «≤ 2 niveles / PSNR ≥ 50 dB» como tolerancia, se reaplica con ese
  criterio declarado de antemano.
- **Proceso**: para cambios de rendimiento en el render, declarar la
  tolerancia de imagen en términos de lo visible (PNG pre-codificación, PSNR)
  y no solo «bit a bit/≤1», porque el reordenamiento de flotantes es inevitable.
