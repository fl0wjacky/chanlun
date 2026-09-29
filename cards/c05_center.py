#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""概念卡 05 中枢"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cards.base import *
import json
from core import analyze
from config import data

W, H = 1400, 2990                    # 卡片尺寸；模块常量，各段函数直接用
OUTNAME = "c05_中枢.png"

PA = [(110, 100), (100, 108), (108, 102)]          # A、B 两节共用的「下 - 上 - 下」三笔
CWC = 405                                          # C、D 两节的小格宽度（收进分节面板内）
X0C = (76, 497, 918)
T_TREND = [(110, 100), (100, 108), (108, 102), (102, 116), (116, 112), (112, 118), (118, 114)]
P_UP = [(110, 100), (100, 108), (108, 102), (102, 118), (118, 104),
        (104, 124), (124, 110), (110, 122), (122, 114)]
P_DN = [(220 - a, 220 - b) for a, b in P_UP]


def pts_of(pairs, x0, x1, Y):
    n, out = len(pairs), []
    for k in range(n + 1):
        p = pairs[0][0] if k == 0 else pairs[k - 1][1]
        out.append((x0 + k / n * (x1 - x0), Y(p)))
    return out


def draw_box(d, pt, PI0, PI1, Y, ZG, ZD, col=BL, label=None, dy=-28, below=False):
    x0, x1 = pt[PI0][0], pt[PI1 + 1][0]
    d.rectangle([x0, Y(ZG), x1, Y(ZD)], fill=col + (52,), outline=col, width=4)
    d.line([x0 - 30, Y(ZG), x1, Y(ZG)], fill=col + (100,), width=2)
    d.line([x0 - 30, Y(ZD), x1, Y(ZD)], fill=col + (100,), width=2)
    if label:
        lchip(d, x0 + 10, Y(ZD) + 8 if below else Y(ZG) + dy, label, col)
    return x0, x1


def dashed_band(d, x0, x1, Y, ZG, ZD, col=BL, w=5, dl=18, gp=13):
    d.rectangle([x0, Y(ZG), x1, Y(ZD)], fill=(235, 242, 255, 26))
    xx = x0
    while xx < x1:
        e = min(xx + dl, x1)
        d.line([xx, Y(ZG), e, Y(ZG)], fill=col, width=w)
        d.line([xx, Y(ZD), e, Y(ZD)], fill=col, width=w)
        xx = e + gp


def head_line(d, y0, y1, txt, desc, chip_dy=18):
    """分节面板 + 标题标签 + 标签右侧的说明。"""
    w = section(d, y0, y1, txt, chip_dy=chip_dy)
    if desc:
        d.text((80 + w + 40, y0 + chip_dy + 8), desc, font=f_n, fill=MU)


def minicell(d, x0, y0, w, h, title, pairs, ZG, ZD, pmin, pmax, note):
    d.rounded_rectangle([x0, y0, x0 + w, y0 + h], 16, fill=CARD, outline=LINE, width=2)
    d.text((x0 + 18, y0 + 12), title, font=f_p, fill=TX)
    m = Mini(d, x0 + 30, y0 + 62, x0 + w - 30, y0 + h - 52, pmin, pmax)
    pt = pts_of(pairs, x0 + 80, x0 + w - 80, m.Y)
    polyline(d, pt, BL, 6)
    draw_box(d, pt, 0, 2, m.Y, ZG, ZD, BL, "[%g, %g]" % (ZD, ZG), below=True)
    d.text((x0 + 18, y0 + h - 36), note, font=f_t, fill=MU)


