#!/usr/bin/env python3
"""Film de marca cinematográfico — 15s, 16:9, 24fps (marca del pack o flags).
4 shots. El ancla del logo es el centro geométrico de cada plano.
El logo se usa tal cual (escala uniforme, sin rotar ni deformar).

SUPERSEDED: usar `film_marca_v2.py` (dirección de arte preferida por el autor).
Este v1 se conserva solo como referencia histórica.
Uso: python film_marca.py --brand brand/mi_marca.json -o film.mp4
"""
import os, sys, math, argparse, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W,H=1920,1080; FPS=24; DUR=15.0; N=int(DUR*FPS)
BASE=os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from _film import (LADO, args_formato, args_identidad, clamp01, dibujar_lema,  # noqa: E402
                   draw_glow, lienzo, lineas_lema, preparar, prog, rejilla, text_center, vivo)
# Identidad: se fija en main() desde el pack pedido o los flags (_film.preparar).
NEGRO=ROJO=BLANCO_H=BRASA=BRASA_SUAVE=CALIDO=CHISPA=None
LOGO=None; JAKARTA=None; NOMBRE=""; LEMA=[]
# logo en pantalla: 700px, su ancla en el centro del frame (16:9) o en el
# tercio alto (9:16, el texto debajo queda en la zona segura); en configurar
ISO_S=700; SC=ISO_S/LADO
KH=(960,540)
KH_SRC=None; ISO_POS=None

def bezier_out(k):
    """cubic-bezier(0.2,0,0,1) aproximado (easeOutExpo-like)."""
    k=clamp01(k); return 1-pow(1-k,3) if k<1 else 1

