#!/usr/bin/env python3
"""Guarda del piso de letra legible: el motor no puede contradecirlo.

El problema que motivó esto: `MIN_LETRA=26` dice que 26 px es el mínimo
legible y que lo mide el QA (`medir_animacion`, LETRA_MIN). Pero el motor
dibujaba SEIS textos por debajo de ese piso con tamaño FIJO (24, 22, 20 px),
y ademas bajaba el piso de auto-fit a 12/14/16 en otros siete sitios. Como
el texto se dibujaba a tamaño fijo, no lo arreglaba ni el auto-fit ni el
copy: esas escenas NO PODIAN pasar el QA por construccion.

Este test hace el invariante explicito y lo vigila sobre el AST (no con
grep: un "grep 24" en un archivo con 4000 lineas no dice si ese 24 se
dibuja, y un nombre de variable no aparece en el fuente).

Reglas:
1. La escala no puede tener un rol por debajo del piso (ESCALA["nota"] >= 26).
2. Un tamaño FIJO de texto por debajo del piso solo se permite si el texto
   dibujado NO tiene alfanumericos: eso es un glifo (un "✓"), no una palabra.
   El QA mide lo mismo (ignora los strings sin alfanumericos): motor y QA
   tienen que estar de acuerdo sobre que es "texto".
3. El piso de auto-fit nunca baja del piso global (18): es el "no
   microscopico", y el que juzga la legibilidad es el QA.
4. El tamaño objetivo de un auto-fit (el 2o argumento) no puede ser un
   literal por debajo del piso: el motor no puede PLANEAR dibujar 21 px.

Run with: python3 -m unittest discover -s SKILL/scripts/_tests
"""

import ast
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
BASE = os.path.dirname(SCRIPTS)
sys.path.insert(0, os.path.join(SCRIPTS, "ffmpeg_tools"))
sys.path.insert(0, SCRIPTS)

import render_plan as RP  # noqa: E402

RENDER = os.path.join(SCRIPTS, "render_plan.py")
PISO_AUTO = 18          # piso global de auto-fit (el de `fuente_que_cabe`)


def _literal(node):
    try:
        v = ast.literal_eval(node)
    except Exception:
        return None
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _es_alfanumerico(texto):
    return any(c.isalnum() for c in texto)


class AnalisisMotor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(RENDER, encoding="utf-8") as fh:
            cls.src = fh.read()
        cls.tree = ast.parse(cls.src)

        # 1) Los glifos permitidos: textos SIN alfanumericos y el nodo exacto
        #    de la fuente con la que se dibujan.
        cls.glifos = set()
        for nodo in ast.walk(cls.tree):
            if not isinstance(nodo, ast.Call) or not isinstance(nodo.func, ast.Attribute):
                continue
            if nodo.func.attr != "text" or len(nodo.args) < 2:
                continue
            txt = nodo.args[1]
            if not (isinstance(txt, ast.Constant) and isinstance(txt.value, str)):
                continue
            if _es_alfanumerico(txt.value):
                continue
            for kw in nodo.keywords:
                if kw.arg == "font":
                    cls.glifos.add(id(kw.value))

    # ---- reglas ---------------------------------------------------------

    def test_la_escala_no_tiene_un_rol_bajo_el_piso(self):
        for rol, tam in RP.ESCALA.items():
            self.assertGreaterEqual(
                tam, RP.MIN_LETRA,
                f"ESCALA[{rol!r}] = {tam} px esta bajo el piso legible "
                f"({RP.MIN_LETRA}); el QA rechazaria cualquier pieza que lo use")

    def test_ningun_texto_fijo_bajo_el_piso(self):
        """Un tamaño fijo bajo el piso solo se permite en un glifo."""
        culpables = []
        for nodo in ast.walk(self.tree):
            if not isinstance(nodo, ast.Call) or not isinstance(nodo.func, ast.Attribute):
                continue
            if nodo.func.attr not in ("fX", "fT", "fM") or not nodo.args:
                continue
            tam = _literal(nodo.args[0])
            if tam is None or tam >= RP.MIN_LETRA:
                continue
            if id(nodo) in self.glifos:
                continue
            culpables.append((nodo.lineno, tam, ast.unparse(nodo)[:60]))
        self.assertEqual(
            culpables, [],
            "el motor dibuja texto por debajo del piso legible "
            f"({RP.MIN_LETRA} px). Sube a ESCALA['nota'] o declara el glifo:\n"
            + "\n".join(f"  linea {ln}: {tam} px  {txt}" for ln, tam, txt in culpables))

    def test_el_piso_de_auto_fit_no_baja_del_piso_global(self):
        culpables = []
        for nodo in ast.walk(self.tree):
            if not isinstance(nodo, ast.Call):
                continue
            nombre = nodo.func.attr if isinstance(nodo.func, ast.Attribute) else (
                nodo.func.id if isinstance(nodo.func, ast.Name) else "")
            if nombre != "fuente_que_cabe":
                continue
            for kw in nodo.keywords:
                if kw.arg == "minimo":
                    v = _literal(kw.value)
                    if v is not None and v < PISO_AUTO:
                        culpables.append((nodo.lineno, v))
        self.assertEqual(
            culpables, [],
            f"el piso de auto-fit no puede bajar de {PISO_AUTO} (el global de "
            "fuente_que_cabe); por debajo, la letra queda ilegible para siempre")

    def test_el_auto_fit_no_planea_dibujar_bajo_el_piso(self):
        """El 2o argumento de fuente_que_cabe es el tamaño que el motor
        quiere usar: si es un literal bajo el piso, el auto-fit NUNCA va a
        llegar a 26 y el QA lo va a rechazar siempre."""
        culpables = []
        for nodo in ast.walk(self.tree):
            if not isinstance(nodo, ast.Call):
                continue
            nombre = nodo.func.attr if isinstance(nodo.func, ast.Attribute) else (
                nodo.func.id if isinstance(nodo.func, ast.Name) else "")
            if nombre != "fuente_que_cabe" or len(nodo.args) < 3:
                continue
            tam = _literal(nodo.args[2])
            if tam is not None and tam < RP.MIN_LETRA:
                culpables.append((nodo.lineno, tam))
        self.assertEqual(
            culpables, [],
            f"el motor PLANEA dibujar texto a menos de {RP.MIN_LETRA} px: "
            "esa pieza no puede pasar el QA por construccion")


class ContratoDelMotor(unittest.TestCase):
    def test_el_glifo_de_verificado_esta_declarado(self):
        """El '✓' es un simbolo dentro de un badge: se declara para que la
        guarda sepa que es una excepcion, no un descuido."""
        self.assertTrue(hasattr(RP, "TAM_CHECK"))
        self.assertLess(RP.TAM_CHECK, RP.MIN_LETRA)

    def test_la_escala_tiene_los_cinco_roles(self):
        for rol in ("titular", "rotulo", "dato", "secundario", "nota"):
            self.assertIn(rol, RP.ESCALA)


if __name__ == "__main__":
    unittest.main()
