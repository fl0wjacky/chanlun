# 第五批「盘整＋盘整」两个候选的影响面（只量不改）。用法：python3 notes/b5/pz_merge.py <线上快照.gz>
# 候选 1：相邻两段都是盘整 ⇒ 拿掉中间那一刀，整层照常重算（中枢跨过原分界重找、D3 照常合成、段型照常判），反复做到没有相邻盘整为止。
# 候选 2：拿掉那一刀，但不重算，并起来的那段直接记「盘整」（框不动）。
import sys, json, gzip, importlib, collections
sys.path[:0] = [".", "tools"]
from core.analyze import analyze, analyze_file
from config import tick_of
T = importlib.import_module("core.trend")
DATA = ["aaplusdt_1h.json","aaplusdt_2h.json","aaplusdt_30m.json","aaplusdt_4h.json","btc_4h.json","zec15.json","zec30_cut.json","zec_1h.json","zec_2h.json","zec_4h.json"]
syms = {"ZECUSDT": "zec", "BTCUSDT": "btc", "AAPLUSDT": "aaplusdt"}
snap = json.loads(gzip.open(sys.argv[1]).read())
ch = [(f, analyze_file(f)) for f in DATA] + [(k, analyze(snap[k]["bars"], tick=tick_of(syms[k.split()[0]] + "_.json"))) for k in sorted(snap)]
real_fb = T.find_bounds
def run_without(r, drop):
    def fb(*a, **k):
        res = real_fb(*a, **k)
        keep = [i for i, b in enumerate(res["bounds"]) if b["bar"] not in drop]
        return dict(res, bounds=[res["bounds"][i] for i in keep], ks=[res["ks"][i] for i in keep])
    T.find_bounds = fb
    try:
        return T.trend_v3(r)
    finally:
        T.find_bounds = real_fb
def pairs(v):
    s = v["segments"]
    return [y["i0"] for x, y in zip(s, s[1:]) if not x["head"] and x["type"] == "盘整" and y["type"] == "盘整"]
tot = collections.Counter(); rows = []
for name, r in ch:
    v0 = T.trend_v3(r); p0 = pairs(v0)
    if not p0:
        continue
    drop, v, rounds = set(), v0, 0
    while True:
        p = pairs(v)
        if not p or rounds > 20:
            break
        drop |= set(p); v = run_without(r, drop); rounds += 1
    t0 = collections.Counter(s["type"] + ("·升" if s["upgraded"] else "") for s in v0["segments"])
    t1 = collections.Counter(s["type"] + ("·升" if s["upgraded"] else "") for s in v["segments"])
    tot["图"] += 1; tot["原相邻盘整对"] += len(p0); tot["候选1 拿掉的刀"] += len(drop)
    tot["段数 改前"] += len(v0["segments"]); tot["段数 候选1"] += len(v["segments"]); tot["段数 候选2"] += len(v0["segments"]) - len(p0)
    tot["合成框 改前"] += len(v0["units"]); tot["合成框 候选1"] += len(v["units"])
    rows.append((name, len(p0), len(drop), len(v0["segments"]), len(v["segments"]), dict(t0), dict(t1)))
print(dict(tot))
for x in rows: print("  ", x)
