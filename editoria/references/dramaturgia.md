# Dramaturgia — gancho, hilo y retención

Fuente canónica del **guion** en EditorIA: cómo atrapa la pieza, por qué
cada escena da motivo para seguir, y cómo el viaje llega al final sin
planitud. Las técnicas de craft (hook triple visual, pattern interrupt,
loop seamless) viven en `references/tecnicas-video.md` «Hooks y retención»;
aquí vive el contrato que el agente escribe **antes** de elegir tipos.

El dominio visual sigue en `references/principios.md`. El texto por escena,
en `references/copy.md`. Este archivo es el arco y el hilo.

## 1. Contrato en una frase

**Gancho en los primeros segundos → cada escena deja un motivo para la
siguiente → un solo viaje continuo → payoff que cumple la promesa del
arranque.** Sin eso, el plan es un catálogo de planos, no un guion.

## 2. El gancho (0–3 s)

Se planea **antes** que el resto. Sin gancho deliberado no hay video
(`principios.md`, leyes creativas; checklist L4 en `checklist-qa.md`).

Reglas accionables:

1. **Algo pasa en el frame 0.** Nada de logo lento, fade-in vacío ni
   "hola". Texto o golpe visual desde el primer fotograma (en mute se
   entiende: hoja de gancho en `checklist-qa.md`).
2. **Una promesa, no un índice.** El gancho dice qué va a pasar o qué
   duele; no enumera el menú de la pieza.
3. **Tipo de la familia `gancho`.** La primera escena (la que cubre t≈0)
   sale de la familia de `scripts/data/repertorio.json` → intención
   `gancho` (`apertura`, `hero`, `countdown`, `buscador`, `pildoras`,
   `orbOpen`). Se pide con `repertorio.py sugerir --intenciones gancho,…`.
4. **Copy del gancho.** `texto1`/`texto2` de `apertura` (u homólogo) son
   el golpe, no un párrafo (`escenas.md` §apertura; aritmética en
   `copy.md`).
5. **El auditor lo mira.** `auditar_plan.py` avisa `sin-gancho` si la
   primera escena no es de esa familia o no cubre el arranque.

## 3. Plantillas de arco (elegir UNA antes del plan)

Escribir la elegida en el tratamiento (`proyecto.py` → `TRATAMIENTO.md`)
y bajarla a afirmaciones (`copy.md` §1). No mezclar dos arcos en la misma
pieza.

| Arco | Forma | Cuándo |
|---|---|---|
| **Hook → beats → payoff → CTA** | promesa → una idea por escena → entrega → acción | shorts, ads 15–30 s (default) |
| **PAS** | dolor → agitación → alivio | el dolor es claro y urgente |
| **BAB** | antes → después → puente | transformación / producto |
| **Result-first** | resultado a ~2 s → rebobinar al cómo | demos, proof |
| **Fábula** | marco → deseo → dilema → giro → resonancia | piezas narrativas / festival |
| **Discovery** | setup → tensión → giro → revelación → roadmap | resúmenes con giro real |

Proporciones útiles (ads/shorts): gancho ≤3 s; cuerpo por beats; payoff
antes del CTA; CTA ≥2 s legible. La ventana 8–15 s es la zona de
supervivencia (`tecnicas-video.md`).

### Fábula (detalle)

Para piezas narrativas de EditorIA (lecciones de festivales 2026: Oscar
*The Girl Who Cried Pearls*; Annie *Snow Bear*; Annecy *Paper Trail*):

1. **Marco** (10%): quién cuenta y por qué importa.
2. **Mundo y deseo** (25%): quiere algo simple y visual.
3. **Dilema** (40%): el deseo choca con un costo; mostrar, no explicar.
4. **Giro** (15%): consecuencia no obvia.
5. **Resonancia** (10%): imagen final quieta; la última escena
   recontextualiza la primera.

