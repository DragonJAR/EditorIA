#!/usr/bin/env python3
"""Tests de verificar_ritmo.py — la verificacion de ritmo de una pieza.

Por que existe el flag `--sobre-footage-vivo`: los minimos de "cuadros
quietos" y "pausa" son de una pieza de motion graphics, donde el silencio
visual lo compone el PIECE. Una pieza sobre planos reales que siempre se
mueven no puede tener ese silencio: no es un defecto, es que el minimo no
aplica (el mismo caso que la rafaga, que ya es un WARN cuando el concepto
no la pide). Con el flag, esos dos minimos pasan a "no aplica" (con su
motivo) y los demas (cadencia, rafaga) se siguen midiendo igual.

Y por que existe la clase `TestVeredictoHonesto`: el verificador decia
"PASS — no lee como slideshow" sobre una comprobacion que NO se habia
medido. Sin cortes detectados no hay duraciones de toma que comparar, el
coeficiente de variacion no se tiene, y el resultado era un WARN que no es
un fallo: la pieza salia aprobada con la comprobacion sin hacer. Un PASS
sobre una medicion que no ocurrio es una afirmacion que el verificador no
puede hacer. Ahora esa comprobacion sale SIN MEDIR (codigo 2), que no es un
fallo y no es un aprobado: la pieza sigue sin verificar.

Run with: python3 -m unittest discover -s SKILL/scripts/_tests
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
VERIFICAR = os.path.join(SCRIPTS, "verificar_ritmo.py")


def _video_movido(destino, segundos=2):
    """Imagen que cambia en cada cuadro: 0 % de cuadros quietos."""
    subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", f"testsrc=duration={segundos}:size=160x90:rate=10",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", destino],
        check=True, capture_output=True, timeout=120)
    return destino


def _video_con_fundido(destino):
    """Silencio visual y NINGUN corte duro, por construccion.

    Un plano de color (1,5 s quietos) que se funde con una imagen en
    movimiento: el fundido no es un corte, asi que `scene-select` no ve
    ninguno (0 cortes), pero el silencio visual si se cumple (39 % de
    cuadros quietos y una pausa de 1,5 s). Es el caso donde la cadencia NO
    se puede medir y el verificador tiene que decirlo.
    """
    subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", "color=c=navy:size=160x90:rate=10:d=2.5",
        "-f", "lavfi", "-i", "testsrc=duration=2.5:size=160x90:rate=10",
        "-filter_complex", "[0][1]xfade=transition=fade:duration=1:offset=1.5",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", destino],
        check=True, capture_output=True, timeout=120)
    return destino


class TestSalvedadPorConcepto(unittest.TestCase):
    """El flag pone "quietud" y "pausa" en no aplica, sin tocar el resto."""

    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp()
        cls.video = _video_movido(os.path.join(cls.dir, "vivo.mp4"))
        # Dos planes con las MISMAS escenas (3 tomas: 3 s, 6 s y 5 s -> CV 0.27)
        # y distinto HECHO declarado. El que lleva el hecho exime el
        # silencio visual; el que no lo lleva, no. Los cortes los dan los dos:
        # sin ellos la cadencia queda SIN MEDIR (ver TestVeredictoHonesto) y
        # una comprobacion sin medir no puede dar un PASS.
        cls.plan_con_hecho = os.path.join(cls.dir, "plan.json")
        with open(cls.plan_con_hecho, "w", encoding="utf-8") as fh:
            json.dump({
                "duracion": 20.0,
                "sobre_footage_vivo": True,
                "escenas": [
                    {"tipo": "apertura", "from": 0.0, "to": 3.0},
                    {"tipo": "bento", "from": 3.0, "to": 9.0},
                    {"tipo": "final", "from": 9.0, "to": 14.0},
                ],
            }, fh)
        cls.plan_sin_hecho = os.path.join(cls.dir, "plan_sin.json")
        with open(cls.plan_sin_hecho, "w", encoding="utf-8") as fh:
            json.dump({
                "duracion": 20.0,
                "escenas": [
                    {"tipo": "apertura", "from": 0.0, "to": 3.0},
                    {"tipo": "bento", "from": 3.0, "to": 9.0},
                    {"tipo": "final", "from": 9.0, "to": 14.0},
                ],
            }, fh)

    def _correr(self, *args):
        return subprocess.run([sys.executable, VERIFICAR, self.video] + list(args),
                              capture_output=True, text=True, timeout=300)

    def test_sin_el_flag_el_silencio_visual_falla(self):
        """Una pieza que se mueve siempre no tiene cuadros quietos: sin el
        flag, los minimos de silencio visual se cumplen como se cumplen."""
        r = self._correr()
        self.assertIn("quietud", r.stdout)
        self.assertIn("FAIL", r.stdout)
        self.assertIn("pausa", r.stdout)

    def test_con_el_flag_no_aplica_y_no_falla(self):
        """El flag es lo que exime el silencio visual (el plan de este test no
        declara el hecho). Los cortes vienen del plan, para que la cadencia
        SI se mida: una comprobacion sin medir no puede dar un PASS."""
        r = self._correr("--sobre-footage-vivo", "--plan", self.plan_sin_hecho)
        self.assertIn("no aplica sobre footage vivo", r.stdout)
        self.assertIn("N/A", r.stdout)
        self.assertNotIn("FAIL", r.stdout)
        self.assertIn("PASS", r.stdout)      # el resultado overall es PASS
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_el_plan_declara_el_hecho_y_manda_en_los_cortes(self):
        """El plan es el documento de la pieza: ahi quedan registrados los
        cortes (los beats que percibe el espectador) y el HECHO de que se
        compone sobre footage vivo. Un flag de CLI no deja constancia."""
        r = subprocess.run([sys.executable, VERIFICAR, self.video, "--plan",
                            self.plan_con_hecho],
                           capture_output=True, text=True, timeout=300)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("no aplica sobre footage vivo", r.stdout)
        # la cadencia se mide con los TIEMPOS DE LAS ESCENAS del plan:
        # duraciones 3, 6 y 5 -> CV 0.26 (no se detectan cortes en el video)
        self.assertRegex(r.stdout, r"PASS\s+cadencia\s+CV=0\.\d+")
        self.assertIn("3 tomas", r.stdout)   # 3 escenas -> 3 duraciones

    def test_un_plan_sin_el_hecho_no_exime_nada(self):
        """El campo declara el HECHO: si no esta, los minimos se miden."""
        r = subprocess.run([sys.executable, VERIFICAR, self.video, "--plan",
                            self.plan_sin_hecho],
                           capture_output=True, text=True, timeout=300)
        self.assertIn("quietud", r.stdout)
        self.assertNotIn("no aplica sobre footage vivo", r.stdout)

    def test_el_flag_no_toca_la_cadencia_ni_la_rafaga(self):
        """El flag es una salvedad de CONCEPTO para el silencio visual: los
        otros minimos se siguen midiendo."""
        r = self._correr("--sobre-footage-vivo")
        self.assertIn("cadencia", r.stdout)
        self.assertIn("ráfaga", r.stdout)


class TestVeredictoHonesto(unittest.TestCase):
    """El veredicto no puede ser PASS sobre una medicion que no ocurrio."""

    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp()
        cls.video = _video_con_fundido(os.path.join(cls.dir, "fundido.mp4"))

    def _correr(self, *args, script=VERIFICAR):
        return subprocess.run([sys.executable, script, self.video] + list(args),
                              capture_output=True, text=True, timeout=300)

    def test_sin_cortes_no_dice_pass(self):
        """Sin cortes no hay duraciones de toma que comparar: la cadencia NO
        se pudo medir. El veredicto tiene que decirlo (SIN MEDIR, codigo 2),
        y no puede afirmar "no lee como slideshow" sobre una medicion que no
        ocurrio."""
        r = self._correr()
        self.assertIn("SIN MEDIR", r.stdout)
        self.assertNotIn("no lee como slideshow", r.stdout)
        self.assertNotEqual(r.returncode, 0,
                             f"sin medir no es un aprobado: {r.stdout}")
        self.assertEqual(r.returncode, 2,
                         f"el codigo distingue 'sin medir' (2) de 'fallo' (1) "
                         f"y de 'aprobado' (0): {r.stdout}")

    def test_el_resto_de_las_comprobaciones_sigue_medido(self):
        """SIN MEDIR es solo la cadencia: el silencio visual se midio (el
        video tiene 39 % de cuadros quietos y una pausa de 1,5 s) y asi se
        dice. Un veredicto que se calla lo que si midio tampoco es honesto."""
        r = self._correr()
        self.assertRegex(r.stdout, r"PASS\s+quietud")
        self.assertRegex(r.stdout, r"PASS\s+pausa")

    def test_la_mutacion_del_veredicto_la_caza(self):
        """MUTACION: si el veredicto vuelve a tratar "sin medir" como un
        PASS, este guard tiene que notarlo.

        Se muta una COPIA del script (el original no se toca): la rama que
        convierte lo no medido en veredicto se apaga. El mutante dice "no
        lee como slideshow" y sale con 0; el original dice SIN MEDIR y sale
        con 2. Si los dos dijeran lo mismo, este guard no miraria nada. Y si
        la mutacion no se aplica (el verificador cambio de forma), el test
        falla aqui: una mutacion que no se aplica no prueba nada.
        """
        carpeta = os.path.join(self.dir, "mutado")
        os.makedirs(carpeta, exist_ok=True)
        ruta = os.path.join(carpeta, "verificar_ritmo.py")
        shutil.copy(VERIFICAR, ruta)
        # el script importa de ffmpeg_tools/ (el coeficiente de variacion
        # vive ahi): un enlace al directorio real, para no copiarlo
        os.symlink(os.path.join(SCRIPTS, "ffmpeg_tools"),
                   os.path.join(carpeta, "ffmpeg_tools"))
        with open(ruta, encoding="utf-8") as fh:
            fuente = fh.read()
        self.assertIn("    if sin_medir:", fuente,
                      "el verificador ya no tiene esta rama: la mutacion no "
                      "se aplica y este guard es un puntero a nada")
        with open(ruta, "w", encoding="utf-8") as fh:
            fh.write(fuente.replace("    if sin_medir:", "    if False:", 1))
        r = self._correr(script=ruta)
        self.assertIn("no lee como slideshow", r.stdout,
                      "la mutacion no cambio el veredicto: el guard no tiene poder")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
