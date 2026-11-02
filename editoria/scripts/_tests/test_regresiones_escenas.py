#!/usr/bin/env python3
"""Regresiones de las escenas del reel (1.11.1): cada test es un defecto visto
en un render real (ERRORES-ESCENAS del reel Binance) que no puede volver.

QUE PROTEGE
 1. `frase`: la palabra activa nunca desaparece al pasar de gris a blanco
    (se leyó «Binance lo confirma» sin el «no») y lo ya dicho no sale de
    pantalla por la ventana.
 2. `pasos` (y toda lista): el `at` propio de cada item manda.
 3. `subrayado`: lee el markup `*clave*` y pasa de dos líneas sin cortar.
 4. `cartel`: el acento cruza espacios y la caja va sobre su palabra.
 5. «Fuente: Fuente: X» y «DRAGONJAR» no vuelven.
 6. `final`: `sobrio` apaga latido y halo.
 7. `cadena` / `constancia`: en 9:16 van en columna, con letra ≥ 28 px y sin
    copy cortado.
 8. el pack DragonJAR: IBM Plex Mono, logotipo para fondo oscuro, dos grises.

Y los bloqueantes de la auditoría visual (copy largo, 1:1, reglas de marca):
 P0-1 un titular largo no tumba el render (orbOpen en 9:16 y 1:1).
 P0-2 lo que no cabe se anota en RECORTES (texto_que_cabe).
 P0-3 los signos del markup no salen literales en texto corrido ni en items,
      y «SELECT * FROM» o «~/home» no se tocan.
 P0-4 una etiqueta de una línea no baja del piso legible: recorta y anota.
 P0-5 un rótulo de dos líneas empuja lo que va debajo (rotulo_extra).
 P1   1:1 compone en columna; `rebote`, `particulas` y `volumen` del pack.

Run with: python3 -m unittest discover -s scripts/_tests
"""
import copy
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
SKILL = os.path.dirname(SCRIPTS)
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, os.path.join(SCRIPTS, "ffmpeg_tools"))


def _muestra(tipo):
    with open(os.path.join(SCRIPTS, "escenas_muestra.json"), encoding="utf-8") as fh:
        e = copy.deepcopy(json.load(fh)["escenas"][tipo])
    e.setdefault("tipo", tipo)
    return e


class _Base(unittest.TestCase):
    ancho, alto = 1080, 1920

    @classmethod
    def setUpClass(cls):
        try:
            import numpy  # noqa: F401
            from PIL import Image  # noqa: F401
        except ImportError:
            raise unittest.SkipTest("sin numpy/PIL")
        import render_plan as R
        cls.R = R
        R.formato(cls.ancho, cls.alto)
        cls.ctx = R.Ctx()

    def setUp(self):
        self.R.formato(self.ancho, self.alto)
        del self.R.RECORTES[:]

    def alfa(self, capa, caja=None):
        import numpy as np
        a = np.asarray(capa.split()[3], dtype=np.int64)
        if caja:
            x0, y0, x1, y1 = (int(v) for v in caja)
            a = a[max(0, y0):y1, max(0, x0):x1]
        return int(a.sum())


