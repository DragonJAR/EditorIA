#!/usr/bin/env python3
"""Tests de las reglas de contenido que el motor corrige solo.

QUE PROTEGE

1. El CIERRE acepta `marca` o `titulo` (uno de los dos). Antes `e["marca"]`
   reventaba con KeyError y el error no decia de que campo se trataba: un
   plan con `titulo` (el nombre de la pieza, no el del pack) moria sin
   decir por que.
2. La APERTURA deja la 1.a frase el tiempo de poder leerse: si el plan la
   cambia antes, el cambio (y la 2.a frase) se corren, sin pasarse del final
   de la escena. MEDIDO: «Tu pyme tambien es» se leia en 0,9 s.

Run with: python3 -m unittest discover -s SKILL/scripts/_tests
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
for p in (SCRIPTS, os.path.join(SCRIPTS, "ffmpeg_tools")):
    if p not in sys.path:
        sys.path.insert(0, p)

import render_plan as R  # noqa: E402


class TestCierreConTitulo(unittest.TestCase):
    def test_el_cierre_acepta_titulo(self):
        """Un cierre con `titulo` (y sin `marca`) no puede reventar."""
        e = {"tipo": "final", "from": 0.0, "to": 3.0,
             "titulo": "HABLEMOS",
             "at": {"lema": 1.0, "boton": 1.6}}
        escena = R.completar_escena(dict(e))
        ctx = R.Ctx()
        capa = R.sc_final(ctx, escena, 2.0)     # no debe lanzar KeyError
        self.assertIsNotNone(capa)

    def test_el_cierre_sigue_aceptando_marca(self):
        """Con `marca` todo sigue igual (no se rompe lo que funcionaba)."""
        e = {"tipo": "final", "from": 0.0, "to": 3.0,
             "marca": "DragonJAR",
             "at": {"lema": 1.0, "boton": 1.6}}
        escena = R.completar_escena(dict(e))
        capa = R.sc_final(R.Ctx(), escena, 2.0)
        self.assertIsNotNone(capa)


class TestAperturaLegible(unittest.TestCase):
    def _apertura(self, cambio, p1, p2, texto1=("Tu pyme tambien es",)):
        return {"tipo": "apertura", "from": 0.0, "to": 8.0,
                "texto1": list(texto1), "texto2": ["unaPyme"],
                "at": {"cambio": cambio, "p1": list(p1), "p2": list(p2)}}

    def test_el_cambio_se_corre_para_que_se_pueda_leer(self):
        """Si la 1.a frase se cambia antes de poder leerse, el cambio se corre."""
        # la 1.a frase entra en 0.1 y el cambio es a 0.9: apenas 0.8 s
        e = self._apertura(0.9, [0.1], [0.95])
        ajustada = R.completar_escena(dict(e))
        cambio = ajustada["at"]["cambio"]
        self.assertGreater(cambio, 0.9,
                           "el cambio no se corrio: la 1.a frase se lee en "
                           f"{cambio - 0.1 - 0.45:.2f} s")
        # y la 2.a frase se corre con el (si no, se solaparian)
        self.assertGreaterEqual(ajustada["at"]["p2"][0], cambio,
                                "la 2.a frase no se corrio con el cambio")

    def test_un_cambio_ya_generoso_no_se_toca(self):
        """Si ya hay tiempo de lectura, no se toca nada."""
        e = self._apertura(5.0, [0.1], [5.2])
        ajustada = R.completar_escena(dict(e))
        self.assertEqual(ajustada["at"]["cambio"], 5.0,
                         "un cambio que ya daba tiempo de lectura se movio")

    def test_el_cambio_no_se_pasa_del_final(self):
        """El margen manda: si no cabe, el cambio se queda donde estaba."""
        e = self._apertura(0.9, [0.1], [0.95])
        e["to"] = 1.5          # escena corta: no hay margen
        ajustada = R.completar_escena(dict(e))
        self.assertLessEqual(ajustada["at"]["cambio"], e["to"],
                             "el cambio se paso del final de la escena")


if __name__ == "__main__":
    unittest.main()
