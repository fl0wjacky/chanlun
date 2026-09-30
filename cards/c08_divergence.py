#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""概念卡 08 背驰

2026-09-29 重做：旧版把「MACD 辅助判断」当成了背驰本身。
新版按原文分层：定义（同向两段的力度比较）→ 趋势背驰 → 盘整背驰 → 定理与级别。
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cards.base import *

W, H = 1400, 2586                    # 卡片尺寸；模块常量，各段函数直接用
OUTNAME = "c08_背驰.png"


def macd_bars(d, x0, x1, base, top, step=18):
    """一串 MACD 柱子：中间最高、两头收。base 是 0 轴像素 y，top 是最大柱高。"""
    n = max(2, int((x1 - x0) / step))
    for i in range(n):
        x = x0 + i * step
        h = top * (1 - abs(i - (n - 1) / 2) / max(1, (n - 1) / 2 + 0.6))
        h = max(h, top * 0.18)
        d.rectangle([x, base - h, x + step * 0.62, base], fill=UP)
    return base


def draw_definition(d):
    """A 定义：比的是同向两段的力度"""
    section(d, 200, 880, "背驰 = 同向两段，后一段力气更小", AM, chip_dy=16)
    d.text((620, 220), "不是「感觉涨不动」，是同向两段力度的比较；", font=f_n, fill=MU)
    d.text((620, 250), "背驰必有逆转，但逆转不等于大跌", font=f_n, fill=MU)

    # 价格：A 之前的中枢 → A 段上涨 → B 中枢 → C 段创新高（第 24 课：A 之前必须已有中枢）
    m = Mini(d, 130, 300, 1300, 530, 96, 138)
    pts = [(140, 97), (175, 104), (205, 100.5), (235, 104.5), (265, 101),
           (360, 120), (430, 116), (510, 122), (590, 117.5), (660, 121), (880, 133)]
    d.rectangle([165, m.Y(104), 250, m.Y(100.5)], fill=(120, 170, 255, 45), outline=BL, width=3)
    d.rectangle([400, m.Y(122), 620, m.Y(116.5)], fill=(120, 170, 255, 45), outline=BL, width=3)
    zigp(m, pts, BL, 6)
    lchip(d, 140, 536, "A 之前的中枢", BL)
    lchip(d, 300, 536, "A 段", BL)
    lchip(d, 430, 536, "B 段 = 中枢", BL)
    lchip(d, 700, 536, "C 段", BL)
    d.text((900, 300), "C 高点 133 > A 高点 120", font=f_n, fill=TX)
    d.text((900, 332), "价格还在创新高", font=f_t, fill=MU)

    # MACD 柱子：标签放 0 轴下方，不再压住柱子
    base = 700
    macd_bars(d, 272, 380, base, 86)
    macd_bars(d, 420, 640, base, 15)
    macd_bars(d, 680, 880, base, 38)
    d.line([130, base, 1300, base], fill=LINE, width=2)
    d.text((250, base + 10), "A 段柱子面积大", font=f_t, fill=(170, 178, 192))
    d.text((424, base + 10), "B 段缩小", font=f_t, fill=(170, 178, 192))
    d.text((684, base + 10), "C 段面积明显更小 → 背驰", font=f_t, fill=RD)

    d.text((86, 756), "第 15 课定义（趋势力度）：前一「吻」结束到后一「吻」开始，期间由短期均线与长期均线相交所形成的面积；",
           font=f_t, fill=TX)
    d.text((86, 786), "前后两个同向趋势中，后一次的趋势力度比上一次弱，就形成背驰。第 17 课又说：背驰是两相邻同向趋势间，",
           font=f_t, fill=TX)
    d.text((86, 816), "后者比前者的走势力度减弱所造成的。", font=f_t, fill=TX)
    d.text((500, 816), "第 24 课答疑：「背驰和什么均线都没有关系，说的是 MACD。」",
           font=f_t, fill=AM)


