#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把中枢的延伸/终结判定，从「笔的区间是否触及」改成「第三类买卖点」。

旧规则（错）：只要后续某一笔的价格区间与原中枢区间有交集，就算延伸。
   → 但笔永远从上一笔的终点起步，而那个终点往往还在中枢里，
     于是几乎每一笔都"触及"，中枢永远不终结。

新规则（第 20 课）：
   某一笔向上离开（终点 > ZG），紧接着的下一笔回试也没回到 ZG 以内
   → 构成第三类买点 → 中枢到此终结。
   向下离开（终点 < ZD）后回抽不升破 ZD → 第三类卖点 → 同样终结。
   否则视为仍在围绕中枢波动 → 继续延伸。
"""
P = "/var/minis/workspace/chanlun_mag/core/center.py"
s = open(P, encoding="utf-8").read()

old = s[s.index("def find_centers"):]
new = '''def find_centers(pens):
    """pens: build_pens() 输出的笔列表。返回中枢列表。

    中枢 = 连续三笔的公共重叠区间；成立之后按「第三类买卖点」决定何时终结。
    """
    zs, i = [], 0
    N = len(pens)
    while i + 2 < N:
        a, b, c = pens[i], pens[i + 1], pens[i + 2]
        ZG = min(a["hi"], b["hi"], c["hi"])
        ZD = max(a["lo"], b["lo"], c["lo"])
        if ZG > ZD:                                   # 三笔确有公共重叠
            end = i + 2                               # 中枢至少覆盖到第三笔
            j = i + 3
            while j < N:
                p1 = pens[j]["p1"]                    # 这一笔的终点
                nxt = pens[j + 1]["p1"] if j + 1 < N else None
                if p1 > ZG and nxt is not None and nxt > ZG:
                    break                             # 三买 → 中枢终结于第 j-1 笔
                if p1 < ZD and nxt is not None and nxt < ZD:
                    break                             # 三卖 → 同上
                end = j
                j += 1
            zs.append(dict(
                X0=pens[i]["i0"],                     # 横向范围：第一笔起点 → 最后一笔终点
                X1=pens[end]["i1"],
                F1=pens[i + 2]["i1"],                 # 成立段终点 = 第三笔的终点
                ZG=ZG, ZD=ZD,
                live=(end == N - 1),                  # 是否延伸到数据末尾
                npens=end - i + 1,
            ))
            i = end + 1
        else:
            i += 1
    return zs
'''
open(P, "w", encoding="utf-8").write(s[:s.index("def find_centers")] + new)
print("engine patched")
