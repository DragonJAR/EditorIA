#!/usr/bin/env python3
"""Tests unitarios deterministas para utilidades core, frontmatter, subtítulos
y catálogo de 30 escenas + 17 primitivas DRY de EditorIA (stdlib-only).
"""
import ast
import json
import os
import re
import sys
import unittest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.dirname(TESTS_DIR)
SKILL_DIR = os.path.dirname(SCRIPTS_DIR)
FFMPEG_TOOLS_DIR = os.path.join(SCRIPTS_DIR, "ffmpeg_tools")

for p in (SCRIPTS_DIR, FFMPEG_TOOLS_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

import _comun  # noqa: E402
import _delivery  # noqa: E402
import caption  # noqa: E402


class TestFrontmatterAndSkillSpec(unittest.TestCase):
    """Verifica que el frontmatter de SKILL.md cumpla la guía Skill-for-Claude."""

    def setUp(self):
        with open(os.path.join(SKILL_DIR, "SKILL.md"), encoding="utf-8") as fh:
            self.sk = fh.read()
        m = re.match(r"^---\n(.*?)\n---\n", self.sk, re.S)
        self.fm = m.group(1) if m else ""

    def test_frontmatter_present_and_valid_yaml_lines(self):
        self.assertTrue(bool(self.fm))
        for ln in self.fm.splitlines():
            if not ln.strip() or ln.lstrip().startswith("#"):
                continue
            kv = re.match(r"^[A-Za-z0-9_-]+:\s*(.+)$", ln)
            self.assertIsNotNone(kv, f"Línea YAML inválida: {ln}")
            v = kv.group(1).strip()
            if (v.startswith("'") and v.endswith("'")) or (v.startswith('"') and v.endswith('"')):
                continue
            if (v.startswith("{") and v.endswith("}")) or (v.startswith("[") and v.endswith("]")):
                continue
            self.assertNotIn(": ", v, f"Valor sin comillas con ': ' en frontmatter: {ln}")

    def test_required_and_recommended_fields(self):
        self.assertRegex(self.fm, re.compile(r"^name:\s*editoria\s*$", re.M))
        self.assertRegex(self.fm, re.compile(r"^license:\s*MIT\s*$", re.M))
        compat = re.search(r"^compatibility:\s*(.+)$", self.fm, re.M)
        self.assertIsNotNone(compat)
        c_val = compat.group(1).strip().strip("'\"")
        self.assertTrue(1 <= len(c_val) <= 500)
        desc = re.search(r"^description:\s*(.+)$", self.fm, re.M)
        self.assertIsNotNone(desc)
        d_val = desc.group(1).strip().strip("'\"")
        self.assertLess(len(d_val), 1024)
        self.assertIn("use when", d_val.lower())
        self.assertIn("do not use", d_val.lower())


class TestComunUtilities(unittest.TestCase):
    """Pruebas de funciones deterministas en scripts/ffmpeg_tools/_comun.py."""

    def test_segmentos_enfasis(self):
        self.assertEqual(
            _comun.segmentos_enfasis("Videos con *física real* hoy"),
            [("Videos con ", False), ("física real", True), (" hoy", False)],
        )
        self.assertEqual(_comun.segmentos_enfasis(""), [])

    def test_color_hex_and_rgb(self):
        self.assertEqual(_comun.color_hex("#e8480c"), "E8480C")
        self.assertEqual(_comun.color_hex("0x1a2b3c"), "1A2B3C")
        self.assertEqual(_comun.hex_a_rgb("#E8480C"), (232, 72, 12))

    def test_parse_and_format_time(self):
        self.assertAlmostEqual(_comun.parse_time("01:30.5"), 90.5)
        self.assertAlmostEqual(_comun.parse_time("00:01:05,250"), 65.25)
        self.assertAlmostEqual(_comun.parse_time("00:00:02:15", fps=30.0), 2.5)
        self.assertEqual(_comun.fmt_srt_time(65.25), "00:01:05,250")
        self.assertEqual(_comun.fmt_smpte_time(2.5, 30.0), "00:00:02:15")

    def test_colores_marca_neutral_and_pack(self):
        import glob
        neutro = _comun.colores_marca(None)
        self.assertEqual(neutro["acento"], (232, 72, 12))
        packs = sorted(glob.glob(os.path.join(SKILL_DIR, "brand", "*.json")))
        self.assertTrue(len(packs) >= 1)
        pack_col = _comun.colores_marca(packs[0])
        self.assertNotEqual(pack_col["acento"], (232, 72, 12))


class TestDeliverySpecs(unittest.TestCase):
    """Pruebas de márgenes seguros y zonas de pantalla final en _delivery.py."""

    def test_safe_margins_vertical_and_horizontal(self):
        m_reels = _delivery.safe_margins_px("reels", 1080, 1920)
        self.assertGreater(m_reels["bottom"], m_reels["top"])
        self.assertGreater(m_reels["right"], 0)
        m_yt = _delivery.safe_margins_px("youtube", 1920, 1080)
        self.assertEqual(m_yt["top"], m_yt["bottom"])

    def test_end_screen_zones_inside_frame(self):
        zonas = _delivery.end_screen_px(1920, 1080)
        self.assertIn("marca", zonas)
        for _, (x, y, w, h) in zonas.items():
            self.assertGreaterEqual(x, 0)
            self.assertGreaterEqual(y, 0)
            self.assertLessEqual(x + w, 1920)
            self.assertLessEqual(y + h, 1080)


class TestCaptionLogic(unittest.TestCase):
    """Pruebas de fraseo consciente y saltos de línea fijos en caption.py."""

    def test_clean_word_preserves_numbers_and_contractions(self):
        self.assertEqual(caption.clean_word("¡100%!"), "100%")
        self.assertEqual(caption.clean_word("«3.5»"), "3.5")
        self.assertEqual(caption.clean_word("don't,"), "don't")

    def test_phrase_aware_never_ends_on_leader_word(self):
        cues = [(0.0, 4.0, "Un lugar para volver cuando el mundo va rápido")]
        agrupados = caption.phrase_aware(cues, max_words=5)
        self.assertGreaterEqual(len(agrupados), 2)
        for _, _, txt in agrupados[:-1]:
            ultima = txt.split()[-1].lower()
            self.assertNotIn(ultima, caption.LEADERS)

    def test_partir_fijo_wraps_long_line(self):
        texto = "Un lugar para volver cuando el mundo va demasiado rápido"
        partido, fijo = caption._partir_fijo(texto, 160, 680, None)
        self.assertTrue(fijo)
        self.assertIn("\n", partido)


class TestSceneCatalogAndPrimitivesAST(unittest.TestCase):
    """Verifica las 30 escenas y 17 primitivas DRY en render_plan.py y muestras."""

    def setUp(self):
        rp_path = os.path.join(SCRIPTS_DIR, "render_plan.py")
        with open(rp_path, encoding="utf-8") as fh:
            self.tree = ast.parse(fh.read())
        with open(os.path.join(SCRIPTS_DIR, "escenas_muestra.json"), encoding="utf-8") as fh:
            self.muestras = json.load(fh)["escenas"]

    def test_scenes_dict_matches_muestras_and_has_30_scenes(self):
        scenes_keys = []
        for node in self.tree.body:
            if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "SCENES" for t in node.targets):
                if isinstance(node.value, ast.Dict):
                    scenes_keys = [k.value for k in node.value.keys if isinstance(k, ast.Constant)]
        self.assertEqual(len(scenes_keys), 30)
        self.assertEqual(set(scenes_keys), set(self.muestras.keys()))
        self.assertIn("hero", scenes_keys)
        self.assertIn("bento", scenes_keys)

    def test_all_dry_primitives_and_new_scene_functions_exist(self):
        funcs = {n.name for n in self.tree.body if isinstance(n, ast.FunctionDef)}
        requeridas = {
            "barra_h", "cuenta_up", "arco", "particulas", "cuadricula",
            "linewrap", "text_reveal", "kenburns", "smoothstep", "cursor",
            "onda_clic", "odometro", "estrellas", "imagen_ajustada",
            "tarjeta_cristal", "boton_halo", "insignia_3d",
            "sc_hero", "sc_bento",
        }
        self.assertTrue(requeridas.issubset(funcs), f"Faltan funciones: {requeridas - funcs}")

    def test_all_muestras_have_valid_timing_window(self):
        for nombre, m in self.muestras.items():
            self.assertIn("from", m, nombre)
            self.assertIn("to", m, nombre)
            self.assertGreater(m["to"], m["from"], nombre)
            self.assertIsInstance(m.get("at", {}), dict, nombre)


if __name__ == "__main__":
    unittest.main()
