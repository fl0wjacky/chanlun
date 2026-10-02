# -*- coding: utf-8 -*-
"""从**出好的图**上量线宽（笔 / 线段 / 各类中枢框）—— 只读像素，不问代码。

为什么要有这个：`style.py` 里写 `seg_w = 5` 只证明"我想让它 5"，不证明**画出来是 5**。
2026-10-02 小栋要「线段默认线宽 3 → 2」，Python 这边我定的数是 5（理由写在 style.py 里），
那就得从图上量一遍：改前量到 7、改后量到 5，这条改动才算落地。

怎量：15 分钟图的线段**都很陡**（没有一条接近水平，竖直截距会放大好几倍），所以不切竖直，
而是**沿线段法线**切：在线上取一点，沿单位法线以 0.25 px 步长走，数命中线段色的采样点数 × 0.25。
法线方向与线段垂直 ⇒ 量到的就是**真线宽**，跟斜率无关。图例里那根线段样例是**水平**画的，
竖直截距就是线宽本身，拿它跟实测的线段对一下 —— 两个数不一致就说明"图例说的"和"图上画的"分家了。

    python3 notes/linewidth-check.py out/zec15_duan.png                  # 单张
    python3 notes/linewidth-check.py 改后.png 改前.png                     # 两张对比着打
退出码：0 = 量到了；1 = 一个都没量到（窗口/颜色不对？）—— 量不到 ≠ 通过。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collections import Counter                                          # noqa: E402

from PIL import Image                                                    # noqa: E402
from config import data, tick_of                                          # noqa: E402
from core.analyze import analyze                                          # noqa: E402
from render.style import CHART                                           # noqa: E402

LEGEND_Y = 1160 + 62                                     # chart_zec_segments.py 里图例所在的那一行


def window():
    """chart_zec_segments.py 的坐标，逐字抄。"""
    bars = json.load(open(data("zec15.json"), encoding="utf-8"))
    r = analyze(bars, tick=tick_of("zec15.json"))
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
    X = lambda i: X0 + 12 + (i - a0) / (n - 1) * (PW - 24)
    Y = lambda p: Y0 + PHt - (p - pmin) / (pmax - pmin) * PHt
    return r, X, Y


def run(png, col, legend_y):
    """所有线段上取一批样本，沿**法线**数 `col` 的采样点 × 0.25 → 线宽分布。

    单点量一次不算数（接头、端点、跟 K 线交叠的地方都会偏），所以取一批、报**众数**。
    ★ 系统性偏差：量出来总比配置值大 0.5 px 左右（PIL 画线 + 采样取整 + 折线接头），
      两侧同一个偏差 —— 所以看的是**改动前后的差**，不是「绝对值等于配置值」。
    """
    r, X, Y = window()
    done = [s for s in r["segs"] if not s.get("live")]
    im = Image.open(png).convert("RGB")
    px = im.load()
    W, H = im.size
    vals = []
    for s in done:
        x0, x1 = X(s["i0"]), X(s["i1"])
        y0, y1 = Y(s["p0"]), Y(s["p1"])
        dx, dy = x1 - x0, y1 - y0
        L = (dx * dx + dy * dy) ** 0.5
        if L < 60:                                            # 太短的线段端点效应占比大
            continue
        nx, ny = -dy / L, dx / L                              # 单位法线
        for t in (0.25, 0.4, 0.5, 0.6, 0.75):
            x, y = x0 + dx * t, y0 + dy * t
            if not (20 < x < W - 20 and 20 < y < H - 20):
                continue
            hits, seen = 0, False
            for k in range(-40, 41):                          # 法线方向 ±10 px
                hx, hy = int(round(x + nx * k * 0.25)), int(round(y + ny * k * 0.25))
                if px[hx, hy] == col:
                    hits += 1
                    seen = True
                elif seen:                                    # 走出线段就停（别数到隔壁那条）
                    break
            if hits:
                vals.append(round(hits * 0.25, 2))
    if not vals:
        return None, None, 0
    vals.sort()
    med = vals[len(vals) // 2]
    mode = Counter(vals).most_common(1)[0][0]
    return mode, med, len(vals)


def legend_line(png, col, y):
    """图例里那根**水平**线段样例的厚度：竖直截距就是线宽本身。
    只认「左右各 25 px 也是同一色」的像素 —— 样例只有 70 px 长，±40 就永远落空
    （这个坑我第一版就踩了：量出来「没量到」，看着像图上没有那条线）。"""
    im = Image.open(png).convert("RGB")
    px = im.load()
    W, _ = im.size
    best = 0
    for x in range(0, W, 3):
        for yy in range(y - 16, y + 16):
            if px[x, yy] == col and px[x - 25, yy] == col and px[x + 25, yy] == col:
                h = 0
                while px[x, yy + h] == col:
                    h += 1
                best = max(best, h)
    return best or None


def main():
    if len(sys.argv) < 2:
        print(__doc__.strip().split("\n")[-3])
        return 2
    ok = False
    for png in sys.argv[1:]:
        if not os.path.exists(png):
            print("★ %s 不存在" % png)
            continue
        mode, med, n = run(png, CHART["seg"], LEGEND_Y)
        if mode is None:
            print("%-46s 线段实测线宽：**没量到**" % png)
            continue
        ok = True
        lg = legend_line(png, CHART["seg"], LEGEND_Y)
        print("%-46s 线段线宽 众数 %.2f / 中位 %.2f（%d 个样本）｜图例样例 %s px"
              % (png, mode, med, n, lg if lg else "没量到"))
    if not ok:
        print("★ 一张都没量到 —— 量不到 ≠ 通过")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
