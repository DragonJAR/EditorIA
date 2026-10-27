# Paleta — el color se elige, no se hereda

> Regla dura: **el brand pack manda solo si el usuario nombró una marca.**
> Sin marca, el agente **elige la paleta según el brief** usando el catálogo
> de este documento y la declara en el plan. Una pieza en modo libre nunca
> debe parecerse a una marca concreta: ni a la del pack de ejemplo.

## 1. Por qué el color se elige y no se hereda

El modo libre no es "DragonJAR con otro nombre". El pack de ejemplo es rojo
(`#C11B05`); si el respaldo del modo libre fuera también rojo, toda pieza
sin marca saldría con la firma visual de una marca que el usuario no pidió.
Por eso el respaldo es un **azul frío sin identidad** y el resto son paletas
del catálogo, elegidas por su armonía.

El color no es decoración: **el acento comunica**. Comunica de qué tema va
la pieza, para quién es y si es urgente o Informativo. Elegirlo a ciegas
(siempre rojo, siempre naranja) hace que todas las piezas se parezcan.

## 2. Las reglas (no negociables)

1. **Un solo color de acento** en toda la pieza. El acento marca lo
   importante: la cifra, el CTA, la palabra acentuada. Nunca decora.
2. **El acento ocupa ~10 % del plano.** Un plano donde todo es acento no
   tiene acento: no hay jerarquía.
3. **El acento nunca es el fondo ni el texto de cuerpo.** El fondo es
   casi negro (`#0A0A0A`) y el texto de cuerpo es casi blanco (`#FAF8F6`).
4. **Contraste mínimo AA**: el texto de acento sobre el fondo tiene que
   llegar a **4.5:1**. Todas las paletas del catálogo lo cumplen (verificado
   en `scripts/_tests/test_paleta.py`); si añades una, compruébalo.
5. **La paleta es de la pieza, no de la escena.** La misma paleta en las
   42 escenas: si el acento cambia a mitad de video, no es una paleta, es
   un descuido.
6. **El tono de acento se deriva del acento** (×0,65) para las sombras y
   bordes: nunca un segundo color libre.

## 3. El catálogo

| Paleta | Acento | Armonía | Temperatura | Para qué brief |
|---|---|---|---|---|
| `electrico` | `#3D7BFF` | análogo azul→cian (214°) | frío | IA, software, datos, B2B, SaaS, ciberseguridad |
| `menta` | `#14C7A0` | análogo verde→turquesa (168°) | frío | finanzas, salud, crecimiento, clima, logística verde |
| `grafito` | `#94A3B8` | monocromático frío, sin chroma | frío | documentación, legal, industria, auditoría, minimal |
| `ambar` | `#F0A32B` | análogo ámbar→dorado (38°) | cálido | energía, industria, deporte, formación, startups |
| `coral` | `#FF6B5B` | análogo coral→rojo cálido (6°) | cálido | salud, RRHH, cuidado, comunidad, alertas |
| `violeta` | `#8B5CF6` | análogo violeta→lila (265°) | frío | creatividad, educación, premium, wellness, música |
| `magenta` | `#E5479B` | análogo magenta→fucsia (330°) | cálido | cultura, moda, entertainment, social, público joven |
| `oro` | `#C9A227` | dividido complementario: dorado 45° | cálido | lujo, premium, invitaciones, joyería, inmobiliaria |

**Respaldo** (cuando el brief no dice nada): el acento neutro `#3D7BFF`
(azul frío). Es el color más neutro y el que menos se parece a una marca;
no es una decisión estética, es la ausencia de decisión, y por eso es
frío y desaturado.

### Por qué estas armonías y no otras

- **Análogo** (vecinos en la rueda): coherencia sin tedio. Es la elección
  por defecto en un video que informa: el acento se relaciona con el
  contenido sin competir con él.
- **Monocromático frío**: cuando el color debe *no* aparecer (legal,
  auditoría, documentación). Un gris azulado sobre negro dice "esto es un
  dato" sin pedir atención.
- **Dividido complementario**: cuando la pieza quiere lujo o un tono
  "premium" sin caer en el dorado brillante de discount.

