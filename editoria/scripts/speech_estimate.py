#!/usr/bin/env python3
"""speech_estimate.py — Estimación determinista de duración del habla pre-TTS.
Inspirado en @hypit/speech-estimate.
Calcula la duración estimada del habla antes de sintetizar audio (vía ElevenLabs u otro TTS),
permitiendo auditar planes, evitar solapamientos y redimensionar escenas sin incurrir en costos de API.

Las cifras se cuentan como se DICEN ("$142.332" son ocho palabras habladas,
no una): miles, decimales, % y moneda se expanden a palabras (es/en) antes de
contar sílabas. Para una voz concreta, --calibrar mide su ritmo real con el
palabras.json de esa voz (scripts/alinear.py): sílabas entre la primera y la
última palabra, pausas incluidas.

Uso CLI:
  python speech_estimate.py "Texto a estimar" [--idioma es] [--ritmo normal]
  python speech_estimate.py guion.txt --calibrar voz.palabras.json
  python speech_estimate.py plan.json --auditar
"""
import os, sys, re, json, argparse

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg_tools"))
from _comun import leer_palabras  # noqa: E402

# Tasas empíricas de pronunciación (unidades por segundo)
# Español: sílabas/segundo | Inglés: sílabas fonéticas/segundo
RITMOS = {
    "es": {"slow": 4.72, "normal": 5.90, "fast": 7.375},
    "en": {"slow": 4.20, "normal": 4.60, "fast": 5.60},
}


def contar_silabas_espanol(palabra: str) -> int:
    """Cuenta núcleos silábicos en español reconociendo diptongos e hiatos."""
    p = palabra.lower()
    p = re.sub(r"[^a-záéíóúüñ]", "", p)
    if not p:
        return 0
    # 'y' final o aislada suena como 'i'
    if p == "y":
        return 1
    p = re.sub(r"y$", "i", p)

    # Identificar corridas de vocales
    corridas = re.findall(r"[aeiouáéíóúü]+", p)
    nucleos = 0
    for c in corridas:
        # Hiatos por vocal cerrada acentuada (í, ú)
        partes = re.split(r"([íú])", c)
        for part in partes:
            if part in ("í", "ú"):
                nucleos += 1
            elif part:
                # Vocales abiertas (a, e, o, á, é, ó) forman núcleos separados si no son diptongo
                abiertas = len(re.findall(r"[aeoáéó]", part))
                nucleos += max(1, abiertas)
    return max(1, nucleos)


def contar_silabas_ingles(palabra: str) -> int:
    """Heurística morfológica para sílabas en inglés sin dependencias pesadas."""
    p = palabra.lower()
    p = re.sub(r"[^a-z]", "", p)
    if not p:
        return 0
    if len(p) <= 3:
        return 1
    # Quitar terminaciones mudas
    p = re.sub(r"(?:[^laeiouy]|ed|es|e)$", "", p)
    p = re.sub(r"^y", "", p)
    matches = re.findall(r"[aeiouy]{1,2}", p)
    return max(1, len(matches))


contar_silabas_es = contar_silabas_espanol
contar_silabas_en = contar_silabas_ingles

STOP_ES = set("el la los las de que y en un una es por con para no se su al lo como más pero".split())
STOP_EN = set("the and of to in is it you that for with on are this be your was at as have not".split())


def detectar_idioma(texto: str) -> str:
    """'es' o 'en' por palabras frecuentes y tildes; ante la duda, 'es'."""
    ws = re.findall(r"[a-záéíóúñü]+", texto.lower())
    es = sum(w in STOP_ES for w in ws) + 2 * len(re.findall(r"[ñáéíóú¿¡]", texto.lower()))
    return "en" if sum(w in STOP_EN for w in ws) > es else "es"


# ───────────── cifras → palabras (la voz dice "ciento cuarenta y dos mil") ─────────────

_UNIDADES_ES = ("cero uno dos tres cuatro cinco seis siete ocho nueve diez once doce trece "
                "catorce quince dieciséis diecisiete dieciocho diecinueve veinte veintiuno "
                "veintidós veintitrés veinticuatro veinticinco veintiséis veintisiete "
                "veintiocho veintinueve").split()
_DECENAS_ES = "_ _ _ treinta cuarenta cincuenta sesenta setenta ochenta noventa".split()
_CIENTOS_ES = ("_ ciento doscientos trescientos cuatrocientos quinientos seiscientos "
               "setecientos ochocientos novecientos").split()
