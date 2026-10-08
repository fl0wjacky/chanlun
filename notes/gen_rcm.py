import re,subprocess,collections,sys
import os
_BASE=os.environ.get('RCM_BASE','origin/main'); _BASE_NAME=os.environ.get('RCM_BASE_NAME','main')   # 表头写的『基于 …』默认取 origin/main，不取本支 HEAD；跟落地支一起合时可指定（比如 RCM_BASE=e4546d8 RCM_BASE_NAME=land-b4b）
M=subprocess.run(['git','rev-parse','--short',_BASE],capture_output=True,text=True).stdout.strip()
files=subprocess.run(['git','-c','core.quotepath=off','ls-tree','--name-only','HEAD','docs/spec/'],capture_output=True,text=True).stdout.split()
topic=[f for f in files if f.endswith('.md') and not f.split('/')[-1].startswith('第')]
idre=r'(?:S-待定-\d|(?:W|M|J|T|Z|R|C|S|P|D)\d{1,2}(?:-\d+)?)'
pat=re.compile(r'(?<![A-Za-z0-9])('+idre+r')(?![0-9XS-])')   # 不收『S1X1S2X2…』『S1S2…Sn』那种笔序列记号
occ=collections.OrderedDict()
for f in topic:
    t=subprocess.run(['git','show','HEAD:'+f],capture_output=True,text=True).stdout
    for n,line in enumerate(t.split('\n'),1):
        for m in pat.finditer(line):
            k=m.group(1); fn=f.split('/')[-1]
            # 同一个『字母＋数字』在不同文件里是两套编号，按文件分开（Nova 10-08 12:54 逮到 P 撞名）
            if re.match(r'P\d',k): k=('笔' if fn in ('笔.md','分型.md') else '探针')+k
            if re.match(r'C\d',k) and fn=='复权.md': k='不变量'+k
            occ.setdefault(k,[]).append((fn,n,line))
def first_bold(l):
    b=re.search(r'\*\*(.+?)\*\*',l);return b.group(1) if b else ''
def score(k,o):
    f,n,l=o;s=0;fb=first_bold(l)
    if re.search(r'规则 ?'+re.escape(k)+r'(?![0-9-])',l): s+=10
    if re.search(r'(?<![A-Za-z0-9])'+re.escape(k)+r'(?![0-9-])',fb): s+=6
    if l.lstrip().startswith('### ') and k in l: s+=6
    if re.search(r'[（(]'+re.escape(k)+r'[，,）)]',l[:200]): s+=3
    if '~~' in l: s-=4
    return s
def label(k,l):
    hm=re.match(r'\s*#+\s*(.*)',l)
    txt=hm.group(1) if hm else (first_bold(l) or l.strip('-* '))
    m=re.search(r'规则 ?'+re.escape(k)+r'[^：:]*[：:]\s*\**(.+?)\**(?:$|\s)',l)
    if m: txt=m.group(1)
    txt=re.sub(r'[`|*]','',txt).strip()
    return (txt[:70]+'…') if len(txt)>70 else txt
