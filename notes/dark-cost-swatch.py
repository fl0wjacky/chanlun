# -*- coding: utf-8 -*-
"""深底那三支压暗，是「变差」还是「还是够用」—— 用眼睛能拍的图说一遍。

2026-10-02 浅色支合进 main（c70896a）之后，唯一还悬着的是：段 / 类升级 / 买 三色被压暗，
深色底上从 10.66 / 9.69 / 8.55 掉到 5.90 / 5.94 / 5.92。数我报过了，但**数不能代替看**：
小栋要拍 A（留着）/ B（改回亮色），他要看的正是「两种底、两种色值摆在一起」。

所以这是一张**试色板**，不是行情图：3 行被改过的色 × 4 格（深底旧 / 深底新 / 白底旧 / 白底新），
每格：底是**真实的图底色**、笔画是**真实的线宽 / 真实的不透明度**（都从 render/style.py 现读），
格子里写实测对比度。最后一行 卖 #FF5656 是**对照组** —— 它没动过，用它给「正常」定个样。

跑法：`python3 notes/dark-cost-swatch.py`  → `notes/dark-cost-swatch.png`（纯算＋画，不渲染行情）
退出码：0 ＝ 图跟 style.py 的现值对得上；1 ＝ 对不上（有人又改了色，这板过期了，得重画）。
★ 板上的字**不要写 markdown 的星号**：PIL 不认，会原样画出来。判词就写「过」「不过」。
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image, ImageDraw                                          # noqa: E402
from render.style import F                                               # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "dark-cost-swatch.png")
OUT_CHAT = os.path.join(HERE, "dark-cost-swatch-chat.png")   # 量化版：贴聊天用（128 KiB 的附件墙）

# 「改前」的三支 —— 属于历史状态，不跟着代码走，所以只能是字面量（同 notes/upgrade-color-ab.py）。
OLD = {"seg": (242, 193, 78), "up_pen": (196, 181, 253), "buy": (0, 205, 125)}
# 现值自检用：改完这三支该是什么。对不上说明有人又动了色，这板就不再是「现在」。
EXPECT = {"seg": (196, 137, 1), "up_pen": (153, 141, 197), "buy": (0, 170, 104)}

INK_DARK = (234, 238, 246)      # 深底上的字
INK_LIGHT = (24, 28, 38)        # 白底上的字
# ★ 深底取 TradingView 的 #131722（小栋看的那块屏的底），跟卡上、notes/theme-contrast.py 同一个输入。
#   我们渲染器自己的深底是 #101218，比它再暗一档 ⇒ 同一支色在那边只会**更亮**
#   （段 6.17 / 类升级 6.21 / 买 6.20），不会更差。两个底都过，方向一致。
BG_TV_DARK = (19, 23, 34)
BAR = 3.0                       # 图形元素的判据
BAR_TEXT = 4.5                  # 正文（价签上的字）的判据

# ★ 线宽 / 填充这些是 int，不是 tuple —— 过滤时别只放序列，否则取 seg_w 会 KeyError。
CODE = ("import render.style as s, json;"
        "print(json.dumps({'BG': list(s.BG)[:3], 'CHART':"
        " {k: (list(v) if isinstance(v, (list, tuple)) else v)"
        "  for k, v in s.CHART.items() if isinstance(v, (list, tuple, int, float))}}))")


def read_style():
    """起子进程读 style.py：两种主题的底色在 import 期就分岔了，只能各读一次。"""
    out = {}
    for theme in ("dark", "light"):
        env = dict(os.environ, CHANLUN_THEME=theme, PYTHONPATH=ROOT)
        r = subprocess.run([sys.executable, "-c", CODE], env=env, cwd=ROOT,
                           capture_output=True, text=True)
        if r.returncode:
            raise SystemExit("★ 读 %s 主题的 style.py 失败：%s" % (theme, r.stderr.strip()))
        out[theme] = json.loads(r.stdout)
    return out


def lum(c):
    """WCAG 相对亮度：sRGB 线性化后加权。"""
    def f(u):
        u /= 255.0
        return u / 12.92 if u <= 0.03928 else ((u + 0.055) / 1.055) ** 2.4
    r, g, b = (f(x) for x in c[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def over(fg, bg, a):
    """fg 以不透明度 a（0~255）压在 bg 上。★ 逐通道在 sRGB 里插值 —— PIL 的 alpha 合成就是这么干的。"""
    return tuple(round((a / 255.0) * fg[i] + (1 - a / 255.0) * bg[i]) for i in range(3))


def verdict(v, bar):
    """★ 不要在这里用 markdown 的 `**`：这个串会**进这张图**，PIL 原样画出来。"""
    return "过" if v >= bar else "不过"


def main():
    st = read_style()
    C = st["dark"]["CHART"]
    for k, want in EXPECT.items():
        got = tuple(C[k][:3])
        if got != want:
            raise SystemExit("★ %s 现值 %s ≠ 自检期望 %s —— style.py 又动过，这板过期了，重画。"
                             % (k, got, want))

    bg_d = BG_TV_DARK
    bg_l = tuple(st["light"]["BG"])
    seg_w, pc_w, up_fill = C["seg_w"], C["pc_w"], C["up_fill"]

    # 行：标签、旧值、新值、怎么画。控制行「卖」旧＝新（它没动过）。
    rows = [
        ("段（线段本体）", OLD["seg"], tuple(C["seg"][:3]), "line"),
        ("类中枢升一级的框", OLD["up_pen"], tuple(C["up_pen"][:3]), "box"),
        ("买点标记", OLD["buy"], tuple(C["buy"][:3]), "mark"),
        ("卖（对照：没动过）", (255, 86, 86), (255, 86, 86), "mark"),
    ]
    cols = [("深底 · 旧", bg_d, 0), ("深底 · 新", bg_d, 1),
            ("白底 · 旧", bg_l, 0), ("白底 · 新", bg_l, 1)]

    W, M, LBL = 1620, 36, 168
    CW = (W - 2 * M - LBL - 3 * 14) // 4
    CH_ = 168
    TOP = 172          # ★ 不能再小：副标题第三行在 y≈100，行高 24 ⇒ 表头落在 TOP-34 才不会压上去
    H = TOP + 52 + len(rows) * (CH_ + 46) + 96

    im = Image.new("RGB", (W, H), (14, 17, 23))
    d = ImageDraw.Draw(im)
    f_t, f_h, f_l, f_n, f_s = F(34), F(21), F(19), F(24), F(16)

    d.text((M, 26), "深底压暗：小栋要拍的 A / B，两种底摆在一起看", font=f_t, fill=(240, 244, 252))
    d.text((M, 76), "每格底＝真实的图底色，笔画＝真实线宽与不透明度（全部现读 render/style.py）。"
                    "判据 3:1（图形元素）。基线：笔 深 5.08 / 白 3.53（它没动过）。",
           font=f_s, fill=(150, 158, 178))
    d.text((M, 100), "「不改就白底看不见、改了深底没那么晃眼」——这一屏就是这句的全部内容。",
           font=f_s, fill=(150, 158, 178))

    for j, (head, _, _) in enumerate(cols):
        x = M + LBL + j * (CW + 14)
        d.text((x + 6, TOP - 34), head, font=f_h, fill=(200, 208, 224))

    for i, (label, old_c, new_c, kind) in enumerate(rows):
        y = TOP + 44 + i * (CH_ + 46)
        d.text((M, y + CH_ // 2 - 14), label, font=f_l, fill=(224, 230, 240))
        for j, (_, bg, which) in enumerate(cols):
            col = new_c if which else old_c
            x = M + LBL + j * (CW + 14)
            d.rectangle([x, y, x + CW, y + CH_], fill=bg)
            draw_sample(d, kind, col, bg, x, y, CW, CH_, seg_w, pc_w, up_fill,
                        INK_DARK if bg == bg_d else INK_LIGHT)
            v = contrast(col, bg)
            ink = INK_DARK if bg == bg_d else INK_LIGHT
            d.text((x + 14, y + CH_ - 34), "%s  %.2f:1  %s" % (hexs(col), v, verdict(v, BAR)),
                   font=f_n, fill=ink)
        # 深底旧→新 的落差，写在两格中间那一行字的右边，免得要两块屏对着看
        y2 = y + CH_ + 8
        d.text((M + LBL + 8, y2),
               "深底 %.2f → %.2f" % (contrast(old_c, bg_d), contrast(new_c, bg_d)),
               font=f_n, fill=(214, 190, 120) if old_c != new_c else (130, 138, 156))

    d.text((M, H - 62),
           "深底掉的那部分（10.7/9.7/8.6 → 5.9）是换来的：白底从 1.7~2.1（看不见）到 3.0 过线。"
           "要拿回深底原样＝三行改回旧值，一句话的事。",
           font=f_s, fill=(150, 158, 178))
    d.text((M, H - 36),
           "深底＝TradingView #131722（与小栋那块屏一致；渲染器自己的深底 #101218 更暗，同色在那边更亮：6.17 / 6.21 / 6.20）"
           " · 尺子 notes/dark-cost-swatch.py · 数字口径 notes/theme-contrast.py",
           font=f_s, fill=(110, 118, 136))

    im.save(OUT)
    print("→ %s  %d×%d  %d KiB" % (os.path.relpath(OUT, ROOT), im.width, im.height,
                                   os.path.getsize(OUT) // 1024))

    # 贴聊天的那份：整板就几十个纯色 ＋ 字的抗锯齿，量化到 128 色肉眼看不出、体积砍掉一半多
    # （128 KiB 的附件墙 ⇒ 要 ≲98 KiB；**不缩尺寸**，因为缩过的字比量化的字更难看）。
    q = im.quantize(colors=128, method=Image.MEDIANCUT)
    q.save(OUT_CHAT, optimize=True)
    kb = os.path.getsize(OUT_CHAT) / 1024.0
    print("→ %s  %d×%d  %.1f KiB%s"
          % (os.path.relpath(OUT_CHAT, ROOT), q.width, q.height, kb,
             "" if kb <= 98 else "   ★ 超附件墙，要再降"))
    for label, old_c, new_c, _ in rows:
        print("  %-18s 深底 %5.2f → %5.2f   白底 %5.2f → %5.2f"
              % (label, contrast(old_c, bg_d), contrast(new_c, bg_d),
                 contrast(old_c, bg_l), contrast(new_c, bg_l)))
    return 0


def hexs(c):
    return "#%02X%02X%02X" % tuple(c[:3])


def draw_sample(d, kind, col, bg, x, y, w, h, seg_w, pc_w, up_fill, ink):
    """按真实画法画一格：线＝真线宽，框＝真线宽＋真填充，标记＝实心三角＋空心圆。"""
    cx, cy = x + 14, y + h // 2 - 16
    if kind == "line":
        pts = [(cx, cy + 26), (cx + 90, cy - 6), (cx + 190, cy + 22), (cx + 300, cy - 10)]
        d.line(pts, fill=tuple(col[:3]), width=seg_w, joint="curve")
    elif kind == "box":
        box = [cx, cy - 34, cx + 300, cy + 40]
        d.rectangle(box, fill=over(col, bg, up_fill), outline=tuple(col[:3]), width=pc_w)
    elif kind == "mark":
        d.polygon([(cx + 40, cy + 34), (cx + 16, cy - 18), (cx + 64, cy - 18)], fill=tuple(col[:3]))
        d.ellipse([cx + 110, cy - 22, cx + 166, cy + 34], outline=tuple(col[:3]), width=5)
        d.ellipse([cx + 210, cy - 22, cx + 266, cy + 34], fill=tuple(col[:3]))


if __name__ == "__main__":
    sys.exit(main())