class Ctx:
    def __init__(self):
        src=LOGO.copy()   # cuadrado LADO px, escala uniforme (_film.preparar)
        self.iso=src.resize((ISO_S,ISO_S),Image.LANCZOS)  # escala uniforme, sin deformar
        self.iso_rgb=self.iso.convert("RGB")
        # (a) blanco monocromo
        a=self.iso.split()[3]
        self.iso_white=Image.merge("RGBA",(Image.new("L",(ISO_S,ISO_S),BLANCO_H[0]),
            Image.new("L",(ISO_S,ISO_S),BLANCO_H[1]),Image.new("L",(ISO_S,ISO_S),BLANCO_H[2]),a))
        # (b) acento plano del pack
        self.iso_red=Image.merge("RGBA",(Image.new("L",(ISO_S,ISO_S),ROJO[0]),
            Image.new("L",(ISO_S,ISO_S),ROJO[1]),Image.new("L",(ISO_S,ISO_S),ROJO[2]),a))
        # (c) outline: bordes del alpha
        edge=a.filter(ImageFilter.FIND_EDGES)
        self.iso_edge=Image.merge("RGBA",(Image.new("L",(ISO_S,ISO_S),ROJO[0]),
            Image.new("L",(ISO_S,ISO_S),ROJO[1]),Image.new("L",(ISO_S,ISO_S),ROJO[2]),edge))
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
        self.haze=self._radial(700,ROJO+(26,))
        self.ember=self._radial(160,BRASA+(255,))

    def _radial(self,r,color):
        s=r*2
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
            d.ellipse([KH[0]-r,KH[1]-r,KH[0]+r,KH[1]+r],fill=CALIDO+(int(200*pk),))
        # brasas microscópicas a la deriva (hacia arriba)
        for x0,spd,ph,sz,bl in ctx.drift:
            y=(H+80-((t*spd+ph*40)%(H+240)))
            x=x0+18*math.sin(t*0.7+ph)
            a2=int(150*clamp01(1-abs(y-H/2)/(H*0.7)))
            if bl: 
                s2=Image.new("RGBA",(24,24),(0,0,0,0))
                ImageDraw.Draw(s2).ellipse([12-sz,12-sz,12+sz,12+sz],fill=BRASA+(a2,))
                s2=s2.filter(ImageFilter.GaussianBlur(2))
                layer.alpha_composite(s2,(int(x-12),int(y-12)))
            else:
                d.ellipse([x-sz,y-sz,x+sz,y+sz],fill=BRASA+(a2,))

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
                td.line([(x1,y1),(x2,y2)],fill=BRASA+(200,),width=3)
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
            dh.ellipse([hx-10,hy-10,hx+10,hy+10],fill=CHISPA+(255,))
            hl=hl.filter(ImageFilter.GaussianBlur(6))
            layer.alpha_composite(hl,(0,0))
            d.ellipse([hx-5,hy-5,hx+5,hy+5],fill=CHISPA+(255,))
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
                d.ellipse([x-sz,y-sz,x+sz,y+sz],fill=BRASA_SUAVE+(int(170*oa),))

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
            for gx,gy in rejilla(W,H):
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
                d.ellipse([x-sz,y-sz,x+sz,y+sz],fill=BRASA_SUAVE+(int(150*sa),))
        # wordmark: barrido izquierda→derecha (y=820, sin solaparse con el tagline)
        if t>=11.8 and NOMBRE:
            fnt=ImageFont.truetype(JAKARTA,56)
            wm=Image.new("RGBA",(W,120),(0,0,0,0)); dw=ImageDraw.Draw(wm)
            text_center(dw,(W/2,60),NOMBRE,fnt,BLANCO_H+(255,),tracking=26)
            sw=bezier_out(prog(t,11.8,12.6))
            if sw<1:
                m=Image.new("L",(W,120),0)
                ImageDraw.Draw(m).rectangle([0,0,int(W*sw),120],fill=255)
                wm.putalpha(Image.composite(wm.split()[3],Image.new("L",(W,120),0),m))
            layer.alpha_composite(wm,(0,int(KH[1]+ISO_S*0.48)))   # bajo el logo
        # tagline en UNA línea (cabe a 34px; dos líneas no caben con el zoom)
        if t>=12.9 and LEMA:
            ka=prog(t,12.9,13.4)
            fnt2=ImageFont.truetype(JAKARTA,34)
            tg=Image.new("RGBA",(W,80),(0,0,0,0)); dt=ImageDraw.Draw(tg)
            # una sola línea (con el zoom final dos líneas no caben)
            dibujar_lema(tg,W/2,10,lineas_lema(dt,LEMA,fnt2,W*0.86)[:1],fnt2,BLANCO_H,ROJO,0)
            if ka<1:
                al=tg.split()[3].point(lambda v:int(v*ka)); tg.putalpha(al)
            # 16:9: +110 es el máximo que deja el zoom final (y<1049); 9:16 tiene aire
            layer.alpha_composite(tg,(0,int(KH[1]+ISO_S*0.48+(110 if W>=H else 150))))

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

def configurar(a):
    """Instala la identidad pedida (pack o flags) en los globales del film."""
    global NEGRO, ROJO, BLANCO_H, BRASA, BRASA_SUAVE, CALIDO, CHISPA, LOGO, JAKARTA, NOMBRE, LEMA
    global KH_SRC, ISO_POS, W, H, KH
    W,H=lienzo(a.formato)
    KH=(W/2,H/2) if W>=H else (W/2,H*0.40)
    idt=preparar(a)
    p=idt["paleta"]; NEGRO,ROJO,BLANCO_H=p["negro"],p["acento"],p["blanco"]
    BRASA,BRASA_SUAVE,CALIDO,CHISPA=vivo(ROJO,0.10),vivo(ROJO,0.16),vivo(ROJO,0.30),vivo(ROJO,0.75)
    LOGO,JAKARTA,NOMBRE,LEMA,KH_SRC=idt["logo"],idt["fuente"],idt["nombre"],idt["lema"],idt["ancla"]
    ISO_POS=(int(KH[0]-KH_SRC[0]*SC),int(KH[1]-KH_SRC[1]*SC))

def main():
    ap=argparse.ArgumentParser(description="Film de marca v1, 16:9 o 9:16 (referencia; preferir film_marca_v2.py).")
    ap.add_argument("-o","--out",required=True)
    args_identidad(ap); args_formato(ap)
    a=ap.parse_args()
    configurar(a)
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
