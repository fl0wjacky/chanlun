#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证 c06 / c07 / chart_nested / 框架卡上的实测数字与定性结论。

· c06 / c07 / model_dissent：出图时由引擎现算（cards/zec_data.py、model_dissent.gap_rows）。
  这里直接从原始数据另写一遍逐项比对；再核对卡上**无条件写死**的定性说法在当前数据上仍成立
  （例如「扩展占多数」「结构层级大致对应」）—— 刷新 ZEC 数据后跑一遍，不成立就要回去改措辞。
· chart_nested：数字写死在图上（AAPL 30 分钟 → 1 小时），这里按标称核对。
任何一条对不上都会标 ✗ 并以非零状态退出。
"""
import os, sys, json
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import analyze
from config import data
from cards import zec_data as zec

# ---- 写死在图上的标称（改图时同步改这里） ----
NESTED = dict(A=11, unmerged=2, B=13, hit=9, A_1h=4)   # 2026-09-29 改中心定理一口径后回算   # chart_nested：30m 合成 / 未合成 / 1h 笔中枢 / 对得上；1h 合成
C07_MIN_MATCH = 50       # c07「结构层级大致对应」：个数最接近那档，两边互相对上的比例都应 ≥ 此值（%）

FAIL = 0


def check(label, card, got, ok=None):
    global FAIL
    ok = (card == got) if ok is None else ok
    FAIL += not ok
    print("   %s %-36s 卡片 %-16s 回算 %s" % ("✓" if ok else "✗", label, card, got))


def load(fn):
    return analyze(json.load(open(data(fn), encoding="utf-8")))


def times(r, zs, units):
    B = r["bars"]
    return [(B[units[z["PI0"]]["i0"]]["t"], B[units[z["PI1"]]["i1"]]["t"]) for z in zs]


def overlap(ta, za, tb, zb):
    return ta[0] <= tb[1] and tb[0] <= ta[1] and za["ZD"] <= zb["ZG"] and zb["ZD"] <= za["ZG"]


# ---- c06：ZEC 15 分钟，相邻中枢关系 ----
print("=" * 72)
print("c06 走势类型 · ZEC 15 分钟相邻中枢：趋势 vs 扩展（卡片现算 vs 这里另算）")
Z15 = load("zec15.json")
mine = {}
for name, zs in (("线段中枢", Z15["seg_centers"]), ("笔中枢", Z15["centers"])):
    k = Counter(zs[j]["kind"] for j in range(1, len(zs)))
    mine[name] = dict(n=len(zs) - 1, 趋势=k["趋势"], 扩展=k["扩展"], 同一中枢=k["同一中枢"])
    card = zec.pair_stats(zec.run("15m")["seg_centers" if name == "线段中枢" else "centers"])
    check("%s 对数 / 趋势 / 扩展 / 同一中枢" % name, tuple(card.values()), tuple(mine[name].values()))
for name in ("线段中枢", "笔中枢"):
    m = mine[name]
    check("「扩展占多数」在%s上成立" % name, "扩展 > 趋势", "%d > %d" % (m["扩展"], m["趋势"]), m["扩展"] > m["趋势"])

# ---- c07：ZEC 15 分钟线段中枢 vs 高周期笔中枢 ----
print("=" * 72)
print("c07 级别 · ZEC 15 分钟线段中枢（A）vs 高周期笔中枢（B）")
Ad = [s for s in Z15["segs"] if not s.get("live")]
A, TA = Z15["seg_centers"], times(Z15, Z15["seg_centers"], Ad)
rows = {}
for tf, fn in (("1h", "zec_1h.json"), ("2h", "zec_2h.json"), ("4h", "zec_4h.json")):
    R = load(fn)
    Bz, TB = R["centers"], times(R, R["centers"], R["pens"])
    a_hit = sum(1 for i in range(len(A)) if any(overlap(TA[i], A[i], TB[j], Bz[j]) for j in range(len(Bz))))
    b_hit = sum(1 for j in range(len(Bz)) if any(overlap(TA[i], A[i], TB[j], Bz[j]) for i in range(len(A))))
    rows[tf] = dict(A=len(A), B=len(Bz), A_hit=a_hit, B_hit=b_hit)
    check("%s  A / B / A 对上 / B 对上" % tf, tuple(zec.cross(tf).values()), tuple(rows[tf].values()))
best = min(rows, key=lambda t: abs(rows[t]["A"] - rows[t]["B"]))
b = rows[best]
pa, pb = 100 * b["A_hit"] / b["A"], 100 * b["B_hit"] / b["B"]
check("「结构层级大致对应」（%s 两边 ≥%d%%）" % (best, C07_MIN_MATCH), "≥%d%% / ≥%d%%" % (C07_MIN_MATCH, C07_MIN_MATCH),
      "%.0f%% / %.0f%%" % (pa, pb), pa >= C07_MIN_MATCH and pb >= C07_MIN_MATCH)

# ---- chart_nested：AAPL 30 分钟 → 1 小时（写死在图上）----
print("=" * 72)
print("chart_nested · AAPL 30 分钟链式合成 vs 1 小时笔中枢（图上写死的数字）")
R30, R1h = load("aaplusdt_30m.json"), load("aaplusdt_1h.json")
BA, B1 = R30["big"], R1h["centers"]
TA2, TB2 = times(R30, BA, R30["pens"]), times(R1h, B1, R1h["pens"])
hit = sum(1 for i in range(len(BA)) if any(overlap(TA2[i], BA[i], TB2[j], B1[j]) for j in range(len(B1))))
check("30m 合成 / 未合成 / 1h 笔中枢 / 对得上",
      (NESTED["A"], NESTED["unmerged"], NESTED["B"], NESTED["hit"]),
      (len(BA), sum(z["nmerge"] == 1 for z in BA), len(B1), hit))
check("1h 链式合成个数", NESTED["A_1h"], len(R1h["big"]))

# ---- 框架卡 model_dissent：验证表（卡片现算）----
print("=" * 72)
print("框架卡 model_dissent · AAPL 4 小时「向上离开后回试」表（卡片现算 vs 这里另算）")
from cards.model_dissent import gap_rows
card_rows = [(n, round(hi, 2), round(lo, 2), v) for _, n, _, hi, lo, v in gap_rows()]
R4 = load("aaplusdt_4h.json")
Z, P = R4["centers"], R4["pens"]
mine = []
for n, z in enumerate(Z, 1):                     # 另写：按中枢逐笔扫，离开 = 向上笔越过 ZG
    last = Z[n]["PI0"] if n < len(Z) else len(P)
    j = z["PI0"]
    while j + 1 < len(P) and j <= last:
        a, b2 = P[j], P[j + 1]
        if a["p1"] > a["p0"] and a["p1"] > z["ZG"] and b2["p1"] < b2["p0"]:
            v = "三买" if b2["p1"] >= z["ZG"] else ("ZD 下方" if b2["p1"] < z["ZD"] else "假缝隙")
            mine.append((n, round(a["p1"], 2), round(b2["p1"], 2), v))
        j += 1
check("逐行一致（%d 行）" % len(mine), len(card_rows), len(mine), card_rows == mine)
last_is_buy = all(
    [r[3] for r in mine if r[0] == n][-1] == "三买" and [r[3] for r in mine if r[0] == n].count("三买") == 1
    for n in {r[0] for r in mine if r[3] == "三买"})
check("「每个中枢成立的三买都是最后一次」", "成立", "成立" if last_is_buy else "不成立", last_is_buy)

print("=" * 72)
print("全部一致" if FAIL == 0 else "有 %d 条对不上 —— 卡片上的数字或措辞过期了，回去改卡" % FAIL)
sys.exit(1 if FAIL else 0)
