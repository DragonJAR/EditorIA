#!/usr/bin/env python3
"""Catálogo visual del repertorio único (125 opciones).

Una lista plana — sin separar escenas del resto. Cada opción se VE con
`repertorio.demo_de` (escena / caption / grade) y un rótulo fino en la
banda inferior de la zona segura. Nada de fichas vacías ni barras opacas
que tapen el contenido (eso rompía armonía y hacía “invisible” el cuerpo).

Uso:
  python scripts/catalogo_repertorio.py -o /tmp/catalogo-125 \\
      --brand brand/dragonjar.json [--dur 2.8] [--jobs 3]

Salida: catalogo-125.mp4 + manifest.json + hoja.png
"""
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
SKILL = AQUI.parent
sys.path.insert(0, str(AQUI))
sys.path.insert(0, str(AQUI / "ffmpeg_tools"))

from repertorio import catalogo_opciones, demo_de  # noqa: E402

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image = ImageDraw = ImageFont = None

DUR_DEFAULT = 2.8
FPS = 30
W, H = 1080, 1920
# banda inferior de zona segura vertical (~TikTok/Reels): el rótulo NO cubre
# el centro óptico (references/coherencia-espacial.md)
ROTULO_Y = int(H * 0.90)


def run(cmd, check=True):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(f"rc={r.returncode}\n$ {' '.join(map(str, cmd))}\n{r.stderr[-1000:]}")
    return r


def assets_muestra(dst: Path):
    """Reutiliza (o crea) capturas/foto/wav como galeria.assets — DRY con galeria."""
    dst.mkdir(parents=True, exist_ok=True)
    # preferir las ya generadas junto al plan de validación
    for name in ("captura_muestra.png", "captura_muestra_2.png", "foto_muestra.png",
                 "narracion_ia.wav"):
        src = Path("/tmp/validacion-espacial") / name
        if src.exists() and not (dst / name).exists():
            shutil.copy(src, dst / name)
    if not (dst / "foto_muestra.png").exists():
        from galeria import assets as _assets
        from _comun import NEUTRO
        _assets(str(dst), NEUTRO["acento"])
    if not (dst / "narracion_ia.wav").exists():
        run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
             "-i", "aevalsrc=0.4*sin(2*PI*180*t):s=44100:d=4",
             str(dst / "narracion_ia.wav")])
    # base visual rica para captions (no negro vacío)
    base = dst / "base_caption.mp4"
    if not base.exists():
        # kenburns corto de la foto de muestra vía render_plan
        pass  # se crea al primer caption
    # palabras / cues con hablantes
    pal = {
        "palabras": [
            {"texto": "Todas", "inicio": 0.2, "fin": 0.55, "confianza": 1},
            {"texto": "las", "inicio": 0.55, "fin": 0.75, "confianza": 1},
            {"texto": "opciones", "inicio": 0.75, "fin": 1.35, "confianza": 1},
            {"texto": "en", "inicio": 1.5, "fin": 1.7, "confianza": 1},
            {"texto": "un", "inicio": 1.7, "fin": 1.9, "confianza": 1},
            {"texto": "solo", "inicio": 1.9, "fin": 2.25, "confianza": 1},
            {"texto": "catálogo", "inicio": 2.25, "fin": 2.85, "confianza": 1},
        ]
    }
    (dst / "palabras.json").write_text(json.dumps(pal, ensure_ascii=False), encoding="utf-8")
    (dst / "cues_hab.txt").write_text(
        "0:00.2-0:01.4 A: Todas las opciones\n"
        "0:01.5-0:02.9 B: en un solo catálogo\n",
        encoding="utf-8",
    )


