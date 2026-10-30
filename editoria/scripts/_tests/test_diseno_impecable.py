#!/usr/bin/env python3
"""Contratos de la pasada de diseño (feat/diseno-impecable, familia W-A).

Cada clase fija UNA causa raíz, medida sobre el frame que se entrega:

- R1 TEXTO: `draw_seg` respeta toda ancla y dibuja tramos enteros (con
  kerning), el punto de display se acerca a su letra, el texto con alfa se
  mezcla con la tarjeta (no la perfora), las cajas de resalte tienen el
  mismo aire a los dos lados y el "me gusta" no es un emoji.
- R3 MONO: la mono se resuelve por NOMBRE antes que por directorio (la
  preferida gana a la de último recurso), la empaquetada (IBM Plex Mono,
  OFL) es la del motor, el peso pedido se respeta y las etiquetas mono se
  leen (la tinta mediana del glifo llega a 4.5:1 sobre su superficie).

Run: python3 -m pytest -q -p no:cacheprovider _tests/test_diseno_impecable.py
"""

import copy
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, os.path.join(SCRIPTS, "ffmpeg_tools"))
FUENTES = os.path.join(os.path.dirname(SCRIPTS), "assets", "fonts")


def _muestra(tipo):
    with open(os.path.join(SCRIPTS, "escenas_muestra.json"), encoding="utf-8") as fh:
        e = copy.deepcopy(json.load(fh)["escenas"][tipo])
    e["tipo"] = tipo
    return e


def _lum(rgb):
    """Luminancia relativa WCAG de un array (..., 3) en 0..255."""
    c = np.asarray(rgb, np.float64) / 255.0
    c = np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]


def _motor(ancho=1080, alto=1920):
    import render_plan as R
    R.formato(ancho, alto)
    R.aplicar_globales({"escenas": []})
    R._ESCALA.clear()
    return R


def _frame(R, e, t, sin=None):
    """El frame compuesto sobre negro; `sin(font)` -> True suprime ese texto."""
    orig = ImageDraw.ImageDraw.text

    def espia(self, xy, text, fill=None, font=None, *a, **k):
        if sin is not None and font is not None and sin(font):
            return None
        return orig(self, xy, text, fill, font, *a, **k)
    ImageDraw.ImageDraw.text = espia
    try:
        capa = R.pintar(R.Ctx(), e, t)
    finally:
        ImageDraw.ImageDraw.text = orig
    fondo = Image.new("RGBA", (R.W, R.H), (0, 0, 0, 255))
    fondo.alpha_composite(capa)
    return np.asarray(fondo.convert("RGB"), np.float64)


def _tinta(img):
    """Caja de la tinta (alfa/luz > 40) de una imagen L o RGBA."""
    a = np.asarray(img.split()[-1] if img.mode == "RGBA" else img)
    ys, xs = np.nonzero(a > 40)
    return (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())) if len(xs) else None


