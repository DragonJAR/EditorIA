#!/usr/bin/env python3
"""Tests del auditor de plan: credenciales, estructura y voz.

Lo que motivó esto: el SKILL.md promete, en la seccion "Critical", que
"no credentials or API keys appear in plan.json or brand/*.json", y nadie lo
verificaba. Un plan con una key pegada se publica en el repo con la pieza.
Ahora el mismo comando que el agente corre antes de renderizar lo dice.

Run with: python3 -m unittest discover -s SKILL/scripts/_tests
"""

import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)

import auditar_plan as AP  # noqa: E402
from speech_estimate import estimar_duracion  # noqa: E402


def _plan(**extra):
    plan = {"duracion": 3.0,
            "escenas": [{"tipo": "apertura", "from": 0, "to": 3, "texto1": ["Hola"]}]}
    plan.update(extra)
    return plan


class TestCredenciales(unittest.TestCase):
    """Una credencial en el plan se publica con la pieza."""

    def _errores(self, plan):
        return [h["msg"] for h in AP.auditar_estructura(plan) if h["nivel"] == "ERROR"]

    def test_una_key_con_formato_sk_falla(self):
        errs = self._errores(_plan(api_key="sk-abc1234567890xyz"))
        self.assertTrue(errs)
        self.assertIn("credencial", errs[0])

    def test_un_campo_que_se_llama_secret_falla(self):
        errs = self._errores(_plan(marca={"secret": "AKIAIOSFODNN7EXAMPLE"}))
        self.assertTrue(errs)

    def test_una_variable_de_entorno_con_key_falla(self):
        errs = self._errores(_plan(guion="ELEVENLABS_API_KEY=abcd1234"))
        self.assertTrue(errs)

    def test_un_jwt_falla(self):
        errs = self._errores(_plan(nota="Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.abc"))
        self.assertTrue(errs)

    def test_un_plan_limpio_no_da_falso_positivo(self):
        self.assertEqual(self._errores(_plan(rotulo="Mi marca", tokens_de_diseno="abc")), [])

    def test_un_placeholder_no_es_credencial(self):
        self.assertEqual(self._errores(_plan(api_key="<tu key>")), [])
        self.assertEqual(self._errores(_plan(secret="xxx")), [])

    def test_los_packs_de_ejemplo_estan_limpios(self):
        """Todos los packs que se publican, sin nombrar ninguno en el fuente.

        Los packs se descubren con un glob: el nombre del pack de ejemplo es
        una marca de la casa y no puede quedar escrito en el codigo.
        """
        import glob
        packs = glob.glob(os.path.join(SCRIPTS, "..", "brand", "*.json"))
        if not packs:
            self.skipTest("este arbol no trae packs de ejemplo")
        for pack in packs:
            with open(pack, encoding="utf-8") as f:
                self.assertEqual(AP.credenciales_en(json.load(f)), [],
                                 f"credencial en el pack {os.path.basename(pack)}")

    def test_la_credencial_aparece_en_el_archivo_del_plan(self):
        """No basta con la funcion: el ERROR tiene que salir en la salida real."""
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "plan.json")
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump(_plan(api_key="sk-abc1234567890xyz"), f)
            import subprocess
            r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "auditar_plan.py"), ruta],
                               capture_output=True, text=True, timeout=300)
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("credencial", r.stdout)


class TestRelojDeLaNarracion(unittest.TestCase):
    """La tolerancia del audit va con el hueco disponible, no es un numero
    plano.

    La estimacion silabica NO es exacta: medida contra audio real (50 frases
    de la voz del sistema, Paulina es-MX a 178 ppm) overestimate el tiempo
    real entre un 9% y un 24% (mediana 12%). Con un margen FIJO de 0.3s
    (menor que ese error) el audit rechazaba planes cuya narracion cabia de
    verdad: un falso positivo que hacia recortar copy que no sobraba. Ahora
    solo es ERROR cuando el exceso sale de la banda de error de la
    estimacion; por debajo es AVISO, y quien falla si las voces se pisan es
    el TTS real (voz_off.py / voz_local.py), que mide el audio sintetizado.
    """

    TEXTO = "Cada hallazgo llega con su severidad CVSS, para corregir lo que más duele."

    def _plan(self, hueco):
        return {"duracion": hueco * 3,
                "escenas": [
                    {"tipo": "apertura", "from": 0.0, "to": hueco, "voz": self.TEXTO},
                    {"tipo": "bento", "from": hueco, "to": hueco * 2, "voz": "Segunda frase."},
                    {"tipo": "final", "from": hueco * 2, "to": hueco * 3},
                ]}

    def _niveles(self, plan):
        return [h["nivel"] for h in AP.auditar_estructura(plan)]

    def test_un_exceso_dentro_de_la_banda_es_aviso_y_no_error(self):
        est = estimar_duracion(self.TEXTO)
        # la estimacion excede el hueco un 10%: dentro de la banda
        niveles = self._niveles(self._plan(est * 0.9))
        self.assertNotIn("ERROR", niveles)
        self.assertIn("AVISO", niveles)

    def test_un_exceso_fuera_de_la_banda_es_error(self):
        est = estimar_duracion(self.TEXTO)
        # la estimacion excede el hueco un 100%: fuera de toda banda
        self.assertIn("ERROR", self._niveles(self._plan(est * 0.5)))

    def test_el_margen_crece_con_el_hueco(self):
        """Un hueco mas grande tolera un exceso mayor: el margen es
        proporcional, no fijo."""
        est = estimar_duracion(self.TEXTO)
        # con el hueco justo: la estimacion excede un 2% -> aviso
        self.assertNotIn("ERROR", self._niveles(self._plan(est * 0.98)))
        # con el hueco muy justo: la estimacion excede un 40% -> error
        self.assertIn("ERROR", self._niveles(self._plan(est * 0.6)))

    def test_la_voz_que_se_pasa_del_final_del_video_avisa(self):
        """La voz que se sale del FINAL no tiene otra imagen que la tape:
        se corta contra el borde. Con la estimacion no se puede probar el
        corte, asi que avisa (quien falla es el TTS real)."""
        texto = "Esta frase es deliberadamente larguisima para ocupar mucho tiempo de reloj."
        est = estimar_duracion(texto)
        plan = {"duracion": est * 0.5,
                "escenas": [{"tipo": "final", "from": 0.0, "to": est * 0.5, "voz": texto}]}
        avisos = [h for h in AP.auditar_estructura(plan)
                  if h["nivel"] == "AVISO" and "final del video" in h["msg"]]
        self.assertTrue(avisos, "la voz que se pasa del final del video no avisa")

    def test_una_voz_que_cabe_no_avisa_del_final(self):
        texto = "Una frase corta."
        est = estimar_duracion(texto)
        plan = {"duracion": est * 4,
                "escenas": [{"tipo": "final", "from": 0.0, "to": est * 4, "voz": texto}]}
        avisos = [h for h in AP.auditar_estructura(plan)
                  if h["nivel"] == "AVISO" and "final del video" in h["msg"]]
        self.assertFalse(avisos, "una voz que cabe no avisa del final del video")


if __name__ == "__main__":
    unittest.main()
