#!/usr/bin/env python3
"""Tests for ffmpeg_tools/acabado.py — style finishes measured on real pixels.

Builders are pure (checked as strings, no ffmpeg needed). Each finish is also
run end to end on a small synthetic clip with lossless luma (--crf 0), so what
is asserted is the filter's effect and not x264 compression: held poses are
bit-identical, pixel art has a limited palette in exact blocks, the chromatic
split moves the red channel, the glow adds light, scanlines modulate rows, and
audio and size survive. Also covers --dry-run (writes nothing) and bad input.

Run with: python3 -m unittest discover -s SKILL/scripts/_tests
"""

import os
import subprocess
import sys
import tempfile
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(os.path.dirname(HERE), "ffmpeg_tools")
sys.path.insert(0, TOOLS)

import acabado as AC  # noqa: E402

W, H, FPS, DUR = 640, 360, 30, 2
ACABADO = os.path.join(TOOLS, "acabado.py")


def ffmpeg(*a):
    subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-y", *a], check=True)


def frames(path, pix="gray"):
    canales = 1 if pix == "gray" else 3
    raw = subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-i", path, "-f", "rawvideo", "-pix_fmt", pix, "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, H, W) if canales == 1 else \
        np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)


class TestConstructores(unittest.TestCase):
    def test_escalonado(self):
        self.assertEqual(AC.filtro_escalonado(30.0, cada=2), "fps=15:round=down,fps=30")
        self.assertEqual(AC.filtro_escalonado(24.0, fps_pose=12), "fps=12:round=down,fps=24")
        for malo in (dict(cada=1), dict(fps_pose=60), dict(cada=2, fps_pose=12), dict()):
            with self.assertRaises(SystemExit):
                AC.filtro_escalonado(30.0, **malo)

    def test_pixelar_valida_y_construye(self):
        f = AC.filtro_pixelar(1920, 1080, ancho=320, colores=32)
        self.assertIn("scale=320:180:flags=area", f)
        self.assertIn("max_colors=32", f)
        self.assertTrue(f.endswith("scale=1920:1080:flags=neighbor,format=yuv420p"))
        for malo in (dict(colores=1), dict(colores=999), dict(ancho=4), dict(ancho=1920)):
            with self.assertRaises(SystemExit):
                AC.filtro_pixelar(1920, 1080, **malo)

    def test_radios_escalan_con_el_tamano(self):
        chico = AC.cadena_resplandor(540, 960, 4, 30)
        grande = AC.cadena_resplandor(1080, 1920, 4, 30)
        sigma = lambda cadena: float(cadena[2].split("sigma=")[1].split("[")[0])   # noqa: E731
        self.assertAlmostEqual(sigma(grande) / sigma(chico), 2.0, places=1)
        self.assertEqual(AC.px(2, 540, 960), 1)           # nunca 0: el efecto no desaparece
        self.assertEqual(AC.px(2, 2160, 3840), 4)

    def test_crt_usa_barril_negativo_y_comparte_el_glow(self):
        f = AC.filtro_crt(1080, 1920)
        self.assertIn("lenscorrection=k1=-0.12", f)
        self.assertEqual(f.count("split=3"), 1)
        self.assertIn("screen", f)

    def test_vhs_y_aberracion(self):
        self.assertIn("rgbashift=rh=-2:bh=2", AC.filtro_vhs(1080, 1920, 1.0))
        self.assertIn("rgbashift=rh=-4:bh=4", AC.filtro_vhs(1080, 1920, 2.0))
        self.assertEqual(AC.filtro_aberracion(1080, 1920, 3), "rgbashift=rh=-3:bh=3,format=yuv420p")
        with self.assertRaises(SystemExit):
            AC.filtro_vhs(1080, 1920, 0)
        with self.assertRaises(SystemExit):
            AC.cadena_resplandor(1080, 1920, fuerza=5)


