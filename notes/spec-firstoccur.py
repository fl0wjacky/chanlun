# -*- coding: utf-8 -*-
"""说明书（docs/spec/*.md）的**首见**尺 —— atlas

为什么还要一把：仓里已有两把尺，**都不查「首见」**。
  · `notes/spec-quotes.py`   —— 查「「」块能不能逐字回到语料」（逐字尺）
  · `notes/concepts-pipeline/checkquotes.py` —— 同上，更细的分档
⇒ 两把都能让一条**引对了字、却标错了行**的引文全绿。
   例：某句在本课 `:40` 首见、`:88` 复述，标 `L88` 逐字命中、尺全绿，**但坐标是错的**。
   本文件管的就是这一维：**引文标的行号，是不是该内容在本课的首次出现行。**

判据（严档）：
  1. 取正文里每个「」块，若它**恰等于**某课某段**整行切片**（行间按 `\\n` 连接）⇒ 认定它是引文块；
  2. 在**同一课**里找该块**首次出现**的字符位置，映射回行号 ⇒ 该是 `首见行`；
  3. 与**正文里它前面最近的那个 `` `L课:行` `` 坐标**比 —— 不等就报红。
不参与判定的（明确列出，不静默跳过）：
  · 不是「整行切片」的「」块（行文内引的短片段，如「被笔破坏」）⇒ 记 `行文`，不判。
  · 该块在多课里都成立 ⇒ 记 `歧义`，**不猜**，报出来让人看。
  · 块前面找不到坐标 ⇒ 记 `无坐标`，报出来。

★★ **本尺有一条**硬前提**，不满足时读数基本是噪声，别拿去指责别人**：
   它靠「正文里最近的那个 `` `L课:行` ``」来认领引文块。
   ⇒ 只在**「一个坐标紧跟它自己那个块」**的写法下可靠（`分型.md`／`笔.md`／`线段.md` 是这么写的）。
   ⇒ 若正文里存在**不跟块的交叉引用**（如「★ 这与 `L33:145` 是同一个答案的另一次给出」），
     那个坐标会被下面第一个块「就近认领」⇒ 报出**假的「课不符／行不符」**。
   ★ 实测：拿它跑 `docs/spec/中枢.md` 报 14 无坐标 ＋ 4 不符；**逐条看过，那 4 条全是配对漂移，不是对方的错**。
   ⇒ **本尺目前只给「按本写法写的文件」用**；要推广，得先让块自带坐标（或改判据）。

用法：
  python3 notes/spec-firstoccur.py docs/spec/分型.md [更多文件...]
  python3 notes/spec-firstoccur.py docs/spec/分型.md --perturb   # 阳性对照：故意把首见行读成 +1
"""
import os, re, sys

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TXT = os.path.join(R, 'archive/chanlun108/text')
TOK = re.compile(r'「([^「」]*)」')
CIT = re.compile(r'`L(\d+):(\d+)(?:-(\d+))?`')

corpus = {}
for fn in sorted(os.listdir(TXT)):
    if fn.startswith('lesson-') and fn.endswith('.txt'):
        corpus[int(fn[7:10])] = open(os.path.join(TXT, fn), encoding='utf-8').read().split('\n')
assert len(corpus) == 108, '语料课数应为 108，实为 %d' % len(corpus)

JOINED = {n: '\n'.join(v) for n, v in corpus.items()}


def line_of(n, pos):
    """字符位置 -> 行号（1 基）。"""
    acc = 0
    for i, l in enumerate(corpus[n], 1):
        if acc <= pos <= acc + len(l):
            return i
        acc += len(l) + 1
    return len(corpus[n])


def whole_line_slice(block):
    """块**恰好等于**某课某段整行切片吗？

    ★ 必须是整行：匹配起点在该行行首、终点在该行行尾。
      按子串判会把「顶」「底」这类**行文内引**误认成引文块（我第一版就是这么错的）。
    ★ 块里的 `↵` 是 spec-quotes.py 折行的记号，比对前归一回 `\\n`。
    返回课号；多课都成立返回 'AMBIG'；都不成立返回 None。
    """
    if not block:
        return None                      # 「「」＝逐字」这种在讲记号本身，不是引文
    blk = block.replace('↵', '\n')
    hits = []
    for n, j in JOINED.items():
        start = 0
        while True:
            p = j.find(blk, start)
            if p < 0:
                break
            head = (p == 0 or j[p - 1] == '\n')
            tail = (p + len(blk) == len(j) or j[p + len(blk)] == '\n')
            if head and tail:
                hits.append(n)
                break
            start = p + 1
    return hits[0] if len(hits) == 1 else ('AMBIG' if hits else None)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    perturb = '--perturb' in sys.argv
    bad_total = 0
    for src in args:
        text = open(src, encoding='utf-8').read()
        # 按出现顺序收集：坐标 与 引文块
        items = []
        for m in TOK.finditer(text):
            items.append(('block', m.start(), m.group(1)))
        for m in CIT.finditer(text):
            items.append(('cit', m.start(), m))
        items.sort(key=lambda x: x[1])

        ok = waive = bad = amb = noc = 0
        msgs = []
        last_cit = None
        for kind, pos, val in items:
            if kind == 'cit':
                last_cit = val
                continue
            block = val
            n = whole_line_slice(block)
            if n is None:
                waive += 1                      # 行文内引，不判
                continue
            if n == 'AMBIG':
                amb += 1
                msgs.append('  ? 歧义：多课都含此块 → %s' % block[:44])
                continue
            first = line_of(n, JOINED[n].find(block.replace('↵', '\n')))
            if perturb:
                first += 1
            if last_cit is None:
                noc += 1
                msgs.append('  ? 无坐标：L%d:%d 起 → %s' % (n, first, block[:44]))
                continue
            c, a, b = int(last_cit.group(1)), int(last_cit.group(2)), last_cit.group(3)
            b = int(b) if b else a
            # ★ 用完即清：一个坐标只认它**自己**那个块。
            #   否则一个坐标会被后面好几个块各自「就近」认领，把「没坐标」误报成「标错了」。
            last_cit = None
            if c != n:
                bad += 1
                msgs.append('  ✗ 课不符：正文标 L%d，块其实在 L%d（首见 :%d）' % (c, n, first))
            elif a != first:
                bad += 1
                msgs.append('  ✗ 行不符：正文标 L%d:%d-%d，本课首见实为 :%d → %s'
                            % (c, a, b, first, block[:40]))
            else:
                ok += 1
        bad_total += bad
        print('== %s ==' % src)
        print('  首见命中 %d ｜ 行文内引(不判) %d ｜ ★不符 %d ｜ 歧义 %d ｜ 无坐标 %d'
              % (ok, waive, bad, amb, noc))
        for m in msgs:
            print(m)
        if bad == 0:
            print('  ✓ 每个引文块的行号，都是该内容在本课的首次出现行')
    print('-' * 60)
    print('★ 另有 A/B 两维本尺**不查**：① 引文是否逐字（交给 spec-quotes.py ＋ checkquotes.py）；'
          '② 首见是否等于「定义处」（首见可能只是顺口一提，定义在别处 —— 那一维要人读）。')
    return 1 if bad_total else 0


if __name__ == '__main__':
    sys.exit(main())
