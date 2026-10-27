#!/usr/bin/env python3
"""Tests de auditar_mapa.py — la garantia de que la skill no se rompe en islas.

Cada test construye una copia minima de la skill, la rompe de una forma
concreta y comprueba que el auditor la detecta. El ultimo test comprueba que
la skill REAL pasa.

Run with: python3 -m unittest discover -s SKILL/scripts/_tests
"""

import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
BASE = os.path.dirname(SCRIPTS)


def _suites_del_canonico(raiz):
    """Las suites que declara el canonico de ese arbol (lista)."""
    ruta = os.path.join(raiz, "scripts", "data", "suites.json")
    if not os.path.exists(ruta):
        return []
    with open(ruta, encoding="utf-8") as f:
        return (json.load(f) or {}).get("suites") or []


def _escribe_canonico(raiz, suites):
    """Escribe el canonico de suites en el arbol indicado."""
    d = os.path.join(raiz, "scripts", "data")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "suites.json"), "w", encoding="utf-8") as f:
        json.dump({"_que_es": "fixture", "suites": sorted(suites)}, f, indent=1)
AUDITAR = os.path.join(SCRIPTS, "auditar_mapa.py")


def _copia_minima(destino):
    """Una copia con lo que el auditor necesita: referencias, SKILL.md y el
    propio auditor."""
    shutil.copytree(os.path.join(BASE, "references"), os.path.join(destino, "references"))
    os.makedirs(os.path.join(destino, "scripts"), exist_ok=True)
    shutil.copy(AUDITAR, os.path.join(destino, "scripts", "auditar_mapa.py"))
    shutil.copy(os.path.join(BASE, "SKILL.md"), os.path.join(destino, "SKILL.md"))
    return destino


