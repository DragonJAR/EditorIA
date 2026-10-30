#!/usr/bin/env python3
"""Contratos de layout y contraste de la pasada de diseño (familia W-B).

Cada clase fija UNA causa raíz, medida sobre el frame que se entrega:

- R5.4 CAPA FIJA: el rótulo (`rotulo_y()`) y la línea de fuente
  (`pie_fuente`) van en una capa que NO escala ni sigue el encaje del
  contenido (`_crecer`, push-in): solo respira con la flotación de la
  cámara (misma fase en toda escena, 0 en el corte). El rótulo cae a la
  misma altura de pantalla en toda escena y la fuente sobre UNA línea base
  por encima del borde seguro inferior.
- R5.1 APILAR MEDIDO: lo que va debajo se coloca bajo la tinta MEDIDA de lo
  de arriba (`apila`, `tinta`), no en `rotulo_y()+N`: la cifra de `hoy` no
  toca sus tarjetas, las tarjetas de `pago` y del PAGADO de `recupera`
  tienen el mismo aire arriba y abajo (`PAD`), el texto de cada resultado
  del `buscador` va centrado en su caja y la lista del `index` centrada en
  el eje del título.
- R5.2 VIDA EN GRUPO: la vida en reposo desplaza un grupo YA compuesto, nunca
  el layout: el icono que late no corre la columna de texto de
  `notificacion` y una lista flota con UNA flotación (huecos constantes).
- R5.3 ENTRADA: toda entrada sube ELEV px (una cifra, una dirección).
- R5.5 TOKENS: glifo de canal por tabla (WhatsApp y Web no son ambos "W"),
  cifras en es (1.240 · 3,5) por defecto, una columna de 16:9
  (`ancho_columna`), el pedido del chat en la columna de las burbujas, los
  extremos del timeline con la tinta simétrica y el contenido a SEPARA de
  la línea de fuente (`techo_fuente`).
- R6 CONTRASTE: UNA primitiva de decoración bajo texto (`deco_bajo_texto`:
  el dragón de la apertura y las partículas de `orbita` se apagan bajo la
  letra) y UNA regla de acento (`acento_legible`): el énfasis sobre una
  placa, el kicker y el REC chicos sobre casi negro llegan a 4.5:1; la
  fuente sobre una captura clara va en placa. El "¡EN VIVO!" de countdown
  no pasa el margen.

Run: python3 -m pytest -q -p no:cacheprovider _tests/test_layout_impecable.py
"""

import copy
import json
import os
import sys
import unittest

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, os.path.join(SCRIPTS, "ffmpeg_tools"))

MAGENTA = (255, 0, 255)


def _muestra(tipo):
    with open(os.path.join(SCRIPTS, "escenas_muestra.json"), encoding="utf-8") as fh:
        e = copy.deepcopy(json.load(fh)["escenas"][tipo])
    e["tipo"] = tipo
    return e


def _motor(ancho=1080, alto=1920):
    import render_plan as R
    R.formato(ancho, alto)
    R.aplicar_globales({"escenas": []})
    R._ESCALA.clear()
    R._CAMARA["activa"] = False
    return R


def _magenta(img):
    """Máscara de la tinta magenta (el rótulo o la fuente teñidos por el test)."""
    a = np.asarray(img.convert("RGB"), np.int16)
    return (a[..., 0] > 150) & (a[..., 2] > 150) & (a[..., 1] < 90)


def _filas(m):
    ys = np.where(m.any(axis=1))[0]
    return (int(ys.min()), int(ys.max())) if len(ys) else None


def _compuesto(R, e, t, tenir, crudo=False):
    """El frame compuesto de la escena sola en t, con el rótulo (`tenir` =
    "rotulo") o la fuente ("fuente") dibujados en magenta. `crudo`: la capa
    de la escena SIN encuadre (dónde la puso su layout)."""
    orig_rot, orig_pie = R.rotulo, R.pie_fuente

    def rot(ctx, layer, t_, texto, at, y=None, color=None, tam=None):
        return orig_rot(ctx, layer, t_, str(texto).replace("*", ""), at, y=y,
                        color=MAGENTA if tenir == "rotulo" else color, tam=tam)

    def pie(ctx, d, e_, t_, t_def):
        gris = R.GRIS
        if tenir == "fuente":
            R.GRIS = MAGENTA
        try:
            return orig_pie(ctx, d, e_, t_, t_def)
        finally:
            R.GRIS = gris
    R.rotulo, R.pie_fuente = rot, pie
    try:
        if crudo:
            return R.pintar(R.Ctx(), e, t)
        dur = e["to"] - e["from"]
        return R.componer(R.Ctx(), [e], dur, t, set())
    finally:
        R.rotulo, R.pie_fuente = orig_rot, orig_pie


