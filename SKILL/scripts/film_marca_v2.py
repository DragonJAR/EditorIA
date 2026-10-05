#!/usr/bin/env python3
"""Film de marca v2 — dirección de arte (marca del pack o de --logo/--nombre/--lema).
15s, 16:9, 24fps. El isotipo RESPIRA por el plano (no clavado al centro):
macro del keyhole → tercio derecho (trazo láser) → centro (variaciones con
pulso) → final asimétrico (isotipo izquierda, texto derecha).
El ancla del logo (pack logos.ancla, o su centro de masa) es el ancla compositiva;
el logo nunca se deforma ni rota.
Uso: python film_marca_v2.py --brand brand/mi_marca.json -o film.mp4
"""
import os, math, argparse, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W,H=1920,1080; FPS=24; DUR=15.0; N=int(DUR*FPS)
BASE=os.path.dirname(os.path.abspath(__file__))
import sys
sys.path.insert(0, BASE)
from _film import (LADO, args_identidad, clamp01, dibujar_lema, draw_glow, lerp,  # noqa: E402
                   lineas_lema, preparar, prog, text_center, vivo)
# Identidad: se fija en main() desde el pack pedido o los flags (_film.preparar).
NEGRO=ROJO=BLANCO_H=BRASA=BRASA_SUAVE=CALIDO=CHISPA=None
LOGO=None; JAKARTA=None; NOMBRE=""; LEMA=[]
KH_SRC=None  # ancla del logo en el lienzo LADO (pack logos.ancla o centro de masa)

def smooth(k):
    k=clamp01(k); return k*k*(3-2*k)
def bezier_out(k):
    k=clamp01(k); return 1-pow(1-k,3) if k<1 else 1

# coreografía: (t, size, kh_x, kh_y)
KEYS=[(0.0,2000,960,540),(3.0,2080,960,540),(3.8,750,1150,520),
      (6.8,750,1150,520),(7.4,700,960,540),(11.0,700,960,540),
      (11.8,520,640,540),(15.0,545,640,540)]
def choreo(t):
    for i in range(len(KEYS)-1):
        t0,_,_,_=KEYS[i]; t1,_,_,_=KEYS[i+1]
        if t0<=t<=t1:
            _,s0,x0,y0=KEYS[i]; _,s1,x1,y1=KEYS[i+1]
            k=smooth(prog(t,t0,t1))
            return lerp(s0,s1,k),lerp(x0,x1,k),lerp(y0,y1,k)
    _,s,x,y=KEYS[-1]; return s,x,y
def beat_pulse(t):
    p=0.0
    for b in (8.35,9.25,10.15):
        p+=0.035*math.exp(-((t-b)/0.16)**2)
    return 1+p

