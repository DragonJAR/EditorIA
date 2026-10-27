#!/usr/bin/env python3
"""Tests de la RONDA 13: la cadena de estados y los iconos de linea.

QUE PROTEGE

1. Los ICONOS DE LINEA: son TRAZOS, no glifos. Un glifo depende de que la
   fuente lo tenga ("✓" sale como caja vacia en muchas); un trazo se dibuja
   siempre. La escena `cadena` es de las primeras que los necesita.

2. El CONECTOR punteado une los nodos: es lo que dice que es una SECUENCIA
   (una lista de casillas, `constancia`, no dice eso). Sus medidas estan
   medidas sobre el reel de referencia (guiones de 10 px, hueco de 12).

3. El nodo ACTIVO se distingue del PENDIENTE por el borde y el icono: un
   blanco contra un gris. Si los dos se dibujaran igual, la pieza contaria
   una historia que no cuenta.

Run with: python3 -m unittest discover -s scripts/_tests
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)


class TestIconosDeLinea(unittest.TestCase):
    """Los iconos se DIBUJAN (no son glifos)."""

    def setUp(self):
        import render_plan as R
        R.formato(1080, 1920)
        self.R = R
        from PIL import Image, ImageDraw
        self.img = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.img)

    def _puntos(self, nombre, s=34, color=(255, 255, 255, 255)):
        self.R.icono_linea(self.d, nombre, 200, 200, s, color)
        return self.img.convert("RGB")

    def test_el_globo_es_un_circulo_con_una_elipse_y_la_linea_del_ecuador(self):
        """MEDIDO en el reel: circulo de 69 px, elipse vertical de 20 y el
        ecuador. El icono tiene que tener TRAZOS en los cuatro puntos.

        Se miran los puntos DIAGONALES (a 45 grados): son del circulo
        exterior y no los toca ni la elipse (que es estrecha) ni el ecuador
        (que es horizontal). Con los cardinales, la elipse y el ecuador
        taparian al circulo y el test pasaria con el circulo sin dibujar.
        """
        img = self._puntos("globo")
        px = img.load()
        k = 0.707 * 34
        for dx, dy in ((k, -k), (-k, -k), (k, k), (-k, k)):
            # el trazo se rasteriza a 45 grados: se busca tinta en el entorno,
            # no en el punto exacto (un px de diferencia es la rasterizacion)
            hay = any(min(px[x, y]) > 180
                      for x in range(int(200 + dx) - 2, int(200 + dx) + 3)
                      for y in range(int(200 + dy) - 2, int(200 + dy) + 3))
            self.assertTrue(hay,
                            f"el globo no tiene circulo en ({dx:.0f},{dy:.0f})")
        # la elipse vertical: mas tinta en el centro que en los costados
        centro = sum(1 for y in range(190, 210) for x in range(196, 204)
                     if min(px[x, y]) > 200)
        self.assertGreater(centro, 20, "la elipse vertical del globo no esta")
        # el ecuador: la fila del centro lleva la linea entera
        fila = sum(1 for x in range(180, 220) if min(px[x, 200]) > 180)
        self.assertGreater(fila, 30, "el ecuador del globo no esta")

    def test_la_alerta_es_un_triangulo_con_signo(self):
        img = self._puntos("alerta")
        px = img.load()
        # el vertice arriba
        self.assertGreater(min(px[200, 170]), 200, "el triangulo no tiene vertice")
        # la base abajo, a los lados
        self.assertGreater(min(px[200 - 28, 229]), 150, "falta la base izquierda")
        self.assertGreater(min(px[200 + 28, 229]), 150, "falta la base derecha")
        # el signo: una barra vertical
        self.assertGreater(min(px[200, 200]), 150, "falta la barra del signo")

    def test_cada_icono_dibuja_algo(self):
        """Un icono desconocido NO es un hueco: se dibuja el borde de una
        ficha, para que se vea que falta (y no un hole silencioso)."""
        for nombre in ("codigo", "globo", "alerta", "lupa", "reloj", "inventado"):
            img = self._puntos(nombre)
            pix = list(img.getdata())
            self.assertTrue(any(min(p) > 120 for p in pix),
                            f"el icono '{nombre}' no dibujo nada")


class TestLineaDiscontinua(unittest.TestCase):
    """El conector: guiones de 10 px con 12 de hueco (medido)."""

    def setUp(self):
        import render_plan as R
        R.formato(1080, 1920)
        self.R = R
        from PIL import Image, ImageDraw
        self.img = Image.new("RGBA", (400, 120), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.img)

    def test_los_guiones_miden_diez_y_el_hueco_doce(self):
        # 198 = 9 pasos completos (22 cada uno): el ultimo guion no queda
        # cortado por el borde (en el reel el ultimo sale de 2 px: el
        # conector se corta en el nodo, no se estira)
        self.R.linea_discontinua(self.d, 0, 198, 60, (255, 255, 255, 255),
                                 grosor=3, largo=10, hueco=12)
        px = self.img.convert("RGB").load()
        fila = [x for x in range(400) if min(px[x, 60]) > 120]
        runs = []
        s = p = fila[0]
        for x in fila[1:]:
            if x != p + 1:
                runs.append((s, p))
                s = x
            p = x
        runs.append((s, p))
        self.assertEqual(len(runs), 9, f"deberian salir 9 guiones, salen {len(runs)}")
        for a, b in runs:
            self.assertEqual(b - a + 1, 10, f"el guion mide {b - a + 1}, no 10")
        for i in range(len(runs) - 1):
            hueco = runs[i + 1][0] - runs[i][1] - 1
            self.assertEqual(hueco, 12, f"el hueco mide {hueco}, no 12")


class TestCadenaDeEstados(unittest.TestCase):
    """La escena: N nodos con icono, unidos por el conector."""

    def setUp(self):
        import render_plan as R
        R.formato(1080, 1920)
        self.R = R
        self.ctx = R.Ctx()

    def _pintar(self, e, t):
        e = self.R.completar_escena(e, 0)
        return self.R.pintar(self.ctx, e, t)

    def _escena(self, n=3, activo=True):
        icons = ["codigo", "globo", "alerta"][:n]
        return {"tipo": "cadena", "from": 0.0, "to": 6.0,
                "kicker": "LO QUE VIO KEVIN",
                "items": [{"icono": i, "titulo": "Nodo %d" % (k + 1),
                           "sub": "SUB", "activo": activo}
                          for k, i in enumerate(icons)],
                "at": {"item0": 0.3, "item1": 0.7, "item2": 1.1}}

    # ---- medicion de la escena -------------------------------------------
    def _nodos(self, img):
        """(x0, x1, y_medio) de cada nodo: sus bordes BLANCOS.

        El borde de la caja confirmada es blanco y vertical (140 px); el
        texto de mas abajo no llega a eso. Se buscan las columnas con una
        tira larga de blanco y se agrupan de dos en dos (izq, der).
        """
        px = img.load()
        w, h = img.size
        y0, y1 = int(h * 0.50), h
        cols = []
        for x in range(w):
            n = sum(1 for y in range(y0, y1) if min(px[x, y]) > 225)
            if n > 100:
                cols.append(x)
        grupos = []
        for x in cols:
            if grupos and x - grupos[-1][-1] <= 3:
                grupos[-1].append(x)
            else:
                grupos.append([x])
        # las columnas salen por parejas: el borde izquierdo y el derecho de
        # cada caja. La fila del nodo: el BORDE superior y el inferior son
        # las dos filas con mas blanco dentro de la caja; el icono se queda
        # por debajo de ese umbral.
        boxes = []
        for i in range(0, len(grupos) - 1, 2):
            x0, x1 = min(grupos[i]), max(grupos[i + 1])
            filas = [y for y in range(y0, y1)
                     if sum(1 for x in range(x0 + 12, x1 - 12)
                            if min(px[x, y]) > 225) > 90]
            if not filas:
                continue
            boxes.append((x0, x1, min(filas), max(filas)))
        return boxes

    def _cuenta(self, img, box, lo, hi, margen=22):
        """Pixeles del rango [lo, hi] en el INTERIOR de la caja (el icono)."""
        px = img.load()
        x0, x1, yt, yb = box
        return sum(1 for y in range(int(yt) + 15, int(yb) - 15)
                   for x in range(int(x0) + margen, int(x1) - margen)
                   if lo <= min(px[x, y]) <= hi)

    def test_el_conector_une_los_nodos(self):
        """LOS NODOS ESTAN UNIDOS: entre dos nodos hay trazos GRISES en la
        linea del nodo (el conector no es blanco: el blanco es el nodo)."""
        img = self._pintar(self._escena(), 4.0).convert("RGB")
        boxes = self._nodos(img)
        self.assertGreaterEqual(len(boxes), 2, "se esperaban dos nodos")
        x0, x1, yt, yb = boxes[0]
        y = (yt + yb) // 2          # la linea media del nodo
        px = img.load()
        entre = [x for x in range(int(x1) + 5, int(boxes[1][0]) - 5)
                 if 90 <= min(px[x, y]) <= 175]
        self.assertGreater(len(entre), 4,
                           "no hay conector entre los nodos: la cadena no "
                           "parece una secuencia")

    def test_el_nodo_activo_lleva_el_icono_blanco_y_el_pendiente_gris(self):
        """El activo lleva el ICONO en blanco dentro de la caja; el
        pendiente, el mismo icono en gris.

        Es lo que separa "esto ya paso" de "esto sigue en juego": si los dos
        se dibujan igual, la pieza cuenta una historia que no cuenta.

        La prueba es DIFERENCIAL: el MISMO nodo en las dos versiones, para
        que la caja (que no cambia) no pueda tapar la diferencia.
        """
        activa = self._pintar(self._escena(activo=True), 4.0).convert("RGB")
        pendiente = self._pintar(self._escena(activo=False), 4.0).convert("RGB")
        boxes = self._nodos(activa)
        self.assertGreaterEqual(len(boxes), 1, "no se ve ningun nodo")
        caja = boxes[0]
        # el ACTIVO: tinta blanca DENTRO de la caja (el icono)
        blanco_act = self._cuenta(activa, caja, 230, 255)
        self.assertGreater(blanco_act, 200,
                           "el nodo activo tiene que llevar el icono en blanco")
        # el PENDIENTE: en la MISMA caja, el icono en gris
        gris_pend = self._cuenta(pendiente, caja, 90, 175)
        self.assertGreater(gris_pend, 100,
                           "el nodo pendiente tiene que llevar el icono en gris")
        blanco_pend = self._cuenta(pendiente, caja, 230, 255)
        self.assertLess(blanco_pend, 60,
                        "el nodo pendiente no puede llevar el icono en blanco")

    def test_los_nodos_entran_uno_a_uno(self):
        """Al principio hay menos tinta que despues (la cadena se arma)."""
        pronto = self._pintar(self._escena(), 0.45)
        tarde = self._pintar(self._escena(), 4.0)

        def tinta(capa):
            px = capa.convert("RGB")
            w, h = px.size
            p = px.load()
            return sum(1 for y in range(int(h * 0.70), int(h * 0.95))
                       for x in range(w) if min(p[x, y]) > 90)

        self.assertLess(tinta(pronto), tinta(tarde),
                        "la cadena tiene que armarse nodo a nodo")

    def test_el_panel_no_se_sale_de_la_zona_segura(self):
        """El panel vive dentro de la zona segura: si no, el motor entero se
        encoge y la pieza pierde el sitio."""
        R = self.R
        R._ESCALA.clear()
        ctx = self.ctx
        e = R.completar_escena(self._escena(), 0)
        f = R.escala_segura(ctx, e, 0)
        self.assertGreater(f, 0.995,
                           "la escena tiene que caber en la zona segura sin encogerse")


if __name__ == "__main__":
    unittest.main()
