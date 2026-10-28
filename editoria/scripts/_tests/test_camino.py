#!/usr/bin/env python3
"""Tests de la RONDA 15: el trazado de luz y la escena `camino`.

QUE PROTEGE

1. `trazado` es LA PRIMITIVA: un solo trazo que dibuja (la linea que
   revela el logotipo, llena la barra, se enrosca, baja bajo el lema...). Se
   dibuja a SI MISMA (una capa propia y se compone), porque con ImageDraw el
   alfa REEMPLAZA el pixel y una cola que se apaga borraria lo que hubiera
   debajo.

2. La escena `camino` enciende las estaciones CUANDO LA CABEZA LAS PASA: si
   se encendieran todas a la vez, la pieza contaria una historia que no
   cuenta.

3. La camara vuela con la cabeza: es lo que mantiene los cuadros vivos (un
   trazo que se arrastra despacio lo lee el medidor como cuadro congelado:
   medido, 37 % de la pieza "muerta" sin el vuelo, 0 % con el).

Run with: python3 -m unittest discover -s scripts/_tests
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)


class TestTrazado(unittest.TestCase):
    """La primitiva: un trazo de luz."""

    def setUp(self):
        import render_plan as R
        R.formato(1080, 1920)
        self.R = R
        from PIL import Image
        self.Image = Image
        self.img = Image.new("RGBA", (400, 200), (0, 0, 0, 0))

    def _tinta(self, capa):
        return sum(1 for p in capa.convert("RGB").getdata() if sum(p) > 90)

    def test_sin_progreso_no_dibuja_nada(self):
        self.R.trazado(self.img, [(20, 100), (380, 100)], (255, 255, 255, 255),
                       progreso=0.0)
        self.assertEqual(self._tinta(self.img), 0,
                         "sin progreso no hay trazo: la linea aun no ha llegado")

    def test_el_progreso_dibuja_hasta_donde_llega(self):
        pts = [(20, 100), (380, 100)]
        self.R.trazado(self.img, pts, (255, 255, 255, 255), grosor=6,
                       progreso=0.25)
        corto = self._tinta(self.img)
        self.img2 = self.Image.new("RGBA", self.img.size, (0, 0, 0, 0))
        self.R.trazado(self.img2, pts, (255, 255, 255, 255), grosor=6,
                       progreso=1.0)
        largo = self._tinta(self.img2)
        self.assertGreater(largo, corto * 1.5,
                           "a mas progreso, mas trazo: la linea se escribe")
        # y lo escrito esta a la IZQUIERDA (la cabeza va hacia adelante)
        px = self.img2.convert("RGB").load()
        self.assertGreater(sum(1 for x in range(300) if sum(px[x, 100]) > 90), 0,
                           "el tramo final tiene que estar escrito")
        self.assertEqual(sum(1 for x in range(0, 15) if sum(px[x, 100]) > 90), 0,
                         "el tramo inicial ya paso: no se dibuja al reves")

    def test_la_cola_se_apaga(self):
        """La cola del trazo se apaga: el final tiene menos ALFA.

        OJO: el desvanecido vive en el canal ALFA, no en el RGB (convertir a
        RGB tira el alfa y el final pareceria igual de opaco que la cabeza).
        """
        self.R.trazado(self.img, [(20, 100), (380, 100)], (255, 255, 255, 255),
                       grosor=6, progreso=1.0, desvanecer=0.4)
        px = self.img.split()[3].load()      # el canal ALFA
        inicio = sum(px[x, 100] for x in range(30, 60))
        final = sum(px[x, 100] for x in range(340, 370))
        self.assertGreater(inicio, final,
                           "la cola tiene que estar mas apagada que la cabeza")

    def test_la_cola_de_colores_cambia_el_trazado(self):
        """Con `cola`, la linea va cambiando de color a lo largo."""
        img = self.Image.new("RGBA", (400, 200), (0, 0, 0, 0))
        self.R.trazado(img, [(20, 100), (380, 100)], (255, 0, 0, 255),
                       grosor=8, progreso=1.0,
                       cola=[(255, 0, 0, 255), (0, 0, 255, 255)])
        px = img.convert("RGB").load()
        rojo = sum(1 for x in range(30, 60) if px[x, 100][0] > 150)
        azul = sum(1 for x in range(340, 370) if px[x, 100][2] > 150)
        self.assertGreater(rojo, 0, "el principio del trazo es del primer color")
        self.assertGreater(azul, 0, "el final del trazo es del ultimo color")


class TestCamino(unittest.TestCase):
    """La escena: el camino con sus estaciones."""

    def setUp(self):
        import render_plan as R
        R.formato(1080, 1920)
        self.R = R
        self.ctx = R.Ctx()

    def _pintar(self, e, t):
        e = self.R.completar_escena(e, 0)
        return self.R.pintar(self.ctx, e, t).convert("RGB")

    def _escena(self, **extra):
        e = {"tipo": "camino", "from": 0.0, "to": 6.0, "ruta": "recta",
             "estaciones": [{"titulo": "Uno", "icono": "1"},
                            {"titulo": "Dos", "icono": "2"},
                            {"titulo": "Tres", "icono": "3"},
                            {"titulo": "Cuatro", "icono": "4"}],
             "at": {"estacion0": 0.2, "estacion1": 0.8,
                    "estacion2": 1.4, "estacion3": 2.0}}
        e.update(extra)
        return e

    def _estaciones(self, img):
        """(x, y) del centro de cada estacion (la tinta clara mas fuerte)."""
        w, h = img.size
        px = img.load()
        # el acento de la pieza: sin pack es el azul neutro
        ar, ag, ab = self.R.ACENTO[:3]
        puntos = []
        for x in range(0, w, 2):
            for y in range(int(h * 0.30), int(h * 0.62), 2):
                r, g, b = px[x, y]
                if abs(r - ar) < 70 and abs(g - ag) < 70 and abs(b - ab) < 70:
                    puntos.append((x, y))
        return puntos

    def test_las_estaciones_se_encienden_por_orden(self):
        """Al principio la ultima estacion esta APAGADA; al final, encendida.

        No basta con "hay tinta de acento": si todas se encendieran a la vez,
        la pieza contaria una historia que no cuenta. Se mira la ultima
        estacion (la derecha): al principio no hay acento ahi."""
        R = self.R
        R.MARCA_NOMBRE = None
        # t=2,5: las cuatro estaciones ya han entrado, pero la cabeza solo
        # hapassed las dos primeras: las de la derecha siguen apagadas
        temprano = self._estaciones(self._pintar(self._escena(), 2.5))
        tarde = self._estaciones(self._pintar(self._escena(), 5.5))
        self.assertTrue(temprano, "no hay tinta de acento")
        w = self._pintar(self._escena(), 2.5).size[0]
        derecha_temprano = [p for p in temprano if p[0] > w * 0.53]
        derecha_tarde = [p for p in tarde if p[0] > w * 0.53]
        self.assertEqual(derecha_temprano, [],
                         "las estaciones de la derecha estan encendidas antes "
                         "de que la cabeza las pase")
        self.assertTrue(derecha_tarde,
                        "al final las estaciones de la derecha tienen que "
                        "estar encendidas")

    def test_la_camara_de_la_pieza_puede_volar(self):
        """El vuelo es de la PIEZA (el global `camara`), no de la escena: asi
        el mundo puede salirse del encuadre sin que la zona segura encoja la
        escena sola (medido: 0,72 con el vuelo dentro de la escena).

        Y el vuelo es un PANEO + un ZOOM: la camara se desplaza de lado."""
        R = self.R
        R.MARCA_NOMBRE = None
        plan = {"camara": {"z0": 1.0, "z1": 1.0, "x0": 300, "x1": -300},
                "escenas": [{"tipo": "typewriter", "from": 0.0, "to": 6.0,
                             "texto": "hola"}]}
        R.aplicar_globales(plan)
        e = R.completar_escena(plan["escenas"][0], 0)
        izq = R.componer(self.ctx, [e], 6.0, 0.5, set()).convert("L")
        der = R.componer(self.ctx, [e], 6.0, 5.5, set()).convert("L")
        # el texto se ha movido de sitio: la camara ha volado
        def _x_de_tinta(img):
            w, h = img.size
            px = img.load()
            xs = [x for y in range(h) for x in range(w) if px[x, y] > 120]
            return min(xs) if xs else -1
        self.assertNotEqual(_x_de_tinta(izq), _x_de_tinta(der),
                            "la camara no se ha movido: el paneo global no "
                            "llega al compositor")

    def test_el_panel_no_se_sale_de_la_zona_segura(self):
        R = self.R
        R._ESCALA.clear()
        e = R.completar_escena(self._escena(), 0)
        f = R.escala_segura(self.ctx, e, 0)
        self.assertGreater(f, 0.995,
                           "el camino tiene que caber en la zona segura")


if __name__ == "__main__":
    unittest.main()
