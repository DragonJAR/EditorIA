#!/usr/bin/env python3
"""EditorIA plan renderer — ejecuta un plan.json con fluidez total.
Identidad desde brand pack opcional (--brand o campo "brand" en el plan);
sin pack, usa los defaults neutros del renderer.
Uso: python render_plan.py plan.json -o salida.mp4 [--fps 30] [--brand brand/otro.json]
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os, math, json, random, subprocess, sys, argparse

# ---------- identidad: defaults; el brand pack los sobreescribe ----------
ROJO=(193,27,5); ROJO_OSC=(130,18,0); NEGRO=(10,10,10); BLANCO=(250,248,246)
GRIS=(170,170,170); PANEL=(26,26,26); PANEL2=(38,38,38)
HOME=os.path.expanduser("~")
FJ=os.path.join(HOME,"workspace","video-dragonjar","fonts","jakarta.ttf")
FM=os.path.join(HOME,"workspace","video-dragonjar","fonts","montserrat.ttf")
def _mono_portable():
    """Fuente monoespaciada del SO (reemplaza la ruta Linux-only anterior)."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg_tools"))
    try:
        from _plataforma import resolver_fuente
        hit = resolver_fuente("DejaVu Sans Mono", "Consolas", "Menlo", generica="mono")
        if hit:
            return hit
    except Exception:
        pass
    return None
MONO=_mono_portable() or "DejaVuSansMono"
LOGO=os.path.join(HOME,"workspace","video-dragonjar","logo-oscuro.png")
ISOTIPO=os.path.join(HOME,"workspace","video-dragonjar","isotipo.png")

W,H=1080,1920
random.seed(11)

def font(p,s,w=700):
    f=ImageFont.truetype(p,s)
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
        self.blob_big=self._blob(560,(193,27,5,46))
        self.blob_mid=self._blob(380,(193,27,5,30))
        self.blob_wht=self._blob(420,(250,248,246,14))
        # viñeta precomputada (blur 220 por frame sería inviable)
        vig=Image.new("L",(W,H),0); dv=ImageDraw.Draw(vig)
        dv.ellipse([-W*0.25,-H*0.12,W*1.25,H*1.12],fill=255)
        vig=vig.filter(ImageFilter.GaussianBlur(220))
        self.vig_mask=Image.eval(vig,lambda v:int(v*0.55+115))
        self.vig_negro=Image.new("RGBA",(W,H),(0,0,0,255))
        try: self.logo=Image.open(LOGO).convert("RGBA")
        except Exception: self.logo=None
        try: self.iso=Image.open(ISOTIPO).convert("RGBA")
        except Exception: self.iso=None
    def _blob(self,r,color):
        s=r*2; img=Image.new("L",(s,s),0); d=ImageDraw.Draw(img)
        for rr in range(r,0,-8):
            a=int(color[3]*(1-rr/r)**1.6)
            d.ellipse([r-rr,r-rr,r+rr,r+rr],fill=a)
        rgb=Image.new("RGBA",(s,s),color[:3]+(255,)); rgb.putalpha(img)
        return rgb

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

def titular(ctx,layer,t,lineas,ats,tam=120,cy=None,word_gap=36,line_gap=1.18):
    """Titular cinético: palabras con resorte en sus tiempos."""
    d=ImageDraw.Draw(layer)
    fnt=ctx.fT(tam,800)
    # auto-fit
    while tam>50:
        fnt=ctx.fT(tam,800)
        anchos=[seg_width(segs(ln),fnt) for ln in lineas]
        if max(anchos)<=980: break
        tam-=6
    ys=cy or H*0.44
    y0=ys-(len(lineas)-1)*tam*line_gap/2
    wi=0
    for li,ln in enumerate(lineas):
        sg=segs(ln); y=y0+li*tam*line_gap
        total=seg_width(sg,fnt); x=(W-total)/2
        for t_seg,em in sg:
            for ch in t_seg.split(" "):
                if not ch: x+=ctx.tmp.textlength(" ",font=fnt); continue
                at=ats[wi] if wi < len(ats) else ats[-1]; wi+=1
                k=spring(t,at,150,15)
                if k<=0:
                    x+=ctx.tmp.textlength(ch,font=fnt)+word_gap*0.4; continue
                sc=1.7-0.7*min(1,k)
                col=ROJO if em else BLANCO
                # dibujar con escala (aprox: offset vertical por escala)
                d.text((x,y+(1-min(1,k))*30),ch,font=fnt,
                       fill=col+(int(255*clamp01(k*1.5)),))
                x+=ctx.tmp.textlength(ch,font=fnt)+word_gap*0.4
            x+=ctx.tmp.textlength(" ",font=fnt)
    return tam

