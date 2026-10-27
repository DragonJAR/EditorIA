# Intención → escena — el índice inverso del catálogo

`references/escenas.md` dice cómo se construye cada escena. Este es el camino
de vuelta: **lo que el cliente pide en palabras vagas** → la escena que lo
resuelve → la receta de movimiento.

## 1. Antes de elegir escena: ¿para qué se mueve esto?

Cada elemento que se mueve en una pieza cumple un propósito. Si no lo puedes
nombrar, el movimiento sobra (o es decoración, y la decoración no es el
trabajo).

| propósito | en video significa | se resuelve con |
|---|---|---|
| **Coherencia espacial** | lo que entra desde un lado, sale por ese lado | `apertura`, `versus`, `handoff` |
| **Indicación de estado** | el espectador sabe que algo cambió | `listo`, `pago`, `recupera`, `notificacion` |
| **Explicación** | una idea que no se entiende solo con texto | `pasos`, `timeline`, `bento`, `bars`, `pie` |
| **Evitar un cambio brusco** | el corte de un plano al siguiente no se siente como salto | `kenburns`, `versus`, `capa_salida` |
| **Feedback** | la acción del espectador (o del proceso) se acusa recibo | `chat`, `buscador`, `demo`, `comentario` |
| **Deleite** | el momento que se recuerda | `confetti`, `countdown`, `oferta` (solo si el brief lo pide) |

Regla de la casa: **un protagonista por plano**. Si dos elementos se mueven a
la vez, uno de los dos está de mas.

## 2. Si el cliente pide…

### "Quiero una apertura que enganche"
`apertura` — gancho en dos tiempos: `texto1` entra (150 px), `texto2` lo
sustituye (124 px) con `at.cambio`. La mancha crece desde un punto. Es la
escena de la primera frase de la pieza, no un titular generico.

### "Quiero señalar un dato dentro de una captura"
`callout` — elipse que se dibuja sobre el punto exacto + etiqueta con placa.
`captura` es la imagen, `objeto{x, y, r}` el punto (fracciones de la captura),
`etiqueta` lo que se lee. El texto va sobre placa oscura: blanco sobre
captura clara no se lee.

### "Quiero advance what we'll see / an index"
`index` — lista numerada de lo que viene, con el paso activo en acento.
`items[{texto, activo?}]`, entrada escalonada.

### "Quiero una apertura de capitulo con particulas"
`orbOpen` — las particulas CONVERGEN a una figura (`esfera`, `chat`, `robot`)
y entra el titular. Distinto de `orbita`: alli orbitan, aqui se forman.

### "Quiero que se vea mi producto"
`demo` — ventana de app con capturas reales, cursor que viaja de un punto a
otro y zoom a la zona que se toca. **El cursor usa `track()`**: un resorte por
cambio, para que llegue con peso y no frene entre tramos. Captura de verdad:
no se dibuja lo que no existe.

### "Quiero una pantalla de bienvenida / hero de producto"
`hero` — píldora superior, titular con acento, subtítulo y tarjeta central con
la cifra clave. **Ojo**: el subtítulo se dibuja en 2 lineas; si necesita 3, la
tercera se pierde (el linter lo avisa).

### "Quiero una lista de caracteristicas / servicios"
`bento` — 2 a 4 tarjetas Liquid Glass. **El motor dibuja 4**: una quinta
tarjeta se pierde en silencio (el linter lo avisa). Con 3 items, una sola
columna.

### "Quiero mostrar tres o cuatro datos"
`stats` — rejilla de cifras grandes con etiqueta. `bars` para comparar
magnitudes, `ranking` para ordenar, `gauge` para una escala circular, `pie`
para partes de un todo.

### "Quiero explicar un proceso / los pasos"
`pasos` — 1 a 5 pasos en columna (9:16) con el paso activo brillando.
`timeline` si lo que hay es una línea de tiempo con fechas.

### "Quiero comparar dos cosas"
`versus` — dos columnas con su rótulo; el acento va en la que defiendes.

### "Quiero una cita de un cliente"
`quote` — la confianza antes que el movimiento: entra despacio, sin rebote.
`comentario` si el testimonio viene con autor, usuario y fecha (estilo
review/red social).

### "Quiero un testimonio con captura de pantalla"
`comentario` — avatar, verificado, estrellas y likes animados.

### "Quiero que se vea una notificacion / alerta"
`notificacion` — cascada estilo push: entran desde arriba con resorte fisico y
empujan a las anteriores hacia abajo.

### "Quiero una conversacion"
`chat` — burbujas que entran escalonadas y empujan la conversacion.
`medianoche` para un telefono 3D con notificaciones a las 00:47.

