#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""概念卡 09 三类买卖点

2026-09-29 重做：旧版只有三个买点、定理被简化掉「次级别走势类型」这层。
新版补上三个卖点（镜像），并按第 20 课原文完整引用定理，加第 21 课完备性。
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cards.base import *

W, H = 1400, 2760                    # 卡片尺寸；模块常量，各段函数直接用
OUTNAME = "c09_三类买卖点.png"


def mkchart(d, x0, x1, y0, y1, pmin, pmax, prices, boxes=(), marks=(), col=BL):
    """画一条折线 + 若干中枢框 (起点序号, 终点序号, ZG, ZD) + 若干标记点。返回 (Mini, X 函数)。"""
    m = Mini(d, x0, y0, x1, y1, pmin, pmax)
    n = len(prices) - 1
    X = lambda i: x0 + i / n * (x1 - x0)
    for a, b, hi, lo in boxes:
        d.rectangle([X(a), m.Y(hi), X(b), m.Y(lo)], fill=col + (45,), outline=col, width=3)
    polyline(d, [(X(i), m.Y(p)) for i, p in enumerate(prices)], col, 6)
    for i, txt, col2, dy in marks:
        px, py = X(i), m.Y(prices[i])
        d.ellipse([px - 10, py - 10, px + 10, py + 10], fill=BG, outline=col2, width=5)
        tw = d.textlength(txt, font=f_n)
        d.text((px - tw / 2, py + dy), txt, font=f_n, fill=col2)
    return m, X


def draw_theorem(d):
    """A 定理原文"""
    section(d, 200, 540, "第 20 课：第三类买卖点定理（原文）", GR, chip_dy=16)
    d.text((720, 226), "这条定理是「第三类」，前两类另有说法，见下面 C 面板", font=f_n, fill=MU)

    d.rounded_rectangle([86, 272, W - 86, 342], 12, fill=(GR[0], GR[1], GR[2], 22), outline=GR, width=2)
    d.text((108, 280), "买：一个次级别走势类型向上离开缠中说禅走势中枢，然后以一个次级别走势类型回试，",
           font=f_t, fill=TX)
    d.text((108, 310), "　　其低点不跌破 ZG，则构成第三类买点。", font=f_t, fill=TX)

    d.rounded_rectangle([86, 350, W - 86, 420], 12, fill=(RD[0], RD[1], RD[2], 22), outline=RD, width=2)
    d.text((108, 358), "卖：一个次级别走势类型向下离开缠中说禅走势中枢，然后以一个次级别走势类型回抽，",
           font=f_t, fill=TX)
    d.text((108, 388), "　　其高点不升破 ZD，则构成第三类卖点。", font=f_t, fill=TX)

    d.text((86, 432), "两个容易读丢的字眼：①「次级别走势类型」出现了两次 —— 离开的和回试的，都必须是次级别走势类型，"
                      "级别不能丢；", font=f_t, fill=AM)
    d.text((86, 464), "② 第 20 课紧接着补了一句：「并不是任何回调回抽都是第三类买卖点，必须是第一次。」",
           font=f_t, fill=AM)
    d.text((86, 496), "③ 第三类买卖点比第一、二类要后知后觉，但抓得好往往不用浪费盘整的时间（第 20 课）。",
           font=f_t, fill=MU)


