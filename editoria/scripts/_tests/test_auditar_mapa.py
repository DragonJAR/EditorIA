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


if __name__ == "__main__":
    unittest.main()
