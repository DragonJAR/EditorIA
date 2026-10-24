#!/usr/bin/env python3
"""Tests de _comandos_copiables.py — el comando de la prosa, copiado, funciona.

Este guard existe porque `parse_args` NO puede ver un defecto: `verificar_ritmo.py
plan.json` es un comando perfectamente valido para argparse (el posicional se
llama `video`, pero `plan.json` es una cadena) y revienta mas tarde, cuando
ya no hay nadie mirando. El guard lo COPIA y lo CORRE con assets reales, y
juzga si lo que fallo es un veredicto de la herramienta o el comando roto.

Los tests de aqui comprueban las dos mitades:

  · que el guard CORTO lo que tiene que cortar (mutacion): un comando roto
    tiene que salir como problema, no como un "0 problemas" tranquilo.
  · que el guard NO se equivoca: un comando bueno no puede salir como roto,
    y lo que no se puede juzgar se SALTA y se cuenta, nunca se disimula.

Y la regla que las dos mitades comparten: una guarda que nunca ha fallado es
una hipotesis. El arnes de mutaciones es lo que la convierte en hecho.
"""

import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
BASE = os.path.dirname(SCRIPTS)
GUARD = os.path.join(SCRIPTS, "_comandos_copiables.py")


class TestComandosCopiables(unittest.TestCase):
    """El guard: copia, corre y juzga."""

    def _guard(self):
        sys.path.insert(0, SCRIPTS)
        try:
            import _comandos_copiables as cc
        finally:
            sys.path.pop(0)
        return cc

    def test_corta_un_comando_roto(self):
        """MUTACION: un comando documentado con el argumento equivocado tiene
        que salir como problema. Este es el defecto real que motivo el guard:
        `verificar_ritmo.py plan.json` (el plan donde va el video) revienta
        con "ffmpeg no pudo leer"."""
        cc = self._guard()
        problemas, _ = cc.verificar(
            BASE, comandos=["scripts/verificar_ritmo.py plan.json"])
        self.assertTrue(problemas,
                        "el guard no vio un comando roto: "
                        "la prosa podia mandar un plan donde va el video")
        self.assertTrue(any("no pudo leer" in p for p in problemas),
                        f"el motivo no es el del defecto: {problemas}")

    def test_no_corta_un_comando_bueno(self):
        """El guard no puede acusar de roto lo que funciona: un falso positivo
        es tan malo como un falso negativo, porque teaches a ignorar el
        guard."""
        cc = self._guard()
        problemas, informe = cc.verificar(
            BASE, comandos=["scripts/auditar_plan.py plan.json"])
        self.assertEqual(problemas, [],
                         f"el guard acuso a un comando sano: {problemas}")
        self.assertEqual(informe["copiados"], 1,
                         "el comando no se copio: el guard no miró lo que dice")

    def test_lo_que_no_se_puede_juzgar_se_salta_y_se_cuenta(self):
        """Un comando que no se puede juzgar se SALTA, y el salto se CUENTA y
        se NOMBRA. Un guard que se salta la mitad sin decirlo es un guard que
        no mira."""
        cc = self._guard()
        problemas, informe = cc.verificar(
            BASE, comandos=["scripts/clonar_video.py analizar --url \"https://x\" -o r"])
        self.assertEqual(problemas, [])
        self.assertEqual(informe["saltados"], 1,
                         f"el salto no se conto: {informe}")
        self.assertTrue(informe["saltados_por_motivo"],
                        "el salto no tiene motivo nombrado: un numero sin "
                        "motivo es un tapon")

    def test_un_script_puede_copiarse_y_aun_asu_tener_un_comando_fuera(self):
        """La unidad es el COMANDO que el agente copia, no el script: el
        mismo `clonar_video.py` tiene `variar` (local, se copia y se ejecuta)
        y `analizar` (baja el video, no se copia)."""
        cc = self._guard()
        self.assertIn("scripts/clonar_video.py", cc.EJECUTABLES,
                      "el camino local de clonar_video tiene que copiarse")
        self.assertIsNone(
            cc._motivo_de('scripts/clonar_video.py variar --plantilla '
                           'plantilla.json --variantes 3 --tema "x"'),
            "el camino local no puede tener motivo de exclusion")
        self.assertIsNotNone(
            cc._motivo_de('scripts/clonar_video.py analizar --url "u" -o d'),
            "el camino que baja el video de la red no puede copiarse")

    def test_la_lista_de_comandos_tiene_que_ser_completa(self):
        """COMPLETA POR COMANDO: cada comando documentado o se copia, o tiene
        el motivo de por que no. Un comando que no se copia y no tiene motivo
        es un puntero a nada."""
        cc = self._guard()
        sys.path.insert(0, SCRIPTS)
        try:
            import _comandos_doc as cd
        finally:
            sys.path.pop(0)
        cmds = cd.comandos_documentados(BASE) + cd.comandos_de_referencias(BASE)
        sin_motivo = []
        for cmd in cmds:
            partes = cd._partir(cmd)
            if not partes:
                continue
            s = partes[0]
            if "/scripts/" in s:
                s = "scripts/" + s.split("/scripts/", 1)[1]
            if s in cc.EJECUTABLES or cc._motivo_de(cmd):
                continue
            sin_motivo.append(cmd)
        self.assertEqual(sin_motivo, [],
                         f"comando documentado sin motivo y sin copia: {sin_motivo}")
        # y ninguna exclusion sin motivo escrito
        for prefijo, (motivo, _) in cc.FUERA.items():
            self.assertTrue(motivo.strip(),
                            f"exclusion sin motivo: {prefijo}")

    def test_el_motivo_es_por_forma_del_comando(self):
        """Un script puede necesitar la red y aun asi tener una forma que solo
        necesita un fichero local. Sin esto, excluir el script entero se lleva
        por delante comandos que si se ejecutan, y la cobertura de una vertical
        se cae sin que nadie lo note."""
        cc = self._guard()
        # la forma local se copia...
        self.assertIsNone(cc._motivo_de('scripts/referencia.py --video clip.mp4'))
        self.assertIsNone(cc._motivo_de('scripts/clonar_video.py analizar --video ref.mp4'))
        self.assertIsNone(cc._motivo_de('scripts/voz_local.py --listar'))
        # ...y la que baja el video de la red, no
        self.assertIsNotNone(cc._motivo_de('scripts/referencia.py --url "u"'))
        self.assertIsNotNone(cc._motivo_de('scripts/clonar_video.py analizar --url "u"'))
        self.assertIsNotNone(cc._motivo_de('scripts/voz_local.py plan.json -o voz.wav'))

    def test_un_comando_que_no_hace_su_trabajo_se_corta(self):
        """Un comando copiado que imprime ERROR no hizo su trabajo: eso se
        corta. Y OJO: esto NO es lo mismo que un veredicto: una puerta que
        rechaza una pieza mala imprime FAIL, y ahi ha hecho su trabajo."""
        cc = self._guard()
        # un ERROR en la salida de un comando copiado: no hizo su trabajo
        self.assertEqual(cc._juzgar("ERROR: el input no tiene stream de audio"),
                         "ERROR:")
        # un veredicto NO es un fallo del comando: una puerta que rechaza una
        # pieza mala ha hecho su trabajo, y ahi el comando funciona
        self.assertIsNone(cc._juzgar("FAIL quietud 0% cuadros quietos (min 25%)"))
        self.assertIsNone(cc._juzgar("WARN rafaga 0 ventana(s)"))
        # y un crash, si

    def test_las_verticales_locales_llegan_a_la_puerta_fuerte(self):
        """La puerta fuerte tiene que LLEGAR a las verticales, no solo a la
        primera. Medido: la vertical de sonido (mezclar_audio) y las dos
        puertas de veredicto (qa_entrega, puntuar) eran los ultimos huecos
        REALES; todo lo demas se salta por la red, una API, Whisper, o porque
        renderiza la pieza entera."""
        cc = self._guard()
        for cli in ("scripts/mezclar_audio.py", "scripts/qa_entrega.py",
                    "scripts/puntuar.py"):
            self.assertIn(cli, cc.EJECUTABLES,
                          f"{cli} no llega a la puerta fuerte: el comando que "
                          f"el agente copia se queda sin ejecutar")
            self.assertNotIn(cli, cc.FUERA,
                             f"{cli} sigue con su motivo de exclusion: el "
                             f"motivo gana sobre la lista de ejecutables")

    def test_el_comando_de_mezclar_se_copia_y_se_ejecuta_de_verdad(self):
        """El comando de la mezcla de sonido, tal cual lo escribe la prosa, se
        COPIA y se EJECUTA: la voz, la musica y el pack de SFX se sintetizan en
        local, asi que el motivo antiguo ("necesita voz, musica y SFX ya
        renderizados") ya no aplica a esta forma."""
        cc = self._guard()
        cmd = ('scripts/mezclar_audio.py plan.json --video out.mp4 --voz voz.mp3 '
               '--voz-palabras voz.palabras.json --grid grid.json '
               '--pack assets/sfx --musica mus.mp3 -o mezclado.mp4')
        problemas, informe = cc.verificar(BASE, comandos=[cmd])
        self.assertEqual(problemas, [],
                         f"el comando de mezclar salio como roto: {problemas}")
        self.assertEqual(informe["copiados"], 1,
                         "el comando de mezclar no se copio")

    def test_la_mutacion_de_la_cobertura_la_caza(self):
        """MUTACION: si la vertical de sonido vuelve a quedar fuera de la puerta
        fuerte, este guard tiene que notarlo. Se muta una COPIA del modulo (el
        original no se toca) quitando el script de la lista de ejecutables, y
        se comprueba que la copia ya NO lo tiene: si la mutacion no se aplica,
        no prueba nada."""
        cc = self._guard()
        self.assertIn("scripts/mezclar_audio.py", cc.EJECUTABLES,
                      "el original ya no llega: la mutacion no mide nada")
        with open(GUARD, encoding="utf-8") as fh:
            fuente = fh.read()
        linea = '    "scripts/mezclar_audio.py",\n'
        self.assertIn(linea, fuente,
                      "el modulo ya no tiene la linea que se va a mutar")
        tmp = tempfile.mkdtemp(prefix="editoria_mut_")
        try:
            ruta = os.path.join(tmp, "mutado.py")
            with open(ruta, "w", encoding="utf-8") as fh:
                fh.write(fuente.replace(linea, "", 1))
            import importlib.util
            spec = importlib.util.spec_from_file_location("mutado_guard", ruta)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            self.assertNotIn("scripts/mezclar_audio.py", mod.EJECUTABLES,
                             "la mutacion no se aplico: no prueba nada")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_la_salida_no_se_escribe_sobre_la_entrada(self):
        """El valor de -o (y de las otras banderas de salida) va a un sitio de
        raspado. Si se sustituyera por el asset de entrada, el comando
        escribiria encima de lo que lee."""
        cc = self._guard()
        tmp = tempfile.mkdtemp(prefix="editoria_salida_")
        try:
            assets = cc._assets(tmp, BASE)
            sys.path.insert(0, SCRIPTS)
            try:
                import _comandos_doc as cd
            finally:
                sys.path.pop(0)
            partes = cd._partir("scripts/ffmpeg_tools/loudness.py in.mp4 "
                                "-o out.mp4 -I -14 --tp -1.5")
            nuevas, ok = cc._sustituir(partes[1:], assets,
                                        scratch=os.path.join(tmp, "cwd"))
            self.assertTrue(ok)
            self.assertNotEqual(nuevas[0], nuevas[2],
                                 "la salida es el mismo fichero que la entrada")
            self.assertIn("-I", nuevas, f"se perdio una bandera: {nuevas}")
            self.assertIn("-14", nuevas, f"se perdio un valor: {nuevas}")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_la_plantilla_de_ejemplo_produce_un_plan_real(self):
        """La plantilla que el guard usa no es un cascaron: `variar` tiene que
        salir con planes de verdad, con escenas del catalogo y la voz dentro.
        Es la cobertura de la vertical de clonar: un comando que el agente
        copia, EJECUTADO de verdad."""
        cc = self._guard()
        tmp = tempfile.mkdtemp(prefix="editoria_plantilla_")
        try:
            assets = cc._assets(tmp, BASE)
            p = subprocess.run(
                [sys.executable, os.path.join(SCRIPTS, "clonar_video.py"),
                 "variar", "--plantilla", assets["plantilla"],
                 "--variantes", "2", "--tema", "Prueba"],
                capture_output=True, text=True, timeout=300, cwd=tmp)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            planes = sorted(glob.glob(os.path.join(tmp, "variantes", "*", "plan.json")))
            self.assertEqual(len(planes), 2,
                             f"no salieron los 2 planes: {p.stdout}{p.stderr}")
            with open(planes[0], encoding="utf-8") as fh:
                plan = json.load(fh)
            self.assertTrue(plan.get("escenas"), "el plan salio vacio")
            for e in plan["escenas"]:
                self.assertIn("voz", e, "una escena sin voz: el plan no se audito")
                self.assertIn("tipo", e, "una escena sin tipo del catalogo")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_la_cli_del_guard_se_puede_correr(self):
        """El guard tiene que ser una CLI de verdad, no un modulo: se ejecuta
        como proceso, y su `--solo` deja mirar UN comando sin correrlos
        todos. Asi el censo lo mide como lo que es: algo que se EJECUTA (y no
        como un nombre importado, que es lo mismo que no medir nada)."""
        p = subprocess.run(
            [sys.executable, GUARD, "--solo", "verificar_ritmo", "--json"],
            capture_output=True, text=True, timeout=300)
        self.assertEqual(p.returncode, 0, f"el guard fallo: {p.stderr[-500:]}")
        datos = json.loads(p.stdout)
        self.assertEqual(datos["problemas"], [],
                         f"el guard acuso a un comando sano: {datos['problemas']}")
        self.assertGreater(datos["informe"]["copiados"], 0,
                           "el guard no copio ningun comando")

    def test_el_guard_no_escribe_dentro_de_la_skill(self):
        """Un guard que modifica lo que vigila no es un guard. Ninguna CLI que
        el guard copia escribe dentro de la skill."""
        cc = self._guard()
        for cli in cc.EJECUTABLES:
            self.assertNotIn("registrar_aprendizaje", cli,
                             "registrar_aprendizaje escribe en la skill")
        ruta = os.path.join(BASE, "scripts", "registrar_aprendizaje.py")
        with open(ruta, encoding="utf-8") as fh:
            texto = fh.read()
        self.assertIn("references/", texto,
                      "el script ya no escribe en la skill: revisa el motivo "
                      "de la exclusion antes de tocar nada")


if __name__ == "__main__":
    unittest.main()
