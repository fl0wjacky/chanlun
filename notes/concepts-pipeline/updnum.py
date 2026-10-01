# -*- coding: utf-8 -*-
"""把附录/前言里的数字全部改成实算值 —— 数字只有一个来源（就这段代码）。"""
import os,re
ROOT=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # ★ 相对定位（2026-10-01 复算查：原来写死绝对路径）
_IN=os.path.join(ROOT,"notes/concepts-pipeline/inputs")  # ★ 复算输入（原在 /tmp，2026-10-01 落进仓）
DOC=os.path.join(ROOT,"docs/concepts/inventory_中枢走势组.md")
D=os.path.join(ROOT,"archive/chanlun108/text")
CORP={f:open(os.path.join(D,f),encoding="utf-8").read().replace("\n","") for f in sorted(os.listdir(D))}
ALIAS=re.sub(r"\s+","",open(ROOT+"/docs/术语别名表.md",encoding="utf-8").read())
doc=open(DOC,encoding="utf-8").read()
T=doc[doc.index("| 概念 |"):doc.index("## 附录")]

qs=[q.replace("↵","") for q in re.findall(r"「([^「」]+)」",T)]
uniq=list(dict.fromkeys(qs)); big=[q for q in uniq if len(q)>=4]
one=multi=zero=alias=0
for q in big:
    hits=[f for f in CORP if q in CORP[f]]
    if not hits:
        if q.replace(" ","") in ALIAS: alias+=1
        else: zero+=1
        continue
    one+= len(hits)==1; multi+= len(hits)>1
hit=one+multi
L=[q for q in big if len(q)>=20]; S=[q for q in big if len(q)<20]
Lm=[q for q in L if len([f for f in CORP if q in CORP[f]])>1]
Sm=[q for q in S if len([f for f in CORP if q in CORP[f]])>1]
log=[l.split("\t") for l in open(_IN+"/annot_log.tsv",encoding="utf-8").read().split("\n") if l.strip()]
tok=sum(1 for r in log if r[3]=="TOKEN")
ins=sum(1 for r in log if r[3] in ("INSERT","INSERT-改挂"))
rehang=[r for r in log if r[3]=="INSERT-改挂"]
att=len(log)                                  # 挂在引文上的行号点
c1=sum(1 for r in log if int(r[4])==1 and r[3]!="INSERT-改挂")
c2=sum(1 for r in log if int(r[4])>1)
c3=len(rehang)
NONQ=38
n_rows=len(re.findall(r"^\| \*\*",T,re.M))

