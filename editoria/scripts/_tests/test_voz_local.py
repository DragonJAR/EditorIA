#!/usr/bin/env python3
"""Tests de voz_local.py — la voz en off con la voz del sistema (sin API).

Por que existe este archivo: la receta de TTS local estaba escrita en prosa
("coloca cada frase en su instante sobre una pista continua de silencio") sin
que NINGUNA herramienta lo hiciera. El camino local era una isla: la demo
sintetizaba su voz con un script propio, el plan no declaraba 'voz' y la
puerta no podia ver el reloj de la narracion (10 de 10 videos con la frase
cortada). `voz_local.py` cierra la isla: mismo contrato que `voz_off.py`,
misma regla de reloj, y la voz que se elige es la que hay instalada.

Run with: python3 -m unittest discover -s SKILL/scripts/_tests
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)

import voz_local as VL  # noqa: E402

# Una muestra real de `say -v ?`: los nombres pueden llevar espacios y
# parentesis ("Eddy (Español (España))"), y el locale va despues.
MUESTRA_SAY = """Albert              en_US    # Hello! My name is Albert.
Mónica              es_ES    # ¡Hola! Me llamo Mónica.
Paulina             es_MX    # ¡Hola! Me llamo Paulina.
Eddy (Español (España)) es_ES    # ¡Hola! Me llamo Eddy.
Flo (Español (México)) es_MX    # ¡Hola! Me llamo Flo.
"""


class TestParseoDeVoces(unittest.TestCase):
    """El nombre de la voz es lo que se le pasa a `say -v`: hay que leerlo
    entero, con sus espacios y sus parentesis."""

    def test_parsea_nombre_con_parentesis(self):
        voces = VL.parse_voces_say(MUESTRA_SAY)
        nombres = [v["nombre"] for v in voces]
        self.assertIn("Eddy (Español (España))", nombres)
        self.assertIn("Flo (Español (México))", nombres)

    def test_el_locale_y_el_idioma(self):
        voces = {v["nombre"]: v for v in VL.parse_voces_say(MUESTRA_SAY)}
        self.assertEqual(voces["Paulina"]["locale"], "es_MX")
        self.assertEqual(voces["Paulina"]["idioma"], "es")
        self.assertEqual(voces["Albert"]["idioma"], "en")

    def test_una_linea_rara_no_inventa_una_voz(self):
        voces = VL.parse_voces_say("esto no es una voz\nMónica  es_ES  # hola")
        self.assertEqual(len(voces), 1)
        self.assertEqual(voces[0]["nombre"], "Mónica")


class TestEleccionDeVoz(unittest.TestCase):
    """La voz se elige entre las INSTALADAS: si no hay ninguna del idioma
    pedido, el script falla en voz alta (no degrada en silencio)."""

    def setUp(self):
        self.voces = VL.parse_voces_say(MUESTRA_SAY)

    def test_por_nombre_exacto(self):
        v = VL.elegir_voz(self.voces, "say", "es", "Paulina")
        self.assertEqual(v["nombre"], "Paulina")

    def test_por_nombre_sin_distinguir_mayusculas(self):
        v = VL.elegir_voz(self.voces, "say", "es", "paulina")
        self.assertEqual(v["nombre"], "Paulina")

    def test_por_locale(self):
        v = VL.elegir_voz(self.voces, "say", "es", "es_MX")
        self.assertEqual(v["nombre"], "Paulina")

    def test_sin_pedir_usa_la_preferida_del_idioma(self):
        v = VL.elegir_voz(self.voces, "say", "es", None)
        self.assertEqual(v["nombre"], "Mónica")     # la primera de PREFERIDAS
        v_en = VL.elegir_voz(self.voces, "say", "en", None)
        self.assertEqual(v_en["idioma"], "en")

    def test_una_voz_que_no_existe_no_se_inventa(self):
        self.assertIsNone(VL.elegir_voz(self.voces, "say", "es", "Paulina X"))

    def test_sin_voz_del_idioma_no_hay_elegida(self):
        voces = VL.parse_voces_say("Albert              en_US    # Hello!\n")
        self.assertIsNone(VL.elegir_voz(voces, "say", "es", None))
        self.assertEqual(VL.voz_por_idioma(voces, "say", "es"), [])


class TestCache(unittest.TestCase):
    """El mismo texto+voz+velocidad reusa el wav (content-addressing)."""

    def test_mismo_contenido_misma_ruta(self):
        a = VL.cache_path("hola", "Paulina", 178, "say")
        b = VL.cache_path("hola", "Paulina", 178, "say")
        self.assertEqual(a, b)

    def test_voz_o_velocidad_distintas_otra_ruta(self):
        base = VL.cache_path("hola", "Paulina", 178, "say")
        self.assertNotEqual(base, VL.cache_path("hola", "Mónica", 178, "say"))
        self.assertNotEqual(base, VL.cache_path("hola", "Paulina", 200, "say"))
        self.assertNotEqual(base, VL.cache_path("otro", "Paulina", 178, "say"))


class TestContratoDeLaCLI(unittest.TestCase):
    """La CLI se aprende por --help: una opcion sin texto es una opcion que
    se adivina. Y ningun fallo puede salir como traceback."""

    def _correr(self, args):
        return subprocess.run([sys.executable, os.path.join(SCRIPTS, "voz_local.py")] + args,
                              capture_output=True, text=True, timeout=120)

    def test_help_no_es_traceback(self):
        r = self._correr(["--help"])
        self.assertEqual(r.returncode, 0)
        self.assertNotIn("Traceback", r.stderr)
        self.assertIn("--permitir-otro-idioma", r.stdout)

    def test_sin_plan_falla_limpido(self):
        r = self._correr([])
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn("Traceback", r.stderr)
        self.assertIn("plan", (r.stdout + r.stderr).lower())

    def test_un_plan_sin_voz_falla_limpido(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump({"duracion": 5.0, "escenas": [{"tipo": "apertura", "from": 0, "to": 5,
                                                     "texto1": ["Hola"]}]}, fh)
            ruta = fh.name
        try:
            r = self._correr([ruta, "-o", os.path.join(tempfile.gettempdir(), "nope.wav")])
            self.assertNotEqual(r.returncode, 0)
            self.assertNotIn("Traceback", r.stderr)
            self.assertIn("voz", (r.stdout + r.stderr).lower())
        finally:
            os.unlink(ruta)


@unittest.skipUnless(shutil.which("say"), "no hay motor de voz del sistema en esta maquina")
class TestConAudioReal(unittest.TestCase):
    """Con `say` de verdad: la sintesis, el guion y el reloj."""

    def _plan(self, frases):
        escenas = []
        t = 0.0
        for i, f in enumerate(frases):
            escenas.append({"tipo": "apertura", "from": t, "to": t + 5.0, "voz": f})
            t += 5.0
        return {"duracion": t, "escenas": escenas}

    def test_sintetiza_y_escribe_el_guion(self):
        d = tempfile.mkdtemp()
        plan = os.path.join(d, "plan.json")
        guion = os.path.join(d, "guion.txt")
        with open(plan, "w", encoding="utf-8") as fh:
            json.dump(self._plan(["Primera frase de prueba."]), fh)
        wav = os.path.join(d, "voz.wav")
        r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "voz_local.py"),
                            plan, "-o", wav, "--guion", guion, "--voz", "Paulina"],
                           capture_output=True, text=True, timeout=300)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(os.path.exists(wav))
        self.assertGreater(os.path.getsize(wav), 1000)
        # el guion hablado: sin tags de direccion
        with open(guion, encoding="utf-8") as fh:
            self.assertIn("Primera frase", fh.read())
        # el wav de verdad (no un AIFF con nombre de wav)
        with open(wav, "rb") as fh:
            self.assertEqual(fh.read(4), b"RIFF")
            fh.seek(8)
            self.assertEqual(fh.read(4), b"WAVE")

    def test_el_reloj_falla_si_las_voces_se_pisan(self):
        """La narracion manda el reloj: dos voces a la vez es un ERROR."""
        d = tempfile.mkdtemp()
        # dos frases de 5 s en escenas de 5 s: la segunda entra justo cuando
        # la primera termina, pero cada una dura mas de su escena.
        plan = {"duracion": 10.0, "escenas": [
            {"tipo": "apertura", "from": 0.0, "to": 5.0,
             "voz": "Esta frase es deliberadamente muy larga para ocupar mas de cinco segundos de reloj."},
            {"tipo": "bento", "from": 5.0, "to": 10.0,
             "voz": "Esta segunda frase tambien es muy larga y se solapa con la anterior sin duda."},
        ]}
        ruta = os.path.join(d, "plan.json")
        with open(ruta, "w", encoding="utf-8") as fh:
            json.dump(plan, fh)
        r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "voz_local.py"),
                            ruta, "-o", os.path.join(d, "voz.wav"), "--voz", "Paulina"],
                           capture_output=True, text=True, timeout=300)
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn("Traceback", r.stderr)
        self.assertIn("solapadas", (r.stdout + r.stderr).lower())


class TestFinDelVideo(unittest.TestCase):
    """La voz que se pasa del FINAL DEL VIDEO se corta contra el borde.

    Es el unico desborde que no es un aviso: la voz puede continuar sobre la
    siguiente imagen (eso es normal), pero sobre el final del video no hay
    nada que la tape. Antes solo era un AVISO en las dos herramientas, asi
    que un plan escrito asi pasaba la puerta en verde: el defecto que
    tenian las 10 piezas de la demo."""

    def _wav(self, segundos=2.0):
        d = tempfile.mkdtemp()
        ruta = os.path.join(d, "f.wav")
        with wave.open(ruta, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(44100)
            w.writeframes(b"\x00\x00" * int(44100 * segundos))
        return ruta

    def test_una_voz_que_termina_despues_del_video_falla(self):
        wav = self._wav(2.0)
        # la voz entra en 1.5 s y dura 2 s: termina en 3.5 s; el video dura 3
        segs = [(wav, 1500, {"tipo": "final", "from": 1.0, "to": 3.0})]
        with self.assertRaises(SystemExit) as ctx:
            VL.verificar_reloj(segs, duracion_video=3.0)
        self.assertIn("corta", str(ctx.exception).lower())

    def test_una_voz_que_termina_antes_del_video_pasa(self):
        wav = self._wav(2.0)
        segs = [(wav, 1500, {"tipo": "final", "from": 1.0, "to": 3.0})]
        # 1.5 + 2 = 3.5 s de voz, el video dura 4 s: cabe
        VL.verificar_reloj(segs, duracion_video=4.0)

    def test_sin_duracion_no_se_comprueba(self):
        """Sin el dato no se puede afirmar nada: no se inventa un fallo."""
        wav = self._wav(2.0)
        segs = [(wav, 1500, {"tipo": "final", "from": 1.0, "to": 3.0})]
        VL.verificar_reloj(segs)


if __name__ == "__main__":
    unittest.main()
