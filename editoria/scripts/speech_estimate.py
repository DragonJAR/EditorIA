#!/usr/bin/env python3
"""speech_estimate.py — Estimación determinista de duración del habla pre-TTS.
Inspirado en @hypit/speech-estimate.
Calcula la duración estimada del habla antes de sintetizar audio (vía ElevenLabs u otro TTS),
permitiendo auditar planes, evitar solapamientos y redimensionar escenas sin incurrir en costos de API.

Uso CLI:
  python speech_estimate.py "Texto a estimar" [--idioma es] [--ritmo normal]
  python speech_estimate.py plan.json --auditar
"""
import os, sys, re, json, argparse

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


def estimar_duracion(texto: str, idioma: str = "es", ritmo: str = "normal", padding: float = 0.35) -> float:
    """Calcula duración estimada en segundos a partir del texto y ritmo deseado.
    padding: tiempo de amortiguación acústica para respiración y pausas de puntuación.
    """
    if not texto or not texto.strip():
        return 0.0
    
    limpio = re.sub(r"\[[^\]]*\]", " ", texto) # quitar audio-tags de dirección de voz [excited]
    limpio = re.sub(r"<[^|>]*\|([^>]*)>", r"\1", limpio) # soportar texto dual <display|spoken>
    limpio = re.sub(r"@\{/?[a-zA-Z0-9_-]+!?\}", "", limpio) # quitar tags semánticos
    palabras = re.findall(r"\b\w+\b", limpio)
    if not palabras:
        return 0.0
    
    tasa = RITMOS.get(idioma, RITMOS["es"]).get(ritmo, 5.90)
    
    if idioma == "es":
        unidades = sum(contar_silabas_espanol(p) for p in palabras)
    else:
        unidades = sum(contar_silabas_ingles(p) for p in palabras)
        
    # Pausas añadidas por puntuación (puntos, comas, signos de interrogación)
    pausas_comas = len(re.findall(r"[,;:]", limpio)) * 0.15
    pausas_puntos = len(re.findall(r"[.!?]", limpio)) * 0.30
    
    dur = (unidades / tasa) + padding + pausas_comas + pausas_puntos
    return round(dur, 2)


estimar_duracion_habla = estimar_duracion


AIRE_VOZ = 0.40  # Segundos que voz_off.py deja al inicio de cada escena


def auditar_plan_voces(plan_or_path, idioma: str = "es", aire_inicial: float = AIRE_VOZ) -> dict:
    """Revisa un plan.json y detecta si la locución proyectada de alguna escena
    supera el tiempo disponible (to - from - aire_inicial). Retorna dict con estado y lista de alertas/desbordes."""
    if isinstance(plan_or_path, dict):
        plan = plan_or_path
    else:
        with open(plan_or_path, encoding="utf-8") as f:
            plan = json.load(f)
    
    alertas = []
    for i, e in enumerate(plan.get("escenas", [])):
        voz = e.get("voz", "")
        if not voz:
            continue
        t_bruto = float(e.get("to", 0)) - float(e.get("from", 0))
        t_disp = max(0.0, t_bruto - aire_inicial)
        t_est = estimar_duracion(voz, idioma=idioma)
        if t_est > t_disp:
            diff = round(t_est - t_disp, 2)
            alertas.append({
                "escena_index": i,
                "tipo": e.get("tipo", "desconocido"),
                "tiempo_bruto": t_bruto,
                "tiempo_disponible_voz": t_disp,
                "tiempo_estimado": t_est,
                "exceso_segundos": diff,
                "voz": voz
            })
    return {"valido": not bool(alertas), "alertas": alertas}


def main():
    parser = argparse.ArgumentParser(description="speech_estimate — Estimación pre-TTS determinista")
    parser.add_argument("entrada", help="Texto a estimar o ruta a plan.json")
    parser.add_argument("--idioma", default="es", choices=["es", "en"], help="Idioma del hablante")
    parser.add_argument("--ritmo", default="normal", choices=["slow", "normal", "fast"], help="Ritmo")
    parser.add_argument("--auditar", action="store_true", help="Audita un archivo plan.json")
    args = parser.parse_args()

    if args.auditar or args.entrada.endswith(".json"):
        res = auditar_plan_voces(args.entrada, idioma=args.idioma)
        alertas = res.get("alertas", [])
        if res.get("valido", False):
            print(f"OK plan validado: todas las locuciones caben holgadamente en sus escenas.")
            sys.exit(0)
        else:
            print(f"ALERTA: {len(alertas)} escena(s) exceden el tiempo asignado:")
            for a in alertas:
                print(f"  - Escena {a['escena_index']} ({a['tipo']}): disponible {a['tiempo_disponible']}s, "
                      f"estimado {a['tiempo_estimado']}s (exceso: +{a['exceso_segundos']}s)")
                print(f"    Texto: \"{a['voz']}\"")
            sys.exit(1)
    else:
        dur = estimar_duracion(args.entrada, idioma=args.idioma, ritmo=args.ritmo)
        print(f"Duración estimada: {dur:.2f} s ({args.idioma}, ritmo {args.ritmo})")


if __name__ == "__main__":
    main()