class TestTexto(unittest.TestCase):
    """R1: los helpers de texto."""

    def setUp(self):
        self.R = _motor()
        self.f = self.R.Ctx().fT(120, 800)

    def _seg(self, sg, anchor, xy=(700, 300)):
        m = Image.new("L", (1400, 600), 0)
        self.R.draw_seg(ImageDraw.Draw(m), xy, sg, self.f, 255, 255, anchor=anchor)
        return _tinta(m)

    def _ref(self, txt, anchor, xy=(700, 300)):
        m = Image.new("L", (1400, 600), 0)
        ImageDraw.Draw(m).text(xy, txt, font=self.f, fill=255, anchor=anchor)
        return _tinta(m)

    def test_draw_seg_respeta_cada_ancla(self):
        for anchor in ("la", "lm", "ls", "ma", "mm", "rs", "md", "lt"):
            got, ref = self._seg([("Datos ", ""), ("clave", "x")], anchor), self._ref("Datos clave", anchor)
            for g, r in zip(got, ref):
                self.assertLessEqual(abs(g - r), 2, f"ancla {anchor}: {got} vs {ref}")

    def test_draw_seg_conserva_el_kerning(self):
        got = self._seg([("AVATAR ", "x"), ("Tyrone", "")], "la")
        ref = self._ref("AVATAR Tyrone", "la")
        self.assertLessEqual(abs((got[2] - got[0]) - (ref[2] - ref[0])), 3,
                             f"ancho de tinta {got} vs {ref}: el tramo perdió el kerning")

    def test_el_punto_de_display_se_acerca_a_su_letra(self):
        m = Image.new("L", (1400, 600), 0)
        self.R.draw_seg(ImageDraw.Draw(m), (100, 100), [("automático.", "")], self.f, 255, 255)
        cols = np.nonzero(np.asarray(m).max(axis=0) > 40)[0]
        huecos = np.diff(cols)
        hueco_punto = int(huecos[-1] if huecos[-1] > 1 else 0)
        # el último hueco de tinta es el de la "o" al punto
        tramo = cols[np.nonzero(huecos > 1)[0][-1] + 1:]
        hueco_punto = int(tramo[0] - cols[np.nonzero(huecos > 1)[0][-1]])
        self.assertLessEqual(hueco_punto, int(120 * 0.10),
                             f"el punto queda a {hueco_punto} px de su letra a 120 px")

    def test_texto_con_alfa_no_perfora_la_tarjeta(self):
        capa = Image.new("RGBA", (600, 200), (0, 0, 0, 0))
        d = ImageDraw.Draw(capa)
        d.rectangle([0, 0, 600, 200], fill=(40, 40, 40, 255))
        self.R.draw_seg(d, (20, 40), [("Hola", "")], self.f, (255, 255, 255, 100), (255, 255, 255, 100))
        a = np.asarray(capa)
        self.assertEqual(int(a[..., 3].min()), 255, "el texto con alfa perforó la tarjeta")
        self.assertGreater(int(a[..., 0].max()), 40 + 40, "el texto con alfa no se ve")

    def test_el_autor_del_quote_se_funde_sin_agujeros(self):
        R = self.R
        e = R.completar_escena(_muestra("quote"), 0)
        t = e["at"]["autor"] + 0.06
        cajas = []
        orig = ImageDraw.ImageDraw.text

        def espia(s, xy, text, fill=None, font=None, *a, **k):
            if "Laura" in str(text):
                cajas.append(s.textbbox(xy, text, font=font, *a, **k))
            return orig(s, xy, text, fill, font, *a, **k)
        ImageDraw.ImageDraw.text = espia
        try:
            capa = R.pintar(R.Ctx(), e, t)
        finally:
            ImageDraw.ImageDraw.text = orig
        self.assertTrue(cajas)
        x0, y0, x1, y1 = (int(v) for v in cajas[-1])
        alfa = np.asarray(capa)[y0:y1, x0:x1, 3]
        self.assertGreaterEqual(int(alfa.min()), 250, "el autor perfora su tarjeta al fundirse")

    def test_callout_etiqueta_y_detalle_no_se_pisan(self):
        R = self.R
        e = R.completar_escena(_muestra("callout"), 0)
        cajas = {}
        orig = ImageDraw.ImageDraw.text

        def espia(s, xy, text, fill=None, font=None, *a, **k):
            bb = s.textbbox(xy, text, font=font, *a, **k)
            for clave in ("resultado", "Del total"):
                if clave in str(text):
                    cajas[clave] = bb
            return orig(s, xy, text, fill, font, *a, **k)
        ImageDraw.ImageDraw.text = espia
        try:
            R.pintar(R.Ctx(), e, e["to"] - 0.5)
        finally:
            ImageDraw.ImageDraw.text = orig
        self.assertEqual(set(cajas), {"resultado", "Del total"})
        self.assertGreaterEqual(cajas["Del total"][1] - cajas["resultado"][3], R.ESCALA["nota"] * 0.2,
                                f"la etiqueta y el detalle se pisan: {cajas}")

    def _cajas_de_color(self, img, color, banda=None):
        """Columnas/filas del bloque de `color` exacto (±12) y la tinta blanca dentro."""
        a = np.asarray(img).astype(int)
        m = (np.abs(a - np.array(color)).max(axis=2) <= 12)
        # el BLOQUE (columnas con >= 30 px de color seguidos en vertical): el
        # trazo del icono y la raya del rótulo son finos y no cuentan
        xs = np.nonzero(m.sum(axis=0) >= 30)[0]
        tramos = np.split(xs, np.nonzero(np.diff(xs) > 1)[0] + 1)
        bloque = max(tramos, key=len)   # el más ancho: el icono es un aro fino
        x0, x1 = bloque.min(), bloque.max()
        ys = np.nonzero(m[:, x0:x1 + 1].sum(axis=1) >= (x1 - x0) * 0.3)[0]
        y0, y1 = ys.min(), ys.max()
        caja = a[y0:y1 + 1, x0:x1 + 1]
        blanco = caja.min(axis=2) > 200
        by, bx = np.nonzero(blanco)
        return (x0, y0, x1, y1), (x0 + bx.min(), y0 + by.min(), x0 + bx.max(), y0 + by.max()), a

    def test_la_caja_del_cartel_tiene_el_mismo_aire_y_deja_el_espacio_fuera(self):
        for ancho, alto in ((1080, 1920), (1920, 1080)):
            R = _motor(ancho, alto)
            e = R.completar_escena(_muestra("cartel"), 0)
            im = _frame(R, e, e["to"] - 0.6)
            caja, tinta, a = self._cajas_de_color(im, R.ACENTO)
            izq, der = tinta[0] - caja[0], caja[2] - tinta[2]
            arr, aba = tinta[1] - caja[1], caja[3] - tinta[3]
            self.assertLessEqual(abs(izq - der), 3, f"{ancho}x{alto}: aire {izq} vs {der}")
            self.assertLessEqual(abs(arr - aba), 4, f"{ancho}x{alto}: aire {arr} vs {aba}")
            # a la izquierda de la caja, en su franja, la tinta anterior ("con")
            # queda a un espacio de distancia, no pegada al bloque
            fr = a[caja[1]:caja[3] + 1, max(0, caja[0] - 40):caja[0]].min(axis=2) > 200
            cols = np.nonzero(fr.any(axis=0))[0]
            if len(cols):
                self.assertGreaterEqual(40 - cols.max(), 8, f"{ancho}x{alto}: la caja toca la palabra anterior")

    def test_el_marcador_del_quote_no_cubre_el_espacio_final(self):
        R = self.R
        e = R.completar_escena(_muestra("quote"), 0)
        im = _frame(R, e, e["to"] - 0.6)
        col = tuple(int(R.lerp(p_, a_, 0.35)) for p_, a_ in zip(R.PANEL, R.ACENTO))
        a = np.asarray(im).astype(int)
        m = np.abs(a - np.array(col)).max(axis=2) <= 6
        filas = np.nonzero(m.sum(axis=1) > 20)[0]
        self.assertTrue(len(filas))
        # cada franja (grupo de filas contiguas): aire izq vs der de la tinta
        grupos = np.split(filas, np.nonzero(np.diff(filas) > 1)[0] + 1)
        for g in grupos:
            fila = m[g[len(g) // 2]]
            xs = np.nonzero(fila)[0]
            x0, x1 = xs.min(), xs.max()
            tinta = (a[g[0]:g[-1] + 1, x0:x1 + 1].min(axis=2) > 200).any(axis=0)
            tx = np.nonzero(tinta)[0]
            izq, der = tx.min(), (x1 - x0) - tx.max()
            self.assertLessEqual(abs(izq - der), 4, f"marcador: aire {izq} vs {der}")

    def test_el_me_gusta_no_es_un_emoji(self):
        src = open(os.path.join(SCRIPTS, "render_plan.py"), encoding="utf-8").read()
        self.assertNotIn("\u2764", src)
        self.assertNotIn("❤", src)


class TestMono(unittest.TestCase):
    """R3: la mono del motor es la empaquetada, con peso, y se lee."""

    def test_busca_por_nombre_antes_que_por_directorio(self):
        import _plataforma as P
        with tempfile.TemporaryDirectory() as tmp:
            primero, segundo = Path(tmp, "a"), Path(tmp, "b")
            primero.mkdir(); segundo.mkdir()
            (primero / "UltimoRecurso.ttf").write_bytes(b"x")
            (segundo / "Preferida.ttf").write_bytes(b"x")
            orig = P.dirs_fuentes
            P.dirs_fuentes = lambda: [primero, segundo]
            try:
                hit = P._buscar_en_dirs(["Preferida.ttf", "UltimoRecurso.ttf"])
            finally:
                P.dirs_fuentes = orig
        self.assertEqual(Path(hit).name, "Preferida.ttf",
                         "el ORDEN de nombres manda: el primer directorio no "
                         "puede imponer la fuente de último recurso")

    def test_la_mono_del_motor_es_la_empaquetada(self):
        R = _motor()
        self.assertEqual(os.path.dirname(os.path.abspath(R.MONO)), os.path.abspath(FUENTES),
                         f"MONO debe ser la mono empaquetada, no {R.MONO}")
        self.assertIn("IBMPlexMono", os.path.basename(R.MONO))
        lic = open(os.path.join(FUENTES, "OFL.txt"), encoding="utf-8").read()
        self.assertIn("IBM Plex Mono", lic, "la licencia OFL debe nombrar la fuente empaquetada")

    def test_el_fallback_mono_del_pack_es_la_empaquetada(self):
        from _comun import fuente_marca
        pack = os.path.join(os.path.dirname(SCRIPTS), "brand", "carbon.json")
        R = _motor()
        hit = fuente_marca(pack, "etiquetas_mono", R.MONO_FAMILIA, "mono")
        self.assertTrue(hit and os.path.exists(hit))
        if "DejaVu" not in os.path.basename(hit):   # sin DejaVu instalada
            self.assertEqual(os.path.dirname(os.path.abspath(hit)), os.path.abspath(FUENTES))

    def test_el_peso_pedido_se_respeta(self):
        R = _motor()
        f4, f7 = R.font(R.MONO, 28, 400), R.font(R.MONO, 28, 700)
        tinta = []
        for f in (f4, f7):
            m = Image.new("L", (400, 60), 0)
            ImageDraw.Draw(m).text((4, 4), "24 leads hoy", font=f, fill=255)
            tinta.append(float(np.asarray(m, np.float64).sum()))
        self.assertGreater(tinta[1], tinta[0] * 1.12,
                           "peso 700 debe dibujar un trazo más grueso que 400")

    def test_las_etiquetas_mono_se_leen(self):
        """Tinta mediana del glifo mono vs su superficie >= 4.5:1 (AA).

        El color ya pasaba (medir_contraste mide el COLOR): lo que no se leía
        era el trazo de Courier New, tan fino que la mitad de sus píxeles
        quedaban a medio pintar (~3:1 de mediana)."""
        for tipo in ("leads", "handoff"):
            R = _motor()
            e = R.completar_escena(_muestra(tipo), 0)
            t = e["from"] + (e["to"] - e["from"]) * 0.85
            # la familia, no el archivo: el 700 dibuja con el hermano SemiBold
            fam = os.path.basename(R.MONO).rpartition("-")[0] + "-"
            con = _frame(R, e, t)
            sin = _frame(R, e, t, sin=lambda f: os.path.basename(
                str(getattr(f, "path", ""))).startswith(fam))
            dif = np.abs(con - sin).sum(axis=2) > 6
            self.assertGreater(int(dif.sum()), 200, f"{tipo}: no hay etiqueta mono a medir")
            lt, ls = _lum(con[dif]), _lum(sin[dif])
            r = (np.maximum(lt, ls) + 0.05) / (np.minimum(lt, ls) + 0.05)
            self.assertGreaterEqual(float(np.median(r)), 4.5,
                                    f"{tipo}: la mono se lee a {np.median(r):.2f}:1")


if __name__ == "__main__":
    unittest.main()
