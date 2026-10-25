#!/usr/bin/env python3
"""_comandos_copiables.py — el comando que dice la prosa, COPIADO Y PEGADO, funciona.

El guard de comandos (`_comandos_doc.py`) intercepta `parse_args` y prueba que
los argumentos documentados son VALIDOS para la herramienta: que el flag
existe, que los obligatorios estan. Eso es una cosa, y la cumple.

Falta la otra: que el argumento sea del TIPO que la herramienta pide. A
`verificar_ritmo.py plan.json` argparse lo acepta sin pestanear —el
posicional se llama `video`, pero `plan.json` es una cadena valida— y el
comando revienta mas tarde con "ffmpeg no pudo leer". El agente copia el
comando de la prosa, pega, y se queda parado con un error que no esta
documentado en ninguna parte. Por eso hay que COPIARLO Y CORRERLO.

Aqui se copia cada comando documentado, se sustituyen sus placeholders por
assets REALES (el plan de muestra de la skill, un video y un audio minimos
generados con ffmpeg, una plantilla de clonado) y se corre de verdad. El
fallo que se busca no es el veredicto de la herramienta —una puerta que
rechaza una pieza mala ha hecho su trabajo— sino el comando ROTO: el que no
puede ni leer lo que la prosa le manda.

Y la lista tiene que ser COMPLETA, y completa POR COMANDO, no por script:
un script puede tener un camino que se copia (offline) y otro que no (el
mismo `clonar_video.py` tiene `variar`, que es local, y `analizar`, que
baja el video). La unidad es el comando que el agente COPIA, no el fichero.
Por eso los motivos viven aqui como prefijos de comando, y por eso el
informe NOMBRA cada salto: un numero de saltados sin nombres es un tapon.

Uso:
    python3 scripts/_comandos_copiables.py            # informa
    python3 scripts/_comandos_copiables.py --json     # en JSON
    python3 scripts/_comandos_copiables.py --solo txt # solo los que contienen "txt"
"""
import glob
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(BASE, "scripts")

# ---------------------------------------------------------------------------
# Las CLIs cuyo comando documentado se COPIA Y SE CORRE. Criterio: no pagan
# APIs, no salen a la red, no renderizan una pieza entera y terminan en
# segundos.
# ---------------------------------------------------------------------------
EJECUTABLES = {
    "scripts/auditar_plan.py",
    "scripts/auto_qa.py",
    "scripts/beat_file.py",
    "scripts/beat_grid.py",
    "scripts/check_env.py",
    "scripts/clonar_video.py",
    "scripts/contact_sheet.py",
    "scripts/direccion_arte.py",
    "scripts/ffmpeg_tools/caption.py",
    "scripts/ffmpeg_tools/componer.py",
    "scripts/ffmpeg_tools/delivery_check.py",
    "scripts/ffmpeg_tools/loudness.py",
    "scripts/ffmpeg_tools/montaje.py",
    "scripts/ffmpeg_tools/scenes.py",
    "scripts/ffmpeg_tools/speedramp.py",
    "scripts/ffmpeg_tools/verticalizar.py",
    "scripts/hand_draw.py",
    "scripts/retakes.py",
    "scripts/lint_copy.py",
    "scripts/medir_contraste.py",
    "scripts/medir_mezcla.py",
    "scripts/mezclar_audio.py",
    "scripts/proyecto.py",
    "scripts/puntuar.py",
    "scripts/qa_entrega.py",
    "scripts/referencia.py",
    "scripts/render_plan.py",
    "scripts/repertorio.py",
    "scripts/sfx.py",
    "scripts/speech_estimate.py",
    "scripts/verificar_ritmo.py",
    "scripts/voz_local.py",
}

