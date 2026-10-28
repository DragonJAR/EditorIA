#!/usr/bin/env python3
"""Tests de la REGLA del tamaño del catálogo de escenas.

El tamaño del catálogo se afirma en la prosa de docenas de maneras y lo
comprueban tres cosas: el guard (que falla si lo publicado miente), la
herramienta (que lo reescribe) y la puerta (que es el superset). Antes cada
uno tenía su propia lista de frases y MEDIDO la puerta daba verde con 18
cifras falsas en 12 ficheros: una lista de frases solo cubre las frases que
alguien pensó, y la prosa dice el tamaño del catálogo de muchas más formas
("el catálogo de 39 tipos de escena", "las 39 escenas planas", "el motor
tiene 39 tipos de\nescena", "39 escenas (references/escenas.md)").

Estos tests comprueban tres cosas:

  1. la REGLA caza las formas que la lista estrecha no cogía, y en ficheros
     REALES (un ejemplo inventado probaría el ejemplo, no la prosa);
  2. la regla NO toca lo que no afirma el total (histórico, rango, escenas de
     un plan, catálogo externo): un guard que señala de más es un guard que
     nadie escucha;
  3. la herramienta y el guard dicen lo MISMO (una idea, un canónico): el
     ciclo "corrige y vuelve a fallar" tiene que tener salida.

Run with: python3 -m unittest discover -s SKILL/scripts/_tests
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
BASE = os.path.dirname(SCRIPTS)
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)   # para importar el guard y la herramienta

import auditar_mapa as AM            # noqa: E402  el dueño de la regla
import actualizar_conteos as AC      # noqa: E402  la que reescribe con la regla

#: Las cifras que NO afirman el tamaño del catálogo. Cada una con su motivo:
#: un guard que señala de más es un guard que nadie escucha.
NO_AFIRMAN_EL_TOTAL = (
    "El formato plan.json y los 13 tipos de escena vienen del sistema original.",
    "La pieza entera con 2-3 tipos de escena (o un tipo en la mitad).",
    "Ritmo: 4-6 escenas, 3-5 s cada una.",
    "Regla: si la pieza se resuelve en <10 escenas del plan, el motor Python gana.",
    "[Plan] escribo plan.json con 5 escenas tipo apertura + canales + listo.",
    "Catálogo abierto con 201 escenas Remotion en 16 categorías.",
    "El catálogo integra las 13 escenas originales más 23 escenas de datos/UI.",
    "- 2026-10-05 · auditar_plan.py tenia su propia lista de 13 tipos: "
    "tras sumar 11 escenas marcaba ERROR.",
)


def _copia_skill(destino):
    """La skill entera (scripts + references + SKILL.md), sin __pycache__."""
    shutil.copytree(os.path.join(BASE, "scripts"), os.path.join(destino, "scripts"),
                    ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(os.path.join(BASE, "references"), os.path.join(destino, "references"))
    shutil.copy(os.path.join(BASE, "SKILL.md"), os.path.join(destino, "SKILL.md"))
    for sub in ("brand", "film", "assets", "metricas"):
        origen = os.path.join(BASE, sub)
        if os.path.isdir(origen):
            shutil.copytree(origen, os.path.join(destino, sub),
                            ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"))
    return destino


def _ejecuta(skill, *args):
    return subprocess.run([sys.executable, os.path.join(skill, "scripts", "actualizar_conteos.py"),
                           *args], capture_output=True, text=True, timeout=300)


def _audita(skill):
    r = subprocess.run([sys.executable, os.path.join(skill, "scripts", "auditar_mapa.py")],
                       capture_output=True, text=True, timeout=300)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


class TestReglaDelCatalogo(unittest.TestCase):
    def _n(self):
        """El tamaño del catálogo, según el motor (la única fuente)."""
        return AM._n_escenas_publicadas()

    def test_caza_la_forma_del_mapa_real(self):
        """El mapa dice el tamaño del catálogo de tres maneras distintas.

        MEDIDO: estas tres formas no las cogía la lista estrecha de frases, y
        por eso la prosa decía 39 con un motor de 41 escenas y la puerta
        daba verde. Aquí se rompe el número de verdad, en el fichero de
        verdad.
        """
        mapa = os.path.join(BASE, "references", "mapa.md")
        with open(mapa, encoding="utf-8") as f:
            txt = f.read()
        n = self._n()
        roto = re.sub(r"\d+ tipos de escena", f"{n + 1} tipos de escena", txt)
        self.assertNotEqual(roto, txt, "el mapa no dice 'N tipos de escena': "
                                        "el test mediría otra cosa")
        hallazgos = [h for h in AM._cifras_del_catalogo(roto)
                     if not h["exclusion"] and h["cifra"] == n + 1]
        self.assertTrue(hallazgos, "la regla no vio la cifra vieja en el mapa real")

    def test_caza_las_formas_multilinea(self):
        """La prosa parte la frase: "el motor tiene 39 tipos de\\nescena"."""
        texto = "Lo que aporta aquí es un vocabulario de LOOKS: el motor tiene 39 tipos de\nescena, que no son estilos."
        hallazgos = [h for h in AM._cifras_del_catalogo(texto) if not h["exclusion"]]
        self.assertEqual(len(hallazgos), 1, f"se esperaba UNA cifra, hubo {len(hallazgos)}")
        self.assertEqual(hallazgos[0]["cifra"], 39)

    def test_no_toca_lo_que_no_afirma_el_total(self):
        """Cada exclusión tiene su motivo, y el motivo se puede leer."""
        for frase in NO_AFIRMAN_EL_TOTAL:
            hallazgos = AM._cifras_del_catalogo(frase)
            sin_exclusion = [h for h in hallazgos if not h["exclusion"]]
            self.assertEqual(
                sin_exclusion, [],
                f"la regla senala una cifra que no afirma el total: {frase!r}")

    def test_la_descomposicion_se_comprueba_con_la_suma(self):
        """"las 13 escenas originales más 23 escenas": el total es la SUMA."""
        texto = "El catálogo integra las 13 escenas originales más 23 escenas de datos/UI."
        n = self._n()
        descomp = AM._descomposiciones_del_catalogo(texto)
        self.assertEqual(len(descomp), 1, "no se vio la descomposicion")
        self.assertEqual(descomp[0]["primera"], 13)
        self.assertEqual(descomp[0]["primera"] + descomp[0]["segunda"], 36)
        # la herramienta reescribe la SEGUNDA cifra (la primera es historica)
        cambios = []
        nuevo = AC._reescribe_catalogo(texto, n, "prueba", cambios)
        self.assertIn(f"las 13 escenas originales más {n - 13} escenas", nuevo)
        self.assertTrue(cambios, "la herramienta no dijo que cambio nada")

    def test_el_par_de_cifras(self):
        """"43/43 escenas render": las DOS cifras son el total."""
        texto = "la puerta sale 0 (43/43 scenes render, scripts compile)"
        n = self._n()
        pares = AM._pares_del_catalogo(texto)
        self.assertEqual(len(pares), 1, "no se vio el par")
        cambios = []
        nuevo = AC._reescribe_catalogo(texto, n, "prueba", cambios)
        self.assertIn(f"{n}/{n} scenes render", nuevo)

    def test_lo_que_ya_esta_bien_no_se_toca(self):
        """Una prosa con la cifra correcta sale IDÉNTICA (ni un byte)."""
        n = self._n()
        texto = (f"El catálogo tiene {n} tipos de escena y las {n} escenas "
                 f"componen en los dos formatos.\n")
        cambios = []
        self.assertEqual(AC._reescribe_catalogo(texto, n, "prueba", cambios), texto)
        self.assertEqual(cambios, [], "la herramienta dijo que cambio algo sin cambiarlo")

    def test_el_guard_senala_el_numero_viejo_y_la_herramienta_lo_arregla(self):
        """El ciclo entero, en una copia: guardar -> broken -> arreglar -> verde.

        Es el test que importa: el hueco no era que la regla no viera la
        cifra, era que la puerta daba VERDE con la prosa mintiendo.
        """
        self.dir = tempfile.mkdtemp(prefix="editoria_catalogo_")
        self.addCleanup(shutil.rmtree, self.dir, True)
        skill = _copia_skill(os.path.join(self.dir, "skill"))
        mapa = os.path.join(skill, "references", "mapa.md")
        with open(mapa, encoding="utf-8") as f:
            txt = f.read()
        n = self._n()
        roto = re.sub(r"\d+ tipos de escena", f"{n + 1} tipos de escena", txt)
        self.assertNotEqual(roto, txt, "el mapa no dice 'N tipos de escena'")
        with open(mapa, "w", encoding="utf-8") as f:
            f.write(roto)
        # el guard lo ve (avisa o falla, pero lo DICE)
        rc, out = _audita(skill)
        self.assertIn("conteo obsoleto", out,
                      f"el guard no vio la cifra vieja:\n{out[-800:]}")
        # la herramienta lo arregla
        r = _ejecuta(skill)
        self.assertEqual(r.returncode, 0, f"la herramienta fallo:\n{r.stderr}")
        with open(mapa, encoding="utf-8") as f:
            arreglado = f.read()
        self.assertIn(f"{n} tipos de escena", arreglado)
        # y el guard ya no lo ve
        rc, out = _audita(skill)
        self.assertNotIn("conteo obsoleto", out,
                         f"el guard sigue viendo lo que la herramienta arreglo:\n{out[-800:]}")


if __name__ == "__main__":
    unittest.main()
