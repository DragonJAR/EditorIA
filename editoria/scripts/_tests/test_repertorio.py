#!/usr/bin/env python3
"""Tests del repertorio: la única fuente intención→escena y su rotación.

Lo que motivó esto: el catálogo tenía 39 escenas y el flujo normal usaba
siempre las mismas 6-8. Las familias para rotar vivían solo en
clonar_video.py (27 nombres, un fantasma 'titular', 13 huérfanas), el
auditor repetía otra lista a mano en el texto de un aviso, y entre piezas
nadie miraba nada. Ahora repertorio.json es la fuente, repertorio.py la
consume y estos tests fijan que no vuelve a pudrirse.

Run with: python3 -m unittest discover -s SKILL/scripts/_tests
"""
import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)

import auditar_plan as AP  # noqa: E402
import clonar_video as CV  # noqa: E402
import repertorio as REP  # noqa: E402


def _plan(tipos, **extra):
    plan = {"duracion": 5.0 * len(tipos),
            "escenas": [{"tipo": t, "from": i * 5.0, "to": (i + 1) * 5.0,
                         "titulo": "Dato"} for i, t in enumerate(tipos)]}
    plan.update(extra)
    return plan


class TestFuenteUnica(unittest.TestCase):
    def test_sin_huerfanas_ni_fantasmas(self):
        self.assertEqual(REP.validar(), [])

    def test_todo_el_catalogo_es_alcanzable(self):
        cubiertas = {e for v in REP.familias().values() for e in v}
        self.assertEqual(cubiertas, REP.catalogo())
        import render_plan as _R
        self.assertEqual(len(cubiertas), len(_R.SCENES))

    def test_clonar_deriva_de_la_misma_fuente(self):
        fams = REP.familias()
        for rol, inten in REP.cargar()["roles_clonar"].items():
            self.assertEqual(CV.FAMILIAS_ESCENAS[rol], fams[inten])
        todos = {e for v in CV.FAMILIAS_ESCENAS.values() for e in v}
        self.assertTrue(todos <= REP.catalogo(), "familia con fantasma")
        self.assertNotIn("titular", todos)

    def test_una_escena_puede_servir_a_varias_intenciones(self):
        self.assertIn("comparacion", REP.intencion_de("bars"))
        self.assertIn("dato", REP.intencion_de("bars"))


class TestElegir(unittest.TestCase):
    def test_determinista(self):
        a = REP.elegir(["gancho", "dato", "cierre"], semilla=3)
        b = REP.elegir(["gancho", "dato", "cierre"], semilla=3)
        self.assertEqual(a, b)

    def test_evita_la_pieza_anterior_si_puede(self):
        anterior = _plan(["hero", "pie", "hoy", "chat", "confetti"])
        mano = REP.elegir(["gancho", "dato", "proceso", "social", "cierre"],
                          evitar=REP.tipos_de(anterior))
        for m in mano:
            self.assertFalse(m["reutilizada"])
            self.assertNotIn(m["escena"], REP.tipos_de(anterior))

    def test_si_toda_la_familia_se_evita_lo_dice(self):
        mano = REP.elegir(["estado"], evitar=REP.familias()["estado"])
        self.assertTrue(mano[0]["reutilizada"])

    def test_no_repite_dentro_de_la_misma_mano(self):
        mano = REP.elegir(["dato", "comparacion"], semilla=0)
        self.assertEqual(len({m["escena"] for m in mano}), 2)

    def test_intencion_desconocida_falla_claro(self):
        with self.assertRaises(ValueError):
            REP.elegir(["inventada"])


