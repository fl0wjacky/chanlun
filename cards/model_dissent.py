#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""框架卡一：共识 → 分歧 → 证实 / 证伪（机会模型）"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json, datetime
from collections import Counter
from config import out, data
from core import analyze, analyze_file
from render.style import *

f_t, f_s, f_b, f_m, f_n = F(50), F(30), F(34), F(27), F(24)

W, H = 1400, 2200                    # 卡片尺寸；模块常量，各段函数直接用


def box(d, x0, x1, y0, y1, col):
    """中枢 / 共识区：同色半透明底 + 描边"""
    d.rounded_rectangle([x0, y0, x1, y1], 10, fill=col + (46,), outline=col, width=3)


def draw_title(d):
    """标题 + 署名"""
    d.text((60, 44), "缠论的机会模型", font=f_t, fill=TX)
    d.text((62, 112), "共识 → 分歧 → 证实 / 证伪（作者解读，非原文术语）", font=f_s, fill=MU)
    r = "冲浪者 · 2026-09-26"
    d.text((W - d.textlength(r, font=f_n) - 60, 60), r, font=f_n, fill=(110, 118, 136))


def draw_diagram(d):
    """示意图：共识区 → 分歧段 → 回试证实 / 证伪"""
    d.rounded_rectangle([50, 180, W - 50, 900], 22, fill=CARD, outline=LINE, width=2)
    ax0, ax1 = 120, W - 120
    # 中枢区间按第 20 课公式：ZG = 三段高点里最低的，ZD = 三段低点里最高的（屏幕上 y 越小价越高）
    ZG = 632                                   # 中枢① 的 ZG：高点 y=622/632/612 里最低的那个

    box(d, 140, 420, 632, 690, BL)                # 中枢① / 共识区① = [ZD, ZG]
    box(d, 770, 1170, 404, 452, BL)               # 中枢② / 共识区②
    d.text((150, 574), "共识区①  中枢", font=f_m, fill=(200, 215, 255))
    d.text((880, 340), "共识区②  中枢", font=f_m, fill=(200, 215, 255))

    # ZG 线
    x = ax0
    while x < ax1:
        d.line([x, ZG, min(x + 16, ax1), ZG], fill=BL + (230,), width=3); x += 26
    d.text((ax1 - 200, ZG - 38), "ZG（中枢上沿）", font=f_n, fill=BL)

    # 价格折线
    path = [(140,690),(188,622),(232,704),(282,632),(332,700),(396,612),
            (462,516),(520,668),                          # 回试① 跌破 ZG ✗
            (626,462),(680,556),                          # 回试② 站住 ✓
            (770,404),(818,452),(872,398),(930,462),(986,392),(1044,458),(1102,398),
            (1170,388)]
    for i in range(len(path) - 1):
        d.line([path[i], path[i+1]], fill=(255, 255, 255, 220), width=4)

    # 分歧段标注
    d.line([396, 760, 396, 786], fill=AM, width=3)
    d.line([770, 760, 770, 786], fill=AM, width=3)
    d.line([396, 786, 770, 786], fill=AM, width=3)
    d.text((452, 742), "分歧段（缝隙）", font=f_m, fill=AM)

    # 回试点标记
    d.ellipse([520-15, 668-15, 520+15, 668+15], fill=BG, outline=RD, width=5)
    d.text((520, 668), "✗", font=F(26), fill=RD, anchor="mm")
    d.text((540, 690), "① 回试跌回 ZG 以内 → 中枢延伸，不是机会", font=f_m, fill=RD)
    d.ellipse([680-15, 556-15, 680+15, 556+15], fill=BG, outline=GR, width=5)
    d.text((680, 556), "✓", font=F(26), fill=GR, anchor="mm")
    d.text((700, 516), "② 回试不破 ZG → 三买成立，缝隙才被追认", font=f_m, fill=GR)

    d.text((140, 826), "中枢 = 多空达成共识的区间　　分歧 = 有人不同意，把价格拉开　　机会 = 分歧被证实的那一刻",
           font=f_n, fill=MU)


def draw_rules(d):
    """口诀：四句话记住"""
    y = 930
    d.rounded_rectangle([50, y, W - 50, y + 454], 22, fill=CARD, outline=LINE, width=2)
    d.text((86, y + 26), "四句话记住", font=f_s, fill=AM)
    rules = [("中枢是共识", "多空都认的价位区间"),
             ("缝隙是分歧", "有人不同意，把价格拉出去"),
             ("机会在「回不去」被证实的那一下", "不在缝隙中段追，在回试不破 ZG 的那一下"),
             ("缝隙是结果，不是原因", "先有回试通过，才追认这是缝隙")]
    yy = y + 90
    for i, (a, b) in enumerate(rules):
        d.ellipse([86, yy + 6, 86 + 44, yy + 50], fill=(BL + (235,)))
        d.text((86 + 22, yy + 28), str(i + 1), font=f_b, fill=(255, 255, 255), anchor="mm")
        d.text((150, yy), a, font=f_b, fill=TX)
        d.text((150, yy + 46), b, font=f_n, fill=MU)
        yy += 88


