#!/usr/bin/env python3
"""Tests unitarios deterministas de utilidades core, frontmatter, nombres,
subtítulos y catálogo de escenas (39 escenas, primitivas DRY de Ronda 4, 5 y 6).

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
import aplicar_edl as AE  # noqa: E402
import auditar_plan as AP  # noqa: E402
import beat_grid as BG  # noqa: E402
import beat_sync as BS  # noqa: E402
import caption as CAP  # noqa: E402
import grade as GR  # noqa: E402
import medir_mezcla as MM  # noqa: E402
import registrar_aprendizaje as RA  # noqa: E402
import render_plan as RP  # noqa: E402
import shorts_plan as SP  # noqa: E402
import speech_estimate as SE  # noqa: E402
import clonar_video as CV  # noqa: E402


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
        for prim in ("tarjeta_cristal", "boton_halo", "insignia_3d", "sc_hero", "sc_bento",
                     "sc_buscador", "sc_notificacion", "sc_comentario", "sc_pie", "sc_orbita", "sc_audiowave"):
            self.assertIn(prim, fn_names)
        scenes_keys = []
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "SCENES" for t in node.targets):
                scenes_keys = [k.value for k in node.value.keys if isinstance(k, ast.Constant)]
        self.assertIn("hero", scenes_keys)
        self.assertIn("bento", scenes_keys)
        self.assertIn("buscador", scenes_keys)
        self.assertIn("notificacion", scenes_keys)
        self.assertIn("comentario", scenes_keys)
        self.assertIn("pie", scenes_keys)
        self.assertIn("orbita", scenes_keys)
        self.assertIn("audiowave", scenes_keys)
        with open(os.path.join(SCRIPTS, "escenas_muestra.json"), encoding="utf-8") as fh:
            muestras = json.load(fh)["escenas"]
        self.assertEqual(set(scenes_keys), set(muestras.keys()))
        # el numero del catalogo NO se escribe a mano en los tests: sale de
        # aqui (si no, cada escena nueva rompe el test y hay que acordarse)
        self.assertEqual(len(scenes_keys), len(muestras))


class TestComunYDelivery(unittest.TestCase):
    def test_hex_a_rgb_and_color_hex(self):
        self.assertEqual(C.color_hex("#e8480c"), "E8480C")
        self.assertEqual(C.hex_a_rgb("#E8480C"), (232, 72, 12))

    def test_segmentos_enfasis(self):
        self.assertEqual(
            C.segmentos_enfasis("Videos con *física real* hoy"),
            [("Videos con ", False), ("física real", True), (" hoy", False)],
        )

    def test_segmentos_resalte_cajas_y_acento(self):
        """El markup del reel de referencia vive UNA vez: * ~ ^."""
        self.assertEqual(
            C.segmentos_resalte("EL HACKEO A ~NOTEPAD++~ y *más*"),
            [("EL HACKEO A ", ""), ("NOTEPAD++", "roja"),
             (" y ", ""), ("más", "acento")],
        )
        self.assertEqual(
            C.segmentos_resalte("lo ^blanco^ manda"),
            [("lo ", ""), ("blanco", "blanca"), (" manda", "")],
        )

    def test_parse_and_fmt_time(self):
        self.assertAlmostEqual(C.parse_time("01:30.5"), 90.5)
        self.assertEqual(C.fmt_srt_time(90.5), "00:01:30,500")
        self.assertEqual(C.fmt_smpte_time(1.5, 30.0), "00:00:01:15")

    def test_safe_margins_px_and_end_screen_px(self):
        sm_v = D.safe_margins_px("reels", 1080, 1920)
        self.assertGreater(sm_v["bottom"], sm_v["top"])
        sm_h = D.safe_margins_px("youtube", 1920, 1080)
        self.assertGreater(sm_h["left"], 0)
        es = D.end_screen_px(1920, 1080)
        self.assertIn("suscribirse", es)
        self.assertIn("video", es)
        self.assertIn("marca", es)


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

    def test_auditar_estructura_detects_overlaps_gaps_voice_and_short_final(self):
        plan = {
            "duracion": 12.0,
            "escenas": [
                {"tipo": "tipo_invalido", "from": 0.0, "to": 2.0, "voz": " ".join(["palabra"] * 18)},
                {"tipo": "quote", "from": 1.5, "to": 1.7, "voz": "   "},
                {"tipo": "final", "from": 4.0, "to": 5.0, "titulo": "Cierre"},
            ],
        }
        hallazgos = AP.auditar_estructura(plan, tol=0.05, min_final=2.0)
        msgs = [h["msg"] for h in hallazgos]
        self.assertTrue(any("tipo desconocido" in m for m in msgs))
        self.assertTrue(any("solapa con la anterior" in m for m in msgs))
        self.assertTrue(any("muy corta" in m for m in msgs))
        self.assertTrue(any("escena vacía" in m for m in msgs))
        self.assertTrue(any("voz presente pero vacío" in m for m in msgs))
        self.assertTrue(any("hueco de" in m for m in msgs))
        self.assertTrue(any("mínimo 2.0s" in m for m in msgs))
        self.assertTrue(any("termina en 5.00s" in m for m in msgs))

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


class TestPreviewDelPlan(unittest.TestCase):
    """Mirar el plan SIN pagar el render.

    El frame final es una funcion pura del tiempo, asi que un instante se
    compone solo: la hoja del plan cuesta un frame por instante, no los 600
    del video. La MUTACION: si el --preview se comiera el render entero, este
    test cae (comprueba que la hoja sale y que no sale ningun video).
    """

    def _plan(self, tmp):
        plan = {"duracion": 4.0,
                "escenas": [{"tipo": "apertura", "from": 0.0, "to": 4.0,
                             "texto1": ["HOJA"], "texto2": ["DEL", "PLAN"]}]}
        ruta = os.path.join(tmp, "plan.json")
        with open(ruta, "w", encoding="utf-8") as fh:
            json.dump(plan, fh)
        return ruta

    def test_la_hoja_sale_sin_renderizar_el_video(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = self._plan(tmp)
            hoja = os.path.join(tmp, "hoja.jpg")
            r = subprocess.run(
                [sys.executable, os.path.join(SCRIPTS, "render_plan.py"), plan,
                 "--preview", "0,2", "--hoja", hoja],
                capture_output=True, text=True, timeout=600)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertTrue(os.path.isfile(hoja), "la hoja tiene que salir")
            self.assertGreater(os.path.getsize(hoja), 1000, "la hoja no puede estar vacia")
            self.assertIn("ms/frame", r.stdout, "el preview tiene que decir el coste")
            self.assertFalse(os.path.exists(os.path.join(tmp, "plan.mp4")),
                             "el preview no puede renderizar el video")

    def test_un_instante_fuera_del_plan_no_pasa(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = self._plan(tmp)
            r = subprocess.run(
                [sys.executable, os.path.join(SCRIPTS, "render_plan.py"), plan,
                 "--preview", "99"],
                capture_output=True, text=True, timeout=600)
            self.assertNotEqual(r.returncode, 0, "un instante fuera del plan es un error")
            self.assertNotIn("Traceback", r.stderr, f"Traceback: {r.stderr}")


class TestStdlibAudioFallbacks(unittest.TestCase):
    def test_beat_grid_stdlib_helpers_and_demo_bpm(self):
        # list(...) inmuniza la comparación contra ndarray (numpy presente) o list
        # (fallback stdlib): mismo veredicto con o sin numpy en el entorno.
        self.assertEqual(list(BG.maximum_filter1d([1.0, 5.0, 2.0, 0.0], 3)), [5.0, 5.0, 5.0, 2.0])
        self.assertAlmostEqual(BG._percentil_std([10.0, 20.0, 30.0, 40.0], 50), 25.0)
        self.assertEqual(BG.ajustar_rejilla([], 0.0, 90, 140), (90.0, 0.0))
        self.assertEqual(BG.ajustar_rejilla([0.1, 0.2], 0.2, 90, 140), (90.0, 0.0))
        mus_demo = os.path.join(SKILL, "film", "musica_demo.mp3")
        if os.path.isfile(mus_demo):
            g = BG.analizar(mus_demo)
            self.assertAlmostEqual(g["bpm"], 100.0, delta=1.0)
            self.assertGreater(len(g["compases"]), 0)

    def test_medir_mezcla_rms_db_and_fmt_db_stdlib(self):
        x = [0.5, 0.5, 0.1, 0.1]
        mask = [True, True, False, False]
        db = MM.rms_db(x, mask)
        self.assertIsNotNone(db)
        self.assertAlmostEqual(db, -6.02, places=1)
        self.assertIsNone(MM.rms_db(x, [False, False, False, False]))
        self.assertIn("dB", MM.fmt_db(-14.0))
        self.assertIn("—", MM.fmt_db(None))


class TestPostProductionAndLearningModules(unittest.TestCase):
    def test_beat_sync_and_sincronizar_escenas(self):
        grid = {"bpm": 120.0, "beat0": 0.0, "compas0": 0.0}
        beats, bd = BS.beats_hasta(grid, 8.0)
        self.assertAlmostEqual(bd, 0.5)
        self.assertEqual(beats[0], 0.0)
        ta, b, _ = BS.ajustar(0.08, beats, 0.15)
        self.assertAlmostEqual(ta, 0.0)
        self.assertEqual(b, 0.0)
        esc = [
            {"tipo": "hero", "from": 0.0, "to": 3.9, "at": {"titulo": 0.24, "cta": [0.49, 1.02]}},
            {"tipo": "bento", "from": 3.9, "to": 8.0, "at": {"rotulo": 4.24}, "items": [{"at": 5.01}]},
        ]
        sinc, info = BS.sincronizar_escenas(esc, grid, 8.0, mover_cortes=True)
        self.assertEqual(info["bpm"], 120.0)
        m = BS.medir_sincronia(sinc, grid, 8.0)
        self.assertEqual(m["entradas_pct"], 100.0)
        self.assertEqual(m["cortes_compas_pct"], 100.0)

    def test_aplicar_edl_merge_and_filter_concat(self):
        with tempfile.NamedTemporaryFile("w", suffix=".edl", delete=False, encoding="utf-8") as tf:
            tf.write("# comentario\n5.0-7.0\n1.0-3.0\n2.5-4.0\n")
            edl_p = tf.name
        try:
            segs = AE.leer_edl(edl_p)
            self.assertEqual(segs, [(1.0, 4.0), (5.0, 7.0)])
            fc1 = AE.filtro_concat([(1.0, 4.0)], 0.08)
            self.assertIn("trim=start=1.000:end=4.000", fc1)
            fc2 = AE.filtro_concat(segs, 0.08)
            self.assertIn("concat=n=2:v=1:a=1", fc2)
            self.assertIn("afade=t=in", fc2)
        finally:
            os.remove(edl_p)

    def test_grade_filter_and_shorts_plan_validation(self):
        f_full = GR.filtro_grade(0.7, True)
        self.assertIn("colorbalance", f_full)
        self.assertIn("vignette", f_full)
        f_zero = GR.filtro_grade(0.0, False)
        self.assertNotIn("vignette", f_zero)

        errs, avisos, tot = SP.validar(
            {
                "fuente": "in.mp4",
                "formato": "1080x1920",
                "lufs": -14.0,
                "musica": {"volumen_db": -16.0},
                "segmentos": [
                    {"id": "s1", "from": 0.0, "to": 2.5, "hook_overlay": "UNO DOS TRES"},
                    {"id": "s2", "from": 4.0, "to": 17.5},
                ],
            },
            dur_fuente=30.0,
        )
        self.assertEqual(errs, [])
        self.assertEqual(avisos, [])
        self.assertAlmostEqual(tot, 16.0)

        errs_bad, av_bad, _ = SP.validar(
            {
                "fuente": "in.mp4",
                "formato": "999x999",
                "lufs": -3.0,
                "musica": {"ruta": "/no/existe.mp3", "volumen_db": -2.0},
                "subtitulos": {"srt": "/no/existe.srt"},
                "segmentos": [
                    {"id": "dup", "from": 5.0, "to": 10.0, "hook_overlay": "UNO DOS TRES CUATRO CINCO SEIS SIETE"},
                    {"id": "dup", "from": 8.0, "to": 40.0},
                ],
            },
            dur_fuente=20.0,
        )
        self.assertTrue(len(errs_bad) >= 3)
        self.assertTrue(len(av_bad) >= 1)
        with tempfile.TemporaryDirectory() as tmp:
            srt_in = os.path.join(tmp, "in.srt")
            with open(srt_in, "w", encoding="utf-8") as fh:
                fh.write("1\n00:00:05,000 --> 00:00:06,500\nHola mundo\n\n2\n00:00:40,000 --> 00:00:41,000\nFuera\n\n")
            srt_out, ok_c, tot_c = SP.retimear_srt(
                srt_in,
                [{"id": "s1", "from": 4.0, "to": 8.0}, {"id": "s2", "from": 10.0, "to": 14.0}],
                tmp,
            )
            self.assertEqual((ok_c, tot_c), (1, 2))
            self.assertTrue(os.path.isfile(srt_out))

    def test_registrar_aprendizaje_similarity_and_dry_run(self):
        a = RA.palabras("Los subtítulos pop necesitan saltos fijos en libass")
        b = RA.palabras("Subtítulos pop con saltos fijos para libass")
        self.assertGreater(RA.jaccard(a, b), 0.5)
        self.assertGreater(RA.overlap(a, b), 0.7)
        dups = RA.buscar_duplicados(
            os.path.join(SKILL, "references", "reglas-tecnicas.md"),
            "Subtítulos pop con saltos fijos",
            "En libass el sobrepaso a 108% re-envuelve líneas si no se usa \\N y \\q2.",
        )
        self.assertIsInstance(dups, list)
        orig_argv = sys.argv
        try:
            sys.argv = [
                "registrar_aprendizaje.py",
                "--titulo",
                "Aprendizaje unico de prueba XYZ987",
                "--detalle",
                "Evidencia sintetica aislada con dry-run sin tocar archivos.",
                "--dry-run",
            ]
            RA.main()
        finally:
            sys.argv = orig_argv

    def test_beat_file_cli_generates_valid_grid(self):
        import beat_file as BF
        with tempfile.TemporaryDirectory() as tmp:
            out_json = os.path.join(tmp, "beats.json")
            orig_argv = sys.argv
            try:
                sys.argv = [
                    "beat_file.py",
                    "--bpm",
                    "120",
                    "--beat0",
                    "0.25",
                    "--duracion",
                    "4",
                    "--seccion",
                    "intro:0:2",
                    "-o",
                    out_json,
                ]
                BF.main()
            finally:
                sys.argv = orig_argv
            with open(out_json, encoding="utf-8") as fh:
                data = json.load(fh)
            self.assertEqual(data["bpm"], 120.0)
            self.assertEqual(data["secciones"][0]["nombre"], "intro")

    def test_loudness_tp_default_and_shorts_drawtext_escape(self):
        import inspect
        import loudness as LD
        # Verificar que el escape de drawtext cubre comillas, porcentajes y backslashes
        escaped = C.escape_drawtext("100% 'SEGURO'\\OK:TEST,[]")
        self.assertIn(r"\%", escaped)
        self.assertIn(r"\'", escaped)
        self.assertIn(r"\\", escaped)
        self.assertIn(r"\:", escaped)
        # Verificar la signature de LD.normalizar default tp=-1.5
        sig = inspect.signature(LD.normalizar)
        self.assertEqual(sig.parameters["tp"].default, -1.5)
        # Verificar que render_plan expone --con-musica
        r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "render_plan.py"), "--help"],
                           capture_output=True, text=True, timeout=15)
        self.assertEqual(r.returncode, 0)
        self.assertIn("--con-musica", r.stdout)

    def test_resize_guards_in_scenes(self):
        import render_plan as RP
        from PIL import Image
        ctx = RP.Ctx()
        ctx.iso = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
        ctx.logo = Image.new("RGBA", (200, 100), (255, 0, 0, 255))
        RP.MARCA_NOMBRE = "TestBrand"

        escena_canales = {
            "tipo": "canales", "from": 0.0, "to": 5.0,
            "marca": "TestBrand", "rotulo": "Rótulo",
            "canales": [{"canal": "web", "nombre": "Web", "texto": "Audit", "at": 1.0}],
            "at": {"marca": 0.0001, "junta": 3.0, "rotulo": 3.2}
        }
        img_can = RP.sc_canales(ctx, escena_canales, 0.00015)
        self.assertIsInstance(img_can, Image.Image)

        escena_final = {
            "tipo": "final", "from": 0.0, "to": 5.0,
            "marca": "TestBrand", "lema": "Lema", "boton": "Click",
            "at": {"lema": 1.0, "boton": 2.0}
        }
        img_fin = RP.sc_final(ctx, escena_final, 0.1001)
        self.assertIsInstance(img_fin, Image.Image)

        escena_med = {
            "tipo": "medianoche", "from": 0.0, "to": 5.0,
            "hora": "00:00", "notificaciones": []
        }
        img_med = RP.sc_medianoche(ctx, escena_med, 0.001)
        self.assertIsInstance(img_med, Image.Image)


class TestLaFuenteSeDibuja(unittest.TestCase):
    """Toda escena con cifras tiene que DIBUJAR su fuente.

    El linter acepta el campo `fuente` en cualquier escena, pero si el
    motor no lo dibuja, el espectador no lo ve: el plan dice una cosa y la
    pieza dice otra. El gauge era el caso: es una cifra y no la dibujaba.
    """

    def _escenas_que_dibujan(self):
        import ast
        with open(os.path.join(SCRIPTS, "render_plan.py"), encoding="utf-8") as fh:
            arbol = ast.parse(fh.read())
        out = set()
        for n in arbol.body:
            if isinstance(n, ast.FunctionDef) and any(
                    isinstance(x, ast.Call) and isinstance(x.func, ast.Name)
                    and x.func.id == "pie_fuente" for x in ast.walk(n)):
                out.add(n.name[3:])
        return out

    def test_el_gauge_dibuja_la_fuente(self):
        self.assertIn("gauge", self._escenas_que_dibujan(),
                      "el gauge es una cifra y tiene que dibujar su fuente al pie")

    def test_las_escenas_con_cifras_dibujan_la_fuente(self):
        # el linter acepta el campo `fuente` en cualquier escena, asi que las
        # escenas con cifras tienen que dibujarla: si no, el plan dice una
        # cosa y la pieza otra
        faltan = {"gauge", "bento", "index", "oferta", "pasos", "timeline",
                  "versus"} - self._escenas_que_dibujan()
        self.assertEqual(faltan, set(),
                         f"escenas con cifras que no dibujan su fuente: {sorted(faltan)}")

    def test_el_linter_y_el_motor_cuentan_lo_mismo(self):
        # las dos listas tienen que salir del MISMO motor: si el linter dice
        # que una escena dibuja la fuente y el motor no, el aviso miente
        import lint_copy as L
        del_linter = L._escenas_que_dibujan_la_fuente()
        del_motor = self._escenas_que_dibujan()
        self.assertEqual(sorted(del_linter), sorted(del_motor))


class TestViralFeaturesAndPrimitives(unittest.TestCase):
    def test_primitivas_movimiento_overshoot_arco_flash(self):
        # 1. curva_overshoot: en p=0 es 0, en p=1 es 1, y tiene sobrepaso > 1.0 en [0.6, 0.9]
        self.assertAlmostEqual(RP.curva_overshoot(0.0), 0.0, places=4)
        self.assertAlmostEqual(RP.curva_overshoot(1.0), 1.0, places=4)
        max_p = max(RP.curva_overshoot(step / 100.0) for step in range(101))
        self.assertGreater(max_p, 1.05, "curva_overshoot debe sobrepasar 1.0 para el efecto elástico")

        # 2. salto_arco: trayectoria parabólica 2D
        x_mid, y_mid = RP.salto_arco(0, 100, 200, 100, 0.5, altura=40.0)
        self.assertAlmostEqual(x_mid, 100.0)
        self.assertAlmostEqual(y_mid, 60.0, places=2)  # 100 - 40 = 60 en el ápice

        # 3. flash_impacto: genera capa con destello dentro de la ventana de hit
        try:
            from PIL import Image
            layer = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
            # Fuera de tiempo: capa idéntica sin cambios
            layer_out = RP.flash_impacto(layer, 0.1, 1.0)
            self.assertEqual(layer_out.tobytes(), layer.tobytes())
            # En t_hit: capa con opacidad alfa añadida
            layer_hit = RP.flash_impacto(layer, 1.05, 1.0, dur=0.2, max_alpha=120)
            self.assertGreater(layer_hit.getchannel("A").getextrema()[1], 0)
        except Exception as ex:
            self.fail(f"flash_impacto falló: {ex}")

    def test_speech_estimate_syllables_and_pacing(self):
        # Conteo silábico en español
        self.assertEqual(SE.contar_silabas_es("ciberseguridad"), 6)
        self.assertEqual(SE.contar_silabas_es("hola"), 2)

        # Estimación de locución pre-TTS
        dur = SE.estimar_duracion_habla("ciberseguridad", "es")
        self.assertGreater(dur, 0.7)
        self.assertLess(dur, 1.5)

        # Auditoría de plan con locución
        plan_ok = {
            "duracion": 10.0,
            "escenas": [
                {"tipo": "titular", "from": 0.0, "to": 5.0, "voz": "Bienvenidos a la plataforma digital."},
                {"tipo": "final", "from": 5.0, "to": 10.0, "voz": "Comienza hoy tu prueba gratuita."}
            ]
        }
        res_ok = SE.auditar_plan_voces(plan_ok)
        self.assertTrue(res_ok["valido"])
        self.assertEqual(len(res_ok["alertas"]), 0)

        # Plan con texto excesivo para la duración de la escena
        plan_apretado = {
            "duracion": 3.0,
            "escenas": [
                {"tipo": "titular", "from": 0.0, "to": 1.0, "voz": "Esta es una frase extremadamente larga y densa que es imposible de pronunciar en solo un segundo."}
            ]
        }
        res_bad = SE.auditar_plan_voces(plan_apretado)
        self.assertFalse(res_bad["valido"])
        self.assertGreater(len(res_bad["alertas"]), 0)

    def test_clonar_video_segmentacion_y_familias(self):
        # Familias de escenas virales
        self.assertIn("apertura", CV.FAMILIAS_ESCENAS["hook"])
        self.assertNotIn("titular", CV.FAMILIAS_ESCENAS["hook"])
        self.assertIn("ranking", CV.FAMILIAS_ESCENAS["dato"])
        self.assertIn("notificacion", CV.FAMILIAS_ESCENAS["social"])
        self.assertIn("audiowave", CV.FAMILIAS_ESCENAS["cierre"])

        # Segmentación sintética de video de 30 segundos
        segs = CV.detectar_cortes("/fake/video.mp4", 30.0)
        self.assertGreaterEqual(len(segs), 3)
        self.assertEqual(segs[0]["rol"], "hook")
        self.assertEqual(segs[-1]["rol"], "cierre")
        self.assertEqual(segs[0]["from"], 0.0)
        self.assertAlmostEqual(segs[-1]["to"], 30.0)


class TestCorrelacionEstereo(unittest.TestCase):
    """La compatibilidad con mono se mide, no se supone: una cama con los
    canales en contrafase desaparece en un telefono (que reproduce en mono
    sumando canales), y eso tiene que salir en la medicion."""

    def test_una_cama_normal_da_correlacion_alta(self):
        L = [0.5, 0.25, -0.25, 0.5]
        R = [0.5, 0.25, -0.25, 0.5]
        self.assertAlmostEqual(MM.correlacion(L, R), 1.0, places=3)

    def test_una_cama_en_contrafase_da_correlacion_negativa(self):
        L = [0.5, 0.25, -0.25, 0.5]
        R = [-v for v in L]
        self.assertLess(MM.correlacion(L, R), 0)

    def test_sin_audio_no_hay_correlacion(self):
        self.assertIsNone(MM.correlacion(None, None))
        self.assertIsNone(MM.correlacion([], []))


if __name__ == "__main__":
    unittest.main()
