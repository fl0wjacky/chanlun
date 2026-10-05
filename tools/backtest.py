#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""最小回测：拿历史 K 线检验买卖点事后的表现（card-41383e15-d8f，小栋 10-04 ③A）。口径＝docs/spec/回测.md。

    python3 tools/backtest.py [--data a.json,b.json] [--level pen|seg] [--measure macd]
                              [--fee-bps 5] [--slip-bps 5] [--out 报表.json] [--trades]
    python3 tools/backtest.py --probe     # 四个探针（spec 第五节），每个都必须让结果变

规则页四条硬规则在这里的落点：
  ① 确认之后下一根开盘成交 —— trade()：事件在第 t 根确认 ⇒ 第 t+1 根开盘；t+1 不存在 ⇒「数据末尾未成交」。
  ② 费用显式 —— --fee-bps / --slip-bps，每边；买价 ×(1+slip)、卖价 ×(1−slip)，每边再扣 fee；报表第一行原样印。
  ③ 不偷看 —— replay()：逐根重放，只喂 bars[:t+1]，点第一次以 confirmed=True 出现的 t 就是确认时刻。
     键 = (kind, level, 极值那根的时间戳)；漂一根也算新点（严格），另报近邻对（同 kind、相距 ≤2 根）。
  ④ 只用已收盘 —— data/ 下都是历史收盘线；第 t 步只看得见 bars[:t+1]。

交易模型（spec 第三节）：只做多；一二三类买点（含 weak）空仓开多，一二三类卖点持仓平仓；重复信号忽略；
走完还持仓 ⇒ 最后一根收盘盯市，单列「未平」，不计入笔数和胜率。
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.analyze import analyze                              # noqa: E402
import core.signals                                           # noqa: E402,F401
ENG = sys.modules["core.signals"]                             # core/__init__ 把 signals 导成了函数，拿模块要这样

BUY, SELL = ("一买", "二买", "三买"), ("一卖", "二卖", "三卖")
DATA = ("aaplusdt_4h.json", "aaplusdt_2h.json", "aaplusdt_1h.json", "aaplusdt_30m.json", "btc_4h.json",
        "zec_4h.json", "zec_2h.json", "zec_1h.json", "zec15.json")       # spec 第四节：正式报表 9 份
SMALL = 30                                                                # 样本量护栏
COSTS = (0, 5, 10)                                                        # 成本敏感性：fee = slip = 这几档
WARN = "样本太小，这些数字不能拿来判断买卖点好坏"


def load(fn):
    raw = open(os.path.join(ROOT, "data", fn), "rb").read()
    return json.loads(raw), hashlib.sha1(raw).hexdigest()


