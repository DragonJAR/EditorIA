#!/usr/bin/env python3
"""Audita un plan.json de EditorIA antes de renderizar.
Uso: python auditar_plan.py plan.json [--json] [--tol 0.05]
Verifica: solapes de tiempos entre escenas, duraciones negativas o cero,
escenas vacías (sin texto ni voz), campos "voz" presentes pero vacíos,
desorden temporal (from > to, escenas fuera de orden), escena final muy
corta (< 2s), coherencia con plan["duracion"] y que cada voz quepa en su
escena sin pisar la siguiente (sílabas habladas con cifras expandidas al
ritmo del idioma: speech_estimate.py, la fuente única de la estimación).
Reporta cada hallazgo con su timestamp. Solo stdlib.
"""
import argparse, json, os, re, sys

from speech_estimate import AIRE_VOZ, RITMOS, detectar_idioma, estimar_duracion, silabas


def tipos_validos():
    """Los tipos salen del dict SCENES de render_plan.py (fuente única): una
    lista copiada aquí quedaba vieja en cuanto se añadía una escena."""
    ruta_rp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "render_plan.py")
    with open(ruta_rp, encoding="utf-8") as fh:
        src = fh.read()
    bloque = re.search(r"^SCENES\s*=\s*\{(.*?)\}\s*$", src, re.S | re.M).group(1)
    return set(re.findall(r'"(\w+)"\s*:\s*sc_', bloque))


TIPOS_VALIDOS = tipos_validos()


