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
seg = lambda v: {(s["i0"], s["i1"], s["type"]) for s in v["segments"]}
def run(d6):
    T.SAME_LEVEL, T.SAME_LEVEL_D2, T.SAME_LEVEL_D6 = True, True, d6
    try: return {n: T.trend_v3(r) for n, r in R}
    finally: T.SAME_LEVEL, T.SAME_LEVEL_D2, T.SAME_LEVEL_D6 = False, False, None
base = run(None)
for lab, d6 in (("S9 不限方向（乙粗版，＝底座）", None), ("S9＋D6 strict（甲）", "strict"), ("S9＋D6 fallback（甲，照 D6-4 退回）", "fallback")):
    o = run(d6)
    ch = sum(1 for n in base if key(base[n]) != key(o[n]) or seg(base[n]) != seg(o[n]))
    t = collections.Counter(s["type"] for v in o.values() for s in v["segments"])
    print("%s：跟底座比变的图 %d/25，刀 %d（增删 %d），段增删 %d；段型 %s" % (lab, ch, sum(len(v["bounds"]) for v in o.values()),
          sum(len(key(base[n]) ^ key(o[n])) for n in base), sum(len(seg(base[n]) ^ seg(o[n])) for n in base), dict(t)))
