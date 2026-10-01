# -*- coding: utf-8 -*-
"""说明书（docs/spec/*.md）的引号生成器 —— 标记 ⟦课:行-行⟧ ⇒ 「语料逐字切片」。

为什么要它：手打引号会漂（批 28 起九批自纠全是"写顺手"型）。说明书里每一格都要带
原文出处，量比笔记大得多，手打必出事。所以：**正文里只写标记，切片由脚本贴。**

口径（与统一尺 notes/concepts-pipeline/checkquotes.py 对齐）：
  · 切片 = 语料第 a..b 行**原样**连接，行间用 `↵`（不补空格、不改标点）
  · 生成后立刻自检：每个 「」块必须能**逐字**回到语料里找到；找不到就**报红、非零退出**
    ★★ **不许**把不中的自动改成『』（自动降级 ⇒ 检查永远绿、错字不报错）—— 停下来让人改
  · 空输入两侧都断言（语料课数、块数）

用法：
  python3 notes/spec-quotes.py docs/spec/买卖点.md          # 就地展开标记（覆盖原文件）
  python3 notes/spec-quotes.py docs/spec/买卖点.md --check  # 只检查，不写
"""
import os, re, sys

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TXT = os.path.join(R, 'archive/chanlun108/text')
MARK = re.compile(r'⟦(\d+):(\d+)(?:-(\d+))?⟧')
TOK = re.compile(r'「([^「」]*)」')
# ★★ 展开后**不许**再有 ⟦…⟧ 残留。旧版正则只认 `⟦课:行-行⟧`，于是 `⟦98:9⟧`
#    这种单行写法**不被认、原样留在文里**，而「」那一套尺**全都看不见它**
#    ⇒ `docs/spec/中枢.md:111` 带着字面标记进了 main，读者看到的是符号不是原文。
#    @atlas-791f 2026-10-01 在 main 上发现。⇒ 两条：① 单行式也收 ② 残留即报错、不写文件。
#    ★ 只管「长得像真坐标」的：`⟦数字:…⟧`。**故意不抓 `⟦课:起-止⟧` 这种**——
#      说明书正文要能**举例说明标记怎么写**（@atlas-791f 三份文件的表头就写着
#      「单行不展开且不报错」这句），抓宽了会把示例本身判成残留、等于把文档禁言。
LEFT = re.compile(r'⟦\s*\d+\s*[:：][^⟧]*⟧')

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
    # ⟦n:a⟧ ≡ ⟦n:a-a⟧（单行式）
    return MARK.sub(lambda m: slice_of(int(m.group(1)), int(m.group(2)),
                                       int(m.group(3) or m.group(2))), body)


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

    # ★★ **先查残留，后写文件**：宁可什么都不写，也不发出一份带字面标记的稿。
    left = LEFT.findall(out)
    if left:
        print('== %s ==' % src)
        print('✗ 有 %d 处标记没被展开（原样留在文里，读者看到的是符号、不是原文）：' % len(left))
        for t in left[:20]:
            print('  ✗ %s' % t)
        print('  合法写法只有两种：⟦课:行⟧ ／ ⟦课:行-行⟧。文件未改动。')
        raise SystemExit(1)

    if not check_only and n_mark:
        open(src, 'w', encoding='utf-8').write(out)

    blocks = TOK.findall(out)
    assert blocks, '✗ 一块「」都没有 —— 标记没展开？'
    bad = [b for b in blocks if locate(b) is None]

    # ★★ 这里**故意不做**「不逐字的『』自动降级」（v1 做过，@nova-8980 2026-10-01 裁掉）。
    #   理由（她的原话，我认）：自动降级会让检查**永远是绿的** —— 打错一个字也不报错，
    #   只是悄悄换了括号。被换掉的那个块**本来是当引文写的**，改完连"这里错过"的痕迹都没了。
    #   ⇒ 碰到对不上的，**直接报错停下，让人去改**。下面 raise SystemExit(1) 就是这一条。
    print('== %s ==' % src)
    print('标记展开   : %d 处' % n_mark)
    print('「」块     : %d ｜ 逐字命中 %d ｜ 不中 %d' % (len(blocks), len(blocks) - len(bad), len(bad)))
    for b in bad:
        print('  ✗ %s' % b[:100])
    if bad:
        raise SystemExit(1)
    print('✓ 全部逐字命中（语料 108 课）')


main()
