#!/usr/bin/env python3
"""Reglas de copy de EditorIA: extraccion, medicion y bus de tells.

Modulo compartido por `scripts/lint_copy.py` y `scripts/qa_entrega.py`.
No es una CLI (sin main); el validador de la skill lo salta por el prefijo.

Todo lo que se mide aqui sale del motor, no de suposiciones:
  · zona segura   -> SAFE del render_plan (151 px laterales en 1080x1920)
  · ancho de linea -> el `maxw` real del titular (96% de la zona segura)
  · tamano de tipo-> el `tam` por defecto de cada funcion del render_plan
  · tipografia    -> las TTF empaquetadas en assets/fonts (la misma del render)
  · como encoge   -> replicado de `titular()` y `fuente_que_cabe()`
"""
import json
import os
import re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FUENTES = os.path.join(BASE, "assets", "fonts")

# ── geometria del motor (render_plan.py) ────────────────────────────────
W, H = 1080, 1920
MARGEN_LAT = 151
ANCHO_SEGURO = W - 2 * MARGEN_LAT            # 778 px
ANCHO_TITULAR = int(ANCHO_SEGURO * 0.96)    # maxw real de titular(): 746 px
ANCHO_GIGANTE = int(ANCHO_SEGURO * 0.94)    # el grande del remate
WORD_GAP = 36                                # el del titular en render_plan.py

FJ = "PlusJakartaSans-wght.ttf"
FM = "Montserrat-wght.ttf"

# ── roles ───────────────────────────────────────────────────────────────
# modo "titular": varias lineas comparten UN tamano (el auto-fit de titular)
# modo "texto":   una cadena que se encoge sola (fuente_que_cabe)
ROLES = {
    "titular": {"claves": ("texto1", "texto2", "lineas", "titular"), "modo": "titular",
                "tam": 120, "ancho": ANCHO_TITULAR, "lineas": 2, "palabras": 8,
                "fam": FJ, "peso": 800},
    "pildora": {"claves": ("texto",), "modo": "titular", "solo_override": True,
                "tam": 120, "ancho": ANCHO_TITULAR, "lineas": 4, "palabras": 4,
                "fam": FJ, "peso": 800, "por_linea": True},
    "display": {"claves": ("lineas",), "modo": "titular", "solo_override": True,
                "tam": 110, "ancho": ANCHO_TITULAR, "lineas": 2, "palabras": 8,
                "fam": FJ, "peso": 800},
    "gigante": {"claves": ("gigante",), "modo": "texto", "solo_override": True,
                "tam": 300, "ancho": ANCHO_GIGANTE, "lineas": 1, "palabras": 2,
                "fam": FJ, "peso": 800},
    "maquina": {"claves": ("texto",), "modo": "bloque", "solo_override": True,
                "tam": 144, "ancho": ANCHO_SEGURO, "lineas": 4, "palabras": 24,
                "fam": FJ, "peso": 800},
    "rotulo": {"claves": ("rotulo", "titulo", "badge", "kicker", "encabezado"), "modo": "texto",
               "tam": 44, "ancho": ANCHO_SEGURO, "lineas": 2, "palabras": 12,
               "fam": FM, "peso": 700},
    "subtitulo": {"claves": ("subtitulo", "sub", "nota"), "modo": "texto",
                  "tam": 32, "ancho": ANCHO_SEGURO, "lineas": 2, "palabras": 14,
                  "fam": FM, "peso": 600},
    "item": {"claves": ("titulo", "etiqueta", "nombre"), "modo": "texto",
             "tam": 32, "ancho": ANCHO_SEGURO, "lineas": 1, "palabras": 5,
             "fam": FM, "peso": 700},
    "texto": {"claves": ("texto", "desc", "descripcion", "detalle"), "modo": "texto",
              "tam": 26, "ancho": ANCHO_SEGURO, "lineas": 2, "palabras": 11,
              "fam": FM, "peso": 500},
    "pie": {"claves": ("pie", "fuente", "fuente2"), "modo": "texto",
            "tam": 24, "ancho": ANCHO_SEGURO, "lineas": 1, "palabras": 8,
            "fam": FM, "peso": 500},
    "boton": {"claves": ("boton", "cta"), "modo": "texto",
              "tam": 34, "ancho": 420, "lineas": 1, "palabras": 3,
              "fam": FM, "peso": 700},
    "declaracion": {"claves": ("cita", "quote"), "modo": "texto",
                    "tam": 44, "ancho": ANCHO_SEGURO, "lineas": 3, "palabras": 24,
                    "fam": FJ, "peso": 800},
}

