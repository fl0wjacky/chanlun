"""D-4 核验（D-2′＋S5 确认⇔左 D2 已确认且右边已有 D2）：数 S5「确认后变」。
D-2′（Atlas 7843e28）：b 之后到当前的极值 e（L 刀取最高、H 刀取最低，持平取最早），有同级别中枢 X0≥b 且 X1≤e，b 就确认。
原：① D 前缀回放：S9（SAME_LEVEL＋D2），两种 a 口径。每张图在「每一笔终点的后一根」取前缀，整个重算。
D2 刀身份＝(bar, kind)；确认＝这把刀之后、下一把 D2 刀之前，走势层给出了第一个同级别中枢（seg_centers 里 X0 ≥ 刀、X1 ≤ 下一刀）。
S5 刀身份＝(bar, kind)。"""
import sys, os, json, gzip, statistics
from concurrent.futures import ProcessPoolExecutor
sys.path[:0] = [os.getcwd(), "tools"]
VAR = {"甲(小栋定)": dict(SAME_LEVEL_D6="fallback", SL_FIRST_EXEMPT=True)}
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
    prev_d2, prev_s5 = set(), set(); s5conf = {}; s5_gone_conf = []
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
                key = (lambda q: bars[q]["h"]) if b["kind"] == "L" else (lambda q: -bars[q]["l"])
                e = max(range(b["bar"] + 1, c), key=lambda q: (key(q), -q)) if c > b["bar"] + 1 else b["bar"]
                if any(z["X0"] >= b["bar"] and z["X1"] <= min(hi, e) for z in v["seg_centers"]):
                    conf[k] = c
        for k in prev_d2 - d2set:
            same_kind_new = any(x[1] == k[1] and x not in prev_d2 for x in d2set)
            if k in conf: gone_conf += 1
            else:
                gone_pending += 1; moved_pending += same_kind_new
        lost_d2 = sorted(prev_d2 - d2set)
        for k in prev_s5 - s5set:
            if k in s5conf: s5_gone_conf.append((k, c))
            left = [x for x in prev_d2 if x[0] < k[0]]; right = [x for x in prev_d2 if x[0] > k[0]]
            L = max(left) if left else None; Rr = min(right) if right else None
            if L in lost_d2: s5_changes["左端"] += 1
            elif Rr in lost_d2: s5_changes["右端"] += 1
            else: s5_changes["都不是"] += 1
        for k in s5set:
            if k in s5conf: continue
            L = [x for x in d2set if x[0] < k[0]]; R = [x for x in d2set if x[0] > k[0]]
            if L and R and max(L) in conf: s5conf[k] = c
        prev_d2, prev_s5 = d2set, s5set
    delays = [conf[k] - born[k] for k in conf]
    tail_pending = sum(1 for k in prev_d2 if k not in conf)
    return name, var, dict(gone_conf=gone_conf, gone_pending=gone_pending, moved_pending=moved_pending, delays=delays,
                           tail_pending=tail_pending, s5=s5_changes, n_conf=len(conf), s5gc=s5_gone_conf, n_s5conf=len(s5conf))
if __name__ == "__main__":
    args = [(it, var) for var in VAR for it in items()]
    agg = {v: dict(gone_conf=0, gone_pending=0, moved_pending=0, delays=[], tail_pending=0, s5={"左端": 0, "右端": 0, "都不是": 0}, n_conf=0) for v in VAR}
    with ProcessPoolExecutor(4) as ex:
        for name, var, d in ex.map(one, args):
            a = agg[var]
            for k in ("gone_conf", "gone_pending", "moved_pending", "tail_pending", "n_conf"): a[k] += d[k]
            a["delays"] += d["delays"]
            for k in a["s5"]: a["s5"][k] += d["s5"][k]
            print(var, name, d["gone_conf"], d["gone_pending"], "S5确认", d["n_s5conf"], "S5确认后变", d["s5gc"], flush=True)
    for var, a in agg.items():
        dl = a["delays"]
        print("【%s】确认后撤回 %d；待确认被撤 %d（其中同向新刀＝挪 %d）；确认 %d 把，延迟（按笔取前缀，单位 K 线）中位 %s 最大 %s；图尾待确认 %d；S5 刀事后变动 %s" % (
            var, a["gone_conf"], a["gone_pending"], a["moved_pending"], a["n_conf"], statistics.median(dl) if dl else "-", max(dl) if dl else "-", a["tail_pending"], a["s5"]))
