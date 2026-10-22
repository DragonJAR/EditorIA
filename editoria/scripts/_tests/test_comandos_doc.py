#!/usr/bin/env python3
"""Tests de _comandos_doc.py — lo que la doc promete se puede correr.

La skill le pide al agente comandos literales. Si uno le falta un argumento
obligatorio, el agente se para con un error que no esta en la doc. Este test
rompe la doc de tres maneras concretas y comprueba que las detecta.

Cada test verifica UN comando: el barrido completo de los 35 comandos del
SKILL.md tarda minutos (un subproceso por comando) y vive en
`scripts/validate_skill.py`, que es donde tiene que estar.

Run with: python3 -m unittest discover -s SKILL/scripts/_tests
"""

import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
BASE = os.path.dirname(SCRIPTS)
sys.path.insert(0, SCRIPTS)

import _comandos_doc as CD   # noqa: E402

# un comando corto de la doc: sirve de referencia y de caso bueno
CMDS = "scripts/contact_sheet.py --video fuente.mp4 -o hoja.png"


class TestComandosDoc(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="editoria_comandos_")
        self.addCleanup(shutil.rmtree, self.dir, True)
        shutil.copytree(os.path.join(BASE, "references"),
                        os.path.join(self.dir, "references"))
        shutil.copytree(os.path.join(BASE, "scripts"),
                        os.path.join(self.dir, "scripts"),
                        ignore=shutil.ignore_patterns("__pycache__"))
        with open(os.path.join(BASE, "SKILL.md"), encoding="utf-8") as f:
            self.skill = f.read()
        self.ruta = os.path.join(self.dir, "SKILL.md")

    def _escribir(self, txt):
        with open(self.ruta, "w", encoding="utf-8") as f:
            f.write(txt)

    def test_el_comando_de_la_doc_esta_bien(self):
        self._escribir(self.skill + f"\n```bash\npython {CMDS}\n```\n")
        problemas = CD.verificar_comando(self.dir, CMDS)
        self.assertEqual(problemas, [], "\n".join(problemas))

    def test_detecta_que_falta_un_argumento_obligatorio(self):
        roto = "scripts/contact_sheet.py --video fuente.mp4"
        self._escribir(self.skill + f"\n```bash\npython {roto}\n```\n")
        problemas = CD.verificar_comando(self.dir, roto)
        self.assertTrue(problemas)
        self.assertIn("salida", problemas[0])

    def test_detecta_un_flag_que_no_existe(self):
        roto = "scripts/contact_sheet.py --video fuente.mp4 -o hoja.png --flag-inventado 3"
        self._escribir(self.skill + f"\n```bash\npython {roto}\n```\n")
        problemas = CD.verificar_comando(self.dir, roto)
        self.assertTrue(problemas)

    def test_une_las_lineas_continuadas(self):
        # un comando partido con barra invertida es UN comando: sin esto se
        # comprobaria sin su -o y saldria un fallo falso
        partido = "scripts/contact_sheet.py --video fuente.mp4 \\\n  -o hoja.png"
        self._escribir(self.skill + f"\n```bash\npython {partido}\n```\n")
        comandos = CD.comandos_documentados(self.dir)
        self.assertIn("scripts/contact_sheet.py --video fuente.mp4 -o hoja.png", comandos)
        problemas = CD.verificar_comando(
            self.dir, "scripts/contact_sheet.py --video fuente.mp4 -o hoja.png")
        self.assertEqual(problemas, [], "\n".join(problemas))

    def test_el_script_que_no_existe_es_un_problema(self):
        # la ruta se arma en runtime: escrita literal, el auditor de enlaces
        # del mapa la tomaria por un enlace roto a un archivo real
        fantasma = "scripts/" + "no_existe.py"
        problemas = CD.verificar_comando(self.dir, fantasma + " -o x")
        self.assertTrue(problemas)

    def test_los_readme_tambien_se_verifican(self):
        """Los README son la puerta de entrada del proyecto: sus comandos
        se copian tal cual, asi que tambien tienen que ser ejecutables."""
        if not self._hay_readme_del_repo():
            self.skipTest("este arbol no tiene los README del repo (copia instalada)")
        cmds = CD.comandos_de_readme(BASE)
        self.assertTrue(cmds, "los README deberian documentar comandos")
        for cmd in cmds:
            problemas = CD.verificar_comando(BASE, cmd)
            self.assertEqual(problemas, [], "\n".join(problemas))

    def _hay_readme_del_repo(self):
        """Los README viven un nivel arriba de la skill: en el repo estan, en
        la copia instalada no. Ahi no hay nada que verificar."""
        return os.path.isfile(os.path.join(os.path.dirname(BASE), "README.md"))

    def test_un_comando_roto_en_el_readme_se_detecta(self):
        # se mete un comando roto en una copia del README y se comprueba
        if not self._hay_readme_del_repo():
            self.skipTest("este arbol no tiene los README del repo (copia instalada)")
        raiz = os.path.dirname(BASE)
        ruta = os.path.join(raiz, "README.md")
        with open(ruta, encoding="utf-8") as f:
            original = f.read()
        try:
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(original + "\n```bash\npython scripts/auto_qa.py final.mp4 "
                                   "--flag-que-no-existe\n```\n")
            cmds = CD.comandos_de_readme(BASE)
            roto = [c for c in cmds if "--flag-que-no-existe" in c]
            self.assertTrue(roto, "el comando roto deberia detectarse en la lista")
            problemas = CD.verificar_comando(BASE, roto[0])
            self.assertTrue(problemas)
        finally:
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(original)


if __name__ == "__main__":
    unittest.main()
