#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""走势分界 v3（core/trend.py，docs/spec/走势分段.md v3）的检查＋探针。rc=0 才算过。

    python3 tools/trend_check.py              # 基线 + 不变量 + 不看未来
    python3 tools/trend_check.py --self-test  # spec §四 的探针（拿掉一条规则，结果必须变）

  ① 基线（spec §三）：zec15 五个分界（bar、高低、确立那一根）＋ 531.91 撤回一次；zec30 五个；btc_4h／zec_1h／aaplusdt_30m 各一个；
  ② 不变量（data/ 下每份 K 线）：一高一低交替（D2-3）；刀落在同向线段的终点上（D2-1）；确立晚于刀（L88:19-21）；
     相邻两刀之间至少一个中枢（D2-7）；没有框跨过分界（D4-1）；走势首尾相接盖满整张图；每个框的 seg 指对了段；
  ③ 367.77（zec15 bar 11314）不是分界、落在框里（D4-4）；
  ④ 不看未来：每个分界从『最早能确立』那一根截断起就在，之后再截都不变（实时确立比回抽段终点晚，印出来）。
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
from core.analyze import analyze                              # noqa: E402
import core.trend as T                                        # noqa: E402
import re                                                     # noqa: E402

# 线上用哪种 D3 读法以 web/server.py 的 TREND_READING 为准（不 import server，免得起它那一摊）；这里的格子都按它跑
_m = re.search(r'^TREND_READING = "([AB])"', open(os.path.join(ROOT, "web", "server.py"), encoding="utf-8").read(), re.M)
READING = _m.group(1) if _m else None

# spec §三（agent/atlas/spec-v3 22e0570 起）：(bar, 高低, 确立那一根)
BASE = {
    "zec15.json": [(490, "L", None), (7558, "H", None), (9043, "L", None), (12906, "H", None), (14215, "L", None)],
    "zec30_cut.json": [(134, "L", None), (3476, "H", None), (4219, "L", None), (6150, "H", None), (6805, "L", None)],
}
BASE_PRICE = {"btc_4h.json": [("H", 97932.1)], "zec_1h.json": [("L", 205.07)], "aaplusdt_30m.json": [("L", 300.50)]}
def load(path):
    raw = json.load(open(path))
    raw = raw["bars"] if isinstance(raw, dict) else raw
    return [dict(t=b["t"], o=b["o"], h=b["h"], l=b["l"], c=b["c"]) for b in raw]


def kline_files():
    """data/ 下所有「K 线数组」样本（每条有 t/o/h/l/c）；别的 JSON（标注、子图样本）跳过。"""
    out = []
    for fn in sorted(os.listdir(os.path.join(ROOT, "data"))):
        if not fn.endswith(".json") or fn.endswith("_tmp.json"):
            continue
        try:
            raw = json.load(open(os.path.join(ROOT, "data", fn)))
        except ValueError:
            continue
        if isinstance(raw, list) and raw and isinstance(raw[0], dict) and {"t", "o", "h", "l", "c"} <= set(raw[0]):
            out.append(fn)
    return out


# spec D3（小栋 10-05 定 B）：升级中枢留在本级别一起数。下面是**冻结夹具 data/zec15.json** 的段类型（下标 0 起），
# 不是线上：线上窗口在滚，段数和中枢合法都会变（10-06 线上第 1 段 4 个中枢合成一个 n=4 ⇒ 本级别只剩一个 ⇒ 盘整，也对）。
# 夹具里第 1 段（bar 490–7558）4 个中枢只合了 2 个 ⇒ 本级别 3 个 ⇒「上涨」；第 5 段同理。A 读法下两段都是「升级·盘整」。
TYPES = {"zec15.json": ["盘整", "上涨", "盘整", "盘整", "下跌", "上涨"]}
RETRACT = {"zec15.json": [(15295, "H")], "zec30_cut.json": []}
_R = {}


def run(fn, bars=None, **kw):
    from config import tick_of
    key = (fn, len(bars) if bars else None)
    if key not in _R:
        _R[key] = analyze(bars or load(os.path.join(ROOT, "data", fn)), tick=tick_of(fn))
    kw.setdefault("reading", READING)
    return _R[key], T.trend_v3(_R[key], **kw)


