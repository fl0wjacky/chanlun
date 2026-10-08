import sys, math, datetime as D; sys.path[:0]=['.','tools']
from PIL import Image, ImageDraw, ImageFont
import config
from core.analyze import analyze
from core import trend as T
from trend_check import load
bars=load("data/zec15.json"); tk=config.tick_of("zec15.json"); r=analyze(bars,tick=tk)
A=T.trend_v3(r,reading="A")
real=T.find_bounds
def drop(*a, **kw):                                   # 原型 B：451.54 那一刀（小转大）不切，其余照常
    res=real(*a, **kw)
    gone=[b for b in res["bounds"] if round(b["price"],2)==451.54]
    res["bounds"]=[b for b in res["bounds"] if b not in gone]
    res["ks"]=[k for k in res["ks"] if k not in {b["line_seg"]+1 for b in gone}]
    return res
T.find_bounds=drop; Bv=T.trend_v3(r,reading="A"); T.find_bounds=real
B=bars
ix=lambda s: next(i for i,b in enumerate(B) if D.datetime.fromtimestamp(b["t"]/1000,D.timezone.utc).strftime('%m-%d')>=s)
b0,b1=ix("07-01"),ix("09-01")-1
font=ImageFont.truetype(config._pick_font(),15); fsm=ImageFont.truetype(config._pick_font(),12)
W,PH,ML,MR,MT=1800,560,70,20,34
img=Image.new("RGB",(W,PH*2+40),"white"); d=ImageDraw.Draw(img)
seg=B[b0:b1+1]; lo=min(b["l"] for b in seg); hi=max(b["h"] for b in seg); pad=(hi-lo)*.06; lo-=pad; hi+=pad
ts=lambda i: D.datetime.fromtimestamp(B[i]["t"]/1000, D.timezone.utc).strftime('%m-%d %H:%M')
def label(x,y,txt,col,f=fsm):
    w=d.textlength(txt,font=f); d.rectangle([x-2,y-1,x+w+2,y+15],fill="white"); d.text((x,y),txt,fill=col,font=f)
def panel(k,v,tag):
    y0=k*(PH+20); X=lambda i: ML+(i-b0)*(W-ML-MR)/(b1-b0); Y=lambda p: y0+MT+(hi-p)*(PH-MT-50)/(hi-lo)
    p=math.ceil(lo/50)*50
    while p<=hi: d.line([(ML,Y(p)),(W-MR,Y(p))],fill=(225,225,225)); d.text((4,Y(p)-7),"%g"%p,fill=(90,90,90),font=fsm); p+=50
    d.text((ML,y0+6),"ZEC 15m（zec15.json 冻结夹具）· %s～%s UTC · 笔 6 根 · %s"%(ts(b0),ts(b1),tag),fill="black",font=font)
    for i in range(b0,b1+1):
        b=B[i]; col=(200,60,60) if b["c"]>=b["o"] else (40,150,90); d.line([(X(i),Y(b["h"])),(X(i),Y(b["l"]))],fill=col)
    for z in v["seg_centers"]:
        if z["X1"]<b0 or z["X0"]>b1: continue
        yt,yb=max(Y(z["ZG"]),y0+MT),min(Y(z["ZD"]),y0+PH-50)
        d.rectangle([X(max(z["X0"],b0)),yt,X(min(z["X1"],b1)),yb],outline=(40,110,200),width=2)
    for bd in v["bounds"]:
        if not b0<=bd["bar"]<=b1: continue
        x,y=X(bd["bar"]),Y(bd["price"])
        for yy in range(int(y0+MT),int(y0+PH-50),8): d.line([(x,yy),(x,yy+4)],fill=(120,40,160),width=2)
        d.ellipse([x-6,y-6,x+6,y+6],fill=(120,40,160))
        label(x+10, y-22 if bd["kind"]=="H" else y+8, "分界 %s %.2f @%s"%(bd["kind"],bd["price"],ts(bd["bar"])), (120,40,160))
    # 451.54 那一点：两张图都圈出来
    j=next(i for i in range(b0,b1+1) if abs(B[i]["l"]-451.54)<1e-6)
    x,y=X(j),Y(451.54); d.ellipse([x-16,y-16,x+16,y+16],outline=(230,120,0),width=3)
    label(x-60,y+22,"451.54（07-29 04:00）",(230,120,0))
    for s in v["segments"]:
        if s["i1"]<b0 or s["i0"]>b1: continue
        x0,x1=X(max(s["i0"],b0)),X(min(s["i1"],b1))
        d.line([(x0+2,y0+PH-44),(x1-2,y0+PH-44)],fill=(60,60,60),width=2)
        label((x0+x1)/2-30, y0+PH-38, "走势："+s["type"]+("·升" if s["upgraded"] else ""), (0,0,0), font)
panel(0,A,"A 现在的做法：451.54 照切（这一刀标「小转大」）")
panel(1,Bv,"B 照原文「非同级别分解里小转大不切」：451.54 不切（原型，只出图）")
d.text((ML,PH*2+20+4),"紫虚线＝走势分界；蓝框＝线段中枢；橙圈＝451.54 那个点（前一段本级别下跌，没有一买，也不是盘整背驰）",fill=(60,60,60),font=fsm)
img.save(sys.argv[1])
print("A 分界", [(b["kind"],b["price"],ts(b["bar"])) for b in A["bounds"] if b0<=b["bar"]<=b1])
print("B 分界", [(b["kind"],b["price"],ts(b["bar"])) for b in Bv["bounds"] if b0<=b["bar"]<=b1])
print("A 段型", [(s["type"]+("·升" if s["upgraded"] else ""),ts(s["i0"])) for s in A["segments"] if s["i1"]>=b0 and s["i0"]<=b1])
print("B 段型", [(s["type"]+("·升" if s["upgraded"] else ""),ts(s["i0"])) for s in Bv["segments"] if s["i1"]>=b0 and s["i0"]<=b1])
