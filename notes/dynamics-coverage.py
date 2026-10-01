#!/usr/bin/env python3
# 动力学组覆盖表 · 脚本现算（不手数）· iris 2026-10-01
# 主尺（去折行）：删掉 \n 后按 token 数出现次数 —— 词被折行劈开也算得到（本人 ㉘ 那条：单行尺会漏）
# 副尺（单行）：grep -o 口径，与结构组 §7 同尺，被折行劈开的漏
# 两档词场：①广谱＝本组概念的通用名（背驰/力度/买卖点/MACD/缺口/合力，全书高频 ⇒ ≥4 是下限不是筛子）
#           ②特异＝只在本组概念里出现、别组不用的词（用来**排序**，与 bram 同做法）
# ★★★ 第 16 批补第六族『合力』（`合力`/`分力`）—— 这是**第三类盲区**的修法，不是加词。
#   起因：清单里早有『合力』一条（6 处出处：L79:51-55 / L79:8 / L45:20-25 / L86:3-10 / L65:73 / L58:76-77），
#   但词场里**根本没有这个词** ⇒ 覆盖表对**自己清单里已有的一条**完全瞎。
#   实测（第 16 批现算）：只有『分力』救回 L74，只有『合力』救回 L83 ⇒ 表内 88 → 90 课，★未读 42 → 44。
#   机制：**覆盖表能查到的，只有词场认识的词。清单长了、词场没跟上 ⇒ 它会说"这课没有本组概念"，
#   而真话是"我的尺不知道有这个词"。**（前两类盲区：①没去找 ②找到只截半句；这是第三类：**尺不认字**。）
#   修法方向：词场应由**清单反推**生成，不能手维护 —— 手维护就一定会漏，而漏了不报错、只报 0。
# ★ 路径口径（2026-10-01 第 13 批补）：原版全是相对路径，必须 cd 到仓库根才跑得动 ——
#   与 bram 那六个 /tmp 输入同一类毛病。现在按 __file__ 定位，**在哪个目录跑都一样**。
import os, glob, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAMILY = [
    ('背驰', ['背驰','背弛','背馳','背离']),
    ('力度', ['力度']),
    ('买卖点', ['买卖点','买点','卖点']),
    ('MACD', ['MACD','黄白线','零轴','0 轴','柱子']),
    ('缺口', ['缺口','跳空']),
    ('合力', ['合力','分力']),   # ★ 第 16 批补（第三类盲区）：清单里早有这条，词场里一直没有
]
NARROW = ['背驰段','盘整背驰','趋势背驰','类背驰','类似背驰','小转大','小级别转大级别','区间套',
          '黄白线','零轴','0 轴','柱子','趋势平均力度','平均趋势力度','走势力度','背驰级别',
          '第一类买点','第二类买点','第三类买点','第三类卖点','红柱子','绿柱子']
MARK = ['就是','称为','叫做','定义为','所谓','必须','不允许','至少']
READFILE = os.path.join(ROOT, 'notes/read-动力学.txt')   # nova 2026-10-01：三组统一用 notes/read-<组名>.txt
READ = {int(x) for x in open(READFILE).read().split()}
if '--write-read' in sys.argv:      # 名单与覆盖表**同一个来源**：由本脚本写回，不手抄
    open(READFILE, 'w').write('\n'.join(str(n) for n in sorted(READ)) + '\n')
    print(f'{READFILE}: {len(READ)} 课（按数值序写回）')
def num(p): return int(re.search(r'lesson-(\d+)', p).group(1))
rows = []
for p in sorted(glob.glob(os.path.join(ROOT, 'archive/chanlun108/text/lesson-*.txt')), key=num):
    raw = open(p, encoding='utf-8').read(); dew = raw.replace('\n','')
    cols = [(sum(dew.count(t) for t in toks), sum(raw.count(t) for t in toks)) for _, toks in FAMILY]
    broad = sum(c[0] for c in cols)
    broad_raw = sum(c[1] for c in cols)
    narrow = sum(dew.count(t) for t in NARROW)
    defline = sum(1 for l in raw.split('\n')
                  if any(t in l for _, toks in FAMILY for t in toks) and any(m in l for m in MARK))
    rows.append(dict(no=num(p), cols=cols, broad=broad, broad_raw=broad_raw,
                     narrow=narrow, defline=defline, lines=len(raw.split('\n'))))
# 清单里已有的引句条数（＝我去过那儿，不等于读过）
led = open(os.path.join(ROOT, 'docs/concepts/inventory_动力学.md'), encoding='utf-8').read()
quotes = {}
for m in re.finditer(r'^L(\d{1,3}):', led, re.M):
    quotes[int(m.group(1))] = quotes.get(int(m.group(1)), 0) + 1
inb = [r for r in rows if not (r['broad'] < 4 and r['narrow'] == 0)]
out = [r for r in rows if (r['broad'] < 4 and r['narrow'] == 0)]
rows_n = sorted(rows, key=lambda r: (-r['narrow'], -r['broad'], r['no']))
rows_b = sorted(rows, key=lambda r: (-r['broad'], -r['narrow'], r['no']))
print('## 覆盖表 · 表内 %d 课（脚本现算：`notes/dynamics-coverage.py`）\n' % len(inb))
print('**入表条件**：广谱信号 ≥4 **或** 特异词 >0（`broad < 4 and narrow == 0` 的课不入表，'
      '**表外是 %d 课，不是没有课** —— 见 §15.3）。' % len(out))
print('排序：**特异词信号**从高到低（与中枢走势组同做法）。`信号(广谱)` 列同时给单行尺，'
      '两者的差＝被折行劈开的命中。`状态` 只对**本表这一把尺**负责：★未读 ≠ 该课没料，'
      '已精读 ＝ 整课逐行读完（含附录），不是“点读过”。\n')
print('| 课 | 背驰 | 力度 | 买卖点 | MACD | 缺口 | 特异词 | 信号(广谱) | 单行尺 | 定义句行 | 课长 | 清单引句 | 状态 |')
print('|' + '---|' * 12)
for r in rows_n:
    if r['broad'] < 4 and r['narrow'] == 0: continue
    c = ' | '.join(str(d) if d == rr else f'{d}({rr})' for d, rr in r['cols'])
    st = '已精读' if r['no'] in READ else '★未读'
    print(f"| {r['no']} | {c} | **{r['narrow']}** | **{r['broad']}** | {r['broad_raw']} | {r['defline']} | {r['lines']} | {quotes.get(r['no'],0)} | {st} |")
b4 = [r for r in rows if r['broad'] >= 4]
print(f"\n**账目**：广谱信号 ≥4 的课 **{len(b4)} 课 / {sum(r['lines'] for r in b4)} 行**"
      f"（全 108 课共 {sum(r['lines'] for r in rows)} 行）· 其中特异词 >0 的 {len([r for r in b4 if r['narrow']>0])} 课 ·"
      f" 零命中 {len([r for r in rows if r['broad']==0])} 课；"
      f"**表外 {len(out)} 课**（零命中 {len([r for r in out if r['broad']==0])} 课 ＋ "
      f"广谱 1-3 且特异词 0 的 {len([r for r in out if r['broad']>0])} 课："
      + ' '.join(str(r['no']) for r in out if r['broad']>0) + "）")
