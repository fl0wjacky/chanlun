#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""概念卡 07 级别"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cards.base import *
from cards import zec_data as zec

W, H = 1400, 2150                    # 卡片尺寸；模块常量，各段函数直接用
OUTNAME = "c07_级别.png"


def flow(d, x0, y0, items, bw=None, gap=34, rowh=56):
    """画一串流程方块，自动换行"""
    x, y = x0, y0
    for k, (t, c) in enumerate(items):
        w = d.textlength(t, font=f_n) + 32
        if x + w > W - 80:
            x = x0; y += rowh + 26
        d.rounded_rectangle([x, y, x + w, y + rowh], 10, fill=c + (46,), outline=c, width=2)
        d.text((x + 16, y + 13), t, font=f_n, fill=TX)
        if k < len(items) - 1 and x + w + gap + 20 < W - 80:     # 最后一项后面不画箭头
            d.text((x + w + 9, y + 11), "→", font=f_n, fill=MU)
        x += w + gap
    return y + rowh


def draw_recursion(d):
    """A 递归链"""
    section(d, 200, 640, "级别是递归出来的（第 17 + 63 课）")
    d.text((640, 226), "选定一张基础图，从最小的零件开始往上长", font=f_n, fill=MU)
    flow(d, 86, 292, [("K线", BL), ("分型", BL), ("笔", BL), ("线段", BL), ("① 1分中枢", GR),
                      ("1分走势", GR), ("② 5分中枢", GR), ("5分走势", GR), ("③ 30分中枢", AM),
                      ("…", MU), ("日 / 周 / 月中枢", AM)])
    d.rounded_rectangle([76, 470, W - 76, 620], 14, fill=(BL[0], BL[1], BL[2], 26), outline=BL, width=2)
    d.text((100, 482), "一条规则定级别", font=f_n, fill=LB)
    d.text((100, 518), "三个「次级别走势类型」重叠  =  本级别中枢。", font=f_p, fill=TX)
    d.text((100, 558), "递归不能无限下去 —— 最后不可分解的级别，", font=f_t, fill=MU)
    d.text((100, 586), "中枢定义为「至少三个该级别单位 K 线重叠部分」。实操取 1 分或 5 分钟。", font=f_t, fill=MU)


def draw_microscope(d):
    """B 显微镜"""
    section(d, 666, 1040, "级别 = 被观察的物体；K 线周期 = 显微镜倍数")
    d.text((760, 692), "这一条最容易搞错，缠师反复强调", font=f_n, fill=MU)
    d.text((86, 744), "第 63 课：", font=f_n, fill=MU)
    d.text((86, 778), "「再次强调！什么级别的图和什么级别的中枢没有任何必然关系，走势类型以及中枢就如同显微镜下的观察物，",
           font=f_t, fill=AM)
    d.text((86, 806), "　是客观存在的……而级别的图，就如同显微镜，不同倍数的看这客观的图就看到不同的精细程度，如此而已。」",
           font=f_t, fill=TX)
    d.text((86, 850), "第 77 课：", font=f_n, fill=MU)
    d.text((86, 884), "「这里的级别和缺口所在的 K 线图无关，只和本 ID 理论中的走势类型级别有关。", font=f_t, fill=TX)
    d.text((86, 912), "　不同周期 K 线图(不同倍度数显微镜)和走势的级别(显微镜所观察的物体)……这个比喻反复说了，不能再混淆了。」",
           font=f_t, fill=TX)
    d.text((86, 960), "→ 换周期只是换镜片。级别是结构长出来的，不是你把图切到哪一档决定的。", font=f_t, fill=CY)


