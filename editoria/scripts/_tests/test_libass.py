#!/usr/bin/env python3
"""Tests del resolvedor de ffmpeg con libass.

El problema que motivó esto: el ffmpeg de Homebrew no trae libass, y
`brew install ffmpeg-full` lo deja *keg-only* (sin symlink, fuera del PATH).
El remedio que documentaba la skill era `export PATH=...`, pero dentro de un
agente cada llamada de shell es un proceso nuevo: el export no persiste, asi
que el agente ejecutaba `brew install ffmpeg-full`, veia el aviso, y cada
subtitulado quemado seguia fallando con el mismo error de siempre.

Estos tests fijan el contrato:

1. El listado de `-filters` se lee por NOMBRE de filtro, no por el texto de la
   descripcion (donde "libass" y "subtitles" aparecen citados sin ser filtros).
2. La comprobacion se cachea (no se lanza un ffmpeg por cada comando).
3. Los candidatos incluyen el keg de ffmpeg-full aunque no este en el PATH.
4. `ffmpeg_texto()` NUNCA devuelve un binario sin los filtros: si existe uno
   con libass, ese es el que se usa; si no existe, cae al del PATH y lo dice.
5. `ffmpeg_base(texto=True)` usa el binario resuelto; `ffmpeg_base()` sigue
   usando el del PATH (no se paga el coste de inspeccion en cada comando).
6. La documentacion dice que el binario se encuentra solo: si el doc vuelve a
   pedir un `export PATH` manual, el contrato queda roto.

Run with: python3 -m unittest discover -s SKILL/scripts/_tests
"""

import os
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
BASE = os.path.dirname(SCRIPTS)
sys.path.insert(0, os.path.join(SCRIPTS, "ffmpeg_tools"))

import _comun  # noqa: E402
from _comun import (  # noqa: E402
    FILTROS_TEXTO,
    ffmpeg_base,
    ffmpeg_con_texto,
    ffmpeg_texto,
    tiene_filtros_texto,
)

# Listado real de `-filters` (recortado): los filtros de texto y ruido real.
LISTADO_REAL = """File types:
 V.... = Video
Filters:
  T.. = Timeline support
  .S. = Slice threading
 .. abench            V->V       Benchmark part of a filtergraph.
 T. drawtext          V->V       Draw text on top of video frames using libfreetype library.
 .. ass               V->V       Render ASS subtitles onto input video using the libass library.
 .. subtitles         V->V       Render text subtitles onto input video using the libass library.
 ... anull            V->A       Pass the source unchanged to the output.
"""

# Un ffmpeg sin libass: no aparece ningun filtro de texto.
LISTADO_SIN_LIBASS = """File types:
 V.... = Video
Filters:
  T.. = Timeline support
 .. abench            V->V       Benchmark part of a filtergraph.
 ... anull            V->A       Pass the source unchanged to the output.
"""


class FiltroEnListado(unittest.TestCase):
    """El parser de `-filters`."""

    def test_detecta_cada_filtro_de_texto(self):
        for filtro in FILTROS_TEXTO:
            self.assertTrue(_comun._filtro_en_listado(LISTADO_REAL, filtro), filtro)

    def test_no_detecta_lo_que_no_esta(self):
        for filtro in ("libx264", "overlay", "drawbox", "nope"):
            self.assertFalse(_comun._filtro_en_listado(LISTADO_REAL, filtro), filtro)

    def test_ignora_la_descripcion_que_cita_el_nombre(self):
        """La trampa: la descripcion de un filtro puede citar otro.

        "Render text subtitles onto input video using the libass library."
        menciona "subtitles" y "libass" sin que ninguno sea un filtro. Si se
        buscara por substring, el ffmpeg SIN libass pareceria tenerlos.
        """
        listado = (" T. scale            V->V       Scale the input video size and/or convert the image format.\n"
                   " .. overlay          V->V       Overlay a video source on top of the input.\n")
        self.assertFalse(_comun._filtro_en_listado(listado, "subtitles"))
        self.assertFalse(_comun._filtro_en_listado(listado, "ass"))
        self.assertFalse(_comun._filtro_en_listado(listado, "drawtext"))
        self.assertTrue(_comun._filtro_en_listado(listado, "scale"))

    def test_ignora_la_leyenda_y_las_cabeceras(self):
        for linea in ("Filters:", "  T.. = Timeline support", " V.... = Video"):
            listado = linea + "\n"
            for filtro in FILTROS_TEXTO:
                self.assertFalse(_comun._filtro_en_listado(listado, filtro), linea)

    def test_listado_vacio(self):
        self.assertFalse(_comun._filtro_en_listado("", "drawtext"))


