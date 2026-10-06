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

## Reglas del formato
- Tiempos en **segundos absolutos** del video (no relativos a la escena).
- `*texto*` = énfasis (se renderiza en color acento).
- `at` puede ser número, lista de números o dict según la escena.
- `"transicion": "mancha"` = barrido orgánico al entrar la escena.
- Escenas contiguas: el `to` de una = el `from` de la siguiente (la transición
  la maneja el renderizador con la salida anticipada).
- **Marca**: el plan puede declarar `"brand": "brand/dragonjar.json"` (ruta
  absoluta, relativa al directorio actual o a la carpeta de la skill); el
  motor hereda de ahí colores, tipografías, logos y reglas. Sin `"brand"`,
  modo libre: acento neutro y fuentes empaquetadas; el plan puede fijar su
  propio `"acento": "#RRGGBB"`.
- **Logos**: el isotipo/logotipo del pack solo aparece junto al nombre de su
  propia marca (`marca` == `nombre` del pack); nunca acompaña a otro nombre.
- **Presupuesto de "mancha"**: como máximo 2 por pieza (1 si el pack fija
  `transiciones: corte_seco`); `"mancha_max"` lo cambia. El resto se
  renderiza como corte que cruza: la escena saliente termina de irse debajo
  de la entrante (sin frames vacíos) y la entrante arranca con micro-fade de
  30 ms.

## Render

```
python scripts/render_plan.py plan.json -o borrador.mp4              # rápido
python scripts/render_plan.py plan.json -o final.mp4 --blur 5 --force  # entrega
```

`--blur N`: motion blur por N sub-frames (obturador `--obturador 0.5` = 180°).
`--jobs N`: procesos en paralelo (default núcleos−1). Sin `--force` retoma
los frames que ya existen.

**Tamaño**: `"tamano": "1920x1080"` en el plan (o `--tamano`) para 16:9; la
zona segura pasa a la de YouTube. Default 1080×1920. Las 28 escenas se
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

## Tipos de escena (28)
`apertura` · `canales` · `medianoche` · `chat` · `leads` · `handoff` · `pago` ·
`listo` · `pildoras` · `hoy` · `recupera` · `remate` · `final` · `bars` ·
`gauge` · `ranking` · `stats` · `timeline` · `quote` · `versus` · `confetti` ·
`typewriter` · `kenburns` · `pasos` · `countdown` · `oferta` · `demo` ·
`rotulo_inferior`

Ver `references/escenas.md` para los parámetros de cada una.
Ver `scripts/render_plan.py` para el renderizador de referencia.
