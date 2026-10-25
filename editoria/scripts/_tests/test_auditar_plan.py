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
import speech_estimate as SE  # noqa: E402
from speech_estimate import estimar_duracion  # noqa: E402


def _plan(**extra):
    plan = {"duracion": 3.0,
            "escenas": [{"tipo": "apertura", "from": 0, "to": 3, "texto1": ["Hola"]}]}
    plan.update(extra)
    return plan


class TestCadenciaYRepertorio(unittest.TestCase):
    """La cadencia narrada se declara; el poco repertorio se avisa."""

    TIPOS = ["apertura", "bento", "stats", "pasos", "versus", "final",
             "remate", "quote", "index", "hero", "bars", "pie"]

    def _plan(self, tipos, con_voz=False, dur=5.0):
        escenas = []
        for i, tipo in enumerate(tipos):
            e = {"tipo": tipo, "from": i * dur, "to": (i + 1) * dur, "titulo": "Dato"}
            if con_voz:
                e["voz"] = "Una frase corta."
            escenas.append(e)
        return {"duracion": dur * len(tipos), "escenas": escenas}

    def _avisos(self, plan, codigo):
        return [h["msg"] for h in AP.auditar_tells(plan)
                if h.get("codigo") == codigo]

    def test_cadencia_con_voz_dice_como_declararla(self):
        plan = self._plan(self.TIPOS[:6], con_voz=True)
        msgs = self._avisos(plan, "cadencia-uniforme")
        self.assertTrue(msgs)
        self.assertIn("tells_ok", msgs[0])
        self.assertIn("voz", msgs[0])

    def test_poco_repertorio_avisa(self):
        plan = self._plan(["bento"] * 4 + ["stats"] * 4)
        self.assertTrue(self._avisos(plan, "poco-repertorio"))

    def test_repertorio_variado_no_avisa(self):
        plan = self._plan(self.TIPOS[:8])
        self.assertFalse(self._avisos(plan, "poco-repertorio"))

    def test_poco_repertorio_se_puede_declarar(self):
        plan = self._plan(["bento"] * 8)
        plan["tells_ok"] = ["poco-repertorio"]
        self.assertFalse(self._avisos(plan, "poco-repertorio"))


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


