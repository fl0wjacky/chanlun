#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用影子系统的 15 分钟数据，把「笔中枢 vs 线段中枢 的稳定性」测出来。

上一轮在日线上测不出来（线段中枢平均只有 1.1 个，全是噪声）。
现在换 20,000 根 15 分钟 K 线：笔中枢 192 个、线段中枢 25 个，样本够了。

判据（第 83 课原话）：
    「用笔当成构成最小中枢的零件，但这样构造出来的系统，其稳定性极差。」
    「一笔的基础是顶和底分型，而一些瞬间的交易，就足以影响其结构。」
    「而由线段构成最小中枢，则不存在这个问题。……线段受偶尔性的影响比较少。」
    → 若线段中枢的标的内变异 ≮ 笔中枢，该论断被证伪。
"""
import os, sys, json, random, statistics, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import data
from core import analyze

D = json.load(open(data("m15_sub.json")))
SYMS = sorted(D)[:6]
REPS = 5
EPS = [0.0005, 0.002, 0.008]
random.seed(20260928)


def bars_of(sym, eps=0.0):
    out = []
    for i, r in enumerate(D[sym]):
        ts, o, h, l, c = r
        if eps:
            h = h * (1 + random.uniform(-eps, eps))
            l = l * (1 - random.uniform(-eps, eps))
            h = max(h, o, c); l = min(l, o, c)
        out.append(dict(t=i, o=o, h=h, l=l, c=c))
    return out


def counts(sym, eps):
    r = analyze(bars_of(sym, eps))
    return len(r["centers"]), len(r["seg_centers"])


print("=" * 76)
print("样本：%d 个标的 × 20000 根 15 分钟 K 线（影子系统 SurfersTrading/v4/m15.db）"
      % len(SYMS))
print()
t0 = time.time()
base = {}
for s in SYMS:
    base[s] = counts(s, 0.0)
print("基准（无扰动）：笔中枢 %s  ｜ 线段中枢 %s"
      % ([base[s][0] for s in SYMS], [base[s][1] for s in SYMS]))
print()
for eps in EPS:
    cvp, cvs, dp, ds = [], [], [], []
    for s in SYMS:
        pn, sn = [], []
        for _ in range(REPS):
            a, b = counts(s, eps)
            pn.append(a); sn.append(b)
        mp, ms = statistics.mean(pn), statistics.mean(sn)
        dp.append(mp - base[s][0]); ds.append(ms - base[s][1])
        if mp: cvp.append(statistics.pstdev(pn) / mp)
        if ms: cvs.append(statistics.pstdev(sn) / ms)
    print("扰动 ±%.2f%%  笔中枢 标的内变异 %5.1f%%（平均偏移 %+.1f 个）  ｜  "
          "线段中枢 %5.1f%%（平均偏移 %+.1f 个）"
          % (100 * eps, 100 * statistics.mean(cvp), statistics.mean(dp),
             100 * statistics.mean(cvs), statistics.mean(ds)))
print()
print("用时 %.0f 秒" % (time.time() - t0))
print()
print("判据：线段中枢的变异应显著小于笔中枢。")
