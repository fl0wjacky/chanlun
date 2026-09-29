#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""双级别对照图：4H 全景 / 30m 全景 / 30m 放大（级别嵌套演示）+ 结论

数字与结论句全部出图时由引擎现算（core.analyze）。笔中枢属第 83 课所说稳定性差的口径，仅作示意。
约定：未完成的笔 / 仍在延续的中枢一律虚线。
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json, datetime
from PIL import Image, ImageDraw
from render.style import *
from core import analyze
from config import data, out

W = 2900
PADL, PADR, PADT, PADB = 100, 160, 78, 58
D = lambda t: datetime.datetime.fromtimestamp(t, datetime.timezone.utc)


def chip_text(d, xy, text, font, col, placed=None):
    """带底色的文字 —— 压在 K 线 / 分型三角上也读得清。

    placed：本面板已放下的标签框；和它们重叠就往上挪一行（最多挪 4 次）。
    """
    x, y = xy
    tw = d.textlength(text, font=font)
    box = lambda yy: (x - 6, yy - 2, x + tw + 6, yy + font.size + 6)
    hits = lambda b: any(b[0] < q[2] and q[0] < b[2] and b[1] < q[3] and q[1] < b[3] for q in placed or [])
    for _ in range(4):
        if not hits(box(y)):
            break
        y -= font.size + 10
    d.rounded_rectangle(box(y), 6, fill=CARD + (225,))
    d.text((x, y), text, font=font, fill=col)
    if placed is not None:
        placed.append(box(y))


def panel(ax, bars, pens, fx, zs, y0, h, title, sub="", band_zs=None, seg_zs=None,
          zs_label=True, pen_w=4, big=False, last_pen_live=True):
    """zs / seg_zs 的 i0、i1（及 zs 的 F1）都是本面板 bars 里的下标。"""
    d = ImageDraw.Draw(ax, "RGBA")
    f_big, f_s, f_n, f_h = F(40 if big else 34), F(23), F(25), F(28)
    placed = []                                   # 本面板已放下的标签框（避让用）
    labels = []                                   # 中枢标签攒到最后画，免得被笔 / 分型压住
    lo = min(b["l"] for b in bars); hi = max(b["h"] for b in bars)
    for z in list(zs) + list(band_zs or []) + list(seg_zs or []):
        lo = min(lo, z["ZD"]); hi = max(hi, z["ZG"])
    pad = (hi - lo) * 0.07; lo -= pad; hi += pad
    plotW = W - PADL - PADR
    n = len(bars)
    X = lambda i: PADL + i / max(1, n - 1) * plotW
    Yp = lambda p: y0 + PADT + (hi - p) / (hi - lo) * (h - PADT - PADB)
    d.rounded_rectangle([40, y0, W - 40, y0 + h], 18, fill=CARD, outline=LINE, width=2)
    step = 10 if (hi - lo) > 40 else 5
    p = int(lo / step + 1) * step
    while p < hi:
        yy = Yp(p)
        if y0 + PADT < yy < y0 + h - PADB:
            d.line([PADL, yy, W - PADR, yy], fill=(40, 44, 56), width=1)
            d.text((W - PADR + 16, yy - 12), "%.0f" % p, font=f_s, fill=MU)
        p += step
    for z in band_zs or []:                       # 4H 笔中枢映射到 30m 的黄色带
        x0, x1 = X(max(0, z["a"])), X(min(n - 1, z["b"]))
        d.rectangle([x0, Yp(z["ZG"]), x1, Yp(z["ZD"])], fill=(255, 190, 60, 46), outline=AM, width=3)
    bw = max(1, int(plotW / n) - 1)
    for i, b in enumerate(bars):
        x = X(i); up = b["c"] >= b["o"]
        c = (38, 166, 154) if up else (239, 83, 80)
        d.line([x, Yp(b["l"]), x, Yp(b["h"])], fill=c, width=bw if bw > 2 else 1)
        if bw > 2:
            d.rectangle([x - bw / 2, Yp(max(b["o"], b["c"])), x + bw / 2, Yp(min(b["o"], b["c"]))], fill=c)
    for z in seg_zs or []:                        # 线段中枢（青框）
        box = [X(z["i0"]), Yp(z["ZG"]), X(z["i1"]), Yp(z["ZD"])]
        if z["live"]:
            dashed_rect(d, box, CY, width=4, fill=CY + (30,))
        else:
            d.rectangle(box, fill=CY + (30,), outline=CY, width=4)
    for z in zs:
        x0, x1, xf = X(z["i0"]), X(z["F1"]), X(z["i1"])
        yt, yb = Yp(z["ZG"]), Yp(z["ZD"])
        # 约定：仍在延续的中枢整框虚线；已终结的实线（成立段实色、延伸段淡色）
        if z["live"]:
            d.rectangle([x0, yt, x1, yb], fill=(120, 170, 255, 50))
            d.rectangle([x1, yt, xf, yb], fill=(200, 216, 248, 30))
            dashed_rect(d, [x0, yt, max(xf, x1), yb], BL, width=3, dash_len=14, gap=11)
        else:
            d.rectangle([x0, yt, x1, yb], fill=(120, 170, 255, 50), outline=BL, width=3)
            if xf > x1 + 4:
                d.rectangle([x1, yt, xf, yb], fill=(200, 216, 248, 30), outline=BL + (170,), width=2)
        if zs_label:
            lx = max(PADL, x0 - 46)
            d.line([lx, yt, x1, yt], fill=BL + (120,), width=1)
            d.line([lx, yb, x1, yb], fill=BL + (120,), width=1)
            if yb - yt < 60:                      # 窄中枢：两个标签并成一个，放框上方
                labels.append(((max(x0 - 44, PADL + 4), yt - 34), "ZG/ZD %.1f/%.1f" % (z["ZG"], z["ZD"])))
            else:
                labels.append(((max(x0 - 44, PADL + 4), yt + 4), "ZG %.1f" % z["ZG"]))
                labels.append(((max(x0 - 44, PADL + 4), yb - 30), "ZD %.1f" % z["ZD"]))
    for k, pn in enumerate(pens):
        a, b2 = (X(pn["i0"]), Yp(pn["p0"])), (X(pn["i1"]), Yp(pn["p1"]))
        if last_pen_live and k == len(pens) - 1:  # 约定：最后一笔未完成 → 虚线
            dashed_line(d, a, b2, LB, width=pen_w, dash_len=14, gap=9)
        else:
            d.line([a, b2], fill=BL, width=pen_w)
    for f in fx:
        x, yy = X(f["i"]), Yp(f["price"])
        if f["type"] == "top":
            d.polygon([(x, yy - 7), (x - 9, yy - 23), (x + 9, yy - 23)], fill=RD)
        else:
            d.polygon([(x, yy + 7), (x - 9, yy + 23), (x + 9, yy + 23)], fill=GR)
    for xy, t in labels:
        chip_text(d, xy, t, f_s, (205, 222, 255), placed)
    for z in band_zs or []:                       # 黄带标签最后画、加底色，免得被 K 线压住
        chip_text(d, (X(max(0, z["a"])) + 10, Yp(z["ZG"]) - 36), "4H %s" % z["nm"], f_h, AM, placed)
    t0, t1 = bars[0]["t"], bars[-1]["t"]
    dd = D(t0 / 1000).replace(hour=0, minute=0, second=0)       # 刻度按 UTC 午夜
    while dd.timestamp() * 1000 < t1:
        if dd.day == 1 or dd.day % 5 == 0:
            idx = (dd.timestamp() * 1000 - t0) / (t1 - t0) * (n - 1)
            if 0 <= idx <= n - 1:
                x = X(int(round(idx)))
                d.line([x, y0 + h - PADB, x, y0 + h - PADB + 10], fill=(90, 96, 112), width=1)
                lab = "%d月" % dd.month if dd.day == 1 else str(dd.day)
                d.text((x - 15, y0 + h - PADB + 16), lab, font=f_s, fill=MU)
        dd += datetime.timedelta(days=1)
    d.text((PADL + 8, y0 + 16), title, font=f_big, fill=TX)
    if sub:
        d.text((PADL + 8 + d.textlength(title, font=f_big) + 26, y0 + 24), sub, font=f_s, fill=MU)


