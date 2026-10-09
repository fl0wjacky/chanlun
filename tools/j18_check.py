#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""J18：任何高级别的改变都必须先从低级别开始（级别联动.md 七 J18 ＋『编者口径』检查项，Nova 10-08 定）。**只报警，不改图。**

    python3 tools/j18_check.py              # 印每一刀的判定；rc 恒为 0（只报警）
    python3 tools/j18_check.py --self-test  # 反向臂：拧坏一处，违反必须报出来；报不出 ⇒ rc=1

比法（spec 原样）：
  - 比**时间周期之间**：同一份 K 线（data/ 冻结夹具）聚合出两个周期，小的那个是原样、大的那个按整点对齐聚合。
  - 时刻取大周期那个分界**实时确立的那一根 c**（最早一个截断长度：截到 c 为止就有这一刀；之后一直在，见 trend_check ④）。
    两级都只用到 c 那根大 K 线收盘为止的数据（小周期取收盘不晚于它的那些根）。
  - 判法（Nova 10-08 09:22 定，级别联动.md 七 J18『编者口径』；大周期在 c 确立 L、极值在大 K 线 E 上为例，H 反过来）：
      小周期（只用到 c 收盘的数据）在 E 那根大 K 线的时间范围里**有一个已确立的 L** ⇒ 通过；
      没有已确立的、但**待定的 L 候选落在 E 里** ⇒ 『中阴』，单独报、不算违反；
      大周期这一刀是它自己的第一刀（图头，want 两头开）⇒ 『图头』，单独报、不算违反；
      其余 ⇒ **违反**（大周期在 E 转了，小周期在 E 上既没确立也没待定同向的转折）。
    ★ 为什么不用作废的原写法「c 时刻小周期最后一个分界」：D2-6 下，最后一个是 H 时**几乎总有** L 候选（H 之后的最低点），
      『中阴』兜住了一切 ⇒ 把小周期整段上下翻转都报 0 处违反，断言没牙。小周期在 E 之后又反向确立，也不算违反：
      大周期确立很晚（c 比 E 晚几十到上千根），这期间小周期早就走到下一段了，L102 说的是「先后」，不是 c 那一刻的状态。
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [ROOT, HERE]
from core.analyze import analyze                              # noqa: E402
from core.trend import trend_v3                               # noqa: E402
from config import tick_of                                    # noqa: E402

M = 60_000
# (夹具, 小周期毫秒, 大周期毫秒)：小周期是夹具本身，大周期由它聚合
PAIRS = [("zec15.json", 15 * M, 60 * M), ("zec15.json", 15 * M, 30 * M), ("zec_1h.json", 60 * M, 240 * M)]


def load(fn):
    raw = json.load(open(os.path.join(ROOT, "data", fn)))
    raw = raw["bars"] if isinstance(raw, dict) else raw
    return [dict(t=b["t"], o=b["o"], h=b["h"], l=b["l"], c=b["c"]) for b in raw]


def aggregate(bars, step):
    """按 t // step 整点对齐聚合；只收**齐了的**桶（最后一桶不齐就丢，免得大周期最后一根是半根）。"""
    out, k = [], None
    for b in bars:
        key = b["t"] // step
        if key != k:
            out.append(dict(t=key * step, o=b["o"], h=b["h"], l=b["l"], c=b["c"], n=1))
            k = key
        else:
            o = out[-1]
            o["h"], o["l"], o["c"], o["n"] = max(o["h"], b["h"]), min(o["l"], b["l"]), b["c"], o["n"] + 1
    return out


def _trend(bars, fn):
    return trend_v3(analyze([dict(t=b["t"], o=b["o"], h=b["h"], l=b["l"], c=b["c"]) for b in bars], tick=tick_of(fn)), reading="A")


def _sl():
    import core.trend as T
    return bool(T.SAME_LEVEL)


def _has(v, kind, bar):
    """老路：这一刀出现了。同级别（Nova 10-09 13:09 选 (a)，spec 级别联动 J18 Atlas 14d231b）：这把 D2 **已确认**
    （①D 的确认条件，小栋认过）——同级别的刀一画出来就在，只是 state=pending，拿「出现」当确立时刻会早得没意义。"""
    if _sl():
        return any(b["kind"] == kind and b["bar"] == bar and b["rule"] == "D2-2" and b.get("state") == "confirmed" for b in v["bounds"])
    return any(b["kind"] == kind and b["bar"] == bar for b in v["bounds"])


def confirm_at(big, fn, kind, bar, lo, hi):
    """最早的截断长度 n（big[:n]）使这一刀出现 → c ＝ n-1。
    先二分（前提是「确立后一直在」，trend_check ④ 守的就是这条，但它只量 zec15）；二分完**核两头**：
    big[:n] 有、big[:n-1] 没有。核不过（这份数据上不单调）⇒ 退回从 lo 起逐根往后找第一次出现。"""
    a, b = lo, hi                                             # 不变量：big[:b] 有、big[:a] 没有
    while b - a > 1:
        m = (a + b) // 2
        if _has(_trend(big[:m], fn), kind, bar):
            b = m
        else:
            a = m
    if _has(_trend(big[:b], fn), kind, bar) and not _has(_trend(big[:b - 1], fn), kind, bar):
        return b - 1
    for n in range(lo + 1, hi + 1):                           # 不单调：逐根找第一次出现（慢，但不会给错的 c）
        if _has(_trend(big[:n], fn), kind, bar):
            return n - 1
    return hi - 1