class TestCapaFija(unittest.TestCase):
    """R5.4: el rótulo y la fuente no viajan con el encuadre del contenido."""

    ROTULADAS = ("hoy", "recupera", "stats", "timeline", "medianoche", "leads",
                 "bars", "pago", "buscador", "index", "notificacion")
    CON_FUENTE = ("bars", "stats", "timeline", "index", "gauge", "buscador")

    def _tope_rotulo(self, R, tipo, t):
        e = _muestra(tipo)
        e["from"], e["to"] = 0.0, e["to"] - e["from"]
        R._ESCALA.clear()
        f = _filas(_magenta(_compuesto(R, e, t, "rotulo")))
        self.assertIsNotNone(f, f"{tipo}: sin rótulo a {t}s")
        # la tinta de "L" y de "d" no empieza a la misma altura: se mide el
        # desplazamiento de pantalla frente al layout de la escena
        f0 = _filas(_magenta(_compuesto(R, e, t, "rotulo", crudo=True)))
        # el marco respira con la cámara (la flotación, la misma fase en
        # toda escena): lo que no puede es escalar ni seguir al contenido
        return round(f[0] - f0[0] - R.respiracion(e, t)[1])

    def _formato(self, ancho, alto):
        R = _motor(ancho, alto)
        topes = {}
        for tipo in self.ROTULADAS:
            # asentado y casi al final: el push-in ya empujó todo lo que empuja
            e = _muestra(tipo)
            fin = e["to"] - e["from"] - 0.5
            topes[tipo] = (self._tope_rotulo(R, tipo, 2.5), self._tope_rotulo(R, tipo, fin))
        todos = [v for par in topes.values() for v in par]
        self.assertLessEqual(max(abs(v) for v in todos), 1,
                             f"{ancho}x{alto}: el encuadre mueve el rótulo (px de pantalla vs layout): {topes}")

    def test_rotulo_a_la_misma_altura_en_9x16(self):
        self._formato(1080, 1920)

    def test_rotulo_a_la_misma_altura_en_16x9(self):
        self._formato(1920, 1080)

    def test_fuente_sobre_una_linea_base(self):
        for ancho, alto in ((1080, 1920), (1920, 1080)):
            R = _motor(ancho, alto)
            fondos = {}
            for tipo in self.CON_FUENTE:
                e = _muestra(tipo)
                if not e.get("fuente"):
                    continue
                e["from"], e["to"] = 0.0, e["to"] - e["from"]
                R._ESCALA.clear()
                t = e["to"] - 0.5
                f = _filas(_magenta(_compuesto(R, e, t, "fuente")))
                self.assertIsNotNone(f, f"{tipo}: sin línea de fuente")
                fondos[tipo] = round(f[1] - R.respiracion(e, t)[1])
            self.assertGreaterEqual(len(fondos), 3)
            self.assertLessEqual(max(fondos.values()) - min(fondos.values()), 2,
                                 f"{ancho}x{alto}: la línea de fuente no comparte base: {fondos}")
            self.assertLessEqual(max(fondos.values()), R.H - R.SAFE["bottom"] - 12,
                                 f"{ancho}x{alto}: la fuente roza el borde seguro: {fondos}")


def _tinta_en(capa, caja, umbral=90):
    """(y0, y1) de la tinta clara (letra, botón) dentro de `caja` (x0,y0,x1,y1)."""
    x0, y0, x1, y1 = (int(round(v)) for v in caja)
    a = np.asarray(capa.convert("RGB"), np.float32)[y0:y1, x0:x1]
    lum = a.mean(axis=2)
    filas = np.where((lum > umbral).sum(axis=1) > 2)[0]
    return (y0 + int(filas.min()), y0 + int(filas.max())) if len(filas) else None


def _espia(R, nombre, registro):
    orig = getattr(R, nombre)

    def esp(*a, **k):
        registro.append((a, k))
        return orig(*a, **k)
    setattr(R, nombre, esp)
    return lambda: setattr(R, nombre, orig)