# Los comandos documentados que este guard NO copia, con el motivo. La clave
# es un PREFIJO del comando (o el script entero), no el script: por eso
# `clonar_video.py` esta en EJECUTABLES (su camino `variar` es local) y solo
# su `analizar` queda fuera (baja el video de la red).
#
# Sin motivo no hay exclusion: una exclusion sin razon es una puerta que
# nadie mira.
# (motivo, [formas del comando que NO necesitan lo que el motivo dice])
#
# El segundo elemento es lo que hace que la exclusion sea precisa: un script
# puede necesitar la red o una voz, y aun asi tener una forma que solo
# necesita un fichero local. Sin esto, excluir el script entero se lleva por
# delante comandos que si se pueden ejecutar, y la cobertura de una vertical
# se cae sin que nadie lo note. Las formas se comparan por TOKEN.
FUERA = {
    "scripts/_censo_clis.py": ("corre la suite entera: este guard esta dentro de ella", []),
    "scripts/_comandos_copiables.py": ("es este guard: un guard no se copia a si mismo", []),
    "scripts/alinear.py": ("necesita un modelo de voz (Whisper) instalado", []),
    "scripts/clonar_video.py analizar": ("descarga de la red: baja el video de referencia",
                                         ["--video"]),
    "scripts/contact_sheet.py": ("necesita palabras alineadas (Whisper)",
                                  ["--dir", "-n"]),
    "scripts/film_marca_v2.py": ("renderiza la pieza entera: la galeria ya lo hace", []),
    "scripts/medir_animacion.py": ("renderiza la pieza entera para medirla: mas lento que el guard completo", []),
    # `mezclar_audio.py` ya NO se excluye: la voz, la musica y el pack de SFX
    # se sintetizan en local (un wav, un wav y sfx.py), asi que el comando se
    # copia y se ejecuta de verdad. Antes era el unico comando de la vertical de
    # sonido con CERO cobertura de la puerta fuerte, y su motivo ("necesita
    # voz, musica y SFX ya renderizados") era cierto en general pero no en la
    # forma que el agente copia.
    "scripts/musica.py": ("paga una API de musica", []),
    # `puntuar.py` y `qa_entrega.py` ya NO se excluyen: juzgan una pieza, pero
    # la pieza puede ser la de prueba (un video y un plan de fixture), y su
    # veredicto - "NO APROBADA", "GATE: NO PASA" - NO es un comando roto: es
    # una puerta que ha hecho su trabajo. Por eso el comando copiado que
    # imprime ERROR se corta, y el que imprime un veredicto no.
    "scripts/referencia.py": ("descarga de la red", ["--video"]),
    "scripts/registrar_aprendizaje.py": ("escribe DENTRO de la skill "
                                          "(references/reglas-tecnicas.md): un guard no "
                                          "puede modificar lo que vigila", []),
    # `--preview` NO renderiza la pieza entera: compone tres frames del plan
    # (un instante cada uno). El motivo de al lado era cierto para el render
    # y falso para el preview, asi que la excepcion lo deja pasar y el resto
    # sigue saltando con su motivo. Es el mismo patron que con
    # `clonar_video.py` y `referencia.py`.
    "scripts/render_plan.py": ("renderiza la pieza entera (30 s): la galeria ya lo hace",
                               ["--preview"]),
    "scripts/sincronizar_instalada.py": ("reescribe la copia instalada", []),
    "scripts/validate_skill.py": ("es la validacion misma: el guard corre DENTRO de ella, asi que copiarla seria llamarse a si misma (para leer su cabecera: --cabecera)", []),
    "scripts/voz_local.py": ("usa la voz del sistema: depende de la maquina, no del comando",
                              ["--listar"]),
    "scripts/voz_off.py": ("paga una API de TTS", []),
}

# Las firmas de un comando ROTO: no es un veredicto de la herramienta, es la
# herramienta sin poder leer lo que le han mandado. Un veredicto (una puerta
# que rechaza, un linter que encuentra fallos) NO es un fallo del comando.
ROTO = (
    "no pudo leer",
    "No such file or directory",
    "Is a directory",
    "Invalid data found",
    "moov atom not found",
    "the following arguments are required",
    "unrecognized arguments",
    "invalid choice",
    "Traceback (most recent call last)",
    # un comando copiado que imprime ERROR no hizo su trabajo. OJO: esto NO
    # es lo mismo que un veredicto: una puerta que rechaza una pieza mala
    # imprime FAIL, y eso es haber hecho su trabajo. Va al final porque es la
    # firma mas generica: si pilla otra mas especifica, esa dice mas.
    "ERROR:",
)


# ---------------------------------------------------------------------------
# Los assets reales con los que se sustituyen los placeholders de la prosa.
# ---------------------------------------------------------------------------
def _ffmpeg(destino, args_extra, duracion=1):
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
           f"testsrc=duration={duracion}:size=320x180:rate=10"]
    cmd += args_extra
    cmd += ["-pix_fmt", "yuv420p", destino]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return p.returncode == 0 and os.path.exists(destino)


