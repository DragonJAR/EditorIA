#!/usr/bin/env python3
"""Tests de _comandos_copiables.py — el comando de la prosa, copiado, funciona.

Este guard existe porque `parse_args` NO puede ver un defecto: `verificar_ritmo.py
plan.json` es un comando perfectamente valido para argparse (el posicional se
llama `video`, pero `plan.json` es una cadena) y revienta mas tarde, cuando
ya no hay nadie mirando. El guard lo COPIA y lo CORRE con assets reales, y
juzga si lo que fallo es un veredicto de la herramienta o el comando roto.

Los tests de aqui comprueban las dos mitades:

  · que el guard CORTO lo que tiene que cortar (mutacion): un comando roto
    tiene que salir como problema, no como un "0 problemas" tranquilo.
  · que el guard NO se equivoca: un comando bueno no puede salir como roto,
    y lo que no se puede juzgar se SALTA y se cuenta, nunca se disimula.

Y la regla que las dos mitades comparten: una guarda que nunca ha fallado es
una hipotesis. El arnes de mutaciones es lo que la convierte en hecho.
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
BASE = os.path.dirname(SCRIPTS)
GUARD = os.path.join(SCRIPTS, "_comandos_copiables.py")


class TestComandosCopiables(unittest.TestCase):
    """El guard: copia, corre y juzga."""

    def _guard(self):
        sys.path.insert(0, SCRIPTS)
        try:
            import _comandos_copiables as cc
        finally:
            sys.path.pop(0)
        return cc

    def _tiny_video(self, tmp):
        """Un video minimo de verdad (1 s), para los comandos que lo necesitan."""
        destino = os.path.join(tmp, "tiny.mp4")
        p = subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
             "testsrc=duration=1:size=320x180:rate=10",
             "-pix_fmt", "yuv420p", destino],
            capture_output=True, text=True, timeout=120)
        self.assertEqual(p.returncode, 0, f"no se pudo crear el video: {p.stderr}")
        return destino

    def test_corta_un_comando_roto(self):
        """MUTACION: un comando documentado con el argumento equivocado tiene
        que salir como problema. Este es el defecto real que motivo el guard:
        `verificar_ritmo.py plan.json` (el plan donde va el video) revienta
        con "ffmpeg no pudo leer"."""
        cc = self._guard()
        tmp = tempfile.mkdtemp(prefix="editoria_copiable_")
        try:
            assets = cc._assets(tmp, BASE)
            # el comando roto, tal cual lo escribia la prosa
            problemas, _ = cc.verificar(
                BASE, comandos=["scripts/verificar_ritmo.py plan.json"])
            self.assertTrue(problemas,
                            "el guard no vio un comando roto: "
                            "la prosa podia mandar un plan donde va el video")
            self.assertTrue(any("no pudo leer" in p for p in problemas),
                            f"el motivo no es el del defecto: {problemas}")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_no_corta_un_comando_bueno(self):
        """El guard no puede acusar de roto lo que funciona: un falso positivo
        es tan malo como un falso negativo, porque teaches a ignorar el
        guard."""
        cc = self._guard()
        problemas, informe = cc.verificar(
            BASE, comandos=["scripts/auditar_plan.py plan.json"])
        self.assertEqual(problemas, [],
                         f"el guard acuso a un comando sano: {problemas}")
        self.assertEqual(informe["copiados"], 1,
                         "el comando no se copio: el guard no miró lo que dice")

    def test_lo_que_no_se_puede_juzgar_se_salta_y_se_cuenta(self):
        """Un comando con un placeholder que no se puede sustituir se SALTA, y
        el salto se CUENTA. Un guard que se salta la mitad sin decirlo es un
        guard que no mira."""
        cc = self._guard()
        problemas, informe = cc.verificar(
            BASE, comandos=["scripts/clonar_video.py variar --plantilla plantilla.json"])
        self.assertEqual(problemas, [])
        self.assertEqual(informe["saltados"], 1,
                         f"el salto no se conto: {informe}")

    def test_la_lista_de_clis_tiene_que_ser_completa(self):
        """Toda CLI documentada o se copia, o tiene el motivo de por que no.
        Una CLI que no se ejecuta y no tiene motivo es un puntero a nada."""
        cc = self._guard()
        sys.path.insert(0, SCRIPTS)
        try:
            import _comandos_doc as cd
        finally:
            sys.path.pop(0)
        scripts = cd.scripts_de_los_comandos(BASE)
        huerfanos = [s for s in scripts
                     if s not in cc.EJECUTABLES and s not in cc.FUERA]
        self.assertEqual(huerfanos, [],
                         f"CLI documentada sin motivo y sin copia: {huerfanos}")
        # y ninguna exclusion sin motivo escrito
        for cli, motivo in cc.FUERA.items():
            self.assertTrue(motivo.strip(),
                            f"exclusion sin motivo: {cli}")

    def test_la_cli_del_guard_se_puede_correr(self):
        """El guard tiene que ser una CLI de verdad, no un modulo: se ejecuta
        como proceso, y su `--solo` deja mirar UN comando sin correrlos
        todos. Asi el censo lo mide como lo que es: algo que se EJECUTA (y no
        como un nombre importado, que es lo mismo que no medir nada)."""
        p = subprocess.run(
            [sys.executable, GUARD, "--solo", "verificar_ritmo", "--json"],
            capture_output=True, text=True, timeout=300)
        self.assertEqual(p.returncode, 0, f"el guard fallo: {p.stderr[-500:]}")
        datos = json.loads(p.stdout)
        self.assertEqual(datos["problemas"], [],
                         f"el guard acuso a un comando sano: {datos['problemas']}")
        self.assertGreater(datos["informe"]["copiados"], 0,
                           "el guard no copio ningun comando")

    def test_el_guard_no_escribe_dentro_de_la_skill(self):
        """Un guard que modifica lo que vigila no es un guard. Ninguna CLI que
        el guard copia escribe dentro de la skill."""
        cc = self._guard()
        for cli in cc.EJECUTABLES:
            self.assertNotIn("registrar_aprendizaje", cli,
                             "registrar_aprendizaje escribe en la skill")
        ruta = os.path.join(BASE, "scripts", "registrar_aprendizaje.py")
        with open(ruta, encoding="utf-8") as fh:
            texto = fh.read()
        self.assertIn("references/", texto,
                      "el script ya no escribe en la skill: revisa el motivo "
                      "de la exclusion antes de tocar nada")


if __name__ == "__main__":
    unittest.main()
