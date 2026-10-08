# 第五批 ② 那 5 条的影响面（只量不改）。在仓根跑：python3 <本文件> <线上快照.gz>
# 每条：A＝现行；B＝另一档（口径见各节注释），25 张（data/ 10 份＋线上 10-07 快照 15 张），读法 A，6 根。
import sys, json, gzip, importlib, collections, datetime as D
sys.path[:0] = [".", "tools"]
from core.analyze import analyze, analyze_file
from config import tick_of
T = importlib.import_module("core.trend")
S = importlib.import_module("core.signals")
DATA = ["aaplusdt_1h.json", "aaplusdt_2h.json", "aaplusdt_30m.json", "aaplusdt_4h.json", "btc_4h.json",
        "zec15.json", "zec30_cut.json", "zec_1h.json", "zec_2h.json", "zec_4h.json"]
syms = {"ZECUSDT": "zec", "BTCUSDT": "btc", "AAPLUSDT": "aaplusdt"}
snap = json.loads(gzip.open(sys.argv[1]).read())
charts = [(f, analyze_file(f)) for f in DATA] + \
         [(k, analyze(snap[k]["bars"], tick=tick_of(syms[k.split()[0]] + "_.json"))) for k in sorted(snap)]
fmt = lambda r, i: D.datetime.fromtimestamp(r["bars"][i]["t"] / 1000, D.timezone.utc).strftime("%m-%d %H:%M")
out = {}

# ---- Z6：高一级中枢的三组从哪一段起划。A＝扩展链首段起；B＝首段往后挪 1、2 段也算一遍，看合成框（有无、[ZD,ZG]）变不变 ----
real_rg = T._regroup
calls = []
def rec(done, a, b):
    res = real_rg(done, a, b)
    alts = [real_rg(done, a + s, b) for s in (1, 2)]
    calls.append((res, alts, done[a]["i0"]))
    return res
z6 = collections.Counter(); z6_where = {}
for name, r in charts:
    calls.clear(); T._regroup = rec
    try:
        T.trend_v3(r)
    finally:
        T._regroup = real_rg
    seen = set()
    for res, alts, x0 in calls:
        if res is None or x0 in seen:
            continue
        seen.add(x0); z6["合成框"] += 1
        key = lambda h: None if h is None else (round(h["ZD"], 6), round(h["ZG"], 6))
        if any(key(h) != key(res) for h in alts):
            z6["换起点会变"] += 1; z6_where.setdefault(name, []).append(fmt(r, x0))
out["Z6"] = (dict(z6), z6_where)

# ---- Z12：中枢结束后又碰回原区间。B＝同一段走势里，后一个中枢的 [ZD,ZG] 跟前一个的 [ZD,ZG] 有重叠 ⇒ 并回前一个（当延伸）。
#      量：这种相邻对有几对；并了以后段型变几段 ----
z12 = collections.Counter(); z12_where = {}
for name, r in charts:
    v = T.trend_v3(r)
    done = T.find_bounds(r)["done"]
    for g, sg in enumerate(v["segments"]):
        zz = sorted([z for z in v["seg_centers"] if z["seg"] == g], key=lambda z: z["PI0"])
        merged, pairs = [], 0
        for z in zz:
            if merged and not (z["ZG"] < merged[-1]["ZD"] or z["ZD"] > merged[-1]["ZG"]):
                p = merged[-1]
                merged[-1] = dict(p, PI1=z["PI1"], X1=z["X1"], DD=min(p["DD"], z["DD"]), GG=max(p["GG"], z["GG"]))
                pairs += 1
            else:
                merged.append(dict(z))
        if pairs:
            z12["碰回原区间的对数"] += pairs
            b_type = T.classify(T.classify_relations([dict(z) for z in merged]), "A", done)
            a_type = (sg["type"], sg["upgraded"])
            if b_type != a_type:
                z12["段型变"] += 1; z12_where.setdefault(name, []).append((fmt(r, sg["i0"]), a_type, b_type))
out["Z12"] = (dict(z12), z12_where)

# ---- Z15：升级中枢后面低一级的中枢怎么比。A（现行 D3-3 读法 A）＝只数合成框；B＝合成框之后的本级别中枢也拿 [DD,GG] 跟它比 ----
z15 = collections.Counter(); z15_where = {}
real_cls = T.classify
def cls_b(zz, reading="A", done=None):
    units = T._units(zz, done)
    up = [u for u in units if u["n"] > 1]
    if not up:
        return real_cls(zz, reading, done)
    k = max(i for i, u in enumerate(units) if u["n"] > 1)
    seq = up + [u for u in units[k + 1:] if u["n"] == 1]
    if len(seq) == len(up):
        return real_cls(zz, reading, done)
    return (T._trend_of(seq) or "盘整"), True
for name, r in charts:
    a = [(s["type"], s["upgraded"]) for s in T.trend_v3(r)["segments"]]
    T.classify = cls_b
    try:
        vb = T.trend_v3(r)
    finally:
        T.classify = real_cls
    b = [(s["type"], s["upgraded"]) for s in vb["segments"]]
    if len(a) == len(b):
        d = [(fmt(r, s["i0"]), x, y) for s, x, y in zip(vb["segments"], a, b) if x != y]
    else:
        d = [("段数变", len(a), len(b))]
    z15["段型变"] += len(d)
    if d:
        z15_where[name] = d
out["Z15"] = (dict(z15), z15_where)

# ---- 盘整＋盘整：A＝照现在切；B＝相邻两段都是盘整（含升级·盘整、不含图头）就并。量：会少几刀 ----
pp = collections.Counter(); pp_where = {}
for name, r in charts:
    segs = T.trend_v3(r)["segments"]
    for x, y in zip(segs, segs[1:]):
        if x["head"]:
            continue
        if x["type"] == "盘整" and y["type"] == "盘整":
            pp["相邻两段都是盘整（少一刀）"] += 1
            pp_where.setdefault(name, []).append(fmt(r, y["i0"]))
out["盘整＋盘整"] = (dict(pp), pp_where)

# ---- W48：一买一卖要不要 B 段黄白线回抽 0 轴附近。A＝不要（开关默认关）；B＝要（不满足的一买一卖拿掉）----
w = collections.Counter(); w_where = {}
for name, r in charts:
    for lv in ("seg", "pen"):
        sig = [s for s in S.signals(r, lv) if s["kind"] in ("一买", "一卖")]
        w["一买一卖（%s）" % lv] += len(sig)
        bad = [x for x in S.zero_axis(sig, r, lv) if not x["ok"]]
        w["B 下会拿掉（%s）" % lv] += len(bad)
        if bad and lv == "seg":
            w_where.setdefault(name, []).extend("%s %s" % (x["kind"], fmt(r, x["bar"])) for x in bad)
out["W48"] = (dict(w), w_where)

for k, (c, where) in out.items():
    print("==", k, c)
    for n, v in where.items():
        print("   ", n, v[:6], "…" if len(v) > 6 else "")
