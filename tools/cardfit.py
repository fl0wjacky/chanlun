#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""卡片版式体检：**量每一处真的画上去的文字**，看它有没有越界。

为什么不用「渲染成 PNG 再看一眼」当判据：那是代理量——你在缩略图上看到的是
像素，判的却是「这行字放不放得下」，中间隔着一层缩放和一双眼睛。
这里的做法是换定义域（和 fontcheck 包 getmask 同一个套路）：把 ImageDraw.text
包起来，问它**每一次到底被要求把哪串字画在哪个坐标**，再拿字体自己的字宽去量。

口径（与卡片自身一致）：
  横向  右边距  W − 56    （页脚分隔线、各段标题都守这条）
        越界    right > W （真的画到画布外，会被裁掉）
  纵向  出画布  ink_bottom > H            —— 真的画到画布下沿外，会被裁掉（**不容忍**，1px 也是被裁）
        出面板  ink_bottom > 面板底 + 1   —— 字还在画布内，但下半截画在面板外面
                                            （容忍 1px：那 1px 还在面板 width=2 的描边里，报了是噪音）
anchor 按 PIL 语义处理：l 起点 / m 中点 / r 终点。

**纵向量的是墨迹、不是 bbox**：两者差几个像素，而"有没有戳出面板"由墨迹决定。
（2026-09-30 实测：`model_dissent` 那一处 bbox 底说 +6px，墨迹说 +7px。**量法不同数不同。**）

