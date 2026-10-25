#!/usr/bin/env python3
"""clonar_video.py — Motor de clonación y variación viral de videos (inspirado en Hypit).

Ingeniería inversa de videos virales en dos comandos:
1. 'analizar': Ingiere un video de referencia (o URL), extrae cortes, audio,
   ritmo y estructura narrativa, generando 'plantilla.json' y 'ANALYSIS.md'.
2. 'variar': Genera N variantes únicas del video en formato 'plan.json'
   adaptando el tema, permutando escenas visuales equivalentes y validando
   la cadencia de habla con 'speech_estimate.py'.

Uso:
  python3 scripts/clonar_video.py analizar --video ref.mp4 --out clon_trabajo/
  python3 scripts/clonar_video.py analizar --url "https://youtube.com/shorts/..." --out clon_trabajo/
  python3 scripts/clonar_video.py variar --plantilla clon_trabajo/plantilla.json --variantes 3 --tema "Ciberseguridad" --out variantes/
"""
import argparse
import copy
import json
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))
import referencia as REF
import speech_estimate as SE


# Familias de escenas compatibles para variación de layouts visuales (100% catálogo oficial de 39 escenas)
FAMILIAS_ESCENAS = {
    "hook": ["titular", "apertura", "hero", "pildoras", "countdown", "buscador"],
    "dato": ["stats", "ranking", "bars", "gauge", "pie", "bento"],
    "social": ["chat", "comentario", "notificacion", "quote"],
    "proceso": ["pasos", "timeline", "orbita", "leads", "handoff", "hoy"],
    "cierre": ["final", "remate", "audiowave", "oferta", "confetti"]
}

# Mapeo canónico de alias a escenas registradas en render_plan.py
MAPEO_ESCENAS_VALIDAS = {
    "titular": "apertura",
    "pregunta": "apertura",
    "alerta": "buscador",
    "tarjeta": "bento",
    "terminal": "bento",
    "comparativa": "versus",
    "tweet": "comentario",
    "comunidad": "chat",
    "embudo": "pasos",
    "piramide": "ranking",
    "mapa": "timeline",
    "cta": "oferta",
    "logogrid": "final",
    "pantalla": "demo"
}


def _ajustar_voz(texto, hueco):
    """Corta la voz para que quepa en el hueco, con el margen real.

    `hueco` es el tiempo hasta donde empieza la voz SIGUIENTE (o hasta el
    final del video), y la voz entra en `from + 0.4 s` (el aire), asi que el
    tiempo util es `hueco - AIRE_VOZ`. Es la MISMA cuenta que la auditoria
    (`speech_estimate.auditar_plan_voces`).

    Antes se comparaba contra la duracion de la PROPIA escena: un criterio
    mas estricto que el del resto de la skill (una locucion que cruza el
    corte es normal, de hecho es lo habitual), asi que el clonado perdia
    palabras que si cabian. Si la variante nace con la voz desbordada, el
    plan no pasa la puerta y el agente tiene que descubrirlo al auditar el
    plan, no al clonarlo. Aqui se recorta POR PALABRAS hasta que entra.
    """
    util = max(0.2, hueco - SE.AIRE_VOZ)
    palabras = texto.split()
    while palabras and SE.estimar_duracion(" ".join(palabras), "es") > util:
        palabras.pop()
    if not palabras:
        # ni una palabra entra: el texto se deja vacio y lo escribe el agente
        return ""
    return " ".join(palabras)


def rebase_at(obj, offset, factor=1.0):
    """Desplaza y escala recursivamente los timestamps relativos al timeline absoluto."""
    if isinstance(obj, dict):
        res = {}
        for k, v in obj.items():
            if k == "at":
                if isinstance(v, (int, float)):
                    res[k] = round(offset + v * factor, 2)
                elif isinstance(v, dict):
                    res[k] = {
                        sk: (round(offset + sv * factor, 2) if isinstance(sv, (int, float))
                             else [round(offset + item * factor, 2) for item in sv] if isinstance(sv, list)
                             else sv)
                        for sk, sv in v.items()
                    }
                elif isinstance(v, list):
                    res[k] = [round(offset + item * factor, 2) if isinstance(item, (int, float)) else item for item in v]
                else:
                    res[k] = v
            else:
                res[k] = rebase_at(v, offset, factor)
        return res
    elif isinstance(obj, list):
        return [rebase_at(item, offset, factor) for item in obj]
    else:
        return obj


