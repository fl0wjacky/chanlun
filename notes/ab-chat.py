# -*- coding: utf-8 -*-
"""把两张 A/B 对照图**拆成四张单格小图**，压到聊天附件能过的尺寸。

为什么要拆：整张对照图 1365×1390 压到 ≤94 KB（`cumora reply --bytes-b64` 一个实参的墙）要降到
q=56 的 JPEG，字号小的地方就糊了 —— 小栋要判断的恰恰是「这个紫跟那个紫分不分得开」。
拆成单格后**原生分辨率**下每张只有 100 KB 上下，几乎不用压。窗口仍然**从数据算**
（复用 seg-tag-ab 的 seg_window/find_chip 和 upgrade-color-ab 的 rects），不手填像素。

    python3 notes/ab-chat.py <输出目录>
每格自带一道自检：改前改后必须真的不同，否则非零退出。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image, ImageDraw                                            # noqa: E402
from render.style import BG, TX, MU, F                                      # noqa: E402

# ★ 文件名里的连字符让它们不能直接 import（`seg-tag-ab.py`）—— 用 importlib 按路径加载。
#   顺带说一句：这两支脚本 import 的时候**不干活**（只有 if __name__ 才跑），所以能当模块用。
import importlib.util                                                       # noqa: E402


def _load(name):
    here = os.path.dirname(os.path.abspath(__file__))
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), os.path.join(here, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


S = _load("seg-tag-ab")
U = _load("upgrade-color-ab")

TARGET = 94 * 1024          # 一个实参的墙（base64 涨 4/3，实参上限 128 KiB）


def compose(after_png, before_png, rc, head, out):
    ia = Image.open(after_png).convert("RGB")
    ib = Image.open(before_png).convert("RGB")
    ca, cb = ia.crop(rc), ib.crop(rc)
    diff = sum(1 for p, q in zip(ca.getdata(), cb.getdata()) if p != q)
    pct = diff * 100.0 / (ca.size[0] * ca.size[1])
    if pct < 1.0:
        print("★ %s 改前改后只差 %.2f%% —— 不算对照" % (out, pct))
        return None
    f_n, f_h = F(22), F(26)
    c = Image.new("RGB", (ca.size[0] + 40, ca.size[1] * 2 + 176), BG)
    d = ImageDraw.Draw(c)
    d.text((20, 16), head, font=f_h, fill=TX)
    d.text((20, 56), "改前 11a6d43", font=f_n, fill=MU)
    c.paste(cb, (20, 88))
    y = 88 + cb.size[1] + 20
    d.text((20, y), "改后 本支   窗口 %s   改动像素 %.1f%%" % (rc, pct), font=f_n, fill=TX)
    c.paste(ca, (20, y + 32))
    # ★ 尺寸怎么定：先试 PNG 原生（无损，最清楚），不行再 JPEG。
    #   PNG 在这类图上**出乎意料地差** —— K 线那一片本来就碎，LANCZOS 一缩又造出几万种过渡色
    #   （实测 481×387 竟然有 27929 种颜色 / 156 KB），PNG 的无损反而成了负担。
    #   所以退到 JPEG，但要**先保尺寸再降质量**：字比噪点重要。
    out_png = out
    picked = None
    for scale in (1.0, 0.9, 0.8, 0.72, 0.64):
        im = c if scale == 1.0 else c.resize((int(c.size[0] * scale), int(c.size[1] * scale)), Image.LANCZOS)
        if scale == 1.0:
            im.save(out_png, optimize=True)
            if os.path.getsize(out_png) <= TARGET:
                picked = (out_png, im.size, scale, None)
                break
        for q in (88, 80, 72, 64):
            jpg = out.replace(".png", ".jpg")
            im.save(jpg, quality=q, optimize=True, subsampling=0)
            if os.path.getsize(jpg) <= TARGET:
                picked = (jpg, im.size, scale, q)
                break
        if picked:
            break
    if not picked:
        print("★ %s 压不到 %d KB" % (out, TARGET // 1024))
        return None
    path, size, scale, q = picked
    if path != out_png and os.path.exists(out_png):
        os.remove(out_png)
    n = os.path.getsize(path)
    print("%-44s %s  缩放 %.2f%s  %.1f KB  （窗口内改动 %.1f%%）"
          % (os.path.basename(path), size, scale, "" if q is None else " JPEG q%d" % q, n / 1024, pct))
    return path


def main():
    if len(sys.argv) != 2:
        print(__doc__.strip().split("\n")[-1])
        return 2
    outdir = sys.argv[1]
    duan_a = "out/zec15_duan.png"
    duan_b = "../../../chanlun-before/out/zec15_duan.png"
    full_a = "out/zec15_full_smooth.png"
    full_b = "../../../chanlun-before/out/zec15_full_smooth.png"
    if not all(os.path.exists(p) for p in (duan_a, duan_b, full_a, full_b)):
        print("★ 少一张源图：%s" % [p for p in (duan_a, duan_b, full_a, full_b) if not os.path.exists(p)])
        return 1

    jobs = [
        ("① 线段线宽 7→5（沿法线实测 6.75 → 5.50 px）", duan_a, duan_b, S.seg_window()),
        ("② 类中枢新增价签 [ZD, ZG]（原来一个都不标）", duan_a, duan_b, S.find_chip(Image.open(duan_a).convert("RGB"), S.PEN_TAG)[0]),
        ("③ 类中枢升上去的：#%02X%02X%02X 淡紫（原来跟线段中枢升的同一个紫）" % U.UP_PEN, full_a, full_b, None),
        ("④ 线段中枢升上去的：品红 #D946EF ＋ 升级框不再加粗", full_a, full_b, None),
    ]
    up = U.rects()
    jobs[2] = (jobs[2][0], full_a, full_b, up[0][1])
    jobs[3] = (jobs[3][0], full_a, full_b, up[1][1])

    ok = 0
    for i, (head, a, b, rc) in enumerate(jobs, 1):
        if rc is None:
            print("★ 第 %d 格的窗口没算出来" % i)
            continue
        if compose(a, b, rc, head, os.path.join(outdir, "ab-chat-%d.png" % i)):
            ok += 1
    return 0 if ok == 4 else 1


if __name__ == "__main__":
    sys.exit(main())
