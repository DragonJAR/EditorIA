# Método de dirección — del brief a la entrega

El orden en que se dirige una pieza antes de tocar el motor. Aquí vive solo lo
que ninguna otra guía decide: qué hacer **antes** de escribir el plan y cómo
**cerrar** la entrega. El resto se enlaza, no se repite: el listón medido está
en `direccion.md`, el ritmo en `ritmo.md`, el sonido en `sonido.md`, los
pases de revisión en `auto-qa.md` y la entrega en `qa-entrega.md`.

A una pieza se la juzga en este orden: **sonido, ritmo, cámara, dirección**
(actuación, puesta en escena, arco emocional). Que los fotogramas se vean bien
es el punto de partida, no el resultado.

## 1. Tomar el brief (una sola ronda de preguntas)

El usuario da un estilo y un tema, a veces más (duración, idioma, voz, planos
obligatorios, reglas de marca). Lo demás lo decide quien dirige. Se pregunta
**una vez**, en un solo mensaje, y no se vuelve:

- lo que del tema no se pueda decidir solo (hechos; nombres, logos o productos que deban salir);
- si hay material propio: grabación de voz o voz preferida, música, fotos, logos, tipografías, datos;
- el idioma de voz y subtítulos, si no es obvio (por defecto, el del usuario);
- si quiere revisar un storyboard antes (por defecto, no).

Lo que el pedido ya responde se salta; el resto se rellena con valores por
defecto razonables, se resume el brief en unas líneas y se empieza. Una pieza
de 30–60 s ajustada vale más que una rellena; pasados 2–3 minutos el tiempo y
el costo se multiplican, y se le dice al usuario. Sin voz o sin subtítulos
(si lo pide): se quitan esos pasos y el tratamiento lo dice.

Si el usuario aporta una grabación propia, se usa tal cual y se transcribe para
tener los tiempos por palabra. Lo que aporte (logos, fotos, clips, datos) va
primero; si no tiene, se dibujan sustitutos ficticios. Antes de descargar nada
de una fuente externa se le dice qué, de dónde y con qué licencia.

## 2. Buscar un referente antes de escribir

Antes del tratamiento, se eligen **una o dos obras** (películas, títulos de
crédito, juegos, anuncios) que fijan el listón para **este estilo y este tema**.
Se eligen para la pieza, no se toma la de ninguna muestra. Se anota:

- **Qué aprender**: composición, ritmo, gramática de cámara, lógica de color, forma de la banda sonora;
- **Qué no tomar**: personajes, diseños, melodías, planos concretos, logos, tipografías.

El referente sube la calidad más que cualquier regla de abajo. Para un
referente que sea un video, el análisis es `referencia-video.md`.

## 3. Dar forma a la historia

- **Un sujeto, un objetivo, un giro.** Alguien (o un objeto, producto o idea) quiere algo, algo cambia, y termina distinto de como empezó.
- **Gancho en los 3 primeros segundos.** Ningún logo lento antes de que pase algo.
- **Un final que hace eco**: cerrar el arranque, revelar la escala o hacer bien la cosa la segunda vez.
- **Un momento nativo**: algo que solo este medio puede hacer (un pliegue que es la transición, tinta que florece en la escena siguiente, una rejilla tipográfica que encaja en el logo). Va en el pico emocional. Si el estilo lista los suyos, se elige uno o se inventa el que la historia pida.
- **Recortar lo accesorio.** Un chiste que se lee a tamaño miniatura vale más que tres que no. Si un momento necesita explicación, se quita.

## 4. Escribir el tratamiento

`TRATAMIENTO.md` (lo crea `scripts/proyecto.py`) se escribe **antes** de dibujar
nada y antes de abrir ninguna muestra. Pide, en este orden:

1. **Tres estructuras candidatas** (viaje único, antes/después, cuenta atrás, lista que gira...), la elegida y por qué. También de ahí salen la primera imagen, el final y la forma de la banda sonora: la primera idea que llega para un estilo suele ser su cliché.
2. **Logline y arco**: una frase; después planteamiento → giro → final.
3. **Referente**: qué aprender y qué no (§2).
4. **Lista de planos**: encuadre (general, entero, medio, primer plano, detalle), ángulo, movimiento de cámara (empuje, retroceso, paneo, travelling, grúa, zoom), duración y **por qué** así.
5. **Mapa de señales**: tempo, rejilla de compases, instrumentación por sección y en qué pulso cae cada corte, acción clave y subtítulo (`beat_grid.py`, `verificar_ritmo.py`).
6. **Tabla de diseño sonoro** por sección: ambiente, foley principal y estado de la música (§6).
7. **Diseño de subtítulos y rótulos**: la tipografía es parte del estilo.

