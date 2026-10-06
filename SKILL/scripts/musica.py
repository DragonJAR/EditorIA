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
import os, sys, argparse, subprocess, requests

def gen(prompt,dur,out):
    key=os.environ.get("ELEVENLABS_API_KEY")
    if not key: sys.exit("Falta ELEVENLABS_API_KEY en el entorno")
    r=requests.post("https://api.elevenlabs.io/v1/music",
        headers={"xi-api-key":key,"Content-Type":"application/json"},
        json={"prompt":prompt,"music_length_ms":int(dur*1000),
              "model_id":"music_v1"},timeout=180)
    r.raise_for_status()
    open(out,"wb").write(r.content)
    print("OK",out)

def vdur(video):
    r=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
                      "-of","csv=p=0",video],capture_output=True,text=True)
    return float(r.stdout.strip())

def mix(video,voz,musica,out,mus_vol=0.12):
    # música a volumen base + ducking por la voz; voz siempre al frente.
    # Defaults verificados (v4 AI Tinkerers): música ~15 dB bajo la voz
    # (medido con scripts/medir_mezcla.py). Ver reglas-tecnicas.md.
    # duración explícita del video (nada de -shortest: recorta si la voz es más corta)
    dur=vdur(video)
    fc=(f"[2:a]volume={mus_vol},apad=whole_dur={dur}[mx];"
        f"[1:a]apad=whole_dur={dur},asplit=2[vox1][vox2];"
        f"[mx][vox1]sidechaincompress=threshold=0.015:ratio=12:attack=15:"
        f"release=600:makeup=1[duck];"
        f"[duck][vox2]amix=inputs=2:normalize=0:duration=longest,"
        f"atrim=0:{dur}[aout]")
    subprocess.run(["ffmpeg","-y","-v","error","-i",video,"-i",voz,"-i",musica,
                    "-filter_complex",fc,"-map","0:v","-map","[aout]",
                    "-c:v","copy","-c:a","aac","-b:a","160k",
                    "-movflags","+faststart",out],check=True)
    print("OK",out)

def mix_music_only(video,musica,out,mus_vol=0.8,fade_out=2.0):
    """Video + música de fondo, sin voz. Fade de salida para cerrar limpio."""
    dur=vdur(video)
    fc=(f"[1:a]volume={mus_vol},apad=whole_dur={dur},"
        f"afade=t=out:st={dur-fade_out}:d={fade_out},atrim=0:{dur}[aout]")
    subprocess.run(["ffmpeg","-y","-v","error","-i",video,"-i",musica,
                    "-filter_complex",fc,"-map","0:v","-map","[aout]",
                    "-c:v","copy","-c:a","aac","-b:a","160k",
                    "-movflags","+faststart",out],check=True)
    print("OK",out)

def main():
    ap=argparse.ArgumentParser(); s=ap.add_subparsers(dest="cmd",required=True)
    g=s.add_parser("gen",help="genera música con ElevenLabs Music (requiere ELEVENLABS_API_KEY)"); g.add_argument("-o",required=True)
    g.add_argument("--prompt",required=True); g.add_argument("--dur",type=float,default=30)
    m=s.add_parser("mix",help="video + voz en off + música con ducking (la música baja bajo la voz)"); m.add_argument("-v",required=True); m.add_argument("-a",required=True)
    m.add_argument("-m",required=True); m.add_argument("-o",required=True)
    m.add_argument("--mus-vol",type=float,default=0.12,
                   help="volumen base de la música (def: 0.12 ≈ 15 dB bajo la voz)")
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
    elif a.cmd=="musiconly": mix_music_only(a.v,a.m,a.o,a.mus_vol,a.fade_out)
    else: mix(a.v,a.a,a.m,a.o,a.mus_vol)

if __name__=="__main__": main()
