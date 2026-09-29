#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证 c05 卡片要画的三组笔序列：引擎算出的中枢，是否与卡片标称一致。"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.center import find_centers
from core import analyze
from config import data
import json


def mk(pairs):
    """[(起价, 终价), ...] → 笔列表"""
    out = []
    for k, (a, b) in enumerate(pairs):
        out.append(dict(p0=a, p1=b, hi=max(a, b), lo=min(a, b),
                        i0=k * 10, i1=k * 10 + 10, x0=k, x1=k + 1))
    return out


CASES = [
    ("A / B① 下-上-下（形成）", [(110,100),(100,108),(108,102)],
     "中枢 [102,108]，覆盖笔 1-3"),
    ("B② 上-下-上（形成）", [(100,110),(110,102),(102,108)],
     "中枢 [102,108]，覆盖笔 1-3"),
    ("C1 延续（后续 Z 段仍与区间重叠）", [(110,100),(100,108),(108,102),(102,107),(107,103)],
     "中枢 [102,108]，覆盖笔 1-5，仍在延伸"),
    ("C2 三买封口", [(110,100),(100,108),(108,102),(102,116),(116,112)],
     "中枢 [102,108]，覆盖笔 1-3，已封口"),
    ("C3 三卖封口", [(100,110),(110,102),(102,108),(108,94),(94,98)],
     "中枢 [102,108]，覆盖笔 1-3，已封口"),
    ("D1 新生·趋势（三买之后新中枢在更上方）",
     [(110,100),(100,108),(108,102),(102,116),(116,112),(112,118),(118,114)],
     "A[102,108]波动[100,110]／B[114,116]波动[112,118] → 不相交 ⇒ 趋势"),
    ("D2 扩展·向上", [(110,100),(100,108),(108,102),(102,118),(118,104),
                   (104,124),(124,110),(110,122),(122,114)],
     "A[102,108]波动[100,118]／B[114,122]波动[110,124] → 重叠[110,118] ⇒ 升级"),
    ("D3 扩展·向下（D2 的上下镜像）",
     [(220-a,220-b) for a,b in [(110,100),(100,108),(108,102),(102,118),(118,104),
                                (104,124),(124,110),(110,122),(122,114)]],
     "A[112,118]波动[102,120]／B[98,106]波动[96,110] → 重叠[102,110] ⇒ 升级"),
]

import re
FAIL = 0
for name, pairs, expect in CASES:
    z = find_centers(mk(pairs))
    # 标称里的中枢区间（「中枢 [a,b]」「A[a,b]」「B[a,b]」，不含「波动[..]」）按顺序与引擎比对
    want = [(float(a), float(b)) for a, b in re.findall(r"(?:中枢 |A|B)\[(\d+),\s*(\d+)\]", expect)]
    have = [(x["ZD"], x["ZG"]) for x in z][:len(want)]
    ok = want == have
    FAIL += not ok
    got = " ／ ".join("[%g, %g] 覆盖笔 %d-%d%s" % (
        x["ZD"], x["ZG"], x["PI0"] + 1, x["PI1"] + 1,
        "（延伸中）" if x["live"] else "（已封口）") for x in z) or "无"
    print("=" * 66)
    print("%s" % name)
    print("   标称：%s" % expect)
    print("   引擎：%s　%s" % (got, "✓" if ok else "✗ 区间与标称不符"))

print("=" * 66)
print("两个方向升级例子的波动范围（验证「重叠」这条论断）")
for nm, PS in (("D2 向上", [(110,100),(100,108),(108,102),(102,118),(118,104),
                          (104,124),(124,110),(110,122),(122,114)]),
               ("D3 向下", [(220-a,220-b) for a,b in
                          [(110,100),(100,108),(108,102),(102,118),(118,104),
                           (104,124),(124,110),(110,122),(122,114)]])):
    rngs = []
    for x in find_centers(mk(PS)):
        seg = PS[x["PI0"]:x["PI1"]+1]
        rngs.append((min(min(a,b) for a,b in seg), max(max(a,b) for a,b in seg)))
    ov = (max(r[0] for r in rngs), min(r[1] for r in rngs))
    print("   %s  A%s B%s → 重叠 [%g, %g] ⇒ 定理二成立" % (nm, rngs[0], rngs[1], ov[0], ov[1]))

print("=" * 66)
print("引擎自检（真实数据）")
for fn, tag in (("aaplusdt_4h.json", "4小时"), ("aaplusdt_30m.json", "30分钟")):
    r = analyze(json.load(open(data(fn), encoding="utf-8")))
    ok = all(z["ZG"] > z["ZD"] and z["X1"] >= z["X0"] for z in r["centers"])
    print("   [%s] 中枢 %d 个，区间与横向范围全部合法: %s" % (tag, len(r["centers"]), ok))
    FAIL += not ok

print("=" * 66)
print("全部一致" if FAIL == 0 else "有 %d 处与标称不符" % FAIL)
sys.exit(1 if FAIL else 0)
