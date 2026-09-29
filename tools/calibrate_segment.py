#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用 59 个标的 × 24417 根日线校准线段层。

三项检验：
  ① 不变量：笔数≥3、单数、相邻方向相反、首尾相接、覆盖全部笔
  ② 线段长度分布（理论最小 3 笔）
  ③ ★ 时间反转对称性 —— 把K线倒过来重划，线段端点应当一致。
     线段是结构，不该因为"从哪边开始看"而改变。这条最能暴露
     「第二种情况（有缺口）」的简化问题。
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import data
from core import analyze
from core.segment import build_segments, check_segments

KL = json.load(open(data("mag_klines.json")))


def bars_of(coin):
    return [dict(t=i, o=r[1], h=r[2], l=r[3], c=r[4]) for i, r in enumerate(KL[coin])]


def seg_dates(coin, reverse=False):
    b = bars_of(coin)
    if reverse:
        b = b[::-1]
    r = analyze(b)
    segs = build_segments(r["pens"])
    ends = set()
    for s in segs:
        d = KL[coin]
        ends.add(d[s["i0"]][0]); ends.add(d[s["i1"]][0])
    return ends, len(segs), len(r["pens"]), segs, r


inv_bad = 0
lens = []
fwd_cnt = rev_cnt = 0
sym_same = sym_diff = 0
worst = []
for coin in sorted(KL):
    ends_f, nf, npf, sf, rf = seg_dates(coin, False)
    ends_r, nr, npr, sr, rr = seg_dates(coin, True)
    inv_bad += len(check_segments(sf, rf["pens"])) + len(check_segments(sr, rr["pens"]))
    lens += [s["npens"] for s in sf if not s.get("live")]
    fwd_cnt += 1; rev_cnt += 1
    if npf >= 6:                                   # 样本太短的跳过对称性比较
        if ends_f == ends_r:
            sym_same += 1
        else:
            sym_diff += 1
            d = len(ends_f ^ ends_r)
            worst.append((coin, npf, npr, len(ends_f), len(ends_r), d))

print("=" * 70)
print("样本：%d 个标的，%d 根日线" % (len(KL), sum(len(v) for v in KL.values())))
print()
print("① 不变量违规总数：%d" % inv_bad)
print("② 线段长度：最短 %d 笔，最长 %d 笔，平均 %.1f 笔（理论最小 3）"
      % (min(lens), max(lens), sum(lens) / len(lens)))
from collections import Counter
c = Counter(lens)
print("   分布：", dict(sorted(c.items())))
print()
print("③ 时间反转对称性（笔数 ≥6 的标的）")
print("   端点完全一致：%d ｜ 不一致：%d" % (sym_same, sym_diff))
if worst:
    print("   不一致最多的前 8 个：")
    for w in sorted(worst, key=lambda x: -x[5])[:8]:
        print("      %-8s 笔正%3d/反%3d  端点正%2d/反%2d  差 %d"
              % (w[0], w[1], w[2], w[3], w[4], w[5]))
