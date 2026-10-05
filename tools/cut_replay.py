#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""中枢切分逐根重放（docs/spec/中枢切分.md 第三节第 2 条）：每一刀从出现到切成晚多少根、多少刀作废、多少刀切成后被撤回。
口径跟 tools/backtest.py 的重放一样：第 t 步只喂 bars[:t+1]。刀的键 = 切点那根的时间戳（落在线段端点上）。

    python3 tools/cut_replay.py <bars.json> [--measure macd] [--warm 200]
"""
import argparse, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from core.analyze import analyze                              # noqa: E402
import core.signals                                           # noqa: E402,F401
from core.cut import cut_centers                              # noqa: E402
S = sys.modules["core.signals"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bars"); ap.add_argument("--measure", default="macd"); ap.add_argument("--warm", type=int, default=200)
    ap.add_argument("--tick", type=float, default=None)
    a = ap.parse_args()
    raw = json.load(open(a.bars)); raw = raw["bars"] if isinstance(raw, dict) else raw
    bars = [dict(t=b["t"], o=b["o"], h=b["h"], l=b["l"], c=b["c"]) for b in raw]
    seen, done_at, void_at, last = {}, {}, {}, {}
    retracted = set()
    for t in range(a.warm, len(bars)):
        r = analyze(bars[:t + 1], tick=a.tick)
        _, cuts = cut_centers(r, S.signals(r, "pen", a.measure))
        now = {}
        for c in cuts:
            k = bars[c["cut_bar"]]["t"]
            now[k] = c["status"]
            seen.setdefault(k, t)
            if c["status"] == "done":
                done_at.setdefault(k, t)
            if c["status"] == "void":
                void_at.setdefault(k, t)
        for k, st in last.items():                         # 上一根还是 done、这一根没了或不是 done ⇒ 切成后撤回
            if st == "done" and now.get(k) != "done":
                retracted.add(k)
        last = now
    lag = [done_at[k] - seen[k] for k in done_at]
    fin = last
    print("刀（出现过的）%d · 最后还在 %d" % (len(seen), len(fin)))
    print("切成过 %d · 平均从出现到切成 %.1f 根（中位 %s）" % (len(done_at), sum(lag) / max(1, len(lag)),
          sorted(lag)[len(lag) // 2] if lag else "-"))
    print("作废过 %d · 切成后被撤回 %d · 出现过后来整刀消失 %d" % (len(void_at), len(retracted), len(set(seen) - set(fin))))
    print("终版：", {s: sum(1 for v in fin.values() if v == s) for s in ("done", "pending", "void")})


if __name__ == "__main__":
    main()
