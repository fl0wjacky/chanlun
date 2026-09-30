#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""概念卡 04 线段"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cards.base import *

W, H = 1400, 2560
OUTNAME = "c04_线段.png"

# A、B 两节共用的一段走势（9 个端点价 = 8 笔），与 c04b 同一组数据。
# 引擎回算（第 67 课口径）：前 5 笔 S1…S3 是一条向上线段 96 → 112，第一种情况结束；
# 后 3 笔 X3 S4 X4 是下一条向下线段的开头。
P = [96, 102, 98, 107, 101, 112, 104, 108, 100]
N = len(P) - 1
SEG = 5                                                  # 这条向上线段的笔数
LAB = ["S1", "X1", "S2", "X2", "S3", "X3", "S4", "X4"]
X = lambda i: 170 + i / N * 560


def draw_rules(d):
    """A 五条硬要求：线段至少三笔、前三笔重合、笔数单数……"""
    section(d, 200, 690, "线段是什么（第 77 课）")
    d.text((480, 226), "线段 = 至少三笔，且前三笔必须有重合", font=f_n, fill=MU)

    ma = Mini(d, 130, 366, 760, 600, 94, 116)
    q = [(X(i), ma.Y(p)) for i, p in enumerate(P)]
    polyline(d, q[:SEG + 1], BL, 6)
    polyline(d, q[SEG:], (105, 115, 132), 4)             # 下一段的开头，画淡
    for i in range(N):
        col = (GR if LAB[i].startswith("S") else RD) if i < SEG else DIM
        d.text(((X(i) + X(i + 1)) / 2 - 14, ma.Y(max(P[i], P[i + 1])) - 38), LAB[i],
               font=f_t, fill=col)
    d.line([X(0), 306, X(3), 306], fill=AM, width=3)
    d.line([X(0), 306, X(0), 330], fill=AM, width=3)
    d.line([X(3), 306, X(3), 330], fill=AM, width=3)
    d.text((X(0) + 6, 274), "前三笔必须有重合（这里是 98~102）", font=f_n, fill=AM)
    d.line([X(0), 622, X(SEG), 622], fill=CY, width=3)
    d.line([X(0), 622, X(0), 636], fill=CY, width=3)
    d.line([X(SEG), 622, X(SEG), 636], fill=CY, width=3)
    d.text((X(0) + 20, 630), "这条线段：5 笔（单数），96 → 112", font=f_t, fill=CY)
    d.text((X(SEG) + 30, 630), "↑ 淡色 = 下一段的开头", font=f_t, fill=DIM)

    d.rounded_rectangle([790, 300, W - 80, 664], 14, fill=(BL[0], BL[1], BL[2], 24), outline=BL, width=2)
    d.text((812, 316), "五条硬要求", font=f_n, fill=LB)
    for k, t in enumerate([
            "① 至少三笔（否则一笔就能当线段，两者没区别）",
            "② 开始的三笔 必须有重合",
            "③ 包含的笔数 必须是单数",
            "④ 两端分型性质相反 —— 不能从顶到顶、从底到底"]):
        d.text((812, 358 + k * 40), t, font=f_t, fill=TX)
    d.text((812, 536), "⑤ 必须被「另一个线段」破坏才算完成", font=f_t, fill=TX)
    d.text((812, 568), "　 （单单一笔刺破不算）", font=f_t, fill=MU)
    d.text((812, 614), "→ 线段是把「笔」聚成一层，比笔稳定得多", font=f_t, fill=AM)


