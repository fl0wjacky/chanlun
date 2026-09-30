#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""卡片版式体检：**量每一处真的画上去的文字**，看它有没有越界。

为什么不用「渲染成 PNG 再看一眼」当判据：那是代理量——你在缩略图上看到的是
像素，判的却是「这行字放不放得下」，中间隔着一层缩放和一双眼睛。
这里的做法是换定义域（和 fontcheck 包 getmask 同一个套路）：把 ImageDraw.text
包起来，问它**每一次到底被要求把哪串字画在哪个坐标**，再拿字体自己的字宽去量。

口径（与卡片自身一致）：
  右边距   W − 56      （页脚分隔线、各段标题都守这条）
  越界     right > W   （真的画到画布外，会被裁掉）
anchor 按 PIL 语义处理：l 起点 / m 中点 / r 终点。
"""
import os, sys, importlib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image, ImageDraw

MARGIN = 56
RECORDS = []
_ORIG = ImageDraw.ImageDraw.text


def _spy(self, xy, text, *a, **kw):
    RECORDS.append((xy, text, kw.get("font"), kw.get("anchor") or "la"))
    return _ORIG(self, xy, text, *a, **kw)


def _install():
    """装上探针。**这一步漏了的话，下面的检查会一边倒地报「全部 OK」**——
    本文件第一版就是这样：`_spy` 写好了、忘了赋值，14 张卡全报「文字 0 处」。
    所以装上之后立刻自检一次（见 main 开头），不靠人记得。"""
    ImageDraw.ImageDraw.text = _spy


def _selftest():
    """探针自检：拿一张 1×1 的图真画一次字，探针必须看得见；看不见就抛。"""
    RECORDS.clear()
    im = Image.new("RGB", (8, 8))
    ImageDraw.Draw(im).text((0, 0), "x")
    got = len(RECORDS)
    RECORDS.clear()
    if got != 1:
        raise RuntimeError("版式探针没装上：画了 1 次字、探针只看到 %d 次" % got)


def _extent(x, text, font, anchor):
    """返回 (left, right)。多行按最宽的一行算。"""
    w = max((font.getlength(ln) for ln in str(text).split("\n")), default=0)
    h = anchor[0] if anchor else "l"
    if h == "m":
        return x - w / 2, x + w / 2
    if h == "r":
        return x - w, x
    return x, x + w


def check(mod, name):
    RECORDS.clear()
    im = mod.build()
    W = im.width
    bad = []
    for xy, text, font, anchor in RECORDS:
        if font is None or not str(text).strip():
            continue
        left, right = _extent(xy[0], text, font, anchor)
        if right > W or left < 0:
            bad.append((right - W, "越界", xy, text, left, right))
        elif right > W - MARGIN:
            bad.append((right - (W - MARGIN), "破边距", xy, text, left, right))
    return W, len(RECORDS), sorted(bad, reverse=True)


def main():
    _install()
    _selftest()
    from cards.build_all import CARDS
    extra = [("model_dissent", "M1 机会模型"), ("level_recursion", "M2 级别递归")]
    total = 0
    for name, title in [(n, t) for n, t in CARDS] + extra:
        try:
            mod = importlib.import_module("cards." + name)
        except Exception as e:
            print("%-22s 跳过：%s: %s" % (name, type(e).__name__, e))
            continue
        W, n, bad = check(mod, name)
        total += len(bad)
        head = "%-22s W=%-5d 文字 %3d 处  %s" % (
            name, W, n, "OK" if not bad else "★ %d 处越界/破边距" % len(bad))
        print(head)
        for over, kind, xy, text, left, right in bad:
            s = str(text).replace("\n", "⏎")
            print("    %s %+6.0fpx  x=%-4d→%-6.0f  %s" % (kind, over, xy[0], right, s[:78]))
    print("\n合计 %d 处" % total)
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
