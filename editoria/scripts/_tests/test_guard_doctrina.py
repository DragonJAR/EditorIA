#!/usr/bin/env python3
"""Tests del guard de prosa (doctrina de las capacidades).

La doctrina de la skill (`references/capacidades.md`) es que una capacidad
externa no es un requisito del motor pero SI puede ser necesaria para que
la pieza salga como tiene que salir: cuando falta, se DECLARA al usuario con
su comando. La palabra que significa "no hace falta" no puede volver a
colarse pegada a una capacidad, porque esa palabra es un motivo para
entregar menos en silencio.

Un guard que no encuentra su objeto no prueba nada, asi que el primer test
mete una frase rota en un arbol temporal y exige que se caiga.

Run with: python3 -m unittest discover -s SKILL/scripts/_tests
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
BASE = os.path.dirname(SCRIPTS)
GUARD = os.path.join(SCRIPTS, "_guard_doctrina.py")

#: La carpeta de los fixtures se arma en runtime, no escrita aqui: el guard
#: de enlaces lee tambien los .py, y una ruta de ejemplo que no existe de
#: verdad es un enlace roto (el que la lea buscara un fichero que no esta).
CARPETA = "referen" + "ces"

sys.path.insert(0, SCRIPTS)
import _guard_doctrina as G  # noqa: E402


class GuardDoctrina(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="editoria_doctrina_")
        self.addCleanup(shutil.rmtree, self.dir, True)

    def _escribir(self, rel, texto):
        ruta = os.path.join(self.dir, rel)
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, "w", encoding="utf-8") as fh:
            fh.write(texto)
        return ruta

    # --- la mutacion: la frase rota tiene que caer -------------------------

    def test_una_frase_rota_se_cae(self):
        """La MUTACION: si el guard no encuentra la frase rota, no prueba nada."""
        self._escribir(f"{CARPETA}/rota.md",
                       "El motor funciona sin el.\n"
                       "Remotion es opcional para cualquier pieza.\n")
        faltas = G.violaciones(self.dir)
        self.assertEqual(len(faltas), 1,
                         f"la frase rota tiene que caer (encontradas: {faltas})")
        self.assertEqual(faltas[0][0], f"{CARPETA}/rota.md")
        self.assertIn("Remotion", faltas[0][2])

    def test_el_sustantivo_de_capacidad_tambien_cae(self):
        """La misma falta sin nombrar la capacidad: "los motores ..."."""
        self._escribir(f"{CARPETA}/rota2.md",
                       "`remotion.md` y `hyperframes.md` cubren los motores "
                       "opcionales.\n")
        faltas = G.violaciones(self.dir)
        self.assertEqual(len(faltas), 1,
                         f"una capacidad sin nombre propio tambien cae (encontradas: {faltas})")

    def test_la_cli_devuelve_codigo_de_error_con_la_frase_rota(self):
        """La puerta tiene que poder FALLAR, no solo informar."""
        self._escribir(f"{CARPETA}/rota3.md", "Blender es opcional.\n")
        r = subprocess.run([sys.executable, GUARD, "--base", self.dir],
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 1,
                         f"con una frase rota la CLI tiene que salir con 1 (salio {r.returncode})")
        self.assertIn("rota3.md", r.stdout,
                      "la salida tiene que nombrar el fichero roto")

    # --- lo que NO es una falta --------------------------------------------

    def test_la_doctrina_dicha_no_es_una_falta(self):
        """Decir que NO es opcional es la doctrina: no puede marcarse."""
        self._escribir(f"{CARPETA}/buena.md",
                       "Las capacidades no son opcionales: se declaran.\n"
                       "El motor no lo necesita, y eso no significa que la pieza "
                       "no lo necesite.\n")
        self.assertEqual(G.violaciones(self.dir), [],
                         "la doctrina escrita como negacion no es una falta")

    def test_un_campo_del_plan_puede_ser_opcional(self):
        """El campo `voz` es un campo: opcional de verdad."""
        self._escribir(f"{CARPETA}/campo.md",
                       "El campo `voz` es opcional: si no viene, se usa la voz "
                       "del sistema.\n")
        self.assertEqual(G.violaciones(self.dir), [],
                         "un campo del plan puede ser opcional de verdad")

    def test_una_herramienta_ajena_no_es_la_capacidad(self):
        """Whisper cerca de un dato opcional no es una falta."""
        self._escribir(f"{CARPETA}/ajena.md",
                       "alinear.py, Whisper/WhisperX, con hablante opcional) -> "
                       "cues con karaoke\n")
        self.assertEqual(G.violaciones(self.dir), [],
                         "una palabra opcional que no califica a la capacidad no es una falta")

    # --- el arbol real ------------------------------------------------------

    def test_la_skill_real_no_tiene_faltas(self):
        """La skill de verdad no puede tener ninguna."""
        faltas = G.violaciones(BASE)
        self.assertEqual(faltas, [],
                         f"la prosa de la skill tiene faltas de doctrina: {faltas[:5]}")

    def test_el_guard_no_se_marca_a_si_mismo(self):
        """El fuente del guard contiene la palabra: no puede marcarse."""
        with open(GUARD, encoding="utf-8") as fh:
            texto = fh.read()
        faltas = G.violaciones(self.dir)
        self.assertEqual(faltas, [])
        self._escribir("scripts/_guard_doctrina.py", texto)
        self.assertEqual(G.violaciones(self.dir), [],
                         "el guard no puede senalar su propio fuente")

    def test_la_cli_sobre_la_skill_real_pasa(self):
        """Y la CLI, tal cual la ejecutaria un agente, sale con 0."""
        r = subprocess.run([sys.executable, GUARD, "--base", BASE],
                           capture_output=True, text=True, timeout=300)
        self.assertEqual(r.returncode, 0,
                         f"la CLI tiene que pasar sobre la skill real (salio {r.returncode}):\n"
                         f"{r.stdout}\n{r.stderr}")


if __name__ == "__main__":
    unittest.main()
