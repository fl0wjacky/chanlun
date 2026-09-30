# -*- coding: utf-8 -*-
"""三类买卖点（第 20 / 21 / 24 课），按某一层中枢判：线段中枢（默认，正规）或类中枢（笔构成，对照）。

    第一类（一买 / 一卖）—— 趋势背驰（第 21 / 24 课）：
        下跌趋势 = 相邻中枢「下跌延续」（第 20 课中心定理二①）。设最后一个中枢为 B：
        A 段 = 进入 B 之前最后一段向下走势，C 段 = 离开 B、创出 B 的波动范围新低（< DD）的那一段。
        C 段力度 < A 段力度 × 比例 → 背驰，一买在 C 段的终点。
        力度：MACD 柱面积（第 24 课「向下看绿柱子」，默认）或价格斜率（|Δ价| / K 线根数）。
        确认：背驰后回拉进最后一个中枢（高点 ≥ ZD），第 18 / 72 课「趋势结束的标志就是形成该级别的背驰后
        对最后一个中枢的回拉」；回拉之前先跌破 C 段低点 → 背驰失败，不算。一卖镜像。
    第二类（二买 / 二卖）—— 第 21 课「第一买点出现后的第二段次级别走势低点就构成第二类买点」：
        确认的一买之后，反弹段之后的那一段回调的终点。跌破一买低点也算，标为「弱」（第 54 / 101 课）。
    第三类（三买 / 三卖）—— 第 20 课定义，与引擎的中枢终结同一口径（center.find_centers）：
        离开段从中枢区间里出发，回试段整段在 ZG 之上（ZD 之下）；三买在回试段的终点。

    确认 vs 待确认：点所在的那一段已经走完（后面又出了一段）才算确认；还在走的记为待确认
    （confirmed=False），之后可能被改掉或消失。线段层只用已完成线段算中枢，所以待确认只来自最后那条未完成线段。

返回 [dict(kind="一买"…, bar=原始K线下标, price, confirmed, weak, level, center=中枢序号), ...]，按 bar 排序。
"""
from .center import find_centers


def macd_hist(bars, fast=12, slow=26, sig=9):
    """MACD 柱 = DIF − DEA（与 TradingView 内置 MACD 的 histogram 同义；不乘 2，面积比不受影响）。

    EMA 用第一根收盘价起算（Pine 版照此手写，不用 ta.ema 的 SMA 起算，两边逐根一致）。
    """
    out = []
    for n, b in enumerate(bars):
        c = b["c"]
        if n == 0:
            ef = es = c
            dea = 0.0
        else:
            ef += (c - ef) * 2 / (fast + 1)
            es += (c - es) * 2 / (slow + 1)
            dea += (ef - es - dea) * 2 / (sig + 1)
        out.append(ef - es - dea)
    return out


def _units(r, level):
    """(全部单位含未完成的, 构成中枢的单位, 中枢)。单位统一带 i0/i1/p0/p1/hi/lo。"""
    if level == "seg":
        segs = r["segs"]
        done = [s for s in segs if not s.get("live")]
        return segs, done, r["seg_centers"]
    return r["pens"], r["pens"], r["centers"]


def strength(u, hist, measure="macd"):
    """一段走势的力度：MACD 柱面积（只算与该段同向的柱子），或斜率。"""
    up = u["p1"] > u["p0"]
    if measure == "slope":
        return abs(u["p1"] - u["p0"]) / max(1, u["i1"] - u["i0"])
    seg = hist[u["i0"]:u["i1"] + 1]
    return sum(h for h in seg if h > 0) if up else -sum(h for h in seg if h < 0)


