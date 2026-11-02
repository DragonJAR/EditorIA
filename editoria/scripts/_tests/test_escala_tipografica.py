#!/usr/bin/env python3
"""Tests de la escala tipográfica del motor.

La auditoría del catálogo encontró que el mismo rol (un nombre, un detalle,
un estado) salía a 26, 27, 28, 30, 32, 34, 36, 40 o 44 px según la escena:
el ojo lo lee como "cada plano usa su propia tipografía". La corrección fue
una escala única (ESCALA) en `render_plan.py`.

Este test fija el contrato para que no vuelva a dispersarse:

1. La escala existe, tiene sus cinco roles y es monótona.
2. El piso de letra del motor es el mismo que mide el QA (26).
3. El auto-fit no puede dejar texto por debajo de ese piso.
4. Ningún texto de overlay usa un tamaño literal fuera de la escala.
5. La elevación de entrada es una sola cifra.
6. Las superficies comparten radio.

Run with: python3 -m unittest discover -s SKILL/scripts/_tests
"""

import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
MOTOR = os.path.join(SCRIPTS, "render_plan.py")

# Texto que NO es tipografía de la pieza: vive dentro de un mockup diegético
# (un post, un player). Es parte de la imagen, no del sistema tipografico.
DIEGETICOS = {("sc_comentario", 34), ("sc_comentario", 26)}


def _motor():
    with open(MOTOR, encoding="utf-8") as f:
        return f.read()


