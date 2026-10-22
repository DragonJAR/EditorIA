# Auto-QA — el loop cerrado de ver, detectar y corregir

El agente no entrega un video que no haya *mirado*. Este es el protocolo
obligatorio después de cada render, antes de entregar.

## El loop

```
render → auto_qa.py → MIRAR el sheet → confirmar/descartar → corregir →
re-render → auto_qa.py → comparar → entregar
```

1. **Barrido máquina**: `python scripts/auto_qa.py video.mp4`
   Detecta sin visión: frames negros, imagen congelada >1s, flashes,
   silencios largos, clipping. Sale 1 si hay defectos.
2. **Revisión visual** (obligatoria aunque salga 0): abrir el contact sheet
   el contact sheet `video_qa.png` y mirarlo cuadro por cuadro. La máquina no ve texto
   cortado, solapes, ni errores de marca — el agente sí. Con
   `--safe plataforma` (reels, tiktok, shorts…) el sheet dibuja la zona
   segura en cada tile: lo que quede fuera lo tapa la UI.
3. **Confirmar o descartar**: cada defecto máquina se confirma con los ojos
   o se descarta con motivo (ej. fade-out intencional → usar
   `--ignorar-fin` en la siguiente pasada).
4. **Corregir** según la tabla de abajo.
5. **Re-verificar**: re-render + `auto_qa.py` de nuevo. El reporte debe salir
   limpio *y* el sheet debe verse bien.
6. **Documentar**: cada defecto real deja su lección en
   `references/reglas-tecnicas.md`.

## Métricas de animación (antes de renderizar)

`python scripts/medir_animacion.py` mide el catálogo sin codificar (unos
minutos): pops, tirones, tiempo muerto, densidad, letra y zona por escena y
formato, con nota 0–100. Es el banco de la mejora recursiva: toda mejora se
mide contra `metricas/historial.jsonl` y se queda solo si sube la nota sin
romper `validate_skill.py`. Un pop se diagnostica con
`--ver escena:v|h:segundo` (par de frames con los bloques abruptos marcados).
`--plan plan.json` mide un plan entero (cortes incluidos), `--video x.mp4`
cualquier video ya renderizado (a su propio fps) y `--cortes` la ventana de
cada corte entre escenas consecutivas del catálogo (27 pares × 2 formatos):
toda escena se prueba saliendo y entrando contra otra.

Qué mide cada número (calibrado con casos sintéticos en `validate_skill.py`):
- **pop**: en un frame, ≥ 35 % de los bloques que cambian de golpe no tienen
  origen cerca en el frame anterior (ni exacto ni suavizado). Lo que aparece
  deja casi todo sin origen; lo que se mueve o escala, solo su borde. Las
  cifras que cuentan quedan exentas (cambian por diseño).
- **tirones**: un frame quieto entre dos que se mueven (corte o salto de un
  frame) o un frame que se mueve 4× más que sus dos vecinos (teletransporte).
- **muerto**: % del hold con quietud SOSTENIDA (≥ 0.5 s bajo el umbral de
  auto_qa); el punto de giro de una flotación no cuenta.
- **densidad**: eventos de movimiento por segundo en la parte activa (sin la salida común), con umbral relativo al pico propio de la escena (30 %, piso 0.15: la respiración sola no es un evento). Doctrina: 0.5–2.
- **solapes**: textos visibles que se pisan con cada escena asentada (55 % y 80 %), por caja de tinta real; −10 por cada uno (máx. 3). Las métricas de movimiento no ven composición: este sí. Con `--plan` mide los textos REALES del agente, antes de renderizar.
- **letra**: tamaño mínimo de texto **en reposo** (≥ 26 px sobre 1080). En reposo
  = con el tamaño con el que el texto se queda: si un botón entra con resorte y
  pasa por 21 px a mitad de camino, eso es la animación y no la tipografía, así
  que no cuenta. Se toma la mediana ponderada por frames de cada texto.
- **zona**: factor de `escala_segura` (1 = compuesta dentro de la zona segura).
Causas que encontró (y su fix en la primitiva): ease aplicado dos veces
(cursor a 85 px/frame), resorte en barras de datos (rebota por encima del
valor), cifras proporcionales al contar (tiemblan de lado), texto que entra
sin el alfa de su tarjeta, tamaños de letra enteros al escalar (saltos de
1 px), odómetro de 0.25 s con ease_out (saltaba ~100 px/frame).

## Tabla de defectos → causa → fix

