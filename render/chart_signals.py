#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AAPL 4H 截图上的三买判定（对每个中枢的回试点做 ZG 核对）＋ 一买 / 二买 疑点。

价格 / 日期 / ZG / ZD 全部由 render/shot_calib.py 从像素现算，与 chart_annotate 同一套标定。
判据：第 20 课三买定理 —— 向上离开后的回试，低点不跌破 ZG 才构成第三类买点。
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import out, SCREENSHOT
from render.style import *            # noqa: F401,F403
from render.shot_calib import P, Ypx, datestr, CENTERS, ZG, ZD

SRC = SCREENSHOT
OUT = out("aapl_chanlun_buysell.png")

im = Image.open(SRC).convert("RGB")
W, H = im.size
TOP, BOT = 48, 340
cv = Image.new("RGB", (W, H + TOP + BOT), BG)
cv.paste(im, (0, TOP))
d = ImageDraw.Draw(cv, "RGBA")
f_t, f_h, f_n, f_s = F(34), F(25), F(23), F(20)
Y = lambda y: y + TOP

# ---- ZG 参考线（三个可用本级别笔复算的蓝框中枢）----
for nm in ("⑤", "②", "①"):
    c = CENTERS[nm]
    y, txt = c["yt"], "ZG %.1f" % ZG(nm)
    d.line([c["x0"], Y(y), c["x1"], Y(y)], fill=SH_BLUE + (200,), width=3)
    tw = d.textlength(txt, font=f_s)
    d.rectangle([c["x0"] - tw - 26, Y(y) - 16, c["x0"] - 12, Y(y) + 16], fill=SH_PAPER + (235,), outline=SH_BLUE, width=2)
    d.text((c["x0"] - tw - 19, Y(y) - 13), txt, font=f_s, fill=SH_INK)

# ---- 回试点：编号, 回试低点像素 (x, y), 对应中枢, 类别 ----
ITEMS = [
    (1, 1179, 620, "⑤", "buy"),
    (2,  998, 684, "⑤", "no"),
    (3, 1621, 615, "②", "no"),
    (4, 2110, 268, "①", "no"),
    (5, 2150, 168, "①", "wait"),
    (6,  264, 741, None, "unk"),
    (7,  488, 593, None, "unk"),
]
LAB = {1: "三买成立", 2: "回试跌破 ZG", 3: "回试跌破 ZG", 4: "回试跌破 ZG", 5: "待确认", 6: "疑一买", 7: "疑二买"}
COL = {"buy": SH_OK, "no": SH_BAD, "wait": SH_WAIT, "unk": SH_UNK}

for n, x, y, zc, kind in ITEMS:
    c = COL[kind]
    lab = LAB[n]
    # 垂直线 + 水平小刻度（体现"低点 vs ZG"的落差）
    if zc is not None:
        yz = Ypx(ZG(zc))
        d.line([x, Y(yz), x, Y(y)], fill=c + (190,), width=3)
        d.line([x - 14, Y(yz), x + 14, Y(yz)], fill=c + (220,), width=3)
    r = 21
    d.ellipse([x - r, Y(y) - r, x + r, Y(y) + r], fill=SH_PAPER + (245,), outline=c, width=5)
    t = str(n); tw = d.textlength(t, font=f_n)
    d.text((x - tw / 2, Y(y) - 15), t, font=f_n, fill=c)
    tw2 = d.textlength(lab, font=f_n)
    if x > 1850:
        d.text((x - 26 - tw2, Y(y) - 14), lab, font=f_n, fill=c)
    else:
        d.text((x + 26, Y(y) - 14), lab, font=f_n, fill=c)
    mark = {"buy": "✓", "no": "×", "wait": "?", "unk": "?"}[kind]
    d.text((x - 8, Y(y) + 24), mark, font=f_h, fill=c)

# ---- 标题 / 图例 ----
d.rectangle([0, 0, W, TOP], fill=BG)
d.text((24, 7), "AAPL 4H · 三买判定（ZG 核对）＋ 一买 / 二买 疑点", font=f_t, fill=TX)
r = "冲浪者 · 2026-09-26"
d.text((W - d.textlength(r, font=f_h) - 26, 12), r, font=f_h, fill=MU)

it = {n: (x, y) for n, x, y, _, _ in ITEMS}
low = lambda n: P(it[n][1])
day = lambda n: datestr(it[n][0])
y0 = H + TOP
d.rectangle([0, y0, W, H + TOP + BOT], fill=CARD)
d.line([0, y0, W, y0], fill=LINE, width=2)
rows = [
    ("①", SH_OK, "✓ 三买成立", "%s · 约 %.1f" % (day(1), low(1)),
     "中枢⑤（ZG %.1f）向上离开后回试，低点 %.1f 未跌破 ZG → 成立（待对照截图核实：该点落在中枢② 的时间范围内）"
     % (ZG("⑤"), low(1))),
    ("②", SH_BAD, "× 不成立", "%s · 约 %.1f" % (day(2), low(2)),
     "中枢⑤ 第一次向上离开的回试，低点 %.1f 跌回中枢内（ZG %.1f / ZD %.1f）→ 不算三买，中枢延续"
     % (low(2), ZG("⑤"), ZD("⑤"))),
    ("③", SH_BAD, "× 不成立", "%s · 约 %.1f" % (day(3), low(3)),
     "中枢② 的回试低点 %.1f 跌破 ZG %.1f 与 ZD %.1f → 不构成三买；回试已跌破 ZD，是否构成三卖、中枢是否被破坏仍待确认"
     % (low(3), ZG("②"), ZD("②"))),
    ("④", SH_BAD, "× 不成立", "%s · 约 %.1f" % (day(4), low(4)),
     "中枢① 的第一次回试，低点 %.1f 跌回中枢内 → 中枢延续（仍在延续，所以整框画虚线）" % low(4)),
    ("⑤", SH_WAIT, "? 待确认", "现在 · 关键价 %.1f" % ZG("①"),
     "中枢① 第二次向上离开后，若回踩不跌破 %.1f，将成为图中第二个三买" % ZG("①")),
    ("⑥⑦", SH_UNK, "? 存疑", "%s / %s" % (day(6), day(7)),
     "疑似一买 %.1f、疑似二买 %.1f —— 图左端数据被截断且无背驰副图，无法验证，仅作标记" % (low(6), low(7))),
]
yy = y0 + 14
d.text((24, yy), "判定明细", font=f_t, fill=AM); yy += 44
for n, c, verdict, when, why in rows:
    d.rectangle([24, yy + 3, 24 + 56, yy + 31], fill=c)
    d.text((30, yy + 5), n, font=f_s, fill=SH_PAPER)
    d.text((92, yy), verdict, font=f_h, fill=c)
    d.text((300, yy + 2), when, font=f_s, fill=TX)
    d.text((560, yy + 2), why, font=f_s, fill=MU)
    yy += 45

cv.save(OUT)
print("saved", OUT, cv.size)
