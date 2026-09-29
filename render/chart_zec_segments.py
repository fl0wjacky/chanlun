#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ZEC 15 分钟概览：最后 16 条线段里的「笔」「线段」「线段中枢」，看线段层实际长什么样。

画法与全量图共用（render/full_common.py）：未完成的笔 / 线段、仍在延续的中枢一律虚线；
线段端点顶红、底绿；标签最后画、带底色。
"""
import os, sys, json, math, datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import data, out, tick_of
from PIL import Image, ImageDraw
from render.style import *
from render.full_common import draw_layers, draw_labels, draw_signals, legend
from core import analyze

bars = json.load(open(data("zec15.json"), encoding="utf-8"))   # tools/fetch_klines.py ZECUSDT 15m 拉的最新数据
D = lambda ms: datetime.datetime.fromtimestamp(ms / 1000, datetime.timezone.utc).strftime("%m/%d")
r = analyze(bars, tick=tick_of("zec15.json"))
done = [s for s in r["segs"] if not s.get("live")]
segs = r["segs"][-16:]                              # 只画最后 16 条线段，避免太挤
a0 = segs[0]["i0"]                                  # 视窗：从这 16 条线段的起点到最后一根K线
view = bars[a0:]

W, H = 2900, 1560
im = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(im, "RGBA")
f_t, f_s, f_n = F(46), F(30), F(24)
d.text((60, 40), "ZEC/USDT 永续 · 15 分钟 · 笔 / 线段 / 线段中枢（最后 16 条线段）", font=f_t, fill=TX)
d.text((62, 104), "币安永续 ZECUSDT ｜ 全量 %s – %s 共 %d 根K线 ｜ 图中只画最后 16 条线段：%s – %s（UTC）"
       % (D(bars[0]["t"]), D(bars[-1]["t"]), len(bars), D(view[0]["t"]), D(view[-1]["t"])), font=f_s, fill=MU)
rr = "冲浪者 · %s" % datetime.date.today().isoformat()
d.text((W - d.textlength(rr, font=f_n) - 60, 60), rr, font=f_n, fill=(110, 118, 136))

# 绘图区先画在子图上：视窗外的笔 / 中枢自然被裁掉，不会伸进边距
X0, X1, Y0, Y1 = 120, W - 260, 200, 1160
PW, PHt = X1 - X0, Y1 - Y0
pmin = min(b["l"] for b in view); pmax = max(b["h"] for b in view)
pad = (pmax - pmin) * 0.04
pmin -= pad; pmax += pad
n = len(view)
X = lambda i: 12 + (i - a0) / (n - 1) * (PW - 24)   # i 为全量K线下标；左右各留 12 像素给端点圈
Y = lambda p: PHt - (p - pmin) / (pmax - pmin) * PHt

raw = (pmax - pmin) / 7                             # 价格刻度：步长取 1/2/5×10^n
e = 10 ** math.floor(math.log10(raw))
step = next(s * e for s in (1, 2, 5, 10) if s * e >= raw)
ticks = [k * step for k in range(math.ceil(pmin / step), math.floor(pmax / step) + 1)]

sub = Image.new("RGB", (PW, PHt), BG)
g = ImageDraw.Draw(sub, "RGBA")
for p in ticks:
    g.line([0, Y(p), PW, Y(p)], fill=(34, 38, 48), width=1)
labels = draw_layers(g, r, X, Y, keep=lambda a, b: b > a0)   # 恰好止于视窗起点的不画
labels += draw_signals(g, r, X, Y, keep=lambda a, b: b > a0)
draw_labels(g, labels, f_n, CY)
im.paste(sub, (X0, Y0))
d.rectangle([X0 - 1, Y0 - 1, X1, Y1], outline=LINE, width=1)
for p in ticks:                                     # 价格刻度在绘图区右侧
    d.text((X1 + 14, Y0 + Y(p) - 14), "%g" % p, font=f_n, fill=MU)

legend(d, 64, Y1 + 62, f_n)

# 统计
up = sum(1 for s in segs if s["dir"] == "up")
c1 = sum(1 for s in segs if s["case"] == 1)
c2 = sum(1 for s in segs if s["case"] == 2)
live = sum(1 for s in segs if s.get("live"))
d.text((60, Y1 + 130), "全量：笔 %d 条 ｜ 完成线段 %d 条 ｜ 线段中枢 %d 个（类中枢 %d 个）"
       % (len(r["pens"]), len(done), len(r["seg_centers"]), len(r["centers"])), font=f_s, fill=TX)
d.text((60, Y1 + 180), "图中 16 条：向上 %d ／ 向下 %d　｜　第一种情况 %d ／ 第二种情况 %d ／ 未完成 %d"
       % (up, len(segs) - up, c1, c2, live), font=f_n, fill=MU)
d.text((60, Y1 + 222), "平均每线段 %.1f 笔（全量）　｜　线段中枢只用已完成线段计算（项目口径）｜ 第 83 课：「由线段构成最小中枢，则不存在这个问题」"
       % (sum(s["npens"] for s in done) / len(done)), font=f_n, fill=MU)

im.save(out("zec15_duan.png"))
print("saved", im.size, "笔", len(r["pens"]), "完成线段", len(done), "线段中枢", len(r["seg_centers"]))
