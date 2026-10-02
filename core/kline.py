# -*- coding: utf-8 -*-
"""K线标准化（包含处理）与分型。

对应《教你炒股票》第 65 课。

这一段是整个引擎的地基：后面所有的笔、中枢、买卖点，输入都是这里
输出的『标准化序列』，而不是原始K线序列。两个概念必须严格分开：

    原始 K 线     例如 3072 根
    标准化序列    例如 2039 根   ← 分型/笔/中枢 全部基于它

每根标准化K线同时带两个位置编号：
    k  在标准化序列里的下标  → 用于逻辑（判断分型、数间隔）
    i  对应原始K线的下标     → 用于显示（画图、对时间）
"""


def quantize(bars, tick):
    """价格精度（第 64 课）：把最高 / 最低价按 tick 取整，差不到一个 tick 的看成相同。

    「所有预设精度，唯一必须遵守的，就是精度一旦预设，就一定要一路保持。」
    tick=None → 原样（即交易所的最小价位）。每个标的用什么精度，在 config.TICK 里明写。
    """
    if not tick:
        return bars
    q = lambda p: round(round(p / tick) * tick, 10)
    return [dict(b, h=q(b["h"]), l=q(b["l"])) for b in bars]


def _contains(a_h, a_l, b_h, b_l):
    """两根K线是否存在包含关系（任意一方完整罩住另一方）。

    只比较最高价与最低价 —— 开盘价、收盘价不参与。
    允许取等号（两根完全一样也算包含）。
    """
    return (a_h >= b_h and a_l <= b_l) or (b_h >= a_h and b_l <= a_l)


def _standardize_span(bars, start):
    """单段标准化：bars 是连续的一段原始K线，start 是它在全局序列里的起始下标。

    原算法（第 65 课）本体，不认断点——断点的切分在 standardize() 里做。
    i / ih / il 一律回补成全局下标，所以切几段拼起来和整段跑的坐标系一致。
    """
    n = len(bars)
    if n == 0:
        return []
    k = 1
    while k < n and _contains(bars[k - 1]["h"], bars[k - 1]["l"],
                              bars[k]["h"], bars[k]["l"]):
        k += 1
    if k >= n:                                   # 整段都在互相包含
        return [dict(h=bars[0]["h"], l=bars[0]["l"], i=start, ih=start, il=start)]

    # ih / il 记录『这个极值是哪一根原始K线贡献的』，供画图精确定位
    m = [dict(h=bars[k - 1]["h"], l=bars[k - 1]["l"], i=start + k - 1, ih=start + k - 1, il=start + k - 1),
         dict(h=bars[k]["h"], l=bars[k]["l"], i=start + k, ih=start + k, il=start + k)]
    for i in range(k + 1, n):
        bh, bl = bars[i]["h"], bars[i]["l"]
        p, p2 = m[-1], m[-2]
        up = p["h"] > p2["h"] or (p["h"] == p2["h"] and p["l"] > p2["l"])
        if _contains(p["h"], p["l"], bh, bl):
            if up:                               # 向上：两个端点都取高
                m[-1] = dict(h=max(p["h"], bh), l=max(p["l"], bl), i=start + i,
                             ih=start + i if bh > p["h"] else p["ih"],
                             il=start + i if bl > p["l"] else p["il"])
            else:                                # 向下：两个端点都取低
                m[-1] = dict(h=min(p["h"], bh), l=min(p["l"], bl), i=start + i,
                             ih=start + i if bh < p["h"] else p["ih"],
                             il=start + i if bl < p["l"] else p["il"])
        else:
            m.append(dict(h=bh, l=bl, i=start + i, ih=start + i, il=start + i))
    return m


