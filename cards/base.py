# -*- coding: utf-8 -*-
"""概念卡公共层：卡片页框、要点列表、简笔图元。

卡片脚本只负责画什么，字体 / 配色 / 坐标映射 / 虚线 / 三角
这些「怎么画」统一由 render.style 提供，不要在这里再复制一份。
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from render.style import *            # noqa: F401,F403

W, H = 1400, 1180          # 默认卡片尺寸；个别卡片用 set_size() 覆盖
OUT = config.OUT + os.sep       # 卡片脚本用 OUT + "文件名"

f_b, f_n, f_p, f_t = F(24), F(23), F(27), F(20)


def set_size(w, h):
    """覆盖卡片尺寸。

    注意：head / foot 用的是本模块的 W/H，但卡片自己画图用的是
    它 import 进来的副本。所以卡片要么调 newcard()，要么写成
        W, H = set_size(1400, 2040)
    只写 set_size(...) 而不接返回值，卡片会停在默认的 1400x1180。
    """
    global W, H
    W, H = w, h
    return w, h


def cs(m, X, Y, bars, w=16):
    """在 Mini 上画一组 K 线。"""
    candles(m.d, X, Y, bars, w=w)


def zig(m, pts, col=BL, w=5):
    """按像素坐标连折线。"""
    d = m.d
    for a, b in zip(pts, pts[1:]):
        d.line([a, b], fill=col, width=w)


def zigp(m, pts, col=BL, w=5):
    """pts 为 (x像素, 价格)，自动把价格映射成 y。"""
    d = m.d
    q = [(x, m.Y(p)) for x, p in pts]
    for a, b in zip(q, q[1:]):
        d.line([a, b], fill=col, width=w)
    return q


def dot(d, x, y, col, r=11, txt=""):
    d.ellipse([x - r, y - r, x + r, y + r], fill=BG, outline=col, width=4)
    if txt:
        tw = d.textlength(txt, font=f_b)
        d.text((x - tw / 2, y - 25), txt, font=f_b, fill=col)


def head(d, no, name, oneliner):
    """卡片页眉：编号 + 名称 + 一句话定义。"""
    d.text((56, 34), no, font=F(38), fill=(70, 78, 96))
    d.text((132, 24), name, font=F(58), fill=TX)
    d.text((136, 104), oneliner, font=F(28), fill=MU)
    d.line([56, 168, W - 56, 168], fill=LINE, width=2)


def foot(d, src, trap):
    """卡片页脚：原文出处 + 最易踩的坑。"""
    d.line([56, H - 150, W - 56, H - 150], fill=LINE, width=2)
    d.text((56, H - 136), "原文", font=F(22), fill=(96, 104, 122))
    d.text((132, H - 136), src, font=F(24), fill=(168, 176, 192))
    d.text((56, H - 96), "陷阱", font=F(22), fill=(96, 104, 122))
    d.text((132, H - 96), trap, font=F(24), fill=AM)


def points(d, items, y0=828):
    """页脚上方的要点列表（左侧彩色小标签 + 右侧说明）。"""
    bw = max(d.textlength(k, font=f_n) for k, _ in items) + 40
    vx = 56 + bw + 24
    for i, (k, v) in enumerate(items):
        yy = y0 + i * 62
        d.rounded_rectangle([56, yy + 2, 56 + bw, yy + 46], 10, fill=BL + (52,))
        tw = d.textlength(k, font=f_n)
        d.text((56 + (bw - tw) / 2, yy + 8), k, font=f_n, fill=(190, 210, 255))
        d.text((vx, yy + 9), v, font=f_p, fill=TX)


def section(d, y0, y1, title, accent=AM, chip_dy=18):
    """整宽的分节面板 + 左上角标题标签。返回标签宽度（方便把副标题排在它右边）。"""
    d.rounded_rectangle([56, y0, W - 56, y1], 20, fill=PANEL, outline=LINE, width=2)
    return chip(d, 80, y0 + chip_dy, title, accent, f_p)


def callout(d, y0, y1, col, alpha=22):
    """整宽的强调框：同色半透明底 + 3px 描边（放结论 / 实测 / 警示）。"""
    d.rounded_rectangle([56, y0, W - 56, y1], 20, fill=col + (alpha,), outline=col, width=3)


def _ink_rows(text, font):
    """真画一遍，量这串字的墨迹上下沿（相对绘制原点）。

    不能用 textbbox：那个底带字体自带的 descent，比真墨迹低 1~3px，
    拿它摆字会把字摆得比实际需要的更高。墨迹才是"看得见的那个东西"。
    """
    im = Image.new("L", (600, 80), 0)
    ImageDraw.Draw(im).text((20, 30), text, font=font, fill=255)
    rows = [y for y in range(80) if any(im.getpixel((x, y)) for x in range(600))]
    return None if not rows else (rows[0] - 30, rows[-1] - 30)


def lchip(d, x, y, text, col, anchor="l"):
    """带底色的小标签 —— 压在线/框上也读得清。anchor="r" 时 x 是右端。

    框高是写死的 27px（y-4..y+23）—— 所以**字要按字体的墨迹在框里摆正**：
    原来字画在 y，墨迹底在 Droid 下到 y+24（比框底低 1px）、Noto 下到 y+27（低 4px），
    框没小，是字太靠下。按墨迹居中后，框的落点一个像素都不动 ⇒ 不会去压下面的线/框。
    """
    tw = d.textlength(text, font=f_t)
    bx = x if anchor == "l" else x - tw
    top, bot = y - 4, y + 23
    ty = y
    ink = _ink_rows(text, f_t)
    if ink:
        ty = top + (bot - top - (ink[1] - ink[0])) // 2 - ink[0]
    d.rounded_rectangle([bx - 7, top, bx + tw + 7, bot], 6, fill=CARD + (240,))
    d.text((bx, ty), text, font=f_t, fill=col)
    return tw


def newcard(no, name, oneliner, accent=BL, panel=True):
    """开一张空卡片，返回 (image, draw)。

    panel=True 时预画一块 [196, 800] 的默认面板；卡片自己用 section() 分节时
    传 panel=False，否则默认面板的边线会从各节之间的缝隙里露出来。
    """
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im, "RGBA")
    head(d, no, name, oneliner)
    if panel:
        d.rounded_rectangle([56, 196, W - 56, 800], 20, fill=PANEL, outline=LINE, width=2)
    return im, d
