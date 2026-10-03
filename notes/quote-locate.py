# -*- coding: utf-8 -*-
"""把文档里的「」块逐块定位回语料：报 L课:行（起-止），并印出**前后 N 行原文**。

为什么要它：复核一份说明书时，"引文逐字对上了"只是及格线 —— 真正要问的是
**归纳有没有越出原文**，而那只在看到上下文时才看得出来（一句被折行劈开的引文
尤其容易把否定词留在上一行）。所以这把尺不判绿红，只把读的人送到**该读的地方**。

用法：
  python3 notes/quote-locate.py docs/spec/中枢.md                  # 全文件
  python3 notes/quote-locate.py docs/spec/中枢.md --lines 181-217  # 只看某一节
  python3 notes/quote-locate.py docs/spec/中枢.md --ctx 3          # 前后各 N 行（默认 3）
"""
import os
import re
import sys

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TXT = os.path.join(R, 'archive/chanlun108/text')


def load():
    corpus = {}
    for fn in sorted(os.listdir(TXT)):
        if fn.startswith('lesson-') and fn.endswith('.txt'):
            corpus[int(fn[7:10])] = open(
                os.path.join(TXT, fn), encoding='utf-8').read().split('\n')
    assert len(corpus) == 108, '语料课数应为 108，实为 %d' % len(corpus)
    return corpus


def merged_of(lines):
    """→ (合并文本, 每字符 (行号, 列号))；接缝不补空格（与 fuquan-scan 同尺）"""
    text, pos = [], []
    for i, ln in enumerate(lines, 1):
        text.append(ln)
        pos.extend([(i, c) for c in range(len(ln))])
    return ''.join(text), pos


def blocks(path, lo=None, hi=None):
    """→ [(起始行号, 引文原文（含 ↵）)]，按文件里出现顺序"""
    src = open(path, encoding='utf-8').read().split('\n')
    out = []
    for ln_no, line in enumerate(src, 1):
        if lo and not (lo <= ln_no <= hi):
            continue
        # 同一行可能有多个「」块
        for m in re.finditer(r'「([^」]*)」', line):
            out.append((ln_no, m.group(1)))
    return out


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    path = sys.argv[1]
    ctx = 3
    if '--ctx' in sys.argv:
        ctx = int(sys.argv[sys.argv.index('--ctx') + 1])
    lo = hi = None
    if '--lines' in sys.argv:
        a, b = sys.argv[sys.argv.index('--lines') + 1].split('-')
        lo, hi = int(a), int(b)

    corpus = load()
    merged = {}
    for n, lines in corpus.items():
        merged[n] = merged_of(lines)

    bl = blocks(path, lo, hi)
    print('# %s ｜ 「」块 %d 个 ｜ 前后各 %d 行' % (path, len(bl), ctx))
    hit = miss = 0
    for ln_no, body in bl:
        needle = body.replace('↵', '')
        found = []
        for n, (text, pos) in merged.items():
            start = 0
            while True:
                o = text.find(needle, start)
                if o < 0:
                    break
                found.append((n, pos[o][0], pos[o + len(needle) - 1][0]))
                start = o + 1
        print('\n── 文档 :%d ──' % ln_no)
        if not found:
            miss += 1
            print('   ✗ 定位不到（可能含装饰符/叠字差异，需手工找）')
            print('     引文头 40 字：%s' % needle[:40])
            continue
        hit += 1
        for (n, l1, l2) in found:
            tag = '' if len(found) == 1 else '  ⚠ 同文多处（%d 处之一）' % len(found)
            print('   → L%d:%d-%d%s' % (n, l1, l2, tag))
            for i in range(max(1, l1 - ctx), min(len(corpus[n]), l2 + ctx) + 1):
                mark = '▶' if l1 <= i <= l2 else ' '
                print('      %s %4d| %s' % (mark, i, corpus[n][i - 1]))
    print('\n定位 %d ｜ 未定位 %d' % (hit, miss))


if __name__ == '__main__':
    main()
