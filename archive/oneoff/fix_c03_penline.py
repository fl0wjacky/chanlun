#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修正 c03：向下笔画反了 + ④不该有笔线 + 补第62课原文口径。"""
P = "/var/minis/workspace/chanlun_mag/cards/c03_pen.py"
s = open(P, encoding="utf-8").read()

# 1) cellc：按分型类型取极值点，而不是写死「左低右高」
s = s.replace(
    '          marks=None, labels=None, pen_ends=None, pen_col=BL):',
    '          marks=None, labels=None, pen_pts=None, pen_col=BL):')
s = s.replace(
    '    pen_ends: (i, j)                          画笔',
    '    pen_pts: [(i, \'top\'|\'bot\'), (j, ...)]    画笔（按分型类型取极值点）')
s = s.replace(
    '''    if pen_ends:
        i, j = pen_ends
        d.line([Xc(i), m.Y(bars[i][2]), Xc(j), m.Y(bars[j][1])], fill=pen_col, width=6)''',
    '''    if pen_pts:
        (i, ki), (j, kj) = pen_pts
        yi = m.Y(bars[i][1] if ki == "top" else bars[i][2])
        yj = m.Y(bars[j][1] if kj == "top" else bars[j][2])
        d.line([Xc(i), yi, Xc(j), yj], fill=pen_col, width=6)''')

# 2) ① 向上笔
s = s.replace(
    "      marks=[(1, \"bot\", GR), (5, \"top\", RD)], pen_ends=(1, 5))",
    "      marks=[(1, \"bot\", GR), (5, \"top\", RD)],\n"
    "      pen_pts=[(1, \"bot\"), (5, \"top\")])")
# 3) ② 向下笔
s = s.replace(
    "      marks=[(1, \"top\", RD), (5, \"bot\", GR)], pen_ends=(1, 5))",
    "      marks=[(1, \"top\", RD), (5, \"bot\", GR)],\n"
    "      pen_pts=[(1, \"top\"), (5, \"bot\")])")

# 4) ③ 不成笔：改用「间隔」指示，不要画成笔
s = s.replace(
    '''# 用一条红虚线标出「两个分型只隔这么点」
_m = Mini(d, 76 + 40, 1202 + 104, 76 + 614 - 40, 1202 + 256, 97.4, 102.1)
d.line([_m.X(1, 5), _m.Y(100.5), _m.X(3, 5), _m.Y(99.8)], fill=RD, width=3)''',
    '''# 标出两个分型的间隔（不画笔 —— 因为这里压根没成笔）
_g = Mini(d, 76 + 40, 1202 + 104, 76 + 614 - 40, 1202 + 256, 97.4, 102.1)
_gx1, _gx3, _gy = _g.X(1, 5), _g.X(3, 5), 1202 + 244
d.line([_gx1, _gy, _gx3, _gy], fill=RD, width=3)
d.line([_gx1, _gy - 9, _gx1, _gy + 9], fill=RD, width=3)
d.line([_gx3, _gy - 9, _gx3, _gy + 9], fill=RD, width=3)
d.text((_gx1 - 4, _gy + 12), "间隔 = 2，要 ≥ 4 才成笔", font=f_t, fill=RD)''')

# 5) ④ 同类：这里也没成笔，去掉那条蓝线
s = s.replace(
    '      marks=[(1, "top", (120, 126, 146)), (2, "bot", (120, 126, 146)), (5, "top", GR)],\n'
    '      labels=[(5, "保留", GR, "up")])',
    '      marks=[(1, "top", (120, 126, 146)), (2, "bot", (120, 126, 146)), (5, "top", GR)],\n'
    '      labels=[(1, "丢", (120, 126, 146), "up"), (5, "留", GR, "up")])')

# 6) 解剖图右下角：改用第62课的原文口径
s = s.replace(
    'd.text((840, 658), "连线：底分型最低点 → 顶分型最高点", font=f_n, fill=BL)\n'
    'd.text((840, 690), "向下笔反过来：顶分型最高点 → 底分型最低点", font=f_n, fill=BL)',
    'd.text((790, 658), "底 = 底分型的最低点　顶 = 顶分型的最高点", font=f_n, fill=BL)\n'
    'd.text((790, 690), "笔 = 两个相邻的「顶」与「底」之间", font=f_n, fill=BL)')

# 7) 页脚换成第62课原文
s = s.replace('foot(d, "第 65 课《再说说分型、笔、线段》",',
              'foot(d, "第 62 课：顶分型的最高点叫「顶」，底分型的最低点叫「底」；两个相邻的顶和底之间构成一笔",')
open(P, "w", encoding="utf-8").write(s)
print("patched")