def rotulo(ctx,layer,t,texto,at,y=None,color=BLANCO,tam=44):
    if t<at: return
    k=spring(t,at,140,16)
    d=ImageDraw.Draw(layer)
    sg=segs(texto); fnt=ctx.fX(tam,700)
    draw_seg(d,((W)/2,y or H*0.30),sg,fnt,color,ROJO,anchor="ma")
    # alpha por resorte
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
    if t < cambio:
        titular(ctx,layer,t,e["texto1"],e["at"]["p1"],tam=150)
    else:
        titular(ctx,layer,t,e["texto2"],e["at"]["p2"],tam=124)
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
        iw=int(150*sc) if ctx.iso else 0
        total=iw+(26*sc if ctx.iso else 0)+tw
        x0=(W-total)/2
        if ctx.iso:
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
            x=W-90-tw; col=(58,20,14)
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
                                 fill=ROJO+(26,) if pi%2 else (250,248,246,22))
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
    titular(ctx,layer,t,e["lineas"],ats,tam=110,cy=H*0.36)
    g=e["at"]["gigante"]
    k=spring(t,g,80,9)
    if k>0:
        sc=2.2-1.2*min(1,k)
        fnt=ctx.fT(int(300*sc),800)
        tw=ctx.tmp.textlength(e["gigante"],font=fnt)
        # glow
        glow=Image.new("RGBA",(int(tw)+120,380),(0,0,0,0)); dg=ImageDraw.Draw(glow)
        dg.text((60,40),e["gigante"],font=fnt,fill=ROJO+(90,))
        glow=glow.filter(ImageFilter.GaussianBlur(30))
        layer.alpha_composite(glow,(int(W/2-glow.width/2),int(H*0.62-190)))
        d.text((W/2,H*0.62),e["gigante"],font=fnt,
               fill=BLANCO+(int(255*clamp01(k*1.4)),),anchor="ma")
    return capa_salida(layer,t,e["to"])

def sc_final(ctx,e,t):
    layer=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(layer)
    at=e["at"]
    k=spring(t,e["from"]+0.1,70,12)
    if k>0:
        # Solo DragonJAR usa el PNG oficial; otras marcas se rotulan con la tipografía
        if e["marca"].lower()=="dragonjar" and ctx.logo:
            lw=int(760*min(1,k))
            lg=ctx.logo.resize((lw,int(lw*ctx.logo.height/ctx.logo.width)),Image.LANCZOS)
            layer.alpha_composite(lg,(int(W/2-lw/2),int(H*0.40-lg.height/2)))
        else:
            fnt_m=ctx.fT(int(120*min(1,k)),800)
            d.text((W/2,H*0.40),e["marca"],font=fnt_m,
                   fill=BLANCO+(int(255*clamp01(k*1.4)),),anchor="mm")
    if t>=at["lema"]:
        rotulo(ctx,layer,t,e["lema"],at["lema"],y=H*0.58,tam=52)
    if t>=at["boton"]:
        kb=spring(t,at["boton"],120,14)
        bw,bh=520,110; x=(W-bw)/2; yy=H*0.70
        d.rounded_rectangle([x,yy,x+bw,yy+bh],radius=55,fill=ROJO+(int(255*min(1,kb)),))
        d.text((W/2,yy+bh/2),e["boton"],font=ctx.fX(40,800),fill=BLANCO,anchor="mm")
    return layer  # sin salida: fundido global al final

SCENES={"apertura":sc_apertura,"canales":sc_canales,"medianoche":sc_medianoche,
        "chat":sc_chat,"leads":sc_leads,"handoff":sc_handoff,"pago":sc_pago,
        "listo":sc_listo,"pildoras":sc_pildoras,"hoy":sc_hoy,"recupera":sc_recupera,
        "remate":sc_remate,"final":sc_final}

