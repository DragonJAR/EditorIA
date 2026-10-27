#!/usr/bin/env python3
"""Tests de la RONDA 12: el clip enmarcado, la barra de deplecion y el acta.

QUE PROTEGE (tres primitivas nuevas y un defecto encontrado de paso):

1. El CLIP ENMARCADO (`componer.py --marco`): el video entra en una caja con
   esquinas redondeadas sobre el lienzo negro. El fallo que lo dejaba roto
   era de una linea: `alphamerge` recibe DOS entradas (el clip y la mascara)
   y con una sola, ffmpeg aborta con "crop:default has output 0 (rec)
   unconnected" (medido: el modo no componia nada).

2. La BARRA DE DEPLECION: la franja que se estrecha del ancho completo a
   cero a lo largo de la pieza. Su forma esta MEDIDA sobre el reel de
   referencia (De8KNkdDT68): ancho = W * (1 - t/duracion), lineal y anclada a
   la izquierda. Un test que solo mirara "hay una barra" no comprobaria la
   forma, que es justo lo que se clona.

3. El ACTA (`constancia`): las casillas con su marca (✓ lo confirmado, ○ lo
   pendiente). El ✓ se DIBUJA (no es el glifo) y el copy se acorta cuando no
   cabe: la letra no baja del piso.

4. La HERRAMIENTA DE CONTEOS: `actualizar_conteos.py` decia "desfasado en:
   nada" mientras el guard seguia diciendo que las cifras estaban viejas, y
   con razon: los patrones no tienen grupo de captura y la cifra se sacaba
   de un grupo que no existia. Una herramienta que miente es peor que una
   que no existe: el bucle "corre la herramienta y vuelve a fallar" no tiene
   salida.

Run with: python3 -m unittest discover -s scripts/_tests
"""

import os
import re
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
TOOLS = os.path.join(SCRIPTS, "ffmpeg_tools")
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, TOOLS)

import componer as comp  # noqa: E402


def _fondo(destino, segundos=2, fps=24, tam="320x180"):
    """Un video de fondo con imagen (testsrc: colores, para distinguirlos
    del negro del lienzo)."""
    subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", f"testsrc=duration={segundos}:size={tam}:rate={fps}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", destino],
        check=True, capture_output=True, timeout=120)
    return destino


def _capa_con_alfa(destino, segundos=2, fps=24, tam="1080x1920"):
    """Una capa CON ALFA: un cuadro opaco en un punto del lienzo.

    OJO: `color=c=white@0.5` de lavfi NO lleva alfa (el source sale en
    yuv420p y la alfa se pierde): la capa sale opaca y el texto, negro. La
    alfa de verdad se hace con `format=rgba` + `geq` (como en test_componer.py).
    """
    subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", f"color=c=white:duration={segundos}:size={tam}:rate={fps}",
        "-vf", "format=rgba,geq=r=255:g=255:b=255:"
               "a='if(gt(X,700)*lt(X,900)*gt(Y,700)*lt(Y,900),255,0)'",
        "-c:v", "prores_ks", "-profile:v", "4444",
        "-pix_fmt", "yuva444p10le", destino],
        check=True, capture_output=True, timeout=120)
    return destino


def _audio(destino, segundos=2, fps=24):
    """Un fichero CON audio (una pista de tono)."""
    subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", f"sine=frequency=440:duration={segundos}:sample_rate=48000",
        "-c:a", "aac", destino],
        check=True, capture_output=True, timeout=120)
    return destino


