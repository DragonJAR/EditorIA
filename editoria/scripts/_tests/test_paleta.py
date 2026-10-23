#!/usr/bin/env python3
"""Tests del sistema de paletas del modo libre.

El problema que motivó esto: la paleta neutra del modo libre era un
rojo-naranja casi igual al rojo del pack de ejemplo. Toda pieza sin marca
salía con la firma visual de una marca que el usuario no había pedido, y el
skill no tenía ninguna teoría del color que permitiera elegir otra.

Estos tests fijan el contrato:

1. El catálogo existe y cada paleta trae el juego completo de tokens.
2. El respaldo del modo libre NO es el color de ningún pack del repo.
3. Cada acento pasa WCAG AA (>= 4.5:1) sobre su fondo (se usa para texto).
4. La marca manda sobre la paleta (precedencia en el motor).
5. Una paleta que no existe es un error explícito, no un default silencioso.
6. La referencia de paleta está indexada en el mapa.

(Ojo: este archivo no puede nombrar ninguna marca — el validador prohibe
marcas quemadas en scripts/. Por eso el test compara contra los packs que
encuentra en brand/ en vez de contra uno en concreto.)

Run with: python3 -m unittest discover -s SKILL/scripts/_tests
"""

import json
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
BASE = os.path.dirname(SCRIPTS)
sys.path.insert(0, os.path.join(SCRIPTS, "ffmpeg_tools"))

from _comun import (NEUTRO, PALETAS, info_paleta, paleta_libre,  # noqa: E402
                    hex_a_rgb, contraste, texto_sobre, TEXTO_CLARO)

TOKENS = ("acento", "acento_oscuro", "negro", "blanco", "gris")


def _luminancia(rgb):
    """Luminancia relativa WCAG (sRGB lineal)."""
    out = []
    for v in rgb[:3]:
        c = v / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * out[0] + 0.7152 * out[1] + 0.0722 * out[2]


