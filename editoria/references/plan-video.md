# Plan de video — formato `plan.json`

El plan es la partitura: cada escena declara su tipo, su ventana de tiempo y los
instantes (`at`) en que aparece cada elemento. El renderizador lo ejecuta.

```json
{
  "duracion": 45.5,
  "fondo": "oscuro",
  "escenas": [
    {
      "tipo": "apertura",
      "from": 0, "to": 3.62,
      "texto1": ["¿Gestionar *reservas?*"],
      "texto2": ["Ahora todo", "es *automático!*"],
      "at": { "cambio": 1.44,
              "p1": [0.16, 0.58, 0.78],
              "p2": [1.44, 1.76, 1.86, 2.42, 2.8, 3.04] }
    },
    {
      "tipo": "canales",
      "from": 3.62, "to": 8.55,
      "transicion": "mancha",
      "marca": "TuMarca",
      "rotulo": "Todos tus canales, *una agenda*",
      "canales": [
        {"canal": "whatsapp", "nombre": "Marta Ruiz",
         "texto": "¿Tienen fecha para el sábado?", "at": 4.82}
      ],
      "at": {"marca": 4.26, "junta": 7.25, "rotulo": 7.25}
    }
  ]
}
```

## El modelo antes del dibujo (`datos`)

Las cifras de una pieza se declaran **una vez**, arriba, con su fuente; las
escenas las referencian. Asi ninguna escena puede contradecir a otra, y el
linter (`scripts/lint_copy.py`) avisa si dos escenas dan valores distintos
para la misma etiqueta, si un dato no declara su fuente, o si una escena
pide un dato que el plan no define.

```json
{
  "datos": {
    "servicios":  {"valor": 6,   "fuente": "catálogo comercial 2026"},
    "hallazgos":  {"valor": 1240,"fuente": "escaneo Q3"}
  },
  "escenas": [
    { "tipo": "stats", "cards": [
        {"valor": {"$dato": "servicios"}, "etiqueta": "servicios"},
        {"valor": {"$dato": "hallazgos"}, "etiqueta": "hallazgos"} ] }
  ]
}
```

`{"$dato": "nombre"}` se resuelve al `valor` de ese dato antes de componer.
Si el nombre no existe, el render muere con un mensaje claro (fail-loud).
El bloque `datos` es opcional: una escena puede seguir escribiendo su cifra
a mano (con su `fuente`), pero entonces el linter no puede garantizar que
dos escenas no se contradigan.

## Los SFX del plan (`sfx`)

El plan puede declarar los golpes de sonido de la pieza. Cada cue dice
**qué sonido**, **en qué ancla** cae y **en qué escena** ocurre:

```json
"sfx": [
  {"escena": 1, "ancla": "escena",   "at": 0.15, "sonido": "whoosh", "volumen": 0.7},
  {"escena": 2, "ancla": "palabra",  "palabra": 3, "sonido": "click"},
  {"escena": 3, "ancla": "beat",     "beat": 12,   "sonido": "ding"},
  {"escena": 4, "ancla": "pico",     "pico": 3,    "sonido": "thud"},
  {"escena": 5, "ancla": "absoluta", "t": 12.4,    "sonido": "pop"}
]
```

| ancla | se resuelve a | necesita |
|---|---|---|
| `escena` | `escena.from + at` | nada |
| `absoluta` | `t` en segundos | nada |
| `palabra` | el onset de la palabra M de la voz de esa escena | los tiempos de palabra (`scripts/alinear.py`) |
| `beat` | el beat N de la rejilla musical | la rejilla (`scripts/beat_grid.py --json`) |
| `pico` | el transitorio N de la música | la misma rejilla |

Los sonidos disponibles son los del pack procedural: `click`, `pop`, `drop`,
`whoosh`, `ding`, `thud`, `tick`, `swell` (`scripts/sfx.py`).

Densidad: **entre 8 y 12 cues por minuto**. Menos suena vacío; más, saturado.
El ensamblado lo hace `scripts/mezclar_audio.py`, que coloca cada efecto en su
instante y lo mezcla con la voz y la música (la música se baja bajo la voz).