def baseline():
    bad = []
    for fn, want in BASE.items():
        _, v = run(fn)
        got = [(b["bar"], b["kind"]) for b in v["bounds"]]
        if got != [(b, k) for b, k, _ in want]:
            bad.append("%s 分界 %s ≠ %s" % (fn, got, [(b, k) for b, k, _ in want]))
        rg = [(x["bar"], x["kind"]) for x in v["retracted"]]
        if rg != RETRACT[fn]:
            bad.append("%s 撤回 %s ≠ %s" % (fn, rg, RETRACT[fn]))
    for fn, want in BASE_PRICE.items():
        _, v = run(fn)
        got = [(b["kind"], round(b["price"], 2)) for b in v["bounds"]]
        if got != want:
            bad.append("%s 分界 %s ≠ %s" % (fn, got, want))
    return bad


def invariants(fn):
    r, v = run(fn)
    bad = []
    done = [s for s in r["segs"] if not s.get("live")]
    ends = {s["i1"]: s for s in done}
    bs = v["bounds"]
    for a, b in zip(bs, bs[1:]):
        if a["kind"] == b["kind"]:
            bad.append("不交替 %d/%d" % (a["bar"], b["bar"]))
    for b in bs:
        s = ends.get(b["bar"])
        if s is None or (s["p1"] > s["p0"]) != (b["kind"] == "H"):
            bad.append("刀 %d 不在同向线段终点" % b["bar"])
        if b["pullback_end_bar"] <= b["bar"]:
            bad.append("刀 %d 回抽段终点不晚于刀" % b["bar"])
    for a, b in zip(bs, bs[1:]):                 # D2-7：两刀之间至少一个中枢
        if not [z for z in v["seg_centers"] if a["bar"] <= z["X0"] and z["X1"] <= b["bar"]]:
            bad.append("%d→%d 之间没有中枢" % (a["bar"], b["bar"]))
    for b in bs:                                 # D4-1：框不跨分界
        for z in v["seg_centers"]:
            if z["X0"] < b["bar"] < z["X1"]:
                bad.append("框 %d–%d 跨过分界 %d" % (z["X0"], z["X1"], b["bar"]))
    seg = v["segments"]
    for z in v["seg_centers"]:                    # 每个框的 seg 指的那段走势真的装得下它（前端靠它编字母）
        g = z.get("seg")
        if g is None or not (0 <= g < len(seg)) or not (seg[g]["i0"] <= z["X0"] and z["X1"] <= seg[g]["i1"]):
            bad.append("框 %d–%d 的 seg=%r 不对" % (z["X0"], z["X1"], g))
    for b in bs:                                  # 对外 seg 只指走势段号：bounds 不许带同名键（用 line_seg）
        if "seg" in b:
            bad.append("bounds 带了 seg 键（该叫 line_seg）")
        elif not any(s["i0"] == b["bar"] for s in seg[1:]):
            bad.append("分界 %d 不是某一段走势的起点" % b["bar"])
    if sum(s["n_centers_level"] for s in seg) != len(v["seg_centers"]):
        bad.append("各段 n_centers_level 之和 ≠ seg_centers 个数")
    if seg[0]["i0"] != 0 or seg[-1]["i1"] != len(r["bars"]) - 1 or any(
            a["i1"] != b["i0"] for a, b in zip(seg, seg[1:])):
        bad.append("走势没有首尾相接盖满")
    return bad


def first_seen(fn, k, want, bars, lo):
    """第 k 个分界最早在哪一根截断时就有了（二分；之后一直在，见 no_future 的复查）。"""
    hi = len(bars) - 1

    def ok(t):
        _, v = run(fn, bars[:t + 1])
        return [(x["bar"], x["kind"]) for x in v["bounds"]][:k + 1] == want
    if not ok(hi):
        return None
    while lo < hi:
        mid = (lo + hi) // 2
        if ok(mid):
            hi = mid
        else:
            lo = mid + 1
    return lo


def no_future(fn="zec15.json"):
    """不看未来：每个分界在它『最早能确立』的那一根截断重跑就在，此后再截（＋1 天、＋1 周、＋1 月）都还在、不变。
    ★ 最早能确立 ≠ spec 表里的『确立』列（那是回抽段的终点）：线段要等后面的 K 线才算走完，所以实时会晚一截，这里一并印出来。"""
    bars = load(os.path.join(ROOT, "data", fn))
    _, full = run(fn)
    bad, lags = [], []
    for k, b in enumerate(full["bounds"]):
        want = [(x["bar"], x["kind"]) for x in full["bounds"][:k + 1]]
        seen = first_seen(fn, k, want, bars, b["pullback_end_bar"])
        if seen is None:
            bad.append("%d 截到图尾都没有" % b["bar"])
            continue
        lags.append(seen - b["pullback_end_bar"])
        for extra in (96, 672, 2880):            # 15m：1 天、1 周、1 月
            t = seen + extra
            if t >= len(bars):
                break
            _, v = run(fn, bars[:t + 1])
            if [(x["bar"], x["kind"]) for x in v["bounds"]][:k + 1] != want:
                bad.append("%d 在 %d 出现、%d 又变了" % (b["bar"], seen, t))
    print("    实时比回抽段终点晚：%s 根" % lags)
    return bad


