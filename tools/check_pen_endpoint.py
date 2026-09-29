#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查：笔端点在图上被画到哪一根原始K线上？是否正好是那根极值K线？

引擎当前把合并组的「最后一根」索引当作端点位置，但那不一定是
贡献了极值（最高/最低）的那一根。脚本对比两种口径，量出偏差。
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import data
from core.kline import standardize, fractals, _contains
from core.pen import build_pens_v1 as build_pens   # 这个诊断是针对 v1 划笔写的


def standardize_track(bars):
    """在标准化时额外记住：每个极值来自哪一根原始K线。"""
    n = len(bars)
    k = 1
    while k < n and _contains(bars[k-1]["h"], bars[k-1]["l"], bars[k]["h"], bars[k]["l"]):
        k += 1
    m = [dict(h=bars[k-1]["h"], l=bars[k-1]["l"], i=k-1, ih=k-1, il=k-1),
         dict(h=bars[k]["h"], l=bars[k]["l"], i=k, ih=k, il=k)]
    for i in range(k + 1, n):
        bh, bl = bars[i]["h"], bars[i]["l"]
        p, p2 = m[-1], m[-2]
        up = p["h"] > p2["h"] or (p["h"] == p2["h"] and p["l"] > p2["l"])
        if _contains(p["h"], p["l"], bh, bl):
            if up:
                m[-1] = dict(h=max(p["h"], bh), l=max(p["l"], bl), i=i,
                             ih=i if bh > p["h"] else p["ih"],
                             il=i if bl > p["l"] else p["il"])
            else:
                m[-1] = dict(h=min(p["h"], bh), l=min(p["l"], bl), i=i,
                             ih=i if bh < p["h"] else p["ih"],
                             il=i if bl < p["l"] else p["il"])
        else:
            m.append(dict(h=bh, l=bl, i=i, ih=i, il=i))
    return m


for fn, tag in (("aaplusdt_4h.json", "4小时"), ("aaplusdt_30m.json", "30分钟")):
    bars = json.load(open(data(fn), encoding="utf-8"))
    m_old = standardize(bars)
    m_new = standardize_track(bars)

    # 用新版极值索引重建分型，再走同样的笔构造
    def fx_from(m, key):
        out = []
        for kk in range(1, len(m) - 1):
            a, b, c = m[kk-1], m[kk], m[kk+1]
            if b["h"] > a["h"] and b["h"] > c["h"] and b["l"] > a["l"] and b["l"] > c["l"]:
                out.append(dict(k=kk, i=b[key[0]], type="top", price=b["h"]))
            elif b["l"] < a["l"] and b["l"] < c["l"] and b["h"] < a["h"] and b["h"] < c["h"]:
                out.append(dict(k=kk, i=b[key[1]], type="bot", price=b["l"]))
        return out

    f_old = fx_from(m_old, ("i", "i"))
    f_new = fx_from(m_new, ("ih", "il"))
    _, seq_old = build_pens(f_old, 4)
    _, seq_new = build_pens(f_new, 4)

    diff = [i for i in range(min(len(seq_old), len(seq_new)))
            if seq_old[i]["i"] != seq_new[i]["i"]]
    print("=" * 60)
    print("[%s] 笔端点 %d 个" % (tag, len(seq_new)))
    print("  两种口径位置不同的端点: %d 个（%.0f%%）"
          % (len(diff), 100.0 * len(diff) / max(1, len(seq_new))))
    if diff:
        shifts = [abs(seq_new[i]["i"] - seq_old[i]["i"]) for i in diff]
        print("  偏移量（根）: 最小 %d / 最大 %d / 平均 %.1f"
              % (min(shifts), max(shifts), sum(shifts) / len(shifts)))
        print("  样例（前 5 个）:")
        for i in diff[:5]:
            o, n = seq_old[i], seq_new[i]
            print("     k=%3d %s  旧:i=%4d(最后一根)  新:i=%4d(极值那根)  差 %d 根"
                  % (n["k"], n["type"], o["i"], n["i"], abs(o["i"] - n["i"])))
