#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""取句器：按 L课:行-行 从语料现取原文，绝不转抄。
用法：python3 notes/readall/pull108.py L37:3-20  [L38:5-9 ...]
输出：每段前一行 `== L37:3-20 ==`，正文里硬折行 → ↵（折行看得见，好核）。

语料不在仓库里（archive/ 不进仓），是各人本机 fetch 下来的同一份：
    <repo>/archive/chanlun108/text/lesson-NNN.txt
指纹自检（应得 534212 字 / sha1 前 12 位 1d6bae92041c）：
    cat archive/chanlun108/text/lesson-*.txt | tr -d '\n' | shasum | cut -c1-12
    # 注意：要按课号排序、只去换行（别去空格），才是这个指纹。
可用 CHANLUN108_DIR 覆盖语料目录。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))          # notes/readall/ -> repo root
BASE = os.environ.get("CHANLUN108_DIR", os.path.join(REPO, "archive", "chanlun108", "text"))


def pull(spec):
    lesson, rng = spec.split(":")
    n = int(lesson.lstrip("Ll"))
    if "-" in rng:
        a, b = (int(x) for x in rng.split("-"))
    else:
        a = b = int(rng)
    p = os.path.join(BASE, "lesson-%03d.txt" % n)
    lines = open(p, encoding="utf-8").read().split("\n")
    print("== %s ==" % spec)
    for i in range(a, b + 1):
        print("%d| %s" % (i, lines[i - 1].replace("\n", "↵")))


if __name__ == "__main__":
    if not sys.argv[1:]:
        sys.exit(__doc__)
    for spec in sys.argv[1:]:
        pull(spec)
        print()
