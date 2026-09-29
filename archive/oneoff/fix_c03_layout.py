#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""c03 版式修补：拉开层次，消除文字重叠。"""
P = "/var/minis/workspace/chanlun_mag/cards/c03_pen.py"
s = open(P, encoding="utf-8").read()

# 卡片加高
s = s.replace('set_size(1400, 1880)', 'set_size(1400, 1920)')

# ---- A 解剖图：重排纵向层次 ----
s = s.replace(
    'd.text((300, 226), "分型本身各占 3 根K线；两段之间至少要空出 1 根 —— 这 1 根才叫「独立K线」", font=f_n, fill=MU)',
    'd.text((300, 224), "分型各占 3 根K线；两段之间至少要空出 1 根 —— 这 1 根才叫「独立K线」", font=f_n, fill=MU)')
s = s.replace('ma = Mini(d, 180, 330, 1220, 620, 97.6, 103.2)',
              'ma = Mini(d, 180, 392, 1220, 648, 97.6, 103.2)')
s = s.replace('bracket(1, 3, 292, GR, "底分型（占 3 根）")', 'bracket(1, 3, 368, GR, "底分型（占 3 根）")')
s = s.replace('bracket(4, 4, 292, CY, "独立K线")', 'bracket(4, 4, 368, CY, "独立K线")')
s = s.replace('bracket(5, 7, 292, RD, "顶分型（占 3 根）")', 'bracket(5, 7, 368, RD, "顶分型（占 3 根）")')
s = s.replace('d.line([Xa(2), 232, Xa(6), 232], fill=AM, width=3)', 'd.line([Xa(2), 300, Xa(6), 300], fill=AM, width=3)')
s = s.replace('d.line([Xa(2), 232, Xa(2), 250], fill=AM, width=3)', 'd.line([Xa(2), 300, Xa(2), 318], fill=AM, width=3)')
s = s.replace('d.line([Xa(6), 232, Xa(6), 250], fill=AM, width=3)', 'd.line([Xa(6), 300, Xa(6), 318], fill=AM, width=3)')
s = s.replace('d.text((Xa(2) + 8, 238), "两个分型中心之间 = 5 根K线（可少于此数就不成笔）", font=f_n, fill=AM)',
              'd.text((Xa(2) + 10, 266), "两个分型中心之间 = 5 根K线（少于此数就不成笔）", font=f_n, fill=AM)')
s = s.replace('''for i, lab, col in ((2, "底", GR), (6, "顶", RD)):
    d.text((Xa(i) - 10, 648), lab, font=f_b, fill=col)
d.text((180, 648), "这笔：索引差 = 4（下限）→ 中间刚好空出 1 根独立K线", font=f_n, fill=MU)''',
'''d.text((180, 656), "本笔：索引差 = 4（下限）→ 中间刚好空出 1 根独立K线", font=f_n, fill=MU)''')

# ---- B 标题：说明右移 ----
s = s.replace('d.text((380, 751), "决定走哪条，只看两件事', 'd.text((520, 751), "决定走哪条，只看两件事')

# ---- cellc：mini 上移收紧，说明行下移；去掉与说明打架的端点标签 ----
s = s.replace('m = Mini(d, x0 + 40, y0 + 108, x0 + w - 40, y0 + 272, lo - pad, hi + pad)',
              'm = Mini(d, x0 + 40, y0 + 104, x0 + w - 40, y0 + 256, lo - pad, hi + pad)')
s = s.replace('d.text((x0 + 16, y0 + 288), note, font=f_t, fill=MU)',
              'd.text((x0 + 16, y0 + 300), note, font=f_t, fill=MU)')
s = s.replace('''      marks=[(1, "bot", GR), (5, "top", RD)],
      labels=[(1, "底", GR, "dn"), (5, "顶", RD, "up")], pen_ends=(1, 5))''',
              '      marks=[(1, "bot", GR), (5, "top", RD)], pen_ends=(1, 5))')
s = s.replace('''      marks=[(1, "top", RD), (5, "bot", GR)],
      labels=[(1, "顶", RD, "up"), (5, "底", GR, "dn")], pen_ends=(1, 5))''',
              '      marks=[(1, "top", RD), (5, "bot", GR)], pen_ends=(1, 5))')
s = s.replace('''      marks=[(1, "bot", GR), (3, "top", RD)],
      labels=[(1, "底", GR, "dn"), (3, "顶 ✗", RD, "up")])''',
              '      marks=[(1, "bot", GR), (3, "top", RD)],\n'
              '      labels=[(3, "✗ 太近", RD, "up")])')
s = s.replace('_m = Mini(d, 76 + 40, 1171 + 108, 76 + 614 - 40, 1171 + 272, 97.4, 102.1)',
              '_m = Mini(d, 76 + 40, 1171 + 104, 76 + 614 - 40, 1171 + 256, 97.4, 102.1)')
s = s.replace('''      labels=[(1, "顶(丢)", (120, 126, 146), "up"), (2, "底(丢)", (120, 126, 146), "dn"),
              (5, "顶(留)", GR, "up")])''',
              '      labels=[(5, "保留", GR, "up")])')

# ---- C 数据条：结论单独一行，面板加高 ----
s = s.replace('d.rounded_rectangle([56, 1585, W - 56, 1725], 20, fill=(GR[0], GR[1], GR[2], 24), outline=GR, width=3)',
              'd.rounded_rectangle([56, 1585, W - 56, 1765], 20, fill=(GR[0], GR[1], GR[2], 24), outline=GR, width=3)')
s = s.replace('d.text((900, 1681), "平均约 5 个分型才出 1 条笔", font=f_n, fill=AM)',
              'd.text((86, 1717), "换算下来：平均约 5 个分型才筛出 1 条笔。", font=f_p, fill=AM)')

open(P, "w", encoding="utf-8").write(s)
print("patched")
