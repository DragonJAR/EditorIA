#!/usr/bin/env python3
"""Film de marca cinematográfico DragonJAR — 15s, 16:9, 24fps.
4 shots. El keyhole del isotipo es el centro geométrico de cada plano.
El logo se usa tal cual (escala uniforme, sin rotar ni deformar).

SUPERSEDED: usar `film_marca_v2.py` (dirección de arte preferida por el autor).
Este v1 se conserva solo como referencia histórica.
Uso: python film_marca.py -o film.mp4
"""
import os, sys, math, argparse, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W,H=1920,1080; FPS=24; DUR=15.0; N=int(DUR*FPS)
NEGRO=(10,10,10); ROJO=(193,27,5); BLANCO_H=(250,248,246)
BASE=os.path.dirname(os.path.abspath(__file__))
ISO_PATH=os.path.join(os.path.dirname(BASE),"brand","assets","dragonjar-isotipo.png")
JAKARTA = None
def _resolver_jakarta():
    """Resuelve la fuente Plus Jakarta Sans sin rutas hardcodeadas (Windows/macOS/Linux)."""
    import sys as _sys
    _sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg_tools"))
    try:
        from _plataforma import resolver_fuente
        hit = resolver_fuente("Plus Jakarta Sans", "Jakarta", generica="sans-bold")
        if hit:
            return hit
    except Exception:
        pass
    return None
JAKARTA = _resolver_jakarta()
if not JAKARTA:
    raise SystemExit("no se encontro fuente (Plus Jakarta Sans o similar)")


# keyhole en coords originales del PNG (1126x1126), medido
KH_SRC=(559.7,540.9)
# isotipo en pantalla: 700px, keyhole en el centro del frame
ISO_S=700; SC=ISO_S/1126.0
KH=(960,540)
ISO_POS=(int(KH[0]-KH_SRC[0]*SC),int(KH[1]-KH_SRC[1]*SC))

def clamp01(x): return max(0.0,min(1.0,x))
def lerp(a,b,k): return a+(b-a)*k
def bezier_out(k):
    """cubic-bezier(0.2,0,0,1) aproximado (easeOutExpo-like)."""
    k=clamp01(k); return 1-pow(1-k,3) if k<1 else 1
def prog(t,a,b): return clamp01((t-a)/max(1e-6,b-a))

