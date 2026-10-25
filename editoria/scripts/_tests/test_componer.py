#!/usr/bin/env python3
"""Tests de `ffmpeg_tools/componer.py` — la composicion de la tipografia
sobre el footage.

QUE PROTEGE
  La receta (desenfoque SOLO detras de la letra, velo suave, la capa con
  alfa) vivia en la prosa y en el script del demo: dos copias. Si la copia
  que se ejecuta se rompe, la pieza sale con la tipografia encima de un
  rectangulo (o con fondo negro) y NADIE lo nota hasta que se entrega.

  Estos tests la EJECUTAN: hacen un fondo, hacen una capa con alfa, componen
  y miran el resultado. Un test que solo comprobara que el script responde
  no probaria nada.

  Y los tres errores que rompen la pieza se avisan ANTES de renderizar:
  · tasas distintas (tirones, que el medidor de movimiento cuenta);
  · una capa sin alfa (el texto sale con fondo negro);
  · tamaños distintos (se componen desajustados).

Run with: python3 -m unittest discover -s scripts/_tests
"""

import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
TOOLS = os.path.join(SCRIPTS, "ffmpeg_tools")
COMPONER = os.path.join(TOOLS, "componer.py")

sys.path.insert(0, TOOLS)
import componer as comp  # noqa: E402


def _fondo(destino, segundos=2, fps=24, tam="320x180"):
    """Un video de fondo con imagen y audio."""
    subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", f"testsrc=duration={segundos}:size={tam}:rate={fps}",
        "-f", "lavfi", "-i", f"sine=frequency=440:duration={segundos}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", destino],
        check=True, capture_output=True, timeout=120)
    return destino


def _capa_con_alfa(destino, segundos=2, fps=24, tam="320x180"):
    """Una capa CON ALFA: un cuadro de color con transparencia (Prores 4444)."""
    subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", f"color=c=white@0.5:duration={segundos}:size={tam}:rate={fps}",
        "-f", "lavfi", "-i", f"color=c=black@0.0:duration={segundos}:size={tam}:rate={fps}",
        "-filter_complex", "[0:v][1:v]overlay=format=auto,format=rgba[v]",
        "-map", "[v]", "-c:v", "prores_ks", "-profile:v", "4444",
        "-pix_fmt", "yuva444p10le", destino],
        check=True, capture_output=True, timeout=120)
    return destino


def _fondo_rayado(destino, segundos=2, fps=24, tam="640x360"):
    """Un fondo de RAYADO de 1 px: la nitidez maxima.

    Sirve para medir la profundidad sin ambiguedad: un desenfoque se lleva
    por delante el rayado (la nitidez cae) y donde no hay letra el rayado
    sigue ahi (la nitidez se queda). Con un fondo "de foto" la diferencia es
    un ojo y el test pasa siempre: un guard que pasa siempre no mide nada.
    """
    subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", f"color=c=gray:s={tam}:r={fps}",
        "-vf", "geq=lum='mod(X+Y,2)*255'",
        "-t", str(segundos), "-c:v", "libx264", "-pix_fmt", "yuv420p", destino],
        check=True, capture_output=True, timeout=120)
    return destino


def _capa_media(destino, segundos=2, fps=24, tam="640x360"):
    """Una capa que cubre SOLO la mitad IZQUIERDA, con alfa.

    Sirve para medir la profundidad: la zona con letra tiene que quedar
    DESENFOCADA y la zona sin letra NITIDA. Si la mascara se rompe (y se
    desenfoca todo, o no se desenfoca nada), las dos mitades salen iguales.

    La capa tiene el MISMO tamano que el fondo: la composicion no reescala
    (una capa mas pequena que el fondo no se puede componer).
    """
    subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", f"color=c=white:duration={segundos}:size={tam}:rate={fps}",
        "-vf", "format=rgba,geq=r=255:g=255:b=255:a='if(lt(X,W/2),128,0)'",
        "-c:v", "prores_ks", "-profile:v", "4444",
        "-pix_fmt", "yuva444p10le", destino],
        check=True, capture_output=True, timeout=120)
    return destino


