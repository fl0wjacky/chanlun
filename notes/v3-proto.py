"""docs/spec/走势分段.md §三／§四 的原型（只读，不改引擎）。用法：python3 notes/v3-proto.py zec15.json [P1|P2|P3]
v3 D2 原型（只读）：本级别＝线段中枢，次级别＝线段。
死点＝当前走势里的最高点 H（或最低点 L）；确立＝H 之后、价格没再过 H 的前提下，
以「H 之前（含跨 H）最后一个中枢」为准出第一个三卖（离开段收在 ZD 下、回抽段高点 < ZD）。
确立后在 H 切，从 H 重新算中枢，方向交替。逐段推进，只用已完成线段 done[:t+1]。"""
import sys,json;sys.path.insert(0,'.')
from core.analyze import analyze;import importlib
C=importlib.import_module("core.cut")
fn=sys.argv[1]; PROBE=sys.argv[2] if len(sys.argv)>2 else ''   # '' / P1 不重算 / P2 不交替 / P3 不查过H
raw=json.load(open('data/'+fn));raw=raw['bars'] if isinstance(raw,dict) else raw
B=[dict(t=b['t'],o=b['o'],h=b['h'],l=b['l'],c=b['c']) for b in raw]
r=analyze(B,tick=0.01); done=[s for s in r['segs'] if not s.get('live')]
import datetime as D, warnings; warnings.filterwarnings('ignore')
ts=lambda i: D.datetime.utcfromtimestamp(B[i]['t']/1000).strftime('%m-%d %H:%M')
ks=[]; bnd=[]          # ks: 切点段序号（新组起点）；bnd: (段序号 j 的终点, 'H'/'L', 确立段 t)
start=0; want=None     # want: 下一个分界要的是 'H' 还是 'L'（None＝两头都开）
for t in range(start+2,len(done)):
  zs=C._centers_with_cuts(done[:t+1],[] if PROBE=='P1' else ks)
  lo=ks[-1] if ks else 0
  piece=range(lo,t+1)
  for typ in ('H','L'):
    if want and typ!=want: continue
    # 本段走势里的极值（只看到 t-2 为止：后面要留离开段和回抽段）
    cand=list(range(lo,t-1))
    if not cand: continue
    j=max(cand,key=lambda k:(done[k]['p1'] if typ=='H' else -done[k]['p1'],k))
    if (done[j]['p1']>done[j]['p0'])!=(typ=='H'): continue      # 极值得是同向段的终点
    # 价格之后没再越过它
    after=[done[k] for k in range(j+1,t+1)]
    if PROBE!='P3' and typ=='H' and max(a['hi'] for a in after)>done[j]['p1']: continue
    if PROBE!='P3' and typ=='L' and min(a['lo'] for a in after)<done[j]['p1']: continue
    # 参照中枢：本组里 X0 不晚于 H 那一根的最后一个中枢
    ref=[z for z in zs if z['PI0']>=lo and z['X0']<=done[j]['i1']]
    if not ref: continue
    z=ref[-1]
    leave,back=done[t-1],done[t]
    if leave['i0']<done[j]['i1']: continue
    if typ=='H' and leave['p1']<z['ZD'] and back['p1']<z['ZD'] and back['p1']>back['p0']:
      pass
    elif typ=='L' and leave['p1']>z['ZG'] and back['p1']>z['ZG'] and back['p1']<back['p0']:
      pass
    else: continue
    ks.append(j+1); bnd.append((j,typ,t,z)); want=None if PROBE=='P2' else ('L' if typ=='H' else 'H'); break
print(fn,'segs',len(done),'分界',len(bnd))
for j,typ,t,z in bnd:
  s=done[j]; print('  %s %s bar %d %.2f  确立于段%d终点 %s（参照中枢 ZD %.2f ZG %.2f）'%(typ,ts(s['i1']),s['i1'],s['p1'],t,ts(done[t]['i1']),z['ZD'],z['ZG']))
