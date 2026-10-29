#!/usr/bin/env python3
"""Tests del repertorio talking-head (claude-video-effects destilado).

QUE PROTEGE

1. El JSON tiene exactamente 45 efectos saneados (validar()).
2. La entrada desde SKILL.md / mapa / animacion.md §0 / capacidades existe.
3. El CLI listar/sugerir/receta/validar responde sin red.

Run with: python3 -m unittest discover -s scripts/_tests
"""

import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
BASE = os.path.dirname(SCRIPTS)
DATOS = os.path.join(SCRIPTS, "data", "efectos_talking_head.json")
SCRIPT = os.path.join(SCRIPTS, "efectos_talking_head.py")
REF = os.path.join(BASE, "references", "efectos-talking-head.md")

sys.path.insert(0, SCRIPTS)
import efectos_talking_head as ETH  # noqa: E402


class TestEfectosTalkingHead(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(DATOS, encoding="utf-8") as fh:
            cls.datos = json.load(fh)
        with open(REF, encoding="utf-8") as fh:
            cls.ref = fh.read()

    def test_validar_ok_y_conteo_45(self):
        malos = ETH.validar(self.datos)
        self.assertEqual(malos, [], malos)
        self.assertEqual(len(self.datos["efectos"]), 45)
        self.assertEqual(self.datos["conteo"], 45)

    def test_ids_unicos_y_campos(self):
        ids = [e["id"] for e in self.datos["efectos"]]
        self.assertEqual(len(ids), len(set(ids)))
        for e in self.datos["efectos"]:
            self.assertIn(e["preferir"], ("externo", "nativo", "ambos"))
            self.assertTrue(e["ocasion"])
            self.assertIn("efectos_talking_head.py", e["ruta"])

    def test_moody_es_nativo_grade(self):
        moody = next(e for e in self.datos["efectos"] if e["id"] == "moody")
        self.assertEqual(moody["preferir"], "nativo")
        self.assertIn("grade", moody["nativo"])

    def test_no_hincha_scenes(self):
        self.assertIn("No añade tipos a SCENES", self.datos["_que_es"])
        self.assertTrue(self.datos["descartado_a_proposito"])

    def test_doc_apunta_al_json_no_copia_tabla(self):
        self.assertIn("efectos_talking_head.json", self.ref)
        self.assertIn("efectos_talking_head.py", self.ref)
        # no duplicar el inventario: la doc no enumera los 45 ids en tabla
        self.assertNotIn("| `orbit` |", self.ref)

    def test_entrada_desde_skill_mapa_selector_capacidades(self):
        for rel in (
            "SKILL.md",
            os.path.join("references", "animacion.md"),
            os.path.join("references", "mapa.md"),
            os.path.join("references", "capacidades.md"),
            os.path.join("references", "video-real.md"),
        ):
            path = os.path.join(BASE, rel)
            with open(path, encoding="utf-8") as fh:
                txt = fh.read()
            self.assertIn(
                "efectos-talking-head.md",
                txt,
                f"{rel} tiene que enlazar la técnica talking-head",
            )

    def test_cli_listar_sugerir_receta_validar(self):
        env = {**os.environ, "PYTHONPATH": SCRIPTS}
        r = subprocess.run(
            [sys.executable, SCRIPT, "validar"],
            cwd=BASE, capture_output=True, text=True, env=env, check=False,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("OK", r.stdout)

        r = subprocess.run(
            [sys.executable, SCRIPT, "listar", "--preferir", "nativo", "--json"],
            cwd=BASE, capture_output=True, text=True, env=env, check=False,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        filas = json.loads(r.stdout)
        self.assertTrue(any(e["id"] == "moody" for e in filas))

        r = subprocess.run(
            [sys.executable, SCRIPT, "sugerir", "--pedido", "reels orbitando mi cabeza"],
            cwd=BASE, capture_output=True, text=True, env=env, check=False,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("orbit", r.stdout)

        r = subprocess.run(
            [sys.executable, SCRIPT, "receta", "--fx", "spotlight", "--start", "2", "--end", "5"],
            cwd=BASE, capture_output=True, text=True, env=env, check=False,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("git clone", r.stdout)
        self.assertIn("spotlight", r.stdout)
        self.assertIn("rm -rf /tmp/claude-video-effects", r.stdout)


if __name__ == "__main__":
    unittest.main()
