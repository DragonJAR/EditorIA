# Auto-mejora de la skill (protocolo)

Cada proyecto debe dejar la skill mejor de lo que la encontró. Este protocolo
define QUÉ capturar, DÓNDE y CÓMO — sin duplicar, sin burocracia, sin
corazonadas.

## 1. Criterio de captura (las 4 condiciones, todas obligatorias)

1. **Real**: resolvió un problema que apareció en un build verdadero, no hipotético.
2. **Repetible**: sirve para otros videos y briefs, no solo para este proyecto.
3. **Verificado**: observado en un render, comando o frame real. Evidencia, no teoría.
4. **Nuevo**: no existe ya en la skill (buscar antes en `reglas-tecnicas.md`
   y en la referencia del dominio).

Si falla alguna condición, no se documenta. Un hack de un solo uso no es
un aprendizaje; una corazonada sin evidencia no es un hecho.

## 2. Dónde va (una sola ubicación canónica — DRY)

| Tipo de aprendizaje | Destino |
|---|---|
| Hecho técnico puntual (comando, flag, trampa, número) | `references/reglas-tecnicas.md` (log fechado) |
| Doctrina que toca un pilar de `principios.md` | `references/principios.md` |
| Específico de un dominio (audio, ritmo, marca, cine...) | la referencia del dominio; si es transversal, enlace desde `reglas-tecnicas.md` |
| Referencia nueva (un archivo que no existía) | el dominio que le toque en `references/mapa.md`, con su pie de enlace |

El contenido vive en UN solo lugar; los demás enlazan, nunca copian.
Si dudas entre dos destinos, elige el más específico y enlaza desde el general.

Una referencia nueva sin enlazar convierte la skill en un archon: el pie
(`→ Canónico: ... · Dominio: ... · Vecinos: ...`) y su fila en el mapa son
obligatorios, y `scripts/auditar_mapa.py` lo verifica.

## 3. Cómo registrar (eficiente: un comando)

```bash
python scripts/registrar_aprendizaje.py --titulo "Que aprendimos" --detalle "Lo que se vio y por que" \
    --destino reglas
```

`--destino` acepta `reglas` (por defecto), `principios` o `ref` — este
último necesita `--ref` con el nombre del archivo de referencia (sin `.md`).

El script:

- Anexa la entrada con la fecha de hoy en el formato canónico.
- Busca duplicados por similitud antes de escribir; si encuentra un candidato,
  aborta salvo `--forzar` (el agente decide si es matiz nuevo o duplicado).
- Rechaza angle brackets (los prohíbe el validador) y entradas vacías.
- `--dry-run` muestra la entrada sin escribir (útil para revisar redacción).

Formato canónico:

`- YYYY-MM-DD · **Título corto**: detalle verificable con números, comandos o rutas reales.`

## 4. Cierre del loop (confiable)

- Después de registrar: `python scripts/validate_skill.py` debe seguir en
  `SKILL VALIDO`. Si rompe, el registro está mal hecho, no el validador.
- Ese validador incluye el **chequeo de islas**: toda referencia nueva tiene
  que ser alcanzable desde `SKILL.md`, llevar su pie y entrar en el mapa.
- Si el aprendizaje cambia el comportamiento de un script, el cambio va en el
  script, no solo en la documentación.
- Si el aprendizaje corrige una regla existente, se edita la regla en su lugar;
  no se apila una contradicción encima.
- Al reempaquetar el ZIP, lo aprendido viaja dentro.

## Anti-patrones

- Documentar corazonadas sin evidencia.
- Duplicar la misma regla en dos referencias con palabras distintas.
- Dejar pudrir: un aprendizaje que ya no aplica se elimina o se marca
  `SUPERSEDED`, no se conserva como verdad.
- Registrar por registrar: un aprendizaje sólido vale más que cinco obviedades.
- Reescribir archivos enteros para un aprendizaje de una línea: se anexa la
  entrada, nada más.

---

→ Canónico: `references/instalacion.md` · Dominio: operacion · Vecinos: `references/lecciones-produccion.md`, `references/auto-qa.md`, `references/mapa.md`
