#!/usr/bin/env python3
"""Tests for direccion_arte.py and the tells lint of auditar_plan.py.

Covers: the direction library (schema, real scene types, WCAG contrast of every
palette), deterministic dealing, filters by engine and real assets, honest
relaxation, SISTEMA.md / style pack generation (the pack is read by the same
helpers the engine uses and is never overwritten), pack verification, and the
tells lint (what it flags, what it must not flag, and how it is silenced).

Run with: python3 -m unittest discover -s SKILL/scripts/_tests
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, os.path.join(SCRIPTS, "ffmpeg_tools"))

import auditar_plan as AP  # noqa: E402
import direccion_arte as DA  # noqa: E402
from _comun import colores_marca, contraste, hex_a_rgb, load_brand  # noqa: E402


def args(**kw):
    base = dict(brief="", sector=None, tono=None, modo=None, energia=None, tiene=[], motor="plan",
                opciones=3, semilla=0, excluir=[], json=False)
    base.update(kw)
    return SimpleNamespace(**base)


def ids(mano):
    return [d["id"] for d in mano]


class TestBiblioteca(unittest.TestCase):
    def test_biblioteca_sana(self):
        self.assertEqual(DA.validar_biblioteca(DA.cargar(), AP.TIPOS_VALIDOS), [])

    def test_contraste_wcag(self):
        self.assertAlmostEqual(contraste("#000000", "#FFFFFF"), 21.0, places=1)
        self.assertAlmostEqual(contraste("#777777", "#777777"), 1.0, places=2)
        self.assertGreater(contraste("#FFFFFF", "#0A0A0A"), contraste("#888888", "#0A0A0A"))

    def test_validar_detecta_un_acento_flojo(self):
        datos = DA.cargar()
        datos["direcciones"][0]["paleta"]["acento"] = "#202020"
        self.assertTrue(any("acento" in p for p in DA.validar_biblioteca(datos)))

    def test_validar_detecta_escena_inexistente_y_personalidad_rara(self):
        datos = DA.cargar()
        datos["direcciones"][0]["escenas"] = ["no_existe"]
        datos["direcciones"][1]["movimiento"]["personalidad"] = "media"
        malos = DA.validar_biblioteca(datos, AP.TIPOS_VALIDOS)
        self.assertTrue(any("no_existe" in p for p in malos))
        self.assertTrue(any("fluidez.md" in p for p in malos))


class TestReparto(unittest.TestCase):
    def setUp(self):
        self.datos = DA.cargar()

    def test_determinista_por_brief(self):
        a = ids(DA.repartir(self.datos, args(brief="demo de editor"))[0])
        b = ids(DA.repartir(self.datos, args(brief="demo de editor"))[0])
        self.assertEqual(a, b)

    def test_semilla_da_otras_manos(self):
        manos = {tuple(ids(DA.repartir(self.datos, args(brief="x", semilla=s))[0])) for s in range(6)}
        self.assertGreater(len(manos), 1)

    def test_sin_assets_solo_direcciones_que_no_los_necesitan(self):
        for s in range(8):
            for d in DA.repartir(self.datos, args(semilla=s, opciones=5))[0]:
                self.assertIn("nada", d["necesita"], d["id"])

    def test_assets_reales_amplian_el_reparto(self):
        sin = set(ids(DA.repartir(self.datos, args(opciones=20))[1]))
        con = set(ids(DA.repartir(self.datos, args(opciones=20, tiene=["fotos", "footage", "capturas"]))[1]))
        self.assertTrue(sin < con)

    def test_motor_plan_excluye_lienzos_claros(self):
        pool = DA.repartir(self.datos, args(opciones=20, tiene=["fotos"]))[1]
        self.assertTrue(all(d["motor"]["plan"] for d in pool))
        libre = DA.repartir(self.datos, args(opciones=20, tiene=["fotos"], motor="libre"))[1]
        self.assertTrue(any(not d["motor"]["plan"] for d in libre))

    def test_filtros_aplican_y_se_relajan_con_honestidad(self):
        mano, pool, relajados, _ = DA.repartir(self.datos, args(tono="demo", modo="demostrar", sector="tecnologia"))
        self.assertTrue(all("demo" in d["tonos"] for d in pool))
        mano, pool, relajados, _ = DA.repartir(self.datos, args(energia="alta", tono="parodia", sector="deporte"))
        self.assertTrue(mano)
        self.assertTrue(relajados)           # no había 3 con esos filtros: se dijo cuáles se soltaron

    def test_excluir(self):
        d0 = ids(DA.repartir(self.datos, args(brief="z"))[0])
        d1 = ids(DA.repartir(self.datos, args(brief="z", excluir=d0))[0])
        self.assertFalse(set(d0) & set(d1))


class TestElegirYPack(unittest.TestCase):
    def test_pack_lo_leen_los_helpers_del_motor(self):
        d = DA.por_id(DA.cargar(), "hud_tecnico")
        with tempfile.TemporaryDirectory() as tmp:
            ruta = os.path.join(tmp, "estilo.json")
            with open(ruta, "w", encoding="utf-8") as fh:
                json.dump(DA.pack_json(d), fh, ensure_ascii=False)
            c = colores_marca(ruta)
            self.assertEqual(c["acento"], hex_a_rgb(d["paleta"]["acento"]))
            self.assertEqual(c["negro"], hex_a_rgb(d["paleta"]["negro"]))
            marca = load_brand(ruta)
            self.assertEqual(marca["caption"]["position"], d["caption"]["position"])
            self.assertEqual(marca["font"], "Montserrat")

    def test_elegir_escribe_y_no_pisa(self):
        with tempfile.TemporaryDirectory() as tmp:
            cmd = [sys.executable, os.path.join(SCRIPTS, "direccion_arte.py"), "elegir", "producto_actuando", "--out", tmp]
            self.assertEqual(subprocess.run(cmd, capture_output=True, text=True).returncode, 0)
            self.assertTrue(os.path.isfile(os.path.join(tmp, "SISTEMA.md")))
            self.assertTrue(os.path.isfile(os.path.join(tmp, "estilo.json")))
            with open(os.path.join(tmp, "SISTEMA.md"), "w", encoding="utf-8") as fh:
                fh.write("mis decisiones")
            r = subprocess.run(cmd, capture_output=True, text=True)
            self.assertIn("no se toca", r.stdout)
            with open(os.path.join(tmp, "SISTEMA.md"), encoding="utf-8") as fh:
                self.assertEqual(fh.read(), "mis decisiones")

    def test_lienzo_claro_no_genera_pack(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "direccion_arte.py"), "elegir",
                                "cartel_plano", "--out", tmp], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(os.path.isfile(os.path.join(tmp, "SISTEMA.md")))
            self.assertFalse(os.path.exists(os.path.join(tmp, "estilo.json")))
            self.assertIn("lienzo claro", r.stdout)

    def test_no_se_escribe_dentro_de_la_skill(self):
        r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "direccion_arte.py"), "elegir", "monumento",
                            "--out", os.path.join(os.path.dirname(SCRIPTS), "proyecto_x")],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        self.assertNotIn("Traceback", r.stderr)

    def test_ficha_incluye_idea_contraste_y_excepciones(self):
        md = DA.ficha_md(DA.por_id(DA.cargar(), "monumento"), "mi brief")
        for frag in ("## La idea", "Prueba del competidor", "Contraste sobre el lienzo", "## Excepciones por escena",
                     "mi brief"):
            self.assertIn(frag, md)


class TestVerificar(unittest.TestCase):
    def _verificar(self, acento, *extra):
        """Pack propio del test (acento a elegir): independiente de los packs de brand/."""
        with tempfile.TemporaryDirectory() as tmp:
            ruta = os.path.join(tmp, "pack.json")
            with open(ruta, "w", encoding="utf-8") as fh:
                json.dump({"nombre": "prueba", "colores": {"acento": acento, "blanco": "#FAF8F6",
                                                          "gris": "#AAAAAA", "negro": "#0A0A0A"}}, fh)
            return subprocess.run([sys.executable, os.path.join(SCRIPTS, "direccion_arte.py"), "verificar", ruta, *extra],
                                  capture_output=True, text=True)

    def test_acento_flojo_avisa_y_sirve_solo_en_texto_grande(self):
        r = self._verificar("#B8230F")          # ~3.1:1 sobre #0A0A0A
        self.assertEqual(r.returncode, 0)
        self.assertIn("AVISO", r.stdout)
        self.assertIn("texto grande", r.stdout)

    def test_acento_ilegible_falla(self):
        self.assertIn("FALLA", self._verificar("#202020").stdout)

    def test_estricto_sale_con_1_solo_si_algo_no_llega(self):
        self.assertEqual(self._verificar("#B8230F", "--estricto").returncode, 1)
        self.assertEqual(self._verificar("#FFD23F", "--estricto").returncode, 0)

    def test_pack_inexistente_es_error_claro(self):
        r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "direccion_arte.py"), "verificar", "/no/existe.json"],
                           capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn("Traceback", r.stderr)


def plan(*escenas, **extra):
    return dict({"escenas": [dict(e, **{"from": i * 3, "to": i * 3 + 3}) for i, e in enumerate(escenas)]}, **extra)


def codigos(p):
    return sorted({h["codigo"] for h in AP.auditar_tells(p)})


class TestTells(unittest.TestCase):
    def test_plan_demo_del_proyecto_sin_tells(self):
        with open(os.path.join(SCRIPTS, "demo_plan.json"), encoding="utf-8") as fh:
            self.assertEqual(AP.auditar_tells(json.load(fh)), [])

    def test_detecta_cada_codigo(self):
        casos = {
            "jerga": {"tipo": "apertura", "texto1": ["Desbloquea tu potencial"]},
            "correccion": {"tipo": "final", "lema": "No es una herramienta. Es un equipo."},
            "emoji": {"tipo": "notificacion", "items": [{"app": "X", "icono": "🎬"}]},
            "placeholder": {"tipo": "final", "lema": "Lorem ipsum"},
            "numeracion": {"tipo": "pasos", "items": [{"titulo": "Paso 01 abrir"}]},
            "prueba-inventada": {"tipo": "stats", "cards": [{"valor": "10.000+ clientes"}]},
            "titular-largo": {"tipo": "hero", "titulo": "Una frase de titular extremadamente larga que ya no cabe"},
        }
        for codigo, escena in casos.items():
            self.assertIn(codigo, codigos(plan(escena)), codigo)

    def test_no_marca_palabras_espanolas_comunes(self):
        for texto in ("Todo en un solo lugar", "TODO LISTO", "Ahora es automático", "Diez veces más rápido"):
            self.assertEqual(codigos(plan({"tipo": "apertura", "texto1": [texto]})), [], texto)

    def test_fuente_declarada_acepta_la_cifra(self):
        escena = {"tipo": "stats", "cards": [{"valor": "10.000 usuarios"}], "fuente": "Informe 2026"}
        self.assertNotIn("prueba-inventada", codigos(plan(escena)))

    def test_escena_repetida_y_excepciones(self):
        self.assertIn("escena-repetida", codigos(plan(*[{"tipo": "stats", "cards": [{"valor": "1"}]}] * 3)))
        self.assertNotIn("escena-repetida", codigos(plan(*[{"tipo": "kenburns"}] * 3)))

    def test_rotulo_en_todas_y_cadencia(self):
        escenas = [{"tipo": t, "rotulo": "A"} for t in ("canales", "chat", "stats", "bars", "pie")]
        p = plan(*escenas)
        self.assertIn("rotulo-en-todas", codigos(p))
        self.assertIn("cadencia-uniforme", codigos(p))          # todas duran 3 s

    def test_tells_ok_silencia(self):
        p = plan({"tipo": "final", "lema": "Lorem ipsum"}, tells_ok=["placeholder"])
        self.assertEqual(codigos(p), [])

    def test_siempre_aviso_nunca_error(self):
        p = plan({"tipo": "final", "lema": "Lorem ipsum desbloquea"})
        self.assertTrue(all(h["nivel"] == "AVISO" for h in AP.auditar_tells(p)))

    def test_muestras_canonicas_sin_emoji(self):
        with open(os.path.join(SCRIPTS, "escenas_muestra.json"), encoding="utf-8") as fh:
            muestras = json.load(fh)["escenas"]
        for tipo, e in muestras.items():
            self.assertNotIn("emoji", codigos({"escenas": [dict(e, tipo=tipo)]}), tipo)

    def test_cli_sin_tells(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = os.path.join(tmp, "plan.json")
            with open(ruta, "w", encoding="utf-8") as fh:
                json.dump(plan({"tipo": "final", "lema": "Lorem ipsum"}), fh)
            con = subprocess.run([sys.executable, os.path.join(SCRIPTS, "auditar_plan.py"), ruta],
                                 capture_output=True, text=True)
            sin = subprocess.run([sys.executable, os.path.join(SCRIPTS, "auditar_plan.py"), ruta, "--sin-tells"],
                                 capture_output=True, text=True)
            self.assertIn("[placeholder]", con.stdout)
            self.assertNotIn("[placeholder]", sin.stdout)


if __name__ == "__main__":
    unittest.main()
