#!/usr/bin/env python3
"""La escena que la puerta recortaba, compuesta por el camino de la puerta.

`validate_skill.py` recorre las 45 muestras en 9:16 y 16:9. Este test no
repite ese recorrido: fija el defecto que esa puerta cazó en el renderer
compartido, y la armonía que la puerta no numera sola (un rótulo, un rol,
el acento del token neutro). Llama `SCENES`, `RECORTES`, `escala_segura` y
`medir_animacion.solapes`, no una copia de la medición.

Run with: python3 -m unittest scripts._tests.test_armonia_catalogo
"""

import glob
import json
import os
import re
import sys
import unittest
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
BASE = os.path.dirname(SCRIPTS)
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, os.path.join(SCRIPTS, "ffmpeg_tools"))


def _muestras():
    with open(os.path.join(SCRIPTS, "escenas_muestra.json"), encoding="utf-8") as fh:
        data = json.load(fh)
    return data.get("escenas", data)


class TestMedianocheCabe(unittest.TestCase):
    """En 16:9 el teléfono se achica y la nota se agranda para seguir en el piso.

    El cuerpo de la muestra ya no cabe en una línea. Se parte con `linewrap`.
    Recortarlo escribía el copy en `RECORTES` y la pieza lo perdía en silencio.
    """

    def test_el_copy_cabe_en_los_dos_formatos_sin_bajar_del_piso(self):
        import render_plan as R
        import medir_animacion as MA
        from PIL import Image, ImageDraw

        e0 = dict(_muestras()["medianoche"], tipo="medianoche")
        original = ImageDraw.ImageDraw.text
        orig_resize = Image.Image.resize
        fallos = []
        try:
            for ancho, alto in ((1080, 1920), (1920, 1080)):
                R.formato(ancho, alto)
                ctx = R.Ctx()
                e = dict(e0)
                R.RECORTES.clear()
                R._ESCALA.clear()
                dibujado = []
                escala_tel = []

                def espia(self, xy, text, fill=None, font=None, *a, **k):
                    if font is not None and str(text).strip() and any(c.isalnum() for c in str(text)):
                        dibujado.append((str(text), float(getattr(font, "size", 0)), self.im.size))
                    return original(self, xy, text, fill, font, *a, **k)

                def resize(self, size, *a, **k):
                    if self.size == (560, 1140) and size[0]:
                        escala_tel.append(size[0] / 560)
                    return orig_resize(self, size, *a, **k)

                ImageDraw.ImageDraw.text = espia
                Image.Image.resize = resize
                try:
                    R.SCENES["medianoche"](ctx, e, 4.2)
                except Exception as ex:
                    fallos.append(f"{ancho}x{alto} {type(ex).__name__}: {ex}")
                    continue
                finally:
                    ImageDraw.ImageDraw.text = original
                    Image.Image.resize = orig_resize
                recortes = [rc for rc in list(R.RECORTES)
                            if not str(rc.get("texto", "")).lower().endswith(
                                (".wav", ".mp3", ".mp4", ".m4a", ".aiff", ".mov"))]
                if recortes:
                    fallos.append(f"{ancho}x{alto} recorta {recortes[0]['texto'][:40]!r}")
                if not escala_tel:
                    fallos.append(f"{ancho}x{alto} el telefono no se escalo")
                    continue
                esc = escala_tel[-1]
                for n in e["notificaciones"]:
                    for campo in ("titulo", "texto"):
                        for palabra in str(n[campo]).replace("*", "").split():
                            if not any(palabra in t for t, _, _ in dibujado):
                                fallos.append(f"{ancho}x{alto} falta {palabra!r}")
                if any("…" in t for t, _, _ in dibujado):
                    fallos.append(f"{ancho}x{alto} hay elipsis")
                bajo = [f"{t[:16]!r} {round(s * esc)}px"
                        for t, s, sz in dibujado
                        if sz != (R.W, R.H) and s * esc < R.MIN_LETRA - 0.05]
                if bajo:
                    fallos.append(f"{ancho}x{alto} bajo el piso {bajo[0]}")
                if any(s < R.MIN_LETRA for _, s, sz in dibujado if sz == (R.W, R.H)):
                    fallos.append(f"{ancho}x{alto} rotulo bajo el piso")
                R._ESCALA.clear()
                factor = R.escala_segura(ctx, e, 0)
                if factor < 0.75:
                    fallos.append(f"{ancho}x{alto} zona x{factor:.2f}")
                R._ESCALA.clear()
                for p in MA.solapes(R, ctx, [e], float(e["to"]) + 5):
                    fallos.append(f"{ancho}x{alto} {p}")
        finally:
            ImageDraw.ImageDraw.text = original
            Image.Image.resize = orig_resize
        self.assertEqual(fallos, [])

    def test_el_copy_largo_cabe_entero_dentro_del_telefono(self):
        """copy x2 es el copy que escribe un agente. Las tarjetas se apilan
        dentro del teléfono: el texto no se sale del bitmap y no se elide."""
        import render_plan as R
        import medir_animacion as MA
        from PIL import Image, ImageDraw

        e0 = dict(_muestras()["medianoche"], tipo="medianoche")
        original = ImageDraw.ImageDraw.text
        orig_ac = Image.Image.alpha_composite
        orig_resize = Image.Image.resize
        fallos = []
        try:
            for ancho, alto in ((1080, 1920), (1920, 1080)):
                R.formato(ancho, alto)
                ctx = R.Ctx()
                e = dict(MA.copy_x2(R, e0), tipo="medianoche")
                R.RECORTES.clear()
                textos, puestos, marcos, escala_tel = [], [], [], []
                sello = 0

                def marca(img):
                    nonlocal sello
                    token = getattr(img, "_qa_medianoche", None)
                    if token is None:
                        sello += 1
                        token = sello
                        setattr(img, "_qa_medianoche", token)
                    return token

                def espia(self, xy, text, fill=None, font=None, *a, **k):
                    if font is not None and str(text).strip() and any(
                            c.isalnum() for c in str(text)):
                        img = self._image
                        bb = self.textbbox(xy, str(text), font=font,
                                           anchor=k.get("anchor"))
                        # Sello en la imagen, no id(): Pillow reutiliza el id
                        # en cuanto la tarjeta anterior se libera.
                        textos.append((marca(img), str(text), bb[1], bb[3],
                                       img.size, float(font.size)))
                    return original(self, xy, text, fill, font, *a, **k)

                def comp(self, im, *a, **k):
                    dest = a[0] if a else k.get("dest", (0, 0))
                    if not isinstance(dest, tuple):
                        dest = (0, 0)
                    if self.size == (560, 1140) and im.size[0] < 560:
                        dy, ah = dest[1], im.size[1]
                        token = getattr(im, "_qa_medianoche", None)
                        quedan = []
                        for tid, texto, top, bot, sz, tam in textos:
                            if token is not None and tid == token:
                                puestos.append((texto, dy + top, dy + bot,
                                                tam, dy, ah))
                            else:
                                quedan.append((tid, texto, top, bot, sz, tam))
                        textos[:] = quedan
                        marcos.append((dy, ah))
                    elif self.size == im.size and self.size != (560, 1140):
                        origen, destino = marca(im), marca(self)
                        textos[:] = [
                            (destino if tid == origen else tid, texto, top, bot, sz, tam)
                            for tid, texto, top, bot, sz, tam in textos]
                    return orig_ac(self, im, *a, **k)

                def resize(self, size, *a, **k):
                    if self.size == (560, 1140) and size[0]:
                        escala_tel.append(size[0] / 560.0)
                    return orig_resize(self, size, *a, **k)

                ImageDraw.ImageDraw.text = espia
                Image.Image.alpha_composite = comp
                Image.Image.resize = resize
                try:
                    R.SCENES["medianoche"](ctx, e, 4.2)
                except Exception as ex:
                    fallos.append(f"{ancho}x{alto} {type(ex).__name__}: {ex}")
                    continue
                finally:
                    ImageDraw.ImageDraw.text = original
                    Image.Image.alpha_composite = orig_ac
                    Image.Image.resize = orig_resize
                if not escala_tel:
                    fallos.append(f"{ancho}x{alto} el telefono no se escalo")
                    continue
                esc = escala_tel[-1]
                if not marcos:
                    fallos.append(f"{ancho}x{alto} no se pego ninguna tarjeta")
                    continue

                reloj_fondo = 0.0
                vistos = Counter()
                for iid, texto, top, bot, sz, tam in textos:
                    if "…" in texto:
                        fallos.append(f"{ancho}x{alto} elide {texto[-24:]!r}")
                    if sz != (560, 1140):
                        continue
                    if top < 0 or bot > 1140:
                        fallos.append(
                            f"{ancho}x{alto} reloj fuera {texto!r} {bot:.0f}")
                    reloj_fondo = max(reloj_fondo, bot)
                    if tam * esc < R.MIN_LETRA - 0.05:
                        fallos.append(
                            f"{ancho}x{alto} reloj bajo el piso {texto!r}")
                for texto, top, bot, tam, dy, ah in puestos:
                    if "…" in texto:
                        fallos.append(f"{ancho}x{alto} elide {texto[-24:]!r}")
                    if dy < 0 or dy + ah > 1140 or top < 0 or bot > 1140:
                        fallos.append(
                            f"{ancho}x{alto} {texto[-24:]!r} sale a y={bot:.0f}")
                    if tam * esc < R.MIN_LETRA - 0.05:
                        fallos.append(f"{ancho}x{alto} bajo el piso {texto[-16:]!r}")
                    vistos.update(texto.split())
                for dy, ah in marcos:
                    if dy < reloj_fondo - 1:
                        fallos.append(
                            f"{ancho}x{alto} tarjeta pisa el reloj y={dy:.0f}")
                        break
                need = Counter()
                for n in e["notificaciones"]:
                    for campo in ("titulo", "texto"):
                        need.update(str(n[campo]).replace("*", "").split())
                for pal, veces in need.items():
                    if vistos[pal] < veces:
                        fallos.append(
                            f"{ancho}x{alto} falta {pal!r} ({vistos[pal]}/{veces})")
                recortes = [rc for rc in list(R.RECORTES)
                            if not str(rc.get("texto", "")).lower().endswith(
                                (".wav", ".mp3", ".mp4", ".m4a", ".aiff", ".mov"))]
                if recortes:
                    fallos.append(
                        f"{ancho}x{alto} recorta {recortes[0]['texto'][:40]!r}")
        finally:
            ImageDraw.ImageDraw.text = original
            Image.Image.alpha_composite = orig_ac
            Image.Image.resize = orig_resize
        self.assertEqual(fallos, [])


