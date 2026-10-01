import os,re
ROOT="/home/cumora/.cumora/agents/bram-9d29/workspace/wt-concepts"
D=ROOT+"/archive/chanlun108/text"
CORP={f:open(os.path.join(D,f),encoding="utf-8").read().replace("\n","") for f in sorted(os.listdir(D))}
ALIAS=re.sub(r"\s+","",open(ROOT+"/docs/术语别名表.md",encoding="utf-8").read())
doc=open(ROOT+"/docs/concepts/inventory_中枢走势组.md",encoding="utf-8").read()
T=doc[doc.index("| 概念 |"):doc.index("## 附录")]
qs=[q.replace("↵","") for q in re.findall(r"「([^「」]+)」",T)]
uniq=list(dict.fromkeys(qs)); big=[q for q in uniq if len(q)>=4]
one=multi=zero=alias=0
for q in big:
    hits=[f for f in CORP if q in CORP[f]]
    if not hits:
        alias+= 1 if q.replace(" ","") in ALIAS else 0; zero+= 0 if q.replace(" ","") in ALIAS else 1; continue
    one+= len(hits)==1; multi+= len(hits)>1
L=[q for q in big if len(q)>=20]; S=[q for q in big if len(q)<20]
Lm=[q for q in L if len([f for f in CORP if q in CORP[f]])>1]
Sm=[q for q in S if len([f for f in CORP if q in CORP[f]])>1]
ann=len(re.findall(r"L\d+:\d+(?:-\d+)?",T))
log=[l.split("\t") for l in open("/tmp/annot_log.tsv",encoding="utf-8").read().split("\n")]
print("【表内】「」 %d ｜ 去重 %d ｜ ≥4字 %d"%(len(qs),len(uniq),len(big)))
print("  回全库：命中 1 课 %d ｜ 命中 >1 课 %d ｜ 0 命中 %d（含只引别名表 %d）⇒ 命中 %d"%(one,multi,zero,alias,one+multi))
print("  跨课：≥20 字 %d 条 → 跨课 %d 条 ｜ <20 字 %d 条 → 跨课 %d 条"%(len(L),len(Lm),len(S),len(Sm)))
print("  行号点 %d ｜ 标注日志条数 %d（单命中 %d ／ 多命中 %d ／ 0命中 %d）"%(ann,len(log),
      sum(1 for r in log if int(r[4])==1),sum(1 for r in log if int(r[4])>1),sum(1 for r in log if int(r[4])==0)))
c1=sum(1 for r in log if int(r[4])==1 and r[3]!="INSERT-改挂")
c2=sum(1 for r in log if int(r[4])>1)
c3=sum(1 for r in log if r[3]=="INSERT-改挂")
print("  五格：✓✓✗ %d ｜ ✓✓✓ %d ｜ ✗✓✓（改挂） %d ｜ 合计 %d（应＝挂在引文上的行号点 %d）"%(c1,c2,c3,c1+c2+c3,len(log)))
print("  中阴行在？ %s ｜ 非同级别分解行在？ %s"%("中阴（中阴身）" in T,"**非同级别分解**" in T))
