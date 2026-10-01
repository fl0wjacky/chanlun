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
    if q not in txt:                                   # ①
        bad.append(('①逐字', i, les, a, q[:40]))
        continue
    upto = txt[:txt.index(q)]
    got = upto.count('\n') + 1                         # ② 首次出现处的行号
    if got != a:
        bad.append(('②行号', i, les, a, '实际 %d' % got))
    hits = [n for n, t in LESSONS.items() if q in t]   # ③
    if len(hits) != 1:
        print('  ③跨课 文件%d行 L%d:%d 也在 %s' %
              (i, les, a, ' '.join('第%d课' % n for n in hits if n != les)))

print('台账 %d 条 · 逐字/行号有问题 %d 条' % (len(rows), len(bad)))
for k, i, les, a, extra in bad:
    print('  %s 文件%d行 L%d:%d  %s' % (k, i, les, a, extra))
sys.exit(1 if bad else 0)