### "Quiero un buscador / spotlight"
`buscador` — barra con lupa de acento y cursor intermitente.

### "Quiero una linea de tiempo de datos"
`canales` — "todos tus canales, un lugar": donde esta cada cosa que vigila.

### "Quiero pasar el relevo / traspasar algo"
`handoff` — persona + contexto + temperatura: el traspaso se ve con su
informacion, no solo con un nombre.

### "Quiero una tabla de oportunidades / leads"
`leads` — tabla priorizada con la fila 1 destacada.

### "Quiero un precio / una oferta"
`oferta` — un descuento, un codigo, un CTA. `pago` para el comprobante y
`recupera` para el pago recuperado.

### "Quiero un momento de celebracion"
`confetti` — confeti determinista (semilla fija: el render es reproducible) +
texto. `listo` para el check con estallido. `countdown` para una cuenta
regresiva exacta: el numero es funcion del tiempo.

### "Quiero una cita de un libro / un texto que se escribe"
`typewriter` — caracter a caracter, a ritmo constante. `kenburns` para una
imagen con zoom y paneo progresivo (es una foto, no una escena de datos).

### "Quiero un plano de fondo con la imagen"
`kenburns` — el fondo de la pieza cuando lo que importa es la foto, no el dato.

### "Quiero que el copy se escriba y se lea, palabra a palabra"
`frase` — la frase entra palabra a palabra y lo ya dicho se desvanece; la
palabra clave va en blanco y en negrita sobre el gris. Es la escena del copy
que se LEE (un reel de copy, un dato que se explica), no del titular que
golpea. `typewriter` es el otro: caracter a caracter, con cursor, para una
cita o una transcripcion.

### "Quiero dejar constancia de lo que quedo confirmado y lo que quedo pendiente"
`constancia` — el acta de la pieza: un panel con el guion de arriba y N
casillas, cada una con su marca (✓ lo confirmado, ○ lo pendiente) y su texto
en versalitas. Es la escena del reel de "cara" (`De8KNkdDT68`). Sirve para
acordar con el cliente: lo que ya se hizo, lo que esta en juego y lo que
queda por delante. `listo` es el caso de UN solo estado (una sola explosion);
`constancia` es la lista.

### "Quiero el cierre de marca"
`final` — isotipo, lema con acento y boton. Va SIEMPRE al final, y su
`at.lema` cae despues de que el plano ya esta asentado.

## 2b. Rotacion: no usar siempre las mismas

Este indice da UNA escena por intencion, y esa es la trampa: si cada pieza
resuelve «dato» con `stats` y «cierre» con `final`, todas las piezas se
parecen aunque el catalogo tenga 39 tipos. La escena se elige por el
argumento, y dentro de la misma intencion hay familia para rotar. La tabla
de abajo ES `scripts/data/repertorio.json` (la única fuente; si difieren,
manda el JSON y `repertorio.py validar` lo dice):

| intencion | familia (rota segun el argumento y la pieza anterior) |
|---|---|
| gancho | `apertura`, `hero`, `countdown`, `buscador`, `pildoras`, `orbOpen` |
| dato | `stats`, `bars`, `ranking`, `gauge`, `pie`, `bento` |
| proceso | `pasos`, `timeline`, `orbita`, `leads`, `handoff`, `hoy` |
| social/testimonio | `chat`, `comentario`, `notificacion`, `quote`, `medianoche` |
| cierre | `remate`, `final`, `oferta`, `confetti`, `audiowave` |
| comparacion | `versus`, `bars`, `ranking` |
| demostracion | `demo`, `callout`, `buscador` |
| estado | `listo`, `pago`, `recupera`, `notificacion`, `constancia` |
| imagen-texto | `kenburns`, `typewriter`, `rotulo_inferior`, `quote` |
| estructura | `index`, `canales`, `medianoche` |

Una escena puede servir a varias intenciones (`bars` da un dato y también
compara): por eso las 39 escenas del motor quedan alcanzables, incluidas
las que la antigua tabla dejaba fuera (`versus`, `demo`, `callout`,
`kenburns`, `typewriter`, `listo`, `pago`, `recupera`, `index`, `canales`,
`medianoche`, `orbOpen`, `rotulo_inferior`).

El mecanismo, no la memoria del agente:

```bash
python scripts/repertorio.py sugerir --intenciones gancho,dato,proceso,cierre --anterior ../pieza-anterior/plan.json
python scripts/repertorio.py cobertura plan.json
python scripts/auditar_plan.py plan.json --anterior ../pieza-anterior/plan.json
```

