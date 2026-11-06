#!/usr/bin/python
"""Animated true-color terminal screensaver; no third-party dependencies."""
import json, math, random, select, shutil, signal, subprocess, sys, termios, time, tty

GOLD=(216,182,106)

def paint_navi(pixels, cx, cy, scale, t):
    """A blue-white orb, four fluttering wings, and a fading fairy trail."""
    height=len(pixels); width=len(pixels[0])
    unit=max(1.4,scale*.075)

    def position(at):
        angle=at*.24
        return (cx+math.cos(angle)*scale*.86,
                cy+math.sin(angle)*scale*.67+math.sin(at*1.7)*unit*.65)

    def light(x,y,radius,color,strength):
        for py in range(max(0,int(y-radius*3)),min(height,int(y+radius*3)+1)):
            for px in range(max(0,int(x-radius*3)),min(width,int(x+radius*3)+1)):
                alpha=strength*math.exp(-((px-x)**2+(py-y)**2)/(radius*radius))
                old=pixels[py][px]
                pixels[py][px]=tuple(min(255,int(a+(b-a)*alpha)) for a,b in zip(old,color))

    for i in range(18,0,-1):
        x,y=position(t-i*.09)
        light(x,y,unit*.38,(105,185,255),.32*(1-i/19))
    x,y=position(t)
    light(x,y,unit*2.4,(90,170,255),.46)
    flutter=.7+.3*math.sin(t*15)
    for side in (-1,1):
        for upper in (True,False):
            wx=x+side*unit*(1.25 if upper else .95)*flutter
            wy=y+unit*(-1.0 if upper else .85)
            rx=unit*(1.4 if upper else .95)*flutter
            ry=unit*(.58 if upper else .43)
            angle=side*(-.65 if upper else .5)
            ca,sa=math.cos(angle),math.sin(angle)
            for py in range(max(0,int(wy-unit*2)),min(height,int(wy+unit*2)+1)):
                for px in range(max(0,int(wx-unit*2)),min(width,int(wx+unit*2)+1)):
                    dx=px-wx; dy=py-wy
                    d=((dx*ca+dy*sa)/rx)**2+((-dx*sa+dy*ca)/ry)**2
                    if d<1:
                        alpha=.45+.4*(1-d)
                        old=pixels[py][px]
                        pixels[py][px]=tuple(int(a+(b-a)*alpha) for a,b in zip(old,(195,231,255)))
    light(x,y,unit*.9,(125,211,255),.95)
    light(x,y,unit*.45,(246,253,255),1.0)

def frame(w,h,t):
    # Render two square-ish pixels per terminal cell, using the upper half block.
    ph=h*2
    scale=min(w/2.8,ph/2.6)
    cx=w*.5+math.sin(t*.07)*w*.055
    cy=ph*.48+math.cos(t*.09)*ph*.04
    pulse=.84+.16*math.sin(t*.75)
    pixels=[]
    for y in range(ph):
        row=[]
        for x in range(w):
            dx=(x-cx)/scale; dy=(y-cy)/scale
            glow=math.exp(-(dx*dx+dy*dy)*2.4)
            rgb=(int(11+12*glow),int(16+24*glow),int(14+16*glow))
            for tx,ty in ((0,-.75),(-.433,0),(.433,0)):
                v=(dy-ty)/.75
                if 0<=v<=1 and abs(dx-tx)<=.433*v:
                    edge=min(v,1-v,.433*v-abs(dx-tx))
                    shine=(.65+.24*(1-v)+.11*math.sin(dx*2+t*.3))*pulse
                    if edge<.018: shine*=.6
                    rgb=tuple(int(c*shine) for c in GOLD)
                    break
            row.append(rgb)
        pixels.append(row)
    rng=random.Random(64)
    for _ in range(42):
        px=rng.random(); py=rng.random(); speed=rng.uniform(.012,.038); phase=rng.random()*math.tau
        x=int((px+.012*math.sin(t*.2+phase))*w)%w
        y=int(((py-t*speed)%1)*ph)
        light=.35+.6*(.5+.5*math.sin(t*.9+phase))
        pixels[y][x]=tuple(int(c*light) for c in GOLD)
    paint_navi(pixels,cx,cy,scale,t)
    out=['\033[H']
    for y in range(h):
        last=None
        for x in range(w):
            pair=(pixels[y*2][x],pixels[y*2+1][x])
            if pair!=last:
                a,b=pair
                out.append('\033[38;2;%d;%d;%dm\033[48;2;%d;%d;%dm'%(*a,*b))
                last=pair
            out.append('▀')
        out.append('\033[0m')
        if y<h-1: out.append('\r\n')
    return ''.join(out)

def main():
    fd=sys.stdin.fileno(); saved=termios.tcgetattr(fd)
    def stop(*_): raise SystemExit
    for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGHUP): signal.signal(sig,stop)
    try:
        tty.setcbreak(fd)
        sys.stdout.write('\033[?1049h\033[?25l\033[?1003h\033[?1006h\033[2J'); sys.stdout.flush()
        start=time.monotonic(); lastcheck=0
        while True:
            now=time.monotonic(); t=now-start
            w,h=shutil.get_terminal_size()
            sys.stdout.write(frame(w,max(1,h-1),t)); sys.stdout.flush()
            if select.select([fd],[],[],.05)[0]: break
            if now-lastcheck>1:
                lastcheck=now
                # Lock or focus changes must dismiss the animation as well.
                result=subprocess.run(['hyprctl','activewindow','-j'],capture_output=True,text=True)
                try:
                    if json.loads(result.stdout).get('class')!='org.omarchy.screensaver': break
                except (ValueError,AttributeError): break
    finally:
        sys.stdout.write('\033[?1003l\033[?1006l\033[0m\033[?25h\033[?1049l'); sys.stdout.flush()
        termios.tcsetattr(fd,termios.TCSADRAIN,saved)
        # Like Omarchy's saver, dismiss every monitor together.
        subprocess.run(['pkill','-f','[o]rg.omarchy.screensaver'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

if __name__=='__main__': main()
