#!/usr/bin/env python3
"""Cierre de la pasada de diseño (familia W-C): R7 por escena y los restos.

Cada clase fija UNA causa, medida sobre el motor o sobre el frame:

- COPY x2: el estrés de copy de validate_skill duplica SOLO el texto que el
  espectador lee (`medir_animacion.copy_x2`, con los campos token del motor
  `render_plan.CAMPOS_TOKEN`): duplicar `colores: "serie"` a "serie serie"
  terminaba el proceso (die -> SystemExit) y el bloque de humo de escenas
  (copy x2, solapes) no corría nunca.
- POP DE CONTADOR: en un video (sin zonas de cifra del motor) la cifra
  nueva de un contador se agrupa con las que cuentan en 2D, no por fila: un
  contador desplazado en vertical (recentrado) daba pop a ciertas alturas.
- FRASE: lo dicho baja a la pista (no a cero: sin huecos a media medida), la
  frase se centra en su zona a 0,6 del titular y supera la ocupación mínima.
- SUBRAYADO: la línea sigue el ancho del texto (no el de la zona segura).
- PACK SIN FUGA: `aplicar_brand` fija el solape de su regla en los DOS
  sentidos; un pack `corte_seco` dejaba SOLAPE=0.25 instalado para el resto
  del proceso y un test de prosa fallaba según el orden.

Run: python3 -m pytest -q -p no:cacheprovider _tests/test_cierre_impecable.py
"""

import copy
import json
import os
import sys
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
BASE = os.path.dirname(SCRIPTS)
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, os.path.join(SCRIPTS, "ffmpeg_tools"))


def _muestras():
    with open(os.path.join(SCRIPTS, "escenas_muestra.json"), encoding="utf-8") as fh:
        return json.load(fh)["escenas"]


def _muestra(tipo):
    e = copy.deepcopy(_muestras()[tipo])
    e["tipo"] = tipo
    return e


def _motor(ancho=1080, alto=1920):
    import render_plan as R
    R.formato(ancho, alto)
    R.aplicar_globales({"escenas": []})
    R._ESCALA.clear()
    R._CAMARA["activa"] = False
    return R


class TestCopyX2(unittest.TestCase):
    """El bloque de humo de validate_skill recorre las 45 escenas con copy x2."""

    def test_los_campos_token_no_se_duplican(self):
        import medir_animacion as M
        import render_plan as R
        e = M.copy_x2(R, _muestra("subrayado"))
        self.assertEqual(e["colores"], "serie")
        t0 = _muestra("subrayado")["texto"]
        self.assertEqual(e["texto"], f"{t0} {t0}")
        o = M.copy_x2(R, _muestra("oferta"))
        self.assertEqual((o["moneda"], o["miles"], o["decimal"]), ("$", ".", ","))

    def test_el_humo_completa_las_escenas_en_los_dos_formatos(self):
        import medir_animacion as M
        caidas = []
        for ancho, alto in ((1080, 1920), (1920, 1080)):
            R = _motor(ancho, alto)
            ctx = R.Ctx()
            for nombre in R.SCENES:
                e = M.copy_x2(R, _muestra(nombre))
                if "imagen" in e:
                    e["imagen"] = None
                R._ESCALA.clear()
                try:
                    # el instante asentado del bloque de solapes (80 %)
                    R.componer(ctx, [e], e["to"] + 5, e["from"] + (e["to"] - e["from"]) * 0.8, set())
                except BaseException as ex:   # noqa: B036 - un die() es SystemExit
                    caidas.append(f"{nombre} {ancho}x{alto}: {type(ex).__name__}: {ex}")
        self.assertEqual(caidas, [], "el humo de copy x2 se corta en una escena")


class TestPopContadorDesplazado(unittest.TestCase):
    """Un contador movido en grupo (recentrado vertical) no es un pop: el
    detector de video agrupa la cifra nueva con las que cuentan en 2D, no
    por fila de la rejilla (antes: pop a ciertas alturas, 0 a otras)."""

    def _video(self, dy, aparece_lejos=False, n=24):
        F = np.full((n, 320, 180), 12.0, np.float32)
        for i in range(n):
            for x, v in ((95, i * 2),) + (((65, 1000 + i * 2),) if i >= 12 else ()):
                rng = np.random.default_rng(v)
                F[i, 130 + dy:180 + dy, x:x + 30] = rng.choice([12.0, 245.0], size=(50, 30))
            if aparece_lejos and i >= 12:
                F[i, 250:300, 20:120] = 240.0
                F[i, 260:290, 30:110] = 30.0
        return F

    def test_el_contador_a_cualquier_altura_no_es_pop(self):
        import medir_animacion as M
        pops = {dy: M.metricas(self._video(dy), 30, 2.0)["pops"] for dy in range(0, 20)}
        self.assertEqual({dy: p for dy, p in pops.items() if p}, {},
                         "la cifra nueva de un contador desplazado se mide como aparición")

    def test_un_objeto_separado_sigue_siendo_pop(self):
        import medir_animacion as M
        for dy in (0, 4, 14):
            with self.subTest(dy=dy):
                self.assertEqual(M.metricas(self._video(dy, True), 30, 2.0)["pops"], [0.4])