def _t_num(v):
    """Convierte int/float (no bool) a float; devuelve None si no es numérico."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return float(v)


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
    if fr is None or to is None:
        return mal

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


def auditar_estructura(plan, tol=0.05, min_final=2.0):
    """Audita un diccionario de plan ya cargado y devuelve lista de hallazgos."""
    if not isinstance(plan, dict):
        return [{"nivel": "ERROR", "t": 0.0, "msg": "el plan raíz debe ser un objeto JSON"}]
    escenas = plan.get("escenas", [])
    if not isinstance(escenas, list):
        return [{"nivel": "ERROR", "t": 0.0, "msg": "el campo 'escenas' debe ser una lista"}]
    hallazgos = []

    def add(nivel, t, msg):
        hallazgos.append({"nivel": nivel, "t": round(float(t or 0.0), 2), "msg": msg})

    pares_validos = []
    for idx, e in enumerate(escenas):
        if not isinstance(e, dict):
            add("ERROR", 0.0, f"escena {idx}: debe ser un objeto JSON")
            continue
        pares_validos.append((idx, e))

    ordenadas = sorted(pares_validos, key=lambda p: _t_num(p[1].get("from")) or 0.0)
    prev_to_val = None
    prev_idx = None
    for idx, e in ordenadas:
        fr_raw, to_raw = e.get("from"), e.get("to")
        fr, to = _t_num(fr_raw), _t_num(to_raw)
        tipo = e.get("tipo", "?")
        if tipo not in TIPOS_VALIDOS:
            add("ERROR", fr if fr is not None else 0.0,
                f"escena {idx} ({tipo}): tipo desconocido — "
                f"válidos: {', '.join(sorted(TIPOS_VALIDOS))}")
        if fr is None or to is None:
            add("ERROR", fr if fr is not None else 0.0,
                f"escena {idx} ({tipo}): falta from/to numérico")
            continue
        for donde, sub in (("at", e.get("at")),):
            for v in at_fuera(sub, fr, to):
                add("AVISO", fr,
                    f"escena {idx} ({tipo}): {donde}={v} fuera de la ventana "
                    f"[{fr},{to}] — el elemento nunca aparece")
        for lista_k in ("mensajes", "canales", "pasos", "items", "notificaciones"):
            items_l = e.get(lista_k)
            if not isinstance(items_l, list):
                continue
            for j, m in enumerate(items_l):
                if isinstance(m, dict) and "at" in m:
                    for v in at_fuera(m["at"], fr, to):
                        add("AVISO", fr,
                            f"escena {idx} ({tipo}): sub-elemento {j} at={v} "
                            f"fuera de [{fr},{to}]")
        if to <= fr:
            add("ERROR", fr, f"escena {idx} ({tipo}): duración no positiva (from={fr}, to={to})")
        if to - fr < 0.4:
            add("AVISO", fr, f"escena {idx} ({tipo}): muy corta ({to-fr:.2f}s)")
        if es_vacia(e):
            add("AVISO", fr, f"escena {idx} ({tipo}): escena vacía (sin texto ni voz)")
        if "voz" in e and isinstance(e["voz"], str) and not e["voz"].strip():
            add("AVISO", fr, f"escena {idx} ({tipo}): campo voz presente pero vacío")
        if prev_to_val is not None:
            if fr < prev_to_val - tol:
                add("ERROR", fr, f"escena {idx} ({tipo}): solapa con la anterior "
                                 f"(from={fr} < to_previo={prev_to_val})")
            elif fr - prev_to_val > 1.0:
                add("AVISO", prev_to_val, f"hueco de {fr-prev_to_val:.2f}s entre escena "
                                          f"{prev_idx} y {idx}")
        prev_to_val = to
        prev_idx = idx

    # La narración manda el reloj: la voz estimada debe caber en su escena y,
    # sobre todo, no pisar la voz siguiente (voz_off mezcla con amix: dos
    # voces a la vez). Estimación antes de pagar TTS; voz_off mide la real.
    con_voz = [(idx, e) for idx, e in ordenadas
               if isinstance(e.get("voz"), str) and e["voz"].strip()
               and _t_num(e.get("from")) is not None]
    # idioma: plan["idioma"], luego plan["numeros"], luego el texto de las voces
    idioma = plan.get("idioma") if plan.get("idioma") in RITMOS else (
        plan.get("numeros") if plan.get("numeros") in RITMOS
        else detectar_idioma(" ".join(e["voz"] for _, e in con_voz)))
    ritmo = plan.get("ritmo_voz", "normal")
    if ritmo not in RITMOS[idioma]:
        add("AVISO", 0.0, f"ritmo_voz '{ritmo}' desconocido ({', '.join(RITMOS[idioma])}); uso normal")
        ritmo = "normal"
    for k, (idx, e) in enumerate(con_voz):
        fr_v = _t_num(e.get("from"))
        to_v = _t_num(e.get("to"))
        n, dur = silabas(e["voz"], idioma), estimar_duracion(e["voz"], idioma, ritmo)
        fin = fr_v + AIRE_VOZ + dur
        sig = (_t_num(con_voz[k + 1][1]["from"]) + AIRE_VOZ) if k + 1 < len(con_voz) else None
        # la estimación tiene ±0.3s de error: por debajo es aviso, no error
        if sig is not None and fin > sig + 0.3:
            add("ERROR", fr_v, f"escena {idx}: la voz ({n} sílabas ≈ "
                f"{dur:.1f}s) pisaría la voz siguiente en {fin - sig:.1f}s — "
                f"alargar la escena o recortar el texto")
        elif sig is not None and fin > sig:
            add("AVISO", fr_v, f"escena {idx}: la voz ({n} sílabas ≈ "
                f"{dur:.1f}s) roza la voz siguiente — verificar con voz_off.py")
        elif to_v is not None and fin > to_v:
            add("AVISO", fr_v, f"escena {idx}: la voz ({n} sílabas ≈ "
                f"{dur:.1f}s) se sale de la escena en {fin - to_v:.1f}s")

    ordenadas_con_t = [(idx, e) for idx, e in ordenadas
                       if _t_num(e.get("from")) is not None and _t_num(e.get("to")) is not None]
    if ordenadas_con_t:
        idx, e = ordenadas_con_t[-1]
        dur_fin = _t_num(e.get("to")) - _t_num(e.get("from"))
        if dur_fin < min_final:
            add("AVISO", _t_num(e.get("from")),
                f"escena final {idx} ({e.get('tipo','?')}): dura {dur_fin:.2f}s "
                f"(mínimo {min_final}s para tarjeta final)")

    dur_plan = _t_num(plan.get("duracion"))
    if dur_plan is not None and ordenadas_con_t:
        fin = max(_t_num(e.get("to")) for _, e in ordenadas_con_t)
        if abs(fin - dur_plan) > 0.5:
            add("AVISO", fin, f"plan['duracion']={plan['duracion']}s pero la última "
                              f"escena termina en {fin:.2f}s")

    for msg in credenciales_en(plan):
        add("ERROR", 0.0, msg)

    return hallazgos


#: como se ve una credencial. El plan va al repo y al guion: una key pegada
#: ahi se publica. La regla del SKILL.md ("no credentials or API keys appear
#: in plan.json or brand/*.json") era una promesa sin ningun check: ahora la
#: cumple el mismo comando que el agente corre antes de renderizar.
_PATRONES_CRED = (
    (re.compile(r"sk-[A-Za-z0-9_\-]{12,}"), "una key con formato sk-..."),
    (re.compile(r"(?i)\b(eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.)"), "un JWT"),
    (re.compile(r"(?i)\b(?:api[_\-]?key|apikey|secret|token|password|passwd|bearer|authorization)\b\s*[:=]"),
     "una clave o un token"),
    (re.compile(r"(?i)\b[A-Z][A-Z0-9_]{4,}(?:API[_\-]?KEY|SECRET|TOKEN|PASSWORD)\b"),
     "el nombre de una variable de entorno con una key"),
)

#: el nombre del campo es la senal: "secret", "api_key", "token"...
_NOMBRE_CRED = re.compile(
    r"(?i)^(api[_\-]?key|apikey|secret|secret[_\-]?key|access[_\-]?token|auth[_\-]?token|"
    r"token|password|passwd|pwd|bearer|authorization|credential[s]?)$")

#: valores que NO son una credencial (placeholders de un pack o de un ejemplo)
_PLACEHOLDER = re.compile(r"(?i)^(x{3,}|\.{3,}|<[^>]*>|null|none|todo|changeme|placeholder|"
                          r"your[_\-]?\w*|mi[_\-]?\w*|aqu[ií]|xxx+|\$\{.*\}|%.*%)$")


def credenciales_en(datos, ruta=""):
    """Mensajes con las credenciales que aparecen en un JSON (plan o pack)."""
    hallados = []
    if isinstance(datos, dict):
        for k, v in datos.items():
            donde = f"{ruta}.{k}" if ruta else str(k)
            if isinstance(v, str):
                for pat, que in _PATRONES_CRED:
                    if pat.search(v):
                        hallados.append(f"posible credencial en '{donde}' ({que}): "
                                        f"quitalo — el plan se publica en el repo")
                        break
            else:
                hallados += credenciales_en(v, donde)
            # el NOMBRE del campo tambien delata: una clave llamada "secret"
            # o "api_key" en un plan significa que alguien la pego ahi
            if isinstance(v, str) and v.strip() and not _PLACEHOLDER.search(v):
                if _NOMBRE_CRED.search(str(k)):
                    hallados.append(f"el campo '{donde}' parece una credencial "
                                    f"(nombre de campo sensible): quitalo — el plan "
                                    f"se publica en el repo")
    elif isinstance(datos, list):
        for i, v in enumerate(datos):
            hallados += credenciales_en(v, f"{ruta}[{i}]")
    return hallados


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

    if not os.path.isfile(a.plan):
        msg = f"ERROR: no existe el archivo de plan: {a.plan}"
        if a.json:
            print(json.dumps({"errores": 1, "hallazgos": [{"nivel": "ERROR", "t": 0.0, "msg": msg}]},
                             ensure_ascii=False, indent=1))
            sys.exit(1)
        sys.exit(msg)
    try:
        with open(a.plan, encoding="utf-8") as fh:
            plan = json.load(fh)
    except (OSError, ValueError) as ex:
        msg = f"ERROR: JSON inválido en {a.plan}: {ex}"
        if a.json:
            print(json.dumps({"errores": 1, "hallazgos": [{"nivel": "ERROR", "t": 0.0, "msg": msg}]},
                             ensure_ascii=False, indent=1))
            sys.exit(1)
        sys.exit(msg)

    hallazgos = auditar_estructura(plan, tol=a.tol, min_final=a.min_final)
    escenas = plan.get("escenas", []) if isinstance(plan, dict) and isinstance(plan.get("escenas"), list) else []
    errores = sum(1 for h in hallazgos if h["nivel"] == "ERROR")
    if a.json:
        print(json.dumps({"errores": errores, "hallazgos": hallazgos},
                         ensure_ascii=False, indent=1))
    else:
        if not hallazgos:
            # el string importa: el SKILL.md promete "PLAN VALIDO" y el agente
            # busca esa palabra para saber que el plan esta listo
            print(f"OK · PLAN VALIDO: {len(escenas)} escenas auditadas")
        else:
            print(f"{errores} error(es), {len(hallazgos)-errores} aviso(s) "
                  f"en {len(escenas)} escenas:")
            for h in sorted(hallazgos, key=lambda x: x["t"]):
                print(f"[{h['nivel']}] t={h['t']:.2f}s — {h['msg']}")
    sys.exit(1 if errores else 0)


if __name__ == "__main__":
    main()
