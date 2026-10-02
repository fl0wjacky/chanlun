# -*- coding: utf-8 -*-
"""前提③ 的「上一层」数组里，级别齐不齐？（只读，给 bram 那条 ① 对账）

bram 量到：`build_hierarchy()` 返回的**一个列表**里混着两类 —— 真合成过的（level=2、nmerge>1）
和**没合成、原样浅拷贝进来的单中枢**（nmerge=1、level 保持 1）。本脚本量的是**这件事对前提③
有没有后果**：三个问题 ——
    ① 两支 higher（笔层 seg_centers / 线段层 build_hierarchy(seg_centers)）各有多少条、几条是合成过的
    ② 线段层那些**没合成的单中枢**，有没有真的当过「上一层的中枢」（即参与过命中判定）
    ③ 前提③ 在六份数据上的命中，是命中在合成条上还是单中枢上
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.analyze import analyze_file
from core.signals import _units, _higher_centers, check_premise3

FILES = ["zec15.json", "zec_1h.json", "zec_4h.json", "btc_4h.json",
         "aaplusdt_4h.json", "aaplusdt_30m.json"]


def kind(c):
    n = c.get("nmerge", 1)
    return "合成(level=%s,nmerge=%d)" % (c.get("level", 1), n) if n > 1 else "单中枢(浅拷贝,level=%s)" % c.get("level", 1)


def cands(r, level):
    AU, _U, Z = _units(r, level)
    for k in range(1, len(Z)):
        B = Z[k]
        if B["rel"] not in ("下跌延续", "上涨延续"):
            continue
        want_down = B["rel"] == "下跌延续"
        same = (lambda u: u["p1"] < u["p0"]) if want_down else (lambda u: u["p1"] > u["p0"])
        a = next((q for q in range(B["PI0"] - 1, -1, -1) if same(AU[q])), None)
        c = next((q for q in (B["PI1"] + 1, B["PI1"] + 2) if q < len(AU) and same(AU[q])), None)
        if a is None or c is None:
            continue
        A, C = AU[a], AU[c]
        yield k, B, min(A["lo"], B["DD"], C["lo"]), max(A["hi"], B["GG"], C["hi"])


for level in ("pen", "seg"):
    print("── 层级 %s ── 上一层 = %s" % (level, "seg_centers（本来就只有一级，无混级问题）"
                                     if level == "pen" else "build_hierarchy(seg_centers, 已完成线段)"))
    for fn in FILES:
        r = analyze_file(fn)
        H = _higher_centers(r, level)
        merged = [c for c in H if c.get("nmerge", 1) > 1]
        lone = [c for c in H if c.get("nmerge", 1) == 1]
        hits = []
        for k, B, lo, hi in cands(r, level):
            v = check_premise3(H, B, lo, hi, True)
            if v["hit"]:
                hits.append((k, v["center"]))
        print("  %-18s higher %2d 条 = 合成 %d ＋ 单中枢 %d ｜ 命中 %d 个%s"
              % (fn, len(H), len(merged), len(lone), len(hits),
                 "" if not hits else " → " + "; ".join(
                     "B#%d 落在 %s" % (k, kind(c)) for k, c in hits)))
    print()
