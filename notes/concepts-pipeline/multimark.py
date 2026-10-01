import os,re
ROOT=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # ★ 相对定位（2026-10-01 复算查：原来写死绝对路径）
DOC=os.path.join(ROOT,"docs/concepts/inventory_中枢走势组.md")
D=os.path.join(ROOT,"archive/chanlun108/text")
files=sorted(os.listdir(D))
CORP={f:open(os.path.join(D,f),encoding="utf-8").read().replace("\n","") for f in files}
LESSON={f:int(re.search(r"(\d+)",f).group(1)) for f in files}

def hits(q):
    q=q.replace("↵","")
    if len(q)<4: return []
    return sorted(LESSON[f] for f in files if q in CORP[f])

def fmt(s):
    s=sorted(s)
    if len(s)<=6:
        return "另见第 %s 课"%"、".join(str(x) for x in s)
    return "另见第 %s 等 %d 课"%("、".join(str(x) for x in s[:6]), len(s))

lines=open(DOC,encoding="utf-8").read().split("\n")
# 幂等：先拆掉上一版追加的跨课标注与摘要行
lines=[re.sub(r" *(<br>)?跨课·[^|]*\|\s*$", " |", l) if l.startswith("|") and l.count("|")==8 and ("跨课·" in l) else l for l in lines]
lines=[l for l in lines if not l.startswith("**跨课检测（")]
out=[];rows=0;appendix=False
for ln in lines:
    if ln.startswith("## 附录"): appendix=True
    if appendix or not ln.startswith("|"):
        out.append(ln); continue
    if ln.startswith("|---") or ln.startswith("| 概念 |"):
        out.append(ln); continue
    c=ln.split("|")
    cited=set(int(x) for x in re.findall(r"(?:L|第)\s*(\d+)\s*课?", "|".join(c[3:6])))   # 出处列点名的课
    L=set(); S=set()
    for q in re.findall(r"「([^「」]+)」",ln):
        H=hits(q)
        if len(H)<=1: continue
        o=set(H)-cited
        if not o: continue
        (L if len(q.replace("↵",""))>=20 else S).update(o)
    if not L and not S: out.append(ln); continue
    rows+=1
    parts=[]
    if L: parts.append("跨课·**复述待看**：长引文%s"%fmt(L))
    if S: parts.append("跨课·撞句待看：短碎片%s"%fmt(S))
    t=ln.rstrip(); assert t.endswith("|")
    out.append(t[:-1]+" <br>%s |"%("；".join(parts)))
doc="\n".join(out)

# 表头前一行：口径节摘要
SUM=("**跨课检测（全表 180 条去重引文 × 全 108 课，逐字；口径按 @nova-8980 定稿）**：引句 ≥20 字 "
     "**121 条 → 命中 >1 课 9 条**（≈7.4%）· <20 字 56 条 → 命中 >1 课 19 条（词片段，**不作引文计**）· 只引别名表 3 条 · 未命中 0。"
     "命中 >1 课的行已就地标注：长引文标**复述待看**，短碎片标**撞句待看**（20 字阈值按 @atlas-791f 口径；短句的整句复述会落进「撞句」那格，别当噪声跳过）。")
doc=re.sub(r"(\n\| 概念 \|)", "\n"+SUM+r"\1", doc, count=1)
open(DOC,"w",encoding="utf-8").write(doc)
print("就地标注的行数：%d"%rows)
for ln in doc.split("\n"):
    if "跨课·" in ln: print("  %-26s %s"%(ln.split("|")[1].strip()[:26], re.search(r"跨课·.{0,90}",ln).group(0)))
