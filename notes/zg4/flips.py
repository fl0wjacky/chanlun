"""决策树代码侧：每个开关翻到另一边，25 张里动几张图、线段增删几条、分界增删几刀（只读）。"""
import sys, os, json, gzip
sys.path[:0] = [os.getcwd(), "tools"]
import importlib
from core.analyze import analyze
import core.trend as T, core.segment as SG
SIG = importlib.import_module("core.signals")
from config import tick_of
snap = json.loads(gzip.open(os.environ["LIVE15"]).read())
syms = {"ZECUSDT": "zec", "BTCUSDT": "btc", "AAPLUSDT": "aaplusdt"}
items = [(k, snap[k]["bars"], syms[k.split()[0]] + "_.json") for k in sorted(snap)]
for fn in ["aaplusdt_1h", "aaplusdt_2h", "aaplusdt_30m", "aaplusdt_4h", "btc_4h", "zec15", "zec30_cut", "zec_1h", "zec_2h", "zec_4h"]:
    items.append(("data/" + fn, json.load(open("data/%s.json" % fn)), fn + ".json"))
def run(kw_an=None, kw_tr=None):
    out = {}
    for name, bars, tk in items:
        r = analyze(bars, tick=tick_of(tk), **(kw_an or {}))
        v = T.trend_v3(r, **(kw_tr or {}))
        sg = SIG.signals(r, "seg")
        out[name] = ({(s["i0"], s["i1"]) for s in r["segs"] if not s.get("live")},
                     {(b["bar"], b["kind"]) for b in v["bounds"]},
                     {(s["i0"], s["i1"], s["type"], s["upgraded"]) for s in v["segments"]},
                     {(x["bar"], x["kind"]) for x in sg})
    return out
base = run()
def diff(o, lab):
    ch = segs = cuts = types = sigs = 0
    for k in base:
        a, b = base[k], o[k]
        d = [len(a[i] ^ b[i]) for i in range(4)]
        if any(d): ch += 1
        segs += d[0]; cuts += d[1]; types += d[2]; sigs += d[3]
    print("%-34s 变的图 %2d/25  线段±%-4d 分界±%-3d 走势段±%-4d 线段级买卖点±%d" % (lab, ch, segs, cuts, types, sigs), flush=True)
mods = {"SG": SG, "T": T, "SIG": SIG}
FLAGS = [("SG", "S11_START_OK"), ("SG", "HEAD_DIR_FIX"), ("SG", "HEAD_EXT_FIX"), ("SG", "HEAD_EXT_CUTOFF"), ("SG", "HEAD_DIR_NO_TENT"),
         ("SG", "GAP_COVER"), ("SG", "S10_TIE"), ("SG", "S7_NOW"), ("SG", "L77_MERGE"), ("SG", "L77_STRICT_NEWLOW"),
         ("T", "_R6_B"), ("T", "_BLOCK_RETRACTED"), ("T", "_MOVE_ENDS"), ("T", "_DIR_RULE"), ("T", "_D3_REGROUP"), ("T", "_D6_BASE_ONLY"),
         ("T", "_D3_LIVE_TAIL"), ("T", "_D28"), ("T", "_XZD_SECOND"), ("SIG", "_M29")]
for m, f in FLAGS:
    mod = mods[m]; old = getattr(mod, f); setattr(mod, f, not old)
    try: diff(run(), "%s=%s" % (f, not old))
    finally: setattr(mod, f, old)
for kw, lab in ((dict(alternate=False), "trend alternate=False（D2-3）"), (dict(no_exceed=False), "trend no_exceed=False"),
                (dict(regroup=False), "trend regroup=False"), (dict(check_empty=False), "trend check_empty=False（D2-7）"),
                (dict(standardize=False), "trend standardize=False（D2-0）"), (dict(reading="B"), "trend reading=B（D3）")):
    diff(run(kw_tr=kw), lab)
diff(run(kw_an=dict(pen="new")), "analyze pen=new（新笔 L81）")
old = SG.FEAT_STD_DEFAULT
diff(run(kw_an=dict(min_gap=4)), "min_gap=4（＝7 根成笔）")
