# -*- coding: utf-8 -*-
"""绘图公共层：字体、配色、坐标映射、基础图元。

所有出图脚本（charts/ 与 cards/）都从这里取，不要各自复制一份。
"""
import json
from PIL import Image, ImageDraw, ImageFont

from config import FONT as FONT_PATH, _NOTDEF_CHARS, _notdef_mask

# ---- 配色 ----
BG    = (16, 18, 24)      # 页面底色
CARD  = (25, 28, 36)      # 卡片底
PANEL = (19, 22, 29)      # 内嵌面板底
LINE  = (52, 57, 70)      # 分割线
TX    = (234, 238, 246)   # 正文
MU    = (142, 150, 168)   # 次要文字
DIM   = (100, 108, 128)   # 弱化文字
BL    = (86, 142, 255)    # 主线蓝（笔 / 中枢）
LB    = (120, 170, 255)   # 亮蓝
GR    = (0, 205, 125)     # 绿（底 / 成立）
RD    = (255, 86, 86)     # 红（顶 / 否定）
AM    = (255, 190, 60)    # 琥珀（方向 / 强调）
CY    = (64, 200, 220)    # 青（第三根 / 辅助）
GY    = (150, 158, 178)   # 灰（定方向的那根）
UP    = (38, 166, 154)    # 阳线
DN    = (239, 83, 80)     # 阴线

# ---- 截图标注配色：画在浅底 TradingView 截图上，要深、要饱和，所以和上面深底那套分开 ----
# ---- 真实数据全量图的配色 / 线宽（render/full_common.py 用）----
# 规则：笔与它构成的类中枢同色，线段与它构成的线段中枢同色；满 9 段的高一级别中枢用同色加粗框。
# 想改就在项目根目录放一个 chart_style.json 覆盖其中任意几项，例如 {"pen": [120, 120, 255], "seg": [255, 150, 0]}。
CHART = dict(
    pen=BL, seg=AM,              # 笔 / 类中枢的颜色；线段 / 线段中枢的颜色
    pen_w=2, seg_w=7,            # 笔、线段的线宽
    pc_w=2, sc_w=4,              # 类中枢、线段中枢的框线宽
    pc_fill=22, sc_fill=34,      # 框内填充的不透明度（0–255）
    up_w=4,                      # 高一级别框：在所属中枢框线宽之上再加粗多少（满 27 段再加一倍）
    sig_seg=True, sig_pen=True,  # 买卖点：线段中枢层（大号实心）/ 类中枢层（小号空心，标「·笔」）
    sig_pending=True,            # 待确认的买卖点也画（文字加「?」、更淡）
    sig_measure="macd",          # 一买一卖的背驰力度："macd"（MACD 柱面积）/ "slope"（斜率）
    buy=GR, sell=RD,             # 买点 / 卖点颜色
)


def _load_chart_style():
    import json, os
    f = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chart_style.json")
    if os.path.exists(f):
        for k, v in json.load(open(f, encoding="utf-8")).items():
            if k not in CHART:
                raise KeyError("chart_style.json 里的 %s 不认识，可用：%s" % (k, ", ".join(CHART)))
            CHART[k] = tuple(v) if isinstance(v, list) else v


_load_chart_style()

SH_BLUE   = (30, 90, 210)         # 同级别中枢框（可用三笔复算）/ ZG 线
SH_DEEP   = (20, 70, 190)         # 延伸段虚线与括注
SH_ORANGE = (230, 150, 20)        # 另一级别中枢框
SH_RED    = (214, 40, 40)         # 另一级别中枢框
SH_OK     = (0, 150, 70)          # 判定：成立
SH_BAD    = (200, 40, 40)         # 判定：不成立
SH_WAIT   = (220, 150, 0)         # 判定：待确认
SH_UNK    = (130, 130, 140)       # 判定：存疑
SH_INK    = (20, 20, 20)          # 白底标签上的字 / 描边
SH_PAPER  = (255, 255, 255)       # 标签底
SH_BLUE_FILL   = (120, 170, 255, 55)   # 中枢框半透明填充
SH_ORANGE_FILL = (255, 214, 140, 60)
SH_RED_FILL    = (255, 120, 120, 60)
SH_EXT_FILL    = (190, 210, 245, 45)   # 延伸段填充（比成立段更淡）

# ---- CHANLUN 3.0 指标在截图里的原色：图例色块要和截图对得上，extract_chart_pens 也按它取掩码 ----
IND_PEN = (84, 120, 246)          # 笔折线
IND_TOP = (223, 72, 76)           # 顶分型三角
IND_NOW = (68, 150, 130)          # 底分型三角 / 当前价格线