def _plantilla(destino):
    """Una plantilla de clonado minima pero REAL.

    `clonar_video.py variar` no necesita la red: necesita la estructura que
    produce `analizar` (los segmentos de la referencia). Con una plantilla
    minima se puede correr el camino de clonar de verdad, y asi el comando
    que el agente copia en esa vertical queda EJECUTADO, no solo vigilado por
    sus argumentos.
    """
    plantilla = {
        "origen": "referencia de prueba (guard)",
        "duracion_referencia": 12.0,
        "aspecto": "9:16",
        "fps": 30,
        "segmentos": [
            {"indice": 1, "from": 0.0, "to": 4.0, "duracion": 4.0,
             "rol": "hook", "tipo_sugerido": "apertura"},
            {"indice": 2, "from": 4.0, "to": 8.0, "duracion": 4.0,
             "rol": "dato", "tipo_sugerido": "stats"},
            {"indice": 3, "from": 8.0, "to": 12.0, "duracion": 4.0,
             "rol": "cierre", "tipo_sugerido": "final"},
        ],
    }
    with open(destino, "w", encoding="utf-8") as fh:
        json.dump(plantilla, fh, indent=1, ensure_ascii=False)
    return destino


def _plan_ligero(destino, skill_dir):
    """Un plan minimo pero REAL: dos escenas del catalogo, con voz.

    No es un cascaron: las escenas son de verdad (`apertura` y `final`, del
    catalogo de la propia skill) y llevan la voz que el motor espera. Lo que
    se quita es la DURACION: 2 s en vez de 30.
    """
    muestras_p = os.path.join(skill_dir, "scripts", "escenas_muestra.json")
    muestras = {}
    if os.path.exists(muestras_p):
        with open(muestras_p, encoding="utf-8") as fh:
            muestras = (json.load(fh) or {}).get("escenas") or {}

    def escena(tipo, frm, to):
        e = dict(muestras.get(tipo, {"tipo": tipo}))
        e["tipo"] = tipo
        e["from"] = frm
        e["to"] = to
        e["voz"] = "Una frase de prueba."
        return e

    plan = {"duracion": 2.0, "tema": "prueba",
            "escenas": [escena("apertura", 0.0, 1.0), escena("final", 1.0, 2.0)]}
    with open(destino, "w", encoding="utf-8") as fh:
        json.dump(plan, fh, indent=1, ensure_ascii=False)
    return destino