def draw_feature_seq(d):
    """B 特征序列：把反向的笔当成 K 线再找分型"""
    cw = section(d, 712, 1330, "★ 核心：把「笔」当成「K线」再用一遍", GR)
    d.text((80 + cw + 20, 738), "第 67 课：「把每一元素看成是一 K 线」", font=f_n, fill=MU)

    d.text((86, 788), "向上笔开始的线段，写成序列：S1 X1 S2 X2 S3 X3 …", font=f_n, fill=TX)
    Q_SEG63 = "原文：「任何 Si 与 Si+1 之间，一定有重合区间。而考察序列 X1X2…Xn，该序列中，Xi 与 Xi+1 之间　　　并不一定有重合区间，因此，这序列更能代表线段的性质。」"
    d.text((86, 826), Q_SEG63[:59],
           font=f_t, fill=MU)
    d.text((86, 852), Q_SEG63[59:], font=f_t, fill=MU)
    d.rounded_rectangle([86, 892, W - 86, 942], 12, fill=(GR[0], GR[1], GR[2], 34), outline=GR, width=2)
    d.text((106, 904), "特征序列定义：① 序列 X1X2…Xn = 以向上笔开始线段的特征序列；"
                       "② 序列 S1S2…Sn = 以向下笔开始线段的特征序列。", font=f_t, fill=TX)

    mb = Mini(d, 130, 1000, 1260, 1190, 96, 114)
    G2 = (68, 150, 130)
    xs = {1: 330, 3: 590, 5: 850, 7: 1110}              # X1 X2 X3 X4 的横坐标
    for i, x in xs.items():                             # 每根向下笔画成一根 K 线
        hi, lo = max(P[i], P[i + 1]), min(P[i], P[i + 1])
        col = AM if i == 5 else G2
        d.rectangle([x - 26, mb.Y(hi), x + 26, mb.Y(lo)], fill=col)
        d.text((x - 50, mb.Y(hi) - 32), "X%d  %d~%d" % ((i + 1) // 2, lo, hi), font=f_t, fill=col)
    # X2、X3 的重叠带 = 无缺口
    d.rectangle([xs[3] + 26, mb.Y(107), xs[5] - 26, mb.Y(104)], fill=GR + (70,))
    d.text((xs[3] - 26, 1196), "绿带 = X2、X3 的重叠区 104~107 → 第一、二元素之间无缺口", font=f_t, fill=GR)
    d.text((xs[5] - 70, mb.Y(104) + 10), "↑ 顶分型：X3 高低点都最高", font=f_t, fill=AM)

    d.text((86, 1238), "本例：X3 与左右两根构成顶分型，且第一、二元素（X2、X3）重叠 → 第一种情况，线段在 112 结束。",
           font=f_t, fill=TX)
    d.text((86, 1282), "做法：把向下的每一笔当成一根 K 线 → 做包含处理（标准特征序列）→ 找顶分型 → 再按有无缺口判定终点",
           font=f_n, fill=GR)


def draw_two_cases(d):
    """C 两种情况：特征序列分型的前两元素之间有无缺口"""
    section(d, 1356, 1860, "线段结束的两种情况")
    d.text((480, 1382), "区别只在特征序列的分型里：前两个元素之间有没有缺口", font=f_n, fill=MU)
    d.rounded_rectangle([80, 1430, 690, 1740], 14, fill=CARD, outline=GR, width=2)
    d.text((102, 1446), "第一种 · 没有缺口", font=f_n, fill=GR)
    d.text((102, 1488), "特征序列的顶分型里，第一和第二元素之间", font=f_t, fill=TX)
    d.text((102, 1516), "不存在缺口 → 该线段在顶分型的高点处结束。", font=f_t, fill=TX)
    d.text((102, 1564), "→ 一次确认就够了，干脆。", font=f_t, fill=MU)
    d.text((102, 1610), "以向上笔开始的线段，只考察 顶分型；", font=f_t, fill=TX)
    d.text((102, 1638), "以向下笔开始的线段，只考察 底分型。", font=f_t, fill=TX)
    d.text((102, 1690), "（上一节的例子就是这一种）", font=f_t, fill=DIM)

    d.rounded_rectangle([710, 1430, W - 80, 1740], 14, fill=CARD, outline=RD, width=2)
    d.text((732, 1446), "第二种 · 有缺口", font=f_n, fill=RD)
    d.text((732, 1488), "第一和第二元素之间有缺口 → 不能马上确认，", font=f_t, fill=TX)
    d.text((732, 1516), "还要等从该分型最高点开始的向下一笔起，", font=f_t, fill=TX)
    d.text((732, 1544), "其特征序列也出现底分型，才确认结束。", font=f_t, fill=TX)
    d.text((732, 1586), "→ 要来回确认一次，所以线段会晚一步确认。", font=f_t, fill=MU)
    d.text((732, 1628), "第 67 课：后一序列不一定封闭前一序列的缺口；", font=f_t, fill=TX)
    d.text((732, 1656), "且第二序列中的分型，不分第一二种情况。", font=f_t, fill=TX)
    d.text((732, 1700), "（这是最容易绕晕的一处 —— 先记有无缺口）", font=f_t, fill=DIM)

    Q_SEG112 = "第 71 课：「特征序列的分型中，第一元素就是以该假设转折点前线段的最后一个特征元素，　　　　　第二个元素，就是从这转折点开始的第一笔」"
    d.text((86, 1760), Q_SEG112[:43],
           font=f_t, fill=CY)
    d.text((86, 1788), Q_SEG112[43:], font=f_t, fill=CY)
    d.text((86, 1822), "→ 缺口看的就是这两根：转折点前的最后一根反向笔，与转折点后的第一笔。", font=f_t, fill=MU)


def draw_why(d):
    """D 为什么值得学：笔层的类中枢不稳，线段才是最小中枢的零件"""
    callout(d, 1886, 2390, GR, 22)
    chip(d, 80, 1904, "为什么这一层不能跳过", GR, f_p)
    d.text((86, 1964), "第 83 课：「为什么不能由笔构成最小中枢？……用笔当成构成最小中枢的零件，但这样构造出来的系统，其稳定性极差。」", font=f_t, fill=TX)
    d.text((86, 2000), "　　　　「一笔的基础是顶和底分型，而一些瞬间的交易，就足以影响其结构。……而由线段构成最小中枢，则不存在这个问题。」", font=f_t, fill=TX)
    d.text((86, 2044), "→ 笔是快照，线段是经过一次确认的结构。常见指标画的多是笔层的类中枢（不稳定那一档）；",
           font=f_n, fill=AM)
    d.text((86, 2076), "　 线段才是正规最小中枢的零件（第 64 课「线段以下是没有中枢的，所以说是类中枢」）。", font=f_n, fill=AM)
    d.text((86, 2124), "★ 实做之后看到的一件事：第 67、71、78 课讲的是同一个定义，要三课一起读。", font=f_n, fill=CY)
    d.text((86, 2156), "　 ① 包含处理不能跨过假设的分界点 —— 第 71 课：前后两元素「是不存在包含关系的」；",
           font=f_t, fill=TX)
    d.text((86, 2184), "　 ② 第一笔「属於中间地带」（71 课）、第二种情况未出分型（78 课）都是待定，揭晓前不判（v1 笔上 AAPL 30 分钟由此 21 → 24 段）。",
           font=f_t, fill=TX)
    d.text((86, 2232), "★ 实做之后的验证：扰一根K线，看「一个偶尔一笔的错误」能传播多远", font=f_n, fill=GR)
    d.text((86, 2266), "　 样本：影子系统 15 分钟数据（3 标的 × 20000 根 × 60 次随机单根扰动，幅度 ±0.5%）", font=f_t, fill=MU)
    d.text((86, 2294), "　 60 次单根扰动中，笔端点有变化的占 13~23%　｜　线段端点有变化的占 3~5%", font=f_n, fill=TX)
    d.text((86, 2324), "　 → 线段的变化率比笔低约 4~7 倍（tools/calibrate_perturb1.py，v2 引擎回算）。", font=f_n, fill=AM)
    d.text((86, 2354), "　 与第 83 课「一个线段的改变，不会因为一个偶尔一笔的错误而改变」一致（样本小，仅作示意）。",
           font=f_t, fill=AM)


def build():
    """画整张卡，返回 PIL Image。"""
    set_size(W, H)
    im, d = newcard("04", "线段", "把几笔合成一层 —— 而合成的方法，是把「笔」当成「K线」再用一遍", panel=False)
    draw_rules(d)
    draw_feature_seq(d)
    draw_two_cases(d)
    draw_why(d)
    foot(d, "第 67 课（特征序列、两种情况）；第 71 课（分型的第一、二元素）；第 77 课（五条硬要求）；第 83 课",
         "跳过线段直接用笔 —— 相当于跳过了一次确认，结构的稳定性会差一个档次")
    return im


def main():
    build().save(OUT + OUTNAME)
    print("04")




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
