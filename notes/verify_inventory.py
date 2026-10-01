#!/usr/bin/env python3
# 清单引句台账复核 · 三判据 ＋ 五格分类（iris）
#
# ★ 重建说明（2026-10-01，第 12 批）：这个脚本原先只在 `docs/concepts/inventory_动力学.md`
#   的「附：复算命令」里被引用，**但仓里和 git 历史里都没有这个文件**（`git log --all` 查过）
#   —— 也就是说，之前报的「台账 N 条 · 逐字/行号 0 条」**别人复算不出来**。
#   本文件是照 §2 的三判据重写的。★ 它是**重建版，不是原件**：
#   判据按文档写死了，数对不对以本文档 §15.10 五 的对账表为准。
#
# 三判据（缺一条就不叫核过）：
#   ① 逐字命中：q.replace("↵","\n") 在本课里取子串（**不删空格**）
#   ② 行号对得上：命中位置换回行号，与标的 L课:行-行 比
#   ③ 命中的课有几课：逐字命中证不了出处唯一（语料里整段复述）
#
# 用法：python3 notes/verify_inventory.py docs/concepts/inventory_动力学.md
#
# ★ 路径口径（2026-10-01 第 13 批补）：原版把 CORPUS 写成**相对路径**，
#   必须 cd 到仓库根才跑得动 —— 与 bram 那六个 /tmp 输入是同一类毛病。
#   现在按 __file__ 定位，**在哪个目录跑都一样**。
import os, re, sys, glob, hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'docs/concepts/inventory_动力学.md')
CORPUS = os.path.join(ROOT, 'archive/chanlun108/text')

LESSONS = {}
for p in sorted(glob.glob(CORPUS + '/lesson-*.txt')):
    n = int(re.search(r'lesson-(\d+)', p).group(1))
    LESSONS[n] = open(p, encoding='utf-8').read()

# 语料指纹（与文档「复算命令」同一算法）
h = hashlib.sha256()
for n in range(1, 109):
    h.update(('%d:' % n).encode())
    h.update(LESSONS[n].encode())
print('语料指纹', h.hexdigest()[:16])

ROW = re.compile(r'^L(\d{1,3}):(\d+)(?:-(\d+))?\s+「(.*)」\s*$')

rows, bad = [], []
for i, line in enumerate(open(LEDGER, encoding='utf-8').read().split('\n'), 1):
    m = ROW.match(line)
    if not m:
        continue
    les, a, b, q = int(m.group(1)), int(m.group(2)), m.group(3), m.group(4)
    q = q.replace('↵', '\n')
    rows.append((i, les, a, b, q))

    txt = LESSONS.get(les, '')
    # ★★ 2026-10-01 第 14 批：**首/尾 `…` 的截断引，本器此前一律判①逐字不过**。
    #   与自查尺是同一个盲点（那把是 `len(segs) < 2`），本批两处一起修。
    #   规矩不变：**`…` 是唯一允许的不连续，且必须显式打出**；每片仍须逐字、仍须同课、仍须按序。
    segs = [s for s in q.split('…') if s.strip()]
    if not segs:
        bad.append(('①逐字', i, les, a, '空块'))
        continue
    pos, ok, firstline = 0, True, None
    for si, s in enumerate(segs):
        p = txt.find(s, pos)
        if p < 0:
            ok = False
            break
        if si == 0:
            firstline = txt[:p].count('\n') + 1
        pos = p + len(s)
    if not ok:                                         # ①
        bad.append(('①逐字', i, les, a, '（片片查）' + q[:40]))
        continue
    # ② 行号：**有前导 `…` 的行不查首行**（那正是"从句子中间开始引"的声明），
    #    其余仍要求首片首次出现处整除起始行号。
    if not q.startswith('…') and firstline != a:
        bad.append(('②行号', i, les, a, '实际 %d' % firstline))
    # ③ 用**最长的一片**查跨课（用 segs[0] 会在 `…` 行上把「本 ID 理论的」这种短头当线索，噪声极大）
    probe = max(segs, key=len)
    hits = [n for n, t in LESSONS.items() if probe in t]
    if len(hits) != 1:
        print('  ③跨课 文件%d行 L%d:%d 也在 %s' %
              (i, les, a, ' '.join('第%d课' % n for n in hits if n != les)))