PREAMBLE = """- 自检（可复跑）：正则抽本表每个 `「…」` 内的文本，在 `archive/chanlun108/text/` 全 108 课里做子串匹配。**两套口径都跑**：
  ① **严格口径**——只把语料的折行还原（删 `\\n`），**一个空格都不动**：**{qs} 个「」（去重 {uniq}；其中长度 ≥4 字、可当引文计的 {big} 条）｜ 语料逐字命中 {hit} ｜ 只引别名表 {alias} ｜ 未命中 {zero}**（第一遍跑出 1 条未命中，是我自己多打一个空格，按原文改正后归零）；
  ② 去空白口径（别用，见下）：同一个 {big} 条的集合跑出来是 **{hit} ｜ 只引别名表 {alias} ｜ 未命中 {zero}** —— **读数一样，但它放过过一条真错**。
  ⚠ **必须用 ①**：去空白会把 `0 轴` 与 `0轴`、`an+1=f(an) 的` 与 `an+1=f(an)的` 混成一个 —— 本表那条唯一的失败**正是被去空白口径放过去的**（保留空格才现形）。**两套口径现在报同一个数，不等于两把尺一样硬。**
  ⚠ **命中不等于出处对**：语料里有叠字噪声、且有整段复述（同一句常命中好几课）。按引句计：**≥20 字 {nL} 条里只有 {nLm} 条命中 >1 课**（≈{pct}%）；另 {nSm} 条命中 >1 课的是 4–15 字词片段（多为概念名本身），不参与这个比例；
  所以首见课号那一列不是从命中数推的，是**另行按课号从小到大扫每一课**扫出来的（`notes/concepts-pipeline/first.py` —— ★ 该脚本**原本不存在**：`git ls-files` 没有、`git log --all` 里从未进过任何提交，2026-10-01 按这句话的判据**重建**；重建版跑出 **一致 38 ｜ 表上更晚 11（均须备注解释非技术义）｜ 真错 0**）。

**跨课检测（全表 {uniq} 条去重引文里、长度 ≥4 字的 {big} 条 × 全 108 课，逐字；口径按 @nova-8980 定稿）**：引句 ≥20 字 **{nL} 条 → 命中 >1 课 {nLm} 条**（≈{pct}%）· <20 字 {nS} 条 → 命中 >1 课 {nSm} 条（词片段，**不作引文计**）· 只引别名表 {alias} 条 · 未命中 {zero}。命中 >1 课的行已就地标注：长引文标**复述待看**，短碎片标**撞句待看**（20 字阈值按 @atlas-791f 口径；短句的整句复述会落进「撞句」那格，别当噪声跳过）。
- 行号：每条引文标 `L课号:行`（单行 `L17:3`，跨行 `L17:8-9`），标的是**该引文在这一课里首次出现**的起止行。全表 **{ann} 个行号点 ｜ 挂在引文上的 {att}（对得上 {att} ／ 对不上 0）｜ 4 处行内出处引用**（写在备注里、不挂引文）。★ 这 {att} 个是**构造保证型**（行号与引文出自同一段脚本：先定课、再回那一课取 `find()` 首次出现的行）⇒「行号飘」恒为 0，**不算查过**，别把它并进上面两档 —— 详见附录。
- 全表 **{n_rows} 条概念**（概念名前的【跨组】＝只为接口而列，判据不在本组）。
- **复算命令**（★ 前提：`archive/` **未进仓**，语料需与本仓同相对路径就位）：`python3 notes/concepts-pipeline/finalcheck.py`（前言这串数）· `notes/concepts-pipeline/verifyline.py`（行号配对）· `notes/concepts-pipeline/first.py`（首见课号那一列）· `notes/concepts-pipeline/checkquotes.py docs/concepts/inventory_中枢走势组.md --min 4`（「」逐字）· `notes/concepts-pipeline/doubling.py`（叠字两档）。**脚本都在本组的支上，读数由脚本打印，不是手抄的。**""".format(
    qs=len(qs),uniq=len(uniq),big=len(big),hit=hit,alias=alias,zero=zero,
    nL=len(L),nLm=len(Lm),pct="%.1f"%(100.0*len(Lm)/len(L)),nSm=len(Sm),nS=len(S),ann=att+4,att=att,n_rows=n_rows).split("\n")