**「合计 N 处」必须连着字体（名字 + sha256）读** —— 同一个仓库同一个提交，两支字体会给出两个数，
而且差的不是零头：Droid `97320619` 合计 3 处 / Noto `2c76254f` 合计 16 处，
多出来的 13 处是**同一个机制**（卡片的小标签框按「字号+内边距」定高，不是逐个字量的；
Noto 的汉字在同一字号下墨迹低 3~4px，就戳出标签底框）。所以下面 main() 会先把字体打出来。
**换字体是发卡前的指定项，不是无关项。**
"""
import os, sys, importlib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image, ImageDraw

MARGIN = 56
PANEL_TOL = 1        # 「出面板」容忍 1px：那 1px 还在面板描边（width=2）里，报了就是噪音
RECORDS = []          # 文字：(xy, text, font, anchor)
PANELS = []           # 面板矩形：[x0, y0, x1, y1]
_ORIG = ImageDraw.ImageDraw.text
_ORIG_RR = ImageDraw.ImageDraw.rounded_rectangle
_ORIG_RECT = ImageDraw.ImageDraw.rectangle


def _spy(self, xy, text, *a, **kw):
    RECORDS.append((xy, text, kw.get("font"), kw.get("anchor") or "la"))
    return _ORIG(self, xy, text, *a, **kw)


def _mk_rect_spy(orig):
    """面板探针：**只记不判**。哪个矩形算"面板"不在这里定 —— 判断时按
    「包含这行文字顶部的最内层矩形」取，卡片自己的画法说了算。"""
    def spy(self, xy, *a, **kw):
        try:
            x0, y0, x1, y1 = xy
        except (TypeError, ValueError):
            return orig(self, xy, *a, **kw)
        PANELS.append((x0, y0, x1, y1))
        return orig(self, xy, *a, **kw)
    return spy


def _install():
    """装上探针。**这一步漏了的话，下面的检查会一边倒地报「全部 OK」**——
    本文件第一版就是这样：`_spy` 写好了、忘了赋值，14 张卡全报「文字 0 处」。
    所以装上之后立刻自检一次（见 main 开头），不靠人记得。"""
    ImageDraw.ImageDraw.text = _spy
    ImageDraw.ImageDraw.rounded_rectangle = _mk_rect_spy(_ORIG_RR)
    ImageDraw.ImageDraw.rectangle = _mk_rect_spy(_ORIG_RECT)


def _selftest():
    """探针自检：拿一张 1×1 的图真画一次字，探针必须看得见；看不见就抛。"""
    RECORDS.clear(); PANELS.clear()
    im = Image.new("RGB", (8, 8))
    d = ImageDraw.Draw(im)
    d.text((0, 0), "x")
    d.rounded_rectangle([0, 0, 4, 4], 1)
    got, gotp = len(RECORDS), len(PANELS)
    RECORDS.clear(); PANELS.clear()
    if got != 1:
        raise RuntimeError("版式探针没装上：画了 1 次字、探针只看到 %d 次" % got)
    if gotp != 1:
        raise RuntimeError("面板探针没装上：画了 1 个圆角矩形、探针只看到 %d 个" % gotp)

    # 墨迹口径自证：`_ink_rows` 报的行范围，必须和「真画一遍再逐行找像素」一模一样。
    # 这条是 2026-09-30 立的，代价是一次真错：我当时在**整张已画好的卡**上扫墨迹行来量某一行字，
    # 于是把**面板自己的描边**算成了这行字的墨迹，报出 +11px —— 真值是 +7，多算 4px，
    # 而这个错数被三个人引用过。**工具报的数，它自己得能复算**；不能复算的数，改的是别人的代码。
    from render.style import F as _F
    _f = _F(22)
    for s, x0, y0 in (("三卖", 10, 6), ("[102,108]", 10, 6), ("Ag", 10, 6)):
        canvas = Image.new("L", (260, 60), 0)
        ImageDraw.Draw(canvas).text((x0, y0), s, font=_f, fill=255)
        rows = [y for y in range(60) if any(canvas.getpixel((x, y)) for x in range(260))]
        ink = _ink_rows(s, _f)
        got = (y0 + ink[0], y0 + ink[1]) if ink else None
        want = (rows[0], rows[-1]) if rows else None
        if got != want:
            raise RuntimeError("墨迹口径自证不过：%r 真画一遍是 %s..%s，_ink_rows 报 %s"
                               % (s, want and want[0], want and want[1], got))
    RECORDS.clear(); PANELS.clear()


def _font_id():
    """正在量的那支字体：**全路径** + sha256 前 8 位。

    路径给全，是因为 `CHANLUN_FONT` 只认全路径（给文件名 config 直接 FileNotFoundError）——
    报数时只印文件名，别人照着复现会先撞一个和结论无关的错。
    sha256 是因为**同名两支字体是有的**（见 memory 里那两支 Droid：`97320619` 有 ✔✗✘、
    `23920155` 两样都缺），只写文件名认不出是哪一支。
    """
    import hashlib
    from config import FONT as _FP
    try:
        h = hashlib.sha256(open(_FP, "rb").read()).hexdigest()[:8]
    except OSError as e:
        return "%s（读不出 sha256：%s）" % (_FP, e)
    return "%s  sha256:%s" % (_FP, h)


def _extent(x, text, font, anchor):
    """返回 (left, right)。多行按最宽的一行算。"""
    w = max((font.getlength(ln) for ln in str(text).split("\n")), default=0)
    h = anchor[0] if anchor else "l"
    if h == "m":
        return x - w / 2, x + w / 2
    if h == "r":
        return x - w, x
    return x, x + w


def _ink_rows(text, font):
    """文字**墨迹**的行范围（相对文字原点）；空串/空白返回 None。

    不是 bbox：bbox 是字体给的行盒，墨迹是真正落下去的那几行像素。两者差几像素，
    而"有没有戳出面板"由墨迹决定 —— 拿 bbox 判会把"差 3px 就戳出来"读成"没戳出来"。
    多行文本按整块算（mask 的每一行，行间空白不计）。
    """
    s = str(text)
    if not s.strip():
        return None
    bb = font.getbbox(s)
    m = font.getmask(s)
    w, h = m.size
    if not w or not h:
        return None
    b = bytes(m)
    rows = [y for y in range(h) if any(b[y * w:(y + 1) * w])]
    if not rows:
        return None
    return bb[1] + rows[0], bb[1] + rows[-1]


def _panel_of(x, ink_top):
    """包含 (x, ink_top) 的**最内层**矩形；没有就返回 None。

    "最内层"= 面积最小那个：卡片会在面板里再叠高亮块，取包含它的最小矩形才不会
    把内层高亮当成面板底。
    """
    best = None
    for x0, y0, x1, y1 in PANELS:
        if x0 <= x <= x1 and y0 <= ink_top <= y1:
            if best is None or (x1 - x0) * (y1 - y0) < (best[2] - best[0]) * (best[3] - best[1]):
                best = (x0, y0, x1, y1)
    return best


def check(mod, name):
    RECORDS.clear(); PANELS.clear()
    im = mod.build()
    W, H = im.width, im.height
    bad = []
    for xy, text, font, anchor in RECORDS:
        if font is None or not str(text).strip():
            continue
        left, right = _extent(xy[0], text, font, anchor)
        if right > W or left < 0:
            bad.append((right - W, "越界", xy, text, left, right))
        elif right > W - MARGIN:
            bad.append((right - (W - MARGIN), "破边距", xy, text, left, right))
        ink = _ink_rows(text, font)
        if ink is None:
            continue
        ink_top, ink_bot = xy[1] + ink[0], xy[1] + ink[1]
        if ink_bot > H:
            bad.append((ink_bot - H, "纵向出画布", xy, text, ink_top, ink_bot))
            continue
        p = _panel_of(xy[0], ink_top)
        if p is not None and ink_bot > p[3] + PANEL_TOL:
            bad.append((ink_bot - p[3], "出面板", xy, text, ink_top, ink_bot))
    return W, H, len(RECORDS), sorted(bad, reverse=True)


def main():
    _install()
    _selftest()
    print("[版式体检] 字体 %s" % _font_id())
    from cards.build_all import CARDS
    extra = [("model_dissent", "M1 机会模型"), ("level_recursion", "M2 级别递归")]
    total = 0
    for name, title in [(n, t) for n, t in CARDS] + extra:
        try:
            mod = importlib.import_module("cards." + name)
        except Exception as e:
            print("%-22s 跳过：%s: %s" % (name, type(e).__name__, e))
            continue
        W, H, n, bad = check(mod, name)
        total += len(bad)
        head = "%-22s W=%-5d H=%-5d 文字 %3d 处  %s" % (
            name, W, H, n, "OK" if not bad else "★ %d 处" % len(bad))
        print(head)
        for over, kind, xy, text, a, b in bad:
            t = str(text).replace("\n", "⏎")
            where = ("x=%-4d→%-6.0f" % (xy[0], b) if kind in ("越界", "破边距")
                     else "y=%-5.0f→%-6.0f" % (a, b))
            print("    %-8s %+6.0fpx  %-14s %s" % (kind, over, where, t[:70]))
    print("\n合计 %d 处" % total)
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
