#!/usr/bin/env python3
"""_plataforma.py — abstracciones de sistema operativo para EditorIA.

Solo stdlib. Centraliza todo lo que cambia entre Windows, macOS y Linux:
detección del SO, directorios de fuentes, directorio temporal y resolución
de fuentes por nombre. Los scripts importan desde aquí en vez de hardcodear
rutas POSIX.
"""
import atexit
import os
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional


def sistema() -> str:
    """'Windows', 'macOS' o 'Linux'."""
    s = platform.system()
    return {"Windows": "Windows", "Darwin": "macOS", "Linux": "Linux"}.get(s, s)


def es_windows() -> bool:
    return platform.system() == "Windows"


_TMP_PROCESO = None


def dir_temp() -> str:
    """Directorio temporal PROPIO de este proceso (reemplaza '/tmp' hardcodeado).

    Un nombre FIJO en el temp del sistema se pisa cuando hay dos corridas a
    la vez: dos montajes escriben la misma lista de concat y cada ffmpeg lee
    la del otro (un video silenciosamente distinto, que es PEOR que un
    fallo), y el borrado del segundo se lleva la lista que el primero
    todavia esta leyendo. Cada proceso tiene el suyo, y se va solo al
    terminar.
    """
    global _TMP_PROCESO
    if _TMP_PROCESO is None:
        _TMP_PROCESO = tempfile.mkdtemp(prefix="editoria_")
        atexit.register(shutil.rmtree, _TMP_PROCESO, True)
    return _TMP_PROCESO


# Fuentes empaquetadas con la skill (OFL): assets/fonts/. Van primero.
FUENTES_SKILL = Path(__file__).resolve().parents[2] / "assets" / "fonts"

# Alias de familia -> archivo empaquetado (para resolver por nombre).
ALIAS_SKILL = {
    "plus jakarta sans": "PlusJakartaSans-wght.ttf",
    "jakarta": "PlusJakartaSans-wght.ttf",
    "jakarta.ttf": "PlusJakartaSans-wght.ttf",
    "montserrat": "Montserrat-wght.ttf",
    "montserrat.ttf": "Montserrat-wght.ttf",
}


def fuente_skill(nombre: str) -> Optional[str]:
    """Resuelve una familia o archivo contra las fuentes empaquetadas."""
    clave = Path(str(nombre)).name.lower()
    archivo = ALIAS_SKILL.get(clave) or ALIAS_SKILL.get(str(nombre).lower())
    if archivo and (FUENTES_SKILL / archivo).exists():
        return str(FUENTES_SKILL / archivo)
    return None


def dirs_fuentes() -> List[Path]:
    """Directorios de fuentes: primero los de la skill, luego los del SO."""
    return ([FUENTES_SKILL] if FUENTES_SKILL.exists() else []) + _dirs_fuentes_so()


def _dirs_fuentes_so() -> List[Path]:
    """Directorios de fuentes del sistema, en orden de preferencia."""
    s = platform.system()
    if s == "Windows":
        base = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
        local = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Windows" / "Fonts"
        return [p for p in (base, local) if p.exists()] or [base]
    if s == "Darwin":
        return [Path(p) for p in (
            "/System/Library/Fonts/Supplemental",
            "/System/Library/Fonts",
            "/Library/Fonts",
            str(Path.home() / "Library" / "Fonts"),
        ) if Path(p).exists()]
    # Linux y otros Unix
    return [Path(p) for p in (
        "/usr/share/fonts",
        "/usr/local/share/fonts",
        str(Path.home() / ".fonts"),
        str(Path.home() / ".local" / "share" / "fonts"),
    ) if Path(p).exists()]


# Nombres de archivo comunes por familia genérica y SO.
FUENTES_GENERICAS = {
    "sans": {
        "Windows": ["arial.ttf", "segoeui.ttf", "calibri.ttf"],
        "macOS": ["Arial.ttf", "Helvetica.ttc", "/System/Library/Fonts/Supplemental/Arial.ttf"],
        "Linux": ["DejaVuSans.ttf", "LiberationSans-Regular.ttf"],
    },
    "sans-bold": {
        "Windows": ["arialbd.ttf", "segoeuib.ttf"],
        "macOS": ["Arial Bold.ttf", "Helvetica Bold.ttf"],
        "Linux": ["DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"],
    },
    "mono": {
        "Windows": ["consola.ttf", "cour.ttf"],
        "macOS": ["Menlo.ttc", "Courier New.ttf"],
        "Linux": ["DejaVuSansMono.ttf", "LiberationMono-Regular.ttf"],
    },
}


def _buscar_en_dirs(nombres: List[str]) -> Optional[str]:
    for d in dirs_fuentes():
        for n in nombres:
            p = Path(n)
            if p.is_absolute():
                if p.suffix.lower() in (".ttf", ".ttc", ".otf") and p.exists():
                    return str(p)
                continue
            # Búsqueda recursiva: las fuentes suelen estar en subdirectorios
            # (ej. truetype/dejavu/DejaVuSans.ttf)
            for cand in d.rglob(n):
                if cand.is_file():
                    return str(cand)
    return None


def resolver_fuente(*nombres: str, generica: Optional[str] = None) -> Optional[str]:
    """Resuelve una fuente a archivo existente.

    1. Busca cada nombre en los directorios de fuentes del SO.
    2. En Linux/Unix con fontconfig, usa `fc-match` como fallback.
    3. Si se pide `generica` ('sans', 'sans-bold', 'mono'), prueba sus
       archivos típicos por SO.
    Devuelve la ruta o None si no hay coincidencia.
    """
    for n in nombres:
        hit = fuente_skill(n)
        if hit:
            return hit
        p = Path(os.path.expanduser(str(n)))
        if p.is_absolute() and p.exists():
            return str(p)
    s = sistema()
    candidatos: List[str] = list(nombres)
    if generica and generica in FUENTES_GENERICAS:
        candidatos += FUENTES_GENERICAS[generica].get(s, [])
    hit = _buscar_en_dirs(candidatos)
    if hit:
        return hit
    # Fallback fontconfig (Linux/Unix con fontconfig instalado).
    # Ojo: fc-match NUNCA falla — si el nombre no existe devuelve un fallback.
    # Se verifica que la familia coincida antes de aceptar el resultado.
    exe = shutil.which("fc-match")
    if exe:
        for nombre in nombres:
            try:
                p = subprocess.run(
                    [exe, "--format=%{file}\n%{family}\n", nombre],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    text=True, timeout=5)
                lineas = p.stdout.splitlines()
                ruta = lineas[0].strip() if len(lineas) > 0 else ""
                familia = lineas[1].strip().lower() if len(lineas) > 1 else ""
                pedido = Path(nombre).stem.lower()
                if (p.returncode == 0 and ruta and os.path.exists(ruta)
                        and (pedido in familia or familia in pedido)):
                    return ruta
            except (OSError, subprocess.TimeoutExpired):
                continue
    return None


def python_actual() -> str:
    """Intérprete Python en uso (portable; en Windows 'python3' no existe)."""
    import sys
    return sys.executable
