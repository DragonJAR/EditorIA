#!/usr/bin/env python3
"""Música de fondo para EditorIA (ElevenLabs Music).
Uso:
  source ~/.secrets.env
  python3 musica.py gen -o musica.mp3 --prompt "..." --dur 30
  python3 musica.py mix -v video.mp4 -a voz.mp3 -m musica.mp3 -o final.mp4
El mix aplica ducking (sidechain): la música baja cuando hay voz en off,
para que la cadencia respire con la narración. La key sale de
$ELEVENLABS_API_KEY (nunca en el skill ni en archivos).
"""
import os, sys, argparse, subprocess

def gen(prompt,dur,out):
    key=os.environ.get("ELEVENLABS_API_KEY")
    if not key: sys.exit("Falta ELEVENLABS_API_KEY en el entorno. Sin clave (o sin acuerdo de pago) "
                         "no entregues la pieza sin musica: genera la cama procedural con "
                         "'musica.py cama -o cama.wav --dur <segundos>' y mezclala con mix/musiconly, "
                         "declarandola como respaldo (references/sonido.md)")
    try:
        import requests   # solo gen usa la red: mezclar no depende de requests
    except ImportError:
        sys.exit("Falta el paquete requests para la API de ElevenLabs: pip install requests "
                 "(la cama procedural 'musica.py cama' no lo necesita)")
    r=requests.post("https://api.elevenlabs.io/v1/music",
        headers={"xi-api-key":key,"Content-Type":"application/json"},
        json={"prompt":prompt,"music_length_ms":int(dur*1000),
              "model_id":"music_v1"},timeout=180)
    r.raise_for_status()
    with open(out,"wb") as fh:
        fh.write(r.content)
    print("OK",out)

def cama(dur,out,bpm=92,raiz=110.0,menor=True,vol=0.5):
    """Cama musical procedural, sin API y sin derechos: osciladores de ffmpeg.

    El respaldo cuando no hay ELEVENLABS_API_KEY ni acuerdo de pago: un pad
    de acorde (fundamental, quinta, octava y tercera) con un pulso grave al
    tempo, filtrado suave y fundidos de entrada/salida. No es una
    composicion: es la cama declarada como tal, para mezclarla con `mix`
    (ducking bajo la voz) en vez de entregar la pieza sin musica.
    Determinista: los mismos parametros dan el mismo wav.
    """
    tercera=1.1892 if menor else 1.2599  # tercera menor / mayor
    freqs=[raiz, raiz*1.5, raiz*2, raiz*tercera]
    partes=[]; entradas=[]
    for i,f in enumerate(freqs):
        entradas+=["-f","lavfi","-i",f"sine=frequency={f:.2f}:duration={dur}"]
        partes.append(f"[{i}:a]volume={vol/(i+1.6):.3f}[s{i}]")
    entradas+=["-f","lavfi","-i",f"sine=frequency={raiz/2:.2f}:duration={dur}"]
    pulso=60.0/max(30.0,float(bpm))
    partes.append(f"[{len(freqs)}:a]volume={vol*0.7:.3f},tremolo=f={1/pulso:.3f}:d=0.9[pul]")
    mezcla="".join(f"[s{i}]" for i in range(len(freqs)))+"[pul]"
    fade_out=max(0.0,dur-2.0)
    fc=(";".join(partes)+f";{mezcla}amix=inputs={len(freqs)+1}:normalize=0,"
        f"lowpass=f=1400,afade=t=in:st=0:d=1.2,afade=t=out:st={fade_out}:d=2.0,"
        f"atrim=0:{dur}[aout]")
    r=subprocess.run(["ffmpeg","-y","-v","error",*entradas,"-filter_complex",fc,
                      "-map","[aout]","-ar","48000","-ac","2",out],
                     capture_output=True,text=True)
    if r.returncode!=0:
        sys.exit(f"ERROR: ffmpeg fallo al generar la cama procedural: {(r.stderr or '').strip()[:300]}")
    print("OK",out,"(cama procedural sin API: pad", "menor" if menor else "mayor",
          f"a {bpm} BPM sobre {raiz:.0f} Hz; declararla como respaldo, no como composicion)")

def vdur(video):
    if not os.path.isfile(video):
        sys.exit(f"ERROR: no existe el video: {video}")
    r=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
                      "-of","csv=p=0",video],capture_output=True,text=True)
    s=(r.stdout or "").strip()
    if r.returncode != 0 or not s:
        sys.exit(f"ERROR: ffprobe no pudo leer la duración de {video}")
    try:
        return float(s)
    except ValueError:
        sys.exit(f"ERROR: duración inválida en {video}: {s!r}")