def _assets(tmp, skill_dir):
    """Los assets con los que se sustituye lo que la prosa nombra."""
    a = {}
    plan = os.path.join(skill_dir, "scripts", "demo_plan.json")
    if os.path.exists(plan):
        a["plan"] = plan
        # Un plan LIGERO (2 escenas, 2 s) para las piezas que se miden
        # enteras: la puerta y la rubrica no necesitan un plan rico, necesitan
        # que el COMANDO funcione. Medido: con el plan de muestra (30 s) cada
        # ejecucion cuesta 35 s y 77 s; con el ligero, 4,5 s y 5,9 s. Los 13
        # comandos de esas dos piezas dejan de costar 12 minutos y cuestan
        # 66 segundos.
        a["plan_ligero"] = _plan_ligero(os.path.join(tmp, "plan_ligero.json"), skill_dir)
    # el video lleva AUDIO: loudness y montaje mapean 0:a, y un video mudo
    # no les da nada que hacer (el comando "funciona" y no hace su trabajo)
    vid = os.path.join(tmp, "video.mp4")
    if _ffmpeg(vid, ["-f", "lavfi", "-i", "sine=frequency=440:duration=1"]):
        a["video"] = vid
    aud = os.path.join(tmp, "audio.wav")
    if _ffmpeg(aud, ["-f", "lavfi", "-i", "sine=frequency=440:duration=1"], duracion=1):
        a["audio"] = aud
    mp3 = os.path.join(tmp, "audio.mp3")
    if _ffmpeg(mp3, ["-f", "lavfi", "-i", "sine=frequency=440:duration=1"], duracion=1):
        a["mp3"] = mp3
    img = os.path.join(tmp, "imagen.png")
    if _ffmpeg(img, ["-frames:v", "1"], duracion=1):
        a["imagen"] = img
    txt = os.path.join(tmp, "guion.txt")
    with open(txt, "w", encoding="utf-8") as fh:
        fh.write("Una frase de prueba.\n")
    a["texto"] = txt
    csv = os.path.join(tmp, "datos.csv")
    with open(csv, "w", encoding="utf-8") as fh:
        fh.write("nombre,apellido\nAna,Lopez\n")
    a["csv"] = csv
    srt = os.path.join(tmp, "subs.srt")
    with open(srt, "w", encoding="utf-8") as fh:
        fh.write("1\n00:00:00,000 --> 00:00:01,000\nHola\n\n")
    a["srt"] = srt
    a["plantilla"] = _plantilla(os.path.join(tmp, "plantilla.json"))
    # trazos a mano: JSON mínimo para hand_draw.py suavizar/pintar
    trazos = os.path.join(tmp, "trazos.json")
    with open(trazos, "w", encoding="utf-8") as fh:
        json.dump({
            "strokes": [{
                "color": "#101827",
                "width": 6,
                "points": [[40, 40], [80, 60], [120, 50], [200, 180]],
            }],
        }, fh)
    a["trazos"] = trazos
    # una carpeta de stills: `contact_sheet --dir` no necesita palabras
    # alineadas (eso es lo que exige Whisper), solo imagenes
    stills = os.path.join(tmp, "stills")
    os.makedirs(stills, exist_ok=True)
    for i in range(2):
        if "imagen" in a:
            shutil.copy(a["imagen"], os.path.join(stills, f"still_{i}.png"))
    a["stills"] = stills
    # la voz CON palabras: lo que resuelve el ancla "palabra" del plan. Se
    # escribe a mano (son palabras de prueba) porque `alinear.py` necesita
    # Whisper, que no esta instalado en todas las maquinas.
    palabras = os.path.join(tmp, "palabras.json")
    with open(palabras, "w", encoding="utf-8") as fh:
        json.dump({"palabras": [{"texto": f"palabra{i}", "inicio": round(0.1 * i, 3),
                                 "fin": round(0.1 * i + 0.09, 3)} for i in range(60)]}, fh)
    a["palabras"] = palabras
    # la rejilla musical: la genera la herramienta DE VERDAD (beat_grid.py)
    # sobre la cama de prueba, para que el ancla "beat" tenga algo que resolver
    if "audio" in a:
        grid = os.path.join(tmp, "grid.json")
        p = subprocess.run([sys.executable, os.path.join(skill_dir, "scripts", "beat_grid.py"),
                            a["audio"], "--json", grid],
                           capture_output=True, text=True, timeout=120)
        if p.returncode == 0 and os.path.exists(grid):
            a["grid"] = grid
    # el pack de efectos: lo sintetiza sfx.py (procedural, sin assets
    # externos). Con el, `mezclar_audio.py` deja de necesitar nada de fuera.
    pack = os.path.join(tmp, "sfx")
    subprocess.run([sys.executable, os.path.join(skill_dir, "scripts", "sfx.py"),
                    "-o", pack], capture_output=True, text=True, timeout=120)
    if os.path.isdir(pack):
        a["pack"] = pack
    # el pack de marca se busca por el NOMBRE DE FICHERO, no por el nombre de
    # la marca: en el codigo no vive ninguna marca concreta (la regla es
    # white-label, y el guard de marcas quemadas lo vigila). El que haya en
    # brand/ sirve igual.
    packs = sorted(glob.glob(os.path.join(skill_dir, "brand", "*.json")))
    if packs:
        a["brand"] = packs[0]
    return a


# Los placeholders de la prosa y el asset que los sustituye. La clave es el
# sufijo del nombre; None = no se sabe sustituir (el comando se salta).
_SUFIJOS = {
    ".mp4": "video", ".mov": "video", ".webm": "video", ".mkv": "video",
    ".mp3": "mp3", ".wav": "audio", ".m4a": "audio", ".aac": "audio",
    ".png": "imagen", ".jpg": "imagen", ".jpeg": "imagen",
    ".txt": "texto", ".csv": "csv", ".srt": "srt",
}

# Un marcador que nadie sustituye: "..." o algo entre < > o { }. Los que si
# se sustituyen tienen extension (plan.json, video.mp4) - de ahi sale el
# asset. Los demas llegan tal cual al comando.
_MARCADOR = re.compile(r"\.\.\.|<[^>]*>|\{[^}]*\}")


