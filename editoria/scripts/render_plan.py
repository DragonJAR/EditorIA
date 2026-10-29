#!/usr/bin/env python3
"""EditorIA plan renderer — ejecuta un plan.json con fluidez total.
Identidad desde brand pack opcional (--brand o campo "brand" en el plan);
sin pack, usa los defaults neutros del renderer.
Uso: python render_plan.py plan.json -o salida.mp4 [--fps 30] [--brand brand/otro.json]
"""
import os, math, json, random, re, sys, argparse
try:
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
except ModuleNotFoundError as _e_dep:
    if __name__ == "__main__" and "-h" not in sys.argv and "--help" not in sys.argv:
        sys.exit(f"ERROR: falta dependencia ({_e_dep.name}): pip install pillow numpy")
    np = Image = ImageDraw = ImageFont = ImageFilter = ImageChops = None

# ---------- identidad: defaults NEUTROS; el brand pack los sobreescribe ----------
# Sin pack (modo libre) nada de marca: acento neutro y fuentes empaquetadas.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg_tools"))
from _plataforma import resolver_fuente
from _comun import NEUTRO, aplicar_grano, segmentos_enfasis, segmentos_resalte  # paleta, grano y markup * ~ ^
ACENTO=NEUTRO["acento"]; ACENTO_OSC=NEUTRO["acento_oscuro"]; NEGRO=NEUTRO["negro"]
BLANCO=NEUTRO["blanco"]; GRIS=NEUTRO["gris"]; PANEL=(26,26,26); PANEL2=(38,38,38)

# ---------- tokens de categoría y de estado (references/paleta.md) ----------
# Las escenas de datos necesitan MÁS de un color (porciones, temperaturas,
# un "pagado"): antes cada una traía sus RGB a mano y no seguían a la marca.
# Se derivan del acento: SERIE[0] es el acento y el resto sale de Okabe-Ito
# (la paleta categórica pensada para daltonismo), eligiendo cada vez el que
# más se aleja de los ya elegidos con visión normal Y simulada. EXITO y AVISO
# son su verde y su naranja. Todos suben de luz hasta leerse sobre el fondo.
# Un pack puede declararlos en `colores` (serie, exito, aviso) y entonces mandan.
OKABE_ITO=((230,159,0),(86,180,233),(0,158,115),(240,228,66),(0,114,178),(213,94,0),(204,121,167))
_DEUTERANOPIA=((0.367322,0.860646,-0.227968),(0.280085,0.672501,0.047413),(-0.011820,0.042940,0.968881))
_PROTANOPIA=((0.152286,1.052583,-0.204868),(0.114503,0.786281,0.099216),(-0.003882,-0.048116,1.051998))
N_SERIE=5

def _simula(c,m):
    """El color como lo ve una visión de dos conos (Machado 2009, sRGB lineal)."""
    li=[(v/255)/12.92 if v/255<=0.04045 else ((v/255+0.055)/1.055)**2.4 for v in c[:3]]
    out=[]
    for fila in m:
        x=max(0.0,min(1.0,sum(k*v for k,v in zip(fila,li))))
        out.append(255*(12.92*x if x<=0.0031308 else 1.055*x**(1/2.4)-0.055))
    return out

def distancia_daltonica(a,b):
    """La PEOR distancia RGB entre dos colores: visión normal, deuteranopía y
    protanopía. Dos categorías que se confunden en una de las tres se confunden."""
    def d(p,q): return math.dist(p[:3],q[:3])
    return min(d(a,b),d(_simula(a,_DEUTERANOPIA),_simula(b,_DEUTERANOPIA)),
               d(_simula(a,_PROTANOPIA),_simula(b,_PROTANOPIA)))

def _legible(c,fondo,minimo=4.5):
    """Sube la luz (HLS, mismo tono) hasta que el color se lee sobre el fondo."""
    import colorsys
    from _comun import contraste
    h,l,s=colorsys.rgb_to_hls(*[v/255 for v in c[:3]])
    rgb=tuple(c[:3])
    while contraste(rgb,fondo)<minimo and l<0.97:
        l+=0.01; rgb=tuple(int(round(v*255)) for v in colorsys.hls_to_rgb(h,l,s))
    return rgb

def tokens_de_estado(acento,negro):
    """{serie, exito, aviso} derivados del acento (ver el bloque de arriba)."""
    pool=[_legible(c,negro) for c in OKABE_ITO]
    serie=[tuple(acento[:3])]
    while len(serie)<N_SERIE:
        c=max(pool,key=lambda p:min(distancia_daltonica(p,q) for q in serie))
        serie.append(c); pool.remove(c)
    return {"serie":serie,"exito":_legible(OKABE_ITO[2],negro),"aviso":_legible(OKABE_ITO[0],negro)}

_ESTADO=tokens_de_estado(ACENTO,NEGRO)
SERIE=_ESTADO["serie"]; EXITO=_ESTADO["exito"]; AVISO=_ESTADO["aviso"]

def colores_de(valor):
    """La lista de colores de un parámetro de escena: "serie" (la de la marca),
    una lista de RGB/hex, o None."""
    if valor is None: return None
    if valor=="serie": return [tuple(c) for c in SERIE[:4]]
    return [hex_a_rgb(c) if isinstance(c,str) else tuple(c) for c in valor]

FJ=resolver_fuente("Plus Jakarta Sans", generica="sans-bold")
FJI=None   # display en itálica: la trae el pack si la declara ("titulares_itálica")
FM=resolver_fuente("Montserrat", generica="sans")
MONO=resolver_fuente("DejaVu Sans Mono", "Consolas", "Menlo", generica="mono")
LOGO=None; ISOTIPO=None; MARCA_NOMBRE=None
TRANSICIONES="libre"   # idioma de transición; el pack puede fijar "corte_seco"
ALFA=False   # salida .webm/.mov: overlay transparente (sin fondo vivo, salida por alfa)

# Las reglas que declara un pack (`reglas`) se dividen en dos familias, y hay
# que saber en cuál está cada una: si el motor la aplica, se cumple siempre; si
# es guía del agente, depende de que el agente la lea. Una regla que nadie
# aplica es una promesa que nadie cumple: por eso la lista vive AQUÍ y el test
# la comprueba contra lo que dice references/brand-packs.md y contra lo que
# declara cada pack (si un pack declara una regla que no está en ninguna de
# las dos listas, nadie la cumple).
REGLAS_DEL_MOTOR = {"transiciones"}          # el motor las lee y las hace cumplir
REGLAS_DEL_AGENTE = {"rejillas_decorativas", # guia del agente: las lee el que
                      "efectos_glitch",      # escribe el plan, no el motor
                      "isotipo_con_protagonista"}
REGLAS_DEL_PACK = REGLAS_DEL_MOTOR | REGLAS_DEL_AGENTE

# El copy que el motor recortó en el render actual. Un recorte es legal (la
# pieza sigue siendo legible) pero es una pérdida de copy: si no se anota,
# nadie se entera hasta que lee la pieza.
RECORTES=[]

W,H=1080,1920
MARGEN=151   # margen lateral seguro simétrico (unión Reels/TikTok/Shorts, ver _delivery.py)
SAFE={"top":192,"bottom":422,"left":151,"right":151}   # zona segura en px (se recalcula en main)
CENTRO_Y=0.45   # ancla vertical (fracción de H) de la escala y la cámara: el centro
                # de la zona segura de 9:16 cae ahí ((192 + 1498) / 2 = 0.44·H)

# ESCALA TIPOGRÁFICA — una sola fuente de verdad para todo el catálogo.
# Antes cada escena fijaba sus propios tamaños a mano y el mismo rol (un
# nombre, un detalle, un estado) salía a 26, 27, 28, 30, 32, 34, 36, 40 o 44
# según la escena: el ojo lo lee como "cada plano usa su propia tipografía".
# Ahora un rol = un tamaño, y el piso (28) queda por encima del mínimo
# legible (LETRA_MIN=26) con margen.
ESCALA={
    "titular":    120,   # titular cinético (auto-fit; el copy lo acorta, no el motor)
    "rotulo":      44,   # kicker de la escena, siempre en y=H*0.20
    "dato":        36,   # valor principal, nombre de la persona, etiqueta de boton
    "secundario":  32,   # cuerpo: mensajes, titulos de item, pares clave-valor
    "nota":        28,   # apoyo: estado, detalle, fecha, caption
}
MIN_LETRA=26   # piso de LETRA LEGIBLE: lo mide el QA (LETRA_MIN, misma cifra)
TAM_CHECK=14   # glifo "✓" de verificado, dentro de un badge de 18 px. NO es
                # texto (no tiene alfanumericos): no cuenta para el piso de
                # letra legible, igual que lo excluye la medicion del QA.
                # Un glifo es un simbolo, no una palabra que se pueda leer.
TAM_MIN_ROTULO=30   # hasta donde puede encogerse un rótulo para caber en la zona segura
ELEV=30        # elevación de entrada (px) en fade+resorte: una sola cifra
               # para titular, rótulo y grupos (antes 30/24/24)
STAGGER=0.06   # s entre items de una lista o grilla (animacion.md §4: 40-90 ms).
               # Antes cada escena escribía su `i*0.xx` (0.08-0.40 s): una lista
               # de cuatro filas tardaba 1.2 s en armarse y se leía lenta.

def escalonado(at, clave, i, base):
    """Instante de entrada del item `i` de una cascada: el `at` explícito del
    plan manda (`item2`); si no, sigue a `<clave>0` (o `base`) a paso STAGGER.
    Así un plan que solo fija cuándo empieza la lista hereda la cadencia."""
    return at.get(f"{clave}{i}", at.get(f"{clave}0", base) + i * STAGGER)

def zona_segura(plataforma):
    """Márgenes seguros en px desde la tabla canónica (_delivery.py).
    'vertical' = unión de reels/tiktok/shorts; los laterales se hacen simétricos
    (composición centrada) tomando el mayor."""
    import _delivery as D
    plats=["reels","tiktok","shorts"] if plataforma=="vertical" else [plataforma]
    m={"top":0,"bottom":0,"left":0,"right":0}
    for p_ in plats:
        sm=D.safe_margins_px(p_,W,H)
        for k in m: m[k]=max(m[k],sm[k])
    lat=max(m["left"],m["right"]); m["left"]=m["right"]=lat
    return m
random.seed(11)

_FONT_CACHE={}
def _fuente_minima(s):
    try: return ImageFont.load_default(size=s)   # Pillow >= 10.1
    except TypeError: return ImageFont.load_default()
def font(p,s,w=700):
    # tamaño a 1/4 px (Pillow acepta fraccionarios): int() hacía que todo texto
    # que escala (palabras, slams, la marca) avanzara a saltos de 1 px
    s=max(8.0,round(s*4)/4); key=(p,s,w)
    if key in _FONT_CACHE: return _FONT_CACHE[key]
    try: f=ImageFont.truetype(p,s) if p else _fuente_minima(s)
    except OSError: f=_fuente_minima(s)
    _FONT_CACHE[key]=f
    try: f.set_variation_by_axes([w])
    except Exception: pass
    return f

# ---------- motor de fluidez ----------
def ease_in_out(p):
    p=max(0,min(1,p)); return 4*p**3 if p<0.5 else 1-(-2*p+2)**3/2
def ease_out(p):
    p=max(0,min(1,p)); return 1-(1-p)**3
def curva_overshoot(p, s=1.70158):
    """Curva de overshoot paramétrica (Back Out). p en [0, 1]. s define la amplitud del rebote."""
    p = max(0.0, min(1.0, float(p))) - 1.0
    return p * p * ((s + 1.0) * p + s) + 1.0

def prog(t,a,b,e=ease_in_out):
    if b<=a: return 1.0 if t>=b else 0.0
    return e((t-a)/(b-a))
def spring(t,t0,stiff=120,damp=13):
    """Resorte subamortiguado 0->1 con overshoot. La base de la fluidez."""
    if t<=t0: return 0.0
    dt=t-t0; w=math.sqrt(stiff); d=damp/(2*w)
    if d>=1: return 1-math.exp(-w*dt)*(1+w*dt)
    wd=w*math.sqrt(1-d*d)
    return 1-math.exp(-d*w*dt)*(math.cos(wd*dt)+d*w/wd*math.sin(wd*dt))


# SISTEMA DE MOVIMIENTO — el gesto de la casa, con nombre.
# Antes cada escena inventaba su resorte (23 combinaciones distintas: el
# overshoot iba del 3 % al 20 % y la calma del 0.17 s al 0.40 s). El ojo no
# ve los numeros: ve que un plano "rebota" y el siguiente "se asienta", y esa
# incoherencia se lee como "cada escena la hizo alguien distinto". Ahora hay
# SEIS gestos, y el rol lo elige lo que el elemento ES.
#
#   rol        resorte        overshoot  calma   para que
#   titular    (150, 15)        8.8 %    0.23 s  la frase que abre la pieza
#   bloque     (120, 15)        5.2 %    0.29 s  una tarjeta, una ficha, un precio
#   elemento   (110, 14)        6.0 %    0.29 s  un chip, un dato, un boton, una burbuja
#   suave      (130, 16)        4.5 %    0.28 s  entra sin robar atencion (pies, subtitulos)
#   pop        (150, 13)       14.0 %    0.20 s  el dato que QUIERE que lo mires (un landing)
#   lento      ( 70, 12)        3.9 %    0.40 s  el ritmo de los libros: abrir y cerrar sin prisa
#
# REGLA: un elemento entra con `entra(t, instante, "rol")`. Si necesitas un
# gesto nuevo, primero pregunta si de verdad es un rol nuevo: casi siempre
# es uno de estos seis con otra intencion.
MOVIMIENTO = {
    "titular":  (150, 15),
    "bloque":   (120, 15),
    "elemento": (110, 14),
    "suave":    (130, 16),
    "pop":      (150, 13),
    "lento":    ( 70, 12),
}


def entra(t, t0, rol="bloque"):
    """Entrada de un elemento con el gesto del ROL (MOVIMIENTO)."""
    stiff, damp = MOVIMIENTO[rol]
    return spring(t, t0, stiff, damp)


def latido(t, t0=0.0, periodo=1.6, amp=0.10):
    """Vida suave en el hold: 1±amp, sin inventar un resorte nuevo.

    Las escenas que se asientan (frase, index, camino, gauge…) no pueden
    quedar congeladas: el medidor lo lee como tiempo muerto. Un seno lento
    sobre el acento / el trazo activo mantiene el cuadro vivo sin robar
    protagonismo al dato. DRY: una sola curva; cada escena elige qué pintar
    con ella (alfa del subrayado, grosor de la cabeza, brillo del activo).
    """
    if t < t0:
        return 1.0
    return 1.0 + amp * math.sin(2 * math.pi * (t - t0) / max(0.2, float(periodo)))


def track(t,paradas,stiff=260,damp=26):
    """Resorte MULTI-DESTINO: un resorte por cambio, sumados.

    Cuando un valor cambia de objetivo varias veces (un cursor que visita
    tres puntos, una caja que crece y despues encoge, una barra que salta),
    NO se reinicia el resorte: se suma un resorte por cambio, cada uno con
    su instante. Asi el movimiento sigue siendo continuo (nada se frena en
    seco entre tramos) y sigue siendo FUNCION PURA DEL TIEMPO: el frame 812
    se pinta sin simular los 811 anteriores, que es lo que permite el
    render incremental y el cache de frames.

    `paradas` es una lista [(instante, valor), ...] ordenada por instante.
    stiff=260 / damp=26 -> 1,4% de overshoot y asienta en 0,33 s: llega
    con peso y se calma, sin rebote visible. stiff=150 / damp=15 (el
    default de la casa) sobresale un 8,8%: ese es el salto del titular.
    """
    if not paradas: return 0.0
    v=paradas[0][1]
    for i in range(1,len(paradas)):
        t0,val=paradas[i]
        v+=(val-paradas[i-1][1])*spring(t,t0,stiff,damp)
    return v
def clamp01(x): return max(0,min(1,x))
def lerp(a,b,k): return a+(b-a)*k
def flota(t,t0,amp=6,freq=0.45):
    """Flotación idle: respiración sutil cuando el elemento ya asentó."""
    if t<=t0: return 0.0
    return amp*math.sin(2*math.pi*freq*(t-t0))

def salto_arco(x0, y0, x1, y1, p, altura=35.0):
    """Trayectoria parabólica 2D de (x0, y0) a (x1, y1) con pico de arco en el punto medio."""
    p = max(0.0, min(1.0, float(p)))
    x = x0 + (x1 - x0) * p
    y = y0 + (y1 - y0) * p - altura * 4.0 * p * (1.0 - p)
    return (x, y)

def flash_impacto(layer, t, t_hit, dur=0.22, color=(255, 255, 255), max_alpha=110):
    """Destello de impacto con curva ADSR (ataque rápido, caída suave) sobre el layer."""
    if t < t_hit or t > t_hit + dur:
        return layer
    dt = t - t_hit
    t_atk = dur * 0.15
    if dt < t_atk:
        al = (dt / t_atk) * max_alpha
    else:
        al = ((dur - dt) / (dur - t_atk)) ** 1.8 * max_alpha
    al = int(max(0, min(255, al)))
    if al <= 0:
        return layer
    flash = Image.new("RGBA", layer.size, color[:3] + (al,))
    layer.alpha_composite(flash)
    return layer

# ---------- texto con énfasis *...* ----------
segs=segmentos_enfasis   # '*palabra*' = énfasis en acento (una sola implementación)
def seg_width(sg,fnt):
    tmp=ImageDraw.Draw(Image.new("L",(10,10)))
    return sum(tmp.textlength(t,font=fnt) for t,_ in sg)
def draw_seg(d,xy,sg,fnt,fill,emph_fill,anchor="la",spacing=0):
    x,y=xy; tmp=ImageDraw.Draw(Image.new("L",(10,10)))
    if anchor=="ma":
        x-= (seg_width(sg,fnt)+spacing*(sum(len(t) for t,_ in sg)-1))/2
    for t,em in sg:
        for ch in t:
            d.text((x,y),ch,font=fnt,fill=emph_fill if em else fill)
            x+=tmp.textlength(ch,font=fnt)+spacing

class Ctx:
    def __init__(self):
        if Image is None or np is None:
            sys.exit("ERROR: falta dependencia (PIL/numpy): pip install pillow numpy")
        self.fT=lambda s,w=800: font(FJ,s,w)
        self.fTi=lambda s,w=800: font(FJI or FJ,s,w)   # display en itálica (si el pack la trae)
        self.fX=lambda s,w=600: font(FM,s,w)
        self.fM=lambda s,w=700: font(MONO,s,w)
        self.tmp=ImageDraw.Draw(Image.new("L",(10,10)))
        # blobs suaves del fondo (se generan una vez)
        self.blob_big=self._blob(560,ACENTO+(46,))
        self.blob_mid=self._blob(380,ACENTO+(30,))
        self.blob_wht=self._blob(420,(250,248,246,14))
        self.mota_acento=self._blob(9,ACENTO+(70,))       # objetos de ambiente del mundo
        self.mota_blanca=self._blob(7,(250,248,246,60))
        # viñeta precomputada (blur 220 por frame sería inviable)
        vig=Image.new("L",(W,H),0); dv=ImageDraw.Draw(vig)
        dv.ellipse([-W*0.25,-H*0.12,W*1.25,H*1.12],fill=255)
        vig=vig.filter(ImageFilter.GaussianBlur(220))
        self.vig_mask=Image.eval(vig,lambda v:int(v*0.55+115))
        self.vig_negro=Image.new("RGBA",(W,H),(0,0,0,255))
        self.logo=self._img(LOGO); self.iso=self._img(ISOTIPO)
    @staticmethod
    def _img(p):
        if not p: return None
        try:
            im=Image.open(p).convert("RGBA"); bb=im.getbbox()
            return im.crop(bb) if bb else im
        except Exception: return None
    def _blob(self,r,color):
        # Gradiente radial continuo (numpy) + dither: sin bandas concéntricas.
        import numpy as np
        s=r*2; yy,xx=np.mgrid[0:s,0:s].astype(np.float32)
        d=np.sqrt((xx-r+0.5)**2+(yy-r+0.5)**2)/r
        a=color[3]*np.clip(1-d,0,1)**1.6
        a=a+np.random.default_rng(r).uniform(-0.5,0.5,a.shape)
        img=Image.fromarray(np.clip(a+0.5,0,255).astype("uint8"),"L")
        rgb=Image.new("RGBA",(s,s),color[:3]+(255,)); rgb.putalpha(img)
        return rgb

def es_marca_del_pack(nombre):
    """Un logo solo acompaña a su propia marca (nunca isotipo ajeno junto a otro nombre)."""
    return bool(MARCA_NOMBRE) and str(nombre).strip().lower()==MARCA_NOMBRE.strip().lower()

def mundo(ctx,t,oscuro=True,seed=1):
    """Fondo vivo: blobs a la deriva + viñeta. Sin rejillas ni líneas."""
    img=Image.new("RGBA",(W,H),NEGRO+(255,))
    bx=W*0.5+W*0.28*math.sin(t*0.11+seed*2.1)
    by=H*0.30+H*0.10*math.cos(t*0.09+seed*1.3)
    img.alpha_composite(ctx.blob_big,(int(bx-560),int(by-560)))
    bx2=W*0.5+W*0.30*math.sin(t*0.07+seed*4.2+2)
    by2=H*0.72+H*0.08*math.sin(t*0.10+seed)
    img.alpha_composite(ctx.blob_mid,(int(bx2-380),int(by2-380)))
    # objetos de ambiente (fluidez.md): motas de luz que derivan lento y
    # titilan — el fondo está vivo también en los holds, sin distraer
    for i in range(18):   # sprites pre-difuminados (un blur de cuadro entero costaba +30 %)
        rnd=random.Random(seed*97+i)
        vel=rnd.uniform(14,32)
        x=(rnd.uniform(0,W)+18*math.sin(t*rnd.uniform(0.2,0.5)+i))%W
        y=H-((rnd.uniform(0,H)+vel*t)%(H+40))+20          # suben despacio
        a=rnd.uniform(0.45,1.0)*(0.65+0.35*math.sin(t*rnd.uniform(0.6,1.4)+i*1.7))
        sp=ctx.mota_acento if i%3==0 else ctx.mota_blanca
        sp=sp if a>=0.99 else Image.fromarray((np.asarray(sp,np.float32)*[1,1,1,a]).astype(np.uint8),"RGBA")
        img.alpha_composite(sp,(int(x-sp.width/2),int(y-sp.height/2)))
    # viñeta sutil para profundidad (precomputada)
    img=Image.composite(img,ctx.vig_negro,ctx.vig_mask)
    return img

def mancha_mask(ctx,t,t0,dur=0.7,fx=0.5,fy=0.45):
    """Máscara de blob orgánico creciente para transiciones."""
    p=clamp01((t-t0)/dur); e=ease_in_out(p)
    maxr=math.hypot(W,H)*0.75
    r=maxr*e
    mask=Image.new("L",(W,H),0); d=ImageDraw.Draw(mask)
    pts=[]
    for i in range(72):
        a=i/72*math.pi*2
        rr=r*(1+0.22*math.sin(a*4+t*6)+0.10*math.sin(a*7-t*4))
        pts.append((W*fx+rr*math.cos(a),H*fy+rr*math.sin(a)))
    d.polygon(pts,fill=255)
    return mask


def marca_fondo(ctx, layer, cx, cy, r, t, t0, dur=0.7, color=None, alpha=90):
    """La MARCA del pack (el isotipo) como fondo que CRECE y se ENCOGE.

    El gesto es el de la apertura (nace de un punto, crece y se encoge con el
    cambio de titular); lo que cambia es la FORMA: donde antes habia un blob
    organico de cuatro lobulos ahora esta la identidad de la marca.

    Va como FONDO (misma luz, misma curva, misma zona) para no competir con el
    titular: el pack lo declara con `reglas.isotipo_con_protagonista: false` y
    por eso va TENUE, no como firma.

    Devuelve False si el pack no trae isotipo: el que llama cae al blob de
    siempre. El gesto no depende de que la marca tenga isotipo.
    """
    iso = getattr(ctx, "iso", None)
    if iso is None:
        return False
    k = clamp01((t - t0) / max(1e-6, dur))
    if k <= 0 or r <= 4:
        return True
    col = color or ACENTO
    # el resplandor: la misma luz difusa del fondo, crecida con el radio
    g = max(16, int(r * 1.7))
    halo = ctx.blob_mid.resize((g, g), Image.BILINEAR)
    halo.putalpha(halo.getchannel("A").point(lambda v: int(v * k)))
    layer.alpha_composite(halo, (int(cx - g / 2), int(cy - g / 2)))
    # la MARCA, como silueta en el color de la marca: el isotipo en su propio
    # color es la verdad de la marca, y el texto (blanco) encima conserva el
    # contraste. En blanco la silueta se lavaria sobre un plano claro y
    # taparia el titular.
    s = max(12, int(r * 1.45))
    paso = max(8, (s // 8) * 8)
    cache = getattr(ctx, "_iso_cache", None)
    if cache is None:
        cache = ctx._iso_cache = {}
    if paso not in cache:
        sil = Image.new("RGBA", iso.size, tuple(col[:3]) + (0,))
        sil.putalpha(iso.getchannel("A"))
        cache[paso] = sil.resize((paso, paso), Image.LANCZOS)
    im = cache[paso].copy()
    im.putalpha(im.getchannel("A").point(lambda v: int(v * k * alpha / 255)))
    layer.alpha_composite(im, (int(cx - paso / 2), int(cy - paso / 2)))
    return True


def iris_mask(ctx, t, t0, dur=0.7, fx=0.5, fy=0.38):
    """Máscara de círculo que crece desde un punto: la apertura en iris.
    Es el corte firma del video con presentador: la escena entra desde la
    cara. Comparte el presupuesto de la `mancha` (las dos piden atención).
    Determinista: el radio es función pura del tiempo."""
    p = clamp01((t - t0) / max(1e-6, dur))
    r = math.hypot(W, H) * 0.78 * ease_out(p)
    mask = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(mask)
    cx, cy = W * fx, H * fy
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    return mask


def resplandor(layer, bbox, color, sigma, alfa=255, dibujar=None, escala=1):
    """Halo difuso del `color` sobre `bbox` (x0, y0, x1, y1 en coordenadas de
    `layer`). UNA sola receta para todos los brillos de las escenas.

    El lienzo se ACOLCHA 3σ por lado: el desenfoque nunca se recorta. Sin
    eso el halo se pintaba en un lienzo del tamaño justo de la forma, el blur
    extendía el borde y se veía el CUADRADO del lienzo (zoom_orbita.png).
    `dibujar(d, ox, oy)` pinta otra forma (un texto) restando el origen
    (ox, oy) del lienzo; por defecto, una elipse en `bbox` con alfa `alfa`.
    `escala` > 1 pinta y desenfoca a 1/escala y amplía (un halo grande y
    barato; solo con la elipse). Devuelve el lienzo; si `layer` no es None,
    lo compone encima."""
    pad = int(math.ceil(3 * sigma))
    x0, y0, x1, y1 = bbox
    ox, oy = int(math.floor(x0)) - pad, int(math.floor(y0)) - pad
    w, h = int(math.ceil(x1)) + pad - ox, int(math.ceil(y1)) + pad - oy
    q = max(1, int(escala)) if dibujar is None else 1
    # el fondo transparente lleva el MISMO color: el blur no oscurece el borde
    g = Image.new("RGBA", (max(1, -(-w // q)), max(1, -(-h // q))), tuple(color[:3]) + (0,))
    d = ImageDraw.Draw(g)
    if dibujar is not None:
        dibujar(d, ox, oy)
    else:
        d.ellipse([(x0 - ox) / q, (y0 - oy) / q, (x1 - ox) / q, (y1 - oy) / q],
                  fill=tuple(color[:3]) + (int(alfa),))
    g = g.filter(ImageFilter.GaussianBlur(sigma / q))
    if q > 1:
        g = g.resize((w, h), Image.BILINEAR)
    if layer is not None:
        layer.alpha_composite(g, (ox, oy))
    return g


# La salida del corte por defecto: la escena que sale sigue ENTERA hasta el
# corte y se va en SOLAPE s debajo de la que entra. Medido (trans_zoom.png):
# con 0.25 s antes + 0.45 s después quedaba al ~12 % 0.3 s tras el corte, un
# fantasma bajo el texto nuevo, y el fundido previo vaciaba el cuadro antes de
# que la nueva mostrara nada. El primer elemento que entra llega a ~+0.2 s:
# la salida sostiene el cuadro hasta ahí y a +0.3 s ya no queda (< 2 %).
SOLAPE=0.32      # s que la salida se superpone con la entrada de la siguiente
SOLAPE_DISSOLVE=0.40   # s del fundido cruzado (transicion "dissolve")
SOLAPE_PRE=0.0   # s de fundido de salida ANTES del corte (0: sale desde el corte)
# El pack puede declarar "corte_seco": entonces el corte es seco (la escena que
# entra aparece de inmediato) pero el saliente se disuelve DEBAJO durante un
# cuarto de segundo. Sin ese retardo quedaba un hueco vacío entre escenas: la
# que salía se iba antes de que la siguiente empezara a mostrar contenido.
SOLAPE_SECO=0.25
SOLAPE_PRE_SECO=0.03

def capa_salida(layer,t,to_):
    """Salida que se SOLAPA con la escena siguiente: empieza SOLAPE_PRE s antes
    del fin y termina SOLAPE s después, debajo de lo que ya entra (antes
    terminaba en `to` y quedaban frames de fondo vacío en cada corte: un
    parpadeo que fluidez.md prohíbe; si dura de más, deja un fantasma)."""
    s=prog(t,to_-SOLAPE_PRE,to_+SOLAPE,smoothstep)   # cruza el corte: sin hueco vacío
    if s<=0: return layer
    a=layer.split()[3].point(lambda v:int(v*(1-s)))
    layer.putalpha(a)
    return layer

def instante_saliente(e,t):
    """El instante en que se pinta una escena que sale por una transición de
    máscara (iris, mancha, dissolve): su estado SIN fundir, el de justo antes
    de que empiece `capa_salida`. La salida la hace la máscara; si además se
    fundía, la máscara abría sobre fondo vacío (0.3-0.5 s medidos)."""
    return min(t,e["to"]-SOLAPE_PRE)

def sale_por_mascara(escenas,i,manchas_ok):
    """¿La escena i sale por una transición de máscara de la siguiente?"""
    if i+1>=len(escenas): return False
    # el iris entra siempre por su rama de `componer` (como allí)
    tr=escenas[i+1].get("transicion")
    return tr=="dissolve" or tr=="iris" or (i+1) in manchas_ok

def titular(ctx,layer,t,lineas,ats,tam=120,cy=None,word_gap=36,line_gap=1.18,maxw=None):
    """Titular cinético: cada palabra entra con resorte en su `at`, con escala
    real (1.16 -> 1.0, el overshoot del resorte da el asentamiento) y elevación.
    Auto-fit sobre el ancho REAL de la línea (palabras + huecos).

    Markup (mismo que `frase`, vía `segmentos_resalte`): `*clave*` en tinta
    de acento; `~clave~` caja roja (texto blanco); `^clave^` caja blanca
    (texto oscuro). Es el sistema del reel de referencia — una sola fuente.
    """
    zx0,_,zx1,_=caja_segura()
    maxw=maxw or (zx1-zx0)*0.96   # cabe en la zona SEGURA (W-2*MARGEN es más ancho en 9:16)
    def palabras(ln):
        # kind: '' | 'acento' | 'roja' | 'blanca' (segmentos_resalte)
        return [(w_, kind) for t_seg, kind in segmentos_resalte(ln)
                for w_ in t_seg.split(" ") if w_]
    def ancho(ln,fnt):
        ws=palabras(ln); gap=ctx.tmp.textlength(" ",font=fnt)+word_gap*0.4
        # las cajas suman un poco de padding horizontal al medir
        extra=0.0
        for w_, kind in ws:
            if kind in ("roja", "blanca"):
                extra += fnt.size * 0.32
        return (sum(ctx.tmp.textlength(w_,font=fnt) for w_,_ in ws)
                + gap*max(0,len(ws)-1) + extra)
    while tam>40:
        fnt=ctx.fT(tam,800)
        if max(ancho(ln,fnt) for ln in lineas)<=maxw: break
        tam-=4
    fnt=ctx.fT(tam,800)
    gap=ctx.tmp.textlength(" ",font=fnt)+word_gap*0.4
    ys = cy if cy is not None else vy(0.44)
    y0=ys-(len(lineas)-1)*tam*line_gap/2
    wi=0
    for li,ln in enumerate(lineas):
        y=y0+li*tam*line_gap
        x=(W-ancho(ln,fnt))/2
        for w_, kind in palabras(ln):
            ww=ctx.tmp.textlength(w_,font=fnt)
            pad = tam * 0.16 if kind in ("roja", "blanca") else 0.0
            at=ats[wi] if wi < len(ats) else ats[-1]+2*STAGGER*(wi-len(ats)+1); wi+=1   # palabras de más: siguen la cadencia
            k=entra(t, at, "titular")
            if k>0:
                sc=1+0.16*(1-k)
                f2=ctx.fT(tam*sc,800) if abs(sc-1)>0.004 else fnt
                ww2=ctx.tmp.textlength(w_,font=f2)
                yy=y+tam   # línea base FINAL: la palabra sube desde detrás de ella
                asc,desc=f2.getmetrics()
                pad2 = f2.size * 0.16 if kind in ("roja", "blanca") else 0.0
                # la caja de la palabra (con aire arriba para el overshoot); su
                # borde de abajo es la línea de clip
                bx0=int(x-pad2)-4; by0=int(yy-asc-f2.size*0.12)
                by1=int(math.ceil(yy+max(desc,f2.size*0.25)))+2
                tile=Image.new("RGBA",(int(math.ceil(ww2+2*pad2))+8,by1-by0),(0,0,0,0))
                dt_=ImageDraw.Draw(tile)
                if kind in ("roja", "blanca"):
                    caja=[x - pad2 - bx0, yy - f2.size * 0.85 - by0,
                          x + ww2 + pad2 - bx0, yy + f2.size * 0.25 - by0]
                    relleno = ACENTO if kind == "roja" else BLANCO
                    dt_.rounded_rectangle(caja, radius=int(f2.size * 0.12),
                                          fill=relleno + (255,))
                    col = BLANCO if kind == "roja" else NEGRO
                elif kind == "acento":
                    col = ACENTO
                else:
                    col = BLANCO
                dt_.text((x+ww2/2-bx0,yy-by0),w_,font=f2,
                         fill=col+(255,),anchor="ms")
                _revela_clip(layer,tile,(bx0,by0),k)
            x+=ww+gap+2*pad
    return tam

def rotulo_y():
    """Altura canónica unificada para rótulos según formato (H*0.20 en 9:16, H*0.16 en 16:9).
    Garantiza coherencia espacial y retícula uniforme entre escenas (references/coherencia-espacial.md)."""
    return vy(0.20) if H > W else vy(0.16)

def rotulo(ctx,layer,t,texto,at,y=None,color=None,tam=44):
    """Rótulo con entrada real: cada línea sube desde detrás de su línea base
    (revelado por máscara, `_revela_clip`) con el resorte del rol (nunca de golpe)."""
    color=color or BLANCO
    if not texto or t<at: return 0   # sin rótulo en el plan: no se dibuja
    k=entra(t, at, "bloque")
    sg=segs(texto); fnt=ctx.fX(tam,700)
    zx0,_,zx1,_=caja_segura()   # el rótulo cabe en la zona segura: encoge, nunca se sale
    ancho=(zx1-zx0)-20
    while tam>TAM_MIN_ROTULO and seg_width(sg,fnt)>ancho:
        tam-=2; fnt=ctx.fX(tam,700)
    yy=rotulo_y() if y is None else y
    asc,desc=fnt.getmetrics(); aire=int(tam*0.12)   # aire arriba para el overshoot
    for i,ln in enumerate(partir_segs(sg,fnt,ancho)):   # si ni a 30 px cabe: dos líneas
        y_ln=yy+i*tam*1.2
        bx0=int(W/2-seg_width(ln,fnt)/2)-4; by0=int(y_ln)-aire
        tile=Image.new("RGBA",(int(seg_width(ln,fnt))+10,aire+asc+desc+2),(0,0,0,0))
        draw_seg(ImageDraw.Draw(tile),(W/2-bx0,y_ln-by0),ln,fnt,color+(255,),ACENTO+(255,),anchor="ma")
        _revela_clip(layer,tile,(bx0,by0),k)
    return k

def partir_segs(sg,fnt,ancho):
    """Segmentos con énfasis en 1 línea si caben; si no, en 2 líneas
    equilibradas cortando entre palabras (el énfasis se conserva)."""
    if seg_width(sg,fnt)<=ancho: return [sg]
    pal=[(w_,em) for t_,em in sg for w_ in t_.split(" ") if w_]
    def armar(ps):
        out=[]
        for i,(w_,em) in enumerate(ps):
            if out and out[-1][1]==em: out[-1]=(out[-1][0]+" "+w_,em)
            else: out.append(((" " if i else "")+w_,em))
        return out
    mejor=min(range(1,len(pal)) or [1],key=lambda c:max(seg_width(armar(pal[:c]),fnt),seg_width(armar(pal[c:]),fnt)))
    return [armar(pal[:mejor]),armar(pal[mejor:])]

def vk():
    """Factor vertical de la caja segura actual frente a la de diseño: 1 sin
    banda de subtítulos; < 1 con "subtitulos": true (la caja es más baja)."""
    banda=int(H*BANDA_SUBS["fraccion"])
    if not banda: return 1.0
    top=SAFE["top"]; b0=H-(SAFE["bottom"]-banda); b1=H-SAFE["bottom"]
    return (b1-top)/max(1,(b0-top))

def vy(f):
    """y de diseño (fracción de H) re-mapeada a la caja segura actual: las
    escenas compuestas en fracciones de H suben y se comprimen sobre la banda
    de subtítulos en vez de que la red las encoja enteras. Sin banda = H*f."""
    y=H*f; top=SAFE["top"]
    return y if y<=top else top+(y-top)*vk()

def bajo_rotulo(y,tam=44,aire=0.45):
    """Primer y libre bajo un rótulo anclado arriba en `y` (alto de línea +
    aire). Lo que va debajo del rótulo se mide desde aquí, nunca con una
    fracción fija de H: en 16:9 H*0.04 son 43 px y el rótulo mide ~55."""
    return y+tam*(1.2+aire)

def tarjeta(ctx,img,x,y,w,h,radio=28,alpha=255):
    d=ImageDraw.Draw(img)
    borde=(255,255,255,int(28*alpha/255))   # el borde funde con la tarjeta (antes saltaba a 28)
    if h < 2*radio or w < 2*radio:  # rounded_rectangle falla si h/w < 2*radio
        d.rectangle([x,y,x+w,y+h],fill=PANEL+(alpha,))
        d.rectangle([x,y,x+w,y+h],outline=borde)
        return
    d.rounded_rectangle([x,y,x+w,y+h],radius=radio,fill=PANEL+(alpha,))
    d.rounded_rectangle([x,y,x+w,y+h],radius=radio,outline=borde)


def tarjeta_cristal(ctx, img, x, y, w, h, radio=28, alpha=255, tinte=None, brillo=1.0):
    """Superficie Liquid Glass (inspirada en glass.samasante.com, MIT):
    panel translúcido esmerilado con tinte sutil, reflejo diagonal y borde
    especular superior-izquierdo (liseré spéculaire). DRY: `hero`, `bento`."""
    d = ImageDraw.Draw(img)
    col_t = tinte or ACENTO
    base_r = int(PANEL[0] * 0.82 + col_t[0] * 0.18)
    base_g = int(PANEL[1] * 0.82 + col_t[1] * 0.18)
    base_b = int(PANEL[2] * 0.82 + col_t[2] * 0.18)
    fill_a = int(min(242, 218 * alpha / 255))
    borde_suave = (255, 255, 255, int(44 * alpha / 255 * brillo))
    borde_especular = (255, 255, 255, int(115 * alpha / 255 * brillo))
    r_ = min(radio, max(1, int(min(w, h) // 2)))
    d.rounded_rectangle([x, y, x + w, y + h], radius=r_, fill=(base_r, base_g, base_b, fill_a),
                        outline=borde_suave, width=2)
    if w > 2 * r_ + 16 and h > 24:
        d.line([(x + r_, y + 1.5), (x + w - r_, y + 1.5)], fill=borde_especular, width=2)
        d.line([(x + 1.5, y + r_), (x + 1.5, y + h * 0.55)], fill=borde_especular, width=2)


def boton_halo(d, cx, cy, w, h, texto, fnt, t, t0, color=None, alpha=255,
               hecho=None, fnt_hecho=None):
    """Botón CTA de la casa: píldora con marco blanco fino y halo que late.

    UN componente para toda la pieza (hero, final, pago, demo): el mismo
    aspecto en todas las escenas; solo cambian el texto y, en `pago`, el
    estado "hecho" (píldora blanca con el check de acento). Antes cada
    escena se dibujaba el suyo: cuatro botones distintos en la misma pieza
    (con halo y marco, solo halo, o nada) rompen el sistema de componentes.
    """
    col = color or ACENTO
    r_ = int(h // 2)
    pulso = 0.5 + 0.5 * math.sin(max(0.0, t - t0) * 3.6)
    exp = 6 + 6 * pulso
    halo_a = int((38 + 34 * pulso) * alpha / 255)
    d.rounded_rectangle([cx - w / 2 - exp, cy - h / 2 - exp, cx + w / 2 + exp, cy + h / 2 + exp],
                        radius=int((h + 2 * exp) // 2), outline=col + (halo_a,), width=3)
    if hecho:
        # estado "hecho": la misma píldora, en blanco, con el check de acento
        d.rounded_rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], radius=r_,
                            fill=(255, 255, 255, int(alpha)))
        fh = fnt_hecho or fnt
        tw = d.textlength(hecho, font=fh)
        ca = col + (int(alpha),)
        check(d, cx - tw / 2 - 10, cy, 13, ca, 6)
        d.text((cx + 16, cy), hecho, font=fh, fill=ca, anchor="mm")
        return
    d.rounded_rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2],
                        radius=r_, fill=col + (int(alpha),),
                        outline=(255, 255, 255, int(95 * alpha / 255)), width=2)
    d.text((cx, cy), texto, font=fnt, fill=BLANCO + (int(alpha),), anchor="mm")


def insignia_3d(d, cx, cy, r, icono, fnt, color=None, alpha=255, t=0.0):
    """Insignia 3D táctil extruida con sombra de contacto, bisel inferior y
    brillo especular superior (inspirada en 3dicons.co, CC0). DRY: `bento`."""
    col = color or ACENTO
    osc = tuple(max(0, int(c * 0.58)) for c in col)
    claro = tuple(min(255, int(c + (255 - c) * 0.42)) for c in col)
    dy = flota(t, 0.0, amp=3.5, freq=0.55)
    cy_f = cy + dy
    # sombra de contacto
    d.ellipse([cx - r * 0.82, cy + r * 0.78, cx + r * 0.82, cy + r * 1.12],
              fill=(0, 0, 0, int(90 * alpha / 255)))
    # extrusión inferior (volumen 3D)
    rr = max(8, int(r * 0.42))
    d.rounded_rectangle([cx - r, cy_f - r + 7, cx + r, cy_f + r + 7],
                        radius=rr, fill=osc + (int(alpha),))
    # cara principal
    d.rounded_rectangle([cx - r, cy_f - r, cx + r, cy_f + r],
                        radius=rr, fill=col + (int(alpha),),
                        outline=claro + (int(140 * alpha / 255),), width=2)
    # reflejo especular superior
    d.ellipse([cx - r * 0.55, cy_f - r * 0.72, cx + r * 0.55, cy_f - r * 0.18],
              fill=claro + (int(75 * alpha / 255),))
    if icono:
        d.text((cx, cy_f), str(icono)[:3], font=fnt, fill=BLANCO + (int(alpha),), anchor="mm")

# ───────────────────────── primitivas DRY para escenas de datos/UI ─────────────────────────
# Cada nueva escena se compone de estas primitivas. DRY: las escenas NO duplican lógica
# de barras / anillos / círculos / partículas / grids; la llaman aquí.

def barra_h(d, x, y, ancho, alto, fraccion, color, radio=None, pista=18, min_px=None):
    """Barra horizontal rellenable: track + fill con esquinas redondeadas.
    `fraccion` ∈ [0, 1] controla el porcentaje visible (la animación lo interpola).
    `min_px`: piso visual del fill cuando fraccion>0 (un 6/48 no puede verse
    como un punto: en ranking quedaba un “nub” ilegible). None = alto (una
    píldora mínima del alto de la pista).
    DRY: la usan `bars`, `ranking`, `progreso`, `leads.puntaje`."""
    radio = radio or alto // 2
    if ancho < 2 * radio or alto < 2 * radio:
        radio = min(radio, min(ancho, alto) // 2)
    # track
    d.rounded_rectangle([x, y, x + ancho, y + alto], radius=radio, fill=(255, 255, 255, int(pista)))
    # fill
    f = clamp01(fraccion)
    if f <= 0:
        return
    # el piso visual crece CON la fraccion (no salta a min_px en el frame 1:
    # eso seria un pop). En reposo (f≈1) un valor chico no queda en un “nub”.
    raw = max(1, int(ancho * f))
    if min_px:
        piso_vivo = max(1, int(float(min_px) * f))
        fill_w = min(int(ancho), max(raw, piso_vivo))
    else:
        fill_w = raw
    if fill_w < 2 * radio:   # nace de 0: una píldora más angosta, no una entera de golpe
        r_ = max(0, fill_w // 2)
        d.rounded_rectangle([x, y, x + fill_w, y + alto], radius=r_, fill=color)
    elif fill_w >= ancho - 2:
        d.rounded_rectangle([x, y, x + fill_w, y + alto], radius=radio, fill=color)
    else:
        d.rectangle([x, y, x + fill_w, y + alto], fill=color)
        d.pieslice([x, y, x + 2 * radio, y + 2 * radio], 90, 270, fill=color)
        d.pieslice([x + fill_w - 2 * radio, y, x + fill_w, y + 2 * radio], 270, 90, fill=color)


def decimales_de(v):
    """Decimales con que se ESCRIBIÓ un número (3.5 -> 1, 12 -> 0, 0.25 -> 2)."""
    if isinstance(v, int) or float(v).is_integer():
        return 0
    return min(3, len(repr(float(v)).split(".")[1]))


NUMEROS = {"miles": ",", "decimal": "."}   # separadores de toda cifra; el plan los fija con "numeros"
LOCALES = {"es": {"miles": ".", "decimal": ","}, "en": {"miles": ",", "decimal": "."},
           "fr": {"miles": "\u202f", "decimal": ","}}


BANDA_SUBS = {"fraccion": 0.0}   # alto reservado abajo para subtítulos quemados
BANDA_SUBTITULOS = 0.12


def aplicar_globales(plan):
    """Ajustes de TODO el plan, en una sola puerta (render, workers, banco):
    - `"numeros": "es"` (1.240 · 4,8), "en" (1,240 · 4.8), "fr" o
      {"miles": ".", "decimal": ","}: separadores de toda cifra.
    - `"subtitulos": true`: reserva una banda abajo (12 % del alto) sobre la
      zona segura; toda escena compone encima y los subtítulos no pisan nada."""
    BANDA_SUBS["fraccion"] = BANDA_SUBTITULOS if plan.get("subtitulos") else 0.0
    v = plan.get("numeros", "en")
    NUMEROS.update(LOCALES.get(v, LOCALES["en"]) if isinstance(v, str) else
                   {k: str(v.get(k, NUMEROS[k])) for k in ("miles", "decimal")})
    _preparar_camara(plan)
    _preparar_deplecion(plan)
    _preparar_cabecera(plan)
    try:
        _GRANO["amp"] = max(0, int(plan.get("grano", 0) or 0))
    except (TypeError, ValueError):
        _GRANO["amp"] = 0


# ---- CAMARA DE LA PIEZA (una trayectoria, no una por escena) -------------
#
# El problema: `respiracion` usaba `dt = t - e["from"]`, o sea el reloj de la
# cámara se REINICIABA en cada corte. Medido en el plan de muestra: la escena
# saliente llegaba a escala 1,0433 con dy +5,7 px y la entrante arrancaba en
# 1,0000 con dy 0,00 -> un salto de 4,3-5 % de escala y hasta 6 px en CADA
# union. La pieza se leia como un montage, no como una toma continua.
#
# La solución: el plan declara la TRAYECTORIA de la cámara y se evalua sobre
# el reloj GLOBAL de la pieza. Por construcción es continua: en un corte, la
# escena que sale y la que entra ven el MISMO instante, así que calculan la
# MISMA escala. No hace falta sincronizar nada: no hay dos relojes.
#
#   "camara": {"z0": 2.40, "z1": 1.00, "flota": 6}
#
# `z0` y `z1` son las escalas al principio y al final de la pieza (z1 < z0 es
# un alejamiento progresivo: el objeto se hace pequeno y la pieza respira).
# Sin `camara` en el plan, el motor se comporta como antes (el push-in por
# escena): esta capacidad es opt-in y no cambia las piezas existentes.
_CAMARA={"z0":None,"z1":None,"flota":6,"t0":0.0,"t1":1.0,"activa":False}


def _preparar_camara(plan):
    """Deja la trayectoria de cámara lista (o la apaga si el plan no la pide)."""
    _CAMARA.update({"z0":None,"z1":None,"flota":FLOTA_CAM,"t0":0.0,"t1":1.0,
                    "activa":False,"x0":0.0,"x1":0.0,"y0":0.0,"y1":0.0})
    if "camara" not in plan:
        return                      # el plan no la pide: la camara se comporta como antes
    cam=plan.get("camara") or {}
    if not isinstance(cam,dict):
        return
    try:
        z0=float(cam.get("z0",1.0)); z1=float(cam.get("z1",z0))
    except (TypeError,ValueError):
        return
    esc=plan.get("escenas") or []
    if not esc:
        return
    t0=float(min((e.get("from",0.0) for e in esc), default=0.0))
    t1=float(max((e.get("to",t0) for e in esc), default=t0+1.0))
    if t1<=t0:
        t1=t0+1.0
    # el RECORRIDO de la camara: de donde sale a donde llega (en px). Con
    # esto la camara tambien VIAJA de lado, no solo se acerca: un vuelo
    # continuo (una pieza, un solo recorrido) es un paneo + un zoom.
    try:
        x0=float(cam.get("x0",0.0)); x1=float(cam.get("x1",x0))
        y0=float(cam.get("y0",0.0)); y1=float(cam.get("y1",y0))
    except (TypeError,ValueError):
        x0=x1=y0=y1=0.0
    _CAMARA.update({"z0":z0,"z1":z1,"flota":float(cam.get("flota",FLOTA_CAM)),
                    "t0":t0,"t1":t1,"activa":True,
                    "x0":x0,"x1":x1,"y0":y0,"y1":y1})


def _escala_camara(t):
    """La escala de la cámara en el instante t (trayectoria global)."""
    if not _CAMARA["activa"]:
        return 1.0
    z0,z1=_CAMARA["z0"],_CAMARA["z1"]
    t0,t1=_CAMARA["t0"],_CAMARA["t1"]
    p=clamp01((t-t0)/max(1e-6,t1-t0))
    return z0+(z1-z0)*p


def _offset_camara(t):
    """El RECORRIDO de la camara (px): de donde sale a donde llega.

    Es lo que hace que la camara VIAJE de lado y no solo se acerque: con
    esto una pieza puede ser un solo recorrido continuo en vez de una tanda
    de planos."""
    if not _CAMARA["activa"]:
        return 0.0, 0.0
    t0,t1=_CAMARA["t0"],_CAMARA["t1"]
    p=clamp01((t-t0)/max(1e-6,t1-t0))
    p=smoothstep(p)
    dx=_CAMARA["x0"]+(_CAMARA["x1"]-_CAMARA["x0"])*p
    dy=_CAMARA["y0"]+(_CAMARA["y1"]-_CAMARA["y0"])*p
    return dx, dy


# ---- LA BARRA DE DEPLECION (el reel de "cara") ---------------------------
#
# En el reel de referencia hay una barra roja de 5 px PEGADA al borde
# superior del lienzo que se DEPLETA: empieza al ancho completo y se estrecha
# hasta cero en el ultimo segundo de la pieza.
#
# MEDIDO sobre De8KNkdDT68 (55,300 s, 1080x1920), leyendo el ancho de la
# franja roja en la fila 0 (prediccion = 1080*(1 - t/55,3)):
#     t= 0,2 s -> 1076 px  (predice 1076)
#     t= 5,0 s ->  982 px  (predice  982)
#     t=11,0 s ->  866 px  (predice  865)
#     t=17,0 s ->  748 px  (predice  748)
#     t=23,0 s ->  632 px  (predice  631)
#     t=29,0 s ->  514 px  (predice  514)
#     t=35,0 s ->  398 px  (predice  396)
#     t=41,0 s ->  280 px  (predice  279)
#     t=47,0 s ->  162 px  (predice  162)
#     t=52,0 s ->   64 px  (predice   64)
#     t=55,0 s ->    0 px  (predice    0)
# o sea: ancho = W * (1 - t/duracion). Lineal y anclada a la IZQUIERDA.
#
# Vive en el PLAN y no en una escena porque es de la PIEZA entera: las escenas
# van y vienen, la barra no. Si fuera una escena, la pieza tendria que gastar
# una escena entera en la barra y el plan diria una cosa falsa (que la pieza
# tiene una escena mas de las que tiene).
#
#     "deplecion": {"y": 0, "alto": 5, "color": "acento"}
#
_DEPLECION={"activa":False,"y":0,"alto":5,"color":None,"ancho":None,
             "t0":0.0,"t1":None}

def _color_de_deplecion(valor):
    """El color de la barra: un token del pack ("acento", "blanco", "gris",
    "negro") o un hex ("#BD1700"). Sin esto, el color seria el acento del
    paquete en cada pieza y la barra no se podria individuar."""
    if valor is None:
        return ACENTO
    if isinstance(valor,(list,tuple)) and len(valor)>=3:
        rgb=tuple(int(v) for v in valor[:3])
        return rgb+(int(valor[3]) if len(valor)>3 else 255,)
    tokens={"acento":ACENTO,"acento_oscuro":ACENTO_OSC,"blanco":BLANCO,
            "gris":GRIS,"negro":NEGRO}
    if isinstance(valor,str):
        v=valor.strip().lower()
        if v in tokens:
            return tokens[v]
        if v.startswith("#") or all(c in "0123456789abcdefABCDEF" for c in v.lstrip("#")):
            from _comun import hex_a_rgb
            return hex_a_rgb(v)+(255,)
    return ACENTO


def _preparar_deplecion(plan):
    """Deja la barra de deplecion lista (o la apaga si el plan no la pide)."""
    _DEPLECION.update({"activa":False,"y":0,"alto":5,"color":None,
                        "ancho":None,"t0":0.0,"t1":None})
    cfg=plan.get("deplecion")
    if cfg is None:
        return
    if cfg is True:
        cfg={}
    if not isinstance(cfg,dict):
        return
    try:
        y=int(cfg.get("y",0)); alto=int(cfg.get("alto",5))
    except (TypeError,ValueError):
        return
    if alto<=0:
        return
    ancho=cfg.get("ancho")
    try:
        ancho=int(ancho) if ancho is not None else None
    except (TypeError,ValueError):
        ancho=None
    _DEPLECION.update({"activa":True,"y":y,"alto":alto,
                        "color":_color_de_deplecion(cfg.get("color")),
                        "ancho":ancho,"t0":0.0,"t1":None})


# ---- LA CABECERA DE MARCA (el rack que firma la pieza) --------------------
#
# En el reel de "cara" hay una banda arriba en TODOS los fotogramas: el logo
# de la marca a la izquierda y un chip con la FUENTE a la derecha.
#
# MEDIDO sobre De8KNkdDT68 (1080x1920): el logo ocupa de x=71 a x=290 y el
# chip va de x=300 a x=977, en la banda y=138..180 (a 7 % del alto, por
# encima de la zona segura, como la UI de la plataforma); el chip es un
# rectangulo de esquinas redondeadas (radio ~12) con el borde de 1 px en
# gris y el texto en monoespaciada.
#
# OJO CON EL PAPEL DEL CHIP: el chip es la FUENTE (de donde sale el
# material), NO la accion. El boton es la accion y va en otra parte: si el
# chip dice "hablamos" y el boton dice "miralo en YouTube", la pieza
# promete dos cosas y no cumple ninguna.
#
# Es un GLOBAL del plan y no una escena por una razon medida: la banda
# esta en todos los fotogramas, mientras que una escena ocupa una ventana
# (y las escenas no se solapan). Ademas, una escena estatica la declara la
# puerta CONGELADA ("ningun hold congelado"): el rack no se mueve, asi que
# como escena no tendria nada que hacer en su propia ventana.
#
#     "cabecera": {"chip": "CHARLA COMPLETA - youtu.be/...", "marca": "..."}
#
_CABECERA={"activa":False,"chip":"","marca":"","y":132,"alto":44}

#: El GRANO de pelicula: la misma tecnica que usaban los films de marca,
#: ahora tambien en el motor de planes (una sola implementacion, en
#: `_comun.aplicar_grano`). `amp` 0 = sin grano (por defecto: no se ve a
#: simple vista, pero el video H.264 se ve "plano" sin el).
_GRANO={"amp":0}


def _preparar_cabecera(plan):
    """Deja la cabecera lista (o la apaga si el plan no la pide)."""
    _CABECERA.update({"activa":False,"chip":"","marca":"","y":132,"alto":44})
    cfg=plan.get("cabecera")
    if cfg is None:
        return
    if cfg is True:
        cfg={}
    if not isinstance(cfg,dict):
        return
    try:
        y=int(cfg.get("y",132)); alto=int(cfg.get("alto",44))
    except (TypeError,ValueError):
        return
    if alto<=0:
        return
    _CABECERA.update({"activa":True,"chip":str(cfg.get("chip","")).strip(),
                       "marca":str(cfg.get("marca","")).strip(),"y":y,"alto":alto})


def dibuja_cabecera(ctx,layer,t,dur):
    """Pinta la banda de la cabecera: el logo del pack y el chip con la fuente.

    El logo solo sale si la pieza declara `marca` y esa marca es la del pack:
    un logo nunca acompaña a otro nombre."""
    if not _CABECERA["activa"]:
        return
    d=ImageDraw.Draw(layer)
    y=int(_CABECERA["y"]); alto=int(_CABECERA["alto"])
    x_izq=int(W*0.066)          # 71 px en el reel: el margen del logo
    x_der=int(W*0.906)          # 977 px: el borde derecho del chip
    # el logo (a la izquierda): el wordmark si el pack lo trae, y si no el
    # isotipo. SOLO con la marca del pack.
    if _CABECERA["marca"] and es_marca_del_pack(_CABECERA["marca"]):
        lg=ctx.logo or ctx.iso          # el wordmark si el pack lo trae, si no el isotipo
        if lg is not None:
            lh=int(alto*0.92)
            lw=max(1,int(lh*lg.width/lg.height))
            img=lg.resize((lw,lh),Image.LANCZOS)
            k=clamp01(t/0.4)          # entra con la pieza
            if k<1:
                img.putalpha(img.split()[3].point(lambda v:int(v*k)))
            layer.alpha_composite(img,(x_izq,int(y+(alto-lh)/2)))
    # el chip con la fuente (a la derecha)
    texto=_CABECERA["chip"]
    if texto:
        fnt=font(MONO,28,700)
        ancho=int(d.textlength(texto,font=fnt))+44
        x0=x_der-ancho
        k=clamp01(t/0.6)
        d.rounded_rectangle([x0,y,x0+ancho,y+alto],radius=12,
                            outline=(92,92,92,255),width=1)
        d.text((x0+22,y+alto/2),texto,font=fnt,
               fill=(200,200,200,int(255*k)),anchor="lm")


def ancho_de_deplecion(t,dur):
    """El ancho de la barra en el instante t: se estrecha linealmente hasta
    cero al final de la pieza y se queda en cero antes de empezar."""
    if not _DEPLECION["activa"]:
        return 0.0
    t1=_DEPLECION["t1"] if _DEPLECION["t1"] is not None else max(dur,1e-6)
    t0=_DEPLECION["t0"]
    p=clamp01((t-t0)/max(1e-6,t1-t0))
    ancho=_DEPLECION["ancho"] or W
    return max(0.0,ancho*(1.0-p))


def dibuja_deplecion(d,t,dur):
    """Pinta la barra de deplecion. Se dibuja ENCIMA de la escena (es el
    borde del lienzo, no una escena mas)."""
    if not _DEPLECION["activa"]:
        return
    w=ancho_de_deplecion(t,dur)
    if w<=0:
        return
    y=_DEPLECION["y"]; alto=_DEPLECION["alto"]
    d.rectangle([0,y,w,y+alto],fill=_DEPLECION["color"])


def separar(txt, miles=None, decimal=None):
    """'1,234.5' (formato Python) con los separadores pedidos."""
    m, d = miles or NUMEROS["miles"], decimal or NUMEROS["decimal"]
    if (m, d) == (",", "."):
        return txt
    return txt.replace(",", "\0").replace(".", d).replace("\0", m)


# Lo que se RELLENA con un dato (una barra, un arco, un anillo, la cifra que
# cuenta) va por tiempo y con UNA duracion: antes cada escena tenia la suya
# (stats 0.7, cuenta 0.8, bars/ranking 0.9, gauge 1.1, anillo 1.2) y un mismo
# dato se llenaba a cinco ritmos en la misma pieza (animacion.md §3b).
RELLENO = 0.9


def rellena(t, t0, dur=RELLENO):
    """Progreso 0→1 de un relleno de datos: por tiempo, smoothstep (sin
    rebote: un dato no se pasa de su valor)."""
    return smoothstep(clamp01((t - t0) / max(dur, 1e-6)))


def cuenta_up(desde, hasta, t, t0, dur=RELLENO, fmt="{:,}", progreso=None):
    """Cuenta animada de `desde` a `hasta` en `dur` segundos desde `t0`.
    Devuelve el string listo para imprimir (con separadores). Cada valor
    intermedio lleva los MISMOS decimales que el final (3.5 cuenta 0.0 → 3.5,
    nunca 3.4999…): el número no cambia de ancho ni miente al terminar.
    DRY: la usan `stats`, `gauge`, `ranking`, `bars`.
    Si `desde` o `hasta` no son numericos (ej. "10K+", "<5s"), se devuelve tal cual
    sin animar — comun en stat cards pre-formateados."""
    if not isinstance(desde, (int, float)) or not isinstance(hasta, (int, float)):
        # Sin animacion (stat card pre-formateado): muestra el `hasta` siempre
        return str(hasta)
    if progreso is not None:   # sincronizado con otra animación (la cifra viaja con su barra)
        p = clamp01(progreso)
    else:
        p = ease_out(clamp01((t - t0) / max(dur, 1e-6))) if t >= t0 else 0.0
    v = desde + (hasta - desde) * p
    n = max(decimales_de(hasta), decimales_de(desde))
    if fmt == "{:,}":
        return separar(f"{v:,.{n}f}")
    return fmt.format(round(v, n) if n else int(round(v)))


def arco(d, cx, cy, radio, desde_deg, hasta_deg, color, grosor=14):
    """Arco de círculo centrado en (cx, cy) entre ángulos `desde_deg` y `hasta_deg`
    (0° = 3 en punto, sentido horario). DRY: la usan `gauge`, `pie`."""
    d.arc([cx - radio, cy - radio, cx + radio, cy + radio],
          start=desde_deg, end=hasta_deg, fill=color, width=grosor)


def placa_texto(d, x0, y0, x1, y1, radio=18, alpha=175):
    """Placa oscura detras de un texto, para que se lea sobre una imagen clara.

    Sin ella, el texto blanco (el color de la pieza) desaparece sobre una
    captura de interfaz. DRY: la usa `callout`.

    Se compone en una CAPA PROPIA, no pintando el rectangulo directamente:
    `ImageDraw` REEMPLAZA el pixel (no lo mezcla), asi que un negro con alfa
    bajo encima de una captura la BORRA y deja un agujero negro que aparecia
    de golpe (medido: 2 pops en el `callout`). Con la capa propia la placa se
    funde y puede entrar con rampa.
    """
    if alpha <= 0:
        return
    _destino = getattr(d, "_image", None)
    if _destino is None:      # PIL antiguo: sin composite, se pinta directo
        d.rounded_rectangle([x0, y0, x1, y1], radius=radio, fill=(0, 0, 0, int(alpha)))
        return
    ox, oy = int(x0) - 1, int(y0) - 1
    w = int(x1) - ox + 1
    h = int(y1) - oy + 1
    if w <= 0 or h <= 0:
        return
    capa = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(capa).rounded_rectangle([0, 0, w, h], radius=radio,
                                            fill=(0, 0, 0, int(alpha)))
    _destino.alpha_composite(capa, (ox, oy))


def elipse_se_dibuja(d, cx, cy, rx, ry, t, t0, dur=0.8, color=None, grosor=4):
    """Elipse que se dibuja sola (barrido 0->360°). El gesto de "fíjate aquí".

    Determinista: el barrido es función pura del tiempo. DRY: la usa
    `callout` (el resalte sobre el dato clave)."""
    if t < t0:
        return
    col = color or ACENTO
    p = clamp01((t - t0) / max(1e-6, dur))
    e = ease_out(p)
    d.arc([cx - rx, cy - ry, cx + rx, cy + ry],
          start=-90, end=-90 + 360 * e, fill=col, width=grosor)


def particulas(d, t, t0, cx, cy, n=60, color=None, semilla=11):
    """Confetti / celebración determinista (seeded). Sin random: reproducible.
    `color` por defecto usa ACENTO. La usan `confeti`, `listo` (extra), etc."""
    if t < t0:
        return
    color = color or ACENTO
    rng = random.Random(semilla)
    dt = t - t0
    for _ in range(n):
        # ángulo + velocidad fijos por semilla
        ang = rng.uniform(0, 6.283)
        vel = rng.uniform(280, 720)  # px/s
        caida = 980  # px/s^2
        x = cx + math.cos(ang) * vel * dt
        y = cy + math.sin(ang) * vel * dt + 0.5 * caida * dt * dt
        # tamaño y rotación deterministas
        s = rng.uniform(4, 10)
        if y > H + 40 or x < -40 or x > W + 40:
            continue
        c = (color[0], color[1], color[2], rng.randint(160, 230))
        d.ellipse([x - s, y - s, x + s, y + s], fill=c)


def unidad():
    """Unidad de diseño = lado corto del cuadro (1080 en 9:16 y en 16:9): los
    tamaños de letra se escriben en ella, no en W (W*0.055 son 59 px en 9:16
    y 105 px en 16:9)."""
    return min(W, H)


# REPARTO VERTICAL: en 9:16 el hueco que sobra entre filas se reparte entre
# ellas en vez de quedar como una banda centrada en negro. Con TOPE: cada
# hueco crece como mucho REPARTO_MAX x el alto medio de una fila (mas, y las
# filas se leen sueltas, no como una lista). Las filas NO se estiran: crece el
# aire entre ellas. Una regla para `pila` y `cuadricula`, no una por escena.
REPARTO_MAX = 0.5


def reparto(contenido, n, hueco, gap, fila):
    """Hueco entre `n` filas de alto medio `fila` cuyo bloque (filas + huecos
    `gap`) mide `contenido` px, en un sitio de `hueco` px: en 9:16 crece hasta
    REPARTO_MAX·fila con lo que sobra; en 16:9 (o sin sitio) queda `gap`."""
    if H <= W or n < 2 or hueco <= contenido:
        return gap
    return gap + min((hueco - contenido) / (n - 1), REPARTO_MAX * fila)


def pila(alturas, y0, y1, gap=24):
    """Apila bloques de `alturas` px entre y0 e y1: devuelve (centros, f).
    Si no caben, f < 1 encoge TODO por igual (tamaños de letra incluidos)
    en vez de dejar que se pisen; el conjunto queda centrado en su hueco.
    Si sobra sitio en 9:16, el aire entre bloques crece (`reparto`)."""
    n = len(alturas)
    total = sum(alturas) + gap * (n - 1)
    gap = reparto(total, n, y1 - y0, gap, sum(alturas) / max(1, n))
    total = sum(alturas) + gap * (n - 1)
    f = min(1.0, (y1 - y0) / max(1, total))
    y = y0 + ((y1 - y0) - total * f) / 2
    centros = []
    for a in alturas:
        centros.append(y + a * f / 2)
        y += (a + gap) * f
    return centros, f


def caja_segura():
    """(x0, y0, x1, y1) de la zona segura de la plataforma: el contenido se
    COMPONE dentro (escala_segura es la red, no el diseño)."""
    return SAFE["left"], SAFE["top"], W - SAFE["right"], H - SAFE["bottom"]


def pie_fuente(ctx, d, e, t, t_def):
    """La fuente de un dato, en el borde inferior de la zona segura (toda
    cifra lleva su fuente; nunca bajo la UI de la plataforma)."""
    t0 = e.get("at", {}).get("fuente", t_def)
    if e.get("fuente") and t >= t0:
        x0, _, x1, y1 = caja_segura()
        txt = f"Fuente: {e['fuente']}"
        # el piso de la fuente es el rol `nota` de la escala, no el minimo
        # legible del QA: a 26 px la pieza nacia justo en el piso y la
        # rubrica la penalizaba por construccion; si no cabe, parte en dos
        fnt = fuente_que_cabe(ctx.fX, txt, ESCALA["nota"], x1 - x0, 400, minimo=ESCALA["nota"])
        al = int(255 * prog(t, t0, t0 + 0.3, smoothstep))   # entra fundida, no de golpe
        lineas = partir_segs([(txt, False)], fnt, x1 - x0)   # una fuente larga: dos líneas
        for i, ln in enumerate(reversed(lineas)):            # de abajo hacia arriba
            d.text((W / 2, y1 - 24 - i * (fnt.size * 1.2)), "".join(t_ for t_, _ in ln).strip(), font=fnt,
                   fill=GRIS + (al,), anchor="mb")


def cuadricula(x0, y0, ancho_total, alto_total, cols, n, alto_hueco=None):
    """Layout en grilla: devuelve [(x, y, w, h)] para `n` items en `cols` columnas.
    DRY: la usan `stats`, `pasos`, `bento`, `hoy`.
    Centra automáticamente las filas incompletas para mantener armonía visual.
    Con `alto_hueco` (el sitio que tiene la grilla desde y0), la grilla se
    centra en él y en 9:16 reparte lo que sobra entre filas (`reparto`): las
    tarjetas conservan su alto (`alto_total`), crece el aire entre ellas."""
    filas = (n + cols - 1) // cols
    gap = 24
    w = (ancho_total - gap * (cols - 1)) // cols
    h = (alto_total - gap * (filas - 1)) // filas
    gap_v = gap
    if alto_hueco is not None:
        gap_v = reparto(filas * h + gap * (filas - 1), filas, alto_hueco, gap, h)
        y0 = y0 + max(0, (alto_hueco - (filas * h + gap_v * (filas - 1))) / 2)
    out = []
    for i in range(n):
        r, c = divmod(i, cols)
        items_en_fila = cols if (r < filas - 1 or n % cols == 0) else (n % cols)
        ancho_fila = items_en_fila * w + (items_en_fila - 1) * gap
        rx0 = x0 + (ancho_total - ancho_fila) // 2
        c_in_row = c if (r < filas - 1 or n % cols == 0) else (i - (filas - 1) * cols)
        x = rx0 + c_in_row * (w + gap)
        y = y0 + r * (h + gap_v)
        out.append((x, y, w, h))
    return out


try:
    from PIL import features as _features
    TNUM = ["tnum"] if _features.check("raqm") else None   # cifras tabulares nativas
except ModuleNotFoundError:
    TNUM = None


def largo(texto, font, tabular=False):
    """Ancho real de `texto`; `tabular` = medido como lo dibuja cifra()."""
    tmp = ImageDraw.Draw(Image.new("L", (10, 10)))
    if not tabular:
        return tmp.textlength(texto, font=font)
    if TNUM:
        return tmp.textlength(texto, font=font, features=TNUM)
    celda = ancho_tabular(font)
    return sum(celda if c.isdigit() else tmp.textlength(c, font=font) for c in texto)


def recorta_para(texto, font, ancho_max, tmp=None):
    """Recorta `texto` con … hasta que quepa en `ancho_max` con `font`.

    Es la alternativa al encogido cuando la letra NO puede bajar de su tamaño
    de escala: la letra se queda (28 px = ESCALA["nota"]) y lo que se acorta
    es el copy. Encoger hasta el piso de auto-fit (18) deja letra que el QA
    rechaza por ilegible; recortar deja la pieza legible y más corta.

    Lo que se recorta se ANOTA en RECORTES: un copy que pierde palabras sin
    aviso es un defecto que no se ve hasta que alguien lee la pieza (no hay
    linter que sepa el ancho de cada columna: ese ancho lo decide la escena).
    """
    if tmp is None:
        tmp = ImageDraw.Draw(Image.new("L", (10, 10)))
    if tmp.textlength(texto, font=font) <= ancho_max:
        return texto
    RECORTES.append(dict(texto=texto, ancho_max=int(ancho_max)))
    while len(texto) > 3 and tmp.textlength(texto + "…", font=font) > ancho_max:
        texto = texto[:-1]
    return texto + "…"


def cifra(d, xy, texto, font, fill, anchor="mm", final=None):
    """Número con cifras TABULARES: mientras cuenta, su ancho no cambia y no
    tiembla de lado (con dígitos proporcionales "141" es más angosto que
    "142" y el número se re-centra en cada frame). Sin libraqm, celdas fijas.
    `final`: el valor al terminar; se reserva su ancho con espacios de cifra
    (U+2007) para que pasar de "8" a "11" no corra el número ni lo re-centre."""
    if final and len(final) > len(texto):
        texto = "\u2007" * (len(final) - len(texto)) + texto
    if TNUM:
        d.text(xy, texto, font=font, fill=fill, anchor=anchor, features=TNUM)
        return
    ancho = largo(texto, font, True)
    x, y = xy
    x -= {"l": 0, "m": ancho / 2, "r": ancho}[anchor[0]]
    celda = ancho_tabular(font)
    for c in texto:
        w_c = celda if c.isdigit() else d.textlength(c, font=font)
        d.text((x + w_c / 2, y), c, font=font, fill=fill, anchor="m" + anchor[1])
        x += w_c


def fuente_que_cabe(fabrica, texto, tam, ancho_max, peso=800, minimo=18, tabular=False):
    """La fuente más grande (<= tam) con la que `texto` cabe en `ancho_max`.
    `fabrica` es ctx.fT o ctx.fX. Una cifra o etiqueta nunca se sale de su
    tarjeta: se encoge (y nunca por debajo de `minimo`).

    El piso de aquí (18) NO es el piso de legibilidad (26, MIN_LETRA): es el
    mínimo de "no microscópico". El auto-fit existe para que el texto QUEPA
    — si el piso fuera 26, un copy largo se saldría de su caja y la escena
    entera se iría al piso de la zona segura (medido: x0.72 con copy x2).
    El que juzga la legibilidad es el QA (`medir_animacion`, LETRA_MIN): si
    el texto queda por debajo de 26, la pieza no se entrega y se acorta el
    copy, no se achica la letra (references/copy.md)."""
    tam = int(tam)
    while tam > minimo and largo(texto, fabrica(tam, peso), tabular) > ancho_max:
        tam = max(minimo, int(tam * 0.92))
    return fabrica(tam, peso)


def circulo_numero(d, cx, cy, radio, texto, color, color_texto, ctx, alpha=255):
    """Un numero DENTRO de un circulo, centrado y sin desbordar.

    Primitiva unica (la usan `pasos` e `index`): el diametro manda sobre la
    fuente — la cifra se encoge con `fuente_que_cabe` hasta caber en el
    ancho util del circulo (1.4·radio) y se dibuja con `cifra` (tabular,
    centrada en su celda). Antes cada escena fijaba su propio par
    circulo/fuente: en `index` el circulo era de 32 px fijos con la fuente
    secundaria (~44 px), asi que un numero de dos cifras desbordaba y el
    inactivo (gris sobre gris) no se leia.
    """
    texto = str(texto)
    def _con_alpha(c):
        c = tuple(c)
        return c[:3] + (int(c[3] * alpha / 255),) if len(c) == 4 else c + (int(alpha),)
    relleno = _con_alpha(color)
    tinta = _con_alpha(color_texto)
    d.ellipse([cx - radio, cy - radio, cx + radio, cy + radio], fill=relleno)
    fnt = fuente_que_cabe(ctx.fT, texto, int(radio * 1.05), int(radio * 1.4),
                          800, tabular=True)
    cifra(d, (cx, cy), texto, fnt, tinta, anchor="mm", final=texto)


def texto_que_cabe(fabrica, texto, tam, ancho_max, peso=400, max_lineas=2, minimo=18):
    """Ajusta un texto a un ancho PARTIÉNDOLO antes de encogerlo.

    Partir es mejor que encoger: el texto partido conserva el tamaño de la
    escala (se lee igual), mientras que encogerlo lo deja ilegible. Si aun
    partido en `max_lineas` no cabe, se encoge (hasta `minimo`).
    Devuelve (fuente, lineas).
    """
    tam = int(tam)
    fnt = fabrica(tam, peso)
    lineas = linewrap(texto, fnt, ancho_max)
    if len(lineas) <= max_lineas:
        return fnt, lineas
    t = tam
    while t > minimo:
        t = max(minimo, int(t * 0.92))
        fnt = fabrica(t, peso)
        lineas = linewrap(texto, fnt, ancho_max)
        if len(lineas) <= max_lineas:
            break
    return fnt, lineas[:max_lineas]


def columnas_grilla(n):
    """Columnas para n tarjetas según el formato: en 9:16 una columna hasta 3
    (filas anchas que se leen), 2 desde 4; en 16:9 una fila hasta 4."""
    if H > W:
        return 1 if n <= 3 else 2
    return min(n, 4) if n <= 4 else 3


def linewrap(text, fnt, max_width, tmp=None):
    """Word-wrap que respete anchos reales con la fuente dada.
    Devuelve lista de líneas que caben en max_width. DRY: lo usan `quote`, `versus`, `stats`."""
    if tmp is None:
        tmp = ImageDraw.Draw(Image.new("L", (10, 10)))
    palabras = text.split()
    lineas, linea = [], ""
    for p in palabras:
        prueba = (linea + " " + p).strip()
        if tmp.textlength(prueba, font=fnt) <= max_width or not linea:
            linea = prueba
        else:
            lineas.append(linea)
            linea = p
    if linea:
        lineas.append(linea)
    return lineas


def text_reveal(d, text, fnt, x, y, t, t0, dur, color, fill=None, anchor="la", fundido=0.06):
    """Dibuja `text` carácter a carácter (typewriter) a ritmo CONSTANTE (una
    máquina de escribir no acelera: antes usaba ease_out y tecleaba rápido al
    principio). Cada carácter nace con un fundido corto (`fundido` s), no de
    golpe; el prefijo ya escrito se dibuja de una vez (conserva el kerning).
    Devuelve cuántos caracteres hay a la vista. DRY: `sc_typewriter`.
    """
    if t < t0 or not text:
        return 0
    paso = max(dur, 1e-6) / len(text)
    nacidos = min(len(text), int((t - t0) / paso) + 1)    # caracteres que ya empezaron a aparecer
    col = fill or color
    base = col[:3]
    a0 = col[3] if len(col) > 3 else 255
    llenos = [c for c in range(nacidos) if t - (t0 + c * paso) >= fundido]
    n_llenos = len(llenos)
    if n_llenos:
        d.text((x, y), text[:n_llenos], font=fnt, fill=base + (a0,), anchor=anchor)
    for c in range(n_llenos, nacidos):   # el/los que están naciendo
        a = clamp01((t - (t0 + c * paso)) / fundido)
        cx = x + d.textlength(text[:c], font=fnt)
        d.text((cx, y), text[c], font=fnt, fill=base + (int(a0 * a),), anchor=anchor)
    return nacidos


def kenburns(img, t, t0, dur, zoom_from=1.0, zoom_to=1.15, pan_x=0.0, pan_y=0.0):
    """Zoom + paneo progresivo sobre una imagen (devuelve una imagen del mismo tamaño).
    `pan_x`, `pan_y` ∈ [-1, 1] dirigen el paneo. Transformación afín en coma
    flotante: un recorte con offsets enteros hace temblar los paneos lentos.

    DRY: lo usan `sc_kenburns`, `sc_demo` y futuros overlays sobre imagen.
    """
    p = ease_in_out(clamp01((t - t0) / max(dur, 1e-6))) if t >= t0 else 0.0
    z = max(1e-3, lerp(zoom_from, zoom_to, p))
    W2, H2 = img.size
    ox = W2 * (z - 1) / z * (0.5 + pan_x * 0.3)
    oy = H2 * (z - 1) / z * (0.5 + pan_y * 0.3)
    return img.transform(img.size, Image.AFFINE, (1 / z, 0, ox, 0, 1 / z, oy),
                         resample=Image.BICUBIC)


def smoothstep(p):
    """Acelera desde reposo y frena en el destino: el cursor que se lee humano."""
    p = clamp01(p)
    return p * p * (3 - 2 * p)


def icono_linea(d, nombre, cx, cy, s, color, grosor=None):
    """Un icono de LINEA: el trazo, no el dibujo.

    MEDIDO sobre el reel De8KNkdDT68 (1080x1920):
      · el GLOBO: circulo de 69 px (radio 34) con una elipse vertical de 20 de
        ancho y la linea del ecuador; el trazo es de 7 px;
      · la ALERTA: triangulo de 66 de base y 60 de alto, con el signo de
        exclamacion (barra + punto) centrado en el centroide;
      · la LUPA: circulo con el mango en 45 grados;
      · el RELOJ: circulo con dos agujas;
      · el CODIGO: `</>` con tres trazos.

    `s` es el radio del icono (la mitad de su caja) y el trazo sale de `s` si
    no se dice (el 20 % del radio: con el radio de 34 son 7 px, los del reel).
    El color se pasa como RGBA.
    """
    g = grosor or max(2, int(s * 0.20))
    c = color
    n = (nombre or "").strip().lower()
    if n in ("globo", "globe", "mundo", "web"):
        d.ellipse([cx - s, cy - s, cx + s, cy + s], outline=c, width=g)
        d.ellipse([cx - s * 0.29, cy - s, cx + s * 0.29, cy + s], outline=c, width=g)
        d.line([cx - s, cy, cx + s, cy], fill=c, width=g)
    elif n in ("alerta", "aviso", "warning", "alarma"):
        d.line([cx, cy - s * 0.88, cx - s * 0.97, cy + s * 0.88], fill=c, width=g)
        d.line([cx, cy - s * 0.88, cx + s * 0.97, cy + s * 0.88], fill=c, width=g)
        d.line([cx - s * 0.97, cy + s * 0.88, cx + s * 0.97, cy + s * 0.88],
               fill=c, width=g)
        # el signo, en el centroide (mas abajo que el centro de la caja)
        d.line([cx, cy - s * 0.15, cx, cy + s * 0.25], fill=c, width=max(2, int(g * 0.9)))
        d.ellipse([cx - s * 0.11, cy + s * 0.38, cx + s * 0.11, cy + s * 0.60],
                  fill=c)
    elif n in ("lupa", "buscador", "busqueda", "search"):
        r = s * 0.62
        ccx, ccy = cx - s * 0.12, cy - s * 0.12
        d.ellipse([ccx - r, ccy - r, ccx + r, ccy + r], outline=c, width=g)
        d.line([ccx + r * 0.72, ccy + r * 0.72, cx + s * 0.92, cy + s * 0.92],
               fill=c, width=g)
    elif n in ("reloj", "clock", "tiempo"):
        d.ellipse([cx - s, cy - s, cx + s, cy + s], outline=c, width=g)
        d.line([cx, cy, cx, cy - s * 0.62], fill=c, width=g)
        d.line([cx, cy, cx + s * 0.44, cy + s * 0.20], fill=c, width=g)
    elif n in ("codigo", "code", "terminal"):
        d.line([cx - s * 0.30, cy - s * 0.52, cx - s * 0.72, cy], fill=c, width=g)
        d.line([cx - s * 0.72, cy, cx - s * 0.30, cy + s * 0.52], fill=c, width=g)
        d.line([cx + s * 0.30, cy - s * 0.52, cx + s * 0.72, cy], fill=c, width=g)
        d.line([cx + s * 0.72, cy, cx + s * 0.30, cy + s * 0.52], fill=c, width=g)
        d.line([cx + s * 0.16, cy - s * 0.66, cx - s * 0.16, cy + s * 0.66],
               fill=c, width=g)
    else:
        # un icono desconocido: el borde de una ficha, para que se vea que
        # falta (y no un holes silencioso en la pieza)
        d.rounded_rectangle([cx - s * 0.7, cy - s * 0.7, cx + s * 0.7, cy + s * 0.7],
                            radius=int(s * 0.25), outline=c, width=g)


def linea_discontinua(d, x0, x1, y, color, grosor=3, largo=10, hueco=12):
    """Una linea de TRAZOS: el conector de la cadena de estados.

    MEDIDO sobre el reel De8KNkdDT68: los guiones miden 10 px y el hueco
    12 (el paso es de 22), y la linea arranca a 16 px del borde del nodo y
    termina a 10 px del siguiente (no toca los bordes: el conector une, no
    pega).
    """
    if x1 <= x0:
        return
    x = x0
    while x < x1:
        xe = min(x1, x + largo)
        # el trazo va de x a xe-1: `largo` es la TINTA, no los puntos (PIL
        # dibuja el extremo final incluido: con 10 y 11 sale un px de mas)
        d.line([x, y, xe - 1, y], fill=color, width=grosor)
        x = xe + hueco


def trazado(layer, puntos, color, grosor=6, progreso=1.0, desvanecer=0.25,
            alpha=255, brillo=True, cola=None):
    """Un TRAZADO de luz: la linea que lo ata todo.

    LA PRIMITIVA DRY DE LA PIEZA. El prompt del reel de referencia ("The
    Path", spec de Duolingo) pide expressly que "la linea la dibuje UNA sola
    funcion" y la usa para SEIS cosas distintas: revelar el logotipo, la
    barra de progreso, la llama, la onda de voz, la linea bajo el lema y el
    camino de estaciones. Aqui es lo mismo: un unico `trazado` y cada escena
    lo llama con sus puntos. La forma del trazado la decide quien lo llama
    (una recta, una S, una onda), no esta funcion.

    `puntos`: [(x, y), ...] la polilinea.
    `progreso`: 0..1, que parte del trazado esta escrita (la linea "corre").
    `desvanecer`: la cola se apaga (0 = la cola no se apaga nunca).
    `cola`: el ALFABETO de colores por los que va pasando la linea (la linea
    se divide en ramas de colores: el camino que se abre en cuatro).
    `brillo`: el halo ancho debajo del nucleo (un glow, nunca neon).
    `alpha`: la opacidad global.

    Se dibuja sobre una CAPA propia y se compone (no se dibuja con alfa
    encima): con ImageDraw el alfa REEMPLAZA el pixel, y una cola que se
    apaga borraria lo que hubiera debajo.
    """
    if not puntos or len(puntos) < 2:
        return
    sub = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    ds = ImageDraw.Draw(sub)
    # la longitud acumulada de cada tramo (para saber cuanto se ha escrito)
    largos = [0.0]
    for i in range(1, len(puntos)):
        dx = puntos[i][0] - puntos[i - 1][0]
        dy = puntos[i][1] - puntos[i - 1][1]
        largos.append(largos[-1] + math.hypot(dx, dy))
    total = largos[-1] or 1.0
    hasta = clamp01(progreso) * total
    if hasta <= 0:
        return
    cola_t = clamp01(desvanecer) * total
    # el trazo se recorre en pasos FINOS: la cola que se apaga y el degradado
    # de color son por PUNTO, no por tramo (con un tramo solo —una recta—
    # la cola entera se apagaba o no se apagaba nunca)
    paso = max(2.0, float(grosor))
    for i in range(1, len(puntos)):
        x0, y0 = puntos[i - 1]
        x1, y1 = puntos[i]
        seg = math.hypot(x1 - x0, y1 - y0)
        if seg <= 0:
            continue
        n_sub = max(1, int(seg / paso))
        for k in range(n_sub):
            u0, u1 = k / n_sub, (k + 1) / n_sub
            ax, ay = x0 + (x1 - x0) * u0, y0 + (y1 - y0) * u0
            bx, by = x0 + (x1 - x0) * u1, y0 + (y1 - y0) * u1
            pos = largos[i - 1] + seg * u0
            if pos > hasta:
                continue
            a = alpha
            if cola_t > 0:
                a = alpha if pos < hasta - cola_t else \
                    int(alpha * clamp01((hasta - pos) / cola_t))
            if a <= 0:
                continue
            col = color
            if cola:
                # el color va cambiando a lo largo del trazado (las ramas):
                # el primer color ocupa el primer `1/n` del camino, el
                # segundo el siguiente, y asi hasta el final
                idx = int((pos / total) * len(cola))
                col = cola[max(0, min(len(cola) - 1, idx))]
            rgb = tuple(int(c) for c in col[:3])     # el alfa lo pone el trazo
            if brillo:
                ds.line([ax, ay, bx, by], fill=rgb + (int(a * 0.18),),
                        width=int(grosor * 3.2))
            ds.line([ax, ay, bx, by], fill=rgb + (a,), width=int(grosor))
    layer.alpha_composite(sub)


def puntos_de_ruta(x0, y0, x1, y1, forma="recta", n=48, amp=0.18):
    """Los puntos de un trazado, segun la forma: `recta`, `s` (la S que
    recorre el camino de estaciones), `onda` (la voz) o `arco`.

    La FORMA la decide quien llama; `trazado` solo sabe dibujar. Es la
    misma idea que las primitivas de la casa: una funcion, muchas formas.
    """
    pts = []
    if forma == "s":
        # la amplitud es del RECORRIDO y la S se abre en PERPENDICULAR a el:
        # igual en una ruta horizontal (se abre en y) que en una vertical (en
        # x; el camino de 9:16). Antes se medía con |x1-x0| y en vertical no
        # habia S.
        largo_r = math.hypot(x1 - x0, y1 - y0)
        amp_px = amp * largo_r * 0.12
        nx, ny = -(y1 - y0) / max(1e-9, largo_r), (x1 - x0) / max(1e-9, largo_r)
        for i in range(n + 1):
            p = i / n
            o = math.sin(p * math.pi) * amp_px
            pts.append((x0 + (x1 - x0) * p + nx * o, y0 + (y1 - y0) * p + ny * o))
    elif forma == "onda":
        for i in range(n + 1):
            p = i / n
            x = x0 + (x1 - x0) * p
            y = y0 + math.sin(p * math.pi * 2) * (y1 - y0) * amp
            pts.append((x, y))
    elif forma == "arco":
        for i in range(n + 1):
            p = i / n
            ang = math.pi * (1 - p)
            cx, cy = (x0 + x1) / 2, (y1 + (x1 - x0) * 0.5) / 2
            r = (x1 - x0) / 2
            pts.append((cx + r * math.cos(ang) * -1, cy - r * math.sin(ang)))
    else:
        for i in range(n + 1):
            p = i / n
            pts.append((x0 + (x1 - x0) * p, y0 + (y1 - y0) * p))
    return pts


def cursor(d, x, y, escala=1.0, color=None, alpha=255):
    """Flecha de puntero con la punta en (x, y). DRY: `pago`, `demo`.
    `alpha`: el cursor entra fundido (aparecer de la nada es un pop)."""
    s = 54 * escala
    d.polygon([(x, y), (x, y + s * 1.4), (x + s * 0.45, y + s), (x + s * 0.7, y + s * 1.5),
               (x + s * 0.9, y + s * 1.35), (x + s * 0.65, y + s * 0.85), (x + s, y + s)],
              fill=(color or BLANCO) + (int(alpha),), outline=(0, 0, 0, int(160 * alpha / 255)))


def perspectiva_y(img, grados, focal=2.6):
    """Gira `img` sobre su eje vertical con perspectiva real (rotateY de CSS):
    el borde que se aleja se encoge, el que se acerca crece. `focal` en
    anchos de imagen (más chico = perspectiva más marcada). Se resuelven los
    8 coeficientes de la homografía salida→entrada que pide PIL."""
    if abs(grados) < 0.05:
        return img
    w, h = img.size
    th = math.radians(grados)
    f = focal * w
    dst = []
    for x, y in ((0, 0), (w, 0), (w, h), (0, h)):
        xc, yc = x - w / 2, y - h / 2
        z = xc * math.sin(th)
        k = f / (f + z)
        dst.append((w / 2 + xc * math.cos(th) * k, h / 2 + yc * k))
    xs = [p[0] for p in dst]
    ys = [p[1] for p in dst]
    ox, oy = min(xs), min(ys)
    ow, oh = int(math.ceil(max(xs) - ox)), int(math.ceil(max(ys) - oy))
    src = ((0, 0), (w, 0), (w, h), (0, h))
    A, B = [], []
    for (X, Y), (x, y) in zip(dst, src):   # salida (X,Y) -> entrada (x,y)
        X -= ox
        Y -= oy
        A.append([X, Y, 1, 0, 0, 0, -x * X, -x * Y]); B.append(x)
        A.append([0, 0, 0, X, Y, 1, -y * X, -y * Y]); B.append(y)
    coef = np.linalg.solve(np.array(A, float), np.array(B, float))
    return img.transform((max(1, ow), max(1, oh)), Image.PERSPECTIVE, tuple(coef),
                         resample=Image.BICUBIC)


def grupo():
    """Capa vacía para dibujar UN elemento compuesto (un paso, una fila) y
    hacerlo entrar entero con fundir()."""
    sub = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    return sub, ImageDraw.Draw(sub)


def fundir(layer, sub, k, dy=24):
    """Entrada de un grupo: fundido + elevación con el resorte k. La regla
    "nada aparece de golpe" en una sola primitiva (no un alfa por elemento)."""
    if k <= 0:
        return
    a = clamp01(k * 1.4)
    if a < 1:
        sub.putalpha(sub.split()[3].point(lambda v: int(v * a)))
    oy = int((1 - min(1, k)) * dy)
    if oy < 0:   # entra desde arriba: recortar en vez de un destino negativo
        sub = sub.crop((0, -oy, W, H))
        oy = 0
    layer.alpha_composite(sub, (0, oy))


def _revela_clip(layer, tile, xy, k):
    """Revelado por máscara (animacion.md §6): `tile` es el texto dibujado en
    su sitio FINAL y su borde inferior es la línea de clip. Con el resorte k
    del rol que entra, el texto sube desde detrás de esa línea: va (1-k)·alto
    más abajo y lo que cae fuera de la caja no se ve. Sin curva nueva: el
    gesto es el de `entra`. Afín sub-píxel, así que es función pura de t (el
    blur por sub-frames lo necesita). El fundido acompaña al resorte (alfa =
    k): con un fundido corto (k·3) la tinta que el clip destapa en UN frame
    en un titular de 124 px era un pop para el medidor según dónde cayera la
    escena (medido moviendo la apertura: pops en 3 de 5 alturas; con alfa = k,
    0 de 11)."""
    if k <= 0:
        return
    oy = (1 - k) * tile.height   # k > 1 (overshoot): asoma un poco; el tile trae aire arriba
    if abs(oy) > 0.01:
        tile = tile.transform(tile.size, Image.AFFINE, (1, 0, 0, 0, 1, -oy),
                              resample=Image.BICUBIC)
    a = clamp01(k)
    if a < 1:
        tile.putalpha(tile.split()[3].point(lambda v: int(v * a)))
    x, y = int(xy[0]), int(xy[1])
    if x < 0 or y < 0:   # alpha_composite no acepta destinos negativos: recortar
        tile = tile.crop((max(0, -x), max(0, -y), tile.width, tile.height))
        x, y = max(0, x), max(0, y)
    layer.alpha_composite(tile, (x, y))


def check(d, cx, cy, s, color, grosor=None):
    """Check dibujado (no glifo: ✓ no existe en todas las fuentes y sale como
    caja vacía). `s` = medio ancho del trazo."""
    g = grosor or max(3, int(s * 0.38))
    d.line([(cx - s * 0.9, cy), (cx - s * 0.28, cy + s * 0.66)], fill=color, width=g)
    d.line([(cx - s * 0.28, cy + s * 0.66), (cx + s, cy - s * 0.76)], fill=color, width=g)


def onda_clic(d, x, y, t, t_clic, radio=90, dur=0.5):
    """Onda del clic: nace en `t_clic` y se disipa. Devuelve el pulso (1 al
    tocar, 0 al terminar) para escalar el cursor en el mismo frame."""
    if t < t_clic:
        return 0.0
    pk = clamp01((t - t_clic) / dur)
    if pk < 1:
        r = radio * pk
        d.ellipse([x - r, y - r, x + r, y + r], outline=ACENTO + (int(220 * (1 - pk)),), width=5)
    return 1 - pk


def ancho_tabular(ctx_font):
    """Ancho fijo de dígito (el del dígito más ancho): números que no tiemblan."""
    tmp = ImageDraw.Draw(Image.new("L", (10, 10)))
    return max(tmp.textlength(c, font=ctx_font) for c in "0123456789")


RODAR = 0.45   # s que dura el giro de un dígito (0.25 con ease_out saltaba ~100 px/frame)


def _plumas(w, h, borde=0.22):
    """Máscara vertical con bordes difuminados: el dígito entra y sale del
    tambor como en un odómetro real, no cortado a cuchillo."""
    col = np.clip(np.minimum(np.arange(h), np.arange(h)[::-1]) / max(1, h * borde), 0, 1)
    return Image.fromarray((np.repeat(col[:, None], w, axis=1) * 255).astype(np.uint8), "L")


def odometro(layer, texto, texto_prev, rodar, cx, cy, fnt, color):
    """Cifras tipo odómetro centradas en (cx, cy): cada dígito que cambia rueda
    de `texto_prev` a `texto` según `rodar` ∈ [0, 1] (smoothstep, simétrico);
    los demás quedan quietos. Celdas de ancho fijo (tabular) con bordes de
    tambor difuminados. DRY: `countdown` y contadores de rollo."""
    tmp = ImageDraw.Draw(Image.new("L", (10, 10)))
    dw = ancho_tabular(fnt)
    anchos = [dw if c.isdigit() else tmp.textlength(c, font=fnt) for c in texto]
    x = cx - sum(anchos) / 2
    alto = int(fnt.size * 1.25)
    for i, c in enumerate(texto):
        pc = texto_prev[i] if i < len(texto_prev) else c
        celda = Image.new("RGBA", (int(anchos[i]) + 2, alto), (0, 0, 0, 0))
        dc = ImageDraw.Draw(celda)
        if c != pc and rodar > 0:
            off = alto * smoothstep(rodar)
            dc.text((anchos[i] / 2, alto / 2 - off), pc, font=fnt, fill=color, anchor="mm")
            dc.text((anchos[i] / 2, alto / 2 + alto - off), c, font=fnt, fill=color, anchor="mm")
            a_ = celda.split()[3]
            celda.putalpha(Image.fromarray(
                (np.asarray(a_, np.float32) * np.asarray(_plumas(*celda.size), np.float32) / 255)
                .astype(np.uint8), "L"))
        else:
            dc.text((anchos[i] / 2, alto / 2), pc if rodar <= 0 else c, font=fnt, fill=color,
                    anchor="mm")
        layer.alpha_composite(celda, (int(x), int(cy - alto / 2)))
        x += anchos[i]


def estrellas(layer, cx, cy, valor, maximo=5, tam=46, k=1.0, color=None):
    """Fila de estrellas con relleno fraccional EXACTO (4.5 se ve 4.5): pista
    tenue + relleno barrido de izquierda a derecha hasta valor/maximo * k."""
    gap = tam * 0.35
    total = maximo * tam + (maximo - 1) * gap
    x0 = cx - total / 2
    def estrella(x, y, r):
        return [(x + (r if j % 2 == 0 else r * 0.45) * math.cos(-math.pi / 2 + j * math.pi / 5),
                 y + (r if j % 2 == 0 else r * 0.45) * math.sin(-math.pi / 2 + j * math.pi / 5))
                for j in range(10)]
    d = ImageDraw.Draw(layer)
    capa = Image.new("L", (W, H), 0); dm = ImageDraw.Draw(capa)
    for i in range(maximo):
        pts = estrella(x0 + i * (tam + gap) + tam / 2, cy, tam / 2)
        d.polygon(pts, fill=(255, 255, 255, 40))
        dm.polygon(pts, fill=255)
    lleno = clamp01(valor / max(1, maximo)) * clamp01(k)
    corte = Image.new("L", (W, H), 0)
    ImageDraw.Draw(corte).rectangle([0, 0, x0 + total * lleno, H], fill=255)
    from PIL import ImageChops
    mascara = ImageChops.multiply(capa, corte)
    layer.paste(Image.new("RGBA", (W, H), (color or ACENTO) + (255,)), (0, 0), mascara)


# ================= ESCENAS =================
def sc_apertura(ctx,e,t):
    layer=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(layer)
    cambio=e["at"]["cambio"]
    # fondo de entrada tras el titular (centrado con el titular: H*0.44)
    r=W*0.42*entra(t, e["from"], "lento")*(1-prog(t,cambio-0.15,cambio+0.35)*0.75)
    if r>4:
        # con isotipo en el pack, el fondo es la MARCA (crece y se encoge igual);
        # sin isotipo, el blob organico de cuatro lobulos de siempre
        if not marca_fondo(ctx, layer, W/2, H*0.44, r, t, e["from"], 0.7):
            pts=[]
            for i in range(72):
                a=i/72*math.pi*2+t*0.8
                rr=r*(1+0.28*math.sin(a*4+t*2))
                pts.append((W/2+rr*math.cos(a),H*0.44+rr*math.sin(a)))
            d.polygon(pts,fill=ACENTO+(58,))
    # micro-idle: el titular asentado respira (±5 px), nunca queda congelado
    if t < cambio:   # el primer titular se va (fundido + sube) en vez de desaparecer de golpe
        ks=prog(t,cambio-0.35,cambio)   # cúbica: arranca suave
        cy=vy(0.44)+flota(t,e["at"]["p1"][-1]+0.5,5,0.45)-ks*30
        sub,_=grupo()
        titular(ctx,sub,t,e["texto1"],e["at"]["p1"],tam=150,cy=cy)
        if ks>0: sub.putalpha(sub.split()[3].point(lambda v:int(v*(1-ks))))
        layer.alpha_composite(sub)
    else:
        cy=vy(0.44)+flota(t,e["at"]["p2"][-1]+0.5,5,0.45)
        titular(ctx,layer,t,e["texto2"],e["at"]["p2"],tam=124,cy=cy)
    return capa_salida(layer,t,e["to"])

def sc_canales(ctx,e,t):
    layer=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(layer)
    at=e["at"]; junta=prog(t,at["junta"]-0.4,at["junta"]+0.6)   # 1 s: las tarjetas no barren >60 px/frame
    rotulo(ctx,layer,t,e.get("rotulo",""),at["rotulo"],y=rotulo_y())
    # marca que sube y se encoge (grupo logo+texto centrado)
    k=entra(t, at["marca"], "lento")
    if k>0:
        my=lerp(vy(0.52),vy(0.36),junta)
        iso_ok=ctx.iso is not None and es_marca_del_pack(e["marca"])
        # una marca larga encoge para caber (factor FIJO de la escena: sin saltos)
        zx0_,_,zx1_,_=caja_segura()
        ancho110=ctx.tmp.textlength(e["marca"],font=ctx.fT(110,800))+(176 if iso_ok else 0)
        sc=lerp(1.0,0.55,junta)*k*min(1.0,(zx1_-zx0_)*0.94/ancho110)
        fnt_m=ctx.fT(110*sc,800)   # tamaño fraccionario: escala sin saltos de 1 px
        tw=ctx.tmp.textlength(e["marca"],font=fnt_m)
        iw=int(150*sc) if iso_ok else 0
        total=iw+(26*sc if iso_ok else 0)+tw
        x0=(W-total)/2
        if iso_ok and iw > 0:
            iso=ctx.iso.resize((iw,iw),Image.LANCZOS)
            a=iso.split()[3].point(lambda v:int(v*clamp01(k*1.4))); iso.putalpha(a)
            layer.alpha_composite(iso,(int(x0),int(my-iw/2)))
        if iso_ok:
            x0+=iw+26*sc
        d.text((x0,my),e["marca"],font=fnt_m,fill=BLANCO+(int(255*clamp01(k*1.4)),),
               anchor="lm")
    # tarjetas de canal
    for i,c in enumerate(e["canales"]):
        k2=entra(t, c["at"], "elemento")
        if k2<=0: continue
        ang=[-1,0,1][i] if i<3 else 0
        zx0,_,zx1,_=caja_segura()
        abre=min(unidad()*0.3,(zx1-zx0-300)/2)   # recorrido en unidad() y dentro de la zona segura
        # si 3 tarjetas de 300 no caben lado a lado (9:16), van en CASCADA: cada
        # una 96 px más abajo, el nombre de la anterior sigue a la vista
        cascada=96 if 3*300+32>zx1-zx0 else 0
        sx,sy=W/2+ang*abre,vy(0.68)+(i-1)*cascada
        fy=vy(0.58)-120+i*150
        x=lerp(sx,W/2,junta); y=lerp(sy,fy,junta)
        w=lerp(300,min(880,zx1-zx0),junta); h=124
        sc2=k2
        ww,hh=int(w*sc2),int(h*sc2)
        if ww<10: continue
        card=Image.new("RGBA",(ww,hh),(0,0,0,0)); dc=ImageDraw.Draw(card)
        dc.rounded_rectangle([0,0,ww,hh],radius=28,fill=PANEL2+(255,))
        dc.rounded_rectangle([0,0,ww,hh],radius=28,outline=(255,255,255,28),width=2)
        # icono canal (círculo con inicial) — centrado vertical exacto (62 = 124/2)
        dc.ellipse([28,24,104,100],fill=ACENTO+(255,))
        # icono: `icono` del canal o la inicial de su NOMBRE (WhatsApp y Web no son ambos "W")
        ico=str(c.get("icono") or (c.get("nombre") or c["canal"])[:1]).strip()
        dc.text((66,62),ico.upper() if len(ico)==1 else ico,font=fuente_que_cabe(ctx.fT,ico,44,60,800),
                fill=BLANCO,anchor="mm")
        # el NOMBRE del canal entra con su tarjeta (sin él, 2 s de tarjetas vacías:
        # parecían placeholders); el mensaje se revela al asentar la bandeja y el
        # nombre sube a hacerle lugar
        at_=clamp01((junta-0.4)/0.35)
        an=clamp01(k2*1.4)
        if an>0:
            fn=fuente_que_cabe(ctx.fX,c["nombre"],34,max(40,ww-150),800)
            dc.text((130,lerp(62,48,smoothstep(at_))),c["nombre"],font=fn,fill=BLANCO+(int(255*an),),anchor="lm")
        if at_>0:
            dc.text((130,74),c["texto"][:34],font=ctx.fX(ESCALA["nota"],400),fill=GRIS+(int(255*at_),))
        card=card.rotate((1-junta)*ang*8,expand=True,resample=Image.BICUBIC)
        fy_float=flota(t,c["at"]+1.2,5,0.4) if junta>0.9 else 0
        layer.alpha_composite(card,(int(x-card.width/2),int(y-card.height/2+fy_float)))
    return capa_salida(layer,t,e["to"])

def sc_medianoche(ctx,e,t):
    layer=Image.new("RGBA",(W,H),(0,0,0,0))
    rotulo(ctx,layer,t,e.get("rotulo",""),e["from"]+0.1,y=rotulo_y())
    k=entra(t, e["from"], "bloque")
    if k>0:
        tw,th=560,1140
        _,_,_,zy1=caja_segura(); arriba=rotulo_y()+80          # bajo el rótulo, sobre la UI
        sc=min(0.82,(zy1-arriba)*0.96/th)*(0.8+0.2*min(1,k)); cy_tel=(arriba+zy1)/2
        ph=Image.new("RGBA",(tw,th),(0,0,0,0)); dp=ImageDraw.Draw(ph)
        dp.rounded_rectangle([0,0,tw,th],radius=86,fill=(12,12,12,255))
        dp.rounded_rectangle([18,18,tw-18,th-18],radius=70,fill=(16,22,34,255))
        # fondo de pantalla vivo: un halo del acento deriva despacio (la pantalla
        # bloqueada no queda congelada entre notificación y notificación)
        hx=tw/2+130*math.sin(0.9*t); hy=th*0.70+90*math.cos(0.7*t)
        masc=Image.new("L",(tw,th),0)
        ImageDraw.Draw(masc).rounded_rectangle([18,18,tw-18,th-18],radius=70,fill=255)
        brillo=Image.new("RGBA",(tw,th),ACENTO+(0,))
        # a 1/8 y desenfocado: halo suave y barato; la pantalla lo recorta
        resplandor(brillo,(hx-260,hy-260,hx+260,hy+260),ACENTO,120,alfa=110,escala=8)
        brillo.putalpha(ImageChops.multiply(brillo.getchannel("A"),masc))
        ph.alpha_composite(brillo)
        dp.rounded_rectangle([tw/2-85,42,tw/2+85,90],radius=24,fill=(0,0,0,255))
        dp.text((tw/2,160),e.get("fecha",""),font=ctx.fX(ESCALA["secundario"],600),fill=(255,255,255,200),anchor="ma")
        dp.text((tw/2,280),e["hora"],font=ctx.fT(150,700),fill=BLANCO,anchor="ma")   # dígitos hasta y≈438
        nots=e["notificaciones"]
        for i,n in enumerate(nots):
            kn=entra(t, n["at"], "suave")
            if kn<=0: continue
            # cada notificación nueva EMPUJA a las anteriores con resorte (antes
            # saltaban 170 px en un frame: el conteo era un escalón)
            despues=sum(min(1.0,entra(t, m["at"], "suave")) for m in nots[i+1:])
            ny=480+despues*170+(1-min(1,kn))*-24   # baja apenas: nunca cruza la hora
            nw=Image.new("RGBA",(tw-44,140),(0,0,0,0)); dn=ImageDraw.Draw(nw)
            dn.rounded_rectangle([0,0,tw-44,140],radius=28,fill=(255,255,255,36))
            dn.ellipse([22,38,86,102],fill=ACENTO+(255,))
            dn.text((54,70),n["canal"][0].upper(),font=ctx.fT(34,800),fill=BLANCO,anchor="mm")
            dn.text((110,52),n["titulo"],font=ctx.fX(ESCALA["nota"],800),fill=BLANCO)
            # el cuerpo de la notificación es un "nota" de la escala (28 px):
            # antes 24 px, por DEBAJO del piso legible, y con recorte por
            # caracteres. Ahora la letra es la de la escala y el copy se
            # recorta al ancho real de la tarjeta.
            fnt_n=ctx.fX(ESCALA["nota"],400)
            dn.text((110,92),recorta_para(n["texto"],fnt_n,tw-44-110-14,ctx.tmp),
                    font=fnt_n,fill=(255,255,255,190))
            a=nw.split()[3].point(lambda v, _kn=kn:int(v*clamp01(_kn*1.5))); nw.putalpha(a)
            ph.alpha_composite(nw,(22,int(ny)))
        ph=ph.resize((max(1,int(tw*sc)),max(1,int(th*sc))),Image.LANCZOS)
        # giro 3D real al entrar: rotateY de -70° a -12° con el resorte (perspectiva)
        # y sigue girando despacio mientras llegan las notificaciones (-12° → 0°):
        # pantalla oscura = la respiración común no alcanza a leerse como vida
        giro=12*clamp01((t-e["from"])/max(0.1,e["to"]-e["from"]))   # lineal: nace dentro del resorte de entrada
        ph=perspectiva_y(ph,lerp(-70,-12,min(1.0,k))+giro)
        al=clamp01(k*1.6)   # entra fundido, no de golpe en el primer frame
        if al<1: ph.putalpha(ph.split()[3].point(lambda v:int(v*al)))
        layer.alpha_composite(ph,(int(W/2-ph.width/2),int(cy_tel-ph.height/2)))
    return capa_salida(layer,t,e["to"])

def wrap(text,fnt,maxw,tmp):
    words=text.split(" "); lines=[]; cur=""
    for w_ in words:
        t2=(cur+" "+w_).strip()
        if tmp.textlength(t2,font=fnt)<=maxw or not cur: cur=t2
        else: lines.append(cur); cur=w_
    if cur: lines.append(cur)
    return lines

def sc_chat(ctx,e,t):
    """Conversación cliente (izquierda) / IA (derecha), un mensaje a la vez.
    Mensaje: `de` ("cliente" o cualquier otro = IA), `texto`, `at` opcional:
    sin `at` se deriva del anterior (`pausa` de lectura 0.6 s + `escribe`).
    La IA muestra puntos de "escribiendo" `escribe` s antes de responder
    (default 0.7). La última burbuja de cada racha lleva cola. Hilos largos
    hacen auto-scroll con resorte: lo nuevo queda sobre la banda segura y lo
    viejo se desvanece bajo el rótulo."""
    layer=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(layer)
    at=e.get("at",{}); t_rot=at.get("rotulo",e["from"])
    rotulo(ctx,layer,t,e.get("rotulo",""),t_rot,y=rotulo_y())
    fnt=ctx.fX(ESCALA["secundario"],400); GAP=36; ALTO_ESC=84
    zx0,_,zx1,_=caja_segura()   # burbujas ancladas a los bordes de la zona segura
    ancho_burbuja=min(680,(zx1-zx0)*0.82)
    msgs=[]; reloj=t_rot+0.4
    for m in e.get("mensajes",[]):
        ia=m.get("de")!="cliente"
        esc=m.get("escribe",0.7 if ia else 0.0)
        tm=m["at"] if "at" in m else reloj+m.get("pausa",0.6)+esc
        lineas=wrap(m.get("texto",""),fnt,ancho_burbuja,ctx.tmp)
        tw=max(ctx.tmp.textlength(l,font=fnt) for l in lineas)+70
        msgs.append({"ia":ia,"at":tm,"esc":esc,"lineas":lineas,"tw":tw,
                     "hh":len(lineas)*52+44})
        reloj=tm
    for i,mm in enumerate(msgs):
        mm["cola"]=i==len(msgs)-1 or msgs[i+1]["ia"]!=mm["ia"]
    def escribiendo(mm):
        return mm["esc"]>0 and mm["at"]-mm["esc"]<=t
    # altura de la pila: cada burbuja suma con su resorte (el scroll se desliza solo)
    y0 = vy(0.42); alto = 0.0
    for mm in msgs:
        k=entra(t, mm["at"], "elemento")
        if escribiendo(mm):
            ke=entra(t, mm["at"]-mm["esc"], "elemento")
            alto+=(ALTO_ESC+GAP)*min(1,ke)*(1-min(1,k))
        alto+=(mm["hh"]+GAP)*min(1,max(0,k))
    lk=e.get("link")
    # al acercarse el link, el hilo sube con suavidad (antes el límite cambiaba en
    # un escalón y toda la conversación saltaba ~30 px en un frame)
    kl=smoothstep(clamp01((t-(lk.get("at",1e9)-0.4))/0.35)) if lk else 0.0
    # se interpola el DESPLAZAMIENTO, no el límite: con max(0,…) sobre un límite
    # que baja, el scroll arrancaba a mitad de curva (a velocidad plena)
    sube=lambda lim: max(0.0,y0+alto-lim)
    y=y0-lerp(sube(H-SAFE["bottom"]-20),sube(H*0.70),kl)
    for mm in msgs:
        k=entra(t, mm["at"], "elemento")
        lado_x=lambda w_, _ia=mm["ia"]: zx0+12 if not _ia else zx1-12-w_
        visible=clamp01((y-(rotulo_y()+40))/70)          # se desvanece bajo el rótulo
        if escribiendo(mm) and k<1:
            ke=min(1,entra(t, mm["at"]-mm["esc"], "elemento"))*(1-min(1,k))
            if ke>0.02:
                bw=150; x=lado_x(bw); a=int(255*ke*visible)
                d.rounded_rectangle([x,y,x+bw,y+ALTO_ESC],radius=28,fill=PANEL2+(a,))
                for j in range(3):
                    pul=0.4+0.6*(0.5+0.5*math.sin(t*7.5-j*0.9))
                    cxp=x+45+j*30
                    d.ellipse([cxp-8,y+34,cxp+8,y+50],fill=GRIS+(int(a*pul),))
                y+=(ALTO_ESC+GAP)*ke
        if k<=0: continue
        x=lado_x(mm["tw"]); hh=mm["hh"]
        col=tuple(int(c*0.30) for c in ACENTO) if mm["ia"] else PANEL2
        yy=y+(1-min(1,k))*ELEV
        al=int(255*clamp01(k*1.4)*visible)
        d.rounded_rectangle([x,yy,x+mm["tw"],yy+hh],radius=28,fill=col+(al,))
        if mm["cola"]:
            if mm["ia"]:
                xe=x+mm["tw"]
                d.polygon([(xe-40,yy+hh-4),(xe+12,yy+hh+6),(xe-16,yy+hh-24)],fill=col+(al,))
            else:
                d.polygon([(x+40,yy+hh-4),(x-12,yy+hh+6),(x+16,yy+hh-24)],fill=col+(al,))
        for bi,bl in enumerate(mm["lineas"]):
            d.text((x+34,yy+22+bi*52),bl,font=fnt,fill=BLANCO+(al,))
        y+=(hh+GAP)*min(1,k)
    if lk and t>=lk.get("at",1e9):
        k=entra(t, lk["at"], "bloque")
        cw,chh=min(760,zx1-zx0),150; x=(W-cw)/2
        yy=min(H*0.72,caja_segura()[3]-chh-10)+(1-min(1,k))*ELEV   # sobre la UI de la plataforma
        ak=int(255*clamp01(k*1.4))   # la tarjeta y su texto entran juntos
        d.rounded_rectangle([x,yy,x+cw,yy+chh],radius=28,fill=ACENTO+(int(235*ak/255),))
        d.text((x+40,yy+34),lk.get("titulo",""),font=ctx.fX(ESCALA["secundario"],800),fill=BLANCO+(ak,))
        d.text((x+40,yy+84),lk.get("monto",""),font=ctx.fT(ESCALA["rotulo"],800),fill=BLANCO+(ak,))
    return capa_salida(layer,t,e["to"])

def tinta_sobre(fondo):
    """La tinta (BLANCO o NEGRO de la pieza) que se lee sobre `fondo`: un
    texto blanco fijo sobre un token claro (AVISO, un acento ámbar) no llega
    al piso. Misma regla que `texto_sobre` de _comun."""
    from _comun import texto_sobre
    return hex_a_rgb(texto_sobre(fondo, tokens={"blanco": BLANCO, "negro": NEGRO}))

def color_de_temperatura(f_):
    """Color de una temperatura de lead (tolerante: "caliente", "Hot", "frio"…):
    caliente = ACENTO, tibio = AVISO, frío = GRIS (baja prioridad: neutro).
    Un `color` explícito manda. Desconocida: neutro, nunca un KeyError."""
    if f_.get("color"):
        return hex_a_rgb(f_["color"])
    t_=str(f_.get("temp","")).lower().translate(str.maketrans("áéíóú","aeiou"))
    for claves,col in ((("calien","hot","alta"),ACENTO),(("tib","warm","media"),AVISO),
                       (("fri","cold","baja"),GRIS)):
        if t_.startswith(claves): return tuple(col)
    return GRIS

def sc_leads(ctx,e,t):
    layer=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(layer)
    at=e["at"]
    kr=rotulo(ctx,layer,t,e.get("rotulo",""),at["rotulo"],y=rotulo_y())
    if kr>0:   # el total entra con su rótulo
        d.text((W/2,bajo_rotulo(rotulo_y(),aire=0.15)),e.get("total",""),font=ctx.fM(ESCALA["dato"],700),fill=ACENTO+(int(255*clamp01(kr*1.5)),),anchor="ma")
    filas=e["filas"]; n=len(filas)
    zx0,_,zx1,zy1=caja_segura()   # compuesta DENTRO de la zona segura: no se encoge
    y0=rotulo_y()+140
    # reparte el alto útil: filas densas fijas (128) dejaban ocup~0.38
    alto_util=max(200, zy1 - y0 - 40)
    paso=min(148, max(120, alto_util / max(1, n)))
    alto_fila=min(124, paso - 16)
    fy=flota(t, e["from"]+1.6, 4, 0.36)
    color_temp=color_de_temperatura
    for i,f in enumerate(filas):
        t_f=escalonado({}, "fila", i, e["from"]+0.4)
        k=entra(t, t_f, "elemento")
        if k<=0: continue
        sub,ds=grupo()   # la fila entera entra junta (tarjeta, avatar, textos, barra)
        yy=y0+i*paso+fy
        tarjeta(ctx,sub,zx0,yy,zx1-zx0,alto_fila)
        es_hot = str(f.get("temp","")).lower().startswith(("calien","hot","alta"))
        if f["temp"] in at and t>=at[f["temp"]]:   # el resaltado se enciende fundido, no de golpe
            ah=int(255*smoothstep(clamp01((t-at[f["temp"]])/0.2)))
            if es_hot:
                ah=min(255, int(ah * latido(t, at[f["temp"]], 1.5, 0.10)))
            ds.rounded_rectangle([zx0,yy,zx1,yy+alto_fila],radius=28,outline=color_temp(f)+(ah,),width=4)
        pad_v=max(16, int((alto_fila-64)/2))
        ds.ellipse([zx0+24,yy+pad_v,zx0+88,yy+pad_v+64],fill=color_temp(f)+(255,))
        ds.text((zx0+56,yy+pad_v+32),f["nombre"][0],font=ctx.fT(36,800),fill=tinta_sobre(color_temp(f))+(int(255*clamp01(k)),),anchor="mm")   # tinta oscura: entra con la fila
        bmax=min(260,(zx1-zx0)*0.32)   # barra de puntaje a la derecha, el texto se ajusta al resto
        ancho_txt=(zx1-zx0)-bmax-150
        ds.text((zx0+112,yy+pad_v-4),f["nombre"],font=fuente_que_cabe(ctx.fX,f["nombre"],ESCALA["secundario"],ancho_txt,800),fill=BLANCO)
        ds.text((zx0+112,yy+pad_v+34),f["etapa"],font=fuente_que_cabe(ctx.fX,f["etapa"],ESCALA["nota"],ancho_txt,400),fill=GRIS)
        # barra de puntaje: crece sin rebote (un dato no se pasa de su valor)
        bw=(f["puntaje"]/100)*bmax
        bx=zx1-bmax-24
        by_bar=yy+alto_fila/2-12
        ds.rounded_rectangle([bx,by_bar,bx+bmax,by_bar+24],radius=12,fill=(60,60,60,255))
        g_=smoothstep(clamp01((t-t_f)/0.8))
        if bw*g_>=24:
            ds.rounded_rectangle([bx,by_bar,bx+bw*g_,by_bar+24],radius=12,fill=color_temp(f)+(255,))
        fundir(layer,sub,k,dy=-50)
    return capa_salida(layer,t,e["to"])

def sc_handoff(ctx,e,t):
    layer=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(layer)
    at=e["at"]
    rotulo(ctx,layer,t,e.get("rotulo",""),at["rotulo"],y=rotulo_y())
    k=entra(t, at["persona"], "bloque")
    fy=flota(t, at["persona"]+0.9, 5, 0.36)
    y_card = vy(0.30) + fy
    if k>0:   # la ficha entera entra junta
        sub,ds=grupo()
        zx0,_,zx1,_=caja_segura()   # dentro de la zona segura: la letra conserva su tamaño
        tarjeta(ctx,sub,zx0,y_card,zx1-zx0,220)
        # halo del avatar late en el hold (la ficha no se congela)
        pulso=latido(t, at["persona"]+0.6, 1.6, 0.08)
        r_av=50*pulso
        ds.ellipse([zx0+90-r_av,y_card+110-r_av,zx0+90+r_av,y_card+110+r_av],fill=ACENTO+(255,))
        ini=e.get("iniciales") or "".join(w_[0] for w_ in e["cliente"].split()[:2]).upper()   # derivables del nombre
        ds.text((zx0+90,y_card+110),ini,font=fuente_que_cabe(ctx.fT,ini,44,72,800),fill=tinta_sobre(ACENTO),anchor="mm")
        at_=zx1-zx0-200
        ds.text((zx0+170,y_card+52),e["cliente"],font=fuente_que_cabe(ctx.fX,e["cliente"],ESCALA["dato"],at_,800),fill=BLANCO)
        ds.text((zx0+170,y_card+102),e.get("temp",""),font=ctx.fM(ESCALA["nota"],700),fill=_legible(color_de_temperatura(e),PANEL))   # el token, con luz para leerse en la tarjeta
        ds.text((zx0+170,y_card+142),e.get("nota",""),font=fuente_que_cabe(ctx.fX,e.get("nota",""),ESCALA["nota"],at_,400),fill=GRIS)
        fundir(layer,sub,k)
    y=y_card+270
    zx0,_,zx1,_=caja_segura()
    for i,c in enumerate(e["contexto"]):
        kc=entra(t, escalonado({}, "contexto", i, at["contexto"]), "elemento")
        if kc<=0: continue
        yy=y+i*96+(1-min(1,kc))*-40
        al=int(255*clamp01(kc*1.4))
        d.text((zx0+30,yy),c["k"],font=ctx.fM(ESCALA["secundario"],700),fill=ACENTO+(al,))
        d.text((zx0+30,yy+40),c["v"],font=fuente_que_cabe(ctx.fX,c["v"],ESCALA["secundario"],zx1-zx0-60,400),fill=BLANCO+(al,))
    return capa_salida(layer,t,e["to"])

def sc_pago(ctx,e,t):
    layer=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(layer)
    at=e["at"]
    rotulo(ctx,layer,t,e.get("rotulo",""),at["rotulo"],y=rotulo_y())
    k=entra(t, at["comprobante"], "bloque")
    zx0,_,zx1,zy1=caja_segura()
    cw,chh=min(720,zx1-zx0),420; x=(W-cw)/2; y_card=H*0.36 if H>W else H*0.30
    if k>0:
        yy=y_card+(1-min(1,k))*-80
        tarjeta(ctx,layer,x,yy,cw,chh,radio=32,alpha=int(255*min(1,k)))
        ak=int(255*min(1,k))   # el contenido entra con su tarjeta, no antes
        util=cw-64   # todo cabe en la tarjeta (un monto o un nombre largo encoge, no se sale)
        d.text((W/2,yy+80),e["monto"],font=fuente_que_cabe(ctx.fT,e["monto"],96,util,800,tabular=True),
               fill=BLANCO+(ak,),anchor="ma")
        d.text((W/2,yy+190),e["cliente"],font=fuente_que_cabe(ctx.fX,e["cliente"],ESCALA["dato"],util,600),
               fill=BLANCO+(ak,),anchor="ma")
        d.text((W/2,yy+240),e.get("detalle",""),font=fuente_que_cabe(ctx.fX,e.get("detalle",""),ESCALA["nota"],util,400),
               fill=GRIS+(ak,),anchor="ma")
        d.line([(x+80,yy+300),(x+cw-80,yy+300)],fill=(255,255,255,int(40*ak/255)),width=2)
        # botón que el cursor pulsa: el toque TIENE consecuencia (pasa a confirmado)
        bx0,bx1,by0,by1=x+cw*0.2,x+cw*0.8,yy+322,yy+398
        sc=1-0.06*math.sin(math.pi*clamp01((t-at["toque"])/0.18)) if t>=at["toque"] else 1.0
        mx,my=(bx0+bx1)/2,(by0+by1)/2; hw,hh=(bx1-bx0)/2*sc,(by1-by0)/2*sc
        al=int(255*min(1,k))
        # el toque cambia el estado con un fundido cruzado corto (0.25 s), no de golpe
        c_=smoothstep(clamp01((t-at["toque"])/0.25)) if t>=at["toque"] else 0.0
        if c_<1:
            boton_halo(d, mx, my, hw*2, hh*2, e.get("boton","Pagar"),
                       ctx.fX(ESCALA["dato"],800), t, at["toque"], alpha=int(al*(1-c_)))
        if c_>0:
            boton_halo(d, mx, my, hw*2, hh*2, "", ctx.fX(ESCALA["dato"],800), t, at["toque"],
                       alpha=int(al*c_), hecho=e.get("hecho","Pagado"), fnt_hecho=ctx.fX(34,800))
    if t>=at["cursor"]:
        # cursor que se mueve y pulsa
        ck=prog(t,at["cursor"],at["toque"],smoothstep)   # UNA curva (antes ease sobre ease: saltaba 85 px/frame)
        # del borde de la zona segura al pie del comprobante (el toque cae SOBRE él)
        cx=lerp(x+cw*0.15,x+cw*0.7,ck); cy=lerp(zy1-40,y_card+360,ck)
        pk=onda_clic(d,cx,cy,t,at["toque"])
        cursor(d,cx,cy,1+0.25*math.sin((t-at["toque"])*20)*pk,alpha=255*smoothstep(clamp01((t-at["cursor"])/0.25)))
    return capa_salida(layer,t,e["to"])

def sc_listo(ctx,e,t):
    layer=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(layer)
    t0=e["at"]["listo"]
    k=entra(t, t0, "pop")
    if k>0:
        # asentado el estallido, el check flota (centrado, el push-in casi no lo mueve)
        cy=vy(0.5)+flota(t,t0+0.8,7,0.45)
        # estallido de partículas en anillo
        for i in range(24):
            a=i/24*math.pi*2
            rr=180*ease_out(clamp01((t-t0)/0.6))
            x=W/2+rr*math.cos(a); y=cy+rr*math.sin(a)
            al=int(255*(1-clamp01((t-t0)/0.8)))
            d.ellipse([x-10,y-10,x+10,y+10],fill=ACENTO+(al,))
        # check: el círculo CRECE con su resorte (con rebote) y el texto funde
        r=110*k; al=int(255*clamp01(k*1.5))
        d.ellipse([W/2-r,cy-r,W/2+r,cy+r],fill=ACENTO+(al,))
        if k>0.35: check(d,W/2,cy,58*min(1,k),BLANCO+(al,),max(4,int(22*min(1,k))))
        # el texto cabe en la zona segura o no sale: encoge y parte en dos
        # lineas con su enfasis (antes salia a titular fijo, en una linea,
        # con los *asteriscos* literales y desbordado por ambos lados)
        sg=segs(e["texto"]); zx0,_,zx1,_=caja_segura(); ancho=(zx1-zx0)-20
        tam=ESCALA["titular"]; fnt=ctx.fT(tam,800)
        while tam>MIN_LETRA and max(seg_width(ln,fnt) for ln in partir_segs(sg,fnt,ancho))>ancho:
            tam-=4; fnt=ctx.fT(tam,800)
        for i,ln in enumerate(partir_segs(sg,fnt,ancho)):
            draw_seg(d,(W/2,cy+190+(1-min(1,k))*ELEV+i*tam*1.18),ln,fnt,
                     BLANCO+(al,),ACENTO+(al,),anchor="ma")
    return capa_salida(layer,t,e["to"])

def sc_pildoras(ctx,e,t):
    layer=Image.new("RGBA",(W,H),(0,0,0,0))
    # columnas de píldoras cayendo al fondo (centradas simétricamente en W/2 en cualquier formato)
    ncols = max(7, int(W / 140))
    step = W / (ncols + 1)
    for ci in range(ncols):
        x = int(step * (ci + 1))
        off=(t*160+ci*230)%(H+400)-200
        for pi in range(3):
            y=(off+pi*640)%(H+400)-200
            rot=ci*20+pi*40
            pw,phh=110,54
            pill=Image.new("RGBA",(pw,phh),(0,0,0,0)); dp=ImageDraw.Draw(pill)
            dp.rounded_rectangle([0,0,pw,phh],radius=28,
                                 fill=ACENTO+(26,) if pi%2 else BLANCO+(22,))
            pill=pill.rotate(rot,expand=True,resample=Image.BICUBIC)
            layer.alpha_composite(pill,(int(x-pw/2),int(y)))
    ats=e["at"]["palabras"]
    titular(ctx,layer,t,e["texto"],ats,tam=ESCALA["titular"])
    return capa_salida(layer,t,e["to"])

def sc_hoy(ctx,e,t):
    """Panel del día: contador que sube + tarjetas de tareas en cascada, en la
    grilla de la zona segura (2 columnas en 9:16, una fila en 16:9)."""
    layer=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(layer)
    at=e["at"]
    vertical=H>W
    # rótulo y fecha apilados y la fecha entra con el rótulo
    kr=rotulo(ctx,layer,t,e.get("rotulo",""),at["rotulo"],y=rotulo_y())
    if kr>0:
        d.text((W/2,rotulo_y()+54+(1-min(1,kr))*ELEV),e.get("fecha",""),font=ctx.fX(ESCALA["secundario"],400),
               fill=GRIS+(int(255*clamp01(kr*1.5)),),anchor="ma")
    ck=prog(t,at["cuenta"],at["cuenta"]+0.8,ease_out)   # una sola curva
    # la cifra late en el hold (antes se congelaba al llegar al tope)
    pulso_c = latido(t, at["cuenta"] + 0.9, 1.7, 0.06) if t >= at["cuenta"] + 0.9 else 1.0
    if t>=at["cuenta"]:
        cifra(d,(W/2,rotulo_y()+125 if vertical else rotulo_y()+95),str(int(e["cuenta"]*ck)),
              ctx.fT(130,800),ACENTO+(min(255,int(255*clamp01(ck*3)*pulso_c)),),anchor="ma")
    tarjetas=e["tarjetas"]; n=len(tarjetas)
    zx0,_,zx1,_=caja_segura()
    cols=2 if vertical else min(n, 3 if n <= 3 else 4)
    filas_=(n+cols-1)//cols
    y0=rotulo_y()+270 if vertical else rotulo_y()+210
    ALTO_TJ=196   # la tarjeta lleva el titulo en `dato` y el detalle en `secundario`:
                  # a 32/28 px el cuerpo no se leia en un movil
    fy = flota(t, e["from"] + 1.8, 4, 0.38)
    for i,(x,yb,cw,_) in enumerate(cuadricula(zx0,y0,zx1-zx0,filas_*(ALTO_TJ+24),cols,n)):
        tj=tarjetas[i]
        t_tj = escalonado(at, "tarjeta", i, e["from"]+0.6)
        k=entra(t, t_tj, "elemento")
        if k<=0: continue
        sub,ds=grupo()   # la tarjeta entera (borde, insignia, textos) entra junta
        yy=yb + fy
        tarjeta(ctx,sub,x,yy,cw,ALTO_TJ)
        if tj.get("alerta"):
            # el borde de alerta late: marca "ahora" sin inventar un gesto
            al_al = min(255, int(255 * latido(t, t_tj + 0.5, 1.5, 0.12)))
            ds.rounded_rectangle([x,yy,x+cw,yy+ALTO_TJ],radius=28,outline=ACENTO+(al_al,),width=4)
        ancho_txt=cw-(110 if tj.get("n") else 50)
        ds.text((x+30,yy+28),tj["titulo"],font=fuente_que_cabe(ctx.fX,tj["titulo"],ESCALA["dato"],ancho_txt,800),fill=BLANCO)
        # el detalle se PARTE (hasta 2 lineas) antes de encogerse: conserva el
        # tamaño de la escala y no se sale de la tarjeta (references/copy.md)
        _fdet,_ldet=texto_que_cabe(ctx.fX,tj["detalle"],ESCALA["secundario"],ancho_txt,400,max_lineas=2)
        for _li,_lt in enumerate(_ldet):
            ds.text((x+30,yy+82+_li*int(_fdet.size*1.25)),_lt,font=_fdet,fill=GRIS)
        if tj.get("n"):
            ds.ellipse([x+cw-90,yy+28,x+cw-30,yy+88],fill=ACENTO+(255,))
            ds.text((x+cw-60,yy+58),str(tj["n"]),font=ctx.fT(ESCALA["secundario"],800),fill=BLANCO,anchor="mm")
        fundir(layer,sub,k,dy=-50)
    return capa_salida(layer,t,e["to"])

def sc_recupera(ctx,e,t):
    """Pago recuperado: un cursor arrastra la barra; al completarse, tarjeta
    `hecho` (default "PAGADO") con el monto. Centrado en cualquier formato."""
    layer=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(layer)
    at=e["at"]
    kr=rotulo(ctx,layer,t,e.get("rotulo",""),at["rotulo"],y=rotulo_y())
    if kr<=0: return capa_salida(layer,t,e["to"])
    al=int(255*clamp01(kr*1.5)); sube=(1-min(1,kr))*ELEV
    zx0,_,zx1,_=caja_segura()
    bw=min(800,(zx1-zx0)-68); bx=(W-bw)/2; by=vy(0.5) if H>W else vy(0.46)   # -68: la perilla cabe
    d.text((W/2,(vy(0.26) if H>W else vy(0.25))+sube),e["resumen"],font=ctx.fX(ESCALA["dato"],600),
           fill=BLANCO+(al,),anchor="ma")
    # barra de progreso arrastrada por cursor
    rk=prog(t,at["cursor"],at["recupera"],smoothstep)   # una sola curva (antes ease sobre ease)
    d.rounded_rectangle([bx,by+sube,bx+bw,by+44+sube],radius=22,fill=(60,60,60,al))
    if rk>0:
        d.rounded_rectangle([bx,by,bx+max(44,bw*rk),by+44],radius=22,fill=ACENTO+(al,))
    r_perilla = 28
    cx = lerp(bx + r_perilla, bx + bw - r_perilla, rk)
    # perilla late al completar: vida en el hold sin pop nuevo
    r_draw = r_perilla * (latido(t, at["recupera"], 1.4, 0.08) if rk >= 0.98 else 1.0)
    d.ellipse([cx - r_draw, by + 22 - r_draw + sube, cx + r_draw, by + 22 + r_draw + sube],
              fill=BLANCO + (al,))
    yc=by+(H*0.12 if H>W else H*0.14)*vk()
    t_pag = at["pagado"]
    # cruce cliente→PAGADO: antes el texto desaparecía el mismo frame en que
    # saltaba la tarjeta (medido: 1 pop a t=pagado). Fundido cruzado 0.28 s.
    k_pag = entra(t, t_pag, "suave") if t >= t_pag else 0.0
    fade_cli = 1.0 - smoothstep(clamp01((t - (t_pag - 0.12)) / 0.28))
    if fade_cli > 0.02:
        al_cli = int(al * fade_cli)
        d.text((W/2,yc+90+sube),e["cliente"],font=ctx.fX(ESCALA["dato"],600),fill=GRIS+(al_cli,),anchor="ma")
        d.text((W/2,yc+140+sube),e.get("hace",""),font=ctx.fX(ESCALA["nota"],400),fill=GRIS+(al_cli,),anchor="ma")
    if k_pag > 0:
        al_pag = int(255 * min(1, k_pag))
        tarjeta(ctx,layer,bx,yc,bw,240,radio=30,alpha=al_pag)
        d.text((W/2,yc+52),e.get("hecho","PAGADO"),font=ctx.fT(64,800),
               fill=EXITO+(al_pag,),anchor="ma")   # éxito: pago hecho
        d.text((W/2,yc+142),e["monto"],font=ctx.fT(54,800),fill=BLANCO+(al_pag,),anchor="ma")
    return capa_salida(layer,t,e["to"])

def sc_remate(ctx,e,t):
    layer=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(layer)
    ats=e["at"]["palabras"]
    # palabras de las líneas
    words=[]
    for ln in e["lineas"]:
        # el markup * ~ ^ no cuenta como palabra (mismas reglas que titular)
        words+=[w for t_,_k in segmentos_resalte(ln) for w in t_.split(" ") if w]
    titular(ctx,layer,t,e["lineas"],ats,tam=ESCALA["titular"],cy=H*0.36+flota(t,ats[-1]+0.5,4,0.45))
    g=e["at"]["gigante"]
    k=entra(t, g, "pop")
    if k>0:
        sc=1.6-0.6*min(1,k)   # slam: aterriza sin estroboscopio (2.2x movía 100 px/frame)
        zx0,_,zx1,zy1=caja_segura()
        tam_g=fuente_que_cabe(ctx.fT,e["gigante"],300,(zx1-zx0)*0.94,800).size   # "1.000.000×" cabe
        # centro FIJO: donde asienta, sin pasar el borde seguro inferior (el
        # slam crece simétrico alrededor del centro; antes colgaba de arriba)
        bb0=ctx.fT(tam_g,800).getbbox(e["gigante"],anchor="mm"); hb=bb0[3]-bb0[1]
        yc=min(H*0.62+hb/2,zy1-hb*0.65)
        fnt=ctx.fT(int(tam_g*sc),800)
        bb=fnt.getbbox(e["gigante"],anchor="mm")
        a_g=smoothstep(clamp01((t-g)/0.25))
        resplandor(layer,(W/2+bb[0],yc+bb[1],W/2+bb[2],yc+bb[3]),ACENTO,30,
                   dibujar=lambda d_,ox,oy: d_.text((W/2-ox,yc-oy),e["gigante"],font=fnt,
                                                    fill=ACENTO+(int(110*a_g),),anchor="mm"))
        d.text((W/2,yc),e["gigante"],font=fnt,fill=BLANCO+(int(255*a_g),),anchor="mm")
        if e.get("subtexto_gigante") and k > 0:
            fnt_s = fuente_que_cabe(ctx.fX, e["subtexto_gigante"], 60, (zx1 - zx0) * 0.86, 500)
            d.text((W / 2, yc + hb / 2 + 70), e["subtexto_gigante"], font=fnt_s,
                   fill=BLANCO + (int(255 * a_g),), anchor="ma")
    return capa_salida(layer,t,e["to"])

def sc_final(ctx,e,t):
    """Lockup de cierre: entra con resorte y luego RESPIRA (flotación, pulso del
    botón, push-in lento) — un end card quieto es un frame congelado."""
    layer=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(layer)
    at=e["at"]
    k=entra(t, e["from"]+0.1, "lento")
    asienta=e["from"]+1.2
    fy=flota(t,asienta,5,0.32)
    push=1+0.035*prog(t,e["from"],e["to"],ease_in_out)   # push-in de cámara
    if k>0:
        if ctx.logo and es_marca_del_pack(e["marca"]):
            lw=int(760*min(1,k)*push)
            if lw > 0:
                lh=max(1,int(lw*ctx.logo.height/ctx.logo.width))
                lg=ctx.logo.resize((lw,lh),Image.LANCZOS)
                layer.alpha_composite(lg,(int(W/2-lw/2),int(vy(0.40)-lg.height/2+fy)))
        else:
            zx0,_,zx1,_=caja_segura()
            tam_m=fuente_que_cabe(ctx.fT,e["marca"],120,(zx1-zx0)*0.92/1.035,800).size   # con el push máximo: tamaño fijo, sin saltos
            fnt_m=ctx.fT(int(tam_m*min(1,k)*push),800)
            d.text((W/2,vy(0.40)+fy),e["marca"],font=fnt_m,
                   fill=BLANCO+(int(255*clamp01(k*1.4)),),anchor="mm")
    if e.get("lema") and t>=at["lema"]:
        rotulo(ctx,layer,t,e["lema"],at["lema"],y=vy(0.58)+fy*0.6,tam=52)
    if e.get("boton") and t>=at["boton"]:
        kb=entra(t, at["boton"], "bloque")
        bw,bh=520*min(1.0,kb),110*min(1.0,kb); yy=vy(0.70)+(110-bh)/2+fy*0.4
        if bh>4:
            boton_halo(d, W/2, yy+bh/2, bw, bh, e["boton"],
                       ctx.fX(ESCALA["dato"]*min(1.0,kb),800), t, at["boton"],
                       alpha=int(255*min(1,kb)))
    # sale como toda escena: puede no ser la última del plan (si le sigue otra,
    # sin salida desaparecía de golpe al terminar el solape)
    return capa_salida(layer,t,e["to"])


# ───────────────────────── ESCENAS DATA/UI (Catálogo unificado) ─────────────────────────
# Cada escena está compuesta por las primitivas DRY (barra_h, cuenta_up, arco,
# cuadricula, linewrap, particulas). Si necesitas una nueva variante, agrega
# una escena que llame a las primitivas — NO dupliques lógica de animación.
#
# Fuente de patrones: lifeprompt-team/remotion-scenes (201 escenas, MIT) —
# DataAnimations (bar/gauge/line/pie/progress/ranking/stats/timeline),
# ListAnimations (list/timeline), ThemeAnimations (versus, quote).
# Referencia cruzada: references/scene-patterns-from-internet.md

def sc_bars(ctx, e, t):
    """Barras verticales de comparación. Params: `titulo`, `fuente`,
    `barras[{etiqueta, valor, max, color?, acento?}]`, `at{rotulo, bar0..n, fuente}`.
    Cada barra sube con resorte desde su `at.barN`. Acento (color) marca la barra ganadora.
    """
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    at = e["at"]
    if e.get("titulo"):
        rotulo(ctx, layer, t, e["titulo"], at.get("rotulo", e["from"]), y=rotulo_y())
    # titulo solo se lee si el if de arriba pasa; defensivo en runtime por el guard
    barras = e.get("barras", [])
    n = len(barras)
    if n == 0:
        return capa_salida(layer, t, e["to"])  # sin datos, escena vacía
    zx0, zy0, zx1, zy1 = caja_segura()
    ancho_total = zx1 - zx0
    gap = 36
    bw = min(260, (ancho_total - gap * (n - 1)) // n)   # barras, no losas: grupo centrado
    zx0 = (W - (bw * n + gap * (n - 1))) / 2
    # si alguna etiqueta parte en dos lineas, las barras suben ese alto:
    # la segunda linea no puede caer sobre el pie de fuente
    alto_et = max((len(texto_que_cabe(ctx.fX, b.get("etiqueta", ""), ESCALA["nota"], bw, 600,
                                      max_lineas=2)[1]) for b in barras), default=1)
    base_y = zy1 - 130 - (alto_et - 1) * int(ESCALA["nota"] * 1.2)
    max_h = base_y - (rotulo_y() + 140)   # arriba: rótulo + cifra de la barra más alta
    for i, b in enumerate(barras):
        t_in = escalonado(at, "bar", i, e["from"] + 0.2)
        k = entra(t, t_in, "elemento")
        if k <= 0:
            continue
        fraccion = clamp01(b.get("valor", 0) / max(1e-9, b.get("max", 100)))
        col = b.get("color")
        if col is None:
            col = ACENTO if b.get("acento") else BLANCO
        # track (gris) + fill con color
        x0 = zx0 + i * (bw + gap)
        # pista, etiqueta y cifra entran fundidas (0.3 s), no de golpe
        ki = smoothstep(clamp01((t - t_in) / 0.45))
        col = tuple(col[:3]) + (int((col[3] if len(col) > 3 else 255) * ki),)
        d.rounded_rectangle([x0, base_y - max_h, x0 + bw, base_y], radius=18,
                            fill=(255, 255, 255, int(18 * ki)))
        # fill con animación
        # crece con smoothstep en 0.9 s: un dato no rebota por encima de su valor
        # (el resorte lo mostraba de más) y el borde no salta >60 px por frame
        g_ = rellena(t, t_in)
        fill_h = max_h * fraccion * g_
        if fill_h >= 1:   # el radio nunca supera la mitad del alto: nace de 0, no como píldora
            d.rounded_rectangle([x0, base_y - fill_h, x0 + bw, base_y], radius=min(18, fill_h / 2), fill=col)
        # etiqueta abajo: tamano FIJO de la escala, partida en dos lineas
        # antes de recortar. El recorte con "…" perdia copy ("Sistema
        # opera…") en la pieza entregada sin que ninguna puerta lo viera;
        # partir conserva el texto entero al mismo tamano legible.
        fnt, lineas_et = texto_que_cabe(ctx.fX, b.get("etiqueta", ""), ESCALA["nota"], bw, 600,
                                        max_lineas=2)
        for li, ln in enumerate(lineas_et):
            d.text((x0 + bw / 2, base_y + 22 + li * (fnt.size * 1.2)), ln,
                   font=fnt, fill=BLANCO + (int(255 * ki),), anchor="mt")
        # valor arriba de la barra (tamaño fijado por el valor final)
        val = cuenta_up(0, b.get("valor", 0), t, t_in, progreso=g_)   # la cifra dice lo que mide la barra
        # piso 26: una cifra que se encoge por debajo del piso ilegible no es
        # un dato, es ruido (y el QA rechaza la pieza)
        fnt_v = fuente_que_cabe(ctx.fT, cuenta_up(0, b.get("valor", 0), 1e9, 0), 64, bw, 800,
                                tabular=True, minimo=26)
        cifra(d, (x0 + bw / 2, base_y - fill_h - 16), val, fnt_v, col, anchor="mb")
    pie_fuente(ctx, d, e, t, at.get("rotulo", e["from"]) + 1.5)
    return capa_salida(layer, t, e["to"])


def sc_gauge(ctx, e, t):
    """Indicador circular (gauge) con cuenta animada al medio.
    Params: `titulo`, `valor`, `max`, `etiqueta`, `at{rotulo, gauge, valor, etiqueta}`.

    Dos formas del mismo indicador, UNA idea con dos formas: `forma: "anillo"` es
    el dial de marcas radiales (una MAGNITUD leida de un vistazo); sin `forma`
    es el arco de 270 grados (el de antes). El dispatcher va al principio para
    que las dos formas compartan la idea y no la codificacion.
    """
    if e.get("forma") == "anillo":
        return sc_gauge_anillo(ctx, e, t)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    at = e["at"]
    rotulo(ctx, layer, t, e.get("titulo", ""), at.get("rotulo", e["from"]), y=rotulo_y())
    # el arco cabe entre el rótulo y el borde seguro (en 16:9 tapaba el título)
    _, _, _, zy1 = caja_segura()
    arriba, abajo = rotulo_y() + 80, zy1 - 150          # abajo: etiqueta bajo el arco
    r = min(unidad() * 0.34, (abajo - arriba) / 1.707)  # 270°: arriba r, abajo r·sin45°
    cx, cy = W / 2, arriba + r
    grosor = 26
    t_in = at.get("gauge", e["from"] + 0.3)
    ka = smoothstep(clamp01((t - (t_in - 0.3)) / 0.4))   # la pista entra fundida
    arco(d, cx, cy, r, 135, 135 + 270, (255, 255, 255, int(32 * ka)), grosor)
    # el arco llena con smoothstep (sin rebote: un dato no se pasa de su valor)
    # y la cifra dice exactamente lo que marca el arco
    g_ = rellena(t, t_in)
    if g_ > 0:
        fraccion = clamp01(e.get("valor", 0) / max(1e-9, e.get("max", 100)))
        # caps redondeados: discos en los extremos del arco (ImageDraw.arc
        # usa butt caps; el disco cierra el look premium del gauge)
        ang_fin = 135 + 270 * fraccion * g_
        arco(d, cx, cy, r, 135, ang_fin, ACENTO, grosor)
        for ang in (135, ang_fin):
            rad = math.radians(ang)
            ex = cx + r * math.cos(rad)
            ey = cy + r * math.sin(rad)
            rr = grosor / 2
            d.ellipse([ex - rr, ey - rr, ex + rr, ey + rr], fill=ACENTO + (255,))
        # latido suave del arco asentado: mata muerto del hold
        if g_ > 0.98:
            pulso = latido(t, t_in + 1.1, 1.6, 0.06)
            rr = (grosor / 2) * pulso
            rad = math.radians(ang_fin)
            ex = cx + r * math.cos(rad)
            ey = cy + r * math.sin(rad)
            d.ellipse([ex - rr, ey - rr, ex + rr, ey + rr],
                      fill=ACENTO + (min(255, int(200 * pulso)),))
    val = cuenta_up(0, e.get("valor", 0), t, t_in, progreso=g_)
    fnt = fuente_que_cabe(ctx.fT, cuenta_up(0, e.get("valor", 0), 1e9, 0), unidad() * 0.18, r * 1.3,
                          800, tabular=True)
    cifra(d, (cx, cy - 8), val, fnt, BLANCO + (int(255 * ka),), anchor="mm",
          final=cuenta_up(0, e.get("valor", 0), 1e9, 0))
    t_et = at.get("etiqueta", t_in + 0.7)
    if "etiqueta" in e and t >= t_et:
        ke = smoothstep(clamp01((t - t_et) / 0.3))
        d.text((cx, cy + r * 0.707 + 40 + (1 - ke) * 16), e.get("etiqueta", ""), font=ctx.fX(ESCALA["dato"], 600),
               fill=GRIS + (int(255 * ke),), anchor="mt")
    # la fuente de la cifra, al pie de la zona segura: el gauge ES una cifra
    # y una cifra sin fuente a la vista es una cifra suelta (references/copy.md
    # §4). el linter acepta el campo `fuente` en cualquier escena, asi que
    # aqui tiene que dibujarse de verdad.
    if e.get("fuente"):
        pie_fuente(ctx, d, e, t, at.get("fuente", e["from"] + 2.0))
    return capa_salida(layer, t, e["to"])


def _tick_radial(d, cx, cy, r_in, r_out, ang, half_w, color):
    """Una marca radial del anillo: un trapecio fino orientado hacia fuera."""
    a = math.radians(ang)
    ca, sa = math.cos(a), math.sin(a)
    tx, ty = -sa, ca                      # la tangente
    x0, y0 = cx + ca * r_in, cy + sa * r_in
    x1, y1 = cx + ca * r_out, cy + sa * r_out
    d.polygon([(x0 + tx * half_w, y0 + ty * half_w),
               (x1 + tx * half_w, y1 + ty * half_w),
               (x1 - tx * half_w, y1 - ty * half_w),
               (x0 - tx * half_w, y0 - ty * half_w)], fill=color)


def sc_gauge_anillo(ctx, e, t):
    """El medidor de ANILLO: un anillo de marcas radiales que se llena.

    Es la forma "anillo" del gauge (la de arco es la de arriba): un anillo
    completo de N marcas finas, como el velocimetro de un coche o el dial de
    un panel de control. Sirve para lo que el arco no dice: una MAGNITUD
    (0 a 50, 0 a 100) leida de un vistazo, con la marca llena growsl y el
    numero dentro.

    Params: `valor`, `max`, `ticks` (marcas, 50), `etiqueta` (lo pequeno de
    encima: "aprendizaje"), `sufijo` (lo de al lado: "/50"), `color` (la marca
    llena; por defecto el acento del pack), `grosor`, `boton` (el boton oscuro
    debajo: "Editar"), `at{rotulo, gauge, valor, etiqueta}`.
    """
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    at = e["at"]
    valor = e.get("valor", 0)
    maxv = max(1e-9, e.get("max", 100))
    n = int(e.get("ticks", 50))
    color = e.get("color")
    col = tuple(color) + (255,) if isinstance(color, (list, tuple)) and len(color) == 3 else ACENTO

    # el dial vive en el centro de la zona segura: el objeto heroe.
    # `cy` es su altura en fraccion del alto (el copy va encima, en `y_frase`)
    cx, cy = W / 2, H * float(e.get("cy", 0.46))
    r = unidad() * float(e.get("radio", 0.28))
    r_in = r - unidad() * 0.045
    half_w = unidad() * 0.009

    t_in = at.get("gauge", e["from"] + 0.3)
    ka = smoothstep(clamp01((t - (t_in - 0.3)) / 0.4))
    g_ = rellena(t, t_in)
    # el valor ANIMA dentro de la escena: de `valor_desde` (el valor del beat
    # anterior) al valor de este. Sin esto el dial salta de 31 a 3 en el
    # corte y la puerta lo cuenta como 10 pops (medido).
    v0 = e.get("valor_desde", valor)
    dur_esc = max(0.4, float(e["to"]) - float(e["from"]))
    prog = smoothstep(clamp01((t - t_in) / dur_esc))
    valor_actual = v0 + (valor - v0) * prog
    fraccion = clamp01(valor_actual / maxv)
    llenas = int(round(fraccion * n * g_))

    # el anillo: las marcas vacias (oscuras) y las llenas (color)
    for i in range(n):
        ang = -90 + 360.0 * i / n
        if i < llenas:
            _tick_radial(d, cx, cy, r_in, r, ang, half_w, col)
        else:
            _tick_radial(d, cx, cy, r_in, r, ang, half_w, (38, 38, 42, int(255 * ka)))
    # el aro: el borde que cierra el dial
    d.ellipse([cx - r - half_w * 1.6, cy - r - half_w * 1.6,
               cx + r + half_w * 1.6, cy + r + half_w * 1.6],
              outline=(58, 58, 64, int(220 * ka)), width=max(2, int(half_w * 0.55)))

    # dentro: la etiqueta pequena, la cifra grande y el sufijo
    fnt_val = ctx.fT(unidad() * 0.115, 700)
    val = cuenta_up(v0, valor, t, t_in, dur=dur_esc, progreso=g_)
    texto_val = cuenta_up(0, valor, 1e9, 0)
    if e.get("sufijo"):
        fs = ctx.fT(unidad() * 0.042, 600)
        d.text((cx, cy - unidad() * 0.012), texto_val, font=fnt_val, fill=BLANCO + (255,), anchor="rm")
        d.text((cx + unidad() * 0.012, cy - unidad() * 0.004), str(e["sufijo"]), font=fs,
               fill=GRIS + (230,), anchor="lm")
    else:
        d.text((cx, cy - unidad() * 0.012), val, font=fnt_val, fill=BLANCO + (255,), anchor="mm")

    t_et = at.get("etiqueta", t_in + 0.5)
    if e.get("etiqueta") and t >= t_et - 0.3:
        ke = smoothstep(clamp01((t - t_et) / 0.35))
        d.text((cx, cy - unidad() * 0.085), str(e["etiqueta"]), font=ctx.fX(unidad() * 0.024, 500),
               fill=GRIS + (int(220 * ke),), anchor="mm")

    # el boton oscuro (la accion que la escena representa: "Editar")
    t_b = at.get("boton", t_in + 1.0)
    if e.get("boton") and t >= t_b - 0.3:
        kb = smoothstep(clamp01((t - t_b) / 0.35))
        fb = ctx.fX(unidad() * 0.030, 600)
        tw = ctx.tmp.textlength(str(e["boton"]), font=fb)
        bw, bh = tw + unidad() * 0.05, unidad() * 0.062
        bx, by = cx - bw / 2, cy + r * 0.30
        d.rounded_rectangle([bx, by, bx + bw, by + bh], radius=int(bh * 0.28),
                            fill=(30, 30, 34, int(235 * kb)))
        d.text((cx, by + bh / 2), str(e["boton"]), font=fb,
               fill=BLANCO + (int(255 * kb),), anchor="mm")
    # la frase encima del dial: el dial es el objeto y el copy es su lectura.
    # van en la MISMA escena a proposito: el motor compone una escena a la vez,
    # y si el copy fuera otra escena, en el corte el dial desaparecia.
    if e.get("frase"):
        # `y_frase` es la ALTURA de la ultima linea en fraccion del alto (la
        # misma medida que `cy`): el copy va encima del dial y no lo pisa.
        dibuja_frase(ctx, d, e, t, H * float(e.get("y_frase", 0.20)),
                     tam=e.get("tam_frase"))
    if e.get("fuente"):
        pie_fuente(ctx, d, e, t, at.get("fuente", e["from"] + 2.0))
    return capa_salida(layer, t, e["to"])


def sc_ranking(ctx, e, t):
    """Ranking horizontal: items con barra proporcional al valor, etiqueta a la izq,
    valor a la der. El #1 lleva acento. Params: `titulo`, `fuente`, `items[{etiqueta, valor, max}]`,
    `at{rotulo, item0..n, fuente}`. Etiqueta | barra | valor se miden para caber
    en la zona segura en cualquier formato.
    """
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    at = e["at"]
    rotulo(ctx, layer, t, e.get("titulo", ""), at.get("rotulo", e["from"]), y=rotulo_y())
    items = e.get("items", [])
    n = len(items)
    if n == 0:
        return capa_salida(layer, t, e["to"])
    zx0, _, zx1, zy1 = caja_segura()
    y0 = rotulo_y() + 90
    fila_h = min(160, (zy1 - 80 - y0) / n)
    # las filas se APILAN (`pila`): centradas en su hueco y, en 9:16, con el
    # sitio que sobra repartido entre ellas (antes, una banda al centro)
    centros_f, _ = pila([fila_h] * n, y0, zy1 - 80, gap=0)
    hi = fila_h * 0.6
    # los dos tamanos se calculan con la altura de la fila, pero con PISO: un
    # tamaño calculado puede caer por debajo del piso legible sin que el copy
    # lo controle (con muchas filas, la fila se encoge y la letra con ella)
    fnt = ctx.fX(int(max(ESCALA["nota"], min(52, fila_h * 0.36))), 700)
    fnt_v = ctx.fX(int(max(ESCALA["nota"], min(58, fila_h * 0.40))), 800)
    finales = [cuenta_up(0, it.get("valor", 0), 1e9, 0) for it in items]
    w_val = max(largo(v, fnt_v, True) for v in finales) + 24
    # la columna de la etiqueta se MIDE con las etiquetas (antes, un tope fijo
    # del 38 % cortaba "WhatsA…"): toma lo que pide la mas larga y deja a la
    # barra su minimo legible; la que aun no cabe se PARTE en dos lineas con
    # la misma letra (`texto_que_cabe`, como `bars`), nunca se recorta
    BARRA_MIN = int((zx1 - zx0) * 0.30)
    max_w_lab = int(zx1 - zx0 - w_val - 16 - BARRA_MIN)
    w_lab = min(max_w_lab, max(d.textlength(it.get("etiqueta", ""), font=fnt) for it in items) + 28)
    etiquetas = [texto_que_cabe(ctx.fX, it.get("etiqueta", ""), fnt.size, w_lab - 28, 700,
                                max_lineas=2, minimo=ESCALA["nota"]) for it in items]
    x_bar = zx0 + w_lab
    bw = max(100, zx1 - w_val - x_bar - 16)
    max_v = max((i.get("valor", 0) for i in items), default=1) or 1
    for i, it in enumerate(items):
        t_in = escalonado(at, "item", i, e["from"] + 0.2)
        k = entra(t, t_in, "elemento")
        if k <= 0:
            continue
        yi = centros_f[i] - hi / 2
        al = int(255 * clamp01(k * 1.4))
        fnt_l, lineas_l = etiquetas[i]
        paso_l = fnt_l.size * 1.1
        for li, ln in enumerate(lineas_l):
            d.text((zx0, yi + hi / 2 + (li - (len(lineas_l) - 1) / 2) * paso_l), ln,
                   font=fnt_l, fill=BLANCO + (al,), anchor="lm")
        fraccion = clamp01(it.get("valor", 0) / max_v)
        col = ACENTO if i == 0 else BLANCO
        g_ = rellena(t, t_in)   # sin rebote: un dato no se pasa de su valor
        barra_h(d, x_bar, yi, bw, hi, fraccion * g_, col + (int(230 * al / 255),),
                radio=hi // 2, pista=18 * al / 255, min_px=int(hi * 1.15))
        val = cuenta_up(0, it.get("valor", 0), t, t_in, progreso=g_)   # la cifra dice lo que mide la barra
        cifra(d, (zx1, yi + hi / 2), val, fnt_v, col + (al,), anchor="rm")
    pie_fuente(ctx, d, e, t, e["from"] + 2.0)
    return capa_salida(layer, t, e["to"])


def sc_stats(ctx, e, t):
    """Grid de stat cards: cada card muestra cifra grande + etiqueta.
    Params: `titulo`, `fuente`, `cards[{valor, etiqueta, acento?}]`, `at{rotulo, card0..n, fuente}`.
    """
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    at = e["at"]
    rotulo(ctx, layer, t, e.get("titulo", ""), at.get("rotulo", e["from"]), y=rotulo_y())
    cards = e.get("cards", [])
    n = len(cards)
    if n == 0:
        return capa_salida(layer, t, e["to"])  # sin datos, escena vacía
    x0, y0, x1, y1 = caja_segura()
    cols = columnas_grilla(n)
    filas_ = (n + cols - 1) // cols
    alto = min(y1 - 90 - (rotulo_y() + 80), filas_ * unidad() * 0.36)   # tarjetas, no paredes
    ancho = min(x1 - x0, cols * unidad() * 0.62)
    coords = cuadricula((W - ancho) / 2, rotulo_y() + 80, ancho, alto, cols, n,
                        alto_hueco=y1 - 90 - (rotulo_y() + 80))
    for i, (cx, cy, cw, ch) in enumerate(coords):
        t_in = escalonado(at, "card", i, e["from"] + 0.2)
        k = entra(t, t_in, "elemento")
        if k <= 0:
            continue
        c = cards[i]
        # card con resorte: escala 0.92 → 1.0 desde su centro + fundido (no aparece de golpe)
        s = lerp(0.92, 1.0, min(1.0, k))
        al = int(255 * clamp01(k * 1.4))
        tarjeta(ctx, layer, int(cx + cw * (1 - s) / 2), int(cy + ch * (1 - s) / 2),
                int(cw * s), int(ch * s), alpha=al)
        # cifra
        col = (ACENTO if c.get("acento") else BLANCO) + (al,)
        val = cuenta_up(0, c.get("valor", 0), t, t_in, progreso=rellena(t, t_in), fmt="{:,}")
        # tamaño fijado por la cifra FINAL (no salta mientras cuenta)
        fnt_v = fuente_que_cabe(ctx.fT, cuenta_up(0, c.get("valor", 0), 1e9, 0), ch * 0.42, cw * 0.84,
                                tabular=True)
        cifra(d, (cx + cw / 2, cy + ch * 0.42), val, fnt_v, col, anchor="mm")
        # etiqueta
        fnt_l = fuente_que_cabe(ctx.fX, c.get("etiqueta", ""), min(ch * 0.15, 52), cw * 0.86, 600)
        d.text((cx + cw / 2, cy + ch * 0.78), c.get("etiqueta", ""), font=fnt_l, fill=GRIS + (al,), anchor="mm")
    pie_fuente(ctx, d, e, t, e["from"] + 2.0)
    return capa_salida(layer, t, e["to"])


def sc_timeline(ctx, e, t):
    """Timeline con puntos que se encienden en su `at` sobre una línea que
    CRECE hasta cada punto. 16:9: horizontal; 9:16: vertical (etiquetas a la
    derecha, legibles). Params: `titulo`, `items[{etiqueta, fecha}]`, `at{rotulo, item0..n}`.
    """
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    at = e["at"]
    rotulo(ctx, layer, t, e.get("titulo", ""), at.get("rotulo", e["from"]), y=rotulo_y())
    items = e.get("items", [])
    n = len(items)
    if n == 0:
        return capa_salida(layer, t, e["to"])
    zx0, _, zx1, zy1 = caja_segura()
    vertical = H > W
    fnt = ctx.fX(ESCALA["dato"], 700)          # la escala es la misma en 9:16 y 16:9
    fnt_d = ctx.fX(ESCALA["nota"], 500)
    if vertical:
        max_tw = 0
        for it in items:
            for ln in linewrap(it.get("etiqueta", ""), fnt, zx1 - zx0 - 90):
                max_tw = max(max_tw, ctx.tmp.textlength(ln, font=fnt))
            if it.get("fecha"):
                max_tw = max(max_tw, ctx.tmp.textlength(it["fecha"], font=fnt_d))
        total_w = 18 + 50 + max_tw
        x_l = max(zx0 + 30, (W - total_w) / 2 + 18)
        a0, a1 = rotulo_y() + 110, zy1 - 100
        pos = [(x_l, a0 + (a1 - a0) * i / max(1, n - 1)) for i in range(n)]
    else:
        cy = H * 0.54
        w_tramo = min(zx1 - zx0 - 160, int(W * 0.70))
        a0, a1 = (W - w_tramo) / 2, (W + w_tramo) / 2
        pos = [(a0 + (a1 - a0) * i / max(1, n - 1), cy) for i in range(n)]
    HITO = 0.4   # un hito se lee (la línea llega a cada punto): es un beat, no una cascada
    t_ins = [at.get(f"item{i}", e["from"] + 0.2 + i * HITO) for i in range(n)]
    # la línea crece de punto en punto (llega a cada uno cuando se enciende)
    t_linea = t_ins[0] - 0.3
    tramo = 0.0
    for i in range(n - 1):
        tramo += prog(t, max(t_linea, t_ins[i] - 0.15), t_ins[i + 1])
    # el trazo vivo late en el hold (mata muerto residual tras el último hito)
    pulso_ln = latido(t, t_ins[-1] + 0.3, 1.6, 0.08) if t >= t_ins[-1] else 1.0
    if t >= t_linea:
        p0 = pos[0]
        if n > 1:
            iseg = min(n - 2, int(tramo))
            f = tramo - iseg if tramo < n - 1 else 1.0
            pa, pb = pos[iseg], pos[iseg + 1]
            p1 = (lerp(pa[0], pb[0], f), lerp(pa[1], pb[1], f))
        else:
            p1 = p0
        d.line([p0, pos[-1]], fill=(255, 255, 255, 40), width=4)
        d.line([p0, p1], fill=ACENTO + (min(255, int(230 * pulso_ln)),),
               width=max(4, int(6 * pulso_ln)))
    ancho_max = (zx1 - x_l - 50) if vertical else (a1 - a0) / max(1, n - 1) * 0.92
    # el último hito asentado late: el "ahora" del recorrido
    alcanzados = [i for i in range(n) if t >= t_ins[i] and entra(t, t_ins[i], "elemento") > 0.85]
    activo_i = alcanzados[-1] if alcanzados else -1
    for i, it in enumerate(items):
        k = entra(t, t_ins[i], "elemento")
        if k <= 0:
            continue
        x, y = pos[i]
        al = int(255 * clamp01(k * 1.4))
        pulso = latido(t, t_ins[i], 1.5, 0.10) if i == activo_i else 1.0
        radio = 18 * min(1.0, k) * (pulso if i == activo_i else 1.0)
        d.ellipse([x - radio, y - radio, x + radio, y + radio],
                  fill=ACENTO + (min(255, int(al * pulso)),))
        if radio > 6:   # el punto nace de radio 0: el centro blanco solo si cabe
            d.ellipse([x - radio + 5, y - radio + 5, x + radio - 5, y + radio - 5], fill=BLANCO + (al,))
        lineas = linewrap(it.get("etiqueta", ""), fnt, ancho_max)
        col_et = ACENTO + (al,) if i == activo_i else BLANCO + (al,)
        if vertical:
            for li, ln in enumerate(lineas):
                d.text((x + 50, y - 22 + li * 46), ln, font=fnt, fill=col_et, anchor="lm")
            if it.get("fecha"):
                d.text((x + 50, y + 22 + (len(lineas) - 1) * 46), it["fecha"], font=fnt_d,
                       fill=GRIS + (al,), anchor="lm")
        else:
            for li, ln in enumerate(lineas):
                d.text((x, y - 56 - (len(lineas) - 1 - li) * 44), ln, font=fnt,
                       fill=col_et, anchor="mm")
            if it.get("fecha"):
                d.text((x, y + 56), it["fecha"], font=fnt_d, fill=GRIS + (al,), anchor="mm")

    if e.get("fuente"):
        pie_fuente(ctx, d, e, t, at.get("fuente", e["from"] + 1.5))
    return capa_salida(layer, t, e["to"])


def sc_quote(ctx, e, t):
    """Testimonio / cita: la confianza antes que el movimiento.
    Params: `texto` (verbatim; la frase clave entre *asteriscos*, UNA), `autor`,
    `rol?`, `estrellas?` (puntaje real, admite 4.5), `estrellas_max?` (5),
    `fuente?`, `at{card, texto, enfasis, estrellas, autor, fuente}`.
    Las líneas entran en orden de lectura (0.22 s entre líneas); el énfasis
    llega DESPUÉS de que su línea asienta; las estrellas se llenan después de
    la cita; el autor firma al final y se queda quieto.
    """
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    at = e.get("at", {})
    t_card = at.get("card", e["from"])
    k = entra(t, t_card, "elemento")
    if k <= 0:
        return capa_salida(layer, t, e["to"])
    s = lerp(0.94, 1.0, k)
    U = unidad()
    zx0, zy0, zx1, zy1 = caja_segura()
    cw = min(zx1 - zx0, U * 1.35)
    cx = (W - cw) / 2
    # palabras con su marca de énfasis, envueltas con medida real
    fnt = ctx.fX(int(U * 0.055), 600)
    palabras = [(w_, em) for seg, em in segs(e.get("texto", "")) for w_ in seg.split()]
    esp = ctx.tmp.textlength(" ", font=fnt)
    lineas, ln, ancho = [], [], 0.0
    for w_, em in palabras:
        ww = ctx.tmp.textlength(w_, font=fnt)
        if ln and ancho + esp + ww > cw - 120:
            lineas.append(ln); ln, ancho = [], 0.0
        ln.append((w_, em, ww)); ancho += (esp if len(ln) > 1 else 0) + ww
    if ln:
        lineas.append(ln)
    n = len(lineas)
    lh = fnt.size * 1.25
    # el rol cabe DENTRO de la tarjeta: se parte en dos lineas como mucho
    # (antes salia en una linea centrada sin ajustar y se cortaba por los
    # dos lados de la tarjeta y del cuadro)
    fnt_rol, lineas_rol = (texto_que_cabe(ctx.fX, e["rol"], ESCALA["nota"], cw - 80, 500,
                                          max_lineas=2) if e.get("rol") else (None, []))
    # pila vertical medida: comilla · texto · estrellas · autor · rol (nunca se pisan)
    h_com, h_txt = U * 0.13, n * lh
    h_est = U * 0.075 if e.get("estrellas") is not None else 0
    h_aut = (U * 0.06 if e.get("autor") else 0) + (len(lineas_rol) * fnt_rol.size * 1.25
                                                  if lineas_rol else 0)
    ch = h_com + h_txt + h_est + h_aut + U * 0.10
    cy = max(zy0 + 70, (zy0 + zy1) / 2 - ch / 2 + 30)
    ac = int(255 * clamp01(k * 1.4))   # la tarjeta y su comilla entran fundidas, no de golpe
    tarjeta(ctx, layer, int(cx + (1 - s) * cw / 2), int(cy + (1 - s) * ch / 2),
            int(cw * s), int(ch * s), alpha=ac)
    d.text((cx + 40, cy + 20), "\u201C", font=ctx.fT(int(U * 0.22), 800), fill=ACENTO + (ac,), anchor="lt")
    t_texto = at.get("texto", t_card + 0.2)
    y_txt = cy + h_com + lh / 2
    for li, ln in enumerate(lineas):
        t_li = t_texto + li * 0.22
        kl = entra(t, t_li, "suave")
        if kl <= 0:
            continue
        al = int(255 * clamp01(kl * 1.4))
        y = y_txt + li * lh + (1 - min(1, kl)) * 14
        x = cx + cw / 2 - (sum(w_[2] for w_ in ln) + esp * (len(ln) - 1)) / 2
        t_em = at.get("enfasis", t_li + 0.35)
        ke = clamp01((t - t_em) / 0.35)
        for w_, em, ww in ln:
            if em and ke > 0:   # marcador que barre detrás de la frase clave
                d.rectangle([x - 4, y - fnt.size * 0.05, x + (ww + esp) * ease_out(ke),
                             y + fnt.size * 0.62],
                            fill=tuple(int(lerp(p_, a_, 0.35 * ke)) for p_, a_ in zip(PANEL, ACENTO)) + (255,))
            # la frase clave va en BLANCO sobre la banda de acento: en color
            # acento sobre la banda de acento el contraste era ilegible
            d.text((x, y), w_, font=fnt, fill=BLANCO + (al,), anchor="lm")
            x += ww + esp
    y_sig = y_txt + (n - 1) * lh + lh * 0.5
    t_fin = t_texto + n * 0.22 + 0.4
    if e.get("estrellas") is not None:
        t_es = at.get("estrellas", t_fin)
        if t >= t_es:
            estrellas(layer, cx + cw / 2, y_sig + h_est * 0.6, float(e["estrellas"]),
                      int(e.get("estrellas_max", 5)), tam=int(U * 0.043),
                      k=ease_out(clamp01((t - t_es) / 0.6)))
        t_fin = t_es + 0.7
    y_sig += h_est
    t_au = at.get("autor", t_fin)
    if e.get("autor") and t >= t_au:
        ka = entra(t, t_au, "suave")
        al = int(255 * clamp01(ka * 1.4)); dy = (1 - min(1, ka)) * 20
        d.text((cx + cw / 2, y_sig + U * 0.04 + dy), e["autor"],
               font=fuente_que_cabe(ctx.fX, e["autor"], ESCALA["dato"], cw - 80, 800),
               fill=BLANCO + (al,), anchor="mm")
        for li, ln in enumerate(lineas_rol):
            d.text((cx + cw / 2, y_sig + U * 0.075 + li * (fnt_rol.size * 1.25) + dy), ln,
                   font=fnt_rol, fill=GRIS + (al,), anchor="mt")
    if e.get("fuente") and t >= at.get("fuente", t_au + 0.2):
        pie_fuente(ctx, d, e, t, t_au + 0.2)
    return capa_salida(layer, t, e["to"])


def sc_versus(ctx, e, t):
    """Comparación lado a lado (versus). Params: `titulo`, `izquierda{etiqueta, items[]}`,
    `derecha{etiqueta, items[]}`, `at{rotulo, izq, der}`. Cada lado entra en su
    `at` (desliza desde su borde, items en cascada); los items de ambos lados
    comparten UN tamaño, el mayor con el que el más largo cabe en su columna.
    """
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    at = e["at"]
    fr = e["from"]
    rotulo(ctx, layer, t, e.get("titulo", ""), at.get("rotulo", fr), y=rotulo_y())
    x0, _, x1, y1 = caja_segura()
    col_w = (x1 - x0) / 2 - 40
    lados = ((e.get("izquierda", {}), x0 + col_w / 2, at.get("izq", fr + 0.4), BLANCO, -1),
             (e.get("derecha", {}), x1 - col_w / 2, at.get("der", fr + 0.9), ACENTO, 1))
    n = max(1, *(len(l[0].get("items", [])) for l in lados))
    y_label = H * 0.29
    y_items = H * 0.38
    fila_h = min(150, (y1 - 40 - y_items - (60 if e.get("fuente") else 0)) / n)
    todos = [it for l in lados for it in l[0].get("items", [])] or [""]
    largo = max(todos, key=lambda x: ctx.tmp.textlength(x, font=ctx.fX(40, 600)))
    fnt = fuente_que_cabe(ctx.fX, largo, min(56, fila_h * 0.42), col_w - 20, 600)
    fnt_h = fuente_que_cabe(ctx.fT, max((l[0].get("etiqueta", "") for l in lados), key=len),
                            int(min(W, H) * 0.055), col_w, 800)
    k_vs = entra(t, min(l[2] for l in lados), "bloque")
    if k_vs > 0:
        d.text((W / 2, y_label), "vs", font=ctx.fT(int(min(W, H) * 0.05), 800),
               fill=GRIS + (int(255 * clamp01(k_vs * 1.3)),), anchor="mm")
        d.line([W / 2, y_items, W / 2, y_items + n * fila_h], fill=(255, 255, 255, int(40 * min(1, k_vs))),
               width=2)
    for lado, cx, t_in, col, signo in lados:
        k = entra(t, t_in, "bloque")
        if k <= 0:
            continue
        dx = signo * 60 * (1 - min(1, k))
        al = int(255 * clamp01(k * 1.3))
        d.text((cx + dx, y_label), lado.get("etiqueta", ""), font=fnt_h, fill=col + (al,), anchor="mm")
        for i, it in enumerate(lado.get("items", [])):
            ki = entra(t, escalonado({}, "item", i, t_in + 0.15), "bloque")
            if ki <= 0:
                continue
            yi = y_items + i * fila_h + fila_h / 2 + (1 - min(1, ki)) * 24
            d.text((cx, yi), it, font=fnt, fill=BLANCO + (int(255 * clamp01(ki * 1.3)),), anchor="mm")

    if e.get("fuente"):
        pie_fuente(ctx, d, e, t, at.get("fuente", e["from"] + 2.0))
    return capa_salida(layer, t, e["to"])


def sc_confetti(ctx, e, t):
    """Celebración con confeti cayendo + texto opcional. Params: `texto`, `subtexto`,
    `at{particulas, texto}`. Útil para cierres de logro.
    """
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    at = e["at"]
    t_p = at.get("particulas", e["from"])
    t_t = at.get("texto", t_p + 0.3)
    # confeti con semilla determinista (estable si el usuario no cambia la fecha)
    semilla = at.get("timestamp_seed", 11)
    if t >= t_p:
        # lluvia CONTINUA: las partículas reciclan al salir (antes, a mitad de
        # escena ya habían caído todas → confetti vacío / dens disparada al
        # inicio y muerto después). Mezcla acento + blanco; círculos y
        # rectángulos para que no se lea como “lluvia de puntos”.
        dt = t - t_p
        ciclo = 2.6
        for i in range(110):
            rng_i = random.Random(semilla * 31 + i)
            fase = (dt * rng_i.uniform(0.75, 1.25) + rng_i.uniform(0, ciclo)) % ciclo
            x = rng_i.uniform(W * 0.06, W * 0.94) + math.sin(fase * 3.1 + i) * 18
            y = -30 + (H + 80) * (fase / ciclo)
            if y > H + 40:
                continue
            s = rng_i.uniform(5, 12)
            c = ACENTO if i % 3 else BLANCO
            al = rng_i.randint(170, 240)
            if i % 4 == 0:
                d.rectangle([x - s, y - s * 0.4, x + s, y + s * 0.4],
                            fill=(c[0], c[1], c[2], al))
            else:
                d.ellipse([x - s, y - s, x + s, y + s],
                          fill=(c[0], c[1], c[2], al))
    if "texto" in e and t >= t_t:
        k = entra(t, t_t, "elemento")
        if k > 0:
            x0, _, x1, _ = caja_segura()
            fnt = fuente_que_cabe(ctx.fT, e.get("texto", ""), unidad() * 0.10, x1 - x0, 800)
            d.text((W / 2, H * 0.42), e.get("texto", ""), font=fnt,
                   fill=BLANCO + (int(255 * clamp01(k * 1.3)),), anchor="mm")
    if "subtexto" in e and t >= at.get("subtexto", t_t + 0.4):
        x0, _, x1, _ = caja_segura()
        fnt_s = fuente_que_cabe(ctx.fX, e.get("subtexto", ""), unidad() * 0.045, x1 - x0, 600)
        ks = entra(t, at.get("subtexto", t_t + 0.4), "bloque")
        d.text((W / 2, H * 0.42 + unidad() * 0.11 + (1 - min(1, ks)) * 16), e.get("subtexto", ""),
               font=fnt_s, fill=GRIS + (int(255 * clamp01(ks * 1.4)),), anchor="mm")
    return capa_salida(layer, t, e["to"])


# ───────────────────────── ESCENAS TIPO/EFECTO (Ronda 2) ─────────────────────────
# Patrones validados de reactvideoeditor/remotion-templates (81 templates, MIT).
# Cada escena nueva se compone con las primitivas DRY — sin duplicar logica.

def sc_typewriter(ctx, e, t):
    """Texto que se escribe carácter a carácter con cursor. Envuelve en líneas
    dentro de la zona segura (letra en unidad(): se lee en 9:16 y 16:9); el
    cursor acompaña la escritura (fijo mientras escribe, parpadea al terminar).
    Params: `texto`, `tam?`, `cps?` (caracteres por segundo, default 12.5),
    `at{rotulo, cursor, fuente}`.
    Fuente: `typewriter-subtitle.tsx` (reactvideoeditor/remotion-templates).
    """
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    at = e["at"]
    texto = e.get("texto", "")
    if not texto:
        return capa_salida(layer, t, e["to"])
    t_in = at.get("rotulo", e["from"])
    zx0, zy0, zx1, zy1 = caja_segura()
    ancho = zx1 - zx0 - 80
    tam = int(e.get("tam", unidad() * 0.075))
    fnt = ctx.fT(tam, 800)
    lineas = linewrap(texto, fnt, ancho)
    while len(lineas) > 4 and tam > 40:   # demasiado largo: encoger antes que salirse
        tam -= 4
        fnt = ctx.fT(tam, 800)
        lineas = linewrap(texto, fnt, ancho)
    lh = tam * 1.32
    alto = lh * len(lineas)
    y0 = H * 0.45 - alto / 2 + flota(t, t_in + 0.8, 5, 0.35)
    # panel de lectura: aire interior generoso (antes el copy rozaba el borde
    # inferior/izquierdo del panel: se leía apretado)
    pad_panel = max(28, int(tam * 0.55))
    kp = smoothstep(clamp01((t - (t_in - 0.3)) / 0.4))
    if kp > 0:
        d.rounded_rectangle([zx0, y0 - pad_panel, zx1, y0 + alto + pad_panel * 0.7],
                            radius=28, fill=PANEL + (int(180 * kp),))
    paso = 1 / float(e.get("cps", 12.5))
    t_lin, cur = t_in, None
    for li, ln in enumerate(lineas):
        y = y0 + li * lh
        x = zx0 + pad_panel
        n = text_reveal(d, ln, fnt, x, y, t, t_lin, paso * len(ln), BLANCO)
        if n:
            cur = (x + d.textlength(ln[:n], font=fnt), y, n == len(ln))
        t_lin += paso * (len(ln) + 1)   # el salto de línea cuenta como una pulsación
    # cursor: acompaña la escritura; parpadea solo al terminar
    if cur and t >= at.get("cursor", t_in):
        termino = t >= t_lin
        if not termino or math.sin(t * 8) > 0:
            d.rectangle([cur[0] + 6, cur[1] - 2, cur[0] + 6 + max(4, tam * 0.07), cur[1] + tam * 1.05],
                        fill=ACENTO)
    pie_fuente(ctx, d, e, t, e["from"] + 2.5)
    return capa_salida(layer, t, e["to"])


# El AZUL DE LA SELECCION: el recuadro que marca una palabra. No viene del
# pack (no es identidad de marca: es una convencion de lectura, como el
# subrayado o la flecha) y por eso vive aqui y no en el pack.
AZUL_SELECCION=(43,127,255)


def _frase_layout(ctx, e, tam, visibles=None, max_lineas=None):
    """(palabras, lineas, linea_de, ancho_de, gap, lh) de una frase cinetica.

    El flujo de palabras y su salto de linea se calculan UNA vez y los usan
    las escenas que la dibujan (la frase suelta y el dial que lleva la frase
    encima): dos copias de este calculo serian dos copias que se desvanecan.
    """
    zx0, _zy0, zx1, _zy1 = caja_segura()
    maxw = zx1 - zx0 - 40
    fnt = ctx.fX(tam, 500)
    fnt_b = ctx.fX(tam, 800)     # la palabra clave va en negrita: es MAS ANCHA
    # el hueco entre palabras: el ancho del espacio tipográfico + un aire
    # mínimo. Antes era tam*0.24 (~15 px extra a 64): el bloque se leía
    # disperso y con tracking irregular (medido en muestra: gaps visuales
    # de 80–100 px entre palabras cortas). 0.06 deja respirar sin romper
    # la frase en islas.
    gap = ctx.tmp.textlength(" ", font=fnt) + tam * 0.06
    palabras = (e.get("frase") or e.get("texto") or "").split()
    if visibles is not None:
        palabras = [palabras[i] for i in visibles]
    clave = (e.get("clave") or "").strip().lower()

    def _ancho_de(w_):
        """El ancho REAL de la palabra, con la fuente con la que se dibuja.

        Medir todas las palabras con la misma fuente y dibujar la clave con
        otra es como se sale una linea del ancho: el texto se sale de la zona
        segura y el centrado sale mal (medido: la palabra clave en negrita
        empujaba la linea 40 px fuera).
        """
        es_clave = ("*" in w_) or (bool(clave) and
                                  w_.replace("*", "").strip(",.;:!?\u00bf\u00a1\"'").lower() == clave)
        return ctx.tmp.textlength(w_.replace("*", ""), font=(fnt_b if es_clave else fnt))

    lineas, cur, x = [], [], 0.0
    for i, w_ in enumerate(palabras):
        ww = _ancho_de(w_)
        if cur and x + ww > maxw:
            lineas.append(cur); cur = []; x = 0.0
        cur.append((i, x, ww)); x += ww + gap
    if cur:
        lineas.append(cur)
    if max_lineas is not None and len(lineas) > max_lineas:
        # lo que no cabe NO se dibuja: se acorta el COPY, no se achica la letra
        lineas = lineas[:max_lineas]
        linea_de, ancho_de = {}, {}
        for li, ln in enumerate(lineas):
            total = sum(w for _, _, w in ln) + gap * max(0, len(ln) - 1)
            ancho_de[li] = total
            for i, x, _ in ln:
                linea_de[i] = li
        return palabras, lineas, linea_de, ancho_de, gap, maxw
    linea_de, ancho_de = {}, {}
    for li, ln in enumerate(lineas):
        total = sum(w for _, _, w in ln) + gap * max(0, len(ln) - 1)
        ancho_de[li] = total
        for i, x, _ in ln:
            linea_de[i] = li
    return palabras, lineas, linea_de, ancho_de, gap, maxw


def y_de_pantalla(e, t, y_destino):
    """Traduce una Y de PANTALLA (la zona segura) a la capa de la escena.

    La camara escala la capa entera alrededor de su ancla, asi que un copy
    dibujado en coordenadas de capa se va de la zona segura cuando la camara
    se acerca. El copy que debe quedarse QUIETO (la frase) se compensa con la
    inversa de la transformacion.

    Es lo que hace el reel de referencia: el dial se acerca y se aleja, y la
    frase se queda clavada en su sitio. Sin esta compensacion, un zoom fuerte
    saca el texto del cuadro (medido: con la camara a 1,85 la linea de la
    frase caia 10 px por encima del borde superior).
    """
    fr, dy, dx = respiracion(e, t)
    if abs(fr - 1.0) < 1e-6:
        return y_destino
    cx, cy = W / 2, CENTRO_Y * H
    return cy + (y_destino - cy - dy) / fr


def dibuja_frase(ctx, d, e, t, y_ancla, tam=None):
    """Dibuja la frase cinetica: el copy entra PALABRA a PALABRA y el bloque
    sube para que la ultima palabra quede siempre en la misma zona.

    La palabra marcada con `*` (o la que dice `clave`) va en blanco y en
    negrita sobre el gris del resto; `seleccion` le pone encima el recuadro
    azul, como si alguien la hubiera marcado. Lo que ya se ha dicho se
    desvanece: solo se ven las ultimas `ventana` palabras.

    Devuelve el numero de palabras escritas (0 si todavia no hay ninguna).
    """
    at = e.get("at") or {}
    texto = e.get("frase") or e.get("texto") or ""
    if not texto:
        return 0
    t_in = at.get("rotulo", e.get("from", 0.0))
    tam_pantalla = int(tam or e.get("tam", unidad() * 0.055))
    # el copy se queda del MISMO TAMANO en pantalla: la camara escala la
    # capa, asi que el tamano en la capa se divide por el factor de camara.
    # (si no, el texto crecia y menguaba con el zoom, y las lineas se
    # rozaban: un texto pisa a otro)
    fr_cam, _dy_cam, _dx_cam = respiracion(e, t)
    tam = max(18, int(round(tam_pantalla / max(0.2, fr_cam))))
    # el AUTO-FIT: la frase se encoge hasta que cabe en la zona segura (en
    # ANCHO y en ALTO). Sin esto, un copy largo se sale del cuadro y la
    # escena entera baja al piso de la zona segura (medido: x0.72 con el
    # copy x2, y con la banda de subtitulos todavia menos).
    zx0, zy0, zx1, zy1 = caja_segura()
    ancho_max = (zx1 - zx0) - 40
    # el bloque crece hacia ARRIBA desde el ancla: el sitio que tiene es el
    # de ARRIBA del ancla, no toda la zona segura (si no, con el copy x2 el
    # bloque se sale por arriba y la escena baja al piso de la zona)
    # la posicion la da vy(): remapea la fraccion de H a la caja segura
    # ACTUAL (con la banda de subtitulos, la caja se comprime y la frase
    # sube en vez de que la red la encoja entera)
    y_frase = vy(float(e.get("y", 0.20)))
    alto_max = max(60.0, y_frase - zy0)
    palabras_txt = (e.get("frase") or e.get("texto") or "").split()
    # el piso es el de LEGIBILIDAD (26 px), no un piso de "no microscopico":
    # una letra por debajo de 26 no se lee en un telefono (medido: con el copy
    # x2 el auto-fit bajaba la frase a 13 px y la puerta lo rechazaba). Si
    # con 26 px el copy no cabe, se ACORTA EL COPY (lo que no cabe, no se
    # dibuja), no se achica la letra: references/copy.md.
    max_lineas = 99
    # el piso es el de la TINTA (26 px), no el del cuerpo: la letra que se
    # mide es la caja real del texto, y a 26 px de cuerpo la tinta mide ~19
    # (medido: la puerta rechazaba 22 px con el copy x2)
    piso_fuente = int(MIN_LETRA * 1.45)
    while tam > piso_fuente:
        _f = (ctx.fTi if (e.get("itálica") or e.get("italica")) else ctx.fX)(tam, 500)
        _lineas = linewrap(" ".join(palabras_txt), _f, ancho_max, ctx.tmp)
        if (len(_lineas) * tam * 1.52) <= alto_max:
            max_lineas = len(_lineas)
            break
        tam = max(piso_fuente, int(tam * 0.92))
    else:
        # con la letra en su MINIMO todavia no cabe: se acorta el copy
        _f = (ctx.fTi if (e.get("itálica") or e.get("italica")) else ctx.fX)(tam, 500)
        _lineas = linewrap(" ".join(palabras_txt), _f, ancho_max, ctx.tmp)
        max_lineas = max(1, int(alto_max // max(1, tam * 1.52)))
    # la ITALICA del display (el reel de referencia escribe en itálica): si la
    # escena la pide y el pack la trae, se usa; si no, la redonda.
    fab = ctx.fTi if (e.get("itálica") or e.get("italica")) else ctx.fX
    fnt = fab(tam, 500)         # la frase es texto courant, no titular
    fnt_b = fab(tam, 800)        # la palabra clave, en negrita
    clave = (e.get("clave") or "").strip().lower()
    seleccion = (e.get("seleccion") or "").strip().lower()

    def _limpia(w_):
        return w_.replace("*", "").replace("~", "").replace("^", "")

    def _caja_de(w_):
        """El tipo de resalte de una palabra: "roja", "blanca" o None.

        El markup: `~palabra~` la pone en una CAJA ROJA (texto blanco) y
        `^palabra^` en una CAJA BLANCA (texto oscuro). Es el sistema del reel
        de referencia: la palabra que sostiene el dato va dentro de un
        bloque de color, y el resto es texto.
        """
        if "~" in w_:
            return "roja"
        if "^" in w_:
            return "blanca"
        return None

    def _marca(w_):
        """(es_clave, es_seleccion) de una palabra."""
        ws = _limpia(w_).strip(",.;:!?\u00bf\u00a1\"'").lower()
        return ("*" in w_) or (bool(clave) and ws == clave), (bool(seleccion) and ws == seleccion)

    cps = float(e.get("cps", 1.6))
    ventana = int(e.get("ventana", 5))
    todas = (e.get("frase") or e.get("texto") or "").split()
    k = min(len(todas), int(max(0.0, t - t_in) * cps) + 1)
    if k <= 0:
        return 0
    primero = max(0, k - ventana)
    # el layout es de las palabras VISIBLES: el bloque se recompone en cada
    # palabra nueva y sale centrado. Con el layout de la frase ENTERA, una
    # linea casi vacia se centraba como si estuviera llena y se salia del
    # cuadro por la izquierda (medido: 160 px fuera).
    #
    # Y el bloque NO se mueve de golpe: cuando la recomposicion cambia el
    # sitio de una palabra, esa palabra se funde de su sitio viejo al nuevo.
    # Si se moviera de golpe, el medidor lo contaria como un pop (un bloque de
    # 10x10 px que cambia de golpe: medido, 10 pops, todos en el instante de
    # anadir palabra).
    dur_fusion = 0.22
    # el layout es FIJO (la frase entera): el bloque NO se recompone al anadir
    # palabra. Es lo que hace el reel de referencia: las palabras aparecen en
    # su sitio y las viejas se apagan; el bloque no se mueve (medido: si se
    # recompone, el bloque salta de sitio y el medidor lo cuenta como un pop:
    # 10 pops, todos en el instante de anadir palabra).
    palabras, lineas, linea_de, ancho_de, gap, maxw = _frase_layout(
        ctx, e, tam, max_lineas=max_lineas)
    # el interlineado se compensa con la camara: si no, el copy crecia y
    # menguaba con el zoom (la camara escala la capa entera).
    lh = tam * 1.52      # en la capa: con la camara, sale a 1,52 en pantalla
    linea_ancla = max(linea_de.values()) if linea_de else 0
    zx0, _zy0, _zx1, _zy1 = caja_segura()
    y_ancla = y_de_pantalla(e, t, y_ancla)
    # respiración del bloque (3 px): sin ella el hold entre palabras se lee
    # muerto (medido: frase 81/100, muerto 0,75). Misma `flota` que final/hero.
    y_ancla = y_ancla + flota(t, t_in + 0.4, 3.0, 0.45)
    # el instante en que entra la palabra nueva: la fusion va de alli
    t_palabra = t_in + max(0, k - 1) / max(0.01, cps)
    m_fusion = smoothstep(clamp01((t - t_palabra) / dur_fusion))

    def _sitio(layout_lineas, layout_linea_de, layout_ancho, idx):
        li = layout_linea_de.get(idx)
        if li is None:
            return None
        pos = [p for p in layout_lineas[li] if p[0] == idx]
        if not pos:
            return None
        ultimo = max(layout_linea_de.values()) if layout_linea_de else 0
        return (zx0 + (maxw - layout_ancho.get(li, 0)) / 2.0 + pos[0][1],
                y_ancla + (li - ultimo) * lh)

    # EL ESTADO DE CADA PALABRA (teleprompter legible, no nube dispersa):
    #   · la que aun NO se ha alcanzado: se ve en GRIS tenue, MISMO tamaño
    #     (encogerla a 0,66 rompía la baseline y abría huecos feos)
    #   · la alcanzada: BLANCA; dentro de la ventana no baja del piso de
    #     contraste (0,45): un fade a negro sobre fondo negro es ilegible
    #   · la ACTIVA: blanca + SUBRAYADO de acento con latido (mata muerto)
    #   · la clave (*…*): no se apaga: es el mensaje
    #
    # El CRECIMIENTO de la activa: si apareciese de golpe, el medidor lo
    # cuenta como un pop (un bloque de 10x10 px que cambia de golpe).
    dur_crece = 0.34
    for i in range(len(palabras)):
        w_ = palabras[i]
        texto_w = _limpia(w_)
        es_clave, es_sel = _marca(w_)
        tipo_caja = _caja_de(w_)
        alcanzada = i < k
        activa = (i == k - 1)
        edad = k - 1 - i
        if not alcanzada:
            fade = 0.30                 # pista del copy por delante, no protagonista
        elif edad == 0:
            fade = 1.0
        else:
            # dentro de la ventana: piso 0,45 (legible); fuera: se apaga
            crudo = max(0.0, 1.0 - (edad - 1) / float(max(1, ventana)))
            fade = max(0.45, crudo) if edad < ventana else crudo
        if es_clave:
            fade = max(fade, 0.92)       # la clave no se apaga: es el mensaje
        if activa:
            fade *= smoothstep(clamp01((t - t_palabra) / 0.22))
        sitio = _sitio(lineas, linea_de, ancho_de, i)
        if sitio is None:
            continue
        x, y = sitio
        # solo la ACTIVA crece (0,82 -> 1,0): menos jerk que 0,66->1 y sin
        # encoger el resto de la frase (baseline estable)
        escala_p = 1.0
        if activa:
            escala_p = 0.82 + 0.18 * smoothstep(clamp01((t - t_palabra) / dur_crece))
        # jerarquía: clave/caja/activa en blanco; el resto alcanzado en gris
        # legible; lo por delante, gris tenue (teleprompter, no nube blanca)
        if tipo_caja == "blanca":
            col = NEGRO
        elif es_clave or tipo_caja == "roja" or activa:
            col = BLANCO
        elif alcanzada:
            col = (200, 200, 200)       # gris claro: se lee, no compite con la clave
        else:
            col = GRIS
            fade = max(fade, 0.36)      # pista visible (a>80) sin robar foco
        tam_p = max(10, int(round(tam * escala_p)))
        f = fab(tam_p, 800) if (es_clave or tipo_caja) else fab(tam_p, 500)
        al = int(255 * fade)
        if al <= 2:
            continue
        if tipo_caja:
            # la CAJA DE RESALTE, detras del texto: roja con texto blanco o
            # blanca con texto oscuro (medido: 8-12 px de radio, el relleno
            # toca la ascender y deja ~14 px de aire bajo la linea base)
            ww = ctx.tmp.textlength(texto_w, font=f)
            pad_x, pad_y = tam_p * 0.16, tam_p * 0.16
            caja = [x - pad_x, y - pad_y * 0.55, x + ww + pad_x, y + tam_p * 1.02]
            relleno = ACENTO if tipo_caja == "roja" else BLANCO
            d.rounded_rectangle(caja, radius=int(tam_p * 0.12),
                                fill=relleno + (al,))
        d.text((x, y), texto_w, font=f, fill=col + (al,), anchor="la")
        if es_sel:
            ww = ctx.tmp.textlength(texto_w, font=f)
            d.rounded_rectangle([x - tam * 0.12, y - tam * 0.10, x + ww + tam * 0.12,
                                 y + tam * 1.02], radius=int(tam * 0.16),
                                outline=AZUL_SELECCION + (min(255, al + 40),),
                                width=max(2, int(tam * 0.035)))
        if activa and not tipo_caja:
            # el SUBRAYADO de acento de la palabra activa + latido: sin el
            # latido, tras asentar cada palabra el hold quedaba muerto
            # (medido: frase 81/100, muerto 0,75)
            ww = ctx.tmp.textlength(texto_w, font=f)
            grosor = max(4, int(tam_p * 0.075 * latido(t, t_palabra, 1.35, 0.14)))
            al_line = min(255, int(al * latido(t, t_palabra, 1.35, 0.10)))
            d.rectangle([x, y + tam_p * 1.02, x + ww, y + tam_p * 1.02 + grosor],
                        fill=ACENTO + (al_line,))
    return k


def sc_frase(ctx, e, t):
    """Frase cinetica: el copy entra PALABRA a PALABRA y el bloque sube para
    que la ultima palabra quede siempre en la misma zona (teleprompter).

    Es la escena del copy que se LEE, no el titular que golpea: no sale de
    golpe, se escribe. La palabra marcada con `*` (o la que dice `clave`) va
    en blanco y en negrita sobre el gris del resto; `seleccion` le pone
    encima el recuadro azul, como si alguien la hubiera marcado. Lo que ya se
    ha dicho se desvanece: solo se ven las ultimas `ventana` palabras.

    Params: `frase` (el texto; `*palabra*` marca la clave), `clave` (alternativa
    a los asteriscos), `seleccion` (la palabra con recuadro), `cps` (palabras
    por segundo, 1.6), `tam`, `y` (donde queda la ultima palabra), `ventana`
    (palabras visibles, 5), `at{rotulo}`.
    """
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    dibuja_frase(ctx, d, e, t, vy(float(e.get("y", 0.20))))
    pie_fuente(ctx, d, e, t, e["from"] + 2.5)
    return capa_salida(layer, t, e["to"])


def _encaja_una_linea(fabrica, texto, tam, ancho_max, peso=800, minimo=26):
    """(fuente, texto) en UNA linea que cabe en `ancho_max`.

    Primero se ENCOGE la letra (hasta el piso de letra legible, 26 px: por
    debajo no se lee en un movil) y, si aun asi no cabe, se ACORTA EL COPY
    (por palabras y, como ultima medida, a media palabra). La regla de
    references/copy.md: la letra no baja del piso; lo que se acorta es el
    copy, y queda anotado en RECORTES.

    Sin esto, un texto largo se sale de su hueco y PISA al de al lado: la
    puerta lo mide ("ningun texto pisa a otro") y lo rechaza.
    """
    texto = str(texto)
    f = fuente_que_cabe(fabrica, texto, tam, ancho_max, peso, minimo=minimo)
    if largo(texto, f) <= ancho_max:
        return f, texto
    RECORTES.append(dict(texto=texto, ancho_max=int(ancho_max)))
    palabras = texto.split()
    while len(palabras) > 1:
        palabras = palabras[:-1]
        t = " ".join(palabras) + "…"
        if largo(t, f) <= ancho_max:
            return f, t
    t = ""
    for ch in texto:
        if largo(t + ch + "…", f) > ancho_max:
            break
        t += ch
    return f, (t + "…" if t else texto)


def _lineas_de_casilla(texto, fnt, ancho, max_lineas=2):
    """Las lineas del texto de una casilla.

    La letra NO se encoge: el piso de letra legible es del QA (26 px) y el rol
    `secundario` esta en 32. Si el copy no cabe en `max_lineas` lo que se
    acorta es el COPY, no la letra (references/copy.md). Lo que se acorta
    queda anotado en RECORTES: un copy que pierde palabras sin aviso es un
    defecto que no se ve hasta que alguien lee la pieza.
    """
    lineas = linewrap(texto, fnt, ancho)
    if len(lineas) > max_lineas:
        RECORTES.append(dict(texto=texto, ancho_max=int(ancho)))
        palabras = texto.split()
        while len(palabras) > 1:
            palabras = palabras[:-1]
            lineas = linewrap(" ".join(palabras), fnt, ancho)
            if len(lineas) <= max_lineas:
                break
    # una palabra suelta mas ANCHA que la casilla no se parte (el word-wrap
    # no parte palabras): se recorta con puntos, o se sale de la caja
    salida = []
    for ln in lineas[:max_lineas]:
        if largo(ln, fnt) > ancho:
            ln = recorta_para(ln, fnt, ancho)
        salida.append(ln)
    return salida


def sc_constancia(ctx, e, t):
    """El acta de la pieza: N casillas, cada una con su marca (✓ lo que ya esta
    confirmado, ○ lo que queda pendiente) y su texto en versalitas.

    Es la escena del reel de "cara" (De8KNkdDT68): un panel con el guion de
    arriba y, dentro, las casillas de lo que cada parte confirma.

    MEDIDO sobre ese reel (1080x1920, leyendo los pixeles):
      · el panel va de x=60 a x=1019 (960 de ancho) con el borde a 1 px;
      · la raya del kicker mide 40x6 px y el kicker va en monoespaciada;
      · las casillas miden 425 px con 37 de separacion;
      · el circulo lleno mide 64 px de diametro y lleva el ✓ DENTRO, en negro
        sobre blanco; el vacio es solo un aro, sin relleno;
      · la casilla confirmada tiene el borde BLANCO y el texto en blanco; la
        pendiente, el borde gris y el texto en gris.
    El ✓ se DIBUJA (no es el glifo: "✓" no existe en todas las fuentes y sale
    como caja vacia) y el circulo se llena en el instante en que el item se
    confirma: `hecho` puede ser `true`/`false` o el segundo en que se
    confirma (el ✓ se dibuja entonces).

    Params: `items[{texto, hecho}]`, `kicker?`, `y?`, `at{item0..n}`.
    """
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    items = e.get("items") or []
    if not items:
        return capa_salida(layer, t, e["to"])

    at = e.get("at") or {}
    x0, _, x1, y1 = caja_segura()
    n = len(items)
    cols = 1 if n == 1 else 2          # el reel: dos casillas en fila
    filas = (n + cols - 1) // cols

    PANEL_PAD = 26
    GAP = 24
    KICKER_ALTO = 30
    CIRCULO_D = 64
    TILE_PAD = 16
    RADIO = 18

    pan_w = x1 - x0
    inner = pan_w - 2 * PANEL_PAD
    tile_w = (inner - GAP * (cols - 1)) // cols
    ancho_txt = tile_w - 2 * TILE_PAD

    # el texto de la casilla: versalitas del display en itálica (el del reel).
    # El rol es `secundario` (la escala ya lo define como "titulos de item").
    fab = ctx.fTi if FJI else ctx.fT
    tam = ESCALA["secundario"]
    alto_linea = int(tam * 1.16)
    alto_txt = 0
    for it in items:
        _l = _lineas_de_casilla(str(it.get("texto", "")).upper(),
                                fab(tam, 800), ancho_txt)
        alto_txt = max(alto_txt, len(_l) * alto_linea)
    tile_h = TILE_PAD + CIRCULO_D + 18 + max(1, alto_txt) + TILE_PAD
    panel_h = PANEL_PAD * 2 + (KICKER_ALTO + 26 if e.get("kicker") else 0) \
        + filas * tile_h + (filas - 1) * GAP

    try:
        y_panel = int(e.get("y", y1 - panel_h))
    except (TypeError, ValueError):
        y_panel = int(y1 - panel_h)
    y_panel = max(0, min(y_panel, H - panel_h))

    # el panel entra con la primera casilla (nada aparece de golpe)
    k_panel = entra(t, at.get("item0", e["from"] + 0.3), "bloque")
    sub_p, dp = grupo()
    dp.rounded_rectangle([x0, y_panel, x1, y_panel + panel_h], radius=RADIO,
                         fill=PANEL + (255,), outline=(70, 70, 70, 255), width=2)

    # el kicker: la raya de acento y el guion en monoespaciada
    y_k = y_panel + PANEL_PAD
    if e.get("kicker"):
        dp.rectangle([x0 + PANEL_PAD, y_k + 10, x0 + PANEL_PAD + 40, y_k + 16],
                     fill=ACENTO + (255,))
        fnt_k = ctx.fM(ESCALA["nota"], 700)
        dp.text((x0 + PANEL_PAD + 56, y_k + 13), str(e["kicker"]).upper(),
                font=fnt_k, fill=GRIS + (255,), anchor="lm")
    fundir(layer, sub_p, k_panel)

    y_tiles = y_k + (KICKER_ALTO + 26 if e.get("kicker") else 0)
    for i, it in enumerate(items):
        fila, col = divmod(i, cols)
        tx = x0 + PANEL_PAD + col * (tile_w + GAP)
        ty = y_tiles + fila * (tile_h + GAP)
        t_in = escalonado(at, "item", i, e["from"] + 0.3)
        k = entra(t, t_in, "elemento")
        if k <= 0:
            continue
        sub, ds = grupo()      # la casilla entera entra fundida
        hecho = it.get("hecho", False)
        # `hecho` puede ser un booleano (confirmada desde el principio o
        # nunca) o el SEGUNDO en que se confirma (el ✓ se dibuja entonces).
        if isinstance(hecho, bool):
            kc = 1.0 if hecho else 0.0
        else:
            kc = clamp01((t - float(hecho)) / 0.28)
        cx = tx + tile_w / 2
        cy = ty + TILE_PAD + CIRCULO_D / 2
        texto = str(it.get("texto", "")).upper()
        lineas = _lineas_de_casilla(texto, fab(tam, 800), ancho_txt)
        y_txt = ty + TILE_PAD + CIRCULO_D + 18
        # la casilla se dibuja PENDIENTE (aro vacio, borde gris, texto gris)
        ds.rounded_rectangle([tx, ty, tx + tile_w, ty + tile_h], radius=RADIO,
                             fill=PANEL2 + (255,), outline=(92, 92, 92, 255), width=2)
        ds.ellipse([cx - CIRCULO_D / 2, cy - CIRCULO_D / 2,
                    cx + CIRCULO_D / 2, cy + CIRCULO_D / 2],
                   outline=(92, 92, 92, 255), width=3)
        for li, ln in enumerate(lineas):
            ds.text((cx, y_txt + li * alto_linea), ln, font=fab(tam, 800),
                    fill=GRIS + (255,), anchor="ma")
        # y, cuando se CONFIRMA, la version confirmada se funde encima (fondo
        # negro, borde blanco, circulo lleno con el ✓ y el texto en blanco).
        # Fundida y no de golpe: un bloque que cambia en UN frame es un pop
        # (medido: confirmar en t=1,5 s daba un pop de 1,5 px).
        if kc > 0:
            ox, oy = int(tx) - 2, int(ty) - 2
            conf = Image.new("RGBA", (int(tile_w) + 4, int(tile_h) + 4),
                             (0, 0, 0, 0))
            dc = ImageDraw.Draw(conf)
            dc.rounded_rectangle([2, 2, tile_w + 2, tile_h + 2], radius=RADIO,
                                 fill=NEGRO + (255,), outline=BLANCO + (255,), width=2)
            r = CIRCULO_D / 2
            dc.ellipse([cx - ox - r, cy - oy - r, cx - ox + r, cy - oy + r],
                       fill=BLANCO + (255,))
            # el ✓ tiene que CABER dentro del circulo: su punto mas lejano
            # esta a 1,255·s del centro (mas el grosor del trazo)
            s_check = int((CIRCULO_D / 2 - 5) / 1.255)
            check(dc, cx - ox, cy - oy, s_check, NEGRO, max(4, int(s_check * 0.32)))
            for li, ln in enumerate(lineas):
                dc.text((cx - ox, y_txt - oy + li * alto_linea), ln,
                        font=fab(tam, 800), fill=BLANCO + (255,), anchor="ma")
            if kc < 1:
                conf.putalpha(conf.split()[3].point(lambda v: int(v * kc)))
            sub.alpha_composite(conf, (ox, oy))
        fundir(layer, sub, k)
    return capa_salida(layer, t, e["to"])


def sc_cadena(ctx, e, t):
    """La cadena de estados: N nodos con icono de linea, unidos por una linea
    discontinua, cada uno con su etiqueta.

    Es la escena del reel de "cara" (De8KNkdDT68): lo que vio cada quien, en
    fila y con el paso marcado. A diferencia de `constancia` (que es una LISTA
    de casillas con ✓), aqui los nodos se ENCADENAN: el conector punteado
    dice que es una secuencia.

    MEDIDO sobre ese reel (1080x1920):
      · el nodo es una caja de 149x140 con las esquinas redondeadas (radio
        21) y el borde de 2 px (blanco el que esta activo, gris el que no);
      · el icono de linea mide 69 px y va centrado en el nodo;
      · la etiqueta va DEBAJO: el nombre en negrita y debajo una linea en
        monoespaciada, mas pequena y en gris;
      · el conector son guiones de 10 px con 12 de hueco, en la linea media
        de los nodos.

    Params: `items[{icono, titulo, sub?, activo?}]`, `kicker?`, `y?`,
    `at{item0..n}`.
    """
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    items = e.get("items") or []
    if not items:
        return capa_salida(layer, t, e["to"])

    at = e.get("at") or {}
    x0, _, x1, y1 = caja_segura()
    n = len(items)
    PANEL_PAD = 26
    KICKER_ALTO = 30
    GAP = 24
    RADIO = 21
    NODE = 140
    ICONO_R = 34
    TAM_ICONO = int(ICONO_R * 2 * 0.46)      # la caja del icono: 31 px de texto

    pan_w = x1 - x0
    inner = pan_w - 2 * PANEL_PAD
    paso = inner // n
    node = min(NODE, paso - 30)
    alto_txt = int(ESCALA["secundario"] * 1.16)
    alto_sub = int(ESCALA["nota"] * 1.16)
    sub_h = alto_sub if any(it.get("sub") for it in items) else 0
    panel_h = PANEL_PAD * 2 + (KICKER_ALTO + 26 if e.get("kicker") else 0) \
        + node + 10 + alto_txt + (6 + sub_h if sub_h else 0)

    try:
        y_panel = int(e.get("y", y1 - panel_h))
    except (TypeError, ValueError):
        y_panel = int(y1 - panel_h)
    y_panel = max(0, min(y_panel, H - panel_h))

    # el panel entra con el primer nodo (nada aparece de golpe)
    k_panel = entra(t, at.get("item0", e["from"] + 0.3), "bloque")
    sub_p, dp = grupo()
    dp.rounded_rectangle([x0, y_panel, x1, y_panel + panel_h], radius=RADIO,
                         fill=PANEL + (255,), outline=(70, 70, 70, 255), width=2)
    y_k = y_panel + PANEL_PAD
    if e.get("kicker"):
        dp.rectangle([x0 + PANEL_PAD, y_k + 10, x0 + PANEL_PAD + 40, y_k + 16],
                     fill=ACENTO + (255,))
        fnt_k = ctx.fM(ESCALA["nota"], 700)
        dp.text((x0 + PANEL_PAD + 56, y_k + 13), str(e["kicker"]).upper(),
                font=fnt_k, fill=GRIS + (255,), anchor="lm")
    fundir(layer, sub_p, k_panel)

    y_nodos = y_k + (KICKER_ALTO + 26 if e.get("kicker") else 0)
    centro = y_nodos + node / 2
    for i, it in enumerate(items):
        xc = x0 + PANEL_PAD + paso * (i + 0.5)
        tx = xc - node / 2
        ty = y_nodos
        t_in = escalonado(at, "item", i, e["from"] + 0.3)
        k = entra(t, t_in, "elemento")
        if k <= 0:
            continue
        sub, ds = grupo()
        # el conector va ANTES del nodo (y 16 px despues del anterior: une,
        # no pega). Se dibuja en la misma capa que el nodo, asi que entra
        # con el.
        if i > 0:
            x_prev = x0 + PANEL_PAD + paso * (i - 0.5) + node / 2
            linea_discontinua(ds, x_prev + 16, tx - 10, centro,
                              (120, 120, 120, 255), grosor=3, largo=10, hueco=12)
        activo = bool(it.get("activo", True))
        borde = BLANCO + (255,) if activo else (92, 92, 92, 255)
        relleno = NEGRO + (255,) if activo else PANEL2 + (255,)
        ds.rounded_rectangle([tx, ty, tx + node, ty + node], radius=RADIO,
                             fill=relleno, outline=borde, width=2)
        icono_linea(ds, it.get("icono", ""), xc, centro, ICONO_R,
                    BLANCO + (255,) if activo else (110, 110, 110, 255))
        y_txt = ty + node + 10
        # el titulo va en su propia caja (el reel NO lo pone en versalitas:
        # solo el sub-rótulo va en monoespaciada mayúscula). Se ENCOGE hasta
        # el piso de letra legible y, si aun asi no cabe, se acorta el copy:
        # si se sale de su hueco, PISA al del nodo de al lado (la puerta lo
        # mide: "ningun texto pisa a otro").
        fnt_t, titulo = _encaja_una_linea(ctx.fT, it.get("titulo", ""),
                                           ESCALA["secundario"], paso - 16,
                                           800, 26)
        ds.text((xc, y_txt), titulo, font=fnt_t,
                fill=BLANCO + (255,) if activo else GRIS + (255,), anchor="ma")
        if it.get("sub"):
            fnt_s, sub_txt = _encaja_una_linea(ctx.fM, it.get("sub", ""),
                                                ESCALA["nota"], paso - 16, 700, 26)
            ds.text((xc, y_txt + alto_txt + 6), sub_txt,
                    font=fnt_s, fill=GRIS + (255,), anchor="ma")
        fundir(layer, sub, k)
    return capa_salida(layer, t, e["to"])


def sc_cartel(ctx, e, t):
    """El cartel: el rótulo de arriba, un icono de línea GRANDE en el acento
    y la afirmación al lado.

    Es el cartel del reel de "cara": "¿QUÉ ESTÁ PASANDO CON NOTEPAD++?" con
    la lupa al lado, y "LO VIO DIEGO DESDE / 0 OCT" con el reloj.

    MEDIDO sobre De8KNkdDT68 (1080x1920): el panel va de x=60 a x=1019 con
    el borde de 1 px; la raya del rótulo mide 40x6 px; el icono de línea
    mide ~100 px y va en el acento; la afirmación es el display en negrita y
    la palabra que sostiene el dato va en un BLOQUE ROJO (texto blanco).

    El texto usa el markup del kit: `*clave*` la pone en el acento,
    `~caja~` en un bloque rojo (texto blanco) y `^caja^` en un bloque
    blanco (texto oscuro).

    Params: `texto` (la afirmación), `kicker?` (el rótulo de arriba),
    `icono?` (lupa, reloj, alerta, globo, codigo), `tam?`, `y?`,
    `at{panel, icono, texto}`.
    """
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    at = e.get("at") or {}
    x0, _, x1, y1 = caja_segura()
    PANEL_PAD = 26
    RADIO = 20
    ICONO_R = 50
    GAP_ICONO = 34
    tam = int(e.get("tam", 60))   # 52 px se quedaba en una franja chica del 9:16
    fab = ctx.fTi if (e.get("itálica") or e.get("italica")) else ctx.fT
    fnt = fab(tam, 500)
    fnt_b = fab(tam, 800)

    # las palabras del texto y su resalte (el markup del kit, POR CARACTER:
    # "~NOTEPAD++~?" pone el bloque solo en NOTEPAD++ y deja la interrogacion
    # fuera, como en el reel)
    palabras = []
    for w in str(e.get("texto", "")).split():
        segs, buf, tipo, clave, dentro = [], "", None, False, False
        for ch in w:
            if ch in "*~^":
                if buf:
                    segs.append((buf, tipo if dentro else None,
                                 clave if dentro else False))
                buf = ""
                if dentro:            # el marcador de CIERRA el bloque
                    tipo, clave, dentro = None, False, False
                else:                # el de apertura lo ENTIERRA
                    tipo = {"~": "roja", "^": "blanca"}.get(ch)
                    clave = (ch == "*")
                    dentro = True
            else:
                buf += ch
        if buf:
            segs.append((buf, tipo if dentro else None, clave if dentro else False))
        if segs:
            palabras.append(segs)
    if not palabras:
        return capa_salida(layer, t, e["to"])

    # el reparto en lineas: el texto va a la derecha del icono
    ancho_ico = ICONO_R * 2 if e.get("icono") else 0
    x_txt = x0 + PANEL_PAD + ancho_ico + (GAP_ICONO if ancho_ico else 0)
    ancho_txt = x1 - PANEL_PAD - x_txt
    lineas, linea, ancho_linea = [], [], 0
    for segs in palabras:
        w_ = sum(ctx.tmp.textlength(s[0], font=fnt_b if s[2] else fnt) for s in segs)
        if linea and ancho_linea + w_ > ancho_txt:
            lineas.append(linea)
            linea, ancho_linea = [], 0
        linea.append(segs)
        ancho_linea += w_ + ctx.tmp.textlength(" ", font=fnt)
    if linea:
        lineas.append(linea)
    alto_linea = int(tam * 1.18)
    alto_texto = len(lineas) * alto_linea

    alto_kicker = 30 if e.get("kicker") else 0
    alto_panel = PANEL_PAD * 2 + alto_kicker + 20 + max(alto_texto, ICONO_R * 2)
    try:
        y_panel = int(e.get("y", y1 - alto_panel))
    except (TypeError, ValueError):
        y_panel = int(y1 - alto_panel)
    y_panel = max(0, min(y_panel, H - alto_panel))

    # el panel (entra con la pieza)
    k_panel = entra(t, at.get("panel", e["from"] + 0.2), "bloque")
    sub_p, dp = grupo()
    dp.rounded_rectangle([x0, y_panel, x1, y_panel + alto_panel], radius=RADIO,
                         fill=PANEL + (255,), outline=(70, 70, 70, 255), width=2)
    y_k = y_panel + PANEL_PAD
    if e.get("kicker"):
        dp.rectangle([x0 + PANEL_PAD, y_k + 10, x0 + PANEL_PAD + 40, y_k + 16],
                     fill=ACENTO + (255,))
        fnt_k = ctx.fM(ESCALA["nota"], 700)
        dp.text((x0 + PANEL_PAD + 56, y_k + 13), str(e["kicker"]).upper(),
                font=fnt_k, fill=GRIS + (255,), anchor="lm")
    fundir(layer, sub_p, k_panel)

    y_cont = y_k + alto_kicker + 20

    # el icono grande, en el acento
    if e.get("icono"):
        cx = x0 + PANEL_PAD + ICONO_R
        cy = y_cont + max(alto_texto, ICONO_R * 2) / 2
        k_ico = entra(t, at.get("icono", e["from"] + 0.4), "bloque")
        if k_ico > 0:
            sub_i, di = grupo()
            icono_linea(di, e["icono"], cx, cy, ICONO_R, ACENTO + (255,))
            if k_ico < 1:
                sub_i.putalpha(sub_i.split()[3].point(lambda v: int(v * k_ico)))
            layer.alpha_composite(sub_i)

    # la afirmación, con la palabra en su bloque
    k_txt = entra(t, at.get("texto", e["from"] + 0.6), "bloque")
    if k_txt > 0:
        sub_t, dt = grupo()
        y_linea = y_cont
        for ln in lineas:
            x_linea = x_txt
            for segs in ln:
                for txt_w, tipo, clave in segs:
                    f_ = fnt_b if clave else fnt
                    w_ = dt.textlength(txt_w, font=f_)
                    if tipo == "roja":
                        dt.rectangle([x_linea - 6, y_linea - 4, x_linea + w_ + 6,
                                      y_linea + alto_linea - 8], fill=ACENTO + (255,))
                        dt.text((x_linea, y_linea), txt_w, font=f_,
                                fill=BLANCO + (255,), anchor="la")
                    elif tipo == "blanca":
                        dt.rectangle([x_linea - 6, y_linea - 4, x_linea + w_ + 6,
                                      y_linea + alto_linea - 8], fill=BLANCO + (255,))
                        dt.text((x_linea, y_linea), txt_w, font=f_,
                                fill=NEGRO + (255,), anchor="la")
                    else:
                        dt.text((x_linea, y_linea), txt_w, font=f_,
                                fill=ACENTO + (255,) if clave else BLANCO + (255,),
                                anchor="la")
                    x_linea += w_
                x_linea += dt.textlength(" ", font=fnt)
            y_linea += alto_linea
        if k_txt < 1:
            sub_t.putalpha(sub_t.split()[3].point(lambda v: int(v * k_txt)))
        layer.alpha_composite(sub_t)
    return capa_salida(layer, t, e["to"])


def sc_camino(ctx, e, t):
    """El camino: una linea de luz que corre por la pieza y va encendiendo
    las estaciones que pasa.

    Es la idea del reel de referencia ("The Path"): una sola linea de luz
    hace de todo (revela el logotipo, llena la barra, se enrosca en la llama,
    es la onda de la voz, baja bajo el lema) y CADA FUNCION DE LA PIEZA es
    una estacion en el camino. Aqui la linea se dibuja con UNA funcion
    (`trazado`) y las estaciones son las insignias 3D que la casa ya tiene
    (`insignia_3d`).

    MEDIDO sobre el reel (1080x1920): el nodo mide ~100 px de lado con el
    labio oscuro debajo (el boton 3D de Duolingo), el borde se redondea con
    radio ~30 y la linea pasa por el CENTRO de los nodos (es la linea la
    que los revela, no un adorno al lado).

    Params: `estaciones[{titulo, icono?, hecha?}]`, `ruta?` (recta, s),
    `y?`, `ancho?`, `at{estacion0..n}`.
    """
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    estaciones = e.get("estaciones") or []
    if not estaciones:
        return capa_salida(layer, t, e["to"])
    at = e.get("at") or {}
    zx0, zy0, zx1, zy1 = caja_segura()
    R = 50
    col_linea = e.get("color") or ACENTO
    n = len(estaciones)
    # el camino entero flota: latido solo de grosor/alfa no alcanza el umbral
    # de muerto en el hold final (medido 0.29 → nota 86)
    fl = flota(t, e["from"] + 0.8, 4, 0.40)
    # 9:16: el camino corre en VERTICAL (como el timeline: etiquetas a la
    # derecha del nodo). Horizontal, 778 px de linea en un lienzo de 1920 de
    # alto dejaban el 87 % de la zona en negro (ocupacion 0.13). Se queda en
    # horizontal si el plan fija la geometria (`y`, `x0`, `x1`) o vuela la
    # camara de la pieza (su paneo es lateral: el mundo se desliza de lado).
    vertical = (H > W and not _CAMARA["activa"]
                and not any(k in e for k in ("y", "x0", "x1")))
    fnts = [fuente_que_cabe(ctx.fT, str(est.get("titulo", "")).upper(), ESCALA["secundario"],
                            (zx1 - zx0) * 0.55 if vertical else (zx1 - zx0) / max(1, n) - 12, 800)
            for est in estaciones]
    if vertical:
        w_et = max(ctx.tmp.textlength(str(est.get("titulo", "")).upper(), font=f)
                   for est, f in zip(estaciones, fnts))
        xr = int((W - (2 * R + 28 + w_et)) / 2 + R)        # el grupo nodo+etiqueta, centrado
        paso = min((zy1 - zy0) / n, 2 * R * (2 + REPARTO_MAX * 2))
        ya = (zy0 + zy1) / 2 - paso * n / 2 + fl
        pts = puntos_de_ruta(xr, ya, xr, ya + paso * n, e.get("ruta", "recta"))
    else:
        y = int(e.get("y", H * 0.46) + fl)
        x0 = int(e.get("x0", zx0))
        x1 = int(e.get("x1", zx1))
        pts = puntos_de_ruta(x0, y, x1, y, e.get("ruta", "recta"))

    # el MUNDO: la linea y las estaciones, en coordenadas de mundo
    mundo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    p0 = 0.5 / n
    p1 = 1.0 - 0.5 / n
    prog = clamp01((t - e["from"]) / max(1e-6, e["to"] - e["from"]))
    cabeza = p0 + (p1 - p0) * prog
    grosor = int(e.get("grosor", 7))
    # PISTA tenue del recorrido completo: sin ella, las estaciones pendientes
    # parecían desconectadas (el trazo solo dibuja lo ya recorrido). DRY:
    # la misma `trazado`, otro progreso/alfa.
    trazado(mundo, pts, (72, 72, 72), grosor=max(3, grosor - 2),
            progreso=1.0, desvanecer=0.0, brillo=False, alpha=130)
    # la linea viva: la MISMA funcion para todos (DRY) + latido en la cabeza
    # cuando el progreso se asienta (mata muerto del hold final)
    g_vivo = max(grosor, int(grosor * latido(t, e["from"] + (e["to"] - e["from"]) * 0.55,
                                             1.5, 0.10)))
    trazado(mundo, pts, col_linea, grosor=g_vivo,
            progreso=cabeza, desvanecer=0.22, cola=e.get("colores"))

    # las estaciones: se encienden cuando la cabeza las pasa. Cada una va en
    # el CENTRO de su hueco (no en el borde): asi su etiqueta cabe dentro de
    # la zona segura (en el borde, la etiqueta de la ultima se salia: medido,
    # la escena se encogia sola a 0,98).
    for i, est in enumerate(estaciones):
        pos = (i + 0.5) / n
        idx = int(pos * (len(pts) - 1))
        cx, cy = pts[idx]
        t_in = at.get(f"estacion{i}", e["from"])
        k = entra(t, t_in, "elemento")
        if k <= 0:
            continue
        encendida = cabeza >= pos - 0.02
        # la estación bajo la cabeza late: es el "ahora" del camino
        en_cabeza = encendida and abs(cabeza - pos) < (0.55 / n)
        col = col_linea if encendida else (110, 110, 110)
        a = int(255 * k) if encendida else int(150 * k)
        if en_cabeza:
            a = min(255, int(a * latido(t, t_in, 1.4, 0.08)))
        sub_n, dn = grupo()
        r_nodo = int(R * (latido(t, t_in, 1.4, 0.04) if en_cabeza else 1.0))
        insignia_3d(dn, cx, cy, r_nodo, est.get("icono"), ctx.fT(30, 800),
                     color=col, alpha=a, t=t)
        # el nombre de la estacion, debajo (a la derecha en vertical) — se
        # ENCOGE / acorta al hueco (LECCIONES era más ancha que el nodo)
        xy_et, anc = ((cx + R + 28, cy), "lm") if vertical else ((cx, cy + R + 18), "ma")
        dn.text(xy_et, str(est.get("titulo", "")).upper(), font=fnts[i],
                fill=(BLANCO if encendida else GRIS) + (a,), anchor=anc)
        if k < 1:
            sub_n.putalpha(sub_n.split()[3].point(lambda v: int(v * clamp01(k * 1.4))))
        mundo.alpha_composite(sub_n)

    # EL VUELO DE LA CAMARA NO ES DE LA ESCENA: es de la PIEZA (el global
    # `camara`, que ademas ya trae el paneo). Si la escena volara por su
    # cuenta, el factor de la zona segura mediria un mundo que se sale del
    # cuadro y la escena se encogeria sola (medido: 0,72). Con la camara
    # global, el mundo se escapa del encuadre porque la camara se ha ido,
    # que es lo que pasa de verdad.
    fundir(layer, mundo, 1.0)
    return capa_salida(layer, t, e["to"])


def sc_subrayado(ctx, e, t):
    """El texto con su LINEA DE LUZ debajo: la linea es la linea base.

    Es el cierre del reel de referencia ("The Path"): el lema se apoya en la
    linea y la linea se parte en los colores de los cursos y vuelve a
    juntarse.

    La linea la dibuja `trazado` (la MISMA primitiva que el camino y que
    cualquier otro trazo): aqui lo que cambia son los puntos y los colores.
    DRY: cinco trazos dibujados de cinco maneras son cinco trazos que se
    desincronizan.

    Params: `texto` (el lema), `color?`, `colores?` (la linea se parte en
    estos colores; "serie" = la SERIE de la marca), `y?`, `grosor?`,
    `at{texto, linea}`.
    """
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    texto = str(e.get("texto", "")).strip()
    if not texto:
        return capa_salida(layer, t, e["to"])
    d = ImageDraw.Draw(layer)
    at = e.get("at") or {}
    zx0, _, zx1, _ = caja_segura()
    y = int(e.get("y", H * 0.58))
    tam = int(e.get("tam", 56))
    fab = ctx.fTi if (e.get("itálica") or e.get("italica")) else ctx.fT
    fnt = fab(tam, 800)
    col = e.get("color") or ACENTO
    colores = colores_de(e.get("colores"))   # "serie": las categorías de la marca

    # el lema, centrado, en un maximo de dos lineas
    ancho_max = int((zx1 - zx0) * 0.92)
    palabras = texto.split()
    lineas, linea, ancho = [], "", 0.0
    for p in palabras:
        w_ = ctx.tmp.textlength((linea + " " + p).strip(), font=fnt)
        if linea and w_ > ancho_max:
            # la palabra NO cabe: la linea se parte aqui (mirar el ancho CON
            # la palabra, no el de antes: si no, la linea se sale de la zona
            # segura y la escena entera se encoge)
            lineas.append(linea)
            linea, ancho = p, ctx.tmp.textlength(p, font=fnt)
        else:
            linea = (linea + " " + p).strip()
            ancho = w_
    if linea:
        lineas.append(linea)
    lineas = lineas[:2]
    alto_linea = int(tam * 1.16)

    k_txt = entra(t, at.get("texto", e["from"] + 0.2), "bloque")
    y_linea = y + 26
    if k_txt > 0:
        sub_t, dt = grupo()
        y_txt = y - len(lineas) * alto_linea
        for i, ln in enumerate(lineas):
            dt.text((W / 2, y_txt + i * alto_linea), ln, font=fnt,
                    fill=BLANCO + (int(255 * k_txt),), anchor="ma")
        if k_txt < 1:
            sub_t.putalpha(sub_t.split()[3].point(lambda v: int(v * k_txt)))
        # la linea va DEBAJO de la TINTA REAL del texto, no de una caja
        # teorica: el alto de la fuente cambia con la tipografia del pack y
        # con la caja la linea se meteia dentro del texto (medido: con el
        # pack la tinta bajaba 78 px y la linea se comia el texto)
        bb = sub_t.getbbox()
        if bb:
            y_linea = int(bb[3]) + 18
        layer.alpha_composite(sub_t)

    # la linea: la MISMA funcion de siempre, con sus puntos y sus colores
    x0 = int(W / 2 - ctx.tmp.textlength(max(lineas, key=len), font=fnt) / 2)
    x1 = int(W / 2 + ctx.tmp.textlength(max(lineas, key=len), font=fnt) / 2)
    if x1 - x0 < 40:
        x0, x1 = zx0, zx1
    k_lin = entra(t, at.get("linea", e["from"] + 0.8), "bloque")
    if k_lin > 0:
        sub_l = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        pts = puntos_de_ruta(x0, y_linea, x1, y_linea, "recta")
        trazado(sub_l, pts, col, grosor=int(e.get("grosor", 7)),
                progreso=clamp01(k_lin * 1.2), desvanecer=0.0, cola=colores)
        layer.alpha_composite(sub_l)
    return capa_salida(layer, t, e["to"])


def sc_kenburns(ctx, e, t):
    """Ken Burns sobre una imagen: zoom + paneo progresivo. Ideal para
    galerías, openings sobre foto, documentales.
    Params: `imagen` (ruta), `titulo`, `subtitulo?`, `zoom_from?`, `zoom_to?`,
    `pan_x?`, `pan_y?`, `at{rotulo, kenburns, texto}`.

    Fuente: `ken-burns.tsx` (reactvideoeditor/remotion-templates).
    """
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    at = e["at"]
    # fondo negro por si la imagen no carga
    d.rectangle([0, 0, W, H], fill=(0, 0, 0, 255))
    # imagen cubriendo el 9:16, cargada una vez por proceso (imagen_ajustada)
    base = imagen_ajustada(e.get("imagen"), W, H)
    # la foto (a sangre, cubre el cuadro) entra disuelta, lineal en 0.75 s: tras
    # un corte aparecía entera en un frame; en 0.4 s smoothstep saltaba 59 de luma
    # cada 0.25 s (destello); lineal y más larga queda bajo el umbral de auto_qa
    a_foto = clamp01((t - e["from"]) / 0.75)
    if base is not None:
        t_kb = at.get("kenburns", e["from"] + 0.2)
        layer.alpha_composite(kenburns(base, t, t_kb, dur=e.get("dur_kb", 4.0),
                                       zoom_from=e.get("zoom_from", 1.0),
                                       zoom_to=e.get("zoom_to", 1.15),
                                       pan_x=e.get("pan_x", 0.0),
                                       pan_y=e.get("pan_y", 0.0)))
    # oscurecer para que el texto lea
    # (componer, no dibujar: ImageDraw con alfa REEMPLAZA píxeles y borraba la foto)
    # texto: abajo, pero DENTRO de la zona segura (la foto es a sangre, el texto no)
    x0, _, x1, y1 = caja_segura()
    fnt = ctx.fT(80, 800)
    lineas = linewrap(e.get("titulo", ""), fnt, x1 - x0) if e.get("titulo") else []
    y_sub = y1 - 40
    y_tit = y_sub - (70 if e.get("subtitulo") else 0) - 90 * len(lineas) + 45
    velo = Image.new("RGBA", (W, H), (0, 0, 0, 0))   # gradiente: el texto lee sin cortar la foto
    vd = ImageDraw.Draw(velo)
    y_velo = int(y_tit - 160)
    for y in range(y_velo, H, 4):
        vd.rectangle([0, y, W, y + 4], fill=(0, 0, 0, int(170 * clamp01((y - y_velo) / 260))))
    layer.alpha_composite(velo)
    if lineas and t >= at.get("texto", e["from"] + 0.5):
        k = entra(t, at.get("texto", e["from"] + 0.5), "bloque")
        al = int(255 * clamp01(k * 1.3))
        for i, ln in enumerate(lineas):
            d.text((W / 2, y_tit + i * 90 + (1 - min(1, k)) * 24), ln, font=fnt,
                   fill=BLANCO + (al,), anchor="mm")
    if e.get("subtitulo") and t >= at.get("subtitulo", e["from"] + 1.5):
        k = entra(t, at.get("subtitulo", e["from"] + 1.5), "bloque")
        fnt_s = fuente_que_cabe(ctx.fX, e["subtitulo"], 36, x1 - x0, 600)
        d.text((W / 2, y_sub), e["subtitulo"], font=fnt_s,
               fill=GRIS + (int(255 * clamp01(k * 1.3)),), anchor="mm")
    if a_foto < 1:   # disolución de entrada sobre la capa ya compuesta (la foto es opaca)
        layer.putalpha(layer.split()[3].point(lambda v: int(v * a_foto)))
    return capa_salida(layer, t, e["to"])


def sc_pasos(ctx, e, t):
    """Ruta de N pasos (1-5) en fila (16:9) o columna (9:16), con el paso
    activo brillando y los demás atenuados. Params: `titulo`, `items[{titulo, texto, at}]`,
    `at{rotulo, item0..n}`. Fuente: `progress-steps.tsx` (reactvideoeditor/remotion-templates).
    """
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    at = e["at"]
    rotulo(ctx, layer, t, e.get("titulo", ""), at.get("rotulo", e["from"]), y=rotulo_y())
    items = e.get("items", [])
    n = len(items)
    if n == 0:
            return capa_salida(layer, t, e["to"])
    vertical = H > W  # layout en columna para 9:16
    if vertical:
        # columna
        _, _, _, zy1 = caja_segura()
        y0 = rotulo_y() + 90
        _res = 60 if e.get("fuente") else 0
        fila_h = min(260, (zy1 - y0 - _res) / n)
        y0 += ((zy1 - y0 - _res) - fila_h * n) / 2
        cx = W / 2
        # el ACTIVO es el último ya asentado (o el marcado): antes TODOS los
        # entrados brillaban en acento y no se leía el "ahora" del proceso
        t_ins = [escalonado(at, "item", j, e["from"] + 0.3) for j in range(n)]
        alcanzados = [j for j in range(n) if t >= t_ins[j] and entra(t, t_ins[j], "elemento") > 0.85]
        marcado = next((j for j, it in enumerate(items) if it.get("activo")), None)
        activo_idx = marcado if marcado is not None else (alcanzados[-1] if alcanzados else -1)
        fy = flota(t, e["from"] + 1.5, 4, 0.36)
        for i, it in enumerate(items):
            t_in = t_ins[i]
            k = entra(t, t_in, "elemento")
            if k <= 0:
                continue
            sub, ds = grupo()   # el paso entero entra fundido
            yi = y0 + i * fila_h + fila_h * 0.1 + fy
            # número
            radio = min(fila_h * 0.35, 60)
            es_activo = (i == activo_idx)
            pulso = latido(t, t_in, 1.5, 0.07) if es_activo else 1.0
            col_n = ACENTO if es_activo else ((90, 90, 90, 255) if i in alcanzados or i < activo_idx
                                              else (70, 70, 70, 255))
            circulo_numero(ds, cx, yi + radio, radio, i + 1, col_n, BLANCO, ctx,
                           alpha=min(255, int(255 * pulso)) if es_activo else 255)
            # texto debajo del número
            fnt = ctx.fX(int(min(46, fila_h * 0.18)), 700)
            col_t = BLANCO if (es_activo or i <= activo_idx) else GRIS
            ds.text((cx, yi + 2 * radio + 8), it.get("titulo", ""), font=fnt,
                    fill=col_t + (255,), anchor="mt")
            y_fin = yi + 2 * radio + 8 + fnt.size
            if it.get("texto"):
                fnt_t = ctx.fX(int(min(32, fila_h * 0.13)), 400)
                ds.text((cx, y_fin + 6), it.get("texto", ""), font=fnt_t,
                        fill=GRIS + (255,), anchor="mt")
                y_fin += 6 + fnt_t.size
            # conector: del texto al círculo siguiente (nunca atraviesa la letra)
            if i < n - 1 and yi + fila_h + fila_h * 0.1 - 10 > y_fin + 14:
                ds.line([cx, y_fin + 14, cx, yi + fila_h - 10],
                       fill=(150, 150, 150, 255), width=3)
            fundir(layer, sub, k)
    else:
        # fila (misma regla de activo que la columna)
        zx0, _, zx1, _ = caja_segura()
        x0, w_disp = zx0, zx1 - zx0
        col_w = w_disp / n
        cy = H * 0.50
        t_ins = [escalonado(at, "item", j, e["from"] + 0.3) for j in range(n)]
        alcanzados = [j for j in range(n) if t >= t_ins[j] and entra(t, t_ins[j], "elemento") > 0.85]
        marcado = next((j for j, it in enumerate(items) if it.get("activo")), None)
        activo_idx = marcado if marcado is not None else (alcanzados[-1] if alcanzados else -1)
        for i, it in enumerate(items):
            t_in = t_ins[i]
            k = entra(t, t_in, "elemento")
            if k <= 0:
                continue
            sub, ds = grupo()   # el paso entero entra fundido
            radio = min(col_w * 0.18, 60)
            xi = x0 + (i + 0.5) * col_w - radio          # centrado en su columna
            es_activo = (i == activo_idx)
            pulso = latido(t, t_in, 1.5, 0.07) if es_activo else 1.0
            col_n = ACENTO if es_activo else ((90, 90, 90, 255) if i <= activo_idx
                                              else (70, 70, 70, 255))
            circulo_numero(ds, xi + radio, cy, radio, i + 1, col_n, BLANCO, ctx,
                           alpha=min(255, int(255 * pulso)) if es_activo else 255)
            # texto
            fnt = ctx.fX(int(unidad() * 0.042), 700)
            lineas = linewrap(it.get("titulo", ""), fnt, col_w * 0.85)
            col_t = BLANCO if (es_activo or i <= activo_idx) else GRIS
            for li, ln in enumerate(lineas):
                ds.text((xi + radio, cy + radio + 18 + li * (fnt.size + 4)),
                       ln, font=fnt, fill=col_t + (255,), anchor="mt")
            if it.get("texto"):
                fnt_t = ctx.fX(int(unidad() * 0.03), 400)
                ds.text((xi + radio, cy + radio + 26 + len(lineas) * (fnt.size + 4)),
                       it["texto"], font=fuente_que_cabe(ctx.fX, it["texto"], fnt_t.size, col_w * 0.9, 400),
                       fill=GRIS, anchor="mt")
            # conector hasta el borde del círculo siguiente
            if i < n - 1:
                ds.line([xi + 2 * radio + 10, cy, x0 + (i + 1.5) * col_w - radio - 10, cy],
                       fill=(150, 150, 150, 255), width=3)
            fundir(layer, sub, k)
    if e.get("fuente"):
        pie_fuente(ctx, ImageDraw.Draw(layer), e, t, at.get("fuente", e["from"] + 1.5))
    return capa_salida(layer, t, e["to"])


# ───────── Ronda 3: iart-ai/motion-skills (MIT) — ver references/scene-patterns-from-internet.md ─────────

def _fmt_tiempo(seg, formato):
    h, r = divmod(int(seg), 3600); m, s_ = divmod(r, 60)
    if formato == "ss":
        return f"{int(seg):02d}"
    if formato == "hh:mm:ss":
        return f"{h:02d}:{m:02d}:{s_:02d}"
    return f"{h * 60 + m:02d}:{s_:02d}"


def sc_countdown(ctx, e, t):
    """Cuenta regresiva exacta. El número es función pura del tiempo (nunca un
    contador acumulado): marca 00 en el frame exacto `at.inicio + segundos`.
    Cada dígito que cambia rueda tipo odómetro en los últimos RODAR s de su
    segundo (llega exacto al cambio); dígitos de ancho fijo (no tiemblan).
    Params: `segundos` (default: hasta 1 s antes del fin de la escena),
    `formato` (ss | mm:ss | hh:mm:ss; default según la duración), `rotulo?`,
    `final?` (texto al llegar a cero, ej. "¡EN VIVO!"), `at{rotulo, inicio}`.
    Fuente: countdown-video (iart-ai/tiktok-video-skills).
    """
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    at = e.get("at", {})
    t0 = at.get("inicio", e["from"] + 0.3)
    if e.get("rotulo"):
        rotulo(ctx, layer, t, e["rotulo"], at.get("rotulo", e["from"]), y=rotulo_y())
    total = float(e.get("segundos", max(1.0, e["to"] - t0 - 1.0)))
    formato = e.get("formato") or ("ss" if total < 60 else "mm:ss" if total < 3600 else "hh:mm:ss")
    restante = total - max(0.0, t - t0)
    mostrado = max(0, math.ceil(restante - 1e-9))
    rodar = clamp01((RODAR - (restante - (mostrado - 1))) / RODAR) if mostrado > 0 else 0.0
    actual, siguiente = _fmt_tiempo(mostrado, formato), _fmt_tiempo(max(0, mostrado - 1), formato)
    tam = int(min(300, H * 0.20))   # en 16:9 el alto manda: aire bajo el rótulo
    while tam > 80:
        fnt = ctx.fT(tam, 800)
        if ancho_tabular(fnt) * len(actual) <= W - 2 * MARGEN:
            break
        tam -= 10
    k = entra(t, t0 - 0.3, "elemento")
    t_fin = t0 + total
    kf = entra(t, t_fin, "pop") if e.get("final") else 0.0
    # al llegar a cero los dígitos se funden del todo EN SU LUGAR (subiendo
    # chocaban con el rótulo en 16:9) y el texto final los reemplaza: antes el
    # 00 quedaba al 25 % y el final lo pisaba
    ks = prog(t, t_fin, t_fin + 0.2, smoothstep) if e.get("final") else 0.0
    alfa = int(255 * clamp01(k * 1.4) * (1 - ks))
    if alfa > 0:
        odometro(layer, siguiente, actual, rodar, W / 2, H * 0.45, fnt, BLANCO + (alfa,))
    if kf > 0:
        zx0, _, zx1, _ = caja_segura()
        sc = 1 + 0.25 * (1 - min(1, kf))   # golpe: llega grande y asienta con el resorte
        ff = fuente_que_cabe(ctx.fT, e["final"], tam * 0.62 * sc, (zx1 - zx0) * 0.94)
        d.text((W / 2, H * 0.45 + flota(t, t_fin + 0.4, 5, 0.45)), e["final"], font=ff,   # asentado, respira
               fill=ACENTO + (int(255 * clamp01(kf * 1.4)),), anchor="mm")
    return capa_salida(layer, t, e["to"])


def _fmt_precio(v, e):
    dec = e.get("decimales")
    if dec is None:   # mismos decimales en todos los precios de la oferta
        dec = 0 if all(float(x).is_integer() for x in precios_oferta(e)[:2]) else 2
    txt = f"{v:,.{dec}f}"
    txt = separar(txt, e.get("miles"), e.get("decimal"))   # la escena manda; si no, el plan
    m = e.get("moneda", "$")
    return f"{txt} {m}" if e.get("moneda_despues") else f"{m}{txt}"


def precios_oferta(e):
    """`ahora` y el % se CALCULAN de `antes` (nunca escritos dos veces).
    Fail-loud: un precio incoherente rompe el render antes de mentir en pantalla."""
    antes = float(e.get("antes", 0))
    if "ahora" in e:
        ahora = float(e["ahora"])
    elif "descuento" in e:
        ahora = round(antes * (1 - float(e["descuento"]) / 100), 2)
    else:
        raise ValueError("oferta: falta `ahora` o `descuento`")
    if not 0 < ahora < antes:
        raise ValueError(f"oferta: precios incoherentes (antes={antes}, ahora={ahora}): "
                         "`ahora` debe ser positivo y menor que `antes`")
    pct = (1 - ahora / antes) * 100
    if "ahora" in e and "descuento" in e and abs(pct - float(e["descuento"])) > 0.5:
        raise ValueError(f"oferta: `descuento`={e['descuento']}% no coincide con "
                         f"antes/ahora ({pct:.1f}%): dar solo uno de los dos")
    return antes, ahora, round(pct)


def sc_oferta(ctx, e, t):
    """Oferta: UN descuento, un código, un CTA. El número es el mensaje.
    Orden: el descuento aterriza (lo más grande) → se TACHA el precio viejo →
    DESPUÉS el nuevo cuenta hacia abajo hasta su valor → código quieto (≥2 s,
    se lee y se captura) → vencimiento real → CTA.
    Params: `antes`, `ahora` o `descuento` (uno de los dos), `moneda` ($),
    `decimales?`, `miles?`/`decimal?` (separadores), `mostrar?`
    (porcentaje | monto; default: monto si el ahorro es < 10), `codigo?`,
    `vence?`, `cta?`, `rotulo?`,
    `at{rotulo, descuento, tachado, precio, codigo, vence, cta}`.
    Fuente: promo-video (iart-ai/ecommerce-video-skills).
    """
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    at = e.get("at", {})
    fr = e["from"]
    antes, ahora, pct = precios_oferta(e)
    mostrar = e.get("mostrar") or ("monto" if antes - ahora < 10 else "porcentaje")
    badge = f"-{pct}%" if mostrar == "porcentaje" else f"-{_fmt_precio(antes - ahora, e)}"
    zx0, zy0, zx1, zy1 = caja_segura()
    tam = 300
    while tam > 90 and ctx.tmp.textlength(badge, font=ctx.fT(tam, 800)) > (zx1 - zx0) * 0.92:
        tam -= 10
    # pila medida (en 16:9 encoge junta en vez de pisarse)
    if e.get("rotulo"):
        rotulo(ctx, layer, t, e["rotulo"], at.get("rotulo", fr), y=rotulo_y(),
                tam=ESCALA["rotulo"])
    bloques = [("badge", tam * 1.12), ("antes", 100),
               ("precio", 160), ("codigo", 124 if e.get("codigo") else 0),
               ("vence", 50 if e.get("vence") else 0), ("cta", 120 if e.get("cta") else 0)]
    bloques = [b for b in bloques if b[1]]
    top_pila = bajo_rotulo(rotulo_y(), ESCALA["rotulo"], aire=0.3) if e.get("rotulo") else zy0 + 20
    ys, f = pila([a for _, a in bloques], top_pila,
                zy1 - (60 if e.get("fuente") else 10), gap=26)
    Y = {n: y for (n, _), y in zip(bloques, ys)}
    px = lambda v: max(MIN_LETRA, int(v * f))   # noqa: E731  (nunca ilegible)
    t_d = at.get("descuento", fr + 0.4)
    kd = entra(t, t_d, "pop")
    if kd > 0:
        sc = 1 + 0.12 * (1 - min(1, kd))   # aterriza desde un poco más grande
        d.text((W / 2, Y["badge"]), badge, font=ctx.fT(int(px(tam) * sc), 800),
               fill=ACENTO + (int(255 * clamp01(kd * 1.5)),), anchor="mm")
    t_t = at.get("tachado", fr + 1.3)
    ka = entra(t, t_t - 0.35, "suave")
    if ka > 0:
        txt = _fmt_precio(antes, e); fnt = ctx.fT(px(92), 700)
        tw_ = ctx.tmp.textlength(txt, font=fnt); y = Y["antes"]
        d.text((W / 2, y), txt, font=fnt, fill=GRIS + (int(255 * clamp01(ka * 1.4)),), anchor="mm")
        kt = ease_out(clamp01((t - t_t) / 0.35))
        if kt > 0:
            x0 = W / 2 - tw_ / 2 - 12
            d.line([(x0, y + 6), (x0 + (tw_ + 24) * kt, y - 6)], fill=ACENTO + (255,), width=px(10))
    t_p = at.get("precio", t_t + 0.5)
    if t >= t_p:
        kp = entra(t, t_p, "pop")
        v = antes + (ahora - antes) * ease_out(clamp01((t - t_p) / 0.9))
        sc = 1 + 0.06 * max(0, 1 - abs((t - t_p - 0.9) / 0.15)) if t > t_p + 0.75 else 1
        cifra(d, (W / 2, Y["precio"]), _fmt_precio(v, e), ctx.fT(int(px(150) * sc), 800),
              BLANCO + (int(255 * clamp01(kp * 1.5)),), anchor="mm")
    if e.get("codigo"):
        t_c = at.get("codigo", t_p + 1.2)
        kc = entra(t, t_c, "suave")
        if kc > 0:
            txt = e["codigo"]
            max_cw = (zx1 - zx0) * 0.90
            fnt = fuente_que_cabe(ctx.fM, txt, px(56), max_cw - px(90), 700)
            cw_ = min(max_cw, ctx.tmp.textlength(txt, font=fnt) + px(90)); chh = px(104)
            x0, y0 = W / 2 - cw_ / 2, Y["codigo"] - chh / 2 + (1 - min(1, kc)) * 20
            al = int(255 * clamp01(kc * 1.4))
            d.rounded_rectangle([x0, y0, x0 + cw_, y0 + chh], radius=px(22), fill=PANEL2 + (al,))
            paso = 22   # borde punteado: lee como "código para copiar"
            for xx in range(int(x0 + 18), int(x0 + cw_ - 18), paso):
                for yy_ in (y0, y0 + chh):
                    d.line([(xx, yy_), (min(xx + 11, x0 + cw_ - 18), yy_)], fill=ACENTO + (al,), width=3)
            d.text((W / 2, y0 + chh / 2), txt, font=fnt, fill=BLANCO + (al,), anchor="mm")
    if e.get("vence"):
        t_v = at.get("vence", at.get("codigo", t_p + 1.2) + 0.3)
        kv = entra(t, t_v, "suave")
        if kv > 0:
            d.text((W / 2, Y["vence"]), e["vence"], font=ctx.fX(px(38), 600),
                   fill=GRIS + (int(255 * clamp01(kv * 1.4)),), anchor="mm")
    if e.get("cta"):
        t_b = at.get("cta", at.get("vence", t_p + 1.5) + 0.5)
        kb = entra(t, t_b, "pop")
        if kb > 0:
            max_bw = (zx1 - zx0) * 0.92
            fnt = fuente_que_cabe(ctx.fT, e["cta"], px(ESCALA["dato"]), max_bw - px(120), 800)
            bw_ = min(max_bw, ctx.tmp.textlength(e["cta"], font=fnt) + px(120)); bh_ = px(110)
            s_ = 0.9 + 0.1 * min(1.08, kb)
            x0, y0 = W / 2 - bw_ * s_ / 2, Y["cta"] - bh_ * s_ / 2
            al = int(255 * clamp01(kb * 1.4))
            d.rounded_rectangle([x0, y0, x0 + bw_ * s_, y0 + bh_ * s_], radius=int(bh_ * s_ / 2),
                                fill=ACENTO + (al,))
            d.text((W / 2, y0 + bh_ * s_ / 2), e["cta"], font=fnt, fill=BLANCO + (al,), anchor="mm")

    if e.get("fuente"):
        pie_fuente(ctx, d, e, t, at.get("fuente", e["from"] + 2.0))
    return capa_salida(layer, t, e["to"])


_IMG_CACHE = {}


def imagen_ajustada(ruta, ancho, alto):
    """Imagen escalada a (ancho, alto) con cubrir+recorte, cacheada por proceso
    (cargar y redimensionar en cada frame es lo que hace lento un render)."""
    clave = (ruta, int(ancho), int(alto))
    if clave not in _IMG_CACHE:
        img = None
        if ruta and os.path.isfile(os.path.expanduser(ruta)):
            try:
                base = Image.open(os.path.expanduser(ruta)).convert("RGBA")
                f = max(ancho / base.width, alto / base.height)
                base = base.resize((max(1, int(base.width * f)), max(1, int(base.height * f))),
                                   Image.LANCZOS)
                x0, y0 = (base.width - int(ancho)) // 2, (base.height - int(alto)) // 2
                img = base.crop((x0, y0, x0 + int(ancho), y0 + int(alto)))
            except Exception as ex:
                info(f"no se pudo cargar {ruta}: {ex}")
        _IMG_CACHE[clave] = img
    return _IMG_CACHE[clave]


def sc_demo(ctx, e, t):
    """Demo de producto desde capturas (sin grabar pantalla): ventana con barra
    y URL, cursor que viaja con smoothstep al objetivo, onda del clic y cambio
    de pantalla en el MISMO frame, zoom al foco (≤2×) con spotlight y un
    beneficio por paso. Cámara O cursor, nunca los dos a la vez.
    Params: `captura` (PNG/JPG, idealmente capturada a 2×), `url?`, `rotulo?`,
    `aspecto?` (alto/ancho de la captura si no hay archivo; default 0.625),
    `pasos[{x, y (0..1 sobre la captura), at (clic), zoom? (≤2, default 1.6),
    texto?, captura? (pantalla que aparece con el clic)}]`, `at{rotulo, ventana}`.
    Ritmo: 15 s = 3–4 pasos; 30 s = 5–7 (acortar pasos, nunca los holds de lectura).
    Fuente: product-demo-video (iart-ai/ecommerce-video-skills).
    """
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    at = e.get("at", {})
    if e.get("rotulo"):
        rotulo(ctx, layer, t, e["rotulo"], at.get("rotulo", e["from"]), y=rotulo_y())
    kv = entra(t, at.get("ventana", e["from"] + 0.2), "suave")
    if kv <= 0:
        return capa_salida(layer, t, e["to"])
    zx0_, _, zx1_, _ = caja_segura()
    bw = int(min(W * 0.86, zx1_ - zx0_))   # la ventana cabe en la zona segura
    ruta = e.get("captura")
    asp = e.get("aspecto", 0.625)
    if ruta and os.path.isfile(os.path.expanduser(ruta)):
        try:
            with Image.open(os.path.expanduser(ruta)) as im_:
                asp = im_.height / im_.width
        except Exception:
            pass
    barra, pie = 48, 152   # pie: aire + botón del beneficio bajo la ventana
    # el bloque (ventana + botón) se centra ENTRE el rótulo y el borde seguro
    # inferior: con H*0.44 fijo, en 16:9 la ventana tapaba el rótulo
    arriba = bajo_rotulo(rotulo_y()) + 16 if e.get("rotulo") else caja_segura()[1]
    libre = caja_segura()[3] - arriba
    bh = int(min(H * 0.48, bw * asp, libre - barra - pie))
    x0 = (W - bw) // 2
    y0 = int(arriba + (libre - (barra + bh + pie)) / 2 + (1 - min(1, kv)) * 40)
    pasos = sorted(e.get("pasos", []), key=lambda p_: p_.get("at", 0))
    # pantalla vigente: la del último clic ya ocurrido que traiga `captura`
    pantalla, previa, t_cambio = ruta, None, None
    for p_ in pasos:
        if p_.get("captura") and t >= p_.get("at", 0):
            previa, pantalla, t_cambio = pantalla, p_["captura"], p_.get("at", 0)
    img = imagen_ajustada(pantalla, bw, bh)
    # el cambio de pantalla arranca en el MISMO frame del clic, fundido en 0.15 s
    if img is not None and t_cambio is not None and t - t_cambio < 0.15:
        ant = imagen_ajustada(previa, bw, bh)
        if ant is not None:
            img = Image.blend(ant, img, smoothstep(clamp01((t - t_cambio) / 0.15)))
    if img is None:   # sin captura: maqueta neutra (nunca un hueco negro)
        img = Image.new("RGBA", (bw, bh), PANEL2 + (255,))
        dm = ImageDraw.Draw(img)
        for r_ in range(6):
            dm.rounded_rectangle([40, 40 + r_ * bh // 7, bw * (0.45 + 0.08 * (r_ % 3)),
                                  40 + r_ * bh // 7 + bh // 14], radius=10, fill=(70, 70, 70, 255))
    # cámara: zoom al foco del paso vigente, sale antes de que viaje el cursor
    z, fx, fy, foco = 1.0, 0.5, 0.5, 0.0
    for i, p_ in enumerate(pasos):
        a_ = p_.get("at", 0)
        nxt = pasos[i + 1].get("at", 1e9) if i + 1 < len(pasos) else 1e9
        # zoom de cámara en 1 s smoothstep (0.7 s ease_in_out barría ~40 px/frame);
        # nace EN el clic, encima del fundido de pantalla: si esperaba a que el
        # fundido terminara, quedaba un frame quieto y el zoom arrancaba en seco
        zin = smoothstep(clamp01((t - a_) / 1.0))
        zout = smoothstep(clamp01((t - (nxt - 1.4)) / 0.9))
        s_ = zin * (1 - zout)
        if s_ > 0:
            # asentado el zoom (cursor quieto), la cámara sigue entrando lento:
            # el hold respira sin mover cámara y cursor a la vez
            deriva = 0.04 * min(3.0, max(0.0, t - (a_ + 0.85)))
            z = 1 + (min(2.0, p_.get("zoom", 1.6)) - 1 + deriva) * s_
            fx, fy, foco = p_.get("x", 0.5), p_.get("y", 0.5), s_
    fxp, fyp = fx * bw, fy * bh
    cx_, cy_ = fxp * (1 - 1 / z), fyp * (1 - 1 / z)
    vista = img.transform(img.size, Image.AFFINE, (1 / z, 0, cx_, 0, 1 / z, cy_),
                          resample=Image.BICUBIC)
    # una superficie clara que cubre medio cuadro (16:9) entra fundida en 1 s:
    # con el alfa del resorte la luminancia saltaba 80 en 0.2 s (flash en auto_qa)
    a_v = int(255 * smoothstep(clamp01((t - at.get("ventana", e["from"] + 0.2)) / 1.0)))
    if foco > 0:   # spotlight: atenuar todo menos el foco
        mask = Image.new("L", (bw, bh), int(120 * foco))
        r_f = 150 * z
        ImageDraw.Draw(mask).ellipse([(fxp - cx_) * z - r_f, (fyp - cy_) * z - r_f,
                                      (fxp - cx_) * z + r_f, (fyp - cy_) * z + r_f], fill=0)
        vista.paste(Image.new("RGBA", (bw, bh), (0, 0, 0, 255)), (0, 0),
                    mask.filter(ImageFilter.GaussianBlur(30)))
    marco = Image.new("RGBA", (bw, bh + barra), (0, 0, 0, 0))
    dm = ImageDraw.Draw(marco)
    dm.rounded_rectangle([0, 0, bw, bh + barra], radius=28, fill=PANEL + (255,))
    for k_ in range(3):
        dm.ellipse([22 + k_ * 26, 17, 36 + k_ * 26, 31], fill=(90, 90, 90, 255))
    if e.get("url"):
        # la URL es un "nota" de la escala (28 px). Antes 20 px: por debajo
        # del piso legible, en una barra de 30 que no lo contenia. La barra
        # crece para que la letra quepa dentro y el copy se recorta.
        dm.rounded_rectangle([120, 5, bw - 30, 43], radius=19, fill=PANEL2 + (255,))
        fnt_url=ctx.fX(ESCALA["nota"],500)
        dm.text((140, 24), recorta_para(e["url"], fnt_url, bw - 30 - 140 - 14, ctx.tmp),
                font=fnt_url, fill=GRIS, anchor="lm")
    marco.paste(vista, (0, barra))
    if a_v < 255:
        marco.putalpha(marco.split()[3].point(lambda v: int(v * a_v / 255)))
    layer.alpha_composite(marco, (x0, y0))
    # cursor: viaja del objetivo anterior al actual en [at-0.6, at]; luego clic
    # El viaje usa un resorte multi-destino (track): cada tramo tiene masa y
    # se calma al llegar, y si dos tramos se solapan el cursor no frena en
    # seco entre ellos. track es funcion pura del tiempo (no reinicia nada).
    # paradas: (instante, posicion) — un cambio por tramo y por llegada
    paradas_x, paradas_y = [], []
    px_prev, py_prev = 0.85, 0.92
    for p_ in pasos:
        a_ = p_.get("at", 0)
        paradas_x.append((a_ - 0.6, px_prev))
        paradas_x.append((a_, p_.get("x", .5)))
        paradas_y.append((a_ - 0.6, py_prev))
        paradas_y.append((a_, p_.get("y", .5)))
        px_prev, py_prev = p_.get("x", .5), p_.get("y", .5)
    pos = None
    for p_ in pasos:
        a_ = p_.get("at", 0)
        if t < a_ - 0.6:
            break
        pos = (track(t, paradas_x, 260, 26), track(t, paradas_y, 260, 26), a_, p_)
    if pos:
        px = x0 + (pos[0] * bw - cx_) * z
        py = y0 + barra + (pos[1] * bh - cy_) * z
        pul = onda_clic(d, px, py, t, pos[2])
        cursor(d, px, py, 0.8 * (1 - 0.15 * pul))
        p_ = pos[3]
        if p_.get("texto") and t >= pos[2] + 0.15:
            kt = entra(t, pos[2] + 0.15, "bloque")
            nxt_ = [q.get("at", 0) for q in pasos if q.get("at", 0) > pos[2]]
            fuera = clamp01((t - (nxt_[0] - 1.3)) / 0.4) if nxt_ else 0
            al = int(255 * clamp01(kt * 1.4) * (1 - fuera))
            if al > 0:
                fnt = fuente_que_cabe(ctx.fT, p_["texto"], 44, zx1_ - zx0_ - 80, 800)   # el botón cabe
                tw_ = ctx.tmp.textlength(p_["texto"], font=fnt) + 80
                yb = y0 + barra + bh + 60
                boton_halo(d, W / 2, yb + 46, tw_, 92, p_["texto"], fnt, t, pos[2] + 0.15,
                           alpha=al)
    return capa_salida(layer, t, e["to"])


def sc_rotulo_inferior(ctx, e, t):
    """Rótulo inferior (lower third): nombre + rol sobre panel, anclado a la
    izquierda dentro del title-safe y elevado sobre la banda de UI en 9:16.
    Entra barra → nombre → rol (stagger 0.12 s, entrada ~0.45 s), se QUEDA
    quieto mientras se lee y sale más rápido de lo que entró; el primer y el
    último frame quedan vacíos (no aparece ni se corta de golpe en el NLE).
    Ideal como overlay con alfa: `-o rotulo.mov` (ProRes 4444) o `.webm`.
    Params: `nombre`, `rol?`, `lado?` (izq | der), `at{entra}`.
    Fuente: lower-thirds (iart-ai/lower-thirds-skills, tiktok-video-skills).
    """
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    at = e.get("at", {})
    t_in = at.get("entra", e["from"] + 0.15)
    t_out = e["to"] - 0.4
    if t < t_in:
        return layer
    base = int(min(W, H) * 0.06)
    margen = max(SAFE["left"], int(W * 0.06))
    ancho_max = W - 2 * margen - 70
    tam = base
    while tam > 24:   # fit: un nombre largo se encoge, nunca se sale del panel
        fn, fr_ = ctx.fT(tam, 800), ctx.fX(int(tam * 0.55), 600)
        wn = ctx.tmp.textlength(e.get("nombre", ""), font=fn)
        wr = ctx.tmp.textlength(e.get("rol", ""), font=fr_) if e.get("rol") else 0
        if max(wn, wr) <= ancho_max:
            break
        tam -= 2
    pad = int(tam * 0.55)
    bw = int(max(wn, wr) + 2 * pad + 12)
    bh = int(tam * 1.25 + (tam * 0.55 * 1.5 if e.get("rol") else 0) + pad * 1.2)
    y0 = int(H - SAFE["bottom"] - bh - H * 0.03)
    x0 = margen if e.get("lado", "izq") != "der" else W - margen - bw
    k_panel = ease_out(clamp01((t - t_in) / 0.45)) * (1 - ease_in_out(clamp01((t - t_out - 0.1) / 0.25)))
    k_txt = 1 - clamp01((t - t_out) / 0.15)
    if k_panel <= 0:
        return layer
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle([x0, y0, x0 + max(12, bw * k_panel), y0 + bh], radius=14,
                        fill=PANEL + (232,))
    d.rectangle([x0, y0, x0 + 10, y0 + bh], fill=ACENTO + (255,))
    for txt, fnt, col, dt, yy in ((e.get("nombre", ""), fn, BLANCO, 0.12, y0 + pad * 0.6),
                                  (e.get("rol", ""), fr_, ACENTO, 0.24, y0 + pad * 0.6 + tam * 1.25)):
        if not txt:
            continue
        kr = smoothstep(clamp01((t - t_in - dt) / 0.5)) * k_txt   # barrido parejo (ease_out revelaba media palabra en 2 frames)
        if kr <= 0:
            continue
        # se dibuja sobre una capa del tamaño del cuadro: así `medir_animacion`
        # ve la letra (antes el text() iba a un buffer auxiliar y letra_min=0)
        tw_ = int(ctx.tmp.textlength(txt, font=fnt)) + 4
        th_ = int(fnt.size * 1.4)
        ox, oy = int(x0 + pad + 12), int(yy)
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(img).text((ox, oy), txt, font=fnt, fill=col + (255,))
        # máscara que barre con borde DIFUMINADO (40 px): la letra se revela, no aparece entera
        borde = 40
        x_rev = ox + (tw_ + borde) * kr
        xs = np.arange(W, dtype=np.float32)
        rampa = np.clip((x_rev - xs) / borde, 0, 1)
        a_ = np.asarray(img.split()[3], np.float32) * rampa[None, :]
        # fuera de la franja del texto, alfa 0 (no contaminar el panel)
        a_[:max(0, oy), :] = 0
        a_[min(H, oy + th_):, :] = 0
        a_[:, :max(0, ox)] = 0
        a_[:, min(W, ox + tw_ + borde):] = 0
        img.putalpha(Image.fromarray(a_.astype(np.uint8), "L"))
        layer.alpha_composite(img)
    return layer


def sc_hero(ctx, e, t):
    """Hero de lanzamiento de producto/SaaS (supahero.io + navbar.gallery +
    scrolltide.co + glass.samasante.com + cta.gallery): píldora de navegación
    o anuncio superior, titular cinético con subtítulo, tarjeta Liquid Glass
    con métrica clave y botón CTA con halo pulsante.
    Params: `badge?`, `titulo`, `subtitulo?`, `metrica?`, `etiqueta_metrica?`,
    `cta?`, `at{badge, titulo, card, cta}`."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    at = e.get("at", {})
    x0, y0, x1, y1 = caja_segura()
    ancho_u = x1 - x0
    u = unidad()
    # 1. Píldora de anuncio / navbar superior (navbar.gallery Announcement/Tabs)
    t_b = at.get("badge", e["from"] + 0.15)
    badge_txt = e.get("badge", "NUEVO LANZAMIENTO")
    kb = entra(t, t_b, "elemento")
    yb = y0 + int((y1 - y0) * 0.08)
    if kb > 0 and badge_txt:
        sub, ds = grupo()
        fb = fuente_que_cabe(ctx.fM, badge_txt.upper(), ESCALA["nota"], int(ancho_u * 0.76), 700)
        wb = min(int(ancho_u * 0.94), int(largo(badge_txt.upper(), fb) + 64))
        hb = max(44, int(fb.size * 1.9))
        tarjeta_cristal(ctx, sub, W / 2 - wb / 2, yb - hb / 2, wb, hb, radio=hb // 2, alpha=255)
        tw_b = largo(badge_txt.upper(), fb)
        gap_b = 14
        r_dot = 6
        bloque_w = r_dot * 2 + gap_b + tw_b
        start_x = W / 2 - bloque_w / 2
        ds.ellipse([start_x, yb - r_dot, start_x + r_dot * 2, yb + r_dot], fill=ACENTO + (255,))
        ds.text((start_x + r_dot * 2 + gap_b, yb), badge_txt.upper(), font=fb, fill=BLANCO + (255,), anchor="lm")
        fundir(layer, sub, kb, dy=18)
    # 2. Titular + subtítulo (supahero.io + scrolltide.co Focus Reveal)
    t_t = at.get("titulo", e["from"] + 0.45)
    # el kicker cae en la MISMA altura que en las demas escenas (rotulo_y): un
    # rotulo que salta de altura entre escenas rompe el ritmo
    yt = rotulo_y()
    rotulo(ctx, layer, t, e.get("titulo", "Tu producto en *movimiento*"), t_t, y=yt, tam=ESCALA["rotulo"])
    sub_txt = e.get("subtitulo", "")
    if sub_txt and t >= t_t + 0.2:
        ks = entra(t, t_t + 0.2, "suave")
        als = int(255 * clamp01(ks * 1.4))
        # el subtítulo se PARTE antes de encogerse: encogerlo para que quepa en
        # UNA línea lo dejaba en 18 px (ilegible) para después partirlo en dos.
        fs, lns_s = texto_que_cabe(ctx.fX, sub_txt, ESCALA["secundario"],
                                   int(ancho_u * 0.90), 600, max_lineas=2, minimo=18)
        ys = bajo_rotulo(yt, ESCALA["rotulo"], aire=1.15)
        for li, ln_s in enumerate(lns_s):
            ImageDraw.Draw(layer).text((W / 2, ys + li * int(fs.size * 1.22)), ln_s,
                                       font=fs, fill=GRIS + (als,), anchor="ma")
    # 3. Tarjeta Liquid Glass central con métrica (glass.samasante.com)
    t_c = at.get("card", e["from"] + 1.05)
    kc = entra(t, t_c, "elemento")
    yc = y0 + int((y1 - y0) * 0.56)
    hc = int((y1 - y0) * 0.23)
    wc = min(int(ancho_u * 0.92), 860)
    if kc > 0:
        sub, ds = grupo()
        tarjeta_cristal(ctx, sub, W / 2 - wc / 2, yc - hc / 2, wc, hc, radio=32, alpha=255)
        met = e.get("metrica", "3.4x")
        etq = e.get("etiqueta_metrica", "más conversión en 30 días")
        fm = fuente_que_cabe(ctx.fT, str(met), int(u * 0.080), int(wc * 0.84), 800, minimo=28)
        fe = fuente_que_cabe(ctx.fX, str(etq), ESCALA["secundario"], int(wc * 0.86), 600)
        ds.text((W / 2, yc - hc * 0.14), str(met), font=fm, fill=ACENTO + (255,), anchor="mm")
        ds.text((W / 2, yc + hc * 0.24), str(etq), font=fe, fill=BLANCO + (255,), anchor="mm")
        fundir(layer, sub, kc, dy=26)
    # 4. CTA con anillo de halo pulsante (cta.gallery + scrolltide.co)
    t_cta = at.get("cta", e["from"] + 1.75)
    cta_txt = e.get("cta", "Empieza hoy")
    k_cta = entra(t, t_cta, "elemento")
    if k_cta > 0 and cta_txt:
        sub, ds = grupo()
        y_cta = y0 + int((y1 - y0) * 0.84)
        f_cta = fuente_que_cabe(ctx.fT, cta_txt, ESCALA["dato"], int(ancho_u * 0.72), 800)
        w_cta = min(int(ancho_u - 32), max(280, int(largo(cta_txt, f_cta) + 88)))
        h_cta = max(68, int(f_cta.size * 2.1))
        boton_halo(ds, W / 2, y_cta, w_cta, h_cta, cta_txt, f_cta, t, t_cta)
        fundir(layer, sub, k_cta, dy=20)
    return capa_salida(layer, t, e["to"])


def sc_bento(ctx, e, t):
    """Grilla Bento con iconos 3D táctiles, tarjetas Liquid Glass y cierre
    tipográfico (3dicons.co + glass.samasante.com + scrolltide.co + footer.design).
    Params: `rotulo?`, `items[{icono?, titulo, texto, acento?}]`, `pie?`,
    `at{rotulo, item0..n, pie}`."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    at = e.get("at", {})
    x0, y0, x1, y1 = caja_segura()
    yr = rotulo_y()
    rotulo(ctx, layer, t, e.get("rotulo", "Todo en *una grilla*"), at.get("rotulo", e["from"] + 0.15), y=yr)
    items = (e.get("items") or [
        {"icono": "01", "titulo": "Rápido", "texto": "Render en minutos", "acento": True},
        {"icono": "02", "titulo": "Fiel", "texto": "Tu marca exacta"},
        {"icono": "03", "titulo": "Limpio", "texto": "QA cuadro a cuadro"}
    ])[:4]
    n = len(items)
    top_grid = bajo_rotulo(yr, 44, aire=1.15)
    bot_grid = y1 - ((82 if e.get("pie") else 20) + (46 if e.get("fuente") else 0))
    cols = 1 if (H > W and n <= 3) else 2
    cajas = cuadricula(x0, int(top_grid), x1 - x0, int(bot_grid - top_grid), cols, n)
    fy = flota(t, e["from"] + 1.6, 4, 0.38)
    for i, (it, (cx0, cy0, cw, ch)) in enumerate(zip(items, cajas)):
        t_i = it.get("at", escalonado(at, "item", i, e["from"] + 0.65))
        ki = entra(t, t_i, "elemento")
        if ki <= 0:
            continue
        sub, ds = grupo()
        es_ac = bool(it.get("acento")) or i == 0
        cy0 = cy0 + fy
        # la tarjeta acento late el brillo: el hold del bento no se congela
        br = (1.2 * latido(t, t_i + 0.5, 1.6, 0.08)) if es_ac else 0.85
        tarjeta_cristal(ctx, sub, cx0, cy0, cw, ch, radio=26, alpha=255,
                        tinte=ACENTO if es_ac else PANEL2, brillo=br)
        r_ico = min(38, max(26, int(min(cw, ch) * 0.20)))
        f_ico = ctx.fM(max(24, int(r_ico * 0.78)), 700)
        ico_txt = it.get("icono") or f"{i + 1:02d}"
        tit_i = it.get("titulo", "")
        txt_i = it.get("texto", "")
        if cols == 1 or cw > ch * 1.45:
            ix = cx0 + 28 + r_ico
            iy = cy0 + ch / 2
            insignia_3d(ds, ix, iy, r_ico, ico_txt, f_ico,
                        color=ACENTO if es_ac else PANEL2, t=t - t_i)
            tx0 = ix + r_ico + 26
            tw_max = max(80, cw - (tx0 - cx0) - 24)
            ft = fuente_que_cabe(ctx.fT, tit_i, ESCALA["secundario"], tw_max, 800)
            fx = fuente_que_cabe(ctx.fX, txt_i, ESCALA["nota"], tw_max, 600)
            ds.text((tx0, cy0 + ch * 0.36), tit_i, font=ft, fill=BLANCO + (255,), anchor="lm")
            ds.text((tx0, cy0 + ch * 0.68), txt_i, font=fx, fill=GRIS + (255,), anchor="lm")
        else:
            ix = cx0 + cw / 2
            iy = cy0 + ch * 0.30
            insignia_3d(ds, ix, iy, r_ico, ico_txt, f_ico,
                        color=ACENTO if es_ac else PANEL2, t=t - t_i)
            tw_max = max(80, cw - 36)
            ft = fuente_que_cabe(ctx.fT, tit_i, ESCALA["secundario"], tw_max, 800)
            fx = fuente_que_cabe(ctx.fX, txt_i, ESCALA["nota"], tw_max, 600)
            ds.text((ix, cy0 + ch * 0.64), tit_i, font=ft, fill=BLANCO + (255,), anchor="mm")
            ds.text((ix, cy0 + ch * 0.83), txt_i, font=fx, fill=GRIS + (255,), anchor="mm")
        fundir(layer, sub, ki, dy=22)
    pie_txt = e.get("pie", "")
    t_pie = at.get("pie", e["from"] + 0.8 + n * 0.35)
    if pie_txt and t >= t_pie:
        kp = entra(t, t_pie, "suave")
        alp = int(255 * clamp01(kp * 1.4))
        fp = fuente_que_cabe(ctx.fM, pie_txt.upper(), ESCALA["nota"], x1 - x0 - 20, 700)
        ImageDraw.Draw(layer).text((W / 2, y1 - 24 - (46 if e.get("fuente") else 0)),
                                   pie_txt.upper(), font=fp,
                                   fill=ACENTO + (alp,), anchor="mb")
    if e.get("fuente"):
        pie_fuente(ctx, ImageDraw.Draw(layer), e, t, at.get("fuente", e["from"] + 1.5))
    return capa_salida(layer, t, e["to"])


def sc_buscador(ctx, e, t):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    at = e["at"]
    if e.get("rotulo"):
        rotulo(ctx, layer, t, e["rotulo"], at.get("rotulo", e["from"]), y=rotulo_y())
    zx0, zy0, zx1, zy1 = caja_segura()
    query = e.get("query", "")
    t_query = at.get("query", e["from"] + 0.3)
    k_bar = entra(t, t_query - 0.2, "elemento")
    if k_bar <= 0:
        return capa_salida(layer, t, e["to"])
    
    ancho_max = zx1 - zx0
    wb = min(ancho_max - 30, int(unidad() * 1.25 if W > H else (zx1 - zx0) * 0.92))
    hb = int(unidad() * 0.09 if W > H else 94)
    xb = (W - wb) / 2
    yb = rotulo_y() + (90 if H > W else 70) + flota(t, t_query + 0.8, 4, 0.35)
    
    al_bar = int(255 * clamp01(k_bar * 1.4))
    tarjeta_cristal(ctx, layer, xb, yb, wb, hb, radio=hb // 2, alpha=int(220 * clamp01(k_bar)))
    d.rounded_rectangle([xb, yb, xb + wb, yb + hb], radius=hb // 2,
                        outline=(255, 255, 255, int(60 * clamp01(k_bar))), width=2)
    
    lupa_x = xb + 36
    lupa_y = yb + hb / 2
    r_lupa = int(hb * 0.18)
    d.ellipse([lupa_x - r_lupa, lupa_y - r_lupa, lupa_x + r_lupa, lupa_y + r_lupa],
              outline=ACENTO + (al_bar,), width=3)
    d.line([lupa_x + int(r_lupa * 0.7), lupa_y + int(r_lupa * 0.7),
            lupa_x + int(r_lupa * 1.4), lupa_y + int(r_lupa * 1.4)],
           fill=ACENTO + (al_bar,), width=3)
    
    max_w_q = wb - 120
    tam_q = fuente_que_cabe(ctx.fX, query, int(hb * 0.40), max_w_q, 600, minimo=18).size
    fnt_q = ctx.fX(tam_q, 600)
    query = recorta_para(query, fnt_q, max_w_q, ctx.tmp)
    dur_q = max(0.4, len(query) * 0.045)
    tx_x = xb + 76
    tx_y = yb + (hb - tam_q) / 2 - 2
    n_letras = text_reveal(d, query, fnt_q, tx_x, tx_y, t, t_query, dur_q, BLANCO)
    
    cur_x = tx_x + (ctx.tmp.textlength(query[:n_letras], font=fnt_q) if n_letras else 0)
    if t >= t_query and (t < t_query + dur_q or math.sin(t * 8) > 0):
        d.rectangle([cur_x + 4, tx_y + 2, cur_x + 7, tx_y + tam_q + 2], fill=ACENTO + (al_bar,))
    
    resultados = e.get("resultados", [])
    if resultados:
        y_r0 = yb + hb + 18
        # filas más altas + gap: el resultado secundario se lee y ocupa zona
        # (antes ocup~0.29; panel blanco@22 sobre negro era casi invisible)
        hr_item = int(unidad() * 0.10 if W > H else 100)
        gap_r = 14
        for i, res in enumerate(resultados):
            t_res = escalonado(at, "res", i, t_query + dur_q + 0.2)
            kr = entra(t, t_res, "bloque")
            if kr <= 0:
                continue
            al_r = int(255 * clamp01(kr * 1.4))
            yr = y_r0 + i * (hr_item + gap_r)
            es_acento = res.get("acento", False)
            if es_acento:
                bg_col = ACENTO + (int(110 * clamp01(kr)),)
                borde_col = ACENTO + (int(220 * clamp01(kr)),)
                col_tit = BLANCO + (al_r,)
                col_desc = BLANCO + (int(210 * clamp01(kr)),)
                dot_col = BLANCO + (al_r,)
            else:
                # placa por encima de PANEL2: (38,38,38) sobre negro apenas se
                # lee como tarjeta; sube luminancia + borde
                bg_col = (56, 56, 62, int(245 * clamp01(kr)))
                borde_col = (255, 255, 255, int(72 * clamp01(kr)))
                col_tit = BLANCO + (al_r,)
                col_desc = (200, 200, 200, int(240 * clamp01(kr)))
                dot_col = (210, 210, 210, int(220 * clamp01(kr)))
            d.rounded_rectangle([xb, yr, xb + wb, yr + hr_item], radius=18,
                                fill=bg_col, outline=borde_col, width=2)
            d.ellipse([xb + 24, yr + hr_item / 2 - 6, xb + 36, yr + hr_item / 2 + 6], fill=dot_col)
            
            t_res_txt = res.get("texto", "")
            max_w_t = wb - 80
            fnt_rt = fuente_que_cabe(ctx.fX, t_res_txt, int(hr_item * 0.32), max_w_t, 700, minimo=18)
            t_res_txt = recorta_para(t_res_txt, fnt_rt, max_w_t, ctx.tmp)
            d.text((xb + 50, yr + 16), t_res_txt, font=fnt_rt, fill=col_tit)
            desc = res.get("desc", "")
            if desc and hr_item >= 70:
                fnt_rd = fuente_que_cabe(ctx.fX, desc, ESCALA["nota"], max_w_t, 400, minimo=18)
                desc = recorta_para(desc, fnt_rd, max_w_t, ctx.tmp)
                d.text((xb + 50, yr + hr_item - 34), desc, font=fnt_rd, fill=col_desc)
                
    pie_fuente(ctx, d, e, t, at.get("rotulo", e["from"]) + 2.0)
    return capa_salida(layer, t, e["to"])


def sc_notificacion(ctx, e, t):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    at = e["at"]
    if e.get("rotulo"):
        rotulo(ctx, layer, t, e["rotulo"], at.get("rotulo", e["from"]), y=rotulo_y())
    zx0, zy0, zx1, zy1 = caja_segura()
    items = e.get("items", [])
    if not items:
        return capa_salida(layer, t, e["to"])
    n = len(items)
    ancho_card = min(zx1 - zx0 - 30, int(unidad() * 1.25 if W > H else (zx1 - zx0) * 0.92))
    x0 = (W - ancho_card) / 2
    h_card = int(unidad() * 0.13 if W > H else 140)
    gap = 18
    y_base = rotulo_y() + (90 if H > W else 70) + flota(t, e["from"] + 0.8, 5, 0.32)
    
    LLEGA = 0.8   # cada notificación es un beat que se lee, no una cascada
    for i, it in enumerate(items):
        t_in = at.get(f"item{i}", e["from"] + 0.4 + i * LLEGA)
        k = entra(t, t_in, "bloque")
        if k <= 0:
            continue
        despues = sum(min(1.0, entra(t, at.get(f"item{j}", e["from"] + 0.4 + j * LLEGA), "suave"))
                      for j in range(i + 1, n))
        y_i = y_base + despues * (h_card + gap) + (1 - min(1, k)) * -50 + flota(t, t_in + 0.5, 7, 0.45 + i * 0.08)
        al = int(255 * clamp01(k * 1.4))
        
        tarjeta_cristal(ctx, layer, x0, y_i, ancho_card, h_card, radio=24, alpha=int(220 * clamp01(k)))
        d.rounded_rectangle([x0, y_i, x0 + ancho_card, y_i + h_card], radius=28,
                            outline=(255, 255, 255, int(45 * clamp01(k))), width=2)
        
        app = it.get("app", "App")
        r_ico = int(h_card * 0.28)
        ico_x = x0 + 26
        ico_y = y_i + (h_card - r_ico * 2) / 2
        d.rounded_rectangle([ico_x, ico_y, ico_x + r_ico * 2, ico_y + r_ico * 2], radius=14,
                            fill=ACENTO + (al,))
        ico_char = it.get("icono", app[:1].upper())
        fnt_ico = ctx.fT(int(r_ico * 1.0), 800)
        d.text((ico_x + r_ico, ico_y + r_ico), ico_char, font=fnt_ico, fill=BLANCO + (al,), anchor="mm")
        
        tx_x = ico_x + r_ico * 2 + 20
        # la hora va en la MISMA linea que el titulo (derecha): el ancho del
        # titulo reserva el de la hora REAL. Con una reserva fija (110 px) y la
        # hora a 28 px ("hace 5 min" ~ 140 px) los dos se pisaban.
        hora = it.get("hora", "ahora")
        fnt_h = ctx.fX(ESCALA["nota"], 400)   # antes int(h_card*0.15) = 21 px
        w_hora = ctx.tmp.textlength(hora, font=fnt_h)
        tx_w = max(80, int(x0 + ancho_card - 26 - 20 - w_hora - tx_x))

        # título del item: un "secundario" de la escala. Antes int(h_card*0.22)
        # = 30 px, una cifra que no estaba en la escala.
        fnt_tit = fuente_que_cabe(ctx.fX, it.get("titulo", ""), ESCALA["secundario"], tx_w, 800)
        d.text((tx_x, y_i + 18), it.get("titulo", ""), font=fnt_tit, fill=BLANCO + (al,))

        texto_it = it.get("texto", "")
        max_w_txt = max(60, int(x0 + ancho_card - 26 - tx_x))
        # cuerpo: un "nota" de la escala (28 px). Antes int(h_card*0.17) = 23 px,
        # por debajo del piso legible, y con el auto-fit que lo encogia mas. Se
        # PARTE antes de encoger: la letra se queda, lo que se acorta es el copy.
        fnt_txt, lineas = texto_que_cabe(ctx.fX, texto_it, ESCALA["nota"], max_w_txt,
                                          400, max_lineas=2, minimo=18)
        for li, ln in enumerate(lineas[:2]):
            d.text((tx_x, y_i + 20 + int(h_card * 0.28) + li * int(h_card * 0.24)), ln,
                   font=fnt_txt, fill=GRIS + (int(210 * clamp01(k)),))
        
        # la hora se dibuja al final (derecha de la linea del titulo): su
        # fuente y su ancho ya estan calculados arriba
        d.text((x0 + ancho_card - 26, y_i + 22), hora, font=fnt_h,
               fill=GRIS + (int(160 * clamp01(k)),), anchor="ra")
               
    pie_fuente(ctx, d, e, t, at.get("rotulo", e["from"]) + 2.5)
    return capa_salida(layer, t, e["to"])


def sc_comentario(ctx, e, t):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    at = e["at"]
    if e.get("rotulo"):
        rotulo(ctx, layer, t, e["rotulo"], at.get("rotulo", e["from"]), y=rotulo_y())
    zx0, zy0, zx1, zy1 = caja_segura()
    
    t_card = at.get("card", e["from"] + 0.3)
    kc = entra(t, t_card, "elemento")
    if kc <= 0:
        return capa_salida(layer, t, e["to"])
    al = int(255 * clamp01(kc * 1.4))
    
    wc = min(zx1 - zx0 - 30, int(unidad() * 1.25 if W > H else (zx1 - zx0) * 0.92))
    hc = int(unidad() * 0.50 if W > H else 440)
    xc = (W - wc) / 2
    yc = (zy0 + zy1 - hc) / 2 + 20 + flota(t, t_card + 0.8, 7, 0.45)
    
    tarjeta_cristal(ctx, layer, xc, yc, wc, hc, radio=28, alpha=int(230 * clamp01(kc)))
    d.rounded_rectangle([xc, yc, xc + wc, yc + hc], radius=28,
                        outline=(255, 255, 255, int(50 * clamp01(kc))), width=2)
    
    r_av = 38
    av_x = xc + 36 + r_av
    av_y = yc + 36 + r_av
    d.ellipse([av_x - r_av, av_y - r_av, av_x + r_av, av_y + r_av], fill=ACENTO + (al,))
    ini = e.get("iniciales") or "".join(w[:1].upper() for w in e.get("autor", "User").split()[:2])
    d.text((av_x, av_y), ini, font=ctx.fT(34, 800), fill=BLANCO + (al,), anchor="mm")
    
    nom_x = av_x + r_av + 20
    reserva_der = 230 if e.get("estrellas") else 60
    max_w_nom = max(120, wc - (nom_x - xc) - reserva_der)
    fnt_nom = fuente_que_cabe(ctx.fX, e.get("autor", ""), 34, max_w_nom, 800, minimo=18)
    d.text((nom_x, av_y - 4), e.get("autor", ""), font=fnt_nom, fill=BLANCO + (al,), anchor="ls")
    
    if e.get("verificado", True):
        w_nom = ctx.tmp.textlength(e.get("autor", ""), font=fnt_nom)
        bv_x = nom_x + w_nom + 12
        d.ellipse([bv_x, av_y - 20, bv_x + 18, av_y - 2], fill=ACENTO + (al,))
        d.text((bv_x + 9, av_y - 11), "✓", font=ctx.fX(TAM_CHECK, 800), fill=BLANCO + (al,), anchor="mm")
    
    usr = e.get("usuario", "@cliente")
    d.text((nom_x, av_y + 8), usr, font=ctx.fX(ESCALA["nota"], 400), fill=GRIS + (int(200 * clamp01(kc)),), anchor="la")
    
    if e.get("estrellas"):
        estrellas(layer, xc + wc - 110, av_y, float(e["estrellas"]), 5, tam=26, k=kc)
        
    d.line([xc + 36, av_y + r_av + 20, xc + wc - 36, av_y + r_av + 20],
           fill=(255, 255, 255, int(30 * clamp01(kc))), width=1)
    
    texto = e.get("texto", "")
    t_txt = at.get("texto", t_card + 0.4)
    kt = clamp01((t - t_txt) / 0.5)
    # el cuerpo se PARTE antes de encogerse: antes se encogia para que el
    # parrafo entero quepa en UNA linea (18 px, ilegible) y luego se partia
    # en 4 lineas. Ahora mantiene el tamaño de la escala y se parte.
    fnt_txt, lineas = texto_que_cabe(ctx.fT, texto, int(unidad() * 0.048 if W > H else 38),
                                      wc - 72, 600, max_lineas=4, minimo=18)
    lh = fnt_txt.size * 1.35
    y_linea = av_y + r_av + 42
    for li, ln in enumerate(lineas[:4]):
        draw_seg(d, (xc + 36, y_linea + li * lh), segs(ln), fnt_txt,
                 BLANCO + (int(255 * kt),), ACENTO + (int(255 * kt),))
                 
    likes = str(e.get("likes", "840"))
    t_likes = at.get("likes", t_card + 1.2)
    kl = clamp01((t - t_likes) / 0.5)
    y_fot = yc + hc - 36
    # piso de escala (nota=28): 26 px era justo el LETRA_MIN del QA y se veía
    # justo en el límite en móvil
    d.text((xc + 36, y_fot), f"❤️ {likes} Me gusta",
           font=ctx.fX(ESCALA["nota"], 700),
           fill=ACENTO + (int(255 * kl),), anchor="ls")
    fecha = e.get("fecha", "Reciente")
    d.text((xc + wc - 36, y_fot), fecha, font=ctx.fX(ESCALA["nota"], 400),
           fill=GRIS + (int(180 * kl),), anchor="rs")
           
    pie_fuente(ctx, d, e, t, at.get("rotulo", e["from"]) + 2.5)
    return capa_salida(layer, t, e["to"])


def colores_del_pie(porciones):
    """El color de cada porción: su `color` explícito, ACENTO para la del
    acento (o la primera) y, para el resto, la SERIE de la marca sin el acento,
    en orden (antes cinco RGB a mano que no seguían a la marca)."""
    resto = list(SERIE[1:]) or [GRIS]
    out, j = [], 0
    for i, p in enumerate(porciones):
        c = p.get("color")
        if c is not None:
            out.append(hex_a_rgb(c) if isinstance(c, str) else tuple(c[:3]))
        elif p.get("acento") or i == 0:
            out.append(tuple(ACENTO))
        else:
            out.append(tuple(resto[j % len(resto)])); j += 1
    return out


def centro_del_pie(e):
    """(cifra, etiqueta) del centro del donut: el `centro` declarado, o la
    porción del acento (su % y su etiqueta). "100%" no decía nada."""
    if e.get("centro") is not None:
        return str(e["centro"]), ""
    por = e.get("porciones") or []
    if not por:
        return "", ""
    total = sum(float(p.get("valor", 0)) for p in por) or 1.0
    ac = next((p for p in por if p.get("acento")), por[0])
    return f"{int(float(ac.get('valor', 0)) / total * 100)}%", str(ac.get("etiqueta", ""))


def sc_pie(ctx, e, t):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    at = e["at"]
    if e.get("titulo"):
        rotulo(ctx, layer, t, e["titulo"], at.get("rotulo", e["from"]), y=rotulo_y())
    zx0, zy0, zx1, zy1 = caja_segura()
    porciones = e.get("porciones", [])
    if not porciones:
        return capa_salida(layer, t, e["to"])
    
    total = sum(float(p.get("valor", 0)) for p in porciones) or 1.0
    t_pie = at.get("pie", e["from"] + 0.3)
    k_pie = entra(t, t_pie, "elemento")
    if k_pie <= 0:
        return capa_salida(layer, t, e["to"])
    
    horizontal = W > H
    r = int(unidad() * 0.28 if horizontal else unidad() * 0.24)
    if horizontal:
        fnt_et_test = ctx.fX(int(unidad() * 0.035), 600)
        max_et_w = max((ctx.tmp.textlength(p.get("etiqueta", ""), font=fnt_et_test) for p in porciones), default=100)
        w_legend = min(int((zx1 - zx0) * 0.45), int(22 + 14 + max_et_w + 30 + 80))
        gap_col = 60
        w_total = 2 * r + gap_col + w_legend
        col1_left = (W - w_total) / 2
        cx = col1_left + r
        cy = (zy0 + zy1) / 2 + 25
        ley_x = col1_left + 2 * r + gap_col
        pct_x = ley_x + w_legend
        ley_y = cy - r + 20
        gap_ley = int(unidad() * 0.08)
    else:
        cx = W / 2
        cy = rotulo_y() + r + 50 + flota(t, t_pie + 0.8, 7, 0.45)
        w_legend = min(zx1 - zx0 - 40, int(W * 0.82))
        ley_x = (W - w_legend) / 2
        pct_x = ley_x + w_legend
        ley_y = cy + r + 40
        gap_ley = 54
    
    pie_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dp = ImageDraw.Draw(pie_layer)
    
    ang_actual = -90.0 + (t - t_pie) * 4.0 if t > t_pie else -90.0
    colores = colores_del_pie(porciones)   # una sola fuente para el donut y la leyenda
    
    for i, p in enumerate(porciones):
        t_p = at.get(f"p{i}", t_pie + i * 0.25)
        kp = entra(t, t_p, "suave")
        if kp <= 0:
            continue
        frac = float(p.get("valor", 0)) / total
        # el barrido va por TIEMPO (0.55 s), no atado al resorte: con el
        # resorte la porcion giraba ~35 grados por frame y eso se lee como un
        # pop (medido: 4 pops en el donut horizontal). Es el mismo criterio
        # que la elipse del `callout` (0.9 s para 360 grados).
        barrido = 360.0 * frac * clamp01((t - t_p) / 0.55)
        ang_fin = ang_actual + barrido
        
        col = colores[i]
        al_sec = int(255 * clamp01(kp * 1.4))
        col_rgba = col[:3] + (al_sec,)
        
        if ang_fin > ang_actual:
            dp.pieslice([cx - r, cy - r, cx + r, cy + r], start=ang_actual, end=ang_fin, fill=col_rgba)
        ang_actual += 360.0 * frac
    
    r_in = int(r * 0.58)
    dp.ellipse([cx - r_in, cy - r_in, cx + r_in, cy + r_in], fill=(12, 12, 14, 255))
    dp.ellipse([cx - r_in, cy - r_in, cx + r_in, cy + r_in], outline=(255, 255, 255, 40), width=2)
    
    centro_txt, centro_etq = centro_del_pie(e)
    fnt_c = fuente_que_cabe(ctx.fT, centro_txt, int(r_in * 0.65), r_in * 1.5, 800)
    # el centro late en el hold: el donut ya no se mueve tras el barrido
    pulso_c = latido(t, t_pie + 1.2, 1.7, 0.07)
    al_c = min(255, int(255 * clamp01(k_pie * 1.4) * pulso_c))
    dy_c = -r_in * 0.12 if centro_etq else 0
    dp.text((cx, cy + dy_c), centro_txt, font=fnt_c, fill=BLANCO + (al_c,), anchor="mm")
    if centro_etq:   # la etiqueta de la porción del acento, chica, bajo la cifra
        w_etq = r_in * 1.4
        fnt_e = fuente_que_cabe(ctx.fX, centro_etq, int(r_in * 0.16), w_etq, 600, minimo=18)
        dp.text((cx, cy + dy_c + fnt_c.size * 0.42), recorta_para(centro_etq, fnt_e, w_etq, ctx.tmp),
                font=fnt_e, fill=GRIS + (al_c,), anchor="ma")
    
    layer.alpha_composite(pie_layer)
    
    for i, p in enumerate(porciones):
        t_p = at.get(f"p{i}", t_pie + i * 0.25)
        kp = entra(t, t_p, "suave")
        if kp <= 0:
            continue
        es_ac = bool(p.get("acento")) or i == 0
        col = colores[i]
        yi = ley_y + i * gap_ley
        pulso_l = latido(t, t_p + 0.6, 1.6, 0.08) if es_ac else 1.0
        al_l = min(255, int(255 * clamp01(kp * 1.4) * pulso_l))
        
        d.rounded_rectangle([ley_x, yi, ley_x + 22, yi + 22], radius=6, fill=col[:3] + (al_l,))
        etq = p.get("etiqueta", "")
        fnt_et = ctx.fX(int(unidad() * 0.035 if horizontal else 30), 600)
        
        pct_txt = f"{int(p.get('valor', 0) / total * 100)}%"
        w_pct = ctx.tmp.textlength(pct_txt, font=fnt_et)
        max_w_et = (pct_x - w_pct - 24) - (ley_x + 36)
        if ctx.tmp.textlength(etq, font=fnt_et) > max_w_et:
            fnt_et = fuente_que_cabe(ctx.fX, etq, fnt_et.size, max_w_et, 600, minimo=18)
            etq = recorta_para(etq, fnt_et, max_w_et, ctx.tmp)
                
        d.text((ley_x + 36, yi - 2), etq, font=fnt_et, fill=BLANCO + (al_l,))
        d.text((pct_x, yi - 2), pct_txt, font=fnt_et, fill=ACENTO + (al_l,), anchor="ra")
               
    pie_fuente(ctx, d, e, t, at.get("rotulo", e["from"]) + 2.5)
    return capa_salida(layer, t, e["to"])


def sc_orbita(ctx, e, t):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    at = e["at"]
    zx0, zy0, zx1, zy1 = caja_segura()
    
    cx = W / 2
    cy = (zy0 + zy1) / 2 + flota(t, e["from"] + 0.5, 6, 0.35)
    
    t_in = at.get("titulo", e["from"] + 0.4)
    k = entra(t, t_in, "elemento")
    al = int(255 * clamp01(k * 1.4))
    
    r_core = min(int((zx1 - zx0) * 0.22), int(unidad() * 0.18))
    # pulso = latido DRY (antes seno suelto 3.5 Hz: nervioso vs el resto del catálogo)
    pulso = latido(t, e["from"], 1.6, 0.12)
    resplandor(layer, (cx - r_core, cy - r_core, cx + r_core, cy + r_core), ACENTO,
               max(1, int(r_core * 0.45)), alfa=int(70 * pulso))
    
    n_part = 18
    r_orb = min(int((zx1 - zx0) * 0.38), int(unidad() * 0.28))
    inclinaciones = [0.35, -0.40, 0.85]
    velocidades = [1.2, -0.9, 1.5]
    
    for ring_i, (inc, vel) in enumerate(zip(inclinaciones, velocidades)):
        for p_i in range(n_part):
            theta = t * vel + p_i * (2 * math.pi / n_part)
            px = r_orb * math.cos(theta)
            py = r_orb * math.sin(theta) * inc
            z = math.sin(theta)
            scale_z = 0.7 + 0.5 * (z + 1) / 2
            
            x_screen = int(cx + px)
            y_screen = int(cy + py)
            rad_p = max(2, int(6 * scale_z))
            al_p = int((120 + 135 * (z + 1) / 2) * clamp01(k))
            col_p = ACENTO if (ring_i + p_i) % 3 == 0 else BLANCO
            d.ellipse([x_screen - rad_p, y_screen - rad_p, x_screen + rad_p, y_screen + rad_p],
                      fill=col_p + (al_p,))
                      
    kicker = e.get("kicker", "")
    if kicker:
        tk = at.get("kicker", e["from"] + 0.2)
        kk = entra(t, tk, "bloque")
        if kk > 0:
            fnt_k = ctx.fM(int(unidad() * 0.035 if W > H else 28), 700)
            d.text((cx, cy - r_orb - 50), kicker.upper(), font=fnt_k,
                   fill=ACENTO + (int(255 * clamp01(kk * 1.4)),), anchor="mm")
                   
    titulo = e.get("titulo", "")
    if titulo and k > 0:
        # el titulo se PARTE antes de encogerse (ver sc_comentario)
        fnt_tit, lineas = texto_que_cabe(ctx.fT, titulo, int(unidad() * 0.08 if W > H else 72),
                                          zx1 - zx0 - 40, 800, max_lineas=3, minimo=18)
        lh = fnt_tit.size * 1.25
        y_tit0 = cy - (len(lineas) * lh) / 2
        for li, ln in enumerate(lineas):
            draw_seg(d, (cx, y_tit0 + li * lh), segs(ln), fnt_tit,
                     BLANCO + (al,), ACENTO + (al,), anchor="ma")
                     
    subtitulo = e.get("subtitulo", "")
    if subtitulo:
        ts = at.get("subtitulo", t_in + 0.8)
        ks = entra(t, ts, "bloque")
        if ks > 0:
            fnt_sub = fuente_que_cabe(ctx.fX, subtitulo, int(unidad() * 0.04 if W > H else 34), zx1 - zx0 - 60, 400)
            # subtítulo más claro: GRIS@220 sobre negro perdía jerarquía
            d.text((cx, cy + r_orb + 50), subtitulo, font=fnt_sub,
                   fill=(200, 200, 200, int(240 * clamp01(ks * 1.4))), anchor="mm")
                   
    return capa_salida(layer, t, e["to"])


def sc_audiowave(ctx, e, t):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    at = e["at"]
    if e.get("rotulo"):
        rotulo(ctx, layer, t, e["rotulo"], at.get("rotulo", e["from"]), y=rotulo_y())
    zx0, zy0, zx1, zy1 = caja_segura()
    
    t_card = at.get("tarjeta", e["from"] + 0.3)
    kc = entra(t, t_card, "elemento")
    if kc <= 0:
        return capa_salida(layer, t, e["to"])
    al = int(255 * clamp01(kc * 1.4))
    
    wc = min(zx1 - zx0 - 30, int(unidad() * 1.25 if W > H else (zx1 - zx0) * 0.92))
    hc = int(unidad() * 0.48 if W > H else 420)
    xc = (W - wc) / 2
    yc = (zy0 + zy1 - hc) / 2 + 20 + flota(t, t_card + 0.8, 7, 0.45)
    
    tarjeta_cristal(ctx, layer, xc, yc, wc, hc, radio=28, alpha=int(230 * clamp01(kc)))
    d.rounded_rectangle([xc, yc, xc + wc, yc + hc], radius=28,
                        outline=(255, 255, 255, int(45 * clamp01(kc))), width=2)
                        
    # play late: el hold del wave ya mueve barras; el botón ancla la lectura
    pulso_p = latido(t, t_card + 0.5, 1.5, 0.10)
    r_play = 24 * pulso_p
    px = xc + 36 + 24
    py = yc + 36 + 24
    d.ellipse([px - r_play, py - r_play, px + r_play, py + r_play],
              fill=ACENTO + (min(255, int(al * pulso_p)),))
    d.polygon([(px - 6, py - 10), (px - 6, py + 10), (px + 10, py)], fill=BLANCO + (al,))
    
    hab = e.get("hablante", "Audio seguro")
    arch = e.get("archivo", "grabacion.wav")
    est = e.get("estado", "REC ● 00:14")
    fnt_est = ctx.fM(ESCALA["nota"], 700)
    w_est = ctx.tmp.textlength(est, font=fnt_est)
    
    max_w_header = (xc + wc - 36 - w_est - 24) - (px + r_play + 18)
    fnt_hab = fuente_que_cabe(ctx.fX, hab, int(unidad() * 0.028 if W > H else 30), max_w_header, 700, minimo=18)
    hab = recorta_para(hab, fnt_hab, max_w_header, ctx.tmp)
    d.text((px + r_play + 18, py - 6), hab, font=fnt_hab, fill=BLANCO + (al,), anchor="ls")

    # el nombre del archivo es un "nota" de la escala (28 px): antes 22 px fijo,
    # por debajo del piso legible (y con piso de auto-fit 12, que rompia el piso
    # global de 18). Tamaño FIJO + recorte con …: un nombre de archivo largo se
    # corta ("narracion_sinteti…"), no se vuelve ilegible.
    fnt_arch = ctx.fM(ESCALA["nota"], 400)
    arch = recorta_para(arch, fnt_arch, max_w_header, ctx.tmp)
    d.text((px + r_play + 18, py + 8), arch, font=fnt_arch, fill=GRIS + (int(180 * clamp01(kc)),), anchor="la")
    d.text((xc + wc - 36, py), est, font=fnt_est, fill=ACENTO + (al,), anchor="rm")
    
    d.line([xc + 36, py + r_play + 22, xc + wc - 36, py + r_play + 22],
           fill=(255, 255, 255, int(25 * clamp01(kc))), width=1)
           
    t_onda = at.get("onda", t_card + 0.4)
    ko = clamp01((t - t_onda) / 0.5)
    n_bars = 28 if W > H else 24
    w_wave = wc - 72
    bw = max(4, int(w_wave / (n_bars * 1.5)))
    gap_b = int((w_wave - n_bars * bw) / max(1, n_bars - 1))
    
    cy_wave = yc + hc * 0.58
    max_h_bar = int(hc * 0.28)
    
    for bi in range(n_bars):
        arm1 = math.sin(t * 7.0 + bi * 0.35)
        arm2 = math.cos(t * 4.2 - bi * 0.25)
        arm3 = math.sin(t * 11.5 + bi * 0.6)
        amp = clamp01(abs(arm1 * 0.5 + arm2 * 0.35 + arm3 * 0.15))
        hb_bar = max(6, int(max_h_bar * amp * ko))
        
        bx = xc + 36 + bi * (bw + gap_b)
        by0 = cy_wave - hb_bar / 2
        by1 = cy_wave + hb_bar / 2
        col_bar = ACENTO if (bi % 4 == 0) else BLANCO
        al_bar = int((180 + 75 * amp) * clamp01(ko))
        d.rounded_rectangle([bx, by0, bx + bw, by1], radius=bw // 2,
                            fill=col_bar + (al_bar,))
                            
    prog_y = cy_wave + max_h_bar / 2 + 22
    p_frac = prog(t, t_onda, e["to"] - 0.4)
    d.rounded_rectangle([xc + 36, prog_y, xc + wc - 36, prog_y + 6], radius=3,
                        fill=(255, 255, 255, int(40 * clamp01(kc))))
    if p_frac > 0:
        d.rounded_rectangle([xc + 36, prog_y, xc + 36 + int((wc - 72) * p_frac), prog_y + 6], radius=3,
                            fill=ACENTO + (al,))
                            
    trans = e.get("transcripcion", "")
    if trans:
        t_tr = at.get("texto", t_onda + 0.6)
        dur_tr = max(0.5, len(trans) * 0.04)
        # la transcripcion es un `nota` de la escala (28): a 26 nacia justo
        # en el piso legible y la rubrica penalizaba la pieza por diseno
        fnt_tr = fuente_que_cabe(ctx.fX, trans, ESCALA["nota"], wc - 72, 400)
        text_reveal(d, trans, fnt_tr, xc + 36, prog_y + 18, t, t_tr, dur_tr, GRIS)
        
    return capa_salida(layer, t, e["to"])


def sc_callout(ctx, e, t):
    """Resalte sobre el dato clave: elipse que se dibuja + etiqueta.

    "Mira este 60 %". Params: `titulo?`, `captura?` (imagen a resaltar),
    `objeto{x, y, r}` (fracciones de la CAPTURA: centro y radio relativo),
    `etiqueta`, `detalle?`, `fuente?`, `at{rotulo, circulo, etiqueta}`.

    Sin `captura` la elipse flota sobre el fondo (sirve para señalar un titulo
    o una cifra de la propia escena). Con `captura` señala un punto de ella.
    El texto va sobre una placa oscura: blanco sobre captura clara no se lee.

    DRY: `elipse_se_dibuja` (el barrido), `imagen_ajustada`, `placa_texto`,
    `rotulo`, `pie_fuente`."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    at = e.get("at", {})
    zx0, zy0, zx1, zy1 = caja_segura()
    # 1. la captura va DEBAJO (es lo que se resalta)
    if e.get("captura"):
        cap = imagen_ajustada(e["captura"], int(zx1 - zx0), int(zy1 - zy0))
        if cap is not None:
            layer.alpha_composite(cap, (int(zx0), int(zy0)))
    obj = e.get("objeto") or {}
    # 2. el punto resaltado: relativo a la captura si la hay, al lienzo si no
    if e.get("captura"):
        cx = zx0 + (zx1 - zx0) * float(obj.get("x", 0.5))
        cy = zy0 + (zy1 - zy0) * float(obj.get("y", 0.5))
        rx = (zx1 - zx0) * float(obj.get("r", 0.26)) / 2
    else:
        cx = W * float(obj.get("x", 0.5))
        cy = H * float(obj.get("y", 0.5))
        rx = W * float(obj.get("r", 0.26)) / 2
    ry = rx * 0.62                      # elipse tumbada: el dato suele ser horizontal
    # 3. el rotulo, ENCIMA de todo y con placa (si hay captura debajo)
    if e.get("titulo"):
        t_r = at.get("rotulo", e["from"])
        k_r = entra(t, t_r, "suave")
        if k_r > 0:
            # el enfasis (*...*) se dibuja con los segmentos del motor: el texto
            # literal con asteriscos seria un bug
            sg = segs(e["titulo"])
            fr = ctx.fX(ESCALA["rotulo"], 700)
            ancho = (zx1 - zx0) - 20
            tw = seg_width(sg, fr)
            dos_lineas = seg_width(sg, ctx.fX(TAM_MIN_ROTULO, 700)) > ancho
            y_r = rotulo_y() - 14
            al_r = int(255 * clamp01(k_r * 1.4))
            if e.get("captura"):
                # la placa mide el texto REAL (rotulo lo encoge si no cabe)
                w_pl = min(tw, ancho)
                x_pl = W / 2 - w_pl / 2
                alto_pl = ESCALA["rotulo"] * (2.1 if dos_lineas else 1.25)
                # la placa entra con RAMPA (0.3 s), no con el resorte: es un
                # bloque grande y oscuro, y con el resorte subia de golpe
                # (medido: 2 pops en el callout, uno por cada placa)
                placa_texto(d, x_pl - 16, y_r - 8, x_pl + w_pl + 16, y_r + alto_pl,
                            alpha=int(175 * prog(t, t_r, t_r + 0.3, smoothstep)))
            yy_r = y_r + (1 - min(1, k_r)) * ELEV
            for i, ln in enumerate(partir_segs(sg, fr, ancho)):
                draw_seg(d, (W / 2, yy_r + i * ESCALA["rotulo"] * 1.2), ln, fr,
                         BLANCO + (al_r,), ACENTO + (al_r,), anchor="ma")
    # 4. la elipse que se dibuja + el punto exacto
    t_c = at.get("circulo", e["from"] + 0.35)
    k_c = entra(t, t_c, "elemento")
    if k_c > 0:
        elipse_se_dibuja(d, cx, cy, rx, ry, t, t_c, 0.9, ACENTO, 4)
        d.ellipse([cx - 7, cy - 7, cx + 7, cy + 7], fill=ACENTO + (int(220 * k_c),))
    # 5. la etiqueta: DEBAJO de la elipse, centrada y con placa
    etiqueta = e.get("etiqueta", "")
    if etiqueta:
        t_e = at.get("etiqueta", t_c + 0.35)
        k_e = entra(t, t_e, "suave")
        if k_e > 0:
            fnt = fuente_que_cabe(ctx.fT, etiqueta, ESCALA["dato"], zx1 - zx0 - 80, 800)
            sg_e = segs(etiqueta)
            tw = seg_width(sg_e, fnt)
            ex = min(max(cx - tw / 2, zx0 + 10), zx1 - tw - 10)
            ey = min(max(cy + ry + 52, zy0 + 10), zy1 - 40)
            al = int(255 * k_e)
            fd = None
            if e.get("detalle"):
                fd = fuente_que_cabe(ctx.fX, e["detalle"], ESCALA["nota"], zx1 - zx0 - 80, 400)
            alto_placa = ESCALA["dato"] + (50 if fd else 0) + 26
            if e.get("captura"):
                # la placa entra CON el texto, con rampa (no de golpe): ver la
                # placa del rotulo
                placa_texto(d, ex - 14, ey - 14, ex + tw + 14, ey + alto_placa - 14,
                            alpha=int(175 * prog(t, t_e, t_e + 0.3, smoothstep)))
            draw_seg(d, (ex, ey), sg_e, fnt, BLANCO + (al,), ACENTO + (al,), anchor="lm")
            if fd:
                d.text((ex, ey + 46), e["detalle"], font=fd, fill=GRIS + (al,), anchor="lm")
            # el conector baja de la elipse a la etiqueta
            d.line([(cx, cy + ry + 4), (cx, ey - 12)], fill=ACENTO + (int(120 * al),), width=2)
    if e.get("fuente"):
        pie_fuente(ctx, d, e, t, at.get("fuente", e["from"] + 1.2))
    return capa_salida(layer, t, e["to"])


def sc_index(ctx, e, t):
    """Indice de contenidos: lo que vamos a ver, con el paso activo resaltado.

    "Lo que vamos a ver". Params: `titulo?`, `items[{texto, activo?}]`,
    `at{rotulo, item0..n}`. Cada item entra escalonado (stagger) y el
    activo lleva el acento; al terminar, todos quedan atenuados salvo el
    ultimo que searrho.
    DRY: `cuenta_up` (el numero), `linewrap`, `rotulo`."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    at = e.get("at", {})
    if e.get("titulo"):
        rotulo(ctx, layer, t, e["titulo"], at.get("rotulo", e["from"]), y=rotulo_y())
    items = e.get("items") or []
    if not items:
        return capa_salida(layer, t, e["to"])
    zx0, zy0, zx1, zy1 = caja_segura()
    n = len(items)
    top = bajo_rotulo(rotulo_y(), ESCALA["rotulo"], aire=1.15)
    alto = zy1 - top - (60 if e.get("fuente") else 20)
    fila_h = min(int(alto / max(1, n)), 150)
    y0 = top + max(0, (alto - fila_h * n) // 2)
    # el bloque entero flota en el hold: el latido solo de alfa no alcanza
    # el umbral de densidad (medido dens 0.45 < banda 0.5)
    fy = flota(t, e["from"] + 1.4, 5, 0.42)
    for i, it in enumerate(items):
        t_i = escalonado(at, "item", i, e["from"] + 0.3)
        k = entra(t, t_i, "elemento")
        if k <= 0:
            continue
        texto = str(it.get("texto", ""))
        activo = bool(it.get("activo")) or (i == n - 1 and not any(
            it2.get("activo") for it2 in items))
        fnt = fuente_que_cabe(ctx.fX, texto, ESCALA["secundario"], zx1 - zx0 - 120, 600)
        y = y0 + i * fila_h + fy
        num = cuenta_up(1, i + 1, t, t_i, 0.4)
        al = int(255 * clamp01(k * 1.4))
        # inactivo: gris más claro (antes ~GRIS*0.85 sobre negro perdía contraste
        # en móvil); activo: acento con latido para no morir en el hold
        pulso = latido(t, t_i, 1.5, 0.10) if activo else 1.0
        if activo:
            col = ACENTO + (min(255, int(al * pulso)),)
        else:
            col = (168, 168, 168, int(al * 0.92))
        # el numero en su circulo (primitiva comun): el inactivo va en
        # blanco atenuado sobre gris, no gris sobre gris (no se leia).
        # El radio del badge es FIJO (si late, fuente_que_cabe baja la letra
        # bajo LETRA_MIN=26). El latido va al alfa y al subrayado.
        radio_n = max(22, min(28, int(fila_h * 0.24)))
        circulo_numero(d, zx0 + radio_n, y, radio_n, num,
                       ACENTO if activo else (60, 60, 60, 255), BLANCO, ctx,
                       alpha=min(255, int(al * pulso)) if activo else al)
        x_texto = zx0 + 2 * radio_n + 20
        d.text((x_texto, y), texto, font=fnt, fill=col, anchor="lm")
        if activo:
            d.line([(x_texto, y + 22), (x_texto + ctx.tmp.textlength(texto, font=fnt),
                                     y + 22)],
                   fill=ACENTO + (min(255, int(160 * al / 255 * pulso)),),
                   width=max(2, int(2 * pulso)))

    if e.get("fuente"):
        pie_fuente(ctx, d, e, t, at.get("fuente", e["from"] + 1.5))
    return capa_salida(layer, t, e["to"])


def sc_orbOpen(ctx, e, t):
    """Apertura de capitulo: esfera de particulas que se forma + titular.

    "Empezamos". Params: `titulo`, `subtitulo?`, `figura?` (`esfera`, `chat`
    o `robot`), `at{titulo, subtitulo}`.
    Las particulas NACEN dispersas y CONVERGEN a una esfera: es lo contrario
    que `orbita` (donde orbitan). Determinista: semilla fija.
    DRY: `particulas` (la semilla determinista), `titular` (el gesto de la
    casa), `rotulo`."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    at = e.get("at", {})
    zx0, zy0, zx1, zy1 = caja_segura()
    cx = W / 2
    cy = H * 0.38
    r = int(unidad() * 0.19)
    t_s = e["from"] + 0.1
    k_s = entra(t, t_s, "bloque")
    if k_s > 0:
        # las particulas convergen: nacen en un anillo y caen al nucleo.
        # El anillo de nacimiento NO puede salirse de la zona segura (si no,
        # la escena entera se encoge paracalerlo dentro).
        rng = random.Random(7)
        r_max = (zx1 - zx0) / 2 * 0.92
        figura = str(e.get("figura", "esfera"))
        for _ in range(90):
            ang = rng.uniform(0, 6.283)
            r0 = min(r * rng.uniform(2.0, 3.0), r_max)
            rr = r0 + (r - r0) * k_s
            a = ang + (1 - k_s) * 1.6
            if figura == "chat":
                # convergen al contorno de una burbuja (cuadrado redondeado)
                u = math.cos(a) * rr / r
                v = math.sin(a) * rr / r
                x = cx + max(-1, min(1, u * 1.7)) * r
                y = cy + max(-1, min(1, v * 1.7)) * r * 0.72
            elif figura == "robot":
                x = cx + max(-1, min(1, math.cos(a) * 1.5)) * r
                y = cy + max(-1, min(1, math.sin(a) * 1.5)) * r * 0.8
            else:
                x = cx + rr * math.cos(a)
                y = cy + rr * math.sin(a) * 0.72
            sz = max(2, int(rng.uniform(3, 7) * k_s))
            al = int(235 * clamp01(k_s * 1.5))
            d.ellipse([x - sz, y - sz, x + sz, y + sz], fill=ACENTO + (al,))
        # el nucleo: un halo gaussiano suave
        rr = int(r * 0.62)
        resplandor(layer, (cx - rr, cy - rr, cx + rr, cy + rr), ACENTO,
                   max(6, int(r * 0.22)), alfa=int(90 * k_s))
        if figura == "robot":
            rr2 = int(r * 0.5)
            d.rounded_rectangle([cx - rr2, cy - rr2, cx + rr2, cy + rr2],
                                radius=int(rr2 * 0.34), fill=BLANCO + (int(200 * k_s),))
            for ex_ in (-rr2 * 0.36, rr2 * 0.36):
                d.ellipse([cx + ex_ - 9, cy - 12, cx + ex_ + 9, cy + 6],
                          fill=ACENTO + (int(220 * k_s),))
        elif figura == "chat":
            rr2 = int(r * 0.5)
            d.rounded_rectangle([cx - rr2, cy - rr2 * 0.8, cx + rr2, cy + rr2 * 0.8],
                                radius=int(rr2 * 0.26), outline=BLANCO + (int(210 * k_s),), width=5)
            d.polygon([(cx - rr2 * 0.5, cy + rr2 * 0.8), (cx - rr2 * 0.18, cy + rr2 * 0.8),
                       (cx - rr2 * 0.34, cy + rr2 * 1.25)], fill=BLANCO + (int(210 * k_s),))
        else:
            d.ellipse([cx - rr * 0.42, cy - rr * 0.42, cx + rr * 0.42, cy + rr * 0.42],
                      fill=BLANCO + (int(200 * k_s),))
    t_t = at.get("titulo", e["from"] + 0.7)
    lineas = str(e.get("titulo", "")).split("\n") if e.get("titulo") else []
    # `titular` ancla por el BORDE SUPERIOR de la primera linea: el subtitulo
    # va por debajo del titular, no a una distancia fija de la esfera
    y_tit = cy + r + 60
    if lineas:
        titular(ctx, layer, t, lineas, [t_t], tam=ESCALA["titular"], cy=y_tit)
    if e.get("subtitulo"):
        t_sb = at.get("subtitulo", t_t + 0.35)
        k_sb = entra(t, t_sb, "suave")
        if k_sb > 0:
            fs = fuente_que_cabe(ctx.fX, e["subtitulo"], ESCALA["secundario"], zx1 - zx0 - 60, 600)
            y_sb = y_tit + ESCALA["titular"] + 34
            d.text((cx, y_sb), e["subtitulo"], font=fs,
                   fill=GRIS + (int(255 * clamp01(k_sb * 1.4)),), anchor="ma")
    return capa_salida(layer, t, e["to"])


SCENES={"apertura":sc_apertura,"canales":sc_canales,"medianoche":sc_medianoche,
        "chat":sc_chat,"leads":sc_leads,"handoff":sc_handoff,"pago":sc_pago,
        "listo":sc_listo,"pildoras":sc_pildoras,"hoy":sc_hoy,"recupera":sc_recupera,
        "remate":sc_remate,"final":sc_final,
        # Catálogo unificado (ver references/scene-patterns-from-internet.md)
        "bars":sc_bars,"gauge":sc_gauge,"ranking":sc_ranking,"stats":sc_stats,
        "timeline":sc_timeline,"quote":sc_quote,"versus":sc_versus,"confetti":sc_confetti,
        # Ronda 2: reactvideoeditor/remotion-templates (81 templates MIT)
        "typewriter":sc_typewriter,"kenburns":sc_kenburns,"pasos":sc_pasos,
        # Ronda 12: la frase cinetica (el copy que se lee palabra a palabra)
        "frase":sc_frase,
        # Ronda 12: el acta de lo confirmado (el panel de casillas del reel)
        "constancia":sc_constancia,
        # Ronda 13: la cadena de estados (los nodos unidos del reel)
        "cadena":sc_cadena,
        # Ronda 14: el cartel (el panel con el icono grande y la afirmacion)
        "cartel":sc_cartel,
        # Ronda 15: el camino (la linea de luz y las estaciones que enciende)
        "camino":sc_camino,
        # Ronda 16: el lema con su linea de luz debajo (la linea es la base)
        "subrayado":sc_subrayado,
        # Ronda 3: iart-ai/motion-skills (MIT)
        "countdown":sc_countdown,"oferta":sc_oferta,"demo":sc_demo,
        "rotulo_inferior":sc_rotulo_inferior,
        # Ronda 6: indice, resalte y apertura de particulas (futuras del catalogo)
        "index":sc_index,"callout":sc_callout,"orbOpen":sc_orbOpen,
        # Ronda 4: UI/Hero/Bento/Glass/3D-Icons (supahero, scrolltide, glass.samasante, 3dicons, cta.gallery, footer.design)
        "hero":sc_hero,"bento":sc_bento,
        # Ronda 5: Interactivos / Métricas / Audio / Social
        "buscador":sc_buscador,"notificacion":sc_notificacion,"comentario":sc_comentario,
        "pie":sc_pie,"orbita":sc_orbita,"audiowave":sc_audiowave}

# Escenas cuya composición está verificada también en horizontal (W > H).
# El resto se diseñó para 9:16: en 16:9 se solapan (verificado en frames).
# ================= MAIN =================
# hex_a_rgb vive en _comun (unica fuente; DRY). Reusar aquí:
from _comun import hex_a_rgb, info, leer_json  # noqa: E402,F401  # sys.path ya apunta a ffmpeg_tools

def _instalar_tokens(c):
    """Vuelca un juego de tokens de color en los globales del motor.

    ÚNICA puerta: la usan tanto el pack de marca como la paleta del catálogo,
    para que los dos caminos instalen exactamente los mismos globals.
    """
    global ACENTO, ACENTO_OSC, NEGRO, BLANCO, GRIS, SERIE, EXITO, AVISO
    ACENTO, ACENTO_OSC, NEGRO, BLANCO, GRIS = (c["acento"], c["acento_oscuro"],
                                               c["negro"], c["blanco"], c["gris"])
    # categoría y estado: los declarados (pack) mandan; si no, del acento
    est=tokens_de_estado(ACENTO,NEGRO)
    SERIE=[tuple(x) for x in (c.get("serie") or est["serie"])]
    EXITO=tuple(c.get("exito") or est["exito"]); AVISO=tuple(c.get("aviso") or est["aviso"])


def aplicar_paleta(nombre):
    """Instala una paleta del catálogo de modo libre (references/paleta.md).

    El pack de marca SIEMPRE gana: si el usuario nombró una marca, sus
    colores mandan y esta función no se llama. Sin marca, la paleta la elige
    el agente según el brief (teoría del color) y se declara en el plan
    ("paleta": "menta") o con --paleta.
    """
    from _comun import info_paleta, paleta_libre
    _instalar_tokens(paleta_libre(nombre))
    _info = info_paleta(nombre)
    _detalle = (f" ({_info['esquema']}, {_info['tono']})" if _info else "")
    print(f"paleta '{nombre}'{_detalle}: acento #%02X%02X%02X" % ACENTO, flush=True)


def aplicar_brand(brand_path):
    """Instala la identidad del pack: colores, tipografías, logos y reglas.
    La lectura vive en _comun (colores_marca, fuente_marca, ruta_de_pack):
    la misma para todas las herramientas del kit."""
    global LOGO, ISOTIPO, MARCA_NOMBRE, TRANSICIONES   # fuentes: vía globals()
    global SOLAPE, SOLAPE_PRE
    from _comun import colores_marca, fuente_marca, leer_pack, ruta_de_pack
    d = leer_pack(brand_path)
    c = colores_marca(brand_path)
    col = d.get("colores") or {}   # serie / exito / aviso declarados por el pack
    if col.get("serie"): c["serie"] = [hex_a_rgb(x) for x in col["serie"]]
    for k in ("exito", "aviso"):
        if col.get(k): c[k] = hex_a_rgb(col[k])
    _instalar_tokens(c)
    global FJI
    for rol, glob, defecto, gen in (("titulares", "FJ", "Plus Jakarta Sans", "sans-bold"),
                                    ("texto", "FM", "Montserrat", "sans"),
                                    ("etiquetas_mono", "MONO", "DejaVu Sans Mono", "mono"),
                                    ("titulares_itálica", "FJI", "Plus Jakarta Sans", "sans-bold")):
        hit = fuente_marca(brand_path, rol, defecto, gen)
        if hit: globals()[glob] = hit
    logos = d.get("logos") or {}
    LOGO = ruta_de_pack(brand_path, logos.get("logotipo") or logos.get("fondo_oscuro"))
    ISOTIPO = ruta_de_pack(brand_path, logos.get("isotipo"))
    MARCA_NOMBRE = d.get("nombre")
    TRANSICIONES = (d.get("reglas") or {}).get("transiciones", "libre")
    # "corte_seco" es una REGLA del pack: el solape entre escenas se reduce a un
    # micro-fade (sin disolvencia de 0.45 s entre dos pantallas de texto).
    if TRANSICIONES == "corte_seco":
        SOLAPE, SOLAPE_PRE = SOLAPE_SECO, SOLAPE_PRE_SECO
    print(f"brand pack: {d.get('nombre', brand_path)} — acento #%02X%02X%02X" % ACENTO, flush=True)

COLUMNA={"chat","leads","handoff"}   # se leen como columna (conversación, tabla, ficha)

def pintar(ctx,e,t):
    """Capa de la escena en el instante t. En horizontal, las escenas de
    COLUMNA se componen en un lienzo virtual de 9:16-ancho (1080 px) centrado:
    una conversación o una tabla de 1920 px de ancho no se lee."""
    global W,MARGEN
    fn=SCENES[e["tipo"]]
    if not (W>H and e["tipo"] in COLUMNA and W>1080): return fn(ctx,e,t)
    w_real,m_real=W,MARGEN
    W=1080; MARGEN=min(MARGEN,int(W*0.06))
    try:
        capa=fn(ctx,e,t)
    finally:
        W,MARGEN=w_real,m_real
    out=Image.new("RGBA",(W,H),(0,0,0,0)); out.alpha_composite(capa,((W-1080)//2,0))
    return out

_ESCALA={}
A_SANGRE={"kenburns","confetti"}   # cubren el cuadro a propósito: no se miden ni encogen
_ZONAS={}   # caja declarada por escena: {"idx": (x0,y0,x1,y1)}
def escala_segura(ctx,e,idx):
    """Factor de escala FIJO por escena para que su contenido quepa en la zona
    segura. Se mide el bbox del contenido en varios instantes de la escena
    (no por frame: un factor por frame bombearía).

    ZONA DECLARADA: si la escena trae `"zona": [x0,y0,x1,y1]`, el factor se
    calcula sobre esa caja y NO sobre el bbox medido. Dos escenas que
    declaran la misma zona salen con el MISMO factor, y entonces el contenido
    conserva su sitio de una a otra (antes: cada escena midia su propio bbox
    y el factor saltaba 0,5-1 % en cada corte: medido 1,000 / 0,995 / 0,991
    sobre la caja ancla (W/2, 0,45H), o sea la caja no se quedaba quieta).
    """
    if idx in _ESCALA: return _ESCALA[idx]
    if e["tipo"] in A_SANGRE: _ESCALA[idx]=1.0; return 1.0   # fondo a sangre; el texto ya va en la zona segura
    cx,cy=W/2,CENTRO_Y*H
    zona=e.get("zona")
    if isinstance(zona,(list,tuple)) and len(zona)==4:
        try:
            xs0,ys0,xs1,ys1=(float(v) for v in zona)
        except (TypeError,ValueError):
            zona=None
        if zona is not None:
            f=1.0
            if xs1>xs0 and ys1>ys0:
                f=min(f,(cx-SAFE["left"])/max(1,cx-xs0),(W-SAFE["right"]-cx)/max(1,xs1-cx),
                      (cy-SAFE["top"])/max(1,cy-ys0),(H-SAFE["bottom"]-cy)/max(1,ys1-cy))
            f=max(0.70,min(1.0,f))
            _ESCALA[idx]=f if f<0.995 else 1.0
            return _ESCALA[idx]
    fr,to=e["from"],e["to"]
    xs0,xs1,ys0,ys1=W,0,H,0
    for i in range(6):
        t=fr+0.25+(max(0.0,to-0.6-fr-0.25))*i/5
        bb=pintar(ctx,e,t).split()[3].point(lambda v:255 if v>110 else 0).getbbox()
        if bb:
            xs0=min(xs0,bb[0]); ys0=min(ys0,bb[1]); xs1=max(xs1,bb[2]); ys1=max(ys1,bb[3])
    cx,cy=W/2,CENTRO_Y*H
    cabe=math.inf   # cuánto podría crecer el contenido alrededor del ancla y seguir dentro
    if xs1>xs0:
        cabe=min((cx-SAFE["left"])/max(1,cx-xs0),(W-SAFE["right"]-cx)/max(1,xs1-cx),
                 (cy-SAFE["top"])/max(1,cy-ys0),(H-SAFE["bottom"]-cy)/max(1,ys1-cy))
    f=max(0.70,min(1.0,cabe))
    if f<0.995: print(f"  zona segura: escena {idx} ({e['tipo']}) escalada x{f:.3f}",flush=True)
    _ESCALA[idx]=f if f<0.995 else 1.0
    llena=_crecer(e,(xs0,ys0,xs1,ys1)) if _ESCALA[idx]==1.0 and xs1>xs0 else (1.0,0.0)
    _ESCALA[("llena",idx)]=llena
    # holgura para el push-in: la que deja el contenido YA colocado (encogido,
    # crecido o llevado al centro óptico), medida desde el punto donde empuja
    _ESCALA[("holgura",idx)]=(_holgura((xs0,ys0,xs1,ys1),_ESCALA[idx]*llena[0],llena[1])
                              if xs1>xs0 else math.inf)
    return _ESCALA[idx]

# LLENAR EL LIENZO: la misma medición, en el otro sentido. Una escena cuyo
# contenido ocupa una franja chica de la zona segura (un titular corto, unas
# píldoras) crece hasta llenarla, con tope, y se centra en vertical en la
# zona segura. El crecimiento deja sitio al push-in de la cámara (EMPUJE):
# crecida y empujada, sigue dentro de la zona segura (la que mide el QA).
LLENA_MAX=1.35   # tope: más allá el raster ampliado empieza a ablandar la letra
LLENA_MIN=1.02   # por debajo no compensa mover la escena (sería un salto sin ganancia)
NO_CRECEN=A_SANGRE|{"final","kenburns","demo","rotulo_inferior"}   # a sangre u overlay: su sitio es el diseño
# COMPOSICIÓN VERTICAL: toda escena que no tiene su sitio por diseño lleva el
# centro de su contenido al centro ÓPTICO de la zona segura (el ojo pone el
# centro un poco más arriba que el geométrico). Antes solo se recentraba la
# escena que crecía y casi ninguna crece (las limita el ancho): medido en el
# catálogo, la mitad de arriba o de abajo del 9:16 quedaba en negro.
CENTRO_OPTICO=0.46   # fracción de la altura de la zona segura, desde arriba
BANDA_MAX=0.5        # una escena más alta que media zona ya la compone (rótulo arriba,
                     # fuente al pie): moverla solo la carga hacia arriba
ANCLADAS={"constancia","cadena","cartel"}   # van ABAJO por su rol, bajo la cara del reel...
# ...pero SOLO si hay cara debajo. Antes se anclaban siempre, y sin video
# debajo el cartel quedaba pegado al pie de la zona con el 80 % del 9:16 en
# negro (medido: ocupacion 0.17-0.22). Hay cara debajo cuando la pieza es un
# overlay (ALFA: se compone sobre el video) o la escena lo declara
# (`sobre_cara: true`, p. ej. un plan con la toma ya quemada en el fondo).

def sobre_cara(e):
    """¿La escena va encima de una cara/toma? UN predicado: lo usan el
    encuadre (`_crecer`) y la prosa (escenas.md, repertorio)."""
    return bool(ALFA or e.get("sobre_cara"))

def sitio_propio(e):
    """¿La escena tiene su sitio por diseño? A sangre/overlay (NO_CRECEN) o
    anclada abajo con cara debajo."""
    return e["tipo"] in NO_CRECEN or (e["tipo"] in ANCLADAS and sobre_cara(e))

def _crecer(e,bb):
    """(factor, dy) del encuadre del bbox `bb`: crece alrededor de (W/2,
    CENTRO_Y·H) hasta llenar la zona segura (con tope) y dy lleva su centro
    vertical al centro óptico (CENTRO_OPTICO), sin salirse de la zona. Función
    pura del bbox medido: el mismo (g, dy) en toda la escena. Sin cambio:
    (1.0, 0.0): a sangre, overlay, ancladas por su rol, `y` o `zona`
    declaradas, o trayectoria global de cámara (fijan el sitio del contenido).
    Las ANCLADAS solo con cara debajo (`sobre_cara`)."""
    if (ALFA or sitio_propio(e) or e.get("zona") or e.get("y") is not None
            or _CAMARA["activa"]): return (1.0,0.0)
    x0,y0,x1,y1=bb; cx,cy=W/2,CENTRO_Y*H
    zx0,zy0,zx1,zy1=caja_segura()
    g=min(LLENA_MAX,(cx-zx0)/max(1,cx-x0),(zx1-cx)/max(1,x1-cx),(zy1-zy0)/max(1,y1-y0))
    g/=1+EMPUJE   # el push-in de la cámara cabe dentro
    if g<LLENA_MIN: g=1.0
    alto=g*(y1-y0)
    if g==1.0 and alto>BANDA_MAX*(zy1-zy0): return (1.0,0.0)   # ya compone la zona: es su diseño
    # el centro buscado, sujeto a que el bbox (crecido) quepa entero en la zona
    # CON el push-in y la flotación encima (si no, una escena crecida queda
    # pegada arriba y la cámara tiene que arrancar más abierta)
    c=zy0+CENTRO_OPTICO*(zy1-zy0)
    ocupa=min(zy1-zy0,alto*(1+EMPUJE)+2*FLOTA_CAM)
    c=min(max(c,zy0+ocupa/2),zy1-ocupa/2)
    # encajar: Y = cy + dy + g·(y - cy); el centro del bbox cae en c
    dy=c-cy-g*((y0+y1)/2-cy)
    return (g,dy) if g>1.0 or abs(dy)>=1.0 else (1.0,0.0)

def _holgura(bb,f,dy):
    """Cuánto puede empujar la cámara el bbox `bb` ya colocado (escala f y dy
    alrededor de (W/2, CENTRO_Y·H)) sin salirse de la zona segura: el push-in
    escala alrededor de (W/2, CENTRO_Y·H + dy) y la flotación (FLOTA_CAM) lo
    sube y lo baja encima (sin ella, medido, el gauge salía 5 px por abajo)."""
    x0,y0,x1,y1=bb; cx,cy=W/2,CENTRO_Y*H; py=cy+dy
    zx0,zy0,zx1,zy1=caja_segura()
    return max(1.0,min((cx-zx0)/max(1,f*(cx-x0)),(zx1-cx)/max(1,f*(x1-cx)),
                       (py-zy0-FLOTA_CAM)/max(1,f*(cy-y0)),(zy1-py-FLOTA_CAM)/max(1,f*(y1-cy))))

def llenado(ctx,e,idx):
    """(factor, dy) de crecimiento de la escena idx (se mide con escala_segura)."""
    escala_segura(ctx,e,idx)
    return _ESCALA.get(("llena",idx),(1.0,0.0))

# Respiración de cámara: push-in lento y constante en toda escena que no mueve
# su propia cámara. Un plano asentado nunca queda congelado (fluidez.md) y el
# movimiento es uno solo para todo el catálogo, no una flotación por escena.
EMPUJE=0.06   # push-in a lo largo de TODA la escena (animacion.md §5: 4-8 %). Antes era
              # 1 %/s con tope 5 %: en una escena de 3 s, 3 %, y no se veía. El
              # crecimiento del lienzo (LLENA_MAX) le deja este sitio en la zona segura.
CAMARA_PROPIA={"final","kenburns","demo","rotulo_inferior"}   # ya se mueven o son overlay
QUIETAS={"rotulo_inferior"}   # se LEE quieta (lower third / overlay): sin push-in ni eventos,
                              # pero no congelada: lleva la vida en reposo (`vida`)

FLOTA_CAM=6    # px de flotación vertical: mueve TODOS los bordes (el push-in casi no
               # mueve lo que está cerca de su centro)
FLOTA_HZ=0.3   # una oscilación cada ~3.3 s: se siente, no se mira

def vida(e,t):
    """dy de la VIDA EN REPOSO: la flotación de la cámara (FLOTA_CAM a FLOTA_HZ,
    el `flota` de siempre) sin el push-in. Para las escenas que se leen quietas
    (QUIETAS): medido, un rótulo inferior sostenido 3 s sobre un fondo quieto
    era un congelado de 3 s (la puerta `quieto_max` > 1 s fallaba en el video
    real). final, kenburns y demo ya se mueven solas y no la llevan."""
    return flota(t,e["from"],FLOTA_CAM,FLOTA_HZ)

def empuja(e):
    """¿La escena lleva el push-in por escena? (no: overlay, cámara propia,
    `respira: false` o trayectoria global de cámara)."""
    return not (ALFA or e["tipo"] in CAMARA_PROPIA or not e.get("respira",True)
                or _CAMARA["activa"])

def respiracion(e,t):
    """(escala, dy, dx) de la cámara de la escena: push-in de EMPUJE a lo largo
    de la escena (ease_in_out) + flotación suave.

    El reloj es GLOBAL cuando el plan declara una trayectoria de cámara
    (`plan["camara"]`): la cámara no se reinicia en cada corte, así que la
    escala y la flotación son continuas de una escena a la siguiente (antes
    el reloj era `t - e["from"]` y en cada corte la escala saltaba 4-5 %:
    medido, la pieza se leía como un montage y no como una toma continua).

    Sin trayectoria declarada el motor se comporta como antes: el push-in es
    por escena y la flotación también. La capacidad es opt-in y no cambia las
    piezas ya hechas.
    """
    if not e.get("respira",True): return 1.0,0.0,0.0
    if e["tipo"] in QUIETAS: return 1.0,vida(e,t),0.0   # también como overlay: el rótulo no se congela
    if ALFA or e["tipo"] in CAMARA_PROPIA: return 1.0,0.0,0.0
    if _CAMARA["activa"]:
        # trayectoria global: continua por construcción (mismo t -> misma escala)
        dx,_dy_rec=_offset_camara(t)
        return (_escala_camara(t), _CAMARA["flota"]*math.sin(2*math.pi*0.3*t), dx)
    dt=max(0.0,t-e["from"])
    dur=max(0.5,e.get("to",e["from"]+4.0)-e["from"])
    # ease_in_out (una curva canónica): arranca y llega sin tirón; pasado el
    # corte (la salida se solapa con la siguiente) se queda donde llegó
    return 1+EMPUJE*ease_in_out(dt/dur), flota(t,e["from"],FLOTA_CAM,FLOTA_HZ), 0.0

def encajar(layer,f,dy=0.0,dx=0.0):
    """Escala la capa alrededor de (W/2, CENTRO_Y·H) y la desplaza dx/dy px, con
    precisión sub-píxel (afín: sin escalones de 1 px en un movimiento lento)."""
    if abs(f-1)<0.0005 and abs(dy)<0.01 and abs(dx)<0.01: return layer
    cx,cy=W/2,CENTRO_Y*H
    return layer.transform((W,H),Image.AFFINE,
                           (1/f,0,cx-cx/f+dx,0,1/f,cy-(cy+dy)/f),
                           resample=Image.BICUBIC)

def encuadrar(ctx,e,idx,t,capa):
    """La capa de la escena con su encuadre: la red de la zona segura (encoge),
    el llenado (crece y centra) y la cámara (push-in y flotación), en UNA
    transformación afín."""
    fr,dy,dx=respiracion(e,t)
    g,dyl=llenado(ctx,e,idx)
    if empuja(e):
        # el push-in TERMINA donde el contenido llena la zona segura: si no hay
        # sitio para EMPUJE, la toma arranca un poco más abierta y llega a su
        # encaje. Se nota igual (misma razón 1+EMPUJE) y nunca se sale.
        fr*=min(1.0,_ESCALA.get(("holgura",idx),1+EMPUJE)/(1+EMPUJE))
    return encajar(capa,escala_segura(ctx,e,idx)*g*fr,dy+dyl,dx)

def componer(ctx,escenas,dur,t,manchas_ok):
    """Compone el frame en el instante t (puede ser sub-frame, para el blur)."""
    t=max(0.0,min(t,dur-1e-6))
    s=None; si=0
    for i,e in enumerate(escenas):
        if e["from"]<=t<e["to"]: s=e; si=i; break
    if s is None: s=escenas[-1]; si=len(escenas)-1
    # un solo mundo continuo para todo el video (con una semilla por escena el
    # fondo saltaba de lugar en cada corte)
    bg=Image.new("RGBA",(W,H),(0,0,0,0)) if ALFA else mundo(ctx,t,seed=1)
    ts=instante_saliente(s,t) if sale_por_mascara(escenas,si,manchas_ok) else t
    layer=encuadrar(ctx,s,si,t,pintar(ctx,s,ts).copy())
    ep=escenas[si-1] if si>0 else None
    if s.get("transicion")=="iris" and si>0 and t-s["from"]<0.9:
        # IRIS: la escena nueva se abre en circulo desde un punto (la cara)
        prev=encuadrar(ctx,ep,si-1,t,pintar(ctx,ep,instante_saliente(ep,t)).copy())
        fx=s.get("transicionX",0.5); fy=s.get("transicionY",0.38)
        mask=iris_mask(ctx,t,s["from"],0.9,fx,fy)
        inv=Image.eval(mask,lambda v:255-v)
        nada=Image.new("RGBA",(W,H),(0,0,0,0))
        bg.alpha_composite(Image.composite(prev,nada,inv))
        bg.alpha_composite(Image.composite(layer,nada,mask))
    elif s.get("transicion")=="dissolve" and si>0 and t-s["from"]<SOLAPE_DISSOLVE:
        # DISOLUCION: la escena nueva aparece encima de la anterior con alfa
        # creciente (un corte suave, sin mancha). Es la transicion mas neutra:
        # no pide atencion como la mancha ni ensucia con formas.
        kd=smoothstep(clamp01((t-s["from"])/SOLAPE_DISSOLVE))
        prev=encuadrar(ctx,ep,si-1,t,pintar(ctx,ep,instante_saliente(ep,t)).copy())
        prev.putalpha(prev.split()[3].point(lambda v:int(v*(1-kd))))   # cruza: la que sale baja lo que la otra sube
        bg.alpha_composite(prev)
        layer=layer.copy()
        layer.putalpha(layer.split()[3].point(lambda v:int(v*kd)))
        bg.alpha_composite(layer)
    elif si in manchas_ok and t-s["from"]<0.9:
        prev=encuadrar(ctx,ep,si-1,t,pintar(ctx,ep,instante_saliente(ep,t)).copy())
        fx=s.get("transicionX",0.5); fy=s.get("transicionY",0.45)
        mask=mancha_mask(ctx,t,s["from"],0.9,fx,fy)
        inv=Image.eval(mask,lambda v:255-v)
        nada=Image.new("RGBA",(W,H),(0,0,0,0))
        bg.alpha_composite(Image.composite(prev,nada,inv))
        bg.alpha_composite(Image.composite(layer,nada,mask))
    else:
        if si>0 and t-s["from"]<SOLAPE:   # la anterior termina de irse DEBAJO de la nueva
            bg.alpha_composite(encuadrar(ctx,ep,si-1,t,pintar(ctx,ep,t).copy()))
        if si>0 and t-s["from"]<0.03:   # corte seco con micro-fade de 30 ms (sin pop)
            layer=capa_entrada(layer,t,s["from"])
        bg.alpha_composite(layer)
    dibuja_deplecion(ImageDraw.Draw(bg),t,dur)   # el borde del lienzo, ENCIMA de la escena
    dibuja_cabecera(ctx,bg,t,dur)                 # la banda que firma la pieza
    if dur-t<0.8:   # fundido al cierre con ease-IN (x²): arranca suave y llega a negro en el
        k=clamp01((0.8-(dur-t))/0.8)**2   # último frame (smoothstep se quedaba 0.25 s en negro: black_frame)
        if ALFA:   # un overlay se va por transparencia, no a negro
            bg.putalpha(bg.split()[3].point(lambda v:int(v*(1-k))))
        else:
            bg.alpha_composite(Image.new("RGBA",(W,H),(0,0,0,int(255*k))))
    return bg if ALFA else bg.convert("RGB")

def capa_entrada(layer,t,t0,dur=0.03):
    k=clamp01((t-t0)/dur)
    a=layer.split()[3].point(lambda v:int(v*k)); layer.putalpha(a); return layer

def frame_con_blur(ctx,escenas,dur,t,fps,n,obturador,manchas_ok):
    """Motion blur por submuestreo temporal: promedia n sub-frames repartidos en
    la ventana del obturador (0.5 = 180°, el look de cine). n=1 lo desactiva."""
    img = componer(ctx,escenas,dur,t,manchas_ok) if n<=1 else _blur_de_submuestreo(ctx,escenas,dur,t,fps,n,obturador,manchas_ok)
    amp = _GRANO["amp"]
    if amp > 0:
        # el grano va DESPUES del blur: el grano es de la pelicula, no del
        #movimiento (si no, el patron de ruido se emborrona con el blur)
        img = aplicar_grano(img, W, H, int(round(t*fps)), amp)
    return img


def _blur_de_submuestreo(ctx,escenas,dur,t,fps,n,obturador,manchas_ok):
    """El promedio de sub-frames del obturador (lo que hace el motion blur)."""
    import numpy as np
    ventana=obturador/fps
    acc=None
    for k in range(n):
        tk=t+ventana*((k+0.5)/n-0.5)
        a=np.asarray(componer(ctx,escenas,dur,tk,manchas_ok),dtype=np.float32)
        if ALFA:   # promediar premultiplicado: si no, los bordes se oscurecen
            a=np.concatenate([a[...,:3]*a[...,3:4]/255,a[...,3:4]],axis=2)
        acc=a if acc is None else acc+a
    acc/=n
    if ALFA:
        al=acc[...,3:4]
        acc[...,:3]=np.where(al>0,acc[...,:3]*255/np.maximum(al,1e-6),0)
    return Image.fromarray(np.clip(acc+0.5,0,255).astype("uint8"))

def presupuesto_manchas(escenas,maximo,avisar=True):
    """La 'mancha' es opt-in y motivada: como máximo `maximo` por pieza
    (fluidez.md). Las que excedan el presupuesto pasan a corte seco."""
    ok=[]; pedidas=[i for i,e in enumerate(escenas)
                    if i>0 and e.get("transicion") in ("mancha", "iris")]
    for i in pedidas:
        if len(ok)<maximo: ok.append(i)
    if avisar and len(pedidas)>len(ok):
        print(f"AVISO: {len(pedidas)} transiciones 'mancha'/'iris' pedidas; se respetan {len(ok)} "
              f"(máximo {maximo}, ver references/fluidez.md); el resto, corte seco",flush=True)
    return set(ok)

_W={}
def _init_worker(brand_path,acento,plan,maximo_cfg,safe=None,escalas=None,alfa=False,
                 geo=(1080,1920,151),paleta=None):
    """Inicializa un proceso de render (portable: también con 'spawn' en Windows/macOS)."""
    global ACENTO, ACENTO_OSC, ALFA, W, H, MARGEN
    ALFA=alfa; W,H,MARGEN=geo
    if brand_path:
        import io, contextlib
        with contextlib.redirect_stdout(io.StringIO()): aplicar_brand(brand_path)
    elif paleta:
        import io, contextlib
        with contextlib.redirect_stdout(io.StringIO()): aplicar_paleta(paleta)
    elif acento:
        ACENTO=hex_a_rgb(acento); ACENTO_OSC=tuple(max(0,int(c*0.65)) for c in ACENTO)
    if safe: SAFE.update(safe)
    if escalas: _ESCALA.update(escalas)
    aplicar_globales(plan)
    esc=sorted(plan["escenas"],key=lambda s:s["from"])
    maximo=maximo_cfg if maximo_cfg is not None else (1 if TRANSICIONES=="corte_seco" else 2)
    _W.update(ctx=Ctx(),esc=esc,dur=plan["duracion"],ok=presupuesto_manchas(esc,maximo,avisar=False))

# PNG de cuadro con compresión 1: el PNG no pierde nada (píxeles idénticos) y el
# nivel por defecto (6) costaba 239 ms por cuadro, más que componerlo (~190 ms)
PNG_CUADRO={"compress_level":1}

def _render_worker(job):
    fi,fp,fps,blur,obt=job
    frame_con_blur(_W["ctx"],_W["esc"],_W["dur"],fi/fps,fps,blur,obt,_W["ok"]).save(fp,**PNG_CUADRO)
    return fi

def _progreso_render(hechos,total,t0):
    """Linea de progreso con ETA: % hecho, transcurrido y estimado restante.

    Sin esto, un render --blur 5 de una pieza de ~60 s (cada frame se
    compone 5 veces: minutos en una VM modesta) parece un cuelgue y un
    timeout lo mata sin dejar rastro de cuanto faltaba.
    """
    import time as _t
    tr=_t.time()-t0; pct=100.0*hechos/max(1,total)
    eta=tr/max(1,hechos)*(total-hechos) if hechos else 0
    print(f"  {hechos}/{total} ({pct:.0f}%) · {tr/60:.1f} min · quedan ~{eta/60:.1f} min",flush=True)

def revisar_overlay(tmpd,n,fps):
    """Chequeos de un overlay transparente (lower third, título, bug):
    empieza y termina vacío (no aparece de golpe ni se corta en el NLE),
    nada pinta el cuadro entero (perdería la transparencia) y todo queda
    dentro del title-safe 5%. Devuelve la lista de avisos."""
    avisos=[]; caja=None
    def alfa(fi):
        return Image.open(f"{tmpd}/f_{fi:04d}.png").split()[3].point(lambda v:255 if v>12 else 0)
    if alfa(0).getbbox(): avisos.append("el primer frame no está vacío: el overlay aparece de golpe")
    if alfa(n-1).getbbox(): avisos.append("el último frame no está vacío: el overlay se corta de golpe")
    for fi in range(0,n,max(1,int(fps/3))):
        a=alfa(fi); bb=a.getbbox()
        if not bb: continue
        if sum(a.histogram()[255:])>0.97*W*H:
            avisos.append(f"t={fi/fps:.2f}s: algo pinta todo el cuadro (el archivo dejaría de ser transparente)")
            break
        caja=bb if caja is None else (min(caja[0],bb[0]),min(caja[1],bb[1]),max(caja[2],bb[2]),max(caja[3],bb[3]))
    if caja and (caja[0]<W*0.05 or caja[1]<H*0.05 or caja[2]>W*0.95 or caja[3]>H*0.95):
        avisos.append(f"el gráfico invade el 5% exterior (title-safe): caja {caja}")
    return avisos

def formato(ancho,alto,plataforma=None):
    """Fija el lienzo y su zona segura (9:16 → unión Reels/TikTok/Shorts;
    horizontal → YouTube). Una sola puerta: render y validador la usan."""
    global W,H,MARGEN
    W,H=int(ancho),int(alto)
    plataforma=plataforma or ("vertical" if H>W else "youtube")
    if plataforma!="ninguna": SAFE.update(zona_segura(plataforma))
    else: SAFE.update({"top":0,"bottom":0,"left":0,"right":0})
    SAFE["bottom"]+=int(H*BANDA_SUBS["fraccion"])   # banda de subtítulos (aplicar_globales)
    MARGEN=max(SAFE["left"],int(W*0.05))
    _ESCALA.clear()
    return plataforma

def render(plan_path,plan,out,a):
    """Renderiza un plan ya cargado a `out` (.mp4; .webm/.mov = con alfa)."""
    global ACENTO, ACENTO_OSC, ALFA, W, H
    if out is None:
        # solo --preview: no se renderiza nada, pero las rutas de trabajo
        # (cache de frames) necesitan un nombre.
        out=os.path.splitext(os.path.basename(plan_path))[0]+".preview.mp4"
    ALFA=os.path.splitext(out)[1].lower() in (".webm",".mov")
    try:
        W,H=(int(v) for v in str(a.tamano or plan.get("tamano","1080x1920")).lower().split("x"))
    except ValueError:
        sys.exit("ERROR: tamano debe ser ANCHOxALTO, ej. 1920x1080")
    from _comun import resolver_pack
    brand_path = resolver_pack(a.brand or plan.get("brand"))   # marca SOLO si se pide
    if brand_path:
        aplicar_brand(brand_path)   # la marca manda SIEMPRE que se haya pedido
    elif a.paleta or plan.get("paleta"):
        aplicar_paleta(a.paleta or plan.get("paleta"))   # paleta elegida segun el brief
    elif plan.get("acento"):   # modo libre: el plan puede fijar solo el acento
        ACENTO=hex_a_rgb(plan["acento"]); ACENTO_OSC=tuple(max(0,int(c*0.65)) for c in ACENTO)
    aplicar_globales(plan)   # antes de formato: la banda de subtítulos entra en la zona segura
    formato(W,H,a.plataforma or plan.get("plataforma"))
    if BANDA_SUBS["fraccion"]:
        base=SAFE["bottom"]-int(H*BANDA_SUBS["fraccion"])   # borde inferior de la banda
        print(f"banda de subtítulos reservada: quemar con caption.py --margin "
              f"{round((base+H*0.025)/H*288)} (unidades libass, 288 = alto)",flush=True)
    ctx=Ctx(); fps=a.fps
    dur=plan["duracion"]; n=int(dur*fps)
    escenas=preparar_escenas(ctx,plan)
    maximo=plan.get("mancha_max", 1 if TRANSICIONES=="corte_seco" else 2)
    manchas_ok=presupuesto_manchas(escenas,maximo)
    if a.preview:
        return _preview(ctx,escenas,dur,fps,a,manchas_ok)
    tmpd=f"{out}.frames"; os.makedirs(tmpd,exist_ok=True)
    print(f"{n} frames, {len(escenas)} escenas, blur x{a.blur}"+(" · overlay con alfa" if ALFA else ""),flush=True)
    if a.blur and a.blur>1:
        print(f"  blur x{a.blur}: cada frame se compone {a.blur} veces; en una VM modesta "
              f"una pieza de ~60 s puede tardar varios minutos (progreso con ETA abajo; "
              f"sin --force, reanudar retoma los frames ya hechos)",flush=True)
    pend=[fi for fi in range(n) if a.force or not os.path.exists(f"{tmpd}/f_{fi:04d}.png")]
    if len(pend)<n: print(f"  retoma: {n-len(pend)} frames ya existen",flush=True)
    jobs=[(fi,f"{tmpd}/f_{fi:04d}.png",fps,a.blur,a.obturador) for fi in pend]
    import time as _time; _t0=_time.time()
    if a.jobs<=1:
        for i,j in enumerate(jobs):
            frame_con_blur(ctx,escenas,dur,j[0]/fps,fps,a.blur,a.obturador,manchas_ok).save(j[1],**PNG_CUADRO)
            if i%150==0: _progreso_render(i+1,len(jobs),_t0)
    else:
        from multiprocessing import Pool
        _pal=a.paleta or plan.get("paleta")
        init=(brand_path if brand_path else None, None if brand_path else plan.get("acento"),
              dict(plan,escenas=escenas), plan.get("mancha_max"), dict(SAFE), dict(_ESCALA), ALFA, (W,H,MARGEN),
              None if brand_path else _pal)   # escenas YA preparadas
        try:
            with Pool(a.jobs,initializer=_init_worker,initargs=init) as pool:
                for i,_ in enumerate(pool.imap_unordered(_render_worker,jobs,chunksize=4)):
                    if i%150==0: _progreso_render(i+1,len(jobs),_t0)
        except (PermissionError, OSError):
            _init_worker(*init)
            for i,j in enumerate(jobs):
                _render_worker(j)
                if i%150==0: _progreso_render(i+1,len(jobs),_t0)
    if ALFA:
        for av in revisar_overlay(tmpd,n,fps): print("AVISO overlay:",av,flush=True)
    print("frames ok, codificando…",flush=True)
    from _comun import codificar_frames   # BT.709 exacto; .webm/.mov = con alfa
    res=codificar_frames(f"{tmpd}/f_%04d.png", fps, out, crf=20)
    if res.get("alfa"):
        print(f"  alfa verificado: el frame central decodifica {res['transparente']:.0%} transparente",flush=True)
    # la música con la que se editó al ritmo va en el entregable (sin voz y sin
    # alfa; con voz en off la mezcla con ducking es musica.py mix)
    if plan.get("musica") and not ALFA and (getattr(a, "con_musica", False) or not any(e.get("voz") for e in escenas)):
        import musica
        from loudness import normalizar
        ext=os.path.splitext(out)[1]
        mezcla,final=f"{out}.mezcla{ext}",f"{out}.final{ext}"
        musica.mix_music_only(out,plan["musica"],mezcla)
        # -14 LUFS (lo que esperan las plataformas) con techo -1.5 dBTP: el AAC
        # suma sobrepico tras loudnorm y a -1.0 quedaba justo en el límite
        nivel=normalizar(mezcla,final,lufs=-14.0,tp=-1.5,duracion=dur)
        os.replace(final,out)
        os.remove(mezcla)
        print(f"  música mezclada y normalizada: {float(nivel['input_i']):.1f} LUFS",flush=True)
    # el render dice QUE produjo: el SKILL.md promete "1080x1920 @30fps" y el
    # agente no deberia tener que abrir ffprobe para comprobarlo
    print(f"OK {out} · {W}x{H} @{fps}fps · h264 yuv420p · {dur:.1f}s")

MEDIOS=("imagen","captura","musica")   # campos del plan que apuntan a un archivo

def resolver_medios(nodo,base):
    """Rutas de imagen/captura relativas al PLAN (no al cwd), absolutas y
    verificadas antes de renderizar: una foto que no existe sería un video
    negro en silencio. Modifica `nodo` y devuelve las rutas que faltan."""
    faltan=[]
    if isinstance(nodo,list):
        for v in nodo: faltan+=resolver_medios(v,base)
    elif isinstance(nodo,dict):
        for k,v in nodo.items():
            if k in MEDIOS and isinstance(v,str):
                ruta=os.path.expanduser(v)
                cand=[ruta] if os.path.isabs(ruta) else [os.path.join(base,ruta),ruta]
                ok=next((c for c in cand if os.path.isfile(c)),None)
                if ok: nodo[k]=os.path.abspath(ok)
                else: faltan.append(v)
            else:
                faltan+=resolver_medios(v,base)
    return faltan

_MUESTRAS={}
def muestra(tipo):
    """La muestra realista de una escena (scripts/escenas_muestra.json): fuente
    única de ejemplos para galería, banco, validador y mensajes de error."""
    if not _MUESTRAS:
        ruta=os.path.join(os.path.dirname(os.path.abspath(__file__)),"escenas_muestra.json")
        _MUESTRAS.update(json.load(open(ruta,encoding="utf-8"))["escenas"])
    return _MUESTRAS.get(tipo)

def _escalar_t(v,k,t0):
    if isinstance(v,list): return [_escalar_t(x,k,t0) for x in v]
    if isinstance(v,dict): return {a:_escalar_t(b,k,t0) for a,b in v.items()}
    if isinstance(v,(int,float)) and not isinstance(v,bool): return round(t0+v*k,3)
    return v

def completar_escena(e,i=0):
    """Tiempos por defecto: los `at` que el plan no trae se toman de la muestra
    de esa escena, escalados a SU duración (una escena de 8 s reparte sus
    entradas como la muestra de 5 s, estiradas). El agente escribe contenido;
    la coreografía tiene un default con oficio. Devuelve una copia."""
    tipo=e.get("tipo")
    if tipo not in SCENES:
        sys.exit(f"ERROR: escena {i+1}: tipo «{tipo}» no existe. Tipos: {', '.join(SCENES)}")
    if not all(isinstance(e.get(c),(int,float)) for c in ("from","to")) or e["to"]<=e["from"]:
        sys.exit(f"ERROR: escena {i+1} ({tipo}): necesita `from` y `to` en segundos, con to > from")
    e=dict(e); m=muestra(tipo)
    # `at` SIEMPRE existe: una escena nueva (sin muestra) que no traiga tiempos
    # se rompe al leer `e["at"]` dentro de la escena (KeyError, no un aviso)
    e["at"]=dict(e.get("at") or {})
    if m and isinstance(m.get("at"),dict):
        k=(e["to"]-e["from"])/max(0.1,m["to"]-m["from"])
        at=dict(e.get("at") or {})
        for clave,v in m["at"].items():
            if clave not in at: at[clave]=_escalar_t(v,k,e["from"])
        e["at"]=at
    return e

COMUNES={"tipo","from","to","at","transicion","transicionX","transicionY","respira","voz"}
_CAMPOS={}
def campos_de(tipo):
    """Campos que una escena LEE, sacados de su propio codigo (e["x"] /
    e.get("x") en su funcion y en los helpers a los que LLAMA): el esquema
    nunca se desincroniza del renderizador porque ES el renderizador.

    El alcance es el que de verdad existe: una escena ve los campos de SUS
    helpers, no los de todas. Antes, cualquier helper con un `e` en la firma
    exercia sus campos en TODAS las escenas: al anadir `dibuja_frase` (que
    lee `cps`), el campo `cps` paso a ser "conocido" en el esquema de las 40,
    y la sugerencia de un campo mal escrito (`pasos` -> `items`) empezo a
    proponer `cps` (medido: lo caza el check "campos mal escritos").
    """
    if not _CAMPOS:
        import inspect
        pat=re.compile(r'\be(?:\.get\(|\[)"(\w+)"')
        llama=re.compile(r"\b([A-Za-z_]\w*)\s*\(")
        helpers={}
        for nombre,f_ in list(globals().items()):
            if not inspect.isfunction(f_): continue
            if "e" not in inspect.signature(f_).parameters: continue
            try: src=inspect.getsource(f_)
            except (OSError,TypeError): src=""
            helpers[nombre]=(set(pat.findall(src)),src)

        def _de(nombre,visto):
            """Los campos de un helper y de los helpers a los que llama."""
            if nombre in visto or nombre not in helpers: return set()
            visto.add(nombre)
            campos,src=helpers[nombre]
            for c in llama.findall(src):
                campos=campos|_de(c,visto)
            return campos

        comunes=set(COMUNES)
        for t_,f_ in SCENES.items():
            try: src=inspect.getsource(f_)
            except (OSError,TypeError): src=""
            campos=set(pat.findall(src))
            for c in llama.findall(src):
                campos=campos|_de(c,set())
            _CAMPOS[t_]=comunes|campos
    return _CAMPOS.get(tipo,set(COMUNES))

def avisos_de_campos(e,i=0):
    """Un campo que la escena no lee es casi siempre un error del plan (`pasos`
    en vez de `items`, `titulo` en vez de `rotulo`): la escena saldría vacía
    EN SILENCIO. Devuelve avisos con la sugerencia más parecida."""
    import difflib
    conocidos=campos_de(e.get("tipo"))
    avisos=[]
    for k_ in e:
        if k_ in conocidos or k_.startswith("_"): continue
        sug=difflib.get_close_matches(k_,sorted(conocidos-COMUNES),n=1,cutoff=0.5)
        ej=muestra(e.get("tipo")) or {}
        if not sug:   # ¿lo que trae es la lista que la escena espera con otro nombre?
            listas=[c for c,v in ej.items() if isinstance(v,list) and c not in e]
            sug=listas[:1] if isinstance(e[k_],list) else []
        avisos.append(f"AVISO: escena {i+1} ({e.get('tipo')}): `{k_}` no lo usa esta escena"
                      +(f" — ¿quisiste decir `{sug[0]}`?" if sug else "")
                      +f" (campos de la muestra: {', '.join(c for c in ej if c not in COMUNES)})")
    return avisos

def error_de_escena(e,i,ex):
    """Un campo que falta, explicado (nunca un KeyError crudo): qué escena,
    qué campo y un ejemplo completo de esa escena para copiar."""
    tipo=e.get("tipo"); campo=ex.args[0] if isinstance(ex,KeyError) and ex.args else None
    que=f"falta el campo `{campo}`" if campo else f"{type(ex).__name__}: {ex}"
    ej=json.dumps(muestra(tipo) or {},ensure_ascii=False)
    return (f"ERROR: escena {i+1} ({tipo}, {e.get('from')}–{e.get('to')} s): {que}.\n"
            f"  Ejemplo completo de `{tipo}` (scripts/escenas_muestra.json):\n  {ej}")

_REJILLAS={}
def al_ritmo(escenas,plan):
    """Cortes al "uno" del compás y entradas al medio beat de `musica`
    (beat_sync.sincronizar_escenas). Con voz en off, solo las entradas: la voz
    se ubica por los tiempos originales de cada escena. `"ritmo": false` lo
    apaga. La rejilla se analiza una vez por archivo."""
    import beat_grid
    import beat_sync
    ruta=plan["musica"]
    if ruta not in _REJILLAS:
        _REJILLAS[ruta]=beat_grid.analizar(ruta)
    hay_voz=any(e.get("voz") for e in escenas)
    escenas,info=beat_sync.sincronizar_escenas(escenas,_REJILLAS[ruta],plan["duracion"],mover_cortes=not hay_voz)
    print(f"al ritmo de la música: {info['bpm']} BPM · {info['entradas']} entradas al medio beat"
          +("" if hay_voz else f" · {info['cortes']} cortes al compás")
          +f" (desvío máx {info['desvio_max']} s)",file=sys.stderr,flush=True)
    return escenas

def resolver_datos(plan):
    """Resuelve las referencias `{"$dato": "nombre"}` de las escenas contra el
    bloque `datos` del plan.

    EL MODELO ANTES DEL DIBUJO: las cifras de una pieza se declaran UNA vez,
    arriba, con su fuente; las escenas las referencian. Asi ninguna escena
    puede contradecir a otra: si dos ponian 3 y 9 para el mismo dato, ahora
    hay un solo 3 (o un solo 9) y el linter avisa de la contradiccion.

        "datos": {"servicios": {"valor": 6, "fuente": "catálogo 2026"}},
        ... en la escena: "valor": {"$dato": "servicios"}
    """
    datos=plan.get("datos") or {}
    if not isinstance(datos,dict):
        sys.exit("ERROR: el bloque 'datos' del plan debe ser un objeto {nombre: {valor, fuente}}")
    for nombre,entrada in datos.items():
        if not isinstance(entrada,dict) or "valor" not in entrada:
            sys.exit(f"ERROR: el dato '{nombre}' no tiene 'valor' (usa {{valor, fuente}})")
    return datos

def _resolver_dato(dato,datos,i,escena):
    if isinstance(dato,dict) and "$dato" in dato:
        nombre=dato["$dato"]
        if nombre not in datos:
            sys.exit(f"ERROR: escena {i} ({escena.get('tipo','?')}) pide el dato "
                     f"'{nombre}' y el plan no lo declara en 'datos'")
        return datos[nombre]["valor"]
    return dato

def _recorrer_datos(nodo,datos,i,escena):
    if isinstance(nodo,dict):
        if "$dato" in nodo and len(nodo)==1:
            return _resolver_dato(nodo,datos,i,escena)
        return {k:_recorrer_datos(v,datos,i,escena) for k,v in nodo.items()}
    if isinstance(nodo,list):
        return [_recorrer_datos(v,datos,i,escena) for v in nodo]
    return nodo

def preparar_escenas(ctx,plan):
    """Escenas del plan listas para componer: tiempos completados desde la
    muestra, en orden, y cada una compuesta UNA vez (escala_segura) para fallar
    en segundos con un mensaje claro, no tras minutos de render. Una sola
    puerta para render_plan y medir_animacion --plan."""
    aplicar_globales(plan)
    datos=resolver_datos(plan)
    escenas=sorted((completar_escena(e,i) for i,e in enumerate(plan["escenas"])),key=lambda s:s["from"])
    if datos:
        for i,e in enumerate(escenas):
            resuelto=_recorrer_datos(e,datos,i,e)
            e.clear(); e.update(resuelto)
    # el dial no salta entre beats: cada escena de gauge arranca en el valor
    # de la anterior (salvo que el plan lo diga). El plan puede declarar
    # `valor_desde` para romper la cadena a proposito.
    _valor_previo=None
    for e in escenas:
        if e.get("tipo")=="gauge" and e.get("forma")=="anillo":
            if "valor_desde" not in e and _valor_previo is not None:
                e["valor_desde"]=_valor_previo
            _valor_previo=e.get("valor",_valor_previo)
        elif e.get("tipo")=="gauge" and e.get("valor") is not None:
            _valor_previo=e.get("valor")
    if plan.get("musica") and plan.get("ritmo",True):   # edición al ritmo de la música
        escenas=al_ritmo(escenas,plan)
    for i,e in enumerate(escenas):
        for av in avisos_de_campos(e,i): print(av,file=sys.stderr,flush=True)
    if ctx is not None and Image is not None:
        for i,e in enumerate(escenas):
            try:   # compone de verdad (escala_segura cachea por índice: no basta)
                for t in (e["from"]+0.05,(e["from"]+e["to"])/2,e["to"]-0.05): pintar(ctx,e,t)
                escala_segura(ctx,e,i)
            except (KeyError,IndexError,TypeError) as ex:
                sys.exit(error_de_escena(e,i,ex))
    return escenas

def medios_o_morir(plan,base,quien="el plan"):
    faltan=resolver_medios(plan,base)
    if faltan:
        sys.exit(f"ERROR: {quien} usa archivos que no existen (rutas relativas al plan): "
                 + ", ".join(sorted(set(faltan))))

# ---------- plantilla × tabla: un plan, N videos ----------
_PH=re.compile(r"\{([A-Za-z_]\w*)\}")

def _numero(v):
    if isinstance(v,(int,float)) or not isinstance(v,str): return v
    try: return int(v)
    except ValueError:
        try: return float(v)
        except ValueError: return v

def sustituir(nodo,fila,faltan):
    """Reemplaza {campo} en todo string del plan con la fila. Un string que es
    SOLO "{campo}" toma el valor tipado (un número sigue siendo número y
    cuenta). Los campos sin columna se acumulan en `faltan` (fail-loud)."""
    if isinstance(nodo,dict): return {k:sustituir(v,fila,faltan) for k,v in nodo.items()}
    if isinstance(nodo,list): return [sustituir(v,fila,faltan) for v in nodo]
    if not isinstance(nodo,str): return nodo
    for c in _PH.findall(nodo):
        if c not in fila: faltan.add(c)
    m=_PH.fullmatch(nodo)
    if m and m.group(1) in fila: return _numero(fila[m.group(1)])
    return _PH.sub(lambda mm:str(fila.get(mm.group(1),mm.group(0))),nodo)

def leer_tabla(ruta):
    if ruta.lower().endswith(".json"):
        filas=json.load(open(ruta,encoding="utf-8"))
        if isinstance(filas,dict): filas=filas.get("filas",[])
        return filas
    import csv
    with open(ruta,encoding="utf-8-sig",newline="") as f:
        muestra=f.read(4096); f.seek(0)
        try: dialecto=csv.Sniffer().sniff(muestra,delimiters=",;\t")
        except csv.Error: dialecto=csv.excel   # una sola columna: no hay separador que adivinar
        return [dict(r) for r in csv.DictReader(f,dialect=dialecto)]

def _preview(ctx, escenas, dur, fps, a, manchas_ok):
    """MIRA el plan sin pagar el render: compone los instantes pedidos y los
    pone en una hoja.

    El frame final es una funcion pura del tiempo (se compone en `t`, sin
    depender de los frames anteriores), asi que un instante se compone solo:
    no hace falta renderizar lo de antes para ver lo de ahora. Por eso esto
    es una hoja de contactos DEL PLAN, no un video recortado.
    """
    import time as _time, tempfile as _tf, shutil as _sh
    from contact_sheet import mosaico
    instantes = []
    for x in str(a.preview).replace(";", ",").split(","):
        x = x.strip()
        if not x:
            continue
        try:
            instantes.append(float(x))
        except ValueError:
            sys.exit(f"ERROR: --preview pide instantes en segundos, no '{x}'")
    if not instantes:
        sys.exit("ERROR: --preview necesita al menos un instante (ej. --preview 0,2.5,5)")
    d = _tf.mkdtemp(prefix="editoria_preview_")
    tiles = []
    vistos = []
    for t in instantes:
        if t < 0 or t > dur:
            print(f"AVISO: {t}s esta fuera del plan (dura {dur}s): se omite", flush=True)
            continue
        t0 = _time.time()
        img = frame_con_blur(ctx, escenas, dur, t, fps, a.blur, a.obturador, manchas_ok)
        ms = (_time.time() - t0) * 1000
        ruta = os.path.join(d, f"t_{t:07.2f}.png")
        img.save(ruta, **PNG_CUADRO)
        tiles.append((ruta, f"{t:.2f}s", ""))
        vistos.append(t)
        print(f"  {t:.2f}s  {ms:.0f} ms/frame", flush=True)
    if not tiles:
        sys.exit("ERROR: ningun instante del --preview cae dentro del plan")
    if a.hoja:
        salida = a.hoja
    elif a.out:
        salida = os.path.splitext(a.out)[0] + ".preview.jpg"
    else:
        salida = os.path.splitext(a.plan)[0] + ".preview.jpg"
    mosaico(tiles, cols=min(3, len(tiles)), ancho_tile=640, salida=salida)
    _sh.rmtree(d, ignore_errors=True)   # el mosaico ya tiene los pixeles en memoria
    print(f"hoja de contactos del plan: {salida}")
    print(f"instantes: {', '.join(f'{t:.2f}s' for t in vistos)} · duracion del plan: {dur}s")
    return salida


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("plan"); ap.add_argument("-o","--out",required=False,
                    help="salida .mp4 (o .webm/.mov = overlay con alfa); con --datos admite {campo}. Con --preview no hace falta")
    ap.add_argument("--preview",default=None,
                    help="instantes a mirar separados por comas (ej. 0,2.5,5): compone solo esos frames y escribe una hoja de contactos, SIN renderizar el video entero")
    ap.add_argument("--hoja",default=None,
                    help="donde se escribe la hoja del --preview (default: <salida>.preview.jpg)")
    ap.add_argument("--fps",type=int,default=30)
    ap.add_argument("--brand", default=None,
                    help="brand pack (brand/*.json); el plan también acepta campo \"brand\"")
    ap.add_argument("--paleta", default=None,
                    help="paleta del modo libre (references/paleta.md): electrico, menta, grafito, "
                         "ambar, coral, violeta, magenta, oro. El plan también acepta campo "
                         "\"paleta\". Si hay --brand, la marca manda")
    ap.add_argument("--blur",type=int,default=1,
                    help="sub-frames de motion blur (1=off, 4-6 para entrega final)")
    ap.add_argument("--obturador",type=float,default=0.5,
                    help="ángulo de obturador como fracción del frame (0.5 = 180°)")
    ap.add_argument("--jobs",type=int,default=max(1,(os.cpu_count() or 2)-1),
                    help="procesos de render en paralelo (default: núcleos-1)")
    ap.add_argument("--plataforma",default=None,
                    help="zona segura: vertical (Reels+TikTok+Shorts, default), reels, tiktok, shorts, ninguna")
    ap.add_argument("--con-musica", action="store_true",
                    help="fuerza la mezcla y normalización de música en el entregable aunque las escenas tengan texto de voz")
    ap.add_argument("--force",action="store_true",
                    help="re-renderiza todos los frames aunque ya existan")
    ap.add_argument("--tamano",default=None,
                    help="ANCHOxALTO (default 1080x1920 o el campo \"tamano\" del plan; 1920x1080 para 16:9)")
    ap.add_argument("--datos",help="tabla CSV/TSV/JSON: un video por fila; el plan usa {columna}")
    ap.add_argument("--fila",type=int,help="con --datos: renderizar solo esta fila (1 = primera) "
                    "para verificarla antes del lote")
    import os as _os, sys as _sys
    _sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "ffmpeg_tools"))
    from _comun import ayudar
    ayudar(ap, {'--fps': 'cuadros por segundo (30 default; 24 para look de cine)'})
    a=ap.parse_args()
    if not a.out and not a.preview:
        ap.error("falta -o/--out (usa --preview si lo que quieres es mirar el plan sin renderizarlo)")
    if a.preview and not a.hoja:
        _base=os.path.splitext(a.out or os.path.basename(a.plan))[0]
        a.hoja=_base+".preview.jpg"
    from _comun import asegurar_padre
    if a.out: asegurar_padre(a.out)
    if a.hoja: asegurar_padre(a.hoja)
    plan=leer_json(a.plan,"el plan")
    base=os.path.dirname(os.path.abspath(a.plan))
    if not a.datos:
        medios_o_morir(plan,base)
        return render(a.plan,plan,a.out,a)
    filas=leer_tabla(a.datos)
    if not filas: sys.exit(f"ERROR: {a.datos} no tiene filas")
    if a.fila:
        if not 1<=a.fila<=len(filas): sys.exit(f"ERROR: --fila {a.fila} fuera de 1..{len(filas)}")
        sel=[(a.fila,filas[a.fila-1])]
    else:
        sel=list(enumerate(filas,1))
    # validar TODAS las filas antes de renderizar nada (nunca "{nombre}" en pantalla)
    trabajos=[]
    for n_,fila in sel:
        faltan=set(); p_=sustituir(plan,fila,faltan)
        out=sustituir(a.out,fila,faltan)
        if faltan:
            sys.exit(f"ERROR fila {n_}: el plan usa {{{', '.join(sorted(faltan))}}} y la tabla "
                     f"no tiene esa(s) columna(s): {', '.join(fila)}")
        if out==a.out and len(sel)>1:
            b,ext=os.path.splitext(a.out); out=f"{b}_{n_:03d}{ext}"
        medios_o_morir(p_,base,f"la fila {n_}")
        trabajos.append((n_,p_,out))
    print(f"plantilla × {len(trabajos)} fila(s) de {a.datos}",flush=True)
    for n_,p_,out in trabajos:
        ruta=f"{out}.plan.json"   # el plan resuelto queda junto al video (reproducible)
        json.dump(p_,open(ruta,"w",encoding="utf-8"),ensure_ascii=False,indent=1)
        print(f"— fila {n_}: {out}",flush=True)
        render(ruta,p_,out,a)

if __name__=="__main__": main()