def _momentos_medidos(video_path):
    """Los momentos del video, MEDIDOS.

    Una sola fuente para la medicion: este modulo NO reimplementa el corte de
    plano ni la envolvente de audio, se los pide a la herramienta que ya lo
    hace (`scripts/ffmpeg_tools/scenes.py`: scdet para los cortes, envolvente
    RMS cada 0.5 s, picos de audio y highlights ordenados por valor).

    Devuelve None si la herramienta no esta o falla: el llamador cae a la
    deteccion por silencio (mas pobre, pero nunca inventada).
    """
    script = os.path.join(BASE, "scripts", "ffmpeg_tools", "scenes.py")
    if not os.path.isfile(script):
        return None
    try:
        r = subprocess.run([sys.executable, script, video_path, "--json",
                            "--highlights", "8"],
                           capture_output=True, text=True, timeout=900)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    try:
        d = json.loads(r.stdout)
    except ValueError:
        return None
    if not isinstance(d, dict) or not d.get("scenes"):
        return None
    return d


def _segmentos_medidos(mid):
    """Los segmentos del video con el VALOR medido al lado.

    El rol NO lo pone la medicion: lo pone la estructura que se esta clonando
    (primero el gancho, ultimo el cierre, el cuerpo alternando social/dato),
    porque clonar es reproducir el patron del original. Lo que si pone la
    medicion es el VALOR de cada tramo y donde esta el pico: sin eso, el rol
    era una suposicion sobre una posicion.
    """
    escenas = mid.get("scenes") or []
    picos = mid.get("audio_peaks") or []

    # el pico de audio MAS fuerte dentro de cada escena
    pico_de = {}
    for p in picos:
        t = p.get("time")
        if t is None:
            continue
        for i, sc in enumerate(escenas):
            if sc["start"] <= t < sc["end"]:
                if i not in pico_de or (p.get("rms") or 0) > (pico_de[i].get("rms") or 0):
                    pico_de[i] = p

    n = len(escenas)
    max_rms = max((sc.get("audio_rms") or 0) for sc in escenas) if escenas else 0
    # que tramo es el mas fuerte (ranking por valor; el ORDEN no cambia)
    orden = sorted(range(n), key=lambda i: -(escenas[i].get("audio_rms") or 0))
    fuerza = {i: r + 1 for r, i in enumerate(orden)}

    # Sin cortes duros no hay estructura que repartir en roles: una pieza
    # de animacion continua (scdet ve 1-2 tramos en minutos de video) no
    # tiene HOOK ni CIERRE localizables por posicion. Inventarlos (el
    # primer tramo «hook», el resto «cierre») deja una plantilla inutil:
    # se marca como continua y los beats se sacan de la transcripcion y
    # los mosaicos, no de los cortes (references/referencia-video.md §3).
    continua = n <= 2
    segmentos = []
    for i, sc in enumerate(escenas):
        if continua:
            rol = "continuo"
        elif i == 0:
            rol = "hook"
        elif i == n - 1:
            rol = "cierre"
        else:
            rol = "social" if (i - 1) % 2 else "dato"
        pico = pico_de.get(i)
        rms = round(sc.get("audio_rms") or 0, 4)
        if pico:
            nota = (f"pico de audio en {round(pico['time'], 2)}s "
                    f"({round(pico.get('rms') or 0, 4)} RMS)")
            if rms >= max_rms and max_rms > 0:
                nota += ": el tramo mas fuerte del video"
        else:
            nota = "sin pico de audio: tramo tranquilo (no sostiene el climax)"
        segmentos.append({
            "indice": i + 1,
            "from": round(sc["start"], 2),
            "to": round(sc["end"], 2),
            "duracion": round(sc["end"] - sc["start"], 2),
            "rol": rol,
            "tipo_sugerido": None if continua else FAMILIAS_ESCENAS[rol][0],
            "audio_rms": rms,
            "audio_peak": round(sc.get("audio_peak") or 0, 4),
            "pico": round(pico["time"], 2) if pico else None,
            "fuerza": fuerza.get(i),
            "nota": nota,
        })
    return segmentos


