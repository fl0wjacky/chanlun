#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""term-sweep —— 从原文里「抽」术语，拿去和已交付的清单对差集，找漏网。

和「先定词场、再逐词回全库数」那类扫描的区别：**候选不是我挑的**，是从原文自己的
写法里抽出来的 —— 所以它查不出我没想到的词，但能查出「我想不到要去挑」的词。
两遍合起来才是完整的（挑词表扫语义场，抽术语扫原文的命名习惯）。

两种抽法：
  A 引号术语：原文用 “…” 标出来的短词（3–18 字、无标点数字），出现在 ≥N 课
  B 定义句型：`“X” 称为/叫做/称作/定义为` 与 `称为 “X”` —— 抓的是**原文自己下了定义**的术语

用法：
  python3 notes/term-sweep.py                        # 默认：课数 ≥2、不排除任何已收词
  python3 notes/term-sweep.py --known docs/concepts/inventory_中枢走势组.md \
                              --known docs/concepts/inventory_结构组.md     # 排除已收
  python3 notes/term-sweep.py --field 中枢,走势,级别,分解,扩展,延伸,新生   # 只看某一组的语义场
  python3 notes/term-sweep.py --min-lessons 1 --all  # 连只出现一课的都列（噪声大，看单课命名时用）

读数怎么用：`课数` 高 = 原文反复用的正式名（漏了就是真漏）；`课数 1` 的多是行文里的
临时说法，除非它出现在 `称为/定义为` 句型里（那是原文给的定义，一课也算数 ——
本组清单里「震荡中轴」（L92）就是这么一条）。
"""

import argparse
import collections
import os
import re
import sys

CJK = "".join(chr(c) for c in range(0x4E00, 0x9FA6))
BAD = re.compile(r"[，。；：！？、（）()“”「」《》\dA-Za-z]")
QUOTED = re.compile(r"“([^”]{2,24})”")
DEF_A = re.compile(r"“([^”]{2,24}?)”\s*(?:就)?(?:称为|叫做|称作|定义为)")
DEF_B = re.compile(r"(?:称为|叫做|称作|定义为)\s*“?([^”，。；：、\s“”]{%d,%d})" % (2, 14))


def load_corpus(d):
    """→ {课号: 全文（折行已合并，接缝不补空格）}"""
    out = {}
    for f in sorted(os.listdir(d)):
        m = re.search(r"(\d+)", f)
        if not m or not f.endswith(".txt"):
            continue
        out[int(m.group(1))] = open(os.path.join(d, f), encoding="utf-8").read().replace("\n", "")
    return out


def load_known(paths):
    """从已交付清单里抠出概念名（表格第一格的 **…**）。"""
    names = set()
    for p in paths:
        try:
            txt = open(p, encoding="utf-8").read()
        except OSError as e:
            print("  ⚠ 读不到 %s：%s" % (p, e), file=sys.stderr)
            continue
        for cell in re.findall(r"^\|\s*\*\*(.+?)\*\*", txt, re.M):
            names.add(re.sub(r"（.*?）|【.*?】|\s", "", cell))
    return names


def covered(cand, known):
    """候选已经被某个概念名覆盖（互为子串，且概念名 ≥3 字）？"""
    return any(k and len(k) >= 3 and (k in cand or cand in k) for k in known)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="archive/chanlun108/text")
    ap.add_argument("--known", action="append", default=[],
                    help="已交付清单（可给多个）；抽出的候选若被它覆盖就不列")
    ap.add_argument("--min-lessons", type=int, default=2)
    ap.add_argument("--field", default="", help="逗号分隔的关键词，候选里必须含其中一个")
    ap.add_argument("--all", action="store_true", help="连已收的也列出来（标「已收」）")
    a = ap.parse_args()

    corp = load_corpus(a.corpus)
    if not corp:
        sys.exit("语料目录没找到：%s" % a.corpus)
    known = load_known(a.known)
    field = [w for w in a.field.split(",") if w]

    cnt = collections.Counter()
    les = collections.defaultdict(set)
    how = collections.defaultdict(set)          # 术语 → {抽法}
    for n, t in corp.items():
        for q in QUOTED.findall(t):
            q = q.strip()
            if len(q) >= 3 and not BAD.search(q):
                cnt[q] += 1
                les[q].add(n)
                how[q].add("A")
        for pat in (DEF_A, DEF_B):
            for q in pat.findall(t):
                q = q.strip()
                if len(q) >= 2 and not BAD.search(q):
                    cnt[q] += 1
                    les[q].add(n)
                    how[q].add("B")

    rows = []
    for q, ls in les.items():
        if len(ls) < a.min_lessons:
            continue
        if field and not any(w in q for w in field):
            continue
        hit = covered(q, known)
        if hit and not a.all:
            continue
        rows.append((len(ls), cnt[q], min(ls), q, "".join(sorted(how[q])), "已收" if hit else "**新**"))
    rows.sort(key=lambda r: (-r[0], -r[1], r[2]))

    mode = "＋".join([p for p, on in (("A 引号术语", True), ("B 定义句型", True)) if on])
    print("term-sweep ｜ 语料 %d 课 ｜ 抽法 %s ｜ 课数 ≥%d%s%s ｜ 候选 %d 条"
          % (len(corp), mode, a.min_lessons,
             " ｜ 语义场 " + a.field if field else "",
             " ｜ 已排除 %d 个已收概念名" % len(known) if known and not a.all else "",
             len(rows)))
    print()
    print("| 课数 | 次数 | 首见 | 候选 | 抽法 | |")
    print("|---|---|---|---|---|---|")
    for nl, c, first, q, hw, tag in rows:
        print("| %d | %d | L%d | %s | %s | %s |" % (nl, c, first, q, hw, tag))
    print()
    print("读法：课数 ≥2 且标 **新** 的，回原文看它有没有定义 —— 有定义而清单里没有，就是漏网。")


if __name__ == "__main__":
    main()
