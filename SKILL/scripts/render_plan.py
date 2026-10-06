#!/usr/bin/env python3
"""EditorIA plan renderer — ejecuta un plan.json con fluidez total.
Identidad desde brand pack opcional (--brand o campo "brand" en el plan);
sin pack, usa los defaults neutros del renderer.
Uso: python render_plan.py plan.json -o salida.mp4 [--fps 30] [--brand brand/otro.json]
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
import os, math, json, random, re, sys, argparse

# ---------- identidad: defaults NEUTROS; el brand pack los sobreescribe ----------
# Sin pack (modo libre) nada de marca: acento neutro y fuentes empaquetadas.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg_tools"))
from _plataforma import resolver_fuente
from _comun import NEUTRO, segmentos_enfasis   # paleta neutra y énfasis *...* únicos del kit
ACENTO=NEUTRO["acento"]; ACENTO_OSC=NEUTRO["acento_oscuro"]; NEGRO=NEUTRO["negro"]
BLANCO=NEUTRO["blanco"]; GRIS=NEUTRO["gris"]; PANEL=(26,26,26); PANEL2=(38,38,38)
FJ=resolver_fuente("Plus Jakarta Sans", generica="sans-bold")
FM=resolver_fuente("Montserrat", generica="sans")
MONO=resolver_fuente("DejaVu Sans Mono", "Consolas", "Menlo", generica="mono")
LOGO=None; ISOTIPO=None; MARCA_NOMBRE=None
TRANSICIONES="libre"   # idioma de transición; el pack puede fijar "corte_seco"
ALFA=False   # salida .webm/.mov: overlay transparente (sin fondo vivo, salida por alfa)

W,H=1080,1920
MARGEN=151   # margen lateral seguro simétrico (unión Reels/TikTok/Shorts, ver _delivery.py)
SAFE={"top":192,"bottom":422,"left":151,"right":151}   # zona segura en px (se recalcula en main)

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
def ease_out_back(p):
    p=max(0,min(1,p)); c=1.70158; return 1+(c+1)*(p-1)**3+c*(p-1)**2
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
def clamp01(x): return max(0,min(1,x))
def lerp(a,b,k): return a+(b-a)*k
def flota(t,t0,amp=6,freq=0.45):
    """Flotación idle: respiración sutil cuando el elemento ya asentó."""
    if t<=t0: return 0.0
    return amp*math.sin(2*math.pi*freq*(t-t0))

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
        self.fT=lambda s,w=800: font(FJ,s,w)
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

SOLAPE=0.45  # s que la salida de una escena se superpone con la entrada de la siguiente

def capa_salida(layer,t,to_):
    """Salida anticipada que se SOLAPA con la escena siguiente: empieza 0.25 s
    antes del fin y termina SOLAPE s después, debajo de lo que ya entra (antes
    terminaba en `to` y quedaban frames de fondo vacío en cada corte: un
    parpadeo que fluidez.md prohíbe)."""
    s=prog(t,to_-0.25,to_+SOLAPE,smoothstep)   # cruza el corte: sin hueco vacío
    if s<=0: return layer
    a=layer.split()[3].point(lambda v:int(v*(1-s)))
    layer.putalpha(a)
    return layer

def titular(ctx,layer,t,lineas,ats,tam=120,cy=None,word_gap=36,line_gap=1.18,maxw=None):
    """Titular cinético: cada palabra entra con resorte en su `at`, con escala
    real (1.16 -> 1.0, el overshoot del resorte da el asentamiento) y elevación.
    Auto-fit sobre el ancho REAL de la línea (palabras + huecos)."""
    d=ImageDraw.Draw(layer)
    zx0,_,zx1,_=caja_segura()
    maxw=maxw or (zx1-zx0)*0.96   # cabe en la zona SEGURA (W-2*MARGEN es más ancho en 9:16)
    def palabras(ln):
        return [(w_,em) for t_seg,em in segs(ln) for w_ in t_seg.split(" ") if w_]
    def ancho(ln,fnt):
        ws=palabras(ln); gap=ctx.tmp.textlength(" ",font=fnt)+word_gap*0.4
        return sum(ctx.tmp.textlength(w_,font=fnt) for w_,_ in ws)+gap*max(0,len(ws)-1)
    while tam>40:
        fnt=ctx.fT(tam,800)
        if max(ancho(ln,fnt) for ln in lineas)<=maxw: break
        tam-=4
    fnt=ctx.fT(tam,800)
    gap=ctx.tmp.textlength(" ",font=fnt)+word_gap*0.4
    ys=cy or H*0.44
    y0=ys-(len(lineas)-1)*tam*line_gap/2
    wi=0
    for li,ln in enumerate(lineas):
        y=y0+li*tam*line_gap
        x=(W-ancho(ln,fnt))/2
        for w_,em in palabras(ln):
            ww=ctx.tmp.textlength(w_,font=fnt)
            at=ats[wi] if wi < len(ats) else ats[-1]+0.12*(wi-len(ats)+1); wi+=1   # palabras de más: siguen la cadencia
            k=spring(t,at,150,15)
            if k>0:
                sc=1+0.16*(1-k)
                col=ACENTO if em else BLANCO
                f2=ctx.fT(tam*sc,800) if abs(sc-1)>0.004 else fnt
                d.text((x+ww/2,y+tam+(1-min(1,k))*30),w_,font=f2,
                       fill=col+(int(255*clamp01(k*1.5)),),anchor="ms")
            x+=ww+gap
    return tam

def rotulo(ctx,layer,t,texto,at,y=None,color=None,tam=44):
    """Rótulo con entrada real: fade + elevación 24 px con resorte (nunca de golpe)."""
    color=color or BLANCO
    if not texto or t<at: return 0   # sin rótulo en el plan: no se dibuja
    k=spring(t,at,140,16)
    al=int(255*clamp01(k*1.5))
    d=ImageDraw.Draw(layer)
    sg=segs(texto); fnt=ctx.fX(tam,700)
    zx0,_,zx1,_=caja_segura()   # el rótulo cabe en la zona segura: encoge, nunca se sale
    ancho=(zx1-zx0)-20
    while tam>30 and seg_width(sg,fnt)>ancho:
        tam-=2; fnt=ctx.fX(tam,700)
    yy=(y or H*0.30)+(1-min(1,k))*24
    for i,ln in enumerate(partir_segs(sg,fnt,ancho)):   # si ni a 30 px cabe: dos líneas
        draw_seg(d,(W/2,yy+i*tam*1.2),ln,fnt,color+(al,),ACENTO+(al,),anchor="ma")
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

# ───────────────────────── primitivas DRY para escenas de datos/UI ─────────────────────────
# Cada nueva escena se compone de estas primitivas. DRY: las escenas NO duplican lógica
# de barras / anillos / círculos / partículas / grids; la llaman aquí.

def barra_h(d, x, y, ancho, alto, fraccion, color, radio=None, pista=18):
    """Barra horizontal rellenable: track + fill con esquinas redondeadas.
    `fraccion` ∈ [0, 1] controla el porcentaje visible (la animación lo interpola).
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
    fill_w = max(1, int(ancho * f))
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


def cuenta_up(desde, hasta, t, t0, dur=0.8, fmt="{:,}", progreso=None):
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
        return f"{v:,.{n}f}"
    return fmt.format(round(v, n) if n else int(round(v)))


def arco(d, cx, cy, radio, desde_deg, hasta_deg, color, grosor=14):
    """Arco de círculo centrado en (cx, cy) entre ángulos `desde_deg` y `hasta_deg`
    (0° = 3 en punto, sentido horario). DRY: la usan `gauge`, `pie`."""
    d.arc([cx - radio, cy - radio, cx + radio, cy + radio],
          start=desde_deg, end=hasta_deg, fill=color, width=grosor)


def particulas(d, t, t0, cx, cy, n=60, color=None, semilla=11):
    """Confetti / celebración determinista (seeded). Sin random: reproducible.
    `color` por defecto usa ACENTO. La usan `confeti`, `listo` (extra), etc."""
    if t < t0:
        return
    color = color or ACENTO
    rng = random.Random(semilla)
    dt = t - t0
    for i in range(n):
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


def pila(alturas, y0, y1, gap=24):
    """Apila bloques de `alturas` px entre y0 e y1: devuelve (centros, f).
    Si no caben, f < 1 encoge TODO por igual (tamaños de letra incluidos)
    en vez de dejar que se pisen; el conjunto queda centrado en su hueco."""
    total = sum(alturas) + gap * (len(alturas) - 1)
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
        fnt = fuente_que_cabe(ctx.fX, txt, 28, x1 - x0, 400, minimo=26)
        al = int(255 * prog(t, t0, t0 + 0.3, smoothstep))   # entra fundida, no de golpe
        lineas = partir_segs([(txt, False)], fnt, x1 - x0)   # una fuente larga: dos líneas
        for i, ln in enumerate(reversed(lineas)):            # de abajo hacia arriba
            d.text((W / 2, y1 - 24 - i * 34), "".join(t_ for t_, _ in ln).strip(), font=fnt,
                   fill=GRIS + (al,), anchor="mb")


def cuadricula(x0, y0, ancho_total, alto_total, cols, n):
    """Layout en grilla: devuelve [(x, y, w, h)] para `n` items en `cols` columnas.
    DRY: la usan `stats`, `lineup`, `pasos`."""
    filas = (n + cols - 1) // cols
    gap = 24
    w = (ancho_total - gap * (cols - 1)) // cols
    h = (alto_total - gap * (filas - 1)) // filas
    out = []
    for i in range(n):
        r, c = divmod(i, cols)
        x = x0 + c * (w + gap)
        y = y0 + r * (h + gap)
        out.append((x, y, w, h))
    return out


from PIL import features as _features
TNUM = ["tnum"] if _features.check("raqm") else None   # cifras tabulares nativas