def _sobre_negro(capa):
    f = Image.new("RGBA", capa.size, (0, 0, 0, 255))
    f.alpha_composite(capa)
    return f


class TestApilarMedido(unittest.TestCase):
    """R5.1: el layout se apila desde cajas MEDIDAS."""

    FORMATOS = ((1080, 1920), (1920, 1080))

    def test_la_cifra_de_hoy_no_toca_sus_tarjetas(self):
        for ancho, alto in self.FORMATOS:
            R = _motor(ancho, alto)
            e = _muestra("hoy")
            cifras, tarjetas = [], []
            quita = [_espia(R, "cifra", cifras), _espia(R, "tarjeta", tarjetas)]
            try:
                R.pintar(R.Ctx(), e, 3.0)
            finally:
                for q in quita:
                    q()
            (d, xy, texto, fnt, fill), k = cifras[-1][0][:5], cifras[-1][1]
            ancla = k.get("anchor", cifras[-1][0][5] if len(cifras[-1][0]) > 5 else "mm")
            fondo = xy[1] + fnt.getbbox(texto, anchor=ancla)[3]
            arriba = min(a[3] for a, _ in tarjetas)
            with self.subTest(formato=(ancho, alto)):
                self.assertGreaterEqual(arriba - fondo, 24,
                                        f"la cifra termina en {fondo} y la tarjeta empieza en {arriba}")

    def _aire_de_tarjeta(self, R, tipo, t, cual=-1):
        e = _muestra(tipo)
        tarjetas = []
        quita = _espia(R, "tarjeta", tarjetas)
        try:
            capa = R.pintar_partes(R.Ctx(), e, t)[0]
        finally:
            quita()
        a, _ = tarjetas[cual]
        x, y, w, h = a[2:6]
        tinta = _tinta_en(_sobre_negro(capa), (x + 4, y + 2, x + w - 4, y + h - 2))
        return tinta[0] - y, (y + h) - tinta[1]

    def test_pago_y_pagado_con_el_mismo_aire_arriba_y_abajo(self):
        for ancho, alto in self.FORMATOS:
            R = _motor(ancho, alto)
            e = _muestra("pago")
            casos = (("pago", e["at"]["cursor"] - 0.05), ("recupera", _muestra("recupera")["to"] - 0.4))
            for tipo, t in casos:
                arriba, abajo = self._aire_de_tarjeta(R, tipo, t)
                with self.subTest(formato=(ancho, alto), tipo=tipo):
                    self.assertLessEqual(abs(arriba - abajo), 4,
                                         f"{tipo}: aire arriba {arriba} vs abajo {abajo}")

    def test_el_monto_de_pago_no_se_pega_a_su_nombre(self):
        R = _motor()
        e = _muestra("pago")
        textos = []
        quita = _espia(R, "pon_texto", textos)
        try:
            R.pintar(R.Ctx(), e, e["at"]["cursor"] - 0.05)
        finally:
            quita()
        caja = {}
        for a, k in textos:
            if a[2] in (e["monto"], e["cliente"]):
                b = k["font"].getbbox(a[2], anchor=k.get("anchor", "la"))
                caja[a[2]] = (a[1][1] + b[1], a[1][1] + b[3])
        hueco = caja[e["cliente"]][0] - caja[e["monto"]][1]
        self.assertGreaterEqual(hueco, 20, f"monto y nombre a {hueco} px")

    def test_cada_resultado_del_buscador_centrado_en_su_caja(self):
        for ancho, alto in self.FORMATOS:
            R = _motor(ancho, alto)
            e = _muestra("buscador")
            cajas = []
            orig = R.ImageDraw.ImageDraw.rounded_rectangle

            def espia(self_, xy, *a, **k):
                if k.get("radius") == 18:
                    cajas.append(xy)
                return orig(self_, xy, *a, **k)
            R.ImageDraw.ImageDraw.rounded_rectangle = espia
            try:
                capa = R.pintar_partes(R.Ctx(), e, e["to"] - 0.5)[0]
            finally:
                R.ImageDraw.ImageDraw.rounded_rectangle = orig
            self.assertTrue(cajas)
            negro = _sobre_negro(capa)
            for x0, y0, x1, y1 in cajas:
                tinta = _tinta_en(negro, (x0 + 46, y0 + 3, x1 - 4, y1 - 3), umbral=120)
                arriba, abajo = tinta[0] - y0, y1 - tinta[1]
                with self.subTest(formato=(ancho, alto), caja=(y0, y1)):
                    self.assertLessEqual(abs(arriba - abajo), 4, f"aire {arriba} arriba vs {abajo} abajo")

    def test_la_lista_del_index_centrada_en_el_eje(self):
        for ancho, alto in self.FORMATOS:
            R = _motor(ancho, alto)
            e = _muestra("index")
            capa = R.pintar_partes(R.Ctx(), e, e["to"] - 0.5)[0]
            m = np.asarray(capa.getchannel("A")) > 110
            y1_marco = R.H - R.SAFE["bottom"] - 70   # sin la fuente
            cols = np.where(m[:y1_marco].any(axis=0))[0]
            centro = (cols.min() + cols.max()) / 2
            with self.subTest(formato=(ancho, alto)):
                self.assertLessEqual(abs(centro - R.W / 2), 6,
                                     f"la lista va de {cols.min()} a {cols.max()} (eje {R.W / 2})")


