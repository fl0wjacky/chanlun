import os,re
ROOT=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # ★ 相对定位（2026-10-01 复算查：原来写死绝对路径）
DOC=os.path.join(ROOT,"docs/concepts/inventory_中枢走势组.md")
D=os.path.join(ROOT,"archive/chanlun108/text")
files=sorted(os.listdir(D))
joined={};breaks={}
for f in files:
    t=open(os.path.join(D,f),encoding="utf-8").read()
    j="";br=set()
    for ch in t:
        if ch=="\n": br.add(len(j))
        else: j+=ch
    joined[f]=j;breaks[f]=br

def mark(q):
    for f in files:
        i=joined[f].find(q)
        if i<0: continue
        out=[];prev=0
        for b in sorted(x-i for x in breaks[f] if i<x<i+len(q)):  # 只标引文**内部**的折行，首尾不算
            out.append(q[prev:b]);out.append("↵");prev=b
        out.append(q[prev:])
        return "".join(out),f
    return None,None

s=open(DOC,encoding="utf-8").read()
s=s.replace("↵","")   # 幂等
cnt={"marked":0,"unmarked":0}
nf={}
def sub(m):
    q=m.group(1)
    if len(q)<4: return m.group(0)
    mk,f=mark(q)
    if mk is None:
        cnt["unmarked"]+=1; return m.group(0)
    cnt["marked"]+=1
    nf[f]=nf.get(f,0)+1
    return "「"+mk+"」"
s=re.sub(r"「([^「」]+)」",sub,s)
open(DOC,"w",encoding="utf-8").write(s)
print("标了 ↵ 的引文段 %d ｜ 没标（引别名表/我自己的话） %d"%(cnt["marked"],cnt["unmarked"]))
print("折行取自哪几课（前 8）：",sorted(nf.items())[:8])