## Reglas del formato
- Tiempos en **segundos absolutos** del video (no relativos a la escena).
- `*texto*` = énfasis (se renderiza en color acento).
- `at` puede ser número, lista de números o dict según la escena.
- **`at` es opcional**: lo que falte se toma de la muestra de esa escena
  (`scripts/escenas_muestra.json`) escalado a su duración. El agente escribe
  contenido; la coreografía tiene un default con oficio. Fijar `at` solo para
  sincronizar con la voz o el beat.
- Campos decorativos opcionales (`rotulo`, `fecha`, `detalle`, `nota`, `temp`,
  `hace`, `lema`, `boton`, `total`; `iniciales` sale del nombre). Si falta
  contenido esencial, el render falla en < 1 s diciendo escena, campo y un
  ejemplo completo para copiar.
- `"transicion": "mancha"` = barrido orgánico al entrar la escena.
- **Cifras**: `"numeros": "es"` (1.240 · 4,8), `"en"` (default: 1,240 · 4.8),
  `"fr"` o `{"miles": ".", "decimal": ","}` a nivel de plan: aplica a toda
  cifra animada y a los precios que no fijen los suyos. Público hispano → `"es"`.
- **Voz (estimación)**: `"idioma": "es"|"en"` y `"ritmo_voz": "slow"|"normal"|"fast"`
  a nivel de plan fijan cómo `scripts/auditar_plan.py` estima si cada `voz`
  cabe antes de la voz siguiente (sílabas habladas con cifras expandidas,
  `scripts/speech_estimate.py`). Sin `idioma`, sale de `numeros` o del texto.
  Escribe en `voz` lo que se DICE ("A P I", "dos mil veinticuatro" si importa
  la lectura) y en los campos de texto lo que se VE ("API", "2024").
- **Música (edición al ritmo)**: `"musica": "pista.mp3"` (ruta relativa al
  plan) analiza el tempo (`beat_grid.analizar`: BPM, beat y el «uno» del
  compás) y, en la puerta única del render, lleva cada entrada (`at`) al medio
  beat más cercano y cada corte entre escenas al «uno» del compás (si está a
  ≤ 1 beat; si no, al beat). Con voz en off solo se ajustan las entradas (la
  voz va por los tiempos originales). `"ritmo": false` lo apaga. Sin voz,
  el MP4 sale con esa misma música, recortada al largo del video y normalizada
  a -14 LUFS / -1.5 dBTP (pasa `delivery_check` de Reels y YouTube); con voz,
  la mezcla con ducking es `scripts/musica.py mix`.
  `medir_animacion --plan` imprime la SINCRONÍA: % de entradas en medio beat
  y de cortes en el uno, frente al azar.
- **Subtítulos quemados**: `"subtitulos": true` (o `"subtitulos": "voz.srt"` con la ruta del archivo generado) reserva una banda abajo (12 %
  del alto, sobre la UI de la plataforma): toda escena compone encima y el
  render imprime el `--margin` exacto para `caption.py`. Sin banda, los
  subtítulos pisan fuentes, botones y pies de las escenas. `caption.py` sin
  marca usa la Montserrat empaquetada (la misma de las escenas).
- **Campos mal escritos**: el render y `medir_animacion --plan` avisan de todo
  campo que la escena no lee, con la sugerencia más parecida (`pasos` →
  `items`, `titulo` → `rotulo`): una escena que saldría vacía EN SILENCIO. El
  esquema sale del propio código de cada escena. Comentarios: campos `_algo`.
