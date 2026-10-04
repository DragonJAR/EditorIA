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
La API key sale de $ELEVENLABS_API_KEY (nunca en el skill ni en archivos).
"""
import os, sys, json, argparse, subprocess, hashlib, requests

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

def cache_path(texto, voz_id, model):
    """Path content-addressed: el mismo texto+voz+modelo reusa el MP3."""
    h = hashlib.md5(f"{model}|{voz_id}|{texto}".encode()).hexdigest()[:12]
    d = os.path.expanduser("~/.cache/editoria/voz")
    os.makedirs(d, exist_ok=True)
    return f"{d}/vo_{h}.mp3"

def tts(texto, out, voz_id, model):
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
    a = ap.parse_args()
    voz_id = VOCES.get(a.voz, a.voz) if a.voz else VOCES[DEFAULT_POR_IDIOMA[a.idioma]]
    plan=json.load(open(a.plan, encoding="utf-8"))
    segs=[]
    for i,e in enumerate(sorted(plan["escenas"],key=lambda s:s["from"])):
        vox=e.get("voz")
        if not vox: continue
        f=cache_path(vox, voz_id, a.model)
        if os.path.exists(f) and os.path.getsize(f) > 1500:
            print(f"cache escena {i} ({e['tipo']})",flush=True)
        else:
            print(f"TTS escena {i} ({e['tipo']}): {vox[:50]}…",flush=True)
            tts(vox, f, voz_id, a.model)
        delay_ms=int((e["from"]+0.4)*1000)
        segs.append((f,delay_ms))
    if not segs: sys.exit("El plan no tiene campos 'voz'")
    # mezcla con delays
    fc=[]; amix=[]
    for i,(f,dl) in enumerate(segs):
        fc+=["-i",f]; amix.append(f"[{i}:a]adelay={dl}|{dl}[a{i}]")
    amix.append("".join(f"[a{i}]" for i in range(len(segs)))+
                f"amix=inputs={len(segs)}:normalize=0[aout]")
    subprocess.run(["ffmpeg","-y","-v","error",*fc,
                    "-filter_complex",";".join(amix),
                    "-map","[aout]","-c:a","libmp3lame","-b:a","160k",a.out],
                   check=True)
    print("OK",a.out)

if __name__=="__main__": main()
