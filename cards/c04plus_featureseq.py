#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""补充卡：特征序列 / 缺口 —— 从图上认出来。

用户反馈「特征序列、有缺口、无缺口 看不懂」，说明 04 卡缺一张认图的卡。
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cards.base import *

W, H = 1400, 2400
OUTNAME = "c04b_特征序列.png"

# 与 c04 同一组数据：前 5 笔是一条向上线段 96 → 112（第一种情况结束），后 3 笔是下一段的开头
PT = [96, 102, 98, 107, 101, 112, 104, 108, 100]
N = len(PT) - 1
SEG = 5
LAB = ["S1", "X1", "S2", "X2", "S3", "X3", "S4", "X4"]
G2 = (68, 150, 130)
XPOS = lambda i: 220 + i / N * 960


def draw_segment(d):
    """A 第 ① 步：先看一段走势（S 绿、X 红）"""
    section(d, 200, 640, "第 ① 步：先看一段走势")
    d.text((520, 226), "前 5 笔（S1 … S3）是一条向上线段，后 3 笔是下一段的开头", font=f_n, fill=MU)
    m = Mini(d, 200, 310, 1200, 560, 94, 116)
    q = [(XPOS(i), m.Y(p)) for i, p in enumerate(PT)]
    polyline(d, q[:SEG + 1], BL, 7)
    polyline(d, q[SEG:], (105, 115, 132), 4)
    for i in range(N):
        xm = (XPOS(i) + XPOS(i + 1)) / 2
        col = GR if LAB[i].startswith("S") else RD
        d.text((xm - 18, m.Y(max(PT[i], PT[i + 1])) - 42), LAB[i], font=f_n, fill=col)
    d.text((XPOS(SEG) - 30, m.Y(112) - 76), "112", font=f_t, fill=AM)
    d.text((86, 596), "向上的笔（S）标绿，向下的笔（X）标红；淡色部分已经是下一段。这条线段 5 笔，单数。",
           font=f_t, fill=MU)


def draw_down_pens(d):
    """B 第 ② 步：只看向下的笔 —— 这一串就是特征序列"""
    section(d, 670, 1190, "第 ② 步：只看那些「向下的笔」", GR)
    d.text((600, 696), "缠师把这一串单独拎出来，叫「特征序列」", font=f_n, fill=MU)
    m2 = Mini(d, 200, 740, 1200, 900, 94, 116)
    polyline(d, [(XPOS(i), m2.Y(p)) for i, p in enumerate(PT)], (105, 115, 132), 4)
    for i in (1, 3, 5, 7):
        d.line([XPOS(i), m2.Y(PT[i]), XPOS(i + 1), m2.Y(PT[i + 1])], fill=G2, width=9)
        d.text(((XPOS(i) + XPOS(i + 1)) / 2 - 18, m2.Y(max(PT[i], PT[i + 1])) - 42), LAB[i], font=f_n, fill=G2)
    d.text((86, 918), "把灰色的部分（向上的笔）暂时忘掉，只留下向下的：X1、X2、X3、X4。", font=f_n, fill=TX)
    d.text((86, 952), "（X3、X4 已在线段终点之后，但判断线段在哪结束，恰恰要靠它们 —— 见第 ③ 步）", font=f_t, fill=MU)
    d.rounded_rectangle([86, 990, W - 86, 1102], 12, fill=(GR[0], GR[1], GR[2], 30), outline=GR, width=2)
    d.text((108, 1002), "为什么看向下的，不看向上的？", font=f_t, fill=GR)
    d.text((108, 1036), "第 67 课：任何 Si 与 Si+1 之间一定有重合；而 Xi 与 Xi+1 之间「并不一定有重合」", font=f_t, fill=TX)
    d.text((108, 1066), "　　　—— 所以这一串更能代表线段的性质。", font=f_t, fill=TX)
    d.text((86, 1128), "把每一段向下的笔，当成一根 K 线（高点＝该笔起点，低点＝该笔终点）↓", font=f_t, fill=MU)


