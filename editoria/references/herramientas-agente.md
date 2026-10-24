# Herramientas del agente — cómo se usa una capacidad y cómo se entrega

`references/capacidades.md` DECLARA con qué cuenta la skill: visión, generación
de imágenes, navegador y búsqueda, más los MCP conectados. Esta referencia es
la otra mitad: el HANDOFF. Qué archivo deja cada una, con qué campo del plan
se nombra y qué se dice cuando la herramienta no está conectada. Una capacidad
sin handoff es una promesa que nadie cumple.

## 1. La regla: la herramienta del agente es capacidad de la pieza

Las herramientas que el agente tiene conectadas (navegador, MCP, generación de
imágenes, búsqueda, visión, control de la GUI) son **capacidades de la pieza**,
igual que ffmpeg o el pack de marca: si el brief las necesita, levantan el
listón del resultado.

- Si la pieza necesita una y el agente **no la tiene**: se DECLARA en la
  **primera respuesta** (no en la entrega, que es tarde), con dos cosas: qué se
  pierde exactamente y qué se entrega en su lugar. Ese "en su lugar" es
  honesto y ejecutable, no un consuelo.
- Si la pieza necesita una y el agente **sí la tiene**: se usa. Y si el agente
  tiene una herramienta que esta skill no exploitaba (un MCP de navegador, una
  app conectada, una CLI del entorno), también se usa: la skill tiene una lista
  de necesidades, no una lista cerrada de herramientas (cómo se identifica el
  inventario, en la sección 2). Y si se usa una herramienta **fuera de la
  skill**, se dice cuál y por qué.
- Nunca se degrada en silencio. El orden es el de `references/capacidades.md`:
  primero la mejor salida posible; si no se puede, se declara y se explica la
  alternativa. Degradar está bien; degradar sin decirlo no. Y "no encontré"
  sin haber buscado no vale: se declara que la herramienta no está conectada.

Las herramientas locales se comprueban al arrancar (`python3 scripts/check_env.py`);
las del agente las comprueba el agente, y su veredicto va en la primera respuesta.

## 2. El inventario es del AGENTE (y cómo se identifica)

La skill **no lleva una lista de herramientas**: el inventario cambia con la
instalación y con la sesión, y una lista escrita aquí se quedaría vieja en
silencio (es el mismo fallo que un número de prosa sin vigilar). Lo que la
skill fija es el PROCEDIMIENTO; el inventario lo aporta el agente.

**Cómo se identifica** (en este orden, y sin adivinar):

1. **Mirar la propia lista de herramientas.** Lo que el agente tiene conectado
   se ve: son las herramientas que puede invocar. Si hay servidores MCP
   configurados, su lista se **pide al runtime** (el comando de inventario de
   MCP que traiga el entorno), no se supone ni se cuenta de memoria.
2. **Mirar lo que el entorno ofrece**, que no es lo mismo: una CLI instalada,
   un binario, un servicio en localhost, una carpeta de material.
3. **Pasarle el mismo test que a cualquier capacidad**: ¿la pieza de este
   encargo necesita esto? Si la respuesta es sí, la herramienta levanta el
   listón del resultado: se usa; si no está, se DECLARA (sección 1).
4. **Dejar el veredicto por escrito**: qué herramientas se usaron y por qué
   queda en `PROGRESO.md` del proyecto, para que otra sesión sepa qué se
   tenía y qué se usó.

Cuando el agente **no puede enumerar** su propio inventario (agentes cerrados,
sin introspección), el mínimo honesto es el que sí ve: las herramientas que
puede invocar y las que ha usado en esta sesión — y se dice que la lista no
se pudo comprobar entera. "No pude enumerar X" es una afirmación honesta;
"no lo tengo" sin mirar, no lo es.

### Herramientas que suelen estar conectadas (ejemplos, no lista cerrada)

Esta tabla NO es el inventario: es el patrón de handoff de las que aparecen
en casi cualquier agente. La que tengas se aplica con esta misma lógica; la
que no tengas, se declara.

