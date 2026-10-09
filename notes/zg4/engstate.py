"""引擎内 state（_sl_state）前缀回放：定稿口径全开＋锁。数 ①确认后消失（D2／S5）②确认→待确认 回翻（无状态实现特有的风险）③确认数、图尾待确认。"""
import sys, os, json, gzip
from concurrent.futures import ProcessPoolExecutor
sys.path[:0] = [os.getcwd(), "tools", os.path.dirname(__file__)]
from dreplay import items
def one(it):
    name, fn = it
    from core.analyze import analyze
    import core.trend as T, core.pen as PEN
    from config import tick_of
    T.SAME_LEVEL = T.SAME_LEVEL_D2 = True; T.SAME_LEVEL_D6 = "fallback"; T.SL_FIRST_EXEMPT = True; PEN.PEN_FINAL_LOCK = True

    syms = {"ZECUSDT": "zec", "BTCUSDT": "btc", "AAPLUSDT": "aaplusdt"}
    if fn: bars = json.load(open("data/%s.json" % fn)); tk = fn + ".json"
    else: bars = json.loads(gzip.open(os.environ["LIVE15"]).read())[name]["bars"]; tk = syms[name.split()[0]] + "_.json"
    t = tick_of(tk); full = analyze(bars, tick=t)
    cuts = sorted({p["i1"] + 1 for p in full["pens"]} | {len(bars)})
    o = {"D2消失": 0, "S5消失": 0, "D2回翻": 0, "S5回翻": 0, "D2确认": set(), "S5确认": set()}; ex = []
    prev = {}; born = {}; confat = {}
    for c in cuts:
        bs = T.trend_v3(analyze(bars[:c], tick=t))["bounds"]
        cur = {(b["bar"], b["kind"], b["rule"]): b.get("state") for b in bs}
        if any(s is None for s in cur.values()): raise SystemExit("有刀没 state：%s %d" % (name, c))
        for k, s in prev.items():
            if s != "confirmed": continue
            tag = "D2" if k[2] == "D2-2" else "S5"
            if k not in cur: o[tag + "消失"] += 1; ex.append((tag, "消失", k, c))
            elif cur[k] != "confirmed": o[tag + "回翻"] += 1; ex.append((tag, "回翻", k, c))
        for k, s in cur.items():
            born.setdefault(k, c)
            if s == "confirmed": confat.setdefault(k, c)
            if s == "confirmed": o[("D2" if k[2] == "D2-2" else "S5") + "确认"].add(k)
        prev = cur
    o["D2延迟"] = [confat[k] - born[k] for k in confat if k[2] == "D2-2"]
    if o["D2延迟"]:
        mk = max((k for k in confat if k[2] == "D2-2"), key=lambda k: confat[k] - born[k])
        ex.insert(0, ("最长延迟", mk, born[mk], confat[mk], confat[mk] - born[mk]))
    o["D2确认"] = len(o["D2确认"]); o["S5确认"] = len(o["S5确认"])
    o["图尾待确认D2"] = sum(1 for k, s in prev.items() if k[2] == "D2-2" and s == "pending")
    return name, o, ex[:3]
if __name__ == "__main__":
    tot = {}
    with ProcessPoolExecutor(6) as pool:
        for name, o, ex in pool.map(one, items()):
            print(name, {k: v for k, v in o.items() if k != "D2延迟"}, ex, flush=True)
            for k, v in o.items(): tot[k] = tot.get(k, [] if k == "D2延迟" else 0) + v
    import statistics; dl = tot.pop("D2延迟")
    print("合计", tot, "D2延迟 中位", statistics.median(dl), "最大", max(dl))