def draw_six_points(d):
    """B 买点三个 / 卖点三个"""
    section(d, 560, 1230, "六个点，一次看全", CY, chip_dy=16)
    d.text((400, 586), "左：三个买点　｜　右：三个卖点（方向相反，规则一样）", font=f_n, fill=MU)

    # 下跌趋势：中枢① [138,145] → 中枢② [124,129]（GG② 130 < DD① 137，依次向下；引擎 find_centers 复算一致）
    # 一买在最后中枢②下方；二买这里画的是不破一买低点的常见情形（跌破也算，最弱，第 54 / 101 课）；三买向上离开中枢②后回试不破 ZG 129
    BUY = [152, 138, 145, 137, 144, 124, 130, 121, 129, 108, 120, 114, 134, 131, 140]
    SELL = [256 - p for p in BUY]

    # 左：买点
    d.rounded_rectangle([76, 630, 690, 1200], 16, fill=CARD, outline=LINE, width=2)
    d.text((94, 642), "买点", font=f_p, fill=GR)
    mb, Xb = mkchart(d, 106, 660, 700, 1050, 100, 156, BUY,
                     boxes=[(1, 4, 145, 138), (5, 8, 129, 124)],
                     marks=[(9, "一买", GR, 16), (11, "二买", GR, 16), (13, "三买", GR, 16)])
    d.text((Xb(1) + 8, mb.Y(145) - 32), "中枢①", font=f_t, fill=(190, 210, 255))
    d.text((Xb(5) + 8, mb.Y(129) - 32), "中枢② ZG 129 / ZD 124", font=f_t, fill=(190, 210, 255))
    d.text((94, 1074), "一买：下跌趋势最后一个中枢下方的背驰点", font=f_t, fill=TX)
    d.text((94, 1100), "二买：一买后次级别回调；一般不破一买低点，跌破也算（最弱）", font=f_t, fill=TX)
    d.text((94, 1126), "三买：离开中枢后回试，低点不跌破 ZG", font=f_t, fill=TX)
    d.text((94, 1156), "一买在中枢下、三买在中枢上；二买可在任何位置（第 21 课）。", font=f_t, fill=MU)

    # 右：卖点
    d.rounded_rectangle([710, 630, 1324, 1200], 16, fill=CARD, outline=LINE, width=2)
    d.text((728, 642), "卖点（镜像）", font=f_p, fill=RD)
    ms, Xs = mkchart(d, 740, 1294, 700, 1050, 100, 156, SELL,
                     boxes=[(1, 4, 118, 111), (5, 8, 132, 127)], col=RD,
                     marks=[(9, "一卖", RD, -46), (11, "二卖", RD, -46), (13, "三卖", RD, -46)])
    d.text((Xs(1) + 8, ms.Y(111) + 8), "中枢①", font=f_t, fill=(255, 190, 190))
    d.text((Xs(5) + 8, ms.Y(127) + 8), "中枢② ZG 132 / ZD 127", font=f_t, fill=(255, 190, 190))
    d.text((728, 1074), "一卖：上涨趋势最后一个中枢上方的背驰点", font=f_t, fill=TX)
    d.text((728, 1100), "二卖：一卖后次级别反弹；一般不破一卖高点，升破也算（最弱）", font=f_t, fill=TX)
    d.text((728, 1126), "三卖：离开中枢后回抽，高点不升破 ZD", font=f_t, fill=TX)
    d.text((728, 1156), "第 15 课：「卖点的情况就反过来」，不需要另记一套。", font=f_t, fill=MU)


def draw_sources(d):
    """C 三个买点各自的判据"""
    section(d, 1250, 1710, "三个买点，各自的出处", AM, chip_dy=16)
    d.text((520, 1276), "定理只管第三类；一买二买的定义见第 17 / 21 课", font=f_n, fill=MU)

    rows = [
        ("一买", GR, "下跌确立后，最后一个中枢下方的背驰点。",
         "第 21 课：「只有在下跌确立后的中枢下方才可能出现买点。这就是第一类买点。」"
         "MACD 辅助（第 15 课）：「第一类买点都是在 0 轴之下背驰形成的」—— 没有趋势，没有背驰。"),
        ("二买", GR, "一买后第一次次级别回调的低点；一般不破一买低点，跌破也算，属最弱的一种。",
         "第 17 / 21 课定义；第 52 课：「一个 5 分钟回试不破低点，那就是第二类买点」。"
         "MACD 辅助（第 15 课）：「第二类买点都是第一次上 0 轴后回抽确认形成的」。"
         "第 14 课：「大级别的第二类买点，由次一级别相应走势的第一类买点构成」。"
         "跌破一买：第 54 课答疑「当然有可能，虽然很少见」；第 101 课「是完全可以的」，属最弱"),
        ("三买", GR, "向上离开中枢后回试，低点不跌破 ZG，且必须是第一次。",
         "第 20 课原文（见 A 面板）。三类里它最不用猜底 —— 但要等它先证明自己不回来。"),
    ]
    yy = 1320
    for k, c, v, src in rows:
        d.rounded_rectangle([86, yy, 196, yy + 48], 10, fill=c + (46,), outline=c, width=2)
        tw = d.textlength(k, font=f_n)
        d.text((86 + (110 - tw) / 2, yy + 10), k, font=f_n, fill=c)
        d.text((216, yy + 2), v, font=f_n, fill=TX)
        # 原文出处按宽度折行
        x, maxw = 216, 1100
        line = ""
        for ch in src:
            if d.textlength(line + ch, font=f_t) > maxw:
                d.text((x, yy + 38), line, font=f_t, fill=MU)
                yy += 30
                line = ""
            line += ch
        d.text((x, yy + 38), line, font=f_t, fill=MU)
        yy += 96


