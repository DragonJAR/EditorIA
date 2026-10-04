#!/usr/bin/env python3
"""EditorIA plan renderer — ejecuta un plan.json con fluidez total.
Identidad desde brand pack opcional (--brand o campo "brand" en el plan);
sin pack, usa los defaults neutros del renderer.
Uso: python render_plan.py plan.json -o salida.mp4 [--fps 30] [--brand brand/otro.json]
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os, math, json, random, subprocess, sys, argparse

# ---------- identidad: defaults NEUTROS; el brand pack los sobreescribe ----------
# Sin pack (modo libre) nada de marca: acento neutro y fuentes empaquetadas.
ROJO=(232,72,12); ROJO_OSC=(150,46,8); NEGRO=(10,10,10); BLANCO=(250,248,246)
GRIS=(170,170,170); PANEL=(26,26,26); PANEL2=(38,38,38)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg_tools"))
from _plataforma import resolver_fuente
FJ=resolver_fuente("Plus Jakarta Sans", generica="sans-bold")
FM=resolver_fuente("Montserrat", generica="sans")
MONO=resolver_fuente("DejaVu Sans Mono", "Consolas", "Menlo", generica="mono")
LOGO=None; ISOTIPO=None; MARCA_NOMBRE=None
TRANSICIONES="libre"   # idioma de transición; el pack puede fijar "corte_seco"

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
def segs(text):
    out=[]; buf=""; emph=False; i=0
    while i < len(text):
        if text[i]=="*":
            if buf: out.append((buf,emph)); buf=""
            emph=not emph; i+=1; continue
        buf+=text[i]; i+=1
    if buf: out.append((buf,emph))
    return out
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
        self.blob_big=self._blob(560,ROJO+(46,))
        self.blob_mid=self._blob(380,ROJO+(30,))
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
                col=ROJO if em else BLANCO
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
    draw_seg(d,(W/2,yy),sg,fnt,color+(al,),ROJO+(al,),anchor="ma")
    return k

def tarjeta(ctx,img,x,y,w,h,radio=28,alpha=255):
    d=ImageDraw.Draw(img)
    if h < 2*radio or w < 2*radio:  # rounded_rectangle falla si h/w < 2*radio
        d.rectangle([x,y,x+w,y+h],fill=PANEL+(alpha,))
        d.rectangle([x,y,x+w,y+h],outline=(255,255,255,28))
        return
    d.rounded_rectangle([x,y,x+w,y+h],radius=radio,fill=PANEL+(alpha,))
    d.rounded_rectangle([x,y,x+w,y+h],radius=radio,outline=(255,255,255,28))

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
        d.polygon(pts,fill=ROJO+(58,))
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
        dc.ellipse([28,24,104,100],fill=ROJO+(255,))
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
            dn.ellipse([22,38,86,102],fill=ROJO+(255,))
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
    layer=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(layer)
    rotulo(ctx,layer,t,e["rotulo"],e["at"]["rotulo"],y=H*0.20)
    y=H*0.42
    for m in e["mensajes"]:
        k=spring(t,m["at"],140,15)
        if k<=0: continue
        fnt=ctx.fX(32,400)
        maxw=680
        blines=wrap(m["texto"],fnt,maxw,ctx.tmp)
        tw=max(ctx.tmp.textlength(l,font=fnt) for l in blines)+70
        hh=len(blines)*52+44
        if m["de"]=="cliente":
            x=90; col=PANEL2
        else:
            x=W-90-tw; col=tuple(int(c*0.30) for c in ROJO)
        yy=y+(1-min(1,k))*-60+flota(t,m["at"]+1.0,4,0.5)
        al=int(255*clamp01(k*1.4))
        d.rounded_rectangle([x,yy,x+tw,yy+hh],radius=30,fill=col+(al,))
        for bi,bl in enumerate(blines):
            d.text((x+34,yy+22+bi*52),bl,font=fnt,fill=BLANCO+(al,))
        y+=hh+36
    lk=e.get("link")
    if lk and t>=lk["at"]:
        k=spring(t,lk["at"],120,14)
        cw,chh=760,150; x=(W-cw)/2; yy=H*0.72
        d.rounded_rectangle([x,yy,x+cw,yy+chh],radius=28,fill=ROJO+(int(235*min(1,k)),))
        d.text((x+40,yy+34),lk["titulo"],font=ctx.fX(34,800),fill=BLANCO)
        d.text((x+40,yy+84),lk["monto"],font=ctx.fT(44,800),fill=BLANCO)
    return capa_salida(layer,t,e["to"])

def sc_leads(ctx,e,t):
    layer=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(layer)
    at=e["at"]
    rotulo(ctx,layer,t,e["rotulo"],at["rotulo"],y=H*0.20)
    d.text((W/2,H*0.24),e["total"],font=ctx.fM(36,700),fill=ROJO,anchor="ma")
    y0=H*0.32
    colores_temp={"Caliente":ROJO,"Tibio":(200,140,40),"Frío":(90,140,200)}
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
        d.ellipse([160,H*0.30+60,260,H*0.30+160],fill=ROJO+(255,))
        d.text((210,H*0.30+110),e["iniciales"],font=ctx.fT(44,800),fill=BLANCO,anchor="mm")
        d.text((300,H*0.30+52),e["cliente"],font=ctx.fX(40,800),fill=BLANCO)
        d.text((300,H*0.30+102),e["temp"],font=ctx.fM(30,700),fill=(200,140,40))
        d.text((300,H*0.30+142),e["nota"],font=ctx.fX(28,400),fill=GRIS)
    y=H*0.30+270
    for i,c in enumerate(e["contexto"]):
        kc=spring(t,at["contexto"]+i*0.4,130,15)
        if kc<=0: continue
        yy=y+i*96+(1-min(1,kc))*-40
        d.text((140,yy),c["k"],font=ctx.fM(30,700),fill=ROJO)
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
        if t>=at["toque"]:
            pk=prog(t,at["toque"],at["toque"]+0.5)
            d.ellipse([cx-90*pk,cy-90*pk,cx+90*pk,cy+90*pk],
                      outline=ROJO+(int(220*(1-pk)),),width=5)
            pulse=1+0.25*math.sin((t-at["toque"])*20)* (1-pk)
        else: pulse=1
        s=int(54*pulse)
        d.polygon([(cx,cy),(cx,cy+s*1.4),(cx+s*0.45,cy+s),(cx+s*0.7,cy+s*1.5),
                   (cx+s*0.9,cy+s*1.35),(cx+s*0.65,cy+s*0.85),(cx+s,cy+s)],
                  fill=BLANCO+(255,))
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
            d.ellipse([x-10,y-10,x+10,y+10],fill=ROJO+(al,))
        # check
        s=int(120*min(1,k))
        d.ellipse([W/2-110,H*0.5-110,W/2+110,H*0.5+110],fill=ROJO+(255,))
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
                                 fill=ROJO+(26,) if pi%2 else BLANCO+(22,))
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
           fill=ROJO,anchor="ma")
    y0=H*0.44
    for i,tj in enumerate(e["tarjetas"]):
        k=spring(t,e["from"]+0.6+i*0.3,130,15)
        if k<=0: continue
        col=i%2; row=i//2
        x=90+col*(W/2-70); yy=y0+row*190+(1-min(1,k))*-50
        tarjeta(ctx,layer,x,yy,W/2-110,160,alpha=int(255*min(1,k)))
        if tj.get("alerta"):
            d.rounded_rectangle([x,yy,x+W/2-110,yy+160],radius=28,
                                outline=ROJO+(255,),width=4)
        d.text((x+30,yy+28),tj["titulo"],font=ctx.fX(30,800),fill=BLANCO)
        d.text((x+30,yy+70),tj["detalle"][:30],font=ctx.fX(26,400),fill=GRIS)
        if tj.get("n"):
            d.ellipse([x+W/2-200,yy+28,x+W/2-140,yy+88],fill=ROJO+(255,))
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
    d.rounded_rectangle([bx,by,bx+bw*ease_in_out(rk),by+44],radius=22,fill=ROJO+(255,))
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
                                  fill=ROJO+(int(110*clamp01(k*1.4)),),anchor="ma")
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
                                outline=ROJO+(int(70*pul*min(1,kb)),),width=3)
            d.rounded_rectangle([x,yy,x+bw,yy+bh],radius=int(bh/2),fill=ROJO+(int(255*min(1,kb)),))
            if kb>0.5:
                d.text((W/2,yy+bh/2),e["boton"],font=ctx.fX(40*min(1.0,kb),800),
                       fill=BLANCO+(int(255*clamp01((kb-0.5)*2)),),anchor="mm")
    return layer  # sin salida: fundido global al final

SCENES={"apertura":sc_apertura,"canales":sc_canales,"medianoche":sc_medianoche,
        "chat":sc_chat,"leads":sc_leads,"handoff":sc_handoff,"pago":sc_pago,
        "listo":sc_listo,"pildoras":sc_pildoras,"hoy":sc_hoy,"recupera":sc_recupera,
        "remate":sc_remate,"final":sc_final}

# ================= MAIN =================
def hex_a_rgb(h):
    h = h.strip().lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

def _ruta_pack(base, valor):
    """Ruta de un asset del pack: relativa al JSON, absoluta, ~ o nombre de familia."""
    if not valor: return None
    v=os.path.expanduser(str(valor))
    cand=v if os.path.isabs(v) else os.path.join(base, v)
    if os.path.exists(cand): return cand
    return resolver_fuente(str(valor))

def aplicar_brand(brand_path):
    """Instala la identidad del pack: colores, tipografías, logos y reglas."""
    global ROJO, ROJO_OSC, NEGRO, BLANCO, GRIS, FJ, FM, MONO, LOGO, ISOTIPO, MARCA_NOMBRE, TRANSICIONES
    try:
        d = json.load(open(os.path.expanduser(brand_path), encoding="utf-8"))
    except (OSError, ValueError) as e:
        sys.exit(f"ERROR: no se pudo leer el brand pack {brand_path}: {e}")
    base=os.path.dirname(os.path.abspath(os.path.expanduser(brand_path)))
    colores = dict(d.get("colors") or {}); colores.update(d.get("colores") or {})
    acento = colores.get("acento") or colores.get("primary") or colores.get("accent")
    if not acento:
        sys.exit(f"ERROR: el brand pack {brand_path} no declara color de acento")
    ROJO = hex_a_rgb(acento)
    ROJO_OSC = hex_a_rgb(colores["acento_oscuro"]) if colores.get("acento_oscuro") else \
        tuple(max(0, int(c * 0.65)) for c in ROJO)
    if colores.get("negro"): NEGRO = hex_a_rgb(colores["negro"])
    if colores.get("blanco"): BLANCO = hex_a_rgb(colores["blanco"])
    if colores.get("gris"): GRIS = hex_a_rgb(colores["gris"])
    tip = d.get("tipografias") or {}
    for clave, glob in (("titulares", "FJ"), ("texto", "FM"), ("etiquetas_mono", "MONO")):
        t = tip.get(clave) or {}
        hit = _ruta_pack(base, t.get("archivo")) or (resolver_fuente(t["familia"]) if t.get("familia") else None)
        if hit: globals()[glob] = hit
        elif t: print(f"AVISO: tipografía '{clave}' del pack no encontrada; uso la empaquetada", flush=True)
    logos = d.get("logos") or {}
    LOGO = _ruta_pack(base, logos.get("logotipo") or logos.get("fondo_oscuro"))
    ISOTIPO = _ruta_pack(base, logos.get("isotipo"))
    MARCA_NOMBRE = d.get("nombre")
    TRANSICIONES = (d.get("reglas") or {}).get("transiciones", "libre")
    print(f"brand pack: {d.get('nombre', brand_path)} — acento {acento}", flush=True)

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
    bg=mundo(ctx,t,seed=si+1)
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
        f2=Image.new("RGBA",(W,H),(0,0,0,int(255*clamp01((0.8-(dur-t))/0.8))))
        bg.alpha_composite(f2)
    return bg.convert("RGB")

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
        acc=a if acc is None else acc+a
    return Image.fromarray(np.clip(acc/n+0.5,0,255).astype("uint8"))

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
def _init_worker(brand_path,acento,plan_path,maximo_cfg,safe=None,escalas=None):
    """Inicializa un proceso de render (portable: también con 'spawn' en Windows/macOS)."""
    global ROJO, ROJO_OSC
    if brand_path:
        import io, contextlib
        with contextlib.redirect_stdout(io.StringIO()): aplicar_brand(brand_path)
    elif acento:
        ROJO=hex_a_rgb(acento); ROJO_OSC=tuple(max(0,int(c*0.65)) for c in ROJO)
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

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("plan"); ap.add_argument("-o","--out",required=True)
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
    a=ap.parse_args()
    plan=json.load(open(a.plan, encoding="utf-8"))
    brand_path = a.brand or plan.get("brand")
    if brand_path:
        if not os.path.isabs(os.path.expanduser(brand_path)) and not os.path.exists(brand_path):
            cand=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),brand_path)
            if os.path.exists(cand): brand_path=cand
        aplicar_brand(brand_path)
    elif plan.get("acento"):   # modo libre: el plan puede fijar su acento
        global ROJO, ROJO_OSC
        ROJO=hex_a_rgb(plan["acento"]); ROJO_OSC=tuple(max(0,int(c*0.65)) for c in ROJO)
    plataforma=a.plataforma or plan.get("plataforma","vertical")
    if plataforma!="ninguna": SAFE.update(zona_segura(plataforma))
    else: SAFE.update({"top":0,"bottom":0,"left":0,"right":0})
    ctx=Ctx(); fps=a.fps
    dur=plan["duracion"]; n=int(dur*fps)
    escenas=sorted(plan["escenas"],key=lambda s:s["from"])
    maximo=plan.get("mancha_max", 1 if TRANSICIONES=="corte_seco" else 2)
    manchas_ok=presupuesto_manchas(escenas,maximo)
    for i,e in enumerate(escenas): escala_segura(ctx,e,i)   # una vez, antes del render
    tmpd=f"{a.out}.frames"; os.makedirs(tmpd,exist_ok=True)
    print(f"{n} frames, {len(escenas)} escenas, blur x{a.blur}",flush=True)
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
              a.plan, plan.get("mancha_max"), dict(SAFE), dict(_ESCALA))
        with Pool(a.jobs,initializer=_init_worker,initargs=init) as pool:
            for i,_ in enumerate(pool.imap_unordered(_render_worker,jobs,chunksize=4)):
                if i%150==0: print(f"  {i}/{len(jobs)}",flush=True)
    print("frames ok, codificando…",flush=True)
    subprocess.run(["ffmpeg","-y","-v","error","-framerate",str(fps),
                    "-i",f"{tmpd}/f_%04d.png","-c:v","libx264","-preset","medium",
                    "-crf","20","-pix_fmt","yuv420p","-movflags","+faststart",a.out],
                   check=True)
    print("OK",a.out)

if __name__=="__main__": main()
