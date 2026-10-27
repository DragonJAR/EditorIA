#!/usr/bin/env python3
"""Tests del canal alfa de la CAPA .webm en `scripts/ffmpeg_tools/componer.py`.

MEDIDO: una capa .webm (VP9) con alfa de verdad —la etiqueta `alpha_mode=1`
y un frame central que decodifica 88 % transparente— salia con el aviso "la
capa NO lleva canal alfa" y el clip de debajo se tapaba con un RECTANGULO
NEGRO: el texto se veia sobre fondo negro en vez de desvanecido.

La causa no era la capa: el decoder NATIVO de ffmpeg descarta el alfa del
VP9 (el stream se ve como `yuv420p`), asi que el compositor (a) lo diagnostico
mal y (b) leia la capa opaca. El arreglo son dos cosas: mirar la ETIQUETA
(alpha_mode=1) y forzar `libvpx-vp9` al leer la entrada.

Estos tests comprueban las dos mitades: lo que el guard DIAGNOSTICA y lo que
la pieza sale.

Run with: python3 -m unittest discover -s SKILL/scripts/_tests
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
TOOLS = os.path.join(SCRIPTS, "ffmpeg_tools")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import componer as comp  # noqa: E402


def _fondo(destino, segundos=2, fps=24, tam="320x180"):
    """Un video de fondo con imagen (testsrc: colores, distinguibles del negro)."""
    subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", f"testsrc=duration={segundos}:size={tam}:rate={fps}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", destino],
        check=True, capture_output=True, timeout=120)
    return destino


def _capa_webm_con_alfa(destino, segundos=2, fps=24, tam="320x180"):
    """Una capa .webm (VP9) CON ALFA: un cuadro opaco en un punto del lienzo.

    La alfa de verdad se hace con `format=rgba` + `geq`: un `color=c=white@0.5`
    de lavfi NO lleva alfa (el source sale en yuv420p y la alfa se pierde).
    """
    subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", f"color=c=white:duration={segundos}:size={tam}:rate={fps}",
        "-vf", "format=rgba,geq=r=255:g=255:b=255:"
               "a='if(gt(X,10)*lt(X,60)*gt(Y,10)*lt(Y,60),255,0)'",
        "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-auto-alt-ref", "0",
        "-b:v", "0", destino],
        check=True, capture_output=True, timeout=180)
    return destino


class TestAlfaDeLaCapaWebm(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="alfa_webm_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.base = _fondo(os.path.join(self.tmp, "base.mp4"))
        self.capa = _capa_webm_con_alfa(os.path.join(self.tmp, "capa.webm"))
        self.salida = os.path.join(self.tmp, "final.mp4")

    def test_el_guion_dice_que_esta_capa_no_tiene_alfa(self):
        """El diagnostico: una capa .webm CON alfa no puede salir como opaca."""
        self.assertIs(comp._tiene_alfa(self.capa), True,
                      "el compositor no ve el alfa de la capa .webm (alpha_mode=1)")

    def test_el_clip_de_abajo_no_se_tapa_con_negro(self):
        """La pieza: donde la capa es transparente se ve el clip, no un rectangulo.

        Este es el fallo que se ve: con la capa leida opaca, el texto salia
        sobre fondo NEGRO en vez de desvanecido, y el clip de debajo
        desaparecia. Se mide en el frame final: un pixel de la zona
        transparente tiene que tener color de FONDO, no ser negro.
        """
        avisos, _cmd = comp.componer(self.base, self.capa, salida=self.salida,
                                     crf=30, preset="ultrafast")
        texto_avisos = " ".join(avisos) if isinstance(avisos, (list, tuple)) else str(avisos)
        self.assertNotIn("NO lleva canal alfa", texto_avisos,
                         "el compositor acusa a la capa de no tener alfa cuando si la tiene")
        # el pixel: el lienzo es el del kit (1080x1920) y la capa esta en el
        # centro-arriba; se mide en un punto TRANSPARENTE de la capa (abajo)
        frame = os.path.join(self.tmp, "frame.png")
        subprocess.run(["ffmpeg", "-v", "error", "-i", self.salida,
                        "-vf", "select=eq(n\\,10)", "-frames:v", "1", "-y", frame],
                       check=True, capture_output=True, timeout=120)
        from PIL import Image
        with Image.open(frame) as im:
            rgb = im.convert("RGB")
            ancho, alto = rgb.size
            # la capa solo tapa su cuadro (arriba a la izquierda): una esquina
            # lejana es transparente, y si la capa llega opaca ahi sale NEGRO
            px = rgb.getpixel((ancho - 30, alto - 30))
        self.assertTrue(any(c > 30 for c in px),
                        f"el clip de debajo sale tapado por un rectangulo negro "
                        f"(pixel {px} en {ancho}x{alto}): la capa se leyo opaca")


if __name__ == "__main__":
    unittest.main()
