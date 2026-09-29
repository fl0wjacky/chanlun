# -*- coding: utf-8 -*-
"""全量图共用的画法（ZEC 分面板版 / 顺滑版 / 概览，BTC 等任意标的的顺滑版）：结构层、标签、图例、刻度。

约定：未完成的笔 / 线段、仍在延续的中枢一律虚线；已完成的实线。
标签（中枢区间、价格刻度）一律最后画、带底色、互相避让 —— 免得被 K 线和笔压住。
"""
from render.style import *


def draw_layers(g, r, X, Y, keep=lambda a, b: True, bar_w=2):
    """在画布 g 上画：类中枢（笔构成，淡）→ 线段中枢 → K 线 → 笔 → 线段。

    X(i) / Y(p)：K 线下标、价格 → 像素（X 给的是这根 K 线的中心）；
    keep(a, b)：下标区间 [a, b] 要不要画（分面板时筛本月）；bar_w：每根 K 线占的像素宽。
    返回标签请求 [((x, y), 文本) 或 ((x, y), 文本, 颜色)]，交给 draw_labels 最后画：
    线段中枢的区间，以及满 9 段中枢的「↑高一级」标记（第 33 课，引擎 z["up"]；满 27 段标「↑高两级」）。
    """
    bars, pens, segs = r["bars"], r["pens"], r["segs"]
    done = [s for s in segs if not s.get("live")]     # 线段中枢的序号指向「已完成线段」
    labels = []

    def up_mark(z, box):
        if z.get("up"):
            labels.append(((max(box[0], 0) + 8, box[1] - 36), "↑高%s级" % "一两三四"[len(z["up"]) - 1], AM))

    for z in r["centers"]:
        a, b = pens[z["PI0"]]["i0"], pens[z["PI1"]]["i1"]
        if keep(a, b):
            box = [X(a), Y(z["ZG"]), X(b), Y(z["ZD"])]
            up_mark(z, box)
            if z["live"]:
                dashed_rect(g, box, BL + (120,), width=2, fill=BL + (20,))
            else:
                g.rectangle(box, fill=BL + (20,), outline=BL + (95,), width=2)
    for z in r["seg_centers"]:
        a, b = done[z["PI0"]]["i0"], done[z["PI1"]]["i1"]
        if keep(a, b):
            box = [X(a), Y(z["ZG"]), X(b), Y(z["ZD"])]
            if z["live"]:
                dashed_rect(g, box, CY, width=5, fill=CY + (38,))
            else:
                g.rectangle(box, fill=CY + (38,), outline=CY, width=5)
            labels.append(((max(box[0], 0) + 8, box[1] - 36), "[%g, %g]" % (round(z["ZD"], 2), round(z["ZG"], 2))))
            up_mark(z, box)
    for i, b in enumerate(bars):                      # K 线：影线 + 实体
        if keep(i, i):
            col = UP if b["c"] >= b["o"] else DN
            top, bot = Y(max(b["o"], b["c"])), Y(min(b["o"], b["c"]))
            if bar_w <= 2:                            # 2 像素：影线占左边 1 像素，实体铺满 2 像素
                x = X(i) - 1
                g.line([x, Y(b["h"]), x, Y(b["l"])], fill=col + (160,), width=1)
                g.rectangle([x, top, x + 1, bot], fill=col + (210,))
            else:                                     # 更宽：影线居中，实体两侧各留 1 像素缝
                x = X(i)
                g.line([x, Y(b["h"]), x, Y(b["l"])], fill=col + (200,), width=max(1, bar_w // 5))
                g.rectangle([x - bar_w / 2 + 1, top, x + bar_w / 2 - 1, max(bot, top + 1)], fill=col + (230,))
    for k, p in enumerate(pens):                      # 最后一笔未完成（终点还会被更极端的分型替换）→ 虚线
        if keep(p["i0"], p["i1"]):
            a, b = (X(p["i0"]), Y(p["p0"])), (X(p["i1"]), Y(p["p1"]))
            if k == len(pens) - 1:
                dashed_line(g, a, b, LB, width=3, dash_len=12, gap=8)
            else:
                g.line([a, b], fill=BL + (235,), width=2)
    for s in segs:                                    # 未完成（live）→ 虚线；端点：顶红、底绿
        if keep(s["i0"], s["i1"]):
            a, b = (X(s["i0"]), Y(s["p0"])), (X(s["i1"]), Y(s["p1"]))
            if s.get("live"):                         # 未完成段画到「迄今的极值」（向上段最高、向下段最低）——
                ext = s["hi"] if s["dir"] == "up" else s["lo"]    # 那才是它眼下可能的终点；之后的走势由笔表达
                k = max(j for j in range(s["PI0"], s["PI1"] + 1) if pens[j]["p1"] == ext)
                b = (X(pens[k]["i1"]), Y(ext))
            if s.get("live"):
                dashed_line(g, a, b, AM, width=7, dash_len=26, gap=16)
            else:
                g.line([a, b], fill=AM, width=7)
            up = s["dir"] == "up"
            for (x, y), col in ((a, GR if up else RD), (b, RD if up else GR)):
                g.ellipse([x - 9, y - 9, x + 9, y + 9], fill=BG, outline=col, width=4)
    return labels


def draw_labels(g, labels, font, col, placed=None):
    """带底色的标签，最后画；与已放下的框重叠就往上挪一行（最多 4 次）。"""
    placed = [] if placed is None else placed
    for lab in labels:
        (x, y), text = lab[0], lab[1]
        c = lab[2] if len(lab) > 2 else col
        tw = g.textlength(text, font=font)
        box = lambda yy: (x - 6, yy - 2, x + tw + 6, yy + font.size + 8)
        for _ in range(4):
            bx = box(y)
            if not any(bx[0] < q[2] and q[0] < bx[2] and bx[1] < q[3] and q[1] < bx[3] for q in placed):
                break
            y -= font.size + 12
        g.rounded_rectangle(box(y), 6, fill=BG + (215,))
        g.text((x, y), text, font=font, fill=c)
        placed.append(box(y))
    return placed


def legend(d, x, y, font):
    """图例样例与实际画法一致：K 线红绿、笔 / 线段是线、中枢是框、未完成是虚线。"""
    def item(draw_sample, name):
        nonlocal x
        draw_sample(x, y)
        d.text((x + 84, y - 14), name, font=font, fill=TX)
        x += 84 + d.textlength(name, font=font) + 56
    item(lambda x0, y0: [d.rectangle([x0 + k * 14, y0 - 10 + (k % 2) * 6, x0 + k * 14 + 8, y0 + 6 + (k % 2) * 6],
                                     fill=(UP, DN)[k % 2]) for k in range(5)], "K线")
    item(lambda x0, y0: d.line([x0, y0, x0 + 70, y0], fill=BL, width=3), "笔")
    item(lambda x0, y0: dashed_line(d, (x0, y0), (x0 + 70, y0), LB, 3, 12, 8), "未完成的笔")
    item(lambda x0, y0: d.line([x0, y0, x0 + 70, y0], fill=AM, width=7), "线段")
    item(lambda x0, y0: dashed_line(d, (x0, y0), (x0 + 70, y0), AM, 7, 22, 12), "未完成的线段")
    item(lambda x0, y0: d.rectangle([x0, y0 - 14, x0 + 70, y0 + 14], fill=CY + (38,), outline=CY, width=4), "线段中枢")
    item(lambda x0, y0: d.rectangle([x0, y0 - 14, x0 + 70, y0 + 14], fill=BL + (20,), outline=BL + (95,), width=2),
         "类中枢（对照）")
    item(lambda x0, y0: dashed_rect(d, [x0, y0 - 14, x0 + 70, y0 + 14], CY, 3, fill=CY + (20,), dash_len=12, gap=8),
         "仍在延续的中枢")
    item(lambda x0, y0: d.text((x0 + 24, y0 - 16), "↑", font=font, fill=AM), "高一级 = 满 9 段的中枢（第 33 课）")
    return x


def price_ticks(pmin, pmax):
    """对数轴上的价格刻度：跨度大（≥3 倍）用 1/1.2/1.5/2/…×10^n；跨度小用线性整数间隔（约 10 条）。"""
    import math
    if pmax / pmin >= 3:
        steps = (1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 7, 8)
        return [v * 10 ** k for k in range(-2, 8) for v in steps if pmin <= v * 10 ** k <= pmax]
    raw = (pmax - pmin) / 10
    e = 10 ** math.floor(math.log10(raw))
    step = next(s * e for s in (1, 2, 2.5, 5, 10) if s * e >= raw)
    return [k * step for k in range(math.ceil(pmin / step), math.floor(pmax / step) + 1)]