def cell(d, x0, y0, w, title, tcol, pairs, pmin, pmax, notes, draw_fn, sub=None):
    d.rounded_rectangle([x0, y0, x0 + w, y0 + 450], 16, fill=CARD, outline=LINE, width=2)
    d.text((x0 + 18, y0 + 10), title, font=f_p, fill=tcol)
    if sub:
        d.text((x0 + 18, y0 + 40), sub, font=f_t, fill=MU)
    m = Mini(d, x0 + 30, y0 + 62, x0 + w - 30, y0 + 312, pmin, pmax)
    pt = pts_of(pairs, x0 + 50, x0 + w - 50, m.Y)
    polyline(d, pt, BL, 6)
    draw_fn(d, m, pt, x0, w)
    for k, t in enumerate(notes):
        d.text((x0 + 18, y0 + 322 + k * 26), t, font=f_t, fill=MU)


def f_ext(d, m, pt, x0, w):
    draw_box(d, pt, 0, 2, m.Y, 108, 102, BL)
    dashed_band(d, pt[3][0], pt[5][0], m.Y, 108, 102, BL)
    d.line([pt[3][0], m.Y(108), pt[3][0], m.Y(102)], fill=BL, width=4)
    lchip(d, pt[0][0] + 4, m.Y(108) - 34, "实线 = 成立段", (205, 222, 255))
    lchip(d, pt[3][0] + 6, m.Y(102) + 10, "虚线 = 延续段", AM)


def f_buy(d, m, pt, x0, w):
    draw_box(d, pt, 0, 2, m.Y, 108, 102, BL, "[102,108]", below=True)
    x, y = pt[5]
    d.ellipse([x - 9, y - 9, x + 9, y + 9], fill=GR)
    lchip(d, x - 16, y - 46, "三买", GR, anchor="r")


def f_sell(d, m, pt, x0, w):
    draw_box(d, pt, 0, 2, m.Y, 108, 102, BL, "[102,108]", below=True)
    x, y = pt[5]
    d.ellipse([x - 9, y - 9, x + 9, y + 9], fill=RD)
    lchip(d, x - 16, y + 24, "三卖", RD, anchor="r")


def f_two(d, m, pt, x0, w, A, B, ZGA, ZDA, ZGB, ZDB, ov=None):
    if ov:
        d.rectangle([pt[0][0], m.Y(ov[1]), pt[len(pt) - 1][0], m.Y(ov[0])],
                    fill=(255, 190, 60, 34), outline=AM, width=2)
    draw_box(d, pt, A[0], A[1], m.Y, ZGA, ZDA, BL)
    draw_box(d, pt, B[0], B[1], m.Y, ZGB, ZDB, GR)
    lchip(d, pt[A[0]][0] + 6, m.Y(ZGA) + 8, "A", (205, 222, 255))
    lchip(d, pt[B[1] + 1][0] - 80, m.Y(ZGB) + 8, "B", GR)


def draw_definition(d):
    """A 定义与公式"""
    head_line(d, 200, 800, "中枢 = 三段的重叠", "第 17 课：「某级别走势类型中，被至少三个连续次级别走势类型所重叠的部分」")
    ma = Mini(d, 180, 350, 1240, 620, 98.5, 112)
    ptA = pts_of(PA, 260, 1160, ma.Y)
    polyline(d, ptA, BL, 7)
    draw_box(d, ptA, 0, 2, ma.Y, 108, 102, BL, "中枢 [102, 108]", below=True)
    for x, y in ptA:
        d.ellipse([x - 8, y - 8, x + 8, y + 8], fill=(255, 255, 255, 230))
    for i in range(3):
        d.text(((ptA[i][0] + ptA[i + 1][0]) / 2 - 22, 630), "笔%d" % (i + 1), font=f_b, fill=MU)
    d.line([ptA[0][0], 288, ptA[3][0], 288], fill=CY, width=3)
    d.line([ptA[0][0], 288, ptA[0][0], 304], fill=CY, width=3)
    d.line([ptA[3][0], 288, ptA[3][0], 304], fill=CY, width=3)
    d.text((ptA[0][0] + 180, 294), "横向范围 = 第一笔起点 → 第三笔终点", font=f_t, fill=CY)
    d.text((80, 664), "公式（第 20 课）：A、B、C 的高、低点为 a1\\a2、b1\\b2、c1\\c2，区间 = [ max(a2,b2,c2) , min(a1,b1,c1) ]",
           font=f_n, fill=TX)
    d.text((80, 698), "本例 = [ max(100,100,102) , min(110,108,108) ] = [ 102 , 108 ]", font=f_n, fill=AM)
    d.text((80, 734), "第 20 课：「但无论是哪种情况，中枢的公式都可以简化为[max(a2，c2)，min(a1，c1)]」—— 结果一样。",
           font=f_t, fill=MU)
    d.text((80, 764), "口径：本卡用笔示意中枢（笔中枢是本项目口径）；原文最小级别中枢以线段为基础（第 65、78 课）。",
           font=f_t, fill=CY)


