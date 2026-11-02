"""Regresiones del lote 1.11.2: composición común (centro, foco de demo,
moneda, títulos que parten), QA de balance/foco, paleta de una sola fuente,
plataforma deducida y capturas de muestra con el color del tema."""
import os, sys, tempfile, unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(AQUI)
SKILL = os.path.dirname(SCRIPTS)
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, os.path.join(SCRIPTS, "ffmpeg_tools"))
import render_plan as R  # noqa: E402
import qa_entrega as Q  # noqa: E402
import medir_animacion as M  # noqa: E402
from _comun import SINTAXIS_PALETA, ayuda_paleta, LETRA_MIN  # noqa: E402


class FocoDemo(unittest.TestCase):
    def test_objetivo_del_borde_no_se_corta(self):
        bw, bh, asp = 900, 520, 1000 / 1600
        p = {"x": 0.856, "y": 0.085, "zoom": 1.6}
        self.assertFalse(R.foco_recortado(p, asp, bw, bh))

    def test_caja_mas_grande_que_la_vista_se_detecta(self):
        p = {"x": 0.5, "y": 0.5, "zoom": 2.0, "caja": [0.8, 0.8]}
        self.assertTrue(R.foco_recortado(p, 0.625, 900, 520))

    def test_mapeo_cubrir_centra(self):
        x, y = R.a_vista_demo(0.5, 0.5, 0.8, 900, 500)
        self.assertAlmostEqual(x, 450, delta=1)
        self.assertAlmostEqual(y, 250, delta=1)

    def test_encuadre_queda_dentro(self):
        cx, cy = R.encuadre_foco(890, 10, 2.0, 900, 500)
        self.assertLessEqual(cx + 450, 900 + 1e-6)
        self.assertGreaterEqual(cy, 0)


class QA(unittest.TestCase):
    def test_desbalance_y_foco_son_fallos(self):
        f = Q._defectos_composicion(30, 1.0, [], desbalance=["hero@1s: bloque alto"], focos=["demo paso 1"])
        self.assertEqual(len(f), 2)
        self.assertTrue(any("descentrado" in x for x in f))
        self.assertTrue(any("zoom" in x for x in f))

    def test_solapes_conserva_su_firma(self):
        self.assertTrue(callable(M.solapes))
        self.assertTrue(callable(M.composicion_asentada))

    def test_letra_minima_unica(self):
        self.assertEqual(R.MIN_LETRA, LETRA_MIN)
        self.assertEqual(Q.LETRA_MIN, LETRA_MIN)


class Paleta(unittest.TestCase):
    def test_una_sola_fuente(self):
        skill = open(os.path.join(SKILL, "SKILL.md"), encoding="utf-8").read()
        self.assertIn(SINTAXIS_PALETA.split(": ", 1)[1], skill)
        self.assertIn(SINTAXIS_PALETA.split(": ", 1)[1], ayuda_paleta())
        campo = [c for c in R.PLAN_CAMPOS if c["nombre"] == "paleta"][0]
        self.assertIn(SINTAXIS_PALETA, campo["significado"])

    def test_skill_sin_azul_frio(self):
        skill = open(os.path.join(SKILL, "SKILL.md"), encoding="utf-8").read()
        self.assertNotIn("cold, identity-free blue", skill)
        self.assertLessEqual(len(skill.split()), 5000)


class Defectos(unittest.TestCase):
    def test_moneda_y_ruta_declaradas(self):
        mon = [p for p in R.esquema_de("oferta") if p["nombre"] == "moneda"][0]
        self.assertEqual(mon["defecto"], '"$"')
        ruta = [p for p in R.esquema_de("camino") if p["nombre"] == "ruta"][0]
        self.assertEqual(ruta["defecto"], '"s"')
        self.assertFalse(ruta["markup"])


class Capturas(unittest.TestCase):
    def test_resalte_sale_del_acento(self):
        import galeria
        from PIL import Image
        cols = []
        for ac in ((40, 160, 90), (60, 90, 220)):
            d = tempfile.mkdtemp()
            galeria.assets(d, ac)
            im = Image.open(os.path.join(d, "captura_muestra_2.png")).convert("RGB")
            cols.append(im.getpixel((800, 210)))
        self.assertNotEqual(cols[0], cols[1])
        for c in cols:
            self.assertNotEqual(c, (255, 236, 225))


if __name__ == "__main__":
    unittest.main()
