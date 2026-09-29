#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""c03：给真实数据补溯源，并新增「被丢掉的波动去哪了」一栏。"""
P = "/var/minis/workspace/chanlun_mag/cards/c03_pen.py"
s = open(P, encoding="utf-8").read()

s = s.replace('set_size(1400, 1950)', 'set_size(1400, 2190)')

old_c = s[s.index('# ============ C 真实数据 ============'):s.index('foot(d,')]
new_c = '''# ============ C 真实数据 ============
d.rounded_rectangle([56, 1616, W - 56, 1806], 20, fill=(GR[0], GR[1], GR[2], 24), outline=GR, width=3)
d.text((86, 1630), "真实数据：分型是廉价的，笔是筛出来的", font=f_p, fill=GR)
d.text((86, 1666), "币安合约 AAPLUSDT 永续　4小时 384 根 ／ 30分钟 3072 根　2026/07/26 – 09/27（UTC）",
       font=f_t, fill=MU)
d.text((86, 1700), "4 小时：127 个分型 → 25 条笔　（成笔 25 ／ 跳过 51 ／ 同类处理 50）", font=f_n, fill=TX)
d.text((86, 1732), "30 分钟：1057 个分型 → 232 条笔　（成笔 232 ／ 跳过 412 ／ 同类处理 412）", font=f_n, fill=TX)
d.text((86, 1768), "换算下来：平均约 5 个分型才筛出 1 条笔。", font=f_p, fill=AM)

# ============ D 丢掉的波动去哪了 ============
d.rounded_rectangle([56, 1836, W - 56, 2030], 20, fill=(BL[0], BL[1], BL[2], 26), outline=BL, width=3)
d.text((86, 1852), "被丢掉的那些分型，会不会把笔扯断？—— 不会", font=f_p, fill=LB)
d.text((86, 1892), "第 62 课原文：「所谓笔，就是顶和底之间的其他波动，都可以忽略不算」", font=f_n, fill=TX)
d.text((86, 1926), "所以被丢掉的分型不是「断口」，它只是被并进了这一笔的跨度里 —— 笔本身照样首尾相接。", font=f_n, fill=MU)
d.text((86, 1966), "实测：25 条笔首尾相接、0 处断点；逐根喂入 354 次，改动过的笔从未超过 1 条。", font=f_n, fill=AM)
d.text((86, 2000), "（换句话说：只有「最后一笔」会随新K线重画，更早的笔一旦成立就不再变。）", font=f_t, fill=MU)

'''
s = s.replace(old_c, new_c)
open(P, "w", encoding="utf-8").write(s)
print("patched")