class Ctx:
    def __init__(self):
        src=LOGO.copy()   # cuadrado LADO px, escala uniforme (_film.preparar)
        self.src=src
        self.iso1400=src.resize((1400,1400),Image.LANCZOS)
        a1400=self.iso1400.split()[3]
        self.variants={
            "color":self.iso1400,
            "white":Image.merge("RGBA",(Image.new("L",(1400,1400),BLANCO_H[0]),
                Image.new("L",(1400,1400),BLANCO_H[1]),Image.new("L",(1400,1400),BLANCO_H[2]),a1400)),
            "red":Image.merge("RGBA",(Image.new("L",(1400,1400),ROJO[0]),
                Image.new("L",(1400,1400),ROJO[1]),Image.new("L",(1400,1400),ROJO[2]),a1400)),
            "edge":Image.merge("RGBA",(Image.new("L",(1400,1400),ROJO[0]),
                Image.new("L",(1400,1400),ROJO[1]),Image.new("L",(1400,1400),ROJO[2]),
                a1400.filter(ImageFilter.FIND_EDGES))),
        }
        self.mini=src.resize((110,110),Image.LANCZOS)
        # trazo en coords locales (keyhole en KH_SRC)
        self.trace_local=self._trace_path()
        random.seed(11)
        self.drift=[(random.uniform(0,W),random.uniform(30,70),
                     random.uniform(0,6.28),random.uniform(2,5),
                     random.choice([0,2])) for _ in range(30)]
        self.orbit=[(random.uniform(220,380),random.uniform(0,6.28),
                     random.uniform(0.3,0.6)*(1 if i%2 else -1),
                     random.uniform(2,4)) for i in range(24)]
        self.haze=self._radial(700,ROJO+(26,))
        self.ember=self._radial(160,BRASA+(255,))

    def _radial(self,r,color):
        s=r*2
        yy,xx=np.mgrid[0:s,0:s]
        d=np.sqrt((xx-r)**2+(yy-r)**2)/r
        al=np.clip(1-d,0,1)**2.2
        arr=np.zeros((s,s,4),dtype=np.uint8)
        arr[...,0]=color[0]; arr[...,1]=color[1]; arr[...,2]=color[2]
        arr[...,3]=(al*color[3]).astype(np.uint8)
        return Image.fromarray(arr,"RGBA")

    def _trace_path(self):
        small=self.src.resize((700,700),Image.LANCZOS)
        a=np.array(small.split()[3])
        edge=np.array(Image.fromarray(a).filter(ImageFilter.FIND_EDGES))
        ys,xs=np.nonzero(edge>40)
        pts=np.stack([xs,ys],axis=1).astype(float)
        # a coords del lienzo LADO
        pts=pts/700*LADO
        step=max(1,len(pts)//1100); pts=pts[::step]
        order=[int(np.argmax(pts[:,1]))]
        remaining=pts.copy(); idx=np.arange(len(pts))
        mask=np.ones(len(pts),bool); mask[order[0]]=False
        remaining=remaining[mask]; idx=idx[mask]
        cur=pts[order[0]]
        while len(remaining)>0:
            d2=((remaining-cur)**2).sum(axis=1)
            bi=int(np.argmin(d2))
            order.append(int(idx[bi])); cur=remaining[bi]
            m=np.ones(len(remaining),bool); m[bi]=False
            remaining=remaining[m]; idx=idx[m]
        return pts[np.array(order)]  # locales LADO, ancla en KH_SRC

    def iso_at(self,size,variant="color"):
        v=self.variants[variant]
        return v.resize((int(size),int(size)),Image.BILINEAR)

def place_iso(layer,iso,size,khx,khy,alpha=1.0):
    """Pega el isotipo de `size` px con el keyhole en (khx,khy)."""
    if alpha<1.0:
        al=iso.split()[3].point(lambda v:int(v*alpha)); iso.putalpha(al)
    x=int(khx-KH_SRC[0]/LADO*size); y=int(khy-KH_SRC[1]/LADO*size)
    layer.alpha_composite(iso,(x,y))

def render_frame(ctx,t):
    img=Image.new("RGB",(W,H),NEGRO)
    layer=Image.new("RGBA",(W,H),(0,0,0,0))
    d=ImageDraw.Draw(layer)
    size,khx,khy=choreo(t)
    # halo volumétrico sigue al keyhole
    draw_glow(layer,ctx.haze,khx,khy,1.2+0.08*math.sin(t*0.9),80)

    # ---- 0-3: MACRO del keyhole ----
    if t<3.4:
        iso=ctx.iso_at(size)
        al=iso.split()[3].point(lambda v:int(v*0.16)); iso.putalpha(al)
        place_iso(layer,iso,size,khx,khy)
        pk=math.sin(math.pi*clamp01((t-0.3)/2.4))
        if pk>0:
            draw_glow(layer,ctx.ember,khx,khy,0.6+1.0*pk,int(255*pk))
            r=int(12+30*pk)
            d.ellipse([khx-r,khy-r,khx+r,khy+r],fill=CALIDO+(int(210*pk),))
        for x0,spd,ph,sz,bl in ctx.drift:
            y=(H+80-((t*spd+ph*40)%(H+240)))
            x=x0+18*math.sin(t*0.7+ph)
            a2=int(150*clamp01(1-abs(y-H/2)/(H*0.7)))
            if bl:
                s2=Image.new("RGBA",(24,24),(0,0,0,0))
                ImageDraw.Draw(s2).ellipse([12-sz,12-sz,12+sz,12+sz],fill=BRASA+(a2,))
                layer.alpha_composite(s2.filter(ImageFilter.GaussianBlur(2)),(int(x-12),int(y-12)))
            else:
                d.ellipse([x-sz,y-sz,x+sz,y+sz],fill=BRASA+(a2,))

    # ---- 3.4-7.4: PULLBACK + trazo láser (tercio derecho) ----
    if 3.4<=t<7.5:
        p=bezier_out(prog(t,3.9,6.9))
        n=int(p*len(ctx.trace_local))
        if n>1:
            sc=size/LADO
            kx,ky=KH_SRC
            pts=(ctx.trace_local[:n]-np.array([kx,ky]))*sc+np.array([khx,khy])
            tl=Image.new("RGBA",(W,H),(0,0,0,0)); td=ImageDraw.Draw(tl)
            for i in range(len(pts)-1):
                x1,y1=pts[i]; x2,y2=pts[i+1]
                if abs(x2-x1)+abs(y2-y1)>20*sc+8: continue
                td.line([(x1,y1),(x2,y2)],fill=BRASA+(210,),width=3)
            talpha=1-prog(t,6.9,7.4)
            if talpha<1:
                al=tl.split()[3].point(lambda v:int(v*talpha)); tl.putalpha(al)
            layer.alpha_composite(tl,(0,0))
            if n<len(ctx.trace_local) and t<6.9:
                hx,hy=pts[-1]
                hl=Image.new("RGBA",(W,H),(0,0,0,0))
                ImageDraw.Draw(hl).ellipse([hx-9,hy-9,hx+9,hy+9],fill=CHISPA+(255,))
                layer.alpha_composite(hl.filter(ImageFilter.GaussianBlur(5)),(0,0))
        io=prog(t,6.0,7.1)
        if io>0:
            place_iso(layer,ctx.iso_at(size),size,khx,khy,alpha=io)
        oa=prog(t,4.0,4.8)*(1-prog(t,10.8,11.6))
        if oa>0:
            for rr,a0,om,sz in ctx.orbit:
                an=a0+t*om
                x=khx+rr*math.cos(an); y=khy+rr*math.sin(an)*0.92
                d.ellipse([x-sz,y-sz,x+sz,y+sz],fill=BRASA_SUAVE+(int(170*oa),))

    # ---- 7.4-11.2: VARIACIONES al centro, con pulso ----
    if 7.2<=t<11.3:
        s2=size*beat_pulse(t)
        variants=["white","red","edge"]
        seg=min(2,int(t-7.4))
        local=(t-7.4)-seg
        cur=variants[seg]
        if local>0.72 and seg<2:
            k=bezier_out(prog(local,0.72,1.0))
            place_iso(layer,ctx.iso_at(s2,cur),s2,khx,khy)
            place_iso(layer,ctx.iso_at(s2,variants[seg+1]),s2,khx,khy,alpha=k)
        else:
            place_iso(layer,ctx.iso_at(s2,cur),s2,khx,khy)
        if t>=10.1:
            k=prog(t,10.1,10.6)
            pat=Image.new("RGBA",(W,H),(0,0,0,0))
            for gy in range(-2,3):
                for gx in range(-4,5):
                    m=ctx.mini.copy()
                    al=m.split()[3].point(lambda v:int(v*110*k)); m.putalpha(al)
                    pat.alpha_composite(m,(int(khx+gx*150-55),int(khy+gy*150-55)))
            layer.alpha_composite(pat,(0,0))
            if t>=10.6:
                place_iso(layer,ctx.iso_at(s2,"red"),s2,khx,khy,
                          alpha=bezier_out(prog(t,10.6,11.2)))

    # ---- 11.2-15: FINAL asimétrico (isotipo izq, texto der) ----
    if t>=11.2:
        s3=size
        if t<11.9:
            place_iso(layer,ctx.iso_at(s3,"red"),s3,khx,khy,alpha=prog(t,11.2,11.9))
        else:
            place_iso(layer,ctx.iso_at(s3),s3,khx,khy)
        sa=1-prog(t,11.4,12.8)
        if sa>0:
            for rr,a0,om,sz in ctx.orbit[:10]:
                an=a0+11.4*om+(t-11.4)*om*0.12
                x=khx+rr*math.cos(an); y=khy+rr*math.sin(an)*0.92
                d.ellipse([x-sz,y-sz,x+sz,y+sz],fill=BRASA_SUAVE+(int(150*sa),))
        tx=1380  # centro del bloque de texto
        if t>=11.9 and NOMBRE:
            fnt=ImageFont.truetype(JAKARTA,50)
            wm=Image.new("RGBA",(W,110),(0,0,0,0)); dw=ImageDraw.Draw(wm)
            text_center(dw,(tx,55),NOMBRE,fnt,BLANCO_H+(255,),tracking=22)
            sw=bezier_out(prog(t,11.9,12.7))
            if sw<1:
                m=Image.new("L",(W,110),0)
                ImageDraw.Draw(m).rectangle([0,0,int(W*sw),110],fill=255)
                wm.putalpha(Image.composite(wm.split()[3],Image.new("L",(W,110),0),m))
            layer.alpha_composite(wm,(0,380))
        if t>=12.9 and LEMA:
            ka=prog(t,12.9,13.4)
            fnt2=ImageFont.truetype(JAKARTA,30)
            tg=Image.new("RGBA",(W,140),(0,0,0,0)); dt=ImageDraw.Draw(tg)
            dibujar_lema(tg,tx,8,lineas_lema(dt,LEMA,fnt2,W*0.42)[:3],fnt2,BLANCO_H,ROJO,50)
            if ka<1:
                al=tg.split()[3].point(lambda v:int(v*ka)); tg.putalpha(al)
            layer.alpha_composite(tg,(0,520))

    img=Image.composite(layer.convert("RGB"),img,layer.split()[3])
    # push-in global sutil 1.00→1.06
    z=1+0.06*bezier_out(t/DUR)
    zw,zh=int(W*z),int(H*z)
    zm=img.resize((zw,zh),Image.BILINEAR)
    img=zm.crop(((zw-W)//2,(zh-H)//2,(zw-W)//2+W,(zh-H)//2+H))
    gr=(np.random.randint(-7,8,size=(H,W,1))).astype(np.int16)
    arr=np.asarray(img).astype(np.int16)+gr
    img=Image.fromarray(np.clip(arr,0,255).astype(np.uint8))
    if t>13.8:
        img=Image.blend(img,Image.new("RGB",(W,H),(0,0,0)),prog(t,13.8,15.0))
    return img

def configurar(a):
    """Instala la identidad pedida (pack o flags) en los globales del film."""
    global NEGRO, ROJO, BLANCO_H, BRASA, BRASA_SUAVE, CALIDO, CHISPA, LOGO, JAKARTA, NOMBRE, LEMA, KH_SRC
    idt=preparar(a)
    p=idt["paleta"]; NEGRO,ROJO,BLANCO_H=p["negro"],p["acento"],p["blanco"]
    BRASA,BRASA_SUAVE,CALIDO,CHISPA=vivo(ROJO,0.10),vivo(ROJO,0.16),vivo(ROJO,0.30),vivo(ROJO,0.70)
    LOGO,JAKARTA,NOMBRE,LEMA,KH_SRC=idt["logo"],idt["fuente"],idt["nombre"],idt["lema"],idt["ancla"]

def main():
    ap=argparse.ArgumentParser(description="Film de marca 16:9 (15 s, 24 fps) sobre el logo de la marca pedida.")
    ap.add_argument("-o","--out",required=True)
    args_identidad(ap)
    a=ap.parse_args()
    configurar(a)
    ctx=Ctx()
    print(f"trace: {len(ctx.trace_local)} puntos",flush=True)
    tmpd=a.out+".frames"; os.makedirs(tmpd,exist_ok=True)
    for fi in range(N):
        t=fi/FPS
        render_frame(ctx,t).save(f"{tmpd}/f_{fi:04d}.png")
        if fi%48==0: print(f"  {fi}/{N}  t={t:.1f}s",flush=True)
    import sys as _sys
    _sys.path.insert(0, os.path.join(BASE, "ffmpeg_tools"))
    from _comun import codificar_frames   # H.264 BT.709 exacto (color de marca fiel)
    codificar_frames(f"{tmpd}/f_%04d.png", FPS, a.out, crf=18)
    print("OK",a.out)

if __name__=="__main__": main()
