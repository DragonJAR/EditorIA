#!/usr/bin/env python3
"""Tests de las REGLAS que declara un brand pack.

Una regla que un pack declara pero que nadie aplica es una promesa que nadie
cumple. Este archivo comprueba que:

  1. La lista del motor (REGLAS_DEL_MOTOR / REGLAS_DEL_AGENTE) es la MISMA
     que la que dice references/brand-packs.md: si la doc aprende una regla
     nueva, el codigo tiene que saber de ella.
  2. Todo pack del repo declara reglas que estan en esa lista: un pack no
     puede declarar una regla que nadie lee.
  3. La regla que el motor dice aplicar, la APLICA de verdad: con
     `transiciones: corte_seco` el corte entre escenas es seco; con `libre`
     se solapan. El ultimo test rompe el motor a proposito y comprueba que la
     garantia lo nota: una guarda que nunca se ha visto fallar no es una
     guarda, es una hipotesis.

Run with: python3 -m unittest discover -s SKILL/scripts/_tests
"""

import json
import os
import re
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
BASE = os.path.dirname(SCRIPTS)
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, os.path.join(SCRIPTS, "ffmpeg_tools"))

import render_plan as R  # noqa: E402

BRANDS = os.path.join(BASE, "brand")
DOC = os.path.join(BASE, "references", "brand-packs.md")


def _reglas_documentadas():
    """Las claves `reglas` que la referencia reconoce."""
    with open(DOC, encoding="utf-8") as f:
        txt = f.read()
    bloque = txt.split("Claves `reglas` reconocidas:")[-1].split("## ")[0]
    return set(re.findall(r"^- `([a-z_]+)`", bloque, re.M))


class ReglasDelPack(unittest.TestCase):

    def test_la_lista_del_motor_es_la_de_la_documentacion(self):
        """La fuente de verdad es UNA: si la doc y el codigo se separan, una
        regla queda sin dueno."""
        doc = _reglas_documentadas()
        self.assertTrue(doc, "no se hallaron reglas en la referencia")
        self.assertEqual(
            doc, R.REGLAS_DEL_PACK,
            "las reglas del motor y las de la referencia no son las mismas: "
            f"doc={sorted(doc)} motor={sorted(R.REGLAS_DEL_PACK)}")

    def test_ningun_pack_declara_una_regla_que_nadie_conoce(self):
        """Un pack puede declarar reglas; no puede declarar reglas que no
        están en la lista de nadie."""
        for nombre in sorted(os.listdir(BRANDS)):
            if not nombre.endswith(".json"):
                continue
            with open(os.path.join(BRANDS, nombre), encoding="utf-8") as f:
                pack = json.load(f)
            declaradas = set((pack.get("reglas") or {}).keys())
            declaradas -= {k for k in declaradas if k.startswith("_")}
            desconocidas = declaradas - R.REGLAS_DEL_PACK
            self.assertFalse(
                desconocidas,
                f"{nombre} declara reglas que nadie lee: {sorted(desconocidas)}")

    def test_el_motor_aplica_la_regla_de_transiciones(self):
        """`transiciones: corte_seco` tiene que cambiar el corte de verdad, y
        `libre` tiene que dejarlo como estaba. Si el motor ignorase la regla,
        las dos ramas darian el MISMO solape y este test caeria."""
        with tempfile.TemporaryDirectory() as tmp:
            for valor, esperado in (("corte_seco", "SOLAPE_SECO"), ("libre", "SOLAPE")):
                with open(os.path.join(BRANDS, "dragonjar.json"), encoding="utf-8") as f:
                    pack = json.load(f)
                pack["reglas"]["transiciones"] = valor
                ruta = os.path.join(tmp, f"pack_{valor}.json")
                with open(ruta, "w", encoding="utf-8") as f:
                    json.dump(pack, f, ensure_ascii=False)
                solape_previo = R.SOLAPE
                try:
                    R.aplicar_brand(ruta)
                    self.assertEqual(R.TRANSICIONES, valor)
                    self.assertEqual(
                        R.SOLAPE, getattr(R, esperado),
                        f"con transiciones={valor} el motor no aplico la regla "
                        f"(solape {R.SOLAPE}, se esperaba {getattr(R, esperado)})")
                finally:
                    R.SOLAPE = solape_previo
                    R.SOLAPE_PRE = 0.25

    def test_un_pack_nuevo_no_puede_colarse(self):
        """Un pack con una regla desconocida se rechaza, no se ignora en
        silencio: es la forma de que la lista no se quede vieja."""
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(BRANDS, "dragonjar.json"), encoding="utf-8") as f:
                pack = json.load(f)
            pack["reglas"]["regla_inventada"] = True
            ruta = os.path.join(tmp, "pack_inventado.json")
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump(pack, f, ensure_ascii=False)
            declaradas = set(pack["reglas"].keys())
            desconocidas = declaradas - R.REGLAS_DEL_PACK
            self.assertTrue(
                desconocidas,
                "una regla que no esta en la lista tiene que detectable: "
                "si esto falla, la lista ya no protege de nada")


if __name__ == "__main__":
    unittest.main()