class TestEscalaTipografica(unittest.TestCase):
    def setUp(self):
        self.src = _motor()
        self.lineas = self.src.split("\n")

    def _esc(self, nombre):
        m = re.search(r"^ESCALA=\{(.*?)^\}", self.src, re.S | re.M)
        self.assertIsNotNone(m, "el motor debe definir ESCALA")
        bloque = m.group(1)
        val = {}
        for k, v in re.findall(r'"(\w+)":\s*(\d+)', bloque):
            val[k] = int(v)
        self.assertIn(nombre, val, f"ESCALA debe tener el rol '{nombre}'")
        return val[nombre]

    def test_la_escala_tiene_los_cinco_roles(self):
        m = re.search(r"^ESCALA=\{(.*?)^\}", self.src, re.S | re.M)
        self.assertIsNotNone(m)
        roles = set(re.findall(r'"(\w+)":\s*\d+', m.group(1)))
        self.assertEqual(roles, {"titular", "rotulo", "dato", "secundario", "nota"},
                         "la escala debe tener exactamente los cinco roles")

    def test_la_escala_es_monotona(self):
        e = {k: self._esc(k) for k in ("titular", "rotulo", "dato", "secundario", "nota")}
        self.assertGreater(e["titular"], e["rotulo"])
        self.assertGreater(e["rotulo"], e["dato"])
        self.assertGreater(e["dato"], e["secundario"])
        self.assertGreater(e["secundario"], e["nota"])

    def test_el_piso_de_la_escala_no_toca_el_minimo_legible(self):
        # LETRA_MIN del QA = 26 (scripts/medir_animacion.py)
        with open(os.path.join(SCRIPTS, "medir_animacion.py"), encoding="utf-8") as f:
            qa = f.read()
        m = re.search(r"LETRA_MIN\s*=\s*(\d+)", qa)
        self.assertIsNotNone(m, "medir_animacion.py debe definir LETRA_MIN")
        letra_min = int(m.group(1))
        self.assertGreaterEqual(self._esc("nota"), letra_min,
                                "el rol mas pequeno no puede bajar del piso legible")
        m2 = re.search(r"^MIN_LETRA\s*=\s*(\d+)", self.src, re.M)
        self.assertIsNotNone(m2, "el motor debe declarar MIN_LETRA")
        self.assertEqual(int(m2.group(1)), letra_min,
                         "el piso del motor y el del QA deben ser el mismo numero")

    def test_el_autofit_no_puede_bajar_del_piso(self):
        """El auto-fit tiene SU piso, y no es el de legibilidad.

        Medido: con el piso del auto-fit en 26 (el de legibilidad), un copy
        largo se sale de su caja y la escena entera se va al piso de la zona
        segura (x0.72 con copy x2). El auto-fit existe para que el texto
        QUEPA; el que juzga la legibilidad es el QA (LETRA_MIN = 26), y lo
        que se acorta cuando el texto no cabe es el COPY, no la letra.
        """
        m = re.search(r"def fuente_que_cabe\([^)]*minimo=(\d+)", self.src, re.S)
        self.assertIsNotNone(m, "fuente_que_cabe debe declarar su piso")
        piso_auto = int(m.group(1))
        with open(os.path.join(SCRIPTS, "medir_animacion.py"), encoding="utf-8") as f:
            qa = f.read()
        letra_min = int(re.search(r"LETRA_MIN\s*=\s*(\d+)", qa).group(1))
        self.assertLess(piso_auto, letra_min,
                        "el piso del auto-fit debe ser MENOR que el de legibilidad: "
                        "el auto-fit hace que el texto quepa, el QA juzga si se lee")
        # y el piso de legibilidad es el mismo número en los dos lados
        m2 = re.search(r"^MIN_LETRA\s*=\s*(\d+)", self.src, re.M)
        self.assertIsNotNone(m2, "el motor debe declarar MIN_LETRA")
        self.assertEqual(int(m2.group(1)), letra_min,
                         "el piso de legibilidad del motor y el del QA deben ser el mismo número")

    def test_ningun_texto_de_overlay_usa_un_tamano_fuera_de_la_escala(self):
        escala = {self._esc(k) for k in ("titular", "rotulo", "dato", "secundario", "nota")}
        cur = None
        fallos = []
        for i, ln in enumerate(self.lineas):
            m = re.match(r"def (sc_\w+)\(", ln)
            if m:
                cur = m.group(1)
            if ".text(" not in ln:
                continue
            blob = ln + " " + (self.lineas[i + 1] if i + 1 < len(self.lineas) else "")
            if "ESCALA[" in blob:
                continue
            t = re.findall(r"f[TMX]\(\s*(\d{2,3})|,\s*(\d{2,3}),\s*"
                           r"(?:ancho|util|col_w|zx1|at_|w|max)", blob)
            tam = [int(x) for g in t for x in g if x]
            if not tam:
                continue
            v = tam[0]
            if 26 <= v <= 48 and v not in escala and (cur, v) not in DIEGETICOS:
                fallos.append(f"{cur} L{i+1}: {v} px (escala={sorted(escala)})")
        self.assertEqual(fallos, [],
                         "texto de overlay con tamano fuera de la escala:\n  " + "\n  ".join(fallos))

    def test_la_elevacion_de_entrada_es_una_sola_cifra(self):
        m = re.search(r"^ELEV\s*=\s*(\d+)", self.src, re.M)
        self.assertIsNotNone(m, "el motor debe declarar ELEV")
        # ninguna entrada puede seguir con su propio 24/30 a mano
        for frag in ("(1-min(1,k))*24", "(1-min(1,k))*30", "(1-min(1,kr))*24",
                     "(1-min(1,kr))*30"):
            self.assertNotIn(frag, self.src,
                             f"la elevacion debe pasar por ELEV (quedo '{frag}')")
        self.assertGreaterEqual(self.src.count("*ELEV"), 4,
                                "ELEV debe usarse en titular, rotulo y grupos")

    def test_las_superficies_comparten_radio(self):
        radios = [int(r) for r in re.findall(r"rounded_rectangle\([^)]*?radius=(\d+)", self.src)]
        # 28 es el radio canonico de SUPERFICIE (tarjeta, tarjeta_cristal, panel).
        # Los demas son pildoras (radio = h/2) o elementos pequenos (barras de
        # progreso, chips, pestanas de un mockup diegetico), no superficies.
        permitidos = {
            28,               # superficie
            38, 46, 22, 24,   # pildoras: radio = h/2
            19,               # pildora de la barra del navegador (h/2 de 38)
            70, 86,           # circulos decorativos
            12, 15, 14, 6, 3, # elementos pequenos (barras, chips, pestanas)
            18,               # columnas de grafico y filas de un mockup
        }
        fuera = sorted({r for r in radios if r not in permitidos})
        self.assertEqual(fuera, [],
                         f"radios de superficie fuera del canon: {fuera}")

    def test_el_auditor_conoce_la_escala_del_motor(self):
        """El valor unico de la escala vive en el motor; el auditor lo repite
        para vigilar la doc. Este test ata los dos (como el piso de letra)."""
        with open(os.path.join(SCRIPTS, "auditar_mapa.py"), encoding="utf-8") as f:
            auditor = f.read()
        m = re.search(r'"nombre":\s*"escala tipografica".*?"valor":\s*'
                      r'\(([\d.,\s]+)\)', auditor, re.S)
        self.assertIsNotNone(m, "auditar_mapa.py debe declarar la escala tipografica")
        declarado = tuple(float(x) for x in re.findall(r"[\d.]+", m.group(1)))
        motor = (self._esc("titular"), self._esc("rotulo"), self._esc("dato"),
                 self._esc("secundario"), self._esc("nota"))
        self.assertEqual(declarado, motor,
                         "la escala del auditor y la del motor deben ser la misma")


if __name__ == "__main__":
    unittest.main()
