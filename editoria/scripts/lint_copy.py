#!/usr/bin/env python3
"""lint_copy.py — comprueba el copy de un plan contra el contrato de copy.

Determinista, sin red y sin modelo: mide el texto con las tipografias
empaquetadas del motor y lo compara con la zona segura real. Complementa a
`auditar_plan.py` (que valida tiempos y estructura) y a `auto_qa.py` (que
valida el render).

Uso:
    python3 scripts/lint_copy.py plan.json
    python3 scripts/lint_copy.py plan.json --json
    python3 scripts/lint_copy.py plan.json --strict    # los avisos tambien fallan

Salida: 0 si no hay fallos, 1 si hay fallos, 2 si la entrada no se puede leer.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import _copy as C  # noqa: E402

def _regex_patrones(patrones):
    return [re.compile(p, re.I) for p in patrones]


CORRECCIONES = _regex_patrones(C.CORRECCION_RE)
MUEBLE = _regex_patrones(C.MUEBLE_RE)


def _plan_has_em_dash(entradas):
    n = sum(v["valor"].count("—") for v in entradas)
    return n


def analizar(plan):
    """Devuelve (fallos, avisos) como listas de dicts {ruta, msg}."""
    entradas = C.extraer(plan)
    fallos, avisos = [], []

    for e in entradas:
        rol = e["rol"]
        r = C.ROLES[rol]
        valor = e["valor"]
        tam_nom = e.get("tam_ef") or r["tam"]

        # 1) el texto no entra: el motor lo encoge (y con el titular, encoge
        #    TODAS las lineas, no solo la larga) o ya no cabe ni al minimo
        if r["modo"] == "titular":
            tam_final, escala = C.ajustar_titular(e["lineas"], tam=tam_nom, ancho_max=r["ancho"],
                                                   fam=r["fam"], peso=r["peso"])
            if tam_final is not None:
                if tam_final <= 40:
                    fallos.append({"ruta": e["ruta"],
                                   "msg": f"el {rol} no cabe ni al minimo (40 px): el motor "
                                          f"lo recorta o se sale de la zona segura"})
                elif escala < 0.87:
                    avisos.append({"ruta": e["ruta"],
                                   "msg": f"el {rol} queda en {tam_final} px (de {tam_nom}): la "
                                          f"linea mas larga encoge todas las lineas (x{escala:.2f})"})
        elif r["modo"] == "bloque":
            tam_final, escala = C.ajustar_bloque(valor, rol)
            if tam_final is not None and escala < 0.60:
                avisos.append({"ruta": e["ruta"],
                               "msg": f"el bloque queda en {tam_final} px (de {tam_nom}): se "
                                      f"encoge para caber (x{escala:.2f})"})
        else:
            tam_final, escala = C.ajustar_texto(valor, rol, tam_efectivo=tam_nom)
            if tam_final is not None:
                if tam_final <= 18:
                    fallos.append({"ruta": e["ruta"],
                                   "msg": "el texto no cabe ni al minimo (18 px): el motor lo "
                                          "recorta o se sale de la zona segura"})
                elif escala < 0.85:
                    avisos.append({"ruta": e["ruta"],
                                   "msg": f"el texto queda en {tam_final} px (de {tam_nom}): "
                                          f"se encoge para entrar (x{escala:.2f})"})

        # 2) demasiadas lineas para el rol
        if len(e["lineas"]) > r["lineas"]:
            fallos.append({"ruta": e["ruta"],
                           "msg": f"{len(e['lineas'])} lineas para un {rol} (max {r['lineas']})"})

        # 3) demasiadas palabras
        if r.get("por_linea"):
            for linea in e["lineas"]:
                n = C.n_palabras(linea)
                if n > r["palabras"]:
                    avisos.append({"ruta": e["ruta"],
                                   "msg": f"una pildora de {n} palabras (max {r['palabras']})"})
                    break
        else:
            n = C.n_palabras(valor)
            if n > r["palabras"]:
                avisos.append({"ruta": e["ruta"],
                               "msg": f"{n} palabras en un {rol} (max {r['palabras']}): es una "
                                      f"frase, no un titulo"})

        # 4) vocabulario de genero
        for g in C.GENERO_RE:
            if re.search(r"\b" + g, valor, re.I):
                avisos.append({"ruta": e["ruta"],
                               "msg": f"vocabulario de genero: '{g}'"})
                break

        # 5) la correccion "no es solo X, es Y"
        for rx in CORRECCIONES:
            if rx.search(valor):
                avisos.append({"ruta": e["ruta"], "msg": "la correccion 'no es solo X, es Y'"})
                break

        # 6) tricolonio: solo es tell en un rol de titulo
        if rol in C.ROLES_TITULO:
            for linea in e["lineas"]:
                if C.es_tricolon(linea):
                    avisos.append({"ruta": e["ruta"], "msg": "tricolonio: 'Rápido. Simple. Seguro.'"})
                    break

        # 7) furniture text
        for rx in MUEBLE:
            if rx.search(valor):
                avisos.append({"ruta": e["ruta"], "msg": "texto de mobiliario (metadato que nadie pidio)"})
                break

        # 8) glifos como icono
        for g in C.GLIFO_RE:
            if g in valor:
                avisos.append({"ruta": e["ruta"], "msg": f"glifo decorativo '{g}' en vez de icono"})
                break

    # 9) el motor dibuja un maximo: lo que excede se pierde SIN aviso
    for i, esc in enumerate(plan.get("escenas") or []):
        if not isinstance(esc, dict):
            continue
        tipo = str(esc.get("tipo", "")).lower()
        limite = C.LIMITES_ITEMS.get(tipo)
        if limite and len(esc.get("items") or []) > limite:
            n = len(esc["items"])
            fallos.append({"ruta": f"escenas[{i}]",
                           "msg": f"la escena '{tipo}' dibuja {limite} items: {n - limite} se "
                                  f"pierden en silencio; usa menos items o otra escena"})
        for clave, max_lineas in (C.LIMITES_LINEAS.get(tipo) or {}).items():
            texto = esc.get(clave)
            if not isinstance(texto, str) or not texto.strip():
                continue
            n_lineas = C.lineas_subtitulo_hero(texto)
            if n_lineas and n_lineas > max_lineas:
                fallos.append({"ruta": f"escenas[{i}].{clave}",
                               "msg": f"el motor dibuja {max_lineas} lineas y este texto ocupa "
                                      f"{n_lineas}: la ultima se pierde en silencio"})

    # 10) toda cifra lleva su fuente (principio de la skill)
    for i, esc in enumerate(plan.get("escenas") or []):
        if not isinstance(esc, dict):
            continue
        cifras = _cifras_de(esc)
        if cifras and not (esc.get("fuente") or esc.get("pie")):
            avisos.append({"ruta": f"escenas[{i}]",
                           "msg": f"cifra sin fuente ({', '.join(cifras[:3])}): toda cifra lleva su fuente"})

    # 11) el modelo antes del dibujo: un solo dato por concepto
    _chequear_modelo(plan, fallos, avisos)

    # 12) los cues de SFX: sonido conocido, ancla valida, densidad con turno
    _chequear_sfx(plan, fallos, avisos)

    # 10b) una fuente declarada en una escena que NO la dibuja: el
    # espectador no la vera y la regla "toda cifra lleva su fuente" no se
    # cumple. se comprueba contra el motor, no contra una lista a mano.
    _dibujan = _escenas_que_dibujan_la_fuente()
    if isinstance(_dibujan, str):
        avisos.append({"ruta": "escenas[]",
                       "msg": f"no se puede leer el motor para saber que escenas dibujan "
                              f"la fuente ({_dibujan}): este check no puede afirmar nada"})
        _dibujan = None
    if _dibujan is not None:
        for i, esc in enumerate(plan.get("escenas") or []):
            if not isinstance(esc, dict) or not esc.get("fuente"):
                continue
            tipo = str(esc.get("tipo", "")).lower()
            if tipo and tipo not in _dibujan:
                avisos.append({"ruta": f"escenas[{i}]",
                               "msg": f"la escena '{tipo}' declara fuente pero no la dibuja: "
                                      f"el espectador no la vera. anade pie_fuente al motor "
                                      f"o quita el campo `fuente`"})

    # 11) cita: su origen o marca que es voz de marca
    for i, esc in enumerate(plan.get("escenas") or []):
        if isinstance(esc, dict) and str(esc.get("tipo", "")).lower() == "quote":
            if esc.get("autor") and not (esc.get("fuente") or esc.get("nota")):
                avisos.append({"ruta": f"escenas[{i}]",
                               "msg": "cita sin origen declarado: pon la fuente o marca que es voz de marca"})

    # 12) la misma escena dos veces seguidas se lee como relleno
    tipos = C.orden_escenas(plan)
    for i in range(len(tipos) - 1):
        if tipos[i] == tipos[i + 1] and tipos[i] not in ("final",):
            avisos.append({"ruta": f"escenas[{i}] -> escenas[{i+1}]",
                           "msg": f"dos escenas '{tipos[i]}' seguidas: se lee como relleno"})

    # 13) bento de tres: el "tres cosas paralelas" por defecto
    for i, esc in enumerate(plan.get("escenas") or []):
        if isinstance(esc, dict) and str(esc.get("tipo", "")).lower() == "bento":
            if len(esc.get("items") or []) == 3:
                avisos.append({"ruta": f"escenas[{i}]",
                               "msg": "bento de tres: usa el numero que tiene el contenido"})

    # 14) el guion em dash como costumbre
    n_em = _plan_has_em_dash(entradas)
    if n_em > 1:
        avisos.append({"ruta": "plan", "msg": f"{n_em} rayas em: usa punto"})

    return fallos, avisos


def _escenas_que_dibujan_la_fuente():
    """Los tipos de escena que DIBUJAN la fuente (leido del motor por AST).

    El linter acepta el campo `fuente` en cualquier escena, pero el motor
    solo lo dibuja en las que lo llaman: si una escena declara una fuente y
    no la dibuja, el espectador no la ve y la regla "toda cifra lleva su
    fuente" es una mentira para esa escena. Se lee del motor para que la
    lista no se pueda quedar vieja.
    """
    import ast
    import os
    motor = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "render_plan.py")
    try:
        with open(motor, encoding="utf-8") as fh:
            arbol = ast.parse(fh.read())
    except (OSError, SyntaxError, ValueError) as e:
        # NO se traga en silencio: si el motor no se puede leer, este check
        # no puede affirmar nada, y callar seria un check apagado
        return f"__error__:{type(e).__name__}"
    out = set()
    for n in arbol.body:
        if not isinstance(n, ast.FunctionDef):
            continue
        if any(isinstance(x, ast.Call) and isinstance(x.func, ast.Name)
               and x.func.id == "pie_fuente" for x in ast.walk(n)):
            out.add(n.name[3:])          # sc_gauge -> gauge
    return out


def _cifras_de(esc):
    """Valores numericos mostrados en pantalla (dato, no decoracion)."""
    out = []
    if isinstance(esc.get("valor"), (int, float)):
        out.append(str(esc["valor"]))
    for clave in ("cards", "barras", "items"):
        for sub in esc.get(clave) or []:
            if isinstance(sub, dict) and isinstance(sub.get("valor"), (int, float)):
                out.append(str(sub["valor"]))
    return out


def _datos_del_plan(plan):
    return plan.get("datos") or {}


def _refs_dato(nodo, acc):
    """Recolecta las referencias {"$dato": nombre} de un nodo."""
    if isinstance(nodo, dict):
        if "$dato" in nodo and len(nodo) == 1:
            acc.append(nodo["$dato"])
        for v in nodo.values():
            _refs_dato(v, acc)
    elif isinstance(nodo, list):
        for v in nodo:
            _refs_dato(v, acc)
    return acc


def _etiquetas_con_valor(plan):
    """(etiqueta normalizada, valor, ruta) de cada cifra que lleva nombre."""
    salida = []
    for i, esc in enumerate(plan.get("escenas") or []):
        if not isinstance(esc, dict):
            continue
        pares = []
        if isinstance(esc.get("valor"), (int, float)):
            pares.append((esc.get("etiqueta") or esc.get("rotulo") or "", esc["valor"]))
        for clave in ("cards", "barras"):
            for j, sub in enumerate(esc.get(clave) or []):
                if isinstance(sub, dict) and isinstance(sub.get("valor"), (int, float)):
                    pares.append((sub.get("etiqueta", ""), sub["valor"]))
        for et, val in pares:
            if et:
                salida.append((_norm(et), val, f"escenas[{i}]"))
    return salida


def _norm(t):
    return " ".join(str(t).lower().split())


def _chequear_sfx(plan, fallos, avisos):
    """Los cues de SFX del plan: sonido conocido, ancla valida y densidad.

    La densidad la fija la doctrina: entre 8 y 12 cues por minuto. Menos
    suena vacio; mas, saturado.
    """
    cues = plan.get("sfx") or []
    if not cues:
        return
    dur = float(plan.get("duracion") or 0)
    escenas = [e for e in (plan.get("escenas") or []) if isinstance(e, dict)]
    anclas = ("escena", "palabra", "beat", "pico", "absoluta")
    for i, cue in enumerate(cues):
        if not isinstance(cue, dict):
            fallos.append({"ruta": f"sfx[{i}]", "msg": "el cue no es un objeto"})
            continue
        sonido = cue.get("sonido")
        if sonido not in C.SONIDOS_SFX:
            fallos.append({"ruta": f"sfx[{i}]",
                           "msg": f"sonido desconocido '{sonido}' "
                                  f"(disponibles: {', '.join(C.SONIDOS_SFX)})"})
        ancla = cue.get("ancla", "absoluta")
        if ancla not in anclas:
            fallos.append({"ruta": f"sfx[{i}]", "msg": f"ancla desconocida '{ancla}'"})
        elif ancla == "escena":
            n = cue.get("escena")
            if not isinstance(n, int) or n < 1 or n > len(escenas):
                fallos.append({"ruta": f"sfx[{i}]", "msg": f"escena {n} fuera de rango"})
        elif ancla == "palabra" and not cue.get("palabra"):
            fallos.append({"ruta": f"sfx[{i}]", "msg": "ancla 'palabra' sin 'palabra'"})
        elif ancla == "beat" and not cue.get("beat"):
            fallos.append({"ruta": f"sfx[{i}]", "msg": "ancla 'beat' sin 'beat'"})
        elif ancla == "pico" and not cue.get("pico"):
            fallos.append({"ruta": f"sfx[{i}]", "msg": "ancla 'pico' sin 'pico'"})
        elif ancla == "absoluta" and cue.get("t") is None:
            fallos.append({"ruta": f"sfx[{i}]", "msg": "ancla 'absoluta' sin 't'"})
    if dur > 0:
        dens = len(cues) / (dur / 60.0)
        if dens > C.DENSIDAD_SFX_MAX:
            avisos.append({"ruta": "sfx",
                           "msg": f"densidad de {dens:.1f} cues/min (max {C.DENSIDAD_SFX_MAX}): "
                                  f"la pieza se va a saturar"})
        elif dens < C.DENSIDAD_SFX_MIN and dur > 6:
            avisos.append({"ruta": "sfx",
                           "msg": f"densidad de {dens:.1f} cues/min: por debajo de "
                                  f"{C.DENSIDAD_SFX_MIN} puede sonar vacia"})


def _chequear_modelo(plan, fallos, avisos):
    """EL MODELO ANTES DEL DIBUJO: un solo dato por concepto.

    - una referencia $dato que el plan no declara: FALLO (el render muere)
    - un dato declarado sin su fuente: AVISO
    - la misma etiqueta con dos valores distintos: AVISO (es una contradiccion)
    """
    datos = _datos_del_plan(plan)
    if not isinstance(datos, dict):
        fallos.append({"ruta": "datos", "msg": "el bloque 'datos' debe ser un objeto"})
        return
    for nombre, entrada in datos.items():
        if not isinstance(entrada, dict) or "valor" not in entrada:
            fallos.append({"ruta": f"datos.{nombre}", "msg": "el dato no tiene 'valor'"})
        elif not (entrada.get("fuente") or "").strip():
            avisos.append({"ruta": f"datos.{nombre}",
                           "msg": "el dato no declara su fuente (toda cifra lleva su fuente)"})
    for i, esc in enumerate(plan.get("escenas") or []):
        if not isinstance(esc, dict):
            continue
        refs = _refs_dato(esc, [])
        for nombre in refs:
            if nombre not in datos:
                fallos.append({"ruta": f"escenas[{i}]",
                               "msg": f"referencia al dato '{nombre}', que el plan no declara"})
    visto = {}
    for et, val, ruta in _etiquetas_con_valor(plan):
        clave = _norm(et)
        if clave in visto and visto[clave][0] != val:
            avisos.append({"ruta": ruta,
                           "msg": f"el dato '{et}' aparece con dos valores "
                                  f"({visto[clave][0]} en {visto[clave][1]} y {val}): contradiccion"})
        else:
            visto.setdefault(clave, (val, ruta))


def main():
    ap = argparse.ArgumentParser(
        description="Comprueba el copy de un plan: longitudes, tells de genero, "
                    "cifras sin fuente y orden de escenas.",
        epilog="El copy se escribe para entrar en la zona segura; el motor encoge, "
               "no reescribe. Sale 0 si no hay fallos, 1 si hay fallos, 2 si la entrada no existe.")
    ap.add_argument("plan", help="ruta del plan.json a auditar")
    ap.add_argument("--json", action="store_true",
                    help="devuelve el informe en JSON por stdout en vez de texto")
    ap.add_argument("--strict", action="store_true",
                    help="tratar tambien los avisos como fallo (codigo de salida 1)")
    args = ap.parse_args()

    if not os.path.exists(args.plan):
        print(f"ERROR: no existe el plan '{args.plan}'", file=sys.stderr)
        return 2
    try:
        plan = C.cargar_plan(args.plan)
    except (OSError, ValueError) as ex:
        print(f"ERROR: no se puede leer el plan '{args.plan}': {ex}", file=sys.stderr)
        return 2
    if not isinstance(plan, dict) or not plan.get("escenas"):
        print(f"ERROR: '{args.plan}' no parece un plan de EditorIA (sin escenas)", file=sys.stderr)
        return 2

    fallos, avisos = analizar(plan)
    if args.json:
        print(json.dumps({"plan": args.plan, "fallos": fallos, "avisos": avisos},
                         ensure_ascii=False, indent=1))
    else:
        for etiqueta, lista in (("FALLO", fallos), ("AVISO", avisos)):
            for h in lista:
                print(f"{etiqueta} {h['ruta']}: {h['msg']}")
        print(f"COPY: {len(fallos)} fallos, {len(avisos)} avisos "
              f"({len(plan.get('escenas') or [])} escenas)")
    return 1 if (fallos or (args.strict and avisos)) else 0


if __name__ == "__main__":
    sys.exit(main())
