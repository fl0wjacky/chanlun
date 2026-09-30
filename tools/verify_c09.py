#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证 c09 卡片注释里那句「引擎 find_centers 复算一致」。

cards/c09_buypoints.py:60 的注释声称卡片上画的两个中枢区间是引擎复算过的：
    下跌趋势：中枢① [138,145] → 中枢② [124,129]（GG② 130 < DD① 137，依次向下；引擎 find_centers 复算一致）

但那张卡自己**不 import core、不调 find_centers**（只 from cards.base import *），
mkchart() 也纯粹是画图（画折线 + 手给的框），所以这句话在仓里**没有留下任何可复核的痕迹**。
本工具就是补上那个痕迹：拿卡片自己的折线当笔序列，真跑一遍引擎，逐项跟注释对。

注意喂给 find_centers 的是**卡片折线的相邻点直连**，不是 build_pens() 的输出 ——
卡片只给了 15 个价位、没给 K 线，这是它的数据能支撑的唯一构造。构造方式在此写明，
免得下次有人以为验过的是别的什么东西。
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.center import find_centers

# 与 cards/c09_buypoints.py:62 完全相同的画图折线
BUY = [152, 138, 145, 137, 144, 124, 130, 121, 129, 108, 120, 114, 134, 131, 140]

# 卡片标称的（c09_buypoints.py:60 注释 + :69 mkchart boxes 两处一致）
EXPECT = [(138, 145), (124, 129)]

pens = [dict(i0=k, i1=k + 1, p0=BUY[k], p1=BUY[k + 1],
             lo=min(BUY[k], BUY[k + 1]), hi=max(BUY[k], BUY[k + 1]))
        for k in range(len(BUY) - 1)]

zs = find_centers(pens)
got = [(z["ZD"], z["ZG"]) for z in zs]

print("=" * 62)
print("c09 卡片标称：中枢① [138,145] → 中枢② [124,129]（注释说这是引擎复算一致的）")
print("喂给引擎：卡片折线的 %d 个相邻点直连 → %d 条笔（非 build_pens）" % (len(BUY), len(pens)))
print("-" * 62)

bad = 0
for i, want in enumerate(EXPECT):
    if i < len(got):
        ok = got[i] == want
        print("中枢%d  卡片标称 [%d,%d]   引擎算出 [%d,%d]   %s"
              % (i + 1, want[0], want[1], got[i][0], got[i][1], "一致" if ok else "★不一致"))
        bad += 0 if ok else 1
    else:
        print("中枢%d  卡片标称 [%d,%d]   引擎只算出 %d 个中枢  ★缺失" % (i + 1, want[0], want[1], len(got)))
        bad += 1

if len(got) > len(EXPECT):
    print("-" * 62)
    print("（引擎另算出 %d 个卡片没画的中枢：%s —— 卡片只画前两个，不算不一致）"
          % (len(got) - len(EXPECT), " ".join("[%d,%d]" % g for g in got[len(EXPECT):])))

print("=" * 62)
if bad:
    print("★ 有 %d 处与卡片注释不符 —— 注释该改，或卡片该改。" % bad)
else:
    print("卡片注释属实：引擎复算出的两个中枢区间与标称逐值相同。")
sys.exit(1 if bad else 0)
