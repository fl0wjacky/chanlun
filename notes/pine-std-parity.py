#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pine 画标准化线段（D-3 C′，Nova 10-09 15:12 定 (b)）：把 chanlun.pine 的 stdSegs／stdMove／stdBest **逐行抄成 Python**，
跟引擎 `core.trend._done(r)`（网页 segs_std 就是它）逐前缀对账。

要回答的唯一问题：
    TradingView 上画的已完成线段（stdSegs），跟网页上画的（segs_std）在每个前缀上是不是同一套端点？

抄的时候照 Pine 的写法，不照 Python 的写法（Python 用 max(key=…)，Pine 用 while 加 >=）——
两种写法在「一样极取后一根」上要一致，这里正好核它。线段方向照 Pine：起笔 p1 > p0。

★ 证不了 Pine 本身（这台机器上编译不了、跑不了）；Pine 那几行要人逐行对着这里核。行号见 chanlun.pine stdSegs。

    python3 notes/pine-std-parity.py               # 6 份真实数据、每个笔端点前缀
    python3 notes/pine-std-parity.py --self-test   # 反向臂：① 不标准化（画原始线段）② 一样极取前一根 —— 都必须红
退出码：0 全对；1 有分歧；3 自检没红
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import core                                                          # noqa: E402,F401
import core.trend as T                                               # noqa: E402
from config import tick_of                                           # noqa: E402

A = sys.modules["core.analyze"]                                      # ★ 别写 import core.analyze as A：拿到的是函数
FILES = ["zec_1h.json", "zec_2h.json", "zec_4h.json", "btc_4h.json", "aaplusdt_1h.json", "aaplusdt_4h.json"]
ARM = None                                                           # 自检：None ／ "raw" ／ "tie_first"


def is_up(u):                                                        # Pine isUp(Unit u) => u.p1 > u.p0
    return u["p1"] > u["p0"]


def std_best(H, L, a, b, top):                                       # Pine stdBest
    j = a
    i = a + 1
    while i <= b:
        if ARM == "tie_first":
            better = H[i] > H[j] if top else L[i] < L[j]
        else:
            better = H[i] >= H[j] if top else L[i] <= L[j]
        if better:
            j = i
        i += 1
    return j


def std_move(piv, top, H, L, k, a, b):                               # Pine stdMove
    moved = False
    if a <= b:
        nb = std_best(H, L, a, b, top[k])
        if nb != piv[k]:
            piv[k] = nb
            moved = True
    return moved


def std_segs(done, P, H, L):                                         # Pine stdSegs
    out = []
    n = len(done)
    if n > 0:
        if ARM == "raw":
            return [(s["i0"], s["i1"], s["p0"], s["p1"]) for s in done]
        piv = [0] * (n + 1)
        top = [False] * (n + 1)
        piv[0] = done[0]["i0"]
        top[0] = not is_up(P[done[0]["PI0"]])
        for k in range(n):
            piv[k + 1] = done[k]["i1"]
            top[k + 1] = is_up(P[done[k]["PI0"]])
        lo0, hiN = done[0]["i0"], done[n - 1]["i1"]
        n_round, again = 0, n >= 2
        while again and n_round < n + 2:
            any_moved = False
            for k in range(1, n):                                    # Pine: for k = 1 to n - 1（n ≥ 2 才进来，不会倒着数）
                if std_move(piv, top, H, L, k, piv[k - 1] + 1, piv[k + 1] - 1):
                    any_moved = True
            again = any_moved
            n_round += 1
        std_move(piv, top, H, L, 0, lo0, piv[1] - 1)
        std_move(piv, top, H, L, n, piv[n - 1] + 1, hiN)
        for k in range(n):
            i0, i1 = piv[k], piv[k + 1]
            out.append((i0, i1, H[i0] if top[k] else L[i0], H[i1] if top[k + 1] else L[i1]))
    return out


