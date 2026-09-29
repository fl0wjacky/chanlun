#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对照：旧整序列口径（包含处理跨分界点）vs 现行口径（第 67 课定义 + 第 71 课分界点规则）。

判据来自第 83 课：「线段受偶尔性的影响比较少」—— 更稳的那个更符合原文精神。
做法：扰动一根 K 线，看线段端点集合变不变。
"""
import os, sys, json, random, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import data
from core import analyze
from core.segment import build_segments, build_segments_whole_seq

D = json.load(open(data("m15_sub.json")))
SYMS = sorted(D)[:2]
N, EPS = 25, 0.005
random.seed(20260928)


def keys(sym, spike=None):
    out = []
    for i, r in enumerate(D[sym]):
        ts, o, h, l, c = r
        if spike and i == spike[0]:
            if spike[1] == "h":
                h = max(h * (1 + EPS), o, c)
            else:
                l = min(l * (1 - EPS), o, c)
        out.append(dict(t=i, o=o, h=h, l=l, c=c))
    a = analyze(out)
    return (frozenset((s["i0"], s["i1"]) for s in build_segments_whole_seq(a["pens"])),
            frozenset((s["i0"], s["i1"]) for s in build_segments(a["pens"])))


print("=" * 70)
print("扰一根K线(±0.5%)，看线段端点集合变不变 —— 变化率低者胜")
print()
for sym in SYMS:
    b67, b71 = keys(sym)
    c67 = c71 = 0
    t0 = time.time()
    for _ in range(N):
        i = random.randrange(100, len(D[sym]) - 100)
        a, b = keys(sym, (i, random.choice("hl")))
        c67 += (a != b67)
        c71 += (b != b71)
    print("  %-14s 旧整序列 %3d 条 → 变化 %.0f%% ｜ 现行 %3d 条 → 变化 %.0f%%   [%.0fs]"
          % (sym, len(b67), 100 * c67 / N, len(b71), 100 * c71 / N, time.time() - t0))
