"""R-3：每个走势段，取段内最后两个线段高点、两个线段低点（走势层那套标准化线段的端点），照 L15 判型，跟现行段型比。"""
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
pair = collections.Counter(); tot = nojudge = 0; ex = []
for name, bars, tk in items:
    r = analyze(bars, tick=tick_of(tk)); v = T.trend_v3(r); done = T.find_bounds(r)["done"]
    for s in v["segments"]:
        if s["head"]:
            continue
        tot += 1
        inner = [d for d in done if d["i0"] >= s["i0"] and d["i1"] <= s["i1"]]
        highs = [d["p1"] for d in inner if T._is_up(d)]; lows = [d["p1"] for d in inner if not T._is_up(d)]
        cur = s["type"] + ("·升" if s["upgraded"] else "")
        if len(highs) < 2 or len(lows) < 2:
            nojudge += 1; pair[(cur, "不可判")] += 1; continue
        hh, hl = highs[-1] > highs[-2], lows[-1] > lows[-2]
        l15 = "上涨" if hh and hl else "下跌" if (not hh and not hl) else "盘整"
        pair[(cur, l15)] += 1
        if l15 != s["type"] and len(ex) < 4: ex.append((name, cur, l15))
same = sum(n for (c, l), n in pair.items() if l != "不可判" and c.split("·")[0] == l)
print("非图头走势段 %d：L15 不可判（段内高点或低点不足两个）%d；可判 %d，其中跟现行同型 %d、不同 %d" % (tot, nojudge, tot - nojudge, same, tot - nojudge - same))
for k, n in sorted(pair.items(), key=lambda x: -x[1]): print("  现行 %s → L15 %s：%d" % (k[0], k[1], n))
print("例", ex)