def engine_commit():
    try:
        return subprocess.run(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()
    except Exception:
        return "?"


# ---------------------------------------------------------------- 信号来源
def replay(bars, level, measure, warm=50):
    """逐根重放 → (确认事件 [dict(kind, t_extreme, bar, confirm_i, weak, gone)] 按确认先后, 重放统计)。"""
    first, events = {}, []
    for t in range(warm, len(bars)):
        for g in ENG.signals(analyze(bars[:t + 1]), level, measure):
            if not g["confirmed"]:
                continue
            key = (g["kind"], level, bars[g["bar"]]["t"])
            if key not in first:
                first[key] = t
                events.append(dict(kind=g["kind"], t_extreme=key[2], bar=g["bar"], confirm_i=t,
                                   weak=bool(g.get("weak"))))
    final = {(g["kind"], level, bars[g["bar"]]["t"])
             for g in ENG.signals(analyze(bars), level, measure) if g["confirmed"]}
    for e in events:
        e["gone"] = (e["kind"], level, e["t_extreme"]) not in final
    pos = {b["t"]: i for i, b in enumerate(bars)}
    ks = sorted(first, key=lambda k: (k[0], pos[k[2]]))
    near = [(x, y) for x, y in zip(ks, ks[1:]) if x[0] == y[0] and abs(pos[y[2]] - pos[x[2]]) <= 2]
    return events, dict(confirmed=len(events), gone=sum(e["gone"] for e in events), near_pairs=len(near))


def merge_near(events, bars):
    """近邻合并对照（spec 二）：同 kind、极值相距 ≤2 根的，只留先确认的那个。主结果不用它。"""
    pos = {b["t"]: i for i, b in enumerate(bars)}
    out = []
    for e in events:
        if any(o["kind"] == e["kind"] and abs(pos[o["t_extreme"]] - pos[e["t_extreme"]]) <= 2 for o in out):
            continue
        out.append(e)
    return out


def final_events(bars, level, measure):
    """终版信号（全量数据跑一遍），当作在极值那根就知道了 —— 只给探针 A / B 用。"""
    return sorted((dict(kind=g["kind"], t_extreme=bars[g["bar"]]["t"], bar=g["bar"], confirm_i=g["bar"],
                        weak=bool(g.get("weak")), gone=False)
                   for g in ENG.signals(analyze(bars), level, measure) if g["confirmed"]),
                  key=lambda e: e["confirm_i"])


# ---------------------------------------------------------------- 成交与统计
def trade(bars, events, fee_bps, slip_bps, fill="next_open"):
    """events → (已平明细, 未平, 逐根权益, 末尾未成交数, 被改掉的点里触发了成交的数)。
    fill=next_open（正式）：第 confirm_i+1 根开盘；fill=confirm_close（探针 D）：确认那根收盘；
    fill=bar_close（探针 A）：极值那根收盘（终版信号的 confirm_i 就是 bar）。"""
    fee, slip = fee_bps / 1e4, slip_bps / 1e4
    by_i, unfilled = {}, 0
    for e in events:
        i = e["confirm_i"] + 1 if fill == "next_open" else e["confirm_i"]
        if i >= len(bars):
            unfilled += 1
            continue
        by_i.setdefault(i, []).append(e)
    trades, pos, eq, curve, gone_hit = [], None, 1.0, [], 0
    for i, b in enumerate(bars):
        px = b["o"] if fill == "next_open" else b["c"]
        for e in by_i.get(i, []):
            if pos is None and e["kind"] in BUY:
                pos = dict(open_confirm_i=e["confirm_i"], open_i=i, open_t=b["t"], open_raw=px,
                           open_px=px * (1 + slip), open_kind=e["kind"], open_extreme_t=e["t_extreme"],
                           weak=e["weak"])
                gone_hit += e["gone"]
            elif pos is not None and e["kind"] in SELL:
                out_px = px * (1 - slip)
                trades.append(dict(pos, close_confirm_i=e["confirm_i"], close_i=i, close_t=b["t"], close_raw=px,
                                   close_px=out_px, close_kind=e["kind"], gross=px / pos["open_raw"] - 1,
                                   net=(out_px / pos["open_px"]) * (1 - fee) ** 2 - 1))
                gone_hit += e["gone"]
                eq *= 1 + trades[-1]["net"]
                pos = None
        curve.append(eq * (b["c"] * (1 - slip) / pos["open_px"]) * (1 - fee) ** 2 if pos else eq)
    open_pos = None
    if pos:
        c = bars[-1]["c"]
        open_pos = dict(pos, close_i=len(bars) - 1, close_t=bars[-1]["t"], close_raw=c, close_kind="未平",
                        gross=c / pos["open_raw"] - 1, net=(c * (1 - slip) / pos["open_px"]) * (1 - fee) ** 2 - 1)
    return trades, open_pos, curve, unfilled, gone_hit


def hold(bars, fee_bps, slip_bps):
    """同期持有不动：第一根开盘买、最后一根收盘卖，同一组成本（spec 四）。"""
    fee, slip = fee_bps / 1e4, slip_bps / 1e4
    return (bars[-1]["c"] * (1 - slip)) / (bars[0]["o"] * (1 + slip)) * (1 - fee) ** 2 - 1


def summary(trades, open_pos, curve):
    comp, peak, mdd = 1.0, 0.0, 0.0
    for x in trades:
        comp *= 1 + x["net"]
    for v in curve:
        peak = max(peak, v)
        mdd = max(mdd, 1 - v / peak)
    weak = [x for x in trades if x["weak"]]
    wcomp = 1.0
    for x in weak:
        wcomp *= 1 + x["net"]
    n = len(trades)
    return dict(n=n, win_rate=round(sum(x["net"] > 0 for x in trades) / n, 4) if n else None,
                pnl_comp=round(comp - 1, 6), pnl_sum=round(sum(x["net"] for x in trades), 6),
                max_dd=round(mdd, 6), weak_n=len(weak), weak_pnl_comp=round(wcomp - 1, 6),
                open_net=round(open_pos["net"], 6) if open_pos else None, small=n < SMALL,
                total=round(comp * (1 + (open_pos["net"] if open_pos else 0)) - 1, 6))   # 已平复利 × 未平盯市


def run_one(fn, level, measure, fee_bps, slip_bps):
    bars, sha = load(fn)
    events, rp = replay(bars, level, measure)
    trades, open_pos, curve, unfilled, gone_hit = trade(bars, events, fee_bps, slip_bps)
    rp.update(gone_traded=gone_hit, unfilled_at_end=unfilled)
    s = summary(trades, open_pos, curve)
    h = hold(bars, fee_bps, slip_bps)
    sens = []
    for c in COSTS:                                              # 成本敏感性：重放一次，成交按各档成本重算
        t_ = trade(bars, events, c, c)
        x = summary(*t_[:3])
        sens.append(dict(cost_bps=c, n=x["n"], win_rate=x["win_rate"], pnl_comp=x["pnl_comp"], total=x["total"],
                         max_dd=x["max_dd"], hold=round(hold(bars, c, c), 6)))
    res = dict(data=fn, sha1=sha, bars=len(bars), level=level, measure=measure, replay=rp,
               hold=round(h, 6), vs_hold=round(s["total"] - h, 6), summary=s, sensitivity=sens,
               trades=trades, open=open_pos)
    if rp["near_pairs"]:                                         # 近邻对不为 0 ⇒ 另出一份合并对照
        t2 = trade(bars, merge_near(events, bars), fee_bps, slip_bps)
        res["near_merged"] = summary(*t2[:3])
    return res


# ---------------------------------------------------------------- 探针（spec 第五节）
def probe(fn, level, measure, fee_bps, slip_bps):
    """四个探针各自跟正式结果比交易明细（开仓时间、开仓价、平仓时间、净收益，含未平），返回 {名字: (变了没有, 笔数)}。"""
    bars, _ = load(fn)
    events, _ = replay(bars, level, measure)
    fin = final_events(bars, level, measure)

    def key(r):
        rows = [(x["open_t"], round(x["open_px"], 8), x["close_t"], round(x["net"], 10)) for x in r[0]]
        return rows + ([("未平", r[1]["open_t"], round(r[1]["net"], 10))] if r[1] else [])
    base = key(trade(bars, events, fee_bps, slip_bps))
    arms = {"A 偷看：终版信号、极值那根收盘": trade(bars, fin, fee_bps, slip_bps, fill="bar_close"),
            "B 终版信号、照样下一根开盘": trade(bars, fin, fee_bps, slip_bps),
            "C 零成本": trade(bars, events, 0, 0),
            "D 确认那根收盘成交": trade(bars, events, fee_bps, slip_bps, fill="confirm_close")}
    return {k: (key(v) != base, len(v[0]) + bool(v[1])) for k, v in arms.items()}, len(base)


# ---------------------------------------------------------------- 打印
def pct(x):
    return "-" if x is None else "%+.2f%%" % (100 * x)


def print_report(r, fee, slip, commit, show_trades):
    s, rp = r["summary"], r["replay"]
    print("— %s  sha1 %s  引擎 %s  level=%s  看法=%s  fee=%.2fbp/边  slip=%.2fbp/边  %d 根"
          % (r["data"], r["sha1"][:12], commit, r["level"], r["measure"], fee, slip, r["bars"]))
    if s["small"]:
        print("  ⚠ %s（笔数 %d < %d）" % (WARN, s["n"], SMALL))
    print("  笔数 %d  胜率 %s  盈亏 复利 %s / 加总 %s  最大回撤 %.2f%%  weak 开的 %d 笔 %s  未平 %s"
          % (s["n"], "-" if s["win_rate"] is None else "%.0f%%" % (100 * s["win_rate"]), pct(s["pnl_comp"]),
             pct(s["pnl_sum"]), 100 * s["max_dd"], s["weak_n"], pct(s["weak_pnl_comp"]), pct(s["open_net"])))
    print("  已平＋未平盯市 %s ｜ 同期持有不动 %s ｜ 差 %s" % (pct(s["total"]), pct(r["hold"]), pct(r["vs_hold"])))
    print("  成本敏感性（fee=slip，每边）：" + "；".join(
        "%dbp 笔数 %d 胜率 %s 复利 %s 回撤 %.2f%% 持有不动 %s" % (
            x["cost_bps"], x["n"], "-" if x["win_rate"] is None else "%.0f%%" % (100 * x["win_rate"]),
            pct(x["pnl_comp"]), 100 * x["max_dd"], pct(x["hold"])) for x in r["sensitivity"]))
    print("  重放：确认事件 %d · 之后被改掉 %d（其中触发了成交 %d）· 近邻对 %d · 末尾未成交 %d"
          % (rp["confirmed"], rp["gone"], rp["gone_traded"], rp["near_pairs"], rp["unfilled_at_end"]))
    if "near_merged" in r:
        m = r["near_merged"]
        print("  近邻合并对照：笔数 %d 盈亏 %s 最大回撤 %.2f%%" % (m["n"], pct(m["pnl_comp"]), 100 * m["max_dd"]))
    if show_trades:
        for x in r["trades"] + ([r["open"]] if r["open"] else []):
            print("    确认 %5d → 开 %5d @%.6g  %s%s(%d)  ‖ 确认 %s → 平 %5d @%.6g %s  毛 %s 净 %s"
                  % (x["open_confirm_i"], x["open_i"], x["open_px"], x["open_kind"], "·weak" if x["weak"] else "",
                     x["open_extreme_t"], x.get("close_confirm_i", "-"), x["close_i"], x["close_raw"],
                     x["close_kind"], pct(x["gross"]), pct(x["net"])))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=",".join(DATA))
    ap.add_argument("--level", default="pen", choices=("seg", "pen"))
    ap.add_argument("--measure", default="macd", choices=ENG.MEASURES)
    ap.add_argument("--fee-bps", type=float, default=5.0, help="每边手续费，基点")
    ap.add_argument("--slip-bps", type=float, default=5.0, help="每边滑点，基点")
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--trades", action="store_true", help="逐笔明细也印出来")
    ap.add_argument("--out")
    a = ap.parse_args()
    files, commit = a.data.split(","), engine_commit()
    print("参数：fee_bps=%.2f slip_bps=%.2f（每边）· level=%s · 看法=%s · 确认后下一根开盘成交 · 只做多 · 引擎 %s"
          % (a.fee_bps, a.slip_bps, a.level, a.measure, commit))
    if a.probe:
        idle = 0
        for fn in files:
            got, nbase = probe(fn, a.level, a.measure, a.fee_bps, a.slip_bps)
            print("— %s（正式 %d 笔，含未平）" % (fn, nbase))
            for k, (changed, n) in got.items():
                idle += not changed
                print("  %s %s（%d 笔）" % ("✓ 变了" if changed else "· 这份上空转", k, n))
        print("探针：%s" % ("每份每条都变了" if not idle else "%d 处空转（见上，空转的那份要写明）" % idle))
        return 0
    out = []
    for fn in files:
        r = run_one(fn, a.level, a.measure, a.fee_bps, a.slip_bps)
        out.append(r)
        print_report(r, a.fee_bps, a.slip_bps, commit, a.trades)
    if a.out:
        json.dump(dict(params=dict(fee_bps=a.fee_bps, slip_bps=a.slip_bps, level=a.level, measure=a.measure,
                                   engine=commit), results=out), open(a.out, "w"), ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
