#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证：笔与笔之间是否连续？以及「丢弃/替换」会改动几条笔？

做法：把 K 线一根一根喂进去，每加一根就重算一次笔，
比较前后两次的笔列表有多少条被改动。
"""
import os, sys, json, datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import data
from core.analyze import analyze

D = lambda ms: datetime.datetime.fromtimestamp(ms / 1000, datetime.timezone.utc)

# ---------- 1) 数据溯源 ----------
for fn, tag in (("aaplusdt_4h.json", "4小时"), ("aaplusdt_30m.json", "30分钟")):
    b = json.load(open(data(fn), encoding="utf-8"))
    print("[%s] %d 根  ｜ %s  →  %s (UTC)"
          % (tag, len(b), D(b[0]["t"]).strftime("%Y-%m-%d %H:%M"),
             D(b[-1]["t"]).strftime("%Y-%m-%d %H:%M")))
print()

# ---------- 2) 笔是否首尾相接 ----------
for fn, tag in (("aaplusdt_4h.json", "4小时"), ("aaplusdt_30m.json", "30分钟")):
    r = analyze(json.load(open(data(fn), encoding="utf-8")))
    p = r["pens"]
    gaps = [i for i in range(len(p) - 1)
            if not (p[i]["i1"] == p[i + 1]["i0"] and abs(p[i]["p1"] - p[i + 1]["p0"]) < 1e-9)]
    print("[%s] 笔 %d 条 ｜ 首尾不相接处: %d ｜ 端点数 == 笔数+1 : %s"
          % (tag, len(p), len(gaps), len(r["seq"]) == len(p) + 1))
print()

# ---------- 3) 逐根喂入：有几条笔会被改动？ ----------
bars = json.load(open(data("aaplusdt_4h.json"), encoding="utf-8"))
prev, stats = None, []
for i in range(30, len(bars) + 1):
    cur = analyze(bars[:i])["pens"]
    if prev is not None:
        k = 0
        while k < min(len(prev), len(cur)) and \
                prev[k]["i0"] == cur[k]["i0"] and abs(prev[k]["p0"] - cur[k]["p0"]) < 1e-9 and \
                prev[k]["i1"] == cur[k]["i1"] and abs(prev[k]["p1"] - cur[k]["p1"]) < 1e-9:
            k += 1
        stats.append((len(prev), k, len(cur)))
    prev = cur

changed = [max(0, m - k) for (m, k, n) in stats]
print("逐根喂入 4 小时数据（%d 次迭代）:" % len(stats))
print("  已成立笔的最大改动条数 : %d   ← 若恒为 0/1，说明只动最后一条"
      % max(changed))
print("  出现「改了 2 条以上」的次数: %d" % sum(1 for c in changed if c >= 2))
print("  平均每次改动条数        : %.2f" % (sum(changed) / len(changed)))
