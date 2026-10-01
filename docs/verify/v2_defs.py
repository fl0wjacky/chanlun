# 第二步：全书「像定义的句子」→ 有没有被任何文档引到（课号＋行号 ±3）
import re,os,glob,json,collections
T='archive/chanlun108/text'
REPO='.'
L={int(re.findall(r'\d+',f)[0]):open(os.path.join(T,f),encoding='utf-8').read().split('\n') for f in os.listdir(T)}
TERMS='分型 笔 线段 特征序列 中枢 走势类型 盘整 趋势 上涨 下跌 级别 买点 卖点 买卖点 背驰 力度 区间套 中阴 均线 吻 缠绕 结合律 延伸 扩展 扩张 新生 包含 缺口 走势'.split()
STRONG=re.compile(r'称为|叫做|所谓|定义|定理|是指|的意思是|就叫')
WEAK=re.compile(r'就是|必须|只能|不能|一定')
# 所有文档里出现过的坐标
cited=collections.defaultdict(set)
docs=glob.glob(REPO+'/docs/**/*.md',recursive=True)+glob.glob(REPO+'/notes/代读-*.md')+glob.glob(REPO+'/notes/sec*.md')
CO=re.compile(r'L(\d{1,3}):`?(\d+)(?:`?\s*[-–－~～]\s*`?:?(\d+))?')
TOK=re.compile(r'L(\d{1,3}):`?(\d+)(?:`?\s*[-–－~～]\s*`?:?(\d+))?|(?<![L\d:])`?:(\d+)(?:`?\s*[-–－~～]\s*`?:?(\d+))?|第\s*(\d{1,3})\s*课')
for d in docs:
    for line in open(d,encoding='utf-8'):
        last=None
        for m in TOK.finditer(line):
            if m.group(1): n=int(m.group(1)); a=int(m.group(2)); b=int(m.group(3) or a); last=n
            elif m.group(4) and last: n=last; a=int(m.group(4)); b=int(m.group(5) or a)
            elif m.group(6): last=int(m.group(6)); continue
            else: continue
            if b<a or b-a>80: b=a
            for i in range(a-3,b+4): cited[n].add(i)
out=[]
for n in sorted(L):
    lines=L[n]; buf='';start=1
    for i,ln in enumerate(lines,1):
        if not buf: start=i
        buf+=ln
        parts=re.split(r'(?<=[。！？；])',buf)
        buf=parts.pop()
        for s in parts:
            s2=s.strip()
            if not(10<=len(s2)<=220): start=i; continue
            if any(t in s2 for t in TERMS) and (STRONG.search(s2) or WEAK.search(s2)):
                strong=bool(STRONG.search(s2))
                if start not in cited[n] and i not in cited[n]:
                    out.append({'L':n,'line':start,'strong':strong,'s':s2[:120]})
            start=i
c=collections.Counter(o['strong'] for o in out)
print('未被引到的定义样句: 强',c[True],'弱',c[False])
json.dump(out,open('/tmp/v2_uncited.json','w'),ensure_ascii=False)
byL=collections.Counter(o['L'] for o in out if o['strong'])
print('强句按课 top15:',byL.most_common(15))
