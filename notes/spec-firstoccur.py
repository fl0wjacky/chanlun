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

★★ **本尺有一条硬前提；前提不成立时它不猜，报「判不了」停下。**
   它靠「**紧邻**在块前面的那个 `` `L课:行` ``」认领引文块（坐标与块之间 ≤3 个换行）。
   前提＝**每个引文块都有自己紧邻的坐标，且一个坐标只领一个块**。
   ⇒ 违反任一条（无主块／一坐标多块）⇒ **rc=2「判不了」**，并把逐条判词标成「不可信」。
      **2 不是「有错」，是「这份文件我判不了」** —— 别把它读成红。

   ★ 为什么要「紧邻」这一条：正文里的**交叉引用**（「★ 这与 `L33:145` 是同一个答案的另一次给出」）
     离块隔着一个标题好几行。按「最近的那个」认领，它会把下面第一个块抢走 ⇒ 报**假的「课不符」**。
     这正是我第一版对 `docs/spec/中枢.md` 报出 4 条假红的原因（逐条看过，**一条都不是作者的错**）。

   ★ 实测九份（main `ccd7441`）：`分型`／`笔`／`线段` **rc=0**；其余六份 **rc=2**（前提不成立）。
     —— 这是**写法差异**，不是那六份有错。

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
    unresolved = 0
    for src in args:
        text = open(src, encoding='utf-8').read()
        # 按出现顺序收集：坐标 与 引文块
        items = []
        for m in TOK.finditer(text):
            items.append(('block', m.start(), m.group(1)))
        for m in CIT.finditer(text):
            items.append(('cit', m.start(), m))
        items.sort(key=lambda x: x[1])

        def newlines_between(p, q):
            return text.count('\n', p, q)

        ok = waive = bad = amb = noc = multi = 0
        msgs = []
        n_cit = n_block = 0
        last_cit = None
        owned = 0                      # 当前坐标已经领过几个块
        for kind, pos, val in items:
            if kind == 'cit':
                n_cit += 1
                last_cit = val
                cit_end = val.end()
                owned = 0
                continue
            block = val
            n = whole_line_slice(block)
            if n is None:
                waive += 1                      # 行文内引，不判
                continue
            n_block += 1
            if n == 'AMBIG':
                amb += 1
                msgs.append('  ? 歧义：多课都含此块 → %s' % block[:44])
                continue
            first = line_of(n, JOINED[n].find(block.replace('↵', '\n')))
            if perturb:
                first += 1
            # ★★ 前提不成立 ⇒ 报错停下，**不猜**（@iris-64a1 提的三条，这里是前两条）。
            #    看不懂的时候不吭声，等于把风险转给下一个读的人。
            # ★ 坐标**只认紧邻它**的那个块。正文里「见 `L33:145`」这种提一句、
            #   离块隔着一个标题好几行 —— 那是**交叉引用**，不是块的主人。
            #   不设这条，悬空的引用会把下面第一个块抢走，报出假的「课不符」。
            if last_cit is None or newlines_between(cit_end, pos) > 3:
                why = ('它前面一个坐标都没有' if last_cit is None
                       else '最近那个坐标（L%s:%s）离它有 %d 个换行，不是紧邻'
                            % (last_cit.group(1), last_cit.group(2), newlines_between(cit_end, pos)))
                noc += 1
                bad += 1
                msgs.append('  ✗ 无主块（%s）：L%d:%d 起 → %s' % (why, n, first, block[:40]))
                last_cit = None
                continue
            if owned >= 1:
                multi += 1
                bad += 1
                msgs.append('  ✗ 一个坐标领了不止一个块（本尺不挑其中一个）：'
                            'L%s:%s 之后第 %d 个块 → %s'
                            % (last_cit.group(1), last_cit.group(2), owned + 1, block[:38]))
                owned += 1
                continue
            owned += 1
            c, a, b = int(last_cit.group(1)), int(last_cit.group(2)), last_cit.group(3)
            b = int(b) if b else a
            if c != n:
                bad += 1
                msgs.append('  ✗ 课不符：正文标 L%d，块其实在 L%d（首见 :%d）' % (c, n, first))
            elif a != first:
                bad += 1
                msgs.append('  ✗ 行不符：正文标 L%d:%d-%d，本课首见实为 :%d → %s'
                            % (c, a, b, first, block[:40]))
            else:
                ok += 1
        premise_broken = (noc + multi) > 0
        if not premise_broken:
            bad_total += bad      # 前提没破，才把「不符」记成真不符
        delta = n_cit - n_block
        print('== %s ==' % src)
        print('  首见命中 %d ｜ 行文内引(不判) %d ｜ 不符 %d（无主块 %d ＋ 一坐标多块 %d）｜ 歧义 %d'
              % (ok, waive, bad, noc, multi, amb))
        print('  坐标 %d 个 ｜ 引文块 %d 个 ｜ 差 %+d%s'
              % (n_cit, n_block, delta,
                 '（差不为 0 正常：表里的坐标往往不跟块；但**块比坐标多**要先看' if delta < 0 else ''))
        if premise_broken:
            print('  ★★ 前提不成立（见下 N 条）：本尺**不判这份文件**。')
            print('     下面的「课不符／行不符」**一条都不可信** —— 那是配对漂移，不是作者的错。')
            print('     要判这份，先让引文块自带坐标（或改用别的判据）。')
        for m in msgs:
            suffix = '  ［前提已破，此条不可信］' if premise_broken and ('课不符' in m or '行不符' in m) else ''
            print(m + suffix)
        if bad == 0:
            print('  ✓ 每个引文块的行号，都是该内容在本课的首次出现行')
        elif premise_broken:
            unresolved += 1   # 不是「有错」，是「判不了」——下面按 rc=2 记
    print('-' * 60)
    print('★ 另有 A/B 两维本尺**不查**：① 引文是否逐字（交给 spec-quotes.py ＋ checkquotes.py）；'
          '② 首见是否等于「定义处」（首见可能只是顺口一提，定义在别处 —— 那一维要人读）。')
    print('★ 退出码：0 ＝ 判过了，全绿 ｜ 1 ＝ 判过了，有真不符 ｜ '
          '2 ＝ **判不了**（前提不成立），不是「有错」')
    if bad_total:
        return 1
    return 2 if unresolved else 0


if __name__ == '__main__':
    sys.exit(main())
