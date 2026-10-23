#!/usr/bin/env python3
"""Voz en off con la VOZ DEL SISTEMA: la maqueta local, sin API y sin costo.

Camino hermano de `voz_off.py` (ElevenLabs) con el MISMO contrato:
    python scripts/voz_local.py plan.json -o voz.wav --guion guion.txt
Del plan salen las escenas con campo 'voz'; cada frase se sintetiza, se
coloca en su instante (inicio de escena + el aire de voz) y se arma una pista
continua. Del resto del camino no hay que cambiar nada: `alinear.py`,
`mezclar_audio.py --voz` y `medir_mezcla.py` reciben el mismo archivo que
reciben de voz_off.py. Lo que cambia es la CALIDAD de la voz, no el proceso.

Por que existe: sin `$ELEVENLABS_API_KEY` la skill dice "trabajar sin voz o
reprogramar" y la pieza se queda sin locucion. Este script es la TERCERA via
—una MAQUETA, no una entrega final— y hay que decirlo al usuario.

Backends: macOS `say`, Linux `espeak-ng`, Windows PowerShell. En macOS y
Linux el script esta probado con audio real; el backend de Windows esta
escrito pero NO se ha podido probar aqui (no hay maquina Windows en este
repo): se documenta como no probado en references/sonido.md.

Lo que NO hace (y hay que decir en voz alta):
  · No hay direccion emocional: los tags [slowly]/[calm] son de ElevenLabs y
    la voz del sistema no los entiende. Se quitan del texto hablado (misma
    regla que `voz_off.py`: `texto_hablado`).
  · No hay red de seguridad: si no hay voz del idioma pedido, el script FALLA
    en voz alta y lista las que hay. Nunca degrada en silencio.

El reloj lo manda la narracion: antes de mezclar se mide cada segmento real
y se falla si una voz pisa a la siguiente (misma comprobacion que
`voz_off.py`, importada de alli: una sola regla para los dos caminos).
"""
import argparse
import hashlib
import os
import platform
import re
import shutil
import subprocess
import sys

_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_AQUI, "ffmpeg_tools"))
from _comun import audio_codec_for, ayudar, die, ffmpeg_base, leer_json  # noqa: E402
from _plataforma import dir_temp  # noqa: E402
from speech_estimate import AIRE_VOZ  # noqa: E402  el aire de voz (la misma
from speech_estimate import RITMOS as RITMOS_ESTIMADOR  # noqa: E402
from speech_estimate import detectar_idioma, silabas  # noqa: E402
from voz_off import texto_hablado, verificar_reloj  # noqa: E402

# Velocidad por defecto en palabras por minuto. La de `say` es 175; 178 es lo
# que usan las piezas de la demo y suena menos apurada.
VELOCIDAD = 178

# Nombres preferidos por idioma y backend. Si no esta ninguno, se toma la
# primera voz del idioma: la maqueta es mejor que no tener maqueta.
PREFERIDAS = {
    "say": {"es": ["Mónica", "Paulina"], "en": ["Samantha", "Alex", "Daniel"]},
    "espeak-ng": {"es": ["es"], "en": ["en-us", "en"]},
    "espeak": {"es": ["es"], "en": ["en-us", "en"]},
    "powershell": {"es": [], "en": []},
}

IDIOMA_NOMBRES = {"es": "español", "en": "inglés"}


# ───────────────────────────── backend ─────────────────────────────
def detectar_backend():
    """El motor de TTS disponible en esta maquina, o None."""
    if platform.system() == "Darwin" and shutil.which("say"):
        return "say"
    for b in ("espeak-ng", "espeak"):
        if shutil.which(b):
            return b
    if platform.system() == "Windows" and (shutil.which("powershell")
                                           or shutil.which("pwsh")):
        return "powershell"
    return None


def sin_backend():
    die("no hay ningun motor de voz del sistema en esta maquina.\n"
        "  macOS:  `say` viene con el sistema.\n"
        "  Linux:  sudo apt install espeak-ng\n"
        "  Windows: PowerShell con System.Speech (viene con el sistema).\n"
        "Sin TTS local, el camino es ElevenLabs (voz_off.py) o trabajar sin voz: "
        "se avisa al usuario y se sigue sin locucion.")


# ───────────────────────────── voces ─────────────────────────────
def parse_voces_say(texto):
    """Voces de macOS a partir de la salida de `say -v ?`.

    Formato: NOMBRE  locale  # muestra. El nombre puede llevar espacios y
    parentesis ("Eddy (Español (España))"), asi que el locale se localiza
    por su forma (xx_XX) y no por posicion. Funcion pura: se puede probar
    sin tener `say` en la maquina.
    """
    voces = []
    for linea in texto.splitlines():
        m = re.match(r"^(?P<nombre>.+?)\s+(?P<locale>[a-z]{2}_[A-Z]{2})\s+#\s*(?P<muestra>.*)$",
                     linea.strip())
        if m:
            voces.append({"nombre": m.group("nombre").strip(),
                          "locale": m.group("locale"),
                          "idioma": m.group("locale").split("_")[0]})
    return voces


