# D2-7 前后图的取数：用 Atlas 的 notes/j18w/d27opts.py（agent/atlas/d27opts）跑 O0（现行）和 O1，各打一份 json，格式跟 l43_dump.py 一样，
# 另外多带 retracted（确认过、后来被撤的刀）。在引擎仓根目录跑：python d27_dump.py <数据文件名> <输出前缀>
import sys, os, json, datetime as DT
sys.path[:0] = ['.', 'tools', 'notes/j18w']
fn, outp = sys.argv[1], sys.argv[2]
os.environ['J18_FILES'] = fn; os.environ['OPTS'] = 'O1'
import d27opts as X                                   # import 时它会把这份数据 O0 对 O1 的增减表打一遍，正好拿来对 Atlas 的数
import core.trend as TR
from core.analyze import analyze
from config import tick_of
bars = json.load(open(os.path.join('data', fn)))
bars = [dict(t=b['t'], o=b['o'], h=b['h'], l=b['l'], c=b['c']) for b in bars]
u = lambda i: DT.datetime.fromtimestamp(bars[i]['t'] / 1000, DT.timezone.utc).strftime('%Y-%m-%d %H:%M')
r = analyze(bars, tick=tick_of(fn))
std = [dict(i0=s['i0'], i1=s['i1'], p0=s['p0'], p1=s['p1']) for s in TR._done(r)]
for opt in ('O0', 'O1'):
    v = X.run(bars, fn, opt)
    segs = [dict(i0=s['i0'], i1=s['i1'], type=s['type'], n=s['n_centers_level']) for s in v['segments']]
    bounds = [dict(bar=b['bar'], rule=b.get('rule', 'D2'), kind=b['kind'], price=b['price'], state=b.get('state')) for b in v['bounds']]
    cz = [dict(i0=z['X0'], i1=z['X1'], ZD=z['ZD'], ZG=z['ZG'], seg=z['seg']) for z in v['seg_centers']]
    ret = [dict(bar=x['bar'], kind=x['kind'], price=x['price'], rbar=x.get('retracted_bar')) for x in v['retracted']]
    bad = [j for j in range(1, len(segs)) if segs[j]['type'] in ('上涨', '下跌') and segs[j]['type'] == segs[j - 1]['type']]
    json.dump(dict(file=fn, segs=segs, bounds=bounds, centers=cz, std=std, bad=bad, retracted=ret), open(f'{outp}_{opt}.json', 'w'), ensure_ascii=False)
    print('==', opt, '刀', len(bounds), '撤回', len(ret))
    for j, s in enumerate(segs):
        if not (u(s['i0']) >= '2025-08-01' and u(s['i0']) <= '2025-11-15'): continue
        b = next((x for x in bounds if x['bar'] == s['i0']), None)
        print(j, u(s['i0']), '→', u(s['i1']), s['type'], s['n'], (f"[{b['rule']} {b['kind']} {b['price']:g} {b['state']}]" if b else ''), '<<< L43' if j in bad else '')
    for x in ret:
        if '2025-08-01' <= u(x['bar']) <= '2025-11-15': print('  撤回', u(x['bar']), x['kind'], x['price'], '撤于', x['rbar'] is not None and u(x['rbar']))