def draw_evidence(d):
    """C 实证：同一段行情，15 分钟的线段层 vs 更高周期的笔层（ZEC；出图时现算）"""
    rows = [(tf, zec.cross(tf)) for tf in ("1h", "2h", "4h")]
    best_tf, best = min(rows, key=lambda t: abs(t[1]["A"] - t[1]["B"]))
    name = {"1h": "1 小时", "2h": "2 小时", "4h": "4 小时"}
    section(d, 1066, 1600, "★ 实证：换一档周期看同一段行情", GR)
    d.text((560, 1092), "15 分钟的线段层，大致对应 %s的笔层 —— 但只是大致" % name[best_tf], font=f_n, fill=MU)
    d.text((86, 1148), "路径 A：在 15 分钟图上画线段中枢（第 83 课的正规最小中枢）", font=f_n, fill=BL)
    d.text((86, 1184), "路径 B：直接在更高周期的图上画类中枢", font=f_n, fill=GR)
    cols = [(86, "路径 B 的周期"), (330, "A · 15 分钟线段中枢"), (620, "B · 该周期类中枢"),
            (880, "A 能对上"), (1100, "B 能对上")]
    for x, t in cols:
        d.text((x, 1236), t, font=f_t, fill=MU)
    yy = 1276
    for tf, c in rows:
        hot = tf == best_tf
        vals = [name[tf], str(c["A"]), str(c["B"]), "%d / %d" % (c["A_hit"], c["A"]), "%d / %d" % (c["B_hit"], c["B"])]
        for (x, _), v, col in zip(cols, vals, (TX if hot else MU, BL, GR, AM, AM)):
            d.text((x, yy), v, font=f_n, fill=col if hot else MU)
        yy += 40
    d.text((86, yy + 2), "「对得上」= 起止时间与中枢区间都有交叠（宽松匹配）；ZECUSDT 永续 %s（UTC），出图时由本引擎现算"
           % zec.date_range("15m"), font=f_t, fill=MU)
    d.line([86, yy + 36, W - 86, yy + 36], fill=LINE, width=2)
    d.text((86, yy + 50), "★ 个数最接近的是 %s（%d vs %d），两边约 %d%% / %d%% 能互相对上 —— 结构层级大致对应。"
           % (name[best_tf], best["A"], best["B"], round(100 * best["A_hit"] / best["A"]),
              round(100 * best["B_hit"] / best["B"])), font=f_n, fill=AM)
    d.text((86, yy + 86), "　 对不上的那部分正说明：级别是结构长出来的，不是换到哪一档周期就等于哪一级。", font=f_t, fill=TX)
    d.text((86, yy + 114), "　 个数相近也不能证明「15 分钟线段 = %s笔」，只说明两种看法看到的结构大体一致。" % name[best_tf],
           font=f_t, fill=TX)
    d.text((86, yy + 146), "　（路径 B 是类中枢，属下面第 83 课所说稳定性差的口径；路径 A 线段中枢只有 %d 个，样本偏薄）"
           % best["A"], font=f_t, fill=MU)


def draw_boundaries(d):
    """D 边界"""
    callout(d, 1626, 1950, RD, 22)
    chip(d, 80, 1644, "两个必须知道的边界", RD, f_p)
    d.text((86, 1704), "边界一：级别 ≠ 周期", font=f_n, fill=RD)
    d.text((86, 1736), "　换周期只是换放大倍数。同一段行情在 4 小时上可能只是「1 个中枢」，", font=f_t, fill=TX)
    d.text((86, 1762), "　在 30 分钟上可能是一连串中枢与连接段 —— 结构没变，只是看得更细。", font=f_t, fill=TX)
    d.text((86, 1800), "边界二：类中枢的稳定性天生就差（第 83 课）", font=f_n, fill=RD)
    d.text((86, 1832), "　「为什么不能由笔构成最小中枢？……用笔当成构成最小中枢的零件，"
                      "但这样构造出来的系统，其稳定性极差。」", font=f_t, fill=TX)
    d.text((86, 1870), "　「……一笔的基础是顶和底分型，而一些瞬间的交易，就足以影响其结构。」", font=f_t, fill=TX)
    d.text((86, 1900), "　→ CHANLUN 3.0 画的就是笔构成的中枢（第 64 课称「类中枢」），属「稳定性极差」那一档；正规最小中枢应由线段构成。", font=f_t, fill=AM)


def build():
    """画整张卡，返回 PIL Image。"""
    set_size(W, H)
    im, d = newcard("07", "级别", "级别不是 K 线周期 —— 它是结构自己长出来的层级",
                    panel=False)
    draw_recursion(d)
    draw_microscope(d)
    draw_evidence(d)
    draw_boundaries(d)
    foot(d, "第 17 课（递归定义 + 最低级别）；第 63 / 77 课（显微镜比喻、级别与图无关）；第 64 / 83 课（类中枢）",
         "把「级别」等同于「K线周期」—— 级别是结构层级，周期只是看它的镜片")
    return im


def main():
    build().save(OUT + OUTNAME)
    print("07")


if __name__ == "__main__":
    main()
