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


class TestSubtitulosEnLaPuerta(unittest.TestCase):
    """Una pieza narrada para redes sin subtitulos declarados no pasa en silencio."""

    def setUp(self):
        self.mod = _cargar(QA_ENTREGA, "qa_entrega_subs")

    def _plan(self, **extra):
        plan = {"duracion": 10.0, "escenas": [
            {"tipo": "apertura", "from": 0, "to": 5, "voz": "Hola."},
            {"tipo": "final", "from": 5, "to": 10, "voz": "Adios."}]}
        plan.update(extra)
        return plan

    def test_narrada_para_reels_sin_declarar_falla(self):
        self.assertIsNotNone(self.mod._defecto_subtitulos(self._plan(), "reels"))

    def test_declarados_en_el_plan_pasan(self):
        self.assertIsNone(self.mod._defecto_subtitulos(
            self._plan(subtitulos=True), "reels"))

    def test_sin_voz_no_se_exigen(self):
        plan = {"escenas": [{"tipo": "apertura", "from": 0, "to": 5}]}
        self.assertIsNone(self.mod._defecto_subtitulos(plan, "reels"))

    def test_fuera_de_redes_no_se_exigen(self):
        self.assertIsNone(self.mod._defecto_subtitulos(self._plan(), "youtube"))


class TestMedirConNombreRaro(unittest.TestCase):
    """El paso de movimiento lee el JSON de medir_animacion, no un regex
    sobre su consola: un video con espacios o sin .mp4 se mide igual."""

    def test_video_con_espacios_se_mide(self):
        import subprocess as _sp
        mod = _cargar(QA_ENTREGA, "qa_entrega_medir")
        with tempfile.TemporaryDirectory() as d:
            video = os.path.join(d, "mi pieza.mov")
            _sp.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
                     "-i", "testsrc=duration=2:size=320x180:rate=10",
                     "-c:v", "libx264", "-pix_fmt", "yuv420p", video],
                    check=True, capture_output=True, timeout=120)
            paso = mod._paso_medir(video)
            self.assertNotEqual(paso["detalle"], "no se pudo medir")
            self.assertIn("nota", paso["detalle"])


class TestQuietoYOcupacionEnLaPuerta(unittest.TestCase):
    """La puerta lee `quieto_max` y `ocupacion` de la medicion y los juzga."""

    def setUp(self):
        self.mod = _cargar(QA_ENTREGA, "qa_entrega_quieto")

    def test_pieza_viva_y_llena_pasa(self):
        # muestra T1-T4 re-renderizada en HEAD: racha 0.25 s, ocupacion 0.44
        self.assertEqual(self.mod._defectos_movimiento(0.25, 0.44), [])

    def test_congelado_largo_falla(self):
        # video real del catalogo: 3.0 s congelado en un rotulo inferior
        fallos = self.mod._defectos_movimiento(3.0, 0.45)
        self.assertEqual(len(fallos), 1)
        self.assertIn("3.0", fallos[0])

    def test_banda_chica_falla(self):
        self.assertEqual(len(self.mod._defectos_movimiento(0.0, 0.10)), 1)

    def test_medicion_vieja_sin_las_claves_no_falla(self):
        self.assertEqual(self.mod._defectos_movimiento(None, None), [])

    def test_los_umbrales_son_los_del_medidor(self):
        """Un umbral = un numero: la puerta no puede divergir del medidor."""
        def const(ruta, nombre):
            with open(ruta, encoding="utf-8") as f:
                return float(re.search(rf"^{nombre}\s*=\s*([\d.]+)", f.read(), re.M).group(1))
        self.assertEqual(self.mod.QUIETO_MAX, const(os.path.join(SCRIPTS, "auto_qa.py"), "FROZEN_MAX"))
        self.assertEqual(self.mod.OCUPACION_MIN,
                         const(os.path.join(SCRIPTS, "medir_animacion.py"), "OCUPACION_MIN"))


class TestConteoDelEncabezado(unittest.TestCase):
    """El encabezado de mapa.md no puede quedarse viejo."""

    def _arbol(self, raiz, declarados):
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
            # el encabezado dice "suites de tests" y una suite es un modulo
            # test_*.py: si el fixture metiera cualquier .py, contaria como
            # suite sin serlo y el fixture probaria otra cosa.
            open(os.path.join(scripts, "_tests", f"test_t{i}.py"), "w").close()
        # un modulo de apoyo: es un archivo mas en _tests/, pero NO es una
        # suite. el encabezado no tiene que cambiar por su culpa.
        open(os.path.join(scripts, "_tests", "apoyo.py"), "w").close()
        return mapa

    def test_detecta_un_conteo_que_no_cuadra(self):
        mod = _cargar(AUDITAR, "auditar_mapa_conteo")
        raiz = tempfile.mkdtemp(prefix="editoria_conteo_")
        try:
            mod.BASE = raiz
            mod.REFS = os.path.join(raiz, "references")
            # declara 9 referencias, 3 scripts, 2 herramientas y 4 suites
            # (hay 1 referencia real extra + los .md declarados)
            self._arbol(raiz, (9, 3, 2, 4))
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
            self._arbol(raiz, (9, 3, 2, 4))
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