def _voces_say():
    """Voces de macOS instaladas."""
    try:
        out = subprocess.run(["say", "-v", "?"], capture_output=True,
                             text=True, timeout=30).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    return parse_voces_say(out)


def _voces_espeak(binario):
    """Voces de espeak: su codigo de dos letras es el idioma."""
    try:
        out = subprocess.run([binario, "--voices"], capture_output=True,
                             text=True, timeout=30).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    voces = []
    for linea in out.splitlines():
        m = re.search(r"Voice:\s*(?P<code>[a-z]{2})", linea)
        if m:
            voces.append({"nombre": m.group("code"), "locale": m.group("code"),
                          "idioma": m.group("code")})
    return voces


def _voces_powershell():
    """Voces instaladas de Windows (System.Speech)."""
    ps = shutil.which("powershell") or shutil.which("pwsh")
    if not ps:
        return []
    cmd = ("Add-Type -AssemblyName System.Speech; "
           "(New-Object System.Speech.Synthesis.SpeechSynthesizer).GetInstalledVoices()"
           " | ForEach-Object { $_.VoiceInfo.Name + '|' + $_.VoiceInfo.Culture.Name }")
    try:
        out = subprocess.run([ps, "-NoProfile", "-Command", cmd], capture_output=True,
                             text=True, timeout=60).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    voces = []
    for linea in out.splitlines():
        if "|" not in linea:
            continue
        nombre, locale = linea.split("|", 1)
        locale = locale.strip()
        m = re.match(r"^([a-z]{2})", locale)
        voces.append({"nombre": nombre.strip(), "locale": locale,
                      "idioma": m.group(1) if m else ""})
    return voces


def listar_voces(backend):
    if backend == "say":
        return _voces_say()
    if backend in ("espeak-ng", "espeak"):
        return _voces_espeak(backend)
    return _voces_powershell()


def elegir_voz(voces, backend, idioma, pedida):
    """La voz que se va a usar, o None si no hay ninguna del idioma pedido.

    `pedida` puede ser el nombre exacto de una voz o un locale (es_MX).
    """
    if pedida:
        for v in voces:
            if v["nombre"].lower() == pedida.lower():
                return v
        for v in voces:
            if v["locale"].lower() == pedida.lower():
                return v
        return None
    preferidas = PREFERIDAS.get(backend, {}).get(idioma, [])
    for nombre in preferidas:
        for v in voces:
            if v["nombre"].lower() == nombre.lower():
                return v
    for v in voces:
        if v["idioma"] == idioma:
            return v
    return None


def voz_por_idioma(voces, backend, idioma):
    """Voces del idioma pedido (para el mensaje de error)."""
    return [v for v in voces if v["idioma"] == idioma]


# ────────────────────────── sintesis ──────────────────────────
def cache_dir():
    d = os.path.expanduser("~/.cache/editoria/voz_local")
    os.makedirs(d, exist_ok=True)
    return d


def _duracion(path):
    """Duracion real de un archivo de audio (ffprobe)."""
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", path], capture_output=True, text=True)
    try:
        return float(r.stdout.strip() or 0)
    except ValueError:
        return 0.0


def cache_path(texto, voz, velocidad, backend):
    """Clave de caché por contenido: el mismo texto+voz+velocidad reusa el wav.

    No es seguridad (usedforsecurity=False lo declara y no falla en FIPS):
    es content-addressing, como el de voz_off.py.
    """
    h = hashlib.md5(f"{backend}|{voz}|{velocidad}|{texto}".encode(),
                    usedforsecurity=False).hexdigest()[:12]
    return os.path.join(cache_dir(), f"voz_{h}.wav")


def _sintetizar_say(texto, voz, velocidad, destino):
    """macOS: `say` escribe un wav REAL con --file-format=WAVE.

    Sin ese flag, `say` escribe AIFF-C con nombre .wav: un archivo que ni
    `wave` ni ffmpeg reconocen (el nombre miente sobre el contenido). Con
    el flag, RIFF/WAVE de verdad, 16 bits mono.
    """
    cmd = ["say", "--data-format=LEI16@22050", "--file-format=WAVE",
           "-v", voz, "-r", str(velocidad), "-o", destino, texto]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        # Some voices fail with the explicit format flags: retry with the
        # default (AIFF-C) and convert with ffmpeg.
        aiff = os.path.join(dir_temp(), "frase.aiff")
        subprocess.run(["say", "-v", voz, "-r", str(velocidad), "-o", aiff, texto],
                       check=True, capture_output=True, timeout=180)
        subprocess.run(ffmpeg_base() + ["-i", aiff, "-ar", "22050", "-ac", "1", destino],
                       check=True, capture_output=True, timeout=180)
        return
    if not os.path.exists(destino) or os.path.getsize(destino) < 128:
        die(f"la voz del sistema no produjo audio: {proc.stderr.strip()[:200]}")


