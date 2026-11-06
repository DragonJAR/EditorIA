#!/usr/bin/env python3
"""Tests de la FIRMA del plan: el video dice de que plan salio.

QUE PROTEGE

1. La firma cambia cuando cambia el plan (una cifra, un copy, un `y`).
2. La caché de frames se INVALIDA cuando la firma cambia: sin esto, cambiar el
   plan y re-renderizar sin `--force` reutiliza los PNG del plan anterior y el
   video sale viejo. MEDIDO: el video llevaba el plan de antes y la puerta lo
   aprobaba (el mtime del video era mas nuevo, asi que la fecha no lo veia).
3. La puerta (qa_entrega) detecta el desfase por la firma, tambien con
   `--sin-medir` (sin medir tiempos): la firma no depende de la maquina.
4. El pack por NOMBRE resuelve ("carbon" → brand/carbon.json) y el error dice
   que packs hay.

Run with: python3 -m unittest discover -s SKILL/scripts/_tests
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
SKILL = os.path.dirname(SCRIPTS)
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)
if os.path.join(SCRIPTS, "ffmpeg_tools") not in sys.path:
    sys.path.insert(0, os.path.join(SCRIPTS, "ffmpeg_tools"))

from _comun import (firma_de_video, firma_plan, buscar_pack,  # noqa: E402
                    packs_disponibles, resolver_pack, version_motor)

PLAN_MIN = {
    "duracion": 1.0,
    "escenas": [
        {"tipo": "apertura", "from": 0.0, "to": 1.0,
         "texto1": ["Hola"], "texto2": ["Mundo"],
         "at": {"cambio": 0.5, "p1": [0.1], "p2": [0.6]}},
    ],
}


class TestFirmaDelPlan(unittest.TestCase):
    def test_la_firma_cambia_cuando_cambia_el_plan(self):
        """Una cifra distinta = firma distinta (y al reves)."""
        a = json.loads(json.dumps(PLAN_MIN))
        b = json.loads(json.dumps(PLAN_MIN))
        self.assertEqual(firma_plan(a), firma_plan(b), "el mismo plan da dos firmas")
        b["escenas"][0]["texto1"] = ["Adios"]
        self.assertNotEqual(firma_plan(a), firma_plan(b),
                            "cambiar el copy no cambio la firma: la cache no se invalidaria")
        c = json.loads(json.dumps(PLAN_MIN))
        c["duracion"] = 2.0
        self.assertNotEqual(firma_plan(a), firma_plan(c),
                            "cambiar la duracion no cambio la firma")

    def test_la_version_del_motor_entra_en_la_firma(self):
        """Un motor nuevo no puede reutilizar frames del anterior."""
        v = version_motor()
        self.assertTrue(v and v != "sin-version",
                        f"no se lee metadata.version del SKILL.md: {v!r}")
        import _comun
        antes = _comun.firma_plan(PLAN_MIN)
        real = _comun.version_motor
        try:
            _comun.version_motor = lambda: "9999.9999"
            despues = _comun.firma_plan(PLAN_MIN)
        finally:
            _comun.version_motor = real
        self.assertNotEqual(antes, despues,
                            "la version del motor NO entra en la firma: un motor "
                            "nuevo podria reutilizar los frames del anterior")

    def test_el_pack_por_nombre_resuelve(self):
        """'carbon' → brand/carbon.json: el catalogo lo enseña asi."""
        nombres = packs_disponibles()
        self.assertTrue(nombres, "la skill no declara ningun pack")
        ruta = buscar_pack(nombres[0])
        self.assertIsNotNone(ruta, f"el pack por nombre {nombres[0]!r} no resuelve")
        self.assertTrue(os.path.isfile(ruta))
        self.assertTrue(resolver_pack(nombres[0]))

    def test_el_error_dice_que_packs_hay(self):
        """Un pack que no existe debe decir los que SI hay."""
        import contextlib
        import io
        salida = io.StringIO()
        with contextlib.redirect_stderr(salida):
            with self.assertRaises(SystemExit):
                resolver_pack("no-existe-este-pack")
        texto = salida.getvalue()
        for nombre in packs_disponibles():
            self.assertIn(nombre, texto,
                          f"el error no menciona el pack {nombre}: {texto!r}")


class TestCacheQueSeInvalida(unittest.TestCase):
    """El fallo de fondo: re-renderizar sin --force con otro plan."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="firma_cache_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.plan = os.path.join(self.tmp, "plan.json")
        self.salida = os.path.join(self.tmp, "pieza.mp4")
        with open(self.plan, "w", encoding="utf-8") as fh:
            json.dump(PLAN_MIN, fh, ensure_ascii=False)

    def _render(self, force=False, conservar=True):
        cmd = [sys.executable, os.path.join(SCRIPTS, "render_plan.py"), self.plan,
               "-o", self.salida, "--fps", "10"]
        if force:
            cmd.append("--force")
        if conservar:   # la caché solo sobrevive al render si se pide
            cmd.append("--conservar-frames")
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        if r.returncode != 0:
            self.fail(f"el render fallo:\n{r.stdout[-1500:]}\n{r.stderr[-1500:]}")
        return r.stdout

    def test_cambiar_el_plan_invalida_los_frames_antes(self):
        """El render 2 con otro plan NO puede reutilizar los frames del 1."""
        self._render()
        frames = os.path.join(self.salida + ".frames")
        self.assertTrue(os.path.isdir(frames), "no hay carpeta de frames")
        marca = os.path.join(frames, ".firma")
        self.assertTrue(os.path.isfile(marca),
                        "no se escribe la marca de la cache: sin ella, un plan "
                        "distinto reutiliza los frames viejos")
        antes = open(marca, encoding="utf-8").read().strip()
        # se cambia el plan (el copy de la primera frase)
        plan2 = json.loads(json.dumps(PLAN_MIN))
        plan2["escenas"][0]["texto1"] = ["Cambiado"]
        with open(self.plan, "w", encoding="utf-8") as fh:
            json.dump(plan2, fh, ensure_ascii=False)
        salida = self._render()
        despues = open(marca, encoding="utf-8").read().strip()
        self.assertNotEqual(antes, despues,
                            "la marca de la cache no cambio con el plan")
        self.assertIn("frames", salida)

    def test_sin_conservar_los_frames_se_borran(self):
        """Por defecto el render borra `<salida>.frames/` al terminar bien.

        MEDIDO: un lote de 25 piezas de ~2 min a 1920x1080 dejó ~3 GB de PNG
        por pieza y llenó el disco a mitad del lote."""
        salida = self._render(conservar=False)
        self.assertTrue(os.path.isfile(self.salida), "no quedó el video")
        self.assertFalse(os.path.exists(self.salida + ".frames"),
                         "los frames temporales quedaron en disco")
        self.assertIn("frames temporales borrados", salida)

    def test_conservar_frames_los_deja(self):
        """`--conservar-frames` deja la caché para re-renderizar o inspeccionar."""
        self._render(conservar=True)
        frames = self.salida + ".frames"
        self.assertTrue(os.path.isdir(frames))
        self.assertTrue(any(f.endswith(".png") for f in os.listdir(frames)))

    def test_el_video_lleva_la_firma(self):
        """El contenedor lleva la firma en su comentario (sin reencodear)."""
        self._render()
        leida = firma_de_video(self.salida)
        self.assertIsNotNone(leida, "el video no lleva la firma del plan")
        with open(self.plan, encoding="utf-8") as fh:
            plan = json.load(fh)
        self.assertEqual(leida, firma_plan(plan, None),
                         "la firma estampada no es la del plan")


