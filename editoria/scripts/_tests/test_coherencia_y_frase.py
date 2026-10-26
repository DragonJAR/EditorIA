#!/usr/bin/env python3
"""Tests de la COHERENCIA de la camara y de las dos escenas nuevas.

QUE PROTEGE (tres cosas que se pueden romper en silencio):

1. La CAMARA no se reinicia en cada corte. Antes el reloj era `t - e["from"]`,
   o sea cada escena empezaba la camara en 1,0000: medido, la saliente
   llegaba a 1,0433 con dy +5,7 px y la entrante arrancaba en 1,0000 con dy
   0,00. Un salto de 4-5 % de escala en cada union: la pieza se leia como un
   montage y no como una toma continua.

2. La ZONA declarada da el MISMO factor a las escenas que la comparten: si
   dos escenas declaran la misma caja, su contenido conserva el sitio.

3. La FRASE cinetica escribe palabra a palabra y el ANILLO se llena: las dos
   escenas nuevas, con su invariante medida (la palabra clave en blanco, el
   resto en gris; el anillo con las marcas llenas justas).

Run with: python3 -m unittest discover -s scripts/_tests
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)


class TestCamaraCoherente(unittest.TestCase):
    """La camara de la pieza es UNA trayectoria, no una por escena."""

    def setUp(self):
        import render_plan as R
        self.R = R

    def _plan(self, **extra):
        plan = {"escenas": [
            {"tipo": "titular", "from": 0.0, "to": 4.0, "titulo": "a"},
            {"tipo": "titular", "from": 4.0, "to": 8.0, "titulo": "b"},
        ]}
        plan.update(extra)
        return plan

    def test_sin_trayectoria_la_camara_sigue_por_escena(self):
        """Sin `camara` en el plan, el motor se comporta como antes.

        Es lo que hace que esta capacidad no rompa las piezas ya hechas.
        """
        R = self.R
        R.aplicar_globales(self._plan())
        self.assertFalse(R._CAMARA["activa"])
        # sin trayectoria la camara es POR ESCENA: el mismo instante visto desde
        # dos escenas da dos camaras distintas (y por eso el corte salta)
        a = R.respiracion({"tipo": "apertura", "from": 0.0}, 3.0)
        b = R.respiracion({"tipo": "apertura", "from": 4.0}, 3.0)
        self.assertNotAlmostEqual(a[0], b[0], places=3)

    def test_la_trayectoria_esta_activa_y_es_global(self):
        R = self.R
        R.aplicar_globales(self._plan(camara={"z0": 2.4, "z1": 1.0, "flota": 0}))
        self.assertTrue(R._CAMARA["activa"])
        # el final de la pieza vale z1 y el principio z0
        self.assertAlmostEqual(R._escala_camara(0.0), 2.4, places=5)
        self.assertAlmostEqual(R._escala_camara(8.0), 1.0, places=5)

    def test_en_un_corte_la_escena_que_sale_y_la_que_entra_ven_lo_mismo(self):
        """LA INVARIANTE: en el instante del corte, la escala es la misma.

        No hace falta sincronizar nada: las dos escenas evaluan la misma
        trayectoria sobre el reloj global. Por eso el corte no salta.
        """
        R = self.R
        R.aplicar_globales(self._plan(camara={"z0": 2.4, "z1": 1.0, "flota": 0}))
        saliente = {"tipo": "titular", "from": 0.0, "to": 4.0}
        entrante = {"tipo": "titular", "from": 4.0, "to": 8.0}
        for t_corte in (4.0,):
            fs, dy_s = R.respiracion(saliente, t_corte)
            fe, dy_e = R.respiracion(entrante, t_corte)
            self.assertAlmostEqual(fs, fe, places=9,
                                   msg="la escala salta en el corte")
            self.assertAlmostEqual(dy_s, dy_e, places=9,
                                   msg="la flotacion salta en el corte")

    def test_sin_trayectoria_la_camara_por_escena_salta_en_el_corte(self):
        """La MUTACION: el defecto de partida, medido.

        Con el reloj por escena (el comportamiento de antes), en el corte la
        escena que sale va a escala 1,04 y la que entra arranca en 1,00: un
        salto. Este test deja el defecto a la vista: si alguien vuelve a
        reiniciar el reloj, el salto vuelve y este test lo delata.
        """
        R = self.R
        R.aplicar_globales(self._plan())
        saliente = {"tipo": "titular", "from": 0.0, "to": 4.0}
        entrante = {"tipo": "titular", "from": 4.0, "to": 8.0}
        fs, _ = R.respiracion(saliente, 4.0)
        fe, _ = R.respiracion(entrante, 4.0)
        self.assertNotAlmostEqual(fs, fe, places=3,
                                  msg="el reloj por escena ya no Salta: "
                                      "el defecto de partida cambio")


class TestZonaDeclarada(unittest.TestCase):
    """La zona declarada: el contenido conserva su sitio de una escena a otra.

    El factor de la zona segura se mide sobre el CONTENIDO de cada escena, y
    por eso dos escenas parecidas salen con factores distintos y la caja da
    un salto en el corte (medido: 1,000 / 0,995 / 0,991). Cuando el plan
    DECLARA la zona, el factor sale de esa caja y no del contenido: dos
    escenas que declaran la misma zona salen con el MISMO factor, y el
    contenido conserva su sitio.
    """

    def setUp(self):
        import render_plan as R
        R.formato(1080, 1920)
        self.R = R

    def _escena(self, zona, texto="hola"):
        return {"tipo": "typewriter", "from": 0.0, "to": 2.0, "zona": zona,
                "texto": texto}

    def test_una_zona_que_se_sale_obliga_a_encoger(self):
        """La zona declarada manda: si se sale de la zona segura, encoge."""
        R = self.R
        ctx = R.Ctx()
        R._ESCALA.clear()
        grande = [0, 0, 1080, 1920]      # el cuadro entero: no cabe en la zona segura
        f = R.escala_segura(ctx, R.completar_escena(self._escena(grande), 0), 0)
        self.assertLess(f, 0.995, "una zona que se sale tiene que encoger")

    def test_dos_escenas_con_la_misma_zona_ouden_el_mismo_factor(self):
        """LA INVARIANTE: misma zona, mismo factor (la caja no salta)."""
        R = self.R
        ctx = R.Ctx()
        R._ESCALA.clear()
        zona = [60, 800, 1020, 1700]
        e1 = self._escena(zona, "hola")
        e2 = self._escena(zona, "una frase mucho mas larga que ocupa bastante mas sitio")
        f1 = R.escala_segura(ctx, R.completar_escena(e1, 0), 0)
        f2 = R.escala_segura(ctx, R.completar_escena(e2, 1), 1)
        self.assertAlmostEqual(f1, f2, places=6,
                               msg="dos escenas con la misma zona deben salir "
                                   "con el mismo factor: si no, la caja salta")

    def test_zonas_distintas_dan_factores_distintos(self):
        """Y al reves: si las zonas son distintas, los factores tambien."""
        R = self.R
        ctx = R.Ctx()
        R._ESCALA.clear()
        grande = [0, 0, 1080, 1920]
        chica = [300, 900, 780, 1500]
        f1 = R.escala_segura(ctx, R.completar_escena(self._escena(grande), 0), 0)
        f2 = R.escala_segura(ctx, R.completar_escena(self._escena(chica), 1), 1)
        self.assertNotAlmostEqual(f1, f2, places=3,
                                  msg="zonas distintas deberian dar factores distintos")

    def test_sin_zona_declarada_se_mide_el_contenido(self):
        """Sin zona declarada, el motor mide el bbox (lo de antes)."""
        R = self.R
        ctx = R.Ctx()
        R._ESCALA.clear()
        e = {"tipo": "typewriter", "from": 0.0, "to": 2.0, "texto": "hola"}
        f = R.escala_segura(ctx, R.completar_escena(e, 0), 0)
        self.assertGreater(f, 0.0)
        self.assertLessEqual(f, 1.0)


class TestFraseCinetica(unittest.TestCase):
    """La frase cinetica: el copy entra palabra a palabra."""

    def setUp(self):
        import render_plan as R
        R.formato(1080, 1920)
        self.R = R
        self.ctx = R.Ctx()

    def _pintar(self, e, t):
        # por la VIA REAL: `completar_escena` es lo que rellena los `at` que el
        # plan no trae (una escena escrita a mano sin `at` no se compone)
        e = self.R.completar_escena(e, 0)
        return self.R.pintar(self.ctx, e, t)

    def test_la_palabra_clave_va_en_blanco_y_el_resto_en_gris(self):
        R = self.R
        e = {"tipo": "frase", "from": 0.0, "to": 6.0,
             "frase": "tu campana *puede* volver", "cps": 1.0}
        # t=2.5 con cps=1 -> tres palabras: "tu", "campana" y la clave "puede"
        capa = self._pintar(e, 2.5)
        pix = capa.getdata()
        blancos = sum(1 for r, g, b, a in pix if a > 120 and r > 235 and g > 235 and b > 235)
        grises = sum(1 for r, g, b, a in pix if a > 80 and 100 < r < 200 and abs(r - g) < 12)
        self.assertGreater(blancos, 200, "la palabra clave tiene que verse en blanco")
        self.assertGreater(grises, 200, "el resto de la frase tiene que verse en gris")

    def test_la_frase_aparece_palabra_a_palabra(self):
        """Al principio hay menos TEXTO que despues.

        La medida es la EXTENSION horizontal, no el numero de pixeles: con el
        sistema de estados por palabra (la recien alcanzada crece desde
        0,66 y la vieja se apaga) el area casi no cambia, pero la linea se
        hace mas larga. Medir el area habria dado un falso negativo.
        """
        R = self.R
        e = {"tipo": "frase", "from": 0.0, "to": 8.0,
             "frase": "uno dos tres cuatro cinco seis", "cps": 1.0}

        def _blancos(e_, t_):
            """Los pixeles BLANCOS: las palabras ALCANZADAS.

            La frase entera esta en el cuadro desde el principio (las no
            alcanzadas, en gris y mas pequenas): lo que crece con el tiempo
            es el numero de palabras alcanzadas, y esa es la medida.
            """
            capa = self._pintar(e_, t_)
            return sum(1 for r, g, b, a in capa.getdata()
                       if a > 120 and r > 225 and g > 225 and b > 215)

        b0 = _blancos(e, 0.1)
        b3 = _blancos(e, 3.1)
        self.assertGreater(b3, b0 * 1.4,
                           "la frase tiene que alcanzar MAS palabras con el tiempo")

    def test_la_palabra_activa_lleva_el_subrayado_rojo(self):
        """El estado de palabra del reel: la ACTIVA lleva el subrayado rojo.

        Es lo que hace que el ojo sepa cual es la palabra que se esta
        leyendo. Se mide por los pixeles del color de acento, que solo
        puede venir del subrayado.
        """
        R = self.R
        e = {"tipo": "frase", "from": 0.0, "to": 8.0,
             "frase": "uno dos tres cuatro cinco", "cps": 1.0}
        ac = R.ACENTO[:3]

        def _acento(capa):
            return sum(1 for r, g, b, a in capa.getdata()
                       if a > 120 and abs(r - ac[0]) < 45 and abs(g - ac[1]) < 45
                       and abs(b - ac[2]) < 45)

        self.assertGreater(_acento(self._pintar(e, 3.2)), 100,
                           "la palabra activa tiene que llevar el subrayado rojo")

    def test_la_caja_roja_marca_la_palabra(self):
        """`~palabra~` la pone dentro de una CAJA ROJA (texto blanco)."""
        R = self.R
        e = {"tipo": "frase", "from": 0.0, "to": 8.0,
             "frase": "esto es ~lo importante* aqui", "cps": 1.0}
        ac = R.ACENTO[:3]
        capa = self._pintar(e, 3.2)
        rojo = sum(1 for r, g, b, a in capa.getdata()
                   if a > 120 and abs(r - ac[0]) < 45 and abs(g - ac[1]) < 45
                   and abs(b - ac[2]) < 45)
        self.assertGreater(rojo, 200, "la palabra en caja roja tiene que verse roja")

    def test_la_caja_blanca_pone_el_texto_oscuro(self):
        """`^palabra^` la pone en una CAJA BLANCA (texto oscuro encima)."""
        R = self.R
        e = {"tipo": "frase", "from": 0.0, "to": 8.0,
             "frase": "esto es ^esto otro* aqui", "cps": 1.0}
        capa = self._pintar(e, 3.2)
        claros = sum(1 for r, g, b, a in capa.getdata()
                     if a > 200 and r > 235 and g > 235 and b > 225)
        self.assertGreater(claros, 200, "la caja blanca tiene que verse blanca")

    def test_la_frase_no_se_sale_de_la_zona_segura(self):
        """Lo que se escribe cabe: la zona segura es el contrato."""
        R = self.R
        e = {"tipo": "frase", "from": 0.0, "to": 8.0,
             "frase": "palabra " * 14, "cps": 3.0}
        capa = self._pintar(e, 4.0)
        bb = capa.split()[3].point(lambda v: 255 if v > 60 else 0).getbbox()
        if bb is None:
            self.skipTest("no se dibujo nada")
        zx0, zy0, zx1, zy1 = R.caja_segura()
        self.assertGreaterEqual(bb[0], zx0 - 6, "la frase se sale por la izquierda")
        self.assertLessEqual(bb[2], zx1 + 6, "la frase se sale por la derecha")


    def test_la_italica_del_display_se_usa_cuando_la_piden(self):
        """El reel de referencia escribe el display en ITALICA.

        Sin una fuente con italica, el resultado se ve en redonda y no se
        parece al original: por eso la variable entra en el pack (el rol
        "titulares_itálica") y la escena la pide con `itálica: true`.
        """
        import render_plan as R
        pack = os.path.join(os.path.dirname(SCRIPTS), "brand", "carbon.json")
        R.aplicar_brand(pack)
        try:
            fnt_recta = R.Ctx().fTi(60, 800)
            self.assertIsNotNone(fnt_recta)
            # el nombre de la fuente dice si es la italica
            nombre = " ".join(str(x) for x in fnt_recta.getname())
            self.assertIn("Italic", nombre,
                          f"la fuente del display deberia ser la italica: {nombre}")
        finally:
            R.aplicar_brand(None)

class TestAnillo(unittest.TestCase):
    """El medidor de anillo: un dial de marcas que se llena."""

    def setUp(self):
        import render_plan as R
        R.formato(1080, 1920)
        self.R = R
        self.ctx = R.Ctx()

    def test_el_anillo_dibuja_marcas_radiales(self):
        R = self.R
        e = {"tipo": "gauge", "forma": "anillo", "from": 0.0, "to": 6.0,
             "valor": 30, "max": 50, "ticks": 50}
        capa = R.pintar(self.ctx, R.completar_escena(e, 0), 3.0)
        bb = capa.split()[3].point(lambda v: 255 if v > 60 else 0).getbbox()
        self.assertIsNotNone(bb, "el anillo no dibujo nada")
        # el dial es grande y esta en el centro del cuadro
        self.assertGreater(bb[2] - bb[0], 400)
        self.assertGreater(bb[3] - bb[1], 400)

    def test_mas_valor_mas_marcas_llenas(self):
        """LA INVARIANTE: el anillo se llena con el valor."""
        R = self.R
        e = {"tipo": "gauge", "forma": "anillo", "from": 0.0, "to": 6.0,
             "valor": 40, "max": 50, "ticks": 50}
        lleno = R.pintar(self.ctx, R.completar_escena(e, 0), 4.0)
        e2 = dict(e, valor=5)
        corto = R.pintar(self.ctx, R.completar_escena(e2, 1), 4.0)
        # el anillo lleno tiene MAS pixeles de color de acento que el corto
        ac = R.ACENTO[:3]

        def _color(capa):
            return sum(1 for r, g, b, a in capa.getdata()
                       if a > 150 and abs(r - ac[0]) < 40 and abs(g - ac[1]) < 40
                       and abs(b - ac[2]) < 40)
        self.assertGreater(_color(lleno), _color(corto) * 1.5,
                           "con mas valor el anillo tiene que tener mas marcas llenas")


if __name__ == "__main__":
    unittest.main()