class TestEfectosEnPixeles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.src = os.path.join(cls.tmp.name, "src.mp4")
        ffmpeg("-f", "lavfi", "-i", f"testsrc2=s={W}x{H}:d={DUR}:r={FPS}", "-f", "lavfi", "-i", f"sine=f=440:d={DUR}",
               "-shortest", "-pix_fmt", "yuv420p", "-c:v", "libx264", "-crf", "10", "-colorspace", "bt709", "-color_primaries", "bt709",
               "-color_trc", "bt709", "-c:a", "aac", cls.src)
        cls.base = frames(cls.src)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def aplicar(self, *args):
        salida = os.path.join(self.tmp.name, f"o_{abs(hash(args))}.mp4")
        r = subprocess.run([sys.executable, ACABADO, *args, self.src, "-o", salida, "--crf", "0"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return salida

    def dims_y_audio(self, ruta):
        p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height,nb_frames",
                            "-of", "csv=p=0", ruta], capture_output=True, text=True).stdout
        self.assertIn(f"video,{W},{H},{FPS * DUR}", p)
        self.assertIn("audio", p)

    def test_escalonado_sostiene_poses_sin_cambiar_fps(self):
        ruta = self.aplicar("escalonado", "--cada", "2")
        self.dims_y_audio(ruta)
        f = frames(ruta)
        self.assertEqual(len(f), FPS * DUR)
        iguales = sum(np.array_equal(f[i], f[i + 1]) for i in range(0, 40, 2))
        self.assertEqual(iguales, 20)                                   # cada pose, dos cuadros idénticos
        self.assertFalse(np.array_equal(f[1], f[2]))                    # y la siguiente pose sí cambia

    def test_pixelar_paleta_limitada_en_bloques_exactos(self):
        ruta = self.aplicar("pixelar", "--ancho", "160", "--colores", "16")
        self.dims_y_audio(ruta)
        y = frames(ruta)[10]
        self.assertLessEqual(len(np.unique(y)), 16)
        bloques = y.reshape(H // 4, 4, W // 4, 4)
        constantes = np.all(bloques == bloques[:, :1, :, :1], axis=(1, 3)).mean()
        self.assertGreater(constantes, 0.99)                            # 640/160 = píxeles de 4x4 exactos

    def test_aberracion_mueve_el_rojo_a_la_izquierda(self):
        ruta = self.aplicar("aberracion", "--px", "12")
        self.dims_y_audio(ruta)
        antes, despues = frames(self.src, "rgb24")[5], frames(ruta, "rgb24")[5]
        d = AC.px(12, W, H)
        con = np.abs(despues[:, : -2 * d, 0].astype(int) - antes[:, d: -d, 0].astype(int)).mean()
        sin = np.abs(despues[:, : -2 * d, 0].astype(int) - antes[:, : -2 * d, 0].astype(int)).mean()
        self.assertLess(con, sin * 0.8)
        # el azul va al lado contrario (el verde se omite: en 4:2:0 se reconstruye con el croma)
        az_con = np.abs(despues[:, 2 * d:, 2].astype(int) - antes[:, d: -d, 2].astype(int)).mean()
        az_sin = np.abs(despues[:, 2 * d:, 2].astype(int) - antes[:, 2 * d:, 2].astype(int)).mean()
        self.assertLess(az_con, az_sin * 0.8)

    def test_resplandor_agrega_luz_sin_cambiar_el_tamano(self):
        ruta = self.aplicar("resplandor", "--fuerza", "0.9")
        self.dims_y_audio(ruta)
        self.assertGreater(frames(ruta)[5].mean(), self.base[5].mean() + 1.0)

    def test_vhs_dibuja_lineas_de_barrido(self):
        ruta = self.aplicar("vhs")
        self.dims_y_audio(ruta)
        f = frames(ruta)[5].astype(float)
        pares, impares = f[0::2].mean(), f[1::2].mean()
        b = self.base[5].astype(float)
        self.assertGreater(abs(pares - impares), abs(b[0::2].mean() - b[1::2].mean()) + 0.5)

    def test_crt_corre_y_conserva_audio_y_tamano(self):
        self.dims_y_audio(self.aplicar("crt"))

    def test_dry_run_no_escribe_nada(self):
        salida = os.path.join(self.tmp.name, "no_debe_existir.mp4")
        r = subprocess.run([sys.executable, ACABADO, "vhs", "--dry-run", self.src, "-o", salida],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(os.path.exists(salida))
        self.assertIn("[dry-run]", r.stderr + r.stdout)

    def test_entradas_malas_dan_error_claro(self):
        for args in (["vhs", os.path.join(self.tmp.name, "no_existe.mp4")],
                     ["escalonado", "--fps-pose", "60", self.src],
                     ["pixelar", "--ancho", "9999", self.src]):
            r = subprocess.run([sys.executable, ACABADO, *args], capture_output=True, text=True)
            self.assertEqual(r.returncode, 1, args)
            self.assertNotIn("Traceback", r.stderr)


if __name__ == "__main__":
    unittest.main()
