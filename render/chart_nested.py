#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""级别递归的实证图：类中枢 → 扩展合成 → 上一级中枢（AAPLUSDT 永续，数字出图时现算）。

两条独立路径：A 在低一级图上画类中枢再把「扩展」链式合成；B 直接在高一级图上画类中枢。
只是个数接近，逐个比对位置只部分对上 —— 不能据此说「两条路径得到同一批中枢」。
全部为类中枢口径（笔构成，第 64 课「类中枢」；第 83 课：稳定性差）。
约定：未完成的笔 / 仍在延续的中枢一律虚线；只有真正合成出来的（nmerge>1）才画成紫色大级别中枢。
"""
import os, sys, json, datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PIL import Image, ImageDraw
from render.style import *
from config import data, out
from core import analyze, analyze_file

PUR = (196, 120, 250)          # 大级别中枢的颜色
W = 2900


def panel(ax, bars, pens, small, big, x0, y0, w, h, title, sub):
    d = ImageDraw.Draw(ax, "RGBA")
    lo = min(b["l"] for b in bars); hi = max(b["h"] for b in bars)
    lo -= (hi - lo) * 0.05; hi += (hi - lo) * 0.05
    X = lambda i: x0 + i / (len(bars) - 1) * w
    Y = lambda p: y0 + 50 + (hi - p) / (hi - lo) * (h - 100)
    step = 10
    p = int(lo / step + 1) * step
    while p < hi:
        yy = Y(p)
        if y0 + 50 < yy < y0 + h - 50:
            d.line([x0, yy, x0 + w, yy], fill=(38, 42, 54), width=1)
            d.text((x0 + w + 14, yy - 12), "%d" % p, font=F(22), fill=MU)
        p += step
    bw = max(1, int(w / len(bars)) - 1)
    for i, b in enumerate(bars):
        x = X(i); c = UP if b["c"] >= b["o"] else DN
        d.line([x, Y(b["l"]), x, Y(b["h"])], fill=c, width=bw if bw > 2 else 1)
        if bw > 2:
            d.rectangle([x - bw / 2, Y(max(b["o"], b["c"])), x + bw / 2, Y(min(b["o"], b["c"]))], fill=c)
    for z in small:                                    # 类中枢（仍在延续 → 虚线）
        box = [X(z["X0"]), Y(z["ZG"]), X(min(z["X1"], len(bars) - 1)), Y(z["ZD"])]
        if z["live"]:
            dashed_rect(d, box, BL, width=3, fill=BL + (46,))
        else:
            d.rectangle(box, fill=BL + (46,), outline=BL, width=3)
    for z in (z for z in big if z["nmerge"] > 1):      # 真正合成出来的大级别中枢（仍在延续 → 虚线）
        a = X(z["X0"])
        box = [a, Y(z["ZG"]), X(min(z["X1"], len(bars) - 1)), Y(z["ZD"])]
        if z.get("live"):
            dashed_rect(d, box, PUR, width=6, fill=PUR + (36,), dash_len=22, gap=12)
        else:
            d.rectangle(box, fill=PUR + (36,), outline=PUR, width=6)
        lab = "大级别中枢 [%.1f, %.1f]" % (z["ZD"], z["ZG"])
        tw = d.textlength(lab, font=F(24))
        d.rounded_rectangle([a + 4, Y(z["ZG"]) - 36, a + 16 + tw, Y(z["ZG"]) - 4], 6, fill=CARD + (230,))
        d.text((a + 10, Y(z["ZG"]) - 32), lab, font=F(24), fill=PUR)
    for k, pn in enumerate(pens):
        a, b2 = (X(pn["i0"]), Y(pn["p0"])), (X(pn["i1"]), Y(pn["p1"]))
        if k == len(pens) - 1:                         # 约定：最后一笔未完成 → 虚线
            dashed_line(d, a, b2, LB, width=3, dash_len=12, gap=8)
        else:
            d.line([a, b2], fill=(120, 170, 255, 190), width=3)
    t0, t1 = bars[0]["t"], bars[-1]["t"]
    dd = datetime.datetime.fromtimestamp(t0 / 1000, datetime.timezone.utc)
    while dd.timestamp() * 1000 < t1:
        if dd.day == 1 or dd.day % 5 == 0:
            idx = (dd.timestamp() * 1000 - t0) / (t1 - t0) * (len(bars) - 1)
            if 0 <= idx <= len(bars) - 1:
                x = X(int(idx))
                d.line([x, y0 + h - 50, x, y0 + h - 42], fill=(90, 96, 112), width=1)
                lab = "%d月" % dd.month if dd.day == 1 else str(dd.day)
                d.text((x - 14, y0 + h - 36), lab, font=F(22), fill=MU)
        dd += datetime.timedelta(days=1)
    d.text((x0, y0 + 6), title, font=F(38), fill=TX)
    d.text((x0, y0 + h + 8), sub, font=F(24), fill=MU)          # 放在面板下方，免得被 K 线压住


def overlap(ta, za, tb, zb):
    return ta[0] <= tb[1] and tb[0] <= ta[1] and za["ZD"] <= zb["ZG"] and zb["ZD"] <= za["ZG"]


def main():
    R = {tf: analyze_file("aaplusdt_%s.json" % tf) for tf in ("30m", "1h", "2h", "4h")}
    r4 = R["4h"]
    B = lambda r, i: datetime.datetime.fromtimestamp(r["bars"][min(i, len(r["bars"]) - 1)]["t"] / 1000,
                                                     datetime.timezone.utc)
    H = 1640
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im, "RGBA")
    d.text((48, 30), "级别是怎么一层层长上去的 —— 用扩展合成对照", font=F(46), fill=TX)
    d.text((50, 96), "币安合约 AAPLUSDT 永续 · %s – %s（UTC）· 全部为类中枢口径（笔构成，第 64 / 83 课：稳定性差，仅作示意）"
           % (B(R["30m"], 0).strftime("%Y/%m/%d"), B(R["30m"], 10 ** 9).strftime("%m/%d %H:%M")), font=F(26), fill=MU)
    rr = "冲浪者 · %s" % datetime.date.today().isoformat()
    d.text((W - d.textlength(rr, font=F(24)) - 48, 44), rr, font=F(24), fill=(110, 118, 136))

    # 图例（笔画成线，中枢画成框；虚线 = 未完成 / 仍在延续）
    lx, ly = 50, 1110
    d.line([lx, ly + 12, lx + 40, ly + 12], fill=(120, 170, 255), width=3)
    d.text((lx + 52, ly), "笔", font=F(26), fill=MU); lx += 52 + d.textlength("笔", font=F(26)) + 70
    for lab, col, w in (("类中枢", BL, 3), ("大级别中枢（扩展链式合成）", PUR, 5)):
        d.rectangle([lx, ly, lx + 34, ly + 24], fill=col + (50,), outline=col, width=w)
        d.text((lx + 46, ly), lab, font=F(26), fill=MU)
        lx += 46 + d.textlength(lab, font=F(26)) + 70
    dashed_line(d, (lx, ly + 12), (lx + 40, ly + 12), (120, 170, 255), 3, 10, 7)
    d.text((lx + 52, ly), "虚线 = 未完成的笔 / 仍在延续的中枢", font=F(26), fill=MU)

    merged = lambda r: [z for z in r["big"] if z["nmerge"] > 1]
    big = max(merged(r4), key=lambda z: z["nmerge"])
    panel(im, r4["bars"], r4["pens"], r4["centers"], r4["big"],
          140, 150, W - 420, 900,
          "4 小时图：%d 个类中枢 → 合出 %d 个大级别中枢" % (len(r4["centers"]), len(merged(r4))),
          "%d 个类中枢相邻不成趋势（扩展或区间重叠）→ 合成大级别中枢 [%.1f, %.1f]（%s → %s）；"
          "区间 = 前中枢、连接段、后中枢三段按高低点取重叠，只看前三段（第 52 / 54 课）"
          % (big["nmerge"], big["ZD"], big["ZG"], B(r4, big["X0"]).strftime("%m/%d"),
             B(r4, big["X1"]).strftime("%m/%d")))

    # 对照表（现算）
    y = 1180
    d.rounded_rectangle([50, y, W - 50, H - 40], 18, fill=CARD, outline=LINE, width=2)
    d.text((86, y + 20), "两条独立路径：个数接近，位置只部分对上", font=F(32), fill=AM)
    cols = [("周期", 120), ("笔数", 330), ("类中枢", 520), ("扩展合并后（其中合成的大级别中枢）", 780)]
    for t, x in cols:
        d.text((86 + x, y + 76), t, font=F(26), fill=MU)
    yy = y + 118
    for tf, name in (("30m", "30 分钟"), ("1h", "1 小时"), ("2h", "2 小时"), ("4h", "4 小时")):
        r = R[tf]
        for x, v, c in ((120, name, TX), (330, str(len(r["pens"])), MU), (520, str(len(r["centers"])), BL),
                        (780, "%d（%d）" % (len(r["big"]), len(merged(r))), PUR)):
            d.text((86 + x, yy), v, font=F(28), fill=c)
        yy += 40
    # 30m 合并后 vs 1h 类中枢：逐个比对位置（时间、区间都交叠）
    A, Bz = R["30m"]["big"], R["1h"]["centers"]
    ta = [(R["30m"]["bars"][z["X0"]]["t"], R["30m"]["bars"][min(z["X1"], len(R["30m"]["bars"]) - 1)]["t"]) for z in A]
    tb = [(R["1h"]["bars"][z["X0"]]["t"], R["1h"]["bars"][min(z["X1"], len(R["1h"]["bars"]) - 1)]["t"]) for z in Bz]
    hit = sum(1 for i, a in enumerate(A) if any(overlap(ta[i], a, tb[j], b) for j, b in enumerate(Bz)))
    d.line([86, yy + 6, W - 86, yy + 6], fill=LINE, width=2)
    d.text((86, yy + 22), "★ 个数对照：30m 合并后 %d  vs  1h 类中枢 %d　｜　1h 合并后 %d  vs  2h 类中枢 %d　｜　2h 合并后 %d  vs  4h 类中枢 %d"
           % (len(A), len(Bz), len(R["1h"]["big"]), len(R["2h"]["centers"]), len(R["2h"]["big"]), len(r4["centers"])),
           font=F(30), fill=AM)
    d.text((86, yy + 66), "→ 只是个数接近：逐个比对位置，30m→1h 只有 %d/%d 对得上，不能说是「同一批中枢」。"
                          "（合成按第 52 课「扩展可以不断延续下去」链式接续，区间只看前三段）" % (hit, len(A)), font=F(26), fill=TX)
    im.save(out("chanlun_nested.png"))
    print("saved", im.size, "| 大中枢 [%.1f, %.1f] nmerge %d | 30m→1h %d/%d" % (big["ZD"], big["ZG"], big["nmerge"], hit, len(A)))


if __name__ == "__main__":
    main()