def _contraste(a, b):
    la, lb = _luminancia(a), _luminancia(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


class TestPaletas(unittest.TestCase):
    def test_el_catalogo_tiene_paletas(self):
        self.assertGreaterEqual(len(PALETAS), 6,
                                "el modo libre necesita un catalogo de paletas, no un color fijo")

    def test_cada_paleta_trae_el_juego_completo_de_tokens(self):
        for nombre, p in PALETAS.items():
            for t in TOKENS:
                self.assertIn(t, p, f"la paleta '{nombre}' no declara '{t}'")
            self.assertIn("esquema", p, f"la paleta '{nombre}' no dice su armonia")
            self.assertIn("tono", p, f"la paleta '{nombre}' no dice su temperatura")
            self.assertIn("para", p, f"la paleta '{nombre}' no dice para que brief sirve")

    def test_ningun_acento_rompe_el_contraste_aa(self):
        # el acento se usa para texto de enfasis: >= 4.5:1 sobre el fondo
        for nombre, p in PALETAS.items():
            c = _contraste(p["acento"], p["negro"])
            self.assertGreaterEqual(c, 4.5,
                                    f"la paleta '{nombre}' no pasa AA (contraste {c:.2f})")

    def test_la_tinta_contrasta_con_el_fondo(self):
        for nombre, p in PALETAS.items():
            c = _contraste(p["blanco"], p["negro"])
            self.assertGreaterEqual(c, 7.0,
                                    f"la paleta '{nombre}': la tinta no se lee sobre el fondo")

    def test_el_texto_sobre_el_acento_sigue_al_fondo(self):
        # el hook de un short va sobre un box del ACENTO de la marca, y el
        # acento lo elige el usuario: un texto de color FIJO deja el titular
        # ilegible en media paleta (menta daba 2:1 con blanco).
        for nombre, p in PALETAS.items():
            texto = texto_sobre(p["acento"])
            c = contraste(texto, p["acento"])
            self.assertGreaterEqual(c, 4.5,
                                    f"la paleta '{nombre}': el texto sobre el acento no se "
                                    f"lee (contraste {c:.2f})")

    def test_el_color_fijo_del_hook_no_llegaba_al_piso(self):
        # por que existe texto_sobre(): con el color fijo, NINGUNA paleta
        # llegaba al piso de 4.5:1. si este test deja de fallar, el catalogo
        # cambio y hay que revisar si el helper sigue haciendo falta.
        malos = [n for n, p in PALETAS.items()
                 if contraste(TEXTO_CLARO, p["acento"]) < 4.5]
        self.assertTrue(malos,
                        "el color fijo ya pasa en todas las paletas: revisa si "
                        "texto_sobre() sigue siendo necesario")

    def test_el_hook_no_usa_un_color_de_texto_fijo(self):
        # el color del titular tiene que seguir al acento: si el codigo
        # vuelve a un color fijo, el texto se lee sobre un fondo que no
        # controla y vuelve el problema de la tinta fija.
        with open(os.path.join(SCRIPTS, "ffmpeg_tools", "shorts_plan.py"),
                  encoding="utf-8") as f:
            src = f.read()
        self.assertIn("fontcolor={texto_sobre(acento)}", src,
                      "el hook tiene que calcular el color del texto sobre el acento")
        self.assertNotIn("fontcolor=#FAF8F6", src,
                         "el hook no puede volver a un color de texto fijo")

    def test_el_respaldo_no_es_el_color_de_ningun_pack(self):
        # el modo libre no puede parecerse a una marca: se compara con TODOS
        # los packs del repo (el de ejemplo incluido), sin nombrarlos aqui
        # (el validador prohibe marcas quemadas en scripts/)
        import glob
        packs = glob.glob(os.path.join(BASE, "brand", "*.json"))
        self.assertTrue(packs, "deberia haber al menos un pack de ejemplo")
        for pack_path in packs:
            with open(pack_path, encoding="utf-8") as fh:
                pack = json.load(fh)
            col = dict(pack.get("colors") or {})
            col.update(pack.get("colores") or {})
            acento_pack = str(col.get("acento") or "").lstrip("#").lower()
            if not acento_pack:
                continue
            r, g, b = NEUTRO["acento"]
            respaldo = f"{r:02x}{g:02x}{b:02x}"
            self.assertNotEqual(respaldo, acento_pack,
                                f"el respaldo del modo libre es el color del pack {pack_path}")
            # ni el mismo tono (dato de color, no solo de hex): rojo = hue < 30 o > 330
            import colorsys
            hue = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)[0] * 360
            self.assertFalse(hue < 30 or hue > 330,
                             f"el respaldo sigue siendo un rojo (hue {hue:.0f}°)")

    def test_una_paleta_inexistente_es_error_explicito(self):
        with self.assertRaises(SystemExit):
            paleta_libre("no-existe")

    def test_sin_nombre_devuelve_el_respaldo(self):
        self.assertEqual(paleta_libre(None)["acento"], NEUTRO["acento"])
        self.assertEqual(paleta_libre("menta")["acento"], PALETAS["menta"]["acento"])

    def test_el_respaldo_no_duplica_los_tokens_de_una_paleta(self):
        """DRY: el fallback se DERIVA del catálogo, no se escribe dos veces.

        Si el fallback viviera aparte, cambiar la paleta por defecto
        dejaría el respaldo viejo (y el modo libre volvería a parecerse a
        una marca que el usuario no pidió).
        """
        from _comun import PALETA_POR_DEFECTO, TOKENS_COLOR
        self.assertIn(PALETA_POR_DEFECTO, PALETAS)
        for t in TOKENS_COLOR:
            self.assertEqual(NEUTRO[t], PALETAS[PALETA_POR_DEFECTO][t],
                             f"el token '{t}' del respaldo esta duplicado")

    def test_la_api_separa_tokens_y_metadatos(self):
        """`paleta_libre` da tokens; `info_paleta` da la armonia y el uso.

        Mezclar las dos cosas obligaba a filtrar dicts en cada consumidor.
        """
        tokens = paleta_libre("menta")
        self.assertIn("acento", tokens)
        self.assertNotIn("esquema", tokens, "los metadatos no viajan con los tokens")
        info = info_paleta("menta")
        self.assertIn("esquema", info)
        self.assertIn("tono", info)
        self.assertNotIn("acento", info)