# ★★★ 2026-10-01 第 15 批加：**③掐尾**（tail-truncation）—— 与自查尺同一栏、同一判据。
#   事件：`L29:214` 那行我只引了前半句、把「这两个前提，明天的帖子都会说到」掐掉且没打 `…`，
#   **该行绿了三批** —— 因为**掐掉尾巴的前缀仍是一个连续子串**，①逐字判据在构造上看不见它。
#   ⇒ 与自查尺同规矩：**引原文至少引到句号或分号；中途截断必须打 `…`**。
#   ★ 本栏**只列表、不计入 bad、不影响退出码** —— 引半句在原文里是常态，它是**审查线索**不是缺陷清单。
#   ★ 三道闸（与自查尺一致）：块 ≥12 字 · 块末不是句末标点 · **语料这句话从块尾到句末还剩 ≥12 字**。
#
# ★★★ 2026-10-01 第 15 批末 · nova `seq 1307` 裁定，**本栏降级为读课时的自查提示**：
#   「至少引到句号或分号」**只管整句引文**（拿来当证据、当定义的那种）；术语／短语不在这条规矩里。
#   **截引不做机器统计、不报数、不开补丁批** —— 754／739 那类数不进汇总。
#   ⇒ 所以：**本栏的条数不得写进文档账目、不得进任何汇总表**，它只在人读课时提示"这几行去看一眼"。
#   ⇒ 本批据此**真去看了**排头那几条，改掉 3 行（`L30:38`／`L30:62`／`L30:44`，都是「两个界限」这一族，
#     属"拿来当定义或当边界的那一句"，按 nova 的规矩**该由读的人自己确认引全**，不是补丁批）。
TERM_CUT = '。！？…”」』）)!?;；：'
tail = []
for ln, line in enumerate(open(LEDGER, encoding='utf-8').read().split('\n'), 1):
    m = ROW.match(line)
    if not m:
        continue
    les, a, b, q = int(m.group(1)), int(m.group(2)), m.group(3), m.group(4)
    qq = q.replace('↵', ' ').rstrip()
    if not qq or qq.endswith('…') or qq[-1] in TERM_CUT:
        continue
    if len(qq) < 12:
        continue
    if qq.startswith('教你炒股票') or qq.startswith('教你'):   # 课题行不是"引了半句"
        continue
    txt = LESSONS.get(les, '')
    p = txt.find(q.replace('↵', '\n'))
    if p < 0:
        continue
    # ★★ 第四道闸（本批补，逐条看过剩下的才敢加）：**声明了行范围的"整段行引"不是掐尾。**
    #   证据：剩下的两条（`L29:196-197`／`L45:38-40`）引文**正好等于语料该行范围的全文**，
    #   句子之所以没引完，是**语料自己在那一行断了行**（§9 第 1 种：硬折行），不是引者掐的。
    #   ⇒ 判据：引文（`↵`→换行）**恰好等于**语料 a-1..b-1 行的拼接。
    if b:
        span = '\n'.join(txt.split('\n')[a - 1:int(b)])
        if q.replace('↵', '\n') == span:
            continue
    rest = txt[p + len(q.replace('↵', '\n')):]
    mm = re.search(r'[。！？]', rest)
    n = len(rest if mm is None else rest[:mm.start()])
    if n >= 12:
        tail.append((n, ln, les, a))

print('台账 %d 条 · 逐字/行号有问题 %d 条' % (len(rows), len(bad)))
if tail:
    tail.sort(reverse=True)
    print('★ ③掐尾（审查线索，不计入有问题）: %d 条 —— 按"原文还剩多少字"从多到少列前 6：' % len(tail))
    for n, ln, les, a in tail[:6]:
        print('    剩 %3d 字｜文件%d行 L%d:%d' % (n, ln, les, a))
for k, i, les, a, extra in bad:
    print('  %s 文件%d行 L%d:%d  %s' % (k, i, les, a, extra))
sys.exit(1 if bad else 0)
