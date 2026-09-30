#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""线段层稳定性：用「中枢存活率」而不是变异系数。

为什么换指标：笔中枢 ~180 个、线段中枢 ~24 个，量级差 7.5 倍 ——
变异系数在量级差异大时不可比。存活率不受量级影响：

    对基准里的每一个中枢，检查扰动后是否还存在一个「大致相同」的中枢
    （区间交并比 > 0.7）。存活率高 = 结构稳定。

判据（第 83 课）：「用笔当成构成最小中枢的零件……其稳定性极差」
              「由线段构成最小中枢，则不存在这个问题」
    （引文按原文逐字，中间略去的一段用省略号标 —— 与 cards/c05_center.py:207 同法。）
    → 若线段中枢的存活率 不高于 笔中枢，该论断被证伪。
"""
import os, sys, json, random, statistics, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import data
from core import analyze

D = json.load(open(data("m15_sub.json")))
SYMS = sorted(D)[:3]
REPS = 5
EPS = 0.002
random.seed(20260928)


def bars_of(sym, eps=0.0):
    out = []
    for i, r in enumerate(D[sym]):
        ts, o, h, l, c = r
        if eps:
            h = h * (1 + random.uniform(-eps, eps)); l = l * (1 - random.uniform(-eps, eps))
            h = max(h, o, c); l = min(l, o, c)
        out.append(dict(t=i, o=o, h=h, l=l, c=c))
    return out


def both(sym, eps):
    r = analyze(bars_of(sym, eps))
    return r["centers"], r["seg_centers"]


def survival(base, new, thr=0.7):
    hit = 0
    for b in base:
        for n in new:
            inter = min(b["ZG"], n["ZG"]) - max(b["ZD"], n["ZD"])
            union = max(b["ZG"], n["ZG"]) - min(b["ZD"], n["ZD"])
            if union > 0 and inter / union > thr:
                hit += 1; break
    return hit / len(base) if base else 0


print("=" * 74)
print("中枢存活率：扰动 ±%.1f%% 后，原中枢还有多少「大致还在」" % (100 * EPS))
print("（交并比 > 0.7 算存活；样本 %d 标的 × %d 次 × 20000 根 15 分钟K线）"
      % (len(SYMS), REPS))
print()
sp, ss = [], []
t0 = time.time()
for s in SYMS:
    bp, bs = both(s, 0.0)
    rp, rs = [], []
    for _ in range(REPS):
        np_, ns_ = both(s, EPS)
        rp.append(survival(bp, np_)); rs.append(survival(bs, ns_))
    print("  %-14s 笔中枢 %3d 个 → 存活 %5.1f%%  ｜  线段中枢 %2d 个 → 存活 %5.1f%%"
          % (s, len(bp), 100 * statistics.mean(rp), len(bs), 100 * statistics.mean(rs)))
    sp.append(statistics.mean(rp)); ss.append(statistics.mean(rs))
print()
print("平均：笔中枢存活 %.1f%%  ｜  线段中枢存活 %.1f%%" % (100 * statistics.mean(sp), 100 * statistics.mean(ss)))
print("用时 %.0f 秒" % (time.time() - t0))