def gap_rows_and_z():
    """引擎现算：4 小时类中枢里，每次「向上离开 ZG」之后的第一次回试。

    返回 (rows, Z)，其中 rows = [(日期, 中枢序号, 中枢, 离开冲高, 回试低点, 判定)]；
    判定 = 三买 / 贯穿（从区间另一侧整段穿过）/ 假缝隙 / ZD 下方。
    出图时现算 —— 换数据或改引擎，卡片自动跟着变，不会过期。

    一并返回 Z 是给 cross_check() 用的：那张表的期望值必须来自被测物之外，
    而 Z 里的 term 由 core/center.py 独立算出（见 cross_check 的说明）。
    """
    r = analyze_file("aaplusdt_4h.json")
    P, B, Z = r["pens"], r["bars"], r["centers"]
    rows = []
    for n, z in enumerate(Z):
        nxt = Z[n + 1]["PI0"] if n + 1 < len(Z) else len(P)
        for j in range(z["PI0"], min(nxt + 1, len(P) - 1)):
            up, dn = P[j], P[j + 1]
            if up["p1"] > up["p0"] and up["p1"] > z["ZG"] and dn["p1"] < dn["p0"]:
                if dn["p1"] > z["ZG"]:                # 回试整段在 ZG 之上：离开段须从区间里出发才算三买（第 20 / 38 课）
                    v = "三买" if z["ZD"] <= up["p0"] <= z["ZG"] else "贯穿"
                else:
                    v = "ZD 下方" if dn["p1"] < z["ZD"] else "假缝隙"
                t = datetime.datetime.utcfromtimestamp(B[dn["i1"]]["t"] / 1000)
                rows.append(("%d月%d日" % (t.month, t.day), n + 1, z, up["p1"], dn["p1"], v))
    return rows, Z


def gap_rows():
    """兼容旧调用（tools/verify_c06_c07.py:95 按 6 元组解包）：只要 rows。"""
    return gap_rows_and_z()[0]


def cross_check(rows, Z):
    """拿引擎自己的中枢终结原因跟卡片的判定对账——**这只查漂移，不构成对原文的验证。**

    先说清它查不了什么，免得又被读成「验证」：
      本卡 L106-108 的谓词  up.p1>up.p0 且 dn.p1>ZG 且 ZD<=up.p0<=ZG
      center.py L120-125 的  u.p1>u.p0 且 w.lo>ZG 且 ZD<=u.p0<=ZG
    而向下笔恒有 lo == p1（在本数据 10/10 实测），所以 dn.p1>ZG 与 w.lo>ZG
    是**同一个条件**。两边是同一份原文规则的两次转写——和 upgrades()/check_centers()
    那种「同一算法的两次转写」同形。**原文读错了，两边一起错，这里查不出来。**

    它真正能查的是**管道**：谁跟谁配成一笔、三买记在哪个中枢上、本卡的扫描范围
    有没有漏掉引擎已判为三买的那一段。所以它是一条**漂移报警**——两处实现一旦
    分家就红。这有价值（内部不一致必须吼），但别把它当独立来源。

    真正的独立来源在引擎之外：data/annot_pens.json 是人工从截图标的笔。要让这张卡
    能验原文，得拿它当外部期望值——那是另一个活，本函数不做。

    依据是第 38 课原文「第三类买卖点，和中枢延伸的结束是一回事情」：三买 ⟺
    中枢终结原因就是三买。双向对，免得漏掉「本卡漏判 / 引擎多判」。

    返回 (对上几个, 不一致的清单)。清单非空 = 两处实现已经分家。
    """
    bad, ok = [], 0
    for n, z in enumerate(Z, 1):
        mine = [r[5] for r in rows if r[1] == n]
        if not mine:
            continue
        card_buy, engine_buy = ("三买" in mine), (z["term"] == "三买")
        if card_buy == engine_buy:
            ok += 1
        else:
            bad.append((n, card_buy, z["term"], mine))
    return ok, bad


MISMATCH = []          # cross_check 的真失败清单；非空 → main() 以 1 退出（见文件末尾）


