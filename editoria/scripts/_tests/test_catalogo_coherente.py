#!/usr/bin/env python3
"""Guards de coherencia del catalogo: lo que la prosa y los datos dicen del
motor es lo que el motor hace.

1. Toda escena que el catalogo de datos NOMBRA existe en `SCENES`.
2. Las cifras de camara y salida que citan los docs salen del motor
   (`EMPUJE`, `SOLAPE`): antes motion_ui decia "push-in 1–5 %", animacion
   "1.04–1.08" y el motor empujaba 6 %; motion-ui seguia con la "salida
   anticipada 0,5 s" que T11 cambio por la salida cruzada desde el corte.

QUE PROTEGE

`efectos_talking_head.json` mandaba al modelo a "escena lineup / pasos" y
el docstring de `cuadricula` decia que la usaba `lineup`: `lineup` no esta
en `SCENES` (es una idea futura, escenas.md), y un plan con `tipo: lineup`
revienta con KeyError. El modelo lee esos JSON para elegir: una escena que
no existe es una instruccion rota.

Se miran:
- `repertorio.json`: `detalle_escenas` (claves) e `intenciones[].escenas`.
- los campos que mandan a una escena del plan en `efectos_talking_head.json`
  y `motion_ui.json` (`nativo`, `adaptar`): la forma "escena a / b" y
  "repertorio a/b" (los nombres encadenados con "/").

Run with: python3 -m pytest -q -p no:cacheprovider _tests/test_catalogo_coherente.py
"""

import json
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
DATA = os.path.join(SCRIPTS, "data")
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, os.path.join(SCRIPTS, "ffmpeg_tools"))

# "escena constancia / pasos / the-bill visual" -> constancia, pasos
# (un nombre de escena es un identificador: empieza por letra y no sigue con
# guion; la cadena "a / b" se corta en la primera palabra que no lo es)
_NOMBRE = r"[A-Za-z][A-Za-z0-9_]*(?![\w-])"
_REFERENCIA = re.compile(r"\b(?:escena|repertorio)\s+((?:%s\s*/\s*)*%s)" % (_NOMBRE, _NOMBRE))
CAMPOS = ("nativo", "adaptar")


def _cargar(nombre):
    with open(os.path.join(DATA, nombre), encoding="utf-8") as fh:
        return json.load(fh)


def _campos(obj, ruta=""):
    """(ruta, texto) de cada campo `nativo`/`adaptar` del JSON."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in CAMPOS and isinstance(v, str):
                yield f"{ruta}.{k}", v
            else:
                yield from _campos(v, f"{ruta}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _campos(v, f"{ruta}[{i}]")


def nombres_referidos(texto):
    out = []
    for m in _REFERENCIA.finditer(texto):
        out += [n.strip() for n in m.group(1).split("/")]
    return out


class TestEscenasReferidas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import render_plan as R
        cls.SCENES = set(R.SCENES)

    def test_el_extractor_lee_la_forma(self):
        self.assertEqual(nombres_referidos("escena constancia / pasos / the-bill visual"),
                         ["constancia", "pasos"])
        self.assertEqual(nombres_referidos("repertorio lineup/pasos"), ["lineup", "pasos"])
        self.assertEqual(nombres_referidos("Zoom escena 1,00→1,08"), [])

    def test_repertorio(self):
        rep = _cargar("repertorio.json")
        faltan = [k for k in rep.get("detalle_escenas", {}) if k not in self.SCENES]
        for it in rep.get("intenciones", []):
            faltan += [f"{it['id']}:{s}" for s in it.get("escenas", [])
                       if s.split(":")[-1] not in self.SCENES]
        self.assertEqual(faltan, [], "repertorio.json nombra escenas que no existen")

    def test_efectos_y_motion(self):
        malos = []
        for fichero in ("efectos_talking_head.json", "motion_ui.json"):
            for ruta, texto in _campos(_cargar(fichero)):
                for n in nombres_referidos(texto):
                    if n not in self.SCENES:
                        malos.append(f"{fichero}{ruta}: '{n}' en «{texto}»")
        self.assertEqual(malos, [], "un campo manda a una escena que no existe en SCENES")

    def test_el_docstring_de_cuadricula(self):
        import render_plan as R
        doc = R.cuadricula.__doc__ or ""
        m = re.search(r"la usan (.+?)\.", doc)
        self.assertTrue(m)
        for n in re.findall(r"`(\w+)`", m.group(1)):
            self.assertIn(n, self.SCENES, f"cuadricula dice que la usa '{n}'")


REFS = os.path.join(os.path.dirname(SCRIPTS), "references")


def _leer(*ruta):
    with open(os.path.join(*ruta), encoding="utf-8") as fh:
        return fh.read()


class TestCifrasDelMotor(unittest.TestCase):
    def setUp(self):
        import render_plan as R
        self.R = R

    def _pct(self):
        return f"{round(self.R.EMPUJE * 100)} %"

    def test_el_push_in_que_citan_es_el_del_motor(self):
        tec = {t["id"]: t for t in _cargar("motion_ui.json")["tecnicas"]}
        textos = {
            "motion_ui.json dimension": tec["dimension"]["numeros"],
            "motion-ui.md": [ln for ln in _leer(REFS, "motion-ui.md").splitlines()
                             if "**Dimension**" in ln][0],
            "animacion.md": [ln for ln in _leer(REFS, "animacion.md").splitlines()
                             if "**Push-in lento**" in ln][0],
        }
        fin = f"1.{round(self.R.EMPUJE * 100):02d}"
        for donde, txt in textos.items():
            with self.subTest(donde=donde):
                self.assertTrue(self._pct() in txt or fin in txt,
                                f"{donde} no cita el push-in del motor ({self._pct()}): {txt}")
                for viejo in ("1–5 %", "4–8 %", "1.04–1.08"):
                    self.assertNotIn(viejo, txt)

    def test_la_salida_que_citan_es_la_del_motor(self):
        R = self.R
        self.assertEqual(R.SOLAPE_PRE, 0.0, "si vuelve a anticipar, la prosa tiene que decirlo")
        seg = f"{R.SOLAPE:.2f}".replace(".", ",")
        tec = {t["id"]: t for t in _cargar("motion_ui.json")["tecnicas"]}
        fade = [tec["fade"]]   # la tecnica que cita la duracion de la salida
        textos = {"motion-ui.md": _leer(REFS, "motion-ui.md"),
                  "escenas.md": _leer(REFS, "escenas.md")}
        textos.update({f"motion_ui.json {t['id']}": t["numeros"] for t in fade})
        for donde, txt in textos.items():
            with self.subTest(donde=donde):
                self.assertNotIn("salida anticipada 0", txt.lower())
                self.assertIn(seg, txt, f"{donde} no cita la salida del motor ({seg} s)")


if __name__ == "__main__":
    unittest.main()