def plan_escena(tipo: str, dur: float, brand: str | None, assets: Path) -> dict:
    muestra = json.loads((AQUI / "escenas_muestra.json").read_text(encoding="utf-8"))["escenas"]
    e = dict(muestra[tipo], tipo=tipo, **{"from": 0.0, "to": dur})
    at = e.get("at") or {}
    if isinstance(at, dict):
        e["at"] = {k: min(float(v), dur - 0.05)
                   for k, v in at.items() if isinstance(v, (int, float))}
    if e.get("captura"):
        e["captura"] = "captura_muestra.png"
    if e.get("imagen"):
        e["imagen"] = "foto_muestra.png"
    if e.get("archivo"):
        e["archivo"] = "narracion_ia.wav"
    for paso in e.get("pasos") or []:
        if paso.get("captura"):
            paso["captura"] = ("captura_muestra_2.png"
                               if "2" in str(paso["captura"]) else "captura_muestra.png")
    plan = {
        "duracion": dur,
        "camara": {"z0": 1.0, "z1": 1.04, "flota": 2},
        "escenas": [e],
    }
    if brand:
        plan["brand"] = brand
    return plan


def render_escena(tipo: str, dest: Path, dur: float, brand: str | None,
                  assets: Path, jobs: int):
    plan = plan_escena(tipo, dur, brand, assets)
    pdir = assets / "plans"
    pdir.mkdir(exist_ok=True)
    for name in ("captura_muestra.png", "captura_muestra_2.png", "foto_muestra.png",
                 "narracion_ia.wav"):
        src = assets / name
        if src.exists():
            shutil.copy(src, pdir / name)
    ruta = pdir / f"{tipo}.json"
    ruta.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    raw = pdir / f"{tipo}.raw.mp4"
    cmd = [sys.executable, str(AQUI / "render_plan.py"), str(ruta), "-o", str(raw),
           "--blur", "1", "--jobs", str(jobs), "--force"]
    if brand:
        cmd += ["--brand", brand]
    run(cmd)
    cut(raw, 0, dest, dur)


def cut(src: Path, t0: float, dest: Path, dur: float):
    run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t0:.3f}", "-i", str(src),
         "-t", str(dur), "-r", str(FPS), "-an",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", str(dest)])


def rotulo_inferior(src: Path, dest: Path, n: int, total: int, oid: str, motor: str, dur: float):
    """Rótulo fino en la banda inferior segura — no tapa el centro óptico."""
    label = f"{n:03d}/{total}  {oid}"
    # escape for drawtext
    def esc(s):
        return s.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    # dos líneas: id + motor; caja semitransparente pequeña
    vf = (
        f"drawtext=text='{esc(label)}':fontsize=28:fontcolor=white:"
        f"x=(w-text_w)/2:y={ROTULO_Y}:"
        f"box=1:boxcolor=black@0.45:boxborderw=10,"
        f"drawtext=text='{esc(motor)}':fontsize=20:fontcolor=0xC82814:"
        f"x=(w-text_w)/2:y={ROTULO_Y + 36}:"
        f"box=1:boxcolor=black@0.35:boxborderw=6"
    )
    run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-vf", vf,
         "-t", str(dur), "-r", str(FPS), "-an",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", str(dest)])


CAP_ARGS = {
    "cap-rail-karaoke": ["--palabras", "palabras.json", "--karaoke", "--phrase-aware", "--animate", "pop"],
    "cap-rail-fade": ["--palabras", "palabras.json", "--animate", "fade", "--phrase-aware"],
    "cap-rail-pop": ["--palabras", "palabras.json", "--animate", "pop", "--phrase-aware"],
    "cap-rail-slide": ["--palabras", "palabras.json", "--animate", "slide", "--phrase-aware"],
    "cap-hablantes": ["--text", "cues_hab.txt", "--hablantes", "A=FFD400,B=4FC3F7",
                      "--animate", "pop", "--karaoke"],
}