class Ctx:
    def __init__(self):
        src=Image.open(ISO_PATH).convert("RGBA")
        self.iso=src.resize((ISO_S,ISO_S),Image.LANCZOS)  # escala uniforme, sin deformar
        self.iso_rgb=self.iso.convert("RGB")
        # (a) blanco monocromo
        a=self.iso.split()[3]
        self.iso_white=Image.merge("RGBA",(Image.new("L",(ISO_S,ISO_S),250),
            Image.new("L",(ISO_S,ISO_S),248),Image.new("L",(ISO_S,ISO_S),246),a))
        # (b) rojo plano #C11B05
        self.iso_red=Image.merge("RGBA",(Image.new("L",(ISO_S,ISO_S),193),
            Image.new("L",(ISO_S,ISO_S),27),Image.new("L",(ISO_S,ISO_S),5),a))
        # (c) outline: bordes del alpha
        edge=a.filter(ImageFilter.FIND_EDGES)
        self.iso_edge=Image.merge("RGBA",(Image.new("L",(ISO_S,ISO_S),193),
            Image.new("L",(ISO_S,ISO_S),27),Image.new("L",(ISO_S,ISO_S),5),edge))
        # mini isotipo para patrón (d)
        self.iso_mini=self.iso.resize((110,110),Image.LANCZOS)
        self.trace=self._trace_path()
        random.seed(7)
        # brasas a la deriva (shot 1): x, velocidad, fase, tamaño, blur
        self.drift=[(random.uniform(0,W),random.uniform(25,60),
                     random.uniform(0,6.28),random.uniform(2,5),
                     random.choice([0,0,2])) for _ in range(26)]
        # brasas en órbita (shots 2-3): radio, ángulo0, omega, tamaño
        self.orbit=[(random.uniform(240,400),random.uniform(0,6.28),
                     random.uniform(0.25,0.5)*(1 if i%2 else -1),
                     random.uniform(2,4)) for i in range(22)]
        # halo volumétrico
        self.haze=self._radial(700,(193,27,5,26))
        self.ember=self._radial(160,(255,60,20,255))

    def _radial(self,r,color):
        s=r*2; img=Image.new("RGBA",(s,s),(0,0,0,0))
        px=img.load()
        # construido con numpy para velocidad
        yy,xx=np.mgrid[0:s,0:s]
        d=np.sqrt((xx-r)**2+(yy-r)**2)/r
        al=np.clip(1-d,0,1)**2.2
        arr=np.zeros((s,s,4),dtype=np.uint8)
        arr[...,0]=color[0]; arr[...,1]=color[1]; arr[...,2]=color[2]
        arr[...,3]=(al*color[3]).astype(np.uint8)
        return Image.fromarray(arr,"RGBA")

    def _trace_path(self):
        """Puntos del contorno ordenados por vecino más cercano (para el láser)."""
        a=np.array(self.iso.split()[3])
        edge=np.array(Image.fromarray(a).filter(ImageFilter.FIND_EDGES))
        ys,xs=np.nonzero(edge>40)
        pts=np.stack([xs,ys],axis=1)
        step=max(1,len(pts)//1100)
        pts=pts[::step]
        order=[int(np.argmax(pts[:,1]))]  # empezar arriba
        rem=set(range(len(pts))); rem.discard(order[0])
        cur=pts[order[0]].astype(float)
        rem_arr=np.array(sorted(rem))
        # greedy NN vectorizado
        remaining=pts[rem_arr]
        idx_map=rem_arr
        while len(remaining)>0:
            d2=((remaining-cur)**2).sum(axis=1)
            bi=int(np.argmin(d2))
            order.append(int(idx_map[bi]))
            cur=remaining[bi]
            mask=np.ones(len(remaining),bool); mask[bi]=False
            remaining=remaining[mask]; idx_map=idx_map[mask]
            if len(order)%300==0: pass
        path=pts[np.array(order)]
        # a coords de pantalla
        path[:,0]+=ISO_POS[0]; path[:,1]+=ISO_POS[1]
        return path

def draw_glow(layer,img,cx,cy,scale,alpha):
    w2=int(img.width*scale); h2=int(img.height*scale)
    g=img.resize((w2,h2),Image.BILINEAR)
    if alpha<255:
        al=g.split()[3].point(lambda v:int(v*alpha/255)); g.putalpha(al)
    layer.alpha_composite(g,(int(cx-w2/2),int(cy-h2/2)))

def text_center(d,xy,txt,font,fill,tracking=0):
    x,y=xy
    if tracking<=0:
        d.text((x,y),txt,font=font,fill=fill,anchor="ma"); return
    widths=[d.textlength(c,font=font) for c in txt]
    total=sum(widths)+tracking*(len(txt)-1)
    cx=x-total/2
    for c,wc in zip(txt,widths):
        d.text((cx,y),c,font=font,fill=fill,anchor="la")
        cx+=wc+tracking

def mixed_line(d,cx,y,segments,font):
    """segments=[(texto,color)]. Centrado."""
    widths=[d.textlength(t,font=font) for t,_ in segments]
    gaps=[d.textlength(" ",font=font)]*(len(segments)-1)
    total=sum(widths)+sum(gaps)
    x=cx-total/2
    for i,(t,col) in enumerate(segments):
        d.text((x,y),t,font=font,fill=col,anchor="la")
        x+=widths[i]+(gaps[i] if i<len(gaps) else 0)

def render_frame(ctx,t,state):
    img=Image.new("RGB",(W,H),NEGRO)
    layer=Image.new("RGBA",(W,H),(0,0,0,0))
    d=ImageDraw.Draw(layer)
    # halo volumétrico respirando
    br=1+0.06*math.sin(t*0.8)
    draw_glow(layer,ctx.haze,KH[0],KH[1],br*1.4,90)

    # ---------- SHOT 1 (0-3): oscuridad, brasa en el keyhole, push-in ----------
    if t<3.2:
        # isotipo apenas visible en la penumbra
        iso=ctx.iso.copy()
        al=iso.split()[3].point(lambda v:int(v*0.10))
        iso.putalpha(al)
        layer.alpha_composite(iso,ISO_POS)
        # brasa: un pulso
        pk=math.sin(math.pi*clamp01(t/2.6))  # 0→1→0
        if pk>0:
            draw_glow(layer,ctx.ember,KH[0],KH[1],0.5+0.9*pk,int(255*pk))
            r=int(10+26*pk)
            d.ellipse([KH[0]-r,KH[1]-r,KH[0]+r,KH[1]+r],fill=(255,120,40,int(200*pk)))
        # brasas microscópicas a la deriva (hacia arriba)
        for x0,spd,ph,sz,bl in ctx.drift:
            y=(H+80-((t*spd+ph*40)%(H+240)))
            x=x0+18*math.sin(t*0.7+ph)
            a2=int(150*clamp01(1-abs(y-H/2)/(H*0.7)))
            if bl: 
                s2=Image.new("RGBA",(24,24),(0,0,0,0))
                ImageDraw.Draw(s2).ellipse([12-sz,12-sz,12+sz,12+sz],fill=(255,70,25,a2))
                s2=s2.filter(ImageFilter.GaussianBlur(2))
                layer.alpha_composite(s2,(int(x-12),int(y-12)))
            else:
                d.ellipse([x-sz,y-sz,x+sz,y+sz],fill=(255,70,25,a2))

    # ---------- SHOT 2 (3-7): láser traza el contorno ----------
    if 3.0<=t<7.2:
        # trazo progresivo (acumula SOLO segmentos en state; la cabeza es transitoria)
        p=bezier_out(prog(t,3.0,6.0))
        n=int(p*len(ctx.trace))
        if n>state["tn"]:
            td=ImageDraw.Draw(state["trace_img"])
            pts=ctx.trace[state["tn"]:n]
            for i in range(len(pts)-1):
                x1,y1=pts[i]; x2,y2=pts[i+1]
                if abs(x2-x1)+abs(y2-y1)>16: continue  # salto: no dibujar
                td.line([(x1,y1),(x2,y2)],fill=(255,60,20,200),width=3)
            state["tn"]=n
        # el trazo se atenúa al final del shot
        talpha=1-prog(t,6.2,7.1)
        if talpha>0:
            ti=state["trace_img"].copy()
            al=ti.split()[3].point(lambda v:int(v*talpha)); ti.putalpha(al)
            layer.alpha_composite(ti,(0,0))
        # cabeza del láser: capa transitoria (no se acumula)
        if 3.0<=t<6.2 and n>0 and n<len(ctx.trace):
            hx,hy=ctx.trace[n-1]
            hl=Image.new("RGBA",(W,H),(0,0,0,0)); dh=ImageDraw.Draw(hl)
            dh.ellipse([hx-10,hy-10,hx+10,hy+10],fill=(255,210,160,255))
            hl=hl.filter(ImageFilter.GaussianBlur(6))
            layer.alpha_composite(hl,(0,0))
            d.ellipse([hx-5,hy-5,hx+5,hy+5],fill=(255,230,200,255))
        # isotipo revelado como unidad
        io=prog(t,5.2,6.8)
        if io>0:
            iso=ctx.iso.copy()
            al=iso.split()[3].point(lambda v:int(v*io))
            iso.putalpha(al)
            # shimmer de escamas: bandas diagonales breves
            sh=prog(t,6.0,6.4)*(1-prog(t,6.6,7.0))
            if sh>0:
                shimmer=Image.new("L",(ISO_S,ISO_S),0)
                ds=ImageDraw.Draw(shimmer)
                off=int(t*900)%160
                for b in range(-ISO_S,ISO_S*2,160):
                    ds.line([(b+off,0),(b+off-ISO_S,ISO_S)],fill=int(90*sh),width=26)
                hi=Image.new("RGBA",(ISO_S,ISO_S),(255,255,255,0))
                hi.putalpha(shimmer)
                iso=Image.alpha_composite(iso,hi)
            layer.alpha_composite(iso,ISO_POS)
        # brasas en órbita lenta alrededor del keyhole
        oa=prog(t,3.2,4.2)*(1-prog(t,10.8,11.6))
        if oa>0:
            for rr,a0,om,sz in ctx.orbit:
                an=a0+t*om
                x=KH[0]+rr*math.cos(an); y=KH[1]+rr*math.sin(an)*0.92
                d.ellipse([x-sz,y-sz,x+sz,y+sz],fill=(255,80,30,int(170*oa)))

    # ---------- SHOT 3 (7-11): variaciones con match-cut en el keyhole ----------
    if 7.0<=t<11.2:
        # segmentos de 1s con dissolve de 0.25 en el beat
        variants=[ctx.iso_white,ctx.iso_red,ctx.iso_edge]
        seg=min(2,int(t-7.0))  # 0,1,2 → a,b,c
        local=(t-7.0)-seg
        cur=variants[seg]
        if local>0.75 and seg<2:
            nxt=variants[seg+1]
            k=bezier_out(prog(local,0.75,1.0))
            layer.alpha_composite(cur,ISO_POS)
            tmp=nxt.copy(); al=tmp.split()[3].point(lambda v:int(v*k)); tmp.putalpha(al)
            layer.alpha_composite(tmp,ISO_POS)
        else:
            layer.alpha_composite(cur,ISO_POS)
        # (d) 10-11: patrón de mini isotipos que vuelve a uno
        if t>=10.0:
            k=prog(t,10.0,10.5)
            pat=Image.new("RGBA",(W,H),(0,0,0,0))
            # rejilla de minis centrada en el keyhole
            for gy in range(-2,3):
                for gx in range(-4,5):
                    mx=int(KH[0]+gx*150-55); my=int(KH[1]+gy*150-55)
                    m=ctx.iso_mini.copy()
                    al=m.split()[3].point(lambda v:int(v*110*k)); m.putalpha(al)
                    pat.alpha_composite(m,(mx,my))
            layer.alpha_composite(pat,(0,0))
            if t>=10.5:
                k2=bezier_out(prog(t,10.5,11.1))
                iso=ctx.iso_red.copy()
                al=iso.split()[3].point(lambda v:int(v*k2)); iso.putalpha(al)
                layer.alpha_composite(iso,ISO_POS)

    # ---------- SHOT 4 (11-15): isotipo full color + wordmark + tagline ----------
    if t>=11.0:
        iso=ctx.iso.copy()
        if t<11.4:  # dissolve desde la variación
            al=iso.split()[3].point(lambda v:int(v*prog(t,11.0,11.4)))
            iso.putalpha(al)
        layer.alpha_composite(iso,ISO_POS)
        # brasas que se asientan
        sa=1-prog(t,11.2,12.6)
        if sa>0:
            for rr,a0,om,sz in ctx.orbit[:10]:
                an=a0+11.2*om+(t-11.2)*om*0.15
                x=KH[0]+rr*math.cos(an); y=KH[1]+rr*math.sin(an)*0.92
                d.ellipse([x-sz,y-sz,x+sz,y+sz],fill=(255,80,30,int(150*sa)))
        # wordmark: barrido izquierda→derecha (y=820, sin solaparse con el tagline)
        if t>=11.8:
            fnt=ImageFont.truetype(JAKARTA,56)
            wm=Image.new("RGBA",(W,120),(0,0,0,0)); dw=ImageDraw.Draw(wm)
            text_center(dw,(W/2,60),"DRAGONJAR",fnt,BLANCO_H+(255,),tracking=26)
            sw=bezier_out(prog(t,11.8,12.6))
            if sw<1:
                m=Image.new("L",(W,120),0)
                ImageDraw.Draw(m).rectangle([0,0,int(W*sw),120],fill=255)
                wm.putalpha(Image.composite(wm.split()[3],Image.new("L",(W,120),0),m))
            layer.alpha_composite(wm,(0,879))
        # tagline en UNA línea (cabe a 34px; dos líneas no caben con el zoom)
        if t>=12.9:
            ka=prog(t,12.9,13.4)
            fnt2=ImageFont.truetype(JAKARTA,34)
            tg=Image.new("RGBA",(W,80),(0,0,0,0)); dt=ImageDraw.Draw(tg)
            mixed_line(dt,W/2,10,[("HACKEAMOS TU ",BLANCO_H),("EMPRESA",ROJO),
                                  (" PARA QUE UN ",BLANCO_H),
                                  ("DELINCUENTE INFORMÁTICO",ROJO),
                                  (" NO LO HAGA.",BLANCO_H)],fnt2)
            if ka<1:
                al=tg.split()[3].point(lambda v:int(v*ka)); tg.putalpha(al)
            layer.alpha_composite(tg,(0,989))

    img=Image.composite(layer.convert("RGB"),img,layer.split()[3])
    # push-in lento centrado en el keyhole (= centro): 1.00→1.06 en 15s.
    # OJO: con zoom, el área segura es y < 540+540/z (a z=1.06 → y<1049).
    z=1+0.06*bezier_out(t/DUR)
    zw,zh=int(W*z),int(H*z)
    zm=img.resize((zw,zh),Image.BILINEAR)
    img=zm.crop(((zw-W)//2,(zh-H)//2,(zw-W)//2+W,(zh-H)//2+H))
    # grano de película sutil
    gr=(np.random.randint(-7,8,size=(H,W,1))).astype(np.int16)
    arr=np.asarray(img).astype(np.int16)+gr
    img=Image.fromarray(np.clip(arr,0,255).astype(np.uint8))
    # fundido a negro final
    if t>13.8:
        f=Image.new("RGB",(W,H),(0,0,0))
        img=Image.blend(img,f,prog(t,13.8,15.0))
    return img

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("-o","--out",required=True)
    a=ap.parse_args()
    ctx=Ctx()
    print(f"trace: {len(ctx.trace)} puntos",flush=True)
    state={"tn":0,"trace_img":Image.new("RGBA",(W,H),(0,0,0,0))}
    tmpd=a.out+".frames"; os.makedirs(tmpd,exist_ok=True)
    for fi in range(N):
        t=fi/FPS
        render_frame(ctx,t,state).save(f"{tmpd}/f_{fi:04d}.png")
        if fi%48==0: print(f"  {fi}/{N}  t={t:.1f}s",flush=True)
    import sys as _sys
    _sys.path.insert(0, os.path.join(BASE, "ffmpeg_tools"))
    from _comun import codificar_frames   # H.264 BT.709 exacto (color de marca fiel)
    codificar_frames(f"{tmpd}/f_%04d.png", FPS, a.out, crf=18)
    print("OK",a.out)

if __name__=="__main__": main()