def draw_macd_premise(d):
    """B 用 MACD 判断的前提"""
    section(d, 900, 1330, "用 MACD 判断背驰的前提", CY, chip_dy=16)
    d.text((520, 926), "第 24 课前提（③在正文里，未编号）：不是看到「新高+柱子变短」就算", font=f_n, fill=MU)

    conds = [
        ("①", "有两段同向的趋势", "A 段与 C 段方向相同", CY),
        ("②", "中间一定有一个盘整或反向趋势连接", "这一段就是 B 段；B 的中枢级别比 A、C 里的中枢都大", CY),
        ("③", "A 段之前已有一个和 B 同级别或更大的中枢", "且不能是和 A 逆向的趋势，否则三段就在一个大中枢里了", CY),
    ]
    yy = 966
    for k, v, note, c in conds:
        d.rounded_rectangle([86, yy, 116, yy + 34], 8, fill=c + (50,))
        d.text((93, yy + 2), k, font=f_t, fill=c)
        d.text((132, yy + 2), v, font=f_n, fill=TX)
        d.text((132, yy + 30), note, font=f_t, fill=MU)
        yy += 68

    d.rounded_rectangle([86, 1176, W - 86, 1310], 14, fill=(GR[0], GR[1], GR[2], 26), outline=GR, width=2)
    d.text((110, 1188), "标准背驰的判据", font=f_n, fill=GR)
    d.text((110, 1224), "B 段这个中枢一般会把 MACD 的黄白线（DIFF、DEA）回拉到 0 轴附近；", font=f_t, fill=TX)
    d.text((110, 1254), "C 段的走势类型完成时，它对应的 MACD 柱子面积（向上看红、向下看绿）比 A 段的面积小 —— 这就是标准背驰。",
           font=f_t, fill=TX)
    d.text((110, 1284), "实操技巧：柱子伸长的力度变慢时，把已经出现的面积 ×2 当作该段面积，所以不必等回跌才发现。",
           font=f_t, fill=AM)


def draw_two_kinds(d):
    """C 趋势背驰 vs 盘整背驰"""
    section(d, 1350, 1960, "两种背驰，后果不一样", GR, chip_dy=16)
    d.text((480, 1376), "第 24 课：「一般不特别声明的，背驰都指最标准的趋势中形成的背驰」", font=f_n, fill=MU)

    CW, X0 = 614, (76, 710)
    # 左：趋势背驰
    d.rounded_rectangle([X0[0], 1420, X0[0] + CW, 1940], 16, fill=CARD, outline=LINE, width=2)
    d.text((X0[0] + 18, 1432), "趋势背驰（默认口径）", font=f_p, fill=GR)
    mt = Mini(d, X0[0] + 30, 1500, X0[0] + CW - 30, 1690, 98, 136)
    d.rectangle([140, mt.Y(106), 230, mt.Y(102.5)], fill=(0, 205, 125, 45), outline=GR, width=3)
    d.rectangle([360, mt.Y(122), 490, mt.Y(116.5)], fill=(0, 205, 125, 45), outline=GR, width=3)
    zigp(mt, [(118, 99), (150, 106), (180, 102.5), (210, 106.5), (240, 103),
              (330, 120), (380, 116.5), (440, 122), (490, 118), (580, 133)], BL, 6)
    d.text((120, mt.Y(106.5) - 34), "A 之前的中枢", font=f_t, fill=GR)
    d.text((368, mt.Y(122) - 34), "B 中枢", font=f_t, fill=GR)
    _ct = "C 段创新高"
    d.text((580 - 14 - d.textlength(_ct, font=f_t), mt.Y(133) - 14), _ct, font=f_t, fill=BL)
    for i, (t, c) in enumerate([("A 之前已有中枢，B 是同一大趋势里的另一个中枢。", TX),
                                ("一旦出现，回跌一定至少重新回到 B 段的中枢里。", TX),
                                ("第 24 课：「趋势背驰是最重要的」。", GR),
                                ("盘整背驰一般在盘整里弄短差时用（见右格）。", MU)]):
        d.text((X0[0] + 18, 1714 + i * 32), t, font=f_t, fill=c)

    # 右：盘整背驰
    d.rounded_rectangle([X0[1], 1420, X0[1] + CW, 1940], 16, fill=CARD, outline=LINE, width=2)
    d.text((X0[1] + 18, 1432), "盘整背驰（盘整里用同一套办法）", font=f_p, fill=AM)
    mp = Mini(d, X0[1] + 30, 1500, X0[1] + CW - 30, 1690, 96, 132)
    d.rectangle([900, mp.Y(119), 1100, mp.Y(113.5)], fill=(255, 190, 60, 45), outline=AM, width=3)
    zigp(mp, [(772, 104), (884, 118), (944, 114), (1014, 119.5), (1074, 116), (1160, 124.5)], BL, 6)
    d.text((908, mp.Y(119) - 34), "大中枢", font=f_t, fill=AM)
    d.ellipse([1160 - 9, mp.Y(124.5) - 9, 1160 + 9, mp.Y(124.5) + 9], fill=BG, outline=AM, width=4)
    _lt = "C 段上破中枢，但面积更小"
    d.text((1294 - d.textlength(_lt, font=f_t), 1500), _lt, font=f_t, fill=AM)
    d.text((X0[1] + 18, 1706), "情况 A（C 段不破中枢）：C 段面积小于 A 段，", font=f_t, fill=TX)
    d.text((X0[1] + 18, 1734), "　其后必定有回跌。", font=f_t, fill=TX)
    d.text((X0[1] + 18, 1768), "情况 B（C 段上破中枢）：原则是先出来，其后 ——", font=f_t, fill=TX)
    d.text((X0[1] + 18, 1796), "　a 回跌不重新跌回 → 在次级别的第一类买点回补，", font=f_t, fill=MU)
    d.text((X0[1] + 18, 1824), "　　 这恰好构成该级别的第三类买点；", font=f_t, fill=GR)
    d.text((X0[1] + 18, 1852), "　b 反之 → 继续该盘整。", font=f_t, fill=MU)
    d.text((X0[1] + 18, 1892), "盘整背驰一般用于盘整中弄短差；破中枢须分清这两种情况。", font=f_t, fill=MU)


