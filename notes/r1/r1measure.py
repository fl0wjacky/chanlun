"""R-1 实测：SAME_LEVEL 开／关，25 张。"""
import sys, os, json, gzip, collections
sys.path[:0] = [os.getcwd(), "tools"]
from core.analyze import analyze
import core.trend as T
from config import tick_of
snap = json.loads(gzip.open(os.environ["LIVE15"]).read())
syms = {"ZECUSDT": "zec", "BTCUSDT": "btc", "AAPLUSDT": "aaplusdt"}
items = [(k, snap[k]["bars"], syms[k.split()[0]] + "_.json") for k in sorted(snap)]
for fn in ["aaplusdt_1h", "aaplusdt_2h", "aaplusdt_30m", "aaplusdt_4h", "btc_4h", "zec15", "zec30_cut", "zec_1h", "zec_2h", "zec_4h"]:
    items.append(("data/" + fn, json.load(open("data/%s.json" % fn)), fn + ".json"))
R = [(name, analyze(bars, tick=tick_of(tk))) for name, bars, tk in items]
key = lambda v: {(b["bar"], b["kind"]) for b in v["bounds"]}
seg = lambda v: {(s["i0"], s["i1"], s["type"], s["upgraded"]) for s in v["segments"]}
base = {n: T.trend_v3(r) for n, r in R}
def run(sl, ov, alt):
    T.SAME_LEVEL, T.SAME_LEVEL_OVERLAP = sl, ov
    try: return {n: T.trend_v3(r, alternate=alt) for n, r in R}
    finally: T.SAME_LEVEL, T.SAME_LEVEL_OVERLAP = False, "ZDZG"
for ov in ("ZDZG", "DDGG"):
    for alt in (True, False):
        o = run(True, ov, alt)
        ch = cuts = segs = 0; per = []
        types = collections.Counter(); nb = 0
        for n in base:
            dc, ds = len(key(base[n]) ^ key(o[n])), len(seg(base[n]) ^ seg(o[n]))
            if dc or ds: ch += 1; per.append((dc, ds, n))
            cuts += dc; segs += ds; nb += len(o[n]["bounds"])
            types.update(s["type"] for s in o[n]["segments"])
        per.sort(reverse=True)
        print("同级别 判重叠=%s D2-3交替=%s：变的图 %d/25，分界 %d→%d（增删 %d），走势段增删 %d；段型 %s；变化最大 %s" % (
            ov, "留" if alt else "放开", ch, sum(len(b["bounds"]) for b in base.values()), nb, cuts, segs, dict(types), per[:3]))
# ④ 相邻中枢重叠／不重叠（同级别中枢，按 D2 组内），两种区间各数一遍；⑤ 中枢之间余下的段数
pairs = {"ZDZG": collections.Counter(), "DDGG": collections.Counter()}; gaps = collections.Counter()
for n, r in R:
    res = T.find_bounds(r); done, ks = res["done"], res["ks"]
    edges = [0] + ks + [len(done)]
    for a, b in zip(edges, edges[1:]):
        zz = T._sl_centers(done, a, b)
        for z1, z2 in zip(zz, zz[1:]):
            gaps[z2["PI0"] - z1["PI1"] - 1] += 1
            for ov in pairs:
                T.SAME_LEVEL_OVERLAP = ov; pairs[ov][T._sl_rel(z1, z2)] += 1
T.SAME_LEVEL_OVERLAP = "ZDZG"
print("相邻中枢关系（同一 D2 组内）：", {k: dict(v) for k, v in pairs.items()})
print("两个中枢之间夹着几段（0＝紧挨着，3+3）：", dict(sorted(gaps.items())))
