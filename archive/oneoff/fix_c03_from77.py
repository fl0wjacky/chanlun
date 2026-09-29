#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按第 77 课原文更新 03 卡片：精确双条件 + 划分三步骤 + 唯一性。"""
P = "/var/minis/workspace/chanlun_mag/cards/c03_pen.py"
s = open(P, encoding="utf-8").read()

s = s.replace('set_size(1400, 2190)', 'set_size(1400, 2450)')

# Panel A 底部：换成第 77 课的精确表述
s = s.replace('d.text((180, 656), "本笔：索引差 = 4（下限）→ 中间刚好空出 1 根独立K线", font=f_n, fill=MU)',
              'd.text((180, 656), "第 77 课：顶和底之间至少有一根K线「不属于顶分型与底分型」→ 索引差 ≥ 4", font=f_n, fill=MU)')
s = s.replace('d.text((790, 658), "底 = 底分型的最低点　顶 = 顶分型的最高点", font=f_n, fill=BL)',
              'd.text((790, 658), "底 = 底分型的最低点　顶 = 顶分型的最高点", font=f_n, fill=BL)')

# 新增 Panel E：原文的两个条件 + 三步骤 + 唯一性
s = s.replace('''# ============ C 真实数据 ============''',
'''# ============ E 原文：两个条件、三步骤、唯一性 ============
d.rounded_rectangle([56, 2094, W - 56, 2280], 20, fill=PANEL, outline=LINE, width=2)
head_line(2112, "原文怎么划笔（第 77 课）", "缠师在这一课里把笔的定义和算法一次讲完了")
d.text((86, 2160), "两个条件：① 顶和底之间至少有一根K线不属于顶分型与底分型（= 索引差 ≥ 4）",
       font=f_t, fill=TX)
d.text((86, 2190), "　　　　　② 顶分型中最高那根K线的区间，至少有一部分高于底分型中最低那根K线的区间", font=f_t, fill=TX)
d.text((86, 2220), "三步骤：一、标出所有符合标准的分型　二、前后同性质时——顶取更高者、底取更低者（相等都先留）",
       font=f_t, fill=TX)
d.text((86, 2250), "　　　　三、处理后相邻顶底即一笔；若相邻同性质，取「最先一个」", font=f_t, fill=TX)
d.text((600, 2250), "② ＋ ③ 的净效果 = 同类取更极端（本引擎如此实现）", font=f_t, fill=AM)

# ============ C 真实数据 ============''')

# footer 出处更新
s = s.replace('foot(d, "第 62 课：顶分型的最高点叫「顶」，底分型的最低点叫「底」；两个相邻的顶和底之间构成一笔",',
              'foot(d, "第 62 课（顶/底的定义）；第 77 课（笔的精确双条件、划分三步骤、唯一性证明）",')
open(P, "w", encoding="utf-8").write(s)
print("patched")
