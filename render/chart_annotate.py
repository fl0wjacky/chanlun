#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在用户 TradingView 截图上标注：笔编号、中枢 ZG/ZD。

笔的顶点不在这里算 —— 先跑 tools/extract_chart_pens.py 生成
data/annot_pens.json，本脚本只负责画。价格 / 日期由 render/shot_calib.py 从像素现算。
约定：仍在延续、未终结的中枢整框虚线（不再用虚线表示「延伸段」）。
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import data, out, SCREENSHOT
from render.style import *            # noqa: F401,F403
from render.shot_calib import P, datestr, CENTERS

SRC = SCREENSHOT
OUT = out("aapl_chanlun_annotated.png")

im = Image.open(SRC).convert("RGB")
W, H = im.size
PAD_TOP = 46
PAD_BOT = 300
canvas = Image.new("RGB", (W, H + PAD_TOP + PAD_BOT), BG)
canvas.paste(im, (0, PAD_TOP))
d = ImageDraw.Draw(canvas, "RGBA")

f_title = F(34); f_h = F(24); f_n = F(22); f_s = F(20); f_xs = F(18)

def Y(y):  # 原图 y -> 画布 y
    return y + PAD_TOP

# ---------- 笔顶点 ----------
V = json.load(open(data("annot_pens.json")))

# ---------- 中枢框（像素实测见 shot_calib.CENTERS）----------
STYLE = {"blue": (SH_BLUE, SH_BLUE_FILL), "orange": (SH_ORANGE, SH_ORANGE_FILL), "red": (SH_RED, SH_RED_FILL)}
BOX = [dict(CENTERS[n], n=n, col=STYLE[CENTERS[n]["kind"]][0], fill=STYLE[CENTERS[n]["kind"]][1])
       for n in ("③", "④", "⑤", "②", "①")]

# ---------- 1) 中枢框：已终结实线，仍在延续整框虚线 ----------
for b in BOX:
    box = [b["x0"], Y(b["yt"]), b["x1"], Y(b["yb"])]
    if b["live"]:
        dashed_rect(d, box, b["col"], width=4, fill=b["fill"])
    else:
        d.rectangle(box, fill=b["fill"], outline=b["col"], width=4)

# ---------- 2) ZG / ZD 引导线与价位标签 ----------
def zl(x0, x1, y, txt, col, right=True):
    d.line([x0, Y(y), x1, Y(y)], fill=col + (150,), width=2)
    tw = d.textlength(txt, font=f_s)
    bx = (x1 - tw - 26) if right else (x0 + 12)
    d.rectangle([bx, Y(y) - 16, bx + tw + 16, Y(y) + 16], fill=SH_PAPER + (240,), outline=col, width=2)
    d.text((bx + 8, Y(y) - 13), txt, font=f_s, fill=SH_INK)

for b in BOX:
    zl(b["x0"] - 50, b["x1"], b["yt"], "ZG %.1f" % P(b["yt"]), b["col"])
    zl(b["x0"] - 50, b["x1"], b["yb"], "ZD %.1f" % P(b["yb"]), b["col"])

# ---------- 3) 中枢名 label ----------
for b in BOX:
    lab = "中枢%s" % b["n"]
    tw = d.textlength(lab, font=f_h)
    ly = Y(b["yt"]) + 6
    d.rectangle([b["x0"] + 8, ly, b["x0"] + 8 + tw + 18, ly + 34], fill=b["col"] + (235,))
    d.text((b["x0"] + 17, ly + 5), lab, font=f_h, fill=SH_PAPER)

# ---------- 4) 笔编号 ----------
for i, (x, y) in enumerate(V):
    r = 13
    d.ellipse([x - r, Y(y) - r, x + r, Y(y) + r], fill=SH_PAPER + (240,), outline=SH_INK, width=3)
    t = str(i + 1)
    tw = d.textlength(t, font=f_n)
    d.text((x - tw / 2, Y(y) - 14), t, font=f_n, fill=SH_INK)

# ---------- 5) 仍在延续的中枢：括注 ----------
for b in BOX:
    if not b["live"]:
        continue
    bx0, bx1 = b["x0"], b["x1"]
    by = Y(b["yt"]) - 52
    d.line([bx0, by + 14, bx0, by + 26], fill=SH_DEEP, width=3)
    d.line([bx1, by + 14, bx1, by + 26], fill=SH_DEEP, width=3)
    d.line([bx0, by + 20, bx1, by + 20], fill=SH_DEEP, width=3)
    txt = "中枢%s 仍在延续 %s → %s（未终结，所以整框虚线）" % (b["n"], datestr(bx0), datestr(bx1))
    tw = d.textlength(txt, font=f_s)
    d.rectangle([bx0 - 6, by - 26, bx0 + tw + 20, by + 4], fill=SH_DEEP + (240,))
    d.text((bx0 + 4, by - 22), txt, font=f_s, fill=SH_PAPER)

# ---------- 6) 标题条 ----------
d.rectangle([0, 0, W, PAD_TOP], fill=BG)
d.text((24, 6), "AAPL/USDT 永续 · 4小时 · 缠论结构标注（CHANLUN 3.0）", font=f_title, fill=TX)
r = "冲浪者 · 2026-09-26"
tw = d.textlength(r, font=f_h)
d.text((W - tw - 26, 10), r, font=f_h, fill=MU)

# ---------- 7) 底部图例 ----------
bx = 0; by0 = H + PAD_TOP
d.rectangle([0, by0, W, H + PAD_TOP + PAD_BOT], fill=CARD)
d.line([0, by0, W, by0], fill=LINE, width=2)
y = by0 + 16
d.text((24, y), "图例", font=f_title, fill=AM); y += 46

rows = [
    ("蓝色折线", IND_PEN, "笔：连接一个顶分型与一个底分型，每笔至少跨 5 根 K 线（白圈数字=笔的转折点序号）"),
    ("红色/绿色小三角", IND_TOP, "顶分型 / 底分型（分型成立 ≠ 成笔，所以三角数量多于转折点）"),
    ("蓝色矩形", SH_BLUE, "中枢：区间由 ZG / ZD 标出；实线框 = 已终结，虚线框 = 仍在延续、未终结"),
    ("橙色 / 红色矩形", SH_ORANGE, "级别未定：用本级别笔回算对不上"),
    ("绿色点线", IND_NOW, "当前价格线"),
]
for name, col, desc in rows:
    d.rectangle([24, y + 4, 60, y + 26], fill=col)
    d.text((74, y), name, font=f_h, fill=TX)
    d.text((74 + 300, y + 2), desc, font=f_s, fill=MU)
    y += 40

canvas.save(OUT)
print("saved", OUT, canvas.size)
