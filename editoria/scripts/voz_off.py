#!/usr/bin/env python3
"""Voz en off con ElevenLabs para un plan.json.
Uso: source ~/.secrets.env && python voz_off.py plan.json -o voz.mp3 [--voz ID] [--model ID]
El plan debe tener "voz" en cada escena. Genera un segmento por escena y los
mezcla en sus tiempos (inicio de escena + 0.4s).
Cache por hash del contenido (texto+voz+modelo) en ~/.cache/editoria/voz:
no re-sintetiza (ni re-paga) segmentos idénticos entre proyectos.
Dirección: el texto admite audio tags de eleven_v3 ([excited], [whisper],
[slowly], [dramatic tone], [long pause]...) y puntuación como ingeniería
(ver references/sonido.md).
Voces por defecto: español -> Fernanda Sanmiguel; inglés -> Brian.
La narración manda el reloj: mide cada segmento y falla si una voz pisa a la
siguiente (antes de mezclar). Pre-TTS, auditar_plan.py estima lo mismo.
La API key sale de $ELEVENLABS_API_KEY (nunca en el skill ni en archivos).
"""
import os, sys, argparse, subprocess, hashlib, re
try:
    import requests
except ImportError:
    requests = None

VOCES = {  # roster probado con audio real (ver references/sonido.md)
    "fernanda": "1aJyZpkt0vxhGPBnPyrs",  # ES fem, latam neutra (default ES)
    "gabriela": "hHjbwzYZW17oh0p05AKv",  # ES fem, cálida (mexicana)
    "camila":    "e84cwhnrHVYn1KRUiXMG",  # ES fem, neutra
    "johan":     "4uvQjLPvqApx1dVzpNfM",  # ES masc, colombiana
    "fran":      "NZ2TecpKTOZyf4AUxLxx",  # ES masc, latam
    "velez":     "ytEyaKD9tSq2dWAVjRQr",  # ES masc, neutra
    "brian":     "nPczCjzI2devNBz1zQrb",  # EN masc, profunda (default EN)
    "sarah":     "EXAVITQu4vr4xnSDxMaL",  # EN fem, madura
    "alice":     "Xb7hH8MSUJpSbSDYk0k2",  # EN fem, educadora (UK)
    "bella":     "hpp4J3VqNfWAUOO0d1Us",  # EN fem, profesional
    "george":    "JBFqnCBsd6RMkjVDRZzb",  # EN masc, narrador (UK)
    "daniel":    "onwK4e9ZLuTAKqWW03F9",  # EN masc, locutor (UK)
}
DEFAULT_POR_IDIOMA = {"es": "fernanda", "en": "brian"}
MODEL = "eleven_v3"  # soporta audio tags de dirección; fallback: eleven_multilingual_v2

def texto_hablado(texto):
    """El texto tal como se ESCUCHA (para el guion y la alineacion).

    Los tags de direccion ([slowly], [calm]...) no se dicen: se leen como
    instruccion para el modelo. Si quedaran en el guion, `alinear.py` los
    contaria como palabras y cada ancla de palabra caeria una posicion
    mas tarde. Los asteriscos de enfasis (*antes*) tampoco son palabras.
    Mismo criterio que `speech_estimate.py`.
    """
    t = re.sub(r"\[[^\]]*\]", " ", texto)
    return re.sub(r"\s+", " ", t.replace("*", " ")).strip()


def cache_path(texto, voz_id, model):
    """Path content-addressed: el mismo texto+voz+modelo reusa el MP3."""
    # clave de caché, no seguridad: usedforsecurity=False lo declara (y no falla en FIPS)
    h = hashlib.md5(f"{model}|{voz_id}|{texto}".encode(), usedforsecurity=False).hexdigest()[:12]
    d = os.path.expanduser("~/.cache/editoria/voz")
    os.makedirs(d, exist_ok=True)
    return f"{d}/vo_{h}.mp3"

def tts(texto, out, voz_id, model):
    if requests is None:
        sys.exit("Falta instalar requests (pip install requests) para sintetizar voz con ElevenLabs")
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key: sys.exit("Falta ELEVENLABS_API_KEY en el entorno")
    settings = {} if model == "eleven_v3" else \
        {"voice_settings": {"stability": 0.55, "similarity_boost": 0.75}}
    r = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{voz_id}",
        headers={"xi-api-key": key, "Content-Type": "application/json"},
        json={"text": texto, "model_id": model, **settings},
        timeout=120)
    r.raise_for_status()
    open(out, "wb").write(r.content)

