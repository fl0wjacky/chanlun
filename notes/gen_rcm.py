import re,subprocess,collections,sys
M=subprocess.run(['git','rev-parse','--short','HEAD'],capture_output=True,text=True).stdout.strip()
files=subprocess.run(['git','-c','core.quotepath=off','ls-tree','--name-only','HEAD','docs/spec/'],capture_output=True,text=True).stdout.split()
topic=[f for f in files if f.endswith('.md') and not f.split('/')[-1].startswith('第')]
idre=r'(?:S-待定-\d|(?:W|M|J|T|Z|R|C|S|P|D)\d{1,2}(?:-\d+)?)'
pat=re.compile(r'(?<![A-Za-z0-9])('+idre+r')(?![0-9-])')
occ=collections.OrderedDict()
for f in topic:
    t=subprocess.run(['git','show','HEAD:'+f],capture_output=True,text=True).stdout
    for n,line in enumerate(t.split('\n'),1):
        for m in pat.finditer(line):
            occ.setdefault(m.group(1),[]).append((f.split('/')[-1],n,line))
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
 'S7':('—','**未实现**（第三批 B13）'),'S10':('—','**未实现**（第三批 B13）'),'S12':('—','**未实现**（第三批 B13）'),
 'S-待定-1':('core/segment.py:374-392（Bram 10-08 摸底）','已实现'),
 'W53':('—','不进代码（Nova 10-08 11:34）'),'W26':('—','未实现，这批不做（W26 后半）'),
 'C3':('core/pen.py min_gap（第三批 ①参数 ②默认 6）','进行中'),
 'P8':('core/kline.py 合并时 `bh > p["h"]` 才换 ih','跟作者 L81 并列取法不同（0.8%），待 Nova 定'),
}
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
        m=re.match(r'\*\*('+idre+r')(?:[（(][^）)]*[）)])?\s*·\s*(.+?)\*\*',line)
        if m and m.group(1) not in title: title[m.group(1)]=(f.split('/')[-1],m.group(2))
        m=re.match(r'\|\s*('+idre+r')\s*\|\s*(.+?)\s*\|',line)
        if m and m.group(1) not in title: title[m.group(1)]=(f.split('/')[-1],re.sub(r'[*`]','',m.group(2)))
rows=[]
key=lambda x:(re.match(r'S-待定|[A-Z]+',x).group(0),[int(v) for v in re.findall(r'\d+',x)])
for k in sorted(occ,key=key):
    best=max(occ[k],key=lambda o:score(k,o))
    code,st=KNOWN.get(k,('',''))
    if k in title and re.match(r'[WMJTZ]\d',k):
        cf,tt=title[k];tt=re.sub(r'[|]','／',tt);tt=(tt[:70]+'…') if len(tt)>70 else tt
        summ=f"{tt}（出处：{cf}）"
    else:
        summ=label(k,best[2])
    rows.append(f"| {k} | `{best[0]}:{best[1]}` | {summ} | {code} | {st} |")
hdr=f"""# 规则对代码总表（底账）

> 基于 main `{M}`。**用途**：spec 里每一条编了号的规则，写清楚代码在哪、还没实现、还是只是说明不进代码。以后拿它防『spec 定了、代码没跟上』。第三批 B13 的 S7、S10、S12 就是这样漏的。
> **怎么生成的**：`notes/gen_rcm.py`。扫 `docs/spec/` 下 17 份主题文件（不含『第 N 章』补翻记录），按编号抓出现处：W、M、J、T、Z、R、C、S、P、D 加数字，以及 S-待定-N。**一个编号常出现在好几处，这里只取最像定义的那一处**（『规则 X』开头、标题、加粗）。W、M、J、T、Z 的摘要取『第 N 章』补翻文件里这个编号的条目标题（标明出处，第四到七章的文件在各章自己的支上）；D、R、S、C、P 和没找到标题的，取 spec 那一行的标题或加粗字，**可能取错**，以定义处原文为准。
> **分工**：Atlas 列规则，并填上已经核过的几条；Bram 填『代码位置』和『状态』。状态五选一：已实现／**未实现**／不进代码（只是说明或操作建议）／进行中／请核。
> W、M、J、T、Z 是各章补翻的条目号，很多只是『原文怎么说』的记录，不是规则，这类直接填『不进代码』。

| 编号 | 定义处（文件:行） | 摘要 | 代码位置 | 状态 |
|---|---|---|---|---|
"""
open('docs/规则对代码总表.md','w',encoding='utf-8').write(hdr+'\n'.join(rows)+'\n')
print(len(rows))
