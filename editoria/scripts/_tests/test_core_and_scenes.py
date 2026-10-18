#!/usr/bin/env python3
"""Tests unitarios deterministas de utilidades core, frontmatter, nombres,
subtítulos y catálogo de escenas (30 escenas, primitivas DRY de Ronda 4).

Se ejecutan con: python3 -m unittest discover -s editoria/scripts/_tests -v
"""
import ast
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(AQUI)
SKILL = os.path.dirname(SCRIPTS)
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, os.path.join(SCRIPTS, "ffmpeg_tools"))

import _comun as C  # noqa: E402
import _delivery as D  # noqa: E402
import auditar_plan as AP  # noqa: E402
import caption as CAP  # noqa: E402


class TestFrontmatterYCatalogo(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(SKILL, "SKILL.md"), encoding="utf-8") as fh:
            self.sk = fh.read()
        m = re.match(r"^---\n(.*?)\n---\n", self.sk, re.S)
        self.fm = m.group(1) if m else ""

    def test_frontmatter_present_and_valid_yaml_scalars(self):
        self.assertTrue(self.fm)
        en_bloque = False
        for ln in self.fm.splitlines():
            if not ln.strip() or ln.lstrip().startswith("#"):
                continue
            if ln.startswith("  ") and en_bloque:
                sub = re.match(r"^\s+[A-Za-z0-9_-]+:\s*(.+)$", ln)
                self.assertIsNotNone(sub, f"subclave inválida en bloque YAML: {ln}")
                sv = sub.group(1).strip()
                if (sv.startswith("'") and sv.endswith("'")) or (sv.startswith('"') and sv.endswith('"')):
                    continue
                if sv.startswith("[") and sv.endswith("]"):
                    continue
                self.assertNotIn(": ", sv, f"sub-escalar YAML sin comillas contiene ': ': {ln}")
                continue
            en_bloque = False
            if re.match(r"^[A-Za-z0-9_-]+:\s*$", ln):
                en_bloque = True
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

    def test_naming_and_structure_compliance_with_guide(self):
        # 1. SKILL.md exact case-sensitive spelling
        self.assertIn("SKILL.md", os.listdir(SKILL))
        # 2. Folder name in strict kebab-case and matching frontmatter name
        folder_name = os.path.basename(SKILL)
        self.assertRegex(folder_name, r"^[a-z0-9]+(-[a-z0-9]+)*$")
        self.assertEqual(folder_name, "editoria")
        # 3. No README.md or .zip anywhere inside skill folder
        for dp, _, fn in os.walk(SKILL):
            if "__pycache__" in dp:
                continue
            for f in fn:
                self.assertFalse(f.lower().startswith("readme"), f"README prohibido dentro de la skill: {f}")
                self.assertFalse(f.lower().endswith(".zip"), f".zip prohibido dentro de la skill: {f}")
        # 4. All references in strict kebab-case
        for f in os.listdir(os.path.join(SKILL, "references")):
            if not f.startswith("."):
                self.assertRegex(f, r"^[a-z0-9]+(-[a-z0-9]+)*\.(md|json)$")
        # 5. Required sections from Skill-for-Claude.txt
        for sec in ("## Instructions", "## Examples", "## Troubleshooting", "## Performance Notes"):
            self.assertIn(sec, self.sk)

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


class TestCliHelpAndModularImports(unittest.TestCase):
    def test_previously_failing_clis_exit_zero_with_usage_on_help(self):
        for rel in (
            "alinear.py",
            "beat_grid.py",
            "medir_mezcla.py",
            os.path.join("ffmpeg_tools", "thumbnail.py"),
        ):
            p = os.path.join(SCRIPTS, rel)
            r = subprocess.run([sys.executable, p, "--help"], capture_output=True, text=True, timeout=15)
            self.assertEqual(r.returncode, 0, f"{rel} --help falló con rc={r.returncode}: {r.stderr}")
            self.assertIn("usage", r.stdout.lower(), f"{rel} --help no imprimió usage:")

    def test_pure_functions_importable_without_numpy_or_pil(self):
        import alinear as AL
        import render_plan as RP
        self.assertEqual(AL.normalizar_palabras("¡Hola, Vídeo 100%!"), ["hola", "video", "100"])
        emp = AL.emparejar(["hola", "mundo"], [("Hola!", 0.1, 0.4, 0.9), ("mundo.", 0.5, 0.9, 0.8)])
        self.assertEqual(emp, [("hola", 0.1, 0.4, 0.9), ("mundo", 0.5, 0.9, 0.8)])
        self.assertEqual(RP.cuenta_up(0, 3.5, 9.0, 0.0), "3.5")
        self.assertEqual(RP.cuenta_up(0, 1500, 9.0, 0.0), "1,500")
        faltan = set()
        res = RP.sustituir({"n": "{n}", "s": "Hola {nombre}", "m": "{x}"}, {"n": "42", "nombre": "Ana"}, faltan)
        self.assertEqual(res, {"n": 42, "s": "Hola Ana", "m": "{x}"})
        self.assertEqual(faltan, {"x"})


class TestAuditarPlanAndCliInputGuards(unittest.TestCase):
    def test_auditar_estructura_handles_missing_from_to_with_at_without_typeerror(self):
        plan = {
            "duracion": 5.0,
            "escenas": [
                {"tipo": "hero", "from": None, "to": 3.0, "at": {"titulo": 1.0}},
                {"tipo": "bento", "from": 0.0, "to": 5.0, "titulo": "OK", "items": [{"titulo": "A", "at": 9.0}]},
            ],
        }
        hallazgos = AP.auditar_estructura(plan)
        errores = [h for h in hallazgos if h["nivel"] == "ERROR"]
        avisos = [h for h in hallazgos if h["nivel"] == "AVISO"]
        self.assertEqual(len(errores), 1)
        self.assertIn("falta from/to", errores[0]["msg"])
        self.assertTrue(any("fuera de [0.0,5.0]" in h["msg"] for h in avisos))

    def test_clis_with_real_flags_report_clean_error_on_missing_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            ne_json = os.path.join(tmp, "no_existe.json")
            ne_mp4 = os.path.join(tmp, "no_existe.mp4")
            ne_mp3 = os.path.join(tmp, "no_existe.mp3")
            ne_dir = os.path.join(tmp, "no_existe_dir")
            out_mp4 = os.path.join(tmp, "out.mp4")
            out_png = os.path.join(tmp, "out.png")
            for cmd in (
                [os.path.join(SCRIPTS, "auditar_plan.py"), ne_json],
                [os.path.join(SCRIPTS, "musica.py"), "musiconly", "-v", ne_mp4, "-m", ne_mp3, "-o", out_mp4],
                [os.path.join(SCRIPTS, "musica.py"), "mix", "-v", ne_mp4, "-a", ne_mp3, "-m", ne_mp3, "-o", out_mp4],
                [os.path.join(SCRIPTS, "poster_frame.py"), ne_mp4, "--t", "1.0", "-o", out_mp4],
                [os.path.join(SCRIPTS, "contact_sheet.py"), "--dir", ne_dir, "-o", out_png],
            ):
                r = subprocess.run([sys.executable] + cmd, capture_output=True, text=True, timeout=15)
                self.assertNotEqual(r.returncode, 0)
                self.assertNotIn("Traceback", r.stderr, f"Traceback en {cmd[0]}: {r.stderr}")


if __name__ == "__main__":
    unittest.main()
