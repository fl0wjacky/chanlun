# -*- coding: utf-8 -*-
"""六个元素色 × 两种底（白 #FFFFFF / 深 #131722）的对比度 —— 线条和价签两件事一起量。

为什么要有这把尺（2026-10-02）
    上午小栋那张截图是**白底**，而价签「30% 同色底 ＋ 白字」是**只按深底挑的**：
    30% 的琥珀压在白底上几乎还是白，白字对比度掉到 1.2~1.5:1 —— 等于没有字。
    「白底上读得清」不能只靠我一句话，得有个能复跑的尺。就是它。

量三件事
    ① 线条：六色直接画在底上（线是**图形元素**，判据 AA 非文本 3:1）
    ② 价签：底（30% 同色 / 实底）× 字（白 / 黑）四种写法，在两种底上（字是**正文**，判据 4.5:1）
    ③ 色块与底的边界：价签底相对图底色（没边界＝价签糊在图里）

★ 一个色在两种底上**最多**能同时拿到 4.08:1（亮度 ≈0.207 处两边等分）：白底要它往下暗、
  深底要它往上亮，天生对拉 ⇒「两底都过 3:1」的亮度带是 [0.1375, 0.30]。
  六色里段 / 类升级 / 买 三色原本在带外。**修法不写死在这张表里，由脚本推**（见 fix_line）：
     · 段 #F2C14E 白底 1.68 → **#C48901**（同色相里彩度拉满的那个解）白 3.03 / 深 5.90
     · 类升级 #C4B5FD 白底 1.85 → **#998DC5**（等比压暗，保 0.28 的淡紫彩度）白 3.01 / 深 5.94
     · 买 #00CD7D 白底 2.09 → **#00AA68**（等比压暗）白 3.02 / 深 5.92
  这三支 2026-10-02 由 iris 定，两边（style.py / chanlun.pine）同值。代价：深底上段 10.66→5.90、
  买 8.55→5.92、类升级 9.69→5.94 —— 仍高于**笔**在深底上一直以来的 5.08（小栋认可的那个亮度），
  所以「深底不能变差」按这条基线算成立；要拿回深底那口亮金，就是这三行改回去，一句话的事。

底和元素色**从 render/style.py 现读**（不同主题各起一个子进程），不手抄 —— 尺子跟着代码走。
六色里谁掉到 3:1 以下，表①下面自动给出「同色相压到刚好过 3:1」的最近解，不需要人来配值。

    python3 notes/theme-contrast.py
退出码：0 = 价签找到了在**两种底**上都过 4.5 的写法；1 = 没有（那这条得重挑）。
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image, ImageDraw                                            # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "theme-contrast.png")

# ① 背景：白底（小栋的截图）／TradingView 深底 #131722，这两个是**输入**（不是我们挑的）
BG_WHITE = (255, 255, 255)
BG_TV_DARK = (19, 23, 34)

# ② 元素色：从 style.py 读，见 read_style()
SIX = [
    ("笔", "pen"),
    ("段", "seg"),
    ("类升级", "up_pen"),
    ("段升级", "up_seg"),
    ("买", "buy"),
    ("卖", "sell"),
]
def fix_line(c, bar=3.0):
    """一个色在白底上不到 `bar` 时，给两条同色相的修法（不改色相是硬要求：色相是「谁是谁」的那条通道）。

    A 等比压暗：sRGB 逐通道乘 k。k 保色相、保 HSV 的 S，是最小改动 —— 但彩度低的色压出来会发闷。
    B 彩度拉满：同色相里 S 最高的那个、白底刚好过 bar 的解。金/红/绿这类本来就是高彩度的色
      压出来更精神；浅紫这种「本来就是淡的」色，拉满会变成另一个色（试过：#3401FF，深底只有 2.2:1），
      所以 B 只在**它自己在深底上仍过 bar** 时才给。
    → (A, k) / (B,) / None（已经过关）
    """
    import colorsys
    if contrast(c, BG_WHITE) >= bar:
        return None
    h, s, v = colorsys.rgb_to_hsv(*[x / 255 for x in c])

    lo, hi = 0.0, 1.0
    for _ in range(40):                    # 压暗：对比度随 k 单调降（k↓ ⇒ 白底对比↑）
        k = (lo + hi) / 2
        if contrast(tuple(round(x * k) for x in c), BG_WHITE) >= bar:
            hi = k
        else:
            lo = k
    a = tuple(round(x * hi) for x in c)

    b = None
    for vi in range(1000, -1, -1):         # 亮到暗扫一遍，取第一个「S 拉满且过关」的
        for si in range(1000, -1, -1):
            r, g, bb = colorsys.hsv_to_rgb(h, si / 1000, vi / 1000)
            cc = (round(r * 255), round(g * 255), round(bb * 255))
            if contrast(cc, BG_WHITE) >= bar:
                if contrast(cc, BG_TV_DARK) >= bar and si / 1000 > s + 1e-9:
                    b = cc
                break
        if b:
            break
    return a, hi, b


def read_style():
    """起子进程读 style.py：不同主题的底在 import 期就分岔了，只能各读一次。"""
    code = ("import render.style as s, json;"
            "print(json.dumps({'BG': s.BG, 'CHART': {k: list(v) for k, v in s.CHART.items()"
            " if isinstance(v, (list, tuple))}}))")
    out = {}
    for theme in ("dark", "light"):
        env = dict(os.environ, CHANLUN_THEME=theme, PYTHONPATH=ROOT)
        r = subprocess.run([sys.executable, "-c", code], env=env, cwd=ROOT,
                           capture_output=True, text=True)
        if r.returncode:
            sys.exit("读 style.py 失败（%s）：%s" % (theme, r.stderr.strip()))
        out[theme] = eval(r.stdout)                                        # noqa: S307
    return out


def lum(c):
    s = [v / 255 for v in c[:3]]
    lin = [(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4) for v in s]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a, b):
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def over(fg, bg, a):
    """fg 以不透明度 a 压在 bg 上。★ 逐通道在 **sRGB** 里插值 —— PIL 的 alpha 合成就是这么干的
    （不是线性光里插值）。照着实现，尺子量出来的才等于屏幕上看到的那个色。"""
    return tuple(round(a * fg[i] + (1 - a) * bg[i]) for i in range(3))


def hexs(c):
    return "#%02X%02X%02X" % c[:3]


def verdict(v, bar):
    """★ 不要在这里用 markdown 的 `**`：这个串会进终端表，也会**进试色表那张图** ——
    图上不会渲染 markdown，只会原样印出两个星号。第一版就是这么漏的。"""
    return "过" if v >= bar else "不过"


def main():
    st = read_style()
    dark_render = tuple(st["dark"]["BG"])
    light_render = tuple(st["light"]["BG"])
    chart = st["dark"]["CHART"]
    cols = {k: tuple(chart[k][:3]) for _, k in SIX}

    print("六个元素色（读自 render/style.py 的 CHART；两边同值，pine 的 input 默认也是这几个）")
    print("  名称     色值       白 #FFFFFF        深 #131722")
    for name, k in SIX:
        row = ""
        for bg in (BG_WHITE, BG_TV_DARK):
            v = contrast(cols[k], bg)
            row += "   %.2f:1 %-6s" % (v, verdict(v, 3.0))
        print("  %-8s %s%s" % (name, hexs(cols[k]), row))
    print("  （另两个底是本仓渲染出来的：深 %s / 白 %s —— 跟上面两列同一量级，量了不另列）"
          % (hexs(dark_render), hexs(light_render)))

    print()
    print("① 线条判据 3:1 —— 谁不过就给最近的同色相修法")
    fails = [(name, k) for name, k in SIX if contrast(cols[k], BG_WHITE) < 3.0
             or contrast(cols[k], BG_TV_DARK) < 3.0]
    if not fails:
        print("  六色在**白底和深底上都过 3:1**，没有要压的。")
    for name, k in fails:
        c = cols[k]
        for bn, bg in (("白", BG_WHITE), ("深", BG_TV_DARK)):
            if contrast(c, bg) < 3.0:
                print("  %s 在%s底 %.2f:1 不过" % (name, bn, contrast(c, bg)))
        f = fix_line(c)
        if f:
            a, kk, b = f
            print("       A 等比压暗 ×%.3f → %s   白 %.2f / 深 %.2f"
                  % (kk, hexs(a), contrast(a, BG_WHITE), contrast(a, BG_TV_DARK)))
            if b:
                print("       B 彩度拉满      → %s   白 %.2f / 深 %.2f"
                      % (hexs(b), contrast(b, BG_WHITE), contrast(b, BG_TV_DARK)))
            else:
                print("       B 彩度拉满       → 不适用（拉满后深底反而掉到 3:1 以下）")

    print()
    print("② 价签四种写法（字是正文，判据 4.5:1）—— 每格是六色里的**最差~最好**")
    forms = [("30% 同色底 ＋ 白字", 0.30, (255, 255, 255)),
             ("30% 同色底 ＋ 黑字", 0.30, (0, 0, 0)),
             ("实底 ＋ 白字", 1.0, (255, 255, 255)),
             ("实底 ＋ 黑字", 1.0, (0, 0, 0))]
    for label, a, ink in forms:
        line = "  %-18s" % label
        okboth = True
        for bn, bg in (("白", BG_WHITE), ("深", BG_TV_DARK)):
            vs = sorted(contrast(over(cols[k], bg, a), ink) for _, k in SIX)
            worst, best = vs[0], vs[-1]
            line += "  %s底 %.2f~%.2f:1 %s " % (bn, worst, best, verdict(worst, 4.5))
            okboth &= worst >= 4.5
        print(line + ("  ← 两底都过" if okboth else ""))
    print("      （黑字那一行是「底越实、六色越挤在一起」，实底的六支只差 %.1f:1；"
          "白字那行反过来 —— 按深底挑的，白底全废）"
          % (max(contrast(cols[k], BG_WHITE) for _, k in SIX)
             - min(contrast(cols[k], BG_WHITE) for _, k in SIX)))

    print()
    print("②b 白字为什么救不回来：琥珀任何一种不透明度下，白字的最优值")
    for a in (0.30, 0.60, 0.85, 1.00):
        bgc = over(cols["seg"], BG_WHITE, a)
        print("     不透明度 %.2f → 底 %s，白字 %.2f:1" % (a, hexs(bgc), contrast(bgc, (255, 255, 255))))
    print("     ⇒ 底越实只会越接近琥珀本身，白字对琥珀的**上限**就是 %.2f:1。"
          % contrast(cols["seg"], (255, 255, 255)))
    print("       要白字过关只能**换色**（把琥珀压到亮度 0.183 以下），不是调不透明度。")

    print()
    print("③ 价签底 vs 图底色（价签得有边界，不然糊在图里；判据 3:1）")
    for bn, bg in (("白", BG_WHITE), ("深", BG_TV_DARK)):
        worst = min((contrast(cols[k], bg), name) for name, k in SIX)
        print("  %s底  最差一支 %s %.2f:1 %s" % (bn, worst[1], worst[0], verdict(worst[0], 3.0)))

    sheet(st, cols)
    print()
    print("试色表 → notes/theme-contrast.png")

    allok = all(contrast(over(cols[k], bg, 1.0), (0, 0, 0)) >= 4.5
                for _, k in SIX for bg in (BG_WHITE, BG_TV_DARK))
    print("结论：实底 ＋ 黑字在两种底上都过 4.5:1 → %s" % ("是" if allok else "**否**"))
    return 0 if allok else 1


def sheet(st, cols):
    """左半深底、右半白底，同一批笔画并排 —— 一眼看两种主题，不靠切图。"""
    from render.style import F

    W, H = 1560, 700          # 高度按内容给：多出来的是空白，不是留白
    HALF = W // 2
    im = Image.new("RGB", (W, H), BG_TV_DARK)
    d = ImageDraw.Draw(im)
    d.rectangle([HALF, 0, W, H], fill=BG_WHITE)
    f_t, f_n, f_s = F(30), F(21), F(17)

    for side, (bg, ink, mut, head) in enumerate((
            (BG_TV_DARK, (234, 238, 246), (142, 150, 168), "深底 #131722"),
            (BG_WHITE, (24, 28, 38), (104, 112, 128), "白底 #FFFFFF（小栋的截图）"))):
        x0 = side * HALF + 34
        d.text((x0, 26), head, font=f_t, fill=ink)

        y = 92
        d.text((x0, y), "① 线条（判据 3:1）", font=f_n, fill=mut)
        y += 34
        for name, k in SIX:
            c = cols[k]
            d.line([x0, y, x0 + 150, y], fill=c, width=5)
            d.ellipse([x0 + 162, y - 7, x0 + 176, y + 7], fill=c)
            v = contrast(c, bg)
            d.text((x0 + 192, y - 12), "%-5s %s  %.2f:1 %s"
                   % (name, hexs(c), v, verdict(v, 3.0)), font=f_s, fill=mut)
            y += 40

        y += 14
        d.line([x0, y, x0 + HALF - 68, y], fill=mut)
        y += 18
        d.text((x0, y), "② 价签写法（判据 4.5:1，取六色最差一支）", font=f_n, fill=mut)
        y += 36
        for label, a, ik in (("30% 底+白字", 0.30, (255, 255, 255)),
                             ("30% 底+黑字", 0.30, (0, 0, 0)),
                             ("实底+白字", 1.0, (255, 255, 255)),
                             ("实底+黑字", 1.0, (0, 0, 0))):
            worst, worst_c = 99.0, None
            for _, k in SIX:
                v = contrast(over(cols[k], bg, a), ik)
                if v < worst:
                    worst, worst_c = v, over(cols[k], bg, a)
            chip = worst_c
            d.rounded_rectangle([x0, y, x0 + 200, y + 32], 5, fill=chip)
            d.text((x0 + 9, y + 6), "[1104.08, 1257.06]", font=f_s, fill=ik)
            d.text((x0 + 214, y + 6), "%-13s %.2f:1 %s"
                   % (label, worst, verdict(worst, 4.5)), font=f_s, fill=mut)
            y += 42

    im.save(OUT)


if __name__ == "__main__":
    sys.exit(main())
