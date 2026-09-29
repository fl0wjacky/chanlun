#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""卡 04c：线段结束的四种情况（向上/向下 × 有缺口/无缺口）"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cards.base import *

W, H = 1400, 1760                    # 卡片尺寸；模块常量，各段函数直接用
OUTNAME = "c04c_四种情况.png"
G2 = (68, 150, 130)


def cell(d, x0, y0, w, h, no, title, fdir, ftype, bars, gap, concl, col):
    d.rounded_rectangle([x0, y0, x0 + w, y0 + h], 16, fill=CARD, outline=LINE, width=2)
    d.text((x0 + 18, y0 + 12), no, font=F(30), fill=(80, 88, 106))
    d.text((x0 + 60, y0 + 16), title, font=f_p, fill=TX)
    d.text((x0 + 18, y0 + 58), "特征序列 = %s　→　找 %s" % (fdir, ftype), font=f_t, fill=MU)
    lo = min(b[1] for b in bars) - (max(b[0] for b in bars) - min(b[1] for b in bars)) * 0.22
    hi = max(b[0] for b in bars) + (max(b[0] for b in bars) - min(b[1] for b in bars)) * 0.22
    m = Mini(d, x0 + 60, y0 + 92, x0 + w - 60, y0 + h - 210, lo, hi)
    n = len(bars)
    step = (w - 120) / n
    X = lambda i: x0 + 60 + (i + 0.5) * step
    for i, (bhi, blo) in enumerate(bars):
        d.line([X(i), m.Y(bhi), X(i), m.Y(blo)], fill=G2, width=5)
        d.rectangle([X(i) - step * 0.28, m.Y(bhi), X(i) + step * 0.28, m.Y(blo)], fill=G2)
        lab = ("X%d" if "向上" in title else "S%d") % (i + 1)
        d.text((X(i) - 16, y0 + h - 202), lab, font=f_t, fill=G2)
    h1, l1 = bars[0][0], bars[0][1]
    h2, l2 = bars[1][0], bars[1][1]
    xa, xb = X(0) + step * 0.3, X(1) - step * 0.3
    if gap:
        # 向上：缺口在 X1 高点与 X2 低点之间；向下：在 S2 高点与 S1 低点之间
        gap_lo, gap_hi = (h1, l2) if l2 > h1 else (h2, l1)
        d.rectangle([xa, m.Y(gap_hi), xb, m.Y(gap_lo)], fill=RD + (80,))
        d.line([xa, m.Y(gap_hi), xb, m.Y(gap_hi)], fill=RD, width=3)
        d.line([xa, m.Y(gap_lo), xb, m.Y(gap_lo)], fill=RD, width=3)
    else:
        ov_lo, ov_hi = max(l1, l2), min(h1, h2)
        d.rectangle([xa, m.Y(ov_hi), xb, m.Y(ov_lo)], fill=GR + (130,), outline=GR, width=3)
    bx = x0 + 18
    if gap:
        d.rounded_rectangle([bx, y0 + h - 140, bx + 30, y0 + h - 122], 4, fill=RD)
        d.text((bx + 40, y0 + h - 144), "两根之间是缺口 → 第二种情况", font=f_t, fill=RD)
    else:
        d.rounded_rectangle([bx, y0 + h - 140, bx + 30, y0 + h - 122], 4, fill=GR)
        d.text((bx + 40, y0 + h - 144), "两根之间有重叠 → 第一种情况", font=f_t, fill=GR)
    d.rounded_rectangle([x0 + 18, y0 + h - 68, x0 + w - 18, y0 + h - 16], 10,
                        fill=col + (40,), outline=col, width=2)
    d.text((x0 + 34, y0 + h - 58), concl, font=f_t, fill=TX)


def draw_rule(d):
    """一句话记住规则"""
    d.rounded_rectangle([56, 200, W - 56, 336], 16, fill=(AM[0], AM[1], AM[2], 26), outline=AM, width=3)
    d.text((86, 214), "一句话记住规则", font=f_p, fill=AM)
    d.text((86, 256), "无缺口 → 【第一种情况】当场确认，线段在分型的高/低点结束。", font=f_n, fill=TX)
    d.text((86, 292), "有缺口 → 【第二种情况】要等「另一个特征序列」也出现分型，才回头确认那一点是终点。", font=f_n, fill=TX)


def draw_cells(d):
    """四种情况：向上/向下 × 无缺口/有缺口"""
    cell(d, 76, 366, 614, 500, "①", "向上线段 · 无缺口", "向下的笔", "顶分型",
         [(101, 97), (108, 100), (103, 98)], False,
         "→ 当场确认：线段在顶分型的高点（108）结束", GR)
    cell(d, 710, 366, 614, 500, "②", "向上线段 · 有缺口", "向下的笔", "顶分型",
         [(101, 97), (108, 103), (104, 99)], True,
         "→ 等第二个序列出【底分型】才确认终点是 108", RD)
    cell(d, 76, 890, 614, 500, "③", "向下线段 · 无缺口", "向上的笔", "底分型",
         [(105, 100), (102, 95), (104, 97)], False,
         "→ 当场确认：线段在底分型的低点（95）结束", GR)
    cell(d, 710, 890, 614, 500, "④", "向下线段 · 有缺口", "向上的笔", "底分型",
         [(105, 100), (97, 93), (103, 96)], True,
         "→ 等第二个序列出【顶分型】才确认终点是 93", RD)


def draw_note(d):
    """注意：第二个序列方向相反"""
    d.text((86, 1408), "注意：第 ② ④ 格里的「第二个序列」，方向和第一个是【相反】的 ——", font=f_t, fill=AM)
    d.text((86, 1436), "　　　向上线段：第一个序列 = 向下的笔，第二个序列 = 向上的笔。两者不是同一串。", font=f_t, fill=AM)
    d.text((86, 1472), "第 71 课：「……如果两个不同的特征序列之间的元素，讨论包含关系是没意义的。", font=f_t, fill=MU)
    d.text((86, 1500), "　　　　显然，特征序列的元素的方向，和其对应的段的方向是刚好相反的」", font=f_t, fill=MU)
    d.text((86, 1540), "包含处理（第 78 课）：第一种情况，假设分界点两边的元素不做包含处理；", font=f_t, fill=CY)
    d.text((86, 1568), "　　　　　　　　　　 第二种情况的第二特征序列，「必须严格按照包含关系的处理来」。", font=f_t, fill=CY)


def build():
    """画整张卡，返回 PIL Image。"""
    set_size(W, H)
    im, d = newcard("04c", "线段结束：四种情况", "向上/向下  ×  无缺口/有缺口 —— 第 67 课的两种情况",
                    panel=False)
    draw_rule(d)
    draw_cells(d)
    draw_note(d)
    foot(d, "第 67 课《线段的划分标准》两种情况；第 71 课（元素方向）；第 78 课（包含处理）",
         "以为「有缺口」和「无缺口」是同一个特征序列里的事 —— 其实第二层换了一个方向相反的序列")
    return im


def main():
    build().save(OUT + OUTNAME)
    print("04c")


if __name__ == "__main__":
    main()