def _nitidez(video, mitad, margen=60):
    """La nitidez (desviacion de los bordes) del INTERIOR de una mitad.

    El margen de 60 px descarta el borde de la capa: si no, ese escalon
    blanco domina la medida y el test no distingue una cosa de la otra.
    """
    from PIL import Image, ImageFilter
    import io
    import statistics
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", video,
                        "-vframes", "1", "-f", "image2pipe", "-vcodec", "png", "-"],
                       capture_output=True, timeout=120)
    img = Image.open(io.BytesIO(r.stdout)).convert("L")
    w, h = img.size
    if mitad == "izq":
        zona = img.crop((margen, margen, w // 2 - margen, h - margen))
    else:
        zona = img.crop((w // 2 + margen, margen, w - margen, h - margen))
    bordes = list(zona.filter(ImageFilter.FIND_EDGES).getdata())
    return statistics.pstdev(bordes) if bordes else 0.0


def _capa_sin_alfa(destino, segundos=2, fps=24, tam="320x180"):
    """Una capa OPACA: un mp4 no lleva alfa (y por eso avisa la herramienta)."""
    subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", f"color=c=white:duration={segundos}:size={tam}:rate={fps}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", destino],
        check=True, capture_output=True, timeout=120)
    return destino


class TestComponerReal(unittest.TestCase):
    """La composicion se EJECUTA: se mira el fichero que sale."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="componer_test_")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_compone_la_capa_sobre_el_fondo(self):
        base = _fondo(os.path.join(self.tmp, "base.mp4"))
        capa = _capa_con_alfa(os.path.join(self.tmp, "capa.mov"))
        salida = os.path.join(self.tmp, "final.mp4")
        avisos, _cmd = comp.componer(base, capa, salida, velo=0, fps=24)
        self.assertTrue(os.path.isfile(salida), "la composicion no produjo el fichero")
        self.assertEqual(avisos, [], f"una composicion limpia no avisa: {avisos}")
        self.assertGreater(os.path.getsize(salida), 1000)

    def test_el_video_de_entrada_no_se_toca(self):
        base = _fondo(os.path.join(self.tmp, "base.mp4"))
        capa = _capa_con_alfa(os.path.join(self.tmp, "capa.mov"))
        antes = os.path.getsize(base)
        mtime = os.path.getmtime(base)
        comp.componer(base, capa, os.path.join(self.tmp, "final.mp4"), velo=0, fps=24)
        self.assertEqual(os.path.getsize(base), antes,
                         "la composicion toco el video de entrada")
        self.assertEqual(os.path.getmtime(base), mtime,
                         "la composicion toco el video de entrada")

    def test_avisa_si_las_tasas_no_casan(self):
        base = _fondo(os.path.join(self.tmp, "base.mp4"), fps=24)
        capa = _capa_con_alfa(os.path.join(self.tmp, "capa.mov"), fps=30)
        avisos = comp._verifica_entradas(base, capa)
        self.assertTrue(any("fps" in a for a in avisos),
                        f"unas tasas distintas tienen que avisar: {avisos}")

    def test_avisa_si_la_capa_no_lleva_alfa(self):
        base = _fondo(os.path.join(self.tmp, "base.mp4"))
        capa = _capa_sin_alfa(os.path.join(self.tmp, "capa.mp4"))
        avisos = comp._verifica_entradas(base, capa)
        self.assertTrue(any("alfa" in a for a in avisos),
                        f"una capa sin alfa tiene que avisar: {avisos}")

    def test_avisa_si_los_tamanos_no_casan(self):
        base = _fondo(os.path.join(self.tmp, "base.mp4"), tam="320x180")
        capa = _capa_con_alfa(os.path.join(self.tmp, "capa.mov"), tam="640x360")
        avisos = comp._verifica_entradas(base, capa)
        self.assertTrue(any("se componen desajustados" in a for a in avisos),
                        f"unos tamanos distintos tienen que avisar: {avisos}")

    def test_una_composicion_limpia_no_avisa(self):
        base = _fondo(os.path.join(self.tmp, "base.mp4"))
        capa = _capa_con_alfa(os.path.join(self.tmp, "capa.mov"))
        self.assertEqual(comp._verifica_entradas(base, capa), [])

    def test_el_fondo_se_desenfoca_SOLO_DETRAS_DE_LA_LETRA(self):
        """La invariante de la composicion: hay PROFUNDIDAD, y SOLO hay alla.

        Detras de la letra el fondo tiene que estar DESENFOCADA; donde no
        hay letra tiene que seguir NITIDO. Son las DOS mitades de lo mismo:
        un desenfoque que se come el cuadro entero (mascara llena) y un
        desenfoque que no ocurre (mascara vacia) rompen la pieza de forma
        distinta, y el test caza las dos.

        El fondo es de RAYADO de 1 px porque la medida tiene que separar
        "desenfocado" de "nítido" sin interpretacion. Medido con esta
        fixture:
          · la mascara correcta:  83,5 la mitad con letra, 126,9 la otra;
          · la mascara vacia:     126,7 y 126,9 (no desenfoca nada);
          · la mascara llena:      29,5 y 41,4 (desenfoca todo).
        """
        base = _fondo_rayado(os.path.join(self.tmp, "base.mp4"))
        capa = _capa_media(os.path.join(self.tmp, "capa.mov"))
        salida = os.path.join(self.tmp, "final.mp4")
        comp.componer(base, capa, salida, velo=0, fps=24)

        nitidez_izq = _nitidez(salida, "izq")    # la mitad con letra
        nitidez_der = _nitidez(salida, "der")    # la mitad sin letra

        # detras de la letra: el fondo esta desenfocado
        self.assertLess(nitidez_izq, nitidez_der * 0.85,
                        f"detras de la letra el fondo tiene que estar "
                        f"desenfocado (izq={nitidez_izq:.1f}, "
                        f"der={nitidez_der:.1f})")
        # donde no hay letra: el fondo sigue nitido (no se desenfoca todo)
        nitidez_fondo = _nitidez(base, "der")
        self.assertGreater(nitidez_der, nitidez_fondo * 0.85,
                           f"donde no hay letra el fondo tiene que seguir "
                           f"nitido (der={nitidez_der:.1f}, "
                           f"fondo={nitidez_fondo:.1f})")

    def test_la_mascara_del_alfa_usa_la_escala_del_filtro(self):
        """La mascara sale en 0-255, que es la escala del filtro `lut`.

        Este es el defecto que la receta arrastraba desde la prosa: la
        expresion devolvia 0-1 (`min(1,(val-28)/130)`), y en la escala del
        filtro eso es CERO: la mascara salia vacia y el fondo NO se
        desenfocaba detras de la letra. La pieza se veia bien igual porque
        el velo y el texto tapaban lo que faltaba, y nadie lo midio.
        """
        cadena = comp.cadena_mascara()
        self.assertIn("min(255,", cadena,
                      "la mascara tiene que salir en la escala 0-255 del lut")
        self.assertNotIn("min(1,", cadena,
                         "un 0-1 en el lut es un 0: la mascara saldria vacia")


class TestVelo(unittest.TestCase):
    """El velo: la capa suave que hace que la caja blanca lea sobre la foto."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="velo_test_")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_el_velo_es_un_png_con_alfa(self):
        ruta = comp.velo_png(os.path.join(self.tmp, "velo.png"), 320, 180, 1.0)
        self.assertTrue(os.path.isfile(ruta))
        from PIL import Image
        img = Image.open(ruta)
        self.assertEqual(img.size, (320, 180))
        self.assertIn("A", img.mode, "el velo tiene que llevar canal alfa")

    def test_el_velo_es_mas_fuerte_arriba_y_abajo(self):
        """El velo cumple su trabajo: donde esta la tipografia hay mas velo."""
        ruta = comp.velo_png(os.path.join(self.tmp, "velo.png"), 320, 180, 1.0)
        from PIL import Image
        alfa = Image.open(ruta).getchannel("A")
        ancho, alto = alfa.size
        arriba = alfa.getpixel((ancho // 2, 2))
        medio = alfa.getpixel((ancho // 2, alto // 2))
        abajo = alfa.getpixel((ancho // 2, alto - 3))
        self.assertGreater(arriba, medio,
                           "arriba tiene que estar mas velado que el centro")
        self.assertGreater(abajo, medio,
                           "abajo tiene que estar mas velado que el centro")

    def test_la_fuerza_cero_deja_el_velo_transparente(self):
        ruta = comp.velo_png(os.path.join(self.tmp, "velo.png"), 320, 180, 0.0)
        from PIL import Image
        alfa = Image.open(ruta).getchannel("A")
        self.assertEqual(alfa.getpixel((160, 2)), 0)


class TestCLI(unittest.TestCase):
    """La CLI: lo que el agente copia y pega."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="componer_cli_")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_ayuda_sin_traceback(self):
        r = subprocess.run([sys.executable, COMPONER, "--help"],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("componer", r.stdout.lower() + r.stderr.lower())

    def test_un_fichero_que_no_existe_no_tiene_traceback(self):
        r = subprocess.run([sys.executable, COMPONER, "no-existe.mp4",
                            "tampoco.mov", "-o", os.path.join(self.tmp, "o.mp4")],
                           capture_output=True, text=True, timeout=60)
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn("Traceback", r.stderr, "un error de usuario no es un traceback")


if __name__ == "__main__":
    unittest.main()
