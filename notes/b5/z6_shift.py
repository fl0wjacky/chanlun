# Z6 换起点（从扩展链第 2、3 段起划 3+3+3）对合成框、段型、分界的影响。用法：python3 notes/b5/z6_shift.py <线上快照.gz>
import sys, json, gzip, importlib, collections
sys.path[:0]=['.','tools']
from core.analyze import analyze, analyze_file
from config import tick_of
T=importlib.import_module('core.trend')
DATA=["aaplusdt_1h.json","aaplusdt_2h.json","aaplusdt_30m.json","aaplusdt_4h.json","btc_4h.json","zec15.json","zec30_cut.json","zec_1h.json","zec_2h.json","zec_4h.json"]
syms={"ZECUSDT":"zec","BTCUSDT":"btc","AAPLUSDT":"aaplusdt"}
snap=json.loads(gzip.open(sys.argv[1]).read())
ch=[(f,analyze_file(f)) for f in DATA]+[(k,analyze(snap[k]["bars"],tick=tick_of(syms[k.split()[0]]+"_.json"))) for k in sorted(snap)]
real=T._regroup
c=collections.Counter(); where={}
for name,r in ch:
    base=T.trend_v3(r)
    nu=len(base['units']); c['最终合成框']+=nu
    for s in (1,2):
        T._regroup=lambda done,a,b,s=s: real(done,a+s,b)
        try: v=T.trend_v3(r)
        finally: T._regroup=real
        c['从第%d段起：合成框'%(s+1)]+=len(v['units'])
        tb=[(x['bar'],x['kind']) for x in base['bounds']]; tv=[(x['bar'],x['kind']) for x in v['bounds']]
        ta=[(x['type'],x['upgraded']) for x in base['segments']]; tt=[(x['type'],x['upgraded']) for x in v['segments']]
        if tb!=tv: c['从第%d段起：分界变的图'%(s+1)]+=1
        dt=sum(1 for x,y in zip(ta,tt) if x!=y)+abs(len(ta)-len(tt))
        c['从第%d段起：段型变'%(s+1)]+=dt
        if dt or tb!=tv: where.setdefault(name,[]).append((s+1,dt,tb!=tv,len(base['units']),len(v['units'])))
print(dict(c)); [print('  ',k,v) for k,v in where.items()]