`sugerir` elige una escena por intención rotando la familia de forma
determinista (misma `--semilla`, misma mano) y evitando los tipos de las
piezas anteriores mientras la familia tenga otra opción; si no la tiene,
lo dice (`reutilizada`). Antes de elegir, mira que tipos uso la pieza
anterior del proyecto (su plan o `PROGRESO.md`): no repitas su tipo
dominante si el argumento no lo pide. `auditar_plan.py` avisa dentro de la
pieza (`poco-repertorio`: solo 2–3 tipos o un tipo en la mitad) y entre
piezas (`ruta-repetida`, solo con `--anterior`); `demo_plan.json` es un
ejemplo trabajado, no la plantilla por defecto.

Y lo que no se usa no se olvida: el plan declara sus intenciones y el
porqué de las que descarta (`"intenciones": [...]`,
`"no_aplica": {"demostracion": "sin capturas reales"}`).
`repertorio.py cobertura` lista cada intención sin tocar como declarada o
SIN DECLARAR, y el auditor avisa (`intencion-sin-escena`,
`intencion-olvidada`) cuando el plan declara y no cumple.

## 3. Receta de movimiento por escena

Los resortes del motor, con el **overshoot medido** (el valor de la
animacion se pasa de su objetivo y vuelve):

| escena | resortes (stiff, damp) | overshoot | como se siente |
|---|---|---|---|
| `apertura` | 60, 10 (mancha) | 7 % | la mancha entra expandiendose |
| `final` | 70, 12 / 120, 14 | 3,9 % / 7,4 % | sobrio: el cierre no compite |
| `listo` | 90, 10 | 14,2 % | el check estalla |
| `oferta` | 170, 12 | 19,6 % | **slam**: aterriza desde un poco mas grande |
| `remate` | 120, 11 | 16,1 % | **slam** del gigante (1,6 → 1,0) |
| `countdown` | 150, 13 | 14,0 % | el numero se asienta con rebote |
| `orbita` | 100, 13 / 120, 15 | 6,8 % / 5,2 % | el nucleo late, los anillos giran |
| `quote` | 110, 14 / 130, 16 | 6,0 % / 4,5 % | entra despacio: es confianza |
| `comentario` | 100, 13 | 6,8 % | tarjeta que aterriza suave |
| `audiowave` | 100, 13 | 6,8 % | la onda respira, la tarjeta entra |
| `bento` | 130, 15 / 130, 16 | 6,4 % / 4,5 % | cascada de tarjetas |
| `chat` | 120,14 / 140,15 / 160,16 | 7,4 / 7,6 / 7,7 % | burbujas que empujan |
| `notificacion` | 120, 15 | 5,2 % | push-down con resorte |
| `pasos` `bars` `ranking` `stats` `timeline` `pie` `leads` `confetti` `versus` `hero` `buscador` `medianoche` `canales` `handoff` `pago` `recupera` `hoy` | 110-140, 13-16 | 4-10 % | la banda media del catalogo |

Sobre el techo de overshoot: `references/fluidez.md` fija un 8 % general. Los
valores de 14-20 % de `oferta`, `remate`, `listo` y `countdown` **no lo
incumplen**: esos resortes alimentan un *slam* (la escala viene desde arriba y
se asienta), no un rebote por encima del objetivo visible.

Y el parametro que casi todos olvidan: **el cursor de `demo` usa `track()`
** (`stiff=260, damp=26`, 1,4 %): un resorte por cambio, sumados. El
movimiento sigue continuo aunque dos tramos se solapen, y sigue siendo
funcion pura del tiempo.

## 4. Si la escena no funciona: la jerarquia de reparacion

En este orden, y parando en cuanto se arregla:

1. **Quita el movimiento.** Si el plano no pide animacion, no la hay.
2. **Redúcelo.** Menos recorrido, menos elementos, menos tiempo en pantalla.
3. **Corrige la curva.** Entrar: `ease_out`. Mover lo que ya esta en pantalla:
   `ease_in_out`. Nunca lineal.
4. **Corrige el origen y la fisica.** El resorte entra desde donde saldria el
   elemento (abajo desde abajo), no desde el centro. Overshoot medido, no
   inventado.
5. **Hazlo interrumpible.** Si algo vuelve a dispararse antes de que el
   anterior termine, **no se reinicia el resorte**: se usa `track()`.
6. **Asimetria.** La entrada y la salida no duran lo mismo: la parte
   deliberada es lenta, el asentamiento es rapido.
7. **Pulido.** Solo aqui: sub-frames de motion blur, grano, velo.

Y el diagnostico inverso: **"el movimiento esta mal" casi nunca se arregla
añadiendo movimiento**. Se arregla quitando, reduciendo o cambiando la curva.

---

→ Canónico: `references/animacion.md` · Dominio: movimiento · Vecinos: `references/escenas.md`, `references/copy.md`, `references/fluidez.md`
