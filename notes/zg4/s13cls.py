"""S-13 第 1 条：那 12 次线段撤销，撤的那一步笔序列改到倒数第几笔（深度＝上一刻笔数 − 第一处不同的下标）。
深度 1、2 ＝改的是未定稿的笔（P1：最后一笔、倒数第二笔不定稿）；深度 ≥3 ＝改了定稿的笔（P2 违反）。"""
import sys, os, json, gzip
sys.path[:0] = [os.getcwd(), "tools"]
from core.analyze import analyze
from config import tick_of
snap = json.loads(gzip.open(os.environ["LIVE15"]).read())
syms = {"ZECUSDT": "zec", "BTCUSDT": "btc", "AAPLUSDT": "aaplusdt"}
P = lambda p: (p["i0"], p["i1"], round(p["p1"], 8))
res = {"未定稿": 0, "定稿后改写": 0}
for name in ["AAPLUSDT 15m", "AAPLUSDT 30m", "BTCUSDT 15m", "BTCUSDT 30m", "ZECUSDT 15m", "data/aaplusdt_30m", "data/zec15"]:
    if name.startswith("data/"): bars = json.load(open("data/%s.json" % name[5:])); tk = name[5:] + ".json"
    else: bars = snap[name]["bars"]; tk = syms[name.split()[0]] + "_.json"
    t = tick_of(tk); full = analyze(bars, tick=t)
    cuts = sorted({p["i1"] + 1 for p in full["pens"]} | {len(bars)})
    prev = None
    for c in cuts:
        r = analyze(bars[:c], tick=t); rl = [s for s in r["segs"] if not s.get("live")]
        if prev is not None:
            gone = prev[0] - {(s["i0"], s["i1"]) for s in rl}
            if gone:
                k = next((i for i, (a, b) in enumerate(zip(prev[1], r["pens"])) if P(a) != P(b)), min(len(prev[1]), len(r["pens"])))
                d = len(prev[1]) - k
                key = "未定稿" if d <= 2 else "定稿后改写"
                res[key] += len(gone)
                print(name, "前缀", c, "撤", sorted(gone), "改到倒数第", d, "笔 →", key, flush=True)
        prev = ({(s["i0"], s["i1"]) for s in rl[:-1]}, r["pens"])
print("合计", res)
