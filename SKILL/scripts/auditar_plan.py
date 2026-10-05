#!/usr/bin/env python3
"""Audita un plan.json de EditorIA antes de renderizar.
Uso: python auditar_plan.py plan.json [--json] [--tol 0.05]
Verifica: solapes de tiempos entre escenas, duraciones negativas o cero,
escenas vacías (sin texto ni voz), campos "voz" presentes pero vacíos,
desorden temporal (from > to, escenas fuera de orden), escena final muy
corta (< 2s), coherencia con plan["duracion"] y que cada voz quepa en su
escena sin pisar la siguiente (2.3 palabras/s, references/sonido.md).
Reporta cada hallazgo con su timestamp. Solo stdlib.
"""
import argparse, json, os, re, sys

# Ritmo de narración de references/sonido.md: segundos = palabras/2.3 + 0.4
RITMO_VOZ = 2.3     # palabras por segundo
AIRE_VOZ = 0.4      # voz_off.py coloca cada segmento en from + 0.4


def tipos_validos():
    """Los tipos salen del dict SCENES de render_plan.py (fuente única): una
    lista copiada aquí quedaba vieja en cuanto se añadía una escena."""
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "render_plan.py"),
               encoding="utf-8").read()
    bloque = re.search(r"^SCENES\s*=\s*\{(.*?)\}\s*$", src, re.S | re.M).group(1)
    return set(re.findall(r'"(\w+)"\s*:\s*sc_', bloque))


TIPOS_VALIDOS = tipos_validos()


def palabras_voz(texto):
    """Palabras habladas: sin audio tags de dirección ([excited], [long pause]...)."""
    return len(re.sub(r"\[[^\]]*\]", " ", texto or "").split())

def es_vacia(e):
    """Sin contenido propio: ningún campo (texto, datos, imagen, voz) más allá
    del tipo, los tiempos y la transición. Cada escena usa campos distintos."""
    for k, v in e.items():
        if k in ("tipo", "from", "to", "transicion", "transicionX", "transicionY"):
            continue
        if isinstance(v, str) and v.strip():
            return False
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return False
        if isinstance(v, (list, dict)) and v:
            return False
    return True

def at_fuera(at, fr, to):
    """Tiempos at: fuera de la ventana [from, to] de la escena."""
    mal = []
    def walk(v):
        if isinstance(v, bool):
            return
        if isinstance(v, (int, float)):
            if not (fr - 0.01 <= v <= to + 0.01):
                mal.append(v)
        elif isinstance(v, list):
            for x in v:
                walk(x)
        elif isinstance(v, dict):
            for x in v.values():
                walk(x)
    walk(at)
    return mal