class TestFrase(_Base):
    def _e(self, **kw):
        e = {"tipo": "frase", "from": 0.0, "to": 8.0, "cps": 2.0, "tam": 64, "y": 0.4,
             "frase": "TRM Labs lo atribuye a TraderTraitor pero Binance no lo confirma todavía",
             "at": {"rotulo": 0.2}}
        e.update(kw)
        return e

    def tinta(self, capa):
        import numpy as np
        a = np.asarray(capa, dtype=np.int64)
        neutra = (np.abs(a[..., 0] - a[..., 1]) < 24) & (np.abs(a[..., 1] - a[..., 2]) < 24)
        return int(a[..., 3][neutra].sum())

    def test_la_activa_nunca_desaparece(self):
        R = self.R
        e = self._e()
        n = len(e["frase"].split())
        for k in range(1, n):
            t_pal = 0.2 + k / 2.0
            antes = self.tinta(R.sc_frase(self.ctx, e, t_pal - 0.01))
            despues = self.tinta(R.sc_frase(self.ctx, e, t_pal + 0.01))
            # al alcanzar una palabra la tinta del TEXTO no cae (antes caía la
            # de la palabra entera: pasaba de pista gris a alfa 0). El
            # subrayado de acento salta de palabra: se mide solo la tinta neutra
            self.assertGreaterEqual(despues, antes * 0.97, f"palabra {k}: {antes} -> {despues}")

    def test_lo_dicho_no_sale_de_pantalla(self):
        R = self.R
        e = self._e(ventana=3)
        pal, lineas, linea_de, ancho_de, gap, maxw = R._frase_layout(self.ctx, e, 64)
        self.assertGreater(len(pal), 6)
        capa = R.sc_frase(self.ctx, e, 7.9)
        # la primera palabra ("TRM") sigue con tinta al final de la frase
        zx0, _, _, _ = R.caja_segura()
        li = linea_de[0]
        x = zx0 + (maxw - ancho_de[li]) / 2.0 + lineas[li][0][1]
        y_ult = R.y_de_pantalla(e, 7.9, R.vy(0.4))
        y = y_ult + (li - max(linea_de.values())) * 64 * 1.52
        self.assertGreater(self.alfa(capa, (x, y - 10, x + lineas[li][0][2], y + 90)), 2000)

    def test_apagar_conserva_el_teleprompter_estricto(self):
        R = self.R
        sin = self.alfa(R.sc_frase(self.ctx, self._e(ventana=3), 7.9))
        con = self.alfa(R.sc_frase(self.ctx, self._e(ventana=3, apagar=True), 7.9))
        self.assertLess(con, sin)

    def test_marcado_de_varias_palabras(self):
        m = self.R.marcas_de_frase("hay *tres palabras clave* aquí")
        self.assertEqual([x[1] for x in m], [False, True, True, True, False])


class TestAtDeItem(_Base):
    def test_el_at_propio_manda(self):
        R = self.R
        e = {"tipo": "pasos", "from": 30.0, "to": 40.0, "titulo": "Lo que te deja",
             "items": [{"titulo": "Uno", "at": 31.0}, {"titulo": "Dos", "at": 33.0},
                       {"titulo": "Tres", "at": 35.0}, {"titulo": "Cuatro", "at": 37.0}],
             "at": {"rotulo": 30.2}}
        e = R.completar_escena(e, 0)       # rellena at.item0..2 con la muestra
        ts = R.tiempos_escalonados(e["at"], "item", e["items"], e["from"] + 0.3, e["from"])
        self.assertEqual(ts, [31.0, 33.0, 35.0, 37.0])
        # y se ve: a los 35,5 s el tercer paso ya entró y el cuarto no
        sin_cuarto = R.sc_pasos(self.ctx, e, 35.9)
        con_cuarto = R.sc_pasos(self.ctx, e, 39.0)
        self.assertLess(self.alfa(sin_cuarto), self.alfa(con_cuarto))

    def test_relativo_y_sin_retroceso(self):
        R = self.R
        items = [{"at": 0.5}, {}, {"at": 2.0}]
        ts = R.tiempos_escalonados({"item1": 0.1}, "item", items, 10.3, 10.0)
        self.assertEqual(ts[0], 10.5)          # < from: relativo al inicio
        self.assertGreater(ts[1], ts[0])       # sin at propio: nunca antes que el anterior
        self.assertEqual(ts[2], 12.0)

    def test_sin_at_de_item_no_cambia_nada(self):
        R = self.R
        at = {"item0": 1.0}
        self.assertEqual(R.tiempos_escalonados(at, "item", [{}, {}, {}], 0.3),
                         [R.escalonado(at, "item", i, 0.3) for i in range(3)])