def F(size):
    return ImageFont.truetype(FONT_PATH, size)


# ---- 字体覆盖：字体文件在 ≠ 字体画得出这些字 ----
#
# config.py 只查 os.path.exists。字体能加载、能返回 ImageFont 句柄，但里面没有这个字形时，
# PIL **不报错**，静默画一个 .notdef 方框——selfcheck 照样「总违规 0 → 全部通过」。
# README 那句「STHeiti / 冬青黑缺 ✓ ✗ ₁₂₃（显示成方框）」说的就是这一格，只是没进代码。
#
# 判据不另走加载路径：**拿 F() 的句柄**，文件路径从句柄上读（.path），所以验的和画的是
# 同一个对象、同一个文件——不存在「检查器读到另一个 ttf」的分叉。
#
# .notdef 的指纹用**位图字节**，不能用尺寸：DejaVu 下 .notdef 是 (14,21)，而位图尺寸同为
# (14,21) 的真字形有 10 个（U+14A6、U+14AB…）。拿尺寸当指纹，这 10 个字会被误报成缺字
# ——那就成了「对正确的活报错」。4764 个真字形里，字节指纹误判 0 个。
# 基准取**三个**私用区码位取多数票，不是取一个——因为**字体可以映射私用区**。实测
# （`tools/fontcheck.py --selftest` 里现造一支把 U+E000 指到 'B' 字形的字体）：
#   单探针时 `.notdef` 的基准变成 'B' 的墨迹 ⇒ 真缺的「中」渲成真 .notdef、跟它比**不相等**
#   ⇒ 判成"有"，而且落进 conflict 而不是 missing —— **读 missing 的人看到的是一张干净白名单**
#   （@bram-9d29 量到的形状；夹具与两支字体的复算见 `card-8ac04844-0ca`）
# 三个码位里两个相同 → 那个就是 .notdef（另有一个被映射了）；三个互不相同 → **判不了**，
# 抛异常，不猜。清单直接取 config.py 那份（它挑字体用的是同一套）：**两份私用区清单是最容易
# 被改一份忘一份的东西**，这个仓已经为"同一格两条判据分家"付过一次账。
#
# **实现也只有一份**：`.notdef` 的推断直接用 `config._notdef_mask`，本文件不再抄一套 ——
# `config.py` 与 `render/style.py` 是同一形状的两个调用点，改法各写一套就会各漏一个角
# （@atlas-791f 的 `card-5ddb51d2-003` 记的就是 config 那一份在「私用区→空白字形」上的缺口；
#   一份实现意味着那个缺口一修、两处同时好，也意味着**它没修之前两处同时带病**）。
_NOTDEF_PROBES = _NOTDEF_CHARS


def _cmap_codepoints(font_path):
    """字体自己声明的 Unicode 码位。没装 fontTools 就返回 None（降级成只看渲染）。"""
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        return None
    ft = TTFont(font_path, lazy=True)
    out = set()
    for t in ft["cmap"].tables:
        if t.isUnicode():
            out |= set(t.cmap.keys())
    return out


def glyph_gaps(text, font=None):
    """text 里**画不出来**的字。

    返回 (missing, conflict)，都按首次出现顺序去重：
      missing  —— 会画成 .notdef 方框的字
      conflict —— 两条判据结论不一致的字：cmap 说「有」而渲染是方框（或反之）。
                  这种字体单看哪一条都不可信，单独报出来给人看，不并进 missing。

    检测器先自检两道，任一不过**抛异常**，不返回「整串都缺」：一个对什么都说缺的检查，是另一种
    静默通过。
      ① .notdef 的基准挑得出来吗（三个私用区码位取多数票，挑不出就是判不了）
      ② 拿已知存在的 'A' 试一次：若 'A' 也判成 .notdef，说明这套判据在这份字体上失灵
    """
    font = font if font is not None else F(24)
    notdef = _notdef_mask(font)
    if notdef is None:
        raise RuntimeError("字形检测器失灵：%s 的私用区被映射得不止一个，挑不出 .notdef 基准，"
                           "缺字结论不可信" % getattr(font, "path", "?"))
    if bytes(font.getmask("A")) == notdef:
        raise RuntimeError("字形检测器失灵：%s 里连 'A' 都被判成 .notdef，缺字结论不可信"
                           % getattr(font, "path", "?"))
    cmap = _cmap_codepoints(font.path) if getattr(font, "path", None) else None

    missing, conflict = [], []
    for ch in dict.fromkeys(text):            # 去重、保序
        if ch.isspace() or ord(ch) < 0x20:
            continue
        by_render = bytes(font.getmask(ch)) == notdef
        by_cmap = (cmap is not None) and (ord(ch) not in cmap)
        if cmap is not None and by_render != by_cmap:
            conflict.append(ch)
        elif by_render:
            missing.append(ch)
    return missing, conflict


