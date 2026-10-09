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
    kw = dict(SAME_LEVEL=True, SAME_LEVEL_D2=True, **kw)
    old = {k: getattr(T, k) for k in kw}
    for k, v in kw.items(): setattr(T, k, v)
    try: return {n: T.trend_v3(r) for n, r in R}
    finally:
        for k, v in old.items(): setattr(T, k, v)
base = run()
def show(lab, o):
    ch = sum(1 for n in o if key(o[n]) != key(base[n]) or [s["type"] for s in o[n]["segments"]] != [s["type"] for s in base[n]["segments"]])
    t = collections.Counter(s["type"] for v in o.values() for s in v["segments"])
    trend = t["上涨"] + t["下跌"]
    print("%s：刀 %d（对 S9 底座增删 %d），变的图 %d/25；段型 上涨 %d、下跌 %d、盘整 %d、无中枢 %d（其中图头 %d）；趋势段合计 %d（底座 %d，少 %d）" % (
        lab, sum(len(v["bounds"]) for v in o.values()), sum(len(key(o[n]) ^ key(base[n])) for n in o), ch,
        t["上涨"], t["下跌"], t["盘整"], t["无中枢"], sum(1 for v in o.values() for s in v["segments"] if s["type"] == "无中枢" and s["head"]),
        trend, bt, bt - trend))
tb = collections.Counter(s["type"] for v in base.values() for s in v["segments"]); bt = tb["上涨"] + tb["下跌"]
show("S9 底座（不限方向）", base)
show("甲（fallback＋甲S-2 豁免）", run(SAME_LEVEL_D6="fallback", SL_FIRST_EXEMPT=True))
show("乙′（不带 -5）", run(R6_YI_PRIME=True))
show("乙′（带 -5）", run(R6_YI_PRIME=True, SL_FIRST_EXEMPT=True))
show("乙′（带 -5＋-6）", run(R6_YI_PRIME=True, SL_FIRST_EXEMPT=True, R6_YI_FALLBACK=True))
show("参照：甲 fallback 不带豁免（764f418）", run(SAME_LEVEL_D6="fallback"))