class TieneFiltrosTexto(unittest.TestCase):
    """La comprobacion contra el binario real."""

    def setUp(self):
        self._cache = dict(_comun._filtros_cache)
        _comun._filtros_cache.clear()

    def tearDown(self):
        _comun._filtros_cache.clear()
        _comun._filtros_cache.update(self._cache)

    def test_binario_inexistente(self):
        self.assertFalse(tiene_filtros_texto("/no/existe/ffmpeg"))

    def test_cachea_la_comprobacion(self):
        """No se lanza un ffmpeg por cada comando: se comprueba una vez."""
        llamadas = []
        real = subprocess.run

        def _fake(cmd, *a, **kw):
            llamadas.append(cmd)
            return real([sys.executable, "-c", "print('')"], capture_output=True, text=True)

        _comun.subprocess.run = _fake
        try:
            self.assertFalse(tiene_filtros_texto("/ruta/falsa"))
            self.assertFalse(tiene_filtros_texto("/ruta/falsa"))
        finally:
            _comun.subprocess.run = real
        self.assertEqual(len(llamadas), 1)


class Candidatos(unittest.TestCase):
    """La busqueda del binario con libass."""

    def test_incluye_el_keg_de_ffmpeg_full_aunque_no_este_en_el_path(self):
        """El caso real: ffmpeg-full es keg-only, no hay symlink en el PATH."""
        candidatos = _comun._candidatos_ffmpeg()
        del_path = shutil.which("ffmpeg")
        kegs = [c for c in candidatos if "ffmpeg-full" in c]
        if not kegs:
            self.skipTest("esta maquina no tiene ffmpeg-full instalado")
        self.assertNotEqual(kegs[0], del_path)
        self.assertIn(kegs[0], candidatos)

    def test_el_primero_es_el_del_path(self):
        candidatos = _comun._candidatos_ffmpeg()
        self.assertEqual(candidatos[0], shutil.which("ffmpeg"))

    def test_sin_duplicados(self):
        candidatos = _comun._candidatos_ffmpeg()
        self.assertEqual(len(candidatos), len(set(candidatos)))


class Resolucion(unittest.TestCase):
    """El contrato que la skill promete al agente."""

    def test_el_binario_resuelto_realmente_tiene_los_filtros(self):
        """Si hay un ffmpeg con libass, `ffmpeg_texto()` devuelve ESE."""
        ruta = ffmpeg_con_texto()
        if not ruta:
            self.skipTest("esta maquina no tiene ningun ffmpeg con libass")
        salida = subprocess.run([ruta, "-hide_banner", "-filters"],
                                capture_output=True, text=True, timeout=15).stdout
        for filtro in FILTROS_TEXTO:
            self.assertTrue(_comun._filtro_en_listado(salida, filtro),
                            f"{ruta} no trae {filtro}")

    def test_texto_siempre_devuelve_algo_usable(self):
        ruta = ffmpeg_texto()
        self.assertTrue(os.path.isfile(ruta))
        self.assertTrue(os.access(ruta, os.X_OK))

    def test_sin_libass_cae_al_del_path_y_no_falla(self):
        """Si no hay ninguno con libass, se usa el del PATH (y `_pista_libass`
        explica el arreglo en el error). Nunca una excepcion."""
        original = _comun._candidatos_ffmpeg
        _comun._candidatos_ffmpeg = lambda: [shutil.which("ffmpeg")]
        try:
            self.assertEqual(ffmpeg_texto(), shutil.which("ffmpeg"))
        finally:
            _comun._candidatos_ffmpeg = original

    def test_ffmpeg_base_texto_usa_el_binario_resuelto(self):
        self.assertEqual(ffmpeg_base(texto=True)[0], ffmpeg_texto())

    def test_ffmpeg_base_normal_no_inspecciona(self):
        """Sin texto no se paga la inspeccion: se usa el del PATH."""
        self.assertEqual(ffmpeg_base()[0], shutil.which("ffmpeg"))


class Documentacion(unittest.TestCase):
    """El doc y el codigo son el mismo contrato."""

    def _ref(self, nombre):
        return os.path.join(BASE, "references", nombre)

    def test_capacidades_dice_que_el_binario_se_encuentra_solo(self):
        texto = open(self._ref("capacidades.md"), encoding="utf-8").read()
        self.assertIn("ffmpeg-full", texto)
        self.assertIn("keg-only", texto)
        # El remedio no puede quedar como "exporta esto a mano": en un agente
        # cada llamada de shell es un proceso nuevo y el export no persiste.
        plano = texto.lower()
        self.assertIn("herramientas lo eligen", plano)
        self.assertIn("no hay que exportar nada a mano", plano)

    def test_el_mensaje_de_error_apunta_al_binario_resuelto(self):
        """La pista de libass sigue siendo util y no promete un export manual."""
        texto = open(self._ref("capacidades.md"), encoding="utf-8").read()
        self.assertIn("ffmpeg-full", texto)

    def test_check_env_usa_el_resolvedor(self):
        """check_env.py y las herramientas deben mirar el MISMO binario."""
        src = open(os.path.join(SCRIPTS, "check_env.py"), encoding="utf-8").read()
        self.assertIn("ffmpeg_con_texto", src)


if __name__ == "__main__":
    unittest.main()
