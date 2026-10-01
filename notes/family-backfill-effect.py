#!/usr/bin/env python3
# 族词回灌 · 影响面实测（动力学组）· iris 2026-10-01
#
# 回答一个问题：**把某个候选词补成族词，账会动多少？**
#   ⇒ 这不是"多一列"的问题。族词一动，`broad ≥4` 就变 ⇒ **表内／★未读／表外 三颗数一起动**，
#     而且这些数**已经写进交付件的散文里**（§15.2 抬头、§15.3 现状、§15.4 那三条名单）。
#   ⇒ 所以回灌**不能顺手做**，必须照第 16 批那样当一次**记账事件：记差值、不回溯改**。
#
# ★ 只读，不写任何文件。
# 用法：python3 notes/family-backfill-effect.py    （在哪个目录跑都一样）
import os, re, glob, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
READFILE = os.path.join(ROOT, 'notes/read-动力学.txt')

BASE = [('背驰', ['背驰','背弛','背馳','背离']), ('力度', ['力度']), ('买卖点', ['买卖点','买点','卖点']),
        ('MACD', ['MACD','黄白线','零轴','0 轴','柱子']), ('缺口', ['缺口','跳空']), ('合力', ['合力','分力'])]
NARROW = ['背驰段','盘整背驰','趋势背驰','类背驰','类似背驰','小转大','小级别转大级别','区间套',
          '黄白线','零轴','0 轴','柱子','趋势平均力度','平均趋势力度','走势力度','背驰级别',
          '第一类买点','第二类买点','第三类买点','第三类卖点','红柱子','绿柱子']

LESSONS = {}
for p in glob.glob(os.path.join(ROOT, 'archive/chanlun108/text/lesson-*.txt')):
    LESSONS[int(re.search(r'lesson-(\d+)', p).group(1))] = open(p, encoding='utf-8').read()
if len(LESSONS) != 108:
    sys.exit('★ 语料不全（只找到 %d 课）—— 数不许在这种状态下报' % len(LESSONS))
DEW = {n: t.replace('\n', '') for n, t in LESSONS.items()}
READ = {int(x) for x in open(READFILE).read().split()} if os.path.exists(READFILE) else set()

def measure(fam):
    inb, out = [], []
    for n in sorted(LESSONS):
        b = sum(sum(DEW[n].count(t) for t in ts) for _, ts in fam)
        r = sum(DEW[n].count(t) for t in NARROW)
        (out if (b < 4 and r == 0) else inb).append(n)
    done = len([n for n in inb if n in READ])
    return len(inb), done, len(inb) - done, len(out), out

b_inb, b_done, b_un, b_out, b_outl = measure(BASE)
print('现口径（六族）：表内 %d · 已精读 %d · ★未读 %d · 表外 %d' % (b_inb, b_done, b_un, b_out))
print()

# nova 2026-10-01 裁：**(b) 不收**（`中枢`／`走势类型`／`线段`／`级别`）；**`均线系统` 例外、收进动力学**
#   ——(b) 的理由，原样记：**收进来表会涨到近乎整本书，欠账一下变大，找到的却还是别组的。**
#   所以下面**只把 (a) 那类当候补**记进账；(b) 那几行留着，是**当反例用的**（谁将来又想收，先看这张表的代价）。
CAND = [
    ('(a)收', '节奏', ['节奏']),
    ('(a)收', '均线系统', ['均线系统','均线']),   # nova 裁：力度最早由均线面积定义（L15），本组管
    ('(a)收', '完全分类', ['完全分类','完全地分类']),
    ('(b)不收', '中枢', ['中枢']),
    ('(b)不收', '走势类型', ['走势类型']),
    ('(b)不收', '级别', ['级别']),
    ('(b)不收', '线段', ['线段']),
]
print('%-6s %-12s %-6s %-7s %-6s %-6s %s' % ('裁', '补这个词', '表内', '已精读', '★未读', '表外', '从表外进表内的课'))
for cls, name, toks in CAND:
    inb, done, un, out, outl = measure(BASE + [(name, toks)])
    # ★ 方向别搞反：要报的是「**本来在表外、补词后进了表内**」= 从旧表外里减掉新表外。
    #   （写成 `[n for n in outl if n not in b_outl]` 会永远报空 —— 进表内的课已经不在 outl 里了。）
    gained = [n for n in b_outl if n not in outl]
    lost = [n for n in outl if n not in b_outl]      # 反向：补词后**掉出**表内的课（应当为空）
    print('%-6s %-12s %-6d %-7d %-6d %-6d %s%s' % (
        cls, name, inb, done, un, out, ' '.join(str(x) for x in gained) or '—',
        ('  ★反向掉出 ' + ' '.join(str(x) for x in lost)) if lost else ''))
print()
print('★ 这张表要说的是两件事，别混：')
print('  ① **(a) 收是有代价的** —— 例：`均线系统` 一补 ⇒ **★未读 15 → 17**，`10`／`11` 进表内。')
print('     补词场不是"少算几个字"，是**当场多欠两课的账** ⇒ 只能当记账事件（记差值、不回溯改）。')
print('  ② **(b) 那几行是反例**：`中枢` 一补，**已精读 75 → 77** —— 因为 `78`／`91` 本来就是我')
print('     **表外自读**的两课（`read-动力学.txt` 的 77 ＝ 表内 75 ＋ 表外自读 2）。')
print('     ⇒ **(b) 一收，"表外自读"这个中间态就没了**，三组的账从此没有共同口径 —— 所以不收。')