## 5. Probar el aspecto

- **Con personajes**: una hoja de modelo (vueltas, 3–4 expresiones, 2–3 poses clave, paleta) y dos fotogramas de estilo.
- **Sin personajes**: tres fotogramas de la pieza, uno de ellos el plano firma.

Se renderizan con el código real, no con una maqueta, y se comparan con el
estilo antes de seguir (`contact_sheet.py`). Si el usuario pidió storyboard:
6–9 planos clave en una sola hoja con número, encuadre y duración, se envían con
el logline y lo que menos se tiene claro, y **se espera su aprobación**. Si no
lo pidió, no se detiene.

## 6. El sonido es la mitad de la pieza

- **Toda acción visible suena**: aterrizajes, páginas, cortes, gotas, clics, tela. El sonido se ajusta al material (papel, madera, metal, tinta y vidrio no suenan igual).
- **Tres capas**: ambiente, foley (atado a las acciones) y música. La música baja bajo el diálogo y el foley clave (`medir_mezcla.py`).
- **Al menos dos silencios reales (o casi)** antes del giro o del pico: el primer sonido que vuelve debe ser de los más importantes de la pieza. Se comprueba con `medir_silencios.py`.
- **El sonido como transición**, al menos dos veces: el sonido de la escena siguiente entra antes (corte en J), o el de la anterior corre sobre el corte (corte en L).
- **Nada de "piano y cuerdas" genérico**: se instrumenta con la paleta sonora del estilo.

## 7. Ritmo: primero la rejilla musical

- El mapa de señales se escribe antes de animar; la imagen se ata a la rejilla y un script comprueba cada señal.
- **Variar el paso**: alternar rápido y lento, con una aceleración o desaceleración clara y un respiro (plano largo o pausa sostenida). Una pieza a velocidad uniforme ha fallado.
- Una acción, un sonido, un corte; pero no cortar en cada pulso. Dejar tiempo para ver.
- **Ritmo para el espectador, no para el reloj**: el piso de lectura (`ritmo.md`) manda. Los rótulos de título se sostienen al menos 4 s. Lo rápido se logra con menos palabras por pantalla, no cortando antes de que se pueda leer.

## 8. Cámara: cada plano tiene un porqué

- Al menos **cuatro movimientos distintos** y cambios reales de encuadre. El 2D también tiene cámara: empuje, retroceso, paralaje, enfoques, marcos dentro de marcos.
- **Un plano firma** que se recuerde: un plano secuencia, una revelación de escala, una transición hecha con el propio medio.
- **Transiciones dentro del medio** (una página que se pasa, una línea tallada que crece, tinta que se extiende), con una gramática coherente. Sin fundidos ni cortes por defecto.
- En los momentos clave el sujeto ocupa al menos un tercio del alto del cuadro, con puesta en escena clara y silueta legible.

## 9. Actuación

- **Anticipación, acción y remate** en cada gesto con sentido. Los personajes cambian de emoción; no se deslizan por la pantalla.
- **Continuidad de movimiento**: se mezclan las poses con fotogramas clave y suavizado; nunca se cambia de pose dentro de un `if` (salvo un golpe cómico deliberado de un solo cuadro). Lo que se sostiene queda **entre las palmas**; el traspaso interpola de una palma a la otra; un objeto que rueda gira distancia ÷ radio.
- Se revisan las acciones clave cada 0,2 s, ampliadas. Y cada expresión, a tamaño final: "preocupado" y "enfadado" distan una ceja.

## 10. Los fallos más vistos

Sujeto pequeño, lejano o pegado al borde. Demasiado oscuro o color sobre el mismo color (rojo sobre rojo). Subtítulos tapando al sujeto. Un chiste o fallo demasiado rápido para entenderse. Fotogramas en blanco en las transiciones. Un efecto con tiempo (iris, zoom, seguimiento) que no sigue al sujeto después de mover la cámara: todo lo que sigue a un sujeto pasa por una sola función mundo→pantalla, nunca coordenadas escritas a mano.

## 11. Cambiar un estilo sin romperlo

Cuando el usuario quiere "mi versión" de un estilo, se le dice qué parte toca
antes de tocarla (los deseos vagos se traducen con la tabla de
`direccion.md`, "Feedback vago → palancas"):