def as_panel(zs):
    """引擎中枢 → 面板用：i0 / i1 / F1 为原始K线下标。"""
    return [dict(z, i0=z["X0"], i1=z["X1"]) for z in zs]


def overlap(ta, za, tb, zb):
    return ta[0] <= tb[1] and tb[0] <= ta[1] and za["ZD"] <= zb["ZG"] and zb["ZD"] <= za["ZG"]


def main():
    b4 = json.load(open(data("aaplusdt_4h.json"), encoding="utf-8"))
    b30 = json.load(open(data("aaplusdt_30m.json"), encoding="utf-8"))
    r4, r30 = analyze(b4), analyze(b30)
    p4, f4, z4 = r4["pens"], r4["fx"], as_panel(r4["centers"])
    p30, f30, z30 = r30["pens"], r30["fx"], as_panel(r30["centers"])
    for k, z in enumerate(z4):
        z["nm"] = "中枢%d" % (k + 1)
    done30 = [s for s in r30["segs"] if not s.get("live")]
    seg30 = [dict(z, i0=done30[z["PI0"]]["i0"], i1=done30[z["PI1"]]["i1"]) for z in r30["seg_centers"]]

    H = 74 + 720 + 30 + 880 + 30 + 760 + 470
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im, "RGBA")
    d.text((48, 28), "同一段行情，两个镜片：4小时 vs 30分钟", font=F(48), fill=TX)
    d.text((50, 96), "AAPL/USDT 永续 · %s – %s（UTC）· 笔中枢口径（第 83 课：稳定性差，仅作示意）"
           % (D(b30[0]["t"] / 1000).strftime("%Y/%m/%d"), D(b30[-1]["t"] / 1000).strftime("%m/%d")),
           font=F(26), fill=MU)
    r = "冲浪者 · %s" % datetime.date.today().isoformat()
    d.text((W - d.textlength(r, font=F(24)) - 48, 44), r, font=F(24), fill=(110, 118, 136))

    y = 150
    panel(im, b4, p4, f4, z4, y, 720, "① 4 小时图 · %d 笔 / %d 个笔中枢" % (len(p4), len(z4)), big=True)
    y += 750
    # 4H 中枢 → 30m 下标（按时间）：a = 起点所在 30m K 线，b = 终点那根 4H K 线走完前的最后一根 30m
    for z in z4:
        ta, tb = b4[z["X0"]]["t"], b4[min(z["X1"], len(b4) - 1)]["t"] + 4 * 3600 * 1000
        z["a"] = next((i for i, b in enumerate(b30) if b["t"] >= ta), 0)
        z["b"] = max(i for i, b in enumerate(b30) if b["t"] < tb)
    panel(im, b30, p30, f30, z30, y, 880,
          "② 30 分钟图 · %d 笔 / %d 个笔中枢" % (len(p30), len(z30)),
          sub="黄色带 = 4H 笔中枢；青框 = 30m 线段中枢（%d 个）" % len(seg30),
          band_zs=z4, seg_zs=seg30, zs_label=False)
    y += 910

    # ③ 放大 4H 中枢3：直接用全量 30m 的结果按时间截取（不在切片上重算，免得边界效应）
    z3 = z4[-1]
    M = 16                                        # 左右各留 16 根 30m（8 小时）
    w0, w1 = max(0, z3["a"] - M), min(len(b30) - 1, z3["b"] + M)
    zb = b30[w0:w1 + 1]
    pz = [dict(p, i0=p["i0"] - w0, i1=p["i1"] - w0) for p in p30 if p["i0"] >= w0 and p["i1"] <= w1]
    fz = [dict(f, i=f["i"] - w0) for f in f30 if w0 <= f["i"] <= w1]
    zz = [dict(z, i0=z["i0"] - w0, i1=z["i1"] - w0, F1=z["F1"] - w0) for z in z30
          if z["i0"] >= w0 and z["i1"] <= w1]
    inner = [z for z in z30 if z["i0"] >= z3["a"] and z["i1"] <= z3["b"]]     # 完整落在中枢3 时间内
    kinds = [z["kind"] for z in inner[1:]]
    band = dict(z3, a=z3["a"] - w0, b=z3["b"] - w0)
    ta, tb = D(b30[z3["a"]]["t"] / 1000), D(b30[z3["b"]]["t"] / 1000)
    panel(im, zb, pz, fz, zz, y, 760,
          "③ 30 分钟图 · 放大 4H 中枢3 覆盖的 %s – %s（UTC）：完整落在其中的 30 分钟笔中枢 %d 个"
          % (ta.strftime("%m/%d %H:%M"), tb.strftime("%m/%d %H:%M"), len(inner)),
          band_zs=[band], big=True, last_pen_live=(w1 == len(b30) - 1))
    y += 790

    # 结论：4H 笔中枢 vs 30m 线段中枢（时间、区间都交叠算对上）
    tz4 = [(b4[z["X0"]]["t"], b4[min(z["X1"], len(b4) - 1)]["t"]) for z in z4]
    ts30 = [(b30[z["i0"]]["t"], b30[z["i1"]]["t"]) for z in seg30]
    hit = sum(1 for i, z in enumerate(z4) if any(overlap(tz4[i], z, ts30[j], s) for j, s in enumerate(seg30)))
    d.rounded_rectangle([40, y, W - 40, y + 350], 18, fill=CARD, outline=LINE, width=2)
    d.text((80, y + 22), "结论", font=F(34), fill=AM)
    lines = [
        "同一段时间：4 小时镜片看到 %d 个笔中枢 / %d 笔；30 分钟镜片看到 %d 个笔中枢 / %d 笔。"
        % (len(z4), len(p4), len(z30), len(p30)),
        "4H 中枢3（%d 笔）在 30 分钟上是 %d 个笔中枢，相邻关系 %d 对扩展、%d 对趋势 —— 放大看仍是一个震荡，结构没变，是镜片变了。"
        % (z3["npens"], len(inner), kinds.count("扩展"), kinds.count("趋势")),
        "4H 的 %d 个笔中枢 与 30m 的 %d 个线段中枢，%d 个对得上（时间、区间都交叠；样本很少）。第 77 课：「不同周期 K 线图(不同倍度数显微镜)"
        % (len(z4), len(seg30), hit),
        "和走势的级别(显微镜所观察的物体)」—— 级别不是 K 线周期。4H 中枢3 的边界（ZG %.1f / ZD %.1f）在 30m 上是反复穿越的区域，"
        "按 30m 细节在边界挂单，容易被来回扫到。" % (z3["ZG"], z3["ZD"]),
    ]
    yy = y + 82
    for t in lines:
        d.text((80, yy), t, font=F(27), fill=TX); yy += 58
    im.save(out("chanlun_2levels.png"))
    print("saved", im.size, "| 中枢3 内 30m 笔中枢", len(inner), kinds, "| 4H↔30m 线段中枢对上", hit)


if __name__ == "__main__":
    main()
