# 图头修法：现行（_start_check 判 ① 型，cutoff）vs S9（只看第一笔 X 两头谁先被破）——6 根下 data 10 份＋线上 15 张，比线段划分
import sys,os,json,gzip;sys.path[:0]=['.','tools']
from core import segment as S
from core.analyze import analyze
from config import tick_of
orig=S._start_check
NARROW='--narrow' in sys.argv
def s9(s,pens,mode=None,memo=None,cutoff=None):
    if cutoff is None: return orig(s,pens,mode,memo,cutoff) if mode else orig(s,pens)
    up=s['dir']=='up';ext=s['lo'] if up else s['hi']
    if s['p0']==ext: return 'ok'
    x=pens[s['PI0']]
    if NARROW:
        # 只在『待定』处境用 S9：X 之后第二、三笔都落在 X 的范围内（L71:23-24「第三笔完全在第一笔的范围内」）；否则照现行判
        lo_,hi_=min(x['p0'],x['p1']),max(x['p0'],x['p1'])
        nxt=pens[s['PI0']+1:s['PI0']+3]
        if len(nxt)<2 or not all(q['lo']>=lo_ and q['hi']<=hi_ for q in nxt):
            return orig(s,pens,mode,memo,cutoff)
    for j in range(s['PI0']+1,min(cutoff,len(pens)-1)+1):
        p=pens[j]
        # 一笔是单调的：向上笔先到低点再到高点，向下笔先到高点再到低点 ⇒ 同一笔两头都破时按时间先后判
        pup=p['p1']>p['p0']
        ev=[('lo',p['lo']),('hi',p['hi'])] if pup else [('hi',p['hi']),('lo',p['lo'])]
        for side,v in ev:
            if up:
                if side=='hi' and v>x['p1']: return 'ok'      # 先破终点 ⇒ 新段成立
                if side=='lo' and v<x['p0']: return 'bad'     # 先破起点 ⇒ V 不是起点（挪）
            else:
                if side=='lo' and v<x['p1']: return 'ok'
                if side=='hi' and v>x['p0']: return 'bad'
    return 'unmeasured'
def segs_of(bars,tick,fn):
    S._start_check=fn
    try: r=analyze(bars,tick=tick)
    finally: S._start_check=orig
    return [(s['PI0'],s['PI1'],s['i0'],s['i1'],s['dir']) for s in r['segs']], r
items=[]
for f in sorted(os.listdir('data')):
    try:
        raw=json.load(open('data/'+f));raw=raw['bars'] if isinstance(raw,dict) else raw
        if isinstance(raw,list) and raw and isinstance(raw[0],dict) and 'h' in raw[0]: items.append(('data/'+f,[dict(t=b['t'],o=b['o'],h=b['h'],l=b['l'],c=b['c']) for b in raw],tick_of(f)))
    except Exception: pass
snap=json.loads(gzip.open('../snap/live15-1007.json.gz').read());syms={"ZECUSDT":"zec","BTCUSDT":"btc","AAPLUSDT":"aaplusdt"}
for key in sorted(snap):
    s,tf=key.split();items.append(('live '+key,snap[key]['bars'],tick_of(syms[s]+"_.json")))
diff=0
for name,bars,tick in items:
    a,ra=segs_of(bars,tick,orig);b,rb=segs_of(bars,tick,s9)
    if a!=b:
        diff+=1
        P=ra['pens']
        print(name,'| 现行图头',a[0][:2],ra['segs'][0]['p0'],'→',ra['segs'][0]['p1'],'| S9 图头',b[0][:2],rb['segs'][0]['p0'],'→',rb['segs'][0]['p1'],'| 段数',len(a),'→',len(b),'| 第一处不同在第',next(k for k,(x,y) in enumerate(zip(a,b)) if x!=y) if any(x!=y for x,y in zip(a,b)) else min(len(a),len(b)),'段')
print('合计',len(items),'份，线段划分不同的',diff,'份')