_UNIDADES_EN = ("zero one two three four five six seven eight nine ten eleven twelve "
                "thirteen fourteen fifteen sixteen seventeen eighteen nineteen").split()
_DECENAS_EN = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def _menor_mil(n: int, idioma: str) -> str:
    c, r = divmod(n, 100)
    if idioma == "es":
        if n == 100:
            return "cien"
        pal = [_CIENTOS_ES[c]] if c else []
        if r < 30:
            pal += [_UNIDADES_ES[r]] if r or not c else []
        else:
            d, u = divmod(r, 10)
            pal += [_DECENAS_ES[d]] + (["y", _UNIDADES_ES[u]] if u else [])
        return " ".join(pal)
    pal = [_UNIDADES_EN[c], "hundred"] if c else []
    if r >= 20:
        d, u = divmod(r, 10)
        pal += [_DECENAS_EN[d]] + ([_UNIDADES_EN[u]] if u else [])
    elif r or not c:
        pal += [_UNIDADES_EN[r]]
    return " ".join(pal)


def numero_a_palabras(n: int, idioma: str = "es") -> str:
    """Entero >= 0 → como se dice (es/en), hasta billones."""
    escalas = ([(10**12, "billón", "billones"), (10**6, "millón", "millones"), (1000, "mil", "mil")]
               if idioma == "es" else
               [(10**12, "trillion", "trillion"), (10**9, "billion", "billion"),
                (10**6, "million", "million"), (1000, "thousand", "thousand")])
    for valor, sing, plur in escalas:
        if n >= valor:
            q, r = divmod(n, valor)
            if idioma == "es" and q == 1:
                cabeza = "mil" if valor == 1000 else "un " + sing
            else:
                cabeza = numero_a_palabras(q, idioma) + " " + plur
            return cabeza + (" " + numero_a_palabras(r, idioma) if r else "")
    return _menor_mil(n, idioma)


_CIFRA_RE = re.compile(r"([$€£]?)(\d+(?:[.,]\d+)*)(\s*%)?")
_MONEDA = {"es": {"$": "dólares", "€": "euros", "£": "libras"},
           "en": {"$": "dollars", "€": "euros", "£": "pounds"}}


def _cifra_dicha(m, idioma: str) -> str:
    moneda, num, pct = m.group(1), m.group(2), m.group(3)
    corte = max(num.rfind("."), num.rfind(","))
    if corte < 0 or re.fullmatch(r"\d{1,3}(?:([.,])\d{3})(?:\1\d{3})*", num):
        entero, dec = re.sub(r"\D", "", num), ""       # 1240 · 1.240 · 1,240: miles
    else:                                              # 4,8 · 1.240,5: el último separador es decimal
        entero, dec = re.sub(r"\D", "", num[:corte]), num[corte + 1:]
    partes = [numero_a_palabras(int(entero), idioma)]
    if dec:
        partes += ["coma" if idioma == "es" else "point"] + [numero_a_palabras(int(d), idioma) for d in dec]
    if pct:
        partes.append("por ciento" if idioma == "es" else "percent")
    if moneda:
        partes.append(_MONEDA.get(idioma, _MONEDA["es"])[moneda])
    return " " + " ".join(partes) + " "


def texto_hablado(texto: str, idioma: str = "es") -> str:
    """Lo que la voz dirá: sin audio tags y con las cifras en palabras."""
    t = re.sub(r"\[[^\]]*\]", " ", texto or "")
    return _CIFRA_RE.sub(lambda m: _cifra_dicha(m, idioma), t)


def silabas(texto: str, idioma: str = "es") -> int:
    """Sílabas habladas del texto (cifras expandidas, tags y marcas fuera).
    Una sigla sin vocales (SQL, CSS) se deletrea: cada letra suena su nombre."""
    contar = contar_silabas_espanol if idioma == "es" else contar_silabas_ingles
    total = 0
    for p in re.findall(r"\b\w+\b", texto_hablado(texto, idioma)):
        if p.isalpha() and not re.search(r"[aeiouyáéíóúü]", p.lower()):
            total += len(p) * (2 if idioma == "es" else 1)
        else:
            total += contar(p)
    return total