| Herramienta | Para qué sirve aquí | Qué se entrega | Si falta |
|---|---|---|---|
| Navegador del agente | entrar en la página que `yt-dlp` no puede descargar; ver una referencia en su contexto; ver la fuente primaria de una cifra | el archivo de video o la imagen en la carpeta del proyecto, con su procedencia anotada en `PROGRESO.md` | se DECLARA: se pide al usuario el archivo y se sigue con lo local |
| MCP de navegador | lo mismo, pero devolviendo la URL final, el texto de la página o la respuesta cruda cuando el navegador no sabe guardar el binario | el texto o el JSON de la fuente en `referencias/{nombre}/evidencia/` del proyecto | se DECLARA: se cae al navegador del agente o a la búsqueda, y se dice |
| Generación de imágenes | el fondo, la textura, el mockup o la ilustración que el brief pide y que el cliente no tiene | el PNG o el JPG en la carpeta del proyecto y el prompt anotado en `TRATAMIENTO.md` | se DECLARA: la pieza va con `solo_texto` (el orden de preferencia de `references/direccion-de-arte.md`) o se pide el material |
| Búsqueda web | encontrar la fuente primaria de una cifra, una técnica o un competidor | la URL real en el campo `fuente` de la escena o del bloque `datos` | se dice que el dato va sin fuente verificable, y el dato no entra |
| Visión (mirar fotogramas) | QA cuadro por cuadro antes de entregar: leer la hoja de contactos y los frames donde pasa algo | la hoja de contactos revisada y la lista de lo que se corrigió | se DECLARA: la puerta automática corre (`scripts/qa_entrega.py`) y el juicio visual queda declarado como no hecho |
| Computer use (GUI) | abrir una aplicación nativa (un editor, un panel, un archivo del sistema) cuando no hay otra vía | el archivo abierto o el ajuste hecho, en la carpeta del proyecto | se DECLARA: se hace por script o se le pide al usuario |

## 3. Los handoff, uno por uno

### 3.1 Un video que `yt-dlp` no puede descargar

`scripts/referencia.py --url` baja con `yt-dlp` un solo video (H.264 cerca de
1080p, sin pisar archivos). Cuando el enlace es un reel de Instagram, un TikTok
con login o un video con protecciones, la descarga falla: el QUÉ ya está en
`references/capacidades.md`; esto es el CÓMO.

1. Se abre la URL con el navegador del agente y se baja **el archivo de video
   que sirve la propia página**: no la vista previa, ni un pantallazo del
   player, ni la miniatura de la tarjeta social.
2. El archivo se guarda en la carpeta del proyecto, en `referencias/{nombre}/`
   (donde `scripts/clonar_video.py analizar --url` deja la fuente,
   `ANALYSIS.md`, `plantilla.json` y la hoja de contactos), con su nombre.
3. La ingesta sigue siendo la de siempre, pero desde el archivo local:
   `python3 scripts/referencia.py --video clip.mp4 -o referencias/{nombre}`.
4. Si el navegador tampoco lo consigue (el player no expone el binario, hay
   login, la página no lo carga): se DECLARA y se pide al usuario el archivo
   (export del sitio o descarga desde la app). Dos intentos y se cambia de vía.
5. Lo que entra por aquí es material fuente (sección 4): se anota de dónde salió.

### 3.2 Generar un asset de imagen

**Dónde**: en la carpeta del proyecto (la que arma `scripts/proyecto.py`: BRIEF,
TRATAMIENTO, PROGRESO), nunca dentro de la skill: la skill es código y la
pieza es material. El entregable va a la carpeta de salida que pida el usuario.

**Cómo lo nombra el plan**: los campos exactos que apuntan a un archivo son
`imagen` (escena `kenburns`) y `captura` (escenas `demo` y `callout`); el motor
los resuelve relativos al plan (`MEDIOS` en `scripts/render_plan.py`). No hay
un campo genérico de asset: el nombre va en el campo de la escena que lo usa,
y el archivo se llama por su PAPEL (`fondo_01.png`), no por su origen.

**Qué se le pide al modelo**: el encuadre (qué se ve, desde dónde, a qué
altura, con qué luz), la relación de aspecto (1080x1920 para un fondo vertical;
la caja donde va la foto si la imagen vive dentro de un plano) y el estilo de
la marca (la paleta y el acento del pack, el tono de la luz, el material). Y
en negativo, que es donde los generadores fallan: sin texto incrustado, sin
logo, sin marca de agua, sin cara reconocible, sin interfaz de usuario.

