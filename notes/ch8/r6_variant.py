# R6 变体：参照中枢改成『本段最近那个中枢』（M28 读法），跟默认 D2-2（起点不晚于 H 的最后一个）比分界
import sys,os,json
ROOT=os.getcwd();sys.path.insert(0,ROOT);sys.path.insert(0,os.path.join(ROOT,'tools'))
import core.trend as T
from core.analyze import analyze
from config import tick_of
orig=T._try_confirm
def nearest(done,t,ks,typ,lo,no_exceed=True):
    cand=range(lo,t-1)
    if not cand: return None
    j=max(cand,key=(lambda k:(done[k]["p1"],k)) if typ=="H" else (lambda k:(-done[k]["p1"],k)))
    if T._is_up(done[j])!=(typ=="H"): return None
    after=done[j+1:t+1]
    if no_exceed and after and (max(a["hi"] for a in after)>done[j]["p1"] if typ=="H" else min(a["lo"] for a in after)<done[j]["p1"]): return None
    zs=T._centers_with_cuts(done[:t+1],ks)
    ref=[z for z in zs if z["PI0"]>=lo and (z["X0"]<=done[j]["i1"] or z["PI1"]<=t-2)]   # 默认那组，加上 H 之后、离开段之前已经走完的中枢；取最近一个
    if not ref: return None
    z=ref[-1];leave,back=done[t-1],done[t]
    ok=(leave["p1"]<z["ZD"] and back["p1"]<z["ZD"] and T._is_up(back)) if typ=="H" else (leave["p1"]>z["ZG"] and back["p1"]>z["ZG"] and not T._is_up(back))
    return (j,z) if ok else None
def load(p):
    raw=json.load(open(p));raw=raw["bars"] if isinstance(raw,dict) else raw
    return [dict(t=b["t"],o=b["o"],h=b["h"],l=b["l"],c=b["c"]) for b in raw]
files=[('data',f) for f in sorted(os.listdir('data'))]+[('tools/fixtures',f) for f in sorted(os.listdir('tools/fixtures'))]
diff=0;tot=0
for d,f in files:
    try:
        bars=load(os.path.join(d,f))
        if not bars or 'h' not in bars[0]: continue
    except Exception: continue
    r=analyze(bars,tick=tick_of(f))
    T._try_confirm=orig;a=T.find_bounds(r)
    T._try_confirm=nearest;b=T.find_bounds(r)
    T._try_confirm=orig
    A=[(x["bar"],x["kind"],x["pullback_end_bar"]) for x in a["bounds"]];B=[(x["bar"],x["kind"],x["pullback_end_bar"]) for x in b["bounds"]]
    tot+=len(A)
    if A!=B:
        diff+=1;print(f"{d}/{f}: 默认 {A}\n   变体 {B}")
print('文件不同',diff,'默认分界合计',tot)

# 细看：变体多出来／提前的那几把，用的参照中枢是哪个、走完没有
log=[]
def nearest_log(done,t,ks,typ,lo,no_exceed=True):
    r=nearest(done,t,ks,typ,lo,no_exceed)
    if r:
        j,z=r;d=orig(done,t,ks,typ,lo,no_exceed)
        log.append(dict(H=done[j]["i1"],typ=typ,t=t,j=j,leave=t-1,PI0=z["PI0"],PI1=z["PI1"],live=z["live"],X0=z["X0"],Hbar=done[j]["i1"],price=done[j]["p1"],ZD=z["ZD"],ZG=z["ZG"],default_ok=d is not None))
    return r
for d,f in [('data','zec15.json'),('tools/fixtures','zec1m_d2std.json')]:
    r=analyze(load(os.path.join(d,f)),tick=tick_of(f));log.clear()
    T._try_confirm=nearest_log;b=T.find_bounds(r);T._try_confirm=orig
    keep={(x["bar"],x["kind"],x["pullback_end_bar"]) for x in b["bounds"]}
    done=b["done"]
    for x in log:
        if (x["H"],x["typ"],done[x["t"]]["i1"]) in keep and not x["default_ok"]:
            print(f,x)