def draw_fractal(d):
    """C 第 ③ 步：把 X1~X4 当 K 线，先做包含处理，再找顶分型"""
    section(d, 1220, 1760, "第 ③ 步：在这串 K 线上找分型")
    d.text((560, 1246), "先做包含处理（标准特征序列）；向上线段只找「顶分型」", font=f_n, fill=MU)

    BAR = [(340, 102, 98), (560, 107, 101), (780, 112, 104), (1000, 108, 100)]
    mc = Mini(d, 280, 1300, 1150, 1560, 94, 116)
    for k, (x, hi, lo) in enumerate(BAR):
        col = AM if k == 2 else G2
        d.rectangle([x - 54, mc.Y(hi), x + 54, mc.Y(lo)], fill=col)
        d.text((x - 20, 1574), "X%d" % (k + 1), font=f_n, fill=col)
        d.text((x - 54, mc.Y(hi) - 34), "%d~%d" % (lo, hi), font=f_t, fill=MU)
    d.rectangle([560 + 54, mc.Y(107), 780 - 54, mc.Y(104)], fill=GR + (80,))
    d.text((86, 1616), "X1(98~102) → X2(101~107) → X3(104~112) → X4(100~108)：相邻两根都不包含，处理后不变。",
           font=f_t, fill=TX)
    d.text((86, 1648), "X3 的高点和低点都比左右两根高 → 顶分型 ✓；第一、二元素 X2、X3 有重叠（绿带 104~107）→ 无缺口。",
           font=f_t, fill=TX)
    d.text((86, 1690), "→ 第一种情况：顶分型的高点 112（S3 的终点）就是这条线段的终点。", font=f_n, fill=AM)


def draw_gap(d):
    """D 第 ④ 步：有缺口 / 无缺口 = 分型第一、二元素有没有重合区间"""
    section(d, 1790, 2240, "第 ④ 步：什么叫有缺口、无缺口", RD)
    d.text((600, 1816), "看分型的第一、二元素有没有重合区间", font=f_n, fill=MU)

    d.rounded_rectangle([80, 1864, 690, 2104], 14, fill=CARD, outline=GR, width=2)
    d.text((102, 1878), "无缺口（有重叠）", font=f_n, fill=GR)
    d.rectangle([116, 1964, 204, 2030], fill=G2)            # 第一元素（低）
    d.rectangle([286, 1924, 374, 1990], fill=G2)            # 第二元素（高）
    d.rectangle([204, 1964, 286, 1990], fill=GR + (80,))
    d.text((392, 1966), "这段有重叠", font=f_t, fill=GR)
    d.text((102, 2058), "→ 第一种情况：不等第二序列；第一笔终点被破才确认（71 课）", font=f_t, fill=TX)

    d.rounded_rectangle([710, 1864, W - 80, 2104], 14, fill=CARD, outline=RD, width=2)
    d.text((732, 1878), "有缺口（完全不重叠）", font=f_n, fill=RD)
    d.rectangle([746, 1990, 834, 2040], fill=G2)            # 第一元素（低）
    d.rectangle([916, 1916, 1004, 1964], fill=G2)           # 第二元素（高）
    d.line([834, 1977, 916, 1977], fill=RD, width=3)
    d.line([834, 1964, 834, 1990], fill=RD, width=2)
    d.line([916, 1964, 916, 1990], fill=RD, width=2)
    d.text((1022, 1966), "这一截没有重合", font=f_t, fill=RD)
    d.text((732, 2058), "→ 第二种情况：不能马上确认，要再等一个分型", font=f_t, fill=TX)

    d.text((86, 2120), "第 67 课：「特征序列的两相邻元素间没有重合区间，称为该序列的一个缺口。」", font=f_t, fill=TX)
    d.text((86, 2150), "→ 两根反向笔之间那段价格，其实被夹在中间的同向笔走过 —— 不是没成交，只是这两根不重叠。",
           font=f_t, fill=MU)
    d.text((86, 2186), "第 67 课：有缺口时，要等从该顶分型最高点开始的向下一笔起的特征序列出现底分型，才确认线段结束。",
           font=f_t, fill=MU)


def build():
    """画整张卡，返回 PIL Image。"""
    set_size(W, H)
    im, d = newcard("04b", "线段：把图画出来看", "「特征序列」不是抽象概念 —— 它就是线段里那些反方向的笔",
                    panel=False)
    draw_segment(d)
    draw_down_pens(d)
    draw_fractal(d)
    draw_gap(d)
    foot(d, "第 67 课《线段的划分标准》—— 特征序列 / 标准特征序列 / 分型 / 两种情况 / 缺口",
         "把特征序列当成陌生的抽象术语 —— 它只是那些反方向的笔")
    return im


def main():
    build().save(OUT + OUTNAME)
    print("04b")




# --- cardfit 失败分支声明（见 tools/cardfit.py 的 failure_modes()）--------------------------
# 三态必须分得开：**无此属性 = 没查过** / `[]` = 查过、没有 / 非空 = 逐支注入并自证。
# 本卡选了 `[]`，所以下面那句理由**不能省** —— 省了就是"一键消音"，把没查刷成查过。
CARDFIT_FAILURES = []
CARDFIT_NO_FAILURE = (
    "本卡正文全部是**字面量**，真实数据下逐条都画出过"
    "（判据：把画上去的字全收下来，看有没有哪条写了却从没出现）；"
    "卡里没有随数据分叉的判据支。量法与逐卡数据见 card-8b15761f-779。"
)

if __name__ == "__main__":
    main()
