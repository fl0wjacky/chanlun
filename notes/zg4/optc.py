"""C：立刀那一刻就要求「上一刀 → 这一刀之间有中枢」，不满足就不立这一刀（上一刀不动、不撤）。只读量，引擎不改：
把 find_bounds 的源码拷一份，D2-7 那一支从「撤上一刀」改成「这一刀不立」。"""
import sys, os, json, gzip, inspect, statistics
sys.path[:0] = [os.getcwd(), "tools"]
from core.analyze import analyze
import core.trend as T
from config import tick_of
src = inspect.getsource(T.find_bounds)
old = src[src.index("                if not [q for q in zz if q[\"PI0\"] >= lo and q[\"PI1\"] <= j]:"):src.index("            ks.append(j + 1)")]
new = '''                if not [q for q in zz if q["PI0"] >= lo and q["PI1"] <= j]:
                    continue
'''
assert old.count("ks.pop()") == 1
ns = {}
exec(compile(src.replace(old, new).replace("def find_bounds(", "def find_bounds_c("), "optc", "exec"), T.__dict__, ns)
C = ns["find_bounds_c"]
orig = T.find_bounds
snap = json.loads(gzip.open(os.environ["LIVE15"]).read())
syms = {"ZECUSDT": "zec", "BTCUSDT": "btc", "AAPLUSDT": "aaplusdt"}
items = [(k, snap[k]["bars"], syms[k.split()[0]] + "_.json") for k in sorted(snap)]
for fn in ["aaplusdt_1h", "aaplusdt_2h", "aaplusdt_30m", "aaplusdt_4h", "btc_4h", "zec15", "zec30_cut", "zec_1h", "zec_2h", "zec_4h"]:
    items.append(("data/" + fn, json.load(open("data/%s.json" % fn)), fn + ".json"))
key = lambda v: {(b["bar"], b["kind"]) for b in v["bounds"]}
tot = dict(ch=0, cuts=0, ret_a=0, ret_c=0, zero_mid=0, zero_mid_a=0, nb_a=0, nb_c=0); gaps_a, gaps_c = [], []; ex = []
def gaps(v, n):
    es = [b["pullback_end_bar"] for b in v["bounds"] if b.get("rule") == "D2-2"]
    return [b - a for a, b in zip([0] + es, es + [n])]
for name, bars, tk in items:
    r = analyze(bars, tick=tick_of(tk))
    a = T.trend_v3(r)
    T.find_bounds = C
    try: c = T.trend_v3(r)
    finally: T.find_bounds = orig
    d = key(a) ^ key(c)
    tot["cuts"] += len(d); tot["ch"] += bool(d)
    tot["ret_a"] += len(a["retracted"]); tot["ret_c"] += len(c["retracted"])
    tot["nb_a"] += len(a["bounds"]); tot["nb_c"] += len(c["bounds"])
    for v, k in ((a, "zero_mid_a"), (c, "zero_mid")):
        tot[k] += sum(1 for g, x in enumerate(v["segments"]) if not x["head"] and not x["live"] and not [z for z in v["seg_centers"] if z["seg"] == g])
    ga, gc = gaps(a, len(bars)), gaps(c, len(bars)); gaps_a += ga; gaps_c += gc
    if d:
        ex.append("%s 刀 %d→%d（−%s ＋%s）最长无刀 %d→%d 根" % (name, len(a["bounds"]), len(c["bounds"]),
                  sorted((b, k) for b, k in key(a) - key(c))[:3], sorted((b, k) for b, k in key(c) - key(a))[:3], max(ga), max(gc)))
    if name in ("ZECUSDT 15m", "AAPLUSDT 15m", "data/zec15"):
        print(name, "C 下分界：", [(b["kind"], b["price"]) for b in c["bounds"]])
        print(name, "现行分界：", [(b["kind"], b["price"]) for b in a["bounds"]])
        print(name, "C 下段型：", [(s["type"] + ("·升" if s["upgraded"] else ""), s["i0"], s["i1"]) for s in c["segments"]])
print(tot)
print("两刀之间（确立时刻）间隔 中位 现行 %d / C %d；最大 现行 %d / C %d" % (statistics.median(gaps_a), statistics.median(gaps_c), max(gaps_a), max(gaps_c)))
for e in ex: print(" ", e)
