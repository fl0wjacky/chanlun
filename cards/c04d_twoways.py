#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""卡 04d：第 67 课 vs 第 71 课 —— 同一个例子，两种走法"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cards.base import *

W, H = 1400, 1680                    # 卡片尺寸；模块常量，各段函数直接用
OUTNAME = "c04d_两种走法.png"
G2 = (68, 150, 130)


def draw_example(d):
    """例题"""
    section(d, 200, 520, "例题")
    d.text((200, 226), "向上线段的一段。假设有人提出：那个高点 V 可能是分界点 —— 怎么验？", font=f_n, fill=MU)
    m = Mini(d, 120, 292, 1280, 470, 92, 110)
    X = lambda i: 140 + i / 6 * 1120
    PATH = [94, 101, 97, 108, 103, 104, 99]        # X1(97~101)、X2(103~108)、X3(99~104)：顶分型 + 缺口
    polyline(d, [(X(i), m.Y(p)) for i, p in enumerate(PATH)], BL, 6)
    for i in range(6):
        xm = (X(i) + X(i + 1)) / 2
        lab = ["S1", "X1", "S2", "X2", "S3", "X3"][i]
        d.text((xm - 18, m.Y(max(PATH[i], PATH[i + 1])) - 40), lab, font=f_t, fill=MU)
    d.line([X(3), m.Y(108), X(6), m.Y(108)], fill=AM + (150,), width=2)
    d.ellipse([X(3) - 12, m.Y(108) - 12, X(3) + 12, m.Y(108) + 12], outline=AM, width=4)
    d.text((X(3) + 22, m.Y(108) - 34), "V", font=f_p, fill=AM)
    d.text((86, 480), "特征序列（向下的笔）＝ X1(97~101)、X2(103~108)、X3(99~104)", font=f_t, fill=TX)


def col(d, x0, title, sub, steps, accent):
    d.rounded_rectangle([x0, 552, x0 + 614, 1280], 18, fill=CARD, outline=accent, width=3)
    chip(d, x0 + 20, 570, title, accent, f_p)
    d.text((x0 + 20, 634), sub, font=f_t, fill=MU)
    yy = 676
    for k, (t, v) in enumerate(steps):
        d.rounded_rectangle([x0 + 20, yy, x0 + 60, yy + 34], 8, fill=accent + (60,))
        d.text((x0 + 33, yy + 4), str(k + 1), font=f_t, fill=accent)
        d.text((x0 + 74, yy + 3), t, font=f_n, fill=TX)
        d.text((x0 + 74, yy + 34), v, font=f_t, fill=MU)
        yy += 82


def draw_columns(d):
    """两栏：第 67 课 vs 第 71 课"""
    col(d, 76, "第 67 课的路子", "先搭结构，再找分型", [
        ("提取特征序列", "向下的笔 → X1、X2、X3"),
        ("做包含处理", "得到「标准特征序列」"),
        ("找顶分型（三个元素）", "X2 的高点和低点都最高 → 成立"),
        ("看分型前两个元素的缺口", "X1 上沿 101 ＜ X2 下沿 103 → 有缺口"),
        ("有缺口 → 第二种情况", "还要等第二个序列出底分型"),
        ("等到 → 线段在 V 结束", "终点 = 顶分型的高点 108"),
    ], BL)

    col(d, 710, "第 71 课的路子", "先假设分界点，再用两种情况去考察", [
        ("假设 V 是分界点", "不用先证明，先假设再验"),
        ("取第一元素 E1", "V 之前的最后一个特征元素 = X1"),
        ("取第二元素 E2", "从 V 开始的第一笔 = X2"),
        ("看 E1 与 E2 之间的缺口", "101 ＜ 103 → 有缺口"),
        ("有缺口 → 第二种情况", "然后「根据定义来考察」：同样要等底分型"),
        ("等到 → V 就是分界点", "终点同样是 108"),
    ], GR)


def draw_compare(d):
    """对照：两者的关系"""
    d.rounded_rectangle([56, 1308, W - 56, 1508], 18, fill=(AM[0], AM[1], AM[2], 26), outline=AM, width=3)
    d.text((86, 1324), "★ 两者的关系：71 课是 67 课的当下读法，不是省掉分型的另一套算法", font=f_p, fill=AM)
    d.text((86, 1370), "第 71 课先假设 V 是分界点，用 V 前后两个元素（E1、E2）判断是第一种还是第二种情况；", font=f_n, fill=TX)
    d.text((86, 1406), "之后仍要「根据定义来考察」—— 分型右侧元素原文比作「辅助线」，要大力去用；E1、E2 之间不做包含处理。",
           font=f_t, fill=MU)
    d.text((86, 1450), "第 71 课原话：「线段的划分，都是可以当下完成的……假设某转折点是两线段的分界点」", font=f_t, fill=CY)


def build():
    """画整张卡，返回 PIL Image。"""
    set_size(W, H)
    im, d = newcard("04d", "两种走法：67 课 vs 71 课",
                    "同一个例子算两遍 —— 71 课是 67 课的当下读法：先假设分界点，用前后两元素定情况",
                    panel=False)
    draw_example(d)
    draw_columns(d)
    draw_compare(d)
    foot(d, "第 67 课《线段的划分标准》；第 71 课《线段划分标准的再分辨》（当下的程序、辅助线、包含）",
         "以为 71 课省掉了分型 —— 两元素只决定是哪种情况；且分界点两侧不做包含处理")
    return im


def main():
    build().save(OUT + OUTNAME)
    print("04d")


if __name__ == "__main__":
    main()
