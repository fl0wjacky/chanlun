#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ZEC 15 分钟 · 全量顺滑版（通用脚本 render/chart_full_smooth.py 的 ZEC 预设）。

与按月分面板的 chart_zec_full.py 互补：分面板版每月纵轴各自缩放，细节最满；
顺滑版全程同一根对数轴，不拼接、不变形。
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from render.chart_full_smooth import render

if __name__ == "__main__":
    render("zec15.json", "ZEC/USDT 永续", "15 分钟", px=2, ph=3600, out_name="zec15_full_smooth.png")