# ================= MAIN =================
def hex_a_rgb(h):
    h = h.strip().lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

def aplicar_brand(brand_path):
    """Lee el acento de un brand pack y lo instala como ROJO/ROJO_OSC globales."""
    global ROJO, ROJO_OSC
    try:
        d = json.load(open(os.path.expanduser(brand_path), encoding="utf-8"))
    except (OSError, ValueError) as e:
        sys.exit(f"ERROR: no se pudo leer el brand pack {brand_path}: {e}")
    colores = d.get("colors") or d.get("colores") or {}
    acento = colores.get("primary") or colores.get("acento") or colores.get("accent")
    if not acento:
        sys.exit(f"ERROR: el brand pack {brand_path} no declara color de acento")
    ROJO = hex_a_rgb(acento)
    ROJO_OSC = tuple(max(0, int(c * 0.65)) for c in ROJO)
    print(f"brand pack: {d.get('nombre', brand_path)} — acento {acento}", flush=True)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("plan"); ap.add_argument("-o","--out",required=True)
    ap.add_argument("--fps",type=int,default=30)
    ap.add_argument("--brand", default=None,
                    help="brand pack (brand/*.json); el plan también acepta campo \"brand\"")
    ap.add_argument("--force",action="store_true",
                    help="re-renderiza todos los frames aunque ya existan")
    a=ap.parse_args()
    plan=json.load(open(a.plan, encoding="utf-8"))
    brand_path = a.brand or plan.get("brand")
    if brand_path:
        aplicar_brand(brand_path)
    ctx=Ctx(); fps=a.fps
    dur=plan["duracion"]; n=int(dur*fps)
    escenas=sorted(plan["escenas"],key=lambda s:s["from"])
    tmpd=f"{a.out}.frames"; os.makedirs(tmpd,exist_ok=True)
    print(f"{n} frames, {len(escenas)} escenas",flush=True)
    for fi in range(n):
        fp=f"{tmpd}/f_{fi:04d}.png"
        if not a.force and os.path.exists(fp):
            if fi%150==0: print(f"  {fi}/{n} (salta, ya existe)",flush=True)
            continue
        t=fi/fps
        # escena activa
        s=None; si=0
        for i,e in enumerate(escenas):
            if e["from"]<=t<e["to"]: s=e; si=i; break
        if s is None: s=escenas[-1]; si=len(escenas)-1
        bg=mundo(ctx,t,seed=si+1)
        layer=SCENES[s["tipo"]](ctx,s,t).copy()
        # transición mancha: revela la nueva sobre la anterior (0.9s, más fluida)
        if s.get("transicion")=="mancha" and t-s["from"]<0.9 and si>0:
            prev=SCENES[escenas[si-1]["tipo"]](ctx,escenas[si-1],t)
            fx=s.get("transicionX",0.5); fy=s.get("transicionY",0.45)
            mask=mancha_mask(ctx,t,s["from"],0.9,fx,fy)
            inv=Image.eval(mask,lambda v:255-v)
            nada=Image.new("RGBA",(W,H),(0,0,0,0))
            bg.alpha_composite(Image.composite(prev,nada,inv))
            bg.alpha_composite(Image.composite(layer,nada,mask))
        else:
            bg.alpha_composite(layer)
        # fundido final global
        if dur-t<0.8:
            f2=Image.new("RGBA",(W,H),(0,0,0,int(255*clamp01((0.8-(dur-t))/0.8))))
            bg.alpha_composite(f2)
        bg.convert("RGB").save(fp)
        if fi%150==0: print(f"  {fi}/{n}",flush=True)
    print("frames ok, codificando…",flush=True)
    subprocess.run(["ffmpeg","-y","-v","error","-framerate",str(fps),
                    "-i",f"{tmpd}/f_%04d.png","-c:v","libx264","-preset","medium",
                    "-crf","20","-pix_fmt","yuv420p","-movflags","+faststart",a.out],
                   check=True)
    print("OK",a.out)

if __name__=="__main__": main()