class TestVidaEnGrupo(unittest.TestCase):
    """R5.2: la flotación y el latido mueven un grupo, no el layout."""

    def test_la_columna_de_texto_de_notificacion_no_tiembla(self):
        R = _motor()
        e = _muestra("notificacion")
        xs = {}
        for t in (3.6, 3.75, 3.9, 4.1, 4.3, 4.6):
            textos = []
            quita = _espia(R, "pon_texto", textos)
            try:
                R.pintar(R.Ctx(), e, t)
            finally:
                quita()
            for a, k in textos:
                if a[2] in [it["titulo"] for it in e["items"]]:
                    xs.setdefault(a[2], set()).add(round(a[1][0], 1))
        for tit, v in xs.items():
            self.assertEqual(len(v), 1, f"'{tit}': la columna de texto se corre: {sorted(v)}")

    def test_una_lista_flota_con_una_sola_flotacion(self):
        for tipo, t in (("notificacion", 4.2), ("canales", 4.4)):
            for ancho, alto in ((1080, 1920), (1920, 1080)):
                R = _motor(ancho, alto)
                e = _muestra(tipo)
                llamadas = []
                quita = _espia(R, "flota", llamadas)
                try:
                    R.pintar(R.Ctx(), e, t)
                finally:
                    quita()
                fases = {tuple(round(float(x), 3) for x in a[1:]) + tuple(sorted(k.items())) for a, k in llamadas}
                with self.subTest(tipo=tipo, formato=(ancho, alto)):
                    self.assertLessEqual(len(fases), 1, f"{tipo}: {len(fases)} flotaciones distintas: {fases}")


class TestEntradaUnaDireccion(unittest.TestCase):
    """R5.3: toda entrada de grupo pasa por ELEV y sube."""

    def test_fundir_usa_elev_por_defecto(self):
        import inspect
        R = _motor()
        self.assertEqual(inspect.signature(R.fundir).parameters["dy"].default, R.ELEV)

    def test_ninguna_entrada_cae_desde_arriba_ni_trae_su_cifra(self):
        import re
        with open(os.path.join(SCRIPTS, "render_plan.py"), encoding="utf-8") as fh:
            src = fh.read()
        malas = re.findall(r"fundir\([^)]*dy\s*=\s*-?[1-9][0-9]*", src)
        malas += re.findall(r"\(1\s*-\s*min\(1,\s*k\w*\)\)\s*\*\s*-\s*\d+", src)
        self.assertEqual(malas, [], "entradas con cifra propia o desde arriba (usar ELEV)")


