# -*- coding: utf-8 -*-
"""尾部稳定性实测：砍掉最后 K 根 K 线，中枢列表从第几个开始变？

问法：在完整数据上，centers[i] 要能被信任（不再被后到的 K 线改写），
i 最小得排到多前面？答案 = 1 + max over K of (最后一个与完整结果**不同**的下标)。

只跑 truncation（每个 K 一次 analyze），不做 O(n^2)。
"""
import json
import sys

sys.path.insert(0, '.')
from core.analyze import analyze

FILES = ["zec15.json", "zec_1h.json", "zec_4h.json", "btc_4h.json",
         "aaplusdt_4h.json", "aaplusdt_30m.json"]
KS = [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233]


def key(c):
    return tuple(sorted((k, v) for k, v in c.items()
                        if k not in ("rel", "kind")))


def first_diff(a, b):
    """第一个不同的下标；没有不同返回 None。"""
    for i in range(min(len(a), len(b))):
        if key(a[i]) != key(b[i]):
            return i
    if len(a) != len(b):
        return min(len(a), len(b))
    return None


for fn in FILES:
    bars = json.load(open('data/' + fn, encoding='utf-8'))
    full = analyze(bars)["centers"]
    worst = -1
    worstk = None
    lines = []
    for k in KS:
        if k >= len(bars) - 30:
            continue
        part = analyze(bars[:-k])["centers"]
        d = first_diff(full, part)
        nfull, npart = len(full), len(part)
        if d is None:
            lines.append(f"    K={k:4d}  完全一致（{npart} 个中枢）")
        else:
            # 从末尾数：这个下标离末尾多远
            back = nfull - d
            lines.append(f"    K={k:4d}  首个不同下标 {d}（离末尾 {back}）"
                         f"  完整 {nfull} 个 / 截断 {npart} 个")
            if d > worst:
                worst, worstk = d, k
    print(f"== {fn}  尾部 {len(full)} 个中枢，{len(bars)} 根 K 线")
    print("\n".join(lines))
    if worst < 0:
        print("  ⇒ 所有 K 都不动：**没有观测到改写**")
    else:
        print(f"  ⇒ 改写最远到达下标 {worst}（K={worstk}），"
              f"即末尾 {len(full) - worst} 个中枢里至少有 1 个不稳；"
              f"下标 ≤ {worst - 1} 的 {worst} 个全程稳定")
    print()
