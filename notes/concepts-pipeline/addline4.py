import os,re
ROOT="/home/cumora/.cumora/agents/bram-9d29/workspace/wt-concepts"
DOC=os.path.join(ROOT,"docs/concepts/inventory_中枢走势组.md")
D=os.path.join(ROOT,"archive/chanlun108/text")
JOIN={};OFF={}
for f in sorted(os.listdir(D)):
    n=int(re.search(r"(\d+)",f).group(1))
    ls=open(os.path.join(D,f),encoding="utf-8").read().split("\n")
    JOIN[n]="".join(ls); off=[];c=0
    for l in ls: off.append(c); c+=len(l)
    OFF[n]=off
def linespan(n,q):
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
    a,b=ln(i),ln(j); return a if a==b else (a,b)
def fmt(n,q):
    s=linespan(n,q)
    if s is None: return None
    return "L%d:%d"%(n,s) if isinstance(s,int) else "L%d:%d-%d"%(n,s[0],s[1])

head,sep,app=open(DOC,encoding="utf-8").read().partition("## 附录")
TOK=[(m.start(),m.end(),int(m.group(1))) for m in re.finditer(r"(?:L|第)\s*(\d+)(?:\s*课)?",head)]
SP=[(m.start(),m.end(),m.group(1).replace("↵","")) for m in re.finditer(r"「([^「」]+)」",head)]
ops=[];used=set();used_tag={};miss=[];LOG=[];n_tok=n_ins=n_same=n_skip=0
for k,(s0,s1,q) in enumerate(SP):
    if len(q)<4: n_skip+=1; continue
    cell=head.rfind("|",0,s0)+1
    prev_end=SP[k-1][1] if k>0 else 0
    gap=max(cell,prev_end)
    cs=[t for t in TOK if gap<=t[0]<s0]
    tag=None;n=None
    if cs:
        a,b,n=cs[-1]
        if (a,b) in used:
            t2=fmt(n,q)
            if t2 is not None and t2==used_tag.get((a,b)): n_same+=1; LOG.append((q,n,used_tag.get((a,b)),"SAME",len([x for x in JOIN if q in JOIN[x]]))); continue
        else:
            tag=fmt(n,q)
            if tag: used.add((a,b)); used_tag[(a,b)]=tag; ops.append((a,b,tag,"TOKEN",q)); n_tok+=1; LOG.append((q,n,tag,"TOKEN",len([x for x in JOIN if q in JOIN[x]]))); continue
    if tag is None:
        hits=[x for x in JOIN if q in JOIN[x]]
        if cs and n is not None:
            t2=fmt(n,q)
        if len(hits)==1:
            tag=fmt(hits[0],q); ops.append((s0,s0,"（%s）"%tag,"INSERT",q)); n_ins+=1; LOG.append((q,n,tag,"INSERT-改挂" if (n is not None and tag[1:].split(":")[0]!=str(n)) else "INSERT",len([x for x in JOIN if q in JOIN[x]])))
        elif not cs:
            n_skip+=1   # 本格内没有课号 ⇒ 不是引文（概念名/我自己的话）
        else:
            miss.append(("token=%d、命中%d课"%(n,len(hits)),q))
ops.sort(key=lambda x:-x[0])
s=head
for a,b,repl,kind,q in ops: s=s[:a]+repl+s[b:]
open(DOC,"w",encoding="utf-8").write(s+sep+app)
open("/tmp/annot_log.tsv","w",encoding="utf-8").write("\n".join("%s\t%s\t%s\t%s\t%d"%r for r in LOG))
print("改写 token %d ｜ 括号补插 %d ｜ 与共享 token 同行免插 %d ｜ 判为非引文跳过 %d ｜ 没能定位 %d ｜ 行号点合计 %d"%(
    n_tok,n_ins,n_same,n_skip,len(miss),len(re.findall(r"L\d+:\d+(?:-\d+)?",s))))
for why,q in miss: print("   ✗ [%s] %s"%(why,q[:40]))