def _cuadros(R, e, ts, lado=180):
    """Frames en gris a la escala de análisis del medidor (lado corto 180)."""
    ctx = R.Ctx()
    out = []
    for t in ts:
        im = R.componer(ctx, [e], e["to"], t, set()).convert("L")
        k = lado / min(im.size)
        out.append(np.asarray(im.resize((round(im.width * k), round(im.height * k))), np.float32))
    return np.array(out)


class TestFrase(unittest.TestCase):
    """R7 frase: lo dicho no deja huecos y la frase llena su zona."""

    def test_lo_dicho_queda_en_su_sitio(self):
        """Al final de la escena se dibujan TODAS las palabras (lo dicho baja
        a la pista, no a cero): la primera línea no empieza a media medida."""
        R = _motor()
        e = R.completar_escena(_muestra("frase"), 0)
        dibujadas = []
        orig = R.pon_texto

        def espia(d, xy, texto, *a, **k):
            fill = k.get("fill")
            if not (isinstance(fill, tuple) and len(fill) == 4 and fill[3] <= 2):
                dibujadas.append(str(texto))
            return orig(d, xy, texto, *a, **k)
        R.pon_texto = espia
        try:
            # 0,3 s después de que entró la última palabra alcanzada (la que
            # entra en ese instante aún está en fundido: no cuenta)
            R.pintar(R.Ctx(), e, e["to"] - 0.5)
        finally:
            R.pon_texto = orig
        palabras = [w.replace("*", "") for w in e["frase"].split()]
        self.assertEqual([w for w in palabras if w not in dibujadas], [],
                         "palabras dichas desaparecen y dejan su hueco en la línea")

    def test_la_frase_supera_la_ocupacion_minima(self):
        """La misma medida que la puerta (`medir_animacion.medir`, escena sola)."""
        import medir_animacion as M
        M._init()
        for f in ("v", "h"):
            with self.subTest(formato=f):
                e = _muestra("frase")
                r = M.medir(("frase", f, [e], e["to"], 15))
                # con margen: la frase de antes daba 0,19-0,21 según el muestreo
                # (al filo de la puerta, pasaba o no según los fps)
                self.assertGreater(r["ocupacion"], M.OCUPACION_MIN * 1.5)


def _tinta_x(capa, umbral=40):
    """(x0, x1) de la tinta de una capa RGBA (alfa > umbral)."""
    a = np.asarray(capa.getchannel("A"))
    xs = np.where((a > umbral).any(axis=0))[0]
    return (int(xs.min()), int(xs.max())) if len(xs) else None


class TestSubrayado(unittest.TestCase):
    """R7 subrayado: la línea es la base del TEXTO, no una regla de zona."""

    def test_la_linea_sigue_el_ancho_del_texto(self):
        for ancho, alto in ((1920, 1080), (1080, 1920)):
            with self.subTest(formato=f"{ancho}x{alto}"):
                R = _motor(ancho, alto)
                e = _muestra("subrayado")
                solo_texto = _tinta_x(R.pintar(R.Ctx(), e, e["at"]["linea"] - 0.05))
                todo = _tinta_x(R.pintar(R.Ctx(), e, e["to"] - 1.0))
                vuelo = max(solo_texto[0] - todo[0], todo[1] - solo_texto[1])
                # un cuarto de cuerpo (72 px) por lado + el remate redondo del
                # trazo (grosor 12) y el apoyo lateral del glifo
                self.assertLessEqual(vuelo, 72 * 0.25 + 12, f"la línea vuela {vuelo} px más allá del texto")


class TestHandoff(unittest.TestCase):
    """R7 handoff: ficha y contexto son UN grupo apilado (SEPARA) en el
    centro óptico del sitio que deja el rótulo, no colgados de vy(0.30)."""

    def test_el_grupo_va_en_el_centro_optico(self):
        for ancho, alto in ((1080, 1920), (1920, 1080)):
            with self.subTest(formato=f"{ancho}x{alto}"):
                R = _motor(ancho, alto)
                e = _muestra("handoff")
                t = e["to"] - 1.0
                contenido, _fija = R.pintar_partes(R.Ctx(), e, t)
                a = np.asarray(contenido.getchannel("A"))
                ys = np.where((a > 40).any(axis=1))[0]
                libre = R.bajo_rotulo(R.rotulo_y())
                zy1 = R.caja_segura()[3]
                optico = libre + R.CENTRO_OPTICO * (zy1 - libre)
                centro = (ys.min() + ys.max()) / 2
                # la flotación del grupo (5 px) y la tinta del texto: 12 px
                self.assertLess(abs(centro - optico), 12,
                                f"el grupo cae a {centro:.0f}, el centro óptico es {optico:.0f}")


