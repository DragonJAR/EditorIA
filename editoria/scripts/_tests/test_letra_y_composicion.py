#!/usr/bin/env python3
"""Tests de la medicion de la letra y de la puerta de composicion.

La letra se mide EN REPOSO: un elemento que entra con resorte pasa por
muchos tamanos y medir "el mas chico que se vio" castigaba la animacion.
La puerta de entrega tiene que aplicar la misma medicion que la rubrica
de premios, o una aprueba lo que la otra rechaza.

Run with: python3 -m unittest discover -s SKILL/scripts/_tests
"""

import os
import sys
import unittest
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)

import medir_animacion as MA   # noqa: E402
import qa_entrega as QA        # noqa: E402


class TestLetraEnReposo(unittest.TestCase):
    """El tamano con el que el texto SE QUEDA, no el que pasa durante la entrada."""

    def test_el_boton_que_crece_no_cuenta_menor(self):
        # un boton que entra de 0 a 40 px: durante la entrada dibuja a 21 px
        cnt = Counter({21: 1, 22: 1, 25: 1, 30: 1, 38: 1, 39: 2, 40: 80})
        self.assertEqual(MA._letra_en_reposo({"el.boton": cnt}), 40)

    def test_el_slam_que_aterriza_grande_no_cuenta_mayor(self):
        # el gigante cae de 1,6x a 1,0x: el tamano en reposo es el pequeno
        cnt = Counter({280: 1, 260: 1, 240: 1, 220: 1, 200: 2, 180: 90})
        self.assertEqual(MA._letra_en_reposo({"OWASP": cnt}), 180)

    def test_texto_estable_toma_su_tamano(self):
        cnt = Counter({30: 50})
        self.assertEqual(MA._letra_en_reposo({"pie": cnt}), 30)

    def test_una_animacion_que_cabe_en_la_ventana_no_confunde_la_letra(self):
        """La ventana de reposo (la segunda mitad de la escena) puede caer
        ENTERA dentro de la animacion de entrada de un texto que entra tarde
        (un boton al final de una escena corta).

        La mediana daba entonces un tamano de paso (24 px) en vez del estado
        en que el texto se queda (36 px): la pieza se rechazaba por su
        animacion, no por su tipografia. El ULTIMO dibujo es el estado en el
        que el texto se queda, que es lo que la funcion dice medir."""
        cnt = Counter({8: 1, 10: 1, 17: 1, 24: 1, 29: 1, 33: 1, 36: 2})
        ultimos = {"dragonjar.org": 36}
        self.assertEqual(MA._letra_en_reposo({"dragonjar.org": cnt}, ultimos), 36)
        # sin el dato del ultimo dibujo, la mediana de siempre (compatibilidad)
        self.assertEqual(MA._letra_en_reposo({"dragonjar.org": cnt}), 24)

    def test_un_texto_que_se_queda_pequeno_sigue_siendo_pequeno(self):
        """La regla nueva no perdona a un texto que de verdad se queda
        pequeno: solo cambia QUE frame se mira (el ultimo, no la mediana)."""
        cnt = Counter({36: 2, 12: 3})
        self.assertEqual(MA._letra_en_reposo({"x": cnt}, {"x": 12}), 12)

    def test_el_menor_entre_textos_manda(self):
        tamanos = {"titular": Counter({110: 50}), "pie": Counter({28: 50})}
        self.assertEqual(MA._letra_en_reposo(tamanos), 28)

    def test_un_texto_que_entra_al_final_no_se_juzga(self):
        # visto menos de 3 frames: entro y no llego a asentar -> no cuenta
        tamanos = {"nuevo": Counter({18: 2}), "pie": Counter({30: 50})}
        self.assertEqual(MA._letra_en_reposo(tamanos), 30)

    def test_sin_textos_devuelve_cero(self):
        self.assertEqual(MA._letra_en_reposo({}), 0)

    def test_el_piso_del_motor_es_26(self):
        self.assertEqual(MA.LETRA_MIN, 26)

    def test_un_simbolo_no_es_una_letra(self):
        """El "✓" de una tarjeta a 14 px es un check, no texto ilegible.

        Los numeros si cuentan (son datos); los signos sueltos no.
        """
        cnt = Counter({14: 50})
        self.assertEqual(MA._letra_en_reposo({"✓": cnt}), 0)
        self.assertEqual(MA._letra_en_reposo({"0,1": cnt}), 14)
        self.assertEqual(MA._letra_en_reposo({"·": cnt}), 0)


class TestDefectosComposicion(unittest.TestCase):
    """La puerta de entrega y la rubrica de premios miden lo mismo."""

    def test_una_pieza_sana_no_tiene_fallos(self):
        self.assertEqual(QA._defectos_composicion(30, 1.0, []), [])

    def test_la_letra_chica_falla(self):
        fallos = QA._defectos_composicion(21, 1.0, [])
        self.assertEqual(len(fallos), 1)
        self.assertIn("letra mínima 21 px", fallos[0])

    def test_la_zona_en_su_piso_falla(self):
        fallos = QA._defectos_composicion(40, 0.70, [])
        self.assertEqual(len(fallos), 1)
        self.assertIn("piso de la zona segura", fallos[0])

    def test_encogerse_un_poco_no_falla(self):
        # encogerse es la senal de que el copy es largo, no un defecto de entrega
        self.assertEqual(QA._defectos_composicion(40, 0.91, []), [])

    def test_los_solapes_fallan(self):
        fallos = QA._defectos_composicion(40, 1.0, ["a", "b"])
        self.assertEqual(len(fallos), 1)
        self.assertIn("2 textos se pisan", fallos[0])

    def test_los_tres_fallos_juntos(self):
        fallos = QA._defectos_composicion(18, 0.70, ["a"])
        self.assertEqual(len(fallos), 3)

    def test_letra_desconocida_no_falla(self):
        # sin plan medido no hay letra: no se inventa un fallo
        self.assertEqual(QA._defectos_composicion(0, 1.0, []), [])


class TestPasoComposicion(unittest.TestCase):
    """El paso de la puerta: mide el plan y dice POR QUE no pudo, si no pudo."""

    def test_un_plan_que_no_se_puede_medir_dice_el_motivo(self):
        import json
        import subprocess
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            plan = os.path.join(d, "plan.json")
            with open(plan, "w", encoding="utf-8") as f:
                json.dump({"duracion": 2.0, "tamano": "1080x1920",
                           "escenas": [{"tipo": "final", "from": 0.0, "to": 2.0}]},
                          f, ensure_ascii=False)
            video = os.path.join(d, "v.mp4")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                            "color=c=black:s=320x240:d=2:r=24", "-c:v", "libx264",
                            "-pix_fmt", "yuv420p", video], check=True, timeout=180)
            paso = QA._paso_composicion(plan, video)
            self.assertFalse(paso["ok"])
            self.assertIn("marca", paso["detalle"],
                          "el motivo del motor tiene que llegar al agente")


if __name__ == "__main__":
    unittest.main()
