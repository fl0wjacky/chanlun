# R6 测量：确立那一刻，H 之后有没有已经长出来的本级别中枢（M28『最近那个中枢』跟 D2-2 参照中枢会不会分开）
import sys,os,json
ROOT=os.getcwd();sys.path.insert(0,ROOT);sys.path.insert(0,os.path.join(ROOT,'tools'))
import core.trend as T
from core.analyze import analyze
from config import tick_of
rec=[]
orig=T._try_confirm
def wrap(done,t,ks,typ,lo,no_exceed=True):
    r=orig(done,t,ks,typ,lo,no_exceed)
    if r is not None:
        j,z=r
        zs=T._centers_with_cuts(done[:t+1],ks)
        later=[q for q in zs if q["PI0"]>=lo and q["X0"]>done[j]["i1"]]
        alt=None
        if later:
            n=later[-1];leave,back=done[t-1],done[t]
            alt=(leave["p1"]<n["ZD"] and back["p1"]<n["ZD"]) if typ=="H" else (leave["p1"]>n["ZG"] and back["p1"]>n["ZG"])
        rec.append((done[j]["i1"],typ,len(later),alt,[(q["PI0"],q["PI1"],q["live"]) for q in later]))
    return r
T._try_confirm=wrap
def load(p):
    raw=json.load(open(p));raw=raw["bars"] if isinstance(raw,dict) else raw
    return [dict(t=b["t"],o=b["o"],h=b["h"],l=b["l"],c=b["c"]) for b in raw]
files=[('data',f) for f in sorted(os.listdir('data'))]+[('tools/fixtures',f) for f in sorted(os.listdir('tools/fixtures'))]
tot=hit=0
for d,f in files:
    try: bars=load(os.path.join(d,f))
    except Exception: continue
    if not bars or not isinstance(bars[0],dict) or 'h' not in bars[0]: continue
    rec.clear()
    try:
        r=analyze(bars,tick=tick_of(f));out=T.find_bounds(r)
    except Exception as e:
        print(f,'ERR',e);continue
    final={(b["bar"],b["kind"]) for b in out["bounds"]}
    calls=[x for x in rec]
    n_conf=len(out["bounds"]);w=[x for x in calls if x[2]>0 and (x[0],x[1]) in final]
    tot+=n_conf;hit+=len(w)
    print(f"{d}/{f}: 分界 {n_conf}，确立时 H 之后已有中枢 {len(w)}",[(x[0],x[1],x[2],x[3]) for x in w][:6])
print('合计',tot,hit)
