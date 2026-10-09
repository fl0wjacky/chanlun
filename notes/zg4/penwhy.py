"""411 次「从倒数第 2 笔起改」+ 91 次 ≥3：按引擎哪条路改的分（作废上一笔 / fix_start 让 P 当端点 / fix_start 合并）。
按笔终点取前缀（同 pendepth）；只跑笔层；把 build_pens 源码打桩：每次改 seq[j] 记 (路, j)。"""
import sys, os, json, gzip, re, inspect
from concurrent.futures import ProcessPoolExecutor
sys.path[:0] = [os.getcwd(), "tools"]
import core.pen as PEN
src = inspect.getsource(PEN.build_pens)
rep = [
 ("                seq[:] = seq[:j + 1] + [P]", "                LOG.append(('P当端点', j + 1, CUR[0])); seq[:] = seq[:j + 1] + [P]"),
 ("                seq[:] = seq[:j + 1] + [g]", "                LOG.append(('合并', j + 1, CUR[0])); seq[:] = seq[:j + 1] + [g]"),
 ("                seq.pop()\n", "                LOG.append(('作废上一笔', len(seq) - 2, CUR[0])); seq.pop()\n"),
 ("    for f in fx:\n        feed(f)", "    for f in fx:\n        CUR[0] = (f['i'], f['type'], f['price']); feed(f)"),
]
for a, b in rep:
    assert src.count(a) == 1, a
    src = src.replace(a, b)
ns = dict(vars(PEN)); ns["LOG"] = []; ns["CUR"] = [None]
exec(src, ns)
def pens_of(bars, t):
    from core.kline import standardize, fractals, quantize
    std = standardize(quantize(bars, t)); fx = fractals(std)
    ns["LOG"].clear()
    pens, seq = ns["build_pens"](fx, std, "old", PEN.MIN_GAP_DEFAULT)
    return pens, list(ns["LOG"]), {(f["i"], f["type"], f["price"]) for f in fx}
def items():
    snap = json.loads(gzip.open(os.environ["LIVE15"]).read())
    out = [(k, None) for k in sorted(snap)]
    return out + [("data/" + f, f) for f in ["aaplusdt_1h", "aaplusdt_2h", "aaplusdt_30m", "aaplusdt_4h", "btc_4h", "zec15", "zec30_cut", "zec_1h", "zec_2h", "zec_4h"]]
def one(it):
    name, fn = it
    from config import tick_of
    syms = {"ZECUSDT": "zec", "BTCUSDT": "btc", "AAPLUSDT": "aaplusdt"}
    if fn: bars = json.load(open("data/%s.json" % fn)); tk = fn + ".json"
    else: bars = json.loads(gzip.open(os.environ["LIVE15"]).read())[name]["bars"]; tk = syms[name.split()[0]] + "_.json"
    t = tick_of(tk)
    full, _, _ = pens_of(bars, t)
    cuts = sorted({p["i1"] + 1 for p in full} | {len(bars)})
    P = lambda p: (p["i0"], p["i1"], round(p["p1"], 8))
    prev = None; pfx = set(); hist = {}
    for c in cuts:
        pens, log, fxs = pens_of(bars[:c], t)
        if prev is not None:
            k = next((i for i, (a, b) in enumerate(zip(prev, pens)) if P(a) != P(b)), min(len(prev), len(pens)))
            if k < len(prev):
                d = len(prev) - k
                if d >= 2:
                    new = [e for e in log if e[2] not in pfx]          # 新出现的分型喂进去时触发的改动
                    deep = min(new, key=lambda e: e[1]) if new else None
                    why = deep[0] if deep else "无新分型事件（尾部标准化/分型变了）"
                    key = ("2" if d == 2 else "≥3", why)
                    hist[key] = hist.get(key, 0) + 1
        prev, pfx = pens, fxs
    return name, hist
if __name__ == "__main__":
    tot = {}
    with ProcessPoolExecutor(1) as ex:
        for name, h in ex.map(one, items()):
            print(name, h, flush=True)
            for d, n in h.items(): tot[d] = tot.get(d, 0) + n
    print("合计", dict(sorted(tot.items())))
