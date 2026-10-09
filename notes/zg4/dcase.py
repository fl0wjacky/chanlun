"""① D 确认后撤：逐处抓位置（刀、生于前缀、确认于前缀、撤之前/撤之后前缀）。用法：dcase.py <口径> <图名>...
原 dreplay：① D 前缀回放：S9（SAME_LEVEL＋D2），两种 a 口径。每张图在「每一笔终点的后一根」取前缀，整个重算。
D2 刀身份＝(bar, kind)；确认＝这把刀之后、下一把 D2 刀之前，走势层给出了第一个同级别中枢（seg_centers 里 X0 ≥ 刀、X1 ≤ 下一刀）。
S5 刀身份＝(bar, kind)。"""
import sys, os, json, gzip, statistics
from concurrent.futures import ProcessPoolExecutor
sys.path[:0] = [os.getcwd(), "tools"]
VAR = {"a进(S9底座)": dict(), "甲(小栋定)": dict(SAME_LEVEL_D6="fallback", SL_FIRST_EXEMPT=True)}
def items():
    snap = json.loads(gzip.open(os.environ["LIVE15"]).read())
    return [(k, None) for k in sorted(snap)] + [("data/" + f, f) for f in ["aaplusdt_1h", "aaplusdt_2h", "aaplusdt_30m", "aaplusdt_4h", "btc_4h", "zec15", "zec30_cut", "zec_1h", "zec_2h", "zec_4h"]]
def one(arg):
    (name, fn), var = arg
    from core.analyze import analyze
    import core.trend as T
    from config import tick_of
    syms = {"ZECUSDT": "zec", "BTCUSDT": "btc", "AAPLUSDT": "aaplusdt"}
    if fn: bars = json.load(open("data/%s.json" % fn)); tk = fn + ".json"
    else: bars = json.loads(gzip.open(os.environ["LIVE15"]).read())[name]["bars"]; tk = syms[name.split()[0]] + "_.json"
    T.SAME_LEVEL, T.SAME_LEVEL_D2 = True, True
    for k, v in VAR[var].items(): setattr(T, k, v)
    t = tick_of(tk); full = analyze(bars, tick=t)
    cuts = sorted({p["i1"] + 1 for p in full["pens"]} | {len(bars)})
    born, conf, gone_pending, gone_conf, moved_pending = {}, {}, 0, 0, 0
    s5_seen, s5_changes = {}, {"左端": 0, "右端": 0, "都不是": 0}
    prev_d2, prev_s5 = set(), set(); cases = []; pc = None
    for c in cuts:
        v = T.trend_v3(analyze(bars[:c], tick=t))
        d2 = [b for b in v["bounds"] if b.get("rule") == "D2-2"]
        d2set = {(b["bar"], b["kind"]) for b in d2}
        s5set = {(b["bar"], b["kind"]) for b in v["bounds"] if b.get("rule") == "S5"}
        for i, b in enumerate(d2):
            k = (b["bar"], b["kind"])
            born.setdefault(k, c)
            if k not in conf:
                hi = d2[i + 1]["bar"] if i + 1 < len(d2) else 10 ** 12
                if any(z["X0"] >= b["bar"] and z["X1"] <= hi for z in v["seg_centers"]):
                    conf[k] = c
        for k in prev_d2 - d2set:
            same_kind_new = any(x[1] == k[1] and x not in prev_d2 for x in d2set)
            if k in conf:
                gone_conf += 1
                rb, ra = analyze(bars[:pc], tick=t), analyze(bars[:c], tick=t)
                S = lambda r: [(x["i0"], x["i1"]) for x in r["segs"] if not x.get("live")]
                sb, sa = S(rb), S(ra)
                lo = max([x for x in prev_d2 if x[0] < k[0]], default=(0, ""))[0]   # 从上一把 D2 刀起
                used = [x for x in sb if x[1] >= lo]
                gone = [x for x in used if x not in sa]
                cases.append(dict(cut=k, born=born[k], conf=conf[k], before=pc, after=c, n=len(bars), tick=t,
                                  segs_changed=gone, why="②S-13 线段被改" if gone else "①D-2 条件不够"))
            else:
                gone_pending += 1; moved_pending += same_kind_new
        lost_d2 = sorted(prev_d2 - d2set)
        for k in prev_s5 - s5set:
            left = [x for x in prev_d2 if x[0] < k[0]]; right = [x for x in prev_d2 if x[0] > k[0]]
            L = max(left) if left else None; Rr = min(right) if right else None
            if L in lost_d2: s5_changes["左端"] += 1
            elif Rr in lost_d2: s5_changes["右端"] += 1
            else: s5_changes["都不是"] += 1
        prev_d2, prev_s5 = d2set, s5set; pc = c
    delays = [conf[k] - born[k] for k in conf]
    tail_pending = sum(1 for k in prev_d2 if k not in conf)
    return name, var, dict(gone_conf=gone_conf, gone_pending=gone_pending, moved_pending=moved_pending, delays=delays,
                           tail_pending=tail_pending, s5=s5_changes, n_conf=len(conf), cases=cases)
if __name__ == "__main__":
    var, names = sys.argv[1], set(sys.argv[2:])
    args = [(it, var) for it in items() if it[0] in names]
    with ProcessPoolExecutor(2) as ex:
        for name, var, d in ex.map(one, args):
            for x in d["cases"]: print(var, name, x, flush=True)
