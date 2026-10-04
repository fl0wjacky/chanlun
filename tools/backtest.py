#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""最小回测：拿历史 K 线检验买卖点（card-41383e15-d8f，小栋 10-04 ③A）。**骨架**，口径以 Atlas 的规则页为准。

    python3 tools/backtest.py [--data zec_4h.json,...] [--level seg|pen] [--measure macd]
                              [--fee-bps 4] [--slip-bps 2] [--out 表.json]
    python3 tools/backtest.py --probe     # 偷看探针：改成「按 bar 成交」结果必须变

卡上四条硬规则在这里怎么落：
  ① 下一根开盘成交：信号在第 t 根确认 ⇒ 第 t+1 根的开盘价成交，不按信号那根。
  ② 手续费、滑点是显式参数（单边，基点），报表头原样列出。买价 ×(1+滑点)、卖价 ×(1−滑点)，每边再扣手续费。
  ③ 不偷看未来：引擎的买卖点只有 bar（极值那根）和 confirmed 布尔，没有「哪一根确认的」。所以**逐根重放**：
     对每个 t 只喂 bars[:t+1] 跑 analyze + signals，某个点（键 = kind + 极值那根的时间戳）**第一次以
     confirmed=True 出现**的那个 t 就是确认时刻。之后它在更长的数据里被改掉 / 消失，照实记进 repaint 计数，
     已成交的不撤。
  ④ 只用已收盘的 K 线：data/ 里的都是历史收盘线；重放时第 t 步只看到 bars[:t+1]（第 t 根当作刚收盘）。

交易模型（暂定，等规则页）：只做多。买点（一买/二买/三买，含 weak）空仓时开多；卖点（一卖/二卖/三卖）持仓时平仓。
数据走完还持仓 ⇒ 按最后一根收盘价记一笔「未平」，单列。权益按每根收盘逐根盯市算最大回撤。

偷看探针（--probe）：同一份数据，改成「用全量数据的终版信号、在极值那根收盘成交」。这是偷看（一类点的极值那根
当时根本不知道是极值）。两种跑法的交易明细必须不同 —— 相同就说明重放没起作用，探针红。
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.analyze import analyze                              # noqa: E402
import core.signals                                           # noqa: E402,F401
ENG = sys.modules["core.signals"]                             # core/__init__ 把 signals 导成了函数，拿模块要这样

BUY, SELL = ("一买", "二买", "三买"), ("一卖", "二卖", "三卖")
DEFAULT_DATA = ("zec_4h.json", "zec_2h.json", "zec_1h.json", "btc_4h.json")


def load(fn):
    return json.load(open(os.path.join(ROOT, "data", fn), encoding="utf-8"))


def replay(bars, level, measure, warm=50):
    """逐根重放 → 确认事件列表 [dict(kind, t_extreme, confirm_i)]，按确认先后；外加 repaint 统计。"""
    first, events = {}, []
    for t in range(warm, len(bars)):
        r = analyze(bars[:t + 1])
        for g in ENG.signals(r, level, measure):
            if not g["confirmed"]:
                continue
            key = (g["kind"], bars[g["bar"]]["t"])
            if key not in first:
                first[key] = t
                events.append(dict(kind=g["kind"], t_extreme=key[1], bar=g["bar"], confirm_i=t, weak=g.get("weak")))
    final = {(g["kind"], bars[g["bar"]]["t"]) for g in ENG.signals(analyze(bars), level, measure) if g["confirmed"]}
    gone = sum(1 for k in first if k not in final)
    # 近邻对：同 kind、极值那根相距 ≤2 根的两个「不同点」—— 键按时间戳算是两个，可能其实是同一个点漂了。
    # 先只计数，判法等规则页（Atlas 10-04）。
    pos = {b["t"]: i for i, b in enumerate(bars)}
    keys = sorted(first, key=lambda k: (k[0], k[1]))
    near = sum(1 for x, y in zip(keys, keys[1:]) if x[0] == y[0] and abs(pos[y[1]] - pos[x[1]]) <= 2)
    return events, dict(confirmed_ever=len(first), gone_by_end=gone, near_pairs=near)


def peek_events(bars, level, measure):
    """偷看版：全量数据的终版已确认信号，当作在极值那根就知道了。"""
    out = []
    for g in ENG.signals(analyze(bars), level, measure):
        if g["confirmed"]:
            out.append(dict(kind=g["kind"], t_extreme=bars[g["bar"]]["t"], bar=g["bar"], confirm_i=g["bar"],
                            weak=g.get("weak")))
    return sorted(out, key=lambda e: e["confirm_i"])


