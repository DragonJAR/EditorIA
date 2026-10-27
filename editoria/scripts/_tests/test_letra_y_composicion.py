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


class TestCirculoNumero(unittest.TestCase):
    """El numero dentro del circulo: cabe en el circulo y se lee.

    En `index` el circulo era de 32 px fijos con la fuente secundaria:
    un numero de dos cifras desbordaba, y el inactivo era gris sobre gris.
    """

    def test_la_cifra_cabe_en_el_circulo(self):
        import render_plan as R
        from PIL import Image, ImageDraw
        R.formato(1080, 1920)
        ctx = R.Ctx()
        img = Image.new("RGBA", (400, 200), (10, 10, 10, 255))
        d = ImageDraw.Draw(img)
        for texto in ("1", "10", "12"):
            R.circulo_numero(d, 100, 100, 24, texto, (60, 60, 60), R.BLANCO, ctx)
            # la fuente elegida tiene que caber en el ancho util del circulo
            fnt = R.fuente_que_cabe(ctx.fT, texto, int(24 * 1.05), int(24 * 1.4),
                                    800, tabular=True)
            self.assertLessEqual(R.largo(texto, fnt, True), 24 * 1.4 + 1)

    def test_el_numero_queda_dentro_de_los_pixeles_del_circulo(self):
        import render_plan as R
        from PIL import Image, ImageDraw
        R.formato(1080, 1920)
        ctx = R.Ctx()
        img = Image.new("RGBA", (200, 200), (0, 0, 0, 255))
        d = ImageDraw.Draw(img)
        R.circulo_numero(d, 100, 100, 24, "12", (60, 60, 60), (255, 255, 255), ctx)
        # fuera del circulo (radio 24) no hay pixeles de la cifra
        px = img.load()
        for x, y in ((100, 60), (100, 140), (60, 100), (140, 100)):
            self.assertEqual(px[x, y], (0, 0, 0, 255))
        # y dentro hay cifra blanca
        blancos = sum(1 for yy in range(76, 125) for xx in range(76, 125)
                      if px[xx, yy][:3] == (255, 255, 255))
        self.assertGreater(blancos, 20)


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

    def test_los_solapes_dicen_que_textos_y_donde(self):
        # un conteo sin dueno obligaba a correr medir_animacion aparte:
        # el veredicto tiene que traer escena, instante y los dos textos
        fallos = QA._defectos_composicion(
            40, 1.0, ["timeline@25.7s: «04»/«Fuente: Cadena»"])
        self.assertIn("timeline@25.7s", fallos[0])
        self.assertIn("«04»", fallos[0])
        self.assertIn("«Fuente: Cadena»", fallos[0])

    def test_la_letra_dice_su_escena(self):
        fallos = QA._defectos_composicion(
            21, 1.0, [], culpables_letra=[
                {"escena": "3:gauge", "texto": "Fuente: El firmware", "letra_px": 21}])
        self.assertIn("3:gauge", fallos[0])
        self.assertIn("Fuente: El firmware", fallos[0])

    def test_la_zona_dice_su_escena(self):
        fallos = QA._defectos_composicion(
            40, 0.70, [], culpables_zona=[{"escena": "2:listo", "zona": 0.72}])
        self.assertIn("2:listo", fallos[0])