def signals(r, level="seg", measure="macd", ratio=1.0, fast=12, slow=26, sig=9):
    """level: "seg" 线段中枢（默认）/ "pen" 类中枢；measure: "macd" / "slope"；ratio: C < A × ratio 才算背驰。"""
    AU, U, Z = _units(r, level)
    hist = macd_hist(r["bars"], fast, slow, sig)
    n_done = len(U)                                  # U 里的单位下标与 AU 一致（已完成的在前）
    last_live = (level == "seg" and len(AU) > n_done) or level == "pen"
    done_idx = lambda q: q < len(AU) - (1 if last_live else 0)   # 这一段已经走完（后面又出了一段）
    down = lambda u: u["p1"] < u["p0"]
    out = []

    def add(kind, q, k, weak=False):
        u = AU[q]
        out.append(dict(kind=kind, bar=u["i1"], price=u["p1"], confirmed=done_idx(q), weak=weak,
                        level=level, center=k + 1, unit=q))

    # ---- 第三类：与中枢终结同一口径 ----
    for k, z in enumerate(Z):
        if z["term"] in ("三买", "三卖"):
            add(z["term"], z["PI1"] + 2, k)
    if level == "seg" and Z and Z[-1]["live"] and len(AU) > n_done:   # 待确认：回试段就是那条未完成线段
        z, j = Z[-1], n_done - 1
        u, w = AU[j], AU[j + 1]
        if j >= z["PI0"] + 3 and z["ZD"] <= u["p0"] <= z["ZG"]:
            if u["p1"] > u["p0"] and w["lo"] > z["ZG"]:
                add("三买", j + 1, len(Z) - 1)
            elif u["p1"] < u["p0"] and w["hi"] < z["ZD"]:
                add("三卖", j + 1, len(Z) - 1)

    # ---- 第一类、第二类 ----
    for k in range(1, len(Z)):
        B = Z[k]
        for want_down, rel, k1, k2 in ((True, "下跌延续", "一买", "二买"), (False, "上涨延续", "一卖", "二卖")):
            if B["rel"] != rel:
                continue
            same = (lambda u: down(u)) if want_down else (lambda u: not down(u))
            a = next((q for q in range(B["PI0"] - 1, -1, -1) if same(AU[q])), None)          # A 段
            c = next((q for q in (B["PI1"] + 1, B["PI1"] + 2) if q < len(AU) and same(AU[q])), None)  # C 段
            if a is None or c is None:
                continue
            C = AU[c]
            if (C["lo"] >= B["DD"]) if want_down else (C["hi"] <= B["GG"]):
                continue                                                  # 没创新低（新高）：不是离开段
            if not strength(C, hist, measure) < strength(AU[a], hist, measure) * ratio:
                continue                                                  # 没背驰
            ok = None                                                     # 背驰后：先回拉进中枢，还是先破 C 的极值
            for q in range(c + 1, len(AU)):
                u = AU[q]
                if (u["lo"] < C["p1"]) if want_down else (u["hi"] > C["p1"]):
                    ok = False; break
                if (u["hi"] >= B["ZD"]) if want_down else (u["lo"] <= B["ZG"]):
                    ok = True; break
            if ok is False:
                continue
            confirmed = bool(ok) and done_idx(c)
            out.append(dict(kind=k1, bar=C["i1"], price=C["p1"], confirmed=confirmed, weak=False,
                            level=level, center=k + 1, unit=c))
            if confirmed and c + 2 < len(AU):                             # 第二类：一买后第二段次级别走势的终点
                s2 = AU[c + 2]
                weak = (s2["p1"] < C["p1"]) if want_down else (s2["p1"] > C["p1"])
                add(k2, c + 2, k, weak)
    out.sort(key=lambda s: (s["bar"], s["kind"]))
    return out


