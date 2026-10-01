#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""坐标尺（通用版）—— 任意「代读」笔记里每一条『引文 ＋ 我标的 L课:行』回语料核。

为什么另写一把（而不是复用 `notes/核坐标-代读.py`）：
  · 那份是 @atlas-791f 给自己那份笔记写的，**claims 是硬编码在脚本里的**
    （18 条手工抄进去的元组），换一份笔记它就抽出 0 条、报绿 —— 又是
    『空输入与全绿长得一模一样』那一侧。
  · 本脚本**从笔记正文里自己抽**引文与坐标，对三份代读稿通用。

判据（与 atlas 那把一致，取严档）：
  · 引文里 `↵` 视作换行（语料是硬折行的；合并时接缝**不加空格**）；
  · 定位引文在该课合并文本里**首次出现**的字符区间，映射回行号；
  · 要求 起点行 == 标的 `a`（末行 b 一并打印，只做提示）。
  首发行对不上的 ⇒ **红**，把「我标／实得／引文」整条打出来。

配对规则（保守，宁漏不误）：
  一行里取**第一个坐标标签** = `L<n>:<a>` 或 `L<n>:<a>`–`<b>`（`–`/`-`/`~` 都认，
  在反引号内外都认），再取该标签**之后**的第一个 ≥4 字的「」块配成一条。
  取不到的（标签后没引文／引文没有标签）计入**跳过**，不判红。
  ★ 本文件的引文块落在**下一行**（长引文我这么排）—— 所以标签后找不到引文时，
    再看**下一个非空行**。

用法：
  python3 notes/concepts-pipeline/coordcheck.py notes/代读-中枢走势组-*.md
  python3 notes/concepts-pipeline/coordcheck.py --perturb <file>   # 阳性对照
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TXT = os.path.join(ROOT, "archive", "chanlun108", "text")

LAB = re.compile(r"`?L(\d+):(\d+)`?\s*[–\-~]\s*`?(\d+)`?|`?L(\d+):(\d+)`?")
QUO = re.compile(r"「([^「」]*)」")


def load():
    les, lines = {}, {}
    for fn in sorted(os.listdir(TXT)):
        if fn.startswith("lesson-") and fn.endswith(".txt"):
            n = int(fn[7:10])
            t = open(os.path.join(TXT, fn), encoding="utf-8").read()
            lines[n] = t.replace("\r", "").split("\n")
            les[n] = "".join(lines[n])
    assert len(les) == 108, "语料只装了 %d 课" % len(les)
    return les, lines


def linemap(lines):
    """字符位置 → 行号（合并文本里**不插**换行符，所以不 +1）。"""
    m, pos = {}, 0
    for i, l in enumerate(lines, 1):
        for _ in range(len(l)):
            m[pos] = i
            pos += 1
    m[pos] = len(lines)
    return m


def norm(s):
    return s.replace("↵", "").strip()


GAP = 2  # 标签与引文之间容得下的字符数（`：`、反引号、空格这类；再宽就会把同一行里的


def scan(path, les, lm, perturb=False):
    """把每一条『坐标标签 ＋ 紧贴着它的引文』配成一条，回语料核首发行。

    配对**只认紧贴**：引文与标签之间隔的字符数 ≤ GAP。这一条是为了掐掉
    『同一行里的另一个 `L课:行` 引用』和『上一颗子弹留下的引文』这两类误配 ——
    它们都是**尺自己的错**，不是笔记的错，报出来只会淹掉真红。
    一行里有多个标签就逐对核（Iris 那种 `A`「…」＋`B`「…」的写法）。
    """
    src = open(path, encoding="utf-8").read().split("\n")
    ok, skip, bad = 0, 0, []
    for line in src:
        blocks = [(x.start(), x.end(), x.group(1)) for x in QUO.finditer(line)]
        for m in LAB.finditer(line):
            n = int(m.group(1) or m.group(4))
            a = int(m.group(2) or m.group(5))
            b = int(m.group(3)) if m.group(3) else a   # 区间标签：a–b 是整段的跨度
            if perturb and not bad and n in les:       # 阳性对照：只扰动第一条
                a += 2
            if n not in les:
                continue
            q = None
            for s, e, t in blocks:                     # 标签**之后**紧贴的
                if 0 <= s - m.end() <= GAP and len(norm(t)) >= 4:
                    q = t
                    break
            if q is None:                              # 标签**之前**紧贴的
                for s, e, t in reversed(blocks):
                    if 0 <= m.start() - e <= GAP and len(norm(t)) >= 4:
                        q = t
                        break
            if q is None:
                skip += 1
                continue
            q = norm(q)
            k = les[n].find(q)
            if k < 0:                                  # 交叉引用／转述 ⇒ 这条尺看不见
                skip += 1
                continue
            first = lm[n][k]
            if not (a <= first <= b):
                bad.append((n, a, b, first, q[:28]))
            else:
                ok += 1
    return ok, skip, bad


def main():
    args = [x for x in sys.argv[1:] if not x.startswith("--")]
    perturb = "--perturb" in sys.argv
    les, lines = load()
    lm = {n: linemap(lines[n]) for n in lines}
    print("语料 108 课 ｜ 共 %d 字 ｜ 尺＝首发行（↵ 视作换行，接缝不补空格）" % sum(len(v) for v in les.values()))
    tot = 0
    for p in args:
        ok, skip, bad = scan(p, les, lm, perturb)
        tot += len(bad)
        print("\n%s" % os.path.basename(p))
        print("  逐条命中 %d ｜ 交叉引用/取不到跳过 %d ｜ 不符 %d" % (ok, skip, len(bad)))
        for n, a, b, f, q in bad[:20]:
            rng = "%d" % a if b == a else "%d–%d" % (a, b)
            print("    ★ L%d 标 :%s，语料首发行 :%d —— %s" % (n, rng, f, q))
    print("\n合计不符 %d 条 ⇒ %s" % (tot, "红" if tot else "绿"))
    return 1 if tot else 0


if __name__ == "__main__":
    sys.exit(main())