KNOWN={
 'R6':('core/trend.py `_try_confirm` 参照中枢那一行（已进 main）','已实现'),
 'J12':('tools/selfcheck.py『J12：买卖点随走势分界变了』反向断言','已实现'),
 'J18':('tools/j18_check.py（只报警）','已实现'),
 'J19':('tools/j19_check.py（只报警）','已实现'),
 'T16':('core/signals.py MEASURE_NOTE ＋ web/app.js 芯片悬停','已实现'),
 'S7':('core/segment.py:428 `_case_at`（`S7_NOW`：等不到结局 ⇒ 分界后单独做包含、构成分型就判 case 3 暂定，段带 tentative；:561 暂定以后整截算未完成）；复核 :688 `verify_by_definition` 独立再写一遍','已实现（第四批 land-b4b：Bram s7-s10-s12 0948c9e；盲推卷两份都过；L79 题 5 出 2 段、3 暂定）'),'S10':('core/segment.py:460 `S10_TIE`：① 追平算破（:421、:424，X 终点只从 r>k+2 起算，自检有反向臂）；② V 跟 e1 一端相同算分界（:396）；_start_check、verify_by_definition :665 跟着改','已实现（第四批 land-b4b；zec15 完成段 186→188，D2-8 刀 787.96→805.0）'),'S12':('core/segment.py `_case_at` 第一种情况：先破 X 哪一头定结局（谁先被破），定了不回头改；暂定（S7）结局没定前后面不再往下切（:561）','已实现（第四批 land-b4b；跟 S-待定-3 同一套，附 3′ 第 3 步）'),
 'S-待定-1':('core/segment.py:374-392（Bram 10-08 摸底）','已实现'),
 'W53':('—','不进代码（Nova 10-08 11:34）'),'W26':('—','未实现，这批不做（W26 后半）'),
 'C3':('core/pen.py min_gap（第三批 ①参数 ②默认 6）','进行中'),
 '笔P2':('core/kline.py `fractals()`：第三根标准化 K 线出现即认分型','已实现（第三批 B10 核过）'),
 '笔P3':('core/kline.py `_standardize_span` 开头那段（整段互相包含时取头一根）','程序自定（原文未给，第三批 B10）'),
 '笔P4':('—','不进代码（只是 spec 位置调整，第三批 B10）'),
 '笔P5':('core/kline.py 标准化后取极值（端点比合并后的 K 线）','已实现（第三批 B10：4.7% 影线越过端点，前端约定行加说明）'),
 '笔P7':('core/kline.py 合并时记 ih／il（出极值的那根原始 K 线）','已实现（第三批 B10）'),
 '笔P9':('core/kline.py `quantize()` 按最小价位取整后逐位比','已实现（第三批 B10）'),
 '笔P8':('core/kline.py 合并时 `bh > p["h"]` 才换 ih（并列取前一根）','不改（Nova 10-08 12:56：L81 数据不够、上下文讲的是包含）'),
}