class TestCoberturaYAuditoria(unittest.TestCase):
    def _avisos(self, plan, codigo, anteriores=None):
        return [h["msg"] for h in AP.auditar_tells(plan, anteriores=anteriores)
                if h.get("codigo") == codigo]

    def test_resumen_mide_contra_el_catalogo_entero(self):
        r = REP.resumen([_plan(["apertura", "stats", "final"])])
        import render_plan as _R
        self.assertEqual(r["n_catalogo"], len(_R.SCENES))
        self.assertEqual(r["n_tipos"], 3)
        self.assertIn("gancho", r["intenciones_cubiertas"])

    def test_no_aplica_queda_explicito_en_el_resumen(self):
        plan = _plan(["apertura"], no_aplica={"imagen-texto": "sin foto"})
        r = REP.resumen([plan])
        fila = next(i for i in r["intenciones_sin_tocar"] if i["id"] == "imagen-texto")
        self.assertTrue(fila["declarada_no_aplica"])
        self.assertEqual(fila["motivo"], "sin foto")

    def test_ruta_repetida_entre_piezas(self):
        anterior = _plan(["apertura", "stats", "stats", "final"])
        actual = _plan(["hero", "stats", "stats", "remate"])
        self.assertTrue(self._avisos(actual, "ruta-repetida", [anterior]))

    def test_ruta_distinta_no_avisa(self):
        anterior = _plan(["apertura", "stats", "pasos", "final"])
        actual = _plan(["countdown", "gauge", "orbita", "audiowave", "versus", "demo"])
        self.assertFalse(self._avisos(actual, "ruta-repetida", [anterior]))

    def test_sin_anteriores_no_hay_ruta_repetida(self):
        plan = _plan(["stats"] * 6)
        self.assertFalse(self._avisos(plan, "ruta-repetida"))

    def test_intencion_declarada_sin_escena(self):
        plan = _plan(["apertura", "stats"],
                     intenciones=["gancho", "proceso"],
                     no_aplica={i: "no aplica" for i in REP.familias()
                                if i not in ("gancho", "dato", "proceso")})
        msgs = self._avisos(plan, "intencion-sin-escena")
        self.assertTrue(any("proceso" in m for m in msgs))

    def test_intencion_olvidada_se_nombra(self):
        plan = _plan(["apertura"], intenciones=["gancho"])
        msgs = self._avisos(plan, "intencion-olvidada")
        self.assertTrue(msgs)
        self.assertIn("dato", msgs[0])

    def test_plan_heredado_sin_declaracion_no_avisa(self):
        plan = _plan(["apertura", "stats", "final", "hero", "bars", "pie", "quote"])
        self.assertFalse(self._avisos(plan, "intencion-olvidada"))
        self.assertFalse(self._avisos(plan, "intencion-sin-escena"))

    def test_todo_declarado_no_avisa(self):
        tipos = ["apertura", "stats", "pasos", "chat", "remate"]
        plan = _plan(tipos, intenciones=["gancho", "dato", "proceso", "social", "cierre"],
                     no_aplica={i: "no aplica a este argumento" for i in REP.familias()
                                if i not in ("gancho", "dato", "proceso", "social", "cierre")})
        self.assertFalse(self._avisos(plan, "intencion-olvidada"))
        self.assertFalse(self._avisos(plan, "intencion-sin-escena"))


class TestCLI(unittest.TestCase):
    """La CLI documentada se ejecuta de verdad (censo de CLIs)."""

    def _corre(self, *args):
        return subprocess.run(
            [sys.executable, os.path.join(SCRIPTS, "repertorio.py"), *args],
            capture_output=True, text=True)

    def test_validar_y_sugerir_por_cli(self):
        r = self._corre("validar")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("REPERTORIO VALIDO", r.stdout)
        r = self._corre("sugerir", "--intenciones", "gancho,dato,cierre", "--json")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        mano = json.loads(r.stdout)["mano"]
        self.assertEqual([m["intencion"] for m in mano], ["gancho", "dato", "cierre"])
        self.assertTrue(all(m["escena"] in REP.catalogo() for m in mano))

    def test_listar_todo_por_cli(self):
        r = self._corre("listar", "--todo")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        import render_plan as _R
        self.assertIn(f"{len(_R.SCENES)} escenas", r.stdout)
        self.assertIn("paletas", r.stdout)


if __name__ == "__main__":
    unittest.main()
