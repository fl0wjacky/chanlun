# -*- coding: utf-8 -*-
"""K线标准化（包含处理）与分型。

对应《教你炒股票》第 65 课。

这一段是整个引擎的地基：后面所有的笔、中枢、买卖点，输入都是这里
输出的「标准化序列」，而不是原始K线序列。两个概念必须严格分开：

    原始 K 线     例如 3072 根
    标准化序列    例如 2039 根   ← 分型/笔/中枢 全部基于它

每根标准化K线同时带两个位置编号：
    k  在标准化序列里的下标  → 用于逻辑（判断分型、数间隔）
    i  对应原始K线的下标     → 用于显示（画图、对时间）
"""


def _contains(a_h, a_l, b_h, b_l):
    """两根K线是否存在包含关系（任意一方完整罩住另一方）。

    只比较最高价与最低价 —— 开盘价、收盘价不参与。
    允许取等号（两根完全一样也算包含）。
    """
    return (a_h >= b_h and a_l <= b_l) or (b_h >= a_h and b_l <= a_l)


def standardize(bars):
    """把原始K线序列压成标准化序列。单遍从左到右扫描，O(n)。

    bars: [{"h": 最高价, "l": 最低价, ...}, ...]

    规则（第 65 课）：
      方向：由「标准化序列的最后两根」决定（新的那根更高 → 向上，更低 → 向下）
      包含：新K线与「序列最后一根」比较
            · 包含   → 合并进最后一根（替换），序列长度不变
            · 不包含 → 追加为新的一根

    起点：找第一对「不包含」的相邻原始K线。前两根无法定方向，之前的丢弃。
    """
    n = len(bars)
    if n == 0:
        return []
    k = 1
    while k < n and _contains(bars[k - 1]["h"], bars[k - 1]["l"],
                              bars[k]["h"], bars[k]["l"]):
        k += 1
    if k >= n:                                   # 整段都在互相包含
        return [dict(h=bars[0]["h"], l=bars[0]["l"], i=0, ih=0, il=0)]

    # ih / il 记录「这个极值是哪一根原始K线贡献的」，供画图精确定位
    m = [dict(h=bars[k - 1]["h"], l=bars[k - 1]["l"], i=k - 1, ih=k - 1, il=k - 1),
         dict(h=bars[k]["h"], l=bars[k]["l"], i=k, ih=k, il=k)]
    for i in range(k + 1, n):
        bh, bl = bars[i]["h"], bars[i]["l"]
        p, p2 = m[-1], m[-2]
        up = p["h"] > p2["h"] or (p["h"] == p2["h"] and p["l"] > p2["l"])
        if _contains(p["h"], p["l"], bh, bl):
            if up:                               # 向上：两个端点都取高
                m[-1] = dict(h=max(p["h"], bh), l=max(p["l"], bl), i=i,
                             ih=i if bh > p["h"] else p["ih"],
                             il=i if bl > p["l"] else p["il"])
            else:                                # 向下：两个端点都取低
                m[-1] = dict(h=min(p["h"], bh), l=min(p["l"], bl), i=i,
                             ih=i if bh < p["h"] else p["ih"],
                             il=i if bl < p["l"] else p["il"])
        else:
            m.append(dict(h=bh, l=bl, i=i, ih=i, il=i))
    return m


def fractals(m):
    """在标准化序列上找分型。

    三根连续标准化K线，只有 4 种相对关系：
        上移+上移 → 不是分型        上移+下移 → 顶分型
        下移+上移 → 底分型          下移+下移 → 不是分型

    因为「相邻两根永不包含」（standardize 保证），所以
    「高点最高」自动蕴含「低点也最高」；这里仍写全 4 个条件，
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
