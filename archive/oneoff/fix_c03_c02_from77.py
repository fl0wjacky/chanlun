#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""收尾：03 的 E 面板重排；02 补第 77 课的「结合律」约束。"""
import re

# ---------- 03 ----------
P = "/var/minis/workspace/chanlun_mag/cards/c03_pen.py"
s = open(P, encoding="utf-8").read()
s = s.replace("set_size(1400, 2470)", "set_size(1400, 2500)")
a = s.index('# ============ E 原文：两个条件、三步骤、唯一性 ============')
b = s.index('# ============ C 真实数据 ============')
s = s[:a] + '''# ============ E 原文：两个条件、三步骤、唯一性 ============
d.rounded_rectangle([56, 2094, W - 56, 2312], 20, fill=PANEL, outline=LINE, width=2)
chip(d, 80, 2112, "原文怎么划笔（第 77 课）", AM, f_p)
d.text((520, 2120), "缠师在这一课里把笔的定义和算法一次讲完了", font=f_n, fill=MU)
d.text((86, 2158), "两个条件：① 顶和底之间至少有一根K线不属于顶分型与底分型（= 索引差 ≥ 4）",
       font=f_t, fill=TX)
d.text((86, 2188), "　　　　　② 顶分型中最高那根K线的区间，至少有一部分高于底分型中最低那根K线的区间",
       font=f_t, fill=TX)
d.text((86, 2218), "三步骤：一、标出所有符合标准的分型　二、前后同性质时——顶取更高者、底取更低者（相等都先留）",
       font=f_t, fill=TX)
d.text((86, 2248), "　　　　三、处理后相邻顶底即一笔；若相邻同性质，取「最先一个」　→ 净效果 = 同类取更极端",
       font=f_t, fill=AM)
d.text((86, 2278), "★ 缠师在本课用反证法自己证明了：按这三步走，笔的划分是唯一的。", font=f_t, fill=GR)

''' + s[b:]
open(P, "w", encoding="utf-8").write(s)

# ---------- 02 ----------
P2 = "/var/minis/workspace/chanlun_mag/cards/c02_fractal.py"
s2 = open(P2, encoding="utf-8").read()
s2 = s2.replace("set_size(1400, 1600)", "set_size(1400, 1700)")
s2 = s2.replace("d.rounded_rectangle([56, 1044, W-56, 1372], 20", "d.rounded_rectangle([56, 1044, W-56, 1472], 20")
s2 = s2.replace('d.text((100, 1070), "三个必须记住的边界", font=f_p, fill=GR)',
                'd.text((100, 1070), "四个必须记住的边界", font=f_p, fill=GR)')
s2 = s2.replace('''    ("③ 分型只有「是 / 不是」",  "缠论对分型给出的定义就是二值的，没有给出「强度」的量化标准；凭肉眼看「这个分型强」不算判定。"),''',
'''    ("③ 分型只有「是 / 不是」",  "缠论对分型给出的定义就是二值的，没有给出「强度」的量化标准；凭肉眼看「这个分型强」不算判定。"),
    ("④ 相邻分型不能共用K线",   "第 77 课：任何相邻的分型之间必须满足结合律 —— 不能有些K线分属不同的分型。"),''')
open(P2, "w", encoding="utf-8").write(s2)
print("patched")
