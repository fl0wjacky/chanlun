#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""c03：去掉自指的「③④」，说明改成两行 + 空间指代；并检查所有说明行是否超宽。"""
P = "/var/minis/workspace/chanlun_mag/cards/c03_pen.py"
s = open(P, encoding="utf-8").read()

# 1) cellc 支持两行说明
s = s.replace(
    '    d.text((x0 + 16, y0 + 300), note, font=f_t, fill=MU)',
    '    _notes = note if isinstance(note, (list, tuple)) else [note]\n'
    '    for _k, _t in enumerate(_notes):\n'
    '        d.text((x0 + 16, y0 + 296 + _k * 32), _t, font=f_t, fill=MU)')

# 2) 四格说明改写
s = s.replace(
    '"底分型(索引1) → 顶分型(索引5)，差 4，刚好够 → 成笔"',
    '"底分型(索引1) → 顶分型(索引5)，差 4，刚好够 → 成笔"')
s = s.replace(
    '"顶分型(索引1) → 底分型(索引5)，差 4 → 成笔（①的镜像）"',
    '"顶分型(索引1) → 底分型(索引5)，差 4 → 成笔（和左格对称）"')
s = s.replace(
    '"底(索引1) → 顶(索引3)，只差 2 < 4 → 这个顶分型被丢弃"',
    '"底分型(索引1) → 顶分型(索引3)，只差 2 < 4 → 顶分型被丢弃"')
s = s.replace(
    '"③④ 连着：底(2) 被跳过 → 末尾仍是顶，新顶更高就顶替它"',
    '["起因在左格：底分型(索引2) 间隔不够，被跳过",\n'
    '       "→ 末尾仍是顶分型 → 新来的顶更高，就顶替旧的那个"]')

open(P, "w", encoding="utf-8").write(s)

# 3) 量一遍所有说明行宽度
import subprocess, sys, os
sys.path.insert(0, "/var/minis/workspace/chanlun_mag")
os.chdir("/var/minis/workspace/chanlun_mag")
from PIL import Image, ImageDraw
from render.style import F
import re
draw = ImageDraw.Draw(Image.new("RGB", (10, 10)))
f = F(20)
for m in re.finditer(r'cellc\([^;]*?\)\)?\n', open(P, encoding="utf-8").read()):
    pass
for line in open(P, encoding="utf-8").read().splitlines():
    if line.strip().startswith('"') and ("索引" in line or "左格" in line or "末尾仍是" in line):
        txt = line.strip().strip(',').strip('"')
        w = draw.textlength(txt, font=f)
        flag = "OK " if w <= 582 else "超宽"
        print("%s %4dpx  %s" % (flag, w, txt))
print("cellc 内容可用宽度上限 = 582px")
