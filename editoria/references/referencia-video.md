# Referencia de video — leer, adaptar y recrear

Cuándo: el usuario trae un video (archivo o enlace) y pide "hazme uno así",
"este mismo con mi producto", "en español", "con mi cara", o quiere aprender
por qué funciona. Clonar una referencia es la vía más rápida a una pieza que
ya demostró retener atención; no es copiar píxeles: es entender qué hace cada
decisión por el espectador y recrear esa relación con el contenido nuevo.

Método destilado de Hypit (hypit-ai/hypit, guías de reference video,
transformations, brief y project files), reescrito para las herramientas
de EditorIA. Complementa `references/ritmo.md` (medir la cadencia de la
referencia) y `references/video-real.md` (editar grabaciones).

## 1. Abrir el proyecto y su memoria

```bash
python scripts/proyecto.py ~/videos/{proyecto} --referencia "{url o archivo}"
```

Crea `BRIEF.md`, `TRATAMIENTO.md`, `PROGRESO.md` y, por referencia,
`referencias/{nombre}/TIMELINE.md` y `evidencia/`. Nunca sobrescribe;
imprime los comandos para ingerir (`scripts/clonar_video.py analizar`, que
deja ahí la fuente, `ANALYSIS.md`, `plantilla.json` y el contact sheet),
transcribir y mosaicar.
Cada archivo tiene UN trabajo:

| Archivo | Qué guarda | Quién lo cambia |
|---|---|---|
| `BRIEF.md` | lo que el usuario pidió, con sus palabras; hechos exactos; límites; gasto acordado | solo cambia cuando cambia la verdad del usuario |
| `TRATAMIENTO.md` | tu respuesta creativa: premisa, arco, sistemas, cómo se propagan los cambios | cuando el diseño está mal (no cuando la implementación falla) |
| `ANALYSIS.md` | por qué funciona la referencia entera (borrador automático de `clonar_video.py`, que tú completas) | cuando la lectura cambia |
| `TIMELINE.md` | qué pasa cuándo en la referencia y qué hace por el espectador | al descubrir detalle nuevo |
| `PROGRESO.md` | foto del ahora: pregunta viva, lo que falta, siguiente acción, material reutilizable | en cada avance |

Son memoria, no bitácoras: se **reescriben** cuando su verdad cambia. Al
retomar (otra conversación, contexto compactado) se leen primero y se sigue
desde el material producido (voz.mp3, palabras.json, renders): perder el
contexto nunca es razón para volver a pagar TTS o música.

## 2. Traer la referencia

```bash
python scripts/clonar_video.py analizar --url "{url}" -o referencias/{nombre}
# o solo la ingesta: python scripts/referencia.py --url "{url}" -o referencias/{nombre}
```

`scripts/referencia.py` descarga con yt-dlp un solo video aunque el enlace
sea de playlist (H.264 cerca de 1080p, nunca pisa un archivo), extrae
metadatos, audio 48 kHz/16 kHz y un contact sheet; `clonar_video.py` suma
cortes, roles y `plantilla.json`. Anotar la URL en `ANALYSIS.md`. Una referencia se
**estudia**; usar su material dentro de otra pieza requiere permiso del autor.

## 3. Hacer visible el tiempo

1. **Palabras con tiempo**: `python scripts/alinear.py fuente.mp4 -o fuente.palabras.json --idioma es` (sin guion = transcripción por palabra; acepta video). La transcripción es evidencia, no interpretación: un nombre mal reconocido no es un error de pronunciación.
2. **Cortes**: `python scripts/ffmpeg_tools/scenes.py fuente.mp4 --sheet evidencia/cortes.png`. Un corte de cámara ayuda a navegar; no decide qué va junto (un objeto que sobrevive al corte pertenece a un sistema más largo).
3. **Cadencia**: `python scripts/verificar_ritmo.py fuente.mp4` sobre la referencia (regla dura de `references/ritmo.md`).
4. **Mosaicos con palabras** (`scripts/contact_sheet.py`), a la escala de la pregunta:

