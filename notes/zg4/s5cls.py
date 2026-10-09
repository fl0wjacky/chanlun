"""D-4：S5 刀「两头 D2 都没动、自己变了」的那几次，按 Atlas 06:56 三类分（口径甲，按笔取前缀，同 dreplay）。
(i)  图尾：上一刻它右边没有 D2 刀；
(iii) 用到的线段事后被改：上一刻 [左中枢 X0, 右中枢 X1] 里的已完成线段，这一刻有不在的；
(ii) 右中枢刚立：上一刻右中枢的第三段就是最后一条已完成线段（紧挨末段）；
其余单列。先判 i，再 iii，再 ii。"""
import sys, os, json, gzip
from concurrent.futures import ProcessPoolExecutor
sys.path[:0] = [os.getcwd(), "tools"]
from dreplay import items
def one(it):
    name, fn = it
    from core.analyze import analyze
    import core.trend as T
    from config import tick_of
    syms = {"ZECUSDT": "zec", "BTCUSDT": "btc", "AAPLUSDT": "aaplusdt"}
    if fn: bars = json.load(open("data/%s.json" % fn)); tk = fn + ".json"
    else: bars = json.loads(gzip.open(os.environ["LIVE15"]).read())[name]["bars"]; tk = syms[name.split()[0]] + "_.json"
    T.SAME_LEVEL, T.SAME_LEVEL_D2, T.SAME_LEVEL_D6, T.SL_FIRST_EXEMPT = True, True, "fallback", True
    t = tick_of(tk); full = analyze(bars, tick=t)
    cuts = sorted({p["i1"] + 1 for p in full["pens"]} | {len(bars)})
    prev = None; out = {}; ex = []
    for c in cuts:
        r = analyze(bars[:c], tick=t); v = T.trend_v3(r)
        d2 = {(b["bar"], b["kind"]) for b in v["bounds"] if b.get("rule") == "D2-2"}
        s5 = {(b["bar"], b["kind"]) for b in v["bounds"] if b.get("rule") == "S5"}
        done = [(s["i0"], s["i1"]) for s in r["segs"] if not s.get("live")]
        zz = [(z["X0"], z["X1"]) for z in v["seg_centers"]]
        if prev:
            pd2, ps5, pdone, pzz = prev
            lost = pd2 - d2
            for k in ps5 - s5:
                left = [x for x in pd2 if x[0] < k[0]]; right = [x for x in pd2 if x[0] > k[0]]
                L = max(left) if left else None; R = min(right) if right else None
                if L in lost or R in lost: continue
                lz = [z for z in pzz if z[1] == k[0]]; rz = [z for z in pzz if z[0] == k[0]]
                x0 = lz[0][0] if lz else k[0]; x1 = rz[0][1] if rz else k[0]
                used = [s for s in pdone if s[0] >= x0 and s[1] <= x1]
                if R is None: cl = "(i) 图尾"
                elif any(s not in done for s in used): cl = "(iii) 线段被改"
                elif rz and pdone and rz[0][1] == pdone[-1][1]: cl = "(ii) 右中枢第三段紧挨末段"
                else: cl = "其余"
                out[cl] = out.get(cl, 0) + 1
                if cl == "其余" and len(ex) < 3: ex.append((k, c))
        prev = (d2, s5, done, zz)
    return name, out, ex
if __name__ == "__main__":
    tot = {}
    with ProcessPoolExecutor(3) as pool:
        for name, o, ex in pool.map(one, items()):
            print(name, o, ex, flush=True)
            for k, n in o.items(): tot[k] = tot.get(k, 0) + n
    print("合计", tot, sum(tot.values()))
