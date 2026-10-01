# -*- coding: utf-8 -*-
"""从 state5（44 行、带跨课标注、无行号）重建：+4 行 +四处行内补证"""
import io,os
ROOT=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_IN=os.path.join(ROOT,"notes/concepts-pipeline/inputs")  # ★ 复算输入（原在 /tmp，2026-10-01 落进仓）
P=os.path.join(ROOT,"docs/concepts/inventory_中枢走势组.md")
s=open(_IN+"/state5.md",encoding="utf-8").read().split("\n")

def ins_after(anchor, rowfile):
    global s
    i=[k for k,l in enumerate(s) if l.startswith(anchor)]
    assert len(i)==1, (anchor, len(i))
    row=open(rowfile,encoding="utf-8").read().strip()
    s=s[:i[0]+1]+[row]+s[i[0]+1:]
    return i[0]+1

# 顺序不重要：锚点各自唯一
a=ins_after("| **走势终完美** |", _IN+"/r_selfsim.txt")
b=ins_after("| **趋势** |", _IN+"/row_pingheng.txt")
c=ins_after("| **中枢震荡** |", _IN+"/row_zhongzhou.txt")

# 中枢的方向 备注补证
k=[n for n,l in enumerate(s) if l.startswith("| **趋势的方向（中枢的方向）** |")]
assert len(k)==1
add="；**同一个缺口第二次被问到**：L17 的答疑里提问者用的词是「向上或向下中枢」，答「明白就好」——同样没给判据，全库两处提问、零处定义"
row=s[k[0]].rstrip()
assert row.endswith("|")
body=row[:-1].rstrip()
i=body.find(" <br>跨课·")          # 跨课标注永远在行尾，插在它前面（multimark 每轮会重写行尾那一段）
s[k[0]]=(body[:i]+add+body[i:] if i>=0 else body+add)+" |"
# ===== 48 行版追加 =====
d=ins_after("| **缠中说禅走势分解定理二** |", _IN+"/row_wanquan.txt")

EXT = {
 "| **走势终完美** |": "；**L102 又给两套说法（第五、第六）**：⑤ L102「因为走势必完美对应的是一种最特殊、最强有力的唯一分解」⑥ L102「本 ID 的理论给出的递归函数，完美地给出市场走势一个类似记数法一样的唯一分解」；同课点出它为什么关键：L102「这才是走势必完美真正关键的地方。」；并点名一个应用：L102「区间套的方法，就是走势必完美的一个重要的应用。」；**另见结构组**：本行引的那句走势必完美定义（分型、笔、线段、不同级别走势类型所对应的递归函数 → 唯一分解），结构组已单列一行，定义不在本组重复登记",
 "| **级别** |": "；**L102 给了「级别」最硬的一段**：L102「级别在本 ID 理论中就极端关键了」＋L102「因为本 ID 理论中的递归函数是有级别的，是级别依次升大的。」——**级别的来源是递归函数**；L102「从 1 分钟一直到年，对应着 8 个级别，其实，这些级别的名字是可以随意取的」——**级别个数与名字都是约定**；L102「任何走势，都可以唯一地表示为 a1A1+a5A5+a30A30 的形式。」——级别的**分表示法**（本表 a+A+b+B+c 是另一种写法）；操作判据：L102「而级别的存在，一个必然的结论就是，任何高级别的改变都必须先从低级别开始。」",
 "| **递归（中枢的递归定义）** |": "；**L101／L102 把递归函数与「唯一分解」焊死**：L101「分型等於递归函数的a0，这完全可以随意设计，如何设计都不会影响到唯一分解定理的证明。」——**a0 是可替换的参数**（对小栋的工具最要紧的一句）；L101「但现在这种设计，一定是所有可能设计中最好的，这使得笔出现的可能性最大并把最多的偶然因数给消除了，使得实际的操作中更容易把走势分解。」——**为什么选这套分型**（是取舍，不是唯一解）；L102「本 ID 的理论给出的递归函数，完美地给出市场走势一个类似记数法一样的唯一分解」；L102「任何走势，都可以在这些级别构成的分解中唯一地表达。」；**另见结构组**：本行引的分型＝递归函数 a0 那句，结构组那边已单列，定义不重复登记",
}
for anchor, add in EXT.items():
    m=[k for k,l in enumerate(s) if l.startswith(anchor)]
    assert len(m)==1, anchor
    row=s[m[0]].rstrip(); assert row.endswith("|"), anchor
    body=row[:-1].rstrip()
    i=body.find(" <br>跨课·")
    s[m[0]]=(body[:i]+add+body[i:] if i>=0 else body+add)+" |"
    print("  补 %s（%d 字）"%(anchor.strip("| *"),len(add)))

print("插入自相似性于第 %d 行、平衡市于第 %d 行、震荡中轴于第 %d 行 ｜ 概念行 %d"%(a+1,b+1,c+1,sum(1 for l in s if l.startswith("| **"))))

# ===== 守卫（2026-10-01 加，实测踩过）=====
# 这脚本把**整份文件**换成「state5 ＋ 四处补插」那张表体草稿。写它的时候全篇就只有表体，
# 前言、附录一…十一 都是**后来**长出来的。所以现在在成品上跑一次 ＝ 把成品换成草稿：
# 实测 **1567 行 → 97 行**，前言与附录全没，**且不报错、还打印「概念行 48」**。
# 而 README 顶上那份「按顺序跑」的链，第一步就是它 —— 按文档做，第一步就毁文件。
#
# ⇒ 本脚本**只能跑在草稿上**。要改成品，改 `inputs/state5.md` 里对应那一行（源头），别跑它。
if os.path.exists(P):
    _old=open(P,encoding="utf-8").read().split("\n")
    _lost=[h for h in (l for l in _old if l.startswith("## ")) if h not in set(s)]
    assert not _lost, ("会丢 %d 个一级标题，拒绝写入：%s —— 本脚本只重建表体，"
                       "跑在成品上＝把成品换成 %d 行的草稿。要改成品请改 inputs/state5.md。"
                       % (len(_lost), _lost[:3], len(s)))
    assert len(s) >= len(_old)-5, "行数从 %d 掉到 %d，拒绝写入"%(len(_old),len(s))
open(P,"w",encoding="utf-8").write("\n".join(s))
