# Copy — el texto decide si un video se lee como diseñado

Un titular de cuatro lineas no lo salva la tipografia, y una pagina de
eslogan no la salva el layout. El copy es la primera decision de diseno: se
escribe antes que el plan, en texto plano, y el plan es la puesta en escena
de lo que ya esta escrito.

Esta referencia es el contrato de copy de EditorIA. La comprueba
`scripts/lint_copy.py` (determinista: mide con las tipografias del motor) y
las reglas viven en `scripts/_copy.py`.

## 1. El argumento primero

Antes de elegir escenas, responder en una linea cada una:

- Quien mira esto y que ya sabe?
- Que es esto, dicho como lo diria quien lo hizo a un amigo?
- Que tiene que creer la persona despues de estos segundos?
- Que se lo hace creer (la imagen, la cifra, el nombre, la demostracion)?
- Que hace despues?

Despues, listar el video como afirmaciones con su prueba, una por escena:

```
1. Tu web es el objetivo.              -> la tienda abierta de noche
2. Lo encontramos antes que nadie.      -> el escaneo en vivo
3. Cada hallazgo trae su severidad.     -> la tabla con la escala
4. No infunde panique: informa.         -> el cierre de marca
```

Una escena sin afirmacion es relleno: se elimina. Asi se sale de la
secuencia de catalogo (apertura, tres caracteristicas, testimonio, precio,
llamada a la accion): **el orden de la lista es el orden del video**.

Para una pieza de 20 segundos: cuatro o cinco afirmaciones, una por escena.

## 2. La aritmética del texto

El motor encoge, no reescribe: si el titular no cabe, baja de 4 en 4 px
hasta que cabe, y cuando el encoge es de mas del 13% **todas las lineas del
titular** quedan mas pequenas de lo que deberian. El copy se escribe para
entrar, no para que el motor lo arregle.

**El piso es 26 px y no se negocia.** El motor nunca dibuja texto por debajo
de eso: si un bloque no cabe, lo PARTE (hasta 2 lineas) y si aun asi no
cabe, el copy es demasiado largo y hay que acortarlo — el motor no lo
achica hasta hacerlo ilegible. Para lo que va en un solo renglon (una URL,
un nombre de archivo) el motor recorta con "…" y conserva el tamano.
La puerta de entrega mide la letra en reposo y falla por debajo de 26: si
te avisa, el problema es el copy, no el motor.

| campo | palabras | lineas | ancho util |
|---|---|---|---|
| kicker (badge, kicker) | 4 | 1 | 778 px a 44 px |
| titular (`titulo`, `rotulo`) | 8 a 12 | 2 | 778 px a 44 px |
| titular cinetico (`texto1`, `texto2`) | 8 | 2 | 746 px a 150 y 124 px |
| frase de apoyo (`subtitulo`) | 14 | 2 | 778 px a 32 px |
| titulo de tarjeta | 5 | 1 | 778 px a 32 px |
| texto de tarjeta | 11 | 2 | 778 px a 28 px |
| pildora (`pildoras`) | 4 por pildora | 1 cada una | 746 px a 120 px |
| pie o fuente | 8 a 16 | 1 a 2 | 778 px a 28 px |
| cita | 24 | 3 | 778 px a 44 px |
| boton | 3 | 1 | 420 px a 34 px |

Medir antes de escribir la frase: a 44 px, la zona segura de 778 px entra
en unas 35 caracteres por linea. A 150 px, en unas 12. Si la frase no cabe
en dos lineas de ese ancho, es una frase, no un titular: se recorta.

Regla de dos lineas: **un titular son dos lineas o menos**. Tres lineas ya
son un parrafo en grande; los jurados lo leen como titular largo, no como
frase de apoyo.

## 3. Formas de titular que funcionan

- **El nombre.** "DragonJAR", con la descripcion en otra parte.
- **Lo que es.** "Un escaneo de tu web, en vivo."
- **La afirmacion.** "Tu web es el objetivo."
- **La instruccion.** "Encuentra tu brecha."
- **El lugar o el momento.** "Tu tienda, 00:47."

Formas a evitar, porque son el promedio de todas las piezas:

- El mad-lib: "La plataforma de seguridad para equipos modernos".
- El tricolonio: "Rapido. Simple. Seguro." (tres afirmaciones, no una).
- La correccion: "No es solo una herramienta, es un metodo".
- "X, reinventada / redefinida / hecha simple".
- Una pregunta que nadie hacia.
- Una palabra del titular con otro estilo (italica, serif, color, subrayado).

