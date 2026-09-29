#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ZEC 15 分钟 · 全量高清图（按月分面板版）：K线、笔、线段、线段中枢（笔中枢淡色对照），一根不省。

每根 K 线 2 像素宽，整张图约 4 万像素宽。按**自然月分面板**，每个面板纵轴按当月价格
各自缩放 —— 这段 ZEC 从一两百涨到一千多，共用一根价格轴会把前几个月压成一条线。
横向连续：跨月的笔 / 线段 / 中枢在相邻两个面板里各画一截（面板间有分隔线，价格刻度各看各的）。
想要从头到尾同一根价格轴，看 chart_zec_full_smooth.py（顺滑版）。
约定：未完成的笔 / 线段、仍在延续的中枢，一律虚线（画法在 render/full_common.py）。
"""
import os, sys, json, math, datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import data, out
from render.style import *
from render.full_common import draw_layers, draw_labels, legend
from core import analyze

PX = 2                                              # 每根K线的像素宽
bars = json.load(open(data("zec15.json"), encoding="utf-8"))
r = analyze(bars)
pens, segs = r["pens"], r["segs"]
done = [s for s in segs if not s.get("live")]
n = len(bars)
utc = lambda ms: datetime.datetime.fromtimestamp(ms / 1000, datetime.timezone.utc)

L, R, T = 40, 40, 300                               # 左 / 右 / 上边距
GAP = 6                                             # 面板之间的分隔
PAD_END = 40                                        # 最后一个面板右侧留白（最后的端点圈、虚线不被裁）
PH = 1700                                           # 面板高度
f_t, f_s, f_n, f_x = F(52), F(30), F(24), F(22)

# ---- 按自然月切面板 ----
months = []
for i, b in enumerate(bars):
    key = utc(b["t"]).strftime("%Y-%m")
    if not months or months[-1][0] != key:
        months.append([key, i, i])
    months[-1][2] = i

W = L + n * PX + GAP * (len(months) - 1) + PAD_END + R
H = T + 60 + PH + 150
im = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(im, "RGBA")


def nice_ticks(a, b, k=8):
    """线性刻度：步长取 1/2/5×10^n，约 k 条。"""
    raw = (b - a) / k
    e = 10 ** math.floor(math.log10(raw))
    step = next(s * e for s in (1, 2, 5, 10) if s * e >= raw)
    t, out_ = math.ceil(a / step) * step, []
    while t <= b:
        out_.append(round(t, 6)); t += step
    return out_


def draw_panel(i0, i1, last):
    """画一个月的面板，返回子图。"""
    pw = (i1 - i0 + 1) * PX + (PAD_END if last else 0)
    sub = Image.new("RGB", (pw, PH), BG)
    g = ImageDraw.Draw(sub, "RGBA")
    lo = min(bars[i]["l"] for i in range(i0, i1 + 1))
    hi = max(bars[i]["h"] for i in range(i0, i1 + 1))
    pad = (hi - lo) * 0.06
    lo, hi = lo - pad, hi + pad
    X = lambda i: (i - i0) * PX + PX / 2
    Y = lambda p: PH - 40 - (p - lo) / (hi - lo) * (PH - 80)

    ticks = nice_ticks(lo, hi)
    for p in ticks:                                 # 网格线先画，刻度文字最后画
        g.line([0, Y(p), pw, Y(p)], fill=(34, 38, 48), width=1)
    for i in range(i0, i1 + 1):
        t = utc(bars[i]["t"])
        if t.hour == 0 and t.minute == 0:
            g.line([X(i), 0, X(i), PH], fill=(40, 45, 56) if t.weekday() == 0 else (27, 30, 38), width=1)

    center_labels = draw_layers(g, r, X, Y, keep=lambda a, b: b >= i0 and a <= i1)
    placed = draw_labels(g, [((xl + 8, Y(p) - 30), "%g" % p) for p in ticks for xl in range(0, pw - 120, 1400)],
                         f_x, MU)
    draw_labels(g, center_labels, f_n, CY, placed)
    return sub


x = L
for m, (key, i0, i1) in enumerate(months):
    sub = draw_panel(i0, i1, m == len(months) - 1)
    im.paste(sub, (x, T + 60))
    d.rectangle([x - 1, T + 59, x + sub.width, T + 60 + PH], outline=LINE, width=2)
    t0, t1 = utc(bars[i0]["t"]), utc(bars[i1]["t"])
    d.text((x + 10, T + 6), "%s  ｜  %s – %s（UTC）｜ 本月价格 %g – %g"
           % (key, t0.strftime("%m/%d"), t1.strftime("%m/%d"),
              round(min(bars[i]["l"] for i in range(i0, i1 + 1)), 2),
              round(max(bars[i]["h"] for i in range(i0, i1 + 1)), 2)), font=f_s, fill=AM)
    for i in range(i0, i1 + 1):                     # 日期刻度（每周一）
        t = utc(bars[i]["t"])
        if t.hour == 0 and t.minute == 0 and t.weekday() == 0:
            d.text((x + (i - i0) * PX + 6, T + 60 + PH + 12), t.strftime("%m/%d"), font=f_n, fill=MU)
    x += sub.width + GAP

# ---- 标题、图例、统计（左上角）----
t0, t1 = utc(bars[0]["t"]), utc(bars[-1]["t"])
d.text((L, 36), "ZEC/USDT 永续 · 15 分钟 · 全量（按月分面板）：K线 / 笔 / 线段 / 线段中枢", font=f_t, fill=TX)
d.text((L + 4, 108), "币安永续 ZECUSDT ｜ %s – %s（UTC）｜ %d 根K线 ｜ 每根 %d 像素 ｜ 按月分面板，纵轴各月自缩放（看价格请看本面板刻度）"
       % (t0.strftime("%Y-%m-%d %H:%M"), t1.strftime("%Y-%m-%d %H:%M"), n, PX), font=f_s, fill=MU)
d.text((L + 4, 152), "笔 %d ｜ 笔中枢 %d ｜ 完成线段 %d（+%d 条未完成）｜ 线段中枢 %d（只用已完成线段计算，项目口径）｜ 最新收盘 %g"
       % (len(pens), len(r["centers"]), len(done), len(segs) - len(done), len(r["seg_centers"]), bars[-1]["c"]),
       font=f_s, fill=TX)
xe = legend(d, L + 4, 222, f_n)
d.text((xe + 40, 208), "约定：未完成的笔 / 线段、仍在延续的中枢一律虚线 ｜ 冲浪者 · %s" % datetime.date.today().isoformat(),
       font=f_n, fill=MU)

im.save(out("zec15_full.png"), optimize=True)
print("saved", im.size, "面板", len(months), "笔", len(pens), "完成线段", len(done), "线段中枢", len(r["seg_centers"]))
