#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统计同一概念的多种写法在 108 课里的出现次数，生成术语别名表。"""
import os, re, glob, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ARCHIVE

BASE = os.path.join(ARCHIVE, "chanlun108", "text")
docs = []
for n in range(1, 109):
    p = os.path.join(BASE, "lesson-%03d.txt" % n)
    if os.path.exists(p):
        docs.append((n, open(p, encoding="utf-8").read()))

GROUPS = [
    ("中枢",               ["缠中说禅走势中枢", "走势中枢", "中枢"]),
    ("连续三笔/次级别重叠", ["三个连续次级别走势类型", "三个连续次级别", "次级别走势类型重叠"]),
    ("延伸 / 延续",         ["延伸", "延续"]),
    ("扩展 / 扩张",         ["扩展", "扩张"]),
    ("走势终完美",          ["走势终完美", "走势必完美", "终完美"]),
    ("三类买卖点",          ["第三类买点", "第三类买卖点", "三类买点", "三买"]),
    ("一买 / 二买",         ["第一类买点", "第一类买卖点", "第二类买点", "二买"]),
    ("分型",               ["顶分型", "底分型", "分型", "特征序列的分型"]),
    ("笔",                 ["一笔", "笔的划分", "分笔"]),
    ("线段",               ["线段"]),
    ("特征序列",            ["特征序列"]),
    ("缺口",               ["缺口", "突破性缺口", "中继性缺口", "衰竭性缺口"]),
    ("背驰",               ["盘整背驰", "趋势背驰", "背驰段", "背驰"]),
    ("级别",               ["次级别", "本级别", "该级别", "高级别", "级别"]),
    ("Z 走势段",            ["Z走势段", "Z 走势段", "Z 段", "Zn"]),
    ("区间套",             ["区间套"]),
    ("中阴",               ["中阴"]),
    ("离开 / 返回",         ["离开", "回抽", "回试", "回拉"]),
    ("中枢的三种运动",       ["延续、扩展、新生", "延续,扩展,新生", "三种运动"]),
    ("走势类型",            ["走势类型", "盘整", "趋势"]),
]

print("%-18s %s" % ("概念", "各种写法的出现次数（全库 108 课）"))
print("-" * 78)
for name, variants in GROUPS:
    out = []
    for v in variants:
        c = sum(t.count(v) for _, t in docs)
        if c:
            out.append("%s %d" % (v, c))
    covered = sum(t.count(variants[0]) for _, t in docs)
    print("%-18s %s" % (name, " ｜ ".join(out) if out else "—"))
