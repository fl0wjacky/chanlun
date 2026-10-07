#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""只报不拦：L99:39-40「连接中枢的走势级别一定小於中枢，换言之，一个走势级别完成后，必然面临至少大一级别的中枢震荡。」
（card-a614755c-169，Nova 10-07：留成只报不拦，图头段跳过。）

    python3 tools/l99_report.py              # 永远 rc=0（只报）；拉不到数据的图照印「没比成」
    python3 tools/l99_report.py --self-test  # 判法自证：造的三组必须判对，不对 rc=1

判法（编者口径，原文没给怎么判）：每个**已完成**的走势段 T_k 跟它后面两段 T_k+1、T_k+2 有公共价格重叠
（三段的最高取最低、最低取最高，前者不低于后者）⇒ 出现了大一级中枢（L17:29 的定义拿走势段当次级别）。
  · 图头段（k=0）跳过：起点被窗口截断，「完成」本身不完整（10-07 实测 3 处违反全在图头段）。
  · 后面不够两段、或者 T_k+1 还在走 ⇒ 未量；T_k+2 还在走且暂时没重叠 ⇒ 未量（不当违反、也不当过）。
数据走 web/server.py 的 get_chart（跟线上同一条路），量的就是线上发出去的那份。
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [ROOT, os.path.join(ROOT, "web"), HERE]
import server                                                 # noqa: E402


def judge(bars, segs):
    """→ [(结论, k, 段型, 说明)]；结论 ∈ 违／过／未量。"""
    rng = [(max(b["h"] for b in bars[x["i0"]:x["i1"] + 1]), min(b["l"] for b in bars[x["i0"]:x["i1"] + 1])) for x in segs]
    out = []
    for k, x in enumerate(segs):
        if k == 0 or x["live"]:
            continue
        if k + 2 >= len(segs) or segs[k + 1]["live"]:
            out.append(("未量", k, x["type"], "后面不够两段走完"))
            continue
        hi = min(rng[j][0] for j in (k, k + 1, k + 2))
        lo = max(rng[j][1] for j in (k, k + 1, k + 2))
        if hi >= lo:
            out.append(("过", k, x["type"], "%g～%g" % (lo, hi)))
        elif segs[k + 2]["live"]:
            out.append(("未量", k, x["type"], "第三段还在走、暂时没重叠"))
        else:
            out.append(("违", k, x["type"], "三段无公共重叠"))
    return out


def self_test():
    """判法自证：造 5 段（每段 2 根 K 线），各喂一种情况，判词必须对 —— 只报的工具也得证明它报得出来。"""
    def mk(rngs, live_last=True):
        bars, segs = [], []
        for j, (h, l) in enumerate(rngs):
            bars += [dict(h=h, l=l), dict(h=h, l=l)]
            segs.append(dict(i0=2 * j, i1=2 * j + 1, type="上涨", live=live_last and j == len(rngs) - 1))
        return bars, segs
    bad = []
    got = judge(*mk([(10, 0), (5, 1), (9, 2), (8, 3), (7, 4)]))          # 段1/2/3 都跟后两段重叠
    if [r[0] for r in got] != ["过", "过", "未量"]:
        bad.append("重叠那组判成 %s" % got)
    got = judge(*mk([(10, 0), (5, 1), (20, 15), (30, 25), (40, 35)], live_last=False))
    if got[0][0] != "违" or got[0][1] != 1:
        bad.append("段1 跟后两段不重叠却没判违：%s" % got)
    got = judge(*mk([(10, 0), (50, 40), (90, 80)], live_last=False))         # 只有图头段跟后面不重叠
    if any(r[1] == 0 for r in got):
        bad.append("图头段没跳过：%s" % got)
    for b in bad:
        print("✗", b)
    print("自证" + ("通过（3 组）" if not bad else "没过"))
    return 1 if bad else 0


def main():
    if "--self-test" in sys.argv:
        return self_test()
    tot = {"违": 0, "过": 0, "未量": 0}
    for sym in server.SYMBOLS:
        for tf in server.TFS:
            try:
                d = json.loads(server.get_chart(sym, tf, span=1, prefetch=False)[0])
                res = judge(d["bars"], d["trend"]["segments"])
            except Exception as e:                            # 只报：拉不到也照印，不拦
                print("· %s %s 没比成：%s" % (sym, tf, str(e)[:80]))
                continue
            c = {t: sum(1 for r in res if r[0] == t) for t in tot}
            for t in tot:
                tot[t] += c[t]
            bad = " ".join("段%d(%s)%s：%s" % (k, ty, v, why) for v, k, ty, why in res if v == "违")
            print("%s %s %s 违 %d · 过 %d · 未量 %d%s" % ("~" if c["违"] else "✓", sym, tf, c["违"], c["过"], c["未量"],
                                                     ("  " + bad) if bad else ""))
    print("L99:39-40（只报不拦，图头段不算）：违 %d · 过 %d · 未量 %d" % (tot["违"], tot["过"], tot["未量"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