def draw_evidence(d):
    """实证：本引擎 4 小时类中枢，逐次核对「缝隙」"""
    rows, Z = gap_rows_and_z()
    y = 1414
    d.rounded_rectangle([50, y, W - 50, y + 730], 22, fill=CARD, outline=LINE, width=2)
    d.text((86, y + 24), "本引擎在这段真实数据上的判定明细（下附两处实现的对账，仅查漂移）", font=f_s, fill=AM)
    hd = ["日期（UTC）", "中枢", "离开冲高", "回试低点", "中枢区间 [ZD, ZG]", "判定"]
    xs = [86, 280, 400, 580, 760, 1080]
    yy = y + 96
    for i, h in enumerate(hd):
        d.text((xs[i], yy), h, font=f_n, fill=MU)
    d.line([86, yy + 38, W - 86, yy + 38], fill=LINE, width=2)
    yy += 56
    for t, n, z, hi, lo, v in rows:
        col = GR if v == "三买" else RD
        mark = {"三买": "✓ 三买", "假缝隙": "✗ 假缝隙", "ZD 下方": "✗ 跌到 ZD 下方", "贯穿": "✗ 贯穿，非三买"}[v]
        for x, txt in zip(xs[:5], [t, "中枢%d" % n, "%.2f" % hi, "%.2f" % lo, "[%.2f, %.2f]" % (z["ZD"], z["ZG"])]):
            d.text((x, yy), txt, font=f_n, fill=TX)
        d.text((xs[5], yy), mark, font=f_n, fill=col)
        yy += 40
    c = Counter(r[5] for r in rows)
    d.line([86, yy + 6, W - 86, yy + 6], fill=LINE, width=2)
    d.text((86, yy + 24), "%d 次向上离开后回试：成立 %d 次，跌回中枢 %d 次，跌到 ZD 下方 %d 次%s —— 不追缝隙中段。"
           % (len(rows), c["三买"], c["假缝隙"], c["ZD 下方"], "，贯穿 %d 次" % c["贯穿"] if c["贯穿"] else ""),
           font=f_m, fill=AM)
    d.text((86, yy + 72), "注：AAPLUSDT 永续 4 小时，07-26 – 09-27；类中枢（笔构成，第 83 课说稳定性差），出图时现算。",
           font=f_n, fill=MU)
    d.text((86, yy + 104), "　 三买按定义就是中枢终结（第 38 课「第三类买卖点，和中枢延伸的结束是一回事情」）：",
           font=f_n, fill=MU)
    d.text((86, yy + 136), "　 离开段从中枢里出发、回试整段不回到区间，当下就判中枢结束，离开段算连接段。", font=f_n, fill=MU)
    thru = [t for t, n, z, hi, lo, v in rows if v == "贯穿"]
    if thru:
        d.text((86, yy + 168), "　 「贯穿」：%s 那次离开段从 ZD 下方整段穿过区间，不是从中枢里出发，由中心定理一兜底判终结。"
               % "、".join(thru), font=f_n, fill=MU)
    yy0 = yy + 168 + 32 * bool(thru)
    d.text((86, yy0), "　 样本只有 %d 次，只作示意。" % len(rows), font=f_n, fill=MU)

    # 对账（本卡唯一会失败的地方）：期望值来自引擎自己的 term，而不是本文件把
    # 上面那个 v 再抄一遍 —— 那样两边同一个谓词，永远不会分歧。
    nok, MISMATCH[:] = cross_check(rows, Z)
    if MISMATCH:
        d.text((86, yy0 + 34),
               "　 ✗ 两处实现分家 %d 处：%s —— 本卡与 core/center.py 的判定已经不一致，先查哪个错。"
               % (len(MISMATCH),
                  "、".join("中枢%d(卡=%s/引擎=%s)" % (n, "三买" if cb else "非三买", t)
                            for n, cb, t, _ in MISMATCH)),
               font=f_n, fill=RD)
    else:
        d.text((86, yy0 + 34),
               "　 ✓ 对账：%d 个有回试的中枢，本卡与 core/center.py 两处实现未分家。"
               "（谓词同源，原文若读错会一起错——这条只报漂移，不当独立验证。）" % nok,
               font=f_n, fill=GR)


def build():
    """画整张卡，返回 PIL Image。"""
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im, "RGBA")
    draw_title(d)
    draw_diagram(d)
    draw_rules(d)
    draw_evidence(d)
    return im


def main():
    build().save(out("chanlun_model.png"))
    if MISMATCH:
        # 出图成功不等于卡是对的：判据和引擎的终结原因对不上时，这张卡不该被当成证据。
        print("model ok（图已出），但两处实现分家 %d 处：%s" % (len(MISMATCH), MISMATCH))
        return 1
    print("model ok，两处实现未分家")
    return 0


if __name__ == "__main__":
    sys.exit(main())