def detectar_cortes(video_path, duracion_total):
    """Detecta cortes aproximados por silencio o cambios de plano."""
    script_silence = os.path.join(BASE, "scripts", "ffmpeg_tools", "silence.py")
    cortes = [0.0]
    if os.path.isfile(script_silence):
        r = subprocess.run([sys.executable, script_silence, video_path, "-d", "0.25"],
                           capture_output=True, text=True)
        # Parsear líneas de silencio si existen
        for ln in (r.stdout or "").splitlines():
            if "silence_start:" in ln:
                try:
                    t = float(ln.split("silence_start:")[1].split()[0])
                    if 1.0 < t < duracion_total - 1.0:
                        cortes.append(round(t, 2))
                except Exception:
                    pass

    # Si no detectó suficientes cortes o no hay audio, segmentar con cadencia viral estándar:
    # Gancho: 0-2.5s, Segmento 1: 2.5-6.0s, Segmento 2: 6.0-10.0s, etc.
    if len(cortes) < 3:
        cadencia = [0.0, min(2.5, duracion_total * 0.25)]
        curr = cadencia[-1]
        paso = 3.5
        while curr + paso < duracion_total - 1.5:
            curr += paso
            cadencia.append(round(curr, 2))
        cadencia.append(round(duracion_total, 2))
        cortes = sorted(list(set(cadencia)))
    else:
        cortes = sorted(list(set(cortes + [round(duracion_total, 2)])))

    segmentos = []
    for i in range(len(cortes) - 1):
        t0, t1 = cortes[i], cortes[i + 1]
        rol = "hook" if i == 0 else ("cierre" if i == len(cortes) - 2 else ("social" if i % 2 == 1 else "dato"))
        segmentos.append({
            "indice": i + 1,
            "from": t0,
            "to": t1,
            "duracion": round(t1 - t0, 2),
            "rol": rol,
            "tipo_sugerido": FAMILIAS_ESCENAS[rol][0]
        })
    return segmentos


