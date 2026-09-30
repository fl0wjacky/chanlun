#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第 54 课算例回算：三个 1 分钟中枢合成 5 分钟中枢，区间应为 [d2, g5]。

原文条件「d1=g2，d2=g4」，走势从 g0=18.5 开始逐段下行；其余价位原文图上没有标数，
这里取一组满足全部文字描述的数：g3 是第三类卖点（d3g3 碰不到 [d1, g1]）、g1d2 > g2d3 > g3d4 力度递减、
g5 高于 d2（区间才非空）。每一小段都是「没有内部结构的线段」，按引擎的中枢公式算三个小中枢，
再按引擎的大中枢区间公式合成。第二部分另验「只看前三段」：再接一个仍碰到区间的中枢，区间不变。

want 的来源分三档，别混（这是本文件最容易被读歪的地方）：
    原文-字面  只有 g0=18.5 —— 原文图上真标了这个数，别处没有
    原文-命题  关系式：「d1=g2，d2=g4」「就是[d1，g2]，也就是一个价位」「只看前三段」——测关系，不抄数
    引擎重算   want 是 fixture 自己的量（区间端点就是链上的点），非重言性最低的一档，只当回归基准
17.0 / 17.8 / 16.6 … 全是这组自编数：当 fixture 可以，当 want 就是把编的数再抄一遍、还贴上「原文验证」的标签。
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.center import find_centers
from core.extend import big_interval, build_hierarchy

g0, d1, g1, d2, g2, d3, g3, d4, g4, d5, g5 = 18.5, 17.0, 17.8, 16.6, 17.0, 16.0, 16.5, 15.8, 16.6, 15.9, 16.8
# 第 54 课原文条件「d1=g2，d2=g4」——这是这组自编数的**前提**，破了下面全部没意义。
# 用 raise 不用 assert：assert 在 python -O 下整条消失，前提破了也没人知道（沉默 ≠ 通过）。
if not (d1 == g2 and d2 == g4):
    raise AssertionError("原文条件「d1=g2，d2=g4」被破坏：这组数不再满足第 54 课的前提，回算无意义")
pts = [g0, d1, g1, d2, g2, d3, g3, d4, g4, d5, g5]
units = [dict(p0=a, p1=b, hi=max(a, b), lo=min(a, b), i0=k, i1=k + 1) for k, (a, b) in enumerate(zip(pts, pts[1:]))]

FAIL = 0


def check(label, want, got):
    """值型校验：want 是链上的点（被原文-命题指名的端点）。

    打印不再自称「原文」—— 本文件里 want 没有一个数是原文图上标出来的字面，
    标成「原文 [17, 17]」就是给它贴一个它没有的出身。要自称原文，得先拿得出
    原文的字面（本文件里只有 g0=18.5）。
    """
    global FAIL
    ok = abs(want[0] - got[0]) < 1e-9 and abs(want[1] - got[1]) < 1e-9
    FAIL += not ok
    print("  %s %-40s want [%g, %g]   引擎 [%g, %g]" % ("✓" if ok else "✗", label, want[0], want[1], got[0], got[1]))


def check_prop(label, prop, ok):
    """命题型校验：want 不是抄来的数，而是原文里的一句话（关系 / 不变式）。

    和 check() 的区别不在严格程度，在**非重言性**：want 一旦是从被测的那组数里
    抄的，测的就是「函数等于它自己的输入」。命题型只测关系，绕开具体值 ——
    所以哪怕别人把整组 fixture 换一组数（只要仍满足原文条件），这条照样有效。
    """
    global FAIL
    FAIL += not ok
    print("  %s %-40s 命题「%s」" % ("✓" if ok else "✗", label, prop))


print("第 54 课：g0d5 = g0d1 + {(d1g1+g1d2+d2g2) + (g2d3+d3g3+g3d4) + (d4g4+g4d5+d5g5)}")
first = find_centers(units[0:3])[0]                       # 走到 d2 时：[d1, g1]
# 这里**不**标「原文-命题」：前三段区间取交 = [max(d1,d1,d2), min(g0,g1,g1)] = [d1, g1]，
# 是这组 fixture 的几何必然 —— want 是被构造逼出来的，这条测的只是「引擎挑对了这三段」。
# 标成原文命题等于给它安一个它没有的出身：本来只是没内涵，标完还多一层假出身（Nova #178）。
check("[引擎重算·构造必然] 走到 d2 时的 1 分钟中枢", (d1, g1), (first["ZD"], first["ZG"]))
Z0 = find_centers(units)[0]                               # 按段往后走：d2g2 仍是震荡，g2d3 离开、d3g3 碰不到 → g3 三卖
ok = Z0["term"] == "三卖" and Z0["PI1"] == 3
FAIL += not ok
print("  %s %-40s 原文-命题 d2g2 属震荡、g3 三卖   引擎 终于第 %d 段、%s" % ("✓" if ok else "✗", "[d1, g1] 中枢怎么结束", Z0["PI1"], Z0["term"]))
A = find_centers(units[1:4])[0]                           # (d1g1+g1d2+d2g2)：原文「就是[d1，g2]，也就是一个价位」
# 原文命题：区间塌成一个价位。旧写法 want=(d1, g2) 是把这组自编数抄进 want，
# 而 d1=g2 是前提（上面已 raise 保证）—— 等于拿 fixture 验 fixture。改测命题本身；
# 「落在原文条件钉住的价位上」这一半用的是链上的点 d1，属推导链自查，不是外部字面。
check_prop("(d1g1+g1d2+d2g2) 的区间 = 一个价位",
           "ZD == ZG（区间塌成一个价位），且落在原文条件 d1=g2 钉住的价位上",
           abs(A["ZD"] - A["ZG"]) < 1e-9 and abs(A["ZD"] - d1) < 1e-9)
B = find_centers(units[4:7])[0]
C = find_centers(units[7:10])[0]
spans = [(z["DD"], z["GG"]) for z in (A, B, C)]           # 「当成线段……高低点就是这线段的端点」
check("[原文-命题] 三个 1 分钟中枢合成的 5 分钟中枢", (d2, g5), big_interval(spans))

print("第 52 课答疑「中枢延伸的情况，只看前三段的区间，后面都是震荡」：")
mk = lambda PI0, PI1, ZD, ZG, DD, GG: dict(PI0=PI0, PI1=PI1, ZD=ZD, ZG=ZG, DD=DD, GG=GG, X0=PI0, X1=PI1, live=False)
pens = [dict(lo=10, hi=12)] * 20
Z = [mk(0, 2, 10.0, 11.0, 9.5, 11.5), mk(4, 6, 11.2, 12.0, 11.1, 12.5), mk(8, 10, 10.5, 11.3, 10.2, 11.6),
     mk(12, 14, 9.0, 10.8, 8.0, 12.9)]
for z in Z:
    z["rel"], z["kind"] = "", ""
pens = [dict(lo=11.0, hi=11.4)] * 20                      # 连接段
big = build_hierarchy(Z, pens)
check("[原文-命题] 接上第 3、4 个中枢后区间不变", big_interval([(9.5, 11.5), (11.0, 11.4), (11.1, 12.5)]), (big[0]["ZD"], big[0]["ZG"]))
print("   成员 %d 个，波动范围 [%g, %g]（随成员扩大）" % (big[0]["nmerge"], big[0]["DD"], big[0]["GG"]))
print("全部一致" if FAIL == 0 else "有 %d 条对不上" % FAIL)
sys.exit(1 if FAIL else 0)