def _copia_completa(destino):
    """Una copia de la skill ENTERA: los guards que comparan el codigo con
    la doc (promesas, catalogo) solo corren sobre el arbol completo."""
    shutil.copytree(os.path.join(BASE, "scripts"), os.path.join(destino, "scripts"),
                    ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(os.path.join(BASE, "references"), os.path.join(destino, "references"))
    shutil.copy(os.path.join(BASE, "SKILL.md"), os.path.join(destino, "SKILL.md"))
    for sub in ("brand", "film", "assets", "metricas"):
        origen = os.path.join(BASE, sub)
        if os.path.isdir(origen):
            shutil.copytree(origen, os.path.join(destino, sub),
                            ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"))
    return destino


def _auditar(destino):
    r = subprocess.run([sys.executable, os.path.join(destino, "scripts", "auditar_mapa.py")],
                       capture_output=True, text=True, timeout=300)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


class TestAuditarMapa(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="editoria_mapa_")
        self.raiz = _copia_minima(self.dir)
        self.addCleanup(shutil.rmtree, self.dir, True)

    def _pie_de(self, nombre):
        ruta = os.path.join(self.raiz, "references", nombre)
        with open(ruta, encoding="utf-8") as f:
            return ruta, f.read()

    def _escribir(self, nombre, txt):
        with open(os.path.join(self.raiz, "references", nombre), "w", encoding="utf-8") as f:
            f.write(txt)

    def test_la_skill_real_pasa(self):
        rc, out = _auditar(BASE)
        self.assertEqual(rc, 0, f"la skill real tiene islas:\n{out}")

    def test_detecta_una_cli_documentada_sin_verificar(self):
        """Una CLI documentada que nadie ejecuta ni vigila por argumentos es un
        puntero a nada: el guard tiene que decirlo (es el "guard sin objeto"
        aplicado a las CLIs)."""
        with tempfile.TemporaryDirectory() as d:
            raiz = _copia_completa(d)
            # se borra el test que ejecuta esas CLIs: nadie las ejecuta ya
            os.remove(os.path.join(raiz, "scripts", "_tests",
                                   "test_cli_de_herramientas.py"))
            rc, out = _auditar(raiz)
            self.assertEqual(rc, 1)
            self.assertIn("cli sin verificar", out)
            self.assertIn("delivery_check.py", out)

    def test_detecta_pie_ausente(self):
        ruta, txt = self._pie_de("copy.md")
        self._escribir("copy.md", re.sub(r"\n\n---\n\n→ Canónico:.*$", "", txt, flags=re.S))
        rc, out = _auditar(self.raiz)
        self.assertEqual(rc, 1)
        self.assertIn("pie ausente", out)

    def test_detecta_canonico_inexistente(self):
        # el path falso se arma en runtime: si estuviera literal en este
        # archivo, el auditor lo veria como un enlace roto propio
        fantasma = "references/" + "fantasia" + ".md"
        _ruta, txt = self._pie_de("fluidez.md")
        self._escribir("fluidez.md", txt.replace("`references/animacion.md`", f"`{fantasma}`"))
        rc, out = _auditar(self.raiz)
        self.assertEqual(rc, 1)
        self.assertIn("canonico inexistente", out)

    def test_detecta_isla(self):
        with open(os.path.join(self.raiz, "references", "isla.md"), "w", encoding="utf-8") as f:
            f.write("# Isla\n\nUn archivo que nadie enlaza.\n")
        rc, out = _auditar(self.raiz)
        self.assertEqual(rc, 1)
        self.assertIn("isla", out)

    def test_detecta_dominio_contradictorio(self):
        _ruta, txt = self._pie_de("fluidez.md")
        self._escribir("fluidez.md", txt.replace("Dominio: movimiento", "Dominio: sonido"))
        rc, out = _auditar(self.raiz)
        self.assertEqual(rc, 1)
        self.assertIn("dominio contradictorio", out)

    def test_detecta_vecino_inexistente(self):
        fantasma = "references/ritmo_" + "fantasma" + ".md"
        _ruta, txt = self._pie_de("fluidez.md")
        self._escribir("fluidez.md", txt.replace("`references/ritmo.md`", f"`{fantasma}`"))
        rc, out = _auditar(self.raiz)
        self.assertEqual(rc, 1)
        self.assertIn("vecino inexistente", out)

    def test_detecta_valor_divergente(self):
        # una regla con un valor unico enunciada con otro numero
        _ruta, txt = self._pie_de("coherencia-espacial.md")
        self._escribir("coherencia-espacial.md",
                       txt.replace("En vertical son **151 px**", "En vertical son **90 px**"))
        rc, out = _auditar(self.raiz)
        self.assertEqual(rc, 1)
        self.assertIn("valor divergente", out)

    def test_detecta_un_target_de_sonoridad_que_no_es_el_canon(self):
        # el target de sonoridad de la skill es -14 enérgico / -16 calmo: son
        # dos valores y ninguno mas. un "-16/-15 para calmado" deja a quien
        # mezcla sin saber a donde apuntar el loudnorm.
        #
        # el bloque dice el valor BUENO y el MALO ("-16 calmo" y despues
        # "-15 para calmado"): con un solo enunciado por bloque el guard
        # miraria el bueno y daria el bloque por limpio.
        raiz = _copia_completa(os.path.join(self.dir, "skill_lufs"))
        s = os.path.join(raiz, "references", "sonido.md")
        with open(s, encoding="utf-8") as f:
            txt = f.read()
        bueno = "−14 enérgico / −16 calmo; ver `checklist-qa.md`)"
        self.assertIn(bueno, txt, "el fixture tiene que traer el canon")
        with open(s, "w", encoding="utf-8") as f:
            f.write(txt.replace(bueno, bueno[:-1] + "; −16/−15 para calmado)"))
        rc, out = _auditar(raiz)
        self.assertEqual(rc, 1, f"el target de sonoridad divergente no se detecto:\n{out}")
        self.assertIn("valor divergente", out)
        self.assertIn("sonoridad", out, "el fallo tiene que decir que regla fallo")

    def test_el_menos_tipografico_no_escapea_del_guard(self):
        # la prosa escribe "-14" con el signo tipografico (U+2212). float() no
        # lo entiende: sin normalizarlo, la regla se compararia NUNCA y un
        # target equivocado pasaria sin que nadie lo viera.
        raiz = _copia_completa(os.path.join(self.dir, "skill_signo"))
        s = os.path.join(raiz, "references", "sonido.md")
        with open(s, encoding="utf-8") as f:
            txt = f.read()
        self.assertIn("−14 enérgico", txt, "el fixture tiene que traer el canon")
        with open(s, "w", encoding="utf-8") as f:
            f.write(txt.replace("−14 enérgico", "−13 enérgico"))
        rc, out = _auditar(raiz)
        self.assertEqual(rc, 1, f"el target equivocado no se detecto:\n{out}")
        self.assertIn("valor divergente", out)

    def test_detecta_ruta_de_entregable_sin_puerta(self):
        # una ruta que produce un video tiene que acabar en la puerta
        _ruta, txt = self._pie_de("mapa.md")
        rota = txt.replace(
            '- **"quiero clonar este video"** → `referencia-video.md` → `formatos.md` → `copy.md` →\n  `qa-entrega.md`.',
            '- **"quiero clonar este video"** → `referencia-video.md` → `formatos.md` → `copy.md`.')
        self.assertNotEqual(rota, txt, "la ruta de prueba no existe: el test miente")
        self._escribir("mapa.md", rota)
        rc, out = _auditar(self.raiz)
        self.assertEqual(rc, 1)
        self.assertIn("ruta sin puerta", out)

    def test_detecta_el_paso_de_edicion_sin_puerta(self):
        # el paso de edicion del SKILL.md tiene que cerrar en la puerta
        ruta_skill = os.path.join(self.raiz, "SKILL.md")
        with open(ruta_skill, encoding="utf-8") as f:
            txt = f.read()
        with open(ruta_skill, "w", encoding="utf-8") as f:
            f.write(txt.replace("python scripts/qa_entrega.py final.mp4\n", ""))
        rc, out = _auditar(self.raiz)
        self.assertEqual(rc, 1)
        self.assertIn("ruta sin puerta", out)

    def test_detecta_una_promesa_que_nadie_imprime(self):
        # "Expected output: PLAN VALIDO" es un contrato: si el script imprime
        # otra cosa, el agente no sabe cuando seguir
        raiz = _copia_completa(tempfile.mkdtemp(prefix="editoria_promesas_"))
        self.addCleanup(shutil.rmtree, raiz, True)
        ruta_skill = os.path.join(raiz, "SKILL.md")
        with open(ruta_skill, encoding="utf-8") as f:
            txt = f.read()
        roto = txt.replace("Expected output: `PLAN VALIDO`",
                           "Expected output: `PLAN IMPECABLE`")
        self.assertNotEqual(roto, txt, "la promesa de prueba no existe: el test miente")
        with open(ruta_skill, "w", encoding="utf-8") as f:
            f.write(roto)
        rc, out = _auditar(raiz)
        self.assertEqual(rc, 1)
        self.assertIn("promesa inexistente", out)

    def test_una_palabra_en_un_comentario_no_cumple_una_promesa(self):
        # el chequeo mira lo que se IMPRIME: un comentario no es una promesa
        raiz = _copia_completa(tempfile.mkdtemp(prefix="editoria_comentarios_"))
        self.addCleanup(shutil.rmtree, raiz, True)
        ruta_skill = os.path.join(raiz, "SKILL.md")
        with open(ruta_skill, encoding="utf-8") as f:
            txt = f.read()
        with open(ruta_skill, "w", encoding="utf-8") as f:
            f.write(txt.replace("Expected output: `PLAN VALIDO`",
                                "Expected output: `PLAN IMPECABLE`"))
        # en otro script, para no romper el auditor que se esta corriendo
        with open(os.path.join(raiz, "scripts", "_nota.py"), "w",
                  encoding="utf-8") as f:
            f.write("# una pieza impecable no es una promesa cumplida\n")
        rc, out = _auditar(raiz)
        self.assertEqual(rc, 1)
        self.assertIn("promesa inexistente", out)

    def test_detecta_una_escena_del_motor_sin_documentar(self):
        # el numero puede cuadrar mientras el nombre que el agente copia ya
        # no existe en el motor
        raiz = _copia_completa(tempfile.mkdtemp(prefix="editoria_escenas_"))
        self.addCleanup(shutil.rmtree, raiz, True)
        ruta = os.path.join(raiz, "references", "plan-video.md")
        with open(ruta, encoding="utf-8") as f:
            txt = f.read()
        self.assertIn("`callout`", txt, "la escena de prueba no esta en el doc")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(txt.replace(" · `callout`", ""))
        rc, out = _auditar(raiz)
        self.assertEqual(rc, 1)
        self.assertIn("escena sin documentar", out)

    def test_detecta_una_escena_ya_implementada_listada_como_futura(self):
        raiz = _copia_completa(tempfile.mkdtemp(prefix="editoria_futuras_"))
        self.addCleanup(shutil.rmtree, raiz, True)
        ruta = os.path.join(raiz, "references", "escenas.md")
        with open(ruta, encoding="utf-8") as f:
            txt = f.read()
        self.assertIn("Ideas de escenas futuras", txt)
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(txt.replace("`broll` ·", "`broll` · `callout` ·", 1))
        rc, out = _auditar(raiz)
        self.assertEqual(rc, 1)
        self.assertIn("escena futura ya existe", out)

    def test_detecta_piso_de_letra_divergente(self):
        # el piso de letra tiene que coincidir con el del motor (26 px)
        _ruta, txt = self._pie_de("glosario.md")
        self.assertIn("26 px", txt, "el glosario debe enunciar el piso de letra")
        self._escribir("glosario.md", txt.replace("**26 px**", "**28 px**"))
        rc, out = _auditar(self.raiz)
        self.assertEqual(rc, 1)
        self.assertIn("piso de letra", out)

    def test_el_piso_de_letra_del_motor_no_se_inventa(self):
        # el motor es la fuente: si LETRA_MIN cambia, el valor esperado cambia
        with open(AUDITAR, encoding="utf-8") as f:
            txt = f.read()
        m = re.search(r'"nombre":\s*"piso de letra".*?"valor":\s*(\d+)', txt, re.S)
        self.assertIsNotNone(m, "la regla del piso de letra debe estar en auditar_mapa.py")
        with open(os.path.join(SCRIPTS, "medir_animacion.py"), encoding="utf-8") as f:
            motor = f.read()
        self.assertIn(f"LETRA_MIN = {m.group(1)}", motor,
                      "el valor esperado tiene que ser el LETRA_MIN real del motor")

    def test_el_numero_de_referencias_no_se_inventa(self):
        # el numero de referencias lo cuenta el ARBOL (los .md de
        # references/): si anade una referencia, el valor esperado del guard
        # cambia con ella, y la prosa avisara del numero viejo
        with open(AUDITAR, encoding="utf-8") as f:
            txt = f.read()
        m = re.search(r'"nombre":\s*"numero de referencias".*?"valor":\s*(\d+)', txt, re.S)
        self.assertIsNotNone(m, "la regla del numero de referencias debe estar "
                               "en auditar_mapa.py")
        refs = os.path.join(BASE, "references")
        reales = len([f for f in os.listdir(refs) if f.endswith(".md")])
        self.assertEqual(int(m.group(1)), reales,
                         f"el guard espera {m.group(1)} referencias y el arbol "
                         f"tiene {reales}: el valor esperado tiene que ser el "
                         f"numero real, no una copia")
        # y la prosa tiene que decir ESE numero, en los dos sitios
        mapa = open(os.path.join(refs, "mapa.md"), encoding="utf-8").read()
        skill = open(os.path.join(BASE, "SKILL.md"), encoding="utf-8").read()
        self.assertIn(f"contra las {reales} referencias", mapa,
                      "el mapa tiene que decir el numero real de referencias")
        self.assertIn(f"this skill: {reales} references", skill,
                      "el SKILL.md tiene que decir el numero real de referencias")

    def test_el_aire_de_voz_no_se_inventa(self):
        # el aire de voz lo decide el codigo (AIRE_VOZ): si cambia, el valor
        # esperado del guard cambia con el, y el guard avisara de que la prosa
        # sigue diciendo el numero viejo
        with open(AUDITAR, encoding="utf-8") as f:
            txt = f.read()
        m = re.search(r'"nombre":\s*"aire de voz".*?"valor":\s*([\d.]+)', txt, re.S)
        self.assertIsNotNone(m, "la regla del aire de voz debe estar en auditar_mapa.py")
        with open(os.path.join(SCRIPTS, "speech_estimate.py"), encoding="utf-8") as f:
            motor = f.read()
        self.assertIn(f"AIRE_VOZ = {m.group(1)}", motor,
                      "el valor esperado tiene que ser el AIRE_VOZ real del codigo")

    def test_la_cadencia_minima_no_se_inventa(self):
        # el umbral del metronomo lo decide el codigo (CV_MIN_CADENCIA): si
        # cambia, el valor esperado del guard cambia con el, y la prosa avisa
        # del numero viejo
        with open(AUDITAR, encoding="utf-8") as f:
            txt = f.read()
        m = re.search(r'"nombre":\s*"cadencia minima[^"]*".*?"valor":\s*([\d.]+)', txt, re.S)
        self.assertIsNotNone(m, "la regla de la cadencia debe estar en auditar_mapa.py")
        with open(os.path.join(SCRIPTS, "ffmpeg_tools", "_comun.py"), encoding="utf-8") as f:
            motor = f.read()
        self.assertIn(f"CV_MIN_CADENCIA = {m.group(1)}", motor,
                      "el valor esperado tiene que ser el CV_MIN_CADENCIA real del codigo")

    def test_la_banda_de_la_estimacion_no_se_inventa(self):
        # la banda (el % del hueco que se tolera) la decide el codigo
        # (BANDA_ESTIMACION): si cambia, el valor esperado del guard cambia
        # con el, y el guard avisara de que la prosa sigue con el numero viejo
        with open(AUDITAR, encoding="utf-8") as f:
            txt = f.read()
        m = re.search(r'"nombre":\s*"banda de la estimaci[oó]n[^"]*".*?"valor":\s*([\d.]+)',
                      txt, re.S)
        self.assertIsNotNone(m, "la regla de la banda debe estar en auditar_mapa.py")
        fraccion = float(m.group(1)) / 100.0   # la prosa dice %, el codigo dice fraccion
        with open(os.path.join(SCRIPTS, "speech_estimate.py"), encoding="utf-8") as f:
            motor = f.read()
        self.assertIn(f"BANDA_ESTIMACION = {fraccion}", motor,
                      "el valor esperado tiene que ser la BANDA_ESTIMACION real del codigo")

    def test_el_margen_minimo_no_se_inventa(self):
        # el suelo del margen (0,30 s) tambien lo decide el codigo
        with open(AUDITAR, encoding="utf-8") as f:
            txt = f.read()
        m = re.search(r'"nombre":\s*"margen m[ií]nimo de la estimaci[oó]n".*?"valor":\s*([\d.]+)',
                      txt, re.S)
        self.assertIsNotNone(m, "la regla del margen minimo debe estar en auditar_mapa.py")
        with open(os.path.join(SCRIPTS, "speech_estimate.py"), encoding="utf-8") as f:
            motor = f.read()
        self.assertIn(f"MARGEN_MIN_ESTIMACION = {m.group(1)}", motor,
                      "el valor esperado tiene que ser el MARGEN_MIN_ESTIMACION real del codigo")

    def test_una_regla_sin_objeto_lo_dice(self):
        # una regla cuyo patron deja de casar se apaga en silencio (no
        # encuentra ningun numero que comparar) y el guard dice "todo bien"
        # sin mirar. Un guard que no encuentra su objeto tiene que decirlo.
        # Se rompe el patron de una regla REAL (una que existe en el estado):
        # una regla inventada no aplica, porque todavia no esta publicada.
        import importlib.util
        spec = importlib.util.spec_from_file_location("am_mod", AUDITAR)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        regla = next(r for r in mod.REGLAS_UNICAS if r["nombre"] == "aire de voz")
        patron = regla["patron"]
        regla["patron"] = r"un numero que no existe en ninguna prosa \d{7}"
        try:
            problemas = []
            mod._chequear_reglas(problemas)
        finally:
            regla["patron"] = patron
        sin_objeto = [p for p in problemas if p["tipo"] == "guard sin objeto"]
        self.assertTrue(sin_objeto, "una regla que no encuentra su objeto no lo dice")
        self.assertTrue(any("aire de voz" in p["msg"] for p in sin_objeto),
                        "el aviso tiene que nombrar la regla que se apago")

    def test_el_aire_que_coloca_la_voz_es_la_constante(self):
        # El aire (0,40 s) estaba declarado como AIRE_VOZ en speech_estimate
        # y VIGILADO en la prosa, pero el codigo que coloca la voz usaba un
        # literal 0.4 (voz_off.py, voz_local.py) y mezclar_audio.py tenia su
        # propia constante OFFSET_VOZ = 0.4. O sea: la constante vigilada no
        # era la que colocaba la voz. Si alguien cambiaba AIRE_VOZ, la prosa
        # avisaba y el motor seguia colocando en 0,4.
        import re as _re
        with open(os.path.join(SCRIPTS, "speech_estimate.py"), encoding="utf-8") as f:
            fuente = f.read()
        aire = _re.search(r"AIRE_VOZ\s*=\s*([\d.]+)", fuente)
        self.assertIsNotNone(aire, "AIRE_VOZ tiene que estar en speech_estimate.py")
        for nombre in ("voz_off.py", "voz_local.py", "mezclar_audio.py"):
            with open(os.path.join(SCRIPTS, nombre), encoding="utf-8") as f:
                codigo = f.read()
            self.assertIn("AIRE_VOZ", codigo,
                          f"{nombre} tiene que usar la constante AIRE_VOZ, no un 0,4 a mano")
            # ningun "+0.4" escrito a mano en la colocacion
            colocacion = _re.findall(r"from[^\n]*\+\s*([\d.]+)\s*\)?\s*\*\s*1000", codigo)
            self.assertEqual([c for c in colocacion if c != aire.group(1)], [],
                             f"{nombre} coloca la voz con un numero que no es el aire")

    def test_el_umbral_de_densidad_no_se_inventa(self):
        # la cifra que la skill enuncia para la densidad tiene que ser la que el
        # motor PENALIZA: menos de 0.5 (aburre) y mas de 2.0 (abrumba)
        with open(AUDITAR, encoding="utf-8") as f:
            txt = f.read()
        m = re.search(r'"nombre":\s*"densidad de movimiento".*?"valor":\s*\(([\d.]+),\s*([\d.]+)\)',
                      txt, re.S)
        self.assertIsNotNone(m, "la regla de la densidad debe estar en auditar_mapa.py")
        with open(os.path.join(SCRIPTS, "medir_animacion.py"), encoding="utf-8") as f:
            motor = f.read()
        self.assertIn(f"dens < {m.group(1)}", motor,
                      "el umbral bajo de densidad tiene que ser el del motor")
        self.assertIn(f"dens > {m.group(2)}", motor,
                      "el umbral alto de densidad tiene que ser el del motor")

    def test_la_banda_del_motor_se_vigila_en_todos_los_documentos(self):
        # la banda que el motor vigila se dice igual en los tres sitios que la
        # enuncian (glosario, auto-qa y fluidez). Si uno la escribe con otra
        # forma ("0,5-2 s" sin el segundo decimal), el patron del guard no la
        # ve y esa cifra deja de vigilarse en silencio.
        import importlib.util
        spec = importlib.util.spec_from_file_location("auditar_mapa_mod", AUDITAR)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        regla = next(r for r in mod.REGLAS_UNICAS if r["nombre"] == "densidad de movimiento")
        for nombre in ("glosario.md", "auto-qa.md", "fluidez.md"):
            with open(os.path.join(BASE, "references", nombre), encoding="utf-8") as f:
                txt = f.read()
            ms = list(re.finditer(regla["patron"], txt))
            self.assertTrue(ms, f"{nombre} no enuncia la banda del motor en una forma que el guard vea")
            for mt in ms:
                v = tuple(float(g.replace(",", ".")) for g in [x for x in mt.groups() if x])
                self.assertEqual(v, regla["valor"],
                                 f"{nombre} dice {v} y el motor vigila {regla['valor']}")

    def test_la_palabra_doctrina_no_equivoca_a_la_banda_del_motor(self):
        # "doctrina" es el ritmo de DISEÑO (mas estrecho); la banda que el motor
        # vigila se llama asi. Si un documento vuelve a llamar "doctrina" a la
        # banda, la palabra significa dos cosas.
        for nombre in ("auto-qa.md", "glosario.md"):
            with open(os.path.join(BASE, "references", nombre), encoding="utf-8") as f:
                txt = f.read()
            self.assertNotRegex(txt, r"[Dd]octrina:?\s*0?\.?5",
                                f"{nombre} llama 'doctrina' a la banda del motor")

    def test_la_densidad_de_cues_no_se_inventa(self):
        # los cues por minuto que enuncia la prosa tienen que ser los que
        # `mezclar_audio.py` avisa (CUES_MIN_MIN y CUES_MIN_MAX)
        with open(AUDITAR, encoding="utf-8") as f:
            txt = f.read()
        m = re.search(r'"nombre":\s*"densidad de cues".*?"valor":\s*\(([\d.]+),\s*([\d.]+)\)',
                      txt, re.S)
        self.assertIsNotNone(m, "la regla de la densidad de cues debe estar en auditar_mapa.py")
        with open(os.path.join(SCRIPTS, "mezclar_audio.py"), encoding="utf-8") as f:
            codigo = f.read()
        self.assertIn(f"CUES_MIN_MIN = {m.group(1)}", codigo,
                      "el minimo de cues tiene que ser el del mezclador")
        self.assertIn(f"CUES_MIN_MAX = {m.group(2)}", codigo,
                      "el maximo de cues tiene que ser el del mezclador")

    def test_detecta_una_densidad_atribuida_al_motor_que_no_es_la_del_motor(self):
        # el glosario decia "el motor pide uno cada 0,8-1,5 s" cuando el motor
        # penaliza fuera de 0,5-2: un numero falso en la prosa, y el guard
        # no lo veia porque comparaba contra el mismo numero equivocado
        raiz = self.raiz
        with open(os.path.join(raiz, "references", "glosario.md"), encoding="utf-8") as f:
            txt = f.read()
        self.assertIn("motor", txt.lower())
        nuevo, n = re.subn(r"0,5-2,0 eventos/s", "0,8-1,5 eventos/s", txt)
        self.assertEqual(n, 1, "el glosario debe enunciar la banda del motor del motor")
        with open(os.path.join(raiz, "references", "glosario.md"), "w", encoding="utf-8") as f:
            f.write(nuevo)
        rc, out = _auditar(raiz)
        self.assertEqual(rc, 1, f"la densidad falsa no se detecto:\n{out}")
        self.assertIn("densidad de movimiento", out)

    def test_detecta_una_suite_sin_enlistar(self):
        # el CANONICO enumera las suites que deben pasar: si esa lista no es
        # el conjunto real, la promesa envejece en silencio
        raiz = self.raiz
        d = os.path.join(raiz, "scripts", "_tests")
        os.makedirs(d, exist_ok=True)
        suites = _suites_del_canonico(BASE)
        self.assertTrue(suites, "el canonico de verdad deberia listar suites")
        _escribe_canonico(raiz, suites)
        # primero, las que el canonico lista, para que el check no grune
        for nombre in suites:
            with open(os.path.join(d, nombre), "w", encoding="utf-8") as f:
                f.write("# suite de mentira\n")
        # ahora una suite que nadie listo (el nombre se arma en piezas: una
        # ruta ficticia literal la marca el auditor de enlaces como rota)
        inventada = "test_" + "inventada.py"
        with open(os.path.join(d, inventada), "w", encoding="utf-8") as f:
            f.write("# suite que nadie listo\n")
        rc, out = _auditar(raiz)
        self.assertEqual(rc, 1, f"la suite sin enlistar no se detecto:\n{out}")
        self.assertIn("suite sin enlistar", out)
        self.assertIn(inventada, out)
        self.assertNotIn("suite listada que no existe", out,
                         "el check debe marcar solo lo que de verdad falta")

    def test_detecta_una_suite_listada_que_no_existe(self):
        raiz = self.raiz
        d = os.path.join(raiz, "scripts", "_tests")
        os.makedirs(d, exist_ok=True)
        fantasma = "test_" + "fantasma.py"
        with open(os.path.join(d, fantasma), "w", encoding="utf-8") as f:
            f.write("# no deberia estar aqui\n")
        # el canonico declara una suite que no existe: enlace roto en lo
        # publicado
        _escribe_canonico(raiz, _suites_del_canonico(BASE) + [fantasma])
        rc, out = _auditar(raiz)
        self.assertEqual(rc, 1, f"la suite fantasma no se detecto:\n{out}")
        self.assertIn("suite listada que no existe", out)

    def test_el_desvio_del_arbol_es_aviso_y_lo_publicado_es_fallo(self):
        # el guard mira las DOS cosas: lo publicado (si lo publicado miente,
        # es un fallo) y el arbol de trabajo (si se ha desviado ahi pero
        # aun no se ha publicado, es un aviso: lo que toca es correr la
        # herramienta que actualiza los numeros)
        repo = os.path.join(self.dir, "repo_dos_pasadas")
        skill = _copia_completa(os.path.join(repo, "skill"))

        def _git(*args):
            subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)

        _git("init", "-q")
        _git("config", "user.email", "test@local")
        _git("config", "user.name", "test")
        _git("add", "-A")
        _git("commit", "-q", "-m", "uno")

        mapa = os.path.join(skill, "references", "mapa.md")
        with open(mapa, encoding="utf-8") as f:
            txt = f.read()
        roto = re.sub(r"\d+ referencias, \d+ scripts", "99 referencias, 99 scripts", txt)
        self.assertNotEqual(txt, roto, "el mapa debe enunciar los conteos")

        # 1) desfasado SOLO en el arbol de trabajo: aviso, y no es fallo
        with open(mapa, "w", encoding="utf-8") as f:
            f.write(roto)
        rc, out = _auditar(skill)
        self.assertEqual(rc, 0, f"un desvio sin publicar deberia ser aviso, no fallo:\n{out}")
        self.assertIn("AVISOS", out)

        # 2) el mismo desvio PUBLICADO: ahi si es fallo
        _git("add", "-A")
        _git("commit", "-q", "-m", "dos")
        rc, out = _auditar(skill)
        self.assertEqual(rc, 1, f"lo publicado desfasado tiene que ser fallo:\n{out}")
        self.assertIn("MAPA:", out)

    def test_detecta_el_numero_de_suites_que_miente_en_la_prosa(self):
        # La prosa dice "(N suites)". Si ese numero miente, la promesa envejece
        # en silencio: el canonico y el arbol estan bien, pero el SKILL.md dice
        # otra cosa. Antes la lista entera se comparaba ruta a ruta y esto se
        # cazaba; ahora el numero tiene que VERIFICARSE, no solo escribirse.
        raiz = _copia_completa(os.path.join(self.dir, "skill_numero"))
        ruta = os.path.join(raiz, "SKILL.md")
        with open(ruta, encoding="utf-8") as f:
            txt = f.read()
        mt = re.search(r"\((\d+) suites\)", txt)
        self.assertIsNotNone(mt, "la prosa deberia decir cuantas suites hay")
        mentira = f"({int(mt.group(1)) + 1} suites)"
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(txt[:mt.start()] + mentira + txt[mt.end():])
        rc, out = _auditar(raiz)
        self.assertEqual(rc, 1, f"el numero que miente tiene que detectarse:\n{out}")
        self.assertIn("numero de suites desfasado", out)

    def test_detecta_una_prosa_que_no_dice_cuantas_suites_hay(self):
        # Si alguien reescribe la frase y el numero deja de estar, la
        # herramienta que lo escribe deja de actualizarlo (su patron no casa)
        # y el numero se congela CON LA GUARDIA PUESTA. Eso es un fallo: la
        # promesa no se puede verificar.
        raiz = _copia_completa(os.path.join(self.dir, "skill_sin_numero"))
        ruta = os.path.join(raiz, "SKILL.md")
        with open(ruta, encoding="utf-8") as f:
            txt = f.read()
        mt = re.search(r"unit tests in (.+?) pass via", txt)
        self.assertIsNotNone(mt, "la prosa deberia hablar de las suites")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(txt[:mt.start()] + "unit tests in the test folder pass via"
                    + txt[mt.end():])
        rc, out = _auditar(raiz)
        self.assertEqual(rc, 1, f"una prosa sin numero tiene que detectarse:\n{out}")
        self.assertIn("no dice cuantas suites hay", out)

    def test_el_extractor_de_rutas_no_trunca(self):
        """Una ruta .jsonl se extrae ENTERA.

        Sin frontera de palabra, la alternativa `json` casa y la "l" final se
        queda fuera: el chequeo de enlaces rotos iba a buscar un fichero que no
        existe. Se notaba porque una EXCEPCION tapaba justo el nombre
        truncado; al des-publicar el fichero, el bug se vio en la copia
        instalada.
        """
        import importlib.util
        spec = importlib.util.spec_from_file_location("am_para_test", AUDITAR)
        am = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(am)          # main() solo corre como script
        # OJO: las rutas del ejemplo se arman EN PIEZAS. El auditor lee los
        # .py (incluido este) y una ruta literal que no existe la marca como
        # enlace roto: el propio test se romperia a si mismo.
        rutas = am._rels_de_texto("mira `metricas/historial.jsonl` y `scripts/"
                                  + "x.py`")
        self.assertIn("metricas/historial.jsonl", rutas,
                      "la ruta .jsonl tiene que extraerse entera")
        self.assertNotIn("metricas/historial" + ".json", rutas,
                         "la ruta no puede truncarse a su extension mas corta")

    def test_avisa_si_no_puede_comparar_el_historial_de_suites(self):
        """Un guard que se salta un caso en silencio no se distingue de uno que
        no mira: el "no se ha podido mirar" tiene que estar escrito."""
        repo = os.path.join(self.dir, "repo_un_commit")
        skill = os.path.join(repo, "editoria")
        _copia_completa(skill)

        def _git(*args):
            subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)

        _git("init", "-q")
        _git("config", "user.email", "test@local")
        _git("config", "user.name", "test")
        _git("add", "-A")
        _git("commit", "-q", "-m", "uno")
        # un solo commit: no hay HEAD~1 con el que comparar el historial
        rc, out = _auditar(skill)
        self.assertIn("no ha mirado nada", out,
                      f"si no se puede comparar, se dice:\n{out[:800]}")

    def test_detecta_un_commit_que_arrastra_trabajo(self):
        # un commit puede llevarse trabajo en vuelo al arbol commiteado: el
        # doc y el codigo quedan coherentes entre si (los dos erroneos a la
        # vez) y los guards de cifras no lo ven, porque comparan el doc
        # contra el MISMO arbol erroneo. Este guard mira el commit anterior.
        repo = os.path.join(self.dir, "repo")
        skill = os.path.join(repo, "skill")
        _copia_completa(skill)

        def _git(*args):
            subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)

        _git("init", "-q")
        _git("config", "user.email", "test@local")
        _git("config", "user.name", "test")
        _git("add", "-A")
        _git("commit", "-q", "-m", "uno")

        # el segundo commit: una suite desaparece del canonico Y del arbol
        suites = _suites_del_canonico(skill)
        self.assertTrue(suites, "el canonico deberia listar suites")
        victim = suites[0]
        ruta = os.path.join(skill, "scripts", "_tests", victim)
        self.assertTrue(os.path.exists(ruta), f"la suite listada {victim} deberia existir")
        os.remove(ruta)
        _escribe_canonico(skill, [s for s in suites if s != victim])
        _git("add", "-A")
        _git("commit", "-q", "-m", "dos")

        rc, out = _auditar(skill)
        self.assertEqual(rc, 1, f"el commit que arrastro trabajo no se detecto:\n{out}")
        self.assertIn("suite perdida en el commit", out)
        self.assertIn(victim, out)

    def test_detecta_una_cifra_de_clis_obsoleta_en_el_contrato(self):
        # el contrato de CLI declara cuantos scripts lo cumplen: si ese
        # numero no es el real, el documento miente sobre la skill
        raiz = _copia_completa(os.path.join(self.dir, "skill_contrato"))
        doc = os.path.join(raiz, "references", "cli-contract.md")
        with open(doc, encoding="utf-8") as f:
            txt = f.read()
        mt = re.search(r"(\d+)\s+de\s+las\s+(\d+)\s+cumplen\s+el\s+contrato", txt)
        self.assertIsNotNone(mt, "el contrato debe decir cuantas CLIs lo cumplen")
        with open(doc, "w", encoding="utf-8") as f:
            f.write(txt.replace(mt.group(0), mt.group(0).replace(mt.group(1), "7"), 1))
        rc, out = _auditar(raiz)
        self.assertEqual(rc, 1, f"la cifra del contrato no se detecto:\n{out}")
        self.assertIn("CLIs con el contrato", out)

    def test_detecta_un_total_de_clis_obsoleto_en_el_contrato(self):
        # la frase del contrato tiene DOS numeros: cuantas cumplen el
        # contrato entero y cuantas CLIs hay. vigilar solo el primero dejaba
        # el segundo sin vigilar (y el segundo acababa de aparecer).
        raiz = _copia_completa(os.path.join(self.dir, "skill_contrato_total"))
        doc = os.path.join(raiz, "references", "cli-contract.md")
        with open(doc, encoding="utf-8") as f:
            txt = f.read()
        mt = re.search(r"(\d+)\s+de\s+las\s+(\d+)\s+cumplen\s+el\s+contrato", txt)
        self.assertIsNotNone(mt, "el contrato debe decir cuantas CLIs lo cumplen")
        with open(doc, "w", encoding="utf-8") as f:
            f.write(txt.replace(mt.group(0), mt.group(0).replace(mt.group(2), "9"), 1))
        rc, out = _auditar(raiz)
        self.assertEqual(rc, 1, f"el total de CLIs no se detecto:\n{out}")
        self.assertIn("en ffmpeg_tools/", out)

    def test_avisa_si_el_historial_no_dice_quien_escribio(self):
        # dos sesiones con la MISMA identidad de git hacen que el campo
        # "autor" no distinga: es la unica parte del historial que no se
        # puede recuperar despues, asi que queda avisado en el propio repo
        repo = os.path.join(self.dir, "repo_autor")
        skill = _copia_completa(os.path.join(repo, "skill"))

        def _git(*args, autor=None):
            cmd = ["git", "-C", repo, *args]
            env = None
            if autor:
                import os as _os
                env = dict(_os.environ)
                env["GIT_AUTHOR_NAME"] = autor
                env["GIT_COMMITTER_NAME"] = autor
            subprocess.run(cmd, capture_output=True, text=True, env=env)

        _git("init", "-q")
        _git("config", "user.email", "test@local")
        _git("config", "user.name", "test")
        for i in range(6):
            with open(os.path.join(skill, "references", "mapa.md"), "a", encoding="utf-8") as f:
                f.write(f"\n<!-- {i} -->\n")
            _git("add", "-A")
            _git("commit", "-q", "-m", f"commit {i}", autor="Una Sola Sesion")
        rc, out = _auditar(skill)
        self.assertEqual(rc, 0, f"la atribucion ambigua es un aviso, no un fallo:\n{out}")
        self.assertIn("autribucion ambigua", out)
        # el aviso tiene que decir QUE hacer, y lo que dice tiene que existir:
        # un aviso que manda a leer una convencion que no esta escrita en
        # ningun lado es un aviso que no sirve. la convencion vive en
        # references/mapa.md (regla 12).
        self.assertIn("references/mapa.md", out,
                      "el aviso tiene que decir donde esta la convencion")
        with open(os.path.join(skill, "references", "mapa.md"), encoding="utf-8") as f:
            self.assertIn("[sesion-", f.read(),
                          "la convencion de sufijos tiene que estar escrita")

        # con dos identidades distintas, el historial SI dice quien escribio
        _git("config", "user.name", "otra sesion")
        with open(os.path.join(skill, "references", "mapa.md"), "a", encoding="utf-8") as f:
            f.write("\n<!-- otra -->\n")
        _git("add", "-A")
        _git("commit", "-q", "-m", "commit de otra sesion", autor="Otra Sesion")
        rc, out = _auditar(skill)
        self.assertNotIn("autribucion ambigua", out,
                         "con dos identidades el historial si distingue")

    def test_el_sufijo_de_sesion_resuelve_la_atribucion(self):
        # con la MISMA identidad de git pero con sufijo en el mensaje, la
        # atribucion se puede leer ahi: el aviso no puede quejarse de algo
        # que ya esta arreglado
        repo = os.path.join(self.dir, "repo_sufijo")
        skill = _copia_completa(os.path.join(repo, "skill"))

        def _git(*args, autor=None):
            cmd = ["git", "-C", repo, *args]
            env = None
            if autor:
                import os as _os
                env = dict(_os.environ)
                env["GIT_AUTHOR_NAME"] = autor
                env["GIT_COMMITTER_NAME"] = autor
            subprocess.run(cmd, capture_output=True, text=True, env=env)

        _git("init", "-q")
        _git("config", "user.email", "test@local")
        _git("config", "user.name", "test")
        for i in range(4):
            with open(os.path.join(skill, "references", "mapa.md"), "a", encoding="utf-8") as f:
                f.write(f"\n<!-- {i} -->\n")
            _git("add", "-A")
            _git("commit", "-q", "-m", f"uno [mia]", autor="Misma Identidad")
        for i in range(4):
            with open(os.path.join(skill, "references", "mapa.md"), "a", encoding="utf-8") as f:
                f.write(f"\n<!-- b{i} -->\n")
            _git("add", "-A")
            _git("commit", "-q", "-m", f"otro [tuyo]", autor="Misma Identidad")
        rc, out = _auditar(skill)
        self.assertEqual(rc, 0, f"el aviso no deberia saltar:\n{out}")
        self.assertNotIn("autribucion ambigua", out,
                         "el sufijo en el mensaje ya dice quien escribio cada commit")

    def test_el_guard_dice_como_arreglar_el_conteo(self):
        # el guard no dice solo QUE esta mal: dice QUE HACER. Un fallo sin
        # remedy es un fallo que el agente no sabe resolver.
        #
        # la copia COMPLETA es obligatoria aqui: el conteo del encabezado se
        # verifica contra el codigo (scripts/ffmpeg_tools, scripts/_tests) y
        # sobre un arbol parcial el chequeo sale temprano sin decir nada
        raiz = _copia_completa(os.path.join(self.dir, "skill_conteo"))
        mapa = os.path.join(raiz, "references", "mapa.md")
        with open(mapa, encoding="utf-8") as f:
            txt = f.read()
        with open(mapa, "w", encoding="utf-8") as f:
            f.write(re.sub(r"\d+ referencias, \d+ scripts", "99 referencias, 99 scripts", txt))
        rc, out = _auditar(raiz)
        self.assertEqual(rc, 1, f"el conteo obsoleto deberia fallar:\n{out}")
        self.assertIn("conteo obsoleto", out)
        self.assertIn("actualizar_conteos.py", out,
                      "el fallo tiene que decir como se arregla")

    def test_un_modulo_de_apoyo_en_tests_no_es_una_suite(self):
        # un .py que NO es test_*.py dentro de _tests/ es un modulo de apoyo:
        # es un archivo mas, pero no una suite. el encabezado del mapa dice
        # "N suites de tests": si el guard exigiera el numero de ARCHIVOS,
        # pediria una suite que no existe y la herramienta —que escribe el
        # numero de suites— no podria satisfacerlo: el bucle "corrige y
        # vuelve a fallar" no tendria salida.
        raiz = _copia_completa(os.path.join(self.dir, "skill_apoyo"))
        with open(os.path.join(raiz, "scripts", "_tests", "apoyo.py"), "w",
                  encoding="utf-8") as f:
            f.write("# modulo de apoyo: no es una suite\n")
        rc, out = _auditar(raiz)
        self.assertEqual(rc, 0, f"un modulo de apoyo no es una suite:\n{out}")

    def test_detecta_un_test_anidado_que_no_se_ejecuta(self):
        # un metodo de test dentro de una funcion es codigo muerto: unittest
        # no lo recoge, no corre, y no cambia ninguna cifra publicada (el
        # numero de suites no cambia), asi que nadie se entera nunca.
        raiz = _copia_completa(os.path.join(self.dir, "skill_test_muerto"))
        p = os.path.join(raiz, "scripts", "_tests", "test_paleta.py")
        with open(p, encoding="utf-8") as f:
            txt = f.read()
        self.assertIn("class TestPaletas(unittest.TestCase):", txt,
                      "el fixture tiene que traer la clase")
        inyeccion = (
            "\n    def helper_que_oculta_un_test(self):\n"
            "        def test_este_no_se_ejecuta(self):\n"
            "            self.fail('este test nunca corre')\n"
            "        return test_este_no_se_ejecuta\n"
        )
        with open(p, "w", encoding="utf-8") as f:
            f.write(txt.replace("class TestPaletas(unittest.TestCase):",
                                "class TestPaletas(unittest.TestCase):" + inyeccion, 1))
        rc, out = _auditar(raiz)
        self.assertEqual(rc, 1, f"el test muerto no se detecto:\n{out}")
        self.assertIn("test que no se ejecuta", out)
        self.assertIn("test_este_no_se_ejecuta", out)

    def test_el_guard_dice_cuando_no_encuentra_su_frase(self):
        # un guard cuyo patron deja de casar con la prosa se apaga en
        # silencio y dice "todo bien" sin mirar nada. tiene que decirlo: su
        # objeto es el numero que verifica.
        raiz = _copia_completa(os.path.join(self.dir, "skill_sin_frase"))
        m = os.path.join(raiz, "references", "mapa.md")
        with open(m, encoding="utf-8") as f:
            txt = f.read()
        # el encabezado se reescribe solo (el numero de suites cambia con cada
        # suite nueva): el test no puede hardcodear la cifra
        mt = re.search(r"referencias, \d+ scripts, \d+ herramientas de ffmpeg y \d+ suites",
                       txt)
        self.assertIsNotNone(mt, "el fixture tiene que traer el encabezado")
        with open(m, "w", encoding="utf-8") as f:
            f.write(txt.replace(mt.group(0), "muchas referencias y scripts"))
        rc, out = _auditar(raiz)
        self.assertEqual(rc, 1, f"el guard se apago en silencio:\n{out}")
        self.assertIn("guard sin objeto", out)

    def test_detecta_una_lista_de_escenas_incompleta(self):
        # el numero puede ser correcto y la LISTA que va al lado estar
        # incompleta: el README en espanol listaba 36 de las 39 mientras el
        # ingles las listaba todas, y el guard de cifras salia verde porque
        # el numero (39) era el correcto. la lista se compara POR CONJUNTO
        # contra el catalogo, no contra el numero.
        repo = os.path.join(self.dir, "repo_lista")
        os.makedirs(repo, exist_ok=True)
        skill = _copia_completa(os.path.join(repo, "editoria"))
        # la lista se arma desde el catalogo del motor de la COPIA, no desde
        # el README del repo: ese archivo no viaja en la copia instalada y un
        # test que depende de el falla ahi (y falla justo en el entorno donde
        # la puerta se usa). Un test tiene que pasar con lo que se publica.
        render = os.path.join(skill, "scripts", "render_plan.py")
        with open(render, encoding="utf-8") as f:
            arbol = ast.parse(f.read())
        catalogo = []
        for n in ast.walk(arbol):
            if isinstance(n, ast.Assign) and isinstance(n.value, ast.Dict):
                for t in n.targets:
                    if isinstance(t, ast.Name) and t.id == "SCENES":
                        catalogo = [k.value for k in n.value.keys
                                    if isinstance(k, ast.Constant)]
        self.assertTrue(catalogo, "el motor tiene que traer SCENES")
        faltan = catalogo[-1]
        incompletos = catalogo[:-1]

        def _readme(nombres, partir=False):
            lista = ", ".join(f"`{n}`" for n in nombres)
            if partir:
                lista = lista.replace(", ", ",\n  ", 1)
            return (f"- Renderizar por plan declarativo con {len(catalogo)} tipos — "
                    f"{lista}.\n")

        # la lista incompleta: el caso que se dio (36 de las 39)
        with open(os.path.join(repo, "README.md"), "w", encoding="utf-8") as f:
            f.write(_readme(incompletos))
        rc, out = _auditar(skill)
        self.assertEqual(rc, 1, f"la lista incompleta no se detecto:\n{out}")
        self.assertIn("lista de escenas desfasada", out)
        self.assertIn(faltan, out, "el fallo tiene que decir que escena falta")

        # y la lista COMPLETA, aunque parta en dos lineas, no da falso positivo:
        # un detector que llora se desactiva
        with open(os.path.join(repo, "README.md"), "w", encoding="utf-8") as f:
            f.write(_readme(catalogo, partir=True))
        rc, out = _auditar(skill)
        self.assertEqual(rc, 0, f"una lista partida en dos lineas dio falso positivo:\n{out}")
        self.assertNotIn("lista de escenas desfasada", out)

    def test_no_acusa_una_clase_con_la_base_en_otro_modulo(self):
        # una clase que hereda de una base definida en OTRO modulo (un
        # BaseTest compartido) no se puede resolver sin importarla: acusar a
        # ciegas es peor que callar, porque un detector que llora se
        # desactiva. Hoy ninguna suite usa una base asi, pero el dia que
        # haya una, el guard no puede marcarla.
        raiz = _copia_completa(os.path.join(self.dir, "skill_base_externa"))
        p = os.path.join(raiz, "scripts", "_tests", "test_paleta.py")
        with open(p, encoding="utf-8") as f:
            txt = f.read()
        marca = "class TestPaletas(unittest.TestCase):"
        self.assertIn(marca, txt, "el fixture tiene que traer la clase")
        with open(p, "w", encoding="utf-8") as f:
            f.write(txt.replace(
                marca,
                "class TestAjeno(BaseDeOtroModulo):\n"
                "    def test_algo(self):\n"
                "        pass\n\n\n" + marca, 1))
        rc, out = _auditar(raiz)
        self.assertEqual(rc, 0, f"una base de otro modulo dio falso positivo:\n{out}")
        self.assertNotIn("test que no se ejecuta", out)

        # y una base LOCAL que no es TestCase SI se acusa: ahi si se puede saber
        p2 = os.path.join(raiz, "scripts", "_tests", "test_paleta.py")
        with open(p2, encoding="utf-8") as f:
            txt2 = f.read()
        with open(p2, "w", encoding="utf-8") as f:
            f.write(txt2.replace(
                marca,
                "class Helper:\n    pass\n\n\nclass TestNoTestCase(Helper):\n"
                "    def test_algo(self):\n        pass\n\n\n" + marca, 1))
        rc, out = _auditar(raiz)
        self.assertEqual(rc, 1, f"una clase que no hereda de TestCase no se acuso:\n{out}")
        self.assertIn("test que no se ejecuta", out)

    def test_detecta_una_convencion_que_el_codigo_pide_y_nadie_escribe(self):
        # el codigo le dice al usuario que use una convencion ("marca que es
        # voz de marca"); si no esta escrita en las referencias, el aviso es
        # un puntero a la nada. ya ha pasado dos veces.
        raiz = _copia_completa(os.path.join(self.dir, "skill_convencion"))
        doc = os.path.join(raiz, "references", "copy.md")
        with open(doc, encoding="utf-8") as f:
            txt = f.read()
        self.assertIn("Voz de marca", txt, "el fixture tiene que traer la convencion")
        with open(doc, "w", encoding="utf-8") as f:
            f.write(txt.replace("Voz de marca", "Lo de la marca"))
        rc, out = _auditar(raiz)
        self.assertEqual(rc, 1, f"la convencion sin escribir no se detecto:\n{out}")
        self.assertIn("convencion sin escribir", out)

    def test_detecta_un_test_duplicado_en_la_misma_clase(self):
        # un metodo repetido en la misma clase: Python conserva el ultimo y
        # el primero es codigo muerto. no se ve: el nombre sigue ahi, con el
        # mismo aspecto, y el segundo parece el unico (y el conteo de tests
        # no se mueve, asi que nada lo delata).
        raiz = _copia_completa(os.path.join(self.dir, "skill_duplicado"))
        p = os.path.join(raiz, "scripts", "_tests", "test_paleta.py")
        with open(p, encoding="utf-8") as f:
            txt = f.read()
        marca = "    def test_una_paleta_inexistente_es_error_explicito(self):"
        self.assertIn(marca, txt, "el fixture tiene que traer el test")
        with open(p, "w", encoding="utf-8") as f:
            f.write(txt.replace(marca, marca + "\n        pass\n\n" + marca, 1))
        rc, out = _auditar(raiz)
        self.assertEqual(rc, 1, f"el test duplicado no se detecto:\n{out}")
        self.assertIn("test que no se ejecuta", out)
        self.assertIn("definido dos veces", out)

    def test_detecta_un_fichero_de_test_roto(self):
        # un fichero de test que no se puede leer no es un test que no corre:
        # es un test ROTO. saltarselo en silencio deja el hueco sin vigilar.
        raiz = _copia_completa(os.path.join(self.dir, "skill_test_roto"))
        p = os.path.join(raiz, "scripts", "_tests", "test_paleta.py")
        with open(p, "a", encoding="utf-8") as f:
            f.write("\nclass Roto(:\n")
        rc, out = _auditar(raiz)
        self.assertEqual(rc, 1, f"el test roto no se detecto:\n{out}")
        self.assertIn("test que no se ejecuta", out)
        self.assertIn("no se puede leer", out)

    def test_detecta_un_texto_fijo_sobre_una_caja_de_acento(self):
        # el hook de un short ponia el titular con color fijo sobre un box del
        # acento de la marca: con menta el titular quedaba a 2:1. el acento lo
        # elige el usuario, asi que el texto tiene que seguir al fondo.
        raiz = _copia_completa(os.path.join(self.dir, "skill_texto"))
        p = os.path.join(raiz, "scripts", "ffmpeg_tools", "shorts_plan.py")
        with open(p, encoding="utf-8") as f:
            txt = f.read()
        self.assertIn("fontcolor={texto_sobre(acento", txt,
                      "el fixture tiene que traer el arreglo")
        with open(p, "w", encoding="utf-8") as f:
            f.write(txt.replace("fontcolor={texto_sobre(acento, tokens=_tok)}", "fontcolor=#FAF8F6"))
        rc, out = _auditar(raiz)
        self.assertEqual(rc, 1, f"el texto fijo sobre acento no se detecto:\n{out}")
        self.assertIn("texto fijo sobre acento", out)
        self.assertIn("shorts_plan.py", out)

    def test_el_guard_no_depende_de_la_forma_del_nombre_del_acento(self):
        # la regla es "el color de la caja menciona el acento". un patron que
        # exigiera frontera de palabra despues de "acento" se escapaba con un
        # nombre como "acento2": el nombre cambia de forma, la caja sigue
        # siendo la del acento y el texto fijo sigue sin poder leerse.
        raiz = _copia_completa(os.path.join(self.dir, "skill_texto2"))
        p = os.path.join(raiz, "scripts", "ffmpeg_tools", "shorts_plan.py")
        with open(p, encoding="utf-8") as f:
            txt = f.read()
        self.assertIn("boxcolor={acento}", txt, "el fixture tiene que traer la caja de acento")
        with open(p, "w", encoding="utf-8") as f:
            f.write(txt.replace("fontcolor={texto_sobre(acento, tokens=_tok)}", "fontcolor=#FAF8F6")
                        .replace("boxcolor={acento}", "boxcolor={acento2}"))
        rc, out = _auditar(raiz)
        self.assertEqual(rc, 1, f"el texto fijo sobre acento con otra forma de nombre "
                                 f"no se detecto:\n{out}")
        self.assertIn("texto fijo sobre acento", out)
        self.assertIn("shorts_plan.py", out)

    def test_detecta_una_clave_del_plan_sin_documentar(self):
        # el plan es el contrato: si el motor lee una clave que ningun
        # documento menciona, el que escribe el plan no la conoce
        raiz = _copia_completa(os.path.join(self.dir, "skill_completa"))
        p = os.path.join(raiz, "scripts", "render_plan.py")
        with open(p, encoding="utf-8") as f:
            txt = f.read()
        self.assertIn('plan.get("paleta"', txt, "el motor lee la paleta del plan")
        nueva = "clave_" + "nueva_del_plan"
        with open(p, "w", encoding="utf-8") as f:
            f.write(txt.replace('plan.get("paleta"',
                                'plan.get("%s", plan.get("paleta")' % nueva, 1))
        rc, out = _auditar(raiz)
        self.assertEqual(rc, 1, f"la clave sin documentar no se detecto:\n{out}")
        self.assertIn("clave del plan sin documentar", out)
        self.assertIn(nueva, out)

    def test_detecta_una_cli_fuera_del_skill_md(self):
        # una CLI enlazada solo en una referencia es una herramienta que el
        # agente no descubre: el .md que lee primero es el SKILL.md
        raiz = _copia_completa(os.path.join(self.dir, "skill_clis"))
        with open(os.path.join(raiz, "scripts", "cli_nueva.py"), "w", encoding="utf-8") as f:
            f.write("# una CLI que nadie encuentra\n")
        rc, out = _auditar(raiz)
        self.assertEqual(rc, 1, f"la CLI fuera del SKILL.md no se detecto:\n{out}")
        self.assertIn("CLI fuera del SKILL.md", out)
        self.assertIn("cli_nueva.py", out)

    def test_detecta_un_conteo_obsoleto_en_ingles(self):
        # el SKILL.md esta en ingles y decia "53 references" cuando hay 55:
        # los patrones del guard buscaban la forma "en kebab-case" y la prosa
        # en ingles se escapaba entera
        raiz = _copia_completa(os.path.join(self.dir, "skill_ingles"))
        s = os.path.join(raiz, "SKILL.md")
        with open(s, encoding="utf-8") as f:
            txt = f.read()
        self.assertRegex(txt, r"\d+\s+references",
                         "el SKILL.md deberia enunciar el numero de referencias")
        with open(s, "w", encoding="utf-8") as f:
            f.write(re.sub(r"(\d+)\s+references", "53 references", txt, count=1))
        rc, out = _auditar(raiz)
        self.assertEqual(rc, 1, f"el conteo obsoleto en ingles no se detecto:\n{out}")
        self.assertIn("conteo obsoleto", out)

    def test_detecta_una_cifra_de_operaciones_obsoleta(self):
        # el SKILL.md dice "montaje.py (19 operations)": si la CLI gana una
        # operacion, ese numero tiene que avisar
        raiz = _copia_completa(os.path.join(self.dir, "skill_cli"))
        s = os.path.join(raiz, "SKILL.md")
        with open(s, encoding="utf-8") as f:
            txt = f.read()
        self.assertRegex(txt, r"\d+\s+operations", "el SKILL.md deberia enunciar las operaciones")
        with open(s, "w", encoding="utf-8") as f:
            f.write(re.sub(r"(\d+)\s+operations", "3 operations", txt, count=1))
        rc, out = _auditar(raiz)
        self.assertEqual(rc, 1, f"la cifra de la CLI no se detecto:\n{out}")
        self.assertIn("operaciones de montage.py", out)