def draw_theorems(d):
    """D 两条定理 + 级别"""
    section(d, 1980, 2416, "背驰之后会怎样：两条定理 + 一件事", RD, chip_dy=16)
    d.text((640, 2006), "白字是原文，灰字是我的白话（带「」的仍是原文）", font=f_n, fill=MU)

    rows = [
        ("背驰-买卖点定理（第 24 课）",
         "任一背驰都必然制造某级别的买卖点，任一级别的买卖点都必然源自某级别走势的背驰。",
         "看到背驰就必然有逆转 —— 但逆转不等于永远逆转。"),
        ("背驰-转折定理（第 29 课）",
         "某级别趋势的背驰将导致：①该趋势最后一个中枢的级别扩展；②或者该级别更大级别的盘整；③或者该级别以上级别的反趋势。",
         "背驰之后有且只有这三种结局，第三种才是通常说的「反转」。"),
        ("级别问题（第 24 课）",
         "背驰同样有级别的问题。一个 1 分钟级别的背驰，绝大多数情况下不会制造一个周线级别的大顶。",
         "逆转多少？——「重新出现新的次级别买卖点为止」。"),
    ]
    yy = 2046
    for k, v, note in rows:
        d.text((86, yy), k, font=f_n, fill=AM)
        d.text((86, yy + 30), v, font=f_t, fill=TX)
        d.text((86, yy + 58), note, font=f_t, fill=MU)
        yy += 96

    d.rounded_rectangle([86, 2326, W - 86, 2400], 12, fill=(CY[0], CY[1], CY[2], 26), outline=CY, width=2)
    d.text((110, 2334), "第 24 课：「光用 MACD 辅助判断，即使你对中枢不大清楚，只要能分清楚 A、B、C 三段，",
           font=f_t, fill=TX)
    d.text((110, 2364), "其准确率也应该在 90%以上。而配合上中枢，那是 100%绝对的……」", font=f_t, fill=TX)


def build():
    """画整张卡，返回 PIL Image。"""
    set_size(W, H)
    im, d = newcard("08", "背驰", "价格还在创新高，但拿同向的两段一比，后一段的力气反而更小", panel=False)
    draw_definition(d)
    draw_macd_premise(d)
    draw_two_kinds(d)
    draw_theorems(d)
    foot(d, "第 15 / 17 课（定义）；第 24 课（MACD、两种背驰、买卖点定理）；第 28 / 29 课（转折）",
         "把 MACD 当背驰、见背驰就重仓反手 —— 必有逆转（24 课），可能只是扩展或盘整（29），不必 V 反（28）")
    return im


def main():
    build().save(OUT + OUTNAME)
    print("08")




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
