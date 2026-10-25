# Glosario — el vocabulario de la skill

EditorIA habla con palabras propias. Un agente que las lea sin conocerlas
interpreta mal: "un wash sobre la escena" no es una instruccion si no sabes
que es un wash. Este archivo define **cada** termino, dice **para que sirve**
y **donde se implementa**.

Si un termino de este glosario aparece en un brief, en una instruccion o en
un parametro del plan, esta es su definicion.

## 1. El plan

| termino | que es | donde |
|---|---|---|
| `plan.json` | la partitura: la fuente de verdad de la pieza. Todo lo demás se deriva de el | `references/plan-video.md` |
| `duracion` | segundos totales de la pieza | `references/plan-video.md` |
| `tamano` | `"1080x1920"` (vertical) o `"1920x1080"` (horizontal) | `references/plan-video.md` |
| `escenas` | la lista de escenas, en orden temporal | `references/plan-video.md` |
| `from` / `to` | ventana de cada escena, en segundos absolutos | `references/plan-video.md` |
| `at` | los instantes exactos en que aparece cada elemento (`at.rotulo`, `at.item0`, `at.cambio`...) | `references/plan-video.md` |
| `voz` | el texto que se dice en esa escena (se segmenta y se mezcla) | `references/sonido.md` |
| `at` de una escena | el ancla de su audio: `palabra` (n), `beat` (n), `pico` (n), `absoluta` (segundos) o `escena+at` | `references/audio.md` |
| `datos` | el modelo de cifras de la pieza: un valor con su fuente, declarado una vez y referenciado por las escenas | `references/plan-video.md` |
| `musica` | la ruta del archivo de musica (el motor puede cortar al ritmo) | `references/audio.md` |
| `marca` | el brand pack: colores, tipografias, logo, isotipo, lema, voz | `references/brand-packs.md` |

## 2. La escena y sus campos

| termino | que es | donde |
|---|---|---|
| `tipo` | cual de las 39 escenas es (ver `references/escenas.md`) | `references/escenas.md` |
| `rotulo` | el titulo de la escena, con enfasis `*...*` en el color de acento | `references/plan-video.md` |
| `kicker` / `badge` | la etiqueta pequena sobre el titulo (categoria o dato) | `references/plan-video.md` |
| `pie` | la linea al pie (la fuente del dato, la firma) | `references/plan-video.md` |
| `fuente` | de donde sale el dato de la escena (obligatorio si hay cifras) | `references/copy.md` |
| `items` | las tarjetas de una escena de rejilla (`bento`, `stats`, `pasos`...) | `references/escenas.md` |
| `valor` / `max` | la cifra y su escala (un `gauge` con `valor: 9, max: 10`) | `references/escenas.md` |
| `gigante` | la cifra o palabra de cierre de un `remate`, hasta 300 px | `references/escenas.md` |
| `subtitulo` | la linea de apoyo bajo el titulo (en el `hero` se dibuja en 2 lineas) | `references/plan-video.md` |

## 3. El oficio del movimiento

| termino | que es | donde |
|---|---|---|
| **mancha** | la transicion de entrada: una mancha de color de acento que se abre y deja ver la escena. No es un fondo | `references/escenas.md` |
| **spot** | el punto de interes de un plano (el ojo, la mano, la pantalla): el motor hace zoom ahi | `references/modos-produccion.md` |
| **wash** | una capa de color (o de negro) que tiñe el plano entero: separa dos tramos o baja el contraste | `references/tecnicas-video.md` |
| **remate** | la escena que cierra un bloque con una cifra gigante y una frase | `references/escenas.md` |
| **pase** | un corte con movimiento: el plano entra y sale, no un corte seco | `references/tecnicas-video.md` |
| **hold** | el tiempo que un elemento se queda quieto en pantalla antes de salir. Un hold corto se lee como prisa | `references/ritmo.md` |
| **overlap** | dos elementos que se solapan en el tiempo: el segundo entra antes de que salga el primero | `references/animacion.md` |
| **stagger** | el retardo escalonado de una cascada (tarjetas que entran de una en una) | `references/animacion.md` |
| **slam** | la entrada de golpe: el elemento cae desde grande y se asienta. 1,6 -> 1,0 | `references/animacion.md` |
| **fundido** | la transicion a negro o a blanco entre dos tramos | `references/tecnicas-video.md` |
| **velo** | la capa negra que se superpone para que la caja blanca lea sobre el footage | `references/modos-produccion.md` |
| **telemetria** | el HUD de datos que acompana a un plano (velocidad, tiempo, contador) | `references/tecnicas-video.md` |
| **respiracion** | la flotacion continua de un elemento ya asentado (±4-6 px): nada queda totalmente quieto | `references/animacion.md` |
| **rebote / overshoot** | el resorte se pasa de su objetivo y vuelve. Techo general: 8 % | `references/animacion.md` |
| **curva / easing** | la forma del movimiento: `ease_out` (entrar), `ease_in_out` (mover lo que ya esta ahi), resorte (todo lo demas) | `references/animacion.md` |
| **arco** | el recorrido en pantalla de un elemento: entra por un lado y sale por el otro, en curva | `references/animacion.md` |
| **densidad** | eventos de movimiento por segundo. El motor penaliza fuera de 0,5-2,0 eventos/s | `references/fluidez.md` |
| **piso de letra** | el minimo de tamano de texto que se lee en un telefono: **26 px** sobre 1080. Se mide EN REPOSO, no durante la entrada | `references/coherencia-espacial.md` |
| **piso de lectura** | el tiempo minimo que un texto debe quedar asentado para poder leerse: 0,8 s por etiqueta, 0,3 s por palabra | `references/ritmo.md` |
| **zona segura** | la parte del cuadro que la UI de la plataforma no tapa. Vertical: 151 px a los lados | `references/coherencia-espacial.md` |
| **caja** | el rectangulo que ocupa un elemento: su centro, su margen y su altura importan | `references/coherencia-espacial.md` |
| **lienzo** | el cuadro del render (1080x1920 en vertical) | `references/reglas-tecnicas.md` |
| **composicion** | como se reparten los elementos: un foco por plano, el bloque de texto centrado en su contenedor | `references/coherencia-espacial.md` |
| **tipografia** | la escala de tamnos, el interlineado y donde va cada rol (titular, apoyo, dato, pie) | `references/reglas-tecnicas.md` |
| **paleta** | los colores de la pieza. Uno solo de acento | `references/principios.md` |
| **acento** | el color unico que comunica (el del pack, o el elegido en modo libre) | `references/principios.md` |
| **movimiento signature** | el gesto propio de la pieza, el que la hace reconocible | `references/principios.md` |
| **firma de estilo / signature features** | lo que hace reconocible un lenguaje MG a primera vista; se juzga, no se diluye | `references/estilos-codigo.md` |
| **un protagonista por plano** | en cada plano, un solo elemento se mueve: si dos se mueven, uno sobra | `references/principios.md` |
| **arco dramatico** | la estructura del relato: marco, tension, giro, resonancia | `references/dramaturgia.md` |
| **hook** | los primeros segundos: lo que obliga a seguir mirando | `references/dramaturgia.md` |
| **payoff** | la revelacion que paga la tension del arco | `references/dramaturgia.md` |

