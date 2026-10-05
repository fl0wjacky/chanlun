#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""中枢切分（core/cut.py，docs/spec/中枢切分.md）的检查＋探针。rc=0 才算过。

    python3 tools/cut_check.py [bars.json]     # 不给就用 data/zec15.json

逐条核：
  ① 形状：cuts 按 cut_bar 升序、cut_bar 都是已完成线段端点、status ∈ pending/done/void、boxes 只在 pending 有且全带 provisional；
  ② 规则 4：没有 done 的刀 ⇒ seg_centers 跟不切那份逐字段相同（待定照回旧框）；
  ③ 规则 5：每一刀的 status 按「切点后头三段已完成线段重叠」独立重算一遍，必须对上；
  ④ 规则 6：只动线段中枢 —— 笔、线段、类中枢、两层买卖点不变（cut_centers 不改 r）；
  探针 A（规格第三节第 4 条）：把『头三段重叠』改成『头一段走完就算』⇒ 切成数必须变；
  探针 B：转折点改在线段层认 ⇒ 线上那两个横跨的框（若在这份数据里）必须切不开 —— 这里量成『线段层认出的刀里没有一刀
         落在 405.9–423 / 523.24–549.65 两个框的内部』。
"""
import copy
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from core.analyze import analyze                              # noqa: E402
import core.signals                                           # noqa: E402,F401
import core.cut as C                                          # noqa: E402
S = sys.modules["core.signals"]


def load(path):
    raw = json.load(open(path))
    raw = raw["bars"] if isinstance(raw, dict) else raw
    return [dict(t=b["t"], o=b["o"], h=b["h"], l=b["l"], c=b["c"]) for b in raw]


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "data", "zec15.json")
    r = analyze(load(path), tick=0.01)
    before = copy.deepcopy(r)
    sig = S.signals(r, "pen", "macd")
    cur, cuts = C.cut_centers(r, sig)
    done = [s for s in r["segs"] if not s.get("live")]
    ends = {done[0]["i0"]} | {s["i1"] for s in done}
    bad = []

    def cell(name, ok, note=""):
        print("%s %s %s" % ("✓" if ok else "✗", name, note))
        if not ok:
            bad.append(name)

    shape_ok = (all(a["cut_bar"] < b["cut_bar"] for a, b in zip(cuts, cuts[1:]))
                and all(c["cut_bar"] in ends and c["status"] in ("pending", "done", "void") and c["level"] == "seg"
                        for c in cuts)
                and all(("boxes" in c) == (c["status"] == "pending") for c in cuts)
                and all(z.get("provisional") is True for c in cuts for z in c.get("boxes", [])))
    cell("① 形状（升序、落在线段端点、status 三选一、boxes 只在 pending 且带 provisional）", shape_ok, "%d 刀" % len(cuts))

    nodone = [dict(c, status="pending") for c in cuts]
    k_none = C._centers_with_cuts(done, [])
    cell("② 一刀不切时重建出来的 ＝ 原 seg_centers（待定照回旧框的前提）", [(z["PI0"], z["PI1"], z["ZD"], z["ZG"]) for z in k_none]
         == [(z["PI0"], z["PI1"], z["ZD"], z["ZG"]) for z in r["seg_centers"]], "（%d 刀全当待定）" % len(nodone))

    pos = {s["i0"]: k for k, s in enumerate(done)}
    mism = []
    for c in cuts:
        k = pos.get(c["cut_bar"], len(done))
        tri = done[k:k + 3]
        want = "pending" if len(tri) < 3 else ("done" if min(x["hi"] for x in tri) >= max(x["lo"] for x in tri) else "void")
        if want != c["status"]:
            mism.append((c["cut_bar"], c["status"], want))
    cell("③ 规则 5 独立重算", not mism, "不符 %s" % mism[:3])

    same = all(r[k] == before[k] for k in ("pens", "segs", "centers", "seg_centers"))
    cell("④ 只动线段中枢（r 原样、买卖点不变）", same and S.signals(r, "pen", "macd") == sig
         and S.signals(r, "seg", "macd") == S.signals(before, "seg", "macd"))

    real = C._status
    C._status = lambda done_, k: "done" if k + 1 <= len(done_) else "pending"     # 头一段走完就算
    try:
        _, cuts_a = C.cut_centers(r, sig)
    finally:
        C._status = real
    n0, na = sum(c["status"] == "done" for c in cuts), sum(c["status"] == "done" for c in cuts_a)
    cell("探针 A：『头一段走完就算』⇒ 切成数变", n0 != na, "%d → %d" % (n0, na))

    seg_sig = S.signals(r, "seg", "macd")
    _, cuts_b = C.cut_centers(r, seg_sig, units=r["segs"])
    targets = [z for z in r["seg_centers"] if round(z["ZD"], 2) in (405.90, 523.24)]
    inside = [c for c in cuts_b for z in targets if z["X0"] < c["cut_bar"] < z["X1"]]
    cell("探针 B：线段层认 ⇒ 那两个框切不开", not inside,
         "（这份数据里找到 %d 个目标框；线段层认出 %d 刀）" % (len(targets), len(cuts_b)))
    print("全部通过" if not bad else "%d 格不过" % len(bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