def standardize(bars, breaks=None):
    """把原始K线序列压成标准化序列。单遍从左到右扫描，O(n)。

    bars: [{"h": 最高价, "l": 最低价, ...}, ...]

    规则（第 65 课）：
      方向：由『标准化序列的最后两根』决定（新的那根更高 → 向上，更低 → 向下）
      包含：新K线与『序列最后一根』比较
            · 包含   → 合并进最后一根（替换），序列长度不变
            · 『不包含』 → 追加为新的一根

    起点：找第一对『不包含』的相邻原始K线。前两根无法定方向，之前的丢弃。

    breaks: [{"i": 原始下标, "reason": ...}] 或 None（默认）。
            断点 i 表示 bars[i] 不得与 bars[i-1] 合并 —— 按断点把 bars 切成
            若干段，各段独立跑上面的规则，再拼起来（下标回补成全局的）。
            breaks=None / [] 时完全走原来的整段单遍，行为与不解断点时逐字节相同。

            断点处两侧**允许**残留包含关系：这正是断点的意思（隔夜/停牌/除权
            跳空，两根K线本来就不该被当成连续的包含）。所以有断点时，
            『相邻仍含包含关系』这条自检必须按段跑，别拿整段去跑
            check_standardized —— 那会把它自己的设计判成 bug。
            跨断点合并的专项检查见 check_no_cross_break_merge()。
    """
    if not breaks:
        return _standardize_span(bars, 0)
    n = len(bars)
    cuts = sorted({b["i"] for b in breaks if 0 < b["i"] < n})   # i=0（首根前面）无意义；越界丢弃
    out, prev = [], 0
    for c in cuts + [n]:
        out.extend(_standardize_span(bars[prev:c], prev))
        prev = c
    return out


def fractals(m):
    """在标准化序列上找分型。

    三根连续标准化K线，只有 4 种相对关系：
        上移+上移 → 不是分型        上移+下移 → 顶分型
        下移+上移 → 底分型          下移+下移 → 不是分型

    因为『相邻两根永不包含』（standardize 保证），所以
    『高点最高』自动蕴含『低点也最高』；这里仍写全 4 个条件，
    作为一道冗余保险 —— 万一标准化有 bug，两边会分叉，便于发现。
    """
    out = []
    for k in range(1, len(m) - 1):
        a, b, c = m[k - 1], m[k], m[k + 1]
        if b["h"] > a["h"] and b["h"] > c["h"] and \
           b["l"] > a["l"] and b["l"] > c["l"]:
            out.append(dict(k=k, i=b["ih"], type="top", price=b["h"]))
        elif b["l"] < a["l"] and b["l"] < c["l"] and \
                b["h"] < a["h"] and b["h"] < c["h"]:
            out.append(dict(k=k, i=b["il"], type="bot", price=b["l"]))
    return out


def check_standardized(m):
    """自检：标准化序列里相邻两根不应存在包含关系。

    等价于：相邻两根的高点必须不等、低点也必须不等。
    返回违规列表，正常情况下必须是空列表。
    """
    bad = []
    for i in range(len(m) - 1):
        a, b = m[i], m[i + 1]
        if _contains(a["h"], a["l"], b["h"], b["l"]):
            bad.append((i, a, b))
    return bad


def check_fractals_alternate(fx):
    """自检：分型的类型必须严格交替（顶、底、顶、底……）。

    分型的位置可以不连续（中间可以空几根不带分型的K线），
    但绝不会出现两个顶分型相邻（中间连一个底都没有）的情况。
    """
    return [(i, fx[i], fx[i + 1]) for i in range(len(fx) - 1)
            if fx[i]["type"] == fx[i + 1]["type"]]


def check_no_cross_break_merge(m, breaks):
    """自检（不变量 A）：标准化序列里任何一根都不得跨过断点去合并原始K线。

    断点 b 的含义是『bars[b] 不得与 bars[b-1] 合并』。所以第 b-1 根与第 b 根
    如果进了同一根标准化K线，这个断点就是被吃掉了。

    怎么从 m 反推『哪几根原始K线进了同一根』：合并只会发生在 m[-1] 上，
    所以第 k 根（k≥1）吃进去的原始K线是 m[k-1]["i"]+1 … m[k]["i"]，其中
    第一根是追加进新的一根（不是合并），从第二根起才是真合并。于是
    『b-1 与 b 同在一根里』等价于 m[k-1]["i"] + 2 ≤ b ≤ m[k]["i"]。

    breaks 为空 → 恒无违规（crypto 恒等那一侧的回归基准）。
    返回违规列表 [(标准化下标 k, 断点 b), ...]，正常情况下必须是空列表。
    """
    if not breaks:
        return []
    bs = sorted({b["i"] for b in breaks})
    bad = []
    for k in range(1, len(m)):
        lo, hi = m[k - 1]["i"] + 2, m[k]["i"]
        bad.extend((k, b) for b in bs if lo <= b <= hi)
    return bad
