"""总纲④ 只读量：main 上现行引擎对 5 条整体要求的现状。不改引擎。"""
import sys, os, json, gzip
sys.path[:0] = [os.getcwd(), "tools"]
from core.analyze import analyze
import core.trend as T
from config import tick_of
items = []
snap = json.loads(gzip.open(os.environ["LIVE15"]).read())
syms = {"ZECUSDT": "zec", "BTCUSDT": "btc", "AAPLUSDT": "aaplusdt"}
for k in sorted(snap):
    s, tf = k.split(); items.append((k, snap[k]["bars"], syms[s] + "_.json"))
for fn in ["aaplusdt_1h", "aaplusdt_2h", "aaplusdt_30m", "aaplusdt_4h", "btc_4h", "zec15", "zec30_cut", "zec_1h", "zec_2h", "zec_4h"]:
    items.append(("data/" + fn, json.load(open("data/%s.json" % fn)), fn + ".json"))
tot = {}
def add(k, v=1): tot[k] = tot.get(k, 0) + v
ex = {}
def eg(k, s):
    ex.setdefault(k, []); len(ex[k]) < 3 and ex[k].append(s)
for name, bars, tk in items:
    r = analyze(bars, tick=tick_of(tk)); n = len(bars)
    P, S = r["pens"], r["segs"]
    # R1 笔层：K 线有没有不属于任何笔的；相邻笔是否首尾同一根
    add("K线总数", n)
    add("R1 图头不在任何笔里的K线", P[0]["i0"]); add("R1 图尾不在任何笔里的K线", n - 1 - P[-1]["i1"])
    for a, b in zip(P, P[1:]):
        if a["i1"] != b["i0"]: add("R1 相邻笔不首尾相接"); eg("R1 相邻笔不首尾相接", "%s 笔 %d-%d" % (name, a["i1"], b["i0"]))
    add("笔总数", len(P))
    add("R1 图头不在任何线段里的笔", S[0]["PI0"]); add("R1 图尾不在任何线段里的笔", len(P) - 1 - S[-1]["PI1"])
    for a, b in zip(S, S[1:]):
        if a["PI1"] + 1 != b["PI0"]: add("R1 相邻线段笔号不接续"); eg("R1 相邻线段笔号不接续", "%s %d→%d" % (name, a["PI1"], b["PI0"]))
    v = T.trend_v3(r, reading="A")
    sg = v["segments"]
    add("走势段总数", len(sg))
    if sg[0]["i0"] != 0 or sg[-1]["i1"] != n - 1: add("R1 走势段没盖满整张图")
    for a, b in zip(sg, sg[1:]):
        if a["i1"] != b["i0"]: add("R1 相邻走势段不首尾相接"); eg("R1 相邻走势段不首尾相接", "%s %d-%d" % (name, a["i1"], b["i0"]))
        else: add("R1 相邻走势段共用接点那根K线")
    done = [x for x in S if not x.get("live")]
    for g, x in enumerate(sg):
        typ = x["type"] + ("·升" if x["upgraded"] else "")
        add("R2 段型=" + typ)
        nseg = sum(1 for d in done if d["i0"] >= x["i0"] and d["i1"] <= x["i1"])
        tag = "图头" if x["head"] else "末段" if x["live"] else "中间"
        if nseg < 3: add("R2 <3 段线段（%s）" % tag); eg("R2 <3 段线段（%s）" % tag, "%s 段%d %s %d 段" % (name, g, typ, nseg))
        zz = [z for z in v["seg_centers"] if z["seg"] == g]
        us = [u for u in v["units"] if u["seg"] == g]
        if not zz: add("R3 0 个本级别中枢（%s）" % tag); eg("R3 0 个本级别中枢（%s）" % tag, "%s 段%d %s" % (name, g, typ))
        if x["type"] in ("上涨", "下跌"):
            # 趋势：按读法 A 升级段数合成单元，否则数本级别中枢；要 ≥2 个、依次同向不重叠（DD～GG）
            cs = us if x["upgraded"] else zz
            cs = sorted(cs, key=lambda z: z["X0"])
            up = x["type"] == "上涨"
            ok = len(cs) >= 2 and all((b["DD"] > a["GG"]) if up else (b["GG"] < a["DD"]) for a, b in zip(cs, cs[1:]))
            if not ok:
                add("R3 趋势段不满足 ≥2 依次同向不重叠（%s）" % tag)
                eg("R3 趋势段不满足 ≥2 依次同向不重叠（%s）" % tag, "%s 段%d %s 个数 %d" % (name, g, typ, len(cs)))
    add("R4 D2-7 撤回的分界", len(v["retracted"])); 
    for rt in v["retracted"]: eg("R4 D2-7 撤回的分界", "%s %s %s" % (name, rt["kind"], rt["price"]))
    add("R4 D2-8 补刀", sum(1 for b in v["bounds"] if b.get("rule") == "D2-8"))
for k in sorted(tot): print(k, tot[k], ex.get(k, ""))
# 附：相邻两段段型（看「盘整+盘整」相邻）
pairs = {}
for name, bars, tk in items:
    v = T.trend_v3(analyze(bars, tick=tick_of(tk)), reading="A")
    sg = v["segments"]
    for a, b in zip(sg, sg[1:]):
        if a["head"]: continue
        k = (a["type"] + ("·升" if a["upgraded"] else ""), b["type"] + ("·升" if b["upgraded"] else ""))
        pairs[k] = pairs.get(k, 0) + 1
print("相邻段型（不含图头）", sorted(pairs.items(), key=lambda x: -x[1]))
c = {}
for name, bars, tk in items:
    v = T.trend_v3(analyze(bars, tick=tick_of(tk)), reading="A")
    for g, x in enumerate(v["segments"]):
        if x["type"] == "盘整" and not x["head"]:
            zz = [z for z in v["seg_centers"] if z["seg"] == g]; us = [u for u in v["units"] if u["seg"] == g]
            k = ("盘整·升" if x["upgraded"] else "盘整", "末段" if x["live"] else "中间", len(zz), len(us))
            c[k] = c.get(k, 0) + 1
print("盘整段：(类型, 位置, 本级别中枢数, 合成单元数) →", sorted(c.items()))
