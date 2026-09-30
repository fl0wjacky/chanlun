"""cardfit 的**第三条尺**：**哪些「写在卡里、会长成字」的正文，真实数据下从没被画上去过。**

为什么需要它：`tools/cardfit.py` 量的是**画出来的字**有没有越界 —— 它**看不见没画出来的字**。
于是一张卡里「写了却从没走到」的那支正文，既不会越界、也不会被报出来：**它不存在，所以它安全。**
本工具把那批字找出来，好让「本卡没有失败分支」这句话**可以被复核**，而不是只能靠信。

    用法（在仓库根跑）：
        python3 tools/cardfit_undrawn.py            # 只报有问题的卡
        python3 tools/cardfit_undrawn.py --all      # 逐卡打全表

判据两条，都必须过：
  ① 探针收下真实数据下**真画上去**的每一个字串（照抄 `tools/cardfit.py` 的装法）；
  ② 从源码 AST 里抽**可能成为正文**的字符串字面量，**先把 `%s/%d` 这类格式符切掉再比** ——
     否则 `"%d~%d"` / `"X%d"` 这些**模板碎片**会被当成"从没画出"，而其画出的是 `3~7`，当然找不到原样串。
     差集 = 「写了但从未画出」⇒ 就是**没被真实数据走到的那一支**的正文。

**口径边界（别当全量读）**：只看得见**字面量**。正文由**变量**拼出来的（`d.text((x,y), sub, …)`）
在这里是隐形的 ⇒ **本工具报 0 不等于「这张卡没有失败分支」**，只等于「没有『写了字的字面量』没画上去」。
"""
"""量法：**哪些「写在卡里、会长成字」的字符串，真实数据下从来没被画上去过。**

判据不是"源码里有没有 if"（那是读，会错），是**画出来的字里有没有它**：
① 装上 ImageDraw.text 探针跑一遍这门卡能跑的正文（用的就是 tools/cardfit.py 自己的探针）；
② 把卡里所有**参与画字**的字符串字面量抽出来（AST，`%` / `+` / f-string 都拆到字面量那一层）；
③ 差集 = 「写了但从未画出」⇒ 那就是**没被真实数据走到的那一支**的正文。

注意口径（别当全量）：**只看得见字面量**。用变量拼出来的正文（`d.text((x,y), sub, …)`）在这里是隐形的 ——
所以本脚本报 0 **不等于**"这张卡没有失败分支"，只等于"没有『写了字的字面量』没画上去"。见 [[tool-success-is-not-correct-result]]。
"""
import ast
import os
import re
import sys


# 跟 tools/cardfit.py 同款：从本文件位置推仓库根，不靠 cwd（否则在别的目录跑就 ModuleNotFoundError）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import ImageDraw  # noqa: E402

CARDS = ["c01_containment", "c02_fractal", "c03_pen", "c04_segment",
         "c04plus_featureseq", "c04c_fourcases", "c04d_twoways", "c05_center",
         "c06_trend", "c07_level", "c08_divergence", "c09_buypoints", "level_recursion"]


def literals_that_can_be_drawn(path):
    """这张卡里所有**可能成为正文**的字符串字面量。含 %/+/join 拆出来的那些。"""
    src = open(path).read()
    tree = ast.parse(src)
    out = set()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and getattr(node.func, "attr", None) == "text"):
            continue
        for a in node.args:
            # 排掉**下标里的**字符串：`r["bars"]` 的 "bars" 是字典键，不是正文 —— 假阳性来源之一
            keys = set()
            for sub in ast.walk(a):
                if isinstance(sub, ast.Subscript) and isinstance(sub.slice, ast.Constant):
                    keys.add(id(sub.slice))
            for sub in ast.walk(a):
                if isinstance(sub, ast.Constant) and isinstance(sub.value, str) and id(sub) in keys:
                    continue
                if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                    # **必须先把 %s/%d 这类格式符切掉再比** —— 第一版没切，于是
                    # `"%d~%d"` / `"15m"` / `"X%d"` 这些**模板碎片**被当成"从未画出"，
                    # 而它们画出来就是 `3~7`，当然找不到原样字符串 ⇒ 假阳性。
                    # 切完只留**真散文**（>=4 字的片段）当判据。
                    for part in re.split(r"%[-+0-9.]*[sdifgxXeE]", sub.value.replace("%%", "\x00")):
                        for line in part.replace("\x00","%").split("\n"):
                            p = line.strip()
                            if len(p) >= 4:
                                out.add(p)
    return out


def drawn_strings(mod):
    """跑 build()，收「真画上去的字」。探针照抄 tools/cardfit.py 的做法。"""
    got = []
    real = ImageDraw.ImageDraw.text

    def probe(self, xy, text, *a, **k):
        got.append(str(text))
        return real(self, xy, text, *a, **k)

    ImageDraw.ImageDraw.text = probe
    try:
        mod.build()
    finally:
        ImageDraw.ImageDraw.text = real
    return got


SHOW_ALL = "--all" in sys.argv
print("%-22s %-8s %-8s %s" % ("卡", "字面量", "画上去", "写了但从未画出（=没走到的那一支）"))
print("-" * 100)
total = 0
for name in CARDS:
    mod = __import__("cards.%s" % name, fromlist=["build"])
    lits = literals_that_can_be_drawn("cards/%s.py" % name)
    drawn = drawn_strings(mod)
    drawn_txt = set()
    for d in drawn:
        for part in d.split("\n"):
            drawn_txt.add(part.strip())
            # 画出来的正文里常含卡里字面量作为子串（模板拼出来的）
    # **只认 `l in dt` 一个方向。** 反过来那条 `dt in l`（"画出来的字是字面量的一部分"）
    # 看着合理，实际是个**假阴性机器**：`扩展`、`中枢` 这种 2 字的绘制会命中任何含它的长句，
    # 于是**没走到的分支被算成走过**。c06 的 `趋势不少于扩展` 就是这么被漏掉的（实测它从未画出）。
    never = sorted(l for l in lits if not any(l in dt for dt in drawn_txt))
    total += len(never)
    if never or SHOW_ALL:
        print("%-22s %-8d %-8d %d" % (name, len(lits), len(drawn_txt), len(never)))
    for l in never[:6]:
        print("      · %s" % (l[:90]))
    if len(never) > 6:
        print("      … 另 %d 条" % (len(never) - 6))
print("-" * 100)
print("合计「写了但从未画出」的字面量：%d" % total)
sys.exit(1 if total else 0)