## 4. La marca

| termino | que es | donde |
|---|---|---|
| **pack** | el archivo de identidad (`brand/*.json`): colores, tipografias, logo, isotipo, lema, voz | `references/brand-packs.md` |
| **isotipo** | el logo de marca (el icono, sin texto) | `references/brand-packs.md` |
| **lema** | la frase de la marca, con enfasis `*...*` | `references/brand-packs.md` |
| **modo marca** | cuando el usuario nombra una marca: se carga su pack y el pack manda | `references/brand-packs.md` |
| **modo libre** | cuando no hay marca: la paleta, la tipografia y el idioma de transicion se eligen del brief. **Nunca se inventa una identidad** | `references/principios.md` |
| **fidelidad de marca** | la marca se usa tal cual: mismo color, misma tipografia, mismo isotipo | `references/principios.md` |

## 5. La produccion

| termino | que es | donde |
|---|---|---|
| **VO** | la voz en off (el texto `voz` de una escena) | `references/sonido.md` |
| **beat** | el pulso de la musica; el corte al beat es un recurso de ritmo | `references/audio.md` |
| **compas** | cuatro beats; el tiempo fuerte es el primero | `references/audio.md` |
| **pico** | un transitorio real de la musica (golpe, stab): el sitio donde un SFX de impacto pega de verdad | `references/audio.md` |
| **ancla** | de que se cuelga un SFX: una palabra, un beat, un pico, un tiempo absoluto o el corte de escena | `references/audio.md` |
| **cue** | una entrada de SFX en la linea de tiempo | `references/sfx.md` |
| **ducking** | la musica se baja bajo la voz (~15 dB) para que la palabra se entienda | `references/audio.md` |
| **LUFS** | la sonoridad percibida de la mezcla. La entrega pide -14 (banda de 2) | `scripts/ffmpeg_tools/_delivery.py` |
| **true peak** | el pico instantaneo. La entrega pide <= -1,0 dBTP | `scripts/ffmpeg_tools/_delivery.py` |
| **motion blur** | el desenfoque de obturador: 180 grados. Se renderiza con sub-frames (`--blur 5`) | `references/animacion.md` |
| **still** | un frame suelto | `references/thumbnails.md` |
| **contact sheet** | la hoja de contactos: la foto del video para revisarlo de un vistazo | `scripts/contact_sheet.py` |
| **storyboard / animatic** | el plan de planos y su montaje sin pulir, para ajustar el ritmo antes de renderizar | `references/ritmo.md` |
| **formato** | la relacion de pieza entera que se repite (quien carga el argumento y que la sostiene) | `references/formatos.md` |
| **corte / montaje** | unir, cortar, fundir, dividir, PiP: las 19 operaciones de `montaje.py` | `references/montaje.md` |
| **puente** | el recurso que cose el video real con la animacion sin que se note | `references/modos-produccion.md` |
| **modo** | de donde sale la imagen: real, animacion o hibrido | `references/modos-produccion.md` |
| **proyecto** | la memoria de un trabajo: BRIEF, TRATAMIENTO, PROGRESO y TIMELINE | `scripts/proyecto.py` |
| **gate** | la puerta antes de entregar: nada pasa si un eje baja de 4 o la media de 4,3 | `references/rubrica-premios.md` |

## 6. Donde se define cada cosa

Si buscas la fuente de una idea, no la repitas: esta tabla esta en
`references/mapa.md` y `scripts/auditar_mapa.py` la verifica.

| dominio | canonico |
|---|---|
| movimiento | `references/animacion.md` |
| estructura | `references/principios.md` |
| plan | `references/plan-video.md` |
| escenas | `references/escenas.md` |
| sonido | `references/sonido.md` |
| copy | `references/copy.md` |
| qa | `references/qa-entrega.md` |
| marca | `references/brand-packs.md` |
| produccion | `references/formatos.md` |
| operacion | `references/instalacion.md` |
| herramienta | `references/capacidades.md` |
| declarar | `references/capacidades.md` |
| indice | `references/mapa.md` |

---

→ Canónico: `references/glosario.md` · Dominio: vocabulario · Vecinos: `references/mapa.md`, `references/escenas.md`, `references/plan-video.md`