def _strength_by_definition(u, hist, measure):
    """第 24 课的力度，**独立另写一份**——本函数存在的唯一理由就是它不调 strength()。

    为什么要抄一遍同样的公式：力度是背驰判据里唯一「算出来的量」，而 check_signals 原先
    只复核结构（点是不是段终点、方向、三类点的位置…），**没有一条看着力度**。
    实测：把 strength() 弄坏（斜率的 max(1, span) 换成 min，等长替换），ZEC 15m pen 的
    90 个买卖点里 12 个换了位置，而 check_signals 照样报 0——门一声不响。
    复核必须独立于被测实现，所以这里宁可重复一遍公式——和 check_centers「另写一遍、
    不调用 upgrades」是同一个写法。**改 strength 的公式时这里要一起改**，这是这份独立的代价。
    """
    if measure == "slope":
        span = u["i1"] - u["i0"]
        return abs(u["p1"] - u["p0"]) / (span if span > 1 else 1)      # 同 max(1, span)，写法不同
    seg = hist[u["i0"]:u["i1"] + 1]
    if u["p1"] > u["p0"]:
        return sum(h for h in seg if h > 0)
    return -sum(h for h in seg if h < 0)


def check_signals(sig, r, level="seg", measure="macd", ratio=1.0):
    """独立复核（只用中枢与单位的原始字段，按定义另写一遍关键条件）。返回违规列表（应为空）。

    measure / ratio 要跟产生 sig 的那次 signals() 调用一致，否则背驰那条会误报。
    **MACD 参数（fast / slow / sig）也要一致** —— 本函数没有这三个形参，它按默认 12 / 26 / 9
    重算 hist（下面 `macd_hist(r["bars"])`），所以调用方若给 signals() 换过参数，复核量的就不是
    同一条线（今天仓里没有这样的调用点：`tools/selfcheck.py:81` 传的都是默认值）。
    """
    AU, U, Z = _units(r, level)
    hist = macd_hist(r["bars"]) if measure == "macd" else None
    bad = []
    for s in sig:
        u = AU[s["unit"]]
        if (u["i1"], u["p1"]) != (s["bar"], s["price"]):
            bad.append(("点不在所属段的终点", s["kind"], s["bar"])); continue
        z = Z[s["center"] - 1]
        buy = s["kind"].endswith("买")
        if (u["p1"] < u["p0"]) != buy:
            bad.append(("买点不在向下段终点 / 卖点不在向上段终点", s["kind"], s["bar"]))
        if s["kind"] in ("三买", "三卖"):
            lv = AU[s["unit"] - 1]                                # 离开段
            if not (z["ZD"] <= lv["p0"] <= z["ZG"]):
                bad.append(("三类买卖点的离开段不是从中枢里出发", s["kind"], s["bar"]))
            if (u["lo"] <= z["ZG"]) if buy else (u["hi"] >= z["ZD"]):
                bad.append(("三类买卖点的回试段碰到了中枢区间", s["kind"], s["bar"]))
        if s["kind"] in ("一买", "一卖"):
            if z["rel"] != ("下跌延续" if buy else "上涨延续"):
                bad.append(("一类买卖点不在趋势的最后一个中枢之后", s["kind"], s["bar"]))
            if (u["lo"] >= z["DD"]) if buy else (u["hi"] <= z["GG"]):
                bad.append(("一类买卖点的 C 段没创新低 / 新高", s["kind"], s["bar"]))
            # 背驰：C 段力度 < A 段力度 × 比例。A 段的找法与 signals() 同一条规则，
            # 但力度用 _strength_by_definition 独立算 —— 这一条是力度那一支唯一的守卫。
            a = next((q for q in range(z["PI0"] - 1, -1, -1)
                      if (AU[q]["p1"] < AU[q]["p0"]) == buy), None)
            if a is None:
                bad.append(("一类买卖点之前找不到同向的 A 段", s["kind"], s["bar"]))
            elif not _strength_by_definition(u, hist, measure) < \
                    _strength_by_definition(AU[a], hist, measure) * ratio:
                bad.append(("背驰不成立：独立重算 C 段力度不小于 A 段 × 比例", s["kind"], s["bar"]))
        if s["kind"] in ("二买", "二卖"):
            first = [t for t in sig if t["kind"] == ("一买" if buy else "一卖") and t["unit"] == s["unit"] - 2]
            if not first or not first[0]["confirmed"]:
                bad.append(("二类买卖点前面没有确认的一类买卖点", s["kind"], s["bar"]))
    return bad