# ---- Bram 10-08 填：代码位置／状态（main 3718ca8 上逐条看过代码；行号是 def 那一行）----
# W、M、J、T、Z 没列在这里的 ⇒ 只是记原文，默认『不进代码』（Nova 13:42）。
T='core/trend.py'; SG='core/segment.py'; PN='core/pen.py'; KL='core/kline.py'; CT='core/center.py'; SI='core/signals.py'; TC='tools/trend_check.py'
KNOWN.update({
 'C3':(f'{PN} `MIN_GAP_DEFAULT`＝3 ＋ web/server.py `PEN_MIN_OPTIONS`（6／7 开关）＋ tradingview/chanlun.pine `penMin`','已实现（main 3718ca8）'),
 'C6':(f'{PN}:254 `check_pens`：顶分型最高 K 线高于底分型最低 K 线（第 77 课），不要求公共部分','已实现'),
 'C7':(f'{KL}:111 `fractals()`：只认二（顶）、四（底）；一、三（上升／下降 K 线）不出','已实现'),
 'C8':(f'{KL}:39 `_standardize_span`：方向看最后两根（新的更高 ⇒ 向上）','已实现'),
 'C9':(f'{PN}:118 `build_pens` 的待定分型／`fix_start`：后面走出来就作废上一笔、换端点','已实现'),
 '笔P1':(f'{PN}:118 `build_pens` `feed()`：成不了笔的分型不进端点序列；同类只留更极端的','已实现（Bram 10-08 核代码）'),
 '笔P6':(f'{PN}:118 `build_pens` `feed()` 的 pend：太近、却比前前个端点更极端的反向分型记待定，上一笔包不住它就回头换','已实现（Bram 10-08 核代码）'),
 'S8':(f'{SG}:333 `_case_at` ④：V 之后的同类元素按分型方向做包含；E1、E2 之间不做','已实现'),
 'S9':(f'{SG}:428 `HEAD_EXT_FIX`（图头修法，card-2783fa1f），不是照 S9 原样写的','已实现（等价：严格照 S9 判 0/25 不同，见表外待办）'),
 'S11':(f'{SG}:333 `_case_at` ③ 提前定（先破 X 终点 ⇒ 新段成立）＋ {SG}:260 `_start_check` `S11_START_OK`（自检 A 第三种合法）','已实现'),
 'S-待定-1':(f'{SG}:333 `_case_at` ③：X 之后第一个反向线段破没破 V（原写 374-392，C3 以后行号挪了）','已实现'),
 'S-待定-2':(f'{SG}:333 `_case_at` 判的是起点已定那一段的终点候选；图头那一段走 `HEAD_EXT_FIX`','已实现（结构保证：非图头段的起点只在上一段确认后才推进，core/segment.py:528；图头那一类见 S9，严格照 S9 0/25 不同；Bram 13:50、Atlas 认）'),
 'S-待定-3':(f'{SG}:333 `_case_at` ③ 的 for 循环：反向线段确认之前，先破 V ⇒ ①、先破 X 终点 ⇒ 新段','已实现'),
 '不变量C1':('tools/selfcheck.py:405-406 `preprocess(adjust="none")` 断言恒等','已实现'),
 'D1':(f'{T}:395 `trend_v3`（整页规则的入口）','已实现'),
 'D1-1':(f'{CT}:114 `find_centers` 一直延伸 ＋ {T}:241 `_units` 扩展升级','已实现'),
 'D1-2':(f'{T}:395 `trend_v3` 只出一种分解（确定的）','已实现'),
 'D1-3':(f'{TC} 不变量 ②（一高一低交替、D2-8 补刀除外）','已实现（推论，由 D2-3／D3 保证；照实标出相邻盘整）'),
 'D2':(f'{T}:152 `find_bounds`','已实现'),
 'D2-0':(f'{T}:56 `_standardize`','已实现'),
 'D2-1':(f'{T}:152 `find_bounds` 候选死点（一样极取后一个）','已实现'),
 'D2-2':(f'{T}:121 `_try_confirm`','已实现'),
 'D2-3':(f'{T}:152 `find_bounds(alternate=True)`','已实现'),
 'D2-4':(f'{T}:37 `_centers_with_cuts`','已实现'),
 'D2-5':('core/trend.py:399 `_death_types`：每把 D2-2 刀标 death／death_why（趋势背驰／盘整背驰／小转大／盘整·未见背驰／比不了），D2-8 补刀单列；:396 一买一卖对不上刀就挂 death_warn；小转大的二类 :458 `_xzd_seconds`（刀后第二段终点，xzd_seconds 键，不进 signals，守 J12）','已实现（第四批 land-b4b：Bram d25-death＋Atlas d25-mismatch／m29-code；25 份 96 刀：趋势背驰 1、盘整背驰 10、小转大 4（同一点）、盘整·未见背驰 18、比不了 59、D2-8 4）'),
 'D2-6':(f'{T}:199 `pending`','已实现'),
 'D2-7':(f'{T}:152 `find_bounds(check_empty=True)` ＋ `_BLOCK_RETRACTED`','已实现'),
 'D2-8':(f'{T}:350 `_d28_cuts`','已实现'),
 'D3':(f'{T}:219 `_regroup` ＋ {T}:241 `_units`','已实现'),
 'D3-1':(f'{T}:299 `_layer`：先按分界切开，再在段里判扩展','已实现'),
 'D3-2':(f'{T}:219 `_regroup`（3+3+3 重算，不拼 DD／GG）','已实现'),
 'D3-3':(f'{T}:284 `classify`（读法 A）','已实现'),
 'D3-4':(f'{T}:241 `_units` `_D3_LIVE_TAIL`','已实现'),
 'D4':(f'{T}:395 `trend_v3` seg_centers（按刀分组重算）','已实现（画框用限方向那组，见 D6-4）'),
 'D4-1':(f'{T}:37 `_centers_with_cuts`；{TC} 不变量 ② 框不跨分界','已实现'),
 'D4-2':(f'{T}:395 `trend_v3`：只按已确立的分界切','已实现'),
 'D4-3':(f'{T}:241 `_units` 合成，不断框','已实现'),
 'D4-4':(f'{TC} ③ 见证（zec15 bar 1900 不切框）','已实现'),
 'D5':(f'{T}:112 `_done`（次级别＝已完成线段）','已实现'),
 'D5-1':(f'{T}:112 `_done`；笔层类中枢不进 trend_v3','已实现'),
 'D6':(f'{T}:299 `_layer` 限方向那一组','已实现'),
 'D6-1':(f'{T}:299 `_layer`','已实现'),
 'D6-2':(f'{T}:299 `_layer`（第一个中枢的豁免）','已实现'),
 'D6-3':(f'{T}:299 `_layer`（盘整段、图头不限）','已实现'),
 'D6-4':(f'{T}:299 `_layer`（先限方向判段型）＋ `_D6_BASE_ONLY`','已实现'),
 'R2':('同 D1-2','原文依据，不另进代码'),'R5':('同 D2-1','原文依据，不另进代码'),'R7':('同 D2-2','原文依据，不另进代码'),
 'R11':('同 D2-5','原文依据（D2-5 已实现，第四批）'),'R12':('同 D2-6','原文依据，不另进代码'),'R13':('同 D2-7','原文依据，不另进代码'),
 'R16':('同 D3-2','原文依据，不另进代码'),'R17':('同 D3-3','原文依据，不另进代码'),'R18':('同 D3-4','原文依据，不另进代码'),
 'R20':('同 D5-1','原文依据，不另进代码'),'R30':('—','不进代码（层数下限的原文依据）'),
 '探针P1':(f'{TC}:359 --self-test 臂 P1（regroup=False）','已实现'),
 '探针P2':(f'{TC}:360 --self-test 臂 P2（alternate=False）','已实现'),
 '探针P3':(f'{TC} --self-test P3 那颗牙（不标准化那条路上量）','已实现'),
 '探针P4':(f'{TC} ③ D4-4 见证（笔层一买 213.46 不切框）；原 core/cut.py 已退役','已实现（换了见证）'),
 '探针P5':(f'{TC}:361 --self-test 臂 P5（check_empty=False）','已实现'),
 '探针P6':(f'{TC} D3-3 读法的反向验证（读法 B）','已实现'),
 'J17':('tools/j17_check.py 的 A（落地支 land-j17-stats，待合 main）','已实现（只统计：6 根下 A 4/47 过不了 5%，Nova 13:45 定落）'),
 'W61':('tools/j17_check.py 的 B（同上）','已实现（只统计：6 根下 B 15/47≈32%）'),
 'M11':(f'{CT}:114 `find_centers`：`ZG >= ZD` 就成立（重叠成一个价位也算）','已实现'),
 'M13':('—','**未实现（开关）**（Nova 10-08 06:47 定命名开关；10-08 14:4x 量：段级 25 份只 4 颗，全在线上 ZEC 15m 一颗二卖后，Nova 14:48 定放着，默认档不动）'),
 'M28':(f'{CT}:114 `find_centers` 三买三卖终结 ＋ {SI}:297 `signals` 第三类','已实现'),
 'M29':('core/signals.py:361 `signals` 第二类：不创新低（高）⇒ 出；创新了但对一类那段有盘整背驰（:297 `_panzheng`，跟 D2-5 共用）⇒ 出；都不是 ⇒ 不出；why 按方向写，weak 先留着给前端','已实现（第四批 land-b4b：agent/atlas/m29-code，含 Bram 的 Pine；25 份段级 0 删 0 加；tools/m29_check.py 主跑＋自检）'),
 'W24':(f'{SI}:297 `signals`：一买一卖只从第二个中枢起判（`range(1, len(Z))`）','已实现'),
 'W46':(f'{SI}:243 `beichi`（一买＝背驰点）＋ core/trend.py `_death_types`（小转大标注）','已实现（行为一直对；第四批起刀上标「小转大」，小转大的二类见 D2-5）'),
 'W49':(f'{SI}:243 `beichi` 取 A／C 段','已实现'),
 'W48':(f'{SI}:64 `zero_axis`（开关，默认不查）','不进代码（口径未定：原文的「1 分钟级别」对应我们哪一档没定；开关默认关，维持；Atlas 13:4x 核）'),
 'T2':(f'{SI}:243 `beichi`：先定比哪两段再读 MACD','已实现（Nova 10-08 08:14 核过）'),
 'T6':(f'{SI}:27 `macd_lines(12, 26, 9)` 默认参数','已实现'),
 'T13':(f'{SI}:121 `wolf_below` ＋ web/server.py `/api/wolf`','已实现（独立开关、默认关）'),
 'Z1':(f'{CT}:95 `upgrades`：满 9 段升级','已实现'),
 'Z2':('同 D6-4','原文依据，不另进代码'),
 'Z8':(f'{CT}:114 `find_centers` 用原始式（三段高点取最小、低点取最大）','已实现（不用化简式）'),
 'Z11':('—','**未实现**（L61 的断法要拿多段组成的离开段比力度，这一层没有；候选读法和 L61 15 点夹具在 中枢.md 附《第四章定案》；Nova 10-08 14:44 定不问小栋，第五批候选卡列为先不做）'),
 'Z13':(f'{CT}:95 `upgrades`：正好 9 段算升级','已实现'),
 'Z14':(f'{CT}:114 `find_centers`：出三买三卖才结束（档 ①）','已实现档 ①；档 ②『满 9 段收口』开关**未实现**（10-08 量：25 份 14 份有 ≥9 段中枢，开了动 3 刀分界、5 段段型；Nova 14:44 定这批不做）'),
})
# 第 N 章补翻文件里的条目标题（W、M、J、T、Z、C、S、P 这些编号的出处），有就拿它当摘要
chap=[('HEAD',f) for f in files if f.endswith('.md') and f.split('/')[-1].startswith('第')]
# 第四到七章的补翻文件不在 main，在各章自己的支上（只读，取条目标题用）
for br,f in [('origin/agent/atlas/ch4-zsbc','docs/spec/第四章-走势类型与背驰.md'),('origin/agent/atlas/ch5-mmd','docs/spec/第五章-买卖点.md'),
             ('origin/agent/atlas/ch6-jb','docs/spec/第六章-级别.md'),('origin/agent/atlas/ch7-gj','docs/spec/第七章-辅助工具.md')]:
    chap.append((br,f))
