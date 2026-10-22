#!/usr/bin/env python3
"""Tests del sistema de movimiento (el 'tacto' de la skill).

La auditoría del catálogo encontró que las 36 escenas usaban 23 resortes
distintos: el overshoot iba del 3 % al 20 % y la calma del 0.17 s al
0.40 s. El ojo no ve los números — ve que un plano "rebota" y el siguiente
"se asienta" — y eso se lee como "cada escena la hizo alguien distinto".

Ahora hay SEIS gestos con nombre (MOVIMIENTO) y todo elemento entra con
`entra(t, instante, "rol")`. Estos tests fijan el vocabulario cerrado:
nadie puede inventar un resorte nuevo sin que se note.
"""

import ast
import math
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
MOTOR = os.path.join(SCRIPTS, "render_plan.py")

ROLES_ESPERADOS = {"titular", "bloque", "elemento", "suave", "pop", "lento"}


def _spring(t, t0, stiff, damp):
    if t <= t0:
        return 0.0
    dt = t - t0
    w = math.sqrt(stiff)
    d = damp / (2 * w)
    if d >= 1:
        return 1 - math.exp(-w * dt) * (1 + w * dt)
    wd = w * math.sqrt(1 - d * d)
    return 1 - math.exp(-d * w * dt) * (math.cos(wd * dt) + d * w / wd * math.sin(wd * dt))


def _fisica(stiff, damp, fps=240):
    over = max(_spring(k / fps, 0, stiff, damp) for k in range(1, int(2.0 * fps))) - 1
    calma = 0.0
    for k in range(1, int(3.0 * fps)):
        if abs(_spring(k / fps, 0, stiff, damp) - 1.0) < 0.01:
            calma = k / fps
            break
    return over * 100, calma


class TestSistemaDeMovimiento(unittest.TestCase):
    def setUp(self):
        with open(MOTOR, encoding="utf-8") as f:
            self.src = f.read()
        self.tree = ast.parse(self.src)

    def _movimiento(self):
        for n in self.tree.body:
            if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "MOVIMIENTO":
                return {k.value: ast.literal_eval(v) for k, v in zip(n.value.keys, n.value.values)}
        return {}

    def test_los_seis_roles_existen(self):
        m = self._movimiento()
        self.assertTrue(m, "el motor debe declarar MOVIMIENTO")
        self.assertEqual(set(m), ROLES_ESPERADOS,
                         "los roles de movimiento son los del sistema, ni uno mas ni uno menos")

    def test_ninguna_entrada_inventa_un_resorte(self):
        """Toda entrada pasa por entra(..., "rol"); nadie escribe stiff/damp a mano."""
        crudos = re.findall(r"spring\([^()]*,\s*\d+\s*,\s*\d+\s*\)", self.src)
        self.assertEqual(crudos, [],
                         f"resortes inventados fuera del sistema: {crudos[:3]}")

    def test_toda_entrada_usa_un_rol_declarado(self):
        roles = set(self._movimiento())
        # sin la definicion de entra() (su parametro por defecto se llama "rol")
        cuerpo = self.src.split("def entra(", 1)[-1]
        usados = set(re.findall(r'entra\([^,]+,[^,]+,\s*"(\w+)"\)', cuerpo))
        self.assertTrue(usados, "debe haber entradas con rol")
        self.assertEqual(usados - roles, set(),
                         f"roles usados que no existen: {usados - roles}")

    def test_los_gestos_son_distintos_entre_si(self):
        """Seis gestos que se sienten iguales no son un sistema."""
        m = self._movimiento()
        sens = {}
        for rol, (st, dp) in m.items():
            over, calma = _fisica(st, dp)
            sens[rol] = (round(over, 1), round(calma, 2))
        for a in sens:
            for b in sens:
                if a < b:
                    self.assertNotEqual(sens[a], sens[b],
                                        f"'{a}' y '{b}' se sienten igual: {sens[a]}")

    def test_el_gesto_pop_es_el_unico_que_rebota_fuerte(self):
        """La regla del sistema: lo que rebota fuerte es lo que quiere que lo mires."""
        m = self._movimiento()
        overs = {r: _fisica(*v)[0] for r, v in m.items()}
        pop = overs["pop"]
        for r, o in overs.items():
            if r != "pop":
                self.assertLess(o, 12.0,
                                f"'{r}' rebota {o:.1f} %: deberia ser un gesto calmo")
        self.assertGreater(pop, 12.0, "el pop tiene que rebotar")

    def test_el_gesto_lento_es_el_mas_calmo(self):
        m = self._movimiento()
        overs = {r: _fisica(*v)[0] for r, v in m.items()}
        lentos = [r for r, o in overs.items() if abs(o - min(overs.values())) < 0.01]
        self.assertIn("lento", lentos, "'lento' tiene que ser el gesto mas calmo")

    def test_hay_un_solo_cta_en_toda_la_pieza(self):
        """El boton CTA es UN componente (boton_halo), no uno por escena.

        Antes: hero con halo y marco, final solo con halo, pago y demo sin
        nada — cuatro botones distintos en la misma pieza.
        """
        n_primitiva = len(re.findall(r"^def boton_halo\(", self.src, re.M))
        self.assertEqual(n_primitiva, 1, "debe existir UNA sola primitiva de boton")
        # ninguna escena puede dibujarse su propio boton CTA
        propios = re.findall(r"rounded_rectangle\([^)]*radius=(?:38|46)\b", self.src)
        self.assertEqual(propios, [],
                         f"botones propios de escena (deberian usar boton_halo): {propios[:3]}")
        # y el CTA de la casa debe ser el que usan las escenas
        self.assertGreaterEqual(self.src.count("boton_halo(d,"), 4,
                                "el CTA de la casa debe usarse en todas las escenas con boton")

    def test_el_rotulo_cae_en_la_misma_altura_en_todas_las_escenas(self):
        """La retícula: el kicker de cada escena, en y=H*0.20.

        Excepción: la LEMA de la tarjeta de cierre (`sc_final`) no es un
        kicker — es la linea final de la pieza, y va mas abajo y mas grande
        a proposito.
        """
        escenas = re.split(r"^def (sc_\w+)\(", self.src, flags=re.M)[1:]
        malas = []
        for i, cuerpo in enumerate(escenas):
            # variables de la escena que valen rotulo_y()
            alias = set(re.findall(r"(\w+)\s*=\s*rotulo_y\(\)", cuerpo))
            for m in re.finditer(r"rotulo\(ctx", cuerpo):
                llamada = cuerpo[m.start():m.start() + 220]
                if 'e["lema"]' in llamada:
                    continue          # la lema de cierre: otro rol, otra posicion
                if "y=rotulo_y(" in llamada:
                    continue
                yv = re.search(r"y=(\w+)", llamada)
                if yv and yv.group(1) in alias:
                    continue
                malas.append(f"{escenas[i]}: {llamada[:60]}")
        self.assertEqual(malas, [],
                         f"escenas cuyo kicker no cae en rotulo_y(): {malas}")


if __name__ == "__main__":
    unittest.main()
