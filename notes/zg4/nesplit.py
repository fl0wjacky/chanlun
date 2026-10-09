"""Nova 10:47 假设 C：锁开（PEN_FINAL_LOCK＋P2′）下的非极值端点，「里面本来就是好几笔」吗？只量，不改引擎。
对每处非极值端点（nonextreme_pens）：P＝这一笔里比端点更极端的那个同类分型（取最极端）。
  起点非极值：在 起点 a 和 P 之间找反向分型 T，使 a→T、T→P 都成笔 ⇒ 这一笔该拆成 a→T→P→终点；
  终点非极值：在 P 和终点 g 之间找反向分型 T，使 P→T、T→g 都成笔 ⇒ 该拆成 起点→P→T→g。
成笔两档：L77（L77:37-40，顶底之间至少一根独立 K 线 ⇒ 标准化序列 k 差 ≥4，顶分型最高那根高于底分型最低那根）；
          现行 6 根（k 差 ≥3，其余同）。分三类：① L77 能分 ② 只有 6 根能分 ③ 都分不出。"""
import sys, os, json, gzip, datetime as D
sys.path[:0] = [os.getcwd(), "tools", os.path.dirname(os.path.abspath(__file__))]
from dreplay import items
import core.pen as PEN
from core.kline import standardize, fractals, quantize
from config import tick_of
syms = {"ZECUSDT": "zec", "BTCUSDT": "btc", "AAPLUSDT": "aaplusdt"}
snap = json.loads(gzip.open(os.environ["LIVE15"]).read())
def ok_pen(a, b, std, gap):
    if a["type"] == b["type"] or abs(b["k"] - a["k"]) < gap:
        return False
    top, bot = (a, b) if a["type"] == "top" else (b, a)
    return std[top["k"]]["h"] > std[bot["k"]]["h"]
W = {}
tot = {"① L77 能分": 0, "② 只有 6 根能分": 0, "③ 都分不出": 0}; ex = {}; per = []
for name, fn in items():
    bars = json.load(open("data/%s.json" % fn)) if fn else snap[name]["bars"]
    tk = (fn + ".json") if fn else syms[name.split()[0]] + "_.json"
    std = standardize(quantize(bars, tick_of(tk))); fx = fractals(std)
    PEN.PEN_FINAL_LOCK = True
    pens, seq = PEN.build_pens(fx, std, "old", PEN.MIN_GAP_DEFAULT)
    PEN.PEN_FINAL_LOCK = False
    byk = {f["k"]: f for f in fx}
    cnt = dict.fromkeys(tot, 0)
    for n, where in PEN.nonextreme_pens(pens, std):
        a, g = seq[n], seq[n + 1]
        e = a if where == "起点" else g                       # 不是极值的那个端点
        inner = [f for f in fx if a["k"] < f["k"] < g["k"] and f["type"] == e["type"]]
        more = (lambda f: f["price"] > e["price"]) if e["type"] == "top" else (lambda f: f["price"] < e["price"])
        cand = [f for f in inner if more(f)]
        if not cand:
            cls = "③ 都分不出"; W["③a 笔内更极端的点不是分型"] = W.get("③a 笔内更极端的点不是分型", 0) + 1
        else:
            P = (max if e["type"] == "top" else min)(cand, key=lambda f: f["price"])
            lo_k, hi_k = (a["k"], P["k"]) if where == "起点" else (P["k"], g["k"])
            left, right = (a, P) if where == "起点" else (P, g)
            Ts = [f for f in fx if lo_k < f["k"] < hi_k and f["type"] != e["type"]]
            mids = sorted([f for f in fx if lo_k < f["k"] < hi_k], key=lambda f: f["k"])
            def can(gap):                                    # 任意多笔的链：left → … → right，相邻两点都成笔（类型交替、隔够、顶高于底）
                reach = [left]
                for f in mids + [right]:
                    if any(ok_pen(p, f, std, gap) for p in reach):
                        if f is right:
                            return True
                        reach.append(f)
                return False
            cls = "① L77 能分" if can(4) else "② 只有 6 根能分" if can(3) else "③ 都分不出"
            if cls == "③ 都分不出":
                why3 = "③b 中间没有反向分型" if not Ts else ("③c 有反向分型但隔不够（6 根也不够）" if not any(
                    abs(T["k"] - left["k"]) >= 3 and abs(right["k"] - T["k"]) >= 3 for T in Ts) else "③d 隔够了但顶不高于底")
                W[why3] = W.get(why3, 0) + 1
        cnt[cls] += 1
        if cls not in ex or (cls != "③ 都分不出" and len(ex[cls]) < 2):
            t = lambda i: D.datetime.fromtimestamp(bars[i]["t"] / 1000, D.timezone.utc).strftime("%m-%d %H:%M")
            ex.setdefault(cls, []).append("%s 第 %d 笔 %s非极值：%s %s %s → %s %s" % (name, n, where, e["type"], t(e["i"]), e["price"],
                                           "（笔内极值）" if not cand else t(P["i"]), "" if not cand else P["price"]))
    per.append((name, cnt))
    for k in tot: tot[k] += cnt[k]
for name, c in per:
    if sum(c.values()): print(name, c)
print("合计", tot, sum(tot.values()))
for k, v in ex.items(): print(k, "例：", v[:2])
print("③ 拆开", W)