- **Cabecera de marca**: `"cabecera": {"chip": "CHARLA COMPLETA - youtu.be/...", "marca": "..."}` (opcional) pone el rack arriba del todo: el logo del pack a la izquierda y un chip con la FUENTE a la derecha. Es un global y no una escena porque la banda va en TODOS los fotogramas mientras que una escena ocupa una ventana (y las escenas no se solapan); además, una escena quieta la declara la puerta "congelada". El chip es la **fuente** (de dónde sale el material), **no** la acción: el botón es la acción y va en otra parte. El logo solo sale si la pieza declara `marca` y esa marca es la del pack.
- **Cámara (trayectoria de la pieza)**: `"camara": {"z0": 1.00, "z1": 1.18, "x0": 260, "x1": -260, "flota": 6}` (opcional) declara el recorrido de la cámara de TODA la pieza: la escala (`z0`→`z1`) y el **paneo** (`x0`→`x1`, `y0`→`y1`, en px). El reloj es global: la cámara no se reinicia en cada corte, así que la pieza se lee como una toma continua y no como un montaje.
- **Barra de depleción**: `"deplecion": {"y": 0, "alto": 5, "color": "acento"}`
  (opcional) dibuja una barra pegada al borde superior del lienzo que se
  DEPLETA: empieza al ancho completo y se estrecha hasta cero en el último
  segundo de la pieza (ancho = `W · (1 − t/duración)`, lineal y anclada a la
  izquierda). Es de la PIEZA entera, no de una escena: por eso la declara el
  plan y no una escena (si fuera una escena, la pieza gastaría una escena
  entera en la barra). `color` admite un token (`"acento"`, `"blanco"`,
  `"gris"`, `"negro"`) o un hex (`"#BD1700"`); `y` y `alto` son px. Sin el
  campo, no hay barra: es opt-in y no cambia las piezas existentes.
- `"respira": false` = apaga la respiración de cámara común (push-in lento +
  flotación) en esa escena; útil para una escena que debe quedar clavada
  (un dato que se lee quieto). Sin ese campo toda escena asentada respira.
- Escenas contiguas: el `to` de una = el `from` de la siguiente (la transición
  la maneja el renderizador con la salida anticipada).
- **Marca**: el plan puede declarar `"brand": "brand/dragonjar.json"` (ruta
  absoluta, relativa al directorio actual o a la carpeta de la skill); el
  motor hereda de ahí colores, tipografías, logos y reglas. Sin `"brand"`,
  modo libre: el plan puede declarar `"paleta": "menta"` (catálogo de
  `references/paleta.md`, elegida según el brief) o su propio
  `"acento": "#RRGGBB"` para un tono suelto. Sin ninguno: el respaldo
  neutro (azul frío sin identidad). **La marca manda sobre la paleta.**
- **Logos**: el isotipo/logotipo del pack solo aparece junto al nombre de su
  propia marca (`marca` == `nombre` del pack); nunca acompaña a otro nombre.
- **Presupuesto de "mancha"**: como máximo 2 por pieza (1 si el pack fija
  `transiciones: corte_seco`); `"mancha_max"` lo cambia. El resto se
  renderiza como corte que cruza: la escena saliente termina de irse debajo
  de la entrante (sin frames vacíos) y la entrante arranca con micro-fade de
  30 ms.
- **Repertorio declarado**: el plan puede declarar qué intenciones
  persigue y por qué descarta las demás, contra la única fuente
  intención→escena (`scripts/data/repertorio.json`):
  `"intenciones": ["gancho", "dato", "proceso", "cierre"]` y
  `"no_aplica": {"demostracion": "sin capturas reales", "imagen-texto": "sin foto ni cita"}`.
  La mano se pide con `python scripts/repertorio.py sugerir --intenciones gancho,dato,proceso,cierre --anterior ../pieza-anterior/plan.json`
  y se verifica con `python scripts/repertorio.py cobertura plan.json`.
  Con alguna de las dos claves presentes, el auditor comprueba que cada
  intención declarada tiene escena (`intencion-sin-escena`) y que ninguna
  intención queda ni usada ni declarada (`intencion-olvidada`): lo no
  usado queda explícito, no olvidado. Sin las claves, plan heredado y el
  auditor no inventa el aviso.

## Render

```
python scripts/render_plan.py plan.json -o borrador.mp4              # rápido
python scripts/render_plan.py plan.json -o final.mp4 --blur 5 --force  # entrega
python scripts/render_plan.py plan.json --preview 0,2.5,5  # mirar sin renderizar
```

`--blur N`: motion blur por N sub-frames (obturador `--obturador 0.5` = 180°).
`--jobs N`: procesos en paralelo (default núcleos−1). Sin `--force` retoma
los frames que ya existen.