class TestMarkup(_Base):
    def test_markup_cruza_espacios(self):
        R = self.R
        p = R.markup_palabras("Hackeamos tu *empresa* para que un *delincuente informático* no lo haga.")
        claves = ["".join(s[0] for s in w) for w in p if any(s[2] for s in w)]
        self.assertEqual(claves, ["empresa", "delincuente", "informático"])
        caja = R.markup_palabras("No fue un ~clic~.")
        self.assertEqual(caja[-1], [("clic", "roja", False), (".", None, False)])

    def test_caja_sobre_su_palabra_y_cruza_el_espacio(self):
        import numpy as np
        from PIL import Image, ImageDraw
        R = self.R
        fnt, fnt_b = self.ctx.fT(68, 500), self.ctx.fT(68, 800)
        img = Image.new("RGBA", (1000, 200), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        linea = R.markup_palabras("No fue ~un clic~.")
        R.dibuja_markup(d, (10, 40), linea, fnt, fnt_b)
        a = np.asarray(img)
        rojo = (np.abs(a[..., 0].astype(int) - R.ACENTO[0]) < 4) & (np.abs(a[..., 1].astype(int) - R.ACENTO[1]) < 4) \
            & (np.abs(a[..., 2].astype(int) - R.ACENTO[2]) < 4) & (a[..., 3] > 200)
        cols = np.where(rojo.any(axis=0))[0]
        x_un = 10 + d.textlength("No fue ", font=fnt)
        x_fin = x_un + d.textlength("un clic", font=fnt)
        self.assertLessEqual(cols.min(), x_un)                      # empieza en «un»
        self.assertGreaterEqual(cols.max(), x_fin - 2)              # acaba en «clic»
        self.assertLess(cols.max(), x_fin + d.textlength(".", font=fnt) + 12)   # el punto, fuera
        # un solo bloque: sin hueco de columnas vacías en el espacio
        self.assertEqual(int(cols.max() - cols.min() + 1), len(cols))

    def test_subrayado_lee_el_markup_y_no_corta(self):
        import numpy as np
        R = self.R
        e = {"tipo": "subrayado", "from": 0.0, "to": 5.0,
             "texto": "Hackeamos tu *empresa* para que un *delincuente informático* no lo haga.",
             "at": {"texto": 0.2, "linea": 0.9}}
        capa = R.sc_subrayado(self.ctx, e, 4.0)
        a = np.asarray(capa)
        rojo = (np.abs(a[..., 0].astype(int) - R.ACENTO[0]) < 6) & (np.abs(a[..., 1].astype(int) - R.ACENTO[1]) < 6) \
            & (a[..., 3] > 200)
        self.assertGreater(int(rojo.sum()), 2000)          # las claves van en el acento
        self.assertEqual(R.RECORTES, [])                   # y nada se cortó en silencio
        palabras = R.markup_palabras(e["texto"])
        fnt = self.ctx.fT(72, 800)
        zx0, _, zx1, _ = R.caja_segura()
        self.assertGreater(len(R.partir_markup(palabras, fnt, fnt, int((zx1 - zx0) * 0.92))), 2)


class TestTextos(_Base):
    def test_fuente_sin_duplicar(self):
        R = self.R
        for f in ("Binance", "Fuente: Binance", "fuente:Binance", "Source: Binance"):
            self.assertEqual(R.texto_fuente(f), "Fuente: Binance")

    def test_versalitas_respeta_la_marca(self):
        R = self.R
        self.assertEqual(R.versalitas("Lo que hace DragonJAR"), "LO QUE HACE DragonJAR")
        guarda = set(R.CASO_MARCA)
        try:
            R.CASO_MARCA.add("Acme")
            self.assertEqual(R.versalitas("con Acme hoy"), "CON Acme HOY")
        finally:
            R.CASO_MARCA.clear()
            R.CASO_MARCA.update(guarda)


class TestFinal(_Base):
    def test_sobrio_apaga_halo_y_latido(self):
        R = self.R
        base = R.completar_escena(_muestra("final"), 0)
        t = 3.37
        normal = R.sc_final(self.ctx, dict(base, sobrio=False), t)   # sin depender del pack instalado
        sobrio = R.sc_final(self.ctx, dict(base, sobrio=True), t)
        a_mano = R.sc_final(self.ctx, dict(base, latido=False, halo=False), t)
        self.assertEqual(self.alfa(sobrio), self.alfa(a_mano))
        self.assertLess(self.alfa(sobrio), self.alfa(normal))   # sin el aro del halo


class TestPanelesVerticales(_Base):
    def test_cadena_y_constancia_en_columna_legibles(self):
        R = self.R
        self.assertEqual(R.disposicion_de({}), "columna")
        cad = {"tipo": "cadena", "from": 0.0, "to": 5.0, "kicker": "Lo que vio el equipo",
               "items": [{"icono": "codigo", "titulo": "Equipo DevOps", "sub": "Laptop de un empleado"},
                         {"icono": "globo", "titulo": "Contenedor", "sub": "Contenedor de servicio"},
                         {"icono": "alerta", "titulo": "Retiros", "sub": "No autorizados"}],
               "at": {"item0": 0.3}}
        R.sc_cadena(self.ctx, cad, 4.0)
        con = {"tipo": "constancia", "from": 0.0, "to": 5.0, "kicker": "Lo que hizo Binance",
               "items": [{"texto": "Pérdidas cubiertas por Binance", "hecho": True},
                         {"texto": "Post-mortem técnico (pendiente)", "hecho": False}],
               "at": {"item0": 0.3}}
        R.sc_constancia(self.ctx, con, 4.0)
        self.assertEqual(R.RECORTES, [], "copy cortado en 9:16")

    def test_letra_minima(self):
        R = self.R
        # en columna los textos usan roles >= 32 px (el piso de la escala es 28)
        self.assertGreaterEqual(int(R.ESCALA["dato"] * 1.15), 28)
        self.assertGreaterEqual(R.ESCALA["secundario"], 28)


class TestPanelesApaisados(_Base):
    ancho, alto = 1920, 1080

    def test_fila_en_16_9(self):
        self.assertEqual(self.R.disposicion_de({}), "fila")
        self.assertEqual(self.R.disposicion_de({"disposicion": "columna"}), "columna")


class TestCopyLargo(_Base):
    LARGO = ("Un titular larguísimo que no cabe en una línea ni en dos "
             "y que antes tumbaba el render entero con *énfasis* incluido")

    def test_p0_1_titular_largo_no_tumba(self):
        R = self.R
        for w, h in ((1080, 1920), (1080, 1080), (1920, 1080)):
            R.formato(w, h)
            e = R.completar_escena({"tipo": "orbOpen", "from": 0, "to": 5,
                                    "titulo": self.LARGO, "subtitulo": "Sub"}, 0)
            for t in (0.9, 1.3, 2.0, 4.0):
                R.sc_orbOpen(self.ctx, e, t)        # antes: ValueError en _revela_clip

    def test_p0_2_lo_que_no_cabe_se_anota(self):
        R = self.R
        _f, lineas = R.texto_que_cabe(self.ctx.fX, self.LARGO * 3, 40, 300, max_lineas=2, minimo=36)
        self.assertEqual(len(lineas), 2)
        self.assertTrue(R.RECORTES)

    def test_p0_3_sin_signos_en_pantalla(self):
        R = self.R
        _f, lineas = R.texto_que_cabe(self.ctx.fX, "un *dato* con ~caja~", 40, 900)
        self.assertEqual(" ".join(lineas), "un dato con caja")
        _f, lineas = R.texto_que_cabe(self.ctx.fX, "un *dato*", 40, 900, markup=True)
        self.assertIn("*", " ".join(lineas))           # quien pinta el énfasis lo conserva
        for literal in ("SELECT * FROM t", "cd ~/home", "2^10"):
            self.assertEqual(R.texto_plano(literal), literal)
        e = R.completar_escena({"tipo": "pasos", "from": 0, "to": 5,
                                "items": [{"titulo": "*Uno*", "texto": "con ~caja~"}]}, 0)
        self.assertEqual(e["items"][0], {"titulo": "Uno", "texto": "con caja"})

    def test_p0_4_linea_al_piso_legible(self):
        R = self.R
        fnt, txt = R.linea_que_cabe(self.ctx.fX, "palabra " * 40, 44, 600)
        self.assertGreaterEqual(fnt.size, R.MIN_LETRA)
        self.assertTrue(txt.endswith("…"))
        self.assertLessEqual(self.ctx.tmp.textlength(txt, font=fnt), 600)
        self.assertTrue(R.RECORTES)

    def test_p0_5_rotulo_de_dos_lineas_empuja(self):
        R = self.R
        corto = R.rotulo_extra(self.ctx, "Tu día")
        largo = R.rotulo_extra(self.ctx, "Tu día entero, *en orden*, con todo lo que "
                                          "importa y nada de lo que sobra hoy")
        self.assertEqual(corto, 0)
        self.assertGreater(largo, 10)


class TestCuadrado(_Base):
    ancho, alto = 1080, 1080

    def test_1_1_compone_en_columna(self):
        R = self.R
        self.assertEqual(R.orientacion(), "cuadrado")
        self.assertEqual(R.disposicion_de({}), "columna")
        R.formato(1920, 1080)
        self.assertEqual(R.orientacion(), "horizontal")
        R.formato(1080, 1920)
        self.assertEqual(R.orientacion(), "vertical")


class TestReglasDeMovimiento(_Base):
    def setUp(self):
        super().setUp()
        R = self.R
        R.REBOTE = R.PARTICULAS = R.VOLUMEN = True    # sin depender del pack instalado

    def tearDown(self):
        R = self.R
        R.REBOTE = R.PARTICULAS = R.VOLUMEN = True

    def test_rebote_false_no_se_pasa(self):
        R = self.R
        self.assertGreater(max(R.entra(i / 100, 0, "pop") for i in range(150)), 1.05)
        R.REBOTE = False
        vals = [R.entra(i / 100, 0, "pop") for i in range(150)]
        self.assertLessEqual(max(vals), 1.0)
        self.assertGreater(vals[-1], 0.97)                       # y llega
        self.assertEqual(vals, sorted(vals))                     # monótona

    def test_particulas_false_deja_el_texto(self):
        R = self.R
        e = R.completar_escena(_muestra("confetti"), 0)
        con = self.alfa(R.sc_confetti(self.ctx, e, 2.0))
        R.PARTICULAS = False
        sin = R.sc_confetti(self.ctx, e, 2.0)
        self.assertLess(self.alfa(sin), con)
        self.assertGreater(self.alfa(sin), 0)                    # el texto sigue

    def test_volumen_false_insignia_plana(self):
        from PIL import Image, ImageDraw
        R = self.R
        def fondo_y():
            img = Image.new("RGBA", (300, 300), (0, 0, 0, 0))
            R.insignia_3d(ImageDraw.Draw(img), 150, 150, 60, None, self.ctx.fT(30, 800))
            return img.split()[3].getbbox()[3]
        con = fondo_y()
        R.VOLUMEN = False
        self.assertLess(fondo_y(), con)          # sin extrusión ni sombra debajo


class TestPackDragonJAR(unittest.TestCase):
    def test_pack(self):
        from _comun import colores_marca, fuente_marca, leer_pack, ruta_de_pack
        pack = os.path.join(SKILL, "brand", "dragonjar.json")
        mono = fuente_marca(pack, "etiquetas_mono", "DejaVu Sans Mono", "mono")
        self.assertTrue(mono and os.path.basename(mono).startswith("IBMPlexMono"), mono)
        self.assertTrue(os.path.exists(mono))
        c = colores_marca(pack)
        self.assertEqual(c["gris_detalle"], (74, 74, 74))
        self.assertNotEqual(c["gris"], (74, 74, 74))        # el texto de apoyo se lee
        d = leer_pack(pack)
        logo = ruta_de_pack(pack, d["logos"]["logotipo"])
        self.assertTrue(logo and os.path.exists(logo))
        self.assertIn("DragonJAR", d["reglas"]["conservar_caso"])
        # marca de precisión: sin rebote, sin partículas, sin volumen 3D
        self.assertEqual([d["reglas"][k] for k in ("rebote", "particulas", "volumen")],
                         [False, False, False])


if __name__ == "__main__":
    unittest.main()
