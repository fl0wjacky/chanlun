"""D2-5 补位量数（只改标注）：定稿口径＋锁，D25_FILL 0／2／3。断言刀位置、走势段三档逐项相同；报每张图改了几把标注、标注分布。"""
import sys, os, json, gzip
sys.path[:0] = [os.getcwd(), "tools", os.path.dirname(os.path.abspath(__file__))]
from dreplay import items
from core.analyze import analyze
import core.trend as T, core.pen as PEN
from config import tick_of
T.SAME_LEVEL = T.SAME_LEVEL_D2 = True; T.SAME_LEVEL_D6 = "fallback"; T.SL_FIRST_EXEMPT = True; T.SAME_LEVEL_DEATH = True
PEN.PEN_FINAL_LOCK = True
syms = {"ZECUSDT": "zec", "BTCUSDT": "btc", "AAPLUSDT": "aaplusdt"}
snap = json.loads(gzip.open(os.environ["LIVE15"]).read())
hist = {0: {}, 2: {}, 3: {}}; ch2 = ch3 = 0; rows = []; trans = {}
for name, fn in items():
    bars = json.load(open("data/%s.json" % fn)) if fn else snap[name]["bars"]
    tk = (fn + ".json") if fn else syms[name.split()[0]] + "_.json"
    r = analyze(bars, tick=tick_of(tk)); out = {}
    for f in (0, 2, 3):
        T.D25_FILL = f; out[f] = T.trend_v3(r)
    T.D25_FILL = 0
    pos = {f: [(b["bar"], b["kind"], b["rule"]) for b in out[f]["bounds"]] for f in out}
    seg = {f: [(s["i0"], s["i1"], s["type"]) for s in out[f]["segments"]] for f in out}
    assert pos[0] == pos[2] == pos[3], "刀动了 %s" % name
    assert seg[0] == seg[2] == seg[3], "走势段动了 %s" % name
    d = {f: [b.get("death") for b in out[f]["bounds"]] for f in out}
    for f in out:
        for x in d[f]: hist[f][x] = hist[f].get(x, 0) + 1
    n2 = sum(a != b for a, b in zip(d[0], d[2])); n3 = sum(a != b for a, b in zip(d[0], d[3]))
    for a, b in zip(d[0], d[3]):
        if a != b: trans[(a, b)] = trans.get((a, b), 0) + 1
    ch2 += n2; ch3 += n3
    if n2 or n3: rows.append((name, n2, n3))
print("刀位置、走势段：三档逐项相同 ✓（25 张）")
for nm, n2, n3 in rows: print("  %s：-2 改 %d、再加 -3 改 %d" % (nm, n2, n3))
print("改标注合计：-1→-2 %d 把；-1→-2→-3 %d 把" % (ch2, ch3))
for f in (0, 2, 3): print("标注分布 FILL=%d" % f, dict(sorted(hist[f].items(), key=lambda x: -x[1])))
print("改成了什么（0→3）", trans)
