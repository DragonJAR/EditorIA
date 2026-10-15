# RSI (Recursive Self-Improvement) — EditorIA v1.5.0

## Alcance (scope)

- **Proyecto**: EditorIA — skill de edición de video con IA (28 escenas, 44 scripts Python, 45 referencias, marca-blanca con pack DragonJAR de ejemplo).
- **Tecnologías**: Python 3.9+, PIL/Pillow, ffmpeg, NumPy, ElevenLabs API; opcional Remotion/Node, HyperFrames.
- **Tamaño**: ~107 archivos tracked en git (rama `main`); SKILL.md ~260 líneas; 45 references; 25 scripts raíz + 19 en ffmpeg_tools/.
- **Estado actual**: working tree limpio, sincronizado con `origin/main` (HEAD = `c6454e3`). Versión documentada 1.5.0.
- **Lo que NO toco**: trabajo ajeno, la arquitectura marca-blanca, el API de scripts, el JSON schema de plan.json/shorts-plan.json, los IDs de las 28 escenas, el catálogo de primitivas DRY.

## Entorno (env)

- OS: macOS
- Python: 3.14.8 (homebrew)
- Git: 2.x
- ffmpeg: instalado
- node/npx: v26.10.0
- Skills en sesión: writing-plans, systematic-debugging, skill-improver, work-unit-commits, etc.

## Comandos de referencia (commands)

```bash
# Validación completa (tarda ~5 min — 28/28 escenas + muchas otras)
python3 SKILL/scripts/validate_skill.py > /tmp/val.log 2>&1

# Inventario
ls SKILL/scripts/*.py | wc -l                # 25
ls SKILL/scripts/ffmpeg_tools/*.py | wc -l   # 19
ls SKILL/references/*.md | wc -l             # 45
ls SKILL/brand/*.json | wc -l                # 1

# Compilación
python3 -m py_compile SKILL/scripts/*.py SKILL/scripts/ffmpeg_tools/*.py 2>&1 | head

# Deuda técnica
grep -c "TODO\|FIXME\|XXX" SKILL/scripts/*.py SKILL/scripts/ffmpeg_tools/*.py 2>/dev/null

# DRY score (reuso de _comun.py)
grep -rn "from _comun import" SKILL/scripts/ 2>/dev/null | wc -l
```

## Línea base reproducible (baseline) — Ciclo 0

- **Validator**: SKILL VALIDO (0 FALLO, 28/28 escenas, exit 0)
- **Tiempo de validator**: ~5 min (medido)
- **Python compilation**: pendiente verificar
- **TODOs en código**: pendiente cuantificar
- **DRY score**: pendiente
- **Seguridad**: ya auditada en turno anterior — 0 secretos, 0 paths absolutos, 0 emails personales, .gitignore estricto (whitelist SKILL/ + READMEs)
- **Documentación**: 45 references + 2 READMEs enriquecidos + SKILL.md con Language Rule
- **Métricas específicas del dominio**: 28 escenas, 6 primitivas DRY, 12 voces TTS, 0 marcas hardcoded

## Presupuesto (budget)

- **Iteraciones**: 3 ciclos como mínimo. Si encuentro mejora aceptable, sigo. Si 3 ciclos consecutivos sin mejora, paro.
- **Tiempo**: max 30 min de validación activa. Si excede, paro y reporto.
- **Alcance de cambios**: solo `SKILL/scripts/`, `SKILL/references/`, `SKILL/brand/`, `SKILL/SKILL.md`. **NO toco** `SKILL/assets/`, `SKILL/film/`, `README*.md`, `LICENSE`, `.gitignore` (salvo aprobación).

## Criterios de aceptación por ciclo

Una mejora se ACEPTA solo si cumple TODO:
1. **Medible**: produce cambio cuantificable en una métrica baseline.
2. **Reproducible**: ejecutando el mismo comando dos veces se obtiene el mismo resultado.
3. **Sin regresión**: validator pasa antes y después con 0 FALLOs.
4. **Sin daño a otras métricas**: las demás métricas no empeoran fuera de tolerancia (max 5% en score, sin nuevos TODOs).
5. **DRY / Coherent**: no duplica lógica existente, no rompe el principio marca-blanca, no introduce dependencias externas innecesarias.
6. **Reversible**: el cambio se puede revertir con un solo `git checkout`.

## Criterios de NO-mejora

- TODOs en código que documentan bugs conocidos (no son objetivos)
- Tests rotos preexistentes (registrados como "no evaluado")
- Dependencias del entorno (CUDA, ffmpeg) que no se pueden instalar

## Referencias externas

1. **DragonJAR/Android-Pentesting-Skill** — mismo owner, patrón de READMEs
2. **DragonJAR/Skill-Editor-IA** (sistema original) — base histórica
3. **lifeprompt-team/remotion-scenes** + **ali-abassi/remotion-templates** + **reactvideoeditor/remotion-templates** — fuentes MIT de patrones

## Plantilla de ciclo

```markdown
### Ciclo N (YYYY-MM-DD HH:MM)
**Hipótesis**: <una mejora concreta>
**Métrica objetivo**: <qué medir>
**Comando medición pre**: ...
**Cambio**: <1 commit, 1 archivo idealmente, reversible>
**Validación**: ...
**Resultado pre → post**: ...
**Decisión**: KEEP / REVERT
**Notas**: ...
```

## Ciclos