def draw_forms(d):
    """B 两种形成方向"""
    head_line(d, 816, 1200, "形成方式只有两种", "第 20 课：「而中枢的形成无非两种：一种是回升形成的；……一种是回调形成的」")
    UP = [(100, 110), (110, 102), (102, 108)]
    minicell(d, 76, 886, 614, 296, "① 下 - 上 - 下（回调形成）", PA, 108, 102, 98.5, 112,
             "区间 = [max(100,102), min(110,108)] = [102, 108]")
    minicell(d, 710, 886, 614, 296, "② 上 - 下 - 上（回升形成）", UP, 108, 102, 98.5, 112,
             "区间 = [max(100,102), min(110,108)] = [102, 108]")
    d.text((86, 1206), "★ 两种方向的算式完全一样 —— 化简后都只看「第 1 笔和第 3 笔」（A、C 段）的区间。", font=f_n, fill=AM)


def draw_single(d):
    """C 单个中枢：延伸 还是 终结"""
    head_line(d, 1240, 1802, "C  延续，还是被终结", "第 22 课：「中枢有三种运动：延续、扩展、新生」", chip_dy=14)
    cell(d, X0C[0], 1320, CWC, "C1 延续", BL, [(110, 100), (100, 108), (108, 102), (102, 107), (107, 103)],
         99.5, 111.5,
         ["后续 Z 段仍与 [ZD,ZG] 重叠，",
          "就是同一中枢（中心定理一）。",
          "后果：框一直往右长，中枢迟迟不终结。",
          "实测 4 小时：最长的覆盖了 13 笔。"], f_ext)
    cell(d, X0C[1], 1320, CWC, "C2 终结 · 三买", GR, [(110, 100), (100, 108), (108, 102), (102, 116), (116, 112)],
         99, 119,
         ["向上离开 116 > ZG 108，回试只到 112，",
          "没跌回 ZG 以内 → 三买 → 封口。",
          "封口后：或新生（范围不碰 → 趋势），",
          "或扩展成更大中枢（见 D2、D3）。"], f_buy)
    cell(d, X0C[2], 1320, CWC, "C3 终结 · 三卖", RD, [(100, 110), (110, 102), (102, 108), (108, 94), (94, 98)],
         92, 113,
         ["向下离开 94 < ZD 102，回抽只到 98，",
          "没升破 ZD → 三卖 → 同样封口。",
          "方向和 C2 相反，规则一样。"], f_sell)


