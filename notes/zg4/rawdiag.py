"""原始线段那 12 次撤：逐条看是笔先变了（K 线前缀下最后几笔被改），还是笔没变、线段自己撤了（真线段层问题）。"""
import sys, os, json, gzip
sys.path[:0] = [os.getcwd(), "tools"]
from core.analyze import analyze
from core.segment import build_segments
from config import tick_of
snap = json.loads(gzip.open(os.environ["LIVE15"]).read())
syms = {"ZECUSDT": "zec", "BTCUSDT": "btc", "AAPLUSDT": "aaplusdt"}
def load(name):
    if name.startswith("data/"):
        fn = name[5:]; return json.load(open("data/%s.json" % fn)), fn + ".json"
    return snap[name]["bars"], syms[name.split()[0]] + "_.json"
P = lambda p: (p["i0"], p["i1"], round(p["p0"], 8), round(p["p1"], 8))
for name in sys.argv[1:]:
    bars, tk = load(name); t = tick_of(tk)
    full = analyze(bars, tick=t)
    cuts = sorted({p["i1"] + 1 for p in full["pens"]} | {len(bars)})
    prev = None
    for c in cuts:
        r = analyze(bars[:c], tick=t)
        rl = [s for s in r["segs"] if not s.get("live")]
        cur = {(s["i0"], s["i1"]) for s in rl}
        if prev is not None:
            gone = prev[0] - cur
            for g in sorted(gone):
                old = prev[1]; pens0 = prev[2]; pens1 = r["pens"]
                k = next((i for i, (a, b) in enumerate(zip(pens0, pens1)) if P(a) != P(b)), min(len(pens0), len(pens1)))
                seg = next(s for s in old if (s["i0"], s["i1"]) == g)
                # 笔不变时：拿上一刻的笔序列逐笔加长（seg_prefix 的口径）看会不会撤
                same_pens = k >= seg["PI1"] + 1
                print(name, "前缀", c, "撤", g, "PI", seg["PI0"], seg["PI1"], "case", seg.get("case"),
                      "| 第一处笔不同 = 笔 %d（上一刻共 %d 笔，这一刻 %d 笔）" % (k, len(pens0), len(pens1)),
                      "⇒ 段里的笔没变（线段层自己撤）" if same_pens else "⇒ 段里的笔先变了")
        prev = (set((s["i0"], s["i1"]) for s in rl[:-1]), rl, r["pens"])
