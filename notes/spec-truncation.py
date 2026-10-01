# -*- coding: utf-8 -*-
"""说明书（docs/spec/*.md）的**截断**尺 —— atlas

为什么还要一把：仓里那两把（`spec-quotes.py` 逐字、`checkquotes.py` 阶梯）都查
「引的文字对不对」，**都不查「引到哪儿为止」**。`checkquotes.py` 有一栏「疑似掐尾」，
但它量的是**末尾标点可不可疑** —— 这既会放过真截断，也会冤掉整行引用。

**本尺只判一件事：引文块是不是停在硬折行的行尾、而句子在下一行接着写。**

判据（只一条，任何人可复算）：
  1. 块尾必须正好落在语料某一行的**行尾**（块本身在行中就跳过，那是行文内引）；
  2. 块尾那个字符**不是句终符**；
  3. 下一行**以内容字开头**（不是空行、不是新标题）。
  ⇒ 三条同时成立 ＝ **真截断**。

★ 为什么句终符里**没有「，」和「、」**：逗号、顿号本来就不结束句子。
  它们出现在行尾，正是「下句在下一行」的**信号**，不是行结束。
  ★ 我第一版把「，」也算成句终符，于是**漏掉了 `分型.md` 的 `L62:8` 那一条**
    （`iris` 在卡 card-03bbd747-264 上逮的）。判据里这一个字符的差别，
    就是「3 条」与「4 条」的差别。

★★ 反面教训（别再犯）：**「原文在这里断了」是关于语料的一个断言，必须回语料查。**
   只看到被截断的那一屏，看不见下一行，**不等于下一行不存在**。
   本尺存在的意义就是让这句断言可执行。

用法：
  python3 notes/spec-truncation.py docs/spec/*.md
退出码：0 ＝ 无真截断 ｜ 1 ＝ 有真截断 ｜ 2 ＝ 前提不成立（语料不全）
"""
import os, re, sys

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TXT = os.path.join(R, 'archive/chanlun108/text')
TOK = re.compile(r'「([^「」]*)」')

# ★ 句终符：句子到这儿**结束**了。
#   「，」「、」**不在**里面 —— 它们本来就是"句子还没完"的记号（这是我第一版的错处）。
TERM = set('。！？；：…”’」』）)') | set('.;:!?"\'')

corpus = {}
for fn in sorted(os.listdir(TXT)):
    if fn.startswith('lesson-') and fn.endswith('.txt'):
        corpus[int(fn[7:10])] = open(os.path.join(TXT, fn), encoding='utf-8').read().split('\n')
if len(corpus) != 108:
    print('判不了：语料应有 108 课，实为 %d —— 别在残缺语料上下结论' % len(corpus), file=sys.stderr)
    sys.exit(2)

JOINED = {n: '\n'.join(v) for n, v in corpus.items()}


def line_of(n, pos):
    acc = 0
    for i, l in enumerate(corpus[n], 1):
        if acc <= pos <= acc + len(l):
            return i
        acc += len(l) + 1
    return len(corpus[n])


def find(blk):
    """块是不是某课的一个**整行切片**？返回 (课, 起点) 或 None。"""
    hits = []
    for n, j in JOINED.items():
        s = 0
        while True:
            p = j.find(blk, s)
            if p < 0:
                break
            if (p == 0 or j[p - 1] == '\n') and (p + len(blk) == len(j) or j[p + len(blk)] == '\n'):
                hits.append((n, p))
                break
            s = p + 1
    return hits[0] if len(hits) == 1 else None


def main():
    files = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not files:
        print(__doc__)
        return 2
    total = 0
    for src in files:
        text = open(src, encoding='utf-8').read()
        print('== %s ==' % src)
        found = 0
        for m in TOK.finditer(text):
            blk = m.group(1).replace('↵', '\n')
            if not blk:
                continue                      # 「「」＝逐字」这种在讲记号本身
            hit = find(blk)
            if not hit:
                continue                      # 行文内引，不判
            n, p = hit
            end = p + len(blk)
            if end < len(JOINED[n]) and JOINED[n][end] != '\n':
                continue                      # 块尾不在行尾 ⇒ 行文内引
            ln = line_of(n, max(p, end - 1))
            nxt = corpus[n][ln] if ln < len(corpus[n]) else ''
            nxt_s = nxt.strip()
            if blk[-1] in TERM or not nxt_s:
                continue                      # 句终符收尾，或下一行是空行/段末
            found += 1
            print('  ✗ L%d:%d 块尾「…%s」' % (n, ln, blk[-18:]))
            print('       下一行开头「%s」 ⇒ 句子在下一行接着写，引文该续上' % nxt_s[:30])
        print('  真截断 %d 条' % found)
        total += found
    print('-' * 56)
    print('合计真截断 %d 条' % total)
    return 1 if total else 0


if __name__ == '__main__':
    sys.exit(main())