class TestTrazadoSuave(unittest.TestCase):
    """R7 camino: el trazo de `trazado` (camino, subrayado, la S) sale con
    borde suavizado (supermuestreo) y uniones redondas, no en escalera."""

    def test_el_borde_de_un_trazo_diagonal_tiene_medios_tonos(self):
        from PIL import Image
        R = _motor()
        capa = Image.new("RGBA", (600, 800), (0, 0, 0, 0))
        R.trazado(capa, [(100, 100), (420, 700)], (255, 255, 255), grosor=12,
                  desvanecer=0.0, brillo=False)
        a = np.asarray(capa.getchannel("A"))
        medios = np.unique(a[(a > 8) & (a < 247)])
        self.assertGreaterEqual(len(medios), 5, "el borde del trazo es una escalera de 0/255")

    def test_el_nucleo_no_tiene_agujeros_en_las_uniones(self):
        from PIL import Image
        R = _motor()
        capa = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
        pts = [(50 + i * 6, 200 + 80 * np.sin(i / 8)) for i in range(50)]
        R.trazado(capa, pts, (255, 255, 255), grosor=10, desvanecer=0.0, brillo=True)
        a = np.asarray(capa.getchannel("A"))
        nucleo = [a[int(round(y)), int(round(x))] for x, y in pts]
        self.assertGreaterEqual(min(nucleo), 240, "el halo del tramo siguiente agujerea el núcleo")


class TestSinHaloDeNeon(unittest.TestCase):
    """R7: el halo de neón es un tell. El botón respira sin aro; el brillo
    del gigante de `remate` es del momento firma y se recoge en el hold."""

    def test_el_boton_no_pinta_fuera_de_su_pildora(self):
        from PIL import Image, ImageDraw
        R = _motor()
        w, h = 400, 100
        for t in np.arange(0.0, 2.0, 0.1):
            capa = Image.new("RGBA", (800, 400), (0, 0, 0, 0))
            R.boton_halo(ImageDraw.Draw(capa), 400, 200, w, h, "Compra ya",
                         R.Ctx().fX(36, 800), float(t), 0.0)
            a = np.asarray(capa.getchannel("A"))
            ys, xs = np.nonzero(a > 10)
            with self.subTest(t=round(float(t), 1)):
                # la respiración (2,5 %) más el antialias: nada de aro alrededor
                self.assertLessEqual(xs.max() - xs.min(), w * 1.025 + 4)
                self.assertLessEqual(ys.max() - ys.min(), h * 1.025 + 4)

    def test_el_brillo_del_gigante_se_recoge_en_el_hold(self):
        R = _motor()
        e = R.completar_escena(_muestra("remate"), 0)
        g = e["at"]["gigante"]

        def halo(t):
            orig = R.pon_texto   # sin la letra: lo que queda es el brillo
            R.pon_texto = lambda *a, **k: None
            try:
                capa = R.pintar(R.Ctx(), e, t)
            finally:
                R.pon_texto = orig
            a = np.asarray(capa.getchannel("A")).astype(float)
            return a[int(R.H * 0.5):].sum()
        pico, hold = halo(g + 0.4), halo(e["to"] - 0.8)
        self.assertLess(hold, 0.5 * pico, f"el brillo sigue encendido en el hold ({hold:.0f} vs {pico:.0f})")


class TestPackSinFuga(unittest.TestCase):
    """Un pack `corte_seco` no deja su solape instalado para lo que sigue."""

    def test_volver_sin_pack_restaura_el_solape(self):
        import render_plan as R
        base = (R.SOLAPE, R.SOLAPE_PRE)
        try:
            R.aplicar_brand(os.path.join(BASE, "brand", "dragonjar.json"))
            self.assertEqual((R.SOLAPE, R.SOLAPE_PRE), (R.SOLAPE_SECO, R.SOLAPE_PRE_SECO))
        finally:
            R.aplicar_brand(None)
        self.assertEqual((R.SOLAPE, R.SOLAPE_PRE), base)
        self.assertEqual(R.TRANSICIONES, "libre")


if __name__ == "__main__":
    unittest.main()
