# Dramaturgia del corto — lo que premian los festivales

Lecciones de los ganadores 2026 (Oscar: *The Girl Who Cried Pearls*;
Annie: *Snow Bear*; Annecy: *Paper Trail*). No es una receta para copiar
estilos — es la estructura dramática que los jurados premian, adaptada a
lo que EditorIA sí puede generar.

## Lo que los jurados premiaron en 2026

1. **Fábula moral completa con giro**: una historia autocontenida con
   planteamiento, dilema y resolución con twist (*Pearls*: amor vs. fortuna).
   El jurado premia la *completitud narrativa*, no la técnica por sí sola.
2. **Restricción como poder**: caras estáticas que actúan con gesto (*Pearls*),
   11.000 dibujos de un solo autor (*Snow Bear*), 2D + objetos (*Paper Trail*).
   La limitación visible y asumida se lee como *estilo*, no como carencia.
3. **Lo táctil sobre lo pulido**: grano, materiales reales, imperfección
   deliberada. El acabado digital perfectamente limpio es lo que *no* ganó.
4. **Silencio o narración, no diálogo expositivo**: tres de los premiados son
   sin diálogo; *Pearls* usa narración enmarcada, no conversaciones.
5. **Tema moral o existencial simple**: codicia vs. amor, soledad, duelo,
   una vida vista en papeles. Una sola idea, llevada hasta el fondo.

## Estructura de fábula (para piezas narrativas de EditorIA)

1. **Marco** (10%): quién cuenta y por qué importa (narración en off).
2. **Mundo y deseo** (25%): el protagonista quiere algo simple y visual.
3. **Dilema** (40%): el deseo choca con un costo moral. Mostrar, no explicar.
4. **Giro** (15%): la elección tiene una consecuencia no obvia.
5. **Resonancia** (10%): imagen final quieta que deja la idea flotando.

## Traducción a las capacidades de EditorIA

| Principio del jurado | Implementación en EditorIA |
|---|---|
| Restricción como estilo | Paleta de 2–3 colores, una sola tipografía, un solo tipo de movimiento por pieza |
| Lo táctil | `scripts/ffmpeg_tools/artesanal.py` (grano, papel, parpadeo) sobre el render limpio |
| Sin diálogo expositivo | Narración en off (`voz_off.py`) o pieza muda con música; el texto en pantalla nombra, no explica |
| Fábula completa | El plan declara arco (marco→deseo→dilema→giro→resonancia) en el brief antes de escribir escenas |
| Giro final | La última escena recontextualiza la primera (misma imagen, nuevo sentido) |

## Lo que EditorIA NO puede prometer (honestidad)

- Animación de personajes con actuación (caminar, gesticular, lip-sync):
  no hay rigs de personaje. Lo más cercano: marioneta digital simple
  (propuesta a futuro, no implementada).
- Dibujo cuadro por cuadro estilo *Snow Bear* / *Butterfly*: 11.000 dibujos
  los hace una mano humana, no un script.
- Stop-motion físico: requiere set, muñecos y años.

Lo que SÍ puede: piezas gráficas con alma de fábula — motion graphics con
restricción deliberada, acabado táctil y estructura dramática completa.
Ese es el carril donde puede competir.
