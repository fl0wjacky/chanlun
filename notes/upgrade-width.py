# -*- coding: utf-8 -*-
"""从图上量**升级框的边框粗细**：改前（11a6d43）加粗 vs 改后（本支）跟母框一样粗。

为什么单开一支：小栋第 2 条是两句话 ——「两种升级中枢分色」和「升级框不再加粗」。分色好证（数颜色
就有），**"不再加粗"光看图看不出来**（差 4 px，缩过的对照图里根本没差）。所以直接量像素：

    框的上下边是**水平线**。在框内选一列竖着扫，数「属于这个颜色」的连续像素 = 边框粗细。

★ 两个坑，第一版都踩了，写在这儿：
  ① **不能精确比色**。框线是带 alpha 混到底色 / 填充上的，实测 (138,142,162) 而不是配置里的
     (122,137,166)、升级框是 (190,172,221) 而不是 (196,181,253)。所以要按**色距**认，不能 `==`。
  ② **升级框和母框的上下边可能贴在一起**（同一个 x 范围，ZG 差得少时两条边只差 2 px，糊成一坨）。
     所以量升级框时**只挑两者分得开的中枢**；母框的粗细则另取**没有升级框的中枢**来量 —— 干净。

    python3 notes/upgrade-width.py <改后.png> <改前.png>
退出码：0 = 两族都量到、且改后升级框粗细 == 母框；1 = 量不到 或 改后仍比母框粗。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import importlib.util                                                       # noqa: E402
from statistics import median                                               # noqa: E402

from PIL import Image                                                       # noqa: E402


def _load(name):
    here = os.path.dirname(os.path.abspath(__file__))
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), os.path.join(here, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


U = _load("upgrade-color-ab")
OLD_UP = U.OLD_UP
TOL = 70.0


def near(p, col, tol=TOL):
    return sum((a - b) ** 2 for a, b in zip(p, col)) <= tol * tol


def run_at(px, x, y, col, reach=16):
    """含 y 这一行的、`col` 的连续段长度（向上向下各走到色距超限为止）。"""
    if not near(px[x, y], col):
        return 0
    n = 1
    yy = y - 1
    while n < reach and near(px[x, yy], col):
        n += 1
        yy -= 1
    yy = y + 1
    while n < reach and near(px[x, yy], col):
        n += 1
        yy += 1
    return n


def sample(im, x0, x1, y, col):
    """框内取几列（避开左端标签那一带）：每列量一次，返回中位数。"""
    px = im.load()
    vals = []
    for f in (0.35, 0.5, 0.65, 0.8):
        x = int(x0 + (x1 - x0) * f)
        n = run_at(px, x, int(round(y)), col)
        if n:
            vals.append(n)
    return median(vals) if vals else 0


def main():
    if len(sys.argv) != 3:
        print(__doc__.strip().split("\n")[-3])
        return 2
    after_png, before_png = sys.argv[1:]
    for p in (after_png, before_png):
        if not os.path.exists(p):
            print("★ %s 不存在" % p)
            return 1
    im_a, im_b = Image.open(after_png).convert("RGB"), Image.open(before_png).convert("RGB")

    r, X, Y = U.mapping()
    pens, done = r["pens"], [s for s in r["segs"] if not s.get("live")]
    families = (
        ("类中枢一族", r["centers"], pens, (122, 137, 166), [U.UP_PEN], "笔色"),
        ("线段中枢一族", r["seg_centers"], done, (242, 193, 78), [U.UP_SEG], "段色"),
    )
    bad = 0
    for name, pool, host, pcol, newcols, pname in families:
        # 母框：**没有升级框**的中枢，边缘干干净净
        plain = [z for z in pool if not z.get("up")]
        pv = []
        for z in plain[:40]:
            x0, x1 = X(host[z["PI0"]]["i0"]), X(host[z["PI1"]]["i1"])
            if x1 - x0 < 150:
                continue
            v = sample(im_a, x0, x1, Y(z["ZG"]), pcol)
            if v:
                pv.append(v)
        if not pv:
            print("★ %s：母框粗细一个都没量到（%s）" % (name, pname))
            bad += 1
            continue
        parent = median(pv)

        # 升级框：只挑升级框上边与母框上边**分得开**的（>25 px），不然两条边糊在一起
        gaps = []
        for z in pool:
            for u in (z.get("up") or []):
                if abs(Y(u["ZG"]) - Y(z["ZG"])) < 25:
                    continue
                x0, x1 = X(host[z["PI0"]]["i0"]), X(host[z["PI1"]]["i1"])
                if x1 - x0 < 150:
                    continue
                gaps.append((z, u, x0, x1))
        if not gaps:
            print("★ %s：找不到「升级框和母框分得开」的中枢 —— 这把尺量不了" % name)
            bad += 1
            continue

        before_w = [sample(im_b, x0, x1, Y(u["ZG"]), OLD_UP) for _, u, x0, x1 in gaps]
        before_w = [v for v in before_w if v]
        print("%s：母框（%s %s）%d px，量在 %d 个无升级框的中枢上"
              % (name, pname, pcol, parent, len(pv)))
        print("  升级框 改前（旧紫 #A78BFA）：%s px  量在 %d 个中枢上"
              % (median(before_w) if before_w else "没量到", len(before_w)))
        if not before_w:
            bad += 1
        per_col = []
        for c in newcols:
            vals = [sample(im_a, x0, x1, Y(u["ZG"]), c) for _, u, x0, x1 in gaps]
            vals = [v for v in vals if v]
            if not vals:
                print("  ★ 改后升级框（%s）没量到" % (c,))
                bad += 1
                continue
            m = median(vals)
            per_col.append(m)
            flag = "✓ 与母框同粗" if m == parent else "★ 比母框粗 %.0f px" % (m - parent)
            print("  升级框 改后（%s %s）：%d px  %s" % (c, "浅紫" if c == U.UP_PEN else "品红", m, flag))
            if m != parent:
                bad += 1
        if before_w and per_col and median(before_w) <= median(per_col):
            print("  ★ 改前的升级框并没有更粗（%s vs %s）—— 「不再加粗」这条改动没被证到"
                  % (median(before_w), median(per_col)))
            bad += 1
    if bad:
        print("★ %d 处没过" % bad)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