| Pregunta | Mosaico |
|---|---|
| El argumento entero, qué sistemas persisten | `--video fuente.mp4 --cada 1 --palabras fuente.palabras.json --filas 4` |
| Qué cambia en una frase | `--alrededor "{frase}" --palabras ... --cada 0.2` |
| Cómo entra, se asienta o sale algo | `--inicio 6.8 --fin 8.4 --todos-los-frames --cols 4 --filas 3` |
| Leer tipografía o geometría | `--en 7.3 --ancho 960` |

Las palabras van DEBAJO de cada cuadro (los subtítulos y gráficas originales
quedan a la vista). Las muestras tienen huecos: un evento breve entre dos
tiles no aparece. Densificar donde la explicación lo pida; unos pocos stills
no son un relato temporal. Guardar en `evidencia/` solo lo que vale la pena
reabrir, con nombres que digan la pregunta (`lista-cambia.png`).

## 4. Leer: el todo y el detalle se corrigen entre sí

Ver la pieza entera primero: gancho, argumento o historia, giros de atención,
payoff, respuesta buscada. Formar una explicación provisional de por qué
funciona. Luego, cada **sistema** (subtítulos, gráficas, B-roll, tipografía,
efectos, sonido) se describe por:

- **contenido y aspecto** — qué muestra, jerarquía, paleta, tipografía;
- **posición** — dónde vive y qué deja libre (la cara, el producto);
- **entrada, comportamiento, permanencia y salida** — trayectoria, escala,
  opacidad, rebote o asentamiento, cuánto se queda;
- **a qué responde** — la palabra, la pausa o la acción que lo dispara;
- **qué hace por el espectador** — presenta a alguien, contrasta dos
  afirmaciones, acumula prueba, amplifica una reacción, cede la atención.

El nombre de un movimiento ("pop") es solo el comienzo: medir su trayectoria,
su ritmo y su relación con los eventos vecinos. Una nueva entrada puede
**reemplazar**, **sumar** a una colección o **tapar** temporalmente: seguir
el estado del sistema a lo largo de la pieza. Cuando algo desconcierta,
ampliar la mirada (palabras cercanas, apariciones previas, consecuencias).
Escribir lo observado separado de lo interpretado; lo que no se puede
sostener con la evidencia queda como pregunta abierta en su tiempo.

Hablar mientras se lee: compartir en la conversación los hallazgos concretos
y un mosaico cuando haga tangible la relación. Los archivos guardan el
detalle; la conversación lleva el sentido y deja que el usuario aporte gusto.

## 5. Escribir ANALYSIS y TIMELINE

`ANALYSIS.md` = el modelo de la pieza entera (el borrador automático da
cortes y roles; la lectura la escribes tú). `TIMELINE.md` = secciones por
tiempo de la fuente y fase con sentido. Ejemplo de sección:

```md
## 6.07–8.27 · La carga de trabajo se acelera

La lista hablada llega a "videos / voces / anuncios / guiones". Cada
sustantivo trae una ilustración a pantalla completa y una palabra en
marcador al centro, que reemplaza a la pareja anterior; el subtítulo de
abajo cede el lugar a esa etiqueta para que se lea como una unidad.
Palabra e imagen entran juntas en cada sustantivo, hacen pop, se asientan
y salen con el siguiente corte. Las esperas cada vez más cortas hacen que
la carga se sienta excesiva. Evidencia: evidencia/lista-cambia.png.
```

Un sistema persistente (un tablero, una cama musical, un estilo de
subtítulo) se documenta una vez y se ubican sus cambios en el tiempo.

## 6. Transformar: conservar el rol, recrear la forma

En una adaptación fiel, lo que el usuario no menciona **se hereda**:
estructura, rol de cada capa, relación promesa/payoff, sistemas visuales y
sonoros. Preguntar solo lo que cambia materialmente el encargo (objetivo,
hechos privados, gasto); el casting de recursos, la dirección de arte y la
implementación son del agente.

