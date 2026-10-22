#!/usr/bin/env python3
"""Tests de la puerta de entrega (qa_entrega.py) y del encabezado de mapa.md.

Dos garantias que la auditoria funcional descubre:

1. El motor cierra SIEMPRE con fundido a negro (render_plan.py: el ultimo
   frame es negro por diseno). Si la puerta no le dice a auto_qa que ignore
   ese cierre, toda pieza hecha con esta skill rechaza su propio final y
   `ENTREGA: aprobada` es inalcanzable. Este test lo fija.

2. El encabezado de mapa.md es la tarjeta de presentacion de la skill
   ("52 referencias, 36 scripts, ..."). Si envejece, miente sobre su propio
   alcance. El auditor tiene que detectarlo.

Run with: python3 -m unittest discover -s SKILL/scripts/_tests
"""

import importlib.util
import os
import re
import shutil
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
BASE = os.path.dirname(SCRIPTS)
QA_ENTREGA = os.path.join(SCRIPTS, "qa_entrega.py")
AUDITAR = os.path.join(SCRIPTS, "auditar_mapa.py")


def _cargar(ruta, nombre):
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestPuertaEntrega(unittest.TestCase):
    """La puerta tiene que poder dejar pasar el cierre en negro."""

    def setUp(self):
        with open(QA_ENTREGA, encoding="utf-8") as f:
            self.src = f.read()

    def test_pasa_el_ignorar_fin_a_auto_qa(self):
        # si la puerta llama a auto_qa sin el margen, el cierre en negro
        # bloquea TODA pieza de la skill
        self.assertRegex(self.src, r"(?s)auto_qa\.py.*?--ignorar-fin",
                         "la puerta debe pasar --ignorar-fin a auto_qa")
        m = re.search(r"_paso_autoqa\([^)]*ignorar_fin", self.src)
        self.assertIsNotNone(m, "_paso_autoqa debe recibir ignorar_fin")

    def test_el_margen_por_defecto_cubre_el_fundido_de_cierre(self):
        # el motor funde los ultimos 0.8 s (render_plan.py): el margen por
        # defecto tiene que ser >= 0.5 s o el cierre vuelve a ser defecto
        m = re.search(r'"--ignorar-fin",\s*type=float,\s*default=([\d.]+)', self.src)
        self.assertIsNotNone(m, "la puerta debe exponer --ignorar-fin")
        self.assertGreaterEqual(float(m.group(1)), 0.5,
                                "el margen por defecto debe cubrir el fundido de cierre")

    def test_el_margen_se_puede_anular(self):
        # quien quiera exigir que ni el ultimo medio segundo tenga negro
        # tiene que poder ponerlo en 0
        m = re.search(r'"--ignorar-fin",\s*type=float,\s*default=([\d.]+)', self.src)
        self.assertIsNotNone(m)
        self.assertGreaterEqual(float(m.group(1)), 0.0)
        self.assertIn("ignorar_fin", self.src)

    def test_el_motor_efectivamente_cierra_en_negro(self):
        """El invariante que hace necesario el margen.

        Si el motor dejara de fundir a negro, el margen sobraria; si el motor
        empieza a fundir mas de 0.5 s, el margen se queda corto. Este test
        ata las dos puntas: el motor y la puerta.
        """
        with open(os.path.join(SCRIPTS, "render_plan.py"), encoding="utf-8") as f:
            motor = f.read()
        m = re.search(r"if\s+dur-t\s*<\s*([\d.]+)\s*:", motor)
        self.assertIsNotNone(m, "el motor debe fundir a negro al cierre")
        fundido = float(m.group(1))
        m2 = re.search(r'"--ignorar-fin",\s*type=float,\s*default=([\d.]+)', self.src)
        self.assertIsNotNone(m2)
        self.assertGreaterEqual(float(m2.group(1)), fundido / 2,
                                "el margen de la puerta debe cubrir el fundido de cierre")


class TestConteoDelEncabezado(unittest.TestCase):
    """El encabezado de mapa.md no puede quedarse viejo."""

    def _arbol(self, raiz, declarados, reales):
        refs = os.path.join(raiz, "references")
        scripts = os.path.join(raiz, "scripts")
        os.makedirs(os.path.join(scripts, "ffmpeg_tools"), exist_ok=True)
        os.makedirs(os.path.join(scripts, "_tests"), exist_ok=True)
        mapa = os.path.join(refs, "mapa.md")
        os.makedirs(refs, exist_ok=True)
        with open(mapa, "w", encoding="utf-8") as f:
            f.write("# Mapa de prueba\n\n"
                    f"{declarados[0]} referencias, {declarados[1]} scripts, "
                    f"{declarados[2]} herramientas de ffmpeg y {declarados[3]} suites de tests.\n")
        for i in range(declarados[0] - 1):
            open(os.path.join(refs, f"r{i}.md"), "w").close()
        for i in range(declarados[1]):
            open(os.path.join(scripts, f"s{i}.py"), "w").close()
        for i in range(declarados[2]):
            open(os.path.join(scripts, "ffmpeg_tools", f"f{i}.py"), "w").close()
        for i in range(declarados[3]):
            open(os.path.join(scripts, "_tests", f"t{i}.py"), "w").close()
        return mapa

    def test_detecta_un_conteo_que_no_cuadra(self):
        mod = _cargar(AUDITAR, "auditar_mapa_conteo")
        raiz = tempfile.mkdtemp(prefix="editoria_conteo_")
        try:
            mod.BASE = raiz
            mod.REFS = os.path.join(raiz, "references")
            # declara 9 referencias, 3 scripts, 2 herramientas y 4 suites
            # (hay 1 referencia real extra + los .md declarados)
            self._arbol(raiz, (9, 3, 2, 4), (9, 3, 2, 4))
            with open(os.path.join(raiz, "references", "mapa.md"), "w", encoding="utf-8") as f:
                f.write("# Mapa de prueba\n\n"
                        "99 referencias, 3 scripts, 2 herramientas de ffmpeg y 4 suites de tests.\n")
            problemas = []
            mod._chequear_conteos(problemas)
            self.assertTrue(problemas, "un conteo viejo tiene que reportarse")
            self.assertIn("conteo obsoleto", problemas[0]["tipo"])
            self.assertIn("99", problemas[0]["msg"])
        finally:
            shutil.rmtree(raiz, ignore_errors=True)

    def test_no_reporta_nada_si_los_conteos_cuadran(self):
        mod = _cargar(AUDITAR, "auditar_mapa_conteo_ok")
        raiz = tempfile.mkdtemp(prefix="editoria_conteo_ok_")
        try:
            mod.BASE = raiz
            mod.REFS = os.path.join(raiz, "references")
            self._arbol(raiz, (9, 3, 2, 4), (9, 3, 2, 4))
            problemas = []
            mod._chequear_conteos(problemas)
            self.assertEqual(problemas, [], "conteos correctos no generan problemas")
        finally:
            shutil.rmtree(raiz, ignore_errors=True)

    def test_la_skill_real_pasa(self):
        mod = _cargar(AUDITAR, "auditar_mapa_conteo_real")
        problemas = []
        mod._chequear_conteos(problemas)
        self.assertEqual(problemas, [],
                         f"el encabezado de mapa.md esta viejo: {problemas}")


if __name__ == "__main__":
    unittest.main()
