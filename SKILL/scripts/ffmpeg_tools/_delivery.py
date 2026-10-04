#!/usr/bin/env python3
"""Tabla canonica de destinos de entrega (modulo interno, no es herramienta).

Una sola tabla que leen las herramientas de delivery: el spec de compliance
(duracion, aspecto, codecs, loudness), los ajustes de encode (preset) y la
zona de la pantalla que tapa la UI propia de cada app (fraccion por borde:
nada legible va ahi).

Patron tomado de kajisho5/ffmpeg-skill (MIT), scripts/_platforms.py: antes
el mismo destino se describia en tres lugares distintos (spec en un lado,
encode en otro, safe zones en ninguno) y un export pasaba todos los checks
con los captions bajo la barra de descripcion. Aqui la tabla es UNA.

Datos: los valores de Shorts/TikTok/Reels y loudness son los verificados de
EditorIA (checklist-qa.md); los destinos que EditorIA no tenia especificados
(x, linkedin, facebook, youtube, podcast, broadcast) se adoptan de
ffmpeg-skill, medidos de la guia de diseno publicada de cada plataforma.
Las safe zones son deliberadamente generosas: un caption 2% mas alto se lee,
uno bajo el boton de compartir no.
"""
from typing import Any, Dict, List, Optional

_SAFE_5 = {"top": 0.05, "bottom": 0.05, "left": 0.05, "right": 0.05}
_NO_SAFE = {"top": 0.0, "bottom": 0.0, "left": 0.0, "right": 0.0}

PLATFORMS: Dict[str, Dict[str, Any]] = {
    "tiktok": {
        "title": "TikTok",
        "frame": {"w": 1080, "h": 1920, "aspect": "9:16"},
        "fps": 30,
        "spec": {"max_duration": 600, "aspects": ["9:16", "1:1"],
                 "min_height": 1080, "fps_max": 60,
                 "codecs": ["h264"], "max_bytes": 4 * 1024 ** 3,
                 "lufs": -14, "lufs_tol": 2.0, "tp": -1.0, "sdr_only": True},
        "safe": {"top": 0.10, "bottom": 0.22, "left": 0.05, "right": 0.14},
        "preset": {"vcodec": "libx264", "preset": "medium", "crf": 18,
                   "pix_fmt": "yuv420p", "acodec": "aac", "ab": "128k",
                   "ar": 44100, "movflags": "+faststart"},
    },
    "reels": {
        "title": "Instagram Reels",
        "frame": {"w": 1080, "h": 1920, "aspect": "9:16"},
        "fps": 30,
        "spec": {"max_duration": 180, "aspects": ["9:16", "4:5", "1:1"],
                 "min_height": 1080, "fps_max": 60,
                 "codecs": ["h264"], "max_bytes": 4 * 1024 ** 3,
                 "lufs": -14, "lufs_tol": 2.0, "tp": -1.0, "sdr_only": True},
        "safe": {"top": 0.08, "bottom": 0.20, "left": 0.05, "right": 0.12},
        "preset": {"vcodec": "libx264", "preset": "medium", "crf": 20,
                   "pix_fmt": "yuv420p", "acodec": "aac", "ab": "128k",
                   "ar": 44100, "movflags": "+faststart"},
    },
    "shorts": {
        "title": "YouTube Shorts",
        "frame": {"w": 1080, "h": 1920, "aspect": "9:16"},
        "fps": 30,
        "spec": {"max_duration": 180, "aspects": ["9:16", "1:1"],
                 "min_height": 1080, "fps_max": 60,
                 "codecs": ["h264"], "max_bytes": 256 * 1024 ** 3,
                 "lufs": -14, "lufs_tol": 2.0, "tp": -1.0, "sdr_only": False},
        "safe": {"top": 0.06, "bottom": 0.18, "left": 0.05, "right": 0.12},
        "preset": {"vcodec": "libx264", "preset": "medium", "crf": 20,
                   "pix_fmt": "yuv420p", "acodec": "aac", "ab": "192k",
                   "ar": 48000, "movflags": "+faststart"},
    },
    "youtube": {
        "title": "YouTube",
        "frame": {"w": 1920, "h": 1080, "aspect": "16:9"},
        "fps": None,
        "spec": {"max_duration": 12 * 3600,
                 "aspects": ["16:9", "9:16", "1:1", "4:3"],
                 "min_height": 720, "fps_max": 60,
                 "codecs": ["h264", "hevc", "av1", "vp9"],
                 "max_bytes": 256 * 1024 ** 3,
                 "lufs": -14, "lufs_tol": 2.0, "tp": -1.0, "sdr_only": False},
        "safe": _SAFE_5,
        "preset": {"vcodec": "libx264", "preset": "medium", "crf": 20,
                   "pix_fmt": "yuv420p", "acodec": "aac", "ab": "192k",
                   "ar": 48000, "movflags": "+faststart"},
    },
    "x": {
        "title": "X (Twitter)",
        "frame": {"w": 1280, "h": 720, "aspect": "16:9"},
        "fps": 30,
        "spec": {"max_duration": 140, "aspects": ["16:9", "1:1", "9:16"],
                 "min_height": 720, "fps_max": 60,
                 "codecs": ["h264"], "max_bytes": 512 * 1024 ** 2,
                 "lufs": -14, "lufs_tol": 3.0, "tp": -1.0, "sdr_only": True},
        "safe": _SAFE_5,
        "preset": {"vcodec": "libx264", "preset": "medium", "crf": 21,
                   "pix_fmt": "yuv420p", "acodec": "aac", "ab": "128k",
                   "ar": 44100, "movflags": "+faststart"},
    },
    "linkedin": {
        "title": "LinkedIn",
        "frame": {"w": 1080, "h": 1080, "aspect": "1:1"},
        "fps": 30,
        "spec": {"max_duration": 600,
                 "aspects": ["16:9", "1:1", "9:16", "4:5"],
                 "min_height": 720, "fps_max": 60,
                 "codecs": ["h264"], "max_bytes": 5 * 1024 ** 3,
                 "lufs": -14, "lufs_tol": 3.0, "tp": -1.0, "sdr_only": True},
        "safe": _SAFE_5,
        "preset": {"vcodec": "libx264", "preset": "medium", "crf": 21,
                   "pix_fmt": "yuv420p", "acodec": "aac", "ab": "128k",
                   "ar": 44100, "movflags": "+faststart"},
    },
    "facebook": {
        "title": "Facebook",
        "frame": {"w": 1920, "h": 1080, "aspect": "16:9"},
        "fps": 30,
        "spec": {"max_duration": 240 * 60,
                 "aspects": ["16:9", "1:1", "9:16", "4:5"],
                 "min_height": 720, "fps_max": 60,
                 "codecs": ["h264", "hevc"], "max_bytes": 4 * 1024 ** 3,
                 "lufs": -14, "lufs_tol": 3.0, "tp": -1.0, "sdr_only": True},
        "safe": _SAFE_5,
        "preset": {"vcodec": "libx264", "preset": "medium", "crf": 21,
                   "pix_fmt": "yuv420p", "acodec": "aac", "ab": "128k",
                   "ar": 44100, "movflags": "+faststart"},
    },
    "podcast": {
        "title": "Podcast (audio)",
        "frame": None,
        "fps": None,
        "spec": {"max_duration": None, "aspects": None, "min_height": 0,
                 "fps_max": None, "codecs": None, "max_bytes": None,
                 "lufs": -16, "lufs_tol": 1.0, "tp": -1.0, "sdr_only": False},
        "safe": _NO_SAFE,
        "preset": {"acodec": "aac", "ab": "128k", "ar": 44100},
    },
    "broadcast": {
        "title": "Broadcast (EBU R128)",
        "frame": {"w": 1920, "h": 1080, "aspect": "16:9"},
        "fps": None,
        "spec": {"max_duration": None, "aspects": ["16:9"],
                 "min_height": 1080, "fps_max": 60,
                 "codecs": ["h264", "hevc", "prores", "dnxhd"],
                 "max_bytes": None,
                 "lufs": -23, "lufs_tol": 1.0, "tp": -1.0, "sdr_only": False},
        "safe": _SAFE_5,
        "preset": {"vcodec": "libx264", "preset": "medium", "crf": 18,
                   "pix_fmt": "yuv420p", "acodec": "aac", "ab": "192k",
                   "ar": 48000, "movflags": "+faststart"},
    },
}

