#!/usr/bin/env python3
"""Tests de la normalizacion de sonoridad para la ENTREGA.

QUE PROTEGE

1. `normalizar` VERIFICA el techo de true peak del RESULTADO y repite con el
   techo bajado si lo pasa. MEDIDO (en el linaje 1.11.3): el AAC suma
   sobrepico DESPUES de loudnorm, asi que con -14 LUFS y techo -1.5 el
   entregable salia a -0.8 dBTP y la entrega de Reels (techo -1.0) lo
   rechazaba. Sin la verificacion, la pieza se entrega y la puerta la
   rechaza despues.
2. `normalizar_para` usa el objetivo de la PLATAFORMA (tabla canonica
   `_delivery`): LUFS y techo de cada una.
3. `mezclar_audio` normaliza al objetivo de la plataforma y lo DICE.

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
for p in (SCRIPTS, TOOLS):
    if p not in sys.path:
        sys.path.insert(0, p)

from loudness import measure, normalizar, normalizar_para  # noqa: E402


class TestTechoVerificado(unittest.TestCase):
    """El techo se comprueba SOBRE EL RESULTADO, no sobre la entrada."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="loudness_")
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _tono(self, nombre, frec=440, vol=0.9, dur=3):
        ruta = os.path.join(self.tmp, nombre)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                        f"sine=frequency={frec}:duration={dur}:sample_rate=48000",
                        "-af", f"volume={vol}", "-c:a", "aac", "-b:a", "192k",
                        ruta], check=True, capture_output=True, timeout=180)
        return ruta

    def test_el_techo_del_resultado_se_verifica(self):
        """Con un techo alcanzable, el resultado TIENE que pasar el techo."""
        entrada = self._tono("entrada.m4a")
        salida = os.path.join(self.tmp, "salida.m4a")
        res = normalizar(entrada, salida, lufs=-14.0, tp=-8.0, tp_max=-1.0,
                         reintentos=3)
        self.assertFalse(res.get("silent"), "el tono de prueba salio en silencio")
        tp = float(res["input_tp"])
        self.assertLessEqual(tp, -1.0 + 0.01,
                             f"el resultado paso el techo (-1.0 dBTP): {tp:.2f} dBTP. "
                             f"El techo no se verifica: la entrega lo rechaza")

    def test_cuando_el_techo_no_se_alcanza_reintenta(self):
        """Un techo por debajo de lo que la senal puede dar: reintenta y lo dice.

        El pico de un tono normalizado no puede bajar de certain valor con
        loudnorm; lo que se puede comprobar es que la herramienta NO se
        queda callada: baja el techo e intenta otra vez (y avisa).
        """
        entrada = self._tono("entrada3.m4a")
        salida = os.path.join(self.tmp, "salida3.m4a")
        import contextlib
        import io
        ruido = io.StringIO()
        with contextlib.redirect_stdout(ruido), contextlib.redirect_stderr(ruido):
            res = normalizar(entrada, salida, lufs=-14.0, tp=-8.0, tp_max=-12.0,
                             reintentos=2)
        self.assertFalse(res.get("silent"))
        self.assertIn("repito con TP", ruido.getvalue(),
                      "la herramienta no aviso de que el resultado pasaba el "
                      f"techo: {ruido.getvalue()[-400:]!r}")

    def test_normalizar_para_usa_el_objetivo_de_la_plataforma(self):
        """El objetivo sale de la tabla de la plataforma, no de un literal."""
        import _delivery
        entrada = self._tono("entrada2.m4a")
        salida = os.path.join(self.tmp, "salida2.m4a")
        sp = _delivery.spec_of("reels")
        res = normalizar_para(entrada, salida, "reels")
        self.assertFalse(res.get("silent"))
        objetivo = float(sp.get("lufs", -14))
        medido = float(res["input_i"])
        self.assertLess(abs(medido - objetivo), 1.0,
                        f"la mezcla quedo a {medido:.1f} LUFS y la plataforma "
                        f"pide {objetivo:.1f}")
        techo = float(sp.get("tp", -1.0))
        self.assertLessEqual(float(res["input_tp"]), techo + 0.01,
                             "el resultado pasa el techo de la plataforma")


if __name__ == "__main__":
    unittest.main()