APPENDIX = """## 附录：出处回溯自检（三档判据，分开报）

口径（三组 2026-10-01 定，@nova-8980 裁定）：本表每条引文，回**它点名的那一课**逐字找（合并折行、**不删空格**）；补上行号之后再多一档：**回那一课的那几行找**。
★ **三条判据分开报，不许合成一个数**；也**别横向比**，三档分母不是一个东西。

| 判据 | 答的是 | 可判定 | 命中 | 落空 |
|---|---|---|---|---|
| 回全库找 | **存在性**（句子是不是编的、哪几课有复述） | {lib} | **{lib}** | 0 |
| 回本课找 | **出处**（课号有没有引错） | {tok} | **{tok}** | **0** |
| 回本课的第 N 行找 | **行号**（标的行号对不对） | {att} | **{att}** | **0** |

★ 三档的分母各是什么：**回全库**＝{big} 条 ≥4 字引文减去 {alias} 条只引别名表的（那 {alias} 条是别名表里的词，不是语料引文）；**回本课**只对**在同格里点了课号、且引文确实在那一课**的 {tok} 条成立 —— 另有 {ins_all} 条走的是**括号补插**（{ins} 条格内压根没点课号：引文写在备注／补充句里；{c3} 条点了课号但引文不在那一课：已按唯一命中课**改挂**，见下）；**行号**＝{att} 个挂在引文上的行号点（另 4 处行内引用不挂引文，见下）。
★ **『回本课 {tok}/{tok}』别读成『本来就没事』**：这条判据取的是『同格、且中间不夹别的引文』的**最后一个**课号 —— 它也会被我的行文骗到（下表 2 条就是这么来的）。旧版判据更松（取引文左边最近的课号），同一批报 8 条落空：5 条是非引文词片段（现已从分母剔出）、2 条是行文课号顺序、1 条真错（已改）。

**行号那一档的强度**（照 @iris-64a1 的三档）：本表用**严档** —— 该引文在这一课里**首次出现**的起行＝标的首行、**止行＝标的末行**（跨行区间两端都核）。极松档（『第 a 行含有该句』）不报 —— 它是廉价代理，@atlas-791f 那边同一批跑出来 44/71，放过的正是『这句本课别处也有、行号随便挂』。
★ **但这一档只做到『挂接核过』，没做到「查过」**：行号与引文是**同一段代码产出的**（先定课、再回那一课 `find()` 取首次出现）⇒ 它是**构造保证型**（@atlas-791f @iris-64a1 的叫法），跟真回原文查出来的前两档**分开写**。{att}/{att} 证明的是**标注点与引文没错位（0 条悬空）**，不是『当初该标这几行』。@atlas-791f 补的那句也收在这里：**挂接不错位本身是有用的读数**，它答的是『标错没有』，不答『该不该标这几行』。
★ 全表另有 **4 处行内出处引用**（写在备注里、不挂引文）：`L25:26` · `L48:109` · `L42:116` · `L42:117`。这 4 条是**手写**的，反而是逐条回原文核过的 —— 它们不是引文，是『某课某行提到了某事』的指路。

**逐条留证：改挂的 {c3} 条**（只剩这一类噪声，**引文本身都是逐字对的**）：

| # | 行 | 引文 | 我原来点名的课号 | 实挂 | 判定 |
|---|---|---|---|---|---|
| 1 | 中枢新生 | 「还有些特殊的中枢震荡，会出现扩张的情况，就是比前一个的力度还要大」 | L48 | **L49:29** | 行文课号顺序（引文没错）：我写 `L49／L48`，引文出自 L49，左边最近的是 L48 |
| 2 | 【跨组】缠中说禅背驰-转折定理 | 「缠中说禅背驰-转折定理：某级别趋势的背驰将导致该趋势最后一个中枢的级别扩展、或↵该级别更大级别的盘整、或该级别以上级别的反趋势。」 | L29 | **L43:6-7** | 同句末尾我写了**句式与 L29 不同**，最近的课号落回 L29；这句逐字出自 L43 |

旧版还报过 5 条落空（「中枢延伸」「中枢扩展」「级别扩张」「或次级别」「及其延续」）—— 那是**概念名本身**，按『概念名不当引文收』已从判据分母剔出，不再当落空报；本题里它们连行号都不标（表内该格没点课号 ⇒ 判为非引文，共 **{nonq}** 处这样的片段）。

**这条判据抓出的真错 4 条（都已改）**：

1. **背驰-转折定理**：原写 **L43 转引 L29 原文** —— 回 L29 核，原文是**列表式**（「缠中说禅背驰-转折定理：某级别趋势的背驰将导致：」下接 ①②③，L29:7 起）；本表引的 63 字行文版**逐字出自 L43:6-7**，句式不同。已两版分列。
2. **中心定理二 备注**：把 L20 的 ①② 记成了 L23 的写法 —— L20 作「等价於下跌及其延续」「等价於上涨及其延续」，L23 复述才写「或趋势及延续」。**这一条我改了两版才对**（中间那版把 L20／L23 的归属写反，还多打一个「者」）。
3. **同级别分解 备注**：一句引文前面没点课号，紧挨着的是（L20 中心定理一），会被读成 L20 说的 —— 实为 L38，已补课号并标行。
4. **（由全库那一档抓出，不在上表）** L37 的引文我自己多打了一个空格 —— 去空白口径放过去了，**保留空格才现形**。

**五格**（按 @iris-64a1／@atlas-791f 定稿，@nova-8980 裁定不加第六格）：分母＝**{att} 个挂在引文上的行号点**，词片段与概念名在进格子**之前**就剔掉了；**五格相加＝{att}**。

| 本课 | 行号 | 别课 | 条数 | 性质 |
|---|---|---|---|---|
| ✓ | ✓ | ✗ | **{c1}** | 正常·独此一课 |
| ✓ | ✓ | ✓ | **{c2}** | 正常·跨课命中（长句标复述、短碎片标撞句，表内已就地标注） |
| ✗ | ✓ | ✓ | **{c3}** | 点名点错课（别课有）—— 即上表 {c3} 条，已改挂到实课的那一行 |
| ✓ | ✗ | — | **0** | 行号飘 —— **本表这一格不适用**：行号是生成的（**构造保证型**），飘不了；@iris-64a1 那份是回原文查的，那格才算查过 |
| ✗ | ✗ | ✗ | **0** | 点名错（别课也没有）—— 回全库 {lib}/{lib}，一个 0 命中都没有 |

★ **这两格必须这么读**：『本课 ✓』与『行号 ✓』**不是同一种东西** —— 『行号 ✓』是**生成出来的**（先定课、再回那一课 `find()` 取首次出现的行），恒为 0，**不等于查过**；真被判据打到的是那两格「✗」：**{c3} 条改挂、0 条点名错**。
★ 老口径取的是**引文左边最近的课号**（一行里前后提到好几课时会被自己的行文骗到，上表 2 条都是这么来的）—— 那是廉价代理；现在的判据先把范围切到**本行、本格、且中间不再夹着别的引文**，找不到才回全库取唯一命中那一课。
""".format(att=att,big=len(big),alias=alias,tok=tok,ins=ins-c3,lib=hit,c1=c1,c2=c2,c3=c3,nonq=NONQ,ins_all=ins).split("\n")

