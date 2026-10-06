#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""级别联动（web/levels.py，card-6e338490）对 spec 的实例：docs/spec/级别联动.md §二 2（15m 合成框 vs 1h 线段中枢）
和 §四 第 4 项（L-7 起点）。夹具是 data/ 里冻结的 ZEC，跟 spec 量的是同一份。

    python3 tools/levels_check.py              # rc=0 全对 ／ 1 有一格不对
    python3 tools/levels_check.py --self-test  # 反向臂：每条判据各拧坏一处，必须红；红不了 ⇒ rc=1

★ 「没量到」一律 unmeasured：对照图没有、窗口没盖住都不许默认成 match（Nova 10-06）。
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [ROOT, os.path.join(ROOT, "web"), HERE]
from core.analyze import analyze                              # noqa: E402
from core.trend import trend_v3                               # noqa: E402
from config import tick_of                                    # noqa: E402
import levels as LV                                           # noqa: E402

M = 60_000
TFS = {"15m": 15 * M, "30m": 30 * M, "1h": 60 * M, "2h": 120 * M, "4h": 240 * M}
FILES = {"15m": "zec15.json", "30m": "zec30_cut.json", "1h": "zec_1h.json", "2h": "zec_2h.json", "4h": "zec_4h.json"}

# §二 2：15m 五个合成框 → (status, {对照图中枢序号: 占比})；占比容 ±1（spec 按开盘时刻量、这里含最后一根的时长）
# 第 1 个：27% 在 1h #1、其余 73% 在 1h 第一个中枢之前 ⇒ partial（Nova 10-06 定的第四种状态，不算分歧）
UNITS_15_VS_1H = [("partial", {1: 27}), ("mismatch", {1: 63, 2: 14}), ("match", {2: 100}),
                  ("match", {2: 100}), ("mismatch", {2: 72, 3: 22})]
# §四 第 4 项（L-7）：各图对 15m 的起点
START = {"30m": "window", "1h": "differs", "2h": "same", "4h": "differs"}


def view(tf):
    fn = FILES[tf]
    raw = json.load(open(os.path.join(ROOT, "data", fn)))
    bars = raw["bars"] if isinstance(raw, dict) else raw
    bars = [dict(t=b["t"], o=b["o"], h=b["h"], l=b["l"], c=b["c"]) for b in bars]
    v = trend_v3(analyze(bars, tick=tick_of(fn)), reading="B")
    return dict(t=[b["t"] for b in bars], step=TFS[tf], bounds=v["bounds"], centers=v["seg_centers"], units=v["units"])


def run(V):
    bad = []
    if LV.finest_tf(TFS) != "15m":
        bad.append("最细周期 %s ≠ 15m" % LV.finest_tf(TFS))
    want_ref = {"15m": "1h", "30m": "2h", "1h": "4h", "2h": None, "4h": None}      # L-8：× 4
    got_ref = {tf: LV.ref_tf(tf, TFS) for tf in TFS}
    if got_ref != want_ref:
        bad.append("对照周期 %s ≠ %s" % (got_ref, want_ref))
    links = LV.unit_links(V["15m"], V["1h"])
    if len(links) != len(UNITS_15_VS_1H):
        bad.append("15m 合成框 %d 个 ≠ spec 的 %d 个" % (len(links), len(UNITS_15_VS_1H)))
    for k, (got, (st, sh)) in enumerate(zip(links, UNITS_15_VS_1H), 1):
        g = {s["i"]: s["pct"] for s in got["share"]}
        if got["status"] != st or set(g) != set(sh) or any(abs(g[i] - sh[i]) > 1 for i in sh):
            bad.append("15m 第 %d 个合成框：%s ≠ spec %s %s" % (k, got, st, sh))
    for tf, st in START.items():
        s = LV.start_link(V[tf], V["15m"], TFS[tf])
        if s["status"] != st:
            bad.append("%s 起点 %s ≠ spec %s（%s）" % (tf, s["status"], st, s))
    # 边界：15m 框正好铺满一个 1h 中枢（同起同止）⇒ 100% match。区间少算最后一根的时长就会量成 80%（线上 30m 实测出过 99.x%）
    h = dict(t=[i * 15 * M for i in range(16)], step=15 * M, bounds=[], centers=[], units=[{"X0": 0, "X1": 15}])
    r = dict(t=[i * 60 * M for i in range(4)], step=60 * M, bounds=[], centers=[{"X0": 0, "X1": 3}], units=[])
    e = LV.unit_links(h, r)[0]
    if e["status"] != "match" or e["share"] != [{"i": 1, "pct": 100}]:
        bad.append("正好铺满一个对照中枢的框没判成 100%% match：%s" % e)
    # 没量到：对照图没有 ⇒ 全 unmeasured；最细图没有 ⇒ unmeasured；对照窗口没盖住 ⇒ unmeasured
    if any(u["status"] != "unmeasured" for u in LV.unit_links(V["15m"], None)):
        bad.append("没有对照图却没写 unmeasured")
    if LV.start_link(V["1h"], None, TFS["1h"])["status"] != "unmeasured":
        bad.append("没有最细图却没写 unmeasured")
    short = dict(V["1h"], t=V["1h"]["t"][len(V["1h"]["t"]) // 2:])          # 对照图只剩后半段
    short_c = [c for c in V["1h"]["centers"] if c["X0"] >= len(V["1h"]["t"]) // 2]
    short = dict(short, centers=[dict(c, X0=c["X0"] - len(V["1h"]["t"]) // 2, X1=c["X1"] - len(V["1h"]["t"]) // 2)
                                 for c in short_c])
    if LV.unit_links(V["15m"], short)[0]["status"] != "unmeasured":
        bad.append("对照图窗口没盖住第一个框却没写 unmeasured")
    return bad


def main():
    V = {tf: view(tf) for tf in TFS}
    bad = run(V)
    if "--self-test" not in sys.argv:
        for b in bad:
            print("✗", b)
        print("全对" if not bad else "%d 处不对" % len(bad))
        return 1 if bad else 0
    if bad:
        print("原样就不对，反向臂没意义：", bad[:2])
        return 1
    arms = []
    span0 = LV._span
    LV._span = lambda v, a, b: (v["t"][a], v["t"][b])                          # 拿掉「最后一根的时长」
    arms.append(("区间不含最后一根", run(V)))
    LV._span = span0
    pct0 = LV.MATCH_PCT
    LV.MATCH_PCT = 50                                                            # 换成跟 spec 实例打架的 50%
    arms.append(("门槛 50%", run(V)))
    LV.MATCH_PCT = pct0
    ul0 = LV.unit_links
    LV.unit_links = lambda h, r: [{"status": "match", "share": []} for _ in h["units"]] if r is None else ul0(h, r)
    arms.append(("没对照图默认 match", run(V)))
    LV.unit_links = ul0
    src = LV.unit_links
    LV.unit_links = lambda h, r: [dict(u, status="mismatch") if u["status"] == "partial" else u for u in src(h, r)]
    arms.append(("partial 并回 mismatch", run(V)))
    LV.unit_links = src
    mult0 = LV.REF_MULT
    LV.REF_MULT = 2                                                              # 对照取下一档
    arms.append(("对照取下一档", run(V)))
    LV.REF_MULT = mult0
    rc = 0
    for name, b in arms:
        print(("✓ 红了" if b else "✗ 没红") + "：" + name + ("（%s）" % b[0] if b else ""))
        rc |= not b
    return rc


if __name__ == "__main__":
    sys.exit(main())