def synthetic(quiet=False, n_cases=300):
    """真实行情上接点区间里几乎碰不到两根一样高（6 份数据「一样极取前一根」的变异一处都不红），所以另造：
    价格只取 5 个档位（到处是平手），线段方向交替，直接对 core.trend._standardize。"""
    import random
    rng = random.Random(20261009)
    for case in range(n_cases):
        nseg = rng.randint(1, 7)
        cuts = sorted(rng.sample(range(1, 6 * nseg + 6), nseg - 1)) if nseg > 1 else []
        nb = (cuts[-1] if cuts else 0) + rng.randint(2, 6)
        bounds = [0] + cuts + [nb - 1]
        bars = []
        for i in range(nb):
            lo = rng.randint(0, 3)
            bars.append(dict(h=float(lo + rng.randint(1, 2)), l=float(lo)))
        up0 = rng.random() < 0.5
        done, P = [], []
        for k in range(nseg):
            up = up0 if k % 2 == 0 else not up0
            i0, i1 = bounds[k], bounds[k + 1]
            done.append(dict(i0=i0, i1=i1, dir="up" if up else "down", PI0=k, PI1=k,
                             p0=bars[i0]["l"] if up else bars[i0]["h"], p1=bars[i1]["h"] if up else bars[i1]["l"]))
            P.append(dict(p0=0.0, p1=1.0 if up else -1.0))
        H = [b["h"] for b in bars]
        L = [b["l"] for b in bars]
        got = std_segs(done, P, H, L)
        want = [(x["i0"], x["i1"], x["p0"], x["p1"]) for x in T._standardize(done, bars)]
        if got != want:
            if not quiet:
                print("✗ 造的第 %d 例（%d 段）：Pine 抄本 %s ≠ 引擎 %s" % (case, nseg, got, want))
            return 1
    if not quiet:
        print("✓ 造的 %d 例（价格只有 5 档，平手到处是）" % n_cases)
    return 0


def run(quiet=False):
    bad = synthetic(quiet)
    for fn in FILES:
        bars = json.load(open(os.path.join(ROOT, "data", fn)))
        bars = bars["bars"] if isinstance(bars, dict) else bars
        tick = tick_of(fn)
        full = A.analyze(bars, tick=tick)
        cuts = sorted({p["i1"] + 1 for p in full["pens"]} | {len(bars)})
        H = [b["h"] for b in bars]                                   # Pine zRH／zRL：原始高低，下标 ＝ 原始下标
        L = [b["l"] for b in bars]
        n_chk = 0
        for c in cuts:
            r = A.analyze(bars[:c], tick=tick)
            done = [s for s in r["segs"] if not s.get("live")]
            P = r["pens"][:-1] if A.SEG_FINAL_PENS and len(r["pens"]) > 1 else r["pens"]   # Pine segPens
            got = std_segs(done, P, H, L)
            want = [(s["i0"], s["i1"], s["p0"], s["p1"]) for s in T._done(r)]
            n_chk += 1
            if got != want:
                bad += 1
                if not quiet:
                    diff = next(k for k, (g, w) in enumerate(zip(got + [None] * 9, want + [None] * 9)) if g != w)
                    print("✗ %s 前缀 %d：第 %d 条 Pine 抄本 %s ≠ 引擎 %s" % (fn, c, diff, got[diff:diff + 1], want[diff:diff + 1]))
                break
        if not quiet:
            print("%s %s：%d 个前缀" % ("✓" if not bad else "·", fn, n_chk))
    if not quiet:
        print("全对" if not bad else "%d 份有分歧" % bad)
    return bad


def self_test():
    global ARM
    rc = 0
    for arm, name in (("raw", "不标准化（TradingView 画原始线段）"), ("tie_first", "一样极取前一根")):
        ARM = arm
        try:
            n = run(quiet=True)
        finally:
            ARM = None
        print("%s 变异「%s」⇒ %d 份分歧" % ("✓" if n else "✗", name, n))
        rc |= 0 if n else 3
    return rc


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv[1:] else (1 if run() else 0))