**Qué se verifica antes de usarlo** (se mira el archivo, no su descripción):
que no traiga texto incrustado, ni el logo de otra marca, ni interfaz si lo que
se busca es una foto; y que encaje con la paleta del pack, porque la imagen
manda en el look del cuadro. Si algo falla, se regenera con el prompt
corregido, no se disimula con un recorte. Sin herramienta de generación: se
DECLARA y no se suplanta con una imagen de otro sitio.

### 3.3 Verificar una cifra antes de escribirla

La regla de `references/copy.md`: **toda cifra lleva su fuente**, y la fuente
es la escala o el estudio real del que sale, no un tercero que no ha dicho eso.
Se busca la cifra, se va a la **fuente primaria** (el informe, el comunicado, la
tabla del organismo: no la nota que la cita, ni el resumen sin fecha, ni el
post que la copia) y se comprueba que dice lo que el plan va a decir: el año,
la unidad, el alcance, la muestra. "El 40 % de los equipos" y "el 40 % de las
empresas de más de 50 empleados" no son el mismo dato.

El `fuente` se escribe con el nombre real de esa fuente. Si la cifra la usan
varias escenas, se declara una vez en el bloque `datos` del plan y las escenas
la referencian con `{"$dato": "nombre"}`, para que ninguna la contradiga.

Un dato sin fuente verificable **no entra** en la pieza: no se inventa ni se
adorna, y se dice qué cifra se quedó fuera y por qué. Sin búsqueda, se declara
en la primera respuesta; la cifra del brief se usa con la fuente del cliente.

### 3.4 Investigar una técnica

Buscar, mirar y **adaptar**. Copiar una técnica sin entenderla produce una
pieza que se sostiene pero no dice nada: el movimiento entra bien y el
argumento no entra.

Se buscan dos o tres ejemplos de la técnica (uno es un caso; tres son un
patrón) y se miran: los que son video, con hoja de contactos
(`scripts/contact_sheet.py --video clip.mp4 --cada 1 -o hoja.png`); los que son
web, con el navegador. Se escribe qué resuelve la técnica y en qué momento de
ESTA pieza entra, y se adapta al material y al ritmo de esta pieza: de una
referencia se copia la FUNCIÓN, no el plano (`references/referencia-video.md`).
Si la técnica necesita un motor que no está, se DECLARA
(`references/capacidades.md`) y se propone la versión que el motor propio
sostiene: el listón no baja solo.

## 4. El anillo: lo que entra de fuera es material fuente

Una página, una imagen o una cifra que trae el agente —o que llega por un MCP
de Drive o de Gmail— es **material fuente**, no verdad. El MCP no es más
fiable que el navegador: solo cambia el transporte. Antes de entrar en el plan:
se anota de dónde sale (la URL, la ruta del MCP, el archivo) en el
`PROGRESO.md` del proyecto; se verifica contra la fuente primaria (para una
cifra, la del dato; para una imagen, quién la tiene y con qué licencia; para
un texto, contra quién dice, cuándo y en qué versión); y lo que no se verifica
no entra. Vale igual para lo que trae una herramienta que la skill no pidió.

## 5. Lo que no se hace

- **No** se pega una captura de pantalla de un video como imagen del plan sin
  mirar si trae interfaz, barra de reproducción, un reloj o un nombre de
  usuario: eso es la foto de una interfaz, no una imagen. Y el texto incrustado
  no se quita: se regenera o se descarta.
- **No** se usa un asset generado sin la marca: si la imagen no lleva el
  acento del pack, el plano se ve prestado; o se declara que la pieza va con
  imagen de fuera, y lo decide el usuario.
- **No** se inventa una URL como fuente: una fuente que no existe es peor que
  no tenerla, porque convierte una cifra suelta en una cita falsa. Una URL que
  no se ha abierto no es una fuente.
- **No** se descarga de una URL sin comprobar la licencia y el uso previsto:
  una imagen de archivo se usa solo con licencia que permita uso comercial,
  con su fuente y su licencia registradas y el crédito pequeño al cierre
  (`references/direccion-de-arte.md`). Y nunca se presenta como el producto, el
  local o la persona del cliente.
- **No** se dice "no encontré" cuando no se buscó: se declara que la
  herramienta no está conectada.

---

→ Canónico: `references/herramientas-agente.md` · Dominio: herramienta · Vecinos: `references/capacidades.md`, `references/instalacion.md`, `references/glosario.md`
