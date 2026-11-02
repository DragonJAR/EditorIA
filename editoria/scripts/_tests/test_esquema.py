"""Esquema de campos de escena y del plan: tipos, obligatorios, `at`,
duración y placeholders. Es la MISMA tabla (`render_plan.esquema_de`,
`PLAN_CAMPOS`, `duracion_de`) que validan auditar_plan y el motor.

Portado de la 1.11.3 sin la clase CatalogoMdJson: catalogo.py/catalogo.json
no existen en esta línea (una sola superficie: repertorio)."""
import json, os, re, subprocess, sys, tempfile, unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(AQUI)
SKILL = os.path.dirname(SCRIPTS)
sys.path.insert(0, SCRIPTS)
import render_plan as R  # noqa: E402
import auditar_plan as A  # noqa: E402


def _audita(escenas, **plan):
    return A.auditar_estructura(dict({"duracion": max(e["to"] for e in escenas), "escenas": escenas}, **plan))


def _auditar_cli(plan):
    """La puerta que ve el agente: auditar_plan.py y su código de salida."""
    with tempfile.TemporaryDirectory() as d:
        ruta = os.path.join(d, "plan.json")
        with open(ruta, "w", encoding="utf-8") as fh:
            json.dump(plan, fh)
        return subprocess.run(
            [sys.executable, os.path.join(SCRIPTS, "auditar_plan.py"), ruta],
            capture_output=True, text=True, timeout=60)


