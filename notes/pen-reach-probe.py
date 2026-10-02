# -*- coding: utf-8 -*-
"""量一件事，用来决定第②步（笔逐根）该怎么做：

**加一根K线之后，`build_pens` 的结果从第几条笔开始变？**

`core/pen.py` 的 `fix_start` 会往回改（`seq[:] = seq[:j+1] + [P]`，j 可以到 0），
它自己还会重喂一段分型。所以"笔逐根"能不能做成"只动尾巴"，不是看代码长得像不像，
而是看这个回溯深度**实际有多远**。

  回溯 = 0 条旧笔被改  ⇒ 只追加，状态机只动尾巴
  回溯小（几条）        ⇒ 「检查点 + 重喂最后一个分型」够用
  回溯能到很远          ⇒ 增量省不了多少，得换方案（或老实说这步做不动）

★ 这个探针**只量**，不判对错。它不改任何代码。
用法：python3 notes/pen-reach-probe.py [--step N] [--max-bars N]
"""
import argparse
import importlib.util
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from core.kline import standardize, fractals, quantize          # noqa: E402
from core.pen import build_pens                                 # noqa: E402

try:
    from config import tick_of
except Exception:                                               # noqa: BLE001
    tick_of = lambda fn: None                                   # noqa: E731


def load(fn):
    bars = json.load(io.open(os.path.join(ROOT, "data", fn), encoding="utf-8"))
    if isinstance(bars, dict):
        bars = bars.get("bars") or bars.get("klines") or bars
    return bars


def key_pen(p):
    return (p["i0"], p["i1"], p["p0"], p["p1"])


def probe(fn, step=1, max_bars=None, rule="old"):
    bars = load(fn)
    if max_bars:
        bars = bars[:max_bars]
    tick = None
    try:
        tick = tick_of(fn)
    except Exception:                                           # noqa: BLE001
        pass
    prev, reaches, changed_at, npens = None, [], 0, []
    for k in range(len(bars)):
        std = standardize(quantize(bars[:k + 1], tick))
        fx = fractals(std)
        pens, _seq = build_pens(fx, std, rule, 4)
        if prev is not None and ((k + 1) % step == 0):
            npens.append(len(pens))
            c = 0
            while c < min(len(pens), len(prev)) and key_pen(pens[c]) == key_pen(prev[c]):
                c += 1
            if c < len(prev):                                   # 有旧笔被动过
                reaches.append(len(prev) - c)
                changed_at += 1
        prev = pens
    return reaches, changed_at, npens


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", type=int, default=1)
    ap.add_argument("--max-bars", type=int, default=None)
    a = ap.parse_args()

    # 与 pine-incremental-parity.py 同一份跳过清单：data/ 里还有几份不是K线序列的文件
    # （annot_* 是标注、mag_* 是别的结构、*_sub* 是片段），拿它们跑会抛类型错。
    skip = ("annot", "mag", "sub")
    files = [f for f in sorted(os.listdir(os.path.join(ROOT, "data")))
             if f.endswith(".json") and not any(x in f for x in skip)]
    print("回溯深度 = 「加一根之后，被改动／作废的旧笔条数」")
    print("  step=%d  max_bars=%s\n" % (a.step, a.max_bars))
    print("  %-22s %8s %8s | %s" % ("数据", "笔数", "有改动次数", "回溯分布（深度:次数）"))
    allr = []
    for fn in files:
        try:
            reaches, nchg, npens = probe(fn, a.step, a.max_bars)
        except Exception as e:                                  # noqa: BLE001
            print("  %-22s 跑不动：%s: %s" % (fn, type(e).__name__, e))
            continue
        allr.extend(reaches)
        dist = {}
        for r in reaches:
            dist[r] = dist.get(r, 0) + 1
        top = sorted(dist.items(), key=lambda kv: -kv[1])[:8]
        s = "  ".join("%d:%d" % (d, c) for d, c in sorted(top))
        print("  %-22s %8s %8d | %s%s" % (fn, max(npens) if npens else "-", nchg, s,
                                          "" if len(dist) <= 8 else "  …共 %d 种" % len(dist)))
    if allr:
        allr.sort()
        n = len(allr)
        def q(p):
            return allr[min(n - 1, int(p * n))]
        print("\n  合计 %d 次改动 ｜ 回溯 中位 %d ｜ p90 %d ｜ p99 %d ｜ 最大 %d"
              % (n, q(0.5), q(0.9), q(0.99), allr[-1]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