class TestRotuloUnico(unittest.TestCase):
    """Un rótulo: la misma altura canónica y el rol `rotulo` de la escala."""

    def test_la_altura_y_el_rol_no_dependen_de_la_escena(self):
        import render_plan as R
        from PIL import Image, ImageDraw

        original = ImageDraw.ImageDraw.text
        try:
            for ancho, alto, frac in ((1080, 1920, 0.20), (1920, 1080, 0.16)):
                R.formato(ancho, alto)
                self.assertEqual(R.rotulo_y(), R.vy(frac))
                ctx = R.Ctx()
                layer = Image.new("RGBA", (R.W, R.H), (0, 0, 0, 0))
                sizes = []

                def espia(self, xy, text, fill=None, font=None, *a, **k):
                    if font is not None and any(c.isalnum() for c in str(text)):
                        sizes.append(int(getattr(font, "size", 0)))
                    return original(self, xy, text, fill, font, *a, **k)

                ImageDraw.ImageDraw.text = espia
                R.rotulo(ctx, layer, 2.0, "Marca", 0.0)
                R.rotulo(ctx, layer, 2.0, "Otra pieza", 0.0)
                self.assertTrue(sizes, f"el rotulo no dibujo texto en {ancho}x{alto}")
                self.assertTrue(all(s == R.ESCALA["rotulo"] for s in sizes), sizes)
                self.assertGreaterEqual(R.ESCALA["nota"], R.MIN_LETRA)
        finally:
            ImageDraw.ImageDraw.text = original


class TestAcentoLibre(unittest.TestCase):
    """Sin pack, el acento es el token neutro. La marca de ejemplo no vive en el motor."""

    def test_el_acento_por_defecto_es_el_neutro_y_no_hay_marca_quemada(self):
        import render_plan as R
        from _comun import NEUTRO

        self.assertEqual(tuple(R.ACENTO[:3]), tuple(NEUTRO["acento"][:3]))
        marcas, colores = [], []
        for ruta in glob.glob(os.path.join(BASE, "brand", "*.json")):
            marcas.append(os.path.splitext(os.path.basename(ruta))[0])
            with open(ruta, encoding="utf-8") as fh:
                data = json.load(fh)
            c = ((data.get("colores") or data.get("colors") or {}).get("acento")
                 or (data.get("colors") or {}).get("primary"))
            if isinstance(c, str):
                colores.append(c.lstrip("#"))
        literal = re.compile("|".join(re.escape(m) for m in marcas + colores) or r"$^", re.I)
        with open(os.path.join(SCRIPTS, "render_plan.py"), encoding="utf-8") as fh:
            src = fh.read()
        hallado = literal.search(src)
        self.assertIsNone(hallado, hallado.group(0) if hallado else "")


if __name__ == "__main__":
    unittest.main()
