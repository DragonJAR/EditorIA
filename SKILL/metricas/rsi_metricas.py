#!/usr/bin/env python3
"""Métricas estáticas reproducibles del código de la skill (RSI_LOG.md).

Instrumento de medición, no parte de la skill: compila todo, cuenta hallazgos
de lint (ruff --isolated, reglas por defecto E4/E7/E9/F), seguridad (bandit, severidad media y
alta), complejidad ciclomática y mantenibilidad (radon), duplicación (bloques
de 6 líneas normalizadas repetidos entre archivos o dentro de uno) y
docstrings de funciones públicas. Requiere en el entorno: ruff, bandit, radon
(pip install ruff bandit radon); si falta uno, su métrica sale "no evaluado".

Uso:  python3 SKILL/metricas/rsi_metricas.py [--json salida.json]
Versión del instrumento: 1 (si cambia un criterio, subir la versión y volver a
medir la línea base).
"""
import argparse
import ast
import hashlib
import json
import os
import py_compile
import re
import subprocess
import sys
from collections import defaultdict

VERSION = 1
AQUI = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(AQUI), "scripts")
VENTANA = 6   # líneas por bloque para la duplicación


def fuentes():
    for dp, _, fn in os.walk(SCRIPTS):
        if "__pycache__" in dp:
            continue
        for f in sorted(fn):
            if f.endswith(".py"):
                yield os.path.join(dp, f)


def correr(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except FileNotFoundError:
        return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", help="guardar el resultado en este archivo")
    a = ap.parse_args()
    archivos = list(fuentes())
    r = {"version_instrumento": VERSION, "archivos_py": len(archivos)}

    # compilación
    fallan = []
    for f in archivos:
        try:
            py_compile.compile(f, doraise=True)
        except py_compile.PyCompileError:
            fallan.append(os.path.relpath(f, SCRIPTS))
    r["compilan"] = f"{len(archivos) - len(fallan)}/{len(archivos)}"

    # líneas de código (sin vacías ni comentarios)
    loc = 0
    for f in archivos:
        loc += sum(1 for ln in open(f, encoding="utf-8") if ln.strip() and not ln.strip().startswith("#"))
    r["loc"] = loc

    # lint
    # --isolated: ninguna configuración del entorno; reglas por defecto de ruff
    p = correr([sys.executable, "-m", "ruff", "check", "--isolated", "--select", "E4,E7,E9,F",
                SCRIPTS, "--output-format", "json", "--quiet"])
    if p is None or (p.returncode not in (0, 1)):
        r["ruff_hallazgos"] = "no evaluado"
    else:
        hall = json.loads(p.stdout or "[]")
        por = defaultdict(int)
        for h in hall:
            por[h["code"]] += 1
        r["ruff_hallazgos"] = len(hall)
        r["ruff_por_regla"] = dict(sorted(por.items(), key=lambda kv: -kv[1]))

    # seguridad
    p = correr([sys.executable, "-m", "bandit", "-r", SCRIPTS, "-f", "json", "-q"])
    if p is None or not p.stdout.strip().startswith("{"):
        r["bandit"] = "no evaluado"
    else:
        res = json.loads(p.stdout)["results"]
        cuenta = defaultdict(int)
        ids = defaultdict(int)
        for x in res:
            cuenta[x["issue_severity"]] += 1
            if x["issue_severity"] in ("MEDIUM", "HIGH"):
                ids[x["test_id"]] += 1
        r["bandit"] = {"HIGH": cuenta["HIGH"], "MEDIUM": cuenta["MEDIUM"], "LOW": cuenta["LOW"],
                       "medio_alto_por_regla": dict(ids)}

    # complejidad y mantenibilidad
    p = correr([sys.executable, "-m", "radon", "cc", "-j", SCRIPTS])
    if p is None or not p.stdout.strip().startswith("{"):
        r["complejidad"] = "no evaluado"
    else:
        bloques = [b for v in json.loads(p.stdout).values() if isinstance(v, list) for b in v]
        cc = [b["complexity"] for b in bloques]
        altos = sorted(((b["complexity"], b["name"]) for b in bloques if b["complexity"] > 20), reverse=True)
        r["complejidad"] = {"funciones": len(cc), "media": round(sum(cc) / max(1, len(cc)), 2),
                            "max": max(cc, default=0), "mayor_a_20": len(altos), "peores": altos[:5]}
    p = correr([sys.executable, "-m", "radon", "mi", "-j", SCRIPTS])
    if p is not None and p.stdout.strip().startswith("{"):
        mi = [v["mi"] for v in json.loads(p.stdout).values() if isinstance(v, dict) and "mi" in v]
        r["mantenibilidad_media"] = round(sum(mi) / max(1, len(mi)), 1)
        r["mantenibilidad_rango_C"] = sum(1 for x in mi if x < 10)

    # duplicación: bloques de VENTANA líneas normalizadas que se repiten
    vistos = defaultdict(list)
    total = 0
    for f in archivos:
        ls = [re.sub(r"\s+", " ", ln.strip()) for ln in open(f, encoding="utf-8")]
        ls = [ln for ln in ls if ln and not ln.startswith("#")]
        for i in range(len(ls) - VENTANA + 1):
            bloque = "\n".join(ls[i:i + VENTANA])
            if len(bloque) < 120:   # bloques triviales (cierres, imports cortos) no cuentan
                continue
            total += 1
            vistos[hashlib.sha1(bloque.encode()).hexdigest()].append(os.path.relpath(f, SCRIPTS))
    dup = sum(len(v) - 1 for v in vistos.values() if len(v) > 1)
    r["duplicacion_bloques"] = dup
    r["duplicacion_pct"] = round(100 * dup / max(1, total), 2)

    # documentación: docstrings de funciones públicas de nivel módulo
    con = sin = 0
    for f in archivos:
        try:
            arbol = ast.parse(open(f, encoding="utf-8").read())
        except SyntaxError:
            continue
        for n in arbol.body:
            if isinstance(n, ast.FunctionDef) and not n.name.startswith("_"):
                if ast.get_docstring(n):
                    con += 1
                else:
                    sin += 1
    r["docstrings_publicas_pct"] = round(100 * con / max(1, con + sin), 1)
    r["funciones_publicas"] = con + sin

    print(json.dumps(r, ensure_ascii=False, indent=1))
    if a.json:
        json.dump(r, open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return 1 if fallan else 0


if __name__ == "__main__":
    sys.exit(main())
