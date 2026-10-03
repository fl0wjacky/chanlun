# -*- coding: utf-8 -*-
"""复权族：全 108 课同义词扫描 —— 三把尺一起报（说明书 docs/spec/复权.md 的取法）。

为什么要三把尺：
  · 语料是**硬折行**的，连"词"都会被拆到两行 ⇒ 逐行 grep 会静默漏（见 memory/chanlun-corpus-wrap）。
  · 源站有**叠字**（OCR 重复字：「标标准」「当当成」）⇒ 字面搜不到 ≠ 原文没有
    （nova 2026-10-03 提醒）⇒ 再加一把"相邻重复字折叠"的尺。
  · 单行口径与去折行口径**数不一样**，各自都对 ⇒ 报数必须连口径报。

用法：
  python3 notes/fuquan-scan.py                # 全表（三把尺）
  python3 notes/fuquan-scan.py --term 复权    # 只看一个词，打印每次命中的 课:行
  python3 notes/fuquan-scan.py --markdown     # 文末台账用的 markdown 表
"""
import os
import re
import sys
import hashlib

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TXT = os.path.join(R, 'archive/chanlun108/text')

# 词的组别：按"同一件事的不同写法"分组，写台账时按组报
GROUPS = [
    ('复权',   ['复权', '前复权', '后复权', '不复权']),
    ('除权除息', ['除权除息', '除权', '除息', '填权', '贴权']),
    ('送配',   ['送配', '送股', '配股', '分红', '派息', '派现']),
    # 第二波：异写与同族词 —— 用来把「字面搜不到」和「原文真没有」分开
    # （nova 2026-10-03：源站有叠字，落空的词必须换写法再搜一遍）
    ('变体／同族', ['向前复权', '向后复权', '复权价', '复权处理', '转增', '增发', '送转',
                    '股息', '红利', '派发', '含权', '抢权', '除权日', '除权缺口',
                    '假填权', '复牌']),
]
TERMS = [t for _, ts in GROUPS for t in ts]


def load():
    """→ {课号: [行, …]}（行号 = 1 起）"""
    corpus = {}
    for fn in sorted(os.listdir(TXT)):
        if fn.startswith('lesson-') and fn.endswith('.txt'):
            corpus[int(fn[7:10])] = open(
                os.path.join(TXT, fn), encoding='utf-8').read().split('\n')
    assert len(corpus) == 108, '语料课数应为 108，实为 %d —— 别在残缺语料上扫' % len(corpus)
    return corpus


def merged(lines):
    """去折行：直接连接（接缝不补空格）。→ (文本, 每字符的 (行号, 列号))"""
    text, pos = [], []
    for i, ln in enumerate(lines, 1):
        text.append(ln)
        pos.extend([(i, c) for c in range(len(ln))])
    return ''.join(text), pos


def fold(text):
    """叠字归一：相邻重复字折叠成一个。→ (文本, 归一后每字符对应原文的下标)"""
    out, idx = [], []
    for i, ch in enumerate(text):
        if out and out[-1] == ch:
            continue
        out.append(ch)
        idx.append(i)
    return ''.join(out), idx


def scan(corpus):
    rows = {}
    for term in TERMS:
        single = {}          # 课 → 逐行出现次数
        for n, lines in corpus.items():
            c = sum(ln.count(term) for ln in lines)
            if c:
                single[n] = c
        merged_hits = []     # [(课, 行, 列)]
        fold_hits = []       # 同上，但走叠字尺
        for n, lines in corpus.items():
            text, pos = merged(lines)                       # 尺②：去折行
            for m in re.finditer(re.escape(term), text):
                o = m.start()
                merged_hits.append((n, pos[o][0], pos[o][1]))
            ftext, fidx = fold(text)                        # 尺③：再去叠字
            for m in re.finditer(re.escape(fold(term)[0]), ftext):
                o = fidx[m.start()]
                fold_hits.append((n, pos[o][0], pos[o][1]))
        rows[term] = {
            'single_lessons': single,
            'single_total': sum(single.values()),
            'merged': merged_hits,
            'merged_lessons': len({h[0] for h in merged_hits}),
            'fold': fold_hits,
            'fold_lessons': len({h[0] for h in fold_hits}),
        }
    return rows


def main():
    corpus = load()
    rows = scan(corpus)
    only = None
    if '--term' in sys.argv:
        only = sys.argv[sys.argv.index('--term') + 1]
    md = '--markdown' in sys.argv

    print('# 复权族扫描 · 语料 %d 课' % len(corpus))
    if md:
        print('\n| 词 | 逐行(次/课) | 去折行(次/课) | 叠字归一(次/课) | 首见(去折行口径) |')
        print('|---|---|---|---|---|')
    for group, terms in GROUPS:
        if not md:
            print('\n## 组：%s' % group)
        for term in terms:
            r = rows[term]
            first = min(r['merged']) if r['merged'] else None
            first_s = 'L%d:%d' % (first[0], first[1]) if first else '—'
            if md:
                print('| %s | %d / %d | %d / %d | %d / %d | %s |' % (
                    term, r['single_total'], len(r['single_lessons']),
                    len(r['merged']), r['merged_lessons'],
                    len(r['fold']), r['fold_lessons'], first_s))
            else:
                print('%-6s 逐行 %3d次/%2d课 ｜ 去折行 %3d次/%2d课 ｜ 叠字归一 %3d次/%2d课'
                      ' ｜ 首见 %s' % (term, r['single_total'], len(r['single_lessons']),
                                       len(r['merged']), r['merged_lessons'],
                                       len(r['fold']), r['fold_lessons'], first_s))
            if only == term:
                for (n, ln, col) in r['merged']:
                    print('    L%d:%d  %s' % (n, ln, corpus[n][ln - 1][max(0, col - 12):col + 24]))
    # 语料指纹
    joined = ''.join(''.join(v) for _, v in sorted(corpus.items()))
    print('\n语料指纹：%d 课 / %d 字 / sha1 %s' % (
        len(corpus), len(joined), hashlib.sha1(joined.encode('utf-8')).hexdigest()[:12]))


main()