def main():
    ap = argparse.ArgumentParser(
        description="Audita un plan.json: solapes, duraciones, escenas vacías, voz vacía, orden temporal.")
    ap.add_argument("plan", help="plan.json a auditar")
    ap.add_argument("--json", action="store_true", help="salida en JSON")
    ap.add_argument("--tol", type=float, default=0.05,
                    help="tolerancia en segundos para solapes (default: 0.05)")
    ap.add_argument("--min-final", type=float, default=2.0,
                    help="duración mínima de la escena final (default: 2.0s)")
    a = ap.parse_args()

    plan = json.load(open(a.plan, encoding="utf-8"))
    escenas = plan.get("escenas", [])
    hallazgos = []

    def add(nivel, t, msg):
        hallazgos.append({"nivel": nivel, "t": round(float(t), 2), "msg": msg})

    ordenadas = sorted(enumerate(escenas), key=lambda p: p[1].get("from", 0))
    for i, (idx, e) in enumerate(ordenadas):
        fr, to = e.get("from"), e.get("to")
        tipo = e.get("tipo", "?")
        if tipo not in TIPOS_VALIDOS:
            add("ERROR", fr if isinstance(fr, (int, float)) else 0,
                f"escena {idx} ({tipo}): tipo desconocido — "
                f"válidos: {', '.join(sorted(TIPOS_VALIDOS))}")
        for donde, sub in (("at", e.get("at")),):
            for v in at_fuera(sub, fr, to):
                add("AVISO", fr,
                    f"escena {idx} ({tipo}): {donde}={v} fuera de la ventana "
                    f"[{fr},{to}] — el elemento nunca aparece")
        for j, m in enumerate(e.get("mensajes", []) + e.get("canales", [])):
            if "at" in m:
                for v in at_fuera(m["at"], fr, to):
                    add("AVISO", fr,
                        f"escena {idx} ({tipo}): sub-elemento {j} at={v} "
                        f"fuera de [{fr},{to}]")
        if fr is None or to is None:
            add("ERROR", 0, f"escena {idx} ({tipo}): falta from/to")
            continue
        if to <= fr:
            add("ERROR", fr, f"escena {idx} ({tipo}): duración no positiva (from={fr}, to={to})")
        if to - fr < 0.4:
            add("AVISO", fr, f"escena {idx} ({tipo}): muy corta ({to-fr:.2f}s)")
        if es_vacia(e):
            add("AVISO", fr, f"escena {idx} ({tipo}): escena vacía (sin texto ni voz)")
        if "voz" in e and isinstance(e["voz"], str) and not e["voz"].strip():
            add("AVISO", fr, f"escena {idx} ({tipo}): campo voz presente pero vacío")
        if i > 0:
            prev_to = ordenadas[i-1][1].get("to", 0)
            if fr < prev_to - a.tol:
                add("ERROR", fr, f"escena {idx} ({tipo}): solapa con la anterior "
                                 f"(from={fr} < to_previo={prev_to})")
            elif fr - prev_to > 1.0:
                add("AVISO", prev_to, f"hueco de {fr-prev_to:.2f}s entre escena "
                                      f"{ordenadas[i-1][0]} y {idx}")

    # La narración manda el reloj: la voz estimada debe caber en su escena y,
    # sobre todo, no pisar la voz siguiente (voz_off mezcla con amix: dos
    # voces a la vez). Estimación antes de pagar TTS; voz_off mide la real.
    con_voz = [(idx, e) for idx, e in ordenadas
               if isinstance(e.get("voz"), str) and e["voz"].strip()
               and isinstance(e.get("from"), (int, float))]
    for k, (idx, e) in enumerate(con_voz):
        n = palabras_voz(e["voz"])
        fin = e["from"] + AIRE_VOZ + n / RITMO_VOZ
        sig = con_voz[k + 1][1]["from"] + AIRE_VOZ if k + 1 < len(con_voz) else None
        # la estimación tiene ±0.3s de error: por debajo es aviso, no error
        if sig is not None and fin > sig + 0.3:
            add("ERROR", e["from"], f"escena {idx}: la voz ({n} palabras ≈ "
                f"{n / RITMO_VOZ:.1f}s) pisaría la voz siguiente en {fin - sig:.1f}s — "
                f"alargar la escena o recortar el texto")
        elif sig is not None and fin > sig:
            add("AVISO", e["from"], f"escena {idx}: la voz ({n} palabras ≈ "
                f"{n / RITMO_VOZ:.1f}s) roza la voz siguiente — verificar con voz_off.py")
        elif isinstance(e.get("to"), (int, float)) and fin > e["to"]:
            add("AVISO", e["from"], f"escena {idx}: la voz ({n} palabras ≈ "
                f"{n / RITMO_VOZ:.1f}s) se sale de la escena en {fin - e['to']:.1f}s")

    if ordenadas:
        idx, e = ordenadas[-1]
        dur_fin = (e.get("to") or 0) - (e.get("from") or 0)
        if dur_fin < a.min_final:
            add("AVISO", e.get("from", 0),
                f"escena final {idx} ({e.get('tipo','?')}): dura {dur_fin:.2f}s "
                f"(mínimo {a.min_final}s para tarjeta final)")

    if "duracion" in plan and ordenadas:
        fin = max(e.get("to", 0) for _, e in ordenadas)
        if abs(fin - plan["duracion"]) > 0.5:
            add("AVISO", fin, f"plan['duracion']={plan['duracion']}s pero la última "
                              f"escena termina en {fin:.2f}s")

    errores = sum(1 for h in hallazgos if h["nivel"] == "ERROR")
    if a.json:
        print(json.dumps({"errores": errores, "hallazgos": hallazgos},
                         ensure_ascii=False, indent=1))
    else:
        if not hallazgos:
            print(f"OK plan limpio: {len(escenas)} escenas auditadas")
        else:
            print(f"{errores} error(es), {len(hallazgos)-errores} aviso(s) "
                  f"en {len(escenas)} escenas:")
            for h in sorted(hallazgos, key=lambda x: x["t"]):
                print(f"[{h['nivel']}] t={h['t']:.2f}s — {h['msg']}")
    sys.exit(1 if errores else 0)

if __name__ == "__main__":
    main()
