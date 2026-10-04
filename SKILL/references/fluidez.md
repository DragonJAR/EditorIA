# Fluidez — principio supremo (mandato de Jaime, 2026-10-03)

"Todo debe ser muy fluido." Nada en un video de EditorIA se queda quieto sin
propósito, ningún corte es brusco o accidental, ninguna entrada es lineal.
(El idioma de transición lo fija el brand pack o el tono — ver
`references/brand-packs.md`; la fluidez manda en entradas, salidas y
transiciones *dentro* de la escena.)

## Motor de movimiento
- **Resortes, no lineales**: toda entrada usa física de resorte (stiffness/damping)
  o `easeOutBack` (overshoot). Lo lineal se siente robótico; el resorte se siente vivo.
- **easeInOutCubic** para desplazamientos largos; **easeOutCubic** para apariciones.
- **Overshoot con medida**: un solo rebote; techo general 8% del tamaño,
  hasta 10% solo en el elemento focal de piezas de alta energía.
  (Canónico aquí; `tecnicas-video.md` lo referencia.)
- **Nada aparece de golpe**: fade + escala 0.9→1.0 + elevación, mínimo 0.35s.

## Continuidad
- **Fondo vivo**: el mundo de fondo (blobs de color, partículas, ondas) se mueve
  SIEMPRE, aunque sea lento. Un fondo congelado mata la fluidez. Sin rejillas
  ni líneas geométricas decorativas (ver `coherencia-espacial.md`; el brand
  pack puede habilitarlas si la marca las pide).
- **Transiciones**: el idioma de transición lo fija el brand pack o el tono de
  la pieza (ver `references/brand-packs.md`; ej. DragonJAR: corte seco por
  defecto entre escenas). La transición orgánica ("mancha": un blob que crece con un
  agujero y barre la pantalla) es opt-in y motivada — 1 o 2 por pieza como
  máximo, nunca como costura por defecto. La fluidez manda en entradas,
  salidas y transiciones *dentro* de la escena; la costura *entre* escenas
  la fija el idioma de transición elegido.
- **Salidas con anticipación**: cada escena empieza su salida 0.5s antes del fin
  (fade + deriva), la siguiente ya está entrando.
- **Objetos de ambiente**: 2-4 elementos sutiles con deriva lenta y rotación
  mínima durante toda la escena (atmósfera, no decoración gratuita).

## Ritmo
- Los tiempos `at:{}` del plan anclan cada elemento a la palabra que se oye
  (o al beat). La animación respira con el contenido, no con un metrónomo.
- Densidad: un evento de movimiento cada 0.8-1.5s. Más rápido abruma, más lento
  aburre. Ojo: densidad de *movimiento*, no de *elementos* — un elemento nuevo
  cada segundo es saturación, no dinamismo. El dinamismo es que los pocos
  elementos presentes estén vivos y armoniosos (ver "Saturación" en
  `principios.md`).

## Personalidad → parámetros (tabla de tokens)

Para derivar los parámetros del motor de resortes en vez de elegirlos por
gusto. Ejes: energía (baja/alta) × tono (serio/lúdico). Leer la personalidad
de la pieza (y del brief del usuario) y aplicar la columna correspondiente.

| Parámetro | Baja + serio (premium/institucional) | Baja + lúdico (cálido/acogedor) | Alta + serio (fintech/enterprise) | Alta + lúdico (deporte/startup) |
|---|---|---|---|---|
| Duración | 1600ms | 1400ms | 700ms | 600–900ms |
| Anticipación | 50–100ms | 100–150ms | 150–200ms | 200–300ms |
| Overshoot | 1.0–1.02 | 1.0 | 1.0 | 1.08–1.10 |
| Squash & stretch | 0% | 4–8% | 0% | 18–40% |
| Easing de entrada | ease-in-out simétrico | ease-in-out suave | ease-out confiado | easeOutExpo `cubic-bezier(0.16,1,0.3,1)` u overshoot `cubic-bezier(0.34,1.56,0.64,1)` |
| Follow-through | settle suave extendido | settle suave | aterriza exacto | bounce rápido |

Leer el brief antes de parametrizar: "institucional" = columna baja+serio;
"energético" = alta+lúdico. Los números del spring (stiffness/damping) se
ajustan para aproximar la duración y el overshoot de la columna.

## Verificación
En el QA, mirar el video a 0.5x: cualquier salto, aparición brusca o fondo
congelado es un defecto que se corrige antes de entregar.
