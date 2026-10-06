#!/usr/bin/env python3
"""Detecta retakes / false-starts sobre segmentos ya transcritos.

Entrada: JSON con segmentos [{start, end, text}] o un SRT. Agrupa los
segmentos en "islas" de sonido (separadas por pausas >= --pausa) y aplica
la regla "la ultima toma gana": una isla (o corrida de islas) que es el
comienzo de lo que viene despues es un false start: se marca para corte
y queda la ultima toma.

Tambien marca islas que son solo muletillas (eh, um, bueno...) y reporta
como "revisar en X.Xs" los casos dudosos (fuzzy-match ambiguo).

Nunca propone cortar dentro de una palabra: los cortes caen en las pausas
entre islas y se expanden con --margen (default 0.3s) para no rozar el
inicio/fin del habla.

Solo stdlib. Sin red, sin keys. La transcripción de entrada la provee
whisper.cpp, el ASR que uses, o segmentos de cualquier otra fuente.

Ejemplos:
  python3 retakes.py transcripcion.json
  python3 retakes.py subs.srt --idioma es --margen 0.4 --edl cortes.edl
  python3 retakes.py transcripcion.json --dry-run --json > plan.json
"""
import argparse
import difflib
import json
import os
import re
import sys
import unicodedata

# Muletillas: una isla que solo tiene estas se va (con --keep-fillers se queda).
FILLERS = {
    "es": {"eh", "em", "este", "esta", "mmm", "mm", "ah", "ay", "ejem"},
    "en": {"um", "uh", "uhm", "hm", "hmm", "mh", "mm", "erm", "er",
           "like", "you", "know", "yknow"},
}
# Lead-ins: palabras con las que empieza una toma que no son parte de la
# frase ("bueno, hoy vamos a..." es la misma toma que "hoy vamos a...").
# Solo se ignoran al COMPARAR tomas; no se cortan del audio.
LEADINS = {
    "es": {"bueno", "bien", "entonces", "o", "sea", "asi", "que", "mira",
           "oye", "pues", "vale", "eh", "este"},
    "en": {"so", "well", "okay", "ok", "right", "now", "actually",
           "basically", "um", "uh"},
}
# Nexos que una toma nueva suele agregar al frente ("and", "that"): se
# apartan solo al comparar dos islas vecinas.
LINKS = {
    "es": {"y", "pero", "que", "entonces", "luego"},
    "en": {"and", "but", "so", "then", "that"},
}

TIME_RE = re.compile(r"(\d+):(\d+):(\d+)[,.](\d+)")


def die(msg):
    print(f"retakes.py: error: {msg}", file=sys.stderr)
    sys.exit(1)


def info(msg):
    print(f"retakes.py: {msg}", file=sys.stderr)


