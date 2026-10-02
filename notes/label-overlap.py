# -*- coding: utf-8 -*-
"""价签挤不挤：把 zec15 那支图上的标签**最后落在哪**算一遍，数重叠（只读，不写图）。

为什么要有这个：2026-10-02 小栋要「每一个中枢左上角都标 [ZD, ZG]」，类中枢一下子多出 142 个价签。
`draw_labels` 的避让是「重叠了往上挪一行，最多挪 4 次」—— **挪完还可能重叠**（上面 4 行也占满了）。
「看着有点挤」是个感觉，这里把它变成数：**有多少对标签的矩形真的相交**。

做法：照 render/chart_zec_segments.py 的窗口重画一遍（画在一块临时子图上，不落盘），
拿 draw_labels 的返回值 `placed`（每个标签最终的矩形），两两求交。
`labels` 与 `placed` 一一对应、同序，所以能报出**是哪些文字**叠在一起。

★ 它能证什么、不能证什么：
    能证 —— 这一份数据、这一个窗口下，标签矩形有没有真交叠、是哪几对、有没有从面板顶跑出去。
    不能证 —— TradingView 上挤不挤（那边是 label 自己排，规则完全不同），
              也不能证「读不清」：矩形相交一定读不清，但不相交也不代表好读（挨太近一样糊）。
★ 退出码 1 的两种情形里，有一种是**旧账**，读的时候别混：
    「'一卖' / '二卖' 两个标签跑出面板顶（y=-112）」在 **11a6d43（没有价签统一、没有类中枢价签）上
    一模一样** —— 是买卖点标签自己的位置问题，不是价签这一改带来的。量的时候两边都跑一遍对比。
    python3 notes/label-overlap.py
退出码：0 = 没有相交、也没有标签跑出面板；1 = 有其中之一（或没标签可量）。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image, ImageDraw                                        # noqa: E402
from config import data, tick_of                                        # noqa: E402
from core.analyze import analyze                                        # noqa: E402
from render.style import BG, F, MU                                      # noqa: E402
from render.full_common import (draw_layers, draw_labels, draw_signals,  # noqa: E402
                                price_ticks)


def duan_window(r, bars):
    """render/chart_zec_segments.py 那套（最后 16 条线段的窗口），逐字抄。"""
    segs = r["segs"][-16:]
    a0 = segs[0]["i0"]
    view = bars[a0:]
    X0, X1, Y0, Y1 = 120, 2900 - 260, 200, 1160
    PW, PHt = X1 - X0, Y1 - Y0
    pmin = min(b["l"] for b in view)
    pmax = max(b["h"] for b in view)
    pad = (pmax - pmin) * 0.04
    pmin -= pad
    pmax += pad
    n = len(view)
    X = lambda i: 12 + (i - a0) / (n - 1) * (PW - 24)
    Y = lambda p: PHt - (p - pmin) / (pmax - pmin) * PHt
    return X, Y, PW, PHt, (lambda a, b: b > a0)


def smooth_window(r, bars):
    """render/chart_full_smooth.py 那套（全量顺滑版，px=2 / ph=3600），逐字抄。

    ★ 画布**不照着开真的 40480×4080**（那要 500 MB）。`draw_labels` 只用到 `textlength`
      和画图（画图会被小画布裁掉，无所谓）—— **矩形是纯几何算出来的**，跟画布多大无关。
      所以这里开一张 100×100 的假画布，量出来的 `placed` 与真图逐字相同。
    """
    n = len(bars)
    px, ph = 2, 3600
    L, R, T = 40, 120, 300
    Y1 = T + 40 + ph
    pmin = min(b["l"] for b in bars) * 0.985
    pmax = max(b["h"] for b in bars) * 1.015
    lo, hi = __import__("math").log(pmin), __import__("math").log(pmax)
    X = lambda i: L + i * px + px / 2
    Y = lambda p: Y1 - (__import__("math").log(p) - lo) / (hi - lo) * (Y1 - (T + 40))
    return X, Y, 100, 100, (lambda a, b: True)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "duan"
    bars = json.load(open(data("zec15.json"), encoding="utf-8"))
    r = analyze(bars, tick=tick_of("zec15.json"))
    X, Y, PW, PHt, keep = (duan_window if mode == "duan" else smooth_window)(r, bars)

    f_n = F(24)
    sub = Image.new("RGB", (PW, PHt), BG)
    g = ImageDraw.Draw(sub, "RGBA")
    labels = draw_layers(g, r, X, Y, keep=keep, **({} if mode == "duan" else {"bar_w": 2}))
    labels += draw_signals(g, r, X, Y, keep=keep)
    if mode == "smooth":            # 顺滑版先铺一排价格刻度（它们也占地方），跟真图一样
        W = 40 + len(bars) * 2 + 120
        every = max(1200, (W - 40 - 120) // 12)
        pmin = min(b["l"] for b in bars) * 0.985
        pmax = max(b["h"] for b in bars) * 1.015
        ticks = price_ticks(pmin, pmax)
        tick_labels = [((xl + 8, Y(p) - 30), "%g" % p)
                       for p in ticks for xl in range(40, W - 120 - 100, every)]
        placed = draw_labels(g, tick_labels, F(22), MU)
    else:
        tick_labels, placed = [], []
    n_ticks = len(placed)                     # 刻度标签先占位，它们也在 placed 里 —— 要切掉
    tick_boxes = list(placed)
    placed = draw_labels(g, labels, f_n, (64, 200, 220), placed)[n_ticks:]
    tick_texts = [t for _, t in tick_labels]
    print("（顺滑版：另有 %d 个价格刻度标签先占了位；它们与结构标签的相交单独数一行）" % n_ticks)
    if not placed:
        print("★ 一个标签都没有 —— 查不了 ≠ 通过")
        return 1

    texts = [lab[1] for lab in labels]
    assert len(texts) == len(placed), "labels 与 placed 数量不等（%d / %d）" % (len(texts), len(placed))
    pairs = []
    for i in range(len(placed)):
        for j in range(i + 1, len(placed)):
            a, b = placed[i], placed[j]
            if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]:
                ov = (min(a[2], b[2]) - max(a[0], b[0])) * (min(a[3], b[3]) - max(a[1], b[1]))
                pairs.append((ov, texts[i], texts[j]))
    # 挪了几行：标签原本该在的位置（-36 那行）与最终落点差多少
    moved = sum(1 for i, (x, y) in enumerate(lab[0] for lab in labels)
                if abs(placed[i][1] - (y - 2)) > 4)
    print("标签 %d 个；两两相交的 %d 对；被避让挪过的 %d 个" % (len(placed), len(pairs), moved))
    # ★ 刻度标签是**先**放的（真图里也是这个顺序），结构标签得绕开它们 —— 绕不开就重叠。
    #   只数结构标签之间的相交会漏掉这一类，所以单列一行。
    cross = 0
    for i, q in enumerate(tick_boxes):
        for j, b in enumerate(placed):
            if q[0] < b[2] and b[0] < q[2] and q[1] < b[3] and b[1] < q[3]:
                cross += 1
                if cross <= 6:
                    print("  ✗ 刻度 %r 压在结构标签 %r 上" % (tick_texts[i], texts[j]))
    print("刻度标签压在结构标签上的 %d 处" % cross)
    # ★ 挪上去的代价：挪出面板顶就被裁掉（画在子图上、再贴进画布，负坐标没有像素）。
    #   所以「相交 0 对」不能一个人交差 —— 得同时没有标签从顶上跑出去，否则只是换了个方式读不到。
    top = min(b[1] for b in placed)
    off = [texts[i] for i, b in enumerate(placed) if b[3] <= 0 or b[1] < 0]
    print("最高的标签落在 y=%d（面板高 %d）；跑出面板的 %d 个%s"
          % (top, PHt, len(off), ("：" + ", ".join(repr(t) for t in off)) if off else ""))
    if pairs:
        pairs.sort(reverse=True)
        for ov, t1, t2 in pairs[:10]:
            print("  ✗ 相交 %4d px²：%r  ⟷  %r" % (ov, t1, t2))
    return 1 if (pairs or off) else 0


if __name__ == "__main__":
    sys.exit(main())
