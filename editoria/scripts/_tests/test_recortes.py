"""Regresión: ninguna etiqueta se recorta en silencio.

`stats` en 1:1 con la etiqueta real del reel («en Tether y USD Coin») salía
«en Tether y USD C…»: la etiqueta iba por la ruta de UNA línea. Ahora se
parte en 2 líneas y se encoge hasta el piso (`texto_que_cabe`); lo que ni
así cabe se anota en `render_plan.RECORTES`, viaja en la medición
(`medir_animacion` → `recortes`) y `qa_entrega` rechaza la pieza.
"""
import contextlib
import io
import os
import sys
import unittest

from PIL import ImageDraw

AQUI = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(AQUI)
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, os.path.join(SCRIPTS, "ffmpeg_tools"))

with contextlib.redirect_stdout(io.StringIO()):
    import render_plan as R  # noqa: E402
    import medir_animacion as MA  # noqa: E402
    import qa_entrega as QE  # noqa: E402


def _stats(etiqueta):
    return {"tipo": "stats", "from": 0, "to": 5, "titulo": "El impacto",
            "cards": [{"valor": 6300, "etiqueta": "impacto estimado", "acento": True},
                      {"valor": 3000, "etiqueta": "congelados"},
                      {"valor": 2300, "etiqueta": etiqueta}],
            "at": {"rotulo": 0.2, "card0": 0.7}}


def _textos(e, ancho=1080, alto=1080):
    R.formato(ancho, alto)
    ctx = R.Ctx()
    R.RECORTES.clear()
    vistos = []
    orig = ImageDraw.ImageDraw.text

    def espia(self, xy, texto, *a, **k):
        vistos.append(str(texto))
        return orig(self, xy, texto, *a, **k)
    ImageDraw.ImageDraw.text = espia
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            R.pintar(ctx, e, 4.5)
    finally:
        ImageDraw.ImageDraw.text = orig
    return vistos, list(R.RECORTES)


class EtiquetaLarga(unittest.TestCase):
    def test_stats_1x1_parte_sin_puntos(self):
        vistos, recortes = _textos(_stats("en Tether y USD Coin"))
        self.assertFalse([v for v in vistos if "…" in v], vistos)
        self.assertEqual(recortes, [])
        junto = " ".join(vistos)
        for palabra in ("Tether", "USD", "Coin"):
            self.assertIn(palabra, junto)

    def test_etiqueta_imposible_se_anota(self):
        larga = "una etiqueta imposible " * 12
        _, recortes = _textos(_stats(larga))
        self.assertTrue(recortes, "lo que no cabe ni partido al piso tiene que ir a RECORTES")


class LaPuertaLoRechaza(unittest.TestCase):
    def test_medir_lleva_los_recortes(self):
        larga = "una etiqueta imposible " * 12
        MA._W["R"], MA._W["ctx"] = R, {}
        MA.FORMATOS["1:1"] = (1080, 1080)
        with contextlib.redirect_stdout(io.StringIO()):
            r = MA.medir(("stats", "1:1", [_stats(larga)], 5.0, 6))
        self.assertTrue(r["recortes"])

    def test_qa_falla_con_recortes(self):
        fallos = QE._defectos_composicion(30, 1.0, [], recortes=["en Tether y USD Coin"])
        self.assertTrue(any("recortad" in f for f in fallos))
        self.assertEqual(QE._defectos_composicion(30, 1.0, []), [])


if __name__ == "__main__":
    unittest.main()
