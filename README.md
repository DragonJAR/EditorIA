# EditorIA

**Navaja suiza de edición de video con IA**, empaquetada como *skill* para Claude.

Crea, edita, resume y mejora videos (`.mp4`): resúmenes animados de reuniones, tipografía cinética, anuncios por plan, films cinematográficos y piezas verticales para redes, para cualquier marca o sin marca.

🇬🇧 [English version](README.en.md)

## Versión

`v1.5.0` — **animación medida, no opinada**: un banco (`scripts/medir_animacion.py`) puntúa cada escena en 9:16 y 16:9 —apariciones de golpe, tirones, arranques sin ease-in, tiempo muerto, densidad de eventos, letra, zona segura y textos que se pisan— y guarda la historia en `SKILL/metricas/historial.jsonl` (catálogo 80 → 99.35/100, 0 pops). Planes de agente robustos: `at` opcional (tiempos desde la muestra de cada escena), avisos de campos mal escritos con sugerencia, error claro en < 1 s, copy largo que encoge o parte en dos líneas. Cifras por idioma (`"numeros": "es"`), banda de subtítulos (`"subtitulos": true`) y subtítulos en la tipografía del kit. Toda opción de toda CLI explicada en `--help`.

Antes, `v1.3.0`: 28 escenas (`oferta`, `demo`, `countdown`, `rotulo_inferior`), overlays con alfa, plantilla × tabla, audiogramas, karaoke por palabra, color BT.709 exacto y QA de fotosensibilidad.

## Estructura

Todo el contenido de la skill vive en la carpeta [`SKILL/`](SKILL/):

| Ruta | Contenido |
|---|---|
| `SKILL/SKILL.md` | Definición de la skill y selector de motor |
| `SKILL/scripts/` | Motores y herramientas (render por plan, música, voz en off, QA, kit `ffmpeg_tools/`) |
| `SKILL/references/` | Documentación de referencia (instalación, escenas, cine, montaje, sonido, etc.) |
| `SKILL/brand/` | Brand packs (marca blanca; incluye `dragonjar.json` como ejemplo, con sus assets en `brand/assets/`) |
| `SKILL/assets/fonts/` | Plus Jakarta Sans y Montserrat (fuentes variables, licencia OFL en `OFL.txt`) |
| `SKILL/film/` | Música de ejemplo para el film de marca |

## Criterio de calidad

Cada pieza se juzga contra una rúbrica de premios de 8 ejes (`SKILL/references/rubrica-premios.md`): idea y hook, dramaturgia, animación, composición, sistema visual, sonido, verdad y acabado técnico. Ningún eje puede quedar por debajo de 4/5. El oficio de animación (12 principios aplicados a motion graphics, motion blur de obturador 180°, cámara virtual, coreografía) está en `SKILL/references/animacion.md`.

## Instalación

1. Copia o enlaza la carpeta `SKILL/` en el directorio de skills de Claude con el nombre `editoria` (por ejemplo `~/.claude/skills/editoria/`).
2. Instala las dependencias según tu sistema (Windows, macOS o Linux): ver `SKILL/references/instalacion.md`.
3. Verifica las capacidades del entorno: `python SKILL/scripts/check_env.py`.
4. Opcional, para voz en off y música con IA: define `ELEVENLABS_API_KEY` en tu entorno (nunca dentro de la skill).

## Uso rápido

Pídele a Claude cosas como: «hazme un video», «resume esta reunión», «edita este anuncio», «mejora este video» o «ponle música».

## Licencia

Ver [LICENSE](LICENSE).