# escenas donde la MISMA clave significa otra cosa que en el resto
ESCENA_OVERRIDE = {
    "pildoras": {"texto": "pildora"},
    "remate": {"lineas": "display", "gigante": "gigante"},
    "quote": {"texto": "declaracion"},
    "apertura": {"texto1": {"rol": "titular", "tam": 150},
                 "texto2": {"rol": "titular", "tam": 124}},
    "typewriter": {"texto": "maquina"},
}

# ── el pack de SFX y la densidad con que se usa ───────────────────────
SONIDOS_SFX = ("click", "pop", "drop", "whoosh", "ding", "thud", "tick", "swell")
DENSIDAD_SFX_MIN = 8      # cues por minuto (la doctrina: 8-12)
DENSIDAD_SFX_MAX = 12

# ── tells: vocabulario de genero (aviso) ───────────────────────────────
# Del registro de tells de una skill de buen gusto: los verbos y adjetivos
# que todo el mundo usa cuando no decidio nada.
GENERO_RE = ("impuls", "potenci", "revolucion", "disruptiv", "sin esfuerzo",
             "facil de usar", "todo en uno", "de ultima generacion",
             "sin precedentes", "aprovecha", "reimagin", "rediseñ",
             "redisen", "transforma tu", "eleva tu", "eleva el", "desbloquea",
             "expansion", "crecimiento exponencial", "lidera la industria",
             "solucion integral", "socio estrategico", "clave para el exito")

# la correccion: "no es solo X, es Y" / "no solo X, sino Y"
CORRECCION_RE = (
    r"no\s+(?:es\s+solo|solo|únicamente|unicamente)\b[^.]{0,60}?\b(?:sino|es)\b",
    r"no\s+se\s+trata\s+de\s+solo\b",
    r"m[áa]s\s+que\s+una?\b",
)

# furniture text: metadatos que nadie pidio en pantalla
MUEBLE_RE = (
    r"\best\.\s*\d{4}", r"\bv\d+\.\d+", r"\b20\d\d\s*[—–-]\s*20\d\d\b",
    r"latitud|longitud|coordenadas", r"\bscroll\b", r"desliza para",
    r"disponible para", r"nivel\s*:\s*\w+",
)

# glifos que hacen de icono (emoji / unicode decorativo)
GLIFO_RE = ("\U0001f300", "\U0001f4a1", "\U0001f680", "\U0001f4e6", "✨", "🔥",
            "⭐", "✅", "❌", "➜", "➔", "→", "←", "↑", "↓", "●", "◉", "★")

# el tricolon es un recurso de TITULAR, no una lista de terminos: solo cuenta
# con punto (no con el punto medio de "ICS · SCADA") y solo en un rol de titulo
ROLES_TITULO = ("titular", "rotulo", "display", "item", "pildora")


# ── tipografia ──────────────────────────────────────────────────────────
def _fuente(familia, tam, peso=800):
    """Carga la TTF variable empaquetada y fija el eje de peso, como el motor."""
    try:
        from PIL import ImageFont
    except ImportError:
        return None
    ruta = os.path.join(FUENTES, familia)
    if not os.path.exists(ruta):
        return None
    try:
        f = ImageFont.truetype(ruta, tam)
    except Exception:
        return None
    try:
        f.set_variation_by_axes([peso])
    except Exception:
        pass
    return f


def _ancho(texto, fnt):
    try:
        from PIL import Image, ImageDraw
        d = ImageDraw.Draw(Image.new("L", (10, 10)))
        return d.textlength(texto, font=fnt)
    except Exception:
        return None


