# J18（L43）前后图的取数：在某个引擎仓里跑同级别分解，把走势段、分界、中枢、标准化线段打成 json。图上不读数，数全从这儿来。
#   python l43_dump.py --root <引擎仓> --file zec15.json --out x.json
import sys, os, json, argparse, datetime as DT
ap = argparse.ArgumentParser(); ap.add_argument('--root', required=True); ap.add_argument('--file', required=True); ap.add_argument('--out', required=True)
ap.add_argument('--set', action='append', default=[], help='core.trend 的开关，NAME=VAL（VAL 按 Python 字面量解析，比如 S5_FIX="Z"）')
a = ap.parse_args(); out = os.path.abspath(a.out)
sys.path[:0] = [a.root]; os.chdir(a.root)
import config
from core.analyze import analyze
import core.trend as TR
import ast
for kv in a.set:
    k, v = kv.split('=', 1); assert hasattr(TR, k), k; setattr(TR, k, ast.literal_eval(v)); print('set', k, '=', getattr(TR, k))
bars = json.load(open(config.data(a.file), encoding='utf-8')); tick = config.tick_of(a.file)
r = analyze(bars, tick=tick); t = TR.trend_v3(r)
FMT = '%Y-%m-%d %H:%M' if bars[-1]['t'] - bars[0]['t'] > 300 * 86400000 else '%m-%d %H:%M'   # 跨年的数据带年份（btc_1h 七年），否则同一个 08-05 分不清是哪一年
u = lambda i: DT.datetime.fromtimestamp(bars[i]['t'] / 1000, DT.timezone.utc).strftime(FMT)
segs = [dict(i0=s['i0'], i1=s['i1'], type=s['type'], n=s['n_centers_level']) for s in t['segments']]
bounds = [dict(bar=b['bar'], rule=b.get('rule', 'D2'), kind=b['kind'], price=b['price'], state=b.get('state')) for b in t['bounds']]
cz = [dict(i0=z['X0'], i1=z['X1'], ZD=z['ZD'], ZG=z['ZG'], seg=z['seg']) for z in t['seg_centers']]
std = [dict(i0=s['i0'], i1=s['i1'], p0=s['p0'], p1=s['p1']) for s in TR._done(r)]
# 两个代价也用引擎自己的 _sl_rel 判（ZDZG 口径），图上不自己比价：
#   l20＝同一段趋势里相邻两个中枢「叠」或方向不一致（L20:6）；pp＝相邻两段都是盘整、两个中枢不叠（Atlas 18:33 ⑤，L38 没讲）
zs = [[z for z in t['seg_centers'] if z['seg'] == j] for j in range(len(segs))]
l20 = [[j, k] for j, s in enumerate(segs) if s['type'] in ('上涨', '下跌') for k in range(1, len(zs[j]))
       if TR._sl_rel(zs[j][k - 1], zs[j][k]) != ('上' if s['type'] == '上涨' else '下')]
pp = [j for j in range(1, len(segs)) if segs[j]['type'] == segs[j - 1]['type'] == '盘整' and zs[j] and zs[j - 1]
      and TR._sl_rel(zs[j - 1][-1], zs[j][0]) != '叠']
# s4＝S4′（trend_check T3′ 同一判法）：S5 接缝、前段只有一个中枢、跨缝那一对按 [ZD,ZG] 不是「叠」
s5b = {b['bar'] for b in t['bounds'] if b.get('rule') == 'S5'}
s4 = [j for j in range(1, len(segs)) if segs[j]['i0'] in s5b and len(zs[j - 1]) == 1 and zs[j]
      and TR._sl_rel(zs[j - 1][-1], zs[j][0]) != '叠']
bad = [j for j in range(1, len(segs)) if segs[j]['type'] in ('上涨', '下跌') and segs[j]['type'] == segs[j - 1]['type']]
for j, s in enumerate(segs):
    b = next((x for x in bounds if x['bar'] == s['i0']), None)
    print(j, u(s['i0']), '→', u(s['i1']), s['type'], s['n'], (f"[{b['rule']} {b['kind']} {b['price']:g} {b['state']}]" if b else ''), '<<< L43' if j in bad else '')
print('L43 接缝', len(bad), '· L20 趋势内中枢叠', len(l20), '· 不叠的盘整＋盘整', len(pp), '· S4′', len(s4))
for j in s4: print('  S4′', j - 1, j, u(segs[j]['i0']), segs[j - 1]['type'], '→', segs[j]['type'], '中枢 X1', zs[j - 1][-1]['X1'])
for j, k in l20: print('  L20', j, u(zs[j][k - 1]['X0']), '→', u(zs[j][k]['X1']))
for j in pp: print('  盘整＋盘整不叠', j - 1, j, u(segs[j]['i0']))
json.dump(dict(file=a.file, segs=segs, bounds=bounds, centers=cz, std=std, bad=bad, l20=l20, pp=pp, s4=s4), open(out, 'w'), ensure_ascii=False)