def ensure_base_caption(assets: Path, brand: str | None, jobs: int, dur: float) -> Path:
    """Base con imagen (kenburns) PERO sin titular quemado.

    Si la base trae titulo/subtitulo, el catálogo muestra dos textos a la
    vez (escena + caption) y se lee como desarmonía / «no se ve el caption».
    """
    base = assets / "base_caption.mp4"
    if base.exists() and base.stat().st_size > 10000:
        return base
    muestra = json.loads((AQUI / "escenas_muestra.json").read_text(encoding="utf-8"))["escenas"]
    e = dict(muestra["kenburns"], tipo="kenburns", titulo="", subtitulo="",
             **{"from": 0.0, "to": dur})
    if e.get("imagen"):
        e["imagen"] = "foto_muestra.png"
    at = e.get("at") or {}
    if isinstance(at, dict):
        e["at"] = {k: min(float(v), dur - 0.05)
                   for k, v in at.items() if isinstance(v, (int, float))}
    plan = {"duracion": dur, "camara": {"z0": 1.0, "z1": 1.04, "flota": 2},
            "escenas": [e]}
    if brand:
        plan["brand"] = brand
    pdir = assets / "plans"
    pdir.mkdir(exist_ok=True)
    for name in ("foto_muestra.png",):
        src = assets / name
        if src.exists():
            shutil.copy(src, pdir / name)
    ruta = pdir / "base_caption.plan.json"
    ruta.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    cmd = [sys.executable, str(AQUI / "render_plan.py"), str(ruta), "-o", str(base),
           "--blur", "1", "--jobs", str(jobs), "--force"]
    if brand:
        cmd += ["--brand", brand]
    run(cmd)
    return base


def render_caption(oid: str, dest: Path, dur: float, brand: str | None,
                   assets: Path, jobs: int):
    base = ensure_base_caption(assets, brand, jobs, max(dur, 3.0))
    raw = assets / f"cap_{oid}.raw.mp4"
    args = CAP_ARGS.get(oid, ["--palabras", "palabras.json", "--karaoke",
                              "--phrase-aware", "--animate", "pop"])
    # paths relative to assets cwd
    cmd = [sys.executable, str(AQUI / "ffmpeg_tools" / "caption.py"),
           str(base), *args, "-o", str(raw)]
    if brand:
        cmd += ["--brand", brand]
    # resolve relative asset names inside args
    fixed = []
    for a in cmd:
        p = assets / a
        if a.endswith((".json", ".txt")) and p.exists():
            fixed.append(str(p))
        else:
            fixed.append(a)
    r = run(fixed, check=False)
    if r.returncode or not raw.exists():
        # fallback: al menos la base con contenido (nunca negro vacío)
        cut(base, 0, dest, dur)
        return "caption-fallback-base"
    cut(raw, 0, dest, dur)
    return "caption"


def render_grade(dest: Path, dur: float, assets: Path, brand: str | None, jobs: int):
    base = ensure_base_caption(assets, brand, jobs, max(dur, 3.0))
    raw = assets / "moody.raw.mp4"
    run([sys.executable, str(AQUI / "ffmpeg_tools" / "grade.py"),
         str(base), "-o", str(raw), "--intensidad", "0.7"])
    cut(raw, 0, dest, dur)


