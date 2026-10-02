# -*- coding: utf-8 -*-
"""引擎对说明书（中枢/走势类型/级别）· 差异演示（只读，不改 core/）

跑法（仓库根目录）：

    python3 docs/audit/engine-vs-spec_中枢走势组_demo.py

五段演示，对应正文 §1 的 ⑤／⑧／⑨／⑤ / ㉗ 五行：

    ① repaint       —— 走势没走完时，同一个中枢的哪些字段被后来改写（含「已终结又复活」）
    ② 否决条件       —— L56:92-94「第三段向下倾斜不算中枢」按最松读法在本数据命中几个
    ③ 终结方式       —— 12 个已终结类中枢里，有几个是靠第三类买卖点终结的
    ④ 笔严格交替     —— center._range 用「起笔奇偶」挑 Z 段的前提是否成立
    ⑤ DD_all/GG_all —— 旧口径字段与 DD/GG 是否恒等

只用 data/btc_4h.json，程序侧 pin 在 core/*.py @ 4d7082e。
"""
import collections
import json
import random
import sys

sys.path.insert(0, '.')
from config import tick_of                      # noqa: E402
from core.analyze import analyze                # noqa: E402

FN = 'btc_4h.json'
BARS = json.load(open('data/' + FN, encoding='utf-8'))
TICK = tick_of(FN)


def snap(n):
    return analyze(BARS[:n], tick=TICK, pen='old')


def head(title):
    print('\n' + '=' * 78)
    print(title)
    print('=' * 78)


# ---------------------------------------------------------------- ① repaint
head('① 走势没走完时，同一个中枢被后来改写（笔为单位往后推进）')

FULL = snap(len(BARS))
PEN_END = [p['i1'] for p in FULL['pens']]
FIELDS = ('X0', 'X1', 'F1', 'ZG', 'ZD', 'DD', 'GG', 'nZ', 'npens', 'PI0', 'PI1', 'live', 'term')


def repaint_scan():
    """按 PI0 对齐相邻两次推进，列出字段变化；单独统计三条要命的。"""
    prev = None
    combo = collections.Counter()
    shots = []
    for nb in PEN_END:
        if nb < 20:
            continue
        cur = {z['PI0']: z for z in snap(nb + 1)['centers']}
        if prev is not None:
            for pi0, b in cur.items():
                a = prev.get(pi0)
                if a is None:
                    continue
                d = [f for f in FIELDS if a[f] != b[f]]
                if not d:
                    continue
                combo[tuple(d)] += 1
                shots.append((nb + 1, pi0, a, b, d))
        prev = cur
    return combo, shots


combo, shots = repaint_scan()
print('字段变化组合（相邻两次推进都出现的同一个中枢）：')
for k, v in combo.most_common():
    print('   %3d 次   %s' % (v, '+'.join(k)))

print('\n三条最要命的：')
for kind, filt in (
    ('a) 由 live 收口时终点**倒退**', lambda a, b, d: a['live'] and not b['live'] and a['PI1'] != b['PI1']),
    ('b) 已终结的**又变回 live**', lambda a, b, d: (not a['live']) and b['live']),
    ('c) 中枢区间 ZG/ZD 被改', lambda a, b, d: a['ZG'] != b['ZG'] or a['ZD'] != b['ZD']),
):
    hits = [(nb, pi0, a, b, d) for nb, pi0, a, b, d in shots if filt(a, b, d)]
    print('\n  %s —— %d 次' % (kind, len(hits)))
    for nb, pi0, a, b, d in hits[:3]:
        print('     bar=%d PI0=%d 变 %s' % (nb, pi0, '+'.join(d)))
        print('        前: PI1=%s nZ=%s ZG=%.1f ZD=%.1f GG=%.1f DD=%.1f live=%s term=%s'
              % (a['PI1'], a['nZ'], a['ZG'], a['ZD'], a['GG'], a['DD'], a['live'], a['term']))
        print('        后: PI1=%s nZ=%s ZG=%.1f ZD=%.1f GG=%.1f DD=%.1f live=%s term=%s'
              % (b['PI1'], b['nZ'], b['ZG'], b['ZD'], b['GG'], b['DD'], b['live'], b['term']))