class TestPrecedenciaEnElMotor(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(SCRIPTS, "render_plan.py"), encoding="utf-8") as f:
            self.src = f.read()

    def test_la_marca_manda_sobre_la_paleta(self):
        # el bloque de precedencia: brand > paleta > acento > respaldo
        i_br = self.src.find("aplicar_brand(brand_path)")
        i_pal = self.src.find("aplicar_paleta(")
        self.assertIsNotNone(i_br) and self.assertIsNotNone(i_pal)
        m = re.search(r"if brand_path:\s*\n\s*aplicar_brand\(brand_path\)[^\n]*\n"
                      r"\s*elif [^\n]*paleta[^\n]*:\s*\n\s*aplicar_paleta\(", self.src)
        self.assertIsNotNone(m, "la precedencia debe ser marca > paleta > acento")

    def test_la_cli_tiene_el_flag_de_paleta(self):
        self.assertIn('"--paleta"', self.src, "render_plan.py debe exponer --paleta")


class TestReferenciaDePaleta(unittest.TestCase):
    def test_la_referencia_existe_y_esta_indexada(self):
        p = os.path.join(BASE, "references", "paleta.md")
        self.assertTrue(os.path.exists(p), "references/paleta.md debe existir")
        with open(p, encoding="utf-8") as fh:
            txt = fh.read()
        self.assertIn("Dominio: color", txt, "la referencia declara su dominio")
        with open(os.path.join(BASE, "references", "mapa.md"), encoding="utf-8") as fh:
            mapa = fh.read()
        self.assertIn("paleta.md", mapa, "el mapa indexa la referencia de paleta")
        for nombre in PALETAS:
            self.assertIn(nombre, txt,
                          f"la referencia documenta la paleta '{nombre}'")

    def test_la_referencia_explica_que_la_marca_manda(self):
        with open(os.path.join(BASE, "references", "paleta.md"), encoding="utf-8") as fh:
            txt = fh.read()
        self.assertIn("manda", txt)


class TestResolutorDeIdentidad(unittest.TestCase):
    """Una sola puerta resuelve la identidad de todas las herramientas."""

    def test_precedencia_color_marca_paleta_respaldo(self):
        import glob
        from _comun import acento_efectivo
        # el pack se busca por ruta (este archivo no puede nombrarlo: el
        # validador prohibe marcas quemadas en scripts/)
        packs = glob.glob(os.path.join(BASE, "brand", "*.json"))
        self.assertTrue(packs, "deberia haber un pack de ejemplo")
        pack = packs[0]
        marca = acento_efectivo(brand=pack)
        paleta = acento_efectivo(paleta="menta")
        respaldo = acento_efectivo()
        explicito = acento_efectivo(color="#ABCDEF")
        self.assertEqual(explicito, (171, 205, 239), "el color explicito manda")
        self.assertNotEqual(marca, paleta)
        self.assertNotEqual(paleta, respaldo)
        self.assertEqual(respaldo, NEUTRO["acento"])
        # la marca gana sobre la paleta
        self.assertEqual(marca, acento_efectivo(brand=pack, paleta="menta"))

    def test_tokens_efectivos_da_el_juego_completo(self):
        from _comun import tokens_efectivos
        t = tokens_efectivos(paleta="menta")
        for k in ("acento", "acento_oscuro", "negro", "blanco", "gris"):
            self.assertIn(k, t, f"faltan los tokens '{k}'")
        self.assertEqual(t["acento"], PALETAS["menta"]["acento"])

    def test_las_herramientas_aceptan_la_paleta(self):
        """El mismo juego de flags en las que pintan con acento.

        La galería les pasa la identidad a todas: si una no acepta --paleta,
        la galería se rompe (y antes se rompía con --brand en audio_viz).
        """
        for cli in ("ffmpeg_tools/caption.py", "ffmpeg_tools/thumbnail.py",
                    "ffmpeg_tools/shorts_plan.py", "audio_viz.py"):
            with open(os.path.join(SCRIPTS, cli), encoding="utf-8") as f:
                src = f.read()
            self.assertIn('"--paleta"', src, f"{cli} debe aceptar --paleta")
            self.assertIn('"--brand"', src, f"{cli} debe aceptar --brand")


if __name__ == "__main__":
    unittest.main()
