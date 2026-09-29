#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 [DD, GG] 改成只统计 Z 走势段，并对比改动前后的差异。

为什么能干净地解：
  原文的 Z 走势段 = 「与中枢形成方向一致」的那几段 = A、B、C 里的 A 和 C。
  而笔的方向在标准化序列上是严格交替的（build_pens 保证 seq 里相邻端点必异类），
  所以 Z 段就是「覆盖区间里索引与第一笔同奇偶的那些笔」——
  等价于「第 1、3、5… 段」，不需要额外判断方向。
"""
import os, sys, json
sys.path.insert(0, "/var/minis/workspace/chanlun_mag")
from config import data
from core import analyze
from core.center import find_centers

P = "/var/minis/workspace/chanlun_mag/core/center.py"
s = open(P, encoding="utf-8").read()
OLD = '''def _range(pens, PI0, PI1):
    """中枢的波动范围 [DD, GG]（第 20 课四个指标里的两个）。"""
    seg = pens[PI0:PI1 + 1]
    return min(p["lo"] for p in seg), max(p["hi"] for p in seg)'''
NEW = '''def _range(pens, PI0, PI1):
    """中枢的波动范围 [DD, GG]（第 20 课）。

    只统计 **Z 走势段** —— 与中枢形成方向一致的那几段（A、C、E…）。
    因为笔的方向在标准化序列上严格交替，Z 段就是「覆盖区间里索引与
    第一笔同奇偶的笔」，也就是第 1、3、5… 段，不需要另行判断方向。
    """
    Z = pens[PI0:PI1 + 1:2]
    return min(p["lo"] for p in Z), max(p["hi"] for p in Z)


def _range_all(pens, PI0, PI1):
    """旧口径：覆盖区间内全部笔的极值（保留用于对比）。"""
    seg = pens[PI0:PI1 + 1]
    return min(p["lo"] for p in seg), max(p["hi"] for p in seg)'''
assert OLD in s
s = s.replace(OLD, NEW)
s = s.replace('''            DD, GG = _range(pens, i, end)''',
              '''            DD, GG = _range(pens, i, end)
            DD_all, GG_all = _range_all(pens, i, end)''')
s = s.replace('''                ZG=ZG, ZD=ZD, DD=DD, GG=GG,''',
              '''                ZG=ZG, ZD=ZD, DD=DD, GG=GG,
                DD_all=DD_all, GG_all=GG_all,
                nZ=len(pens[i:end + 1:2]),''')
open(P, "w", encoding="utf-8").write(s)
print("core/center.py 已改为 Z 段口径\n")

# ---- 对比 ----
print("=" * 74)
print("改动前后对比（[DD,GG] 是否变化）")
for fn, tag in (("aaplusdt_30m.json", "30分钟"), ("aaplusdt_1h.json", "1小时"),
                ("aaplusdt_2h.json", "2小时"), ("aaplusdt_4h.json", "4小时")):
    r = analyze(json.load(open(data(fn), encoding="utf-8")))
    diff = [z for z in r["centers"]
            if abs(z["DD"] - z["DD_all"]) > 1e-9 or abs(z["GG"] - z["GG_all"]) > 1e-9]
    kinds_old, kinds_new = [], []
    for z in r["centers"][1:]:
        pass
    print("[%s] 中枢 %d ｜ Z段口径与全部笔口径不同的: %d 个"
          % (tag, len(r["centers"]), len(diff)))
    for z in diff[:4]:
        print("     中枢[%g,%g] 覆盖%d笔(%d个Z段): Z口径[%g,%g] vs 全口径[%g,%g]"
              % (z["ZD"], z["ZG"], z["npens"], z["nZ"], z["DD"], z["GG"],
                 z["DD_all"], z["GG_all"]))

print()
print("=" * 74)
print("关系判定是否变化")
from collections import Counter
for fn, tag in (("aaplusdt_30m.json", "30分钟"), ("aaplusdt_1h.json", "1小时"),
                ("aaplusdt_2h.json", "2小时")):
    r = analyze(json.load(open(data(fn), encoding="utf-8")))
    c = Counter(z["kind"] for z in r["centers"][1:])
    tot = sum(c.values()); tr = c.get("趋势", 0)
    print("  %-8s %s   趋势占比 %s" % (tag, dict(c), "%.0f%%" % (100*tr/tot) if tot else "—"))
