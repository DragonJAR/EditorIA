#!/usr/bin/env python3
"""Guard de prosa: lo que la pieza puede necesitar no se llama de otra cosa.

La doctrina de la skill (`references/capacidades.md`) es que una capacidad
externa NO es un requisito del motor pero SI puede ser necesaria para que
la pieza salga como tiene que salir. Cuando falta, se DECLARA al usuario con
su comando de instalacion; no se degrada en silencio.

Ese cambio de palabra se puede deshacer sin que nadie lo note: basta con
que alguien escriba en una referencia que una capacidad "no hace falta", y
la skill vuelve a entregar menos en silencio, por escritura. El mapa de
referencias, los conteos y los enlaces siguen en verde: lo unico que cambia
es el liston. Por eso este guard lee la PROSA y no solo la estructura.

QUE BUSCA
  La palabra vetada pegada al nombre de una capacidad (Remotion,
  HyperFrames, Blender, whisper, yt-dlp, ElevenLabs, 3D, diagramas, Node,
  voz, musica) o a un sustantivo de capacidad (motor, capacidad,
  herramienta, integracion).

  Excepcion: si la NEGACION gobierna la palabra ("no es...", "no son...",
  "ni..."), la frase esta declarando la doctrina: bien, no es una falta.

COMO SE USA
  python3 scripts/_guard_doctrina.py             # escanea la skill
  python3 scripts/_guard_doctrina.py --base DIR  # escanea otro arbol
  python3 scripts/_guard_doctrina.py --json      # salida para maquinas

Sale 0 si no hay violaciones, 1 si las hay.

Este fichero no se escanea a si mismo: la palabra vetada se arma en dos
trozos para que el fuente de este guard no contenga la frase que el guard
busca (un guard que se marca a si mismo no lo lee nadie).
"""
import argparse
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: La palabra vetada, en sus dos formas. Se arma en dos trozos para que este
#: fichero no la contenga como palabra suelta (ver la nota del modulo).
_VETA = "opcio" + "nal"
_VETADA = re.compile(r"^" + _VETA + r"(?:es)?$", re.I)

#: Las capacidades que la pieza puede necesitar. La lista de una por una
#: esta en `references/capacidades.md`; aqui solo hace falta saber que
#: para estos nombres la palabra vetada esta prohibida.
NOMBRES = re.compile(
    r"\b(remotion|hyperframes|blender|whisper|yt-dlp|elevenlabs|3d|"
    r"diagramas?|node|voz|m[uú]sica|hand[- ]?draw|mediapipe)\b", re.I)

#: Los sustantivos que nombran una capacidad sin repetir su nombre propio:
#: "los motores ..." es la forma que adopta la falta cuando no dice Remotion.
SUSTANTIVOS = re.compile(
    r"^(motores?|capacidades|herramientas?|integraci[oó]n(?:es)?)$", re.I)

#: La negacion que gobierna la palabra vetada.
NEGACION = re.compile(r"^(no|ni|nunca|sin)$", re.I)

#: Trocea el texto en frases. El punto y coma tambien corta: "NO se portó;
#: ... son ..." son dos frases, y la negacion de la primera no excuse a la
#: segunda.
FRASES = re.compile(r"(?<=[.;!?])\s+|\n")

#: Las palabras de una frase. Los acentos graves se quedan pegados a la
#: palabra: `voz` es un CAMPO del plan, "voz" es la capacidad. El punto solo
#: se come cuando va ENTRE palabras (una extension, un decimal): un punto
#: final es puntuacion, no parte de la palabra ("opcional." es "opcional").
PALABRAS = re.compile(r"`?[^\W_]+(?:[./-][^\W_]+)*`?", re.UNICODE)


def _es_nombre(token):
    """¿El token cuenta como nombre de capacidad?

    Un token entre acentos graves que no lleva punto ni barra es un campo
    del plan (`voz`), no una capacidad: el campo `voz` puede ser opcional de
    verdad. `remotion.md` si lleva punto: ese es el nombre de la capacidad.
    """
    if len(token) >= 2 and token.startswith("`") and token.endswith("`"):
        return "." in token or "/" in token
    return True


def _falta_en_frase(frase):
    """(motivo, frase) si la frase llama de otro modo a una capacidad."""
    palabras = PALABRAS.findall(frase)
    for i, palabra in enumerate(palabras):
        if not _VETADA.match(palabra):
            continue
        previos = palabras[max(0, i - 2):i]
        if any(NEGACION.match(p) for p in previos):
            continue            # la negacion gobierna la palabra: es la doctrina
        for p in previos:
            if _es_nombre(p) and NOMBRES.search(p):
                return "nombre de capacidad", frase
            if SUSTANTIVOS.match(p):
                return "sustantivo de capacidad", frase
        siguiente = palabras[i + 1] if i + 1 < len(palabras) else ""
        if siguiente and _es_nombre(siguiente) and NOMBRES.search(siguiente):
            return "nombre de capacidad", frase
    return None


def violaciones(base=BASE):
    """[(fichero, motivo, frase)] — las frases que rompen la doctrina."""
    salida = []
    base = os.path.abspath(base)
    for dirpath, dirnames, filenames in os.walk(base):
        # los tests guardan sus fixtures aqui: si se escanearan, el guard
        # encontraria en ellos lo que busca encontrar en la prosa real.
        dirnames[:] = [d for d in dirnames
                       if d not in ("__pycache__", "_tests")]
        for nombre in sorted(filenames):
            if not nombre.endswith((".md", ".py", ".json")):
                continue
            ruta = os.path.join(dirpath, nombre)
            try:
                with open(ruta, encoding="utf-8") as fh:
                    texto = fh.read()
            except (OSError, UnicodeDecodeError):
                continue
            for frase in FRASES.split(texto):
                falta = _falta_en_frase(frase)
                if falta:
                    rel = os.path.relpath(ruta, base).replace(os.sep, "/")
                    salida.append((rel, falta[0], " ".join(frase.split())))
    return salida


def main():
    ap = argparse.ArgumentParser(
        description="Guard de prosa: una capacidad que la pieza puede necesitar "
                    "no se declara de otro modo (se DECLARA al usuario)")
    ap.add_argument("--base", default=BASE,
                    help="raiz de la skill a escanear (def: la propia)")
    ap.add_argument("--json", action="store_true", help="salida en JSON")
    a = ap.parse_args()

    falta = violaciones(a.base)
    if a.json:
        print(json.dumps([{"archivo": f, "motivo": m, "frase": t}
                          for f, m, t in falta], ensure_ascii=False, indent=1))
    else:
        for f, motivo, frase in falta:
            print(f"{f}: {motivo}: {frase[:140]}")
        if falta:
            print(f"FALLA  la prosa llama '{_VETA}' a una capacidad "
                  f"({len(falta)} violaciones)")
        else:
            print(f"OK  la prosa no llama '{_VETA}' a ninguna capacidad")
    return 1 if falta else 0


if __name__ == "__main__":
    sys.exit(main())
