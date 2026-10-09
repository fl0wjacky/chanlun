"""S-13 第 3 组（只读量）：P2 锁（PEN_FINAL_LOCK）开/关 × 线段 基准/甲（只用定稿笔，即去掉最后一笔再划线段）。
前缀＝按「默认引擎全图笔终点后一根」取（同 d20replay），已确认线段＝已完成线段去掉最后一条（同 d20replay）。
报：线段确认后撤次数、确认延迟（全图终版里的已完成线段，第一次以已确认身份出现的前缀 − 它终点那一根）、
锁下笔改写深度 ≥2 的次数（应为 0）、全图非极值端点数。乙的「已确认」集合跟甲相同（乙只是把甲里没有的那几条画成待定），
所以撤回与延迟两组相同，不单跑。"""
import sys, os, json, gzip, statistics
from concurrent.futures import ProcessPoolExecutor
sys.path[:0] = [os.getcwd(), "tools"]
from dreplay import items
def one(it):
    name, fn = it
    import core.pen as PEN
    from core.kline import standardize, fractals, quantize
    from core.segment import build_segments
    from config import tick_of
    syms = {"ZECUSDT": "zec", "BTCUSDT": "btc", "AAPLUSDT": "aaplusdt"}
    if fn: bars = json.load(open("data/%s.json" % fn)); tk = fn + ".json"
    else: bars = json.loads(gzip.open(os.environ["LIVE15"]).read())[name]["bars"]; tk = syms[name.split()[0]] + "_.json"
    t = tick_of(tk)
    def pens_of(b, lock):
        PEN.PEN_FINAL_LOCK = lock
        std = standardize(quantize(b, t)); pens, _ = PEN.build_pens(fractals(std), std, "old", PEN.MIN_GAP_DEFAULT)
        PEN.PEN_FINAL_LOCK = False
        return pens, std
    def conf_segs(pens, jia):
        s = build_segments(pens[:-1] if jia else pens)
        done = [(x["i0"], x["i1"]) for x in s if not x.get("live")]
        return done[:-1], set(done)
    out = {}
    full_pens, _ = pens_of(bars, False)
    cuts = sorted({p["i1"] + 1 for p in full_pens} | {len(bars)})
    for lock in (False, True):
        fp, fstd = pens_of(bars, lock)
        out[("非极值端点", lock)] = len(PEN.nonextreme_pens(fp, fstd))
        final = {jia: set(conf_segs(fp, jia)[0]) for jia in (False, True)}
        prev = {False: None, True: None}; first = {False: {}, True: {}}; w = {False: 0, True: 0}; prevp = None; deep = 0
        P = lambda p: (p["i0"], p["i1"], round(p["p1"], 8))
        for c in cuts:
            pens, _ = pens_of(bars[:c], lock)
            if prevp is not None:
                k = next((i for i, (a, b) in enumerate(zip(prevp, pens)) if P(a) != P(b)), min(len(prevp), len(pens)))
                if k < len(prevp) and len(prevp) - k >= 2: deep += 1
            prevp = pens
            for jia in (False, True):
                cs, alld = conf_segs(pens, jia); S = set(cs)
                if prev[jia] is not None: w[jia] += len(prev[jia] - alld)   # 同 d20replay：上一刻已确认的，这一刻连已完成都不是了
                for x in S: first[jia].setdefault(x, c)
                prev[jia] = S
        out[("改到倒数第2笔及更早", lock)] = deep
        for jia in (False, True):
            out[("线段确认后撤", lock, jia)] = w[jia]
            out[("延迟", lock, jia)] = [first[jia][x] - x[1] for x in final[jia] if x in first[jia]]
    return name, out
if __name__ == "__main__":
    tot = {}
    with ProcessPoolExecutor(4) as ex:
        for name, o in ex.map(one, items()):
            print(name, {k: v for k, v in o.items() if k[0] != "延迟"}, flush=True)
            for k, v in o.items(): tot[k] = tot.get(k, [] if k[0] == "延迟" else 0) + v
    for k in sorted(tot, key=str):
        v = tot[k]
        print("合计", k, ("中位 %s 最大 %s 条数 %d" % (statistics.median(v), max(v), len(v))) if k[0] == "延迟" else v)