class TestUnPlanSinEscenasNoEsUnaPieza(unittest.TestCase):
    """Un plan sin escenas no pasa la auditoria.

    Todos los chequeos de estructura viven dentro de bucles sobre las escenas,
    asi que con cero escenas el plan pasaba entero ("PLAN VALIDO: 0 escenas
    auditadas") y el motor reventaba despues con un IndexError sin mensaje.
    Un guard que no mira nada no puede decir "todo bien"."""

    def test_un_plan_sin_escenas_es_error(self):
        plan = {"duracion": 30.0, "escenas": []}
        hallazgos = AP.auditar_estructura(plan)
        errores = [h for h in hallazgos if h["nivel"] == "ERROR"]
        self.assertTrue(errores, "un plan sin escenas tiene que ser un ERROR")
        self.assertIn("no tiene escenas", errores[0]["msg"])

    def test_el_plan_vacio_no_pasa_la_auditoria(self):
        # y por la puerta de verdad (la CLI), que es como lo ve el agente
        import json
        import subprocess
        import tempfile
        d = tempfile.mkdtemp()
        ruta = os.path.join(d, "vacio.json")
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump({"duracion": 30.0, "escenas": []}, f)
        r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "auditar_plan.py"), ruta],
                           capture_output=True, text=True, timeout=120)
        self.assertNotEqual(r.returncode, 0,
                            "un plan sin escenas no puede salir con codigo 0")
        self.assertIn("no tiene escenas", (r.stdout or "") + (r.stderr or ""))


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
        se corta contra el borde. Si el exceso sale de la banda de error de
        la estimacion, el corte es PROVABLE y es ERROR; si no, es un aviso
        (la estimacion no puede probarlo: quien falla es el TTS real)."""
        texto = "Esta frase es deliberadamente larguisima para ocupar mucho tiempo de reloj."
        est = estimar_duracion(texto)
        # el video dura casi lo que la voz: el exceso es pequeno -> aviso
        plan = {"duracion": est * 0.95,
                "escenas": [{"tipo": "final", "from": 0.0, "to": est * 0.95, "voz": texto}]}
        avisos = [h for h in AP.auditar_estructura(plan)
                  if h["nivel"] == "AVISO" and "final del video" in h["msg"]]
        self.assertTrue(avisos, "la voz que se pasa del final del video no avisa")

    def test_una_voz_que_se_pasa_muy_por_encima_del_final_es_error(self):
        """Si el exceso es mayor que la banda de error de la estimacion, el
        corte no se puede negar: es un ERROR, no un aviso."""
        texto = "Esta frase es deliberadamente larguisima para ocupar mucho tiempo de reloj."
        est = estimar_duracion(texto)
        plan = {"duracion": est * 0.5,
                "escenas": [{"tipo": "final", "from": 0.0, "to": est * 0.5, "voz": texto}]}
        errores = [h for h in AP.auditar_estructura(plan)
                   if h["nivel"] == "ERROR" and "final del video" in h["msg"]]
        self.assertTrue(errores, "una voz que se pasa muy por encima del final no es error")

    def test_una_voz_que_cabe_no_avisa_del_final(self):
        texto = "Una frase corta."
        est = estimar_duracion(texto)
        plan = {"duracion": est * 4,
                "escenas": [{"tipo": "final", "from": 0.0, "to": est * 4, "voz": texto}]}
        avisos = [h for h in AP.auditar_estructura(plan)
                  if h["nivel"] == "AVISO" and "final del video" in h["msg"]]
        self.assertFalse(avisos, "una voz que cabe no avisa del final del video")


class TestUnaSolaRegla(unittest.TestCase):
    """La regla del reloj de la voz, en UN solo sitio.

    `auditar_plan.py` (el plan) y `speech_estimate.auditar_plan_voces` (lo
    usa `clonar_video.py`)SON la misma regla: la voz no puede pisar a la voz
    siguiente ni el final del video. Antes cada una tenia la suya: una
    media contra la voz siguiente y la otra exigia que la voz terminase
    DENTRO de su propia escena (mas estricto que el resto de la skill), y
    se contradecian en los 10 planes de la demo (una decia "cabe" y la otra
    "no cabe", cuando la narracion real si cabia).

    Este test es el que habria atrapado esa isla."""

    def _planes(self):
        # 1. la voz cruza el final de su escena pero no pisa a la siguiente
        yield ("cabe aunque cruce su escena", {
            "duracion": 12.0,
            "escenas": [
                {"tipo": "apertura", "from": 0.0, "to": 3.0,
                 "voz": "Una voz bastante larga que se pasa de su escena."},
                {"tipo": "final", "from": 4.0, "to": 12.0, "voz": "Corta."}]})
        # 2. la voz pisa a la siguiente
        yield ("pisa a la siguiente", {
            "duracion": 12.0,
            "escenas": [
                {"tipo": "apertura", "from": 0.0, "to": 3.0,
                 "voz": "Esta voz es tan larga que no hay manera de que quepa antes de que empiece la voz que viene despues."},
                {"tipo": "final", "from": 4.0, "to": 12.0, "voz": "Corta."}]})
        # 3. la ultima voz se pasa del final del video
        yield ("se pasa del final del video", {
            "duracion": 4.0,
            "escenas": [
                {"tipo": "final", "from": 0.0, "to": 4.0,
                 "voz": "Una voz deliberadamente larguisima que no cabe de ninguna manera."}]})

    def test_las_dos_herramientas_dicen_lo_mismo(self):
        for nombre, plan in self._planes():
            se = SE.auditar_plan_voces(plan)
            errores_voz = [h for h in AP.auditar_estructura(plan)
                           if h["nivel"] == "ERROR" and "voz" in h["msg"]]
            self.assertEqual(
                se["valido"], not errores_voz,
                f"'{nombre}': auditar_plan_voces dice {se['valido']} y "
                f"auditar_plan dice {not errores_voz}. Son la misma regla.")


if __name__ == "__main__":
    unittest.main()