class TestTokens(unittest.TestCase):
    """R5.5: un token por relación."""

    def test_cada_canal_con_su_glifo(self):
        R = _motor()
        for tipo, clave in (("canales", "canales"), ("medianoche", "notificaciones")):
            e = _muestra(tipo)
            glifos = [R.glifo_canal(c.get("canal"), c.get("icono")) for c in e[clave]]
            with self.subTest(tipo=tipo):
                self.assertEqual(len(set(map(str, glifos))), len(glifos), f"{tipo}: {glifos}")

    def test_cifras_en_espanol_por_defecto(self):
        R = _motor()
        self.assertEqual(R.cuenta_up(0, 3.5, 1e9, 0), "3,5")
        self.assertEqual(R.cuenta_up(0, 450000, 1e9, 0), "450.000")

    def test_una_columna_en_16x9(self):
        import re
        R = _motor(1920, 1080)
        with open(os.path.join(SCRIPTS, "render_plan.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertEqual(len(re.findall(r"unidad\(\) \* 1\.25 if W > H", src)), 1,
                         "el ancho de columna se escribe una vez (ancho_columna)")
        self.assertEqual(R.ancho_columna(), int(R.unidad() * 1.25))

    def test_el_pedido_del_chat_va_en_la_columna_de_las_burbujas(self):
        for ancho, alto in ((1080, 1920), (1920, 1080)):
            R = _motor(ancho, alto)
            e = _muestra("chat")
            if not e.get("link"):
                self.skipTest("la muestra de chat no trae link")
            cajas = []
            orig = R.ImageDraw.ImageDraw.rounded_rectangle

            def espia(self_, xy, *a, **k):
                cajas.append((tuple(float(v) for v in xy), k.get("fill")))
                return orig(self_, xy, *a, **k)
            R.ImageDraw.ImageDraw.rounded_rectangle = espia
            try:
                R.pintar(R.Ctx(), e, e["to"] - 0.5)
            finally:
                R.ImageDraw.ImageDraw.rounded_rectangle = orig
            acento = tuple(R.ACENTO)
            link = [c for c, f in cajas if f and tuple(f[:3]) == acento]
            burbujas = [c for c, f in cajas if f and tuple(f[:3]) != acento]
            with self.subTest(formato=(ancho, alto)):
                self.assertTrue(link and burbujas)
                self.assertAlmostEqual(link[-1][0], min(b[0] for b in burbujas), delta=2)
                self.assertAlmostEqual(link[-1][2], max(b[2] for b in burbujas), delta=2)

    def test_los_extremos_del_timeline_simetricos_en_16x9(self):
        R = _motor(1920, 1080)
        e = _muestra("timeline")
        capa = R.pintar_partes(R.Ctx(), e, e["to"] - 0.5)[0]
        cols = np.where((np.asarray(capa.getchannel("A")) > 110).any(axis=0))[0]
        self.assertLessEqual(abs((cols.min() + cols.max()) / 2 - R.W / 2), 6,
                             f"la tinta va de {cols.min()} a {cols.max()}")

    def test_el_contenido_respira_sobre_la_fuente(self):
        for ancho, alto in ((1080, 1920), (1920, 1080)):
            R = _motor(ancho, alto)
            for tipo in ("oferta", "index", "bars", "stats", "timeline", "gauge"):
                e = _muestra(tipo)
                if not e.get("fuente"):
                    continue
                capa, fija = R.pintar_partes(R.Ctx(), e, e["to"] - 0.5)
                fondo = _filas(np.asarray(capa.getchannel("A")) > 110)[1]
                techo = _filas(np.asarray(fija.getchannel("A")) > 110)
                techo = [y for y in range(techo[0], techo[1] + 1)
                         if (np.asarray(fija.getchannel("A"))[y] > 110).any() and y > R.H * 0.6][0]
                with self.subTest(tipo=tipo, formato=(ancho, alto)):
                    self.assertGreaterEqual(techo - fondo, 32, f"{tipo}: contenido a {techo - fondo} px de la fuente")


DJ = os.path.join(os.path.dirname(SCRIPTS), "brand", "dragonjar.json")


def _lum1(rgb):
    c = np.asarray(rgb, np.float64) / 255.0
    c = np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]


