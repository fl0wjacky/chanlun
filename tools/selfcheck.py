#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""引擎自检：跑一遍全部不变量检查。任何一项不为 0 都说明引擎有问题。

K 线层（标准化 / 分型）→ 线段层（不变量 + 按原文定义独立复核）→ 中枢层（笔中枢、线段中枢）。
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from config import data
from core import analyze, summarize, check_standardized, check_fractals_alternate
from core.segment import check_segments, verify_by_definition, nonextreme_endpoints
from core.center import check_centers

DATASETS = [("aaplusdt_4h.json", "AAPL 4h"), ("aaplusdt_2h.json", "AAPL 2h"),
            ("aaplusdt_1h.json", "AAPL 1h"), ("aaplusdt_30m.json", "AAPL 30m"),
            ("zec15.json", "ZEC 15m")]

FAIL = 0
R = {tag: analyze(json.load(open(data(fn), encoding="utf-8"))) for fn, tag in DATASETS}


def count(label, n, note=""):
    """打印一项违规计数并计入总数。"""
    global FAIL
    FAIL += n
    print("  %-26s: %d  (应为 0)%s" % (label, n, note))


for tag, r in R.items():
    m = r["std"]
    print("=" * 72)
    print("[%s] %s" % (tag, summarize(r)))
    # K 线层
    count("相邻仍含包含关系", len(check_standardized(m)))
    count("相邻高点相等", sum(1 for i in range(len(m) - 1) if m[i]["h"] == m[i + 1]["h"]))
    count("相邻低点相等", sum(1 for i in range(len(m) - 1) if m[i]["l"] == m[i + 1]["l"]))
    count("分型类型未严格交替", len(check_fractals_alternate(r["fx"])))
    # 分型：4 条件版 vs 只看高点 / 低点版，结果必须一致（「低点也最高」是自动的）
    only_h = {k for k in range(1, len(m) - 1) if m[k]["h"] > m[k - 1]["h"] and m[k]["h"] > m[k + 1]["h"]}
    only_l = {k for k in range(1, len(m) - 1) if m[k]["l"] < m[k - 1]["l"] and m[k]["l"] < m[k + 1]["l"]}
    tops = {f["k"] for f in r["fx"] if f["type"] == "top"}
    bots = {f["k"] for f in r["fx"] if f["type"] == "bot"}
    count("顶分型 4条件≠只看高点", len(tops ^ only_h))
    count("底分型 4条件≠只看低点", len(bots ^ only_l))
    # 线段层
    S, P = r["segs"], r["pens"]
    count("线段不变量违规", len(check_segments(S, P)))
    count("线段定义复核违规", len(verify_by_definition(S, P)),
          "　｜ 诊断：终点非段内极值 %d（原文未要求，只报数）" % len(nonextreme_endpoints(S)))
    # 中枢层
    count("笔中枢不变量违规", len(check_centers(r["centers"], P)))
    count("线段中枢不变量违规", len(check_centers(r["seg_centers"], [s for s in S if not s.get("live")])))

print("=" * 72)
print("总违规数:", FAIL, "→", "全部通过" if FAIL == 0 else "有问题，需排查")
sys.exit(1 if FAIL else 0)
