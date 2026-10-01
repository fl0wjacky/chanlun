#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""iris 版引号自查（四刀归一化）—— 用于和三组的脚本对尺，不是又一门门槛。

四刀（缺一刀就出假红）：
  1. 去 Markdown 加粗 `**`（两侧）
  2. 在 `…` 处切段，逐段比对
  3. 两侧同时剥引号（我这边、语料那边都剥）
  4. 全角/半角统一（语料几乎全用全角）

另去语料的硬折行标记 `↵`（本语料折行符就写在行尾）。

判据：某一侧存在一段 **≥THRESH 字连续逐字** 的子串 ⇒ 判为语料引文。
输出：块数 / 逐字命中 / 归一化后命中 / 不中，并把「不中」的全部打出来。

用法：python3 notes/checkquotes_iris.py <我的md> [--thresh 4]
"""
import re
import sys
import unicodedata

CORPUS = 'archive/chanlun108/text'


def dew(x):
    """去折行 + 全角/半角统一 + 去所有空白/折行符。"""
    x = x.replace('↵', '')          # ↵ 语料硬折行
    x = re.sub(r'\s+', '', x)
    x = unicodedata.normalize('NFKC', x)
    return x


def strip_marks(x):
    """四刀里属于「归一化」的部分：去加粗、剥引号（两侧都做）。"""
    x = x.replace('**', '')
    for ch in '「」『』“”‘’"\'()（）':
        x = x.replace(ch, '')
    return x


def norm(x):
    return strip_marks(dew(x))


def longest_run(a, b):
    """a 的某个子串在 b 中连续出现的最大长度（去折行后）。"""
    best = 0
    n = len(a)
    for i in range(n):
        if n - i <= best:
            break
        for j in range(i + best + 1, n + 1):
            if a[i:j] in b:
                best = j - i
            else:
                break
    return best


def main():
    path = sys.argv[1]
    thresh = 4
    if '--thresh' in sys.argv:
        thresh = int(sys.argv[sys.argv.index('--thresh') + 1])

    corpus = ''
    import os
    for fn in sorted(os.listdir(CORPUS)):
        corpus += open(os.path.join(CORPUS, fn), encoding='utf-8', errors='replace').read()
    C = norm(corpus)
    Craw = dew(corpus)

    text = open(path, encoding='utf-8').read()
    # 块 = 「…」 内内容，允许跨行
    blocks = re.findall(r'「(.+?)」', text, re.S)
    exact = 0
    normed = 0
    miss = []
    for b in blocks:
        if dew(b) in Craw:
            exact += 1
            continue
        segs = [s for s in norm(b).split('…') if s]
        run = max((longest_run(s, C) for s in segs), default=0)
        if run >= thresh:
            normed += 1
        else:
            miss.append((run, b))

    print(f'文件        : {path}')
    print(f'阈值        : 连续逐字 ≥ {thresh} 字')
    print(f'「」块数    : {len(blocks)}')
    print(f'逐字命中    : {exact}')
    print(f'归一化后命中: {normed}')
    print(f'不中        : {len(miss)}')
    if miss:
        print('\n--- 不中的块（最长连续逐字段长, 内容前 60 字）---')
        for run, b in sorted(miss):
            print(f'  [{run}] {b[:60]!r}')


if __name__ == '__main__':
    main()
