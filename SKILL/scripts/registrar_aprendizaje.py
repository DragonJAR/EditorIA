#!/usr/bin/env python3
"""Registra un aprendizaje en la skill siguiendo el protocolo de
references/auto-mejora.md: formato canónico, fecha de hoy, detección de
duplicados por similitud y rechazo de angle brackets.

Uso:
    python scripts/registrar_aprendizaje.py --titulo "..." --detalle "..."
    python scripts/registrar_aprendizaje.py --titulo "..." --detalle "..." \
        --destino ref --ref audio
    python scripts/registrar_aprendizaje.py --titulo "..." --detalle "..." --dry-run
"""
import argparse
import os
import re
import sys
from datetime import date

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESTINOS = {
    "reglas": "references/reglas-tecnicas.md",
    "principios": "references/principios.md",
}

STOPWORDS = set(
    "el la los las un una de del en y o que se con por para como mas muy sin "
    "sobre entre hasta desde esta este esto son sea the a an of to in is are "
    "for with on as at be or and".split()
)
TAG_RE = re.compile(r"<[^/!][^>]*>")
ENTRY_START_RE = re.compile(r"^-\s+\d{4}-\d{2}-\d{2}\s+·")


def palabras(texto):
    toks = re.findall(r"[a-z0-9]+", texto.lower())
    return {t for t in toks
            if (len(t) > 3 or any(c.isdigit() for c in t)) and t not in STOPWORDS}


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def overlap(a, b):
    """Coeficiente de solapamiento: 1.0 si el conjunto menor esta contenido."""
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def entradas_existentes(ruta):
    """Parser tolerante: una entrada empieza en '- YYYY-MM-DD' y continua en
    las lineas siguientes indentadas hasta el proximo bullet, header o vacio."""
    out = []
    linea_actual = None
    texto = []

    def flush():
        nonlocal linea_actual, texto
        if linea_actual is not None:
            out.append((linea_actual, " ".join(texto)))
            linea_actual, texto = None, []

    with open(ruta, encoding="utf-8") as f:
        for i, linea in enumerate(f, 1):
            s = linea.rstrip("\n")
            if ENTRY_START_RE.match(s):
                flush()
                linea_actual = i
                texto = [s]
            elif linea_actual is not None:
                if s.startswith("  ") or s.startswith("\t"):
                    texto.append(s.strip())
                elif s.strip() == "" or s.startswith("- ") or s.startswith("#"):
                    flush()
    flush()
    return out


def buscar_duplicados(ruta, titulo, detalle, umbral=0.35, umbral_titulo=0.6):
    nuevo = palabras(titulo + " " + detalle)
    nuevo_t = palabras(titulo)
    cands = []
    for linea, texto in entradas_existentes(ruta):
        pt = palabras(texto)
        st = overlap(nuevo_t, pt)
        sim = max(jaccard(nuevo, pt), st if st >= umbral_titulo else 0.0)
        if sim >= umbral:
            cands.append((sim, linea, texto[:90]))
    return sorted(cands, reverse=True)[:3]


def main():
    ap = argparse.ArgumentParser(description="Registra un aprendizaje en la skill.")
    ap.add_argument("--titulo", required=True, help="Titulo corto del aprendizaje")
    ap.add_argument("--detalle", required=True, help="Detalle verificable")
    ap.add_argument("--destino", choices=["reglas", "principios", "ref"],
                    default="reglas", help="Donde registrar (default: reglas)")
    ap.add_argument("--ref", help="Nombre de la referencia si --destino ref (sin .md)")
    ap.add_argument("--forzar", action="store_true",
                    help="Escribir aunque haya candidato a duplicado")
    ap.add_argument("--dry-run", action="store_true",
                    help="Mostrar la entrada sin escribir")
    a = ap.parse_args()

    titulo = a.titulo.strip()
    detalle = a.detalle.strip()
    if not titulo or not detalle:
        sys.exit("error: titulo y detalle no pueden estar vacios")
    if len(titulo) > 90:
        sys.exit("error: titulo demasiado largo (max 90 caracteres)")
    if TAG_RE.search(titulo) or TAG_RE.search(detalle):
        sys.exit("error: angle brackets prohibidos en la skill (los rechaza el validador)")

    if a.destino == "ref":
        if not a.ref:
            sys.exit("error: --destino ref requiere --ref NOMBRE")
        rel = "references/%s.md" % a.ref
    else:
        rel = DESTINOS[a.destino]
    ruta = os.path.join(BASE, rel)
    if not os.path.exists(ruta):
        sys.exit("error: no existe %s" % rel)

    hoy = date.today().isoformat()
    entrada = "- %s \u00b7 **%s**: %s" % (hoy, titulo, detalle)
    dups = buscar_duplicados(ruta, titulo, detalle)
    if dups:
        print("Candidatos a duplicado en %s:" % rel)
        for sim, linea, txt in dups:
            print("  linea %d (sim %.2f): %s" % (linea, sim, txt))
        if not a.forzar and not a.dry_run:
            print("Si es un matiz nuevo, reintenta con --forzar.")
            sys.exit(2)

    if a.dry_run:
        print("Entrada propuesta (dry-run, no se escribe):")
        print(entrada)
        return

    with open(ruta, "a", encoding="utf-8") as f:
        f.write(entrada + "\n")
    print("Registrado en %s:" % rel)
    print(entrada)


if __name__ == "__main__":
    main()
