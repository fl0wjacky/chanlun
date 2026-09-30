#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把全部概念卡画一遍：逐张调用各卡的 build()，单张存盘，再竖向拼成一张长图。

不再依赖先单独跑各卡、再从产物目录里 glob 这个做法 —— 顺序由 CARDS 决定，
漏跑、旧图残留都不会混进合集。
"""
import os, sys, importlib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PIL import Image
from config import out
from render.style import BG

W = 1400                  # 长图宽度（各卡同宽）

# 合集顺序 + PDF 目录标题 —— 唯一出处，tools/build_pdf.py 也从这里读
CARDS = [
    ("c01_containment",    "01 包含处理"),
    ("c02_fractal",        "02 分型"),
    ("c03_pen",            "03 笔"),
    ("c04_segment",        "04 线段"),
    ("c04plus_featureseq", "04b 特征序列（认图）"),
    ("c04c_fourcases",     "04c 线段结束的四种情况"),
    ("c04d_twoways",       "04d 两种走法：67 vs 71"),
    ("c05_center",         "05 中枢"),
    ("c06_trend",          "06 走势类型"),
    ("c07_level",          "07 级别"),
    ("c08_divergence",     "08 背驰"),
    ("c09_buypoints",      "09 三类买卖点"),
]


def card_modules():
    """按合集顺序返回 [(模块, 目录标题)]。只 import，不出图。"""
    return [(importlib.import_module("cards." + name), title) for name, title in CARDS]


def main():
    ims = []
    for mod, _ in card_modules():
        im = mod.build()
        im.save(out(mod.OUTNAME))
        print("  ", mod.OUTNAME, im.size)
        ims.append(im)
    tot = Image.new("RGB", (W, sum(i.height for i in ims)), BG)
    y = 0
    for i in ims:
        tot.paste(i, (0, y)); y += i.height
    tot.save(out("chanlun_cards_all.png"))
    print("合集", tot.size, len(ims), "张")


if __name__ == "__main__":
    main()
