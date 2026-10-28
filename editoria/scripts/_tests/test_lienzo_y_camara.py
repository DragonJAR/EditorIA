#!/usr/bin/env python3
"""Tests del lienzo lleno y de la camara que se nota.

QUE PROTEGE

1. LLENAR EL LIENZO: `escala_segura` solo encogia. Una escena con poco
   contenido (un titular corto, unas pildoras) se quedaba en una franja del
   9:16 y el resto era fondo. La misma medicion, en el otro sentido, la hace
   crecer (con tope `LLENA_MAX`) y la centra en la zona segura; una escena
   que ya la llena no se toca. Crecida, sigue DENTRO de la zona segura.

2. LA CAMARA: el push-in era de 1 %/s con tope 5 %: invisible. Ahora empuja
   un `EMPUJE` perceptible a lo largo de la escena, con las mismas
   exenciones (overlays, escenas con camara propia, `respira: false`).

Run with: python3 -m unittest discover -s scripts/_tests
"""

import copy
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, os.path.join(SCRIPTS, "ffmpeg_tools"))


def _muestra(tipo):
    with open(os.path.join(SCRIPTS, "escenas_muestra.json"), encoding="utf-8") as fh:
        e = copy.deepcopy(json.load(fh)["escenas"][tipo])
    e["tipo"] = tipo
    return e


class TestLienzo(unittest.TestCase):
    def setUp(self):
        import render_plan as R
        R.formato(1080, 1920)
        R.aplicar_globales({"escenas": []})
        R._ESCALA.clear()
        self.R = R
        self.ctx = R.Ctx()

    def _tinta(self, capa):
        return capa.split()[3].point(lambda v: 255 if v > 110 else 0).getbbox()

    def test_una_escena_chica_crece_hasta_el_tope_y_queda_centrada(self):
        R = self.R
        e = R.completar_escena({"tipo": "pildoras", "from": 0.0, "to": 3.5,
                                "texto": ["Hola"]}, 0)
        g, dy = R.llenado(self.ctx, e, 0)
        self.assertGreater(g, 1.05, "una escena chica tiene que crecer")
        self.assertLessEqual(g, R.LLENA_MAX)
        self.assertLessEqual(R.escala_segura(self.ctx, e, 0), 1.0,
                             "escala_segura sigue siendo la red: nunca pasa de 1")
        # crecida y con la camara al maximo (fin de la escena), dentro y centrada
        t = e["to"] - 0.05
        bb = self._tinta(R.encuadrar(self.ctx, e, 0, t, R.pintar(self.ctx, e, t).copy()))
        zx0, zy0, zx1, zy1 = R.caja_segura()
        self.assertGreaterEqual(bb[0], zx0 - 1)
        self.assertLessEqual(bb[2], zx1 + 1)
        self.assertGreaterEqual(bb[1], zy0 - 1)
        self.assertLessEqual(bb[3], zy1 + 1)
        self.assertLess(abs((bb[1] + bb[3]) / 2 - (zy0 + zy1) / 2), 0.03 * R.H,
                        "la escena crecida tiene que quedar centrada en la zona segura")

    def test_una_escena_llena_no_se_toca(self):
        R = self.R
        for i, tipo in enumerate(("ranking", "bars", "hoy")):
            e = R.completar_escena(_muestra(tipo), i)
            with self.subTest(tipo=tipo):
                self.assertEqual(R.llenado(self.ctx, e, i), (1.0, 0.0))

    def test_los_overlays_y_la_zona_declarada_no_crecen(self):
        R = self.R
        e = R.completar_escena({"tipo": "pildoras", "from": 0.0, "to": 3.5,
                                "texto": ["Hola"], "zona": [300, 800, 780, 1000]}, 0)
        self.assertEqual(R.llenado(self.ctx, e, 0), (1.0, 0.0))
        e = R.completar_escena(_muestra("rotulo_inferior"), 1)
        self.assertEqual(R.llenado(self.ctx, e, 1), (1.0, 0.0))

    def test_el_cuerpo_de_hoy_y_el_cartel_se_leen_en_un_movil(self):
        """El cuerpo de las tarjetas de `hoy` ya no va al piso de la escala,
        y el cartel arranca en un tamano de cartel."""
        src = open(os.path.join(SCRIPTS, "render_plan.py"), encoding="utf-8").read()
        hoy = src.split("\ndef sc_hoy(", 1)[1].split("\ndef ", 1)[0]
        self.assertFalse('ESCALA["nota"]' in hoy, "el detalle de hoy no va a la letra minima")
        cartel = src.split("\ndef sc_cartel(", 1)[1].split("\ndef ", 1)[0]
        self.assertFalse('e.get("tam", 52)' in cartel, "el cartel arranca en 52 px")


class TestCamara(unittest.TestCase):
    def setUp(self):
        import render_plan as R
        R.formato(1080, 1920)
        R.aplicar_globales({"escenas": []})
        self.R = R

    def test_el_push_in_se_nota(self):
        R = self.R
        e = {"tipo": "titular", "from": 2.0, "to": 6.0}
        f_fin = R.respiracion(e, e["to"])[0]
        self.assertGreaterEqual(f_fin, 1.05, "un push-in de menos del 5 % no se ve")
        self.assertLessEqual(f_fin, 1 + R.EMPUJE + 1e-9)
        self.assertAlmostEqual(R.respiracion(e, e["from"])[0], 1.0, places=6)
        # despues del corte (la salida se solapa con la siguiente) no sigue empujando
        self.assertAlmostEqual(R.respiracion(e, e["to"] + 0.4)[0], f_fin, places=6)

    def test_el_push_in_es_monotono_y_funcion_pura_de_t(self):
        R = self.R
        e = {"tipo": "titular", "from": 0.0, "to": 4.0}
        fs = [R.respiracion(e, i * 0.1)[0] for i in range(41)]
        self.assertEqual(fs, sorted(fs), "el push-in no puede ir y volver")
        self.assertEqual(fs, [R.respiracion(e, i * 0.1)[0] for i in range(41)])

    def test_el_push_in_no_saca_una_escena_llena_de_la_zona_segura(self):
        """Una escena que ya llena la zona segura arranca mas abierta y el
        push-in llega a su encaje: al final sigue dentro (antes se salia
        ~20 px por los lados en el ultimo cuadro)."""
        R = self.R
        R._ESCALA.clear()
        ctx = R.Ctx()
        e = R.completar_escena(_muestra("ranking"), 0)
        f0 = R.respiracion(e, e["from"])[0]
        t = e["to"] - 0.05
        bb = R.encuadrar(ctx, e, 0, t, R.pintar(ctx, e, t).copy()).split()[3] \
            .point(lambda v: 255 if v > 110 else 0).getbbox()
        zx0, zy0, zx1, zy1 = R.caja_segura()
        self.assertGreaterEqual(bb[0], zx0 - 2)
        self.assertLessEqual(bb[2], zx1 + 2)
        self.assertGreaterEqual(R.respiracion(e, t)[0] / f0, 1.05,
                                "la razon del push-in tiene que seguir notandose")

    def test_las_exenciones_siguen(self):
        R = self.R
        for tipo in sorted(R.CAMARA_PROPIA):
            self.assertEqual(R.respiracion({"tipo": tipo, "from": 0.0, "to": 4.0}, 3.0),
                             (1.0, 0.0, 0.0))
        self.assertEqual(R.respiracion({"tipo": "titular", "from": 0.0, "to": 4.0,
                                        "respira": False}, 3.0), (1.0, 0.0, 0.0))


if __name__ == "__main__":
    unittest.main()