**Evitar**: lima + morado (es la firma de la "AI tinkerer" y el ojo la
reconoce al instante — ver `references/estilos.md`); y cualquier acento
demasiado cercano al rojo del pack de ejemplo si la pieza no es de esa
marca.

## 4. Cómo se elige (el procedimiento)

1. **¿El usuario nombró una marca?** → el pack manda. No se elige paleta.
   Fin. (El acento del pack también es el de los subtítulos.)
2. **¿El brief dice un tema, sector o tono?** → busca en la columna
   "Para qué brief" el fila que encaja y usa esa paleta.
3. **¿El brief solo dice la emoción?** → temperatura:
   - confianza, tecnología, precisión, calma → **fría** (`electrico`,
     `menta`, `grafito`, `violeta`)
   - energía, urgencia, humano, celebration → **cálida** (`ambar`, `coral`,
     `magenta`, `oro`)
4. **¿Nada de eso?** → el respaldo (`electrico`) y se dice en la entrega
   qué paleta se usó, para que cambiar sea una línea.

El agente **anuncia la paleta elegida** en su respuesta ("paleta: menta,
fría, para salud y crecimiento") y la declara en el plan. Una pieza sin
paleta declarada usa el respaldo.

## 5. Cómo se declara

En el `plan.json` (lo que se guarda con la pieza y lo que se puede revisar):

```json
{"duracion": 30, "paleta": "menta", "escenas": [ ... ]}
```

O en la línea de comandos:

```bash
python3 scripts/render_plan.py plan.json -o out.mp4 --paleta menta
```

Y en los subtítulos, para que el acento de las captions sea el de la pieza:

```bash
python3 scripts/ffmpeg_tools/caption.py video.mp4 --srt subs.srt --paleta menta
```

La paleta llega a **todo lo que pinta con acento** por la misma puerta
(`acento_efectivo` / `tokens_efectivos` en `_comun.py`): el motor
(`render_plan.py`), los subtítulos (`caption.py`), la onda de audio
(`audio_viz.py`) y el thumbnail (`ffmpeg_tools/thumbnail.py`). Las cuatro
aceptan `--brand` y `--paleta` con la misma precedencia, así que la pieza
se ve de un solo color de punta a punta.

**Precedencia, siempre**: `--brand` (o el campo `"brand"` del plan) gana
sobre `--paleta`, que gana sobre el campo `"acento"` (un tono suelto sin
paleta completa), que gana sobre el respaldo.

## 6. Verificación

- `scripts/check_env.py` no toca el color: la paleta es una decisión, no una
  dependencia.
- `scripts/_tests/test_paleta.py` fija el catálogo, comprueba el contraste
  AA de cada acento sobre su fondo y verifica que el respaldo **no** sea
  el mismo color que el pack de ejemplo.
- La puerta de entrega (`scripts/qa_entrega.py`) no juzga el color: la
  coherencia cromática se juzga mirando la pieza (`references/auto-qa.md`).

## Tipografía e iconos: catálogos de referencia

El color es una decisión y esta skill trae su catálogo (`references/paleta.md`
y el brand pack). La **tipografía** y los **iconos** tienen catálogos externos
que no hay que copiar aquí: se nombran, se eligen y se declaran.

- **Pares tipográficos**: `nextlevelbuilder/ui-ux-pro-max-skill` (MIT) trae 74
  pares con su razonamiento. Sirven para **elegir con nombre** la familia de
  display y la de texto, no para mezclarlas: la doctrina sigue siendo *un
  solo sistema tipográfico* (ver `references/principios.md`).
- **Iconos**: el mismo repo trae 105 iconos SVG curados. El motor dibuja
  iconos como SVG con alfa, nunca como emoji ni como Unicode (regla de copy);
  un catálogo evita dibujarlos a mano y mantiene **un trazo y un grosor**
  (ver la regla de los iconos en `references/principios.md`).

Los catálogos externos son **fuente, no copia**: si el proyecto necesita un
icono que no está, se dibuja; no se importa el catálogo entero.

---

→ Canónico: `references/paleta.md` · Dominio: color · Vecinos: `references/principios.md`, `references/brand-packs.md`, `references/plan-video.md`, `references/coherencia-espacial.md`