def main():
    bad = []

    def cell(name, items):
        print("%s %s %s" % ("✓" if not items else "✗", name, items[:3] if items else ""))
        bad.extend(items)

    cell("① 基线（spec §三）", baseline())
    files = kline_files()
    inv = []
    for fn in files:
        inv += ["%s %s" % (fn, x) for x in invariants(fn)]
    cell("② 不变量（%d 份样本）" % len(files), inv)
    r, v = run("zec15.json")
    in_box = [z for z in v["seg_centers"] if z["X0"] < 11314 < z["X1"]]
    cell("③ 367.77（bar 11314）不是分界、落在框里",
         [] if 11314 not in [b["bar"] for b in v["bounds"]] and in_box else ["11314 是分界或不在框里"])
    cell("⑤ 段类型按线上读法 B（spec D3，server.TREND_READING）", [] if v["reading"] == "B" and [s["type"] for s in v["segments"]] == TYPES["zec15.json"]
         else ["读法 %s 段类型 %s" % (v["reading"], [s["type"] for s in v["segments"]])])
    cell("④ 不看未来（zec15：最早能确立那一根起，之后一直在、不变）", no_future())
    print("全部通过" if not bad else "%d 处不过" % len(bad))
    return 1 if bad else 0


def self_test():
    """spec §四：P1 不重算 ⇒ zec15 3 个；P2 不交替 ⇒ 撤回 20；P5 不查空段 ⇒ 7 个。各自必须变。"""
    _, base = run("zec15.json")
    arms = [("P1 拿掉 D2-4（不重算中枢）", dict(regroup=False), lambda v: len(v["bounds"]) != len(base["bounds"])),
            ("P2 拿掉 D2-3（不交替）", dict(alternate=False), lambda v: len(v["retracted"]) != len(base["retracted"])),
            ("P5 拿掉 D2-7（空段照切）", dict(check_empty=False), lambda v: len(v["bounds"]) != len(base["bounds"])),
            ("D3 换回读法 A（⑤ 那一格必须看得见）", dict(reading="A"),
             lambda v: [s["type"] for s in v["segments"]] != [s["type"] for s in base["segments"]])]
    miss = 0
    # P3（「H 之后价格不再过 H」，按段内 hi／lo）。card-753bd03a（L78 待定改判）以后 zec_1h 第 8 段拆开了，原来那颗牙
    # （zec_1h 不交替 1 刀 1 撤 ↔ 0 刀 3 撤）没了；现在默认规则下 zec15 就咬得到：留着 5 刀，拿掉 7 刀。
    _, b3 = run("zec15.json", no_exceed=False)
    ok = len(b3["bounds"]) != len(base["bounds"])
    print("%s P3 拿掉「H 之后不再过 H」（zec15）⇒ 分界 %d、撤回 %d（留着 %d、%d）" % (
        "✓" if ok else "✗", len(b3["bounds"]), len(b3["retracted"]), len(base["bounds"]), len(base["retracted"])))
    miss += not ok
    # D4-1 的反向验证（原 cut_check --self-test 挪来）：重算中枢时不按刀分组 ⇒ ② 必须报出跨分界的框
    real = T._centers_with_cuts
    T._centers_with_cuts = lambda done, ks: real(done, [])
    try:
        cross = [x for x in invariants("zec15.json") if "跨过分界" in x]
    finally:
        T._centers_with_cuts = real
    ok = bool(cross)
    print("%s D4 拿掉「按刀分组」⇒ ② 报出跨分界的框 %d 个（例 %s）" % ("✓" if ok else "✗", len(cross), cross[:1]))
    miss += not ok
    for name, kw, changed in arms:
        _, v = run("zec15.json", **kw)
        ok = changed(v)
        print("%s %s ⇒ 分界 %d、撤回 %d（原样 %d、%d）" % ("✓" if ok else "✗", name, len(v["bounds"]),
              len(v["retracted"]), len(base["bounds"]), len(base["retracted"])))
        miss += not ok
    return 3 if miss else 0


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else main())
