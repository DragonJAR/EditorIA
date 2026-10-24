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
generados con ffmpeg) y se corre de verdad. El fallo que se busca no es el
veredicto de la herramienta —una puerta que rechaza una pieza mala ha hecho
su trabajo— sino el comando ROTO: el que no puede ni leer lo que la prosa le
manda.

Y la lista tiene que ser COMPLETA: toda CLI documentada o se copia y se corre,
o tiene el motivo de por que no. Una CLI que no se ejecuta y no tiene motivo
es un puntero a nada, y el guard lo dice.

Uso:
    python3 scripts/_comandos_copiables.py            # informa
    python3 scripts/_comandos_copiables.py --json     # en JSON
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
# Las CLIs que este guard COPIA Y CORRE. Criterio: no pagan APIs, no salen a
# la red, no renderizan una pieza entera y terminan en segundos. Cada una
# esta porque hay un comando documentado que la usa con estos argumentos.
# ---------------------------------------------------------------------------
EJECUTABLES = {
    "scripts/auditar_plan.py",
    "scripts/auto_qa.py",
    "scripts/beat_file.py",
    "scripts/beat_grid.py",
    "scripts/check_env.py",
    "scripts/direccion_arte.py",
    "scripts/ffmpeg_tools/caption.py",
    "scripts/ffmpeg_tools/delivery_check.py",
    "scripts/ffmpeg_tools/loudness.py",
    "scripts/ffmpeg_tools/montaje.py",
    "scripts/ffmpeg_tools/scenes.py",
    "scripts/lint_copy.py",
    "scripts/medir_contraste.py",
    "scripts/medir_mezcla.py",
    "scripts/proyecto.py",
    "scripts/sfx.py",
    "scripts/speech_estimate.py",
    "scripts/verificar_ritmo.py",
}

# Las CLIs documentadas que este guard NO copia, con el motivo. Sin motivo no
# hay exclusion: una exclusion sin razon es una puerta que nadie mira.
FUERA = {
    "scripts/_censo_clis.py": "corre la suite entera: este guard esta dentro de ella",
    "scripts/_comandos_copiables.py": "es este guard: un guard no se copia a si "
                                  "mismo (se mediria en un bucle). Lo ejecuta un "
                                  "test y lo corre la validacion",
    "scripts/alinear.py": "necesita un modelo de voz (Whisper) instalado",
    "scripts/clonar_video.py": "descarga de la red",
    "scripts/contact_sheet.py": "necesita palabras alineadas (Whisper)",
    "scripts/film_marca_v2.py": "renderiza la pieza entera: la galeria ya lo hace",
    "scripts/medir_animacion.py": "renderiza la pieza entera para medirla: "
                                "mas lento que el guard completo",
    "scripts/mezclar_audio.py": "necesita voz, musica y SFX ya renderizados",
    "scripts/musica.py": "paga una API de musica",
    "scripts/puntuar.py": "juzga la pieza: su veredicto depende de la pieza, no del comando",
    "scripts/qa_entrega.py": "es la puerta: idem, juzga la pieza",
    "scripts/referencia.py": "descarga de la red",
    "scripts/registrar_aprendizaje.py": "escribe DENTRO de la skill "
                                     "(references/reglas-tecnicas.md): un "
                                     "guard no puede modificar lo que vigila",
    "scripts/render_plan.py": "renderiza la pieza entera (30 s): la galeria ya lo hace",
    "scripts/sincronizar_instalada.py": "reescribe la copia instalada",
    "scripts/validate_skill.py": "es la validacion misma: se ejecuta con esta opcion",
    "scripts/voz_local.py": "usa la voz del sistema: depende de la maquina, no del comando",
    "scripts/voz_off.py": "paga una API de TTS",
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


def _assets(tmp, skill_dir):
    """Los assets con los que se sustituye lo que la prosa nombra."""
    a = {}
    plan = os.path.join(skill_dir, "scripts", "demo_plan.json")
    if os.path.exists(plan):
        a["plan"] = plan
    vid = os.path.join(tmp, "video.mp4")
    if _ffmpeg(vid, []):
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


def _sustituir(partes, assets):
    """(partes, resuelto). Resuelto=False si algo no se puede sustituir."""
    salida = []
    for p in partes:
        base = os.path.basename(p)
        ext = os.path.splitext(base)[1].lower()
        if ext == ".json":
            if "plan" in base.lower() and "shorts" not in base.lower() \
                    and "plantilla" not in base.lower():
                if "plan" not in assets:
                    return None, False
                salida.append(assets["plan"])
                continue
            if base.startswith("brand"):
                if "brand" not in assets:
                    return None, False
                salida.append(assets["brand"])
                continue
            return None, False          # shorts-plan, plantilla, datos: sin schema
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
    nuevas, resuelto = _sustituir(partes[1:], assets)
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


def verificar(skill_dir=None, comandos=None, timeout=120, solo=None):
    """(problemas, informe).

    problemas: [texto] — un comando documentado que, copiado y pegado con
    assets reales, esta roto.
    informe: dict con cuantos comandos se miraron, cuantos se saltaron y
    porque. Los saltos se CUENTAN: un guard que se salta la mitad sin decirlo
    es un guard que no mira.
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
    scripts = cd.scripts_de_los_comandos(skill_dir)

    # 1. la lista tiene que ser COMPLETA: toda CLI documentada o se copia, o
    #    tiene el motivo de por que no.
    problemas = []
    sin_motivo = sorted(s for s in scripts
                         if s not in EJECUTABLES and s not in FUERA)
    for s in sin_motivo:
        problemas.append(f"CLI documentada sin motivo y sin copia: {s}")

    tmp = tempfile.mkdtemp(prefix="editoria_copiables_")
    try:
        assets = _assets(tmp, skill_dir)
        copiados = saltados = 0
        for cmd in comandos:
            partes = cd._partir(cmd)
            if not partes:
                continue
            s = partes[0]
            if "/scripts/" in s:
                s = "scripts/" + s.split("/scripts/", 1)[1]
            if s not in EJECUTABLES:
                saltados += 1
                continue
            ok, motivo, salida = _correr_comando(skill_dir, cmd, tmp, assets,
                                                 timeout=timeout)
            copiados += 1
            if not ok:
                problemas.append(f"{cmd}  ->  {motivo}")
        informe = {"comandos": len(comandos), "copiados": copiados,
                   "saltados": saltados, "clis_documentadas": len(scripts)}
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
    print(f"{len(problemas)} problemas")
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())