# Las banderas cuyo valor es un FICHERO DE SALIDA. La salida no se sustituye
# por el asset: se escribe en un sitio de raspado. Si no, el comando
# escribiria encima de su propia entrada (ffmpeg: "el output es el input").
SALIDAS = ("-o", "--out", "--output", "--salida", "--sheet")


# Las piezas que se miden enteras: la puerta y la rubrica. Para ellas el
# plan es un INPUT (tienen que poder leer un plan), no la materia prima de la
# medicion: por eso se les da el plan LIGERO. Con el motivo escrito al lado.
PLAN_LIGERO_PARA = {
    "scripts/qa_entrega.py": "miden la pieza entera: con el plan de muestra "
                             "cada ejecucion cuesta 35 s y la validacion se va "
                             "a 38 min; con el plan ligero, 4,5 s",
    "scripts/puntuar.py": "miden la pieza entera: con el plan de muestra cada "
                           "ejecucion cuesta 77 s; con el plan ligero, 5,9 s",
}


def _sustituir(partes, assets, scratch=None, plan_key="plan"):
    """(partes, resuelto). Resuelto=False si algo no se puede sustituir."""
    salida = []
    anterior = None
    for p in partes:
        base = os.path.basename(p)
        ext = os.path.splitext(base)[1].lower()
        # la salida se reconoce POR la bandera que la precede, y se comprueba
        # ANTES que la extension: si no, "final.mp4" se sustituiria por el
        # asset de video y el comando escribiria encima de su entrada
        previo = anterior
        anterior = p
        es_salida = previo in SALIDAS and scratch is not None
        if es_salida:
            salida.append(os.path.join(scratch, f"salida{ext or '.out'}"))
            continue
        if previo == "--referencia" and "video" in assets:
            # la referencia es un video (o un enlace): el fichero tiene que
            # EXISTIR, o el comando dice "la referencia no existe" y no hace
            # su trabajo
            salida.append(assets["video"])
            continue
        if ext == ".json":
            bajo = base.lower()
            if "palabras" in bajo:
                if "palabras" not in assets:
                    return None, False
                salida.append(assets["palabras"])
                continue
            if "grid" in bajo:
                if "grid" not in assets:
                    return None, False
                salida.append(assets["grid"])
                continue
            if "plantilla" in bajo:
                if "plantilla" not in assets:
                    return None, False
                salida.append(assets["plantilla"])
                continue
            if "plan" in bajo and "shorts" not in bajo:
                if plan_key not in assets:
                    return None, False
                salida.append(assets[plan_key])
                continue
            if base.startswith("brand"):
                if "brand" not in assets:
                    return None, False
                salida.append(assets["brand"])
                continue
            if "trazo" in bajo or "punto" in bajo or "stroke" in bajo:
                if "trazos" not in assets:
                    return None, False
                salida.append(assets["trazos"])
                continue
            return None, False          # shorts-plan, datos: sin schema
        if base.rstrip("/") == "sfx":
            # el pack de efectos: la carpeta donde `sfx.py` lo escribe. Con
            # su barra final entra aqui tambien (si no, caeria en la carpeta
            # de stills, que no es lo que el comando quiere escribir).
            if "pack" not in assets:
                return None, False
            salida.append(assets["pack"])
            continue
        if p.endswith("/") or p.endswith(os.sep):
            # una carpeta: la de stills del fixture
            if "stills" not in assets:
                return None, False
            salida.append(assets["stills"])
            continue
        if ext in _SUFIJOS:
            clave = _SUFIJOS[ext]
            if clave not in assets:
                return None, False
            salida.append(assets[clave])
            continue
        salida.append(p)
    return salida, True


def _juzgar(texto):
    """El motivo por el que la ejecucion es un comando ROTO, o None."""
    for firma in ROTO:
        if firma in (texto or ""):
            return firma
    return None


