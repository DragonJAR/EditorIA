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
    # La mono del motor (etiquetas, datos, medidas). Antes no había mono
    # empaquetada y en macOS salía Courier New: un trazo tan fino que la
    # etiqueta se leía a ~3:1 aunque su color pasara AA. Dos pesos:
    # assets/fonts/IBMPlexMono-Regular.ttf y assets/fonts/IBMPlexMono-SemiBold.ttf
    # (el 700 que pide el motor sale del SemiBold: `variante_de_peso`).
    "ibm plex mono": "IBMPlexMono-Regular.ttf",
    "plex mono": "IBMPlexMono-Regular.ttf",
}

# Pesos de una familia ESTÁTICA (un archivo por peso, "<familia>-<Peso>.ttf").
# Una variable resuelve el peso con su eje wght; una estática solo lo respeta
# si se elige el archivo hermano. Sin esto, pedir 700 a una estática dibujaba
# el 400 en silencio.
PESOS_ESTATICOS = {"Thin": 100, "ExtraLight": 200, "Light": 300, "Regular": 400,
                   "Medium": 500, "SemiBold": 600, "Bold": 700, "ExtraBold": 800,
                   "Black": 900}


def variante_de_peso(ruta: Optional[str], peso: int) -> Optional[str]:
    """El archivo hermano de `ruta` más cercano al `peso` pedido.

    Solo para familias estáticas nombradas "<familia>-<Peso>.<ext>" (la
    convención de casi todas las OFL). Una variable o un archivo sin peso
    en el nombre se devuelve igual. A igual distancia gana el más pesado
    (pedir 700 con 600 y 800 a mano da 800: el texto pidió énfasis)."""
    if not ruta:
        return ruta
    p = Path(ruta)
    familia, _, actual = p.stem.rpartition("-")
    if not familia or actual not in PESOS_ESTATICOS:
        return ruta
    hermanos = [(abs(v - peso), -v, p.with_name(f"{familia}-{n}{p.suffix}"))
                for n, v in PESOS_ESTATICOS.items()]
    for _, _, cand in sorted(hermanos, key=lambda h: (h[0], h[1])):
        if cand.exists():
            return str(cand)
    return ruta


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
    """El PRIMER nombre que exista en algún directorio.

    El orden de `nombres` es el de preferencia y manda sobre el de los
    directorios: con el bucle al revés, el primer directorio del SO
    (/System/Library/Fonts/Supplemental en macOS) imponía su candidato de
    último recurso (Courier New) aunque la preferida (Menlo) estuviera en
    el siguiente."""
    dirs = dirs_fuentes()
    for n in nombres:
        p = Path(n)
        if p.is_absolute():
            if p.suffix.lower() in (".ttf", ".ttc", ".otf") and p.exists():
                return str(p)
            continue
        for d in dirs:
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
