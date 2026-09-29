#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把概念卡拼成一本手机版 PDF：每卡一页，页面比例随卡片。

顺序与目录标题取自 cards/build_all.CARDS；读的是已存盘的 PNG，所以先跑 build_all。
"""
import os, glob
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import out, FONT
from cards.build_all import card_modules

pdfmetrics.registerFont(TTFont("CN", FONT))

OUT = out("缠论概念卡_合集.pdf")
PW = 420.0                                    # 手机版宽（pt）

ORDER = [(mod.OUTNAME, title) for mod, title in card_modules()]    # [(PNG 文件名, 目录标题)]

c = canvas.Canvas(OUT)

# ---- 封面 ----
CH = PW * 746 / 420
c.setPageSize((PW, CH))
c.setFillColorRGB(16 / 255, 18 / 255, 24 / 255)
c.rect(0, 0, PW, CH, stroke=0, fill=1)
c.setFillColorRGB(0.92, 0.93, 0.96)
c.setFont("CN", 34)
c.drawString(40, CH - 150, "缠论概念卡")
c.setFont("CN", 15)
c.setFillColorRGB(0.58, 0.62, 0.70)
c.drawString(42, CH - 185, "《教你炒股票》核心概念 · 一卡一概念")
c.setFillColorRGB(1.0, 0.75, 0.24)
c.setFont("CN", 12)
y = CH - 240
for _, title in ORDER:
    c.drawString(48, y, "· " + title)
    y -= 22
c.setFillColorRGB(0.58, 0.62, 0.70)
c.setFont("CN", 11)
c.drawString(42, 72, "每个说法均有《教你炒股票》原文出处，并经引擎回算验证")
c.drawString(42, 52, "冲浪者 · 2026-09-28")
c.showPage()

# ---- 逐卡 ----
for fn, title in ORDER:
    p = out(fn)
    if not os.path.exists(p):
        sys.exit("缺少 %s —— 先跑 python3 cards/build_all.py" % p)
    im = Image.open(p)
    w, h = im.size
    ph = PW * h / w
    c.setPageSize((PW, ph))
    c.drawImage(ImageReader(p), 0, 0, width=PW, height=ph)
    c.showPage()

c.save()
sz = os.path.getsize(OUT)
print("saved %s  %.1f MB  %d 页" % (OUT, sz / 1048576, len(ORDER) + 1))