class TestPlanDesincronizado(unittest.TestCase):
    """El plan editado despues del render no puede aprobar el video viejo."""

    def test_plan_posterior_al_video_falla(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            plan, video = os.path.join(d, "p.json"), os.path.join(d, "v.mp4")
            open(plan, "w").close(); open(video, "w").close()
            os.utime(video, (1_000_000, 1_000_000))
            os.utime(plan, (1_000_100, 1_000_100))
            self.assertIsNotNone(QA._defecto_plan_desincronizado(plan, video))

    def test_video_posterior_al_plan_pasa(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            plan, video = os.path.join(d, "p.json"), os.path.join(d, "v.mp4")
            open(plan, "w").close(); open(video, "w").close()
            os.utime(plan, (1_000_000, 1_000_000))
            os.utime(video, (1_000_100, 1_000_100))
            self.assertIsNone(QA._defecto_plan_desincronizado(plan, video))


class TestProgresoAlMedir(unittest.TestCase):
    """Medir un plan tarda minutos: sin progreso parece un cuelgue."""

    def test_medir_anuncia_los_trabajos(self):
        with open(MA.__file__, encoding="utf-8") as f:
            src = f.read()
        self.assertIn("imap_unordered", src)
        self.assertIn("componiendo", src)


class TestEscenasNoDesbordan(unittest.TestCase):
    """Las escenas del reel DragonJAR, con su copy real, dentro de la zona."""

    def _capturar(self, pintar):
        import render_plan as R
        from PIL import ImageDraw
        R.formato(1080, 1920)
        ctx = R.Ctx()
        vistos = []
        original = ImageDraw.ImageDraw.text

        def espia(self, xy, text, fill=None, font=None, *a, **k):
            if font is not None and str(text).strip():
                vistos.append((str(text), font, xy, k.get("anchor", "la")))
            return original(self, xy, text, fill, font, *a, **k)

        ImageDraw.ImageDraw.text = espia
        try:
            pintar(R, ctx)
        finally:
            ImageDraw.ImageDraw.text = original
        return R, vistos

    def test_listo_cabe_y_sin_asteriscos(self):
        def pintar(R, ctx):
            e = R.completar_escena({"tipo": "listo", "from": 0, "to": 6,
                                    "texto": "Formateo *completado*",
                                    "at": {"listo": 0.4}})
            R.sc_listo(ctx, e, 3.0)
        R, vistos = self._capturar(pintar)
        textos = " ".join(t for t, _, _, _ in vistos)
        self.assertNotIn("*", textos)
        x0, _, x1, _ = R.caja_segura()
        for texto, fnt, (x, y), anchor in vistos:
            ancho = R.largo(texto, fnt)
            if anchor.startswith("m"):
                self.assertGreaterEqual(x - ancho / 2, x0 - 2, texto)
                self.assertLessEqual(x + ancho / 2, x1 + 2, texto)
            else:   # draw_seg dibuja caracter a caracter desde la izquierda
                self.assertGreaterEqual(x, x0 - 2, texto)
                self.assertLessEqual(x + ancho, x1 + 2, texto)

    def test_quote_el_rol_cabe_en_la_tarjeta(self):
        def pintar(R, ctx):
            e = R.completar_escena({"tipo": "quote", "from": 0, "to": 7,
                                    "texto": "Borras lo que *ves*. No lo que vive en tu *hardware*.",
                                    "autor": "DragonJAR",
                                    "rol": "Hackeamos tu empresa antes que un delincuente",
                                    "at": {"card": 0.2, "texto": 0.6, "autor": 3.0}})
            R.sc_quote(ctx, e, 5.0)
        R, vistos = self._capturar(pintar)
        x0, _, x1, _ = R.caja_segura()
        rol = [(t, f, xy, a) for t, f, xy, a in vistos if "delincuente" in t
               or "Hackeamos" in t]
        self.assertTrue(rol, "el rol tiene que dibujarse")
        for texto, fnt, (x, y), anchor in rol:
            ancho = R.largo(texto, fnt)
            self.assertGreaterEqual(x - ancho / 2, x0, texto)
            self.assertLessEqual(x + ancho / 2, x1, texto)

    def test_bars_la_etiqueta_no_se_recorta(self):
        def pintar(R, ctx):
            e = R.completar_escena({"tipo": "bars", "from": 0, "to": 8,
                                    "titulo": "Qué borra *formatear*",
                                    "barras": [{"etiqueta": "Sistema operativo", "valor": 100, "max": 100},
                                               {"etiqueta": "Tus archivos", "valor": 100, "max": 100},
                                               {"etiqueta": "El firmware", "valor": 0, "max": 100, "acento": True}],
                                    "at": {"rotulo": 0.2, "bar0": 0.8, "bar1": 1.1, "bar2": 1.4}})
            R.sc_bars(ctx, e, 6.0)
        R, vistos = self._capturar(pintar)
        textos = [t for t, _, _, _ in vistos]
        self.assertNotIn("Sistema opera…", textos)
        self.assertTrue(any("Sistema" in t for t in textos))
        self.assertTrue(any("operativo" in t for t in textos))

    def test_audiowave_la_transcripcion_no_nace_en_el_piso(self):
        def pintar(R, ctx):
            e = R.completar_escena({"tipo": "audiowave", "from": 0, "to": 8,
                                    "rotulo": "¿Tu empresa lo *detectaría?*",
                                    "hablante": "DragonJAR",
                                    "transcripcion": "¿Qué revisarías primero?",
                                    "at": {"rotulo": 0.2, "tarjeta": 0.6, "onda": 1.0,
                                           "texto": 1.6}})
            R.sc_audiowave(ctx, e, 6.0)
        R, vistos = self._capturar(pintar)
        # text_reveal dibuja la transcripcion caracter a caracter: se
        # juzgan los tamanos de todo el texto de la escena
        tamanos = [f.size for t, f, _, _ in vistos if any(c.isalnum() for c in t)]
        self.assertTrue(tamanos)
        self.assertGreaterEqual(min(tamanos), R.ESCALA["nota"])

    def test_la_fuente_no_nace_en_el_piso(self):
        def pintar(R, ctx):
            e = R.completar_escena({"tipo": "gauge", "from": 0, "to": 9,
                                    "titulo": "Lo que el formateo *no toca*",
                                    "valor": 0, "max": 100, "etiqueta": "del firmware",
                                    "fuente": "El firmware vive fuera del sistema de archivos",
                                    "at": {"rotulo": 0.2, "gauge": 0.7, "etiqueta": 2.0,
                                           "fuente": 2.5}})
            R.sc_gauge(ctx, e, 6.0)
        R, vistos = self._capturar(pintar)
        fuentes = [(t, f) for t, f, _, _ in vistos if t.startswith("Fuente:")]
        self.assertTrue(fuentes)
        for t, f in fuentes:
            self.assertGreaterEqual(f.size, R.ESCALA["nota"], t)

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
