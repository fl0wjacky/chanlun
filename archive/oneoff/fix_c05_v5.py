#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""c05 收尾：
① 删掉那条「原文没说」的红框 —— 原文其实给了，是我搜错词
② 修标题被挡：chip 高 47px，之前格子起点比它低，压住了底部
③ 术语按原文改：延续 / 扩展 / 新生
"""
P = "/var/minis/workspace/chanlun_mag/cards/c05_center.py"
s = open(P, encoding="utf-8").read()

s = s.replace("set_size(1400, 3000)", "set_size(1400, 2960)")

# ---- C 面板：chip 与格子拉开 ----
s = s.replace("d.rounded_rectangle([56, 1240, W - 56, 1776], 20", "d.rounded_rectangle([56, 1240, W - 56, 1802], 20")
s = s.replace('head_line(1258, "单个中枢：延伸 还是 终结", "这决定虚线框画到哪")',
              'head_line(1254, "① 延续，还是被终结", "第 22 课：中枢有三种运动 —— 延续、扩展、新生")')
s = s.replace("cell(X0C[0], 1294,", "cell(X0C[0], 1320,")
s = s.replace("cell(X0C[1], 1294,", "cell(X0C[1], 1320,")
s = s.replace("cell(X0C[2], 1294,", "cell(X0C[2], 1320,")
s = s.replace('cell(X0C[0], 1320, CWC, "① 延伸"', 'cell(X0C[0], 1320, CWC, "延续"')

# ---- D 面板 ----
s = s.replace("d.rounded_rectangle([56, 1802, W - 56, 2338], 20", "d.rounded_rectangle([56, 1828, W - 56, 2390], 20")
s = s.replace('head_line(1820, "两个中枢之间：趋势 还是 升级", "判据只有一条 —— 两个中枢的「波动范围」碰不碰得上")',
              'head_line(1842, "② 被终结之后：新生（趋势）还是 扩展（更大级别中枢）",\n'
              '         "判据：两个中枢的波动范围 [DD, GG] 碰不碰得上（GG=max(gn)、DD=min(dn)）")')
s = s.replace("cell(X0C[0], 1856,", "cell(X0C[0], 1908,")
s = s.replace("cell(X0C[1], 1856,", "cell(X0C[1], 1908,")
s = s.replace("cell(X0C[2], 1856,", "cell(X0C[2], 1908,")
s = s.replace('"④ 趋势（两个范围不相交）"', '"③ 新生 · 趋势（两个范围不相交）"')
s = s.replace('"⑤ 向上离开 → 扩展"', '"④ 扩展 · 向上离开"')
s = s.replace('"⑥ 向下离开 → 扩展"', '"⑤ 扩展 · 向下离开"')

# ---- 删掉红框（原文其实给了答案）----
a = s.index('# ---- 升级后的大中枢，区间怎么定？ ----')
b = s.index('# ============ E 扩展出来的大中枢，区间怎么算 ============')
s = s[:a] + s[b:]

# ---- E 面板上移 ----
s = s.replace("d.rounded_rectangle([56, 2490, W - 56, 2712], 20", "d.rounded_rectangle([56, 2420, W - 56, 2660], 20")
s = s.replace('chip(d, 80, 2508, "扩展出来的大中枢，区间怎么算？", GR, f_p)',
              'chip(d, 80, 2438, "扩展出来的大中枢，区间怎么算？", GR, f_p)')
s = s.replace('d.text((640, 2516), "第 49 课 + 第 52 课"', 'd.text((640, 2446), "第 49 课 + 第 52 课"')
s = s.replace('d.text((86, 2556), "① 由什么构成', 'd.text((86, 2494), "① 由什么构成')
s = s.replace('d.text((86, 2590), "　 第 49 课', 'd.text((86, 2528), "　 第 49 课')
s = s.replace('d.text((86, 2622), "② 区间怎么算', 'd.text((86, 2562), "② 区间怎么算')
s = s.replace('d.text((86, 2656), "　 第 52 课', 'd.text((86, 2596), "　 第 52 课')
s = s.replace('d.text((86, 2678), "　 → 把三段合起来', 'd.text((86, 2626), "　 → 把三段合起来')

# ---- 数据条 ----
s = s.replace("d.rounded_rectangle([56, 2738, W - 56, 2838], 20", "d.rounded_rectangle([56, 2690, W - 56, 2790], 20")
s = s.replace('d.text((86, 2752), "实测', 'd.text((86, 2704), "实测')
s = s.replace('d.text((86, 2792), "4 小时 384 根', 'd.text((86, 2744), "4 小时 384 根')
open(P, "w", encoding="utf-8").write(s)
print("patched")
