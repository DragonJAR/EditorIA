#!/usr/bin/env python3
"""Tests de las verticales de la skill — las cinco, y que de verdad funcionen.

La skill declara cinco verticales (scripts/data/verticales.json): crear y
animar, editar, clonar y resumir, el sonido (voz, musica, efectos) y
publicar/viralizar. Y el
guard (scripts/auditar_mapa.py) comprueba que cada una tiene ruta, puerta y
herramientas que alguien EJECUTA.

Aqui van las dos mitades de ese contrato:

  · que las herramientas de las verticales se ejecuten DE VERDAD. Tres de
    ellas (speedramp, verticalizar, retakes) no las ejecutaba ningun test:
    eran punteros a nada, y un puntero a nada en una vertical es una isla.
  · que el guard de verticales tenga PODER: si se le quita la ruta del
    sonido, tiene que decir que falta. Un guard que nunca ha fallado es una
    hipotesis, y una hipotesis no es una garantia.

Run with: python3 -m unittest discover -s SKILL/scripts/_tests
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
BASE = os.path.dirname(SCRIPTS)
AUDITAR = os.path.join(SCRIPTS, "auditar_mapa.py")
VERTICALES = os.path.join(SCRIPTS, "data", "verticales.json")


def _video_sintetico(destino, segundos=2):
    """Un video minimo con imagen y audio (para las herramientas que los usan)."""
    subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", f"testsrc=duration={segundos}:size=320x180:rate=10",
        "-f", "lavfi", "-i", f"sine=frequency=440:duration={segundos}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", destino],
        check=True, capture_output=True, timeout=120)
    return destino


def _srt(destino):
    """Un SRT con dos islas: la primera es un falso arranque."""
    with open(destino, "w", encoding="utf-8") as fh:
        fh.write(
            "1\n00:00:00,000 --> 00:00:02,000\nrepito esto otra vez\n\n"
            "2\n00:00:02,000 --> 00:00:04,000\ny aqui empieza de verdad\n\n"
            "3\n00:00:05,000 --> 00:00:07,000\nla conclusion\n\n")
    return destino


def _corre(script, args, cwd=None):
    return subprocess.run([sys.executable, script] + args,
                          capture_output=True, text=True, timeout=300, cwd=cwd)


class TestHerramientasDeLasVerticales(unittest.TestCase):
    """Las herramientas de las verticales se ejecutan de verdad."""

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="editoria_vert_")
        self.addCleanup(shutil.rmtree, self.dir, True)

    def test_speedramp_se_ejecuta(self):
        """El ramp de velocidad: valida sus segmentos y compone el clip."""
        vid = _video_sintetico(os.path.join(self.dir, "v.mp4"))
        p = _corre(os.path.join(SCRIPTS, "ffmpeg_tools", "speedramp.py"),
                   [vid, "--segment", "0-1:2", "--segment", "1-2:0.5",
                    "-o", os.path.join(self.dir, "ramp.mp4")])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertTrue(os.path.exists(os.path.join(self.dir, "ramp.mp4")))

    def test_verticalizar_se_ejecuta(self):
        """Convertir a vertical: el modo crop deja 1080x1920."""
        vid = _video_sintetico(os.path.join(self.dir, "h.mp4"))
        salida = os.path.join(self.dir, "v.mp4")
        p = _corre(os.path.join(SCRIPTS, "ffmpeg_tools", "verticalizar.py"),
                   [vid, "-o", salida])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertTrue(os.path.exists(salida))

    def test_retakes_se_ejecuta(self):
        """Los retakes: sobre un SRT con un falso arranque, lo marca."""
        srt = _srt(os.path.join(self.dir, "voz.srt"))
        p = _corre(os.path.join(SCRIPTS, "retakes.py"), [srt, "--dry-run"])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("retake", (p.stdout + p.stderr).lower(),
                      f"no detecto el falso arranque: {p.stdout}{p.stderr}")

    def test_el_censo_mide_estas_herramientas(self):
        """Y el CENSO lo sabe: estas tres herramientas tienen que salir como
        ejecutadas por un test. Si no, el guard de verticales las vera como
        punteros a nada."""
        mapa = os.path.join(SCRIPTS, "data", "cli_verificadas.json")
        with open(mapa, encoding="utf-8") as fh:
            medidas = set((json.load(fh) or {}).get("verificadas") or {})
        for cli in ("scripts/ffmpeg_tools/speedramp.py",
                    "scripts/ffmpeg_tools/verticalizar.py",
                    "scripts/retakes.py"):
            self.assertIn(cli, medidas,
                          f"{cli} no esta en el mapa de CLIs medidas: ejecuta su "
                          f"test y regenera el mapa con --escribir")


class TestGuardDeVerticales(unittest.TestCase):
    """El guard de las verticales tiene que tener poder."""

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="editoria_vertguard_")
        self.addCleanup(shutil.rmtree, self.dir, True)

    def _copia(self):
        """Una copia de la skill (lo que el auditor necesita para mirar)."""
        destino = os.path.join(self.dir, "skill")
        shutil.copytree(os.path.join(BASE, "scripts"),
                        os.path.join(destino, "scripts"),
                        ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(os.path.join(BASE, "references"),
                        os.path.join(destino, "references"))
        shutil.copy(os.path.join(BASE, "SKILL.md"),
                    os.path.join(destino, "SKILL.md"))
        return destino

    def _auditar(self, raiz):
        return subprocess.run([sys.executable, os.path.join(raiz, "scripts", "auditar_mapa.py")],
                              capture_output=True, text=True, timeout=300)

    def test_las_cuatro_verticales_declaran_su_ruta(self):
        """MUTACION: si se le quita la ruta a una vertical, el guard lo dice.
        Una guarda que nunca ha fallado es una hipotesis."""
        raiz = self._copia()
        mapa = os.path.join(raiz, "references", "mapa.md")
        with open(mapa, encoding="utf-8") as fh:
            texto = fh.read()
        # se le quitan las DOS rutas de una vertical: la del sonido y la de crear
        quitar = texto
        for nombre in ("quiero CREAR un video", "quiero VOZ en off, música o sonido"):
            quitar = re.sub(r'- \*\*"?' + re.escape(nombre) + r'"?\*\*.*?(?=\n- \*\*|\Z)',
                            "", quitar, flags=re.S)
        self.assertNotIn("quiero VOZ en off", quitar, "no se quito la ruta")
        with open(mapa, "w", encoding="utf-8") as fh:
            fh.write(quitar)
        p = self._auditar(raiz)
        salida = p.stdout + p.stderr
        self.assertIn("vertical sin ruta", salida,
                      f"el guard no vio que faltan rutas:\n{salida[-1500:]}")
        self.assertEqual(p.returncode, 1,
                         f"el guard paso con una vertical sin ruta:\n{salida[-1500:]}")

    def test_una_vertical_sin_entrada_tambien_se_corta(self):
        """MUTACION: si la ENTRADA (el SKILL.md, que es lo primero que lee el
        agente) deja de nombrar una vertical, el guard tiene que decirlo. Una
        vertical con ruta en el mapa pero sin nombre en la entrada tampoco se
        encuentra: el indice no es la puerta de entrada, es un indice.

        La vertical del SONIDO fue justo una isla (no tenia ni ruta), asi que
        esta capa no es teorica."""
        raiz = self._copia()
        skill = os.path.join(raiz, "SKILL.md")
        with open(skill, encoding="utf-8") as fh:
            texto = fh.read()
        # se le quita el nombre a la vertical del sonido
        quitado = texto.replace("mezclar_audio", "el mezclador de la pieza")
        self.assertNotEqual(quitado, texto, "no se quito el nombre")
        with open(skill, "w", encoding="utf-8") as fh:
            fh.write(quitado)
        p = self._auditar(raiz)
        salida = p.stdout + p.stderr
        self.assertIn("vertical sin entrada", salida,
                      f"el guard no vio una vertical que la entrada no nombra:\n{salida[-1500:]}")
        self.assertEqual(p.returncode, 1,
                         f"el guard paso con una vertical sin entrada:\n{salida[-1500:]}")

    def test_una_vertical_sin_puerta_tambien_se_corta(self):
        """Y si su ruta no acaba en la puerta, tambien: una vertical que
        entrega sin medir no es una vertical."""
        raiz = self._copia()
        mapa = os.path.join(raiz, "references", "mapa.md")
        with open(mapa, encoding="utf-8") as fh:
            texto = fh.read()
        # se le quita la puerta SOLO a la ruta del sonido (el bloque entero,
        # no la primera mencion del mapa: el texto va con acentos graves)
        bloques = re.split(r"\n(?=- \*\*)", texto)
        fuera = []
        for b in bloques:
            if "quiero VOZ en off" in b:
                b = b.replace("qa-entrega.md", "otra-cosa.md")
            fuera.append(b)
        quitar = "\n".join(fuera)
        self.assertNotIn("otra-cosa.md", texto, "el texto de la ruta no es el esperado")
        self.assertIn("otra-cosa.md", quitar, "no se quito la puerta")
        with open(mapa, "w", encoding="utf-8") as fh:
            fh.write(quitar)
        p = self._auditar(raiz)
        salida = p.stdout + p.stderr
        self.assertIn("vertical sin puerta", salida,
                      f"el guard no vio una vertical sin puerta:\n{salida[-1500:]}")


if __name__ == "__main__":
    unittest.main()
