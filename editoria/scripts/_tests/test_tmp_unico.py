#!/usr/bin/env python3
"""Tests del temporal propio: dos corridas a la vez no se pisan.

El fallo que motivo esto: dos `montaje join` simultaneos escriben la misma
lista de concat en el temp del SISTEMA, y cada ffmpeg lee la del otro — un
video silenciosamente distinto, que es PEOR que un fallo. Y el borrado del
segundo se lleva la lista que el primero todavia esta leyendo.

La clase: un nombre fijo en un sitio compartido (el temp del sistema) es
un sitio compartido sin concurrencia. La regla: lo temporal de una corrida
va en un directorio PROPIO de esa corrida.

Run with: python3 -m unittest discover -s SKILL/scripts/_tests
"""

import os
import re
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
FFT = os.path.join(SCRIPTS, "ffmpeg_tools")


class TestTemporalUnico(unittest.TestCase):

    def _dir_temp_de(self, proceso):
        code = ("import sys; sys.path.insert(0, %r); "
                "import _plataforma as P; print(P.dir_temp())" % FFT)
        r = subprocess.run([sys.executable, "-c", code],
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip()

    def test_dos_procesos_no_comparten_el_temporal(self):
        # dos corridas a la vez = dos procesos = dos directorios
        self.assertNotEqual(self._dir_temp_de("a"), self._dir_temp_de("b"),
                            "dos procesos comparten el temporal: se pisan")

    def test_dentro_de_un_proceso_es_el_mismo(self):
        code = ("import sys; sys.path.insert(0, %r); "
                "import _plataforma as P; print(P.dir_temp() == P.dir_temp())" % FFT)
        r = subprocess.run([sys.executable, "-c", code],
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(r.stdout.strip(), "True", r.stderr)

    def test_ningun_script_escribe_en_el_temp_del_sistema_con_nombre_fijo(self):
        # el nombre fijo en el temp del sistema es lo que se pisa. lo que
        # importa no es que sea "el temp": es que el NOMBRE sea fijo.
        patron = re.compile(r"gettempdir\(\)\s*,\s*[\"']([^\"']+)[\"']")
        ofensores = []
        for sub in ("", "ffmpeg_tools"):
            d = os.path.join(SCRIPTS, sub) if sub else SCRIPTS
            for f in sorted(os.listdir(d)):
                if not f.endswith(".py") or f == "__init__.py":
                    continue
                ruta = os.path.join(d, f)
                with open(ruta, encoding="utf-8") as fh:
                    txt = fh.read()
                for m in patron.finditer(txt):
                    ofensores.append(f"{os.path.relpath(ruta, SCRIPTS)}: {m.group(1)}")
        self.assertEqual(
            ofensores, [],
            "escribe en el temp del sistema con nombre fijo (se pisa si hay dos "
            "corridas a la vez): " + "; ".join(ofensores))


if __name__ == "__main__":
    unittest.main()
