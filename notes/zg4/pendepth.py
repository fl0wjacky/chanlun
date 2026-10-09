"""「笔定稿」是哪一刻：K 线前缀往后长的时候，笔序列最远改到倒数第几笔（深度＝上一刻笔数 − 第一处不同的下标）。"""
import sys, os, json, gzip
from concurrent.futures import ProcessPoolExecutor
sys.path[:0] = [os.getcwd(), "tools"]
def items():
    snap = json.loads(gzip.open(os.environ["LIVE15"]).read())
    out = [(k, None) for k in sorted(snap)]
    return out + [("data/" + f, f) for f in ["aaplusdt_1h", "aaplusdt_2h", "aaplusdt_30m", "aaplusdt_4h", "btc_4h", "zec15", "zec30_cut", "zec_1h", "zec_2h", "zec_4h"]]
def one(it):
    name, fn = it
    from core.analyze import analyze
    from config import tick_of
    syms = {"ZECUSDT": "zec", "BTCUSDT": "btc", "AAPLUSDT": "aaplusdt"}
    if fn: bars = json.load(open("data/%s.json" % fn)); tk = fn + ".json"
    else: bars = json.loads(gzip.open(os.environ["LIVE15"]).read())[name]["bars"]; tk = syms[name.split()[0]] + "_.json"
    t = tick_of(tk); full = analyze(bars, tick=t)
    cuts = sorted({p["i1"] + 1 for p in full["pens"]} | {len(bars)})
    P = lambda p: (p["i0"], p["i1"], round(p["p1"], 8))
    prev = None; hist = {}
    for c in cuts:
        pens = analyze(bars[:c], tick=t)["pens"]
        if prev is not None:
            k = next((i for i, (a, b) in enumerate(zip(prev, pens)) if P(a) != P(b)), min(len(prev), len(pens)))
            if k < len(prev):
                d = len(prev) - k; hist[d] = hist.get(d, 0) + 1
        prev = pens
    return name, hist
if __name__ == "__main__":
    tot = {}
    with ProcessPoolExecutor(2) as ex:
        for name, h in ex.map(one, items()):
            print(name, dict(sorted(h.items())), flush=True)
            for d, n in h.items(): tot[d] = tot.get(d, 0) + n
    print("合计（改到倒数第几笔 → 次数）", dict(sorted(tot.items())))
