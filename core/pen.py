# -*- coding: utf-8 -*-
"""笔：把标准化序列切成一节一节。

一笔 = 一个顶分型 + 一个底分型相连，且两者之间隔够K线。
「隔够」的度量在标准化序列上做（用 k 的差），不是在原始K线上做。

min_gap = 4 对应流传最广的「整笔至少跨 5 根K线」口径。
这个口径没有官方唯一定论（传统笔 / 新笔 / 4K 各不相同），
选定一种就必须一路保持，否则回测不可复现。
"""


def build_pens(fx, min_gap=4):
    """fx: fractals() 的输出。返回 (笔列表, 笔端点序列)。

    处理同类型分型连续出现的情况：此时取更极端的那个作为端点
    （更高的顶 / 更低的底），而不是两个都留。
    """
    seq = []
    for f in fx:
        if not seq:
            seq.append(f)
            continue
        last = seq[-1]
        if f["type"] == last["type"]:
            if (f["type"] == "top" and f["price"] > last["price"]) or \
               (f["type"] == "bot" and f["price"] < last["price"]):
                seq[-1] = f
        else:
            if f["k"] - last["k"] >= min_gap:
                seq.append(f)

    pens = []
    for a, b in zip(seq, seq[1:]):
        pens.append(dict(
            i0=a["i"], i1=b["i"],          # 原始K线下标（画图用）
            x0=a["k"], x1=b["k"],          # 标准化序列下标（逻辑用）
            p0=a["price"], p1=b["price"],
            hi=max(a["price"], b["price"]),
            lo=min(a["price"], b["price"]),
        ))
    return pens, seq
