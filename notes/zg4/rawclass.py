"""原始线段撤销逐条分类：被撤的那段，在「用最终的笔」划出来的线段里有没有（有 ⇒ 只是暂时被别的盖了；没有 ⇒ 当时是靠还没定的尾笔才确认的）。
另记：撤的那一刻，段后面的笔是否有被改的（第一处笔不同的位置在段后面）。"""
import sys, os, json, gzip
from concurrent.futures import ProcessPoolExecutor
sys.path[:0] = [os.getcwd(), "tools"]
def one(name):
    from core.analyze import analyze
    from config import tick_of
    snap = json.loads(gzip.open(os.environ["LIVE15"]).read())
    syms = {"ZECUSDT": "zec", "BTCUSDT": "btc", "AAPLUSDT": "aaplusdt"}
    if name.startswith("data/"):
        bars = json.load(open("data/%s.json" % name[5:])); tk = name[5:] + ".json"
    else:
        bars = snap[name]["bars"]; tk = syms[name.split()[0]] + "_.json"
    t = tick_of(tk); full = analyze(bars, tick=t)
    final = {(s["i0"], s["i1"]) for s in full["segs"] if not s.get("live")}
    P = lambda p: (p["i0"], p["i1"], round(p["p1"], 8))
    cuts = sorted({p["i1"] + 1 for p in full["pens"]} | {len(bars)})
    prev = None; out = []
    for c in cuts:
        r = analyze(bars[:c], tick=t)
        rl = [s for s in r["segs"] if not s.get("live")]
        if prev is not None:
            for g in sorted(prev[0] - {(s["i0"], s["i1"]) for s in rl}):
                seg = next(s for s in prev[1] if (s["i0"], s["i1"]) == g)
                fp = full["pens"]; k = next((i for i, (a, b) in enumerate(zip(prev[2], fp)) if P(a) != P(b)), len(prev[2]))
                out.append((c, g, seg.get("case"), g in final, k > seg["PI1"]))
        prev = ({(s["i0"], s["i1"]) for s in rl[:-1]}, rl, r["pens"])
    return name, out
if __name__ == "__main__":
    names = ["AAPLUSDT 15m", "AAPLUSDT 30m", "BTCUSDT 15m", "BTCUSDT 30m", "ZECUSDT 15m", "data/aaplusdt_30m", "data/zec15"]
    tot = {}
    with ProcessPoolExecutor(2) as ex:
        for name, out in ex.map(one, names):
            for c, g, case, inf, after in out:
                k = ("最终笔下这段在" if inf else "最终笔下没有这段") + ("，当时尾笔跟最终的不同" if after else "，当时尾笔跟最终一样")
                tot[k] = tot.get(k, 0) + 1
                print(name, "前缀", c, "撤", g, "case", case, k, flush=True)
    print("合计", tot)