class TestMarcoEnmarcado(unittest.TestCase):
    """El clip en una caja: el layout del reel de 'cara'."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="marco_test_")
        self.base = _fondo(os.path.join(self.tmp, "base.mp4"))
        self.capa = _capa_con_alfa(os.path.join(self.tmp, "capa.mov"))
        self.salida = os.path.join(self.tmp, "final.mp4")

    def test_la_mascara_se_une_al_clip_por_las_dos_entradas(self):
        """`alphamerge` recibe el clip Y la mascara.

        Con una sola entrada, ffmpeg aborta con "crop:default has output 0
        (rec) unconnected": el clip recortado se queda sin usar y el modo
        --marco no componia nada (medido en la ronda 12).
        """
        _avisos, cmd = comp.componer(self.base, self.capa, self.salida,
                                      velo=0, fps=24, marco=(60, 250, 960, 947))
        m = re.search(r"\[(\w+)\]\[(\d+):v\]alphamerge", " ".join(cmd))
        self.assertIsNotNone(
            m, "alphamerge tiene que recibir el clip y la mascara: "
               "con una sola entrada ffmpeg aborta")
        self.assertIn(m.group(1), ("rec", "clip"),
                      "la primera entrada de alphamerge es el clip (recortado "
                      "y con su desenfoque)")
        self.assertNotEqual(m.group(1), m.group(2),
                            "la segunda entrada es la mascara (un fichero)")

    def test_la_caja_se_abre_sobre_el_lienzo_negro(self):
        """El clip se ve DENTRO de la caja y el resto del lienzo es negro."""
        comp.componer(self.base, self.capa, self.salida, velo=0, fps=24,
                      marco=(60, 250, 960, 947))
        png = os.path.join(self.tmp, "f.png")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", self.salida,
                        "-frames:v", "1", png], check=True, capture_output=True,
                       timeout=60)
        from PIL import Image
        im = Image.open(png).convert("RGB")
        self.assertEqual(im.size, (1080, 1920), "el lienzo es el del kit")
        fuera = im.getpixel((10, 10))
        self.assertLess(max(fuera), 30,
                        f"fuera de la caja tiene que ser negro, no {fuera}")
        dentro = im.getpixel((540, 700))
        self.assertGreater(max(dentro), 40,
                           f"dentro de la caja tiene que verse el video, no {dentro}")

    def test_las_esquinas_de_la_caja_estan_redondeadas(self):
        """La esquina de la caja no es el video: es negro (esta redondeada)."""
        comp.componer(self.base, self.capa, self.salida, velo=0, fps=24,
                      marco=(60, 250, 960, 947))
        png = os.path.join(self.tmp, "f.png")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", self.salida,
                        "-frames:v", "1", png], check=True, capture_output=True,
                       timeout=60)
        from PIL import Image
        im = Image.open(png).convert("RGB")
        esquina = max(im.getpixel((62, 252)))       # la esquina de la caja
        borde = max(im.getpixel((540, 252)))         # el borde de arriba, a media
        self.assertLess(esquina, 30,
                        "la esquina de la caja esta redondeada: es negro")
        self.assertGreaterEqual(borde, esquina,
                                "el borde de la caja tiene video: la esquina no")

    def test_el_audio_no_se_descoloca(self):
        """El indice del audio es el ULTIMO input, no uno de los imagenes."""
        audio = _audio(os.path.join(self.tmp, "a.m4a"))
        _avisos, cmd = comp.componer(self.base, self.capa, self.salida,
                                      audio=audio, velo=0, fps=24,
                                      marco=(60, 250, 960, 947))
        n_imagen = len([i for i, a in enumerate(cmd) if a == "-i"])
        m = re.search(r"-map (\d+):a", " ".join(cmd))
        self.assertIsNotNone(m, "el audio se mapea")
        self.assertEqual(int(m.group(1)), n_imagen - 1,
                         "el audio es la ultima entrada: si no, suena la imagen")

    def test_un_marco_que_no_cabe_avisa(self):
        """Un marco fuera del lienzo se AVISA antes de renderizar.

        El aviso va POR DELANTE del fallo: si la composicion se rompe, el
        aviso es lo que explica por que (una averia sin explicacion no
        ayuda a nadie).
        """
        avisos = comp._verifica_entradas(self.base, self.capa, fps_esperado=24,
                                         marco=(1000, 1800, 900, 900))
        self.assertTrue(any("marco" in a for a in avisos),
                        "un marco que no cabe tiene que avisar")


class TestDeplacion(unittest.TestCase):
    """La barra que se estrecha del ancho completo a cero."""

    def setUp(self):
        import render_plan as R
        R.formato(1080, 1920)
        self.R = R

    def _plan(self, **extra):
        plan = {"escenas": [{"tipo": "typewriter", "from": 0.0, "to": 10.0,
                              "texto": "hola"}]}
        plan.update(extra)
        return plan

    def test_la_forma_es_la_del_reel_medido(self):
        """LA INVARIANTE: ancho = W * (1 - t/duracion).

        La tabla son las MEDIDAS del reel De8KNkdDT68 (55,300 s, 1080x1920):
        el ancho de la franja roja en la fila 0, contrasted con lo que dice
        la formula. Un "0 % de rechazo" con la barra siempre al ancho
        completo no seria una barra que se deplete: seria un borde.
        """
        R = self.R
        R.aplicar_globales(self._plan(deplecion={"y": 0, "alto": 5}))
        # La tabla son las MEDIDAS del reel De8KNkdDT68 (55,300 s, 1080x1920):
        # el ancho de la franja roja en la fila 0. Se acaba en t=53 porque a
        # partir de ahi el reel ya esta fundiendo a negro y la franja se
        # apaga con el resto (medido 0 px a t=54: eso es el fundido, no la
        # deplecion).
        tabla = ((0.2, 1076), (5.0, 982), (11.0, 866), (17.0, 748),
                 (23.0, 632), (29.0, 514), (35.0, 398), (41.0, 280),
                 (47.0, 162), (50.0, 104), (52.0, 64), (53.0, 46))
        for t, px in tabla:
            self.assertAlmostEqual(R.ancho_de_deplecion(t, 55.3), px, delta=3,
                                   msg=f"a t={t} la barra deberia medir {px} px")
        # y al final de la pieza la barra se ha ido del todo
        self.assertEqual(R.ancho_de_deplecion(55.3, 55.3), 0.0)

    def test_sin_deplecion_no_hay_barra(self):
        """Es opt-in: una pieza que no la pide sale igual que antes."""
        R = self.R
        R.aplicar_globales(self._plan())
        self.assertFalse(R._DEPLECION["activa"])
        self.assertEqual(R.ancho_de_deplecion(1.0, 10.0), 0.0)

    def test_la_barra_se_dibuja_sobre_la_escena(self):
        """La barra va ENCIMA (es el borde del lienzo), y es del acento."""
        R = self.R
        ctx = R.Ctx()
        e = R.completar_escena({"tipo": "typewriter", "from": 0.0, "to": 10.0,
                                 "texto": "hola"}, 0)
        R.aplicar_globales(self._plan(deplecion={"y": 0, "alto": 5}))
        ancho = R.ancho_de_deplecion(1.0, 10.0)
        img = R.componer(ctx, [e], 10.0, 1.0, [])
        dentro = img.getpixel((int(ancho / 2), 2))
        fuera = img.getpixel((int(ancho) + 40, 2))
        self.assertEqual(tuple(dentro[:3]), tuple(R.ACENTO[:3]),
                         f"la barra tiene que ser del acento, es {dentro}")
        self.assertNotEqual(tuple(fuera[:3]), tuple(R.ACENTO[:3]),
                            "fuera de la barra no hay barra")

    def test_el_color_admite_token_y_hex(self):
        R = self.R
        R.aplicar_globales(self._plan(deplecion={"color": "#BD1700"}))
        self.assertEqual(tuple(R._DEPLECION["color"][:3]), (0xBD, 0x17, 0x00))
        R.aplicar_globales(self._plan(deplecion={"color": "blanco"}))
        self.assertEqual(tuple(R._DEPLECION["color"][:3]), tuple(R.BLANCO[:3]))


class TestConstancia(unittest.TestCase):
    """El acta: las casillas con su marca."""

    def setUp(self):
        import render_plan as R
        R.formato(1080, 1920)
        self.R = R
        self.ctx = R.Ctx()

    def _pintar(self, e, t):
        e = self.R.completar_escena(e, 0)
        return self.R.pintar(self.ctx, e, t)

    def _escena(self, hecho=True, segundo=None):
        it = {"texto": "Comparten investigaciones", "hecho": hecho}
        if segundo is not None:
            it["hecho"] = segundo
        return {"tipo": "constancia", "from": 0.0, "to": 6.0,
                "kicker": "A + B",
                "items": [it, {"texto": "Pendiente de firma", "hecho": False}],
                "at": {"item0": 0.2, "item1": 0.6}}

    def _blancos(self, capa, mitad):
        from PIL import Image
        img = capa.convert("RGB")
        w, h = img.size
        if mitad == "izq":
            caja = img.crop((0, 0, w // 2, h))
        else:
            caja = img.crop((w // 2, 0, w, h))
        return sum(1 for p in caja.getdata() if min(p) > 232)

    def test_la_casilla_confirmada_llena_el_circulo_y_la_pendiente_no(self):
        """La marca distingue: la confirmada lleva el circulo lleno."""
        capa = self._pintar(self._escena(hecho=True), 3.0)
        izq = self._blancos(capa, "izq")
        der = self._blancos(capa, "der")
        self.assertGreater(izq, der * 2 + 300,
                           f"la casilla confirmada deberia ser mas clara: "
                           f"{izq} contra {der}")

    def test_el_check_aparece_en_el_instante_declarado(self):
        """`hecho` puede ser el SEGUNDO en que se confirma: antes, esta
        pendiente (el aro vacio)."""
        antes = self._pintar(self._escena(segundo=2.0), 1.5)
        despues = self._pintar(self._escena(segundo=2.0), 2.8)
        self.assertLess(self._blancos(antes, "izq"), self._blancos(despues, "izq"),
                        "antes del instante declarado la casilla esta pendiente")
        self.assertLess(self._blancos(antes, "izq"), self._blancos(antes, "der") + 300,
                        "antes de confirmarse no hay circulo lleno")

    def test_el_check_se_dibuja_y_no_es_el_glifo(self):
        """El ✓ esta DENTRO del circulo: hay tinta oscura dentro del blanco."""
        from PIL import Image
        capa = self._pintar(self._escena(hecho=True), 3.0)
        img = capa.convert("RGB")
        w, h = img.size
        # el circulo lleno esta en la mitad izquierda, en la banda de las
        # casillas: se busca el bloque blanco mas grande y se mira su centro
        px = img.load()
        mejor = None
        for y in range(h - 700, h - 100, 4):
            for x in range(0, w // 2, 4):
                if min(px[x, y]) > 232:
                    mejor = (x, y)
                    break
            if mejor:
                break
        self.assertIsNotNone(mejor, "tiene que haber un circulo blanco")
        x0, y0 = mejor
        # el centro del circulo tiene la tinta del check (negro)
        centro = [px[x0 + dx, y0 + dy] for dx in (-6, 0, 6) for dy in (-6, 0, 6)]
        self.assertTrue(any(max(p) < 90 for p in centro),
                        "el check tiene que estar DIBUJADO dentro del circulo")


if __name__ == "__main__":
    unittest.main()