title={}
for ref,f in chap:
    t=subprocess.run(['git','show',ref+':'+f],capture_output=True,text=True).stdout
    for line in t.split('\n'):
        m=re.match(r'(?:-\s*)?\*\*('+idre+r')(?:[（(][^）)]*[）)])?\s*·\s*(.+?)\*\*',line)
        if m and m.group(1) not in title: title[m.group(1)]=(f.split('/')[-1],m.group(2))
        m=re.match(r'\|\s*('+idre+r')\s*\|\s*(.+?)\s*\|',line)
        if m and m.group(1) not in title: title[m.group(1)]=(f.split('/')[-1],re.sub(r'[*`]','',m.group(2)))
NOW={
 'M13':'现状：已定（Nova 10-08 06:47，命名做开关，不报小栋；14:48 定开关这批不做）',
 'T13':'现状：已定（Nova 10-08 09:02，独立开关、默认关；口径见 均线.md 六.7）',
 'T16':'现状：已定（Nova 10-08 08:19，不改类型、另挂 MEASURE_NOTE；见 背驰.md 六.3）',
 'W33':'现状：已定（Nova 10-08 05:3x，不报小栋）',
 'W60':'现状：已定（Nova 10-08 06:25，以 L52 自己的例子为准，不否定小转大）',
}
rows=[]
key=lambda x:(re.match(r'S-待定|笔P|探针P|不变量C|[A-Z]+',x).group(0),[int(v) for v in re.findall(r'\d+',x)])
for k in sorted(occ,key=key):
    best=max(occ[k],key=lambda o:score(k,o))
    code,st=KNOWN.get(k) or ((('—','不进代码') if re.match(r'[WMJTZ]\d',k) else ('','')))
    raw=k[1:] if k.startswith('笔P') else k
    if k.startswith('笔P') and raw in title:
        cf,tt=title[raw];tt=re.sub(r'[|]','／',tt);tt=(tt[:70]+'…') if len(tt)>70 else tt
        summ=f"{tt}（出处：{cf}）"
    elif k in title and re.match(r'[WMJTZ]\d',k):
        cf,tt=title[k];tt=re.sub(r'[|]','／',tt);tt=(tt[:70]+'…') if len(tt)>70 else tt
        summ=f"{tt}（出处：{cf}）"
        if k in NOW: summ+=' ★'+NOW[k]
    else:
        summ=label(k,best[2])
    rows.append(f"| {k} | `{best[0]}:{best[1]}` | {summ} | {code} | {st} |")