| Defecto máquina | Causa probable | Fix |
|---|---|---|
| `black_frame` | escena que termina antes que el video; fade no intencional | revisar `to` de la última escena; `--ignorar-fin` si el fade es intencional |
| `frozen` | fondo sin animación; elemento estático | fondo vivo continuo; la respiración común de `componer` (push-in lento) — si la escena la apaga (`"respira": false`) o mueve su propia cámara, idle/breathing en el elemento |
| `flash` | pop de audio con corte visual; glitch de render | micro-fade 30ms en el corte; re-renderizar el tramo |
| `silencio` | música que no arranca; gap entre segmentos de voz | revisar mezcla; fundidos en `musica.py` |
| `clipping` | mezcla caliente | bajar master; re-medir con `medir_mezcla.py` |
| `fotosensible` | más de 3 destellos en 1 s (WCAG 2.3.1; medido a fps completo, en pantalla o en un cuadrante) | espaciar los flashes a ≥1/3 s, bajar el contraste del destello o achicar su área |
| `sobresalto` | el audio salta >6 dB al entrar un corte (asusta, no edita) | entrar las capas de a una o dos por compás; marcar el corte con armonía, no con volumen |
| `loop` (con `--loop`) | el último frame no empalma con el primero | igualar composición, posición y color del cierre al frame 0 |

Con `--end-screen 15` el sheet dibuja, en los últimos 15 s, las zonas de la
pantalla final de YouTube (marca en el tercio izquierdo, tarjetas a la
derecha): nada propio debe caer bajo las tarjetas.

## Defectos que solo el ojo ve (checklist visual del sheet)

- **Texto cortado** en bordes → auto-fit o centro mal calculado.
- **Solapes** entre elementos → revisar coordenadas en el plan.
- **Marca**: colores/tipos/logos del pack, sin deformar ni rotar.
- **Coherencia espacial**: `references/coherencia-espacial.md`.
- **Ritmo**: si se lee como diapositivas → `scripts/verificar_ritmo.py`.

## Crítica por pasadas (mirar antes de medir)

El barrido máquina dice que no se midió nada roto; no dice que la pieza sea
buena. Esto es cómo se averigua. Se juzga sobre el contact sheet y los frames
reales, nunca sobre el plan: quien escribió el plan lee en él sus intenciones.
**Juzga primero, mide después**: la mirada de diseño va antes del reporte de
detectores, porque la salida determinista ancla el juicio; después se
sintetizan las dos (dónde coinciden, qué atrapó cada una que la otra no, qué
detección es un falso positivo). Cada pasada se hace por separado; no se
mezclan. Método destilado de la crítica de tasteskill (MIT) y de Impeccable
(Apache 2.0).

1. **Un segundo, luego cinco.** Mirar el frame 0 y el de 1 s, apartar la
   vista: ¿qué viste? Debe haber UNA respuesta (una palabra, una imagen, un
   objeto). Si la respuesta es «un video», no hay foco. Luego cinco segundos
   como extraño: ¿sabes qué es, para quién y qué hacer a continuación?
2. **Entrecerrar los ojos.** El plano se reduce a dos o tres masas de tamaños
   claramente distintos. Muchas masas pequeñas parecidas: todo es mediano y
   nada lidera.
3. **Cubrir el logo.** ¿Podría ser de un competidor o de otra industria? Si
   cambiar el nombre y el sustantivo del titular da una pieza igual de válida,
   no tiene idea (vuelve a `SISTEMA.md`). Y avanzando: ¿la idea llega al cierre
   o la pieza se vuelve plantilla tras el primer plano?
4. **Bordes.** Seguir el borde izquierdo de cada bloque de texto a lo largo de
   la pieza: una pieza compuesta tiene dos o tres posiciones x, reutilizadas a
   propósito; seis significan colocación una a una.
5. **Espacio y marco.** Lo relacionado cerca, lo distinto lejos. ¿Hay un hueco
   accidental (junto a una columna corta, bajo algo que se quitó) en lugar de un
   descanso decidido? Márgenes iguales a ambos lados; ninguna escena con el
   texto en una mitad y la otra vacía; ningún tramo vacío de más de la mitad
   del alto. Es lo primero que nombra un espectador («está pegado a un lado»,
   «espacio vacío al azar»).
6. **Tipografía.** ¿Salto decisivo entre texto y titular (3× o más)? ¿Más de
   cinco tamaños? ¿Algún titular con una palabra huérfana? ¿Subtítulos de más de
   dos líneas?
7. **Color.** Nombrar las proporciones: qué color ocupa más superficie, cuál
   apoya, dónde está el acento. Un acento en diez sitios no significa nada; en
   la acción y un detalle significa «aquí».