def _sintetizar_espeak(binario, texto, voz, velocidad, destino):
    """Linux: espeak escribe el wav directamente (-w)."""
    subprocess.run([binario, "-v", voz, "-s", str(velocidad), "-w", destino, texto],
                   check=True, capture_output=True, timeout=180)


def _sintetizar_powershell(texto, voz, velocidad, destino):
    """Windows: System.Speech escribe el wav; la velocidad es un factor 0..10."""
    ps = shutil.which("powershell") or shutil.which("pwsh")
    factor = max(0, min(10, round(velocidad / 30)))
    esc = texto.replace("'", "''")
    cmd = (f"Add-Type -AssemblyName System.Speech; "
           f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
           f"$s.Rate = {factor}; ")
    if voz:
        cmd += f"$s.SelectVoice('{voz.replace(chr(39), chr(39) + chr(39))}'); "
    cmd += (f"$s.SetOutputToWaveFile('{destino}'); $s.Speak('{esc}'); "
            f"$s.Dispose()")
    proc = subprocess.run([ps, "-NoProfile", "-Command", cmd],
                          capture_output=True, text=True, timeout=300)
    if proc.returncode != 0:
        die(f"PowerShell no pudo sintetizar: {proc.stderr.strip()[:300]}")


def sintetizar(backend, texto, voz, velocidad, destino):
    if backend == "say":
        _sintetizar_say(texto, voz, velocidad, destino)
    elif backend in ("espeak-ng", "espeak"):
        _sintetizar_espeak(backend, texto, voz, velocidad, destino)
    else:
        _sintetizar_powershell(texto, voz, velocidad, destino)


