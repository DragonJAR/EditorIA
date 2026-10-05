#!/usr/bin/env python3
"""EditorIA plan renderer — ejecuta un plan.json con fluidez total.
Identidad desde brand pack opcional (--brand o campo "brand" en el plan);
sin pack, usa los defaults neutros del renderer.
Uso: python render_plan.py plan.json -o salida.mp4 [--fps 30] [--brand brand/otro.json]
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
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
    s=max(8,int(s)); key=(p,s,w)
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

def capa_salida(layer,t,to_):
    """Salida anticipada 0.5s: fade + deriva."""
    s=prog(t,to_-0.5,to_,ease_in_out)
    if s<=0: return layer
    a=layer.split()[3].point(lambda v:int(v*(1-s)))
    layer.putalpha(a)
    return layer

def titular(ctx,layer,t,lineas,ats,tam=120,cy=None,word_gap=36,line_gap=1.18,maxw=None):
    """Titular cinético: cada palabra entra con resorte en su `at`, con escala
    real (1.16 -> 1.0, el overshoot del resorte da el asentamiento) y elevación.
    Auto-fit sobre el ancho REAL de la línea (palabras + huecos)."""
    d=ImageDraw.Draw(layer)
    maxw=maxw or (W-2*MARGEN)
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
            at=ats[wi] if wi < len(ats) else ats[-1]; wi+=1
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
    if t<at: return 0
    k=spring(t,at,140,16)
    al=int(255*clamp01(k*1.5))
    d=ImageDraw.Draw(layer)
    sg=segs(texto); fnt=ctx.fX(tam,700)
    yy=(y or H*0.30)+(1-min(1,k))*24
    draw_seg(d,(W/2,yy),sg,fnt,color+(al,),ACENTO+(al,),anchor="ma")
    return k

def tarjeta(ctx,img,x,y,w,h,radio=28,alpha=255):
    d=ImageDraw.Draw(img)
    if h < 2*radio or w < 2*radio:  # rounded_rectangle falla si h/w < 2*radio
        d.rectangle([x,y,x+w,y,h],fill=PANEL+(alpha,))
        d.rectangle([x,y,x+w,y+h],outline=(255,255,255,28))
        return
    d.rounded_rectangle([x,y,x+w,y+h],radius=radio,fill=PANEL+(alpha,))
    d.rounded_rectangle([x,y,x+w,y+h],radius=radio,outline=(255,255,255,28))

# ───────────────────────── primitivas DRY para escenas de datos/UI ─────────────────────────
# Cada nueva escena se compone de estas primitivas. DRY: las escenas NO duplican lógica
# de barras / anillos / círculos / partículas / grids; la llaman aquí.

def barra_h(d, x, y, ancho, alto, fraccion, color, radio=None):
    """Barra horizontal rellenable: track + fill con esquinas redondeadas.
    `fraccion` ∈ [0, 1] controla el porcentaje visible (la animación lo interpola).
    DRY: la usan `bars`, `ranking`, `progreso`, `leads.puntaje`."""
    radio = radio or alto // 2
    if ancho < 2 * radio or alto < 2 * radio:
        radio = min(radio, min(ancho, alto) // 2)
    # track
    d.rounded_rectangle([x, y, x + ancho, y + alto], radius=radio, fill=(255, 255, 255, 18))
    # fill
    f = clamp01(fraccion)
    if f <= 0:
        return
    fill_w = max(1, int(ancho * f))
    if fill_w >= ancho - 2:
        d.rounded_rectangle([x, y, x + fill_w, y + alto], radius=radio, fill=color)
    else:
        d.rectangle([x, y, x + fill_w, y + alto], fill=color)
        d.pieslice([x, y, x + 2 * radio, y + 2 * radio], 90, 270, fill=color)
        d.pieslice([x + fill_w - 2 * radio, y, x + fill_w, y + 2 * radio], 270, 90, fill=color)


def cuenta_up(desde, hasta, t, t0, dur=0.8, fmt="{:,}"):
    """Cuenta animada de `desde` a `hasta` en `dur` segundos desde `t0`.
    Devuelve el string listo para imprimir (con separadores).
    DRY: la usan `stats`, `gauge`, `ranking`, `bars`, `remate`.
    Si `desde` o `hasta` no son numericos (ej. "10K+", "<5s"), se devuelve tal cual
    sin animar — comun en stat cards pre-formateados."""
    if not isinstance(desde, (int, float)) or not isinstance(hasta, (int, float)):
        # Sin animacion (stat card pre-formateado): muestra el `hasta` siempre
        return str(hasta)
    if t < t0:
        return fmt.format(desde)
    p = clamp01((t - t0) / max(dur, 1e-6))
    p = ease_out(p)
    v = desde + (hasta - desde) * p
    if isinstance(hasta, int) and isinstance(desde, int):
        return fmt.format(int(round(v)))
    return fmt.format(v)


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


def text_reveal(d, text, fnt, x, y, t, t0, dur, color, fill=None, anchor="la"):
    """Dibuja `text` carácter a carácter (typewriter). `t-t0` controla cuántos
    caracteres ya están "escritos". Si el cursor se quiere visible al final,
    pasar `cursor="|"` y dibujarlo fuera.

    DRY: la usan `sc_typewriter`, `sc_callout` (futuro) y `pildoras` (futuro).
    """
    if t < t0:
        return 0  # aún no aparece
    p = clamp01((t - t0) / max(dur, 1e-6))
    p = ease_out(p)
    n_visible = int(math.ceil(len(text) * p))
    visible = text[:n_visible]
    if not visible:
        return 0
    # dibujar los caracteres visibles uno a uno (cada uno con leve delay natural)
    tmp = ImageDraw.Draw(Image.new("L", (10, 10)))
    cursor_x = x
    for ch in visible:
        d.text((cursor_x, y), ch, font=fnt, fill=fill or color, anchor=anchor)
        cursor_x += tmp.textlength(ch, font=fnt)
    return n_visible


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


def cursor(d, x, y, escala=1.0, color=None):
    """Flecha de puntero con la punta en (x, y). DRY: `pago`, `demo`."""
    s = 54 * escala
    d.polygon([(x, y), (x, y + s * 1.4), (x + s * 0.45, y + s), (x + s * 0.7, y + s * 1.5),
               (x + s * 0.9, y + s * 1.35), (x + s * 0.65, y + s * 0.85), (x + s, y + s)],
              fill=(color or BLANCO) + (255,), outline=(0, 0, 0, 160))


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


def odometro(layer, texto, texto_prev, rodar, cx, cy, fnt, color):
    """Cifras tipo odómetro centradas en (cx, cy): cada dígito que cambia rueda
    de `texto_prev` a `texto` según `rodar` ∈ [0, 1]; los demás quedan quietos.
    Celdas de ancho fijo (tabular). DRY: `countdown` y contadores de rollo."""
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
            off = alto * ease_out(rodar)
            dc.text((anchos[i] / 2, alto / 2 - off), pc, font=fnt, fill=color, anchor="mm")
            dc.text((anchos[i] / 2, alto / 2 + alto - off), c, font=fnt, fill=color, anchor="mm")
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
    if t < cambio:
        cy=H*0.44+flota(t,e["at"]["p1"][-1]+0.5,5,0.45)
        titular(ctx,layer,t,e["texto1"],e["at"]["p1"],tam=150,cy=cy)
    else:
        cy=H*0.44+flota(t,e["at"]["p2"][-1]+0.5,5,0.45)
        titular(ctx,layer,t,e["texto2"],e["at"]["p2"],tam=124,cy=cy)
    return capa_salida(layer,t,e["to"])

def sc_canales(ctx,e,t):
    layer=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(layer)
    at=e["at"]; junta=prog(t,at["junta"]-0.2,at["junta"]+0.35)
    rotulo(ctx,layer,t,e["rotulo"],at["rotulo"],y=H*0.20)
    # marca que sube y se encoge (grupo logo+texto centrado)
    k=spring(t,at["marca"],90,14)
    if k>0:
        my=lerp(H*0.52,H*0.36,junta); sc=lerp(1.0,0.55,junta)*k
        fnt_m=ctx.fT(int(110*sc),800)
        tw=ctx.tmp.textlength(e["marca"],font=fnt_m)
        iso_ok=ctx.iso is not None and es_marca_del_pack(e["marca"])
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
        sx,sy=W/2+ang*W*0.3,H*0.68
        fy=H*0.58-120+i*150
        x=lerp(sx,W/2,junta); y=lerp(sy,fy,junta)
        w=lerp(300,880,junta); h=124
        sc2=k2
        ww,hh=int(w*sc2),int(h*sc2)
        if ww<10: continue
        card=Image.new("RGBA",(ww,hh),(0,0,0,0)); dc=ImageDraw.Draw(card)
        dc.rounded_rectangle([0,0,ww,hh],radius=30,fill=PANEL2+(255,))
        dc.rounded_rectangle([0,0,ww,hh],radius=30,outline=(255,255,255,28),width=2)
        # icono canal (círculo con inicial) — centrado vertical exacto (62 = 124/2)
        dc.ellipse([28,24,104,100],fill=ACENTO+(255,))
        dc.text((66,62),c["canal"][0].upper(),font=ctx.fT(44,800),fill=BLANCO,anchor="mm")
        if junta>0.4:
            dc.text((130,32),c["nombre"],font=ctx.fX(34,800),fill=BLANCO)
            dc.text((130,74),c["texto"][:34],font=ctx.fX(27,400),fill=GRIS)
        card=card.rotate((1-junta)*ang*8,expand=True,resample=Image.BICUBIC)
        fy_float=flota(t,c["at"]+1.2,5,0.4) if junta>0.9 else 0
        layer.alpha_composite(card,(int(x-card.width/2),int(y-card.height/2+fy_float)))
    return capa_salida(layer,t,e["to"])

def sc_medianoche(ctx,e,t):
    layer=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(layer)
    rotulo(ctx,layer,t,e["rotulo"],e["from"]+0.1,y=H*0.20)
    k=spring(t,e["from"],110,13)
    if k>0:
        tw,th=560,1140; sc=0.82*(0.8+0.2*min(1,k))
        ph=Image.new("RGBA",(tw,th),(0,0,0,0)); dp=ImageDraw.Draw(ph)
        dp.rounded_rectangle([0,0,tw,th],radius=86,fill=(12,12,12,255))
        dp.rounded_rectangle([18,18,tw-18,th-18],radius=70,fill=(16,22,34,255))
        dp.rounded_rectangle([tw/2-85,42,tw/2+85,90],radius=24,fill=(0,0,0,255))
        dp.text((tw/2,190),e["fecha"],font=ctx.fX(30,600),fill=(255,255,255,200),anchor="ma")
        dp.text((tw/2,330),e["hora"],font=ctx.fT(150,700),fill=BLANCO,anchor="ma")
        nots=e["notificaciones"]
        for i,n in enumerate(nots):
            kn=spring(t,n["at"],120,16)
            if kn<=0: continue
            despues=sum(1 for m in nots[i+1:] if t>=m["at"])
            ny=500+despues*170+(1-min(1,kn))*-90
            nw=Image.new("RGBA",(tw-44,140),(0,0,0,0)); dn=ImageDraw.Draw(nw)
            dn.rounded_rectangle([0,0,tw-44,140],radius=30,fill=(255,255,255,36))
            dn.ellipse([22,38,86,102],fill=ACENTO+(255,))
            dn.text((54,70),n["canal"][0].upper(),font=ctx.fT(34,800),fill=BLANCO,anchor="mm")
            dn.text((110,52),n["titulo"],font=ctx.fX(27,800),fill=BLANCO)
            dn.text((110,92),n["texto"][:30],font=ctx.fX(24,400),fill=(255,255,255,190))
            a=nw.split()[3].point(lambda v:int(v*clamp01(kn*1.5))); nw.putalpha(a)
            ph.alpha_composite(nw,(22,int(ny)))
        ph=ph.resize((int(tw*sc),int(th*sc)),Image.LANCZOS)
        # inclinación 3D aproximada con shear
        layer.alpha_composite(ph,(int(W/2-ph.width/2),int(H*0.62-ph.height/2)))
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
    msgs=[]; reloj=t_rot+0.4
    for m in e.get("mensajes",[]):
        ia=m.get("de")!="cliente"
        esc=m.get("escribe",0.7 if ia else 0.0)
        tm=m["at"] if "at" in m else reloj+m.get("pausa",0.6)+esc
        lineas=wrap(m.get("texto",""),fnt,680,ctx.tmp)
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
    limite=H*0.70 if lk and t>=lk.get("at",1e9)-0.4 else H-SAFE["bottom"]-20
    y=y0-max(0.0,y0+alto-limite)
    for mm in msgs:
        k=spring(t,mm["at"],140,15)
        lado_x=lambda w_: 90 if not mm["ia"] else W-90-w_
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
        cw,chh=760,150; x=(W-cw)/2; yy=H*0.72
        d.rounded_rectangle([x,yy,x+cw,yy+chh],radius=28,fill=ACENTO+(int(235*min(1,k)),))
        d.text((x+40,yy+34),lk.get("titulo",""),font=ctx.fX(34,800),fill=BLANCO)
        d.text((x+40,yy+84),lk.get("monto",""),font=ctx.fT(44,800),fill=BLANCO)
    return capa_salida(layer,t,e["to"])

def sc_leads(ctx,e,t):
    layer=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(layer)
    at=e["at"]
    rotulo(ctx,layer,t,e["rotulo"],at["rotulo"],y=H*0.20)
    d.text((W/2,H*0.24),e["total"],font=ctx.fM(36,700),fill=ACENTO,anchor="ma")
    y0=H*0.32
    colores_temp={"Caliente":ACENTO,"Tibio":(200,140,40),"Frío":(90,140,200)}
    for i,f in enumerate(e["filas"]):
        k=spring(t,e["from"]+0.4+i*0.35,130,15)
        if k<=0: continue
        yy=y0+i*128+(1-min(1,k))*-50
        hl=f["temp"] in at and t>=at[f["temp"]]
        tarjeta(ctx,layer,90,yy,W-180,112,alpha=int(255*clamp01(k*1.5)))
        if hl:
            d.rounded_rectangle([90,yy,W-90,yy+112],radius=28,
                                outline=colores_temp[f["temp"]]+(255,),width=4)
        d.ellipse([120,yy+24,184,yy+88],fill=colores_temp[f["temp"]]+(255,))
        d.text((152,yy+56),f["nombre"][0],font=ctx.fT(36,800),fill=BLANCO,anchor="mm")
        d.text((210,yy+24),f["nombre"],font=ctx.fX(32,800),fill=BLANCO)
        d.text((210,yy+62),f["etapa"],font=ctx.fX(26,400),fill=GRIS)
        # barra de puntaje
        bw=(f["puntaje"]/130)*260
        d.rounded_rectangle([W-420,yy+44,W-160,yy+68],radius=12,fill=(60,60,60,255))
        d.rounded_rectangle([W-420,yy+44,W-420+bw*min(1,k),yy+68],radius=12,
                            fill=colores_temp[f["temp"]]+(255,))
    return capa_salida(layer,t,e["to"])

def sc_handoff(ctx,e,t):
    layer=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(layer)
    at=e["at"]
    rotulo(ctx,layer,t,e["rotulo"],at["rotulo"],y=H*0.20)
    k=spring(t,at["persona"],120,14)
    if k>0:
        tarjeta(ctx,layer,110,H*0.30,W-220,220,alpha=int(255*min(1,k)))
        d.ellipse([160,H*0.30+60,260,H*0.30+160],fill=ACENTO+(255,))
        d.text((210,H*0.30+110),e["iniciales"],font=ctx.fT(44,800),fill=BLANCO,anchor="mm")
        d.text((300,H*0.30+52),e["cliente"],font=ctx.fX(40,800),fill=BLANCO)
        d.text((300,H*0.30+102),e["temp"],font=ctx.fM(30,700),fill=(200,140,40))
        d.text((300,H*0.30+142),e["nota"],font=ctx.fX(28,400),fill=GRIS)
    y=H*0.30+270
    for i,c in enumerate(e["contexto"]):
        kc=spring(t,at["contexto"]+i*0.4,130,15)
        if kc<=0: continue
        yy=y+i*96+(1-min(1,kc))*-40
        d.text((140,yy),c["k"],font=ctx.fM(30,700),fill=ACENTO)
        d.text((140,yy+40),c["v"][:44],font=ctx.fX(30,400),fill=BLANCO)
    return capa_salida(layer,t,e["to"])

def sc_pago(ctx,e,t):
    layer=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(layer)
    at=e["at"]
    rotulo(ctx,layer,t,e["rotulo"],at["rotulo"],y=H*0.20)
    k=spring(t,at["comprobante"],110,13)
    if k>0:
        cw,chh=720,420; x=(W-cw)/2; yy=H*0.36+(1-min(1,k))*-80
        tarjeta(ctx,layer,x,yy,cw,chh,radio=32,alpha=int(255*min(1,k)))
        d.text((W/2,yy+80),e["monto"],font=ctx.fT(96,800),fill=BLANCO,anchor="ma")
        d.text((W/2,yy+190),e["cliente"],font=ctx.fX(34,600),fill=BLANCO,anchor="ma")
        d.text((W/2,yy+240),e["detalle"],font=ctx.fX(28,400),fill=GRIS,anchor="ma")
        d.line([(x+80,yy+300),(x+cw-80,yy+300)],fill=(255,255,255,40),width=2)
    if t>=at["cursor"]:
        # cursor que se mueve y pulsa
        ck=prog(t,at["cursor"],at["toque"])
        cx=lerp(W*0.3,W*0.62,ease_in_out(ck)); cy=lerp(H*0.85,H*0.62,ease_in_out(ck))
        pk=onda_clic(d,cx,cy,t,at["toque"])
        cursor(d,cx,cy,1+0.25*math.sin((t-at["toque"])*20)*pk)
    return capa_salida(layer,t,e["to"])

def sc_listo(ctx,e,t):
    layer=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(layer)
    k=spring(t,e["at"]["listo"],90,10)
    if k>0:
        # estallido de partículas en anillo
        for i in range(24):
            a=i/24*math.pi*2
            rr=180*ease_out(clamp01((t-e["at"]["listo"])/0.6))
            x=W/2+rr*math.cos(a); y=H*0.5+rr*math.sin(a)
            al=int(255*(1-clamp01((t-e["at"]["listo"])/0.8)))
            d.ellipse([x-10,y-10,x+10,y+10],fill=ACENTO+(al,))
        # check
        s=int(120*min(1,k))
        d.ellipse([W/2-110,H*0.5-110,W/2+110,H*0.5+110],fill=ACENTO+(255,))
        d.line([(W/2-52,H*0.5),(W/2-16,H*0.5+38)],fill=BLANCO,width=22)
        d.line([(W/2-16,H*0.5+38),(W/2+58,H*0.5-44)],fill=BLANCO,width=22)
        d.text((W/2,H*0.5+190),e["texto"],font=ctx.fT(110,800),fill=BLANCO,anchor="ma")
    return capa_salida(layer,t,e["to"])

def sc_pildoras(ctx,e,t):
    layer=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(layer)
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
    layer=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(layer)
    at=e["at"]
    rotulo(ctx,layer,t,e["rotulo"],at["rotulo"],y=H*0.20)
    d.text((W/2,H*0.21),e["fecha"],font=ctx.fX(34,400),fill=GRIS,anchor="ma")
    # contador
    ck=prog(t,at["cuenta"],at["cuenta"]+0.8)
    d.text((W/2,H*0.32),str(int(e["cuenta"]*ease_out(ck))),font=ctx.fT(130,800),
           fill=ACENTO,anchor="ma")
    y0=H*0.44
    for i,tj in enumerate(e["tarjetas"]):
        k=spring(t,e["from"]+0.6+i*0.3,130,15)
        if k<=0: continue
        col=i%2; row=i//2
        x=90+col*(W/2-70); yy=y0+row*190+(1-min(1,k))*-50
        tarjeta(ctx,layer,x,yy,W/2-110,160,alpha=int(255*min(1,k)))
        if tj.get("alerta"):
            d.rounded_rectangle([x,yy,x+W/2-110,yy+160],radius=28,
                                outline=ACENTO+(255,),width=4)
        d.text((x+30,yy+28),tj["titulo"],font=ctx.fX(30,800),fill=BLANCO)
        d.text((x+30,yy+70),tj["detalle"][:30],font=ctx.fX(26,400),fill=GRIS)
        if tj.get("n"):
            d.ellipse([x+W/2-200,yy+28,x+W/2-140,yy+88],fill=ACENTO+(255,))
            d.text((x+W/2-170,yy+58),str(tj["n"]),font=ctx.fT(32,800),fill=BLANCO,anchor="mm")
    return capa_salida(layer,t,e["to"])

def sc_recupera(ctx,e,t):
    layer=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(layer)
    at=e["at"]
    rotulo(ctx,layer,t,e["rotulo"],at["rotulo"],y=H*0.20)
    d.text((W/2,H*0.26),e["resumen"],font=ctx.fX(36,600),fill=BLANCO,anchor="ma")
    # barra de progreso arrastrada por cursor
    rk=prog(t,at["cursor"],at["recupera"])
    bx,by,bw=140,H*0.5,800
    d.rounded_rectangle([bx,by,bx+bw,by+44],radius=22,fill=(60,60,60,255))
    d.rounded_rectangle([bx,by,bx+bw*ease_in_out(rk),by+44],radius=22,fill=ACENTO+(255,))
    cx=bx+bw*ease_in_out(rk)
    d.ellipse([cx-34,by-12,cx+34,by+56],fill=BLANCO+(255,))
    if t>=at["pagado"]:
        k=spring(t,at["pagado"],120,14)
        tarjeta(ctx,layer,140,H*0.62,800,220,radio=30,alpha=int(255*min(1,k)))
        d.text((540,H*0.62+70),"PAGADO",font=ctx.fT(64,800),fill=(80,220,120),anchor="ma")
        d.text((540,H*0.62+140),e["monto"],font=ctx.fT(54,800),fill=BLANCO,anchor="ma")
    else:
        d.text((540,H*0.62+90),e["cliente"],font=ctx.fX(36,600),fill=GRIS,anchor="ma")
        d.text((540,H*0.62+140),e["hace"],font=ctx.fX(28,400),fill=GRIS,anchor="ma")
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
    k=spring(t,g,80,9)
    if k>0:
        sc=2.2-1.2*min(1,k)
        fnt=ctx.fT(int(300*sc),800)
        tw=ctx.tmp.textlength(e["gigante"],font=fnt)
        # glow
        # glow: lienzo dimensionado por el bbox real del texto (nunca recorta)
        bb=fnt.getbbox(e["gigante"],anchor="ma"); pad=90
        glow=Image.new("RGBA",(bb[2]-bb[0]+2*pad,bb[3]-bb[1]+2*pad),(0,0,0,0))
        ImageDraw.Draw(glow).text((pad-bb[0],pad-bb[1]),e["gigante"],font=fnt,
                                  fill=ACENTO+(int(110*clamp01(k*1.4)),),anchor="ma")
        glow=glow.filter(ImageFilter.GaussianBlur(30))
        layer.alpha_composite(glow,(int(W/2+bb[0]-pad),int(H*0.62+bb[1]-pad)))
        d.text((W/2,H*0.62),e["gigante"],font=fnt,
               fill=BLANCO+(int(255*clamp01(k*1.4)),),anchor="ma")
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
            fnt_m=ctx.fT(int(120*min(1,k)*push),800)
            d.text((W/2,H*0.40+fy),e["marca"],font=fnt_m,
                   fill=BLANCO+(int(255*clamp01(k*1.4)),),anchor="mm")
    if t>=at["lema"]:
        rotulo(ctx,layer,t,e["lema"],at["lema"],y=H*0.58+fy*0.6,tam=52)
    if t>=at["boton"]:
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
    return layer  # sin salida: fundido global al final


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
    ancho_total = W * 0.78
    gap = 36
    bw = (ancho_total - gap * (n - 1)) // n
    base_y = H * 0.78
    max_h = H * 0.46
    for i, b in enumerate(barras):
        t_in = at.get(f"bar{i}", e["from"] + 0.2 + i * 0.1)
        k = spring(t, t_in, 110, 14)
        if k <= 0:
            continue
        fraccion = clamp01(b.get("valor", 0) / max(1, b.get("max", 100)))
        col = b.get("color")
        if col is None:
            col = ACENTO if b.get("acento") else BLANCO
        # track (gris) + fill con color
        x0 = (W - ancho_total) // 2 + i * (bw + gap)
        # fondo del track
        d.rounded_rectangle([x0, base_y - max_h, x0 + bw, base_y], radius=18, fill=(255, 255, 255, 18))
        # fill con animación
        fill_h = max_h * fraccion * k
        if fill_h > 0:
            d.rounded_rectangle([x0, base_y - fill_h, x0 + bw, base_y], radius=18, fill=col)
        # etiqueta abajo
        fnt = ctx.fX(28, 600)
        d.text((x0 + bw / 2, base_y + 22), b.get("etiqueta", ""), font=fnt, fill=BLANCO, anchor="mt")
        # valor arriba de la barra
        fnt_v = ctx.fT(56, 800)
        val = cuenta_up(0, b.get("valor", 0), t, t_in, dur=0.6, fmt="{:,}")
        d.text((x0 + bw / 2, base_y - fill_h - 60), val, font=fnt_v, fill=col, anchor="mb")
    if e.get("fuente") and t >= at.get("fuente", at.get("rotulo", e["from"]) + 1.5):
        fnt = ctx.fX(22, 400)
        d.text((W / 2, H * 0.93), f"Fuente: {e.get('fuente', '')}", font=fnt, fill=GRIS, anchor="mm")
    return capa_salida(layer, t, e["to"])


def sc_gauge(ctx, e, t):
    """Indicador circular (gauge) con cuenta animada al medio.
    Params: `titulo`, `valor`, `max`, `etiqueta`, `at{rotulo, gauge, valor, etiqueta}`.
    """
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    at = e["at"]
    rotulo(ctx, layer, t, e.get("titulo", ""), at.get("rotulo", e["from"]), y=H*0.18)
    cx, cy, r = W / 2, H * 0.52, W * 0.34
    grosor = 26
    t_in = at.get("gauge", e["from"] + 0.3)
    k = spring(t, t_in, 110, 14)
    # track 270° (de -135° a 135° = 270° barrido)
    arco(d, cx, cy, r, 135, 135 + 270, (255, 255, 255, 32), grosor)
    if k >= 0:
        fraccion = clamp01(e.get("valor", 0) / max(1, e.get("max", 100)))
        ang_fin = 135 + 270 * fraccion * k
        arco(d, cx, cy, r, 135, ang_fin, ACENTO, grosor)
    # número al centro (cuenta animada)
    val = cuenta_up(0, e.get("valor", 0), t, t_in, dur=0.9, fmt="{:,}")
    fnt = ctx.fT(int(W*0.18), 800)
    d.text((cx, cy - 8), val, font=fnt, fill=BLANCO, anchor="mm")
    if "etiqueta" in e and t >= at.get("etiqueta", t_in + 0.7):
        fnt2 = ctx.fX(36, 600)
        d.text((cx, cy + 90), e.get("etiqueta", ""), font=fnt2, fill=GRIS, anchor="mt")
    return capa_salida(layer, t, e["to"])


def sc_ranking(ctx, e, t):
    """Ranking horizontal: items con barra proporcional al valor, etiqueta a la izq,
    valor a la der. El #1 lleva acento. Params: `titulo`, `fuente`, `items[{etiqueta, valor, max}]`,
    `at{rotulo, item0..n, fuente}`.
    """
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    at = e["at"]
    rotulo(ctx, layer, t, e.get("titulo", ""), at.get("rotulo", e["from"]), y=H*0.16)
    items = e.get("items", [])
    n = len(items)
    y0 = H * 0.32
    fila_h = (H * 0.56) // max(1, n)
    max_v = max((i.get("valor", 0) for i in items), default=1) or 1
    for i, it in enumerate(items):
        t_in = at.get(f"item{i}", e["from"] + 0.2 + i * 0.08)
        k = spring(t, t_in, 110, 14)
        if k <= 0:
            continue
        yi = y0 + i * fila_h + fila_h * 0.15
        hi = fila_h * 0.7
        # etiqueta a la izquierda
        fnt = ctx.fX(int(fila_h * 0.42), 700)
        d.text((W * 0.06, yi + hi / 2), it.get("etiqueta", ""), font=fnt, fill=BLANCO, anchor="lm")
        # barra
        x_bar = W * 0.28
        bw = W * 0.62
        fraccion = clamp01(it.get("valor", 0) / max_v)
        col = ACENTO if i == 0 else (255, 255, 255, 220)
        barra_h(d, x_bar, yi, bw, hi, fraccion * k, col, radio=hi // 2)
        # valor a la derecha
        val = cuenta_up(0, it.get("valor", 0), t, t_in, dur=0.6, fmt="{:,}")
        fnt_v = ctx.fX(int(fila_h * 0.5), 800)
        d.text((W * 0.94, yi + hi / 2), val, font=fnt_v, fill=col, anchor="rm")
    if e.get("fuente") and t >= at.get("fuente", e["from"] + 2.0):
        fnt = ctx.fX(22, 400)
        d.text((W / 2, H * 0.94), f"Fuente: {e.get('fuente', '')}", font=fnt, fill=GRIS, anchor="mm")
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
    cols = min(n, 3) if n > 1 else 1
    coords = cuadricula(W * 0.08, H * 0.32, W * 0.84, H * 0.52, cols, n)
    for i, (cx, cy, cw, ch) in enumerate(coords):
        t_in = at.get(f"card{i}", e["from"] + 0.2 + i * 0.08)
        k = spring(t, t_in, 110, 14)
        if k <= 0:
            continue
        c = cards[i]
        # card con resorte (escala 0.9 → 1.0)
        s = lerp(0.92, 1.0, k)
        tarjeta(ctx, layer, cx, cy, int(cw * s), int(ch * s))
        # cifra
        col = ACENTO if c.get("acento") else BLANCO
        fnt_v = ctx.fT(int(ch * 0.30), 800)
        val = cuenta_up(0, c.get("valor", 0), t, t_in, dur=0.7, fmt="{:,}")
        d.text((cx + cw / 2, cy + ch * 0.42), val, font=fnt_v, fill=col, anchor="mm")
        # etiqueta
        fnt_l = ctx.fX(int(ch * 0.13), 600)
        d.text((cx + cw / 2, cy + ch * 0.78), c.get("etiqueta", ""), font=fnt_l, fill=GRIS, anchor="mm")
    if e.get("fuente") and t >= at.get("fuente", e["from"] + 2.0):
        fnt = ctx.fX(22, 400)
        d.text((W / 2, H * 0.94), f"Fuente: {e.get('fuente', '')}", font=fnt, fill=GRIS, anchor="mm")
    return capa_salida(layer, t, e["to"])


def sc_timeline(ctx, e, t):
    """Timeline horizontal con puntos y conectores. Params: `titulo`, `items[{etiqueta, fecha}]`,
    `at{rotulo, item0..n}`.
    """
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    at = e["at"]
    rotulo(ctx, layer, t, e.get("titulo", ""), at.get("rotulo", e["from"]), y=H*0.20)
    items = e.get("items", [])
    n = len(items)
    cy = H * 0.50
    x_ini = W * 0.10
    x_fin = W * 0.90
    # línea base
    d.line([x_ini, cy, x_fin, cy], fill=(255, 255, 255, 80), width=4)
    for i, it in enumerate(items):
        t_in = at.get(f"item{i}", e["from"] + 0.2 + i * 0.1)
        k = spring(t, t_in, 110, 14)
        if k <= 0:
            continue
        # posición en X
        x = x_ini + (x_fin - x_ini) * i / max(1, n - 1) if n > 1 else (x_ini + x_fin) / 2
        # punto + pulso
        radio = 18
        d.ellipse([x - radio, cy - radio, x + radio, cy + radio], fill=ACENTO)
        d.ellipse([x - radio + 3, cy - radio + 3, x + radio - 3, cy + radio - 3],
                  fill=BLANCO)
        pulso = int(255 * clamp01(math.sin((t - t_in) * 6) * 0.5 + 0.5) * k * 0.4)
        if pulso > 0:
            d.ellipse([x - radio - 8, cy - radio - 8, x + radio + 8, cy + radio + 8],
                      outline=(255, 255, 255, pulso), width=3)
        # etiqueta arriba + fecha abajo
        fnt = ctx.fX(26, 700)
        ancho_max = (x_fin - x_ini) / max(1, n) * 0.9
        lineas = linewrap(it.get("etiqueta", ""), fnt, ancho_max)
        for li, ln in enumerate(lineas):
            d.text((x, cy - 60 - (len(lineas) - 1 - li) * 30), ln,
                   font=fnt, fill=BLANCO, anchor="mm")
        if it.get("fecha"):
            fnt_d = ctx.fX(20, 400)
            d.text((x, cy + 50), it.get("fecha", ""), font=fnt_d, fill=GRIS, anchor="mm")
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
    cx, cy, cw, ch = W * 0.10, H * 0.22, W * 0.80, H * 0.62
    tarjeta(ctx, layer, int(cx + (1 - s) * cw / 2), int(cy + (1 - s) * ch / 2),
            int(cw * s), int(ch * s))
    d.text((cx + 40, cy + 30), "\u201C", font=ctx.fT(int(W * 0.22), 800), fill=ACENTO, anchor="lt")
    # palabras con su marca de énfasis, envueltas con medida real
    fnt = ctx.fX(int(W * 0.055), 600)
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
    t_texto = at.get("texto", t_card + 0.2)
    n = len(lineas)
    lh = fnt.size * 1.25
    y_ult = cy + ch * 0.36
    for li, ln in enumerate(lineas):
        t_li = t_texto + li * 0.22
        kl = spring(t, t_li, 130, 16)
        if kl <= 0:
            continue
        al = int(255 * clamp01(kl * 1.4))
        y = cy + ch * 0.36 + (li - (n - 1) / 2) * lh + (1 - min(1, kl)) * 14
        y_ult = y
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
    t_fin = t_texto + n * 0.22 + 0.4
    if e.get("estrellas") is not None:
        t_es = at.get("estrellas", t_fin)
        if t >= t_es:
            estrellas(layer, cx + cw / 2, y_ult + lh * 1.3, float(e["estrellas"]),
                      int(e.get("estrellas_max", 5)), k=ease_out(clamp01((t - t_es) / 0.6)))
        t_fin = t_es + 0.7
    t_au = at.get("autor", t_fin)
    if e.get("autor") and t >= t_au:
        ka = spring(t, t_au, 130, 16)
        al = int(255 * clamp01(ka * 1.4)); dy = (1 - min(1, ka)) * 20
        d.text((cx + cw / 2, cy + ch * 0.80 + dy), e["autor"],
               font=ctx.fX(int(W * 0.040), 800), fill=BLANCO + (al,), anchor="mm")
        if e.get("rol"):
            d.text((cx + cw / 2, cy + ch * 0.86 + dy), e["rol"],
                   font=ctx.fX(int(W * 0.028), 500), fill=GRIS + (al,), anchor="mm")
    if e.get("fuente") and t >= at.get("fuente", t_au + 0.2):
        d.text((cx + cw / 2, cy + ch * 0.93), f"Fuente: {e.get('fuente', '')}",
               font=ctx.fX(20, 400), fill=GRIS, anchor="mm")
    return capa_salida(layer, t, e["to"])


def sc_versus(ctx, e, t):
    """Comparación lado a lado (versus). Params: `titulo`, `izquierda{etiqueta, items[]}`,
    `derecha{etiqueta, items[]}`, `at{rotulo, izq, der}`.
    """
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    at = e["at"]
    rotulo(ctx, layer, t, e.get("titulo", ""), at.get("rotulo", e["from"]), y=H*0.16)
    izq = e.get("izquierda", {}); der = e.get("derecha", {})
    # etiquetas de los lados
    y_label = H * 0.30
    fnt_h = ctx.fT(int(W * 0.055), 800)
    d.text((W * 0.25, y_label), izq.get("etiqueta", ""), font=fnt_h, fill=BLANCO, anchor="mm")
    d.text((W * 0.75, y_label), der.get("etiqueta", ""), font=fnt_h, fill=ACENTO, anchor="mm")
    # VS al medio
    fnt_vs = ctx.fT(int(W * 0.06), 800)
    d.text((W / 2, y_label), "vs", font=fnt_vs, fill=GRIS, anchor="mm")
    # items de cada lado
    n = max(len(izq.get("items", [])), len(der.get("items", [])))
    y_items = H * 0.42
    fila_h = H * 0.46 / max(1, n)
    fnt = ctx.fX(int(fila_h * 0.42), 600)
    for i in range(n):
        yi = y_items + i * fila_h + fila_h / 2
        li = izq.get("items", ["—"])[i] if i < len(izq.get("items", [])) else "—"
        ri = der.get("items", ["—"])[i] if i < len(der.get("items", [])) else "—"
        # texto izquierda (alineado a la derecha)
        d.text((W * 0.46, yi), li, font=fnt, fill=BLANCO, anchor="rm")
        # texto derecha (alineado a la izquierda)
        d.text((W * 0.54, yi), ri, font=fnt, fill=BLANCO, anchor="lm")
        # separador vertical tenue
        d.line([W / 2, yi - fila_h * 0.3, W / 2, yi + fila_h * 0.3],
               fill=(255, 255, 255, 30), width=1)
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
            fnt = ctx.fT(int(W * 0.10), 800)
            d.text((W / 2, H * 0.42), e.get("texto", ""), font=fnt,
                   fill=BLANCO + (int(255 * clamp01(k * 1.3)),), anchor="mm")
    if "subtexto" in e and t >= at.get("subtexto", t_t + 0.4):
        fnt_s = ctx.fX(int(W * 0.045), 600)
        d.text((W / 2, H * 0.52), e.get("subtexto", ""), font=fnt_s, fill=GRIS, anchor="mm")
    return capa_salida(layer, t, e["to"])


# ───────────────────────── ESCENAS TIPO/EFECTO (Ronda 2) ─────────────────────────
# Patrones validados de reactvideoeditor/remotion-templates (81 templates, MIT).
# Cada escena nueva se compone con las primitivas DRY — sin duplicar logica.

def sc_typewriter(ctx, e, t):
    """Texto que aparece carácter a carácter con cursor parpadeante.
    Params: `texto`, `tam`, `at{rotulo, fin, cursor}`. Sin `tam` se auto-ajusta.
    Fuente: `typewriter-subtitle.tsx` (reactvideoeditor/remotion-templates).
    """
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    at = e["at"]
    texto = e.get("texto", "")
    if not texto:
        return capa_salida(layer, t, e["to"])
    t_in = at.get("rotulo", e["from"])
    # auto-fit: ajusta tam al ancho disponible
    tmp = ImageDraw.Draw(Image.new("L", (10, 10)))
    tam = int(e.get("tam", W * 0.075))
    fnt = ctx.fT(tam, 800)
    while tam > 40 and tmp.textlength(texto, font=fnt) > W * 0.85:
        tam -= 4
        fnt = ctx.fT(tam, 800)
    # centrado
    text_w = tmp.textlength(texto, font=fnt)
    cx = (W - text_w) / 2
    cy = H * 0.42
    # fondo sutil para legibilidad (PANEL con alpha)
    panel_h = tam * 1.6
    d.rounded_rectangle([W * 0.05, cy - 30, W * 0.95, cy + panel_h],
                        radius=18, fill=PANEL + (180,))
    # texto progresivo
    n_visible = text_reveal(d, texto, fnt, cx, cy, t, t_in, dur=0.08 * len(texto),
                            color=BLANCO, fill=BLANCO)
    # cursor parpadeante al final
    if n_visible > 0 and t >= at.get("cursor", t_in + 0.1):
        n = n_visible
        cursor_w = tmp.textlength(texto[:n], font=fnt)
        # solo si se termino de escribir (>=95% del texto)
        if n >= len(texto) * 0.95:
            parpadeo = 1 if math.sin(t * 8) > 0 else 0
            if parpadeo:
                d.rectangle([cx + cursor_w + 4, cy - 8, cx + cursor_w + 8, cy + tam + 4],
                            fill=ACENTO)
    # fuente si existe
    if e.get("fuente") and t >= at.get("fuente", e["from"] + 2.5):
        fnt_f = ctx.fX(20, 400)
        d.text((W / 2, H * 0.93), f"Fuente: {e.get('fuente', '')}",
               font=fnt_f, fill=GRIS, anchor="mm")
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
    if base is not None:
        t_kb = at.get("kenburns", e["from"] + 0.2)
        layer.alpha_composite(kenburns(base, t, t_kb, dur=e.get("dur_kb", 4.0),
                                       zoom_from=e.get("zoom_from", 1.0),
                                       zoom_to=e.get("zoom_to", 1.15),
                                       pan_x=e.get("pan_x", 0.0),
                                       pan_y=e.get("pan_y", 0.0)))
    # oscurecer para que el texto lea
    # (componer, no dibujar: ImageDraw con alfa REEMPLAZA píxeles y borraba la foto)
    velo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(velo).rectangle([0, H * 0.65, W, H], fill=(0, 0, 0, 130))
    layer.alpha_composite(velo)
    # texto
    if e.get("titulo") and t >= at.get("texto", e["from"] + 0.5):
        fnt = ctx.fT(80, 800)
        lineas = linewrap(e["titulo"], fnt, W * 0.85)
        for i, ln in enumerate(lineas):
            d.text((W / 2, H * 0.72 + i * 90), ln, font=fnt, fill=BLANCO, anchor="mm")
    if e.get("subtitulo") and t >= at.get("subtitulo", e["from"] + 1.5):
        fnt_s = ctx.fX(36, 600)
        d.text((W / 2, H * 0.90), e.get("subtitulo", ""), font=fnt_s, fill=GRIS, anchor="mm")
    return capa_salida(layer, t, e["to"])


def sc_pasos(ctx, e, t):
    """Ruta de N pasos (1-5) en fila (16:9) o columna (9:16), con el paso
    activo brillando y los demás atenuados. Params: `titulo`, `items[{titulo, texto, at}]`,
    `at{rotulo, item0..n}`. Fuente: `progress-steps.tsx` (reactvideoeditor/remotion-templates).
    """
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    at = e["at"]
    rotulo(ctx, layer, t, e.get("titulo", ""), at.get("rotulo", e["from"]), y=H * 0.14)
    items = e.get("items", [])
    n = len(items)
    if n == 0:
        return capa_salida(layer, t, e["to"])
    vertical = H > W  # layout en columna para 9:16
    if vertical:
        # columna
        y0, h_disp = H * 0.30, H * 0.62
        fila_h = h_disp / n
        cx = W / 2
        for i, it in enumerate(items):
            t_in = at.get(f"item{i}", e["from"] + 0.3 + i * 0.2)
            k = spring(t, t_in, 110, 14)
            if k <= 0:
                continue
            yi = y0 + i * fila_h + fila_h * 0.1
            # número
            radio = min(fila_h * 0.35, 60)
            es_activo = k > 0.5
            d.ellipse([cx - radio, yi, cx + radio, yi + 2 * radio],
                      fill=ACENTO if es_activo else (80, 80, 80, 255))
            fnt_n = ctx.fT(int(radio * 1.2), 800)
            d.text((cx, yi + radio), str(i + 1), font=fnt_n, fill=BLANCO, anchor="mm")
            # texto a la izquierda del número (en columna: debajo)
            fnt = ctx.fX(int(fila_h * 0.18), 700)
            d.text((cx, yi + 2 * radio + 8), it.get("titulo", ""), font=fnt, fill=BLANCO, anchor="mt")
            if it.get("texto"):
                fnt_t = ctx.fX(int(fila_h * 0.13), 400)
                d.text((cx, yi + 2 * radio + 8 + fnt.size + 4),
                       it.get("texto", ""), font=fnt_t, fill=GRIS, anchor="mt")
            # conector
            if i < n - 1:
                d.line([cx, yi + 2 * radio + 4, cx, yi + fila_h - 4],
                       fill=(120, 120, 120, 255), width=3)
    else:
        # fila
        x0, w_disp = W * 0.06, W * 0.88
        col_w = w_disp / n
        cy = H * 0.55
        for i, it in enumerate(items):
            t_in = at.get(f"item{i}", e["from"] + 0.3 + i * 0.2)
            k = spring(t, t_in, 110, 14)
            if k <= 0:
                continue
            xi = x0 + i * col_w + col_w * 0.1
            radio = min(col_w * 0.18, 80)
            es_activo = k > 0.5
            d.ellipse([xi, cy - radio, xi + 2 * radio, cy + radio],
                      fill=ACENTO if es_activo else (80, 80, 80, 255))
            fnt_n = ctx.fT(int(radio * 1.2), 800)
            d.text((xi + radio, cy), str(i + 1), font=fnt_n, fill=BLANCO, anchor="mm")
            # texto
            fnt = ctx.fX(int(col_w * 0.12), 700)
            lineas = linewrap(it.get("titulo", ""), fnt, col_w * 0.85)
            for li, ln in enumerate(lineas):
                d.text((xi + radio, cy + radio + 12 + li * (fnt.size + 4)),
                       ln, font=fnt, fill=BLANCO, anchor="mt")
            # conector
            if i < n - 1:
                d.line([xi + 2 * radio + 6, cy, x0 + (i + 1) * col_w - 6, cy],
                       fill=(120, 120, 120, 255), width=3)
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
    Cada dígito que cambia rueda tipo odómetro en el último cuarto de su
    segundo; dígitos de ancho fijo (no tiemblan).
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
    rodar = clamp01((0.25 - (restante - (mostrado - 1))) / 0.25) if mostrado > 0 else 0.0
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
    alfa = int(255 * clamp01(k * 1.4) * (1 - 0.75 * min(1, kf)))
    if alfa > 0:
        odometro(layer, siguiente, actual, rodar, W / 2, H * 0.45, fnt, BLANCO + (alfa,))
    if kf > 0:
        sc = 1 + 0.2 * (1 - min(1, kf))
        d.text((W / 2, H * 0.45 + tam * 0.75), e["final"], font=ctx.fT(int(tam * 0.55 * sc), 800),
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
    if e.get("rotulo"):
        rotulo(ctx, layer, t, e["rotulo"], at.get("rotulo", fr), y=H * 0.15, tam=52)
    mostrar = e.get("mostrar") or ("monto" if antes - ahora < 10 else "porcentaje")
    badge = f"-{pct}%" if mostrar == "porcentaje" else f"-{_fmt_precio(antes - ahora, e)}"
    t_d = at.get("descuento", fr + 0.4)
    kd = spring(t, t_d, 170, 12)
    if kd > 0:
        tam = 300
        while tam > 90 and ctx.tmp.textlength(badge, font=ctx.fT(tam, 800)) > W - 2 * MARGEN:
            tam -= 10
        sc = 1 + 0.25 * (1 - min(1, kd))
        d.text((W / 2, H * 0.29), badge, font=ctx.fT(int(tam * sc), 800),
               fill=ACENTO + (int(255 * clamp01(kd * 1.5)),), anchor="mm")
    t_t = at.get("tachado", fr + 1.3)
    ka = spring(t, t_t - 0.35, 130, 16)
    if ka > 0:
        txt = _fmt_precio(antes, e); fnt = ctx.fT(92, 700)
        tw_ = ctx.tmp.textlength(txt, font=fnt); y = H * 0.43
        d.text((W / 2, y), txt, font=fnt, fill=GRIS + (int(255 * clamp01(ka * 1.4)),), anchor="mm")
        kt = ease_out(clamp01((t - t_t) / 0.35))
        if kt > 0:
            x0 = W / 2 - tw_ / 2 - 12
            d.line([(x0, y + 6), (x0 + (tw_ + 24) * kt, y - 6)], fill=ACENTO + (255,), width=10)
    t_p = at.get("precio", t_t + 0.5)
    if t >= t_p:
        kp = spring(t, t_p, 140, 14)
        v = antes + (ahora - antes) * ease_out(clamp01((t - t_p) / 0.9))
        sc = 1 + 0.06 * max(0, 1 - abs((t - t_p - 0.9) / 0.15)) if t > t_p + 0.75 else 1
        d.text((W / 2, H * 0.52), _fmt_precio(v, e), font=ctx.fT(int(150 * sc), 800),
               fill=BLANCO + (int(255 * clamp01(kp * 1.5)),), anchor="mm")
    if e.get("codigo"):
        t_c = at.get("codigo", t_p + 1.2)
        kc = spring(t, t_c, 130, 16)
        if kc > 0:
            fnt = ctx.fM(56, 700); txt = e["codigo"]
            cw_ = ctx.tmp.textlength(txt, font=fnt) + 90; chh = 104
            x0, y0 = W / 2 - cw_ / 2, H * 0.60 + (1 - min(1, kc)) * 20
            al = int(255 * clamp01(kc * 1.4))
            d.rounded_rectangle([x0, y0, x0 + cw_, y0 + chh], radius=22, fill=PANEL2 + (al,))
            paso = 22   # borde punteado: lee como "código para copiar"
            for xx in range(int(x0 + 18), int(x0 + cw_ - 18), paso):
                for yy_ in (y0, y0 + chh):
                    d.line([(xx, yy_), (min(xx + 11, x0 + cw_ - 18), yy_)], fill=ACENTO + (al,), width=3)
            d.text((W / 2, y0 + chh / 2), txt, font=fnt, fill=BLANCO + (al,), anchor="mm")
    if e.get("vence"):
        t_v = at.get("vence", at.get("codigo", t_p + 1.2) + 0.3)
        kv = spring(t, t_v, 130, 16)
        if kv > 0:
            d.text((W / 2, H * 0.695), e["vence"], font=ctx.fX(38, 600),
                   fill=GRIS + (int(255 * clamp01(kv * 1.4)),), anchor="mm")
    if e.get("cta"):
        t_b = at.get("cta", at.get("vence", t_p + 1.5) + 0.5)
        kb = spring(t, t_b, 150, 13)
        if kb > 0:
            fnt = ctx.fT(48, 800)
            bw_ = ctx.tmp.textlength(e["cta"], font=fnt) + 120; bh_ = 110
            s_ = 0.9 + 0.1 * min(1.08, kb)
            x0, y0 = W / 2 - bw_ * s_ / 2, H * 0.74
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
    bw = int(W * 0.86)
    ruta = e.get("captura")
    asp = e.get("aspecto", 0.625)
    if ruta and os.path.isfile(os.path.expanduser(ruta)):
        try:
            with Image.open(os.path.expanduser(ruta)) as im_:
                asp = im_.height / im_.width
        except Exception:
            pass
    bh = int(min(H * 0.48, bw * asp))
    barra = 48
    x0 = (W - bw) // 2
    y0 = int(H * 0.44 - (bh + barra) / 2 + (1 - min(1, kv)) * 40)
    pasos = sorted(e.get("pasos", []), key=lambda p_: p_.get("at", 0))
    # pantalla vigente: la del último clic ya ocurrido que traiga `captura`
    pantalla = ruta
    for p_ in pasos:
        if p_.get("captura") and t >= p_.get("at", 0):
            pantalla = p_["captura"]
    img = imagen_ajustada(pantalla, bw, bh)
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
        zin = ease_in_out(clamp01((t - (a_ + 0.15)) / 0.7))
        zout = ease_in_out(clamp01((t - (nxt - 1.3)) / 0.7))
        s_ = zin * (1 - zout)
        if s_ > 0:
            z = 1 + (min(2.0, p_.get("zoom", 1.6)) - 1) * s_
            fx, fy, foco = p_.get("x", 0.5), p_.get("y", 0.5), s_
    fxp, fyp = fx * bw, fy * bh
    cx_, cy_ = fxp * (1 - 1 / z), fyp * (1 - 1 / z)
    vista = img.transform(img.size, Image.AFFINE, (1 / z, 0, cx_, 0, 1 / z, cy_),
                          resample=Image.BICUBIC)
    a_v = int(255 * clamp01(kv * 1.4))
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
                fnt = ctx.fT(44, 800)
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
        kr = ease_out(clamp01((t - t_in - dt) / 0.4)) * k_txt
        if kr <= 0:
            continue
        tw_ = int(ctx.tmp.textlength(txt, font=fnt)) + 4
        img = Image.new("RGBA", (tw_, int(fnt.size * 1.4)), (0, 0, 0, 0))
        ImageDraw.Draw(img).text((0, 0), txt, font=fnt, fill=col + (255,))
        vis = img.crop((0, 0, max(1, int(tw_ * kr)), img.height))   # máscara: barre, no se mueve
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
ESCENAS_HORIZONTALES={"rotulo_inferior","countdown"}

# ================= MAIN =================
# hex_a_rgb vive en _comun (unica fuente; DRY). Reusar aquí:
from _comun import hex_a_rgb, info  # noqa: E402,F401  # sys.path ya apunta a ffmpeg_tools

def aplicar_brand(brand_path):
    """Instala la identidad del pack: colores, tipografías, logos y reglas.
    La lectura vive en _comun (colores_marca, fuente_marca, ruta_de_pack):
    la misma para todas las herramientas del kit."""
    global ACENTO, ACENTO_OSC, NEGRO, BLANCO, GRIS, FJ, FM, MONO, LOGO, ISOTIPO, MARCA_NOMBRE, TRANSICIONES
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

_ESCALA={}
def escala_segura(ctx,e,idx):
    """Factor de escala FIJO por escena para que su contenido quepa en la zona
    segura. Se mide el bbox del contenido en varios instantes de la escena
    (no por frame: un factor por frame bombearía)."""
    if idx in _ESCALA: return _ESCALA[idx]
    fr,to=e["from"],e["to"]
    xs0,xs1,ys0,ys1=W,0,H,0
    for i in range(6):
        t=fr+0.25+(max(0.0,to-0.6-fr-0.25))*i/5
        bb=SCENES[e["tipo"]](ctx,e,t).split()[3].point(lambda v:255 if v>110 else 0).getbbox()
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

def encajar(layer,f):
    if f>=0.999: return layer
    w2,h2=int(W*f),int(H*f)
    small=layer.resize((w2,h2),Image.LANCZOS)
    out=Image.new("RGBA",(W,H),(0,0,0,0))
    out.alpha_composite(small,(int(W/2-w2/2),int(H*0.45-H*0.45*f)))
    return out

def componer(ctx,escenas,dur,t,manchas_ok):
    """Compone el frame en el instante t (puede ser sub-frame, para el blur)."""
    t=max(0.0,min(t,dur-1e-6))
    s=None; si=0
    for i,e in enumerate(escenas):
        if e["from"]<=t<e["to"]: s=e; si=i; break
    if s is None: s=escenas[-1]; si=len(escenas)-1
    bg=Image.new("RGBA",(W,H),(0,0,0,0)) if ALFA else mundo(ctx,t,seed=si+1)
    layer=encajar(SCENES[s["tipo"]](ctx,s,t).copy(),escala_segura(ctx,s,si))
    if si in manchas_ok and t-s["from"]<0.9:
        prev=encajar(SCENES[escenas[si-1]["tipo"]](ctx,escenas[si-1],t),escala_segura(ctx,escenas[si-1],si-1))
        fx=s.get("transicionX",0.5); fy=s.get("transicionY",0.45)
        mask=mancha_mask(ctx,t,s["from"],0.9,fx,fy)
        inv=Image.eval(mask,lambda v:255-v)
        nada=Image.new("RGBA",(W,H),(0,0,0,0))
        bg.alpha_composite(Image.composite(prev,nada,inv))
        bg.alpha_composite(Image.composite(layer,nada,mask))
    else:
        if si>0 and t-s["from"]<0.03:   # corte seco con micro-fade de 30 ms (sin pop)
            layer=capa_entrada(layer,t,s["from"])
        bg.alpha_composite(layer)
    if dur-t<0.8:
        k=clamp01((0.8-(dur-t))/0.8)
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
def _init_worker(brand_path,acento,plan_path,maximo_cfg,safe=None,escalas=None,alfa=False,
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
    plan=json.load(open(plan_path, encoding="utf-8"))
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

def render(plan_path,plan,out,a):
    """Renderiza un plan ya cargado a `out` (.mp4; .webm/.mov = con alfa)."""
    global ACENTO, ACENTO_OSC, ALFA, W, H, MARGEN
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
    plataforma=a.plataforma or plan.get("plataforma","vertical" if H>W else "youtube")
    if plataforma!="ninguna": SAFE.update(zona_segura(plataforma))
    else: SAFE.update({"top":0,"bottom":0,"left":0,"right":0})
    MARGEN=max(SAFE["left"],int(W*0.05))
    _ESCALA.clear()
    ctx=Ctx(); fps=a.fps
    dur=plan["duracion"]; n=int(dur*fps)
    escenas=sorted(plan["escenas"],key=lambda s:s["from"])
    maximo=plan.get("mancha_max", 1 if TRANSICIONES=="corte_seco" else 2)
    manchas_ok=presupuesto_manchas(escenas,maximo)
    if W>H:
        solo_v=sorted({e["tipo"] for e in escenas}-ESCENAS_HORIZONTALES)
        if solo_v:
            print(f"AVISO: escenas compuestas para 9:16 ({', '.join(solo_v)}); en {W}x{H} "
                  f"pueden solaparse — mirar frames antes de entregar (references/plan-video.md)",flush=True)
    for i,e in enumerate(escenas): escala_segura(ctx,e,i)   # una vez, antes del render
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
              plan_path, plan.get("mancha_max"), dict(SAFE), dict(_ESCALA), ALFA, (W,H,MARGEN))
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
    if not a.datos:
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
        trabajos.append((n_,p_,out))
    print(f"plantilla × {len(trabajos)} fila(s) de {a.datos}",flush=True)
    for n_,p_,out in trabajos:
        ruta=f"{out}.plan.json"   # el plan resuelto queda junto al video (reproducible)
        json.dump(p_,open(ruta,"w",encoding="utf-8"),ensure_ascii=False,indent=1)
        print(f"— fila {n_}: {out}",flush=True)
        render(ruta,p_,out,a)

if __name__=="__main__": main()
