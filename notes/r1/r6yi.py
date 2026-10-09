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
R = [(n, analyze(b, tick=tick_of(t))) for n, b, t in items]
key = lambda v: {(b["bar"], b["kind"]) for b in v["bounds"]}
def run(**kw):
    old = {k: getattr(T, k) for k in kw}
    for k, v in kw.items(): setattr(T, k, v)
    try: return {n: T.trend_v3(r) for n, r in R}
    finally:
        for k, v in old.items(): setattr(T, k, v)
def cmp(a, b, lab):
    ch = cuts = segs = t2p = p2t = 0
    for n in a:
        sa = {(s["i0"], s["i1"]): s["type"] for s in a[n]["segments"]}; sb = {(s["i0"], s["i1"]): s["type"] for s in b[n]["segments"]}
        dc = len(key(a[n]) ^ key(b[n])); ds = len(set(sa.items()) ^ set(sb.items()))
        ch += bool(dc or ds); cuts += dc; segs += ds
        for k in set(sa) & set(sb):
            if sa[k] in ("上涨", "下跌") and sb[k] == "盘整": t2p += 1
            if sa[k] == "盘整" and sb[k] in ("上涨", "下跌"): p2t += 1
    print("%s：变的图 %d/25，刀增删 %d，走势段增删 %d；同起止的段里 趋势→盘整 %d、盘整→趋势 %d" % (lab, ch, cuts, segs, t2p, p2t))
# 非同级别（main）
A = run(); B0 = run(_DIR_RULE=False); B1 = run(_DIR_RULE=False, R6_YI_PRIME=True)
cmp(A, B0, "main：甲(D6) → 乙粗版(_DIR_RULE=False)")
cmp(A, B1, "main：甲(D6) → 乙′(_DIR_RULE=False＋a 不进第一个中枢)")
# 同级别 S9
S = run(SAME_LEVEL=True, SAME_LEVEL_D2=True); SJ = run(SAME_LEVEL=True, SAME_LEVEL_D2=True, SAME_LEVEL_D6="fallback")
SY = run(SAME_LEVEL=True, SAME_LEVEL_D2=True, R6_YI_PRIME=True)
cmp(SJ, S, "S9：甲(D6 fallback) → 乙粗版(S9 底座)")
cmp(SJ, SY, "S9：甲(D6 fallback) → 乙′")
cmp(S, SY, "S9：乙粗版(S9 底座) → 乙′")
print("S9 乙′ 刀数", sum(len(v["bounds"]) for v in SY.values()), "S9 底座", sum(len(v["bounds"]) for v in S.values()), "甲fallback", sum(len(v["bounds"]) for v in SJ.values()))
# 硬排除 vs a 可有可无：S9 下 a 跟后两段本来就重叠（可自己当首段）的组数
n_all = n_ov = 0
for n, r in R:
    res = T.find_bounds(r); done, ks = res["done"], res["ks"]
    for a in ks:
        if a + 2 < len(done):
            n_all += 1
            lo = max(done[q]["lo"] for q in range(a, a + 3)); hi = min(done[q]["hi"] for q in range(a, a + 3))
            n_ov += lo <= hi
print("分界之后的组 %d 个，其中 a 跟后两段本来就重叠（原文『a 可有可无』下可以自己当中枢首段）%d 个" % (n_all, n_ov))