# ───────────────────────────── main ─────────────────────────────
def main():
    ap = argparse.ArgumentParser(
        description="Voz en off con la voz del sistema (maqueta local, sin API).")
    ap.add_argument("plan", nargs="?",
                    help="plan.json (references/plan-video.md); no hace falta con --listar")
    ap.add_argument("-o", "--out")
    ap.add_argument("--voz", default=None,
                    help="nombre de la voz instalada (Mónica, Paulina, Samantha...) "
                         "o su locale (es_ES). Default: la primera del idioma")
    ap.add_argument("--idioma", default="es", choices=["es", "en"],
                    help="idioma de la voz: el que le hable al usuario")
    ap.add_argument("--velocidad", type=int, default=VELOCIDAD,
                    help=f"palabras por minuto (default {VELOCIDAD})")
    ap.add_argument("--guion", default=None,
                    help="escribe aqui el guion hablado (los campos 'voz' del plan, "
                         "en orden de escena, sin los tags de direccion)")
    ap.add_argument("--permitir-otro-idioma", action="store_true",
                    help="permite una voz de otro idioma (suena mal: se usa solo "
                         "a proposito)")
    ap.add_argument("--listar", action="store_true",
                    help="lista las voces instaladas y sale")
    ayudar(ap, {"--velocidad": "palabras por minuto de la voz",
                "--permitir-otro-idioma": "permite una voz de otro idioma"})
    a = ap.parse_args()

    backend = detectar_backend()
    if not backend:
        sin_backend()
    voces = listar_voces(backend)

    if a.listar:
        if not voces:
            print(f"no se pudo leer la lista de voces de {backend}")
            return 1
        for v in voces:
            print(f"{v['nombre']}  [{v['locale']}]")
        return 0

    if not a.plan:
        die("falta el plan.json (o usa --listar para ver las voces)")
    if not a.out:
        die("falta el archivo de salida (-o)")

    voz = elegir_voz(voces, backend, a.idioma, a.voz)
    if voz is None:
        if a.voz:
            die(f"la voz {a.voz!r} no esta instalada en esta maquina.\n"
                f"Las que hay: {', '.join(v['nombre'] for v in voces) or '(ninguna)'}\n"
                "Se listan con: python scripts/voz_local.py plan.json -o voz.wav --listar")
        idioma = a.idioma
        hay = voz_por_idioma(voces, backend, idioma)
        if not hay:
            die(f"no hay ninguna voz de {IDIOMA_NOMBRES.get(idioma, idioma)} "
                f"instalada en esta maquina, y el TTS local no degrada en silencio: "
                f"una voz de otro idioma leyendo el guion no es una voz en off.\n"
                f"Las voces que hay: {', '.join(v['nombre'] for v in voces) or '(ninguna)'}\n"
                "macOS: Ajustes -> Accesibilidad -> Contenido hablado -> Voces del sistema "
                "(descarga las de español).\n"
                "Opciones: se avisa al usuario y se sigue con ElevenLabs, o se trabaja "
                "sin voz.")
        die(f"no se pudo elegir voz de {IDIOMA_NOMBRES.get(idioma, idioma)}.")

    if voz["idioma"] != a.idioma and not a.permitir_otro_idioma:
        die(f"la voz {voz['nombre']!r} es de {voz['locale']} y el plan pide "
            f"{IDIOMA_NOMBRES.get(a.idioma, a.idioma)}.\n"
            "Suena mal: una voz de otro idioma leyendo el guion no es una voz en off.\n"
            "O se elige una voz del idioma (--listar), o se pasa "
            "--permitir-otro-idioma a proposito.")

    plan = leer_json(a.plan, "el plan")
    if "escenas" not in plan:
        die("el plan no tiene 'escenas'")
    escenas = sorted(plan["escenas"], key=lambda s: s["from"])
    segs = []
    guion = []
    for e in escenas:
        vox = e.get("voz")
        if not vox:
            continue
        segs.append((vox, int((e["from"] + AIRE_VOZ) * 1000), e))
        guion.append(texto_hablado(vox))
    if not segs:
        die("el plan no tiene campos 'voz'")
    if a.guion:
        with open(a.guion, "w", encoding="utf-8") as fh:
            fh.write("\n".join(guion) + "\n")
        print(f"guion: {a.guion}", flush=True)

    print(f"AVISO: voz del sistema ({backend}, voz {voz['nombre']}, "
          f"{voz['locale']}): entrega de MAQUETA, no final. Sin direccion "
          f"emocional: los tags [slowly]/[calm] no los entiende. Se le dice "
          f"al usuario.", flush=True)

    archivos = []
    for i, (vox, delay_ms, e) in enumerate(segs):
        texto = texto_hablado(vox)
        destino = cache_path(texto, voz["nombre"], a.velocidad, backend)
        if os.path.exists(destino) and os.path.getsize(destino) > 128:
            print(f"cache escena {i} ({e['tipo']})", flush=True)
        else:
            print(f"TTS escena {i} ({e['tipo']}): {texto[:50]}", flush=True)
            tmp = os.path.join(dir_temp(), f"seg{i}.wav")
            sintetizar(backend, texto, voz["nombre"], a.velocidad, tmp)
            if not os.path.exists(tmp) or os.path.getsize(tmp) < 128:
                die(f"la voz del sistema no produjo audio en la escena {i}")
            shutil.move(tmp, destino)
        archivos.append((destino, delay_ms, e))

    # La narracion manda el reloj: la MISMA comprobacion que voz_off.py.
    # Con la duracion del plan: si la voz de la ultima escena se pasa del
    # final del video, la narracion se corta contra el borde (no hay otra
    # imagen que la tape) y eso es un ERROR, no un aviso.
    verificar_reloj(archivos, duracion_video=plan.get("duracion"))

    # Ritmo REAL de esta voz: el estimador silabico es una aproximacion
    # (mide su error contra esta cifra) y el agente necesita saber cuanto
    # se equivoca con la voz que esta usando.
    total_sil = sum(silabas(texto_hablado(vox), detectar_idioma(texto_hablado(vox)))
                    for vox, _dl, _e in segs)
    total_real = sum(_duracion(f) for f, _dl, _e in archivos)
    if total_real > 0.5 and total_sil:
        tasa_est = RITMOS_ESTIMADOR.get(a.idioma, {}).get("normal", 5.90)
        print(f"ritmo real de {voz['nombre']}: {total_sil / total_real:.2f} silabas/s "
              f"(el estimador de speech_estimate.py usa "
              f"{tasa_est:.2f} para 'normal')", flush=True)

    fc = []
    amix = []
    for i, (f, dl, _) in enumerate(archivos):
        fc += ["-i", f]
        amix.append(f"[{i}:a]adelay={dl}|{dl}[a{i}]")
    amix.append("".join(f"[a{i}]" for i in range(len(archivos))) +
                f"amix=inputs={len(archivos)}:normalize=0[aout]")
    cmd = ffmpeg_base() + [*fc, "-filter_complex", ";".join(amix),
                           "-map", "[aout]", *audio_codec_for(a.out), a.out]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        die("no se pudo ensamblar la pista de voz:\n" +
            "\n".join(proc.stderr.strip().splitlines()[-10:]))
    print("OK", a.out)


if __name__ == "__main__":
    main()