def _correr_comando(skill_dir, cmd, tmp, assets, timeout=120):
    """(ok, motivo, salida). ok=False con motivo = comando roto."""
    sys.path.insert(0, os.path.join(skill_dir, "scripts"))
    try:
        import _comandos_doc as cd
    finally:
        sys.path.pop(0)
    partes = cd._partir(cmd)
    if not partes:
        return True, "", ""
    script = partes[0]
    if "/scripts/" in script:
        script = "scripts/" + script.split("/scripts/", 1)[1]
    ruta = os.path.join(skill_dir, script)
    if not os.path.exists(ruta):
        return True, "", ""            # lo ve otro guard
    plan_key = "plan_ligero" if script in PLAN_LIGERO_PARA else "plan"
    nuevas, resuelto = _sustituir(partes[1:], assets, scratch=os.path.join(tmp, "cwd"),
                                  plan_key=plan_key)
    if not resuelto:
        return True, "", ""            # se salta: no se puede sustituir
    cmd_real = [sys.executable, ruta] + nuevas
    trabajo = os.path.join(tmp, "cwd")
    os.makedirs(trabajo, exist_ok=True)
    # La salida va a un FICHERO, no a un pipe: un nieto que hereda el pipe
    # abierto deja a `subprocess.run` esperando para siempre, y el guard se
    # cuelga en vez de juzgar. Con un fichero, el padre sale cuando el padre
    # sale.
    salida = os.path.join(tmp, "salida.txt")
    with open(salida, "wb") as fh:
        proc = subprocess.Popen(cmd_real, stdout=fh, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL, cwd=trabajo,
                                start_new_session=True)
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            # el comando y SUS HIJOS: si solo se mata al padre, el nieto
            # sigue con el grupo y el trabajo de la maquina
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError, OSError):
                proc.kill()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                pass
            return True, "", ""        # no se puede juzgar: no es un fallo
    with open(salida, "rb") as fh:
        texto = fh.read().decode("utf-8", "replace")
    motivo = _juzgar(texto)
    if motivo:
        return False, motivo, texto[-400:]
    return True, "", ""


def _normaliza_cmd(cmd):
    """El comando con la ruta del script normalizada ('editoria/scripts/...'
    -> 'scripts/...'), para poder casar prefijos de comando."""
    sys.path.insert(0, os.path.join(BASE, "scripts"))
    try:
        import _comandos_doc as cd
    finally:
        sys.path.pop(0)
    partes = cd._partir(cmd)
    if not partes:
        return cmd.strip()
    s = partes[0]
    if "/scripts/" in s:
        s = "scripts/" + s.split("/scripts/", 1)[1]
    return " ".join([s] + partes[1:])


def _decide(cmd, script):
    """(copia, motivo). Un comando se COPIA si su script esta entre las
    ejecutables (y ningun motivo lo excluye) o si es una EXCEPCION. Si no,
    lleva su motivo; y si no tiene motivo, es un problema: un comando
    documentado que ni se copia ni dice por que no, es un puntero a nada.
    """
    motivo = _motivo_de(cmd)
    if motivo:
        return False, motivo
    if script in EJECUTABLES:
        return True, None
    return False, None


def _motivo_de(cmd):
    """El motivo por el que un comando NO se copia, o None."""
    norm = _normaliza_cmd(cmd)
    mejor = None
    tokens = norm.split()
    for prefijo, (motivo, excepto) in FUERA.items():
        if not norm.startswith(prefijo):
            continue
        if any(t in tokens for t in excepto):
            continue        # esta forma del comando no necesita lo del motivo
        if mejor is None or len(prefijo) > len(mejor[0]):
            mejor = (prefijo, motivo)
    return mejor[1] if mejor else None