def mix(video,voz,musica,out,mus_vol=0.12):
    # música a volumen base + ducking por la voz; voz siempre al frente.
    # Defaults verificados (v4 AI Tinkerers): música ~15 dB bajo la voz
    # (medido con scripts/medir_mezcla.py). Ver reglas-tecnicas.md.
    # duración explícita del video (nada de -shortest: recorta si la voz es más corta)
    for etq, ruta in (("video", video), ("voz", voz), ("música", musica)):
        if not os.path.isfile(ruta):
            sys.exit(f"ERROR: no existe el archivo de {etq}: {ruta}")
    dur=vdur(video)
    fc=(f"[2:a]volume={mus_vol},apad=whole_dur={dur}[mx];"
        f"[1:a]apad=whole_dur={dur},asplit=2[vox1][vox2];"
        f"[mx][vox1]sidechaincompress=threshold=0.015:ratio=12:attack=15:"
        f"release=600:makeup=1[duck];"
        f"[duck][vox2]amix=inputs=2:normalize=0:duration=longest,"
        f"atrim=0:{dur}[aout]")
    r=subprocess.run(["ffmpeg","-y","-v","error","-i",video,"-i",voz,"-i",musica,
                      "-filter_complex",fc,"-map","0:v","-map","[aout]",
                      "-c:v","copy","-c:a","aac","-b:a","160k",
                      "-movflags","+faststart",out],capture_output=True,text=True)
    if r.returncode != 0:
        sys.exit(f"ERROR: ffmpeg falló al mezclar audio: {(r.stderr or '').strip()[:200]}")
    print("OK",out)

def mix_music_only(video,musica,out,mus_vol=0.8,fade_out=2.0):
    """Video + música de fondo, sin voz. Fade de salida para cerrar limpio."""
    for etq, ruta in (("video", video), ("música", musica)):
        if not os.path.isfile(ruta):
            sys.exit(f"ERROR: no existe el archivo de {etq}: {ruta}")
    dur=vdur(video)
    fc=(f"[1:a]volume={mus_vol},apad=whole_dur={dur},"
        f"afade=t=out:st={max(0.0, dur-fade_out)}:d={fade_out},atrim=0:{dur}[aout]")
    r=subprocess.run(["ffmpeg","-y","-v","error","-i",video,"-i",musica,
                      "-filter_complex",fc,"-map","0:v","-map","[aout]",
                      "-c:v","copy","-c:a","aac","-b:a","160k",
                      "-movflags","+faststart",out],capture_output=True,text=True)
    if r.returncode != 0:
        sys.exit(f"ERROR: ffmpeg falló al mezclar música: {(r.stderr or '').strip()[:200]}")
    print("OK",out)

def main():
    ap=argparse.ArgumentParser(); s=ap.add_subparsers(dest="cmd",required=True)
    g=s.add_parser("gen",help="genera música con ElevenLabs Music (requiere ELEVENLABS_API_KEY)"); g.add_argument("-o",required=True)
    g.add_argument("--prompt",required=True); g.add_argument("--dur",type=float,default=30)
    m=s.add_parser("mix",help="video + voz en off + música con ducking (la música baja bajo la voz)"); m.add_argument("-v",required=True); m.add_argument("-a",required=True)
    m.add_argument("-m",required=True); m.add_argument("-o",required=True)
    m.add_argument("--mus-vol",type=float,default=0.12,
                   help="volumen base de la música (def: 0.12 ≈ 15 dB bajo la voz)")
    c=s.add_parser("cama",help="cama musical procedural con ffmpeg, sin API ni clave (respaldo declarado)")
    c.add_argument("-o",required=True); c.add_argument("--dur",type=float,default=30,
                   help="duración de la cama en segundos")
    c.add_argument("--bpm",type=float,default=92,
                   help="tempo del pulso grave (pulsos por minuto)")
    c.add_argument("--raiz",type=float,default=110.0,
                   help="frecuencia fundamental en Hz (110 = La2)")
    c.add_argument("--mayor",action="store_true",help="acorde mayor (default: menor)")
    c.add_argument("--vol",type=float,default=0.5,
                   help="volumen de la cama (0-1; se mezcla luego con mix a 0.12 bajo la voz)")
    mo=s.add_parser("musiconly",help="video + música de fondo (sin voz)")
    mo.add_argument("-v",required=True); mo.add_argument("-m",required=True)
    mo.add_argument("-o",required=True); mo.add_argument("--mus-vol",type=float,default=0.8)
    mo.add_argument("--fade-out",type=float,default=2.0)
    import os as _os, sys as _sys
    _sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "ffmpeg_tools"))
    from _comun import ayudar
    ayudar(ap, {'--prompt': 'descripción de la música: género, tempo, instrumentos, ánimo (en inglés rinde mejor)', '-v': 'video de entrada', '-a': 'voz en off (mp3/wav)', '-m': 'música (mp3/wav)', '--mus-vol': 'volumen de la música (0–1; mix 0.12 ≈ 15 dB bajo la voz, musiconly 0.8)', '--fade-out': 'segundos de fundido de la música al final'})
    a=ap.parse_args()
    if a.cmd=="gen": gen(a.prompt,a.dur,a.o)
    elif a.cmd=="cama": cama(a.dur,a.o,a.bpm,a.raiz,not a.mayor,a.vol)
    elif a.cmd=="musiconly": mix_music_only(a.v,a.m,a.o,a.mus_vol,a.fade_out)
    else: mix(a.v,a.a,a.m,a.o,a.mus_vol)

if __name__=="__main__": main()