def _contrastes(R, e, t):
    """[(texto, tamaño, ratio mediano)] de cada texto dibujado en el lienzo
    entero, contra la escena dibujada SIN texto (la técnica de
    medir_contraste: la superficie es lo que hay debajo)."""
    import medir_contraste as MC
    from PIL import ImageDraw
    orig = ImageDraw.ImageDraw.text
    ctx = R.Ctx()
    ImageDraw.ImageDraw.text = MC._espia([], False, orig)
    try:
        sup = R.pintar(ctx, e, t)
    finally:
        ImageDraw.ImageDraw.text = orig
    reg = []
    espia = MC._espia(reg, True, orig)

    def con_tam(self_, xy, text, fill=None, font=None, *a, **k):
        n = len(reg)
        r_ = espia(self_, xy, text, fill, font, *a, **k)
        img = getattr(self_, "_image", None)
        for x in reg[n:]:
            x["tam"] = getattr(font, "size", 0)
            if img is None or img.size != sup.size:
                x["fill"] = None   # dibujado en una capa chica: sus coordenadas no son las del lienzo
        return r_
    ImageDraw.ImageDraw.text = con_tam
    try:
        R.pintar(ctx, e, t)
    finally:
        ImageDraw.ImageDraw.text = orig
    base = Image.new("RGBA", sup.size, (10, 10, 10, 255))
    base.alpha_composite(sup)
    S = np.asarray(base.convert("RGB"), np.float64)
    out = []
    for r in reg:
        f = r["fill"]
        if not isinstance(f, (tuple, list)) or len(f) < 3 or (len(f) > 3 and f[3] < 200):
            continue
        x0, y0, x1, y1 = r["caja"]
        x0, y0 = max(0, x0), max(0, y0)
        m = np.asarray(r["msc"], np.float64)[: y1 - y0, : x1 - x0] > 127
        zona = S[y0:y1, x0:x1][: m.shape[0], : m.shape[1]]
        if not m.any() or zona.shape[:2] != m.shape:
            continue
        lt = _lum1(np.asarray(f[:3], np.float64))
        ls = _lum1(zona[m])
        rat = (np.maximum(lt, ls) + 0.05) / (np.minimum(lt, ls) + 0.05)
        out.append((r["texto"], tuple(f[:3]), float(np.median(rat)), r.get("tam", 0)))
    return out