class TestCifrasDelCodigo(unittest.TestCase):
    """Las cifras de la prosa tienen que ser las del codigo.

    La puerta corre un numero de pasos que DEPENDE del modo (con plan
    comprueba el plan y el copy; sin plan no hay plan que comprobar), asi
    que cualquier numero fijo en la prosa es un numero falso. La rubrica
    tiene ocho ejes y el codigo tambien: si divergen, el doc miente.
    """

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="editoria_cifras_")
        self.addCleanup(shutil.rmtree, self.dir, True)

    def _completa(self):
        return _copia_completa(os.path.join(self.dir, "skill"))

    def _ref(self, raiz, nombre):
        with open(os.path.join(raiz, "references", nombre), encoding="utf-8") as f:
            return f.read()

    def _escribir(self, raiz, nombre, txt):
        with open(os.path.join(raiz, "references", nombre), "w", encoding="utf-8") as f:
            f.write(txt)

    def test_detecta_un_numero_falso_de_comprobaciones(self):
        raiz = self._completa()
        txt = self._ref(raiz, "qa-entrega.md")
        self.assertIn("comprobaciones", txt)
        self._escribir(raiz, "qa-entrega.md",
                       txt.replace("Todas las comprobaciones", "Cinco comprobaciones", 1))
        rc, out = _auditar(raiz)
        self.assertEqual(rc, 1, f"el numero falso no se detecto:\n{out}")
        self.assertIn("cifra falsa", out)

    def test_detecta_una_rubrica_descuadrada(self):
        raiz = self._completa()
        txt = self._ref(raiz, "rubrica-premios.md")
        self._escribir(raiz, "rubrica-premios.md", txt.replace("| 8 |", "| 9 |", 1))
        rc, out = _auditar(raiz)
        self.assertEqual(rc, 1, f"la rubrica descuadrada no se detecto:\n{out}")
        self.assertIn("rubrica descuadrada", out)

    def test_detecta_un_numero_de_comprobaciones_obsoleto(self):
        # la puerta corre 3 comprobaciones sin plan y 8 con plan. el numero
        # que dice la prosa tiene que ser ese.
        raiz = _copia_completa(os.path.join(self.dir, "skill_puerta"))
        m = os.path.join(raiz, "references", "mapa.md")
        with open(m, encoding="utf-8") as f:
            txt = f.read()
        self.assertIn("ocho comprobaciones", txt, "el fixture tiene que traer la cifra buena")
        with open(m, "w", encoding="utf-8") as f:
            f.write(txt.replace("ocho comprobaciones", "cinco comprobaciones"))
        rc, out = _auditar(raiz)
        self.assertEqual(rc, 1, f"el numero obsoleto no se detecto:\n{out}")
        self.assertIn("cifra falsa", out)
        self.assertIn("comprobaciones", out)
        self.assertIn("8 con plan", out, "el fallo tiene que decir cuantos corre la puerta")

    def test_el_guard_cuenta_los_pasos_de_la_puerta_de_verdad(self):
        # el contador leia montage.py en vez de qa_entrega.py: contaba 0
        # pasos y comparaba 0 contra la prosa, sin decir nada. anadir un paso
        # a la puerta tiene que cambiar el numero que el guard exige.
        raiz = _copia_completa(os.path.join(self.dir, "skill_pasos"))
        q = os.path.join(raiz, "scripts", "qa_entrega.py")
        with open(q, encoding="utf-8") as f:
            txt = f.read()
        marca = '    pasos.append(_ejecutar("delivery", lambda: _paso_delivery(args.video, args.plataforma)))'
        self.assertIn(marca, txt, "el fixture tiene que traer la puerta")
        with open(q, "w", encoding="utf-8") as f:
            f.write(txt.replace(marca, marca + "\n" + marca, 1))
        rc, out = _auditar(raiz)
        self.assertEqual(rc, 1, f"anadir un paso a la puerta no se vio:\n{out}")
        self.assertIn("cifra falsa", out)
        self.assertIn("9 con plan", out,
                      "el guard tiene que leer qa_entrega.py, no otro archivo")

    def test_detecta_un_eje_renombrado_en_la_rubrica(self):
        raiz = self._completa()
        txt = self._ref(raiz, "rubrica-premios.md")
        self.assertIn("Acabado", txt, "el eje 8 deberia llamarse 'Acabado tecnico'")
        self._escribir(raiz, "rubrica-premios.md", txt.replace("**Acabado", "**Remate", 1))
        rc, out = _auditar(raiz)
        self.assertEqual(rc, 1, f"el eje renombrado no se detecto:\n{out}")
        self.assertIn("rubrica descuadrada", out)
        # el motor es la fuente: si LETRA_MIN cambia, el valor esperado cambia
        with open(AUDITAR, encoding="utf-8") as f:
            txt = f.read()
        m = re.search(r'"nombre":\s*"piso de letra".*?"valor":\s*(\d+)', txt, re.S)
        self.assertIsNotNone(m, "la regla del piso de letra debe estar en auditar_mapa.py")
        with open(os.path.join(SCRIPTS, "medir_animacion.py"), encoding="utf-8") as f:
            motor = f.read()
        self.assertIn(f"LETRA_MIN = {m.group(1)}", motor,
                      "el valor esperado tiene que ser el LETRA_MIN real del motor")