class TestLaPuertaDetectaElDesfase(unittest.TestCase):
    """La puerta tiene que decir que el video no es de este plan."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="firma_qa_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.plan = os.path.join(self.tmp, "plan.json")
        self.video = os.path.join(self.tmp, "pieza.mp4")
        with open(self.plan, "w", encoding="utf-8") as fh:
            json.dump(PLAN_MIN, fh, ensure_ascii=False)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                        "testsrc=duration=1:size=320x180:rate=10",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", self.video],
                       check=True, capture_output=True, timeout=120)

    def test_un_video_sin_firma_no_rompe_la_comprobacion(self):
        """Un video viejo (sin firma) se comprueba por fecha, como antes."""
        sys.path.insert(0, SCRIPTS)
        import qa_entrega
        self.assertIsNone(qa_entrega._defecto_plan_desincronizado(self.plan, self.video),
                          "un video sin firma no puede dar defecto por firma")

    def test_la_firma_equivocada_es_un_defecto(self):
        """Un video con la firma de OTRO plan es un defecto, con fecha o sin ella."""
        sys.path.insert(0, SCRIPTS)
        sys.path.insert(0, os.path.join(SCRIPTS, "ffmpeg_tools"))
        import qa_entrega
        from _comun import estampar_firma
        estampar_firma(self.video, "firma-de-otro-plan")
        defecto = qa_entrega._defecto_plan_desincronizado(self.plan, self.video)
        self.assertIsNotNone(defecto, "la puerta no ve que el video es de otro plan")
        self.assertIn("firma", defecto.lower())

    def test_la_firma_correcta_no_es_defecto(self):
        """El video de ESTE plan no es un defecto."""
        sys.path.insert(0, SCRIPTS)
        sys.path.insert(0, os.path.join(SCRIPTS, "ffmpeg_tools"))
        import qa_entrega
        from _comun import estampar_firma
        with open(self.plan, encoding="utf-8") as fh:
            plan = json.load(fh)
        estampar_firma(self.video, firma_plan(plan, None))
        self.assertIsNone(qa_entrega._defecto_plan_desincronizado(self.plan, self.video))


if __name__ == "__main__":
    unittest.main()
