"""P2′ 全图核：正文违规（须 0）、非极值端点、笔数、例外触发次数和改到多深。"""
import sys,os,json,gzip;sys.path[:0]=['.','tools',os.path.dirname(__file__)]
import core.pen as PEN
from core.kline import standardize, fractals, quantize
from config import tick_of
from dreplay import items
syms={"ZECUSDT":"zec","BTCUSDT":"btc","AAPLUSDT":"aaplusdt"};snap=json.loads(gzip.open(os.environ["LIVE15"]).read())
bad={};badat=[];ne=0;np=[0,0];ev={};fs={}
for name,fn in items():
    if fn: b=json.load(open("data/%s.json"%fn));tk=fn+".json"
    else: b=snap[name]["bars"];tk=syms[name.split()[0]]+"_.json"
    std=standardize(quantize(b,tick_of(tk)));fx=fractals(std)
    PEN.PEN_FINAL_LOCK=True;L=[];PEN.PEN_LOCK_EXCEPTION_LOG=L
    pens,seq=PEN.build_pens(fx,std,"old",PEN.MIN_GAP_DEFAULT)
    PEN.PEN_FINAL_LOCK=False;PEN.PEN_LOCK_EXCEPTION_LOG=None
    for k,n in PEN.check_pens(pens,seq,std): bad[k]=bad.get(k,0)+1; badat.append((name,n))
    ne+=len(PEN.nonextreme_pens(pens,std));np[0]+=len(pens);np[1]+=len(PEN.build_pens(fx,std,"old",PEN.MIN_GAP_DEFAULT)[0])
    for e in L:
        if e[0]=="fix_start": d=e[1]-e[2]; fs[d]=fs.get(d,0)+1
        else: ev[name]=ev.get(name,0)+1
print("正文违规",bad,badat,"| 非极值",ne,"| 笔数",np[0],"(锁关",np[1],")")
print("延伸破 L77 触发",sum(ev.values()),ev,"| 锁下 fix_start 实际改动深度（从倒数第几个端点起，0=没改）",dict(sorted(fs.items())))
