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
  renderiza como corte seco con micro-fade de 30 ms.

## Render

```
python scripts/render_plan.py plan.json -o borrador.mp4              # rápido
python scripts/render_plan.py plan.json -o final.mp4 --blur 5 --force  # entrega
```

`--blur N`: motion blur por N sub-frames (obturador `--obturador 0.5` = 180°).
`--jobs N`: procesos en paralelo (default núcleos−1). Sin `--force` retoma
los frames que ya existen.

## Tipos de escena (13)
`apertura` · `canales` · `medianoche` · `chat` · `leads` · `handoff` · `pago` ·
`listo` · `pildoras` · `hoy` · `recupera` · `remate` · `final`

Ver `references/escenas.md` para los parámetros de cada una.
Ver `scripts/render_plan.py` para el renderizador de referencia.
