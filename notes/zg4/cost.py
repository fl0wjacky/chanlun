"""三件各自 B 方案的代价：25 张里多少张、多少刀变（只读，开关是 trend_v3 现成的探针参数）。"""
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
def key(v): return [(b["bar"], b["kind"], round(b["price"], 8)) for b in v["bounds"]]
def types(v): return [(s["i0"], s["i1"], s["type"], s["upgraded"]) for s in v["segments"]]
for lab, kw in (("①B 去掉 D2-7 撤回", dict(check_empty=False)), ("②B 走势层改用原始线段", dict(standardize=False))):
    ch = cuts = tot = seg_ch = 0; ex = []
    for name, bars, tk in items:
        r = analyze(bars, tick=tick_of(tk))
        a, b = T.trend_v3(r), T.trend_v3(r, **kw)
        ka, kb = set(key(a)), set(key(b)); tot += len(ka)
        d = len(ka ^ kb); cuts += d
        sd = len(set(types(a)) ^ set(types(b)))
        if d or sd: ch += 1; seg_ch += sd; ex.append("%s 刀±%d" % (name, d))
    print(lab, "：变的图 %d/25，刀增删合计 %d（现 %d 刀），走势段增删合计 %d" % (ch, cuts, tot, seg_ch), ex[:8])
# ③ 中间段 / 末段：没标升级却 ≥2 个本级别中枢的盘整段
for name, bars, tk in items:
    r = analyze(bars, tick=tick_of(tk)); v = T.trend_v3(r)
    for g, x in enumerate(v["segments"]):
        if x["type"] == "盘整" and not x["head"] and not x["upgraded"]:
            zz = [z for z in v["seg_centers"] if z["seg"] == g]
            if len(zz) >= 2: print("③", name, "段", g, "中枢", len(zz), "末段" if x["live"] else "中间", x["i0"], x["i1"], "关系", [z.get("rel") for z in zz])
