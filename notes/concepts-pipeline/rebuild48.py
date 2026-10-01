# -*- coding: utf-8 -*-
"""从 state5（44 行、带跨课标注、无行号）重建：+4 行 +四处行内补证"""
import io,os,sys
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
    print("  补 %s（%d 字）"%(anchor.strip("| *"),len(add)),file=sys.stderr)

print("插入自相似性于第 %d 行、平衡市于第 %d 行、震荡中轴于第 %d 行 ｜ 概念行 %d"%(a+1,b+1,c+1,sum(1 for l in s if l.startswith("| **"))),file=sys.stderr)

# ===== 出口（2026-10-01 按 @nova-8980 的判决改，比「加守卫」更彻底）=====
# 守卫（「丢标题就拒绝写入」）只做到「不毁文件」。@nova-8980 要的是更强的：
#   **别把枪口对着成品** —— 谁照着复算命令跑一次，也不该有覆盖交付物的机会。
# 所以这个脚本**不再往成品写**：
#   · 默认写 stdout（管道/重定向随你，那是你自己的选择，不是脚本替你定的）；
#   · 要落文件就自己传路径（`python3 rebuild48.py /tmp/rebuild48.out.md`）；
#   · 传成品的路径 → 当场断言拒绝。
# 产物只有表体草稿这一点没变；要改成品，改 `inputs/state5.md` 里那一行（源头）。
_out = sys.argv[1] if len(sys.argv) > 1 else None
_text = "\n".join(s)
if _out is None:
    sys.stdout.write(_text)
    print("\n[rebuild48] 已写 stdout（%d 行，只有表体草稿）。落文件请自己传路径。" % len(s),
          file=sys.stderr)
else:
    assert os.path.abspath(_out) != os.path.abspath(P), \
        "别把草稿写进成品（%s）。传 /tmp 或任意非成品路径。" % P
    if os.path.exists(_out):
        _old = open(_out, encoding="utf-8").read().split("\n")
        _lost = [h for h in (l for l in _old if l.startswith("## ")) if h not in set(s)]
        assert not _lost, "会丢 %d 个一级标题，拒绝写入 %s：%s" % (len(_lost), _out, _lost[:3])
    open(_out, "w", encoding="utf-8").write(_text)
    print("[rebuild48] 已写 %s（%d 行，只有表体草稿）" % (_out, len(s)), file=sys.stderr)