def _sin_marca(texto):
    """Quita el marcado de enfasis: el motor lo lee como color, no como ancho."""
    return texto.replace("*", "")


def ajustar_titular(lineas, tam=120, ancho_max=ANCHO_TITULAR, minimo=40, fam=FJ, peso=800):
    """Replica el auto-fit de `titular()`: el tamano baja de 4 en 4 hasta que
    la linea mas ancha cabe; el minimo es 40 px. Devuelve (tam_final, escala)."""
    fnt = _fuente(fam, tam, peso)
    if fnt is None:
        return None, None
    gap = (_ancho(" ", fnt) or 0) + WORD_GAP * 0.4

    def ancho_linea(ln, f):
        palabras = [w for w in _sin_marca(ln).split(" ") if w]
        if not palabras:
            return 0.0
        suma = 0.0
        for w in palabras:
            a = _ancho(w, f)
            if a is None:
                return 0.0
            suma += a
        return suma + gap * (len(palabras) - 1)

    t = tam
    while t > minimo:
        f = _fuente(fam, t, peso)
        if f is None:
            return None, None
        if max(ancho_linea(ln, f) for ln in lineas) <= ancho_max:
            break
        t -= 4
    return t, t / tam


def ajustar_texto(texto, rol, tam_efectivo=None):
    """Replica `fuente_que_cabe()`: el tamano baja x0.92 hasta que cabe, con
    piso 18 px. Devuelve (tam_final, escala)."""
    r = ROLES[rol]
    nom = int(tam_efectivo or r["tam"])
    t = nom
    while t > 18:
        f = _fuente(r["fam"], t, r["peso"])
        if f is None:
            return None, None
        a = _ancho(_sin_marca(texto), f)
        if a is None or a <= r["ancho"]:
            break
        t = max(18, int(t * 0.92))
    return t, t / nom


def _envolver(texto, fnt, ancho):
    """Greedy word-wrap, como `linewrap()` del render_plan."""
    palabras = [w for w in _sin_marca(texto).split(" ") if w]
    lineas, actual, w_actual = [], [], 0.0
    espacio = _ancho(" ", fnt) or 0.0
    for w in palabras:
        a = _ancho(w, fnt) or 0.0
        if actual and w_actual + a > ancho:
            lineas.append(" ".join(actual))
            actual, w_actual = [w], a
        else:
            actual.append(w)
            w_actual += a + (espacio if w_actual else 0.0)
    if actual:
        lineas.append(" ".join(actual))
    return lineas or [""]


def ajustar_bloque(texto, rol):
    """Replica el encogido de `sc_typewriter`: envuelve y baja de 4 en 4
    mientras quepan mas lineas de las que el rol permite; piso 40 px."""
    r = ROLES[rol]
    t = int(r["tam"])
    while True:
        f = _fuente(r["fam"], t, r["peso"])
        if f is None:
            return None, None
        if len(_envolver(texto, f, r["ancho"])) <= r["lineas"] or t <= 40:
            break
        t -= 4
    return t, t / r["tam"]


def lineas_subtitulo_hero(texto):
    """Cuantas lineas ocupa el subtitulo del hero, con SU propio auto-fit.

    El hero lo reduce hasta que el texto entero quepa en una linea (piso
    20 px) y despues lo envuelve a 92% del ancho seguro, pero dibuja solo
    las dos primeras: la tercera se pierde sin aviso.
    """
    ancho_u = ANCHO_SEGURO
    tam = int(1080 * 0.032)          # unidad() = lado corto = 1080
    while tam > 20:
        f = _fuente(FM, tam, 600)
        if f is None:
            return None
        a = _ancho(_sin_marca(texto), f)
        if a is None or a <= int(ancho_u * 0.90):
            break
        tam = max(20, int(tam * 0.92))
    f = _fuente(FM, tam, 600)
    if f is None:
        return None
    return len(_envolver(texto, f, int(ancho_u * 0.92)))


