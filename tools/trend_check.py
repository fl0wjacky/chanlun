#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""走势分段（core/trend.py，docs/spec/走势分段.md 第五节）的检查＋探针。rc=0 才算过。

    python3 tools/trend_check.py              # data/ 下每份 K 线样本 + 两份夹具的硬条件
    python3 tools/trend_check.py --self-test  # 两个探针（第五节第 5、7 条）必须各自红

逐条（编号 ＝ spec 第五节）：
  1 首尾相接：前一段终点 == 后一段起点，第一段从第 0 根起，最后一段到最后一根；
  2 中间段（除图头、最后一段）至少一个线段中枢；
  3 分界点都是 done 刀的 cut_bar，且是已完成线段的端点；
  4 段类型只有 盘整／上涨／下跌（图头、最后一段没有中枢时记『无中枢』）；最后一段状态 还在长／中阴，其余 已确认；
  6 硬条件：zec30 上 5354（367.77）、6150（588.8），zec15 上 11314、12906 都是分界；
  8 先后顺序（L17:50）：下跌后面接下跌、上涨后面接上涨的，**只列出来，不算红**（Nova 10-05）。
探针（--self-test）：
  5 拿掉规则 3 ⇒ 第 2 条必须红（zec30 中间段 17 段没中枢；spec 说的 18 段含图头那一段）；
  7 拿掉『去刀后重算中枢』⇒ 留下的刀数必须变。
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
from core.analyze import analyze                              # noqa: E402
import core.signals                                           # noqa: E402,F401
import core.cut as C                                          # noqa: E402
import core.trend as T                                        # noqa: E402
from cut_check import load, kline_files                      # noqa: E402
S = sys.modules["core.signals"]

HARD = {"zec30_cut.json": ((5354, 367.77, "l"), (6150, 588.8, "h")),
        "zec15.json": ((11314, 367.77, "l"), (12906, 588.8, "h"))}
TYPES = ("盘整", "上涨", "下跌")
_R = {}


def run(fn, **kw):
    from config import tick_of
    if fn not in _R:
        r = analyze(load(os.path.join(ROOT, "data", fn)), tick=tick_of(fn))
        _R[fn] = (r, C.cut_centers(r, S.signals(r, "pen", "macd"))[1])
    r, cuts = _R[fn]
    return r, cuts, T.trend_segments(r, cuts, **kw)


def violations(fn, **kw):
    """→ {条目: [说明]}，第 8 条另算（只列不红）。"""
    r, cuts, ts = run(fn, **kw)
    n = len(r["bars"])
    done = [s for s in r["segs"] if not s.get("live")]
    ends = set([done[0]["i0"]] + [s["i1"] for s in done]) if done else set()
    done_cuts = {c["cut_bar"] for c in cuts if c["status"] == "done"}
    bad = {1: [], 2: [], 3: [], 4: []}
    if not ts or ts[0]["i0"] != 0 or ts[-1]["i1"] != n - 1:
        bad[1].append("没盖满 [0, %d]" % (n - 1))
    for a, b in zip(ts, ts[1:]):
        if a["i1"] != b["i0"]:
            bad[1].append("%d→%d 不相接" % (a["i1"], b["i0"]))
    for t in ts[1:-1]:
        if t["n_centers"] == 0:
            bad[2].append("%d–%d" % (t["i0"], t["i1"]))
    for t in ts[1:]:
        if t["i0"] not in done_cuts or t["i0"] not in ends:
            bad[3].append(t["i0"])
    for k, t in enumerate(ts):
        edge = k == 0 or k == len(ts) - 1
        if t["type"] not in TYPES and not (edge and t["type"] == "无中枢"):
            bad[4].append("%d 类型 %s" % (t["i0"], t["type"]))
        want = ("还在长", "中阴") if k == len(ts) - 1 else ("已确认",)
        if t["status"] not in want:
            bad[4].append("%d 状态 %s" % (t["i0"], t["status"]))
    return bad


def order_flags(fn):
    _, _, ts = run(fn)
    return [(a["i0"], a["type"], b["i0"], b["type"]) for a, b in zip(ts, ts[1:])
            if a["type"] == b["type"] and a["type"] in ("上涨", "下跌")]


def hard(fn):
    r, _, ts = run(fn)
    cuts = {t["i0"] for t in ts[1:]}
    return ["%d（%s）" % (b, p) for b, p, side in HARD[fn] if b not in cuts or r["bars"][b][side] != p]


def check(quiet=False):
    files = kline_files()
    total = {1: 0, 2: 0, 3: 0, 4: 0, 6: 0}
    for fn in files:
        bad = violations(fn)
        _, cuts, ts = run(fn)
        h = hard(fn) if fn in HARD else []
        for k in bad:
            total[k] += len(bad[k])
        total[6] += len(h)
        if not quiet:
            nd = sum(c["status"] == "done" for c in cuts)
            types = "".join({"盘整": "盘", "上涨": "涨", "下跌": "跌", "无中枢": "无"}[t["type"]] for t in ts)
            print("%s %-18s done 刀 %2d → 留 %2d · %2d 段 [%s] 末段%s%s" % (
                "✗" if any(bad.values()) or h else "✓", fn, nd, len(ts) - 1, len(ts), types, ts[-1]["status"],
                "".join("  ← 第%d条 %s" % (k, v[:3]) for k, v in bad.items() if v)
                + ("  ← 第6条 不是分界：%s" % h if h else "")))
    flags = {fn: order_flags(fn) for fn in files}
    if not quiet:
        for fn in HARD:
            if fn not in files:
                print("✗ 第6条 夹具 %s 不在 data/ 里" % fn)
        print("第 8 条（L17:50 先后顺序，只列不红）：%s" % (
            "; ".join("%s %s" % (fn, v) for fn, v in flags.items() if v) or "没有同向趋势接同向趋势"))
        print("首尾相接 %d · 中间段无中枢 %d · 分界不是 done 刀/端点 %d · 类型状态 %d · 硬条件 %d" % tuple(
            total[k] for k in (1, 2, 3, 4, 6)))
    total[6] += sum(1 for fn in HARD if fn not in files)
    return sum(total.values())


def self_test():
    miss = 0
    # 5：拿掉规则 3 ⇒ 第 2 条红
    n5 = len(violations("zec30_cut.json", rule3=False)[2])
    ok = n5 > 0
    print("%s 探针 5 拿掉规则 3 ⇒ zec30 中间段无中枢 %d 段（加图头 %d 段）" % (
        "✓" if ok else "✗", n5, n5 + (run("zec30_cut.json", rule3=False)[2][0]["n_centers"] == 0)))
    miss += not ok
    # 7：不重算中枢 ⇒ 留下的刀数变
    for fn in HARD:
        a = len(run(fn)[2]) - 1
        b = len(run(fn, regroup=False)[2]) - 1
        ok = a != b
        print("%s 探针 7 去刀后不重算中枢 ⇒ %s 留 %d → %d 把" % ("✓" if ok else "✗", fn, a, b))
        miss += not ok
    return 3 if miss else 0


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else (1 if check() else 0))
