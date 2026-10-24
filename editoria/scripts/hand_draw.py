#!/usr/bin/env python3
"""Trazos a mano: suavizado, segmentos y viewport para overlays.

Porta (MIT) la lógica de dominio pura de HandDraw
(https://github.com/davbachman/HandDraw) al stack de EditorIA: sin MediaPipe,
sin UI y sin CSS. Sirve para:

  - limpiar polilíneas temblorosas antes de pintar (EMA + snap);
  - pintar un JSON de trazos a un PNG con alfa (overlay para montaje);
  - mapear viewport↔mundo y histéresis pinch/puño si se reconstruye un
    lienzo interactivo en Remotion/HyperFrames/canvas.

Uso:
  python scripts/hand_draw.py suavizar puntos.json -o limpio.json
  python scripts/hand_draw.py pintar trazos.json -o overlay.png --ancho 1080 --alto 1920
  python scripts/hand_draw.py pintar trazos.json -o overlay.png --suavizar

Canónico: references/hand-draw.md
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

Point = Tuple[float, float]
Rect = Dict[str, float]
Size = Dict[str, float]

# Suavizado (HandDraw pointerSmoothing): alpha bajo = más inercia; snap = salto
# brusco que no se debe promediar (cambio de mano / reaparición del tracking).
SUAVIZADO_DEFECTO = {"alpha": 0.26, "snap": 170.0}
SUAVIZADO_DIBUJO = {"alpha": 0.42, "snap": 170.0}

# Brochas por defecto (colores neutros; la marca los sustituye con --color).
BROCHA_LAPIZ = {"ancho": 6.0, "color": "#101827", "borrar": False}
BROCHA_BORRADOR = {"ancho": 34.0, "color": "#000000", "borrar": True}

# Histéresis de gestos (HandDraw gesture): start entra, end sale.
PINCH_INICIO, PINCH_FIN = 0.24, 0.34
PUNO_INICIO, PUNO_FIN = 1.18, 1.38

ZOOM_MIN, ZOOM_MAX = 0.25, 6.0


# ---------------------------------------------------------------------------
# Suavizado de puntero / polilínea
# ---------------------------------------------------------------------------

def suavizar_punto(
    anterior: Optional[Point],
    crudo: Point,
    alpha: float = SUAVIZADO_DEFECTO["alpha"],
    snap: float = SUAVIZADO_DEFECTO["snap"],
) -> Point:
    """EMA con snap: si el salto supera `snap`, toma el punto crudo."""
    if anterior is None:
        return (float(crudo[0]), float(crudo[1]))
    ax, ay = float(anterior[0]), float(anterior[1])
    rx, ry = float(crudo[0]), float(crudo[1])
    if math.hypot(rx - ax, ry - ay) > snap:
        return (rx, ry)
    return (ax + (rx - ax) * alpha, ay + (ry - ay) * alpha)


def suavizar_puntos(
    puntos: Sequence[Point],
    alpha: float = SUAVIZADO_DEFECTO["alpha"],
    snap: float = SUAVIZADO_DEFECTO["snap"],
) -> List[Point]:
    """Aplica `suavizar_punto` en secuencia a una polilínea."""
    out: List[Point] = []
    prev: Optional[Point] = None
    for p in puntos:
        prev = suavizar_punto(prev, p, alpha=alpha, snap=snap)
        out.append(prev)
    return out


# ---------------------------------------------------------------------------
# Viewport (mundo ↔ pantalla)
# ---------------------------------------------------------------------------

def _zoom_seguro(zoom: float) -> float:
    return zoom if math.isfinite(zoom) and zoom > 0 else 1.0


def punto_viewport_a_mundo(
    punto: Point,
    canvas: Rect,
    offset: Point = (0.0, 0.0),
    zoom: float = 1.0,
) -> Point:
    z = _zoom_seguro(zoom)
    return (
        round((punto[0] - canvas["left"]) / z + offset[0]),
        round((punto[1] - canvas["top"]) / z + offset[1]),
    )


def punto_en_rect(punto: Point, rect: Rect) -> bool:
    return (
        rect["left"] <= punto[0] <= rect["left"] + rect["width"]
        and rect["top"] <= punto[1] <= rect["top"] + rect["height"]
    )


def _tamano_visible(viewport: Size, zoom: float) -> Size:
    z = _zoom_seguro(zoom)
    return {"width": viewport["width"] / z, "height": viewport["height"] / z}


def clamp_offset_viewport(
    offset: Point,
    viewport: Size,
    mundo: Size,
    zoom: float = 1.0,
) -> Point:
    vis = _tamano_visible(viewport, zoom)
    return (
        round(min(max(offset[0], 0), max(0, mundo["width"] - vis["width"]))),
        round(min(max(offset[1], 0), max(0, mundo["height"] - vis["height"]))),
    )


def pan_offset_viewport(
    offset: Point,
    delta: Point,
    viewport: Size,
    mundo: Size,
    zoom: float = 1.0,
) -> Point:
    z = _zoom_seguro(zoom)
    return clamp_offset_viewport(
        (offset[0] - delta[0] / z, offset[1] - delta[1] / z),
        viewport,
        mundo,
        zoom,
    )


def centrar_offset_viewport(mundo: Size, viewport: Size, zoom: float = 1.0) -> Point:
    vis = _tamano_visible(viewport, zoom)
    return clamp_offset_viewport(
        ((mundo["width"] - vis["width"]) / 2, (mundo["height"] - vis["height"]) / 2),
        viewport,
        mundo,
        zoom,
    )


def zoom_en_punto(
    offset: Point,
    zoom: float,
    siguiente_zoom: float,
    foco: Point,
    canvas: Rect,
    mundo: Size,
    zmin: float = ZOOM_MIN,
    zmax: float = ZOOM_MAX,
) -> Tuple[Point, float]:
    z = min(zmax, max(zmin, siguiente_zoom))
    local = (foco[0] - canvas["left"], foco[1] - canvas["top"])
    mundo_foco = (
        offset[0] + local[0] / _zoom_seguro(zoom),
        offset[1] + local[1] / _zoom_seguro(zoom),
    )
    nuevo = (
        mundo_foco[0] - local[0] / _zoom_seguro(z),
        mundo_foco[1] - local[1] / _zoom_seguro(z),
    )
    viewport = {"width": canvas["width"], "height": canvas["height"]}
    return clamp_offset_viewport(nuevo, viewport, mundo, z), z


# ---------------------------------------------------------------------------
# Herramienta activa → segmentos de trazo
# ---------------------------------------------------------------------------

def brocha(kind: str = "pencil", color: Optional[str] = None, ancho: Optional[float] = None) -> Dict[str, Any]:
    if kind == "eraser":
        b = dict(BROCHA_BORRADOR)
    else:
        b = dict(BROCHA_LAPIZ)
        if color:
            b["color"] = color
    if ancho is not None:
        b["ancho"] = float(ancho)
    return b


def avanzar_herramienta(
    last: Optional[Point],
    viewport_point: Point,
    canvas: Rect,
    offset: Point = (0.0, 0.0),
    zoom: float = 1.0,
    kind: str = "pencil",
    color: Optional[str] = None,
    ancho: Optional[float] = None,
) -> Tuple[Optional[Point], Optional[Dict[str, Any]]]:
    """Devuelve (nuevo_last, segmento|None). Fuera del canvas limpia el last."""
    if not punto_en_rect(viewport_point, canvas):
        return None, None
    mundo = punto_viewport_a_mundo(viewport_point, canvas, offset, zoom)
    origen = last if last is not None else mundo
    seg = {"kind": kind, "from": origen, "to": mundo, **brocha(kind, color, ancho)}
    return mundo, seg


# ---------------------------------------------------------------------------
# Gestos (histéresis pura; sin MediaPipe)
# ---------------------------------------------------------------------------

def _dist3(a: Dict[str, float], b: Dict[str, float]) -> float:
    dz = float(a.get("z", 0) or 0) - float(b.get("z", 0) or 0)
    return math.hypot(float(a["x"]) - float(b["x"]), float(a["y"]) - float(b["y"]), dz)


def ratio_pinch(landmarks: Sequence[Dict[str, float]]) -> float:
    """Distancia pulgar–índice normalizada por la escala de la palma."""
    if len(landmarks) < 9:
        return float("inf")
    wrist, index_base, thumb_tip, index_tip = landmarks[0], landmarks[5], landmarks[4], landmarks[8]
    palm = _dist3(wrist, index_base)
    if palm == 0:
        return float("inf")
    return _dist3(thumb_tip, index_tip) / palm


def ratio_extension_dedos(landmarks: Sequence[Dict[str, float]]) -> float:
    if len(landmarks) < 21:
        return float("inf")
    wrist = landmarks[0]
    pares = ((5, 8), (9, 12), (13, 16), (17, 20))
    ratios = []
    for base, tip in pares:
        base_d = _dist3(wrist, landmarks[base])
        if base_d == 0:
            continue
        ratios.append(_dist3(wrist, landmarks[tip]) / base_d)
    if not ratios:
        return float("inf")
    return sum(ratios) / len(ratios)


def siguiente_pinch(era_pinch: bool, ratio: float, inicio: float = PINCH_INICIO, fin: float = PINCH_FIN) -> bool:
    return ratio < (fin if era_pinch else inicio)


def siguiente_puno(era_puno: bool, ratio_ext: float, inicio: float = PUNO_INICIO, fin: float = PUNO_FIN) -> bool:
    return ratio_ext < (fin if era_puno else inicio)


# ---------------------------------------------------------------------------
# Pintado a PNG (overlay con alfa)
# ---------------------------------------------------------------------------

def _parse_color(hex_color: str) -> Tuple[int, int, int]:
    c = hex_color.strip().lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    if len(c) != 6:
        raise ValueError(f"color inválido: {hex_color!r}")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def _as_points(raw: Iterable[Any]) -> List[Point]:
    pts: List[Point] = []
    for item in raw:
        if isinstance(item, dict):
            pts.append((float(item["x"]), float(item["y"])))
        else:
            pts.append((float(item[0]), float(item[1])))
    return pts


def pintar_trazos(
    trazos: Sequence[Dict[str, Any]],
    ancho: int,
    alto: int,
    suavizar: bool = False,
    alpha_suave: float = SUAVIZADO_DIBUJO["alpha"],
    snap_suave: float = SUAVIZADO_DIBUJO["snap"],
):
    """Pinta trazos sobre RGBA transparente. Requiere Pillow."""
    try:
        from PIL import Image, ImageDraw
    except ImportError as exc:
        raise SystemExit(
            "ERROR: falta Pillow. Instalar con: pip install pillow"
        ) from exc

    img = Image.new("RGBA", (ancho, alto), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    for trazo in trazos:
        pts = _as_points(trazo.get("points") or trazo.get("puntos") or [])
        if len(pts) < 1:
            continue
        if suavizar and len(pts) > 1:
            pts = suavizar_puntos(pts, alpha=alpha_suave, snap=snap_suave)
        kind = trazo.get("kind") or trazo.get("tipo") or "pencil"
        b = brocha(kind, trazo.get("color"), trazo.get("width") or trazo.get("ancho"))
        w = max(1, int(round(b["ancho"])))
        if b["borrar"]:
            # destination-out aproximado: pintar transparente sobre el trazo
            if len(pts) == 1:
                x, y = pts[0]
                draw.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2], fill=(0, 0, 0, 0))
            else:
                draw.line(pts, fill=(0, 0, 0, 0), width=w, joint="curve")
            continue
        rgb = _parse_color(b["color"])
        fill = (*rgb, 255)
        if len(pts) == 1:
            x, y = pts[0]
            draw.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2], fill=fill)
        else:
            draw.line(pts, fill=fill, width=w, joint="curve")
            # caps redondeados en extremos
            for x, y in (pts[0], pts[-1]):
                draw.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2], fill=fill)
    return img


def _cargar_json(ruta: str) -> Any:
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def _guardar_json(ruta: str, data: Any) -> None:
    padre = os.path.dirname(os.path.abspath(ruta))
    if padre:
        os.makedirs(padre, exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def cmd_suavizar(args: argparse.Namespace) -> int:
    data = _cargar_json(args.entrada)
    if isinstance(data, list):
        pts = _as_points(data)
        limpios = suavizar_puntos(pts, alpha=args.alpha, snap=args.snap)
        out: Any = [{"x": p[0], "y": p[1]} for p in limpios]
    elif isinstance(data, dict) and ("points" in data or "puntos" in data):
        key = "points" if "points" in data else "puntos"
        pts = _as_points(data[key])
        limpios = suavizar_puntos(pts, alpha=args.alpha, snap=args.snap)
        out = dict(data)
        out[key] = [{"x": p[0], "y": p[1]} for p in limpios]
    elif isinstance(data, dict) and ("strokes" in data or "trazos" in data):
        key = "strokes" if "strokes" in data else "trazos"
        out = dict(data)
        nuevos = []
        for trazo in data[key]:
            t = dict(trazo)
            pk = "points" if "points" in t else "puntos"
            pts = _as_points(t.get(pk) or [])
            limpios = suavizar_puntos(pts, alpha=args.alpha, snap=args.snap)
            t[pk] = [{"x": p[0], "y": p[1]} for p in limpios]
            nuevos.append(t)
        out[key] = nuevos
    else:
        sys.exit("ERROR: JSON esperado: lista de puntos, {points|puntos}, o {strokes|trazos}")
    destino = args.out or (os.path.splitext(args.entrada)[0] + ".suave.json")
    _guardar_json(destino, out)
    print(f"suavizado -> {destino}")
    return 0


def cmd_pintar(args: argparse.Namespace) -> int:
    data = _cargar_json(args.entrada)
    if isinstance(data, dict) and ("strokes" in data or "trazos" in data):
        trazos = data.get("strokes") or data.get("trazos")
    elif isinstance(data, list):
        trazos = data
    elif isinstance(data, dict) and ("points" in data or "puntos" in data):
        trazos = [data]
    else:
        sys.exit("ERROR: JSON esperado: {strokes|trazos}, lista de trazos, o un trazo con points")
    img = pintar_trazos(
        trazos,
        ancho=args.ancho,
        alto=args.alto,
        suavizar=args.suavizar,
        alpha_suave=args.alpha,
        snap_suave=args.snap,
    )
    destino = args.out or (os.path.splitext(args.entrada)[0] + ".png")
    padre = os.path.dirname(os.path.abspath(destino))
    if padre:
        os.makedirs(padre, exist_ok=True)
    img.save(destino)
    print(f"overlay -> {destino} ({args.ancho}x{args.alto})")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Suaviza y pinta trazos a mano (overlays con alfa) para EditorIA."
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_suave = sub.add_parser("suavizar", help="EMA + snap sobre puntos o trazos JSON")
    p_suave.add_argument("entrada", help="JSON de puntos o trazos")
    p_suave.add_argument("-o", "--out", default=None, help="salida JSON")
    p_suave.add_argument("--alpha", type=float, default=SUAVIZADO_DEFECTO["alpha"])
    p_suave.add_argument("--snap", type=float, default=SUAVIZADO_DEFECTO["snap"])
    p_suave.set_defaults(func=cmd_suavizar)

    p_pintar = sub.add_parser("pintar", help="pinta trazos JSON a PNG con alfa")
    p_pintar.add_argument("entrada", help="JSON de trazos")
    p_pintar.add_argument("-o", "--out", default=None, help="PNG de salida")
    p_pintar.add_argument("--ancho", type=int, default=1080)
    p_pintar.add_argument("--alto", type=int, default=1920)
    p_pintar.add_argument("--suavizar", action="store_true", help="suaviza cada trazo antes de pintar")
    p_pintar.add_argument("--alpha", type=float, default=SUAVIZADO_DIBUJO["alpha"])
    p_pintar.add_argument("--snap", type=float, default=SUAVIZADO_DIBUJO["snap"])
    p_pintar.set_defaults(func=cmd_pintar)

    args = ap.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