def trade(bars, events, fee_bps, slip_bps, fill="next_open"):
    """events → 交易明细 + 逐根权益。fill=next_open：第 confirm_i+1 根开盘；fill=bar_close：第 confirm_i 根收盘（只给探针用）。"""
    fee, slip = fee_bps / 1e4, slip_bps / 1e4
    by_i = {}
    for e in events:
        i = e["confirm_i"] + 1 if fill == "next_open" else e["confirm_i"]
        if i < len(bars):
            by_i.setdefault(i, []).append(e)
    trades, pos, eq, curve = [], None, 1.0, []
    for i, b in enumerate(bars):
        px = b["o"] if fill == "next_open" else b["c"]
        for e in by_i.get(i, []):
            if pos is None and e["kind"] in BUY:
                pos = dict(entry_i=i, entry_t=b["t"], entry_px=px * (1 + slip), kind_in=e["kind"],
                           signal_t=e["t_extreme"], confirm_i=e["confirm_i"])
            elif pos is not None and e["kind"] in SELL:
                out_px = px * (1 - slip)
                ret = (out_px / pos["entry_px"]) * (1 - fee) ** 2 - 1
                eq *= 1 + ret
                trades.append(dict(pos, exit_i=i, exit_t=b["t"], exit_px=out_px, kind_out=e["kind"], ret=ret))
                pos = None
        mtm = eq * (b["c"] * (1 - slip) / pos["entry_px"] * (1 - fee) ** 2) if pos else eq
        curve.append(mtm)
    open_pos = None
    if pos:
        last = bars[-1]
        ret = (last["c"] * (1 - slip) / pos["entry_px"]) * (1 - fee) ** 2 - 1
        open_pos = dict(pos, exit_i=len(bars) - 1, exit_t=last["t"], exit_px=last["c"], kind_out="未平", ret=ret)
    return trades, open_pos, curve


def summary(trades, open_pos, curve):
    wins = sum(1 for x in trades if x["ret"] > 0)
    pnl = 1.0
    for x in trades:
        pnl *= 1 + x["ret"]
    peak, mdd = 0.0, 0.0
    for v in curve:
        peak = max(peak, v)
        mdd = max(mdd, 1 - v / peak if peak else 0)
    return dict(n=len(trades), win_rate=round(wins / len(trades), 4) if trades else None,
                pnl=round(pnl - 1, 6), max_dd=round(mdd, 6),
                open=round(open_pos["ret"], 6) if open_pos else None)


def run_one(fn, level, measure, fee_bps, slip_bps):
    bars = load(fn)
    events, rp = replay(bars, level, measure)
    trades, open_pos, curve = trade(bars, events, fee_bps, slip_bps)
    return dict(data=fn, bars=len(bars), level=level, measure=measure, events=len(events), repaint=rp,
                summary=summary(trades, open_pos, curve), trades=trades, open=open_pos)


def probe(fn, level, measure, fee_bps, slip_bps):
    """偷看探针，两条各自必须「变」：
      A 按 bar 成交：终版信号、极值那根收盘成交（卡上点名的那种偷看）；
      B 只换信号来源：终版信号当作极值那根就知道，成交照样下一根开盘 —— 单独量「重放」这一步有没有起作用
        （只比 A 的话，重放被换成终版信号也照样会因为成交价不同而「变」，那就成了替身）。"""
    bars = load(fn)
    honest, _ = replay(bars, level, measure)
    peek = peek_events(bars, level, measure)
    key = lambda ts: [(x["entry_t"], round(x["entry_px"], 8), x["exit_t"]) for x in ts[0]]
    h = trade(bars, honest, fee_bps, slip_bps)
    a = trade(bars, peek, fee_bps, slip_bps, fill="bar_close")
    b = trade(bars, peek, fee_bps, slip_bps)
    return key(h) != key(a), key(h) != key(b), summary(*h), summary(*a), summary(*b)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=",".join(DEFAULT_DATA))
    ap.add_argument("--level", default="pen", choices=("seg", "pen"))
    ap.add_argument("--measure", default="macd", choices=ENG.MEASURES)
    ap.add_argument("--fee-bps", type=float, default=4.0, help="单边手续费，基点")
    ap.add_argument("--slip-bps", type=float, default=2.0, help="单边滑点，基点")
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()
    files = a.data.split(",")
    print("参数：level=%s measure=%s 手续费 %.2f bp/边 滑点 %.2f bp/边 · 下一根开盘成交 · 只做多"
          % (a.level, a.measure, a.fee_bps, a.slip_bps))
    if a.probe:
        bad = 0
        for fn in files:
            ca, cb, h, pa, pb = probe(fn, a.level, a.measure, a.fee_bps, a.slip_bps)
            bad += (not ca) + (not cb)
            print("%-14s 重放 %s" % (fn, h))
            print("  %s A 按 bar 成交        %s" % ("✓ 变了" if ca else "✗ 没变", pa))
            print("  %s B 终版信号、下一根开盘 %s" % ("✓ 变了" if cb else "✗ 没变", pb))
        print("偷看探针：%s" % ("全部抓到" if not bad else "%d 份没变（重放没起作用）" % bad))
        return 1 if bad else 0
    out = []
    for fn in files:
        r = run_one(fn, a.level, a.measure, a.fee_bps, a.slip_bps)
        out.append(r)
        s = r["summary"]
        print("%-14s %5d 根 确认事件 %3d（之后被改掉 %d，近邻对 %d）笔数 %3d 胜率 %s 盈亏 %+.2f%% 最大回撤 %.2f%%%s"
              % (fn, r["bars"], r["events"], r["repaint"]["gone_by_end"], r["repaint"]["near_pairs"], s["n"],
                 "-" if s["win_rate"] is None else "%.0f%%" % (100 * s["win_rate"]), 100 * s["pnl"],
                 100 * s["max_dd"], "" if s["open"] is None else " · 未平 %+.2f%%" % (100 * s["open"])))
    if a.out:
        json.dump(dict(params=vars(a), results=out), open(a.out, "w"), ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