class Esquema(unittest.TestCase):
    def test_cada_param_tiene_nombre_tipo_obligatorio_significado(self):
        for t in R.SCENES:
            for p in R.esquema_de(t):
                for k in ("nombre", "tipo", "obligatorio", "significado", "markup"):
                    self.assertIn(k, p, f"{t}.{p.get('nombre')}: falta {k}")
                self.assertTrue(p["significado"], f"{t}.{p['nombre']}: sin significado")

    def test_at_documenta_sus_claves(self):
        at = [p for p in R.esquema_de("timeline") if p["nombre"] == "at"][0]
        self.assertTrue(at["claves"])

    def test_final_sin_marca_es_error_en_auditoria(self):
        h = _audita([{"tipo": "final", "from": 0, "to": 4, "lema": "x"}])
        self.assertTrue(any(x["nivel"] == "ERROR" and "`marca`" in x["msg"] for x in h), h)

    def test_tipo_equivocado_es_error_claro_no_typeerror(self):
        e = {"tipo": "remate", "from": 0, "to": 4, "lineas": ["a"], "gigante": "7", "subtexto_gigante": ["a", "b"]}
        h = _audita([e])
        self.assertTrue(any(x["nivel"] == "ERROR" and "escena 0 (remate)" in x["msg"] and "subtexto_gigante" in x["msg"]
                            for x in h), h)
        with self.assertRaises(SystemExit) as cm:
            R.completar_escena(e, 0)
        self.assertIn("subtexto_gigante", str(cm.exception.code))

    def test_duracion_sobre_el_maximo_es_error(self):
        mx = R.duracion_de("stats")["max"]
        e = dict(R.muestra("stats"), tipo="stats", **{"from": 0, "to": mx + 2})
        e.pop("at", None)
        h = _audita([e])
        self.assertTrue(any(x["nivel"] == "ERROR" and "máximo" in x["msg"] for x in h), h)

    def test_markup_en_boton_se_quita_y_se_avisa(self):
        e = {"tipo": "final", "from": 0, "to": 4, "marca": "X", "boton": "*Compra*"}
        self.assertEqual(R.completar_escena(e, 0)["boton"], "Compra")
        self.assertTrue(any("no admite markup" in x["msg"] for x in _audita([e])))

    def test_sin_copy_de_muestra_en_defaults(self):
        """Ningún campo de texto se rellena con un texto de ejemplo (point 3)."""
        prohibidos = ("Todo en *una grilla*", "Empieza hoy", "NUEVO LANZAMIENTO", "Tu producto en *movimiento*",
                      "3.4x", "@cliente", "Reciente", "Audio seguro", "grabacion.wav", "REC ● 00:14", "\"840\"")
        with open(os.path.join(SCRIPTS, "render_plan.py"), encoding="utf-8") as fh:
            src = fh.read()
        for p in prohibidos:
            self.assertNotIn(p, src, p)
        # rótulos de INTERFAZ (el botón de un checkout) y valores de opción no son copy
        interfaz = {("pago", "boton"), ("pago", "hecho"), ("recupera", "hecho"),
                    ("rotulo_inferior", "lado"), ("orbOpen", "figura"), ("orbita", "figura")}
        for t in R.SCENES:
            for p in R.esquema_de(t):
                d = p.get("default")
                if (t, p["nombre"]) not in interfaz and p["tipo"] == "texto" and isinstance(d, str) and d.startswith('"') and len(d) > 4:
                    self.fail(f"{t}.{p['nombre']}: default de texto {d}")

    def test_bento_sin_items_es_error(self):
        h = _audita([{"tipo": "bento", "from": 0, "to": 5, "rotulo": "x"}])
        self.assertTrue(any(x["nivel"] == "ERROR" and "`items`" in x["msg"] for x in h), h)

    def test_campos_del_plan_tipados(self):
        nombres = {p["nombre"]: p for p in R.PLAN_CAMPOS}
        for k in ("camara", "brand", "paleta", "duracion", "tamano"):
            self.assertIn(k, nombres)
            self.assertTrue(nombres[k]["tipo"])
        self.assertIn(":claro", nombres["paleta"]["significado"])
        for k in ("y", "max_lineas", "zona"):
            self.assertIn("rango", R.CAMPOS_CON_RANGO[k])
        self.assertTrue(nombres["zona"]["significado"])

    def test_final_con_titulo_sin_marca_pasa(self):
        h = _audita([{"tipo": "final", "from": 0, "to": 4, "titulo": "Hoy", "lema": "x"}])
        self.assertFalse(any(x["nivel"] == "ERROR" for x in h), h)

    def test_remate_sin_lineas_se_completa(self):
        e = {"tipo": "remate", "from": 0, "to": 4, "gigante": "3 min", "etiqueta": "tiempo",
             "fuente": "Registro interno", "at": {"gigante": 0.5}}
        out = R.completar_escena(dict(e), 0)
        self.assertEqual(out["gigante"], "3 min")
        self.assertFalse(R.errores_de_esquema(e, 0))

    def test_listas_con_titular_admiten_markup(self):
        def flag(tipo, nombre):
            return [p for p in R.esquema_de(tipo) if p["nombre"] == nombre][0]["markup"]
        self.assertTrue(flag("apertura", "texto1"))
        self.assertTrue(flag("apertura", "texto2"))
        self.assertTrue(flag("remate", "lineas"))
        self.assertFalse(flag("final", "marca"))

    def test_copia_de_muestra_es_error(self):
        e = dict(R.muestra("final"), tipo="final", **{"from": 0, "to": 4, "_muestra": "cierre"})
        h = _audita([e])
        self.assertTrue(any(x["nivel"] == "ERROR" and "muestra" in x["msg"].lower() for x in h), h)

    def test_firma_cambia_si_cambia_y(self):
        sys.path.insert(0, os.path.join(SCRIPTS, "ffmpeg_tools"))
        from _comun import firma_plan
        base = {"tamano": "1080x1920", "duracion": 3, "escenas": [{"tipo": "cartel", "from": 0, "to": 3, "texto": "x", "y": 0.3}]}
        otra = {"tamano": "1080x1920", "duracion": 3, "escenas": [{"tipo": "cartel", "from": 0, "to": 3, "texto": "x", "y": 0.7}]}
        self.assertNotEqual(firma_plan(base), firma_plan(otra))

    def test_final_con_titulo_sin_marca_sale_cero(self):
        r = _auditar_cli({"duracion": 4, "escenas": [
            {"tipo": "final", "from": 0, "to": 4, "titulo": "Hoy", "lema": "Listo"}]})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_final_sin_nombre_sale_distinto_de_cero(self):
        r = _auditar_cli({"duracion": 4, "escenas": [
            {"tipo": "final", "from": 0, "to": 4, "lema": "x"}]})
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        texto = r.stdout + r.stderr
        self.assertTrue("marca" in texto or "titulo" in texto, texto)

    def test_remate_sin_lineas_audita_y_previsualiza(self):
        plan = {"duracion": 4, "tamano": "270x480", "escenas": [{
            "tipo": "remate", "from": 0, "to": 4, "gigante": "3 min",
            "etiqueta": "tiempo", "fuente": "Registro interno", "at": {"gigante": 0.5}}]}
        r = _auditar_cli(plan)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "plan.json")
            hoja = os.path.join(d, "hoja.jpg")
            with open(ruta, "w", encoding="utf-8") as fh:
                json.dump(plan, fh)
            p = subprocess.run(
                [sys.executable, os.path.join(SCRIPTS, "render_plan.py"), ruta,
                 "--preview", "1", "--hoja", hoja, "--blur", "1", "--tamano", "270x480"],
                capture_output=True, text=True, timeout=120)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertTrue(os.path.isfile(hoja), p.stdout + p.stderr)

    def test_copia_de_muestra_sale_distinto_de_cero(self):
        e = dict(R.muestra("final"), tipo="final", **{"from": 0, "to": 4, "_muestra": "cierre"})
        r = _auditar_cli({"duracion": 4, "escenas": [e]})
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertRegex(r.stdout, r"\[ERROR\]")
        self.assertIn("muestra", r.stdout.lower())

    def test_cambio_de_y_invalida_cache_y_qa_rechaza_el_video_viejo(self):
        """Un `y` distinto no reutiliza frames, y qa_entrega rechaza el mp4 viejo
        aunque su mtime sea posterior al plan."""
        import hashlib
        import shutil
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "plan.json")
            video = os.path.join(d, "v.mp4")
            viejo = os.path.join(d, "viejo.mp4")

            def escribir(y):
                with open(ruta, "w", encoding="utf-8") as fh:
                    json.dump({
                        "tamano": "270x480", "duracion": 2,
                        "escenas": [{
                            "tipo": "cartel", "from": 0, "to": 2,
                            "kicker": "Aviso", "icono": "lupa", "texto": "Que esta pasando",
                            "y": y, "at": {"panel": 0.2, "icono": 0.4, "texto": 0.6},
                        }],
                    }, fh)

            def frame(src, dest):
                subprocess.run(
                    ["ffmpeg", "-y", "-v", "error", "-ss", "1", "-i", src, "-frames:v", "1", dest],
                    check=True, capture_output=True, timeout=30)

            cmd = [sys.executable, os.path.join(SCRIPTS, "render_plan.py"), ruta, "-o", video,
                   "--blur", "1", "--fps", "8", "--tamano", "270x480", "--jobs", "2"]
            escribir(0.3)
            primero = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            self.assertEqual(primero.returncode, 0, primero.stdout + primero.stderr)
            with open(video, "rb") as fh:
                sha_vieja = hashlib.sha256(fh.read()).hexdigest()
            f1 = os.path.join(d, "f1.png")
            frame(video, f1)
            escribir(0.7)
            shutil.copy(video, viejo)
            os.utime(viejo, None)
            qa_viejo = subprocess.run(
                [sys.executable, os.path.join(SCRIPTS, "qa_entrega.py"), viejo,
                 "--plan", ruta, "--sin-medir"],
                capture_output=True, text=True, timeout=120)
            self.assertNotEqual(qa_viejo.returncode, 0, qa_viejo.stdout + qa_viejo.stderr)
            self.assertIn("firma del plan no coincide", qa_viejo.stdout + qa_viejo.stderr)
            self.assertRegex(qa_viejo.stdout, r"FALLO\s+plan-vs-video")
            segundo = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            self.assertEqual(segundo.returncode, 0, segundo.stdout + segundo.stderr)
            self.assertNotIn("retoma:", segundo.stdout)
            with open(video, "rb") as fh:
                sha_nueva = hashlib.sha256(fh.read()).hexdigest()
            self.assertNotEqual(sha_vieja, sha_nueva)
            f2 = os.path.join(d, "f2.png")
            frame(video, f2)
            with Image.open(f1) as im1, Image.open(f2) as im2:
                a = im1.convert("L").tobytes()
                b = im2.convert("L").tobytes()
            self.assertEqual(len(a), len(b))
            distintos = sum(1 for x, y in zip(a, b) if abs(x - y) > 40)
            self.assertGreater(distintos / len(a), 0.002)
            qa_nuevo = subprocess.run(
                [sys.executable, os.path.join(SCRIPTS, "qa_entrega.py"), video,
                 "--plan", ruta, "--sin-medir"],
                capture_output=True, text=True, timeout=120)
            self.assertNotIn("firma del plan no coincide", qa_nuevo.stdout + qa_nuevo.stderr)
            self.assertRegex(qa_nuevo.stdout, r"OK\s+plan-vs-video")



