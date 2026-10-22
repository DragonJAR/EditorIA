# Dirección — el listón medido

Guía de dirección de video con métricas: qué separa un video "bien editado"
de uno que se guarda y se comparte.

## El listón en números

- **La música manda desde el primer segundo**: el groove arranca al inicio y
  no se cae. Rango de trabajo: 100–129 BPM — enérgico, no frenético.
- **Movimiento constante**: algo se mueve en el 67–100% de los frames
  (se satisface con micro-idle — respiración ±4–6px — no con impactos);
  45–91 hits visuales por minuto **solo en piezas de alta energía**, la
  mayoría sobre el beat (cortes uno o dos frames antes, a propósito).
  El contenido necesita calma: el movimiento constante no es saturación
  (ver "Saturación: dinámico ≠ lleno" en `principios.md`).
- **Pocos cortes duros, a veces ninguno**: una pieza puede ser una sola toma
  continua sostenida por morphs y movimientos de cámara. (Con un brand pack
  que fije corte seco (`reglas.transiciones`), el corte seco sigue siendo el default
  editorial; el one-shot es una opción de dirección, no la regla.)
- **Copy en statements paralelos cortos**: 1–4 palabras por línea, una palabra
  de acento. Ejemplo de forma: "Corta. Resume. Publica." — la estructura, no
  esas palabras.
- **Un sistema visual por video, un momento firma**: un lenguaje gráfico
  (fondo, easing, tratamiento de texto) y un momento que la gente recuerda.
- **El sujeto real es el héroe**: producto, terminal, interfaz real — no stock
  genérico.
- **Cierre con lockup**: nombre + una línea + a dónde ir, sostenido. Nada
  nuevo después.
- **Los números reales ruedan**: las cifras se cuentan de verdad, con su valor
  exacto en cada frame. Verificación antes de animar.

## Los 10 patrones (qué usar y cuándo)

1. **Una forma, nunca cortar** — un solo elemento que muta (punto → botón →
   tarjeta → píldora), cada cambio en un beat. Para loops de producto.
2. **La pipeline en cuatro palabras** — claims que slamean uno por beat, luego
   el comando se tipea, el grafo vive con un timer. Para plataformas dev e infra.
3. **La terminal como escenario** — la terminal real es el héroe; captions
   tipeados, una palabra de acento. Para CLIs, librerías, open source.
4. **Grilla 2×2** — cuatro mini-escenas sincronizadas que rotan en downbeats.
   Para apps con varios hooks, ads sociales.
5. **Un layout, cada modo** — la misma tarjeta recoloreada por tema/modo, una
   frase de 4 palabras como invitación. Para productos con modos o templates.
6. **La cámara inteligente** — la UI real en una gran tarjeta; un cursor hace
   acciones reales; la cámara zoomea a donde pasa el trabajo. Para demos SaaS.
7. **El hook cinético** — palabras que suben una por beat, la clave en la cara
   de acento; todo se aprieta en un punto que se convierte en la siguiente
   escena. Para los primeros 4–6s de cualquier promo.
8. **El número prueba** — una cifra real enorme; las filas aterrizan una cada
   dos beats con checks, cada una descuenta su monto exacto; el payoff cae en
   el drop. Para fintech, performance, ahorros — cualquier cosa medible.
9. **End card en loop** — todo colapsa al punto inicial: el último frame es el
   primero, y la música también se cierra en loop. Para shorts en loop.
10. **El remake de referencia** — SOLO cuando el usuario lo pide explícito: la
    gramática (timing, transiciones, framing, cámara) se porta; el footage, las
    palabras y los logos nunca.

## Dirección de energía

- La energía del video la deciden las palabras del brief: dinámico/drive/hype
  → groove alto desde los primeros compases; calmado/premium → sin kick o
  groove suave, espacio, colas largas; "calmado y luego explosión" → bajo que
  construye al drop.
- Los cortes siguen la energía: la apertura es lo más apretado del video; lo
  que exige atención lleva más movimiento que lo decorativo.
- Medir el borrador: cuenta hits por minuto y el share en beat. Una pieza
  enérgica debe estar en los rangos de arriba; una calmada más abajo, pero un
  frame quieto fuera del end card es un bug.

## Feedback vago → palancas concretas

"Dale vida", "más premium", "no me convence": nunca tocar el render con una
nota vaga. Traducir a ejes concretos de EditorIA, proponer UNA opción A/B
acotada y preguntar solo si de verdad hay dos lecturas. Tres preguntas
resuelven casi cualquier nota: **¿dónde?** (segundo o escena) · **¿qué eje?**
(color, ritmo, tipo, escala, sonido, mensaje) · **¿comparado con qué?** (un
momento del mismo video que ya funcione, o una referencia).

| Dice | Palancas en EditorIA |
|---|---|
| "más dinámico", "dale vida", "está soso" | cortes más cortos en la apertura (`ritmo.md`), un registro más alto de `fluidez.md` (overshoot, resortes), punch-ins en beats, SFX en hits (`sfx.md`) |
| "más premium", "más elegante" | registro calmo de `fluidez.md` (sin overshoot), más aire, holds largos, un solo acento, grano sutil (`artesanal.py`), transición = corte seco |
| "que resalte", "más punch" | escala del héroe, contraste, el número/frase clave como momento firma (`direccion.md`), subir la mezcla del impacto |
| "muy cargado", "no se entiende" | menos elementos por escena (`principios.md`: saturación), una idea por escena, más tiempo de lectura (`ritmo.md`) |
| "no se ve de marca" | revisar pack: colores, tipos y logo exactos; idioma de transición del pack |
| "se ve barato" | tipografía y espaciado (`coherencia-espacial.md`), easing lineal por accidente, demasiados efectos a la vez |
| "más cinematográfico" | 16:9 / 24 fps (`cine.md`), push-ins lentos, grade y grano, silencio antes del momento firma |

Todo tono lleva su "pero no": "dinámico pero no caótico", "premium pero no
frío". Si el usuario no lo da, proponerlo con la opción A/B. Las notas que
nombran el problema ("la intro se arrastra") se resuelven mejor que las que
dictan la solución ("hazla más rápida"): preferir corregir el problema.

## Reglas de cámara y luz

1. **La cámara sirve a la historia** — nunca se mueve por lucirse. Cada
   movimiento responde a personaje, información o emoción del beat.
2. **Un movimiento por plano** — un solo movimiento principal (+ como mucho
   una acción de enlace continua). Dos movimientos compiten.
3. **Toda luz con fuente explicable** — fijar exposición y balance antes de
   esculpir; si el espectador no puede imaginar de dónde viene la luz, sobra.
4. **Cruces de locación con puente** — dos clips de locaciones distintas se
   unen por puente de sonido o match de acción/forma; nunca fingir plano
   secuencia donde no lo hay.

---

→ Canónico: `references/principios.md` · Dominio: estructura · Vecinos: `references/tonos.md`, `references/ritmo.md`, `references/rubrica-premios.md`
