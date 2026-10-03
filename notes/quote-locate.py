# -*- coding: utf-8 -*-
"""把文档里的「」块逐块定位回语料：报 L课:行（起-止），并印出**前后 N 行原文**。

为什么要它：复核一份说明书时，"引文逐字对上了"只是及格线 —— 真正要问的是
**归纳有没有越出原文**，而那只在看到上下文时才看得出来（一句被折行劈开的引文
尤其容易把否定词留在上一行）。所以这把尺不判绿红，只把读的人送到**该读的地方**。

用法：
  python3 notes/quote-locate.py docs/spec/中枢.md                  # 全文件
  python3 notes/quote-locate.py docs/spec/中枢.md --lines 181-217  # 只看某一节
  python3 notes/quote-locate.py docs/spec/中枢.md --ctx 3          # 前后各 N 行（默认 3）
  python3 notes/quote-locate.py --selftest                         # 空块探针（不需要语料）

★★ 空块（`「」` 里一个字都没有）**跳过并计数**，不参与定位。抬头那句
   「**「」＝原文逐字**」就是模板文字，不是引文 —— 但它在每一份 spec 里都有
   （`docs/spec/*.md` 全 11 份都有空块，中枢 `:4`、复权 `:4` 与 `:125`…）。
   老写法不拦空块时会 IndexError：空 needle 在 `find` 里**连 `len(text)` 那一处也命中**，
   而 `pos` 只有 0…len(text)-1 这些位 ⇒ `pos[len(text)]` 越界。
   （2026-10-03 `docs/spec/中枢.md` 上炸的就是这个，nova 报的。）
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
    """→ [(起始行号, 引文原文（含 ↵）)]，按文件里出现顺序；空块也在内（由调用方计数）"""
    src = open(path, encoding='utf-8').read().split('\n')
    out = []
    for ln_no, line in enumerate(src, 1):
        if lo and not (lo <= ln_no <= hi):
            continue
        # 同一行可能有多个「」块
        for m in re.finditer(r'「([^」]*)」', line):
            out.append((ln_no, m.group(1)))
    return out


def find_block(needle, merged):
    """needle 在语料里的每一处 → [(课, 起行, 止行)]。★ 空 needle 一律 []（调用方单独计数）"""
    if not needle:
        return []
    found = []
    for n, (text, pos) in merged.items():
        start = 0
        while True:
            o = text.find(needle, start)
            if o < 0:
                break
            found.append((n, pos[o][0], pos[o + len(needle) - 1][0]))
            start = o + 1
    return found


def run(path, ctx, lo, hi, corpus, out=sys.stdout):
    """把 path 的「」块逐块定位并印出来 → (命中, 未定位, 空块)"""
    merged = {n: merged_of(lines) for n, lines in corpus.items()}
    bl = blocks(path, lo, hi)
    empty = [ln_no for ln_no, body in bl if not body]
    print('# %s ｜ 「」块 %d 个 ｜ 前后各 %d 行' % (path, len(bl), ctx), file=out)
    if empty:
        print('★ 空块 %d 个（跳过、不定位）：%s —— 多是模板文字（抬头那句「「」＝原文逐字」）；'
              '正文里出现空块则多半是漏字' % (len(empty), '·'.join(':%d' % x for x in empty)), file=out)
    hit = miss = 0
    for ln_no, body in bl:
        if not body:
            continue
        needle = body.replace('↵', '')
        found = find_block(needle, merged)
        print('\n── 文档 :%d ──' % ln_no, file=out)
        if not found:
            miss += 1
            print('   ✗ 定位不到（可能含装饰符/叠字差异，需手工找）', file=out)
            print('     引文头 40 字：%s' % needle[:40], file=out)
            continue
        hit += 1
        for (n, l1, l2) in found:
            tag = '' if len(found) == 1 else '  ⚠ 同文多处（%d 处之一）' % len(found)
            print('   → L%d:%d-%d%s' % (n, l1, l2, tag), file=out)
            for i in range(max(1, l1 - ctx), min(len(corpus[n]), l2 + ctx) + 1):
                mark = '▶' if l1 <= i <= l2 else ' '
                print('      %s %4d| %s' % (mark, i, corpus[n][i - 1]), file=out)
    print('\n定位 %d ｜ 未定位 %d ｜ 空块 %d（跳过）' % (hit, miss, len(empty)), file=out)
    return hit, miss, len(empty)


def selftest():
    """空块探针：老写法（空 needle 不拦）在这一步就 IndexError。

    用假语料，不需要真语料 —— 探针必须能在任何一棵树上跑。
    """
    import io
    import tempfile
    corpus = {1: ['笔是不能构成中枢的', '下面这段是重叠']}
    lines = [
        '# 探针文档',
        '> 引号口径：「」＝原文逐字；『』＝编者的话',      # ← 空块（模板文字）
        '真块：「笔是不能构成中枢的」',                    # ← 能定位
        '缺块：「这句话语料里没有」',                      # ← 定位不到
        '空块：「」',                                      # ← 第二个空块
    ]
    fd, tmp = tempfile.mkstemp(suffix='.md')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    out = io.StringIO()
    try:
        hit, miss, empty = run(tmp, 1, None, None, corpus, out=out)
    except Exception as e:                                  # 老写法在这里炸
        print('✗ 空块探针：跑挂了（%s: %s）' % (type(e).__name__, e))
        return 1
    finally:
        os.unlink(tmp)
    ok = (hit == 1 and miss == 1 and empty == 2)
    print('%s 空块探针：命中 %d（应 1）· 未定位 %d（应 1）· 空块 %d（应 2）· 无异常'
          % ('✓' if ok else '✗', hit, miss, empty))
    if not ok:
        print(out.getvalue())
    return 0 if ok else 1


def main():
    if '--selftest' in sys.argv:
        raise SystemExit(selftest())
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
    run(path, ctx, lo, hi, load())


if __name__ == '__main__':
    main()