def _muestras():
    with open(os.path.join(SCRIPTS, "escenas_muestra.json"), encoding="utf-8") as fh:
        return json.load(fh)["escenas"]


class EsquemaDerivadoDelMotor(unittest.TestCase):
    """Lo que la integracion 524d probaba DIRECTO sobre `errores_de_esquema`
    (sin pasar por auditar_plan): el esquema sale del codigo de la escena, y
    la red de seguridad es que no rechace ninguna muestra del catalogo."""

    def test_at_documenta_sus_claves_en_varias_escenas(self):
        for tipo in ("apertura", "final", "constancia"):
            at = [p for p in R.esquema_de(tipo) if p["nombre"] == "at"]
            self.assertEqual(len(at), 1, f"{tipo} no declara `at`")
            self.assertIn("claves", at[0])

    def test_el_cierre_sin_nombre_es_error(self):
        """`final` sin `marca` ni `titulo`: ERROR con el nombre del campo."""
        e = {"tipo": "final", "from": 0.0, "to": 3.0, "at": {}}
        errs = R.errores_de_esquema(e, 0)
        self.assertTrue(errs, "el cierre sin nombre no es un error")
        self.assertTrue(any("marca" in x or "titulo" in x for x in errs),
                        f"el error no nombra el campo: {errs}")

    def test_el_cierre_con_titulo_pasa(self):
        """`titulo` basta: el cierre no exige `marca`."""
        e = {"tipo": "final", "from": 0.0, "to": 3.0, "titulo": "HABLEMOS",
             "at": {"lema": 1.0, "boton": 1.6}}
        self.assertEqual(R.errores_de_esquema(e, 0), [],
                         "un cierre con `titulo` no puede ser un error")

    def test_un_tipo_equivocado_es_error_claro(self):
        """Una cadena donde va una lista: error con el campo, no TypeError."""
        e = {"tipo": "constancia", "from": 0.0, "to": 3.0,
             "items": "no es una lista", "at": {}}
        errs = R.errores_de_esquema(e, 0)
        self.assertTrue(errs, "un tipo equivocado no es un error")
        self.assertTrue(any("items" in x for x in errs),
                        f"el error no nombra el campo: {errs}")

    def test_ninguna_muestra_del_catalogo_es_rechazada(self):
        """La red de seguridad: el esquema NO puede rechazar una muestra real
        (si marca como obligatorio un campo que la escena no exige, el render
        rechazaria planes validos)."""
        malas = []
        for tipo, ej in _muestras().items():
            e = dict(ej)
            e["tipo"] = tipo
            e.setdefault("from", 0.0)
            e.setdefault("to", 5.0)
            errs = R.errores_de_esquema(e, 0)
            if errs:
                malas.append(f"{tipo}: {errs[0]}")
        self.assertEqual(malas, [],
                         "el esquema rechaza muestras propias del catalogo:\n  " +
                         "\n  ".join(malas))

    def test_la_duracion_de_una_escena_es_razonable(self):
        """Cada escena dice cuanto debe durar (min, recomendado, max)."""
        for tipo in ("apertura", "final", "constancia"):
            d = R.duracion_de(tipo)
            self.assertIsNotNone(d, f"{tipo} no declara duracion")
            self.assertLessEqual(d["min"], d["recomendada"][1])
            self.assertLessEqual(d["recomendada"][1], d["max"])


if __name__ == "__main__":
    unittest.main()