Traducción a capacidades: paleta corta, tipografía única, un idioma de
movimiento; acabado táctil (`artesanal.py`); narración en off o muda; el
plan declara el arco en el brief **antes** de escribir escenas.

## 4. Hilo conductor — motivo para la siguiente

Una escena sin afirmación es relleno (`copy.md`). Una escena sin **motivo
para seguir** es un corte: el espectador puede irse.

Antes de escribir `plan.json`, en texto plano:

```
Afirmación de la escena N.     -> prueba que la carga
Motivo para la N+1:            -> pregunta abierta / tensión / "falta X"
```

En el plan, cada escena **excepto la última** declara ese puente:

```json
{
  "tipo": "apertura",
  "from": 0, "to": 3,
  "texto1": ["Tu web es el objetivo."],
  "texto2": ["Lo encontramos primero."],
  "siguiente": "falta ver cómo se ve el hallazgo"
}
```

- **`siguiente`**: una línea, en voz del espectador o del argumento
  ("¿y la prueba?", "falta el cómo", "el precio aún no cierra"). No es
  copy en pantalla: es el cable del hilo.
- La **última** escena no lleva `siguiente`: cierra el loop (payoff/CTA
  que cumple exactamente la promesa del gancho — message-match).
- El auditor avisa `sin-motivo-siguiente` si falta en una escena que no
  es la final. Se silencia solo si es deliberado:
  `"tells_ok": ["sin-motivo-siguiente"]`.

### Checklist de hilo (antes de renderizar)

- [ ] El gancho promete algo que el cierre paga (ni más ni menos).
- [ ] Cada escena intermedia responde al `siguiente` de la anterior.
- [ ] Ninguna escena se podría reordenar sin romper el argumento.
- [ ] El viaje es continuo: un solo hilo de voz/argumento, muchas
      respuestas visuales (`formatos.md`, narración).
- [ ] Entre escenas, la columna "cómo se sale" del storyboard no está
      vacía (`brief.md`): es el corte / `transicion` del plan.

## 5. Anti-planitud narrativa

| Síntoma | Arreglo |
|---|---|
| Secuencia de catálogo (gancho → 3 features → testimonio → precio → CTA) | Reordenar por el argumento (`copy.md` §1), no por la plantilla |
| Cada escena "explica" sin tensión | Convertir al menos una en pregunta, contraste o cliffhanger menor |
| Tres escenas intercambiables | Fusionar o dar a cada una un rol distinto del arco |
| El medio se siente inventario | Un open loop a mitad (`tecnicas-video.md`) que el payoff cierra |
| Cierre que no recuerda el arranque | Eco: misma imagen/frase del gancho con nuevo sentido |
| Lista de tips sin escalada | El mejor ítem al final, o arco listicle con payoff |

## 6. Lo que los jurados premiaron (contexto, no menú paralelo)

1. Fábula moral completa con giro (completitud narrativa > técnica sola).
2. Restricción como poder (limitación asumida = estilo).
3. Lo táctil sobre lo pulido.
4. Silencio o narración, no diálogo expositivo.
5. Un solo tema moral/existencial llevado al fondo.

EditorIA **no** promete actuación de personaje, cuadro-a-cuadro ni
stop-motion físico. Sí: motion graphics con alma de fábula, restricción
deliberada y arco completo.

## 7. Comprobación

```bash
python3 scripts/auditar_plan.py plan.json           # sin-gancho, sin-motivo-siguiente, …
python3 scripts/lint_copy.py plan.json              # copy / prueba
python3 scripts/repertorio.py sugerir --intenciones gancho,dato,proceso,cierre
```

Creative gate humano: `checklist-qa.md` L4 (hook + hilo). Técnicas de
retención en feed: `tecnicas-video.md`. Share/viral: `share-copy.md`.

---

→ Canónico: `references/dramaturgia.md` · Dominio: estructura · Vecinos: `references/principios.md`, `references/copy.md`, `references/formatos.md`, `references/tecnicas-video.md`