def calibrar(path_palabras: str, idioma: str = None):
    """Ritmo REAL (sílabas/s) de una voz medida → (tasa, idioma). Tramo de la
    primera a la última palabra del palabras.json, con las pausas internas."""
    ps = leer_palabras(path_palabras)
    texto = " ".join(p["texto"] for p in ps)
    idioma = idioma or detectar_idioma(texto)
    tramo = ps[-1]["fin"] - ps[0]["inicio"]
    if tramo <= 0.5:
        sys.exit(f"ERROR: {path_palabras}: tramo hablado demasiado corto para calibrar ({tramo:.2f}s)")
    return silabas(texto, idioma) / tramo, idioma


def estimar_duracion(texto: str, idioma: str = "es", ritmo: str = "normal", padding: float = 0.35,
                     tasa: float = None) -> float:
    """Calcula duración estimada en segundos a partir del texto y ritmo deseado.
    padding: tiempo de amortiguación acústica para respiración y pausas de puntuación.
    """
    if not texto or not texto.strip():
        return 0.0
    
    limpio = re.sub(r"\[[^\]]*\]", " ", texto) # quitar audio-tags de dirección de voz [excited]
    limpio = re.sub(r"<[^|>]*\|([^>]*)>", r"\1", limpio) # soportar texto dual <display|spoken>
    limpio = re.sub(r"@\{/?[a-zA-Z0-9_-]+!?\}", "", limpio) # quitar tags semánticos
    if not re.search(r"\w", limpio):
        return 0.0

    tasa = tasa or RITMOS.get(idioma, RITMOS["es"]).get(ritmo, 5.90)
    unidades = silabas(limpio, idioma)

    # Pausas añadidas por puntuación (puntos, comas, signos de interrogación)
    pausas_comas = len(re.findall(r"[,;:]", limpio)) * 0.15
    pausas_puntos = len(re.findall(r"[.!?]", limpio)) * 0.30
    
    dur = (unidades / tasa) + padding + pausas_comas + pausas_puntos
    return round(dur, 2)


estimar_duracion_habla = estimar_duracion


AIRE_VOZ = 0.40  # Segundos que voz_off.py deja al inicio de cada escena

# Banda de error de la estimacion silabica, MEDIDA (no supuesta): 50 frases
# de la voz del sistema (Paulina es-MX a 178 ppm) sintetizadas con `say` y
# cronometradas con ffprobe contra su estimacion. La estimacion overestimate
# el tiempo real entre un 9% y un 24% (mediana 12%).
#
# Por que importa: la auditoria de planes (auditar_plan.py) no puede usar un
# margen FIJO mas pequeno que esa banda, porque entonces rechaza planes cuya
# narracion cabe de verdad (falso positivo) y hace recortar copy que no
# sobra. El margen va con el hueco disponible; por debajo de la banda es
# AVISO, y el que falla si las voces se pisan es el TTS real (voz_off.py /
# voz_local.py), que mide el audio sintetizado.
BANDA_ESTIMACION = 0.25