def largo(texto, font, tabular=False):
    """Ancho real de `texto`; `tabular` = medido como lo dibuja cifra()."""
    tmp = ImageDraw.Draw(Image.new("L", (10, 10)))
    if not tabular:
        return tmp.textlength(texto, font=font)
    if TNUM:
        return tmp.textlength(texto, font=font, features=TNUM)
    celda = ancho_tabular(font)
    return sum(celda if c.isdigit() else tmp.textlength(c, font=font) for c in texto)


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
    tarjeta: se encoge (y nunca por debajo de `minimo`)."""
    tam = int(tam)
    while tam > minimo and largo(texto, fabrica(tam, peso), tabular) > ancho_max:
        tam = max(minimo, int(tam * 0.92))
    return fabrica(tam, peso)


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
    # mancha de entrada tras el titular (centrada con el titular: H*0.44)
    r=W*0.42*spring(t,e["from"],60,10)*(1-prog(t,cambio-0.15,cambio+0.35)*0.75)
    if r>4:
        pts=[]
        for i in range(72):
            a=i/72*math.pi*2+t*0.8
            rr=r*(1+0.28*math.sin(a*4+t*2))
            pts.append((W/2+rr*math.cos(a),H*0.44+rr*math.sin(a)))
        d.polygon(pts,fill=ACENTO+(58,))
    # micro-idle: el titular asentado respira (±5 px), nunca queda congelado
    if t < cambio:   # el primer titular se va (fundido + sube) en vez de desaparecer de golpe
        ks=prog(t,cambio-0.35,cambio)   # cúbica: arranca suave
        cy=H*0.44+flota(t,e["at"]["p1"][-1]+0.5,5,0.45)-ks*30
        sub,_=grupo()
        titular(ctx,sub,t,e["texto1"],e["at"]["p1"],tam=150,cy=cy)
        if ks>0: sub.putalpha(sub.split()[3].point(lambda v:int(v*(1-ks))))
        layer.alpha_composite(sub)
    else:
        cy=H*0.44+flota(t,e["at"]["p2"][-1]+0.5,5,0.45)
        titular(ctx,layer,t,e["texto2"],e["at"]["p2"],tam=124,cy=cy)
    return capa_salida(layer,t,e["to"])

def sc_canales(ctx,e,t):
    layer=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(layer)
    at=e["at"]; junta=prog(t,at["junta"]-0.4,at["junta"]+0.6)   # 1 s: las tarjetas no barren >60 px/frame
    rotulo(ctx,layer,t,e.get("rotulo",""),at["rotulo"],y=H*0.20)
    # marca que sube y se encoge (grupo logo+texto centrado)
    k=spring(t,at["marca"],90,14)
    if k>0:
        my=lerp(H*0.52,H*0.36,junta)
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
        if iso_ok:
            iso=ctx.iso.resize((iw,iw),Image.LANCZOS)
            a=iso.split()[3].point(lambda v:int(v*clamp01(k*1.4))); iso.putalpha(a)
            layer.alpha_composite(iso,(int(x0),int(my-iw/2)))
            x0+=iw+26*sc
        d.text((x0,my),e["marca"],font=fnt_m,fill=BLANCO+(int(255*clamp01(k*1.4)),),
               anchor="lm")
    # tarjetas de canal
    for i,c in enumerate(e["canales"]):
        k2=spring(t,c["at"],130,15)
        if k2<=0: continue
        ang=[-1,0,1][i] if i<3 else 0
        zx0,_,zx1,_=caja_segura()
        abre=min(unidad()*0.3,(zx1-zx0-300)/2)   # recorrido en unidad() y dentro de la zona segura
        sx,sy=W/2+ang*abre,H*0.68
        fy=H*0.58-120+i*150
        x=lerp(sx,W/2,junta); y=lerp(sy,fy,junta)
        w=lerp(300,min(880,zx1-zx0),junta); h=124
        sc2=k2
        ww,hh=int(w*sc2),int(h*sc2)
        if ww<10: continue
        card=Image.new("RGBA",(ww,hh),(0,0,0,0)); dc=ImageDraw.Draw(card)
        dc.rounded_rectangle([0,0,ww,hh],radius=30,fill=PANEL2+(255,))
        dc.rounded_rectangle([0,0,ww,hh],radius=30,outline=(255,255,255,28),width=2)
        # icono canal (círculo con inicial) — centrado vertical exacto (62 = 124/2)
        dc.ellipse([28,24,104,100],fill=ACENTO+(255,))
        # icono: `icono` del canal o la inicial de su NOMBRE (WhatsApp y Web no son ambos "W")
        ico=str(c.get("icono") or (c.get("nombre") or c["canal"])[:1]).strip()
        dc.text((66,62),ico.upper() if len(ico)==1 else ico,font=fuente_que_cabe(ctx.fT,ico,44,60,800),
                fill=BLANCO,anchor="mm")
        at_=clamp01((junta-0.4)/0.35)   # el texto se revela al asentar la bandeja, fundido
        if at_>0:
            dc.text((130,32),c["nombre"],font=ctx.fX(34,800),fill=BLANCO+(int(255*at_),))
            dc.text((130,74),c["texto"][:34],font=ctx.fX(27,400),fill=GRIS+(int(255*at_),))
        card=card.rotate((1-junta)*ang*8,expand=True,resample=Image.BICUBIC)
        fy_float=flota(t,c["at"]+1.2,5,0.4) if junta>0.9 else 0
        layer.alpha_composite(card,(int(x-card.width/2),int(y-card.height/2+fy_float)))
    return capa_salida(layer,t,e["to"])

def sc_medianoche(ctx,e,t):
    layer=Image.new("RGBA",(W,H),(0,0,0,0))
    rotulo(ctx,layer,t,e.get("rotulo",""),e["from"]+0.1,y=H*0.20)
    k=spring(t,e["from"],110,13)
    if k>0:
        tw,th=560,1140
        _,_,_,zy1=caja_segura(); arriba=H*0.20+80          # bajo el rótulo, sobre la UI
        sc=min(0.82,(zy1-arriba)*0.96/th)*(0.8+0.2*min(1,k)); cy_tel=(arriba+zy1)/2
        ph=Image.new("RGBA",(tw,th),(0,0,0,0)); dp=ImageDraw.Draw(ph)
        dp.rounded_rectangle([0,0,tw,th],radius=86,fill=(12,12,12,255))
        dp.rounded_rectangle([18,18,tw-18,th-18],radius=70,fill=(16,22,34,255))
        # fondo de pantalla vivo: un halo del acento deriva despacio (la pantalla
        # bloqueada no queda congelada entre notificación y notificación)
        hx=tw/2+130*math.sin(0.9*t); hy=th*0.70+90*math.cos(0.7*t)
        q=8   # se pinta a 1/8 y se desenfoca: halo suave sin borde, barato
        halo=Image.new("L",(tw//q,th//q),0)
        ImageDraw.Draw(halo).ellipse([(hx-260)/q,(hy-260)/q,(hx+260)/q,(hy+260)/q],fill=110)
        halo=halo.filter(ImageFilter.GaussianBlur(120/q)).resize((tw,th),Image.BILINEAR)
        masc=Image.new("L",(tw,th),0)
        ImageDraw.Draw(masc).rounded_rectangle([18,18,tw-18,th-18],radius=70,fill=255)
        brillo=Image.new("RGBA",(tw,th),ACENTO+(0,))
        brillo.putalpha(ImageChops.multiply(halo,masc))
        ph.alpha_composite(brillo)
        dp.rounded_rectangle([tw/2-85,42,tw/2+85,90],radius=24,fill=(0,0,0,255))
        dp.text((tw/2,160),e.get("fecha",""),font=ctx.fX(30,600),fill=(255,255,255,200),anchor="ma")
        dp.text((tw/2,280),e["hora"],font=ctx.fT(150,700),fill=BLANCO,anchor="ma")   # dígitos hasta y≈438
        nots=e["notificaciones"]
        for i,n in enumerate(nots):
            kn=spring(t,n["at"],120,16)
            if kn<=0: continue
            # cada notificación nueva EMPUJA a las anteriores con resorte (antes
            # saltaban 170 px en un frame: el conteo era un escalón)
            despues=sum(min(1.0,spring(t,m["at"],120,16)) for m in nots[i+1:])
            ny=480+despues*170+(1-min(1,kn))*-24   # baja apenas: nunca cruza la hora
            nw=Image.new("RGBA",(tw-44,140),(0,0,0,0)); dn=ImageDraw.Draw(nw)
            dn.rounded_rectangle([0,0,tw-44,140],radius=30,fill=(255,255,255,36))
            dn.ellipse([22,38,86,102],fill=ACENTO+(255,))
            dn.text((54,70),n["canal"][0].upper(),font=ctx.fT(34,800),fill=BLANCO,anchor="mm")
            dn.text((110,52),n["titulo"],font=ctx.fX(27,800),fill=BLANCO)
            dn.text((110,92),n["texto"][:30],font=ctx.fX(24,400),fill=(255,255,255,190))
            a=nw.split()[3].point(lambda v:int(v*clamp01(kn*1.5))); nw.putalpha(a)
            ph.alpha_composite(nw,(22,int(ny)))
        ph=ph.resize((int(tw*sc),int(th*sc)),Image.LANCZOS)
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
    rotulo(ctx,layer,t,e.get("rotulo",""),t_rot,y=H*0.20)
    fnt=ctx.fX(32,400); GAP=36; ALTO_ESC=84
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
    y0=H*0.42; alto=0.0
    for mm in msgs:
        k=spring(t,mm["at"],140,15)
        if escribiendo(mm):
            ke=spring(t,mm["at"]-mm["esc"],160,16)
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
        k=spring(t,mm["at"],140,15)
        lado_x=lambda w_: zx0+12 if not mm["ia"] else zx1-12-w_
        visible=clamp01((y-H*0.24)/80)          # se desvanece bajo el rótulo
        if escribiendo(mm) and k<1:
            ke=min(1,spring(t,mm["at"]-mm["esc"],160,16))*(1-min(1,k))
            if ke>0.02:
                bw=150; x=lado_x(bw); a=int(255*ke*visible)
                d.rounded_rectangle([x,y,x+bw,y+ALTO_ESC],radius=30,fill=PANEL2+(a,))
                for j in range(3):
                    pul=0.4+0.6*(0.5+0.5*math.sin(t*7.5-j*0.9))
                    cxp=x+45+j*30
                    d.ellipse([cxp-8,y+34,cxp+8,y+50],fill=GRIS+(int(a*pul),))
                y+=(ALTO_ESC+GAP)*ke
        if k<=0: continue
        x=lado_x(mm["tw"]); hh=mm["hh"]
        col=tuple(int(c*0.30) for c in ACENTO) if mm["ia"] else PANEL2
        yy=y+(1-min(1,k))*24
        al=int(255*clamp01(k*1.4)*visible)
        d.rounded_rectangle([x,yy,x+mm["tw"],yy+hh],radius=30,fill=col+(al,))
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
        k=spring(t,lk["at"],120,14)
        cw,chh=min(760,zx1-zx0),150; x=(W-cw)/2
        yy=min(H*0.72,caja_segura()[3]-chh-10)+(1-min(1,k))*24   # sobre la UI de la plataforma
        ak=int(255*clamp01(k*1.4))   # la tarjeta y su texto entran juntos
        d.rounded_rectangle([x,yy,x+cw,yy+chh],radius=28,fill=ACENTO+(int(235*ak/255),))
        d.text((x+40,yy+34),lk.get("titulo",""),font=ctx.fX(34,800),fill=BLANCO+(ak,))
        d.text((x+40,yy+84),lk.get("monto",""),font=ctx.fT(44,800),fill=BLANCO+(ak,))
    return capa_salida(layer,t,e["to"])

def sc_leads(ctx,e,t):
    layer=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(layer)
    at=e["at"]
    kr=rotulo(ctx,layer,t,e.get("rotulo",""),at["rotulo"],y=H*0.20)
    if kr>0:   # el total entra con su rótulo
        d.text((W/2,bajo_rotulo(H*0.20,aire=0.15)),e.get("total",""),font=ctx.fM(36,700),fill=ACENTO+(int(255*clamp01(kr*1.5)),),anchor="ma")
    y0=H*0.32
    def color_temp(f_):   # tolerante: el agente escribe "caliente", "Hot", "frio"…
        if f_.get("color"):
            return hex_a_rgb(f_["color"])
        t_=str(f_.get("temp","")).lower().translate(str.maketrans("áéíóú","aeiou"))
        for claves,col in ((("calien","hot","alta"),ACENTO),(("tib","warm","media"),(200,140,40)),
                           (("fri","cold","baja"),(90,140,200))):
            if t_.startswith(claves): return col
        return GRIS   # temperatura desconocida: neutro, nunca un KeyError
    for i,f in enumerate(e["filas"]):
        k=spring(t,e["from"]+0.4+i*0.35,130,15)
        if k<=0: continue
        sub,ds=grupo()   # la fila entera entra junta (tarjeta, avatar, textos, barra)
        yy=y0+i*128
        zx0,_,zx1,_=caja_segura()   # compuesta DENTRO de la zona segura: no se encoge
        tarjeta(ctx,sub,zx0,yy,zx1-zx0,112)
        if f["temp"] in at and t>=at[f["temp"]]:   # el resaltado se enciende fundido, no de golpe
            ah=int(255*smoothstep(clamp01((t-at[f["temp"]])/0.2)))
            ds.rounded_rectangle([zx0,yy,zx1,yy+112],radius=28,outline=color_temp(f)+(ah,),width=4)
        ds.ellipse([zx0+24,yy+24,zx0+88,yy+88],fill=color_temp(f)+(255,))
        ds.text((zx0+56,yy+56),f["nombre"][0],font=ctx.fT(36,800),fill=BLANCO,anchor="mm")
        bmax=min(260,(zx1-zx0)*0.32)   # barra de puntaje a la derecha, el texto se ajusta al resto
        ancho_txt=(zx1-zx0)-bmax-150
        ds.text((zx0+112,yy+24),f["nombre"],font=fuente_que_cabe(ctx.fX,f["nombre"],32,ancho_txt,800),fill=BLANCO)
        ds.text((zx0+112,yy+62),f["etapa"],font=fuente_que_cabe(ctx.fX,f["etapa"],26,ancho_txt,400),fill=GRIS)
        # barra de puntaje: crece sin rebote (un dato no se pasa de su valor)
        bw=(f["puntaje"]/100)*bmax
        bx=zx1-bmax-24
        ds.rounded_rectangle([bx,yy+44,bx+bmax,yy+68],radius=12,fill=(60,60,60,255))
        g_=smoothstep(clamp01((t-(e["from"]+0.4+i*0.35))/0.8))
        if bw*g_>=24:
            ds.rounded_rectangle([bx,yy+44,bx+bw*g_,yy+68],radius=12,fill=color_temp(f)+(255,))
        fundir(layer,sub,k,dy=-50)
    return capa_salida(layer,t,e["to"])

def sc_handoff(ctx,e,t):
    layer=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(layer)
    at=e["at"]
    rotulo(ctx,layer,t,e.get("rotulo",""),at["rotulo"],y=H*0.20)
    k=spring(t,at["persona"],120,14)
    if k>0:   # la ficha entera entra junta
        sub,ds=grupo()
        zx0,_,zx1,_=caja_segura()   # dentro de la zona segura: la letra conserva su tamaño
        tarjeta(ctx,sub,zx0,H*0.30,zx1-zx0,220)
        ds.ellipse([zx0+40,H*0.30+60,zx0+140,H*0.30+160],fill=ACENTO+(255,))
        ini=e.get("iniciales") or "".join(w_[0] for w_ in e["cliente"].split()[:2]).upper()   # derivables del nombre
        ds.text((zx0+90,H*0.30+110),ini,font=fuente_que_cabe(ctx.fT,ini,44,72,800),fill=BLANCO,anchor="mm")
        at_=zx1-zx0-200
        ds.text((zx0+170,H*0.30+52),e["cliente"],font=fuente_que_cabe(ctx.fX,e["cliente"],40,at_,800),fill=BLANCO)
        ds.text((zx0+170,H*0.30+102),e.get("temp",""),font=ctx.fM(30,700),fill=(200,140,40))
        ds.text((zx0+170,H*0.30+142),e.get("nota",""),font=fuente_que_cabe(ctx.fX,e.get("nota",""),28,at_,400),fill=GRIS)
        fundir(layer,sub,k)
    y=H*0.30+270
    zx0,_,zx1,_=caja_segura()
    for i,c in enumerate(e["contexto"]):
        kc=spring(t,at["contexto"]+i*0.4,130,15)
        if kc<=0: continue
        yy=y+i*96+(1-min(1,kc))*-40
        al=int(255*clamp01(kc*1.4))
        d.text((zx0+30,yy),c["k"],font=ctx.fM(30,700),fill=ACENTO+(al,))
        d.text((zx0+30,yy+40),c["v"],font=fuente_que_cabe(ctx.fX,c["v"],30,zx1-zx0-60,400),fill=BLANCO+(al,))
    return capa_salida(layer,t,e["to"])

def sc_pago(ctx,e,t):
    layer=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(layer)
    at=e["at"]
    rotulo(ctx,layer,t,e.get("rotulo",""),at["rotulo"],y=H*0.20)
    k=spring(t,at["comprobante"],110,13)
    zx0,_,zx1,zy1=caja_segura()
    cw,chh=min(720,zx1-zx0),420; x=(W-cw)/2; y_card=H*0.36 if H>W else H*0.30
    if k>0:
        yy=y_card+(1-min(1,k))*-80
        tarjeta(ctx,layer,x,yy,cw,chh,radio=32,alpha=int(255*min(1,k)))
        ak=int(255*min(1,k))   # el contenido entra con su tarjeta, no antes
        util=cw-64   # todo cabe en la tarjeta (un monto o un nombre largo encoge, no se sale)
        d.text((W/2,yy+80),e["monto"],font=fuente_que_cabe(ctx.fT,e["monto"],96,util,800,tabular=True),
               fill=BLANCO+(ak,),anchor="ma")
        d.text((W/2,yy+190),e["cliente"],font=fuente_que_cabe(ctx.fX,e["cliente"],34,util,600),
               fill=BLANCO+(ak,),anchor="ma")
        d.text((W/2,yy+240),e.get("detalle",""),font=fuente_que_cabe(ctx.fX,e.get("detalle",""),28,util,400),
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
            a0=int(al*(1-c_))
            d.rounded_rectangle([mx-hw,my-hh,mx+hw,my+hh],radius=38,fill=ACENTO+(a0,))
            d.text((mx,my),e.get("boton","Pagar"),font=ctx.fX(34,800),fill=BLANCO+(a0,),anchor="mm")
        if c_>0:
            a1=int(al*c_)
            d.rounded_rectangle([mx-hw,my-hh,mx+hw,my+hh],radius=38,fill=BLANCO+(a1,))
            fh=ctx.fX(34,800); txt=e.get("hecho","Pagado"); tw=d.textlength(txt,font=fh)
            ca=ACENTO+(a1,)
            check(d,mx-tw/2-10,my,13,ca,6)
            d.text((mx+16,my),txt,font=fh,fill=ca,anchor="mm")
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
    k=spring(t,t0,90,10)
    if k>0:
        # asentado el estallido, el check flota (centrado, el push-in casi no lo mueve)
        cy=H*0.5+flota(t,t0+0.8,7,0.45)
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
        d.text((W/2,cy+190+(1-min(1,k))*30),e["texto"],font=ctx.fT(110,800),fill=BLANCO+(al,),anchor="ma")
    return capa_salida(layer,t,e["to"])

def sc_pildoras(ctx,e,t):
    layer=Image.new("RGBA",(W,H),(0,0,0,0))
    # columnas de píldoras cayendo al fondo (centradas: 135+6*135+67 = 540 = W/2)
    for ci in range(7):
        x=135+ci*135
        off=(t*160+ci*230)%(H+400)-200
        for pi in range(3):
            y=(off+pi*640)%(H+400)-200
            rot=ci*20+pi*40
            pw,phh=110,54
            pill=Image.new("RGBA",(pw,phh),(0,0,0,0)); dp=ImageDraw.Draw(pill)
            dp.rounded_rectangle([0,0,pw,phh],radius=27,
                                 fill=ACENTO+(26,) if pi%2 else BLANCO+(22,))
            pill=pill.rotate(rot,expand=True,resample=Image.BICUBIC)
            layer.alpha_composite(pill,(int(x-pw/2),int(y)))
    ats=e["at"]["palabras"]
    titular(ctx,layer,t,e["texto"],ats,tam=120)
    return capa_salida(layer,t,e["to"])

def sc_hoy(ctx,e,t):
    """Panel del día: contador que sube + tarjetas de tareas en cascada, en la
    grilla de la zona segura (2 columnas en 9:16, una fila en 16:9)."""
    layer=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(layer)
    at=e["at"]
    vertical=H>W
    # rótulo y fecha apilados y la fecha entra con el rótulo
    kr=rotulo(ctx,layer,t,e.get("rotulo",""),at["rotulo"],y=H*0.16)
    if kr>0:
        d.text((W/2,H*0.16+64+(1-min(1,kr))*24),e.get("fecha",""),font=ctx.fX(34,400),
               fill=GRIS+(int(255*clamp01(kr*1.5)),),anchor="ma")
    ck=prog(t,at["cuenta"],at["cuenta"]+0.8,ease_out)   # una sola curva
    if t>=at["cuenta"]:
        cifra(d,(W/2,H*0.27 if vertical else H*0.30),str(int(e["cuenta"]*ck)),
              ctx.fT(130,800),ACENTO+(int(255*clamp01(ck*3)),),anchor="ma")
    tarjetas=e["tarjetas"]; n=len(tarjetas)
    zx0,_,zx1,_=caja_segura()
    cols=2 if vertical else min(n,4)
    filas_=(n+cols-1)//cols
    y0=H*0.40 if vertical else H*0.50
    for i,(x,yb,cw,_) in enumerate(cuadricula(zx0,y0,zx1-zx0,filas_*184,cols,n)):
        tj=tarjetas[i]
        k=spring(t,e["from"]+0.6+i*0.3,130,15)
        if k<=0: continue
        sub,ds=grupo()   # la tarjeta entera (borde, insignia, textos) entra junta
        yy=yb
        tarjeta(ctx,sub,x,yy,cw,160)
        if tj.get("alerta"):
            ds.rounded_rectangle([x,yy,x+cw,yy+160],radius=28,outline=ACENTO+(255,),width=4)
        ancho_txt=cw-(110 if tj.get("n") else 50)
        ds.text((x+30,yy+28),tj["titulo"],font=fuente_que_cabe(ctx.fX,tj["titulo"],30,ancho_txt,800),fill=BLANCO)
        ds.text((x+30,yy+70),tj["detalle"],font=fuente_que_cabe(ctx.fX,tj["detalle"],26,ancho_txt,400),fill=GRIS)
        if tj.get("n"):
            ds.ellipse([x+cw-90,yy+28,x+cw-30,yy+88],fill=ACENTO+(255,))
            ds.text((x+cw-60,yy+58),str(tj["n"]),font=ctx.fT(32,800),fill=BLANCO,anchor="mm")
        fundir(layer,sub,k,dy=-50)
    return capa_salida(layer,t,e["to"])

def sc_recupera(ctx,e,t):
    """Pago recuperado: un cursor arrastra la barra; al completarse, tarjeta
    `hecho` (default "PAGADO") con el monto. Centrado en cualquier formato."""
    layer=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(layer)
    at=e["at"]
    kr=rotulo(ctx,layer,t,e.get("rotulo",""),at["rotulo"],y=H*0.20 if H>W else H*0.16)
    if kr<=0: return capa_salida(layer,t,e["to"])
    al=int(255*clamp01(kr*1.5)); sube=(1-min(1,kr))*24
    zx0,_,zx1,_=caja_segura()
    bw=min(800,(zx1-zx0)-68); bx=(W-bw)/2; by=H*0.5 if H>W else H*0.46   # -68: la perilla cabe
    d.text((W/2,(H*0.26 if H>W else H*0.25)+sube),e["resumen"],font=ctx.fX(36,600),
           fill=BLANCO+(al,),anchor="ma")
    # barra de progreso arrastrada por cursor
    rk=prog(t,at["cursor"],at["recupera"],smoothstep)   # una sola curva (antes ease sobre ease)
    d.rounded_rectangle([bx,by+sube,bx+bw,by+44+sube],radius=22,fill=(60,60,60,al))
    if rk>0:
        d.rounded_rectangle([bx,by,bx+max(44,bw*rk),by+44],radius=22,fill=ACENTO+(al,))
    cx=bx+bw*rk
    d.ellipse([cx-34,by-12+sube,cx+34,by+56+sube],fill=BLANCO+(al,))
    yc=by+(H*0.12 if H>W else H*0.14)
    if t>=at["pagado"]:
        k=spring(t,at["pagado"],120,14)
        tarjeta(ctx,layer,bx,yc,bw,240,radio=30,alpha=int(255*min(1,k)))
        d.text((W/2,yc+52),e.get("hecho","PAGADO"),font=ctx.fT(64,800),fill=(80,220,120),anchor="ma")
        d.text((W/2,yc+142),e["monto"],font=ctx.fT(54,800),fill=BLANCO,anchor="ma")
    else:
        d.text((W/2,yc+90+sube),e["cliente"],font=ctx.fX(36,600),fill=GRIS+(al,),anchor="ma")
        d.text((W/2,yc+140+sube),e.get("hace",""),font=ctx.fX(28,400),fill=GRIS+(al,),anchor="ma")
    return capa_salida(layer,t,e["to"])

def sc_remate(ctx,e,t):
    layer=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(layer)
    ats=e["at"]["palabras"]
    # palabras de las líneas
    words=[]
    for ln in e["lineas"]:
        words+=ln.replace("*","").split(" ")
    titular(ctx,layer,t,e["lineas"],ats,tam=110,cy=H*0.36+flota(t,ats[-1]+0.5,4,0.45))
    g=e["at"]["gigante"]
    k=spring(t,g,120,11)
    if k>0:
        sc=1.6-0.6*min(1,k)   # slam: aterriza sin estroboscopio (2.2x movía 100 px/frame)
        zx0,_,zx1,zy1=caja_segura()
        tam_g=fuente_que_cabe(ctx.fT,e["gigante"],300,(zx1-zx0)*0.94,800).size   # "1.000.000×" cabe
        # centro FIJO: donde asienta, sin pasar el borde seguro inferior (el
        # slam crece simétrico alrededor del centro; antes colgaba de arriba)
        bb0=ctx.fT(tam_g,800).getbbox(e["gigante"],anchor="mm"); hb=bb0[3]-bb0[1]
        yc=min(H*0.62+hb/2,zy1-hb*0.65)
        fnt=ctx.fT(int(tam_g*sc),800)
        bb=fnt.getbbox(e["gigante"],anchor="mm"); pad=90   # glow: lienzo por el bbox real (nunca recorta)
        a_g=smoothstep(clamp01((t-g)/0.25))
        glow=Image.new("RGBA",(bb[2]-bb[0]+2*pad,bb[3]-bb[1]+2*pad),(0,0,0,0))
        ImageDraw.Draw(glow).text((pad-bb[0],pad-bb[1]),e["gigante"],font=fnt,
                                  fill=ACENTO+(int(110*a_g),),anchor="mm")
        glow=glow.filter(ImageFilter.GaussianBlur(30))
        layer.alpha_composite(glow,(int(W/2+bb[0]-pad),int(yc+bb[1]-pad)))
        d.text((W/2,yc),e["gigante"],font=fnt,fill=BLANCO+(int(255*a_g),),anchor="mm")
    return capa_salida(layer,t,e["to"])

def sc_final(ctx,e,t):
    """Lockup de cierre: entra con resorte y luego RESPIRA (flotación, pulso del
    botón, push-in lento) — un end card quieto es un frame congelado."""
    layer=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(layer)
    at=e["at"]
    k=spring(t,e["from"]+0.1,70,12)
    asienta=e["from"]+1.2
    fy=flota(t,asienta,5,0.32)
    push=1+0.035*prog(t,e["from"],e["to"],ease_in_out)   # push-in de cámara
    if k>0:
        if ctx.logo and es_marca_del_pack(e["marca"]):
            lw=int(760*min(1,k)*push)
            lg=ctx.logo.resize((lw,int(lw*ctx.logo.height/ctx.logo.width)),Image.LANCZOS)
            layer.alpha_composite(lg,(int(W/2-lw/2),int(H*0.40-lg.height/2+fy)))
        else:
            zx0,_,zx1,_=caja_segura()
            tam_m=fuente_que_cabe(ctx.fT,e["marca"],120,(zx1-zx0)*0.92/1.035,800).size   # con el push máximo: tamaño fijo, sin saltos
            fnt_m=ctx.fT(int(tam_m*min(1,k)*push),800)
            d.text((W/2,H*0.40+fy),e["marca"],font=fnt_m,
                   fill=BLANCO+(int(255*clamp01(k*1.4)),),anchor="mm")
    if e.get("lema") and t>=at["lema"]:
        rotulo(ctx,layer,t,e["lema"],at["lema"],y=H*0.58+fy*0.6,tam=52)
    if e.get("boton") and t>=at["boton"]:
        kb=spring(t,at["boton"],120,14)
        bw,bh=520*min(1.0,kb),110*min(1.0,kb); x=(W-bw)/2; yy=H*0.70+(110-bh)/2+fy*0.4
        if bh>4:
            # halo que late suave alrededor del botón (acción secundaria)
            pul=0.5+0.5*math.sin((t-at["boton"])*2*math.pi*0.6)
            g=int(10+14*pul)
            d.rounded_rectangle([x-g,yy-g,x+bw+g,yy+bh+g],radius=int(bh/2+g),
                                outline=ACENTO+(int(70*pul*min(1,kb)),),width=3)
            d.rounded_rectangle([x,yy,x+bw,yy+bh],radius=int(bh/2),fill=ACENTO+(int(255*min(1,kb)),))
            if kb>0.5:
                d.text((W/2,yy+bh/2),e["boton"],font=ctx.fX(40*min(1.0,kb),800),
                       fill=BLANCO+(int(255*clamp01((kb-0.5)*2)),),anchor="mm")
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
        rotulo(ctx, layer, t, e["titulo"], at.get("rotulo", e["from"]), y=H*0.18)
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
    base_y = zy1 - 130            # debajo: etiquetas y la fuente, dentro de la zona segura
    max_h = base_y - (H * 0.18 + 150)   # arriba: rótulo (H*0.18) + cifra de la barra más alta
    for i, b in enumerate(barras):
        t_in = at.get(f"bar{i}", e["from"] + 0.2 + i * 0.1)
        k = spring(t, t_in, 110, 14)
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
        g_ = smoothstep(clamp01((t - t_in) / 0.9))
        fill_h = max_h * fraccion * g_
        if fill_h >= 1:   # el radio nunca supera la mitad del alto: nace de 0, no como píldora
            d.rounded_rectangle([x0, base_y - fill_h, x0 + bw, base_y], radius=min(18, fill_h / 2), fill=col)
        # etiqueta abajo
        fnt = fuente_que_cabe(ctx.fX, b.get("etiqueta", ""), 30, bw, 600)
        d.text((x0 + bw / 2, base_y + 22), b.get("etiqueta", ""), font=fnt, fill=BLANCO + (int(255 * ki),),
               anchor="mt")
        # valor arriba de la barra (tamaño fijado por el valor final)
        val = cuenta_up(0, b.get("valor", 0), t, t_in, progreso=g_)   # la cifra dice lo que mide la barra
        fnt_v = fuente_que_cabe(ctx.fT, cuenta_up(0, b.get("valor", 0), 1e9, 0), 64, bw, 800, tabular=True)
        cifra(d, (x0 + bw / 2, base_y - fill_h - 16), val, fnt_v, col, anchor="mb")
    pie_fuente(ctx, d, e, t, at.get("rotulo", e["from"]) + 1.5)
    return capa_salida(layer, t, e["to"])


def sc_gauge(ctx, e, t):
    """Indicador circular (gauge) con cuenta animada al medio.
    Params: `titulo`, `valor`, `max`, `etiqueta`, `at{rotulo, gauge, valor, etiqueta}`.
    """
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    at = e["at"]
    rotulo(ctx, layer, t, e.get("titulo", ""), at.get("rotulo", e["from"]), y=H*0.18)
    # el arco cabe entre el rótulo y el borde seguro (en 16:9 tapaba el título)
    _, _, _, zy1 = caja_segura()
    arriba, abajo = H * 0.18 + 80, zy1 - 150          # abajo: etiqueta bajo el arco
    r = min(unidad() * 0.34, (abajo - arriba) / 1.707)  # 270°: arriba r, abajo r·sin45°
    cx, cy = W / 2, arriba + r
    grosor = 26
    t_in = at.get("gauge", e["from"] + 0.3)
    ka = smoothstep(clamp01((t - (t_in - 0.3)) / 0.4))   # la pista entra fundida
    arco(d, cx, cy, r, 135, 135 + 270, (255, 255, 255, int(32 * ka)), grosor)
    # el arco llena con smoothstep (sin rebote: un dato no se pasa de su valor)
    # y la cifra dice exactamente lo que marca el arco
    g_ = smoothstep(clamp01((t - t_in) / 1.1))
    if g_ > 0:
        fraccion = clamp01(e.get("valor", 0) / max(1e-9, e.get("max", 100)))
        arco(d, cx, cy, r, 135, 135 + 270 * fraccion * g_, ACENTO, grosor)
    val = cuenta_up(0, e.get("valor", 0), t, t_in, progreso=g_)
    fnt = fuente_que_cabe(ctx.fT, cuenta_up(0, e.get("valor", 0), 1e9, 0), unidad() * 0.18, r * 1.3,
                          800, tabular=True)
    cifra(d, (cx, cy - 8), val, fnt, BLANCO + (int(255 * ka),), anchor="mm",
          final=cuenta_up(0, e.get("valor", 0), 1e9, 0))
    t_et = at.get("etiqueta", t_in + 0.7)
    if "etiqueta" in e and t >= t_et:
        ke = smoothstep(clamp01((t - t_et) / 0.3))
        d.text((cx, cy + r * 0.707 + 40 + (1 - ke) * 16), e.get("etiqueta", ""), font=ctx.fX(36, 600),
               fill=GRIS + (int(255 * ke),), anchor="mt")
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
    rotulo(ctx, layer, t, e.get("titulo", ""), at.get("rotulo", e["from"]), y=H*0.16)
    items = e.get("items", [])
    n = len(items)
    if n == 0:
        return capa_salida(layer, t, e["to"])
    zx0, _, zx1, zy1 = caja_segura()
    y0 = H * 0.16 + 110
    fila_h = min(130, (zy1 - 80 - y0) / n)
    y0 += ((zy1 - 80 - y0) - fila_h * n) / 2          # bloque centrado en su hueco
    hi = fila_h * 0.6
    fnt = ctx.fX(int(min(44, fila_h * 0.38)), 700)
    fnt_v = ctx.fX(int(min(48, fila_h * 0.42)), 800)
    finales = [cuenta_up(0, it.get("valor", 0), 1e9, 0) for it in items]
    w_lab = max(d.textlength(it.get("etiqueta", ""), font=fnt) for it in items) + 28
    w_val = max(largo(v, fnt_v, True) for v in finales) + 24
    x_bar = zx0 + w_lab
    bw = max(80, zx1 - w_val - x_bar)
    max_v = max((i.get("valor", 0) for i in items), default=1) or 1
    for i, it in enumerate(items):
        t_in = at.get(f"item{i}", e["from"] + 0.2 + i * 0.08)
        k = spring(t, t_in, 110, 14)
        if k <= 0:
            continue
        yi = y0 + i * fila_h + (fila_h - hi) / 2
        al = int(255 * clamp01(k * 1.4))
        d.text((zx0, yi + hi / 2), it.get("etiqueta", ""), font=fnt, fill=BLANCO + (al,), anchor="lm")
        fraccion = clamp01(it.get("valor", 0) / max_v)
        col = ACENTO if i == 0 else BLANCO
        g_ = smoothstep(clamp01((t - t_in) / 0.9))   # sin rebote: un dato no se pasa de su valor
        barra_h(d, x_bar, yi, bw, hi, fraccion * g_, col + (int(230 * al / 255),), radio=hi // 2,
                pista=18 * al / 255)
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
    rotulo(ctx, layer, t, e.get("titulo", ""), at.get("rotulo", e["from"]), y=H*0.16)
    cards = e.get("cards", [])
    n = len(cards)
    if n == 0:
        return capa_salida(layer, t, e["to"])  # sin datos, escena vacía
    x0, y0, x1, y1 = caja_segura()
    cols = columnas_grilla(n)
    filas_ = (n + cols - 1) // cols
    alto = min(y1 - 90 - H * 0.25, filas_ * unidad() * 0.36)   # tarjetas, no paredes
    ancho = min(x1 - x0, cols * unidad() * 0.62)
    coords = cuadricula((W - ancho) / 2, H * 0.25 + (y1 - 90 - H * 0.25 - alto) / 2,
                        ancho, alto, cols, n)
    for i, (cx, cy, cw, ch) in enumerate(coords):
        t_in = at.get(f"card{i}", e["from"] + 0.2 + i * 0.08)
        k = spring(t, t_in, 110, 14)
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
        val = cuenta_up(0, c.get("valor", 0), t, t_in, dur=0.7, fmt="{:,}")
        # tamaño fijado por la cifra FINAL (no salta mientras cuenta)
        fnt_v = fuente_que_cabe(ctx.fT, cuenta_up(0, c.get("valor", 0), 1e9, 0), ch * 0.42, cw * 0.84,
                                tabular=True)
        cifra(d, (cx + cw / 2, cy + ch * 0.42), val, fnt_v, col, anchor="mm")
        # etiqueta
        fnt_l = fuente_que_cabe(ctx.fX, c.get("etiqueta", ""), min(ch * 0.13, 44), cw * 0.86, 600)
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
    rotulo(ctx, layer, t, e.get("titulo", ""), at.get("rotulo", e["from"]), y=H*0.16)
    items = e.get("items", [])
    n = len(items)
    if n == 0:
        return capa_salida(layer, t, e["to"])
    zx0, _, zx1, zy1 = caja_segura()
    vertical = H > W
    if vertical:
        x_l = zx0 + 60
        a0, a1 = H * 0.16 + 160, zy1 - 120
        pos = [(x_l, a0 + (a1 - a0) * i / max(1, n - 1)) for i in range(n)]
    else:
        cy = H * 0.52
        a0, a1 = zx0 + 120, zx1 - 120
        pos = [(a0 + (a1 - a0) * i / max(1, n - 1), cy) for i in range(n)]
    t_ins = [at.get(f"item{i}", e["from"] + 0.2 + i * 0.4) for i in range(n)]
    # la línea crece de punto en punto (llega a cada uno cuando se enciende)
    t_linea = t_ins[0] - 0.3
    tramo = 0.0
    for i in range(n - 1):
        tramo += prog(t, max(t_linea, t_ins[i] - 0.15), t_ins[i + 1])
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
        d.line([p0, p1], fill=ACENTO + (230,), width=6)
    fnt = ctx.fX(40 if vertical else 36, 700)
    fnt_d = ctx.fX(30 if vertical else 28, 500)
    ancho_max = (zx1 - x_l - 50) if vertical else (a1 - a0) / max(1, n - 1) * 0.92
    for i, it in enumerate(items):
        k = spring(t, t_ins[i], 110, 14)
        if k <= 0:
            continue
        x, y = pos[i]
        al = int(255 * clamp01(k * 1.4))
        radio = 18 * min(1.0, k)
        d.ellipse([x - radio, y - radio, x + radio, y + radio], fill=ACENTO + (al,))
        if radio > 6:   # el punto nace de radio 0: el centro blanco solo si cabe
            d.ellipse([x - radio + 5, y - radio + 5, x + radio - 5, y + radio - 5], fill=BLANCO + (al,))
        lineas = linewrap(it.get("etiqueta", ""), fnt, ancho_max)
        if vertical:
            for li, ln in enumerate(lineas):
                d.text((x + 50, y - 22 + li * 46), ln, font=fnt, fill=BLANCO + (al,), anchor="lm")
            if it.get("fecha"):
                d.text((x + 50, y + 22 + (len(lineas) - 1) * 46), it["fecha"], font=fnt_d,
                       fill=GRIS + (al,), anchor="lm")
        else:
            for li, ln in enumerate(lineas):
                d.text((x, y - 56 - (len(lineas) - 1 - li) * 44), ln, font=fnt,
                       fill=BLANCO + (al,), anchor="mm")
            if it.get("fecha"):
                d.text((x, y + 56), it["fecha"], font=fnt_d, fill=GRIS + (al,), anchor="mm")
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
    k = spring(t, t_card, 110, 14)
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
    # pila vertical medida: comilla · texto · estrellas · autor · rol (nunca se pisan)
    h_com, h_txt = U * 0.13, n * lh
    h_est = U * 0.075 if e.get("estrellas") is not None else 0
    h_aut = (U * 0.06 if e.get("autor") else 0) + (U * 0.04 if e.get("rol") else 0)
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
        kl = spring(t, t_li, 130, 16)
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
            col = ACENTO if (em and ke >= 1) else BLANCO
            d.text((x, y), w_, font=fnt, fill=col + (al,), anchor="lm")
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
        ka = spring(t, t_au, 130, 16)
        al = int(255 * clamp01(ka * 1.4)); dy = (1 - min(1, ka)) * 20
        d.text((cx + cw / 2, y_sig + U * 0.04 + dy), e["autor"],
               font=ctx.fX(int(U * 0.040), 800), fill=BLANCO + (al,), anchor="mm")
        if e.get("rol"):
            d.text((cx + cw / 2, y_sig + U * 0.093 + dy), e["rol"],
                   font=ctx.fX(int(U * 0.028), 500), fill=GRIS + (al,), anchor="mm")
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
    rotulo(ctx, layer, t, e.get("titulo", ""), at.get("rotulo", fr), y=H*0.16)
    x0, _, x1, y1 = caja_segura()
    col_w = (x1 - x0) / 2 - 40
    lados = ((e.get("izquierda", {}), x0 + col_w / 2, at.get("izq", fr + 0.4), BLANCO, -1),
             (e.get("derecha", {}), x1 - col_w / 2, at.get("der", fr + 0.9), ACENTO, 1))
    n = max(1, *(len(l[0].get("items", [])) for l in lados))
    y_label = H * 0.29
    y_items = H * 0.38
    fila_h = min(150, (y1 - 40 - y_items) / n)
    todos = [it for l in lados for it in l[0].get("items", [])] or [""]
    largo = max(todos, key=lambda x: ctx.tmp.textlength(x, font=ctx.fX(40, 600)))
    fnt = fuente_que_cabe(ctx.fX, largo, min(56, fila_h * 0.42), col_w - 20, 600)
    fnt_h = fuente_que_cabe(ctx.fT, max((l[0].get("etiqueta", "") for l in lados), key=len),
                            int(W * 0.055), col_w, 800)
    k_vs = spring(t, min(l[2] for l in lados), 120, 14)
    if k_vs > 0:
        d.text((W / 2, y_label), "vs", font=ctx.fT(int(W * 0.05), 800),
               fill=GRIS + (int(255 * clamp01(k_vs * 1.3)),), anchor="mm")
        d.line([W / 2, y_items, W / 2, y_items + n * fila_h], fill=(255, 255, 255, int(40 * min(1, k_vs))),
               width=2)
    for lado, cx, t_in, col, signo in lados:
        k = spring(t, t_in, 120, 15)
        if k <= 0:
            continue
        dx = signo * 60 * (1 - min(1, k))
        al = int(255 * clamp01(k * 1.3))
        d.text((cx + dx, y_label), lado.get("etiqueta", ""), font=fnt_h, fill=col + (al,), anchor="mm")
        for i, it in enumerate(lado.get("items", [])):
            ki = spring(t, t_in + 0.15 + i * 0.12, 120, 15)
            if ki <= 0:
                continue
            yi = y_items + i * fila_h + fila_h / 2 + (1 - min(1, ki)) * 24
            d.text((cx, yi), it, font=fnt, fill=BLANCO + (int(255 * clamp01(ki * 1.3)),), anchor="mm")
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
        # mezclar acento con blanco para variedad visual (sin random en runtime)
        for i in range(80):
            rng_i = random.Random(semilla * 31 + i)
            ang = rng_i.uniform(0, 6.283)
            vel = rng_i.uniform(280, 720)
            caida = 980
            dt = t - t_p
            x = W * 0.5 + math.cos(ang) * vel * dt
            y = H * 0.45 + math.sin(ang) * vel * dt + 0.5 * caida * dt * dt
            if y > H + 40 or x < -40 or x > W + 40:
                continue
            s = rng_i.uniform(4, 10)
            c = ACENTO if i % 2 == 0 else BLANCO
            d.ellipse([x - s, y - s, x + s, y + s], fill=(c[0], c[1], c[2], rng_i.randint(160, 230)))
    if "texto" in e and t >= t_t:
        k = spring(t, t_t, 110, 14)
        if k > 0:
            x0, _, x1, _ = caja_segura()
            fnt = fuente_que_cabe(ctx.fT, e.get("texto", ""), unidad() * 0.10, x1 - x0, 800)
            d.text((W / 2, H * 0.42), e.get("texto", ""), font=fnt,
                   fill=BLANCO + (int(255 * clamp01(k * 1.3)),), anchor="mm")
    if "subtexto" in e and t >= at.get("subtexto", t_t + 0.4):
        x0, _, x1, _ = caja_segura()
        fnt_s = fuente_que_cabe(ctx.fX, e.get("subtexto", ""), unidad() * 0.045, x1 - x0, 600)
        ks = spring(t, at.get("subtexto", t_t + 0.4), 120, 15)
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
    lh = tam * 1.25
    alto = lh * len(lineas)
    y0 = H * 0.45 - alto / 2
    # panel de lectura: entra con la escena, dentro de la zona segura
    kp = smoothstep(clamp01((t - (t_in - 0.3)) / 0.4))
    if kp > 0:
        d.rounded_rectangle([zx0, y0 - tam * 0.45, zx1, y0 + alto + tam * 0.25], radius=22,
                            fill=PANEL + (int(180 * kp),))
    paso = 1 / float(e.get("cps", 12.5))
    t_lin, cur = t_in, None
    for li, ln in enumerate(lineas):
        y = y0 + li * lh
        x = zx0 + 40
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
        k = spring(t, at.get("texto", e["from"] + 0.5), 120, 15)
        al = int(255 * clamp01(k * 1.3))
        for i, ln in enumerate(lineas):
            d.text((W / 2, y_tit + i * 90 + (1 - min(1, k)) * 24), ln, font=fnt,
                   fill=BLANCO + (al,), anchor="mm")
    if e.get("subtitulo") and t >= at.get("subtitulo", e["from"] + 1.5):
        k = spring(t, at.get("subtitulo", e["from"] + 1.5), 120, 15)
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
    rotulo(ctx, layer, t, e.get("titulo", ""), at.get("rotulo", e["from"]), y=H * 0.14)
    items = e.get("items", [])
    n = len(items)
    if n == 0:
        return capa_salida(layer, t, e["to"])
    vertical = H > W  # layout en columna para 9:16
    if vertical:
        # columna
        _, _, _, zy1 = caja_segura()
        y0 = H * 0.14 + 110
        fila_h = min(260, (zy1 - y0) / n)
        y0 += ((zy1 - y0) - fila_h * n) / 2
        cx = W / 2
        for i, it in enumerate(items):
            t_in = at.get(f"item{i}", e["from"] + 0.3 + i * 0.2)
            k = spring(t, t_in, 110, 14)
            if k <= 0:
                continue
            sub, ds = grupo()   # el paso entero entra fundido
            yi = y0 + i * fila_h + fila_h * 0.1
            # número
            radio = min(fila_h * 0.35, 60)
            es_activo = k > 0.5
            ds.ellipse([cx - radio, yi, cx + radio, yi + 2 * radio],
                      fill=ACENTO if es_activo else (80, 80, 80, 255))
            fnt_n = ctx.fT(int(radio * 1.2), 800)
            ds.text((cx, yi + radio), str(i + 1), font=fnt_n, fill=BLANCO, anchor="mm")
            # texto a la izquierda del número (en columna: debajo)
            fnt = ctx.fX(int(min(46, fila_h * 0.18)), 700)
            ds.text((cx, yi + 2 * radio + 8), it.get("titulo", ""), font=fnt, fill=BLANCO, anchor="mt")
            y_fin = yi + 2 * radio + 8 + fnt.size
            if it.get("texto"):
                fnt_t = ctx.fX(int(min(32, fila_h * 0.13)), 400)
                ds.text((cx, y_fin + 6), it.get("texto", ""), font=fnt_t, fill=GRIS, anchor="mt")
                y_fin += 6 + fnt_t.size
            # conector: del texto al círculo siguiente (nunca atraviesa la letra)
            if i < n - 1 and yi + fila_h + fila_h * 0.1 - 10 > y_fin + 14:
                ds.line([cx, y_fin + 14, cx, yi + fila_h - 10],
                       fill=(120, 120, 120, 255), width=3)
            fundir(layer, sub, k)
    else:
        # fila
        zx0, _, zx1, _ = caja_segura()
        x0, w_disp = zx0, zx1 - zx0
        col_w = w_disp / n
        cy = H * 0.50
        for i, it in enumerate(items):
            t_in = at.get(f"item{i}", e["from"] + 0.3 + i * 0.2)
            k = spring(t, t_in, 110, 14)
            if k <= 0:
                continue
            sub, ds = grupo()   # el paso entero entra fundido
            radio = min(col_w * 0.18, 60)
            xi = x0 + (i + 0.5) * col_w - radio          # centrado en su columna
            es_activo = k > 0.5
            ds.ellipse([xi, cy - radio, xi + 2 * radio, cy + radio],
                      fill=ACENTO if es_activo else (80, 80, 80, 255))
            fnt_n = ctx.fT(int(radio * 1.2), 800)
            ds.text((xi + radio, cy), str(i + 1), font=fnt_n, fill=BLANCO, anchor="mm")
            # texto
            fnt = ctx.fX(int(unidad() * 0.042), 700)
            lineas = linewrap(it.get("titulo", ""), fnt, col_w * 0.85)
            for li, ln in enumerate(lineas):
                ds.text((xi + radio, cy + radio + 18 + li * (fnt.size + 4)),
                       ln, font=fnt, fill=BLANCO, anchor="mt")
            if it.get("texto"):
                fnt_t = ctx.fX(int(unidad() * 0.03), 400)
                ds.text((xi + radio, cy + radio + 26 + len(lineas) * (fnt.size + 4)),
                       it["texto"], font=fuente_que_cabe(ctx.fX, it["texto"], fnt_t.size, col_w * 0.9, 400),
                       fill=GRIS, anchor="mt")
            # conector hasta el borde del círculo siguiente
            if i < n - 1:
                ds.line([xi + 2 * radio + 10, cy, x0 + (i + 1.5) * col_w - radio - 10, cy],
                       fill=(120, 120, 120, 255), width=3)
            fundir(layer, sub, k)
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
        rotulo(ctx, layer, t, e["rotulo"], at.get("rotulo", e["from"]), y=H * 0.28)
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
    k = spring(t, t0 - 0.3, 130, 15)
    t_fin = t0 + total
    kf = spring(t, t_fin, 150, 13) if e.get("final") else 0.0
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
    if (e.get("miles", ","), e.get("decimal", ".")) != (",", "."):
        txt = txt.replace(",", "\0").replace(".", e.get("decimal", ".")).replace("\0", e.get("miles", ","))
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
    bloques = [("rotulo", 70 if e.get("rotulo") else 0), ("badge", tam * 1.12), ("antes", 100),
               ("precio", 160), ("codigo", 124 if e.get("codigo") else 0),
               ("vence", 50 if e.get("vence") else 0), ("cta", 120 if e.get("cta") else 0)]
    bloques = [b for b in bloques if b[1]]
    ys, f = pila([a for _, a in bloques], zy0 + 20, zy1 - 10, gap=26)
    Y = {n: y for (n, _), y in zip(bloques, ys)}
    px = lambda v: max(12, int(v * f))   # noqa: E731
    if e.get("rotulo"):
        rotulo(ctx, layer, t, e["rotulo"], at.get("rotulo", fr), y=Y["rotulo"] - px(22), tam=px(52))
    t_d = at.get("descuento", fr + 0.4)
    kd = spring(t, t_d, 170, 12)
    if kd > 0:
        sc = 1 + 0.12 * (1 - min(1, kd))   # aterriza desde un poco más grande
        d.text((W / 2, Y["badge"]), badge, font=ctx.fT(int(px(tam) * sc), 800),
               fill=ACENTO + (int(255 * clamp01(kd * 1.5)),), anchor="mm")
    t_t = at.get("tachado", fr + 1.3)
    ka = spring(t, t_t - 0.35, 130, 16)
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
        kp = spring(t, t_p, 140, 14)
        v = antes + (ahora - antes) * ease_out(clamp01((t - t_p) / 0.9))
        sc = 1 + 0.06 * max(0, 1 - abs((t - t_p - 0.9) / 0.15)) if t > t_p + 0.75 else 1
        cifra(d, (W / 2, Y["precio"]), _fmt_precio(v, e), ctx.fT(int(px(150) * sc), 800),
              BLANCO + (int(255 * clamp01(kp * 1.5)),), anchor="mm")
    if e.get("codigo"):
        t_c = at.get("codigo", t_p + 1.2)
        kc = spring(t, t_c, 130, 16)
        if kc > 0:
            fnt = ctx.fM(px(56), 700); txt = e["codigo"]
            cw_ = ctx.tmp.textlength(txt, font=fnt) + px(90); chh = px(104)
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
        kv = spring(t, t_v, 130, 16)
        if kv > 0:
            d.text((W / 2, Y["vence"]), e["vence"], font=ctx.fX(px(38), 600),
                   fill=GRIS + (int(255 * clamp01(kv * 1.4)),), anchor="mm")
    if e.get("cta"):
        t_b = at.get("cta", at.get("vence", t_p + 1.5) + 0.5)
        kb = spring(t, t_b, 150, 13)
        if kb > 0:
            fnt = ctx.fT(px(48), 800)
            bw_ = ctx.tmp.textlength(e["cta"], font=fnt) + px(120); bh_ = px(110)
            s_ = 0.9 + 0.1 * min(1.08, kb)
            x0, y0 = W / 2 - bw_ * s_ / 2, Y["cta"] - bh_ * s_ / 2
            al = int(255 * clamp01(kb * 1.4))
            d.rounded_rectangle([x0, y0, x0 + bw_ * s_, y0 + bh_ * s_], radius=int(bh_ * s_ / 2),
                                fill=ACENTO + (al,))
            d.text((W / 2, y0 + bh_ * s_ / 2), e["cta"], font=fnt, fill=BLANCO + (al,), anchor="mm")
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
        rotulo(ctx, layer, t, e["rotulo"], at.get("rotulo", e["from"]), y=H * 0.16)
    kv = spring(t, at.get("ventana", e["from"] + 0.2), 110, 15)
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
    arriba = bajo_rotulo(H * 0.16) + 16 if e.get("rotulo") else caja_segura()[1]
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
    dm.rounded_rectangle([0, 0, bw, bh + barra], radius=22, fill=PANEL + (255,))
    for k_ in range(3):
        dm.ellipse([22 + k_ * 26, 17, 36 + k_ * 26, 31], fill=(90, 90, 90, 255))
    if e.get("url"):
        dm.rounded_rectangle([120, 9, bw - 30, 39], radius=15, fill=PANEL2 + (255,))
        dm.text((140, 24), e["url"], font=ctx.fX(20, 500), fill=GRIS, anchor="lm")
    marco.paste(vista, (0, barra))
    if a_v < 255:
        marco.putalpha(marco.split()[3].point(lambda v: int(v * a_v / 255)))
    layer.alpha_composite(marco, (x0, y0))
    # cursor: viaja del objetivo anterior al actual en [at-0.6, at]; luego clic
    prev = (0.85, 0.92)
    pos = None
    for p_ in pasos:
        a_ = p_.get("at", 0)
        if t < a_ - 0.6:
            break
        k_ = smoothstep((t - (a_ - 0.6)) / 0.6)
        pos = (lerp(prev[0], p_.get("x", .5), k_), lerp(prev[1], p_.get("y", .5), k_), a_, p_)
        prev = (p_.get("x", .5), p_.get("y", .5))
    if pos:
        px = x0 + (pos[0] * bw - cx_) * z
        py = y0 + barra + (pos[1] * bh - cy_) * z
        pul = onda_clic(d, px, py, t, pos[2])
        cursor(d, px, py, 0.8 * (1 - 0.15 * pul))
        p_ = pos[3]
        if p_.get("texto") and t >= pos[2] + 0.15:
            kt = spring(t, pos[2] + 0.15, 140, 16)
            nxt_ = [q.get("at", 0) for q in pasos if q.get("at", 0) > pos[2]]
            fuera = clamp01((t - (nxt_[0] - 1.3)) / 0.4) if nxt_ else 0
            al = int(255 * clamp01(kt * 1.4) * (1 - fuera))
            if al > 0:
                fnt = fuente_que_cabe(ctx.fT, p_["texto"], 44, zx1_ - zx0_ - 80, 800)   # el botón cabe
                tw_ = ctx.tmp.textlength(p_["texto"], font=fnt) + 80
                yb = y0 + barra + bh + 60
                d.rounded_rectangle([W / 2 - tw_ / 2, yb, W / 2 + tw_ / 2, yb + 92], radius=46,
                                    fill=ACENTO + (al,))
                d.text((W / 2, yb + 46), p_["texto"], font=fnt, fill=BLANCO + (al,), anchor="mm")
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
        tw_ = int(ctx.tmp.textlength(txt, font=fnt)) + 4
        img = Image.new("RGBA", (tw_, int(fnt.size * 1.4)), (0, 0, 0, 0))
        ImageDraw.Draw(img).text((0, 0), txt, font=fnt, fill=col + (255,))
        # máscara que barre con borde DIFUMINADO (40 px): la letra se revela, no aparece entera
        borde = 40
        x_rev = (tw_ + borde) * kr
        rampa = np.clip((x_rev - np.arange(tw_)) / borde, 0, 1)
        a_ = np.asarray(img.split()[3], np.float32) * rampa[None, :]
        img.putalpha(Image.fromarray(a_.astype(np.uint8), "L"))
        vis = img
        layer.alpha_composite(vis, (int(x0 + pad + 12), int(yy)))
    return layer


SCENES={"apertura":sc_apertura,"canales":sc_canales,"medianoche":sc_medianoche,
        "chat":sc_chat,"leads":sc_leads,"handoff":sc_handoff,"pago":sc_pago,
        "listo":sc_listo,"pildoras":sc_pildoras,"hoy":sc_hoy,"recupera":sc_recupera,
        "remate":sc_remate,"final":sc_final,
        # Catálogo unificado (ver references/scene-patterns-from-internet.md)
        "bars":sc_bars,"gauge":sc_gauge,"ranking":sc_ranking,"stats":sc_stats,
        "timeline":sc_timeline,"quote":sc_quote,"versus":sc_versus,"confetti":sc_confetti,
        # Ronda 2: reactvideoeditor/remotion-templates (81 templates MIT)
        "typewriter":sc_typewriter,"kenburns":sc_kenburns,"pasos":sc_pasos,
        # Ronda 3: iart-ai/motion-skills (MIT)
        "countdown":sc_countdown,"oferta":sc_oferta,"demo":sc_demo,
        "rotulo_inferior":sc_rotulo_inferior}

# Escenas cuya composición está verificada también en horizontal (W > H).
# El resto se diseñó para 9:16: en 16:9 se solapan (verificado en frames).
# ================= MAIN =================
# hex_a_rgb vive en _comun (unica fuente; DRY). Reusar aquí:
from _comun import hex_a_rgb, info  # noqa: E402,F401  # sys.path ya apunta a ffmpeg_tools

def aplicar_brand(brand_path):
    """Instala la identidad del pack: colores, tipografías, logos y reglas.
    La lectura vive en _comun (colores_marca, fuente_marca, ruta_de_pack):
    la misma para todas las herramientas del kit."""
    global ACENTO, ACENTO_OSC, NEGRO, BLANCO, GRIS, LOGO, ISOTIPO, MARCA_NOMBRE, TRANSICIONES   # fuentes: vía globals()
    from _comun import colores_marca, fuente_marca, leer_pack, ruta_de_pack
    d = leer_pack(brand_path)
    c = colores_marca(brand_path)
    ACENTO, ACENTO_OSC, NEGRO, BLANCO, GRIS = (c["acento"], c["acento_oscuro"], c["negro"],
                                               c["blanco"], c["gris"])
    for rol, glob, defecto, gen in (("titulares", "FJ", "Plus Jakarta Sans", "sans-bold"),
                                    ("texto", "FM", "Montserrat", "sans"),
                                    ("etiquetas_mono", "MONO", "DejaVu Sans Mono", "mono")):
        hit = fuente_marca(brand_path, rol, defecto, gen)
        if hit: globals()[glob] = hit
    logos = d.get("logos") or {}
    LOGO = ruta_de_pack(brand_path, logos.get("logotipo") or logos.get("fondo_oscuro"))
    ISOTIPO = ruta_de_pack(brand_path, logos.get("isotipo"))
    MARCA_NOMBRE = d.get("nombre")
    TRANSICIONES = (d.get("reglas") or {}).get("transiciones", "libre")
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
def escala_segura(ctx,e,idx):
    """Factor de escala FIJO por escena para que su contenido quepa en la zona
    segura. Se mide el bbox del contenido en varios instantes de la escena
    (no por frame: un factor por frame bombearía)."""
    if idx in _ESCALA: return _ESCALA[idx]
    if e["tipo"] in A_SANGRE: _ESCALA[idx]=1.0; return 1.0   # fondo a sangre; el texto ya va en la zona segura
    fr,to=e["from"],e["to"]
    xs0,xs1,ys0,ys1=W,0,H,0
    for i in range(6):
        t=fr+0.25+(max(0.0,to-0.6-fr-0.25))*i/5
        bb=pintar(ctx,e,t).split()[3].point(lambda v:255 if v>110 else 0).getbbox()
        if bb:
            xs0=min(xs0,bb[0]); ys0=min(ys0,bb[1]); xs1=max(xs1,bb[2]); ys1=max(ys1,bb[3])
    cx,cy=W/2,H*0.45
    f=1.0
    if xs1>xs0:
        f=min(f,(cx-SAFE["left"])/max(1,cx-xs0),(W-SAFE["right"]-cx)/max(1,xs1-cx),
              (cy-SAFE["top"])/max(1,cy-ys0),(H-SAFE["bottom"]-cy)/max(1,ys1-cy))
    f=max(0.70,min(1.0,f))
    if f<0.995: print(f"  zona segura: escena {idx} ({e['tipo']}) escalada x{f:.3f}",flush=True)
    _ESCALA[idx]=f if f<0.995 else 1.0
    return _ESCALA[idx]

# Respiración de cámara: push-in lento y constante en toda escena que no mueve
# su propia cámara. Un plano asentado nunca queda congelado (fluidez.md) y el
# movimiento es uno solo para todo el catálogo, no una flotación por escena.
RESPIRA=0.01; RESPIRA_MAX=0.05   # 1 %/s (como un Ken Burns lento), tope 5 %
CAMARA_PROPIA={"final","kenburns","demo","rotulo_inferior"}   # ya se mueven o son overlay
QUIETAS={"rotulo_inferior"}   # quieta POR DISEÑO mientras se lee (lower third / overlay)

FLOTA_CAM=6    # px de flotación vertical: mueve TODOS los bordes (el push-in casi no
               # mueve lo que está cerca de su centro)

def respiracion(e,t):
    """(escala, dy) de la cámara de la escena: push-in lento + flotación suave."""
    if ALFA or e["tipo"] in CAMARA_PROPIA or not e.get("respira",True): return 1.0,0.0
    dt=max(0.0,t-e["from"])
    return 1+min(RESPIRA_MAX,RESPIRA*dt), FLOTA_CAM*math.sin(2*math.pi*0.3*dt)

def encajar(layer,f,dy=0.0):
    """Escala la capa alrededor de (W/2, 0.45H) y la desplaza dy px, con
    precisión sub-píxel (afín: sin escalones de 1 px en un movimiento lento)."""
    if abs(f-1)<0.0005 and abs(dy)<0.01: return layer
    cx,cy=W/2,H*0.45
    return layer.transform((W,H),Image.AFFINE,(1/f,0,cx-cx/f,0,1/f,cy-(cy+dy)/f),
                           resample=Image.BICUBIC)

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
    fr,dy=respiracion(s,t)
    layer=encajar(pintar(ctx,s,t).copy(),escala_segura(ctx,s,si)*fr,dy)
    if si in manchas_ok and t-s["from"]<0.9:
        ep=escenas[si-1]
        fp,dyp=respiracion(ep,t)
        prev=encajar(pintar(ctx,ep,t),escala_segura(ctx,ep,si-1)*fp,dyp)
        fx=s.get("transicionX",0.5); fy=s.get("transicionY",0.45)
        mask=mancha_mask(ctx,t,s["from"],0.9,fx,fy)
        inv=Image.eval(mask,lambda v:255-v)
        nada=Image.new("RGBA",(W,H),(0,0,0,0))
        bg.alpha_composite(Image.composite(prev,nada,inv))
        bg.alpha_composite(Image.composite(layer,nada,mask))
    else:
        if si>0 and t-s["from"]<SOLAPE:   # la anterior termina de irse DEBAJO de la nueva
            ep=escenas[si-1]
            fp,dyp=respiracion(ep,t)
            bg.alpha_composite(encajar(pintar(ctx,ep,t).copy(),escala_segura(ctx,ep,si-1)*fp,dyp))
        if si>0 and t-s["from"]<0.03:   # corte seco con micro-fade de 30 ms (sin pop)
            layer=capa_entrada(layer,t,s["from"])
        bg.alpha_composite(layer)
    if dur-t<0.8:   # fundido al cierre con ease-in-out: no arranca a velocidad plena
        k=smoothstep(clamp01((0.8-(dur-t))/0.8))
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
    if n<=1: return componer(ctx,escenas,dur,t,manchas_ok)
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
    ok=[]; pedidas=[i for i,e in enumerate(escenas) if i>0 and e.get("transicion")=="mancha"]
    for i in pedidas:
        if len(ok)<maximo: ok.append(i)
    if avisar and len(pedidas)>len(ok):
        print(f"AVISO: {len(pedidas)} transiciones 'mancha' pedidas; se respetan {len(ok)} "
              f"(máximo {maximo}, ver references/fluidez.md); el resto, corte seco",flush=True)
    return set(ok)

_W={}
def _init_worker(brand_path,acento,plan,maximo_cfg,safe=None,escalas=None,alfa=False,
                 geo=(1080,1920,151)):
    """Inicializa un proceso de render (portable: también con 'spawn' en Windows/macOS)."""
    global ACENTO, ACENTO_OSC, ALFA, W, H, MARGEN
    ALFA=alfa; W,H,MARGEN=geo
    if brand_path:
        import io, contextlib
        with contextlib.redirect_stdout(io.StringIO()): aplicar_brand(brand_path)
    elif acento:
        ACENTO=hex_a_rgb(acento); ACENTO_OSC=tuple(max(0,int(c*0.65)) for c in ACENTO)
    if safe: SAFE.update(safe)
    if escalas: _ESCALA.update(escalas)
    esc=sorted(plan["escenas"],key=lambda s:s["from"])
    maximo=maximo_cfg if maximo_cfg is not None else (1 if TRANSICIONES=="corte_seco" else 2)
    _W.update(ctx=Ctx(),esc=esc,dur=plan["duracion"],ok=presupuesto_manchas(esc,maximo,avisar=False))

def _render_worker(job):
    fi,fp,fps,blur,obt=job
    frame_con_blur(_W["ctx"],_W["esc"],_W["dur"],fi/fps,fps,blur,obt,_W["ok"]).save(fp)
    return fi

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
    MARGEN=max(SAFE["left"],int(W*0.05))
    _ESCALA.clear()
    return plataforma

def render(plan_path,plan,out,a):
    """Renderiza un plan ya cargado a `out` (.mp4; .webm/.mov = con alfa)."""
    global ACENTO, ACENTO_OSC, ALFA, W, H
    ALFA=os.path.splitext(out)[1].lower() in (".webm",".mov")
    try:
        W,H=(int(v) for v in str(a.tamano or plan.get("tamano","1080x1920")).lower().split("x"))
    except ValueError:
        sys.exit("ERROR: tamano debe ser ANCHOxALTO, ej. 1920x1080")
    from _comun import resolver_pack
    brand_path = resolver_pack(a.brand or plan.get("brand"))   # marca SOLO si se pide
    if brand_path:
        aplicar_brand(brand_path)
    elif plan.get("acento"):   # modo libre: el plan puede fijar su acento
        ACENTO=hex_a_rgb(plan["acento"]); ACENTO_OSC=tuple(max(0,int(c*0.65)) for c in ACENTO)
    formato(W,H,a.plataforma or plan.get("plataforma"))
    ctx=Ctx(); fps=a.fps
    dur=plan["duracion"]; n=int(dur*fps)
    escenas=preparar_escenas(ctx,plan)
    maximo=plan.get("mancha_max", 1 if TRANSICIONES=="corte_seco" else 2)
    manchas_ok=presupuesto_manchas(escenas,maximo)
    tmpd=f"{out}.frames"; os.makedirs(tmpd,exist_ok=True)
    print(f"{n} frames, {len(escenas)} escenas, blur x{a.blur}"+(" · overlay con alfa" if ALFA else ""),flush=True)
    pend=[fi for fi in range(n) if a.force or not os.path.exists(f"{tmpd}/f_{fi:04d}.png")]
    if len(pend)<n: print(f"  retoma: {n-len(pend)} frames ya existen",flush=True)
    jobs=[(fi,f"{tmpd}/f_{fi:04d}.png",fps,a.blur,a.obturador) for fi in pend]
    if a.jobs<=1:
        for i,j in enumerate(jobs):
            frame_con_blur(ctx,escenas,dur,j[0]/fps,fps,a.blur,a.obturador,manchas_ok).save(j[1])
            if i%150==0: print(f"  {i}/{len(jobs)}",flush=True)
    else:
        from multiprocessing import Pool
        init=(brand_path if brand_path else None, None if brand_path else plan.get("acento"),
              plan, plan.get("mancha_max"), dict(SAFE), dict(_ESCALA), ALFA, (W,H,MARGEN))
        with Pool(a.jobs,initializer=_init_worker,initargs=init) as pool:
            for i,_ in enumerate(pool.imap_unordered(_render_worker,jobs,chunksize=4)):
                if i%150==0: print(f"  {i}/{len(jobs)}",flush=True)
    if ALFA:
        for av in revisar_overlay(tmpd,n,fps): print("AVISO overlay:",av,flush=True)
    print("frames ok, codificando…",flush=True)
    from _comun import codificar_frames   # BT.709 exacto; .webm/.mov = con alfa
    res=codificar_frames(f"{tmpd}/f_%04d.png", fps, out, crf=20)
    if res.get("alfa"):
        print(f"  alfa verificado: el frame central decodifica {res['transparente']:.0%} transparente",flush=True)
    print("OK",out)

MEDIOS=("imagen","captura")   # campos del plan que apuntan a un archivo

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
    if m and isinstance(m.get("at"),dict) and isinstance(e.get("at",{}),dict):
        k=(e["to"]-e["from"])/max(0.1,m["to"]-m["from"])
        at=dict(e.get("at") or {})
        for clave,v in m["at"].items():
            if clave not in at: at[clave]=_escalar_t(v,k,e["from"])
        e["at"]=at
    return e

def error_de_escena(e,i,ex):
    """Un campo que falta, explicado (nunca un KeyError crudo): qué escena,
    qué campo y un ejemplo completo de esa escena para copiar."""
    tipo=e.get("tipo"); campo=ex.args[0] if isinstance(ex,KeyError) and ex.args else None
    que=f"falta el campo `{campo}`" if campo else f"{type(ex).__name__}: {ex}"
    ej=json.dumps(muestra(tipo) or {},ensure_ascii=False)
    return (f"ERROR: escena {i+1} ({tipo}, {e.get('from')}–{e.get('to')} s): {que}.\n"
            f"  Ejemplo completo de `{tipo}` (scripts/escenas_muestra.json):\n  {ej}")

def preparar_escenas(ctx,plan):
    """Escenas del plan listas para componer: tiempos completados desde la
    muestra, en orden, y cada una compuesta UNA vez (escala_segura) para fallar
    en segundos con un mensaje claro, no tras minutos de render. Una sola
    puerta para render_plan y medir_animacion --plan."""
    escenas=sorted((completar_escena(e,i) for i,e in enumerate(plan["escenas"])),key=lambda s:s["from"])
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

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("plan"); ap.add_argument("-o","--out",required=True,
                    help="salida .mp4 (o .webm/.mov = overlay con alfa); con --datos admite {campo}")
    ap.add_argument("--fps",type=int,default=30)
    ap.add_argument("--brand", default=None,
                    help="brand pack (brand/*.json); el plan también acepta campo \"brand\"")
    ap.add_argument("--blur",type=int,default=1,
                    help="sub-frames de motion blur (1=off, 4-6 para entrega final)")
    ap.add_argument("--obturador",type=float,default=0.5,
                    help="ángulo de obturador como fracción del frame (0.5 = 180°)")
    ap.add_argument("--jobs",type=int,default=max(1,(os.cpu_count() or 2)-1),
                    help="procesos de render en paralelo (default: núcleos-1)")
    ap.add_argument("--plataforma",default=None,
                    help="zona segura: vertical (Reels+TikTok+Shorts, default), reels, tiktok, shorts, ninguna")
    ap.add_argument("--force",action="store_true",
                    help="re-renderiza todos los frames aunque ya existan")
    ap.add_argument("--tamano",default=None,
                    help="ANCHOxALTO (default 1080x1920 o el campo \"tamano\" del plan; 1920x1080 para 16:9)")
    ap.add_argument("--datos",help="tabla CSV/TSV/JSON: un video por fila; el plan usa {columna}")
    ap.add_argument("--fila",type=int,help="con --datos: renderizar solo esta fila (1 = primera) "
                    "para verificarla antes del lote")
    a=ap.parse_args()
    plan=json.load(open(a.plan, encoding="utf-8"))
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