| Grupo | Qué es | Qué decir |
|---|---|---|
| **Seguro de cambiar** | la paleta dentro de su lógica, la tipografía, el tempo y cuánto se mueve, la paleta sonora, añadir o cambiar un momento nativo | el estilo sigue siendo él mismo; dar 2–3 ideas por cada uno |
| **Cambia su carácter** | los materiales y el render, la lógica de color misma, la gramática de cámara | es posible; decir qué pierde el estilo con cada cambio |
| **No se cambia** | su esencia (y su "lo que no es") y el motor | eso es otro estilo, no una versión: proponer una base más cercana |

Reglas: el cambio sale del uso (un boletín semanal de marca pide tipografía
legible y apertura fija; un canal infantil, formas grandes y lectura lenta);
**hasta cinco cambios por ronda**; la firma del estilo (su momento nativo) se
cambia como mucho una vez; los cambios viajan juntos (movimiento más rápido
pide sonido más denso; paleta más oscura, contraste de tipografía comprobado).
Con marca: el color de marca entra como acento, no como fondo, y la
tipografía de marca debe cubrir el idioma de la pieza y permitir uso en video.
El resultado se guarda como sistema visual del proyecto (`brand-packs.md` y
`direccion-de-arte.md`), con una tabla de decisiones: sección, base, ahora y
por qué. Se prueba con un solo fotograma de estilo, lado a lado con la base, y
se espera al usuario antes de seguir.

## 12. Antes de entregar

- Pasadas de `auto-qa.md`: hojas de contacto, tiras de 0,2 s de las acciones clave y un visionado completo, a velocidad real y con sonido.
- **Una sola ronda de arreglos.** Se corrige todo lo que la revisión encuentre y se comprueba una vez más; lo pequeño que salga en esa segunda mirada (un nivel, un cuadro) es de la misma ronda; lo grande, se dice en una línea al entregar. Las notas posteriores del usuario son rondas nuevas: se cambia solo lo que piden.
- **Que no se parezca a la muestra.** Tras el tratamiento, si se mira una muestra del estilo, se compara estructura, apertura, plano firma, camino de cámara, forma de la banda sonora y final: al menos cuatro de los seis deben diferir.
- Voz: cada línea se transcribe de vuelta y coincide con el guion; sonoridad de entrega (`qa-entrega.md`); sin fotogramas negros ni NaN; subtítulos en sincronía; cada fila de la tabla sonora está de verdad en la mezcla.
- **Entrega**, en la carpeta del proyecto: el video final y su carátula; el `.srt` si hay locución o subtítulos; `TRATAMIENTO.md`; **`CREDITOS.md`** (cada activo de terceros con fuente y licencia); y la fuente con un comando que la reconstruya. Se le dice al usuario dónde está todo y que es responsable de los materiales que use.

## 13. Líneas rojas de derechos

- Las referencias enseñan **gramática**, no se copian: personajes, diseños, melodías, planos, logos o tipografías.
- No aparecen obras, juegos, marcas ni eventos reales salvo que el usuario los posea o tenga derecho a usarlos (incluidos los logos, fotos y clips que entregue: se usan cuando dice que tiene el derecho; si no, se dibujan sustitutos ficticios).
- Solo material CC0, CC BY u OFL, con su fuente y licencia en `CREDITOS.md`. Las obras en dominio público cuentan como CC0; "sin restricciones conocidas" no. Datos o imágenes con otras licencias abiertas (ODbL, CC BY-SA...) solo tras decirle al usuario la licencia y sus condiciones, y que las acepte.
- Una pieza que afirma hechos lleva una **hoja de hechos** en el proyecto: cada afirmación con su URL y la cita textual, o la medición que la produjo.

## 14. Mapas

Rige para todo fotograma con un mapa, un globo o una imagen de satélite.

- **Sin fronteras salvo que la pieza trate de ellas.** Se dibujan costas, relieve, imágenes o calles; se prefiere una vista regional a un mapamundi y se dejan fuera de cuadro las zonas en disputa.
- **Los datos de fronteras por defecto no son neutros.** Si la pieza necesita fronteras, se usan datos de la vista oficial del país de la audiencia y se nombra cuál; en la pieza, un territorio o región no se lista como país si el criterio de la audiencia no lo es: se rotula "países y regiones". Se limpia el campo de país de un conjunto de datos antes de graficarlo.
- **Comprobar y acreditar**: antes de entregar se amplía cada plano con mapa y se revisa contra estas reglas; `CREDITOS.md` nombra los datos del mapa, su fuente y su vista.

---

→ Canónico: `references/direccion.md` · Dominio: estructura · Vecinos: `references/ritmo.md`, `references/sonido.md`, `references/auto-qa.md`, `references/qa-entrega.md`