hdr=f"""# 规则对代码总表（底账）

> **本表不是规范，规范以 `docs/spec` 为准。**
> 基于 {_BASE_NAME} `{M}`。**用途**：spec 里每一条编了号的规则，写清楚代码在哪、还没实现、还是只是说明不进代码。以后拿它防『spec 定了、代码没跟上』。第三批 B13 的 S7、S10、S12 就是这样漏的。
> **怎么生成的**：`notes/gen_rcm.py`。扫 `docs/spec/` 下 17 份主题文件（不含『第 N 章』补翻记录），按编号抓出现处：W、M、J、T、Z、R、C、S、P、D 加数字，以及 S-待定-N。**同一个编号在不同文件里可能是两套东西，按文件分开**：笔.md／分型.md 里的 P 写成『笔P』（第一章待定项），走势分段.md／级别联动.md 里的 P 写成『探针P』（§四反向探针）；复权.md 的 C1 写成『不变量C1』；线段.md 里『S1X1S2X2…』『S1S2…Sn』那种笔序列记号不收。D、R、Z、W、M、J、T 查过，各文件里是同一套。**一个编号常出现在好几处，这里只取最像定义的那一处**（『规则 X』开头、标题、加粗）。W、M、J、T、Z 的摘要取『第 N 章』补翻文件里这个编号的条目标题（标明出处，第四到七章的文件在各章自己的支上）；D、R、S、C、P 和没找到标题的，取 spec 那一行的标题或加粗字，**可能取错**，以定义处原文为准。
> **分工**：Atlas 列规则，并填上已经核过的几条；Bram 填『代码位置』和『状态』。状态五选一：已实现／**未实现**／不进代码（只是说明或操作建议）／进行中／请核。
> W、M、J、T、Z 是各章补翻的条目号，很多只是『原文怎么说』的记录，不是规则，这类直接填『不进代码』。

| 编号 | 定义处（文件:行） | 摘要 | 代码位置 | 状态 |
|---|---|---|---|---|
"""
tail='''

## 表外待办（没有编号、但是 spec 跟代码可能不一致的）

| 事项 | 出处 | 代码位置 | 状态 |
|---|---|---|---|
| 图头段『起点非段内极值、又不是 L78 ① 型就往后挪一笔』的修法（card-2783fa1f，10-07 定），比 S9（10-08 00:37）早；S9 说第一段的待定只按『谁先被破』收、不走 S-待定-1，这条修法要不要改成按 S9 判 | `线段.md` 自检 A 那节『图头段的量不了』（Nova 10-08 13:21） | `core/segment.py` 图头那一条（`HEAD_EXT_FIX`） | **已关**（Nova 10-08 13:40）：量过（`notes/head_s9_probe.py`，6 根，data 10 份＋线上 15 张），严格照 S9 判（只在待定处境用『谁先被破』）0/25 不同 ⇒ 维持现行修法。宽读版（所有起点非极值的图头都按谁先被破）11/25 会变，超出 S9 范围，不采用。以后数据里出现图头待定、两种判法分家的格子时再议 |
'''
open('docs/规则对代码总表.md','w',encoding='utf-8').write(hdr+'\n'.join(rows)+tail)
print(len(rows))