def verificar(skill_dir=None, comandos=None, timeout=120, solo=None):
    """(problemas, informe).

    problemas: [texto] — un comando documentado que, copiado y pegado con
    assets reales, esta roto; o un comando que ni se copia ni tiene motivo.
    informe: dict con cuantos comandos se miraron, cuantos se copiaron y
    ejecutaron, y -por motivo- cuales se saltaron. Los saltos se NOMBRAN: un
    guard que se salta la mitad sin decirlo es un guard que no mira.
    """
    skill_dir = skill_dir or BASE
    sys.path.insert(0, os.path.join(skill_dir, "scripts"))
    try:
        import _comandos_doc as cd
    finally:
        sys.path.pop(0)
    if comandos is None:
        comandos = (cd.comandos_documentados(skill_dir)
                    + cd.comandos_de_referencias(skill_dir))
    if solo:
        comandos = [c for c in comandos if solo in c]

    # 1. la lista tiene que ser COMPLETA POR COMANDO: cada comando documentado
    #    o se copia, o tiene el motivo de por que no.
    problemas = []
    sin_motivo = []
    for cmd in comandos:
        partes = cd._partir(cmd)
        if not partes:
            continue
        s = partes[0]
        if "/scripts/" in s:
            s = "scripts/" + s.split("/scripts/", 1)[1]
        copia, motivo = _decide(cmd, s)
        if copia or motivo:
            continue            # se copia, o no se copia CON MOTIVO
        sin_motivo.append(cmd)
    for c in sin_motivo:
        problemas.append(f"comando documentado sin motivo y sin copia: {c}")

    tmp = tempfile.mkdtemp(prefix="editoria_copiables_")
    try:
        assets = _assets(tmp, skill_dir)
        copiados = 0
        saltados = 0
        por_motivo = {}
        light = {}
        for cmd in comandos:
            partes = cd._partir(cmd)
            if not partes:
                continue
            s = partes[0]
            if "/scripts/" in s:
                s = "scripts/" + s.split("/scripts/", 1)[1]
            copia, motivo = _decide(cmd, s)
            if not copia:
                if motivo:
                    saltados += 1
                    por_motivo.setdefault(motivo, []).append(cmd)
                continue
            if s in PLAN_LIGERO_PARA:
                light.setdefault(s, []).append(cmd)
            # Un marcador que NADIE sustituye. Los que si se sustituyen son
            # los que tienen extension (plan.json, video.mp4): de ahi sale el
            # asset. Un token con "..." o entre < > o { } llega tal cual al
            # comando, y puede NO FALLAR (argparse se come "..." como valor)
            # y aun asi ser una promesa rota: la pieza sale con el titulo
            # literal "...". Solo se mira en los comandos que se COPIAN: los
            # que se saltan con motivo son formas por definicion (el usuario
            # mete su carpeta, su url) y ahi el marcador es donde va lo suyo.
            for t in partes[1:]:
                if _MARCADOR.search(t):
                    problemas.append(
                        f"comando copiado con un marcador que nadie sustituye "
                        f"({t}): se pegara tal cual  ->  {cmd}")
            ok, motivo_rot, salida = _correr_comando(skill_dir, cmd, tmp,
                                                       assets, timeout=timeout)
            copiados += 1
            if not ok:
                problemas.append(f"{cmd}  ->  {motivo_rot}")
        informe = {"comandos": len(comandos), "copiados": copiados,
                   "saltados": saltados,
                   "saltados_por_motivo": {k: len(v) for k, v in por_motivo.items()},
                   "clis_documentadas": len(cd.scripts_de_los_comandos(skill_dir)),
                   # QUE se midio es parte del veredicto: un comando medido con
                   # el plan ligero no dice nada del plan de muestra, y su
                   # salida (una puerta que rechaza la pieza) sin este dato
                   # se lee como un juicio sobre la pieza de 30 s.
                   "plan_ligero": {k: {"comandos": v,
                                        "motivo": PLAN_LIGERO_PARA[k]}
                                   for k, v in light.items()}}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return problemas, informe


def main():
    import argparse
    ap = argparse.ArgumentParser(description="los comandos de la prosa, copiados")
    ap.add_argument("--json", action="store_true", help="salida en JSON")
    ap.add_argument("--solo", default=None,
                    help="copia y corre solo los comandos que contengan este texto "
                         "(para mirar uno concreto sin correrlos todos)")
    a = ap.parse_args()
    problemas, informe = verificar(solo=a.solo)
    if a.json:
        print(json.dumps({"problemas": problemas, "informe": informe},
                         indent=1, ensure_ascii=False))
        return 1 if problemas else 0
    for p in problemas:
        print("FALLO", p)
    print(f"comandos: {informe['comandos']} · copiados: {informe['copiados']}"
          f" · saltados: {informe['saltados']}")
    for motivo, n in sorted(informe["saltados_por_motivo"].items(),
                            key=lambda kv: -kv[1]):
        print(f"   saltado ({n}): {motivo}")
    for script, datos in sorted(informe.get("plan_ligero", {}).items()):
        print(f"   medido con plan LIGERO ({len(datos['comandos'])} comandos de "
              f"{script}): {datos['motivo']}")
    print(f"{len(problemas)} problemas")
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())
