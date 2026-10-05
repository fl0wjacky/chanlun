#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""「确认后又消失」的点拆原因（card-cf3ed018-795，Nova 10-05 替小栋问）。口径跟 tools/backtest.py 的重放同一份。

    python3 tools/bt_gone.py [--data a.json,...] [--level pen] [--jobs 9]

对每份数据逐根重放（只喂 bars[:t+1]），记下每个点第一次 confirmed=True 的时刻；跟全量数据跑出的终版比：
  ① 搬家：终版里没有这个 (kind, 极值根)，但有**同 kind** 的点，极值在 ±W 根之内（W = 这个点从极值到确认
     走了几根，即它自己那一段的尺度），且那个点没被别的「还在」的点占着；
  ② 类别变了：终版里**同一根极值**上有点，但 kind 不同；
  ③ 彻底没了：以上都不是。
（判 ② 先于 ①：同一根上换了类别，比「附近有个同类」更直接。）

另算一列「确认再等一段」：点所在那一段之后，**再多走完一段**才算确认（笔层：unit < 笔数−2；线段层同理按
已完成线段数）。报：这种确认下的确认事件数、其中后来消失的数、两种确认都有的点平均晚多少根。
"""
import argparse
import multiprocessing
import os
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
from backtest import DATA, ENG, analyze, load                 # noqa: E402

CLS = {"一买": "一类", "一卖": "一类", "二买": "二类", "二卖": "二类", "三买": "三类", "三卖": "三类"}


def n_done(r, level):
    if level == "pen":
        return len(r["pens"]) - 1                     # 最后一笔永远是未完成的那一笔（signals 里 last_live 的口径）
    return len([s for s in r["segs"] if not s.get("live")])       # 线段层：已完成线段数


def one(args):
    fn, level, measure, warm = args
    bars, _ = load(fn)
    first, later = {}, {}                             # 键 → 首次确认 t（原口径 / 再等一段）
    meta = {}
    for t in range(warm, len(bars)):
        r = analyze(bars[:t + 1])
        nd = n_done(r, level)
        for g in ENG.signals(r, level, measure):
            if not g["confirmed"]:
                continue
            key = (g["kind"], bars[g["bar"]]["t"])
            if key not in first:
                first[key] = t
                meta[key] = g["bar"]
            if key not in later and g["unit"] + 1 < nd:   # 它那一段之后，再多一段也走完了
                later[key] = t
    fin = [(g["kind"], g["bar"]) for g in ENG.signals(analyze(bars), level, measure) if g["confirmed"]]
    fin_keys = {(k, bars[b]["t"]) for k, b in fin}
    gone = [k for k in first if k not in fin_keys]
    taken = {k for k in first if k in fin_keys}       # 终版里被「还在」的点占着的
    used = set()
    why = {}
    for k in sorted(gone, key=lambda k: first[k]):
        b = meta[k]
        same_bar = [kk for kk, bb in fin if bb == b and kk != k[0]]
        if same_bar:
            why[k] = "② 类别变了"; continue
        w = max(1, first[k] - b)
        near = [(abs(bb - b), bb) for kk, bb in fin if kk == k[0] and abs(bb - b) <= w
                and (kk, bars[bb]["t"]) not in taken and (kk, bb) not in used]
        if near:
            used.add((k[0], min(near)[1]))
            why[k] = "① 搬家"
        else:
            why[k] = "③ 彻底没了"
    delays = [later[k] - first[k] for k in first if k in later]
    return dict(data=fn, confirmed=len(first), gone=len(gone),
                by_why=Counter(why.values()), by_cls=Counter((CLS[k[0]], why[k]) for k in gone),
                later_confirmed=len(later), later_gone=sum(1 for k in later if k not in fin_keys),
                never_later=len(first) - len(later), mean_delay=(sum(delays) / len(delays)) if delays else None,
                bar_minutes=(bars[1]["t"] - bars[0]["t"]) // 60000)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=",".join(DATA))
    ap.add_argument("--level", default="pen", choices=("seg", "pen"))
    ap.add_argument("--measure", default="macd", choices=ENG.MEASURES)
    ap.add_argument("--jobs", type=int, default=1)
    a = ap.parse_args()
    jobs = [(fn, a.level, a.measure, 50) for fn in a.data.split(",")]
    res = multiprocessing.Pool(a.jobs).map(one, jobs) if a.jobs > 1 else list(map(one, jobs))
    W = ("① 搬家", "② 类别变了", "③ 彻底没了")
    tot = Counter()
    print("level=%s 看法=%s" % (a.level, a.measure))
    print("%-18s 确认 消失 | %s | 再等一段：确认 消失 等不到 平均晚(根)" % ("数据", " ".join("%-6s" % w for w in W)))
    for r in res:
        tot.update(dict(confirmed=r["confirmed"], gone=r["gone"], later=r["later_confirmed"],
                        later_gone=r["later_gone"], never=r["never_later"]))
        tot.update({w: r["by_why"][w] for w in W})
        tot.update({c + w: r["by_cls"][(c, w)] for c in ("一类", "二类", "三类") for w in W})
        print("%-18s %4d %4d | %s | %4d %4d %4d %s" % (
            r["data"], r["confirmed"], r["gone"], " ".join("%-6d" % r["by_why"][w] for w in W),
            r["later_confirmed"], r["later_gone"], r["never_later"],
            "-" if r["mean_delay"] is None else "%.1f（×%d 分钟）" % (r["mean_delay"], r["bar_minutes"])))
    print("合计 确认 %d 消失 %d | %s | 再等一段：确认 %d 消失 %d 等不到 %d" % (
        tot["confirmed"], tot["gone"], " ".join("%s %d" % (w, tot[w]) for w in W), tot["later"], tot["later_gone"],
        tot["never"]))
    for c in ("一类", "二类", "三类"):
        print("  %s：%s" % (c, " ".join("%s %d" % (w, tot[c + w]) for w in W)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