def check_pair(fn, fstep, bstep, small=None):
    """→ [dict(big_kind, big_bar, big_price, c, t_c, verdict, small_last, small_pending)]。small 可替换（self-test 用）。"""
    small = small if small is not None else load(fn)
    big = aggregate(small, bstep)
    if big and big[-1]["n"] * fstep < bstep:
        big = big[:-1]
    vb = _trend(big, fn)
    sl = _sl()
    # 同级别：大周期只看 D2（J18 说的是走势转折；S5 是 D2 之间的接缝），而且只看全图里已确认的（待确认的还没「确立」）。
    #   确立时刻从刀所在那根往后找（同级别的刀没有老路的 pullback_end_bar）
    big_cuts = [b for b in vb["bounds"] if b["rule"] == "D2-2" and b.get("state") == "confirmed"] if sl else vb["bounds"]
    out = []
    for k, bd in enumerate(big_cuts):
        c = confirm_at(big, fn, bd["kind"], bd["bar"], bd["bar"] if sl else bd["pullback_end_bar"], len(big))
        t_end = big[c]["t"] + bstep                          # c 那根大 K 线收盘
        t0 = big[bd["bar"]]["t"]
        t1 = t0 + bstep                                      # E ＝ 极值那根大 K 线覆盖的时间
        sm = [b for b in small if b["t"] + fstep <= t_end]
        vs = _trend(sm, fn)
        inE = lambda x: t0 <= sm[x["bar"]]["t"] < t1
        if sl:
            # 小周期：E 里有已确认的同向 D2 ⇒ 通过；只有待确认的 D2、或同向的 S5 ⇒ 『中阴』（转折在，只是还没定）
            conf = [b for b in vs["bounds"] if b["kind"] == bd["kind"] and inE(b) and b["rule"] == "D2-2" and b.get("state") == "confirmed"]
            pend = [b for b in vs["bounds"] if b["kind"] == bd["kind"] and inE(b) and b not in conf] + \
                   [p for p in vs["pending"] if p["kind"] == bd["kind"] and inE(p)]   # 末尾候选（trend.pending）照老路也算
        else:
            conf = [b for b in vs["bounds"] if b["kind"] == bd["kind"] and inE(b)]
            pend = [p for p in vs["pending"] if p["kind"] == bd["kind"] and inE(p)]
        if conf:
            verdict = "通过"
        elif pend:
            verdict = "中阴"
        elif k == 0:
            verdict = "图头"
        else:
            verdict = "违反"
        out.append(dict(big_kind=bd["kind"], big_bar=bd["bar"], big_price=bd["price"], c=c, t_c=big[c]["t"], verdict=verdict,
                        small_last=vs["bounds"][-1]["kind"] if vs["bounds"] else None,
                        small_pending=[(p["kind"], round(p["price"], 2)) for p in vs["pending"]]))
    return out


def main(quiet=False):
    viol = 0
    for fn, fs, bs in PAIRS:
        res = check_pair(fn, fs, bs)
        n = {k: sum(1 for r in res if r["verdict"] == k) for k in ("通过", "中阴", "违反", "图头")}
        viol += n["违反"]
        if not quiet:
            print("%s %s %dm 对 %dm：大周期 %d 刀 —— 通过 %d ／ 中阴 %d ／ 违反 %d ／ 图头 %d" % (
                "⚠" if n["违反"] else "✓", fn, fs // M, bs // M, len(res), n["通过"], n["中阴"], n["违反"], n["图头"]))
            for r in res:
                if r["verdict"] != "通过":
                    print("    %s 大周期 %s %.2f（bar %d，确立 c=%d）⇒ 小周期最后分界 %s、待定 %s" % (
                        r["verdict"], r["big_kind"], r["big_price"], r["big_bar"], r["c"], r["small_last"], r["small_pending"]))
    return viol


def self_test():
    """反向臂：小周期的 K 线整段**上下翻转**（大周期照原样聚合）⇒ 小周期的转折全反 ⇒ 除图头外每一刀都得报违反。"""
    global aggregate
    miss = armed = 0
    real_agg = aggregate
    for fn, fs, bs in PAIRS:
        small = load(fn)
        top = max(b["h"] for b in small) + min(b["l"] for b in small)
        flipped = [dict(t=b["t"], o=top - b["o"], h=top - b["l"], l=top - b["h"], c=top - b["c"]) for b in small]
        big = real_agg(small, bs)
        aggregate = lambda bars, step: [dict(x) for x in big]
        try:
            res = check_pair(fn, fs, bs, small=flipped)
        finally:
            aggregate = real_agg
        body = [r for r in res if r["verdict"] != "图头"]
        nbad = sum(1 for r in body if r["verdict"] == "违反")
        if not body:                                     # 大周期只有图头那一刀 ⇒ 这一对量不出东西，不算过也不算不过
            print("· %s %dm 对 %dm：大周期除图头外没有刀，这一对翻转量不出（跳过）" % (fn, fs // M, bs // M))
            continue
        ok = nbad == len(body)
        miss += not ok
        armed += 1
        print("%s %s %dm 对 %dm：小周期上下翻转 ⇒ 违反 %d／%d（图头除外，要全报）" % ("✓" if ok else "✗", fn, fs // M, bs // M, nbad, len(body)))
    if not armed:
        print("✗ 没有一对量得出来（每对的大周期都只有图头）⇒ 反向臂空转")
    return 1 if miss or not armed else 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    main()
    sys.exit(0)