8. **Imagen.** ¿Hay material real del sujeto? ¿Cada imagen hace un trabajo
   (muestra la cosa, sitúa el lugar, prueba la afirmación)? ¿Mismos recortes y
   un solo tratamiento, o un mix de stock? ¿Algo es una caja gris, una foto
   estirada o un dashboard de barras de relleno?
9. **Igualdad.** Una palabra por escena para su composición (dividida, lista, a
   sangre, cuadrícula, declaración...). La misma palabra dos veces seguidas o
   tres en la pieza es la plantilla asomando (`escena-repetida`).
10. **Teléfono.** Mirar el frame a tamaño de teléfono y dentro de la zona
    segura de la plataforma (`--safe`): ¿composición propia o el 16:9
    apretado? ¿el primer plano sigue siendo una sola cosa clara?
11. **Plenitud.** Pasar los frames de uno en uno: ¿cada uno es un póster
    compuesto o una columna pequeña con suelo muerto a los lados? Una pieza
    austera no es una pieza contenida: si podría confundirse con un wireframe
    sin terminar (formas grises, texto gris, una columna), está incompleta. Un
    único motivo agrandado a toda la pantalla sin nada que leer también es un
    agujero, por audaz que parezca.
12. **Sustancia.** ¿Cada escena que pidió el brief entrega su información
    completa y a tamaño legible? ¿El espectador sale sabiendo lo que venía a
    saber? ¿La acción principal está en pantalla el tiempo suficiente?
13. **Colisiones.** ¿Algo pisa un titular, una cifra o un botón en algún
    instante? ¿Algo se sale del borde?
14. **Competidor y momento firma.** Poner el nombre del competidor más cercano:
    ¿la idea aún funciona? Nombrar el momento firma. Si cualquiera de las dos
    respuestas es débil, es el primer problema de la ronda, antes que cualquier
    detalle.
15. **Pico y final.** Los espectadores recuerdan el punto más intenso y el
    cierre (regla pico-final; el arco y la resonancia final, en `dramaturgia.md`):
    ¿hay un pico recordable y un final que se sostiene como imagen? ¿Hay
    valles emocionales sin consuelo?

Una pieza más rica con recursos de plantilla le ganó siempre, en las pruebas
ciegas de tasteskill con páginas web, a una más limpia pero delgada: las
pasadas 11-13 son donde se comprueba que la pieza no perdió su sustancia al
perder sus tells (`direccion-de-arte.md`).

**Escribir la crítica**, no solo pensarla, con esta forma para poder comparar
rondas:

```
RONDA n
Visto en un segundo: …
Idea (una frase): …
Momento firma: …
Composición por escena (una palabra cada una): …
Puntuación (rubrica-premios.md): … · Topes aplicados: …
Tres problemas principales (el más visible primero), cada uno con el frame donde se ve y el arreglo:
1. …
2. …
3. …
```

Los problemas se nombran como los nombra un diseñador a un colega: «el apoyo
de la escena 3 arranca 40 px a la izquierda del borde del titular», «el
testimonio es la tercera composición dividida seguida». «Podría pulirse» no es
un hallazgo.

**Qué arreglar primero** (lo posterior no rescata lo anterior): la idea →
la jerarquía (un elemento dominante por plano) → la composición → la
tipografía → la imagen → el color → el detalle → el movimiento. Cuando quitar
algo deja un hueco, no se rellena con un adorno: se cierra el hueco, se agranda
lo que queda, o una imagen o un campo de color toma el espacio. Cada arreglo es
una pasada con alcance (`references/pasadas.md`).

**Cuándo parar**: máximo tres rondas (crítica → arreglar los tres primeros →
re-verificar → crítica). Antes si una ronda no encuentra nada que un extraño
notaría. Si la tercera sigue bajo el listón (media < 4.3), se dice claro con los
problemas pendientes; no se redondea hacia arriba.

## Reglas del loop

- Ningún video se entrega con defectos máquina sin descartar.
- Ningún descarte sin motivo escrito (una línea basta).
- Si un defecto reaparece 2 veces, la causa está en el renderer o el plan,
  no en los parámetros: arreglar la raíz, no el síntoma.
- El sheet final limpio se guarda junto al entregable como evidencia de QA.

---

→ Canónico: `references/qa-entrega.md` · Dominio: qa · Vecinos: `references/checklist-qa.md`, `references/rubrica-premios.md`, `references/reglas-tecnicas.md`
