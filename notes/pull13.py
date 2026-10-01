#!/usr/bin/env python3
"""按行号从语料现取引句，绝不转抄（见 memory/chanlun-quote-ledger.md §1）。
用法：python3 notes/pull13.py < spec.txt
spec 每行：<key>\t<lesson>\t<start>\t<end>[\t<必须含的关键词>]
输出：<key>\t<lesson>:<start>-<end>\t「<原文，\n→↵>」
"""
import sys, os

TEXT = os.path.join(os.path.dirname(__file__), '..', 'archive', 'chanlun108', 'text')
CACHE = {}


def lines(n):
    if n not in CACHE:
        p = os.path.join(TEXT, 'lesson-%03d.txt' % n)
        CACHE[n] = open(p, encoding='utf-8').read().split('\n')
    return CACHE[n]


STOP = '。！？：；）】」”…—〇》'


def pull(les, a, b, must=None, maxext=4):
    L = lines(les)
    end = b
    # 行尾不在停顿符 ⇒ 往下多吃，最多 maxext 行（语料硬折行）
    ext = 0
    while ext < maxext:
        tail = L[end - 1].rstrip()
        if tail and tail[-1] in STOP:
            break
        if end >= len(L):
            break
        end += 1
        ext += 1
    body = '\n'.join(L[a - 1:end])
    flat = body.replace('\n', '')
    if must and must not in flat:
        return None, '关键词 %r 不在取出的句子里' % must
    return (body.replace('\n', '↵'), end), None


bad = 0
for raw in sys.stdin.read().splitlines():
    if not raw.strip() or raw.startswith('#'):
        continue
    f = raw.split('\t')
    key, les, a = f[0], int(f[1]), int(f[2])
    b = int(f[3]) if len(f) > 3 and f[3].strip() else a
    must = f[4] if len(f) > 4 and f[4].strip() else None
    res, err = pull(les, a, b, must)
    if err:
        print('!! %s L%d:%d-%d  %s' % (key, les, a, b, err))
        bad += 1
        continue
    body, end = res
    rng = '%d' % a if a == end else '%d-%d' % (a, end)
    print('%s\tL%s:%s\t「%s」' % (key, les, rng, body))
sys.exit(1 if bad else 0)