print('\n「已终结又复活」那一处的笔（说明不是笔被重切，是回抽那一段还在长）：')
for nm, rr in (('bar 1780', snap(1780)), ('bar 1796', snap(1796))):
    print('  %s：' % nm)
    for k in range(92, len(rr['pens'])):
        p = rr['pens'][k]
        print('     笔%2d i0=%d i1=%4d p0=%.1f p1=%.1f lo=%.1f hi=%.1f'
              % (k, p['i0'], p['i1'], p['p0'], p['p1'], p['lo'], p['hi']))


# ------------------------------------------------------------ ② 否决条件
head('② L56:92-94「第三段向下倾斜的不算中枢」· 最松读法量一遍')

CENTERS = FULL['centers']
P = FULL['pens']
hit = []
for k, z in enumerate(CENTERS):
    i = z['PI0']
    a, c = P[i], P[i + 2]
    down_a = a['p1'] < a['p0']
    beyond = (c['lo'] < a['lo']) if down_a else (c['hi'] > a['hi'])
    if beyond:
        hit.append((k, i, down_a, a, c))
print('读法（本轮我的读法，未定）：第一段若向下，第三段终点再破第一段终点 ⇒ 视为「第三段向下倾斜」。')
print('命中 %d / %d 个类中枢：' % (len(hit), len(CENTERS)))
for k, i, dn, a, c in hit:
    print('   中枢#%2d PI0=%2d 第一段%s [%.1f→%.1f]  第三段 [%.1f→%.1f] ⇒ 破 %.1f'
          % (k, i, '向下' if dn else '向上', a['p0'], a['p1'], c['p0'], c['p1'], a['p1']))
print('⇒ 一读就 %d/%d，说明这个读法太松，不能就这么落。' % (len(hit), len(CENTERS)))

# ------------------------------------------------------------ ③ 终结方式
head('③ 已终结的中枢，有几个是靠第三类买卖点终结的')
term = collections.Counter(z['term'] for z in CENTERS)
print('类中枢终结方式：', dict(term))
by3 = term.get('三买', 0) + term.get('三卖', 0)
byleave = term.get('Z 段向上离开', 0) + term.get('Z 段向下离开', 0)
gone = by3 + byleave
print('已终结 %d 个：三买/三卖 %d 个（%.0f%%），纯靠「Z 段离开」%d 个（%.0f%%）'
      % (gone, by3, 100.0 * by3 / gone, byleave, 100.0 * byleave / gone))
print('线段中枢终结方式：', dict(collections.Counter(z['term'] for z in FULL['seg_centers'])))

# ------------------------------------------------------------ ④ 笔交替
head('④ center._range 用「起笔奇偶」挑 Z 段 —— 前提「笔严格交替」在本数据成立吗')
bad = [k for k in range(1, len(P))
       if (P[k]['p1'] > P[k]['p0']) == (P[k - 1]['p1'] > P[k - 1]['p0'])]
print('笔数 %d，方向不交替处：%s' % (len(P), bad or '无（严格交替）'))
print('首尾是否相接（p1[k] == p0[k+1]）：',
      all(abs(P[k]['p1'] - P[k + 1]['p0']) < 1e-9 for k in range(len(P) - 1)))

# ------------------------------------------------------- ⑤ DD_all 恒等
head('⑤ 旧口径字段 DD_all/GG_all 与 DD/GG 是否恒等')
d = [k for k, z in enumerate(CENTERS) if z['DD_all'] != z['DD'] or z['GG_all'] != z['GG']]
print('本数据 %d 个类中枢，分叉 %d 个' % (len(CENTERS), len(d)))
random.seed(7)
found = 0
for _ in range(60000):
    n = random.randint(16, 30)
    p = 100.0
    bs = []
    for _t in range(n):
        p = max(1.0, p * (1 + random.uniform(-0.06, 0.06)))
        bs.append(dict(o=p, h=p * (1 + random.uniform(0, 0.02)),
                       l=p * (1 - random.uniform(0, 0.02)), c=p))
    try:
        rr = analyze(bs, tick=0.01, pen='old')
    except Exception:
        continue
    if any(z['DD_all'] != z['DD'] or z['GG_all'] != z['GG'] for z in rr['centers']):
        found += 1
        break
print('6 万条随机小序列（16~30 根）搜分叉：%s' % ('搜到' if found else '一次都没搜到'))
