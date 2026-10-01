import os,re
ROOT=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # ★ 相对定位（2026-10-01 复算查：原来写死绝对路径）
DOC=os.path.join(ROOT,"docs/concepts/inventory_中枢走势组.md")
D=os.path.join(ROOT,"archive/chanlun108/text")
JOIN={};OFF={}
for f in sorted(os.listdir(D)):
    n=int(re.search(r"(\d+)",f).group(1))
    ls=open(os.path.join(D,f),encoding="utf-8").read().split("\n")
    JOIN[n]="".join(ls)
    off=[];c=0
    for l in ls: off.append(c); c+=len(l)
    OFF[n]=off
def span_of(n,q):
    i=JOIN[n].find(q)
    if i<0: return None
    j=i+len(q)-1;o=OFF[n]
    def ln(x):
        lo,hi=0,len(o)-1
        while lo<hi:
            mid=(lo+hi+1)//2
            if o[mid]<=x: lo=mid
            else: hi=mid-1
        return lo+1
    a,b=ln(i),ln(j)
    return a if a==b else (a,b)
def parse(s):
    s=s.strip()
    if ":" not in s: return None
    a,b=re.match(r"L(\d+):(.*)",s).groups()
    if "-" in b:
        x,y=b.split("-"); return (int(a),int(x),int(y))
    return (int(a),int(b),int(b))
doc=open(DOC,encoding="utf-8").read()
tbl_start=doc.index("| 概念 |")
head=doc[tbl_start:].split("## 附录")[0]
# 标注点：改写式 L17:3  /  插入式 （L20:100） ；取其后第一个 「」 为被标的引文
ANN=[m for m in re.finditer(r"(L\d+:\d+(?:-\d+)?)",head)]
QV=[m for m in re.finditer(r"「([^「」]+)」",head)]
ok=0;bad=[];orphan=[]
for i,m in enumerate(ANN):
    nxt=ANN[i+1].start() if i+1<len(ANN) else len(head)
    qs=[v for v in QV if m.end()<=v.start()<nxt]
    if not qs: orphan.append((m.group(1),head[max(0,m.start()-30):m.end()+30].replace("\n"," "))); continue
    v=qs[0]; q=v.group(1).replace("↵","")
    n,a,b=parse(m.group(1))
    sp=span_of(n,q)
    if sp is None: bad.append((m.group(1),q,"该课找不到此句")); continue
    if isinstance(sp,int): sp=(sp,sp)
    if (sp[0],sp[1])==(a,b): ok+=1
    else: bad.append((m.group(1),q,"实际首次出现 %d-%d"%sp))
print("「回点名的课、回点名的那几行找」——行号点 %d ｜ 挂引文的 %d（对得上 %d ／ 对不上 %d）｜ 行内出处引用（写在行文里、不挂引文）%d"%(len(ANN),len(ANN)-len(orphan),ok,len(bad),len(orphan)))
for a,q,w in bad: print("  ✗ %s :: %s :: %s"%(a,q[:40],w))
for a,ctx in orphan: print("  ⚠ 悬空标注 %s ｜ %s"%(a,ctx))