## 4. Prueba sin inventarla

No inventar clientes, citas de personas con nombre, logos de prensa, cifras
de usuarios, calificaciones ni benchmarks. La prueba inventada es una
mentira y ademas es un tell: se reconoce.

Cuando el brief no trae prueba, usar lo que es cierto por construccion:

- Mostrar la cosa misma, grande. Una demostracion real vale mas que una cita.
- Explicar como funciona, en concreto.
- Usar los datos del brief: precio, plazo, lugar, ano, materiales.
- Si la pieza pide una cita y no hay ninguna real, **decirlo**: que la voz
  sea de la marca o marcar el contenido como muestra.

Los detalles de muestra son otra cosa y **se esperan**: donde el brief da la
forma del contenido pero no cada detalle (seis servicios, "un menu corto",
tres ponentes), escribir el conjunto plausible para que la pieza se pueda
juzgar a su densidad real. Pero=listar cada detalle de muestra en el informe
de entrega para que el cliente lo confirme o lo cambie, y **nunca poner
nombres de empresas o personas reales** en un contenido inventado.

En video esto significa: **toda cifra lleva su fuente** (campo `fuente` de
la escena). Un 9 de severidad sin escala a la vista es una cifra suelta.

Y como se declara cada fuente, para que la pieza la muestre y el linter la
acepte:

- `fuente: "Escala CVSS 3.1"` — la escala o el estudio real del que sale la
  cifra. El motor lo dibuja al pie de la zona segura ("Fuente: Escala CVSS
  3.1") y el linter deja de avisar.
- `fuente: "Voz de marca"` — la cifra o la cita es de la marca: una promesa
  propia, una frase de la propia empresa. Se dice en pantalla, para que
  quien lo ve sepa que lo afirma la marca y no un tercero.
- `nota: "Voz de marca"` — lo mismo en una cita, que ademas lleva `autor`.

Lo que **no** se hace: poner la fuente de un tercero que no ha dicho eso
("Gartner 2024" sobre una cifra inventada). Fabricar la fuente es peor que
no tenerla: convierte una cifra suelta en una cita falsa.

## 5. Lo que se lee como generado

- Verbos y adjetivos del genero: potencia, impulsa, transforma, eleva,
  desbloquea, revolucionario, sin esfuerzo, todo en uno, de ultima
  generacion, solucion integral.
- Etiquetas que fingen ser editoriales: "Notas de campo", "Nuestra filosofia",
  "Confianza silenciosa". Un rotulo puede ser simply "Servicios".
- Texto de mobiliario: "Est. 2024", coordenadas, sellos de version, "Desliza
  para", estados con un punto.
- La raya em como costumbre: una o dos se leen como escritura; diez se leen
  como un modelo. Usar punto.
- Leyendas que explican el diseno: "Un diseno limpio y minimalista para...".
- Etiquetas que repiten el numero: "Paso 1", "Fase 02".
- Tres cosas paralelas por defecto: tres servicios, tres datos, tres pasos.
  Usar el numero que tiene el contenido.

## 6. Microtipografia

- Comillas tipograficas (curly) y apostrofos reales, puntos suspensivos
  reales, guion corto para rangos.
- Espacio duro entre numero y unidad.
- Nada en mayusculas mas de tres palabras; con mayusculas, 0,02 a 0,06 em
  de tracking.
- El enfasis de color es del brand pack y marca lo importante: nunca dos
  palabras subrayadas ni en otro color en el mismo titular.
- El codigo de la marca va con el nombre, no al reves: el isotipo con el
  nombre, el nombre con el lema.

## 7. Comprobacion

```bash
python3 scripts/lint_copy.py plan.json           # fallos y avisos
python3 scripts/lint_copy.py plan.json --json    # informe para maquinas
python3 scripts/lint_copy.py plan.json --strict  # los avisos tambien fallan
```

El linter mide el texto con las TTF del motor y con el mismo auto-fit, asi
que el numero que da ("el titular queda en 64 px de 124") es el que el
render va a usar. Un **fallo** es texto que el motor no puede colocar; un
**aviso** es copy que se lee como generado o que se va a encoger de mas.

Un plan con copy de muestra (cifras de ejemplo, contenido inventado) debe
llevar su lista de contenido a sustituir en el informe de entrega, no
escondida en el render.

---

→ Canónico: `references/copy.md` · Dominio: copy · Vecinos: `references/principios.md`, `references/share-copy.md`, `references/intencion-escena.md`