`--preview 0,2.5,5`: compone SOLO esos instantes (el frame final es una
funcion pura del tiempo, asi que un instante se compone solo) y escribe una
hoja de contactos del plan en `--hoja RUTA` (default: junto al plan, con su
nombre y el sufijo `.preview.jpg`). Es
para mirar el primer cuadro, un plano clave y el ultimo SIN pagar el render
completo: un frame por instante, no los 600 del video. Sin `-o` no hace
falta.

**Tamaño**: `"tamano": "1920x1080"` en el plan (o `--tamano`) para 16:9; la
zona segura pasa a la de YouTube. Default 1080×1920. Las 44 escenas se
componen en los dos formatos (validadas en 9:16 y 16:9 por `validate_skill.py`
y `galeria.py`): los tamaños de letra van en `unidad()` (lado corto), las
pilas se miden con `pila()` y las escenas de lectura en columna (`chat`,
`leads`, `handoff`) se centran a 1080 px de ancho en 16:9. Films de marca:
`--formato 9:16` o `16:9` (`cine.md`).

**Color**: el MP4 sale en BT.709 exacto y etiquetado (el acento del pack se
decodifica tal cual en navegadores y players; ver `reglas-tecnicas.md`).

### Overlay con alfa (lower thirds, títulos, bugs para el editor)

La extensión decide el entregable:

| `-o` | Qué sale | Para |
|---|---|---|
| `.mp4` | H.264 BT.709, con fondo vivo | redes, web |
| `.mov` | ProRes 4444 con alfa, sin fondo | Premiere, DaVinci Resolve, Final Cut |
| `.webm` | VP9 con alfa, sin fondo | OBS (Media Source), Chrome |

Con alfa no hay fondo vivo y el cierre se va por transparencia, no a negro.
Antes de codificar se revisan los frames (vacíos al inicio y al final, nada
pinta el cuadro entero, todo dentro del title-safe 5%) y después se decodifica
un frame del medio para confirmar que el alfa sobrevivió. Uso en cada
herramienta: `modos-produccion.md` ("Overlays con alfa").

### Plantilla × tabla: un plan, N videos (`--datos`)

El plan lleva `{columna}` en cualquier texto; la tabla (CSV, TSV o JSON) trae
una fila por video:

```
python scripts/render_plan.py plan.json --datos ponentes.csv --fila 1 -o "lt_{archivo}.mov"   # verificar UNA
python scripts/render_plan.py plan.json --datos ponentes.csv -o "lt_{archivo}.mov"            # el lote
```

- Un texto que es solo `"{valor}"` toma el valor tipado: un número sigue siendo
  número (y cuenta con `cuenta_up`).
- Fail-loud: si el plan usa una columna que la tabla no tiene, sale con error
  ANTES de renderizar nada (nunca `{nombre}` literal en pantalla).
- `-o` admite `{columna}` para nombrar; si no, se numera `_001`, `_002`…
- El plan resuelto de cada fila queda junto a su video (`*.plan.json`).
- Una variante por variable: en tests A/B, la tabla cambia UNA columna.

## Tipos de escena (44)
`apertura` · `canales` · `medianoche` · `chat` · `leads` · `handoff` · `pago` ·
`listo` · `pildoras` · `hoy` · `recupera` · `remate` · `final` · `bars` ·
`gauge` · `ranking` · `stats` · `timeline` · `quote` · `versus` · `confetti` ·
`typewriter` · `kenburns` · `pasos` · `countdown` · `oferta` · `demo` ·
`rotulo_inferior` · `hero` · `bento` · `buscador` · `notificacion` · `comentario` ·
`pie` · `orbita` · `audiowave` · `index` · `callout` · `orbOpen` · `frase` ·
`constancia` · `cadena` · `cartel` · `camino`

Ver `references/escenas.md` para los parámetros de cada una.
Ver `scripts/render_plan.py` para el renderizador de referencia.

---

→ Canónico: `references/plan-video.md` · Dominio: plan · Vecinos: `references/mapa.md`, `references/escenas.md`, `references/reglas-tecnicas.md`