def norm(word):
    w = unicodedata.normalize("NFD", word.lower())
    w = "".join(c for c in w if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", w)


def toks(text):
    text = re.sub(r"[\[(*][^\])*]*[\])*]", " ", text)  # [Musica], (risas)
    return [t for t in (norm(x) for x in re.split(r"[\s'’\-]+", text)) if t]


def parse_srt_time(s):
    m = TIME_RE.match(s.strip())
    if not m:
        die(f"timecode SRT invalido: '{s.strip()}'")
    h, mi, se, fr = (int(m.group(i)) for i in range(1, 5))
    return h * 3600 + mi * 60 + se + fr / 1000.0


def load_segments(path):
    """-> lista de dicts {start, end, text}."""
    if not os.path.isfile(path):
        die(f"no existe el archivo de segmentos: {path}")
    if path.lower().endswith(".srt"):
        segs = []
        block = []
        with open(path, encoding="utf-8-sig") as fh:
            content = fh.read().replace("\r\n", "\n") + "\n\n"
        for line in content.split("\n"):
            if line.strip():
                block.append(line)
                continue
            if block:
                times = next((b for b in block if "-->" in b), None)
                if times:
                    a, b = times.split("-->")
                    text = " ".join(block[block.index(times) + 1:]).strip()
                    segs.append({"start": parse_srt_time(a),
                                 "end": parse_srt_time(b), "text": text})
                block = []
        if not segs:
            die(f"no se encontraron cues en {path}")
        return segs
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:
        die(f"{path} no es JSON válido (línea {exc.lineno}, columna {exc.colno}): {exc.msg}")
    items = data["segments"] if isinstance(data, dict) and "segments" in data else data
    segs = []
    for i, it in enumerate(items):
        try:
            s, e = float(it["start"]), float(it["end"])
            t = str(it.get("text", "")).strip()
        except (KeyError, TypeError, ValueError):
            die(f"segmento {i}: se esperaba {{start, end, text}}")
        if e <= s:
            die(f"segmento {i}: end ({e}) debe ser mayor que start ({s})")
        if t:
            segs.append({"start": s, "end": e, "text": t})
    if not segs:
        die(f"no se encontraron segmentos en {path}")
    return sorted(segs, key=lambda x: x["start"])


def group_islands(segs, pausa):
    """Agrupa segmentos contiguos en islas de sonido: un hueco > pausa
    abre una isla nueva."""
    islands, cur = [], []
    for sg in segs:
        if cur and sg["start"] - cur[-1]["end"] > pausa:
            islands.append(cur)
            cur = []
        cur.append(sg)
    if cur:
        islands.append(cur)
    out = []
    for isl in islands:
        out.append({
            "start": isl[0]["start"],
            "end": isl[-1]["end"],
            "text": " ".join(s["text"] for s in isl),
            "segments": isl,
            "tokens": toks(" ".join(s["text"] for s in isl)),
        })
    return out


def strip_leadin(t, lead):
    k = 0
    while k < len(t) - 1 and t[k] in lead:
        k += 1
    return t[k:]


def skip_links(t, links):
    k = 0
    while k < min(2, len(t) - 1) and t[k] in links:
        k += 1
    return t[k:]


def starts_like(abandoned, rest):
    """Cuanto de `abandoned` (en letras) es el COMIENZO de `rest` (0-1).
    En letras, no en palabras: el ASR escribe distinto la misma frase.
    Ambas deben empezar juntas (primera letra alineada)."""
    a, s = "".join(abandoned), "".join(rest)
    if len(a) < 2 or len(s) < len(a):
        return 0.0
    best = 0.0
    for k in range(-2, 3):
        m = difflib.SequenceMatcher(None, a, s[:max(1, len(a) + k)], autojunk=False)
        b0 = m.get_matching_blocks()[0]
        if b0.a == 0 and b0.b == 0 and b0.size >= 1:
            best = max(best, m.ratio())
    return best


def is_start_of(abandoned, rest, run=1, fuzzy=0.74, lead=frozenset()):
    # 0.74: medido en material real por el repo origen -- los false starts
    # verdaderos dan 0.75-1.00; una frase que solo continua con un inicio
    # parecido da ~0.71. En corridas de varias islas se exige ademas que las
    # primeras 8 letras coincidan: un FINAL compartido no es un comienzo.
    a, r = strip_leadin(abandoned, lead), strip_leadin(rest, lead)
    if run > 1:
        ha, hr = "".join(a)[:8], "".join(r)[:8]
        if difflib.SequenceMatcher(None, ha, hr[:len(ha)], autojunk=False).ratio() < 0.6:
            return False
    return starts_like(a, r) >= fuzzy


def restarts(ti, tj, adjacent=False, links=frozenset(), lead=frozenset()):
    """tj vuelve a empezar la frase de ti; el final puede diferir
    ("git add sirve para elegir..." y luego "git add sirve para agregar..."):
    las primeras 12 letras (>= 2 palabras) coinciden a >= 0.85. Entre islas
    vecinas tambien: las 3 primeras palabras coinciden (nexos aparte), o ti
    se repite entera dentro de las primeras palabras de tj."""
    ti, tj = strip_leadin(ti, lead), strip_leadin(tj, lead)
    if not ti or not tj:
        return False
    if adjacent:
        a_, b_ = skip_links(ti, links), skip_links(tj, links)
        if len(a_) >= 4 and a_[:4] == b_[:4] and len("".join(a_[:4])) >= 9:
            return True
        n = len(ti)
        if n >= 2 and len("".join(ti)) >= 6 and any(tj[k:k + n] == ti for k in range(1, 4)):
            return True
    if ti[0][0] != tj[0][0]:
        return False
    o, k = "", 0
    while k < len(ti) and (len(o) < 12 or k < 2):
        o += ti[k]
        k += 1
    if len(o) < 12 or k < 2:
        return False
    s = "".join(tj)[:len(o)]
    return len(s) == len(o) and difflib.SequenceMatcher(None, o, s, autojunk=False).ratio() >= 0.85


def sentence_done(text):
    return text.rstrip(' "»)').endswith((".", "!", "?", "…", ":", ","))


def false_starts(islands, gap=10.0, span=6, fuzzy=0.74, links=frozenset(),
                lead=frozenset()):
    """Devuelve (drop, why, reviews). drop: indices de islas que son false
    starts -- para cada i, la corrida mas corta i..j-1 cuyo texto es el
    comienzo de lo que sigue. La ULTIMA toma queda. reviews: casos con
    similitud cercana al umbral (ambiguos) para revision humana."""
    drop, why, reviews, seen_rev = set(), {}, [], set()
    i = 0
    while i < len(islands):
        best_j, best_s = None, 0.0
        for j in range(i + 1, min(i + 1 + span, len(islands))):
            if islands[j]["start"] - islands[j - 1]["end"] > gap:
                break
            ab = [t for k in range(i, j) for t in islands[k]["tokens"]]
            nxt = [t for k in range(j, min(j + span, len(islands)))
                   for t in islands[k]["tokens"]]
            if not ab or not nxt:
                continue
            if j - i <= 3 and restarts(islands[i]["tokens"], islands[j]["tokens"],
                                      adjacent=(j == i + 1), links=links, lead=lead):
                best_j, best_s = j, 1.0
                break
            s = starts_like(strip_leadin(ab, lead), strip_leadin(nxt, lead))
            run_ok = True
            if j - i > 1:
                ha = "".join(strip_leadin(ab, lead))[:8]
                hr = "".join(strip_leadin(nxt, lead))[:8]
                run_ok = (difflib.SequenceMatcher(None, ha, hr[:len(ha)],
                                                 autojunk=False).ratio() >= 0.6)
            if run_ok and s >= fuzzy:
                best_j, best_s = j, s
                break
            if run_ok and s > best_s:
                best_j, best_s = j, s
        if best_j is None or best_s < fuzzy:
            if (best_j is not None and best_s >= fuzzy - 0.12
                    and i not in seen_rev):
                reviews.append({
                    "at": round(islands[i]["start"], 3),
                    "note": (f"posible false start (similitud {best_s:.2f}, "
                             f"umbral {fuzzy}): «{islands[i]['text'][:60]}» -- "
                             f"revisar en {islands[i]['start']:.1f}s"),
                })
                seen_rev.add(i)
            i += 1
            continue
        j = best_j
        ab_letters = "".join(t for k in range(i, j) for t in islands[k]["tokens"])
        glued = (i > 0 and islands[i]["start"] - islands[i - 1]["end"] < 0.6
                 and not sentence_done(islands[i - 1]["text"]))
        if len(ab_letters) <= 4 and glued:
            # una palabra corta pegada a una frase sin terminar: no alcanza
            i += 1
            continue
        for k in range(i, j):
            drop.add(k)
            why[k] = (f"false start: se repite en {islands[j]['start']:.2f}s "
                      f"(«{islands[j]['text'][:60]}»)")
        i = j
    return drop, why, reviews


def subtract(spans, cuts):
    """Resta intervalos de corte de los intervalos base."""
    out = []
    for a, b in sorted(spans):
        cur = [(a, b)]
        for ca, cb in sorted(cuts):
            nxt = []
            for x, y in cur:
                if cb <= x or ca >= y:
                    nxt.append((x, y))
                    continue
                if ca > x:
                    nxt.append((x, ca))
                if cb < y:
                    nxt.append((cb, y))
            cur = nxt
        out.extend(cur)
    return [(round(a, 3), round(b, 3)) for a, b in out if b - a > 0.001]


def merge(spans):
    spans, out = sorted(spans), []
    for a, b in spans:
        if out and a <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="JSON con segmentos [{start, end, text}] o archivo SRT")
    ap.add_argument("-o", "--output", help="JSON de salida (default: <input>_retakes.json)")
    ap.add_argument("--idioma", choices=["es", "en", "auto"], default="auto",
                    help="idioma de las listas de muletillas/lead-ins (default auto: ambas)")
    ap.add_argument("--pausa", type=float, default=0.5,
                    help="un hueco mayor que esto (s) separa dos islas de sonido (default 0.5)")
    ap.add_argument("--margen", type=float, default=0.3,
                    help="los cortes se expanden estos segundos a cada lado para no rozar "
                         "palabras (default 0.3)")
    ap.add_argument("--fuzzy-threshold", type=float, default=0.74,
                    help="similitud minima (0-1) para declarar false start (default 0.74)")
    ap.add_argument("--span", type=int, default=6,
                    help="maximo de islas que puede durar una toma abandonada (default 6)")
    ap.add_argument("--keep-fillers", action="store_true",
                    help="conserva las islas que son solo muletillas (default: se marcan para corte)")
    ap.add_argument("--edl", help="guarda los rangos a conservar (una linea START-END por linea)")
    ap.add_argument("--dry-run", action="store_true",
                    help="muestra el plan sin escribir archivos")
    ap.add_argument("--json", action="store_true",
                    help="imprime el plan completo como JSON en stdout")
    args = ap.parse_args()

    if args.idioma == "auto":
        fill = FILLERS["es"] | FILLERS["en"]
        lead = LEADINS["es"] | LEADINS["en"]
        links = LINKS["es"] | LINKS["en"]
    else:
        fill, lead, links = FILLERS[args.idioma], LEADINS[args.idioma], LINKS[args.idioma]

    segs = load_segments(args.input)
    seg_toks = [toks(s["text"]) for s in segs]
    drops, reviews, trims = [], [], []

    # 1. segmentos que son solo muletillas (su propia isla de "um"/"eh")
    filler_idx = {i for i, t in enumerate(seg_toks) if t and all(x in fill for x in t)}
    for i in sorted(filler_idx):
        if not args.keep_fillers:
            drops.append({
                "start": segs[i]["start"], "end": segs[i]["end"],
                "kind": "filler",
                "reason": "segmento de solo muletillas",
                "text": segs[i]["text"][:80],
            })
    rest = [s for i, s in enumerate(segs) if i not in filler_idx]
    islands = group_islands(rest, args.pausa)
    n_filler = len(drops)
    info(f"{len(segs)} segmentos -> {len(islands)} islas de sonido "
         f"(pausas > {args.pausa}s, {n_filler} segmento(s) de muletillas)")

    # 2. false starts sobre las islas que quedan
    drop_rel, why, rev = false_starts(islands, fuzzy=args.fuzzy_threshold,
                                     span=args.span, links=links, lead=lead)
    reviews.extend(rev)
    dropped_seg_idx = set(filler_idx)
    for r in sorted(drop_rel):
        isl = islands[r]
        drops.append({
            "start": isl["start"], "end": isl["end"],
            "kind": "retake",
            "reason": why[r],
            "text": isl["text"][:80],
        })
        dropped_seg_idx.update(i for i, s in enumerate(segs)
                               if isl["start"] <= s["start"] and s["end"] <= isl["end"])
    # 3. muletillas al inicio de islas conservadas (sugerencia de recorte manual:
    #    sin tiempos por palabra no se puede cortar el audio a ciegas)
    seg_index = {id(s): i for i, s in enumerate(segs)}
    for isl in islands:
        idx = [seg_index[id(s)] for s in isl["segments"]]
        if all(i in dropped_seg_idx for i in idx):
            continue  # isla cortada: no hay nada que sugerir
        n = 0
        for t in isl["tokens"]:
            if t in fill or t in lead:
                n += 1
            else:
                break
        if n:
            trims.append({
                "at": round(isl["start"], 3),
                "note": (f"recortar {n} muletilla(s) al inicio: "
                         f"«{' '.join(isl['tokens'][:n])}» -- revisar en {isl['start']:.1f}s"),
            })

    # cortes expandidos con margen; los keeps son el complemento
    cuts = merge([(max(0.0, d["start"] - args.margen), d["end"] + args.margen)
                  for d in drops])
    for d in drops:
        d["start"], d["end"] = round(d["start"], 3), round(d["end"], 3)
    base = [(s["start"], s["end"]) for s in segs]
    keeps = subtract(base, cuts)

    plan = {
        "input": args.input,
        "islas": len(islands),
        "segmentos": len(segs),
        "keeps": [{"start": a, "end": b} for a, b in keeps],
        "drops": drops,
        "reviews": reviews,
        "trims": trims,
        "params": {"pausa": args.pausa, "margen": args.margen,
                   "fuzzy_threshold": args.fuzzy_threshold, "idioma": args.idioma},
    }

    if args.json or args.dry_run:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    if args.dry_run:
        info("dry-run: no se escribio ningun archivo")
        return 0

    out = args.output or os.path.splitext(args.input)[0] + "_retakes.json"
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(plan, fh, ensure_ascii=False, indent=2)
    if args.edl:
        with open(args.edl, "w", encoding="utf-8") as fh:
            for k in keeps:
                fh.write(f"{k[0]:.3f}-{k[1]:.3f}\n")
        info(f"escribi {args.edl} ({len(keeps)} rangos a conservar)")
    info(f"{len(drops)} islas marcadas para corte "
         f"({sum(1 for d in drops if d['kind'] == 'retake')} retakes, "
         f"{sum(1 for d in drops if d['kind'] == 'filler')} fillers), "
         f"{len(reviews)} para revisar, {len(trims)} recortes sugeridos")
    print(f"OK {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
