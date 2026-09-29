#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""c05：① 给图内标签加底色（彻底解决挡字）② 按第20课原文更新术语与判据。"""
P = "/var/minis/workspace/chanlun_mag/cards/c05_center.py"
s = open(P, encoding="utf-8").read()

# ---------- 1) 带底色的标签 ----------
s = s.replace('''def pts_of(pairs, x0, x1, Y):''',
'''def lchip(x, y, text, col, anchor="l"):
    """带底色的标签 —— 保证压在线/框上也读得清。"""
    tw = d.textlength(text, font=f_t)
    bx = x if anchor == "l" else x - tw
    d.rounded_rectangle([bx - 7, y - 4, bx + tw + 7, y + 23], 6, fill=CARD + (240,))
    d.text((bx, y), text, font=f_t, fill=col)
    return tw


def pts_of(pairs, x0, x1, Y):''')

s = s.replace('''    if label:
        d.text((x0 + 10, Y(ZD) + 8 if below else Y(ZG) + dy), label, font=f_t, fill=col)''',
'''    if label:
        lchip(x0 + 10, Y(ZD) + 8 if below else Y(ZG) + dy, label, col)''')
s = s.replace('''    d.text((pt[0][0] + 4, m.Y(108) - 30), "实线 = 成立段", font=f_t, fill=(205, 222, 255))
    d.text((pt[3][0] + 6, m.Y(102) + 10), "虚线 = 延伸段（不封口）", font=f_t, fill=AM)''',
'''    lchip(pt[0][0] + 4, m.Y(108) - 34, "实线 = 成立段", (205, 222, 255))
    lchip(pt[3][0] + 6, m.Y(102) + 10, "虚线 = 延伸段（不封口）", AM)''')
s = s.replace('''    tw = d.textlength("三买", font=f_b)
    d.text((x - tw / 2, y - 48), "三买", font=f_b, fill=GR)''',
'''    lchip(x + 14, y - 46, "三买", GR)''')
s = s.replace('''    tw = d.textlength("三卖", font=f_b)
    d.text((x - tw / 2, y + 26), "三卖", font=f_b, fill=RD)''',
'''    lchip(x + 14, y + 24, "三卖", RD)''')
s = s.replace('''    d.text((pt[A[0]][0] + 6, m.Y(ZDA) + 8), "A [%g,%g]" % (ZDA, ZGA), font=f_t, fill=(205, 222, 255))
    d.text((pt[B[0]][0] + 6, m.Y(ZDB) + 8), "B [%g,%g]" % (ZDB, ZGB), font=f_t, fill=GR)''',
'''    lchip(pt[A[0]][0] + 6, m.Y(ZDA) + 8, "A 中枢 [%g,%g]" % (ZDA, ZGA), (205, 222, 255))
    lchip(pt[B[0]][0] + 6, m.Y(ZDB) + 8, "B 中枢 [%g,%g]" % (ZDB, ZGB), GR)''')

# ---------- 2) 按原文更新 Panel D ----------
a = s.index('cell(X0C[0], 1832, CWC, "④ 趋势（不重叠）"')
b = s.index('# ============ E 数据')
s = s[:a] + '''cell(X0C[0], 1832, CWC, "④ 趋势（两个范围不相交）", GR, T_TREND, 99, 119,
     ["原文定理二①/②：后 GG < 前 DD = 下跌延续；",
      "后 DD > 前 GG = 上涨延续。两者都叫「趋势」。",
      "本例：前 [100,110]　后 [112,118]",
      "→ 后 DD(112) > 前 GG(110) ⇒ 上涨延续。"],
     lambda m, pt, x0, w: f_two(m, pt, x0, w, (0, 2), (4, 6), 108, 102, 116, 114))

cell(X0C[1], 1832, CWC, "⑤ 向上离开 → 升级", AM, P_UP, 98, 127,
     ["原文定理二④：后 ZD > 前 ZG（新中枢在上方）",
      "且 后 DD ≤ 前 GG（两个范围仍相交）",
      "→ 等价于「形成高级别的走势中枢」。",
      "本例：后 DD(110) ≤ 前 GG(118) ✓"],
     lambda m, pt, x0, w: f_two(m, pt, x0, w, (0, 4), (6, 8), 108, 102, 122, 114, (110, 118)))

cell(X0C[2], 1832, CWC, "⑥ 向下离开 → 升级", AM, P_DN, 93, 122,
     ["原文定理二③：后 ZG < 前 ZD（新中枢在下方）",
      "且 后 GG ≥ 前 DD（两个范围仍相交）",
      "→ 同样等价于「形成高级别的走势中枢」。",
      "本例：后 GG(120) ≥ 前 DD(102) ✓"],
     lambda m, pt, x0, w: f_two(m, pt, x0, w, (0, 4), (6, 8), 118, 112, 106, 98, (102, 110)))

''' + s[b:]

# ---------- 3) 大中枢区间：原文未给 ----------
s = s.replace('''# ============ E 数据 ============''',
'''# ---- 升级后的大中枢，区间怎么定？ ----
d.rounded_rectangle([56, 2314, W - 56, 2402], 16, fill=(RD[0], RD[1], RD[2], 22), outline=RD, width=3)
d.text((86, 2326), "★ 原文只说了「何时」形成大级别中枢，没说「它的区间怎么算」", font=f_p, fill=RD)
d.text((86, 2364), "定理二③④ 给的是成立的**条件**；大中枢的 [ZD, ZG] 公式，原文没有给出。", font=f_t, fill=TX)

# ============ E 数据 ============''')
s = s.replace('set_size(1400, 2600)', 'set_size(1400, 2660)')
s = s.replace('d.rounded_rectangle([56, 2340, W - 56, 2440], 20', 'd.rounded_rectangle([56, 2430, W - 56, 2530], 20')
s = s.replace('d.text((86, 2354), "实测（币安合约', 'd.text((86, 2444), "实测（币安合约')
s = s.replace('d.text((86, 2394), "4 小时 384 根', 'd.text((86, 2484), "4 小时 384 根')
s = s.replace('foot(d, "第 17 课（定义）；第 20 课（公式、定理一/二、第三类买卖点）"',
              'foot(d, "第 17 课（定义）；第 20 课（公式、中心定理一/二、走势级别延续定理二、第三类买卖点）"')
s = s.replace('"以为「框画到哪」是客观事实 —— 延伸何时终结原文没给标准，各家实现不一样"',
              '"延伸何时终结、升级后大中枢的区间 —— 这两件事原文都只给了原则，各家实现不一样"')
open(P, "w", encoding="utf-8").write(s)
print("patched")