PLATFORM_NAMES: List[str] = sorted(PLATFORMS)
ALIASES: Dict[str, str] = {"youtube-shorts": "shorts", "yt-shorts": "shorts",
                           "yt": "youtube", "instagram": "reels", "ig": "reels",
                           "twitter": "x", "fb": "facebook"}
# Destinos contra los que se verifica un entregable (el check de cada uno).
PLATFORM_CHOICES: List[str] = sorted(set(PLATFORM_NAMES) | set(ALIASES))


def resolve(name: Optional[str]) -> Optional[str]:
    """Acepta las formas en que la gente escribe un destino ('ig' -> 'reels')."""
    if not name:
        return None
    key = str(name).strip().lower()
    return ALIASES.get(key, key)


def spec_of(name: str) -> Dict[str, Any]:
    return dict(PLATFORMS[resolve(name)]["spec"])


def safe_of(name: str) -> Dict[str, float]:
    return dict(PLATFORMS[resolve(name)]["safe"])


def safe_margins_px(name: str, width: int, height: int) -> Dict[str, int]:
    """La zona segura en pixeles para un frame de este tamano, por borde."""
    s = safe_of(name)
    return {"top": int(round(s["top"] * height)),
            "bottom": int(round(s["bottom"] * height)),
            "left": int(round(s["left"] * width)),
            "right": int(round(s["right"] * width))}


def preset_of(name: str) -> Dict[str, Any]:
    return dict(PLATFORMS[resolve(name)]["preset"])


def title_of(name: str) -> str:
    return PLATFORMS[resolve(name)]["title"]
