"""③B：扩展链里任意连续 9 段、3+3+3 三组有公共重叠就合成（取最早的一处），其余照现行（不足 9 段不合、末段 D3-4 不合）。"""
import sys, os, json, gzip
sys.path[:0] = [os.getcwd(), "tools"]
from core.analyze import analyze
import core.trend as T
from config import tick_of
snap = json.loads(gzip.open(os.environ["LIVE15"]).read())
syms = {"ZECUSDT": "zec", "BTCUSDT": "btc", "AAPLUSDT": "aaplusdt"}
items = [(k, snap[k]["bars"], syms[k.split()[0]] + "_.json") for k in sorted(snap)]
for fn in ["aaplusdt_1h", "aaplusdt_2h", "aaplusdt_30m", "aaplusdt_4h", "btc_4h", "zec15", "zec30_cut", "zec_1h", "zec_2h", "zec_4h"]:
    items.append(("data/" + fn, json.load(open("data/%s.json" % fn)), fn + ".json"))
orig = T._regroup
def slide(done, a, b):
    for s in range(a, b - 7):
        hz = orig(done, s, b)
        if hz: return hz
    return None
key = lambda v: {(x["bar"], x["kind"]) for x in v["bounds"]}
typ = lambda v: [(s["i0"], s["i1"], s["type"], s["upgraded"]) for s in v["segments"]]
ch = cuts = 0; segtype = 0; ex = []; still = 0
for name, bars, tk in items:
    r = analyze(bars, tick=tick_of(tk)); a = T.trend_v3(r)
    T._regroup = slide
    try: b = T.trend_v3(r)
    finally: T._regroup = orig
    d = len(key(a) ^ key(b))
    ta, tb = typ(a), typ(b)
    sd = len(set(ta) - set(tb))
    if d or sd: ch += 1; ex.append("%s 刀±%d 段变%d" % (name, d, sd))
    cuts += d; segtype += sd
    for g, x in enumerate(b["segments"]):
        if x["type"] == "盘整" and not x["head"] and not x["upgraded"] and len([z for z in b["seg_centers"] if z["seg"] == g]) >= 2: still += 1
print("③B 任意连续 9 段：变的图 %d/25，刀增删 %d，走势段（起止/段型/升级）变了的 %d 段；之后仍「多中枢没升级」的盘整 %d 段" % (ch, cuts, segtype, still))
print(ex)