class TestBasuraEnElHistorial(unittest.TestCase):
    """El historial es texto publicado: un ideograma en un mensaje sale publicado.

    El guard del ARBOL caza la basura de otra generacion en los .md/.py/.json,
    pero el MENSAJE de un commit no vive en el arbol: nadie lo miraba. Por esa
    puerta se colaron dos ideogramas en un mensaje de commit, y si ese commit
    hubiera sido el de la rama, el texto roto habria salido publicado.

    La MUTACION: con el mensaje limpio el guard no dice nada; con un ideograma
    dentro, tiene que decirlo. (El ideograma del fixture va en escapes: si
    estuviera escrito en este fuente, el guard del arbol lo marcaria a el.)
    """

    _BASURA = chr(0x7406) + chr(0x7531)

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="editoria_historial_")
        self.raiz = _copia_minima(os.path.join(self.dir, "skill"))
        self.addCleanup(shutil.rmtree, self.dir, True)

    def _commit(self, mensaje):
        for c in (["init", "-q"], ["config", "user.email", "t@local"],
                  ["config", "user.name", "t"], ["add", "-A"]):
            subprocess.run(["git", "-C", self.raiz] + c, capture_output=True, timeout=30)
        r = subprocess.run(["git", "-C", self.raiz, "commit", "-q", "-m", mensaje],
                           capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)

    def _informe(self):
        """El informe JSON del auditor: lo que importa es en que CUBO cae la
        entrada (fallos o avisos), no el texto que imprime."""
        destino = os.path.join(self.dir, "informe.json")
        subprocess.run([sys.executable, os.path.join(self.raiz, "scripts", "auditar_mapa.py"),
                        "--json", destino], capture_output=True, text=True, timeout=300)
        with open(destino, encoding="utf-8") as f:
            return json.load(f)

    def test_un_mensaje_con_basura_se_caza(self):
        self._commit("fix: la razon pegada a la forma " + self._BASURA)
        rc, out = _auditar(self.raiz)
        self.assertIn("basura en el historial", out,
                      "un mensaje de commit con basura tiene que salir en el informe")
        # y tiene que FRENAR la puerta, no solo decirla: un aviso que no
        # cambia el codigo de salida es una nota, y el texto roto sale
        # publicado igual.
        self.assertEqual(rc, 1,
                         f"la basura en el historial tiene que ser un FALLO (salio {rc}):\n{out}")
        informe = self._informe()
        self.assertTrue(any(p["tipo"] == "basura en el historial"
                            for p in informe["problemas"]),
                        "la entrada tiene que estar en los FALLOS, no en los avisos")

    def test_un_mensaje_limpio_no_se_marca(self):
        self._commit("fix: la razon pegada a la forma")
        rc, out = _auditar(self.raiz)
        self.assertNotIn("basura en el historial", out,
                         "un mensaje limpio no puede marcarse")

    def test_lo_que_ya_salio_avisa_pero_no_frena(self):
        """Lo publicado es HISTORIA: se dice, pero no deja el repo en rojo.

        Un fallo que no se puede arreglar (reescribir el historial) dejaria
        la puerta en rojo para siempre, y una puerta que nadie puede pasar
        no es una puerta: es un adorno."""
        self._commit("fix: la razon pegada a la forma " + self._BASURA)
        subprocess.run(["git", "-C", self.raiz, "update-ref",
                        "refs/remotes/origin/main", "HEAD"],
                       capture_output=True, timeout=30)
        rc, out = _auditar(self.raiz)
        self.assertIn("basura en el historial", out,
                      "lo que ya salio publicado se dice igualmente")
        informe = self._informe()
        self.assertFalse(any(p["tipo"] == "basura en el historial"
                             for p in informe["problemas"]),
                         "lo ya publicado no puede ser un fallo: no se puede arreglar")
        self.assertTrue(any(p["tipo"] == "basura en el historial"
                            for p in informe["avisos"]),
                        "lo ya publicado se dice, en el cubo de los avisos")


if __name__ == "__main__":
    unittest.main()