def auditar_plan_voces(plan_or_path, idioma: str = "es", aire_inicial: float = AIRE_VOZ,
                       ritmo: str = "normal") -> dict:
    """Revisa un plan.json: ¿la voz de alguna escena pisa a la siguiente?

    LA REGLA, en un solo sitio (esta es la fuente: la usan `auditar_plan.py`
    y `clonar_video.py`): la voz no puede solaparse con la voz SIGUIENTE ni
    con el final del video. Que la voz termine despues del final de SU
    propia escena NO es un defecto: una locucion que cruza el corte es
    normal, de hecho es lo habitual (por eso la voz entra en `from + 0.4`).

    Antes esta funcion exigia que la voz terminase dentro de su propia
    escena: un criterio mas estricto que el del resto de la skill, con el
    que los dos-herramientas se contradijian en los 10 planes de la demo
    (esta decia "no cabe" y la otra "cabe", cuando la narracion real SI
    cabia) y `clonar_video.py` recortaba copy de mas paralana.

    El margen es proporcional al hueco (BANDA_ESTIMACION): la estimacion
    silabica se desvía del tiempo real entre un 9% y un 24%, asi que un
    margen fijo rechazaria planes validos. Por debajo de la banda es un
    AVISO ("roza"); el que falla es el TTS real, que mide el audio.

    Devuelve {"valido": bool, "alertas": [...], "avisos": [...]}:
      · alertas: la voz pisa a la siguiente (o al final del video)
      · avisos: la roza (esta dentro de la banda de error de la estimacion)
    """
    if isinstance(plan_or_path, dict):
        plan = plan_or_path
    else:
        with open(plan_or_path, encoding="utf-8") as f:
            plan = json.load(f)

    # las escenas CON voz, en orden: la voz siguiente es la que viene despues
    con_voz = [(i, e) for i, e in enumerate(plan.get("escenas", [])) if e.get("voz")]
    dur_video = plan.get("duracion")
    alertas, avisos = [], []
    for k, (idx, e) in enumerate(con_voz):
        fr_v = float(e.get("from", 0))
        n = silabas(e["voz"], idioma)
        dur = estimar_duracion(e["voz"], idioma=idioma, ritmo=ritmo)
        fin = fr_v + aire_inicial + dur
        if k + 1 < len(con_voz):
            # el limite es donde empieza la voz siguiente
            limite = float(con_voz[k + 1][1].get("from", 0)) + aire_inicial
            contra_fin = False
        elif dur_video is not None:
            # la ultima voz: el borde del video
            limite = float(dur_video)
            contra_fin = True
        else:
            limite = None
            contra_fin = False
        if limite is None:
            continue
        hueco = limite - (fr_v + aire_inicial)
        if fin <= limite:
            continue
        exceso = round(fin - limite, 2)
        base = {
            "escena_index": idx,
            "tipo": e.get("tipo", "desconocido"),
            "voz": e["voz"],
            "silabas": n,
            "tiempo_estimado": dur,
            "tiempo_disponible_voz": round(hueco, 2),
            "exceso_segundos": exceso,
            "contra_final": contra_fin,
        }
        if exceso > max(0.3, BANDA_ESTIMACION * max(hueco, 0)):
            alertas.append(base)
        else:
            avisos.append(base)
    return {"valido": not bool(alertas), "alertas": alertas, "avisos": avisos}


def main():
    parser = argparse.ArgumentParser(description="speech_estimate — Estimación pre-TTS determinista")
    parser.add_argument("entrada", help="Texto a estimar, un .txt/.md con el guion o ruta a plan.json")
    parser.add_argument("--idioma", choices=["es", "en"], help="Idioma del hablante (default: detectado)")
    parser.add_argument("--ritmo", default="normal", choices=["slow", "normal", "fast"], help="Ritmo")
    parser.add_argument("--calibrar", metavar="PALABRAS_JSON",
                        help="usa el ritmo real de una voz medida (palabras.json de alinear.py)")
    parser.add_argument("--auditar", action="store_true", help="Audita un archivo plan.json")
    args = parser.parse_args()

    entrada = args.entrada
    if os.path.splitext(entrada)[1].lower() in (".json", ".txt", ".md") and not os.path.isfile(entrada):
        sys.exit(f"ERROR: no existe el archivo: {entrada}")
    if args.auditar or entrada.endswith(".json"):
        res = auditar_plan_voces(entrada, idioma=args.idioma or "es", ritmo=args.ritmo)
        alertas = res.get("alertas", [])
        if res.get("valido", False):
            print("OK plan validado: todas las locuciones caben holgadamente en sus escenas.")
            sys.exit(0)
        else:
            print(f"ALERTA: {len(alertas)} escena(s) exceden el tiempo asignado:")
            for a in alertas:
                print(f"  - Escena {a['escena_index']} ({a['tipo']}): disponible {a['tiempo_disponible_voz']}s, "
                      f"estimado {a['tiempo_estimado']}s (exceso: +{a['exceso_segundos']}s)")
                print(f"    Texto: \"{a['voz']}\"")
            sys.exit(1)
    else:
        if entrada.endswith((".txt", ".md")):
            with open(entrada, encoding="utf-8") as fh:
                entrada = fh.read()
        idioma = args.idioma or detectar_idioma(entrada)
        tasa, fuente = None, f"ritmo {args.ritmo}"
        if args.calibrar:
            tasa, _ = calibrar(args.calibrar, idioma)
            fuente = f"calibrado {tasa:.2f} síl/s con {args.calibrar}"
        dur = estimar_duracion(entrada, idioma=idioma, ritmo=args.ritmo, tasa=tasa)
        print(f"Duración estimada: {dur:.2f} s ({idioma}, {silabas(entrada, idioma)} sílabas, {fuente})")


if __name__ == "__main__":
    main()
