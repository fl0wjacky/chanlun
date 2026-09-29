#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""★ 按第 83 课原话设计的检验：「一个偶尔一笔的错误」能传播多远。

原文关键句：
    「一笔的基础是顶和底分型，而一些瞬间的交易，就足以影响其结构。」（指笔）
    「一个线段的改变，不会因为一个偶尔一笔的错误而改变，也就是说，线段受偶尔性的影响比较少。」（指线段）

所以正确的问题是：**扰动一根 K 线，笔变了没有？线段变了没有？**
    —— 不是「中枢数量稳不稳」（那个受量级干扰，前面四版都栽在这上面）

做法：随机挑一根 K 线，把它放大 eps（模拟一笔异常成交），重算结构，
      比较笔端点集合 / 线段端点集合与基准是否一致。
"""
import os, sys, json, random, statistics, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import data
from core import analyze
from core.segment import build_segments

D = json.load(open(data("m15_sub.json")))
SYMS = sorted(D)[:3]
TRIALS = 60
EPS = 0.005
random.seed(20260928)


def build(sym, spike=None, eps=EPS):
    """spike = (下标, 'h'|'l')；把那一根的高或低点放大 eps"""
    out = []
    for i, r in enumerate(D[sym]):
        ts, o, h, l, c = r
        if spike and i == spike[0]:
            if spike[1] == "h":
                h = h * (1 + eps); h = max(h, o, c)
            else:
                l = l * (1 - eps); l = min(l, o, c)
        out.append(dict(t=i, o=o, h=h, l=l, c=c))
    r = analyze(out)
    segs = build_segments(r["pens"])
    return (frozenset(p["i"] for p in r["seq"]),
            frozenset((s["i0"], s["i1"]) for s in segs))


print("=" * 74)
print("扰动「一根」K线（放大 %.1f%%），看笔 / 线段 变不变" % (100 * EPS))
print("样本：%d 标的 × 20000 根 15 分钟K线 × %d 次随机单根扰动" % (len(SYMS), TRIALS))
print()
for sym in SYMS:
    bp, bs = build(sym)
    chp = chs = 0
    t0 = time.time()
    for _ in range(TRIALS):
        i = random.randrange(100, len(D[sym]) - 100)
        side = random.choice("hl")
        try:
            np_, ns_ = build(sym, (i, side))
        except Exception:
            continue
        if np_ != bp: chp += 1
        if ns_ != bs: chs += 1
    print("  %-14s 笔端点 %3d 个 ｜ 线段 %2d 条  →  笔变了 %2d/%d (%.0f%%)  ｜  "
          "线段变了 %2d/%d (%.0f%%)   [%.0fs]"
          % (sym, len(bp), len(bs), chp, TRIALS, 100 * chp / TRIALS,
             chs, TRIALS, 100 * chs / TRIALS, time.time() - t0))
print()
print("判据（第 83 课）：线段的变化率应显著低于笔。")
