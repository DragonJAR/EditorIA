# Recetas operativas: video con IA por código

Métodos de producción destilados de la colección Opus 5.5
(skillry.dev/ai-videos/opus-5-5, extracción 2026-10-04). Son recetas, no
teoría: cada una dice cuándo aplica, qué hacer, en qué orden y con qué
herramienta del skill. Las plantillas de prompts verbatim viven en
`references/prompt-motion-graphics.md`.

## 1. Pipeline de 3 agentes para batch de animaciones (stokebuilder)

Cuándo: decenas de animaciones con la misma identidad (podcast visual,
serie de explainers, campaña por capítulos). El caso real: 50 animaciones
de podcast generadas con Opus 5.5.

El método, en orden:

1. **Style bible + component kit PRIMERO.** Un agente escribe la biblia de
   estilo y el kit de componentes antes de animar nada. Todo lo que salga
   después debe verse como el mismo show. Sin esto, 50 animaciones son
   50 videos distintos.
2. **Finder (effort extra-high).** Recorre el material completo y marca
   cada timestamp donde una animación puede llenar espacio y enganchar,
   con un concepto por marca. Sé agresivo y sobre-inclusivo.
3. **Builder (effort medium).** Construye cada animación contra la biblia.
4. **Judge (effort extra-high).** Juzga cada una UNA vez: consistencia de
   marca con las demás, interés visual, relevancia narrativa, criterio
   creativo. **Solo lo atroz vuelve a build. Sin loops de redo
   generalizados.**
5. **Ensamble.** PiP del hablante en cada visual full-screen; carpeta con
   las animaciones individuales además del corte final.

Reglas que lo sostienen (del prompt original):

- Copy verbatim o fiel a lo dicho. Nunca inventar hechos, cifras o citas.
- Cada animación sincroniza sus beats con las palabras habladas.
- Cada gráfico vive dentro de un tramo de audio sin cortar; dejar caras
  entre gráficos.
- Con cámaras: nada de punch-ins ni zooms sobre el hablante.

Mapeo a EditorIA: finder/builder/judge son pasadas del agente con
distinto brief (no necesariamente subagentes). El ensamble va en
ffmpeg, HyperFrames o Remotion según el motor elegido. El judge NO
sustituye el loop cerrado: el render final pasa por
`references/auto-qa.md` igual que cualquier pieza.

## 2. Revisión por contact sheet antes de renderizar (l3d1c)

Cuándo: video generado por código (Remotion/HyperFrames) donde cada
render completo cuesta minutos. El caso real: launch ad en Remotion
hecho en 1 hora sin abrir un editor de video.

El método: en vez de mirar renders, renderizar ~20 stills y mosaicarlos
en **un solo contact sheet** para revisar el corte entero de un vistazo
y pedir cambios en lenguaje natural. Solo después se renderiza el video.

Herramienta: `scripts/contact_sheet.py`:

```
python3 scripts/contact_sheet.py --dir stills/ -o sheet.png
python3 scripts/contact_sheet.py --video corte.mp4 -n 20 -o sheet.png
```

Detalles que lo hacen funcionar (del caso real):

- **Captions medidos en la fuente real** y encogidos para caber en la
  safe zone 9:16 (nada bajo los botones de TikTok). En EditorIA:
  `scripts/ffmpeg_tools/caption.py --max-lines --min-size`.
- **Cada corte cae en una grilla de 120 BPM** (`scripts/beat_grid.py`
  para analizarla, `scripts/beat_sync.py` para ajustar los cortes).
- **Un codebase, N cortes**: los cortes de 30/15/6 s en 16:9 y 9:16 son
  listas de escenas distintas sobre el mismo código, no proyectos
  distintos.

Diferencia con `auto_qa.py`: ese hace QA de un render terminado; esto
revisa el CORTE antes de pagar el render. Uno no sustituye al otro.

## 3. Sincronía frame-exacta con beat file compartido (apoorvjain25)

Cuándo: la música y los visuales deben golpear en el mismo frame y no
basta con "cortar al beat a ojo". El caso real: ad de 51 s donde la
música se compuso nota por nota en Python y cada evento en pantalla cae
sobre un blip en el mismo frame.

El método: la música generada por código **lee el mismo beat file que
los visuales**. No hay dos fuentes de tiempo: hay una. Cada golpe visual
y cada nota salen del mismo archivo, así que coinciden por construcción.

Herramienta: `scripts/beat_file.py` — crea el beat file canónico:

```
python3 scripts/beat_file.py --bpm 120 --duracion 30 \
    --seccion "intro:0:8" --seccion "drop:8:30" -o beats.json
```

El generador de música y el código visual leen `beats.json`; nadie
hardcodea tiempos. Verificado en lab: composición Remotion con 4 golpes
cinéticos cayendo exactamente sobre los beats del archivo
(`~/workspace/lab-remotion2`, composición `BeatHits`).

Relación con lo existente (no duplica):

- `scripts/beat_grid.py` ANALIZA música ya hecha (extrae BPM y beat0).
- `scripts/beat_sync.py` AJUSTA cortes existentes a esa grilla.
- `scripts/beat_file.py` AUTORA el beat primero y todo lo demás lo
  consume. Si la música ya existe, usa `beat_grid`; si la compones tú,
  usa `beat_file`.

## 4. Real-assets-first (doctrina)

De la colección: los resultados que se ven premium usan assets reales,
no placeholders. Receta:

1. **Lee la landing y el codebase** para sacar historia, copy, colores,
   fuente y logo reales (caso @aschapmann; caso l3d1c: importar los
   tokens CSS y las fuentes del sitio para que el video use el mismo
   design system que el producto).
2. **Traza el logo a SVG** para que siga nítido y animable (nunca un
   PNG enmarcado).
3. **App real, datos reales**: pantallas grabadas del simulador o del
   producto, queries corridas contra la BD real (@jesscaroline7).
4. **1-2 videos de referencia + storyboard ANTES del video**
   (@elliot_garreffa). Disciplina de referencias: de cada referencia
   solo se toma lo nombrado (ver `references/checklist-qa.md`).

En EditorIA esto es la regla "verificar antes de afirmar" llevada a
producción: si el asset no es real, el video no sale.

## 5. Pre-flight para video por código

Antes de pedirle a un modelo que genere video por código (HyperFrames,
Remotion o el motor Python), checklist mínimo:

1. Brief con copy real (nada de placeholders).
2. 1-2 referencias nombrando QUÉ se toma de cada una.
3. Storyboard o lista de escenas con duraciones.
4. Motor elegido con criterio (ver "Selector de motor" en SKILL.md).
5. Beat file (`scripts/beat_file.py`) o grilla (`scripts/beat_grid.py`)
   si la música tiene golpes que sincronizar.
6. Plan de revisión: contact sheet pre-render
   (`scripts/contact_sheet.py`) + loop cerrado (`references/auto-qa.md`).
