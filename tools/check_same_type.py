#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证「同类相遇」与「跳过」的结构关系。

假设：分型本身严格交替（顶、底、顶、底…），所以「同类相遇」不可能凭空发生，
      只能是被跳过的那个异类分型造成的 —— 每一次同类相遇，前面必然紧邻一次跳过。
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import data
from core import analyze, analyze_file

T = lambda f: "顶" if f["type"] == "top" else "底"


def trace(fx, min_gap=4):
    """逐步记录每个分型被怎么处理。返回事件列表和最终端点序列。"""
    seq, ev = [], []
    for f in fx:
        if not seq:
            seq.append(f); ev.append((f, "首根", None)); continue
        last = seq[-1]
        if f["type"] == last["type"]:
            if (f["type"] == "top" and f["price"] > last["price"]) or \
               (f["type"] == "bot" and f["price"] < last["price"]):
                seq[-1] = f; ev.append((f, "同类·替换", last))
            else:
                ev.append((f, "同类·保留原端点", last))
        else:
            gap = f["k"] - last["k"]
            if gap >= min_gap:
                seq.append(f); ev.append((f, "成笔", last))
            else:
                ev.append((f, "跳过(间隔%d)" % gap, last))
    return ev, seq


for fn, tag in (("aaplusdt_4h.json", "4小时"), ("aaplusdt_30m.json", "30分钟")):
    r = analyze_file(fn)
    ev, seq = trace(r["fx"])
    n_same = sum(1 for _, a, _ in ev if a.startswith("同类"))
    n_skip = sum(1 for _, a, _ in ev if a.startswith("跳过"))
    # 每一次「同类」的紧邻前一个事件，是不是「跳过」？
    bad = []
    for i, (f, act, _) in enumerate(ev):
        if act.startswith("同类"):
            prev = ev[i - 1][1] if i > 0 else "（无）"
            if not prev.startswith("跳过"):
                bad.append((i, T(f), prev))
    # 每一次「跳过」的下一个事件，是不是「同类」？
    bad2 = []
    for i, (f, act, _) in enumerate(ev):
        if act.startswith("跳过") and i + 1 < len(ev):
            nxt = ev[i + 1][1]
            if not nxt.startswith("同类"):
                bad2.append((i, T(f), nxt))

    print("=" * 60)
    print("[%s] 分型 %d 个" % (tag, len(r["fx"])))
    print("  跳过 %d 次 ／ 同类处理 %d 次  →  差 %d" % (n_skip, n_same, n_skip - n_same))
    print("  「同类」前面不是「跳过」的: %d 处（应为 0）" % len(bad))
    print("  「跳过」后面不是「同类」的: %d 处（应为 0 或 1，末尾那次除外）" % len(bad2))
    if bad2:
        for i, t, nxt in bad2:
            print("     位置 %d：跳过%s之后是「%s」" % (i, t, nxt))
    # 打印前 8 步作为样例
    print("  前 8 步处理：")
    for f, act, last in ev[:8]:
        tail = "%s@%d(%.2f)" % (T(last), last["k"], last["price"]) if last else "（空）"
        print("     %s@%-3d %8.2f   末尾=%-16s → %s" % (T(f), f["k"], f["price"], tail, act))
