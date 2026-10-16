#!/usr/bin/env python3
"""Tests unitarios deterministas de utilidades core, frontmatter, subtítulos
y catálogo de escenas (30 escenas, primitivas DRY de Ronda 4).

Se ejecutan con: python3 -m unittest discover -s SKILL/scripts/_tests -v
"""
import ast
import json
import os
import re
import sys
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(AQUI)
SKILL = os.path.dirname(SCRIPTS)
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, os.path.join(SCRIPTS, "ffmpeg_tools"))

import _comun as C  # noqa: E402
import _delivery as D  # noqa: E402
import caption as CAP  # noqa: E402


class TestFrontmatterYCatalogo(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(SKILL, "SKILL.md"), encoding="utf-8") as fh:
            self.sk = fh.read()
        m = re.match(r"^---\n(.*?)\n---\n", self.sk, re.S)
        self.fm = m.group(1) if m else ""

    def test_frontmatter_present_and_valid_yaml_scalars(self):
        self.assertTrue(self.fm)
        for ln in self.fm.splitlines():
            if not ln.strip() or ln.lstrip().startswith("#"):
                continue
            kv = re.match(r"^[A-Za-z0-9_-]+:\s*(.+)$", ln)
            self.assertIsNotNone(kv, f"línea inválida en frontmatter: {ln}")
            v = kv.group(1).strip()
            if (v.startswith("'") and v.endswith("'")) or (v.startswith('"') and v.endswith('"')):
                continue
            if (v.startswith("{") and v.endswith("}")) or (v.startswith("[") and v.endswith("]")):
                continue
            self.assertNotIn(": ", v, f"escalar YAML sin comillas contiene ': ': {ln}")

    def test_claude_skill_frontmatter_fields(self):
        self.assertIsNotNone(re.search(r"^name:\s*editoria\s*$", self.fm, re.M))
        self.assertIn("license: MIT", self.fm)
        self.assertIn("compatibility:", self.fm)
        desc = re.search(r"^description:\s*(.+)$", self.fm, re.M)
        self.assertIsNotNone(desc)
        val = desc.group(1).strip().strip("'\"")
        self.assertLess(len(val), 1024)
        self.assertIn("use when", val.lower())
        self.assertIn("do not use", val.lower())

    def test_scenes_ast_matches_muestras_and_ronda4_primitives(self):
        with open(os.path.join(SCRIPTS, "render_plan.py"), encoding="utf-8") as fh:
            rp_src = fh.read()
        tree = ast.parse(rp_src)
        fn_names = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
        for prim in ("tarjeta_cristal", "boton_halo", "insignia_3d", "sc_hero", "sc_bento"):
            self.assertIn(prim, fn_names)
        scenes_keys = []
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "SCENES" for t in node.targets):
                scenes_keys = [k.value for k in node.value.keys if isinstance(k, ast.Constant)]
        self.assertEqual(len(scenes_keys), 30)
        self.assertIn("hero", scenes_keys)
        self.assertIn("bento", scenes_keys)
        with open(os.path.join(SCRIPTS, "escenas_muestra.json"), encoding="utf-8") as fh:
            muestras = json.load(fh)["escenas"]
        self.assertEqual(set(scenes_keys), set(muestras.keys()))


class TestComunYDelivery(unittest.TestCase):
    def test_hex_a_rgb_and_color_hex(self):
        self.assertEqual(C.color_hex("#e8480c"), "E8480C")
        self.assertEqual(C.hex_a_rgb("#E8480C"), (232, 72, 12))

    def test_segmentos_enfasis(self):
        self.assertEqual(
            C.segmentos_enfasis("Videos con *física real* hoy"),
            [("Videos con ", False), ("física real", True), (" hoy", False)],
        )

    def test_parse_and_fmt_time(self):
        self.assertAlmostEqual(C.parse_time("01:30.5"), 90.5)
        self.assertEqual(C.fmt_srt_time(90.5), "00:01:30,500")
        self.assertEqual(C.fmt_smpte_time(1.5, 30.0), "00:00:01:15")

    def test_safe_margins_px(self):
        sm_v = D.safe_margins_px("reels", 1080, 1920)
        self.assertGreater(sm_v["bottom"], sm_v["top"])
        sm_h = D.safe_margins_px("youtube", 1920, 1080)
        self.assertGreater(sm_h["left"], 0)


class TestCaptionHelpers(unittest.TestCase):
    def test_phrase_aware_avoids_trailing_leader_words(self):
        cues = [(0.0, 4.0, "Vamos a crear un video para tu marca hoy")]
        out = CAP.phrase_aware(cues, max_words=5)
        self.assertTrue(len(out) >= 2)
        for _, _, txt in out[:-1]:
            ult = txt.split()[-1].lower()
            self.assertNotIn(ult, CAP.LEADERS)

    def test_partir_fijo_fallback_wraps_long_line(self):
        txt = "Un lugar para volver cuando el mundo va demasiado rápido"
        wrapped, fijo = CAP._partir_fijo(txt, 160, 680, None)
        self.assertTrue(fijo)
        self.assertIn("\n", wrapped)


if __name__ == "__main__":
    unittest.main()