def hoja(manifest, out: Path):
    if Image is None:
        return None
    cols = 10
    thumbs = []
    for m in manifest:
        raw = subprocess.run(
            ["ffmpeg", "-v", "error", "-ss", "1.2", "-i", m["clip"],
             "-frames:v", "1", "-vf", "scale=140:248",
             "-f", "image2pipe", "-vcodec", "png", "-"],
            capture_output=True).stdout
        if not raw:
            continue
        import io
        th = Image.open(io.BytesIO(raw)).convert("RGB")
        thumbs.append((m["n"], m["id"], m["via"], th))
    rows = math.ceil(len(thumbs) / cols) if thumbs else 1
    sheet = Image.new("RGB", (cols * 148 + 16, rows * 280 + 30), (16, 16, 18))
    d = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    color = {"escena": (80, 200, 120), "caption": (220, 160, 80),
             "grade": (220, 80, 120)}
    for i, (n, oid, via, th) in enumerate(thumbs):
        r, c = divmod(i, cols)
        x, y = 8 + c * 148, 16 + r * 280
        sheet.paste(th, (x, y))
        col = color.get(via, (180, 180, 180))
        d.rectangle([x, y, x + 140, y + 248], outline=col, width=2)
        d.text((x + 2, y + 250), f"{n:03d} {oid[:14]}", fill=(240, 240, 240), font=font)
        d.text((x + 2, y + 262), via, fill=col, font=font)
    path = out / "hoja.png"
    sheet.save(path)
    return path


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--out", required=True, help="carpeta de salida")
    ap.add_argument("--brand", help="brand pack")
    ap.add_argument("--dur", type=float, default=DUR_DEFAULT)
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument("--solo", help="ids separados por coma (debug)")
    a = ap.parse_args()
    out = Path(a.out).resolve()
    clips = out / "clips"
    assets = out / "assets"
    clips.mkdir(parents=True, exist_ok=True)
    assets_muestra(assets)
    brand = os.path.abspath(a.brand) if a.brand else None

    opts = catalogo_opciones()
    items = sorted(opts.items(), key=lambda kv: kv[0])
    if a.solo:
        want = set(a.solo.split(","))
        items = [(i, o) for i, o in items if i in want]
    total = len(catalogo_opciones()) if not a.solo else len(items)
    # cache de escenas ya renderizadas (muchas opciones comparten análogo)
    cache_escena: dict[str, Path] = {}
    manifest = []
    t0 = time.time()

    for idx, (oid, op) in enumerate(items, 1):
        demo = demo_de(op)
        dest = clips / f"{idx:03d}_{oid}.mp4"
        body = clips / f"{idx:03d}_{oid}.body.mp4"
        print(f"[{idx:03d}/{len(items)}] {demo['motor']} · {oid} → {demo['via']}"
              + (f"/{demo.get('tipo')}" if demo.get("tipo") else ""), flush=True)
        via = demo["via"]
        try:
            if via == "escena":
                tipo = demo["tipo"]
                if tipo not in cache_escena:
                    p = assets / f"escena_{tipo}.mp4"
                    render_escena(tipo, p, a.dur, brand, assets, a.jobs)
                    cache_escena[tipo] = p
                shutil.copy(cache_escena[tipo], body)
                how = f"escena:{tipo}"
            elif via == "caption":
                how = render_caption(oid, body, a.dur, brand, assets, a.jobs)
            elif via == "grade":
                render_grade(body, a.dur, assets, brand, a.jobs)
                how = "grade"
            else:
                raise RuntimeError(f"via desconocida: {via}")
            motor_lbl = demo["motor"]
            if demo.get("analogo"):
                motor_lbl = f"{demo['motor']} · {demo['analogo']}"
            rotulo_inferior(body, dest, idx, total, oid, motor_lbl, a.dur)
        except Exception as ex:
            print(f"  FAIL {oid}: {ex}", flush=True)
            # último recurso: escena frase (siempre visible), nunca ficha vacía
            if "frase" not in cache_escena:
                p = assets / "escena_frase.mp4"
                render_escena("frase", p, a.dur, brand, assets, a.jobs)
                cache_escena["frase"] = p
            shutil.copy(cache_escena["frase"], body)
            rotulo_inferior(body, dest, idx, total, oid, f"error→frase", a.dur)
            how = f"fallback:{ex.__class__.__name__}"
        manifest.append({
            "n": idx, "id": oid, "motor": op.get("motor"), "via": via,
            "how": how, "demo": demo, "clip": str(dest),
        })

    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                                       encoding="utf-8")
    lst = out / "concat.txt"
    lst.write_text("\n".join(f"file '{Path(m['clip']).resolve()}'" for m in manifest) + "\n",
                   encoding="utf-8")
    final = out / "catalogo-125.mp4"
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
         "-i", str(lst), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS),
         str(final)])
    hoja_path = hoja(manifest, out)
    from collections import Counter
    print(f"\nOK {final} · {len(manifest)} clips · {time.time()-t0:.0f}s · "
          f"vias={dict(Counter(m['via'] for m in manifest))}")
    if hoja_path:
        print(f"hoja: {hoja_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