Antes de reemplazar algo, entender todos sus papeles: un presentador puede
ser también avatar, voz, sujeto de B-roll e identidad dentro de una gráfica;
un producto puede ser utilería, pantalla, demostración, afirmación y CTA.
Transformarlo en **todas** sus manifestaciones. Lentes útiles:

- **sujeto o identidad** — quién carga el rol narrativo y dónde aparece;
- **producto o marca** — verdad del producto, uso, UI, prueba, oferta, CTA
  (con brand pack: fidelidad total, `references/brand-packs.md`);
- **guion, idioma o CTA** — sentido, ritmo del habla, texto en pantalla y los
  tiempos que siguen a las palabras nuevas;
- **plataforma, duración o aspecto** — qué funciones sobreviven, se comprimen
  o piden otra composición (`scripts/ffmpeg_tools/verticalizar.py`);
- **estilo o tono** — arte, subtítulos, tipografía, gráficas y sonido a la vez
  (`references/tonos.md`), sin borrar la estructura que funciona;
- **añadir o quitar un sistema** — redistribuir el trabajo que hacía, no dejar
  un hueco narrativo;
- **varias referencias** — pocas y complementarias, cada una con UN rol
  escrito en `TRATAMIENTO.md` (ej.: A = tipografía y lettering, B =
  transiciones y ritmo, C = color y composición); se toma de cada una su
  técnica (animación, ritmo, composición), no su superficie. No mezclar
  todos los detalles de cada una.

La forma no se copia si ya no encaja: se conserva el **propósito** de una
acción o una composición con la forma que tenga sentido para el nuevo
sujeto, producto y plataforma.

### Los tiempos siguen a las palabras, no a los segundos

Un guion nuevo mueve los segundos; la relación se conserva. Si en la
referencia un ícono entra cuando se nombra al jugador y se asienta con el
veredicto, en el plan nuevo ese `at` se ancla a la palabra equivalente del
guion nuevo: `scripts/speech_estimate.py` estima la duración antes del TTS y
`scripts/alinear.py` da el tiempo real de cada palabra después
(`references/plan-video.md`). Solo se copia un intervalo de reloj cuando el
intervalo mismo es parte del diseño.

## 7. Revisar la reconstrucción por función

Usar `ANALYSIS.md` y `TIMELINE.md` como mapa de preguntas. Comparar fuente y
pieza nueva en las **palabras o acciones correspondientes** (no en el mismo
segundo): mosaicos de ambos tramos con `--alrededor` y `--palabras`. El
elemento transformado debe cumplir el mismo papel, no verse igual. La
entrada atrapa, la espera da tiempo de lectura, el movimiento explica un
cambio, la salida libera la siguiente idea. Después, el checklist completo
(`references/checklist-qa.md`) y la rúbrica (`references/rubrica-premios.md`).

## 8. Dónde se corrige cada hallazgo

| La revisión muestra que... | Se corrige en |
|---|---|
| la historia, la lógica de planos o un sistema visual están mal | `TRATAMIENTO.md` (y luego el plan) |
| palabras, hablantes o el texto de una voz están mal | el guion / campo `voz` del plan.json |
| composición, tiempos `at` o parámetros están mal | plan.json o los flags del script |
| una escena o herramienta no puede expresar el diseño | el script (y la lección con `registrar_aprendizaje.py`) |
| el objetivo del usuario cambió | `BRIEF.md`, solo por pedido del usuario |

Antes de cambiar: conectar el problema con su consecuencia y la mejora
buscada (alargar una espera hace legible una comparación). Después: mirar el
tramo cambiado con sus relevos y juzgarlo dentro de la pieza entera.

## 9. Gasto

Antes de cualquier trabajo pagado (TTS, música IA), acordar con el usuario
qué cubre y cuánto, y anotarlo en `BRIEF.md`. Lo que exceda ese acuerdo es
decisión del usuario. `PROGRESO.md` lleva el gasto real frente al acordado.

---

→ Canónico: `references/formatos.md` · Dominio: produccion · Vecinos: `references/modos-rapidos.md`, `references/estilos.md`, `references/copy.md`
