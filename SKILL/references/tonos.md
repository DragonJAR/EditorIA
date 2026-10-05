# Tonos: energía creativa de la pieza

Adaptado del sistema de tonos de `/brag` (latent-spaces/brag, CC-BY). Cada tono
cambia energía de guion, ritmo, personalidad tipográfica y estilo de transición.
Los tonos son presets, no límites: una dirección libre del usuario refina o
reemplaza el preset, pero siempre se mapea al más cercano para ritmo y estructura.

Elegir el tono en el brief, antes del guion. El tono manda sobre la técnica:
una pieza "demo técnica" no usa las mismas transiciones que una "parodia".

## Presets

### `demo` — el tono por defecto
**Energía:** técnica, didáctica, entusiasta. La herramienta hace el chiste sola.
**Voz:** segunda persona, directa, sin humo corporativo. Términos en inglés cuando
son identificadores.
**Tipografía:** la de titulares del brand pack (ExtraBold) para titulares; mono para datos y
etiquetas (kickers con tracking amplio). En modo libre, una sans geométrica de peso alto.
**Ritmo:** 4–6 escenas, 3–5 s cada una. Los pasos aparecen uno por uno.
**Hook:** la promesa concreta ("Resume una reunión de 2 horas en 60 segundos").
**Transiciones:** cortes editoriales secos; entradas con resorte.
**SFX:** moderado — clicks en pasos, ding en el resultado.

### `resumen` — resúmenes de comunidad/eventos

> Ejemplo: resúmenes de AI Tinkerers (badges tipo lanyard por ponente).

**Energía:** celebratoria, ritmo alto, postable.
**Voz:** tercera persona plural, cálida. Nombres propios verificados.
**Tipografía:** titulares gigantes; badges por ponente; chips de datos.
**Ritmo:** ~60–95 s para 4–6 bloques de ponente; 8–13 s por bloque (ver `estilos.md`).
**Hook:** número de edición + dato fuerte en los primeros 2 s.
**Transiciones:** cortes secos con SFX; salidas anticipadas.
**SFX:** moderado — pop en cada chip, golpe suave en cada bloque.

### `anuncio`
**Energía:** comercial, pulida, aspiracional.
**Voz:** imperativa suave ("Mira lo que hace").
**Tipografía:** titulares limpios, mucho aire.
**Ritmo:** 3–5 escenas, 4–6 s. Confianza por restricción.
**Hook:** el producto a toda escala o una sola imagen fuerte.
**Transiciones:** crossfade suave (0.6–0.8 s).
**SFX:** mínimo — 2–3 acentos sutiles.

### `trailer`
**Energía:** dramática, escala de cine. El producto tratado como blockbuster.
**Voz:** épica, frases declarativas cortas.
**Tipografía:** ALL CAPS o titulares a pantalla completa, gran escala.
**Ritmo:** 4–5 escenas, 3–5 s. Reveals dramáticos, no cortes rápidos.
**Hook:** una afirmación grande sobre el mundo, dicha en serio.
**Transiciones:** wipe dramático o crossfade lento con escala (0.95→1.0).
**SFX:** 2–3 grandes — campana grave en el hero, golpe en el outro.

### `parodia`
**Energía:** deadpan corporativo aplicado a algo absurdo. El chiste es la
seriedad con que se dice.
**Voz:** seria, objetiva, sin guiños. Lo absurdo viene del tema, no del tono.
**Tipografía:** caja de oración, peso medio/pesado, mono para datos. Sin decoración.
**Ritmo:** 4–5 escenas estructuradas; cada escena, una afirmación.
**Hook:** el problema, dicho completamente en serio.
**Transiciones:** corte duro o crossfade mínimo (0.2 s).
**SFX:** escaso pero presente — un golpe seco por reveal, un acento UI.

### `caos`
**Energía:** rápida, ruidosa, desatada. El video es el chiste.
**Voz:** agresiva. PALABRAS CORTAS. MAYÚSCULAS. Descarga de métricas.
**Tipografía:** ALL CAPS, peso pesado, ligeramente sobredimensionada; alguna
palabra inclinada o más grande de lo esperado.
**Ritmo:** 6–8 escenas; algunas bajo 2 s; nunca más de 4 s por escena.
**Hook:** algo que no debería existir, dicho a todo volumen.
**Transiciones:** corte duro, flash cut (frame blanco/negro breve), zoom cut
(escala 1.2→1.0 en la entrada).
**SFX:** denso — SFX en cada beat, a veces apilados.

## Tabla tono → estructura

| Tono | Escenas | Ritmo | Transición preferida |
|---|---|---|---|
| `demo` | 4–6 | Didáctico, pasos 1×1 | Corte seco, resorte |
| `resumen` | 5–7 | Alto, bloques 8–13 s | Corte seco + SFX |
| `anuncio` | 3–5 | Contenido, holds largos | Crossfade 0.6–0.8 s |
| `trailer` | 4–5 | Dramático, reveals | Wipe / crossfade con escala |
| `parodia` | 4–5 | Estructurado, una afirmación/escena | Corte duro |
| `caos` | 6–8 | Frenético, escenas <4 s | Flash cut / zoom cut |

## Mapeo de dirección libre

Cuando el usuario dé una dirección libre ("hazlo como un lanzamiento de startup
falso", "como un trailer de película"), mapear al preset más cercano para
ritmo y estructura, pero conservar su dirección en el brief y el plan.

## Leyes que cruzan todos los tonos

- **El brand pack manda sobre el preset; sin pack, el brief manda.** Con pack,
  las reglas de marca (cortes editoriales secos,
  sin crossfades decorativos) tienen prioridad sobre la transición preferida
  del tono. El tono aporta energía, ritmo y voz; el pack fija los límites.
- **El hook es todo / cada frame postable.** Ver Leyes creativas en
  `principios.md` (canónico aquí no se repite: el hook se planea primero,
  ningún frame es de relleno).
- **Legible antes que rápido.** El ritmo viene del movimiento y los cortes,
  nunca de retirar texto antes de que se pueda leer (ver piso de lectura en
  `ritmo.md`).
- **Específico.** La pieza debe sentirse hecha para este tema exacto, no para
  cualquier tema.