def cmd_analizar(origen, es_url, out_dir):
    """Fase 1: Ingesta, extracción y descomposición viral del video."""
    out_dir = out_dir or os.path.join(os.getcwd(), "clon_trabajo")
    os.makedirs(out_dir, exist_ok=True)

    print("=== PASO 1: Ingesta de video de referencia ===")
    ref_data = REF.procesar_referencia(origen, es_url=es_url, out_dir=out_dir)

    dur = ref_data["metadatos"]["duracion"]
    print(f"\n=== PASO 2: Detección de estructura viral y ritmo ({dur}s) ===")
    mid = _momentos_medidos(ref_data["video"])
    continua = False
    if mid:
        segmentos = _segmentos_medidos(mid)
        continua = bool(segmentos) and segmentos[0].get("rol") == "continuo"
        print(f"   {len(segmentos)} momentos MEDIDOS (scenes.py), con su valor al lado")
        if continua:
            print("   AVISO: sin cortes duros (animacion continua): la plantilla NO trae "
                  "roles hook/cierre; los beats salen de la transcripcion por palabra "
                  "y los mosaicos, no de los cortes (referencia-video.md §3)")
    else:
        segmentos = detectar_cortes(ref_data["video"], dur)
        print("   el medidor no respondió: cortes por silencio y cadencia estándar "
              "(menos preciso y SIN valor medido)")

    # Generar plantilla estructural
    plantilla = {
        "origen": origen,
        "duracion_referencia": dur,
        "aspecto": ref_data["metadatos"]["aspecto"],
        "fps": ref_data["metadatos"]["fps"],
        "segmentos": segmentos,
        "animacion_continua": continua,
        "medicion": {
            "fuente": ("scripts/ffmpeg_tools/scenes.py (scdet + envolvente RMS + picos)"
                       if mid else "silencio + cadencia estándar (sin valor medido)"),
            "orden": "audio" if mid else None,
        },
    }
    if mid and mid.get("highlights"):
        # la lista corta: donde esta el valor, para construir el corte AHI
        plantilla["destacados"] = mid["highlights"]

    plantilla_json = os.path.join(out_dir, "plantilla.json")
    with open(plantilla_json, "w", encoding="utf-8") as fh:
        json.dump(plantilla, fh, indent=2, ensure_ascii=False)

    # Generar reporte de análisis viral ANALYSIS.md
    analysis_md = os.path.join(out_dir, "ANALYSIS.md")
    with open(analysis_md, "w", encoding="utf-8") as fh:
        fh.write("# Análisis de Video Viral de Referencia\n\n")
        fh.write(f"- **Origen**: `{origen}`\n")
        fh.write(f"- **Duración**: {dur}s · **Aspecto**: {ref_data['metadatos']['aspecto']} · **FPS**: {ref_data['metadatos']['fps']}\n")
        fh.write("- **Pistas extraídas**: Audio 48kHz (`audio_48k.wav`), Audio 16kHz (`audio_16k.wav`)\n")
        fh.write("- **Storyboard**: Contact Sheet con frames clave (`contact_sheet.png`)\n")
        fh.write(f"- **Medición del valor**: {plantilla['medicion']['fuente']}\n\n")
        if continua:
            fh.write("> **Animación continua, sin cortes duros**: scdet solo ve "
                     f"{len(segmentos)} tramo(s), asi que no hay HOOK/CIERRE que "
                     "localizar por posición y `variar` no debe usarse sobre esta "
                     "plantilla tal cual. Los beats se sacan de la transcripción "
                     "por palabra (`alinear.py` sin guion) y de los mosaicos a "
                     "1 s/5 s: cada frase o cambio de sistema es un beat "
                     "(references/referencia-video.md §3).\n\n")
        fh.write("## Estructura Viral Descompuesta\n\n")
        if mid:
            fh.write("| # | Rol | Tiempos | Duración | Escena Sugerida | Valor medido |\n")
            fh.write("|---|---|---|---|---|---|\n")
            for s in segmentos:
                fh.write(f"| {s['indice']} | **{s['rol'].upper()}** | {s['from']}s - {s['to']}s "
                         f"| {s['duracion']}s | `{s['tipo_sugerido']}` | {s['nota']} |\n")
        else:
            fh.write("| # | Rol | Tiempos | Duración | Escena Sugerida |\n")
            fh.write("|---|---|---|---|---|\n")
            for s in segmentos:
                fh.write(f"| {s['indice']} | **{s['rol'].upper()}** | {s['from']}s - {s['to']}s "
                         f"| {s['duracion']}s | `{s['tipo_sugerido']}` |\n")
            fh.write("\n> Sin valor medido: los roles salen de la posición, no de la "
                     "medición. Míralo con la hoja de contactos antes de comprometerte.\n")
        if plantilla.get("destacados"):
            fh.write("\n## Dónde está el valor (medido)\n\n")
            fh.write("| # | De | A | Duración |\n|---|---|---|---|\n")
            for i, h in enumerate(plantilla["destacados"], 1):
                fh.write(f"| {i} | {h['start']}s | {h['end']}s | {h['duration']}s |\n")
        fh.write("\n## Recomendaciones de Clonación y Variación\n")
        fh.write(f"1. Ejecutar `python scripts/clonar_video.py variar --plantilla {plantilla_json} --variantes 3 --tema '<Nuevo Tema>'`\n")
        fh.write("2. El motor reemplazará los textos manteniendo las cuotas de duración auditadas por `speech_estimate.py`.\n")
        if mid:
            fh.write("3. El corte se construye alrededor de los momentos de valor: "
                     "el remate sale del pico medido, no del último plano por defecto.\n")

    print("\nOK Estructura analizada:")
    print(f"   Plantilla: {plantilla_json}")
    print(f"   Reporte: {analysis_md}")


