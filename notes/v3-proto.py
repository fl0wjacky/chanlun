"""docs/spec/走势分段.md §三／§四 的原型（只读，不改引擎）。用法：python3 notes/v3-proto.py zec15.json [P1|P2|P3|P5|P6]
v3 D2 原型（只读）：本级别＝线段中枢，次级别＝线段。
死点＝当前走势里的最高点 H（或最低点 L）；确立＝H 之后、价格没再过 H 的前提下，
以「H 之前（含跨 H）最后一个中枢」为准出第一个三卖（离开段收在 ZD 下、回抽段高点 < ZD）。
确立后在 H 切，从 H 重新算中枢，方向交替。逐段推进，只用已完成线段 done[:t+1]。"""
import sys,json;sys.path.insert(0,'.')
from core.analyze import analyze;import importlib
C=importlib.import_module("core.cut")
fn=sys.argv[1]; PROBE=sys.argv[2] if len(sys.argv)>2 else ''   # '' / P1 不重算 / P2 不交替 / P3 不查过H / P5 不查前一段有无中枢 / P6 D3 改读法：升级中枢留在本级别数
raw=json.load(open('data/'+fn));raw=raw['bars'] if isinstance(raw,dict) else raw
B=[dict(t=b['t'],o=b['o'],h=b['h'],l=b['l'],c=b['c']) for b in raw]
r=analyze(B,tick=0.01); done=[s for s in r['segs'] if not s.get('live')]
import datetime as D, warnings; warnings.filterwarnings('ignore')
ts=lambda i: D.datetime.utcfromtimestamp(B[i]['t']/1000).strftime('%m-%d %H:%M')
ks=[]; bnd=[]; dropped=[]          # ks: 切点段序号（新组起点）；bnd: (段序号 j 的终点, 'H'/'L', 确立段 t)
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
    # D2-7：这一刀让前一段（上一刀 → 这一刀）一个中枢都没有 ⇒ 不算（L17:44 基本原理二）；图头那一段不查
    if ks and PROBE!='P5':
      zz=C._centers_with_cuts(done[:t+1],ks+[j+1])
      if not [q for q in zz if q['PI0']>=lo and q['PI1']<=j]:
        # 上一刀到这一刀之间没有中枢 ⇒ 两把都去（一高一低），回到上一刀之前那段走势接着走
        ks.pop(); prev=bnd.pop(); dropped.append((prev,(j,typ,t)))
        want=prev[1]; break
    ks.append(j+1); bnd.append((j,typ,t,z)); want=None if PROBE=='P2' else ('L' if typ=='H' else 'H'); break
print(fn,'segs',len(done),'分界',len(bnd),'撤回',len(dropped))
for (pj,pt,ptt,_),(j,typ,t) in dropped: print('  撤回 %s %.2f（确立于段%d）＋不立 %s %.2f（段%d）'%(pt,done[pj]['p1'],ptt,typ,done[j]['p1'],t))
for j,typ,t,z in bnd:
  s=done[j]; print('  %s %s bar %d %.2f  确立于段%d终点 %s（参照中枢 ZD %.2f ZG %.2f）'%(typ,ts(s['i1']),s['i1'],s['p1'],t,ts(done[t]['i1']),z['ZD'],z['ZG']))

# ---- D3：每段走势是什么（同一段走势里先把连续扩展的中枢合成一个高一级中枢，再数） ----
zs=C._centers_with_cuts(done,ks); edges=[0]+ks+[len(done)]
print('走势（D3）:')
for n,(a,b) in enumerate(zip(edges,edges[1:])):
  zz=[z for z in zs if a<=z['PI0'] and z['PI1']<b]
  units=[]
  for i,z in enumerate(zz):
    if i and '扩展' in z['rel']:
      u=units[-1]; units[-1]=dict(DD=min(u['DD'],z['DD']),GG=max(u['GG'],z['GG']),n=u['n']+1)
    else: units.append(dict(DD=z['DD'],GG=z['GG'],n=1))
  rel=['上' if v['DD']>u['GG'] else '下' if v['GG']<u['DD'] else '叠' for u,v in zip(units,units[1:])]
  up=[u for u in units if u['n']>1]
  if not units: kind='无中枢'
  elif up and PROBE!='P6':                    # D3-A：含升级中枢 ⇒ 整段升一级；高一级只数合成出来的中枢
    kind='升级·'+('盘整' if len(up)==1 else '趋势?(%d 个高一级中枢，要再判同向不重叠)'%len(up))
  elif len(units)==1: kind='盘整'
  elif len(set(rel))==1 and rel[0]!='叠': kind=('上涨' if rel[0]=='上' else '下跌')+('（含升级中枢）' if up else '')
  else: kind='？合并后仍重叠 '+''.join(rel)
  tag=' ←图头' if n==0 else (' ←还在长' if n==len(edges)-2 else '')
  print('  %s→%s 中枢%d→单元%d %s %s%s'%(ts(done[a]['i0']),ts(done[b-1]['i1']),len(zz),len(units),[u['n'] for u in units],kind,tag))
