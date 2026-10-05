#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""中枢切分逐根重放（docs/spec/中枢切分.md 第三节第 2 条）：每一刀从出现到切成晚多少根、多少刀作废、多少刀切成后被撤回。
口径跟 tools/backtest.py 的重放一样：第 t 步只喂 bars[:t+1]。

刀的键 = 切点那根的时间戳（落在线段端点上）。线段一重划、切点挪一个端点，会被记成「旧刀消失 + 新刀出现」，所以
「整刀消失」再按认它的笔层点（signal_bar 时间戳 + kind）拆两类（Atlas 10-05）：
  · 点真没了：最后一次见这把刀时认它的那些点，终版里一个都不在了；
  · 切点挪了：点还在，只是终版里它认出的是别的切点。

    python3 tools/cut_replay.py <bars.json> [--measure macd] [--warm 200] [--tick 0.01]
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from core.analyze import analyze                              # noqa: E402
import core.signals                                           # noqa: E402,F401
from core.cut import cut_centers                              # noqa: E402
S = sys.modules["core.signals"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bars")
    ap.add_argument("--measure", default="macd")
    ap.add_argument("--warm", type=int, default=200)
    ap.add_argument("--tick", type=float, default=None)
    a = ap.parse_args()
    raw = json.load(open(a.bars))
    raw = raw["bars"] if isinstance(raw, dict) else raw
    bars = [dict(t=b["t"], o=b["o"], h=b["h"], l=b["l"], c=b["c"]) for b in raw]
    seen, done_at, void_at, last = {}, {}, {}, {}
    retracted, cut_sigs = set(), {}                      # cut_sigs[刀] = 最后一次见它时认它的那些笔层点
    sig_now = {}
    for t in range(a.warm, len(bars)):
        r = analyze(bars[:t + 1], tick=a.tick)
        _, cuts = cut_centers(r, S.signals(r, "pen", a.measure))
        now, sig_now = {}, {}
        for c in cuts:
            k = bars[c["cut_bar"]]["t"]
            now[k] = c["status"]
            seen.setdefault(k, t)
            if c["status"] == "done":
                done_at.setdefault(k, t)
            if c["status"] == "void":
                void_at.setdefault(k, t)
        pen_sig = [g for g in S.signals(r, "pen", a.measure) if g["confirmed"]]
        for c in cuts:                                   # 认这把刀的点：落在这把刀上的那些（cut_centers 只留了最早那个，这里全收）
            cut_sigs[bars[c["cut_bar"]]["t"]] = set()
        from core.cut import _turn_bar, _snap, TURN_KINDS
        done = [s for s in r["segs"] if not s.get("live")]
        if done:
            ends = [done[0]["i0"]] + [s["i1"] for s in done]
            for g in pen_sig:
                if g["kind"] not in TURN_KINDS:
                    continue
                kk = _snap(_turn_bar(g, r["pens"]), ends)
                if kk == 0:
                    continue
                ck, sk = bars[ends[kk]]["t"], (bars[g["bar"]]["t"], g["kind"])
                sig_now[sk] = ck
                if ck in cut_sigs:
                    cut_sigs[ck].add(sk)
        for k, st in last.items():                       # 上一根还是 done、这一根没了或不是 done ⇒ 切成后撤回
            if st == "done" and now.get(k) != "done":
                retracted.add(k)
        last = now
    gone = set(seen) - set(last)
    dead = sum(1 for k in gone if not (cut_sigs.get(k, set()) & set(sig_now)))
    lag = sorted(done_at[k] - seen[k] for k in done_at)
    print("数据：%s · %d 根 · warm %d · measure %s" % (a.bars, len(bars), a.warm, a.measure))
    print("刀（出现过的）%d · 最后还在 %d" % (len(seen), len(last)))
    print("切成过 %d · 从出现到切成：平均 %.1f 根、中位 %s 根" % (
        len(done_at), sum(lag) / max(1, len(lag)), lag[len(lag) // 2] if lag else "-"))
    print("作废过 %d · 切成后被撤回 %d" % (len(void_at), len(retracted)))
    print("整刀消失 %d ＝ 认它的笔层点真没了 %d ＋ 点还在、切点挪到别的端点 %d" % (len(gone), dead, len(gone) - dead))
    print("终版：", {s: sum(1 for v in last.values() if v == s) for s in ("done", "pending", "void")})


if __name__ == "__main__":
    main()