def duracion(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", path], capture_output=True, text=True)
    return float(r.stdout.strip() or 0)

def verificar_reloj(segs):
    """La narración manda el reloj: mide cada segmento real. Si una voz pisa
    a la siguiente, amix las sumaría (dos voces a la vez): se falla ANTES de
    mezclar, diciendo cuánto alargar. Los segmentos quedan en caché (no se
    re-pagan al re-ejecutar tras corregir el plan)."""
    errores = []
    for k, (f, dl, e) in enumerate(segs):
        fin = dl / 1000 + duracion(f)
        if k + 1 < len(segs) and fin > segs[k + 1][1] / 1000:
            errores.append(f"escena {e['tipo']}@{e['from']}s: la voz dura hasta {fin:.2f}s y "
                           f"pisa la siguiente ({segs[k+1][1]/1000:.2f}s) — alargar la escena "
                           f"{fin - segs[k+1][1]/1000 + 0.2:.2f}s o recortar el texto")
        elif fin > e.get("to", fin):
            print(f"AVISO escena {e['tipo']}@{e['from']}s: la voz termina {fin - e['to']:.2f}s "
                  f"después de la escena (cae sobre la siguiente imagen)", flush=True)
    if errores:
        sys.exit("ERROR voces solapadas:\n  " + "\n  ".join(errores))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan"); ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--voz", default=None,
                    help="nombre de voz del roster (fernanda, gabriela, camila, "
                         "johan, fran, velez, brian, sarah, alice, bella, george, "
                         "daniel) o voice_id directo (default según --idioma)")
    ap.add_argument("--idioma", default="es", choices=["es", "en"],
                    help="idioma de la voz por defecto: la que hable el usuario")
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--guion", default=None,
                    help="escribe aqui el guion hablado (los campos 'voz' del plan, en "
                         "orden de escena, sin los tags de direccion): es lo que se "
                         "alinea con alinear.py para anclar animaciones a la palabra")
    import os as _os, sys as _sys
    _sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "ffmpeg_tools"))
    from _comun import ayudar
    ayudar(ap, {'-o': 'audio de salida con la voz de todas las escenas (mp3)', '--model': 'modelo de voz de ElevenLabs'})
    a = ap.parse_args()
    voz_id = VOCES.get(a.voz, a.voz) if a.voz else VOCES[DEFAULT_POR_IDIOMA[a.idioma]]
    from _comun import leer_json
    plan=leer_json(a.plan,"el plan")
    segs=[]
    guion=[]
    pending=[]
    for i,e in enumerate(sorted(plan["escenas"],key=lambda s:s["from"])):
        vox=e.get("voz")
        if not vox: continue
        f=cache_path(vox, voz_id, a.model)
        pending.append((i,e,vox,f))
        delay_ms=int((e["from"]+0.4)*1000)
        segs.append((f,delay_ms,e))
        guion.append(texto_hablado(vox))
    if not segs: sys.exit("El plan no tiene campos 'voz'")
    if a.guion:
        # el guion sale del MISMO plan que genera la voz: si se escribiera a
        # mano, una palabra de mas desplaza TODAS las anclas de palabra en
        # silencio y las animaciones caen sobre la palabra equivocada.
        # Se escribe ANTES del TTS: el guion no depende de la API.
        with open(a.guion,"w",encoding="utf-8") as fh:
            fh.write("\n".join(guion)+"\n")
        print(f"guion: {a.guion}",flush=True)
    for i,e,vox,f in pending:
        if os.path.exists(f) and os.path.getsize(f) > 1500:
            print(f"cache escena {i} ({e['tipo']})",flush=True)
        else:
            print(f"TTS escena {i} ({e['tipo']}): {vox[:50]}…",flush=True)
            tts(vox, f, voz_id, a.model)
    verificar_reloj(segs)
    # mezcla con delays
    fc=[]; amix=[]
    for i,(f,dl,_) in enumerate(segs):
        fc+=["-i",f]; amix.append(f"[{i}:a]adelay={dl}|{dl}[a{i}]")
    amix.append("".join(f"[a{i}]" for i in range(len(segs)))+
                f"amix=inputs={len(segs)}:normalize=0[aout]")
    subprocess.run(["ffmpeg","-y","-v","error",*fc,
                    "-filter_complex",";".join(amix),
                    "-map","[aout]","-c:a","libmp3lame","-b:a","160k",a.out],
                   check=True)
    print("OK",a.out)

if __name__=="__main__": main()
