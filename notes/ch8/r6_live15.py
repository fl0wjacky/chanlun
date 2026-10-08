# R6 在线上 15 张冻结快照（agent/bram/snap-1007 6b233a2 的 notes/snap/live15-1007.json.gz）上量：
# 默认 D2-2 参照中枢 vs 『再加上 H 之后、离开段之前已走完的中枢，取最近一个』（M28/L58 读法）。用法：python3 notes/ch8/r6_live15.py <快照路径>
import sys,os,json,gzip
ROOT=os.getcwd();sys.path[:0]=[ROOT,ROOT+'/tools']
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
    ref=[z for z in zs if z["PI0"]>=lo and (z["X0"]<=done[j]["i1"] or z["PI1"]<=t-2)]
    if not ref: return None
    z=ref[-1];leave,back=done[t-1],done[t]
    ok=(leave["p1"]<z["ZD"] and back["p1"]<z["ZD"] and T._is_up(back)) if typ=="H" else (leave["p1"]>z["ZG"] and back["p1"]>z["ZG"] and not T._is_up(back))
    return (j,z) if ok else None
# 情形计数：默认确立的那一刻，H 之后已经有走完的本级别中枢
seen=[]
def probe(done,t,ks,typ,lo,no_exceed=True):
    r=orig(done,t,ks,typ,lo,no_exceed)
    if r:
        j,_=r;zs=T._centers_with_cuts(done[:t+1],ks)
        later=[z for z in zs if z["PI0"]>=lo and z["X0"]>done[j]["i1"] and z["PI1"]<=t-2]
        seen.append((done[j]["i1"],typ,len(later)))
    return r
snap=json.loads(gzip.open(sys.argv[1]).read())
syms={"ZECUSDT":"zec","BTCUSDT":"btc","AAPLUSDT":"aaplusdt"}
tot=nd=nc=nf=0
for key in sorted(snap):
    s,tf=key.split();r=analyze(snap[key]["bars"],tick=tick_of(syms[s]+"_.json"))
    seen.clear();T._try_confirm=probe;a=T.find_bounds(r)
    fin={(b["bar"],b["kind"]) for b in a["bounds"]};cases=[x for x in seen if (x[0],x[1]) in fin and x[2]>0]
    T._try_confirm=nearest;b=T.find_bounds(r);T._try_confirm=orig
    A=[(x["bar"],x["kind"],round(x["price"],2),x["pullback_end_bar"]) for x in a["bounds"]]
    B=[(x["bar"],x["kind"],round(x["price"],2),x["pullback_end_bar"]) for x in b["bounds"]]
    tot+=len(A);nc+=len(cases)
    if A!=B:
        nf+=1;print(f"{key}: 默认 {A}\n      变体 {B}")
    elif cases: print(f"{key}: 分界不变；确立时 H 之后已有走完的中枢 {len(cases)} 次")
print(f"合计：15 张，默认分界 {tot} 个；确立时 H 之后已有走完的本级别中枢 {nc} 次；分界变了的 {nf} 张")
