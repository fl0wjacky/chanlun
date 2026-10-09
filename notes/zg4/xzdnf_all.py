"""（全量版）D2-5 档 3 下全部小转大二类过 ④′ 不看未来：按笔取前缀，第一次出现以后每个前缀都在、位置价格不变（定稿口径＋锁＋D25_FILL=3）。"""
import sys, os, json, gzip
from concurrent.futures import ProcessPoolExecutor
sys.path[:0] = [os.getcwd(), "tools", os.path.dirname(os.path.abspath(__file__))]
TARGETS = {"ZECUSDT 15m": [(5944, "二卖"), (13648, "二买")], "ZECUSDT 30m": [(6824, "二买")],
           "data/zec15": [(6743, "二卖"), (14447, "二买")], "data/zec30_cut": [(6921, "二买")]}
def one(name):
    from core.analyze import analyze
    import core.trend as T, core.pen as PEN
    from config import tick_of
    T.SAME_LEVEL = T.SAME_LEVEL_D2 = True; T.SAME_LEVEL_D6 = "fallback"; T.SL_FIRST_EXEMPT = True; T.SAME_LEVEL_DEATH = True
    PEN.PEN_FINAL_LOCK = True; T.D25_FILL = 3
    syms = {"ZECUSDT": "zec", "BTCUSDT": "btc", "AAPLUSDT": "aaplusdt"}
    if name.startswith("data/"): bars = json.load(open(name + ".json")); tk = name[5:] + ".json"
    else: bars = json.loads(gzip.open(os.environ["LIVE15"]).read())[name]["bars"]; tk = syms[name.split()[0]] + "_.json"
    t = tick_of(tk); full = analyze(bars, tick=t)
    targets = [(x["bar"], x["kind"]) for x in T.trend_v3(full).get("xzd_seconds", [])]     # 全图终版里的每一颗都查
    if not targets:
        return name, {}, []
    cuts = sorted({p["i1"] + 1 for p in full["pens"]} | {len(bars)})
    first, bad = {}, []
    for c in cuts:
        xs = {(x["bar"], x["kind"]): x["price"] for x in T.trend_v3(analyze(bars[:c], tick=t)).get("xzd_seconds", [])}
        for k in targets:
            if k in xs:
                first.setdefault(k, (c, xs[k]))
                if xs[k] != first[k][1]: bad.append((k, c, "价变了"))
            elif k in first:
                bad.append((k, c, "消失了"))
    return name, {k: first.get(k, (None,))[0] for k in targets}, bad[:3]
if __name__ == "__main__":
    from dreplay import items
    names = [n for n, _ in items()]
    tot = probs = 0
    with ProcessPoolExecutor(6) as ex:
        for name, f, bad in ex.map(one, names):
            tot += len(f); probs += len(bad)
            if f: print(name, "首次出现于前缀", f, "问题", bad if bad else "无", flush=True)
    print("合计 二类 %d 颗，不看未来问题 %d" % (tot, probs))
