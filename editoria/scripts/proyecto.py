#!/usr/bin/env python3
"""Crea (o completa) la carpeta de un proyecto de video con su memoria: los
archivos que permiten retomar el trabajo en otra conversación sin rehacer
nada ni volver a pagar TTS (references/referencia-video.md).

  proyecto/
  ├── BRIEF.md          lo que el usuario pidió: objetivo, hechos, límites, presupuesto acordado
  ├── TRATAMIENTO.md    tu respuesta creativa: premisa, arco, sistemas visuales y sonoros
  ├── PROGRESO.md       foto del ahora: pregunta viva, lo que falta, siguiente acción, renders útiles
  └── referencias/
      └── {nombre}/
          ├── TIMELINE.md   qué pasa cuándo y qué hace por el espectador
          ├── evidencia/    mosaicos y clips que vale la pena reabrir
          └── (clonar_video.py analizar deja aquí la fuente, ANALYSIS.md,
               plantilla.json y el contact sheet)

Nunca sobrescribe: si un archivo existe, lo deja como está (correr de nuevo
con otra --referencia solo agrega lo nuevo). No descarga ni transcribe: la
ingesta es de clonar_video.py / referencia.py (fuente única); aquí solo se
imprimen esos comandos, porque descargar y gastar es decisión explícita. Cada archivo tiene un solo trabajo y se REESCRIBE cuando su
verdad cambia (no son bitácoras). Convención inspirada en los project files
de Hypit (hypit-ai/hypit).

Uso:
  python3 scripts/proyecto.py ~/videos/lanzamiento
  python3 scripts/proyecto.py ~/videos/lanzamiento --referencia "https://www.tiktok.com/@x/video/1"
  python3 scripts/proyecto.py ~/videos/lanzamiento --referencia ref.mp4 --referencia otra.mp4
"""
import argparse
import os
import re
import sys
import unicodedata
from datetime import date

KIT = os.path.dirname(os.path.abspath(__file__))

BRIEF = """# Brief

_Lo que el usuario pidió, con sus palabras cuando reinterpretarlas cambiaría
el encargo. Solo él puede cambiar este archivo (vía la conversación)._

- **Pedido**:
- **Objetivo / público / plataforma**:
- **Entregable**: formato (9:16 · 16:9), duración, idioma
- **Marca**: pack de brand/ o modo libre
- **Hechos que deben ser exactos**: cifras, nombres, oferta, CTA (o [PENDIENTE])
- **Referencias y qué heredar de cada una**:
- **Cambios pedidos** (sustituir persona, producto, idioma, tono...):
- **Límites**: fechas, duración máxima, lo que el usuario se reserva decidir
- **Gasto acordado**: servicios de pago (TTS/música) y presupuesto aceptado
"""

TRATAMIENTO = """# Tratamiento

_Tu respuesta creativa al Brief, en lenguaje de dirección (sin nombres de
scripts ni parámetros). Se reescribe cuando cambia el diseño, no cuando se
corrige la implementación._

- **Premisa y experiencia del espectador**:
- **Arco**: gancho → desarrollo → giro/payoff → CTA
- **Ritmo y trabajo de cada pasaje**:
- **Sistemas visuales**: A-roll, B-roll, subtítulos, tipografía, gráficas, efectos
- **Sonido**: voz, música, SFX y silencios
- **Cómo se propagan los cambios pedidos** por cada sistema:
- **Preguntas creativas abiertas**:
"""

PROGRESO = """# Progreso

_Foto corta del estado actual (no una bitácora). Basta para que otra
conversación continúe sin repetir trabajo pagado._

- **Pregunta viva**:
- **Lo que falta examinar o hacer**:
- **Siguiente acción útil**:
- **Bloqueos reales**:
- **Material producido reutilizable** (voz.mp3, palabras.json, renders, frames):
- **Gasto hasta ahora vs acordado**:

_Actualizado: {hoy}_
"""

TIMELINE = """# Timeline — {nombre}

Fuente: {fuente} · el modelo de la pieza entera va en ANALYSIS.md

_Secciones por tiempo de la fuente y fase con sentido. Cada una conecta los
objetos activos (contenido, posición, entrada, cambios, permanencia, salida)
con las palabras o acciones a las que sirven, y cita la evidencia._

## 0.00–0.00 · (fase)

"""


def slug(texto):
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    t = re.sub(r"^https?://(www\.)?", "", t)
    t = re.sub(r"\.(mp4|mov|mkv|webm|m4v)$", "", t)
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:40] or "referencia"


def escribir(ruta, contenido, creados):
    if os.path.exists(ruta):
        return
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as fh:
        fh.write(contenido)
    creados.append(ruta)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("carpeta", help="carpeta del proyecto (se crea si no existe; nunca dentro de la skill)")
    ap.add_argument("--referencia", action="append", default=[], metavar="VIDEO_O_URL",
                    help="video de referencia (archivo o enlace); repetible")
    a = ap.parse_args()

    raiz = os.path.abspath(os.path.expanduser(a.carpeta))
    if raiz == os.path.dirname(KIT) or raiz.startswith(os.path.dirname(KIT) + os.sep):
        sys.exit("ERROR: el proyecto no va dentro de la skill; elige una carpeta del usuario")
    creados = []
    escribir(os.path.join(raiz, "BRIEF.md"), BRIEF, creados)
    escribir(os.path.join(raiz, "TRATAMIENTO.md"), TRATAMIENTO, creados)
    escribir(os.path.join(raiz, "PROGRESO.md"), PROGRESO.format(hoy=date.today().isoformat()), creados)

    pasos = []
    for ref in a.referencia:
        es_url = ref.lower().startswith(("http://", "https://"))
        if not es_url and not os.path.isfile(ref):
            sys.exit(f"ERROR: la referencia no existe: {ref}")
        nombre = slug(os.path.basename(ref) if not es_url else ref)
        dref = os.path.join(raiz, "referencias", nombre)
        fuente = ref if es_url else os.path.abspath(ref)
        escribir(os.path.join(dref, "TIMELINE.md"), TIMELINE.format(nombre=nombre, fuente=fuente), creados)
        os.makedirs(os.path.join(dref, "evidencia"), exist_ok=True)
        # referencia.py nombra así lo que descarga
        video = os.path.join(dref, "fuente_descargada.mp4") if es_url else fuente
        origen = f'--url "{ref}"' if es_url else f"--video {fuente}"
        pasos.append(f"python3 {os.path.join(KIT, 'clonar_video.py')} analizar {origen} -o {dref}")
        palabras = os.path.join(dref, "fuente.palabras.json")
        pasos += [f"python3 {os.path.join(KIT, 'alinear.py')} {video} -o {palabras} --idioma es  "
                  "# idioma de la referencia",
                  f"python3 {os.path.join(KIT, 'ffmpeg_tools', 'scenes.py')} {video} --sheet "
                  f"{os.path.join(dref, 'evidencia', 'cortes.png')}",
                  f"python3 {os.path.join(KIT, 'contact_sheet.py')} --video {video} --cada 1 "
                  f"--palabras {palabras} --filas 4 -o {os.path.join(dref, 'evidencia', 'pieza.png')}"]

    for r in creados:
        print(f"creado {r}")
    print(f"OK proyecto en {raiz} ({len(creados)} archivo(s) nuevo(s); los existentes no se tocan)")
    if pasos:
        print("Siguientes pasos para leer la referencia (references/referencia-video.md):")
        for p in pasos:
            print("  " + p)


if __name__ == "__main__":
    main()
