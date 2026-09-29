#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""c05 收尾：说明行压到 374px 内、三买/三卖标签改为左对齐、去掉字面星号。"""
P = "/var/minis/workspace/chanlun_mag/cards/c05_center.py"
s = open(P, encoding="utf-8").read()

s = s.replace('lchip(x + 14, y - 46, "三买", GR)', 'lchip(x - 16, y - 46, "三买", GR, anchor="r")')
s = s.replace('lchip(x + 14, y + 24, "三卖", RD)', 'lchip(x - 16, y + 24, "三卖", RD, anchor="r")')

# ④⑤⑥ 说明改写（每行 ≤ 360px）
a = s.index('cell(X0C[0], 1832, CWC, "④ 趋势（两个范围不相交）"')
b = s.index('# ---- 升级后的大中枢，区间怎么定？ ----')
s = s[:a] + '''cell(X0C[0], 1832, CWC, "④ 趋势（两个范围不相交）", GR, T_TREND, 99, 119,
     ["定理二①②：后 GG<前 DD → 下跌延续；",
      "　　　　　 后 DD>前 GG → 上涨延续。",
      "　两者都叫「趋势」。本例：",
      "　前 [100,110]　后 [112,118]",
      "→ 112 > 110 ⇒ 上涨延续"],
     lambda m, pt, x0, w: f_two(m, pt, x0, w, (0, 2), (4, 6), 108, 102, 116, 114))

cell(X0C[1], 1832, CWC, "⑤ 向上离开 → 升级", AM, P_UP, 98, 127,
     ["定理二④：后 ZD>前 ZG（新中枢在上）",
      "且 后 DD ≤ 前 GG（两范围仍相交）",
      "→ 等价于形成高级别中枢",
      "本例：后 DD(110) ≤ 前 GG(118)"],
     lambda m, pt, x0, w: f_two(m, pt, x0, w, (0, 4), (6, 8), 108, 102, 122, 114, (110, 118)))

cell(X0C[2], 1832, CWC, "⑥ 向下离开 → 升级", AM, P_DN, 93, 122,
     ["定理二③：后 ZG<前 ZD（新中枢在下）",
      "且 后 GG ≥ 前 DD（两范围仍相交）",
      "→ 同样形成高级别中枢",
      "本例：后 GG(120) ≥ 前 DD(102)"],
     lambda m, pt, x0, w: f_two(m, pt, x0, w, (0, 4), (6, 8), 118, 112, 106, 98, (102, 110)))

''' + s[b:]

s = s.replace('定理二③④ 给的是成立的**条件**；大中枢的 [ZD, ZG] 公式，原文没有给出。',
              '定理二③④ 给的是成立的条件；大中枢自己的 [ZD, ZG] 公式，原文没有给出。')
open(P, "w", encoding="utf-8").write(s)
print("patched")
