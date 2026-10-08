# Z14 档② 影响面（只量不改）。用法：在仓根 git apply notes/z14/z14b-temp.patch，然后 Z14B={0,1} python3 notes/z14/z14_measure.py out.json；快照路径 ../snap/live15-1007.json.gz（agent/bram/snap-1007 6b233a2）。量完 git checkout core/center.py。
import sys,json,gzip
sys.path[:0]=['.','tools']
from core.analyze import analyze, analyze_file
from core.center import find_centers
from config import tick_of
import importlib; T=importlib.import_module('core.trend')
DATA=["aaplusdt_1h.json","aaplusdt_2h.json","aaplusdt_30m.json","aaplusdt_4h.json","btc_4h.json","zec15.json","zec30_cut.json","zec_1h.json","zec_2h.json","zec_4h.json"]
syms={"ZECUSDT":"zec","BTCUSDT":"btc","AAPLUSDT":"aaplusdt"}
charts=[(f,analyze_file(f)) for f in DATA]
snap=json.loads(gzip.open('../snap/live15-1007.json.gz').read())
charts+=[(k,analyze(snap[k]["bars"],tick=tick_of(syms[k.split()[0]]+"_.json"))) for k in sorted(snap)]
out={}
for name,r in charts:
    sc=r['seg_centers']; v=T.trend_v3(r,reading='A')
    out[name]=dict(sc=[(z['PI0'],z['PI1'],z['ZD'],z['ZG'],z['term']) for z in sc],
      ge9=[(z['PI0'],z['PI1'],z['npens']) for z in sc if z['npens']>=9],
      tc=[(z['PI0'],z['PI1'],round(z['ZD'],4),round(z['ZG'],4)) for z in v['seg_centers']],
      tge9=[(z['PI0'],z['PI1'],z['npens']) for z in v['seg_centers'] if z['npens']>=9],
      units=len(v['units']),
      bounds=[(b['bar'],b['kind'],round(b['price'],4)) for b in v['bounds']],
      types=[s['type']+('·升' if s['upgraded'] else '') for s in v['segments']])
json.dump(out,open(sys.argv[1],'w'),ensure_ascii=False)
# L61
pts=[4267,4226,4254,4213,4279,4210,4270,4245,4282,4245,4305,4277,4312,4245,4270]
pens=[dict(i0=k,i1=k+1,p0=a,p1=b,hi=max(a,b),lo=min(a,b)) for k,(a,b) in enumerate(zip(pts,pts[1:]))]
print('L61',[(60+z['PI0'],60+z['PI1']+1,z['ZD'],z['ZG'],z['term'],z['npens']) for z in find_centers(pens)])