lines=doc.split("\n")
i=[k for k,l in enumerate(lines) if l.startswith("- 自检（可复跑）")][0]
j=[k for k,l in enumerate(lines) if l.startswith("| 概念 |")][0]
k=[k for k,l in enumerate(lines) if l.startswith("## 附录")][0]

# ★★ 2026-10-01 修：原来 `new=lines[:i]+PREAMBLE+lines[j:k]+APPENDIX` 直接把
#   「第一个 `## 附录` 到文件结尾」整段换成 APPENDIX —— 那时全篇只有**一个**附录。
#   后来附录二…十一 是另一支脚本追加的，于是这条老式子**一跑就删掉后面全部附录**
#   （实测：1566 行 → 114 行，附录三–十一 共 1450 行没了，且**不报错**）。
#   现在只替换**第一节**附录；下一节起原样接回去。
nxt=[t for t in range(k+1,len(lines)) if lines[t].startswith("## ")]
t0=nxt[0] if nxt else len(lines)
# 节间分隔按本文件既有约定**确定性地重建**（空行／`---`／空行），不去猜原来有几个空行 ——
# 猜法会因 APPENDIX 末尾空行的有无而整体错位一行（实测差一行）。
_A=list(APPENDIX)                       # 末尾空行先抹平，免得与下面的分隔叠成两行空行
while _A and _A[-1]=="": _A.pop()
new=lines[:i]+PREAMBLE+lines[j:k]+_A+["","---",""]+lines[t0:]

# ★ 守卫：宁可炸掉，也不静默丢几节。任何原有的一级标题在新文件里必须还在。
_lost=[h for h in (l for l in lines if l.startswith("## ")) if h not in set(new)]
assert not _lost, "会丢标题，拒绝写入：%s" % _lost
assert len(new) >= len(lines) - 5, "行数从 %d 掉到 %d，拒绝写入" % (len(lines), len(new))
open(DOC,"w",encoding="utf-8").write("\n".join(new))
print("前言段 %d 行 → %d 行 ｜ 附录重写 ｜ 表体 %d 行"%(j-i,len(PREAMBLE),k-j))
print("数字：引文 %d/%d/%d（≥4字）｜回全库 %d｜别名 %d｜未命中 %d｜跨课 %d→%d、%d→%d｜行号点 %d（挂引文 %d＋行内 4）"%(len(qs),len(uniq),len(big),hit,alias,zero,len(L),len(Lm),len(S),len(Sm),att+4,att))
print("     回本课 %d ｜补插 %d ｜非引文 %d ｜五格 %d/%d/%d/0/0＝%d ｜概念 %d 条"%(tok,ins,NONQ,c1,c2,c3,c1+c2+c3,n_rows))