def load_bars(path):
    """读 K 线 json。"""
    return json.load(open(path, encoding="utf-8"))


class Mini:
    """价格 ↔ 像素 的双向映射，用于在一小块区域里画简图。"""

    def __init__(self, d, x0, y0, x1, y1, pmin, pmax):
        self.d, self.x0, self.y0, self.x1, self.y1 = d, x0, y0, x1, y1
        self.pmin, self.pmax = pmin, pmax

    def X(self, i, n):
        """第 i 个槽位（共 n 个）的横坐标。"""
        return self.x0 + (i + 0.5) / n * (self.x1 - self.x0)

    def Y(self, price):
        return self.y1 - (price - self.pmin) / (self.pmax - self.pmin) * (self.y1 - self.y0)


def dash(d, x0, x1, y, col, w=3, dash_len=11, gap=8):
    """画一条水平虚线。"""
    x = x0
    while x < x1:
        e = min(x + dash_len, x1)
        d.line([x, y, e, y], fill=col, width=w)
        x = e + gap


def dashed_line(d, p0, p1, fill, width=3, dash_len=16, gap=10):
    """任意角度的虚线。约定：未完成的笔 / 线段一律用它画（已完成的用实线）。"""
    (x0, y0), (x1, y1) = p0, p1
    L = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
    if L == 0:
        return
    ux, uy = (x1 - x0) / L, (y1 - y0) / L
    t = 0.0
    while t < L:
        e = min(t + dash_len, L)
        d.line([x0 + ux * t, y0 + uy * t, x0 + ux * e, y0 + uy * e], fill=fill, width=width)
        t = e + gap


def dashed_rect(d, box, outline, width=3, fill=None, dash_len=16, gap=10):
    """虚线框（仍在延续、未终结的中枢用它）。"""
    x0, y0, x1, y1 = box
    if fill:
        d.rectangle(box, fill=fill)
    for a, b in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
        dashed_line(d, a, b, outline, width, dash_len, gap)


def tri_up(d, x, y, col, s=11):
    d.polygon([(x, y - s), (x - s * 0.8, y + s * 0.7), (x + s * 0.8, y + s * 0.7)], fill=col)


def tri_dn(d, x, y, col, s=11):
    d.polygon([(x, y + s), (x - s * 0.8, y - s * 0.7), (x + s * 0.8, y - s * 0.7)], fill=col)


def candles(d, X, Y, bars, w=22, body=True):
    """画一组 K 线。bars 元素为 (open, high, low, close)。"""
    for i, (o, h, l, c) in enumerate(bars):
        x = X(i)
        col = UP if c >= o else DN
        d.line([x, Y(h), x, Y(l)], fill=col, width=max(2, int(w / 6)))
        if body:
            d.rectangle([x - w / 2, Y(max(o, c)), x + w / 2, Y(min(o, c))], fill=col)


def polyline(d, pts, col, w=5):
    for a, b in zip(pts, pts[1:]):
        d.line([a, b], fill=col, width=w)


def arrow_r(d, x0, x1, y, col, w=5, hs=15):
    d.line([x0, y, x1 - hs, y], fill=col, width=w)
    d.polygon([(x1, y), (x1 - hs, y - hs * 0.7), (x1 - hs, y + hs * 0.7)], fill=col)


def panel(d, x0, y0, x1, y1, radius=20, accent=None, alpha=0):
    """一块圆角面板。accent 给了就带同色半透明底 + 描边。"""
    if accent:
        d.rounded_rectangle([x0, y0, x1, y1], radius,
                            fill=accent + (alpha or 40,), outline=accent, width=3)
    else:
        d.rounded_rectangle([x0, y0, x1, y1], radius,
                            fill=PANEL, outline=LINE, width=2)


def chip(d, x, y, text, accent, font, pad_x=20, pad_y=10, text_col=None):
    """一个小圆角标签，返回它的宽度。"""
    w = d.textlength(text, font=font) + pad_x * 2
    h = font.size + pad_y * 2
    d.rounded_rectangle([x, y, x + w, y + h], 10, fill=accent + (46,), outline=accent, width=2)
    d.text((x + pad_x, y + pad_y - 2), text, font=font, fill=text_col or accent)
    return w