def draw_completeness(d):
    """D 为什么只有这三类"""
    section(d, 1730, 2170, "为什么只有这三类？（第 21 课：完备性）", RD, chip_dy=16)
    d.text((760, 1756), "答案是否定的 —— 除了这三类，没有其他买卖点", font=f_n, fill=MU)

    Q_BUY133 = "第 21 课原话：「这三类买卖点，都是被理论所保证的 100%安全的买卖点」；「所谓 100%安全的买卖点，就是这点之后，市场必然发生转折，没有任何模糊或需要分辨的情况需要选择。」"
    d.text((86, 1808), Q_BUY133[:54],
           font=f_t, fill=TX)
    d.text((86, 1838), Q_BUY133[54:], font=f_t, fill=TX)

    d.text((86, 1886), "推演：所有买卖点都必然对应着与该级别最靠近的一个中枢的关系 ——", font=f_n, fill=AM)
    d.text((106, 1920), "· 买点：中枢下产生的必然对应转折，中枢上产生的必然对应延续。", font=f_t, fill=TX)
    d.text((106, 1950), "· 中枢只有三种情况：延续、扩张、新生。中枢延续时，中枢之上不可能有买点（那时只可能有卖点）。", font=f_t, fill=TX)
    d.text((106, 1980), "· 中枢扩张或新生，中枢之上才会存在买点 —— 这就是第三类买点。三买后必然出现两种情况：", font=f_t, fill=GR)
    d.text((126, 2010), "A 中枢扩张，导致一个更大级别的中枢（第 21 课：「尽量避免任何第一种情况就是一个最大的问题」，"
                        "但两种情况都必然赢利）；", font=f_t, fill=MU)
    d.text((126, 2040), "B 中枢新生，就会形成一个上涨的趋势。", font=f_t, fill=MU)
    d.text((106, 2076), "· 只有二买与三买可能重合：一买后次级别走势凌厉地直接上破前面下跌的最后一个中枢，回抽不触及该中枢（第 21 课）。",
           font=f_t, fill=TX)

    d.rounded_rectangle([86, 2112, W - 86, 2158], 12, fill=(CY[0], CY[1], CY[2], 26), outline=CY, width=2)
    d.text((110, 2120), "第 28 课一句话串起来：「背驰是制造底部，制造第一类买点的，而中枢扩展、延伸是制造第二、三类买点的。」",
           font=f_t, fill=TX)


def draw_operations(d):
    """E 操作"""
    section(d, 2190, 2586, "操作上要紧的三句", AM, chip_dy=16)
    d.text((440, 2216), "都是原文，不是我加的", font=f_n, fill=MU)

    Q_BUY159 = "「第三类买卖点后，并不必然是趋势，也有进入更大级别盘整的可能，但这种买卖之所以必然赢利，就是因为即使是盘整，也会有高点出现。」"
    Q_BUY162 = "「操作策略很简单，一旦不能出现趋势，一定要在盘整的高点出掉，这和第一、二类买点的策略是一样的。」"
    ops = [
        ("三买后不必然趋势",
         [Q_BUY159[:31],
          Q_BUY159[31:]]),
        ("所以怎么操作",
         [Q_BUY162[:30],
          Q_BUY162[30:]]),
        ("一买后最弱的反弹",
         ["「这种只触及最后一个中枢的 DD=min(dn) 的反弹，就是背驰后最弱的反弹」",
          "（第 29 课）—— DD 就是围绕该中枢震荡的最低点。"]),
    ]
    yy = 2260
    for k, vs in ops:
        d.text((86, yy), k, font=f_n, fill=AM)
        for i, v in enumerate(vs):
            d.text((86, yy + 32 + i * 28), v, font=f_t, fill=TX)
        yy += 32 + len(vs) * 28 + 26


def build():
    """画整张卡，返回 PIL Image。"""
    set_size(W, H)
    im, d = newcard("09", "三类买卖点", "买点三种、卖点三种，说的都是价格和同一个中枢的关系", panel=False)
    draw_theorem(d)
    draw_six_points(d)
    draw_sources(d)
    draw_completeness(d)
    draw_operations(d)
    foot(d, "第 17 / 21 课（定义与完备性）；第 20 课（三买定理）；第 14 / 15 课（一、二买）；第 28 课",
         "把三买当必涨信号 —— 它是入场理由，不是持有理由；三买后仍可能只是进入更大级别的盘整")
    return im


def main():
    build().save(OUT + OUTNAME)
    print("09")




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
