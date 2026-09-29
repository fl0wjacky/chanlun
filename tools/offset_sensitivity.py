#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""实验：起点不一样，画出的笔、线段还一样吗？

做法：同一份数据，掐掉开头 N 根再算（N = 1, 2, 5, 10, 30, 100, 300），
      把端点换算回原始下标，与「从头算」的版本比较：
      —— 找出「最后一个不一致的位置」，其后完全一致 = 收敛点。
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import data
from core import analyze
from core.segment import build_segments


def run(name, raw):
    bars_full = [dict(t=i, o=r[1], h=r[2], l=r[3], c=r[4]) for i, r in enumerate(raw)]
    n = len(bars_full)

    def endpoints(off):
        r = analyze(bars_full[off:])
        pens = sorted(set([p["i0"] + off for p in r["pens"]] +
                          [p["i1"] + off for p in r["pens"]]))
        segs = build_segments(r["pens"])
        sege = sorted(set([s["i0"] + off for s in segs] +
                          [s["i1"] + off for s in segs]))
        return pens, sege

    bp, bs = endpoints(0)

    def last_diff(a, b):
        """最后一个不一致的原始下标（None = 完全一致）"""
        i, j = len(a) - 1, len(b) - 1
        while i >= 0 and j >= 0 and a[i] == b[j]:
            i -= 1; j -= 1
        cand = []
        if i >= 0: cand.append(a[i])
        if j >= 0: cand.append(b[j])
        return max(cand) if cand else None

    print("== %s（共 %d 根）==" % (name, n))
    print("  掐头   笔端点数(基准%d)  笔最后分歧位   线段端点数(基准%d)  线段最后分歧位" % (len(bp), len(bs)))
    for off in (1, 2, 5, 10, 30, 100, 300):
        p, s = endpoints(off)
        dp, ds = last_diff(bp, p), last_diff(bs, s)
        print("  %4d   %6d           %-12s %6d            %s"
              % (off, len(p), ("第 %d 根" % dp) if dp is not None else "无（全同）",
                 len(s), ("第 %d 根" % ds) if ds is not None else "无（全同）"))
    print()


run("ZEC 15分钟", json.load(open(os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "zec15.json"))))

d2 = json.load(open(data("m15_sub.json")))
k = sorted(d2)[1]
run("%s 15分钟（前 5000 根）" % k, d2[k][:5000])
