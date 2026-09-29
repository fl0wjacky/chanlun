#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""直接检验第 83 课的论断：笔中枢「稳定性极差」，线段中枢则不存在这个问题。

做法：给每根 K 线的高低点加一点随机微扰（模拟「一些瞬间的交易」），
      重算中枢，看数量变化多少。
      笔中枢的变异应显著大于线段中枢 —— 若不然，第 83 课这句话就被证伪。
"""
import os, sys, json, random, statistics
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import data
from core import analyze

KL = json.load(open(data("mag_klines.json")))
random.seed(20260928)


def bars_of(coin, eps=0.0):
    out = []
    for i, r in enumerate(KL[coin]):
        _, o, h, l, c = r
        if eps:
            h = h * (1 + random.uniform(-eps, eps))
            l = l * (1 + random.uniform(-eps, eps))
            h = max(h, o, c); l = min(l, o, c)
        out.append(dict(t=i, o=o, h=h, l=l, c=c))
    return out


def counts(coin, eps=0.0):
    r = analyze(bars_of(coin, eps))
    return len(r["centers"]), len(r["seg_centers"])


print("=" * 78)
print("扰动稳定性：同一标的内部，加 ±eps 微扰后中枢数量的变异")
print()
coins = [c for c in sorted(KL) if len(KL[c]) >= 500]
print("样本：%d 个标的（各 ≥500 根日线），每次 8 组随机微扰\n" % len(coins))
REPS = 8
for eps in (0.001, 0.003, 0.01, 0.03):
    cvp, cvs, ref_p, ref_s = [], [], [], []
    for coin in coins:
        pn, sn = [], []
        for _ in range(REPS):
            a_, b_ = counts(coin, eps)
            pn.append(a_); sn.append(b_)
        mp, ms = statistics.mean(pn), statistics.mean(sn)
        ref_p.append(mp); ref_s.append(ms)
        if mp: cvp.append(statistics.pstdev(pn) / mp)
        if ms: cvs.append(statistics.pstdev(sn) / ms)
    print("eps=%.3f  笔中枢：平均%5.1f个，标的内变异 %5.1f%%  ｜  "
          "线段中枢：平均%4.1f个，标的内变异 %5.1f%%"
          % (eps, statistics.mean(ref_p), 100*statistics.mean(cvp),
             statistics.mean(ref_s), 100*statistics.mean(cvs)))
print()
print("判据：第 83 课说「一些瞬间的交易，就足以影响其结构」（笔中枢）")
print("      「而由线段构成最小中枢，则不存在这个问题」。")
print("      → 若线段中枢的标的内变异 不显著小于 笔中枢，该论断被证伪。")
