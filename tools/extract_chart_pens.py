#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 TradingView 截图里把「笔」的折线顶点提取出来。

这是 chart_annotate.py 的上游：截图 → 本脚本 → data/annot_pens.json → 标注图。

原理：CHANLUN 3.0 的笔折线用固定颜色 (84,120,246)，中枢边框是
(68,119,237)、分型三角是 (68,150,130)/(223,72,76)，色值不同。
所以按**精确色值**取掩码，逐列取最长连通段的中点，再用 RDP 简化成顶点。
（泛匹配「蓝色」会把中枢边框和虚线短划一起捞进来，顶点里全是毛刺。）
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from PIL import Image
from config import data, out, SCREENSHOT
from render.style import IND_PEN

SRC = SCREENSHOT   # 用户上传的截图
DST = data("annot_pens.json")
PEN_COLOR = IND_PEN            # 笔折线（CHANLUN 3.0 原色）
TOL = 16                       # 色值容差
RDP_EPS = 14                   # 简化容差（像素）
Y_LIMIT = 1000                 # 只取价格区，排除底部工具栏


def rdp(p, eps):
    """Ramer–Douglas–Peucker 折线简化。"""
    if len(p) < 3:
        return p
    (x1, y1), (x2, y2) = p[0], p[-1]
    dmax, idx = 0, 0
    for i in range(1, len(p) - 1):
        x0, y0 = p[i]
        num = abs((y2 - y1) * x0 - (x2 - x1) * y0 + x2 * y1 - y2 * x1)
        den = ((y2 - y1) ** 2 + (x2 - x1) ** 2) ** 0.5 or 1
        d = num / den
        if d > dmax:
            dmax, idx = d, i
    if dmax > eps:
        return rdp(p[:idx + 1], eps)[:-1] + rdp(p[idx:], eps)
    return [p[0], p[-1]]


def extract(src=SRC):
    a = np.array(Image.open(src).convert("RGB")).astype(int)
    R, G, B = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    mask = (abs(R - PEN_COLOR[0]) < TOL) & \
           (abs(G - PEN_COLOR[1]) < TOL) & \
           (abs(B - PEN_COLOR[2]) < TOL)
    mask[Y_LIMIT:, :] = False
    pts = []
    for x in range(90, 2240):
        col = np.nonzero(mask[:, x])[0]
        if len(col) == 0:
            continue
        segs, s, p = [], col[0], col[0]
        for y in col[1:]:
            if y - p <= 3:
                p = y
            else:
                segs.append((s, p)); s = p = y
        segs.append((s, p))
        segs.sort(key=lambda t: -(t[1] - t[0]))     # 取最长的一段（避开短线毛刺）
        s, e = segs[0]
        pts.append((x, int((s + e) / 2)))
    return [[x, y] for x, y in rdp(pts, RDP_EPS)]


if __name__ == "__main__":
    v = extract()
    json.dump(v, open(DST, "w"))
    print("提取到 %d 个笔转折点 → %s" % (len(v), DST))
