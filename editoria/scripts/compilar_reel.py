#!/usr/bin/env python3
"""Compila N videos en UN reel: mide, elige el mejor momento de cada uno, los
corta con disolvencia y escribe el plan de las tarjetas.

QUE RESUELVE
  Editar una biblioteca de piezas en una sola pieza es el trabajo central de
  un editor, y la skill tenia las primitivas sueltas (montaje.py corta y
  transiciona; scenes.py mide el valor) pero NADA que las orquestara. Este
  script es esa orquestacion: mide, elige, corta, disuelve y deja el plan
  escrito con los tiempos ya calculados.

DE DONDE SALE EL "MEJOR MOMENTO" DE CADA VIDEO
  1. Si el video tiene plan (o se le pasa con --plan), gana el PLAN: el claim
     de una pieza es la decision del editor, no de la medicion. Del plan se
     toma la ultima escena antes del cierre de marca (el "final"): ahi esta la
     afirmacion que el servicio quiere que se lea, y el corte empieza justo
     cuando su texto entra en pantalla.
  2. Si no hay plan, gana la MEDICION: `scripts/ffmpeg_tools/scenes.py` con
     --json, de donde sale el pico de audio mas fuerte (instante y valor). El
     corte se centra en ese pico. Es mas pobre que el plan (un reel con
     disolvencias es un solo plano y mide poco), pero nunca inventado: si la
     medicion no puede, se dice y se cae al tramo pedido a mano.

POR QUE EL PLAN Y EL MONTAJE SALEN DE LA MISMA CUENTA
  Una disolvencia de 0,25 s se come 0,25 s del segmento que entra. Si el plan y
  el montage cada uno hicieran su cuenta, la voz se desfasaria del footage. Aqui
  los dos salen de la MISMA linea de tiempo: `linea_tiempo()` la calcula una
  vez y la usan las dos.

LO QUE NO HACE (y lo dice)
  · NO renderiza la tipografia, NO pone la voz, NO mezcla el audio, NO
    entrega: eso es el camino canonico (render_plan.py, voz_local.py,
    mezclar_audio.py, loudness.py, qa_entrega.py) y este script IMPRIME los
    comandos que lo terminan. Una pieza se construye con la skill entera, no
    con un atajo.
  · NO toca los videos de entrada.

Uso:
    python3 scripts/compilar_reel.py -o salida/ \
        --titulo "Diez servicios" --lema "Un solo equipo" a.mp4 b.mp4 c.mp4
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(SCRIPTS)
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

XFADE = 0.25          # la disolvencia de los reels: un corte duro es un "pop"
APERTURA = 3.9        # la tarjeta de apertura (o el footage que la sostiene)
CIERRE = 3.55         # la tarjeta de cierre (la voz del cierre necesita aire)


# ---------------------------------------------------------------- seleccion

def _nombre_de(video, i, marca=""):
    """El nombre que va en el rotulo: el del fichero, sin el prefijo de la marca.

    La marca se quita con el NOMBRE DEL PACK (en runtime): ninguna marca
    concreta puede estar escrita en el codigo de la skill.
    """
    base = os.path.splitext(os.path.basename(video))[0]
    if marca:
        base = re.sub(re.escape(marca), "", base, flags=re.I)
    base = re.sub(r"^[\s_-]+", "", base)        # los separadores del principio
    base = re.sub(r"^\d{0,2}[\s_-]*", "", base)  # el numero de orden
    base = base.replace("_", " ").replace("-", " ").strip(" -")
    return base.title() if base else f"Pieza {i + 1}"


def _escena_del_claim(plan):
    """La escena del claim: la ultima antes del cierre de marca.

    El cierre ("final"/"cierre"/"marca") es la firma, no la afirmacion: el
    claim es lo que va justo antes.
    """
    escenas = [e for e in (plan.get("escenas") or []) if isinstance(e, dict)]
    if not escenas:
        return None
    cierres = {"final", "cierre", "marca", "cta"}
    for e in reversed(escenas):
        if str(e.get("tipo", "")).lower() not in cierres:
            return e
    return escenas[0]


def _entrada_del_claim(esc):
    """El instante en que el texto de la escena entra en pantalla."""
    at = esc.get("at") or {}
    vals = []
    for v in at.values():
        try:
            vals.append(float(v))
        except (TypeError, ValueError):
            pass
    if vals:
        return min(vals)
    try:
        return float(esc["from"])
    except (KeyError, TypeError, ValueError):
        return None


def _plan_de(video, plan_comun=None, plan_dir=None):
    """El plan de un video: el comun, el de la carpeta, o el que esta a su lado."""
    if plan_comun:
        try:
            with open(plan_comun, encoding="utf-8") as fh:
                doc = json.load(fh)
            if isinstance(doc, dict) and doc.get("escenas"):
                return doc
        except (OSError, ValueError):
            return None
    cands = []
    if plan_dir:
        base = os.path.splitext(os.path.basename(video))[0]
        cands.append(os.path.join(plan_dir, base + ".json"))
    cands.append(os.path.splitext(video)[0] + ".json")
    for cand in cands:
        if os.path.isfile(cand):
            try:
                with open(cand, encoding="utf-8") as fh:
                    doc = json.load(fh)
                if isinstance(doc, dict) and doc.get("escenas"):
                    return doc
            except (OSError, ValueError):
                return None
    return None


def _pico_medido(video, timeout=900):
    """(instante, valor) del pico de audio mas fuerte, medido con scenes.py."""
    script = os.path.join(BASE, "scripts", "ffmpeg_tools", "scenes.py")
    if not os.path.isfile(script):
        return None
    try:
        r = subprocess.run([sys.executable, script, video, "--json",
                            "--highlights", "6"],
                           capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    try:
        doc = json.loads(r.stdout)
    except ValueError:
        return None
    picos = doc.get("audio_peaks") or []
    if not picos:
        return None
    mejor = max(picos, key=lambda p: float(p.get("rms") or 0))
    try:
        return float(mejor["time"]), float(mejor.get("rms") or 0)
    except (KeyError, TypeError, ValueError):
        return None


def _ventana(video, plan, dur, desde, hasta):
    """(inicio, fin, origen) del corte de este video."""
    if desde is not None and hasta is not None:
        return desde, hasta, "manual"
    if plan:
        esc = _escena_del_claim(plan)
        entrada = _entrada_del_claim(esc) if esc else None
        if entrada is not None:
            ini = max(0.0, entrada - 0.2)
            return ini, ini + dur, "plan"
    pico = _pico_medido(video)
    if pico:
        t = pico[0]
        ini = max(0.0, t - dur / 2.0)
        return ini, ini + dur, "medido"
    return None, None, None


# ------------------------------------------------------------------ montage

def _recorta(video, ini, fin, salida, fps=24):
    """Un trozo del video, sin audio, al fps pedido y en 9:16.

    El recorte es un no-op para un video que ya es vertical (lo habitual), pero
    NORMALIZA el que no lo es: el xfade exige que todos los segmentos tengan
    las mismas dimensiones, y sin esto un reel con un plano apaisado no se
    puede montar.
    """
    fc = ("scale=1080:1920:force_original_aspect_ratio=increase,"
          "crop=1080:1920,setsar=1,fps=" + str(fps))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{ini:.3f}",
                    "-t", f"{max(0.1, fin - ini):.3f}", "-i", video, "-an",
                    "-vf", fc, "-map", "0:v",
                    "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p",
                    salida],
                   check=True, timeout=1800)
    return salida


def _negro(dur, salida, fps=24, w=1080, h=1920):
    """Un tramo en negro (para la apertura o el cierre sin footage)."""
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
                    "-i", f"color=c=black:s={w}x{h}:r={fps}:d={dur:.3f}",
                    "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p",
                    salida], check=True, timeout=600)
    return salida


def linea_tiempo(durs):
    """La linea de tiempo REAL del fondo, y los beats que van sobre ella.

    El fondo es una cadena de segmentos (apertura, un tramo por video, cierre)
    con una DISOLVENCIA entre cada uno. Cada disolvencia se come 0,25 s del
    segmento que entra, asi que el contenido del segmento k empieza en
    suma(durs[:k]) - k*0.25.
    """
    segs = list(durs)
    beats = []
    for n, d in enumerate(durs[1:-1], start=1):
        ini = sum(segs[:n]) - n * XFADE
        fin = ini + d - XFADE
        beats.append({"from": round(ini, 3), "to": round(fin, 3)})
    cierre_ini = sum(segs[:len(segs) - 1]) - (len(segs) - 1) * XFADE
    total = round(cierre_ini + segs[-1], 3)
    return beats, cierre_ini, total


def _fondo(segmentos, salida, fps=24):
    """Los segmentos encadenados con disolvencia: el fondo del reel."""
    durs = [s["dur"] for s in segmentos]
    cadena = []
    prev = None
    for n in range(len(segmentos)):
        if prev is None:
            cadena.append(f"[{n}:v]setpts=PTS-STARTPTS,format=yuv420p[a{n}]")
            prev = f"a{n}"
        else:
            offset = sum(durs[:n]) - n * XFADE
            cadena.append(f"[{prev}][{n}:v]xfade=transition=fade:"
                          f"duration={XFADE}:offset={offset:.3f}[x{n}]")
            prev = f"x{n}"
    total = sum(durs) - (len(durs) - 1) * XFADE
    fc = (";".join(cadena) + f";[{prev}]trim=0:{total:.3f},setpts=PTS-STARTPTS[v]")
    cmd = ["ffmpeg", "-v", "error", "-y"]
    for s in segmentos:
        cmd += ["-i", s["ruta"]]
    cmd += ["-filter_complex", fc, "-map", "[v]", "-r", str(fps),
            "-c:v", "libx264", "-preset", "medium", "-crf", "17",
            "-pix_fmt", "yuv420p", salida]
    subprocess.run(cmd, check=True, timeout=3600)
    return salida


def _pack_de_brand(ruta=None):
    """El pack de marca: el que se le pase, o el que haya en brand/.

    NINGUNA marca concreta puede estar escrita en el codigo (los packs viven
    en brand/ y se publican con la skill): el nombre, el lema y el acento se
    LEEN del pack en runtime.
    """
    if ruta:
        return os.path.abspath(ruta)
    d = os.path.join(BASE, "brand")
    packs = sorted(f for f in os.listdir(d) if f.endswith(".json")) if os.path.isdir(d) else []
    if not packs:
        return None
    return os.path.join(d, packs[0])


def _datos_de_pack(ruta):
    """(nombre, lema) del pack. Vacio si no hay pack."""
    if not ruta or not os.path.isfile(ruta):
        return "", ""
    try:
        with open(ruta, encoding="utf-8") as fh:
            doc = json.load(fh) or {}
    except (OSError, ValueError):
        return "", ""
    return str(doc.get("nombre") or ""), str(doc.get("lema") or "")


def _escribe_plan(ruta, beats, titulo, lema, marca, nombres, total, pack, boton, lema_pack):
    """El plan del reel: apertura, un rotulo por video y el cierre."""
    escenas = [{
        "tipo": "apertura", "from": 0.0, "to": beats[0]["from"] if beats else APERTURA,
        "texto1": [titulo[0], titulo[1]] if len(titulo) > 1 else [titulo[0]],
        "texto2": [lema[0], lema[1]] if len(lema) > 1 else [lema[0]],
        "at": {"cambio": 2.1, "p1": [0.2, 0.6, 1.0], "p2": [2.1, 2.5, 2.9, 3.3]},
        "voz": " ".join(titulo) + ". " + " ".join(lema) + ".",
    }]
    for b, nombre in zip(beats, nombres):
        escenas.append({
            "tipo": "rotulo_inferior", "from": b["from"], "to": b["to"],
            "nombre": nombre,
            "at": {"entra": round(b["from"] + 0.2, 3)},
        })
    ultima = beats[-1]["to"] if beats else 0.0
    lema_final = lema_pack or (" ".join(titulo) + " " + " ".join(lema) + ".")
    escenas.append({
        "tipo": "final", "from": ultima, "to": total,
        "marca": marca,
        "lema": lema_final,
        "boton": boton,
        "at": {"lema": round(ultima + 0.05, 3), "boton": round(ultima + 1.6, 3)},
        "voz": f"{marca}. Seguridad ofensiva.",
    })
    plan = {
        "brand": pack,
        "duracion": total,
        "tamano": "1080x1920",
        "numeros": "es",
        "sfx": [{"escena": n + 1, "ancla": "escena", "at": 0.0, "sonido": "whoosh"}
                 for n in range(len(beats) + 1)]
                + [{"escena": len(escenas), "ancla": "escena", "at": 0.0, "sonido": "ding"}],
        "sobre_footage_vivo": True,
        "tells_ok": ["cadencia-uniforme", "poco-repertorio"],
        "escenas": escenas,
    }
    with open(ruta, "w", encoding="utf-8") as fh:
        json.dump(plan, fh, ensure_ascii=False, indent=1)
    return ruta


def main():
    ap = argparse.ArgumentParser(
        description="Compila N videos en un reel: mide, elige el mejor momento "
                    "de cada uno, los corta con disolvencia y escribe el plan")
    ap.add_argument("videos", nargs="+", help="Los videos a compilar")
    ap.add_argument("-o", "--out", required=True, help="Directorio de salida")
    ap.add_argument("--brand", default=None,
                    help="Pack de marca (default: el que haya en brand/)")
    ap.add_argument("--marca", default=None,
                    help="La marca del cierre (default: la del pack)")
    ap.add_argument("--boton", default="",
                    help="El boton del cierre (default: ninguno)")
    ap.add_argument("--titulo", default="Diez servicios",
                    help="El titular de la apertura (dos lineas con '|')")
    ap.add_argument("--lema", default="Un |solo equipo",
                    help="La segunda linea de la apertura (dos lineas con '|')")
    ap.add_argument("--plan", default=None,
                    help="Un plan comun para todos los videos (si no, se busca "
                         "al lado de cada video)")
    ap.add_argument("--plan-dir", default=None,
                    help="Carpeta con los planes (uno por video)")
    ap.add_argument("--apertura", default=None,
                    help="Video cuyo footage sostiene la tarjeta de apertura "
                         "(si no, la apertura va sobre negro)")
    ap.add_argument("--cierre", default=None,
                    help="Video cuyo footage sostiene la tarjeta de cierre "
                         "(si no, el cierre va sobre negro)")
    ap.add_argument("--duracion", type=float, default=2.5,
                    help="Segundos de cada tramo (el beat del reel)")
    ap.add_argument("--desde", type=float, default=None,
                    help="Tramo manual: inicio en segundos (si no, se mide)")
    ap.add_argument("--hasta", type=float, default=None,
                    help="Tramo manual: fin en segundos")
    ap.add_argument("--fps", type=int, default=24, help="fps del corte (24 nativo)")
    a = ap.parse_args()

    for v in a.videos:
        if not os.path.isfile(v):
            print(f"ERROR: no existe {v}", file=sys.stderr)
            return 2
    if a.desde is not None and a.hasta is None or a.hasta is not None and a.desde is None:
        print("ERROR: --desde y --hasta van juntos", file=sys.stderr)
        return 2

    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    pack = _pack_de_brand(a.brand)
    if pack is None:
        print("ERROR: no hay pack de marca (pasa --brand o pon uno en brand/)",
              file=sys.stderr)
        return 2
    nombre_pack, lema_pack = _datos_de_pack(pack)
    marca = a.marca or nombre_pack
    if not marca:
        print("ERROR: el pack no trae 'nombre' y no se paso --marca", file=sys.stderr)
        return 2
    tmp = tempfile.mkdtemp(prefix="reel_")
    try:
        nombres = []
        segmentos = []
        # la apertura
        if a.apertura:
            ini, fin = 0.0, min(APERTURA, _dur(a.apertura)), "apertura"
            ruta = _recorta(a.apertura, ini, fin, os.path.join(tmp, "apertura.mp4"), a.fps)
            segmentos.append({"ruta": ruta, "dur": fin - ini})
        else:
            segmentos.append({"ruta": _negro(APERTURA, os.path.join(tmp, "apertura.mp4"), a.fps),
                              "dur": APERTURA})
            print("AVISO: sin --apertura, la tarjeta de apertura va sobre negro y el "
                  "auto_qa la marcara como frame negro", file=sys.stderr)

        for i, v in enumerate(a.videos):
            plan = _plan_de(v, a.plan, a.plan_dir)
            ini, fin, origen = _ventana(v, plan, a.duracion, a.desde, a.hasta)
            if ini is None:
                print(f"AVISO: de {os.path.basename(v)} no se pudo saber el mejor "
                      f"momento (ni plan ni medicion). Se usan los primeros "
                      f"{a.duracion:.1f} s.", file=sys.stderr)
                ini, fin, origen = 0.0, a.duracion, "por defecto"
            ruta = _recorta(v, ini, fin, os.path.join(tmp, f"{i:02d}.mp4"), a.fps)
            segmentos.append({"ruta": ruta, "dur": fin - ini})
            nombres.append(_nombre_de(v, i, marca))
            print(f"  {os.path.basename(v)}: {ini:.2f}-{fin:.2f} ({origen}) -> "
                  f"'{nombres[-1]}'")

        # el cierre
        if a.cierre:
            dur_c = _dur(a.cierre)
            ini_c = max(0.0, dur_c - CIERRE)
            ruta = _recorta(a.cierre, ini_c, dur_c, os.path.join(tmp, "cierre.mp4"), a.fps)
            segmentos.append({"ruta": ruta, "dur": dur_c - ini_c})
        else:
            segmentos.append({"ruta": _negro(CIERRE, os.path.join(tmp, "cierre.mp4"), a.fps),
                              "dur": CIERRE})
            print("AVISO: sin --cierre, la tarjeta de cierre va sobre negro y el "
                  "auto_qa la marcara como frame negro", file=sys.stderr)

        beats, cierre_ini, total = linea_tiempo([s["dur"] for s in segmentos])
        base = _fondo(segmentos, os.path.join(out, "base.mp4"), a.fps)

        titulo = [t.strip() for t in a.titulo.split("|")]
        lema = [t.strip() for t in a.lema.split("|")]
        ruta_plan = os.path.join(out, "plan.json")
        _escribe_plan(ruta_plan, beats, titulo, lema, marca, nombres, total,
                      pack, a.boton, lema_pack)

        print(f"\nreel compilado: {total:.2f} s · {len(a.videos)} piezas")
        print(f"  fondo: {base}")
        print(f"  plan: {ruta_plan}")
        print("\nSiguientes pasos (el camino canonico de la skill):")
        print(f"  1. overlay: python3 scripts/render_plan.py {ruta_plan} -o "
              f"{out}/overlay.mov --blur 5 --fps {a.fps} --force")
        print(f"  2. voz:    python3 scripts/voz_local.py {ruta_plan} -o {out}/voz.wav "
              f"--voz Paulina")
        print(f"  3. mezcla: python3 scripts/mezclar_audio.py {ruta_plan} --video "
              f"{base} --voz {out}/voz.wav --musica <cama>.wav --pack <sfx> -o "
              f"{out}/mezcla.mp4")
        print(f"  4. puerta: python3 scripts/qa_entrega.py {out}/reel.mp4 --plan "
              f"{ruta_plan}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


def _dur(video):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", video], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


if __name__ == "__main__":
    sys.exit(main())
