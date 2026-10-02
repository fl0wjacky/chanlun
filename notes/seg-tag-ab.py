# -*- coding: utf-8 -*-
"""「线段线宽 7→5」＋「每个中枢都挂 [ZD, ZG] 价签」的改前 / 改后对照图。

裁剪窗口**不手填像素**，而是**从图上找色块**：价签的 30% 底是个只在价签里出现的混合色
（琥珀价签 = (84,71,40)、笔色价签 = (48,54,67)，都是 0.302×元素色 + 0.698×底色 算出来的），
在改后图里扫这个色，扫到哪就把窗口开在哪。色扫不到 → 直接非零退出（**窗口算错和"图上没变"
是两件事，不能混**）。改前图用**同一个窗口**裁，两边逐像素比，报改动占比。

    python3 notes/seg-tag-ab.py <改后.png> <改前.png> <输出.png>
退出码：0 = 写出对照图；1 = 自检不过（色扫不到 / 窗口里没变化 / 改前改后一样）。
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image, ImageDraw                                    # noqa: E402
from render.style import BG, TX, MU, F                              # noqa: E402

AMBER_TAG = (84, 71, 40)      # 30% 琥珀（线段中枢价签）压在页面底色上
PEN_TAG = (48, 54, 67)        # 30% 笔色（类中枢价签）压在页面底色上
CROP_W, CROP_H = 760, 300


def find_chip(im, col, w=CROP_W, h=CROP_H, min_ink=0.06):
    """在图上找 `col` **最密**、而且**不是一片空**的那一块 → 裁剪窗口（找不到返回 None）。

    两版教训都写在这儿，别再来第三遍：
      第一版「找到第一个色块就算」—— ② 开到了一片空荡的暗带，对照图看着像什么都没改。
      第二版「只看色块最密」—— ① 开到了图上空白的左上角（价签在那儿，但周围什么都没有），
        对照图里只剩一行字。**密 ≠ 有内容**：所以现在加了 `min_ink`，窗口里至少有 6% 的像素
        不是页面底色，才允许当候选。
    做法：行方向用前缀和扫一遍（快），选出 y 带；再在这条带里按列扫一遍选 x。
    """
    px = im.load()
    W, H = im.size
    S = 4
    chip_row = [0] * H
    ink_row = [0] * H
    cols = list(range(0, W, S))
    for y in range(0, H, S):
        c = k = 0
        for x in cols:
            p = px[x, y]
            if p == col:
                c += 1
            if p != BG:
                k += 1
        chip_row[y] = c
        ink_row[y] = k
    if sum(chip_row) < 20:
        return None

    def band_sums(hist, y0):
        return sum(hist[y0:y0 + h])

    best_y, best_n = None, -1
    for y0 in range(0, max(1, H - h), 10):
        if band_sums(ink_row, y0) < min_ink * (h // S) * len(cols):
            continue
        n = band_sums(chip_row, y0)
        if n > best_n:
            best_n, best_y = n, y0
    if best_y is None:
        return None
    chip_col = {}
    for y in range(best_y, min(H, best_y + h), S):
        for x in cols:
            if px[x, y] == col:
                chip_col[x] = chip_col.get(x, 0) + 1
    xs = sorted(chip_col)
    if not xs:
        return None
    xs_set = xs
    best_x, best_n = None, -1
    for x0 in range(0, max(1, W - w), 10):
        n = sum(v for k, v in chip_col.items() if x0 <= k < x0 + w)
        if n > best_n:
            best_n, best_x = n, x0
    return (best_x, best_y, min(W, best_x + w), min(H, best_y + h)), best_n


def seg_window():
    """① 的窗口：**由数据算**——取窗内第一个线段中枢，把它的整个框 + 挂在框顶的价签框进来。

    坐标照 render/chart_zec_segments.py 逐字抄（同一份数据、同一套 X/Y）。不手填像素是为了
    「窗口跟内容一起动」；但不手填也**不能保证它开对了地方**（这一格我前两版都开错了地方：
    一次开到空暗带、一次开到空白角落），所以下面还有一道硬自检：改后图在这个窗口里
    **必须真的数得到价签底色**，数不到就直接退出，不允许"看着差不多"。
    """
    import json as _json
    from config import data as _data, tick_of as _tick
    from core.analyze import analyze as _analyze
    bars = _json.load(open(_data("zec15.json"), encoding="utf-8"))
    r = _analyze(bars, tick=_tick("zec15.json"))
    done = [s for s in r["segs"] if not s.get("live")]
    a0 = r["segs"][-16:][0]["i0"]
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
    for z in r["seg_centers"]:
        a, b = done[z["PI0"]]["i0"], done[z["PI1"]]["i1"]
        if b > a0:
            x0, x1 = X(a), X(b)
            y0, y1 = Y(z["ZG"]) - 60, Y(z["ZD"]) + 40      # 上面留出价签那一行
            return (max(0, int(x0) - 40), max(0, int(y0)), min(2900, int(x0) + CROP_W), int(y1))
    return None


def main():
    if len(sys.argv) != 4:
        print(__doc__.strip().split("\n")[-3])
        return 2
    after_png, before_png, out_png = sys.argv[1:]
    im_a = Image.open(after_png).convert("RGB")
    im_b = Image.open(before_png).convert("RGB")
    f_t, f_n = F(30), F(24)
    d_title = ImageDraw.Draw(Image.new("RGB", (10, 10)))

    parts = []
    for label, col, note, rc in (
            ("① 线段中枢价签（统一成 30% 琥珀底 + 白字）＋ 线段线宽", AMBER_TAG, "价签底 = 30% 琥珀", seg_window()),
            ("② 类中枢价签（新加：每个类中枢都标 [ZD, ZG]）", PEN_TAG, "价签底 = 30% 笔色", None)):
        if label.startswith("②"):
            got = find_chip(im_a, col)
            if not got:
                print("★ 改后图里找不到 %s 的色块（%s）—— 窗口开不出来" % (label, col))
                return 1
            rc, nrows = got
        else:
            if rc is None:
                print("★ ① 由数据算不出窗口 —— 窗内没有线段中枢？")
                return 1
            nrows = sum(1 for x in range(rc[0], rc[2]) for y in range(rc[1], rc[3]) if im_a.getpixel((x, y)) == col)
            if nrows < 200:
                print("★ ① 的窗口里只有 %d 个价签底色像素（%s）—— 窗口跟内容脱节了" % (nrows, col))
                return 1
        ca, cb = im_a.crop(rc), im_b.crop(rc)
        diff = sum(1 for p, q in zip(ca.getdata(), cb.getdata()) if p != q)
        pct = diff * 100.0 / (ca.size[0] * ca.size[1])
        if pct < 1.0:
            print("★ %s：改前改后这个窗口只差 %.2f%% —— 对照图证不了东西" % (label, pct))
            return 1
        parts.append((label, note, rc, ca, cb, pct))
        print("%s ｜ 窗口 %s ｜ 窗口内价签底色像素 %d ｜ 改前改后差 %.1f%%" % (label, rc, nrows, pct))

    pad = 20
    title = "线段线宽 7→5 ＋ 每个中枢都挂 [ZD, ZG]：每格上面是改前（11a6d43）、下面是改后"
    heads = ["%s   %s   窗口 %s   改动像素 %.1f%%" % (lab, note, rc, pct)
             for lab, note, rc, _, _, pct in parts]
    # ★ 画布宽度得**把小标题也算进去**：第一版只按大标题和裁剪宽度算，结果两格小标题右半截
    #   被画布切掉了（PIL 不报错，直接裁）—— 自己出的对照图被裁字，丢人。
    width = max([c.size[0] for _, _, _, c, _, _ in parts]
                + [int(d_title.textlength(s, font=f_n)) for s in heads]
                + [int(d_title.textlength(title, font=f_t))]) + pad * 2
    height = 90 + sum(ca.size[1] * 2 + 100 for _, _, _, ca, _, _ in parts)
    canvas = Image.new("RGB", (width, height), BG)
    d = ImageDraw.Draw(canvas)
    d.text((pad, 20), title, font=f_t, fill=TX)
    y = 80
    for (label, note, rc, ca, cb, pct), head in zip(parts, heads):
        d.text((pad, y), head, font=f_n, fill=TX)
        d.text((pad, y + 32), "改前 11a6d43", font=f_n, fill=MU)
        canvas.paste(cb, (pad, y + 62))
        yy = y + 62 + cb.size[1] + 8
        d.text((pad, yy), "改后 本支", font=f_n, fill=MU)
        canvas.paste(ca, (pad, yy + 30))
        y = yy + 30 + ca.size[1] + 24
    canvas.save(out_png)
    print("写出 %s %s" % (out_png, canvas.size))
    return 0


if __name__ == "__main__":
    sys.exit(main())
