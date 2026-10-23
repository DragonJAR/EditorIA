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
    for sub in ("brand", "metricas"):
        origen = os.path.join(BASE, sub)
        if os.path.isdir(origen):
            shutil.copytree(origen, os.path.join(destino, sub))
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

    def test_detecta_una_densidad_atribuida_al_motor_que_no_es_la_del_motor(self):
        # el glosario decia "el motor pide uno cada 0,8-1,5 s" cuando el motor
        # penaliza fuera de 0,5-2: un numero falso en la prosa, y el guard
        # no lo veia porque comparaba contra el mismo numero equivocado
        raiz = self.raiz
        with open(os.path.join(raiz, "references", "glosario.md"), encoding="utf-8") as f:
            txt = f.read()
        self.assertIn("motor", txt.lower())
        nuevo = re.sub(r"[Ee]l motor penaliza fuera de [\d.,]+-[\d.,]+ s",
                       "El motor pide uno cada 0,8-1,5 s", txt)
        self.assertNotEqual(txt, nuevo, "el glosario debe enunciar la densidad del motor")
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
