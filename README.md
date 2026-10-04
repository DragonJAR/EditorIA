# EditorIA

**Navaja suiza de edición de video con IA**, empaquetada como *skill* para Claude.

Crea, edita, resume y mejora videos (`.mp4`): resúmenes animados de reuniones, tipografía cinética, anuncios por plan, films cinematográficos y piezas verticales para redes, para cualquier marca o sin marca.

🇬🇧 [English version](README.en.md)

## Versión

`v1.0.0` — primera versión.

## Estructura

Todo el contenido de la skill vive en la carpeta [`SKILL/`](SKILL/):

| Ruta | Contenido |
|---|---|
| `SKILL/SKILL.md` | Definición de la skill y selector de motor |
| `SKILL/scripts/` | Motores y herramientas (render por plan, música, voz en off, QA, kit `ffmpeg_tools/`) |
| `SKILL/references/` | Documentación de referencia (instalación, escenas, cine, montaje, sonido, etc.) |
| `SKILL/brand/` | Brand packs (marca blanca; incluye `dragonjar.json` como ejemplo) |
| `SKILL/film/`, `SKILL/demo/` | Recursos de ejemplo |

## Instalación

1. Copia o enlaza la carpeta `SKILL/` en el directorio de skills de Claude con el nombre `editoria`.
2. Instala las dependencias según tu sistema (Windows, macOS o Linux): ver `SKILL/references/instalacion.md`.
3. Verifica las capacidades del entorno: `python SKILL/scripts/check_env.py`.

## Uso rápido

Pídele a Claude cosas como: «hazme un video», «resume esta reunión», «edita este anuncio», «mejora este video» o «ponle música».

## Licencia

Ver [LICENSE](LICENSE).
