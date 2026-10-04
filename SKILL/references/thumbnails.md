# Thumbnails — craft + workflow con review-gate

EditorIA diseña thumbnails como parte de la entrega de un video (YouTube 16:9,
vertical 9:16 para shorts): craft y proceso propios. Generar con el motor de
imagen que EditorIA tenga disponible.

Paleta del brand pack (ej. DragonJAR: negro `#0A0A0A` de fondo, rojo `#C11B05`
para marca y glow, blanco cálido `#FAF8F6` para texto; tipografía de titulares
del pack en ExtraBold para toda la tipografía del thumbnail). En modo libre,
una paleta equivalente: neutro oscuro + un acento + neutro claro.

## Brief del thumbnail (extracción del guion)

Antes de diseñar, extraer el brief con estas reglas:

- **Tensión > información**: el thumbnail no resume el video — abre un loop.
  La pregunta que deja picando vale más que el dato que entrega.
- **Open loop**: debe haber algo sin resolver (una mirada, un contraste, un
  "¿qué pasó?") que solo el video cierra.
- **Thumbnail + título como sistema**: se completan, nunca se repiten. Ninguna
  palabra del título aparece en el thumbnail.
- **Filtros de selección**: ignorar lo interesante pero no visual; binarizar
  las tensiones (elegir UN contraste); la frase que la audiencia discutiría;
  identidad del viewer (¿para quién es este video?).
- **Test del diseñador**: ¿un diseñador lo vuelve visual en 3 segundos? Si la
  idea necesita explicación, no es thumbnail.

## Reglas de craft

1. **Composición — rule of thirds**: dividir el frame en una grilla 3×3; la
   cara, el elemento héroe y el texto van SOBRE las líneas o intersecciones.
   Default: cara en un tercio, texto gancho en otro, héroe sobre una línea.
2. **Color y branding**: una sola paleta reutilizable en todos los thumbnails
   (la del brand pack; ej. DragonJAR: negro + blanco + un gris medio + rojo
   `#C11B05` como acento — nunca un segundo acento). Para que cada video se
   sienta fresco sin salirse de marca, variar el highlight dentro de la paleta
   (un detalle en blanco, el gris medio
   en otro rol, el glow rojo con distinta intensidad).
3. **Tipografía**: una sola cara consistente en todos los thumbnails: la de
   titulares del brand pack (o la elegida en modo libre), en ExtraBold,
   condensada por el formato. La consistencia vence a la novedad.
4. **Los 8 tipos que funcionan**: shock/emoción (la reacción al momento más
   fuerte), big things/big numbers ($600M, +24, ×16), minimal (un frame + una
   pregunta curiosa; destaca por calmado entre thumbnails ruidosos), social
   hacking (una cara famosa del nicho SOLO si el video trata de ella),
   creador + algo más grande, comparación (antes/después, X vs Y),
   blur/oculto (difuminar el resultado para crear click), objeto raro de
   marca (un logo o algo que dispare "¿qué es eso?").
5. **Combinar 2–3 fórmulas**: los thumbnails virales apilan tipos (ej.
   big-number + comparación + shock). Cada concepto debe nombrar las 2–3
   fórmulas que combina. Mantener 2–3 estilos por ~5 videos para que la
   audiencia aprenda el look, luego evolucionar.
6. **Inspiración cross-nicho**: copiar layouts del propio nicho te convierte
   en copia; traer ideas de nichos distintos hace que el thumbnail destaque
   en el feed del nicho del video. Mantener los elementos de marca intactos.
7. **Palabras**: ≤4 palabras siempre, y ninguna palabra del título del video
   (el thumbnail completa el título, nunca lo repite). Opciones: un big number;
   una afirmación bold/contraria a una creencia común; o **nada** — la imagen
   puede cargarla sola. El texto debe aportar lo que el título no dice.
8. **Finishing** (después de generar, en editor): outline duro + sombra en el
   texto, guardar el estilo como reutilizable; darkened detrás del texto
   (pincel suave sobre fondo ocupado); re-colorear el fondo a la paleta;
   blur gaussiano al fondo que compita con el sujeto; grado de color final.
   La legibilidad manda sobre todo.
