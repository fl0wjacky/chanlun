#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""线段「已确认段只增不撤」检查：每份 K 线样本，笔序列逐笔加长，build_segments 的已确认段必须只往后长、不撤销。

    python3 tools/seg_prefix_check.py             # data/ 下全部样本，撤销数必须为 0（rc=0）
    python3 tools/seg_prefix_check.py --self-test # 反向验证：喂一个故意会撤销的划段函数，必须报出来（rc=0 ＝ 报出来了）

为什么要它（card-753bd03a，Nova 10-06 定为合并条件）：
  · Pine 的 ③ 逐根续扫（chanlun.pine::zSegStep）押的就是这条 —— 已确认段一旦被后来的笔撤销，逐根版就跟整段版不一样；
  · L78 待定改判第一版把「反向线段走完」界在它最后一笔（应为被确认那一笔），其余检查全绿，
    只有这条在 zec15 第 836 笔报了一次撤销 —— 那一版还据此误报了 1h 的分界变化。
main 0760562 上全部样本撤销 0。
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
from core.analyze import analyze                              # noqa: E402
from core.segment import build_segments                       # noqa: E402
from trend_check import load, kline_files                     # noqa: E402
from config import tick_of                                    # noqa: E402


def revocations(pens, build=build_segments):
    """→ [(第几笔加进来时, 被撤销的段 (PI0, PI1))]"""
    out, prev = [], []
    for n in range(3, len(pens) + 1):
        cur = [(s["PI0"], s["PI1"]) for s in build(pens[:n]) if not s.get("live")]
        if cur[:len(prev)] != prev:
            k = next((t for t, (a, b) in enumerate(zip(prev, cur)) if a != b), len(cur))
            out.append((n, prev[k]))
        prev = cur
    return out


def main():
    bad = 0
    for fn in kline_files():
        pens = analyze(load(os.path.join(ROOT, "data", fn)), tick=tick_of(fn))["pens"]
        rv = revocations(pens)
        bad += len(rv)
        print("%s %s %d 笔 撤销 %d %s" % ("✓" if not rv else "✗", fn, len(pens), len(rv), rv[:2] if rv else ""))
    for fn in ("aaplusdt_1h_headdir.json", "zecusdt_4h_headext.json"):   # 图头那两条修法的线上夹具（card-24dd71cb／card-2783fa1f）
        bars = json.load(open(os.path.join(HERE, "fixtures", fn)))
        pens = analyze([dict(t=b["t"], o=b["o"], h=b["h"], l=b["l"], c=b["c"]) for b in bars], tick=tick_of(fn))["pens"]
        rv = revocations(pens)
        bad += len(rv)
        print("%s fixtures/%s %d 笔 撤销 %d %s" % ("✓" if not rv else "✗", fn, len(pens), len(rv), rv[:2] if rv else ""))
    fz = json.load(open(os.path.join(HERE, "fixtures", "headfuzz_pens.json")))["seeds"]   # 直接是笔（Atlas 的随机反例）
    for sd, pens in fz.items():
        rv = revocations(pens)
        bad += len(rv)
        print("%s fixtures/headfuzz_pens.json seed %s %d 笔 撤销 %d %s" % ("✓" if not rv else "✗", sd, len(pens), len(rv), rv[:2] if rv else ""))
    print("全部通过（已确认段只增不撤）" if not bad else "%d 处撤销" % bad)
    return 1 if bad else 0


def self_test():
    """反向验证：一个「笔数是 7 的倍数时把最后一个已确认段扔掉」的划段函数 ⇒ 必须报撤销。"""
    def flaky(pens):
        segs = build_segments(pens)
        done = [s for s in segs if not s.get("live")]
        return done[:-1] if done and len(pens) % 7 == 0 else segs
    fn = "zec_1h.json"
    pens = analyze(load(os.path.join(ROOT, "data", fn)), tick=tick_of(fn))["pens"]
    rv = revocations(pens, flaky)
    print("%s 故意撤销的划段函数（%s）⇒ 报出 %d 处" % ("✓" if rv else "✗", fn, len(rv)))
    # 图头那一条拿掉 cutoff（判 ① 型等到反向段确认）⇒ Atlas 的两组随机反例必须报撤回（card-2783fa1f-da8）
    import core.segment as SG
    fz = json.load(open(os.path.join(HERE, "fixtures", "headfuzz_pens.json")))["seeds"]
    SG.HEAD_EXT_CUTOFF = False
    try:
        rv2 = {sd: len(revocations(p)) for sd, p in fz.items()}
    finally:
        SG.HEAD_EXT_CUTOFF = True
    ok2 = all(rv2.values())
    print("%s 图头那一条不设 cutoff ⇒ 随机反例撤回 %s" % ("✓" if ok2 else "✗", rv2))
    return 0 if rv and ok2 else 3


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else main())
