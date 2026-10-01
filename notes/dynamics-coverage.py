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
# ★★ 第 20 批加：**表头自检** —— 表头格子数必须等于数据行格子数。
#   起因（本批自查时撞见）：第 16 批给 FAMILY 加了第六族（合力），**表头那行没跟着改**
#   ⇒ 表头比数据**少一格**，于是「缺口」之后每一列的标签都**错位一格**
#   （读者会把「合力」那一格的 0 读成「特异词」，把特异词读成「信号(广谱)」…），
#   而且在严格 GFM 下多出来的那一格会被丢掉（**状态列整个看不见**）。
#   ⇒ **加族词是真加，改表头不是顺手事** —— 所以让它自己数。
COLS = 1 + len(FAMILY) + 7      # 课 ＋ 各族 ＋ 特异词/信号(广谱)/单行尺/定义句行/课长/清单引句/状态
HEAD = '| 课 | ' + ' | '.join(n for n, _ in FAMILY) + ' | 特异词 | 信号(广谱) | 单行尺 | 定义句行 | 课长 | 清单引句 | 状态 |'
WIDTH_BAD = []   # 表头/数据行宽度不合的课号
if len([c for c in HEAD.split('|')]) - 2 != COLS:
    print(f'★★ 表头自检：表头 {len(HEAD.split("|"))-2} 格 vs 应为 {COLS} 格（族词加了、表头没改）', file=sys.stderr)
print(HEAD)
print('|' + '---|' * COLS)
for r in rows_n:
    if r['broad'] < 4 and r['narrow'] == 0: continue
    c = ' | '.join(str(d) if d == rr else f'{d}({rr})' for d, rr in r['cols'])
    st = '已精读' if r['no'] in READ else '★未读'
    LINE = f"| {r['no']} | {c} | **{r['narrow']}** | **{r['broad']}** | {r['broad_raw']} | {r['defline']} | {r['lines']} | {quotes.get(r['no'],0)} | {st} |"
    if len(LINE.split('|')) - 2 != COLS:
        WIDTH_BAD.append((r['no'], len(LINE.split('|')) - 2))
    print(LINE)
#   ★ 只喊一次 ＋ 报总数：**一次红 90 行的检查等于没检查**（人会把整屏忽略掉）。
if WIDTH_BAD:
    print(f'★★ 表头自检：数据行 {WIDTH_BAD[0][1]} 格 vs 表头 {COLS} 格'
          f'（首例 L{WIDTH_BAD[0][0]}，共 {len(WIDTH_BAD)} 行；族词加了、表头没跟）', file=sys.stderr)
# ★★ 第 17 批加：**抬头自检** —— 脚本算的课数 vs 交付文件此刻自己写的课数。
#   起因（atlas 1359 提的，原文「你这次是靠人工比出来的，该由脚本比」）：
#   第 16 批我改了 §15.22 的新数，却忘了把下面那张抄回来的表一起重生成 ⇒ **同一个数在同一个文件里有两个版本，
#   只有新的那份带记号**。谁读文件谁读到旧的那半（atlas 就是这么读到 88 的）。
#   ⇒ 这条自检的用处不是"跑完总是绿的"，而是**在文件已陈旧时当场喊**：它红 = 交付文件没重新生成。
_m = re.search(r'覆盖表 · 表内 (\d+) 课', led)
if _m and int(_m.group(1)) != len(inb):
    print(f'★★ 抬头自检：不一致 —— 脚本 {len(inb)} 课 vs 文件抬头 {_m.group(1)} 课（交付文件没重新生成）', file=sys.stderr)
else:
    print(f'抬头自检：一致（表内 {len(inb)} 课）', file=sys.stderr)
b4 = [r for r in rows if r['broad'] >= 4]
ACCT = (f"**账目**：广谱信号 ≥4 的课 **{len(b4)} 课 / {sum(r['lines'] for r in b4)} 行**"
        f"（全 108 课共 {sum(r['lines'] for r in rows)} 行）· 其中特异词 >0 的 {len([r for r in b4 if r['narrow']>0])} 课 ·"
        f" 零命中 {len([r for r in rows if r['broad']==0])} 课；"
        f"**表外 {len(out)} 课**（零命中 {len([r for r in out if r['broad']==0])} 课 ＋ "
        f"广谱 1-3 且特异词 0 的 {len([r for r in out if r['broad']>0])} 课："
        + ' '.join(str(r['no']) for r in out if r['broad']>0) + "）")
# ★★ 第 20 批加：**账目自检 ＋ 进度自检** —— 上面那条自检只盯"课数"一个数，
#   而每批真正会动的数是另两颗：**已精读／★未读**（存在 §15.3 散文里，脚本管不着）。
#   第 16 批那次旧数的形状就是"改了这边忘了那边"，所以这里把两颗数也接上。
#   规则：**找不到也不许算绿**（"没得比"和"比对了且相同"必须长得不一样）。
def _chk(name, pat, want):
    _f = re.search(pat, led)
    if _f is None:
        print(f'{name}自检：文件里找不到那一行 —— 没得比（**这不算绿**）', file=sys.stderr)
    elif tuple(int(g) for g in _f.groups()) != want:
        print(f'★★ {name}自检：不一致 —— 脚本 {want} vs 文件 {tuple(int(g) for g in _f.groups())}'
              f'（交付文件没重新生成）', file=sys.stderr)
    else:
        print(f'{name}自检：一致', file=sys.stderr)
DONE = len([r for r in inb if r['no'] in READ])
#   账目那一行比较长，整行比（不走 _chk 的元组比法）：
_a = re.search(r'\*\*账目\*\*：广谱信号[^\n]*', led)
if _a is None:
    print('账目自检：文件里找不到账目行 —— 没得比（**这不算绿**）', file=sys.stderr)
elif _a.group(0) != ACCT:
    print('★★ 账目自检：不一致 —— 文件里第一处账目与本次现算的不同（交付文件没重新生成）', file=sys.stderr)
else:
    print('账目自检：一致', file=sys.stderr)
_chk('进度', r'表内已精读 \*\*(\d+)\*\* · ★未读 \*\*(\d+)\*\*', (DONE, len(inb) - DONE))
_chk('读名单', r'读名单 `notes/read-动力学.txt` 现在 (\d+) 课', (len(READ),))
print('\n' + ACCT)
