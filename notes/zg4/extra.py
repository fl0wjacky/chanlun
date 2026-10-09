import sys, os, json, gzip, statistics
sys.path[:0] = [os.getcwd(), "tools"]
from core.analyze import analyze
import core.trend as T
from config import tick_of
snap = json.loads(gzip.open(os.environ["LIVE15"]).read())
syms = {"ZECUSDT": "zec", "BTCUSDT": "btc", "AAPLUSDT": "aaplusdt"}
items = [(k, snap[k]["bars"], syms[k.split()[0]] + "_.json") for k in sorted(snap)]
for fn in ["aaplusdt_1h", "aaplusdt_2h", "aaplusdt_30m", "aaplusdt_4h", "btc_4h", "zec15", "zec30_cut", "zec_1h", "zec_2h", "zec_4h"]:
    items.append(("data/" + fn, json.load(open("data/%s.json" % fn)), fn + ".json"))
delays = []; zero_mid_B = 0; reasons = {}
for name, bars, tk in items:
    r = analyze(bars, tick=tick_of(tk)); v = T.trend_v3(r); done = T.find_bounds(r)["done"]
    # ①A：分界确立以后，等到它后面出了第一个本级别中枢（中枢最后一根）才算确认 —— 晚了多少根
    for b in v["bounds"]:
        nxt = [z for z in v["seg_centers"] if z["X0"] >= b["bar"] and not z.get("live")]
        if not nxt: continue
        delays.append(max(0, min(z["X1"] for z in nxt) - b.get("pullback_end_bar", b["bar"])))
    # ①B：去掉 D2-7 以后，中间段 0 个中枢
    vb = T.trend_v3(r, check_empty=False)
    for g, x in enumerate(vb["segments"]):
        if not x["head"] and not x["live"] and not [z for z in vb["seg_centers"] if z["seg"] == g]: zero_mid_B += 1
    # ③：多中枢盘整段为什么没合成
    for g, x in enumerate(v["segments"]):
        if x["type"] == "盘整" and not x["head"] and not x["upgraded"]:
            zz = sorted([z for z in v["seg_centers"] if z["seg"] == g], key=lambda z: z["X0"])
            if len(zz) < 2: continue
            nseg = sum(1 for d in done if d["i0"] >= zz[0]["X0"] and d["i1"] <= zz[-1]["X1"])
            why = "末段、最后一个中枢还在走（D3-4）" if x["live"] and zz[-1].get("live") else ("不足 9 段" if nseg < 9 else "≥9 段但三组无重叠")
            reasons[why] = reasons.get(why, 0) + 1
print("①A 确认晚了（根）：n=%d 中位 %d 最大 %d，0 根的 %d" % (len(delays), statistics.median(delays), max(delays), sum(1 for d in delays if d == 0)))
print("①B 去掉 D2-7 以后中间段 0 中枢：", zero_mid_B)
print("③ 没合成的原因：", reasons)
