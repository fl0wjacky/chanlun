"""Nova 10:50：600 处（全是起点非极值）在「更极端的同类点 P′ 出现那一刻」，起点 a 算不算已经定死？
P′＝笔内第一个比 a 更极端的同类分型（时间上最早）。a 定死 ⇔ P′ 之前已经有反向分型 T 让 a→T 成笔（P1：下一笔成立，前一笔才定）。
「成笔」三种读法（Atlas 待核 L77:47-52 的「下一个顶分型」）：任何反向分型都算／按 L77（k 差≥4、顶高于底）／按 6 根（k 差≥3）。
甲＝没定死（锁多管）；乙＝已定死（真冲突）。跟 nesplit 的 ①②③ 交叉。"""
import sys, os, json, gzip, datetime as D
sys.path[:0] = [os.getcwd(), "tools", os.path.dirname(os.path.abspath(__file__))]
from dreplay import items
import core.pen as PEN
from core.kline import standardize, fractals, quantize
from config import tick_of
syms = {"ZECUSDT": "zec", "BTCUSDT": "btc", "AAPLUSDT": "aaplusdt"}
snap = json.loads(gzip.open(os.environ["LIVE15"]).read())
def ok_pen(a, b, std, gap):
    if a["type"] == b["type"] or abs(b["k"] - a["k"]) < gap: return False
    top, bot = (a, b) if a["type"] == "top" else (b, a)
    return std[top["k"]]["h"] > std[bot["k"]]["h"]
def splittable(left, right, fx, std, gap):
    mids = sorted([f for f in fx if left["k"] < f["k"] < right["k"]], key=lambda f: f["k"]); reach = [left]
    for f in mids + [right]:
        if any(ok_pen(p, f, std, gap) for p in reach):
            if f is right: return True
            reach.append(f)
    return False
READ = {"任何反向分型": lambda a, T, std: True, "L77": lambda a, T, std: ok_pen(a, T, std, 4), "6根": lambda a, T, std: ok_pen(a, T, std, 3)}
tab = {r: {} for r in READ}; ex = {}
for name, fn in items():
    bars = json.load(open("data/%s.json" % fn)) if fn else snap[name]["bars"]
    tk = (fn + ".json") if fn else syms[name.split()[0]] + "_.json"
    std = standardize(quantize(bars, tick_of(tk))); fx = fractals(std)
    PEN.PEN_FINAL_LOCK = True; pens, seq = PEN.build_pens(fx, std, "old", PEN.MIN_GAP_DEFAULT); PEN.PEN_FINAL_LOCK = False
    t = lambda i: D.datetime.fromtimestamp(bars[i]["t"] / 1000, D.timezone.utc).strftime("%m-%d %H:%M")
    for n, w in PEN.nonextreme_pens(pens, std):
        a, g = seq[n], seq[n + 1]
        more = (lambda f: f["price"] > a["price"]) if a["type"] == "top" else (lambda f: f["price"] < a["price"])
        Ps = sorted([f for f in fx if a["k"] < f["k"] < g["k"] and f["type"] == a["type"] and more(f)], key=lambda f: f["k"])
        P1 = Ps[0]; Pm = (max if a["type"] == "top" else min)(Ps, key=lambda f: f["price"])
        grp = "①" if splittable(a, Pm, fx, std, 4) else "②" if splittable(a, Pm, fx, std, 3) else "③"
        Ts = [f for f in fx if a["k"] < f["k"] < P1["k"] and f["type"] != a["type"]]
        for r, fn_ in READ.items():
            cls = "乙 已定死" if any(fn_(a, T, std) for T in Ts) else "甲 没定死"
            tab[r][(grp, cls)] = tab[r].get((grp, cls), 0) + 1
            if r == "L77" and (grp, cls) not in ex:
                ex[(grp, cls)] = "%s 第 %d 笔 起点%s %s %s，P′ %s %s" % (name, n, "顶" if a["type"] == "top" else "底", t(a["i"]), a["price"], t(P1["i"]), P1["price"])
        if name == "data/aaplusdt_30m" and abs(a["price"] - 310.44) < 1e-6:
            print("Iris 那处：组", grp, {r: ("乙" if any(f(a, T, std) for T in Ts) else "甲") for r, f in READ.items()}, "P′", t(P1["i"]), P1["price"])
for r in READ:
    print("【%s】" % r, dict(sorted(tab[r].items())), "甲", sum(v for k, v in tab[r].items() if k[1].startswith("甲")), "乙", sum(v for k, v in tab[r].items() if k[1].startswith("乙")))
for k, v in sorted(ex.items()): print(k, "例：", v)
