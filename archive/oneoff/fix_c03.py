#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一次性修补：把 c03 卡片里 cellc() 的参数设计理清。"""
import os

P = "/var/minis/workspace/chanlun_mag/cards/c03_pen.py"
s = open(P, encoding="utf-8").read()

NEW = '''def cellc(x0, y0, w, h, no, title, verdict, vcol, bars, note,
          marks=None, labels=None, pen_ends=None, pen_col=BL):
    """一个情形小格。
    marks  : [(索引, 'top'|'bot', 颜色)]       画分型三角
    labels : [(索引, 文本, 颜色, 'up'|'dn')]  在端点旁加字
    pen_ends: (i, j)                          画笔
    """
    d.rounded_rectangle([x0, y0, x0 + w, y0 + h], 16, fill=CARD, outline=LINE, width=2)
    d.text((x0 + 16, y0 + 8), no, font=F(28), fill=(78, 86, 104))
    d.text((x0 + 52, y0 + 12), title, font=f_p, fill=TX)
    cw = d.textlength(verdict, font=f_n) + 40
    d.rounded_rectangle([x0 + 16, y0 + 52, x0 + 16 + cw, y0 + 90], 10,
                        fill=vcol + (46,), outline=vcol, width=2)
    d.text((x0 + 36, y0 + 60), verdict, font=f_n, fill=vcol)
    lo = min(b[2] for b in bars); hi = max(b[1] for b in bars)
    pad = (hi - lo) * 0.14
    m = Mini(d, x0 + 40, y0 + 108, x0 + w - 40, y0 + 272, lo - pad, hi + pad)
    nn = len(bars)
    Xc = lambda i: m.X(i, nn)
    cs(m, Xc, m.Y, bars, w=34)
    if pen_ends:
        i, j = pen_ends
        d.line([Xc(i), m.Y(bars[i][2]), Xc(j), m.Y(bars[j][1])], fill=pen_col, width=6)
    for (i, kind, col) in (marks or []):
        x = Xc(i)
        if kind == "top":
            yv = m.Y(bars[i][1])
            d.polygon([(x, yv - 8), (x - 11, yv - 24), (x + 11, yv - 24)], fill=col)
        else:
            yv = m.Y(bars[i][2])
            d.polygon([(x, yv + 8), (x - 11, yv + 24), (x + 11, yv + 24)], fill=col)
    for (i, txt, col, side) in (labels or []):
        yv = m.Y(bars[i][1]) if side == "up" else m.Y(bars[i][2])
        d.text((Xc(i) - d.textlength(txt, font=f_t) / 2, yv + (-48 if side == "up" else 30)),
               txt, font=f_t, fill=col)
    d.text((x0 + 16, y0 + 288), note, font=f_t, fill=MU)


'''

a = s.index("def cellc(")
b = s.index("# ① 成笔·向上")
s = s[:a] + NEW + s[b:]

s = s.replace(
    '      [(1, "底", GR), (5, "顶", RD)], pen_ends=(1, 5),\n'
    '      marks=[(1, "bot", GR), (5, "top", RD)])',
    '      marks=[(1, "bot", GR), (5, "top", RD)],\n'
    '      labels=[(1, "底", GR, "dn"), (5, "顶", RD, "up")], pen_ends=(1, 5))')
s = s.replace(
    '      [(1, "顶", RD), (5, "底", GR)], pen_ends=(1, 5),\n'
    '      marks=[(1, "top", RD), (5, "bot", GR)])',
    '      marks=[(1, "top", RD), (5, "bot", GR)],\n'
    '      labels=[(1, "顶", RD, "up"), (5, "底", GR, "dn")], pen_ends=(1, 5))')

old3 = s[s.index('cellc(76, 1171'):s.index('# ④ 同类相遇')]
new3 = '''cellc(76, 1171, 614, 366, "③", "间隔不够", "不成笔 ✗", RD, P3,
      "底(索引1) → 顶(索引3)，只差 2 < 4 → 这个顶分型被丢弃",
      marks=[(1, "bot", GR), (3, "top", RD)],
      labels=[(1, "底", GR, "dn"), (3, "顶 ✗", RD, "up")])
# 用一条红虚线标出「两个分型只隔这么点」
_m = Mini(d, 76 + 40, 1171 + 108, 76 + 614 - 40, 1171 + 272, 97.4, 102.1)
d.line([_m.X(1, 5), _m.Y(100.5), _m.X(3, 5), _m.Y(99.8)], fill=RD, width=3)

'''
s = s.replace(old3, new3)

s = s.replace(
    '      [(1, "顶 ✗丢", AM), (2, "底 ✗丢", AM), (5, "顶 保留", GR)],\n'
    '      pen_ends=(1, 5), marks=[(1, "top", (120, 126, 146)), (2, "bot", (120, 126, 146)), (5, "top", GR)])',
    '      marks=[(1, "top", (120, 126, 146)), (2, "bot", (120, 126, 146)), (5, "top", GR)],\n'
    '      labels=[(1, "顶(丢)", (120, 126, 146), "up"), (2, "底(丢)", (120, 126, 146), "dn"),\n'
    '              (5, "顶(留)", GR, "up")])')

open(P, "w", encoding="utf-8").write(s)
print("patched")