def cmd_variar(plantilla_path, num_variantes, tema, out_dir, marca_path=None):
    """Fase 2: Generación de N variantes del video viral."""
    if not os.path.isfile(plantilla_path):
        sys.exit(f"ERROR: no existe la plantilla: {plantilla_path}")

    with open(plantilla_path, encoding="utf-8") as fh:
        plantilla = json.load(fh)

    out_dir = out_dir or os.path.join(os.path.dirname(plantilla_path), "variantes")
    os.makedirs(out_dir, exist_ok=True)

    # Cargar muestras para autocompletar esquemas válidos
    muestras_path = os.path.join(BASE, "scripts", "escenas_muestra.json")
    muestras = json.load(open(muestras_path, encoding="utf-8"))["escenas"] if os.path.isfile(muestras_path) else {}

    tema = tema or "Ciberseguridad y Productividad Digital"
    segmentos = plantilla.get("segmentos", [])

    if not segmentos:
        # Una plantilla sin segmentos no es una plantilla: no hay estructura que
        # variar. Lo mas probable es que se haya pasado un plan.json donde se
        # espera la plantilla (el motor acepta la abreviatura --plan por
        # --plantilla). Decir "OK Variante 1: 0 escenas" era honesto en los
        # numeros y mentiroso en la palabra: una variante sin escenas no es
        # una variante, y el plan que sale revienta al renderizarlo.
        sys.exit(
            "ERROR: la plantilla no trae 'segmentos' (la estructura de la referencia): "
            "no hay nada que variar.\n"
            "  Este comando espera la plantilla que produce 'analizar' (plantilla.json).\n"
            "  Si le has pasado un plan.json, el motor acepta la abreviatura --plan por "
            "--plantilla: renombralo o usa el plan con render_plan.py.")

    if plantilla.get("animacion_continua") or any(s.get("rol") == "continuo" for s in segmentos):
        sys.exit(
            "ERROR: esta plantilla es de una pieza de animacion continua (sin cortes "
            "duros): no trae roles hook/cierre que variar.\n"
            "  Trocea primero el tramo continuo en beats por frase con la transcripcion "
            "por palabra (scripts/alinear.py sin guion) y los mosaicos, escribe esos "
            "beats como segmentos con su rol en la plantilla, y vuelve a variar.\n"
            "  Ver references/referencia-video.md §3 (animacion continua).")

    print(f"Generando {num_variantes} variantes para el tema: '{tema}'...")

    needing = []            # variantes cuya voz todavia no cabe
    variantes_con_voz = []  # planes escritos
    for v_idx in range(1, num_variantes + 1):
        var_dir = os.path.join(out_dir, f"variante_{v_idx}")
        os.makedirs(var_dir, exist_ok=True)
        escenas_plan = []

        for k, seg in enumerate(segmentos):
            rol = seg["rol"]
            opciones = FAMILIAS_ESCENAS.get(rol, ["titular"])
            # Alternar tipo de escena según variante y normalizar a catálogo de 39 escenas
            raw_tipo = opciones[(v_idx - 1) % len(opciones)]
            tipo = MAPEO_ESCENAS_VALIDAS.get(raw_tipo, raw_tipo)

            raw_muestra = muestras.get(tipo, {"tipo": tipo})
            base_escena = copy.deepcopy(raw_muestra)
            orig_dur = max(0.1, float(base_escena.get("to", 5.0)) - float(base_escena.get("from", 0.0)))
            factor = min(1.0, seg["duracion"] / orig_dur)
            base_escena = rebase_at(base_escena, seg["from"], factor)
            base_escena["tipo"] = tipo
            base_escena["from"] = seg["from"]
            base_escena["to"] = seg["to"]

            # Adaptar copy básico al tema
            if "titulo" in base_escena:
                base_escena["titulo"] = f"*{tema}*: Clave {seg['indice']}" if seg['indice'] > 1 else f"El Secreto de *{tema}*"
            if "kicker" in base_escena:
                base_escena["kicker"] = f"Variante {v_idx}"

            # Inyectar voz para narración y ajustar que quepa en el HUECO:
            # el tiempo hasta donde empieza la voz siguiente (o hasta el
            # final del video), que es lo que mide la auditoría. La voz
            # entra en from+0.4 s (el aire), asi que el tiempo util es
            # hueco-AIRE_VOZ. Antes se comparaba contra la duración de la
            # PROPIA escena: un criterio mas estricto que el del resto de
            # la skill, que hacia perder palabras que si cabian.
            txt_voz = base_escena.get("titulo") or base_escena.get("rotulo") or f"{tema} punto clave {seg['indice']}"
            if k + 1 < len(segmentos):
                hueco = float(segmentos[k + 1]["from"]) - float(seg["from"])
            else:
                # la ultima voz: el borde del video
                hueco = float(plantilla.get("duracion_referencia", 30.0)) - float(seg["from"])
            base_escena["voz"] = _ajustar_voz(txt_voz.replace("*", ""), hueco)

            escenas_plan.append(base_escena)

        plan = {
            "duracion": plantilla.get("duracion_referencia", 30.0),
            "tema": tema,
            "variante": v_idx,
            "escenas": escenas_plan
        }
        if marca_path:
            plan["brand"] = marca_path

        plan_path = os.path.join(var_dir, "plan.json")
        with open(plan_path, "w", encoding="utf-8") as fh:
            json.dump(plan, fh, indent=2, ensure_ascii=False)

        # Auditar con speech_estimate
        audi = SE.auditar_plan_voces(plan)
        if audi["valido"]:
            print(f"OK Variante {v_idx}: {len(escenas_plan)} escenas -> {plan_path} (voz OK)")
        else:
            # el plan NO pasa la puerta: decirlo, no venderlo como "OK"
            print(f"AVISO Variante {v_idx}: {len(escenas_plan)} escenas -> {plan_path} "
                  f"({len(audi['alertas'])} escenas con la voz desbordada)")
            for a in audi["alertas"][:3]:
                print(f"        escena {a['escena_index']}: la voz se sale en "
                      f"{a['exceso_segundos']}s -> alarga la escena o recorta el texto")
            needing.append(v_idx)
        # el texto de voz es un placeholder de la referencia: hay que reescribirlo
        variantes_con_voz.append(plan_path)

    print(f"\n{num_variantes} variantes en: {out_dir}")
    if needing:
        print(f"ATENCION: {len(needing)} variante(s) con la voz desbordada (arriba). "
              "El texto de voz es un PLACEHOLDER de la referencia: reescribilo y "
              "re-audita antes de renderizar.")
    else:
        print("La voz cabe en todas las escenas. El texto sigue siendo un PLACEHOLDER "
              "de la referencia: reescribilo con el copy real antes de renderizar.")
    print(f"Renderizar con: python3 scripts/render_plan.py {os.path.join(out_dir, 'variante_1', 'plan.json')} -o out_v1.mp4")


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = ap.add_subparsers(dest="subcmd", required=True)

    # Subcomando analizar
    p_ana = sub.add_parser("analizar", help="Analizar video viral e inferir plantilla")
    src = p_ana.add_mutually_exclusive_group(required=True)
    src.add_argument("--video", help="Ruta al video local de referencia")
    src.add_argument("--url", help="URL de video (YouTube, TikTok, etc.)")
    p_ana.add_argument("-o", "--out", help="Directorio de salida (default: ./clon_trabajo)")

    # Subcomando variar
    p_var = sub.add_parser("variar", help="Generar variantes a partir de una plantilla")
    p_var.add_argument("--plantilla", required=True, help="Ruta a plantilla.json")
    p_var.add_argument("-n", "--variantes", type=int, default=3, help="Número de variantes a generar (default: 3)")
    p_var.add_argument("--tema", default="Inteligencia Artificial", help="Tema para las variantes")
    p_var.add_argument("--marca", help="Ruta opcional al brand pack (ej: brand/mi_marca.json)")
    p_var.add_argument("-o", "--out", help="Directorio de salida de las variantes")

    args = ap.parse_args()
    if args.subcmd == "analizar":
        es_url = bool(args.url)
        origen = args.url if es_url else args.video
        cmd_analizar(origen, es_url, args.out)
    elif args.subcmd == "variar":
        cmd_variar(args.plantilla, args.variantes, args.tema, args.out, marca_path=args.marca)


if __name__ == "__main__":
    main()
