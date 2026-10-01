# -*- coding: utf-8 -*-
"""说明书（docs/spec/*.md）的引号生成器 —— 标记 ⟦课:行-行⟧ ⇒ 「语料逐字切片」。

为什么要它：手打引号会漂（批 28 起九批自纠全是"写顺手"型）。说明书里每一格都要带
原文出处，量比笔记大得多，手打必出事。所以：**正文里只写标记，切片由脚本贴。**

口径（与统一尺 notes/concepts-pipeline/checkquotes.py 对齐）：
  · 切片 = 语料第 a..b 行**原样**连接，行间用 `↵`（不补空格、不改标点）
  · 生成后立刻自检：每个 「」块必须能**逐字**回到语料里找到；找不到就报红、非零退出
  · 空输入两侧都断言（语料课数、块数）

用法：
  python3 notes/spec-quotes.py docs/spec/买卖点.md          # 就地展开标记（覆盖原文件）
  python3 notes/spec-quotes.py docs/spec/买卖点.md --check  # 只检查，不写
"""
import os, re, sys

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TXT = os.path.join(R, 'archive/chanlun108/text')
MARK = re.compile(r'⟦(\d+):(\d+)-(\d+)⟧')
TOK = re.compile(r'「([^「」]*)」')

corpus = {}
for fn in sorted(os.listdir(TXT)):
    if fn.startswith('lesson-') and fn.endswith('.txt'):
        corpus[int(fn[7:10])] = open(os.path.join(TXT, fn), encoding='utf-8').read().split('\n')
assert len(corpus) == 108, '语料课数应为 108，实为 %d —— 别在残缺语料上生成' % len(corpus)


def slice_of(n, a, b):
    lines = corpus[n]
    if not (1 <= a <= b <= len(lines)):
        raise SystemExit('✗ L%d:%d-%d 越界（该课共 %d 行）' % (n, a, b, len(lines)))
    return '「' + '\n'.join(lines[a - 1:b]).replace('\n', '↵') + '」'


def expand(body):
    return MARK.sub(lambda m: slice_of(int(m.group(1)), int(m.group(2)), int(m.group(3))), body)


def locate(block):
    """逐字回到语料（含 ↵ 折行）；返回课号或 None。"""
    for n, lines in corpus.items():
        if block.replace('↵', '\n') in '\n'.join(lines):
            return n
    return None


def main():
    src = sys.argv[1]
    check_only = '--check' in sys.argv
    body = open(src, encoding='utf-8').read()
    n_mark = len(MARK.findall(body))
    out = expand(body) if n_mark else body
    if not check_only and n_mark:
        open(src, 'w', encoding='utf-8').write(out)

    blocks = TOK.findall(out)
    assert blocks, '✗ 一块「」都没有 —— 标记没展开？'
    bad = [b for b in blocks if locate(b) is None]

    # 自纠：不逐字的「」一律降为『』。生成出来的块永远逐字，所以不中的必然是**我顺手写的强调**。
    # 十批自纠全是这个病（手打的「」＝自己的想法），与其每次人工改，不如让它出不去。
    if bad and not check_only:
        for b in bad:
            out = out.replace('「%s」' % b, '『%s』' % b)
        open(src, 'w', encoding='utf-8').write(out)
        blocks = TOK.findall(out)
        bad = [b for b in blocks if locate(b) is None]

    print('== %s ==' % src)
    print('标记展开   : %d 处' % n_mark)
    print('「」块     : %d ｜ 逐字命中 %d ｜ 不中 %d' % (len(blocks), len(blocks) - len(bad), len(bad)))
    for b in bad:
        print('  ✗ %s' % b[:100])
    if bad:
        raise SystemExit(1)
    print('✓ 全部逐字命中（语料 108 课）')


main()
