#!/usr/bin/env python3
"""Contratos de layout y contraste de la pasada de diseño (familia W-B).

Cada clase fija UNA causa raíz, medida sobre el frame que se entrega:

- R5.4 CAPA FIJA: el rótulo (`rotulo_y()`) y la línea de fuente
  (`pie_fuente`) van en una capa que NO escala ni se desplaza con el
  encuadre (`_crecer`, push-in, flotación): el rótulo cae a la misma altura
  de pantalla en toda escena y en todo instante, y la fuente sobre UNA línea
  base por encima del borde seguro inferior.
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
        return f[0] - f0[0]

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
                f = _filas(_magenta(_compuesto(R, e, e["to"] - 0.5, "fuente")))
                self.assertIsNotNone(f, f"{tipo}: sin línea de fuente")
                fondos[tipo] = f[1]
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


if __name__ == "__main__":
    unittest.main()
