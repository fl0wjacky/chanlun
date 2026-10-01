# ════════════════════════════════════════════════════════════════════════════════
# 结构组 · 行号级审计（@atlas-791f）
#
#   输入
#     · docs/concepts/inventory_结构组.md   被审计的产物
#     · 语料 archive/chanlun108/text/*.txt  ← **gitignored**；路径同生成器（CHANLUN108 → 当前目录 → 兜底）
#
#   输出
#     · stdout   逐条引文的两问结果：问一（课号级）／问二（坐标级），落五格
#
#   复核
#     python3 notes/audit_lines.py
# ════════════════════════════════════════════════════════════════════════════════

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""结构组清单 · 行号级审计（照 iris 02:5xZ 的五格表跑）

第 3 格「行号飘」是「回本课找」这一把尺**抓不到**的 —— 回本课答的是**课号**，
回第 N 行答的才是**坐标**。本脚本把产物里每一条引文拿出来，逐条跑两问：
  问一（课号级）  这句逐字在不在这**一课**里？      —— 不通 ⇒ 落第 4／5 格
  问二（坐标级）  这句逐字在不在我标的**那个行号**上？ —— 不通 ⇒ 落第 3 格（行号飘）
两问都不通再回**全库**找一次，用来把「点名点错课（别课有）」和「哪儿都没有」分开。

用法：python3 notes/audit_lines.py [产物路径]
复核即重跑，不手数。
"""
import os
import re
import sys

BASE = os.path.expanduser("~/.cumora/agents/atlas-791f/workspace/ci/archive/chanlun108")
DOC = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser(
    "~/.cumora/agents/atlas-791f/workspace/ci/docs/concepts/inventory_结构组.md")
BRK = "↵"

# 产物里引文的写法：第 N 课 `:a`「…」／`:a-b`「…」
RE_Q = re.compile(r"第\s*(\d+)\s*课\s*`:(\d+)(?:-(\d+))?`「([^「」]+)」")


def lines(n):
    p = os.path.join(BASE, "text", "lesson-%03d.txt" % n)
    with open(p, encoding="utf-8") as f:
        return f.read().split("\n")


_cache = {}


def flat(n):
    """该课正文去掉换行（换行是排版折行），返回 (扁平文本, 每字符→行号)"""
    if n not in _cache:
        ls = lines(n)
        buf, owner = [], []
        for i, L in enumerate(ls, start=1):
            s = L.strip()
            for ch in s:
                buf.append(ch)
                owner.append(i)
        _cache[n] = ("".join(buf), owner)
    return _cache[n]


_rt = {}


def rowtext(n):
    """{行号: 该行去首尾空白后的文本}"""
    if n not in _rt:
        _rt[n] = {i: L.strip() for i, L in enumerate(lines(n), start=1)}
    return _rt[n]


def find_all(hay, needle):
    out, i = hay.find(needle), 0
    while i >= 0:
        out = hay.find(needle, i)
        if out < 0:
            break
        yield out
        i = out + 1


def corpus_hits(q):
    """回全库找：哪几课含这句（存在性）"""
    hit = []
    for n in range(1, 109):
        if q in flat(n)[0]:
            hit.append(n)
    return hit


def main():
    doc = open(DOC, encoding="utf-8").read()
    items = RE_Q.findall(doc)
    print("产物里按『第 N 课 `:行号`「引文」』写法抽出的引文条数 = %d" % len(items))
    print()
    _stat = {"严 ·首次出现起于标的首行": 0, "松 ·有一次出现起于 a..b": 0,
             "极松·标的那一行含有该句": 0}
    cells = {"正常·独此一课": [], "正常·跨课命中": [], "★行号飘": [],
             "点名点错课(别课有)": [], "点名错(哪儿都没有)": []}
    total = 0
    for lesson, a, b, raw in items:
        n, a = int(lesson), int(a)
        b = int(b) if b else a
        # ★ 第十一遍修：此处**只去了折行符 `↵`，没去 Markdown 装饰** ⇒ 表里写成
        #   「线段被**笔**破坏」的引文会被当成本来就带 `**` 的原文，**在语料里当然找不到**，
        #   于是落进「点名错(哪儿都没有)」——那是本脚本自己造的假红。
        #   归一必须与生成器的 `check_quotes._norm` 一致（去空白 / `↵` / `**`）。
        q = raw.replace(BRK, "").replace("**", "").strip()
        if len(q) < 2:
            continue
        total += 1
        hay, owner = flat(n)
        # 问一：课号级
        if q not in hay:
            others = corpus_hits(q)
            key = "点名点错课(别课有)" if others else "点名错(哪儿都没有)"
            cells[key].append((n, a, b, q[:24], others))
            continue
        # 问二：坐标级 —— 三档强度都算（@iris-64a1 02:3xZ 指出「行号」这一档有两种强度）
        #   严 ：该引文在本课的**首次出现**就起于 a（会把「重复出现、标的不是第一次」报成飘）
        #   松 ：该引文**有一次出现**其起行落在 a..b 之内（本脚本默认口径）
        #   极松：a..b 中某一行**含有**该引文（连"引文只是跨过这一行"也算）
        starts = list(find_all(hay, q))
        onrows = sorted({owner[i] for i in starts})
        first_row = onrows[0] if onrows else None
        rt = rowtext(n)
        mid = any(q in rt.get(r, "") for r in range(a, b + 1))
        _stat["严 ·首次出现起于标的首行"] += 1 if first_row == a else 0
        _stat["松 ·有一次出现起于 a..b"] += 1 if any(a <= r <= b for r in onrows) else 0
        _stat["极松·标的那一行含有该句"] += 1 if mid else 0
        if any(a <= r <= b for r in onrows):
            others = sorted(set(corpus_hits(q)) - {n})
            cells["正常·跨课命中" if others else "正常·独此一课"].append(
                (n, a, b, q[:24], others))
        else:
            cells["★行号飘"].append((n, a, b, q[:24], onrows))
    print("=" * 78)
    for k, v in cells.items():
        print("%-20s %3d 条" % (k, len(v)))
    print("-" * 78)
    print("计 %d 条" % total)
    print()
    print("第二问（坐标）三档强度对照 —— 同一批 %d 条：" % total)
    for k, v in _stat.items():
        print("   %-24s %3d / %d" % (k, v, total))
    print()
    for k, v in cells.items():
        if k.startswith("正常"):
            continue
        if not v:
            continue
        print("### %s" % k)
        for n, a, b, head, extra in v:
            print("  第 %d 课 :%d-%d 「%s…」  实况: %s" % (n, a, b, head, extra))
        print()


if __name__ == "__main__":
    main()
