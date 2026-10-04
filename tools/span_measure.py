#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""往左加载（card-4a6f70bb-74b）的实测表：每个 span 档的拉取 / 计算 / 体积，和相邻两档重叠区的结构差异。

    python3 tools/span_measure.py --end <毫秒> [--spans 1,2,4,8,16] [--only ZECUSDT:15m] [--out 表.json]

取数口径（可复现）：
  · 每个（品种, 周期）**一次**取数，同一根最新 K 线：结束时刻 = --end（给定的毫秒；默认 = 现在往前取整到
    该周期**已收盘**的最后一根）。已收盘的 K 线币安不会改 ⇒ 别人拿同一个 --end 重跑，拿到的是同一份数据。
  · 往前一档一档地补：span=1 拉 [end−210 天, end]，span=2 只补 [end−420 天, end−210 天)，依此类推 ——
    跟服务器「往前补只要缺的那一段」同一个拉法，所以「拉取」那列计的是**这一档新增的那段**的耗时。
  · 币安某一段返回空（没有更早的数据了）⇒ 这一档 earliest=true，不再往后试。
每档：bars 根数、本档补拉耗时、计算耗时（tools/make_web_fixture.shape，即后台同一个函数）、JSON 字节 / gzip 字节。
相邻两档（k 对 2k）的结构差异 —— 量法照 Atlas 写在卡上的（2026-10-04）：
  · 重叠区 = 两份都有的 K 线，**按时间戳对齐**（不按下标）；
  · 比 ① 笔端点（时间戳＋顶/底）② 线段端点（时间戳＋方向）③ 类中枢、线段中枢（起止时间戳＋ZD/ZG）；
    一边有一边没有也算一处；只比**整个落在重叠区里**的东西；
  · 报：差异处数、**最右一处差异离右端几根**（0 = 最新那根；按 span=k 那份的下标数）。
"""
import argparse
import gzip
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

from config import tick_of                                    # noqa: E402
from fetch_klines import fetch                                # noqa: E402
from make_web_fixture import shape                            # noqa: E402

SYMBOLS = {"ZECUSDT": "zec", "BTCUSDT": "btc", "AAPLUSDT": "aaplusdt"}
STEP = {"15m": 15 * 60_000, "30m": 30 * 60_000, "1h": 3600_000, "2h": 7200_000, "4h": 14400_000}
DAY = 86400_000
BASE_DAYS = 210


def structures(d):
    """shape() 的结果 → 四类可比对的东西：{类别: {键: 最右的时间戳}}。键里全是时间戳，不含下标。"""
    t = [b["t"] for b in d["bars"]]
    pens, segs = d["pens"], d["segs"]
    done = [s for s in segs if not s.get("live")]
    out = {"笔端点": {}, "段端点": {}, "类中枢": {}, "线段中枢": {}}
    for p in pens:
        for i, price, other in ((p["i0"], p["p0"], p["p1"]), (p["i1"], p["p1"], p["p0"])):
            out["笔端点"][(t[i], "顶" if price > other else "底")] = t[i]
    for s in segs:
        out["段端点"][(t[s["i0"]], t[s["i1"]], s["dir"], bool(s.get("live")))] = t[s["i1"]]
    for name, zs, host in (("类中枢", d["centers"], pens), ("线段中枢", d["seg_centers"], done)):
        for z in zs:
            a, b = t[host[z["PI0"]]["i0"]], t[host[z["PI1"]]["i1"]]
            out[name][(a, b, z["ZD"], z["ZG"])] = b
    return out


def first_t(key):
    return key[0]


def diff_pair(dk, d2k):
    """span=k 与 span=2k 在重叠区（k 那份的时间范围）里的结构差异。"""
    tk = [b["t"] for b in dk["bars"]]
    lo, n = tk[0], len(tk)
    pos = {x: i for i, x in enumerate(tk)}
    a, b = structures(dk), structures(d2k)
    rep, rightmost = {}, None
    for cat in a:
        ka = {k: v for k, v in a[cat].items() if first_t(k) >= lo}
        kb = {k: v for k, v in b[cat].items() if first_t(k) >= lo}
        diff = set(ka) ^ set(kb)
        rep[cat] = len(diff)
        for k in diff:
            r = n - 1 - pos[(ka.get(k) or kb.get(k))]
            rightmost = r if rightmost is None else min(rightmost, r)
    return dict(per_cat=rep, total=sum(rep.values()), rightmost_from_end=rightmost)


def measure(symbol, tf, end, spans):
    tick = tick_of(SYMBOLS[symbol] + "_.json")
    bars, rows, results, earliest = [], [], {}, False
    prev_lo = end + 1
    for k in spans:
        lo = end - k * BASE_DAYS * DAY
        t0 = time.time()
        chunk = fetch(symbol, tf, lo, prev_lo - 1) if lo < prev_lo else []
        f_s = time.time() - t0
        chunk = [b for b in chunk if b["t"] < prev_lo and b["t"] >= lo]
        if not chunk and bars:
            earliest = True
        bars = sorted({b["t"]: b for b in chunk + bars}.values(), key=lambda b: b["t"])
        prev_lo = lo
        t0 = time.time()
        d = shape(bars, tick, symbol, tf, now_ms=end + STEP[tf])
        c_s = time.time() - t0
        raw = json.dumps(d, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        results[k] = d
        rows.append(dict(span=k, bars=len(bars), first_t=bars[0]["t"], last_t=bars[-1]["t"],
                         fetch_s=round(f_s, 2), fetch_new_bars=len(chunk), compute_s=round(c_s, 2),
                         json_bytes=len(raw), gzip_bytes=len(gzip.compress(raw, 6)), earliest=earliest))
        print("  %s %s span=%-2d %6d 根 补拉 %5.1fs(+%d) 计算 %5.2fs %6.1f MB gz %5.2f MB%s"
              % (symbol, tf, k, len(bars), f_s, len(chunk), c_s, len(raw) / 1e6, rows[-1]["gzip_bytes"] / 1e6,
                 " · earliest" if earliest else ""), flush=True)
        if earliest:
            break
    pairs = []
    ks = [r["span"] for r in rows]
    for k1, k2 in zip(ks, ks[1:]):
        p = diff_pair(results[k1], results[k2])
        p.update(k=k1, k2=k2)
        pairs.append(p)
        print("    差异 span %d↔%d：%d 处 %s · 最右一处离右端 %s 根"
              % (k1, k2, p["total"], p["per_cat"], p["rightmost_from_end"]), flush=True)
    return dict(symbol=symbol, tf=tf, end=end, rows=rows, pairs=pairs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--end", type=int, help="结束时刻（毫秒）；默认 = 现在，按各周期取整到已收盘的最后一根")
    ap.add_argument("--spans", default="1,2,4,8,16")
    ap.add_argument("--only", help="只跑 SYMBOL:tf，逗号分隔")
    ap.add_argument("--out")
    a = ap.parse_args()
    now = a.end or int(time.time() * 1000)
    spans = [int(x) for x in a.spans.split(",")]
    todo = [(s, t) for s in SYMBOLS for t in STEP]
    if a.only:
        want = {tuple(x.split(":")) for x in a.only.split(",")}
        todo = [x for x in todo if x in want]
    out = dict(measured_at=int(time.time() * 1000), end_arg=a.end, spans=spans, cells=[])
    for s, tf in todo:
        end = (now // STEP[tf]) * STEP[tf] - STEP[tf]            # 已收盘的最后一根的开盘时间
        out["cells"].append(measure(s, tf, end, spans))
        if a.out:
            json.dump(out, open(a.out, "w"), ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
