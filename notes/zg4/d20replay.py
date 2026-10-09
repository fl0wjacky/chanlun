"""总纲④ 4.x：D2-0 标准化线段的前缀回放（只读）。每张图按「每一笔的终点后一根」取前缀，
比相邻两个前缀：已完成的原始线段集合、已完成的标准化线段集合，谁少了（＝已确认又变）。"""
import sys, os, json, gzip
from concurrent.futures import ProcessPoolExecutor
sys.path[:0] = [os.getcwd(), "tools"]

def items():
    snap = json.loads(gzip.open(os.environ["LIVE15"]).read())
    syms = {"ZECUSDT": "zec", "BTCUSDT": "btc", "AAPLUSDT": "aaplusdt"}
    out = [(k, None, syms[k.split()[0]] + "_.json") for k in sorted(snap)]
    for fn in ["aaplusdt_1h", "aaplusdt_2h", "aaplusdt_30m", "aaplusdt_4h", "btc_4h", "zec15", "zec30_cut", "zec_1h", "zec_2h", "zec_4h"]:
        out.append(("data/" + fn, fn, fn + ".json"))
    return out

def one(it):
    name, fn, tk = it
    from core.analyze import analyze
    import core.trend as T
    from config import tick_of
    if fn is None:
        bars = json.loads(gzip.open(os.environ["LIVE15"]).read())[name]["bars"]
    else:
        bars = json.load(open("data/%s.json" % fn))
    t = tick_of(tk)
    full = analyze(bars, tick=t)
    cuts = sorted({p["i1"] + 1 for p in full["pens"]} | {len(bars)})
    prevR = prevS = None
    raw_w = std_w = std_only = 0
    ex = []
    for c in cuts:
        r = analyze(bars[:c], tick=t)
        rl = [(s["i0"], s["i1"]) for s in r["segs"] if not s.get("live")]
        dl = [(d["i0"], d["i1"]) for d in T.find_bounds(r)["done"] if not d.get("live")]
        R, S = set(rl[:-1]), set(dl[:-1])                # 最后一条已完成线段可能还是暂定的：不算「已确认」
        if prevR is not None:
            lr, ls = prevR - set(rl), prevS - set(dl)     # 上一刻已确认的，这一刻连「最后一条」都不是了 ⇒ 撤了
            raw_w += len(lr); std_w += len(ls)
            if ls and not lr:
                std_only += len(ls)
                if len(ex) < 3: ex.append((c, sorted(ls)[:2], sorted(S - prevS)[:2]))
        prevR, prevS = R, S
    return name, len(cuts), raw_w, std_w, std_only, ex

if __name__ == "__main__":
    tot = [0, 0, 0, 0]
    with ProcessPoolExecutor(4) as ex:
        for name, n, a, b, c, e in ex.map(one, items()):
            print(name, "前缀", n, "原始撤", a, "标准化撤", b, "其中原始没撤的", c, e, flush=True)
            for i, v in enumerate((n, a, b, c)): tot[i] += v
    print("合计 前缀", tot[0], "原始撤", tot[1], "标准化撤", tot[2], "其中原始没撤的", tot[3])