9. **Test antes de publicar**: ver el thumbnail en un mockup de homepage, a
   tamaño de móvil, entre otros thumbnails. Si se lee claro y destaca → ship;
   si no → de vuelta al boceto.

## Formato de concepto (estandarizado, barato, se aprueba antes de generar)

Generar ~5 conceptos genuinamente distintos (ángulos, no variaciones del
mismo). Cada uno con este formato:

```
### Concepto 01 — {nombre gancho}
- Texto grande: "…" (≤4 palabras)
- Emoción/expresión: {shock, curiosidad, tensión, alegría… + gesto}
- Escena: {fondo diseñado, iluminación, ambiente}
- Composición: {cara en tercio derecho, texto izquierda, elemento héroe…}
- Por qué funciona: {fórmula 1 + fórmula 2, curiosity gap, stakes…}
- Referencia: {técnica tomada de inspiración cross-nicho, en palabras}
```

## Técnica de prompt (orden fijo)

Construir el prompt de generación en este orden:

1. **Sujeto + expresión**: quién y con qué emoción genuina (nunca pose de
   stock; shock real, contemplación, curiosidad).
2. **Vestuario/persona** si es relevante para el brief.
3. **Escena + fondo**: iluminación y mood. Default ganador: sujeto
   cinematográfico con luz lateral fuerte y rim light, compuesto sobre un
   fondo negro/charcoal diseñado con glow radial del acento detrás del
   sujeto — NO una escena fotográfica completa (eso se lee "movie still",
   no thumbnail).
4. **El texto**, entrecomillado y con estilo: la palabra clave en el acento
   del pack, el resto en el neutro claro; pocas palabras = render más limpio. Si el
   texto sale corrupto: generar sin texto y componerlo en editor.
5. **Composición + formato**: 16:9 (o 9:16), sujeto en el tercio indicado,
   alto contraste, foco nítido.
6. **Técnica tomada** de una inspiración, descrita en palabras (nunca "copia X").

## Calibración (reglas del estilo ganador — ejemplo con el pack DragonJAR)

> Esta calibración es la del estilo que ganó en producción con el pack
> DragonJAR. Con otro pack o en modo libre, sustituir "rojo de marca" por
> el acento del brand pack (o del modo libre) y "fondo oscuro" por el fondo
> correspondiente.

- Sujeto cinematográfico + thumbnail diseñado. El sujeto con calidad de cine;
  el fondo, diseñado (negro sólido/charcoal o glow radial del acento).
- **Sin sticker blanco**: sin borde de recorte blanco alrededor del sujeto;
  fundirlo al fondo oscuro con el glow del acento + rim light.
- **Sin glow blanco**: el glow detrás del sujeto es del acento, nunca
  blanco.
- **Sin luz de color en la cara sin fuente visible** en la escena.
- Elemento gráfico: UNO solo, limpio (una flecha, un chip, un big number, una
  tarjeta de cliente). Equilibrar sujeto vs gráfico; ni uno aplasta al otro.
- Personas en elementos gráficos = fotos reales, nunca avatares ilustrados.
- Tipografía premium: bold, limpia; si parece hecha en 5 minutos con una
  cámara, no es suficiente.

## Workflow con review-gate

1. Leer el video/guion: extraer el momento más fuerte (ver
   `scoring-shorts.md`), la cifra héroe y la promesa.
2. Escribir 5 conceptos en el formato de arriba.
3. **Review-gate**: presentarlos al usuario; él aprueba/ajusta. Nada se genera
   antes de su aprobación (el texto es barato; generar es caro).
4. Generar el concepto aprobado. Para composición determinista sobre un
   frame (texto ≤4 palabras, marca, tercios):
   `scripts/ffmpeg_tools/thumbnail.py frame.png --texto "..." --resaltar ...`
   (el brief creativo lo hace el agente; la herramienta ejecuta el craft).
5. Iterar por UN eje a la vez (expresión, fondo, texto, color); las variantes
   se mantienen distintas.
6. Upscale / versión final del ganador + finishing.
