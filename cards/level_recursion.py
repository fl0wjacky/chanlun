#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""框架卡二：级别与递归（一条规则定级别）"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
from config import out, data
from core import analyze, analyze_file
from render.style import *

f_t, f_s, f_b, f_m, f_n = F(50), F(30), F(34), F(27), F(24)

W, H = 1400, 1760                    # 卡片尺寸；模块常量，各段函数直接用


def draw_title(d):
    """标题 + 署名"""
    r = "冲浪者 · 2026-09-26"
    d.text((60, 44), "缠论的「级别」怎么分辨", font=F(50), fill=TX)
    d.text((62, 112), "级别不是 K 线周期，是结构层级", font=f_s, fill=MU)
    d.text((W - d.textlength(r, font=f_n) - 60, 60), r, font=f_n, fill=(110, 118, 136))


def draw_formula(d):
    """核心公式：一条规则定级别"""
    d.rounded_rectangle([50, 180, W - 50, 320], 22, fill=(BL[0], BL[1], BL[2], 38), outline=BL, width=3)
    d.text((86, 206), "一条规则定级别", font=f_m, fill=BL)
    d.text((86, 250), "三个「次级别走势类型」重叠  =  本级别中枢", font=f_b, fill=TX)


def draw_chain(d):
    """递归链（第 63 课原文顺序）"""
    y = 370
    d.rounded_rectangle([50, y, W - 50, y + 340], 22, fill=CARD, outline=LINE, width=2)
    d.text((86, y + 22), "递归链（第 63 课原文顺序）", font=f_s, fill=AM)
    chain = [("K线", BL), ("分型", BL), ("笔", BL), ("线段", BL), ("①1分中枢", GR),
             ("1分走势", GR), ("②5分中枢", GR), ("5分走势", GR), ("③30分中枢", AM),
             ("④日/周/月中枢", AM)]
    bx, by = 86, y + 100
    for i, (t, c) in enumerate(chain):
        w = d.textlength(t, font=f_n) + 34
        if bx + w > W - 86:
            bx = 86; by += 78
        d.rounded_rectangle([bx, by, bx + w, by + 54], 12, fill=c + (46,), outline=c, width=2)
        d.text((bx + 17, by + 11), t, font=f_n, fill=TX)
        if i < len(chain) - 1 and bx + w + 46 < W - 86:     # 最后一项后面不画箭头
            d.text((bx + w + 10, by + 9), "→", font=f_n, fill=MU)
        bx += w + 46
    d.text((86, y + 250), "选定一张基础图（如 1 分钟）→ 画出分型、笔、线段 → 有三个线段重叠，就有了 1 分钟中枢",
           font=f_n, fill=MU)
    d.text((86, y + 284), "→ 1 分钟走势类型再重叠，就是 5 分钟中枢 …… 一路递归到日、周、月。", font=f_n, fill=MU)


def draw_howto(d):
    """实操上怎么分辨"""
    y = 740
    d.rounded_rectangle([50, y, W - 50, y + 590], 22, fill=CARD, outline=LINE, width=2)
    d.text((86, y + 22), "实操上怎么分辨", font=f_s, fill=AM)
    items = [("看构成零件", ["三个连续的「笔」重叠 = 类中枢（第 64 课）；三个连续的「线段」重叠 = 最小的正规中枢"]),
             ("看重叠升级", ["第 20 课中心定理二：前后两个同级别中枢，区间 [ZD,ZG] 不重叠、波动区间 [DD,GG] 重叠",
                           "→ 形成高级别中枢。第 52 课：「中枢扩展不能预先说是某级别的，因为扩展可以不断延续下去。」"]),
             ("看图周期", ["换小一级的图看，原来的「一笔」会展开成一段完整走势类型（趋势或盘整）—— 只是换镜片，不是换级别"]),
             ("看延伸段数", ["延伸不能超过 9 个次级别，「否则就变成更大级别的」（第 32 课答疑；第 33 课：6 段延伸",
                           "加形成中枢那 3 段「就构成更大级别的中枢了」）。引擎：满 9 段同时记高一级，区间按 3+3+3 取重叠（第 64 课）。",
                           "看段数，不看时间 —— 第 44 课：「中枢级别和幅度没有必然的关系。」"])]
    yy = y + 88
    for i, (a, lines) in enumerate(items):
        d.ellipse([86, yy + 4, 86 + 40, yy + 44], fill=(AM[0], AM[1], AM[2], 235))
        d.text((86 + 20, yy + 24), str(i + 1), font=f_b, fill=(30, 25, 10), anchor="mm")
        d.text((146, yy), a, font=f_b, fill=TX)
        for k, b in enumerate(lines):
            d.text((146, yy + 46 + k * 32), b, font=f_n, fill=MU)
        yy += 74 + 32 * len(lines)


def draw_warning(d):
    """警告：类中枢（笔构成的中枢）稳定性极差（第 83 课）"""
    y = 1356
    d.rounded_rectangle([50, y, W - 50, y + 360], 22, fill=(RD[0], RD[1], RD[2], 30), outline=RD, width=3)
    d.text((86, y + 22), "▲  关于「类中枢」（笔构成的中枢）的一个硬伤", font=f_s, fill=RD)
    d.text((86, y + 82), "第 83 课原话：", font=f_n, fill=MU)
    d.text((86, y + 118), "「……用笔当成构成最小中枢的零件，但这样构造出来的系统，其稳定性极差。」",
           font=f_m, fill=TX)
    d.text((86, y + 162), "「……一笔的基础是顶和底分型，而一些瞬间的交易，就足以影响其结构。」", font=f_m, fill=TX)
    Z = analyze_file("aaplusdt_4h.json")["centers"]
    z = min(Z, key=lambda c: c["ZG"] - c["ZD"])           # 出图时现算：最窄的那个类中枢
    d.text((86, y + 214), "本引擎 4 小时 %d 个类中枢，最窄的 [%.2f, %.2f] 只有 %.2f 宽（CHANLUN 3.0 画的也是这种）。"
           % (len(Z), z["ZD"], z["ZG"], z["ZG"] - z["ZD"]), font=f_n, fill=TX)
    d.text((86, y + 250), "所以你会看到：很窄的中枢、笔会重画（多是最后一笔，回头修正时偶尔连带前 1–3 笔）、偶尔算不平。", font=f_n, fill=MU)
    d.text((86, y + 292), "缠师本人的口径：正规的最小中枢由「线段」构成；第 91 课「笔是不能构成中枢的」。", font=f_m, fill=AM)


def build():
    """画整张卡，返回 PIL Image。"""
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im, "RGBA")
    draw_title(d)
    draw_formula(d)
    draw_chain(d)
    draw_howto(d)
    draw_warning(d)
    return im


def main():
    build().save(out("chanlun_level.png"))
    print("level ok")


if __name__ == "__main__":
    main()