# ── limites del motor: lo que se dibuja y lo que se pierde ─────────────
# El motor protege su layout descartando contenido. Si el plan excede el
# limite, lo que sobra NO aparece y nadie se entera: el linter lo dice.
LIMITES_ITEMS = {"bento": 4}
LIMITES_LINEAS = {"hero": {"subtitulo": 2}}


def medir(texto, tam, familia=FM, peso=600):
    """Ancho en px del texto con la tipografia real del motor."""
    fnt = _fuente(familia, tam, peso)
    if fnt is None:
        return None
    return _ancho(_sin_marca(texto), fnt)


# ── extraccion: recorrido del plan ──────────────────────────────────────
def _es_texto(v):
    return isinstance(v, str) and v.strip() != ""


def _lineas_de(v):
    """Un texto puede venir como string o como lista de lineas."""
    if isinstance(v, str):
        return [v] if _es_texto(v) else []
    if isinstance(v, list):
        return [x for x in v if _es_texto(x)]
    return []


def _rol(clave, tipo_escena, anidado=False):
    """El rol de un texto: por clave, con correcciones por escena.
    Devuelve (rol, tam_efectivo): el tamano puede variar por escena."""
    override = ESCENA_OVERRIDE.get(tipo_escena, {})
    if clave in override:
        ov = override[clave]
        if isinstance(ov, dict):
            return ov["rol"], ov.get("tam")
        return ov, None
    if anidado:
        if clave in ("titulo", "etiqueta", "nombre"):
            return "item", None
        if clave in ("texto", "desc", "descripcion", "detalle"):
            return "texto", None
        return None, None
    for rol, r in ROLES.items():
        if r.get("solo_override"):
            continue
        if clave in r["claves"]:
            return rol, None
    return None, None


def extraer(plan):
    """Recorre el plan y devuelve la lista de textos a juzgar.

    Cada entrada: {ruta, clave, rol, lineas, valor, contexto}
    `contexto` distingue el texto suelto de una escena del texto de un item.
    """
    salida = []
    escenas = plan.get("escenas") or []
    for i, esc in enumerate(escenas):
        if not isinstance(esc, dict):
            continue
        tipo = str(esc.get("tipo", "")).lower()
        for clave, valor in esc.items():
            if clave in ("tipo", "from", "to", "at", "brand", "tamano", "duracion"):
                continue
            ruta = f"escenas[{i}]"
            if clave in ("items", "cards", "mensajes", "porciones", "notificaciones"):
                for j, sub in enumerate(valor):
                    if not isinstance(sub, dict):
                        continue
                    for c2, v2 in sub.items():
                        l2 = _lineas_de(v2)
                        if not l2:
                            continue
                        rol, tam_ef = _rol(c2, tipo, anidado=True)
                        if rol:
                            salida.append({"ruta": f"{ruta}.{clave}[{j}].{c2}", "clave": c2,
                                           "rol": rol, "tam_ef": tam_ef, "lineas": l2,
                                           "valor": " ".join(l2), "contexto": "item"})
                continue
            lineas = _lineas_de(valor)
            if not lineas:
                continue
            rol, tam_ef = _rol(clave, tipo)
            if rol:
                salida.append({"ruta": f"{ruta}.{clave}", "clave": clave, "rol": rol,
                               "tam_ef": tam_ef, "lineas": lineas, "valor": " ".join(lineas),
                               "contexto": "escena"})
    return salida


def cargar_plan(ruta):
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def orden_escenas(plan):
    return [str(e.get("tipo", "")).lower() for e in (plan.get("escenas") or [])
            if isinstance(e, dict)]


def n_palabras(texto):
    """Palabras de un texto: los separadores sueltos (punto medio, barra) no."""
    partes = [p for p in re.split(r"\s+", texto)
              if p and p not in ("·", "/", "|", "•", "—")]
    return len(partes)


def es_tricolon(linea):
    """Tricolonio: tres afirmaciones cortas separadas por punto.
    No cuenta una lista de terminos separada por punto medio."""
    segs = [s.strip() for s in re.split(r"\.\s+", linea) if s.strip()]
    if len(segs) < 3:
        return False
    return all(len(s.split()) <= 2 for s in segs)
