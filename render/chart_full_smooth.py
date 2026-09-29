#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全量顺滑版（任意标的 / 周期）：一根连续的对数价格轴，从头到尾不拼接、不变形。

画 K线、笔、线段、线段中枢（笔中枢淡色对照），一根不省；中枢是水平带、笔和线段是直线。
用法：
    python3 render/chart_full_smooth.py btc_4h.json --name "BTC/USDT 永续" --tf "4 小时" --px 8 --ph 2400
    python3 render/chart_full_smooth.py zec15.json  --name "ZEC/USDT 永续" --tf "15 分钟" --px 2 --ph 3600
输出默认 out/<数据文件名>_smooth.png。
约定：未完成的笔 / 线段、仍在延续的中枢一律虚线；最后一根 K 线若尚未收盘，图上注明（画法在 render/full_common.py）。
"""
import os, sys, json, math, time, datetime, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import data, out
from render.style import *
from render.full_common import draw_layers, draw_labels, legend, price_ticks
from core import analyze

utc = lambda ms: datetime.datetime.fromtimestamp(ms / 1000, datetime.timezone.utc)
STEP_MS = {"15 分钟": 15 * 60e3, "30 分钟": 30 * 60e3, "1 小时": 3600e3, "2 小时": 7200e3, "4 小时": 14400e3,
           "1 天": 86400e3}


def render(fn, name, tf, px, ph, out_name=None):
    bars = json.load(open(data(fn), encoding="utf-8"))
    r = analyze(bars)
    pens, segs = r["pens"], r["segs"]
    done = [s for s in segs if not s.get("live")]
    n = len(bars)
    step = STEP_MS.get(tf, bars[1]["t"] - bars[0]["t"])
    last_open = bars[-1]["t"] + step > time.time() * 1000     # 最后一根还没收盘

    L, R, T = 40, 120, 300                          # 左 / 右 / 上边距（右边留给价格刻度）
    W = L + n * px + R
    Y0, Y1 = T + 40, T + 40 + ph
    H = Y1 + 140
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im, "RGBA")
    f_t, f_s, f_n, f_x = F(52), F(30), F(24), F(22)

    pmin = min(b["l"] for b in bars) * 0.985
    pmax = max(b["h"] for b in bars) * 1.015
    lo, hi = math.log(pmin), math.log(pmax)
    X = lambda i: L + i * px + px / 2
    Y = lambda p: Y1 - (math.log(p) - lo) / (hi - lo) * (Y1 - Y0)

    # ---- 网格：价格线（对数位置）+ 每天刻度 / 周一 / 月初 ----
    ticks = price_ticks(pmin, pmax)
    for p in ticks:
        d.line([L, Y(p), W - R, Y(p)], fill=(34, 38, 48), width=1)
    d.text((X(0) + 8, Y0 - 40), utc(bars[0]["t"]).strftime("%Y-%m"), font=f_s, fill=AM)
    for i, b in enumerate(bars):
        t = utc(b["t"])
        if t.hour or t.minute:
            continue
        if t.day == 1 and i > 0:
            d.line([X(i), Y0, X(i), Y1], fill=(60, 66, 80), width=3)
            d.text((X(i) + 8, Y0 - 40), t.strftime("%Y-%m"), font=f_s, fill=AM)
        elif t.weekday() == 0:
            d.line([X(i), Y0, X(i), Y1], fill=(40, 45, 56), width=1)
            d.text((X(i) + 6, Y1 + 12), t.strftime("%m/%d"), font=f_n, fill=MU)
        else:
            d.line([X(i), Y1 - 12, X(i), Y1], fill=(60, 66, 80), width=1)

    # ---- 结构层 + 标签最后画 ----
    center_labels = draw_layers(d, r, X, Y, bar_w=px)
    every = max(1200, (W - L - R) // 12)            # 价格刻度沿宽度重复
    placed = draw_labels(d, [((xl + 8, Y(p) - 30), "%g" % p) for p in ticks for xl in range(L, W - R - 100, every)],
                         f_x, MU)
    draw_labels(d, center_labels, f_n, CY, placed)
    for p in ticks:                                 # 右侧再标一列
        d.text((W - R + 12, Y(p) - 14), "%g" % p, font=f_x, fill=MU)
    if last_open:                                   # 未收盘的最后一根：虚线框出来并注明
        b = bars[-1]
        dashed_rect(d, [X(n - 1) - px, Y(b["h"]) - 6, X(n - 1) + px, Y(b["l"]) + 6], AM, width=2, dash_len=6, gap=4)
        d.text((X(n - 1) - 150, Y(b["l"]) + 14), "未收盘", font=f_n, fill=AM)

    # ---- 标题、图例、统计 ----
    t0, t1 = utc(bars[0]["t"]), utc(bars[-1]["t"])
    d.text((L, 36), "%s · %s · 全量顺滑版：K线 / 笔 / 线段 / 线段中枢" % (name, tf), font=f_t, fill=TX)
    d.text((L + 4, 108), "币安永续 ｜ %s – %s（UTC，末根为开盘时间%s）｜ %d 根K线 ｜ 每根 %d 像素 ｜ 全程同一根对数价格轴（不拼接、不变形）"
           % (t0.strftime("%Y-%m-%d %H:%M"), t1.strftime("%Y-%m-%d %H:%M"), "，尚未收盘" if last_open else "",
              n, px), font=f_s, fill=MU)
    d.text((L + 4, 152), "笔 %d ｜ 笔中枢 %d ｜ 完成线段 %d（+%d 条未完成）｜ 线段中枢 %d（只用已完成线段计算，项目口径）｜ 最新价 %g"
           % (len(pens), len(r["centers"]), len(done), len(segs) - len(done), len(r["seg_centers"]), bars[-1]["c"]),
           font=f_s, fill=TX)
    xe = legend(d, L + 4, 222, f_n)
    d.text((xe + 40, 208), "约定：未完成的笔 / 线段、仍在延续的中枢一律虚线 ｜ 冲浪者 · %s" % datetime.date.today().isoformat(),
           font=f_n, fill=MU)

    path = out(out_name or fn.replace(".json", "_smooth.png"))
    im.save(path, optimize=True)
    print("saved", path.split("/")[-1], im.size, "笔", len(pens), "笔中枢", len(r["centers"]),
          "完成线段", len(done), "线段中枢", len(r["seg_centers"]), "| 末根未收盘" if last_open else "")
    return path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("file", help="data/ 下的K线文件")
    ap.add_argument("--name", default="")
    ap.add_argument("--tf", default="")
    ap.add_argument("--px", type=int, default=2, help="每根K线的像素宽")
    ap.add_argument("--ph", type=int, default=3600, help="价格区高度（像素）")
    ap.add_argument("--out", help="输出文件名（out/ 下）")
    a = ap.parse_args()
    render(a.file, a.name, a.tf, a.px, a.ph, a.out)
