#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""烤一份前端用的样本 JSON —— **接口形状的可执行定义**（前端卡 card-f4b326af-83d）。

为什么要有它：
  ① 前端不该等后台（Bram 的卡 card-29a45ab6-0ac）—— 先按这个形状离线跑起来，后台照着吐就接上了；
  ② 「前端画得对不对」要能跟 `render/chart_full_smooth.py` 并排比，而比的前提是**同一份数据同一份结构**
     —— 样本直接出自 `core.analyze`，不是另写一遍算法（后台卡也这么要求）；
  ③ 形状一改就重烤一次，前端和后台对着同一个文件对字段，不靠口头约定。

用法：
    python3 tools/make_web_fixture.py btc_4h.json            # → web/fixtures/btc_4h.json
    python3 tools/make_web_fixture.py zec_1h.json --symbol ZECUSDT --tf 1h

★ 只搬前端要用的字段，`std` / `fx` / `big` / `seq` 不进去（前端一个都不画，白白让样本胖三倍）。
★ 买卖点**在这里算好写进样本**（`core.signals` 两层各一份）—— 前端不许自己判信号：
  判断只在引擎一处，前端画两处会分家（后台卡「直接用 core.analyze / core.signals 的输出，不另写一套算法」同一条）。
"""
import argparse
import datetime
import json
import os
import sys

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, R)

from config import data, tick_of                      # noqa: E402
from core import analyze                              # noqa: E402
from core.signals import signals                      # noqa: E402

SYMBOL = {"zec": "ZECUSDT", "btc": "BTCUSDT", "aaplusdt": "AAPLUSDT"}
NAME   = {"ZECUSDT": "ZEC/USDT 永续", "BTCUSDT": "BTC/USDT 永续", "AAPLUSDT": "AAPL/USDT 永续"}
TF     = {"15": "15m", "30m": "30m", "1h": "1h", "2h": "2h", "4h": "4h"}
STEP_MS = {"15m": 15 * 60e3, "30m": 30 * 60e3, "1h": 3600e3, "2h": 7200e3, "4h": 14400e3}


def guess(fn):
    """data/ 的文件名 → (symbol, tf)。zec15.json 是 15 分钟那一份的旧名（前缀要保住 tick_of 才认）。"""
    stem = fn[:-5] if fn.endswith(".json") else fn
    for pre, sym in SYMBOL.items():
        if stem.startswith(pre):
            rest = stem[len(pre):].lstrip("_")
            return sym, TF.get(rest, rest)
    raise SystemExit("认不出标的（文件名要以 %s 开头）：%s" % ("/".join(SYMBOL), fn))


def build(fn, symbol=None, tf=None, updated=None, stale=False):
    symbol = symbol or guess(fn)[0]
    tf = tf or guess(fn)[1]
    if tf not in STEP_MS:
        raise SystemExit("周期要在 %s 里：%s" % ("/".join(STEP_MS), tf))
    r = analyze(json.load(open(data(fn), encoding="utf-8")), tick=tick_of(fn))
    nd = len(r["bars"])
    closed = r["bars"][-1]["t"] + STEP_MS[tf] <= (updated or datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000)
    d = dict(
        symbol=symbol, tf=tf, name=NAME.get(symbol, symbol),
        updated=datetime.datetime.fromtimestamp(r["bars"][-1]["t"] / 1000, datetime.timezone.utc)
                         .strftime("%Y-%m-%dT%H:%M:%SZ"),
        closed=bool(closed), nbars=nd,
        bars=r["bars"],
        pens=r["pens"],
        # 线段的 PI0/PI1 指向 segment 列表自己的下标 —— 前端算线段中枢的横跨区要它，原样带上
        segs=r["segs"],
        centers=r["centers"],
        seg_centers=r["seg_centers"],
        # 两层各一份：前端只按 tier 取，不自己判（判据在 core/signals.py 一处）
        signals={"seg": signals(r, "seg", "macd"), "pen": signals(r, "pen", "macd")},
        # 口径只读展示：这两项是**这次分析用的参数**，前端不做成开关（改了它就得整段重算，那是后台的事）
        meta=dict(tick=r["tick"], pen_rule=r["pen_rule"], min_gap=r["min_gap"]),
    )
    # fetched_at / stale 是**后台那层**才有的两个字段（拉币安的时刻；这轮没拉到、回的是上一次的结果）。
    # 样本是从 data/ 的文件烤的，谈不上「拉取」，所以默认不写 —— 前端把「没有 / 为假」都当成不是旧数据，
    # 两条路都走得通（这里 --stale 能烤一份假的，专门用来看角上那格说没说真话）。
    if stale:
        d["fetched_at"] = datetime.datetime.fromtimestamp(
            r["bars"][-1]["t"] / 1000 + STEP_MS[tf] * 3 / 1000, datetime.timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
        d["stale"] = True
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file", help="data/ 下的 K 线文件名")
    ap.add_argument("--symbol")
    ap.add_argument("--tf")
    ap.add_argument("--out", help="默认 web/fixtures/<file 同名>")
    ap.add_argument("--stale", action="store_true",
                    help="烤成「后台这轮没拉到、回的是上一次」的样子（多带 fetched_at/stale），用来看角上那格")
    a = ap.parse_args()
    d = build(a.file, a.symbol, a.tf, stale=a.stale)
    out = a.out or os.path.join(R, "web/fixtures", os.path.basename(a.file))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(d, open(out, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("%s ｜ %s %s ｜ %d 根 ｜ 笔 %d ｜ 类中枢 %d ｜ 线段 %d ｜ 线段中枢 %d ｜ 买卖点 seg %d / pen %d ｜ %d B"
          % (out, d["symbol"], d["tf"], d["nbars"], len(d["pens"]), len(d["centers"]), len(d["segs"]),
             len(d["seg_centers"]), len(d["signals"]["seg"]), len(d["signals"]["pen"]),
             os.path.getsize(out)))


if __name__ == "__main__":
    main()
