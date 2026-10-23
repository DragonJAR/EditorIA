#!/usr/bin/env python3
"""Tests de auditar_mapa.py — la garantia de que la skill no se rompe en islas.

Cada test construye una copia minima de la skill, la rompe de una forma
concreta y comprueba que el auditor la detecta. El ultimo test comprueba que
la skill REAL pasa.

Run with: python3 -m unittest discover -s SKILL/scripts/_tests
"""

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
        # el SKILL.md enumera las suites que deben pasar: si esa lista no es
        # el conjunto real, la promesa envejece en silencio
        raiz = self.raiz
        d = os.path.join(raiz, "scripts", "_tests")
        os.makedirs(d, exist_ok=True)
        # primero, las que el SKILL.md lista, para que el check no grune
        with open(os.path.join(raiz, "SKILL.md"), encoding="utf-8") as f:
            txt = f.read()
        for nombre in set(re.findall(r"scripts/_tests/(test_[A-Za-z0-9_]+\.py)", txt)):
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
        with open(os.path.join(raiz, "SKILL.md"), encoding="utf-8") as f:
            txt = f.read()
        ruta = "scripts" + "/_tests/" + fantasma
        with open(os.path.join(raiz, "SKILL.md"), "w", encoding="utf-8") as f:
            f.write(txt + "\n`" + ruta + "`\n")
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

        # el segundo commit: una suite desaparece de la lista Y del arbol
        s = os.path.join(skill, "SKILL.md")
        with open(s, encoding="utf-8") as f:
            txt = f.read()
        suites = re.findall(r"scripts/_tests/(test_[A-Za-z0-9_]+\.py)", txt)
        self.assertTrue(suites, "el SKILL.md deberia listar suites")
        victim = suites[0]
        ruta = os.path.join(skill, "scripts", "_tests", victim)
        self.assertTrue(os.path.exists(ruta), f"la suite listada {victim} deberia existir")
        os.remove(ruta)
        with open(s, "w", encoding="utf-8") as f:
            f.write(re.sub(r"[,\s]*`?scripts/_tests/" + re.escape(victim) + r"`?", "", txt))
        _git("add", "-A")
        _git("commit", "-q", "-m", "dos")

        rc, out = _auditar(skill)
        self.assertEqual(rc, 1, f"el commit que arrastro trabajo no se detecto:\n{out}")
        self.assertIn("suite perdida en el commit", out)
        self.assertIn(victim, out)

    def test_detecta_una_cifra_de_cli_obsoleta(self):
        # el contrato de CLI declara cuantos scripts lo cumplen: si ese
        # numero no es el real, el documento miente sobre la skill
        raiz = self._completa()
        doc = os.path.join(raiz, "references", "cli-contract.md")
        with open(doc, encoding="utf-8") as f:
            txt = f.read()
        mt = re.search(r"(\d+)\s+CLIs\s+de\s+`?ffmpeg_tools`?\s+usan", txt)
        self.assertIsNotNone(mt, "el contrato debe decir cuantas CLIs lo cumplen")
        with open(doc, "w", encoding="utf-8") as f:
            f.write(txt.replace(mt.group(0), mt.group(0).replace(mt.group(1), "99"), 1))
        rc, out = _auditar(raiz)
        self.assertEqual(rc, 1, f"la cifra del contrato no se detecto:\n{out}")
        self.assertIn("CLIs con el contrato", out)

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

    def test_detecta_una_cifra_de_cli_obsoleta(self):
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
        # la puerta corre 3 comprobaciones sin plan y 6 con plan. el numero
        # que dice la prosa tiene que ser ese.
        raiz = _copia_completa(os.path.join(self.dir, "skill_puerta"))
        m = os.path.join(raiz, "references", "mapa.md")
        with open(m, encoding="utf-8") as f:
            txt = f.read()
        self.assertIn("seis comprobaciones", txt, "el fixture tiene que traer la cifra buena")
        with open(m, "w", encoding="utf-8") as f:
            f.write(txt.replace("seis comprobaciones", "cinco comprobaciones"))
        rc, out = _auditar(raiz)
        self.assertEqual(rc, 1, f"el numero obsoleto no se detecto:\n{out}")
        self.assertIn("cifra falsa", out)
        self.assertIn("comprobaciones", out)
        self.assertIn("6 con plan", out, "el fallo tiene que decir cuantos corre la puerta")

    def test_el_guard_cuenta_los_pasos_de_la_puerta_de_verdad(self):
        # el contador leia montage.py en vez de qa_entrega.py: contaba 0
        # pasos y comparaba 0 contra la prosa, sin decir nada. anadir un paso
        # a la puerta tiene que cambiar el numero que el guard exige.
        raiz = _copia_completa(os.path.join(self.dir, "skill_pasos"))
        q = os.path.join(raiz, "scripts", "qa_entrega.py")
        with open(q, encoding="utf-8") as f:
            txt = f.read()
        marca = "    pasos.append(_paso_delivery(args.video, args.plataforma))"
        self.assertIn(marca, txt, "el fixture tiene que traer la puerta")
        with open(q, "w", encoding="utf-8") as f:
            f.write(txt.replace(marca, marca + "\n" + marca, 1))
        rc, out = _auditar(raiz)
        self.assertEqual(rc, 1, f"anadir un paso a la puerta no se vio:\n{out}")
        self.assertIn("cifra falsa", out)
        self.assertIn("7 con plan", out,
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


if __name__ == "__main__":
    unittest.main()