class TestContraste(unittest.TestCase):
    """R6: decoración bajo texto y acento legible."""

    @classmethod
    def setUpClass(cls):
        import tempfile
        cls.tmp = tempfile.mkdtemp(prefix="wb_contraste_")
        import galeria
        galeria.assets(cls.tmp, (230, 80, 40))

    def _callout(self):
        e = _muestra("callout")
        e["captura"] = os.path.join(self.tmp, os.path.basename(e["captura"]))
        return e

    def _con_marca(self, ancho=1080, alto=1920):
        import render_plan as R
        R.formato(ancho, alto)
        R.aplicar_brand(DJ)
        R.aplicar_globales({"escenas": []})
        R._ESCALA.clear()
        self.addCleanup(R.aplicar_brand, None)   # el pack entero (fuentes, solape), no solo los colores
        self.addCleanup(R._instalar_tokens, dict(acento=R.NEUTRO["acento"],
                                                  acento_oscuro=R.NEUTRO["acento_oscuro"],
                                                  negro=R.NEUTRO["negro"], blanco=R.NEUTRO["blanco"],
                                                  gris=R.NEUTRO["gris"]))
        return R

    def test_el_dragon_no_pasa_detras_del_enfasis(self):
        from PIL import ImageFilter
        R = self._con_marca(1920, 1080)
        e = _muestra("apertura")
        ctx = R.Ctx()
        t = e["to"] - 1.4   # "Ahora es / automático." asentado, el dragón detrás
        capa = R.pintar(ctx, e, t)
        orig = R.marca_fondo
        R.marca_fondo = lambda *a, **k: True
        try:
            solo_texto = R.pintar(ctx, e, t)
        finally:
            R.marca_fondo = orig
        F = Image.new("RGBA", capa.size, (10, 10, 10, 255))
        F.alpha_composite(capa)
        A = np.asarray(F.convert("RGB"), np.float64)
        al = np.asarray(solo_texto.getchannel("A"))
        texto, fuerte = al > 20, al > 230
        self.assertGreater(fuerte.sum(), 500, "no se encontró el titular")
        # la tinta del titular (la mediana: el énfasis rojo domina) contra lo
        # MÁS claro que la rodea (p95 de un anillo de 7 px fuera de la letra)
        S = Image.new("RGBA", solo_texto.size, (10, 10, 10, 255))
        S.alpha_composite(solo_texto)
        lt = np.median(_lum1(np.asarray(S.convert("RGB"), np.float64)[fuerte]))
        cerca = np.asarray(Image.fromarray((fuerte * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(15))) > 0
        lejos = np.asarray(Image.fromarray((texto * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5))) > 0
        fondo = np.percentile(_lum1(A[cerca & ~lejos]), 95)
        ratio = (max(lt, fondo) + 0.05) / (min(lt, fondo) + 0.05)
        self.assertGreaterEqual(ratio, 3.0, f"titular display contra lo que lo rodea: {ratio:.2f}:1")

    def test_enfasis_sobre_placa_y_fuente_sobre_captura(self):
        casos = [("marca", self._con_marca)]
        def neutra():
            R = _motor()
            R._instalar_tokens(dict(acento=R.NEUTRO["acento"], acento_oscuro=R.NEUTRO["acento_oscuro"],
                                    negro=R.NEUTRO["negro"], blanco=R.NEUTRO["blanco"], gris=R.NEUTRO["gris"]))
            return R
        for nombre, preparar in casos + [("neutra", neutra)]:
            R = preparar()
            e = self._callout()
            res = _contrastes(R, e, e["to"] - 0.5)
            self.assertTrue(res, "sin textos medidos")
            for texto, fill, rat, _tam in res:
                with self.subTest(pack=nombre, texto=texto):
                    self.assertGreaterEqual(rat, 4.5, f"'{texto}' {fill} a {rat:.2f}:1")

    def test_kicker_y_rec_chicos_se_leen(self):
        for tipo in ("orbita", "audiowave"):
            R = self._con_marca()
            e = _muestra(tipo)
            res = _contrastes(R, e, e["to"] - 0.5)
            # el texto CHICO (bajo DISPLAY_MIN) de acento: kicker, REC, el
            # énfasis del rótulo. El display se mide arriba (el dragón) y
            # aquí la superficie no ve el apagado de `deco_bajo_texto`
            acento = [r[:3] for r in res if r[1] != tuple(R.BLANCO[:3]) and r[1] != tuple(R.GRIS[:3])
                      and 0 < r[3] < R.DISPLAY_MIN]
            self.assertTrue(acento, f"{tipo}: sin texto de acento medido")
            for texto, fill, rat in acento:
                with self.subTest(tipo=tipo, texto=texto):
                    self.assertGreaterEqual(rat, 4.5, f"{tipo} '{texto}' {fill} a {rat:.2f}:1")

    def test_las_particulas_no_cruzan_el_titulo(self):
        R = _motor()
        e = _muestra("orbita")
        for t in (1.2, 2.0, e["to"] - 0.5):
            capa = R.pintar(R.Ctx(), e, t)
            orig = R.ImageDraw.ImageDraw.ellipse
            R.ImageDraw.ImageDraw.ellipse = lambda *a, **k: None
            try:
                sin = R.pintar(R.Ctx(), e, t)
            finally:
                R.ImageDraw.ImageDraw.ellipse = orig
            from PIL import ImageFilter
            titulo = (np.asarray(sin.getchannel("A")) > 200).astype(np.uint8) * 255
            # zona de respeto: la letra y 6 px alrededor (un punto pegado a una
            # letra se lee como un agujero o una tilde de más)
            zona = np.asarray(Image.fromarray(titulo).filter(ImageFilter.MaxFilter(13))) > 0
            def plano(c):
                f = Image.new("RGBA", c.size, (10, 10, 10, 255))
                f.alpha_composite(c)
                return np.asarray(f.convert("RGB"), np.float64)
            dif = np.abs(plano(capa) - plano(sin)).sum(-1) > 60
            with self.subTest(t=t):
                self.assertLess(int((dif & zona).sum()), 40, "partículas pegadas a la letra del título")

    def test_en_vivo_no_pasa_el_margen(self):
        for ancho, alto in ((1080, 1920), (1920, 1080)):
            R = _motor(ancho, alto)
            e = R.completar_escena(_muestra("countdown"), 0)
            for t in np.arange(e["to"] - 1.1, e["to"] + 0.3, 0.05):
                a = np.asarray(R.encuadre(R.Ctx(), e, 0, float(t)).getchannel("A")) > 110
                cols = np.where(a.any(axis=0))[0]
                if not len(cols):
                    continue
                with self.subTest(formato=(ancho, alto), t=round(float(t), 2)):
                    self.assertGreaterEqual(cols.min(), R.SAFE["left"] - 2)
                    self.assertLessEqual(cols.max(), R.W - R.SAFE["right"] + 2)


if __name__ == "__main__":
    unittest.main()
