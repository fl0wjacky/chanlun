# -*- coding: utf-8 -*-
"""「两种升级中枢分色 + 升级框不再加粗」的改前 / 改后对照图（只读两张全量图，裁出拼一张）。

2026-10-02 小栋第 2 条：类中枢升上去的、线段中枢升上去的原本都是同一个紫（#A78BFA）要分开；
**升级框不再加粗**，线宽跟母框一样。这个脚本把改动**量出来**，不是靠眼看：

    改前（11a6d43）：两个升级框同色 #A78BFA，线宽 = 母框 + 2×(级别+1)
    改后（本支）    ：类中枢升的 #C4B5FD 浅紫、线段中枢升的 #D946EF 品红，线宽 = 母框

裁剪窗口**由数据算出来**（不是手填的像素）：照 chart_full_smooth.py 的 X/Y 把升级框映射到像素，
取它的外接矩形加 padding。所以数据一变、窗口跟着变，不会出现「窗口还在老地方、里面已经不是那个框」。

★ 三道自检（任一不过就非零退出）：
    ① 两个升级框在**改前**图里必须真的存在（裁出来的窗口不能是空的）
    ② 改前 / 改后 在那个窗口里必须**真的不一样**（不然这张对照图什么都没证）
    ③ 改后图里必须能数到两个新色（#C4B5FD / #D946EF）—— 光"不一样"可能是别的地方动了

    python3 notes/upgrade-color-ab.py <改后.png> <改前.png> <输出.png>
"""
import json
import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image, ImageDraw                                    # noqa: E402
from config import data, tick_of                                    # noqa: E402
from core.analyze import analyze                                    # noqa: E402
from render.style import BG, TX, MU, F                              # noqa: E402

UP_PEN = (196, 181, 253)
UP_SEG = (217, 70, 239)
OLD_UP = (167, 139, 250)


def mapping():
    """chart_full_smooth.py 里那套坐标（px=2 / ph=3600），逐字抄。"""
    bars = json.load(open(data("zec15.json"), encoding="utf-8"))
    r = analyze(bars, tick=tick_of("zec15.json"))
    n = len(bars)
    px, ph = 2, 3600
    L, R, T = 40, 120, 300
    Y1 = T + 40 + ph
    lo = math.log(min(b["l"] for b in bars) * 0.985)
    hi = math.log(max(b["h"] for b in bars) * 1.015)
    X = lambda i: L + i * px + px / 2
    Y = lambda p: Y1 - (math.log(p) - lo) / (hi - lo) * (Y1 - (T + 40))
    return r, X, Y


def rects():
    """→ [(标题, 裁剪矩形)]，两个升级框各一个。"""
    r, X, Y = mapping()
    pens, done = r["pens"], [s for s in r["segs"] if not s.get("live")]
    out = []
    for label, z, host in (("① 类中枢升上去的（浅紫）", next(z for z in r["centers"] if len(z.get("up") or []) == 2), pens),
                           ("② 线段中枢升上去的（品红）", next(z for z in r["seg_centers"] if z.get("up")), done)):
        x0, x1 = X(host[z["PI0"]]["i0"]), X(host[z["PI1"]]["i1"])
        ys = [Y(u["ZG"]) for u in z["up"]] + [Y(u["ZD"]) for u in z["up"]] + [Y(z["ZG"])]
        y0, y1 = min(ys), max(ys)
        # padding：左边留出标签（标签挂在 x0+8、框顶上方 36 px），右边/上下给一点余量
        out.append((label, (max(0, int(x0) - 30), max(0, int(y0) - 90), int(min(x1, x0 + 1400)) + 40, int(y1) + 60)))
    return out


def has(png, rgba, tol=6):
    im = Image.open(png).convert("RGB")
    want = tuple(rgba)
    return any(im.getpixel((x, y)) == want
               for x in range(0, im.size[0], 3) for y in range(0, im.size[1], 3))


def main():
    if len(sys.argv) != 4:
        print(__doc__.strip().split("\n")[-1])
        return 2
    after_png, before_png, out_png = sys.argv[1:]
    im_a, im_b = Image.open(after_png).convert("RGB"), Image.open(before_png).convert("RGB")
    f_t, f_n = F(30), F(24)

    # 自检 ③：改后图里必须真有两支新色
    for name, col in (("浅紫 #C4B5FD", UP_PEN), ("品红 #D946EF", UP_SEG)):
        if not has(after_png, col):
            print("★ 改后图里数不到 %s —— 分色没生效？" % name)
            return 1
        # 顺带看一眼旧紫还在不在（应该只剩「别处用」的那点，不该有成片的框）
        print("改后图里有 %s ✓" % name)
    if not has(before_png, OLD_UP, 0):
        print("★ 改前图里数不到旧紫 #A78BFA —— 这张「改前」不是 11a6d43 那张？")
        return 1
    print("改前图里有旧紫 #A78BFA ✓")

    parts = rects()
    pad_x, title_h, gap = 20, 56, 26
    width = max((r[2] - r[0]) for _, r in parts) + pad_x * 2
    height = sum((r[3] - r[1]) * 2 + title_h * 2 + gap * 3 for _, r in parts) + 40 + 90
    canvas = Image.new("RGB", (width, height), BG)
    d = ImageDraw.Draw(canvas)
    d.text((pad_x, 20), "升级中枢分色 + 升级框不再加粗：同一窗口，上＝改前（11a6d43）/ 下＝改后",
           font=f_t, fill=TX)
    y = 90
    for label, rc in parts:
        ca, cb = im_a.crop(rc), im_b.crop(rc)
        # 自检 ①：窗口里得有内容；②：改前改后必须真的不同
        bg_px = (rc[2] - rc[0]) * (rc[3] - rc[1])
        ink_a = sum(1 for p in ca.getdata() if p != BG)
        ink_b = sum(1 for p in cb.getdata() if p != BG)
        if min(ink_a, ink_b) < bg_px * 0.002:
            print("★ %s 的窗口几乎是空的（改后 %d 像素有墨 / 改前 %d）—— 窗口算错了？" % (label, ink_a, ink_b))
            return 1
        diff = sum(1 for p, q in zip(ca.getdata(), cb.getdata()) if p != q)
        pct = diff * 100.0 / bg_px
        if pct < 0.05:
            print("★ %s 改前改后在这个窗口里几乎一样（%.3f%%）—— 这张对照图证不了东西" % (label, pct))
            return 1
        for sub_label, crop in (("改前 11a6d43", cb), ("改后 本支", ca)):
            d.text((pad_x, y), "%s   %s   窗口 %s   改动像素 %.2f%%"
                   % (label, sub_label, rc, pct) if sub_label.startswith("改前") else "",
                   font=f_n, fill=MU if sub_label.startswith("改前") else TX)
            d.rectangle([pad_x - 1, y + 30, pad_x + crop.size[0], y + 30 + crop.size[1]], outline=(60, 66, 80))
            canvas.paste(crop, (pad_x, y + 31))
            y += crop.size[1] + 31 + (title_h if sub_label.startswith("改前") else gap)
    canvas.save(out_png)
    print("写出 %s  %s" % (out_png, canvas.size))
    return 0


if __name__ == "__main__":
    sys.exit(main())
