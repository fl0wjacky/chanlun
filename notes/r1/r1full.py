"""R-1 完整同级别：S9（D2 参照中枢同级别）＋S10 丙8 甲/乙，25 张。"""
import sys, os, json, gzip, collections
sys.path[:0] = [os.getcwd(), "tools"]
from core.analyze import analyze
import core.trend as T
from config import tick_of
snap = json.loads(gzip.open(os.environ["LIVE15"]).read())
syms = {"ZECUSDT": "zec", "BTCUSDT": "btc", "AAPLUSDT": "aaplusdt"}
items = [(k, snap[k]["bars"], syms[k.split()[0]] + "_.json") for k in sorted(snap)]
for fn in ["aaplusdt_1h", "aaplusdt_2h", "aaplusdt_30m", "aaplusdt_4h", "btc_4h", "zec15", "zec30_cut", "zec_1h", "zec_2h", "zec_4h"]:
    items.append(("data/" + fn, json.load(open("data/%s.json" % fn)), fn + ".json"))
R = [(n, analyze(b, tick=tick_of(t))) for n, b, t in items]
key = lambda v: {(b["bar"], b["kind"]) for b in v["bounds"]}
seg = lambda v: {(s["i0"], s["i1"], s["type"], s["upgraded"]) for s in v["segments"]}
base = {n: T.trend_v3(r) for n, r in R}
def run(d2, c8):
    T.SAME_LEVEL, T.SAME_LEVEL_D2, T.SAME_LEVEL_C8 = True, d2, c8
    try: return {n: T.trend_v3(r) for n, r in R}
    finally: T.SAME_LEVEL, T.SAME_LEVEL_D2, T.SAME_LEVEL_C8 = False, False, None
for lab, d2, c8 in (("半个同级别（576b2b3，D2 照现行）", False, None), ("完整同级别 S9（D2 参照中枢也同级别）", True, None),
                    ("S9＋丙8 甲（只认背驰死点）", True, "filter"), ("S9＋丙8 乙（背驰点直接切）", True, "direct"), ("S9＋丙8 丙（D2 照旧＋背驰刀）", True, "plus")):
    o = run(d2, c8)
    ch = sum(1 for n in base if key(base[n]) != key(o[n]) or seg(base[n]) != seg(o[n]))
    nb = sum(len(v["bounds"]) for v in o.values()); dc = sum(len(key(base[n]) ^ key(o[n])) for n in base)
    ds = sum(len(seg(base[n]) ^ seg(o[n])) for n in base)
    rules = collections.Counter(b.get("rule") for v in o.values() for b in v["bounds"])
    types = collections.Counter(s["type"] for v in o.values() for s in v["segments"])
    mv = sum(len(v.get("moved", [])) for v in o.values()); ret = sum(len(v["retracted"]) for v in o.values())
    top = sorted(((len(key(base[n]) ^ key(o[n])), n) for n in base), reverse=True)[:3]
    zero = sum(1 for v in o.values() if not [b for b in v["bounds"] if b.get("rule") not in ("S5", "D2-8")])
    lab = lab + "［无 D2／背驰刀 %d 张］" % zero
    print("%s：变的图 %d/25，分界 96→%d（增删 %d），走势段增删 %d；刀的来源 %s；段型 %s；撤回 %d；挪刀 %d；变化最大 %s" % (lab, ch, nb, dc, ds, dict(rules), dict(types), ret, mv, top))