def draw_pair(d):
    """D 两个中枢之间：趋势 还是 升级"""
    head_line(d, 1828, 2390, "D  被终结之后：新生（趋势）还是 扩展（更大级别中枢）",
              "判据：波动范围 [DD,GG] 碰不碰", chip_dy=14)
    cell(d, X0C[0], 1908, CWC, "D1 新生 · 趋势（范围不交）", GR, T_TREND, 99, 119,
         ["A 前 [102,108]　B 后 [114,116]",
          "定理二②：后 DD(112) > 前 GG(110)",
          "→ 上涨及其延续，也就是「趋势」",
          "（两个中枢的波动范围完全不碰）"],
         lambda d, m, pt, x0, w: f_two(d, m, pt, x0, w, (0, 2), (4, 6), 108, 102, 116, 114))
    cell(d, X0C[1], 1908, CWC, "D2 扩展 · 向上离开", AM, P_UP, 98, 127,
         ["A 前 [102,108]　B 后 [114,122]",
          "定理二④：后 ZD(114) > 前 ZG(108)",
          "且 后 DD(110) ≤ 前 GG(118) → 相交",
          "→ 等价于「形成高级别的走势中枢」"],
         lambda d, m, pt, x0, w: f_two(d, m, pt, x0, w, (0, 4), (6, 8), 108, 102, 122, 114, (110, 118)))
    cell(d, X0C[2], 1908, CWC, "D3 扩展 · 向下离开", AM, P_DN, 93, 122,
         ["A 前 [112,118]　B 后 [98,106]",
          "定理二③：后 ZG(106) < 前 ZD(112)",
          "且 后 GG(110) ≥ 前 DD(102) → 相交",
          "→ 同样「形成高级别的走势中枢」"],
         lambda d, m, pt, x0, w: f_two(d, m, pt, x0, w, (0, 4), (6, 8), 118, 112, 106, 98, (102, 110)))


def draw_extended(d):
    """E 扩展出来的大中枢，区间怎么算"""
    callout(d, 2420, 2688, GR, 20)
    chip(d, 80, 2438, "扩展出来的大中枢，区间怎么算？", GR, f_p)
    d.text((640, 2446), "第 49 课 + 第 52 课", font=f_n, fill=MU)
    d.text((86, 2494), "① 由什么构成：两个同级别中枢 ＋ 它们之间的连接段 = 三个次级别走势类型",
           font=f_n, fill=TX)
    d.text((86, 2528), "　 第 49 课：「相应连接两个次级别的，包含一个第三类买点，所以肯定也是一个次级别」",
           font=f_t, fill=MU)
    d.text((86, 2562), "② 原文只给原则：A ＋ B ＋ C ＝ (A ＋ B ＋ C)", font=f_n, fill=AM)
    d.text((86, 2596), "　 第 52 课：「其实就是 A+B+C=(A+B+C)，而后者符合更大的中枢定义」",
           font=f_t, fill=MU)
    d.text((86, 2626), "　 → 本项目口径：三段各取波动范围 [DD,GG]，再取公共重叠 [max(低), min(高)]（原文未写明）",
           font=f_t, fill=MU)


def draw_data(d):
    """F 数据"""
    callout(d, 2716, 2816, GR, 22)
    d.text((86, 2730), "实测（币安合约 AAPLUSDT 永续 · 2026/07/26 – 09/27 UTC）", font=f_n, fill=GR)
    r4, r30 = (analyze(json.load(open(data(fn), encoding="utf-8"))) for fn in ("aaplusdt_4h.json", "aaplusdt_30m.json"))
    d.text((86, 2770), "笔中枢　4 小时 %d 根 → %d 个 → 合成 %d 个大中枢　｜　30 分钟 %d 根 → %d 个 → 链式合并后剩 %d 个（出图时现算）"
           % (len(r4["bars"]), len(r4["centers"]), len(r4["big"]), len(r30["bars"]), len(r30["centers"]), len(r30["big"])),
           font=f_n, fill=TX)


def build():
    """画整张卡，返回 PIL Image。"""
    set_size(W, H)
    im, d = newcard("05", "中枢", "连续三段次级别走势的重叠区间 —— 把「震荡」变成一个可以算出来的坐标",
                    panel=False)
    draw_definition(d)
    draw_forms(d)
    draw_single(d)
    draw_pair(d)
    draw_extended(d)
    draw_data(d)
    foot(d, "第 17/20 课（定义与公式）；第 22 课（三种运动）；第 49/52 课（扩展）；第 65/78 课（最小中枢）",
         "延续何时停、扩展后大中枢区间怎么取，原文都只给原则；卡上的算法是本项目口径")
    return im


def main():
    build().save(OUT + OUTNAME)
    print("05")


if __name__ == "__main__":
    main()
