# -*- coding: utf-8 -*-
"""代读稿的引号收口：命中保留，未命中的「」一律降为『』。

口径与统一尺 `notes/concepts-pipeline/checkquotes.py` 对齐：
  · 块内 `↵` 视作换行（语料是硬折行的）
  · 含 `…` 的块**按片查**：切成若干片，要求**按序命中同一课**（同统一尺的第四档）
  · 命中 ⇒ 原样保留（本工具**不改写**正文，只做「」→『』的降级）
  · 未命中 ⇒ 判为"我自己的话"，降为『』；并尝试**去空白/去换行后**再找一次，
    找得到就打印出语料里的**逐字切片**，供人工贴回（这是真·标点漂移，不是自己的话）
"""
import os, re, sys

R = os.getcwd()
TXT = os.path.join(R, 'archive/chanlun108/text')
SRC = sys.argv[1]
DST = sys.argv[2]

corpus = {}
for fn in sorted(os.listdir(TXT)):
    if fn.startswith('lesson-') and fn.endswith('.txt'):
        corpus[int(fn[7:10])] = open(os.path.join(TXT, fn), encoding='utf-8').read()

TOK = re.compile(r'「([^「」]*)」')


def _pieces(block):
    ps = [p for p in re.split(r'…+', block) if p]
    return ps or [block]


def locate(block):
    """按片、按序、同一课。返回 (课号, 起, 止) 或 None。"""
    ps = [p.replace('↵', '\n') for p in _pieces(block)]
    for n, text in corpus.items():
        cur, ok, first = 0, True, None
        for p in ps:
            i = text.find(p, cur)
            if i < 0:
                ok = False
                break
            if first is None:
                first = i
            cur = i + len(p)
        if ok:
            return n, first, cur
    return None


def locate_loose(block):
    """去掉所有空白（含 ↵）再找 —— 只用来判断"是漂移还是自己的话"。"""
    key = re.sub(r'\s+', '', block.replace('↵', ''))
    if len(key) < 6:
        return None
    for n, text in corpus.items():
        flat = re.sub(r'\s+', '', text)
        i = flat.find(key)
        if i >= 0:
            return n, key
    return None


body = open(os.path.join(R, SRC), encoding='utf-8').read()

hit, miss, loose = 0, [], []
seen_miss = []


def sub(m):
    global hit
    blk = m.group(1)
    if not blk:
        return m.group(0)
    if locate(blk) is not None:
        hit += 1
        return m.group(0)
    if blk not in seen_miss:
        seen_miss.append(blk)
        l = locate_loose(blk)
        if l is not None:
            loose.append((blk, l))
    return '『' + blk + '』'


out = TOK.sub(sub, body)
open(os.path.join(R, DST), 'w', encoding='utf-8').write(out)

total = len(TOK.findall(body))
print('== 代读稿引号收口 ==')
print('总块数   : %d' % total)
print('语料命中 : %d  ← 这些留在「」里' % hit)
print('降为『』 : %d  ← 逐字不是语料的，一律是我自己的话' % len(seen_miss))
print('  其中"只差空白" %d 条（★ 这类必须人工贴回逐字切片，不能当自己的话）:' % len(loose))
for blk, (n, key) in loose:
    print('    ✗ L%d 「%s」' % (n, blk[:80]))
print('  其余 %d 条（确认是自己的话，保持『』）:' % (len(seen_miss) - len(loose)))
for b in seen_miss:
    if not any(b == x[0] for x in loose):
        print('    · 「%s」' % b[:80])
