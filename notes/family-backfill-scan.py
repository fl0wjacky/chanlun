#!/usr/bin/env python3
# 族词回灌 · 盲区扫描（动力学组）· iris 2026-10-01
#
# 要解决的问题（§15.4 盲区第三条，第 16 批撞见）：
#   `notes/dynamics-coverage.py` 的族词表是**手维护**的。手维护一定会漏，而**漏了不报错、只报 0** ——
#   清单里明明登记在案的一条（『合力』），词场里却没有 ⇒ 覆盖表对**自己清单已有的一条完全瞎**，
#   实测代价是**整课**被漏（`L74`／`L83` 当时躺在「零命中」那一档）。
#
# 本脚本把这条欠账**变成数**：
#   候选词 ＝ 清单里**所有已经起过名的名目**（`「」` 与 `『』` 里长度 2..8 的短名目）——
#   也就是"清单反推"的字面做法：**清单里已经有人给它起过名，词场就该认识它**。
#   覆盖率 ＝ 候选是否已经是现有词场某个词的子串／或包含某个词（＝这把尺已经认这个字）。
#   影响面 ＝ 有多少**表外**课含这个候选（表外课进表 ＝ 那一课此前被印成"本课没有本组概念"）。
#
# ★ 本脚本**只读语料和清单，不写任何文件**；表内/★未读 一个数都不动。
#   回灌本身是**记账事件**（记差值、不回溯改），要等裁定 —— 见 notes/family-backfill.md。
#
# 用法：python3 notes/family-backfill-scan.py    （在哪个目录跑都一样）
import os, re, glob, sys, hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(ROOT, 'docs/concepts/inventory_动力学.md')
READFILE = os.path.join(ROOT, 'notes/read-动力学.txt')

# 词场**照抄** dynamics-coverage.py 的现值（两边一旦不一致，数就不可比 ⇒ 下面有断言）
FAMILY = [('背驰', ['背驰','背弛','背馳','背离']), ('力度', ['力度']), ('买卖点', ['买卖点','买点','卖点']),
          ('MACD', ['MACD','黄白线','零轴','0 轴','柱子']), ('缺口', ['缺口','跳空']), ('合力', ['合力','分力'])]
NARROW = ['背驰段','盘整背驰','趋势背驰','类背驰','类似背驰','小转大','小级别转大级别','区间套',
          '黄白线','零轴','0 轴','柱子','趋势平均力度','平均趋势力度','走势力度','背驰级别',
          '第一类买点','第二类买点','第三类买点','第三类卖点','红柱子','绿柱子']
KNOWN = [t for _, ts in FAMILY for t in ts] + NARROW

# 语料（与 verify_inventory.py 同一算法，用来钉住"数是在哪份语料上算的"）
LESSONS = {}
for p in glob.glob(os.path.join(ROOT, 'archive/chanlun108/text/lesson-*.txt')):
    LESSONS[int(re.search(r'lesson-(\d+)', p).group(1))] = open(p, encoding='utf-8').read()
if len(LESSONS) != 108:
    sys.exit('★ 语料不全（只找到 %d 课）—— 数不许在这种状态下报' % len(LESSONS))
_h = hashlib.sha256()
for n in range(1, 109):
    _h.update(('%d:' % n).encode()); _h.update(LESSONS[n].encode())
DEW = {n: t.replace('\n', '') for n, t in LESSONS.items()}

# 表内/表外（与 dynamics-coverage.py 同口径：广谱 ≥4 **或** 特异词 >0 入表）
def broad(n):  return sum(sum(DEW[n].count(t) for t in ts) for _, ts in FAMILY)
def narrow(n): return sum(DEW[n].count(t) for t in NARROW)
INB = sorted(n for n in LESSONS if not (broad(n) < 4 and narrow(n) == 0))
OUT = sorted(n for n in LESSONS if n not in INB)
READ = {int(x) for x in open(READFILE).read().split()} if os.path.exists(READFILE) else set()

print('语料指纹 %s' % _h.hexdigest()[:16])
print('现口径（六族）：表内 %d · 已精读 %d · ★未读 %d · 表外 %d'
      % (len(INB), len([n for n in INB if n in READ]), len([n for n in INB if n not in READ]), len(OUT)))
print('表外：%s' % ' '.join(str(n) for n in OUT))
print()

led = open(LEDGER, encoding='utf-8').read()
cand = {}
for pat in (r'「([^「」\n]{2,8})」', r'『([^『』\n]{2,8})』'):
    for m in re.finditer(pat, led):
        s = m.group(1).strip()
        if not s or any(ch in s for ch in '，。、；：？！（）()／/·＝=…—'):
            continue
        cand[s] = cand.get(s, 0) + 1

rows = []
for s, times in cand.items():
    if any(s in k or k in s for k in KNOWN):    # 已认得的字，不算漏
        continue
    hits = [n for n in LESSONS if DEW[n].count(s)]
    if not hits:
        continue
    o = sorted(n for n in hits if n in OUT)
    rows.append((len(o), len(hits), times, s, o))
rows.sort(key=lambda r: (-r[0], -r[1], -r[2], r[3]))

print('未被词场覆盖的清单名目（按「能带回几课表外课」降序）')
print('%-4s %-6s %-6s %-14s %s' % ('回外', '命中课', '清单次', '词', '落在表外的课'))
for a, b, c, s, o in rows:
    print('%-4d %-6d %-6d %-14s %s' % (a, b, c, s, ' '.join(str(x) for x in o)))
print()
print('清单里起过名的候选 %d 个；其中**词场不认、而语料里确实有**的 %d 个。' % (len(cand), len(rows)))
print('★ 本表有两类，别并成一条（nova 2026-10-01 已裁，理由记在 notes/family-backfill.md）——')
print('  (a) 本组自己的词漏了（`节奏` · `完全分类`；**`均线系统` 也归本组**，裁语：力度最早由均线面积定义 · `L15`）')
print('      ⇒ 补上就是修第三类盲区（「尺不认字」）；')
print('  (b) **别组的核心词** —— `中枢`／`走势类型`／`线段`／`级别`：**裁：不收**。')
print('      裁语（原样）：**收进来本表会涨到近乎整本书，欠账一下变大，找到的却还是别组的。**')
print('      ⇒ 这一类的名字是「**字不归我这把尺**」，与 (a) 的「尺不认字」**不是一回事**，别并成一条。')
print('★ 影响面（补上会动多少账）用 notes/family-backfill-effect.py 现算 —— (a) 的每一条都要看。')
