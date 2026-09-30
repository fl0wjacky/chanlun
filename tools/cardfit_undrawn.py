"""cardfit 的**第三条尺**：哪些「写在卡里、会长成字」的正文，**在所有跑法里**都没被画上去过。

为什么需要它：`tools/cardfit.py` 量的是**画出来的字**有没有越界 —— 它**看不见没画出来的字**。
于是一张卡里「写了却从没走到」的那支正文，既不会越界、也不会被报出来：**它不存在，所以它安全。**
本工具把那批字找出来，好让「本卡没有失败分支」这句话**可以被复核**，而不是只能靠信。

    用法（在仓库根跑）：
        python3 tools/cardfit_undrawn.py            # 只报有问题的卡
        python3 tools/cardfit_undrawn.py --all      # 逐卡打全表
        python3 tools/cardfit_undrawn.py --why      # 逐张打「无失败分支」的理由

判据（**缺陷 = 在所有跑法里都没画到的字面量**，不是「真数据下没画到」）：
  ① 探针收下**每一跑**真画上去的字：`真数据` 一跑 ＋ 卡自己声明的**每个注入支**各一跑；
  ② 从源码 AST 抽**可能成为正文**的字符串字面量，**先把 `%s/%d` 这类格式符切掉再比** ——
     否则 `"%d~%d"` / `"X%d"` 这些**模板碎片**会被当成"从没画出"，而其画出的是 `3~7`，当然找不到原样串；
  ③ 缺陷 = 字面量 − ⋃(各跑画上去的字)  ⇒ **差集为空才算合规**。

**为什么不能只跑真数据**：`c06_trend` 那条「趋势不少于扩展」是**它自己声明的失败支**，
真数据下必然画不到 —— 只跑真数据会把它判成缺陷，于是**唯一判对的卡会被当成漏洞修掉**。
装上它的注入支再跑一遍，那一句就画上去了 ⇒ 差集空 ⇒ 合规。
**「某一跑没画到」是设计，「所有跑都没画到」才是缺陷** —— 这两个集合差着一整个注入支。

**口径边界（别当全量读）**：
  (a) 只认 `.text(...)` 属性调用 —— 裸调用（`section(...)` / `head_line(...)`）整棵子树不看；
  (b) 字面量必须在**调用实参**里 —— 写在模块级列表里、由循环交给 `text()` 的，一条都进不来；
  (c) 覆盖表 = 扫 `cards/*.py` 里**定义了 `build()`** 的（**不写名单**）——
      硬编码名单的病是**漏扫不报错**：报告上那个 N 和"全扫过"长得一模一样。
⇒ 报 0 **只**等于「在这些参数下没有『从未被任何一跑画到』的字面量」，
   **不等于**「这张卡没有失败分支」。见 [[tool-success-is-not-correct-result]]。
"""
import ast
import hashlib
import importlib
import os
import re
import sys


# 跟 tools/cardfit.py 同款：从本文件位置推仓库根，不靠 cwd（否则在别的目录跑就 ModuleNotFoundError）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image, ImageDraw  # noqa: E402


def card_names():
    """覆盖表：扫 `cards/*.py` 里**定义了 `build()`** 的。**不写名单、不补名字。**

    ⚠ 为什么不能手写名单：`CARDS = [...13 个名字]` 在 `cards/` 已有 **14** 张卡时**不报错** ——
    报告上那个 `13` 和"全扫过"长得一模一样，而漏掉的恰好是 `model_dissent`。
    **补一个名字下次加卡再漏一次；扫面才是取法。**
    """
    out = []
    for fn in sorted(os.listdir("cards")):
        if not fn.endswith(".py") or fn.startswith("_"):
            continue
        try:
            tree = ast.parse(open(os.path.join("cards", fn), encoding="utf-8").read())
        except SyntaxError:
            continue
        if any(isinstance(n, ast.FunctionDef) and n.name == "build" for n in tree.body):
            out.append(fn[:-3])
    return out


def _font_id():
    """正在量的那支字体：**全路径** + sha256 前 8 位（照抄 `tools/cardfit.py`）。

    路径给全，是因为 `CHANLUN_FONT` 只认全路径；sha256 是因为**同名两支字体是有的**，
    只写文件名认不出是哪一支 —— 同一个提交换支字体会给出另一个数。
    """
    from config import FONT as _FP
    try:
        h = hashlib.sha256(open(_FP, "rb").read()).hexdigest()[:8]
    except OSError as e:
        return "%s（读不出 sha256：%s）" % (_FP, e)
    return "%s  sha256:%s" % (_FP, h)


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


_REAL_TEXT = ImageDraw.ImageDraw.text
_DRAWN = []


def _probe(self, xy, text, *a, **k):
    _DRAWN.append(str(text))
    return _REAL_TEXT(self, xy, text, *a, **k)


def _selftest():
    """探针自检：装不上就**当场抛**，不靠人记得。

    `tools/cardfit.py` 第一版是"探针写好了、忘了赋值" ⇒ 14 张卡一边倒报「文字 0 处」。
    我这边装不上的后果**正相反**：画到的字串全空 ⇒ **每个字面量都成了"从未画出"**，
    报出一屏**假缺陷**。两边是同一个病 —— **工具坏了之后，它吐出来的东西还很像结论。**
    """
    ImageDraw.ImageDraw.text = _probe
    try:
        del _DRAWN[:]
        ImageDraw.Draw(Image.new("RGB", (8, 8))).text((0, 0), "x")
        if _DRAWN != ["x"]:
            raise RuntimeError("版式探针没装上：画了 1 次字、探针只看到 %r" % (_DRAWN,))
    finally:
        ImageDraw.ImageDraw.text = _REAL_TEXT
        del _DRAWN[:]


def one_run(mod):
    """跑一次 `mod.build()`，收这一跑真画上去的字（**按行**存，外加整串本身）。

    返回 `(字集合, None)`；跑不成返回 `(None, "错误")`。
    ⚠ **"跑不成"不等于"什么都没画"** —— 把这两件事混成一个空集，就是把「没测」写成「通过」。
    """
    del _DRAWN[:]
    ImageDraw.ImageDraw.text = _probe
    try:
        mod.build()
    except Exception as e:                      # noqa: BLE001 —— 卡的异常按"这一跑没跑成"记账
        return None, "%s: %s" % (type(e).__name__, e)
    finally:
        ImageDraw.ImageDraw.text = _REAL_TEXT
    txt = set()
    for d in _DRAWN:
        txt.add(d.strip())
        for part in d.split("\n"):
            txt.add(part.strip())               # 模板拼出来的正文，字面量常是**某一行**的子串
    del _DRAWN[:]
    return txt, None


def all_runs(mod):
    """这张卡的**所有跑法**：真数据 ∪ 卡自己声明的每个注入支。

    返回 `(runs, dead)` —— `runs` 是 `[(跑法名, 字集合), …]`（含真数据那一跑），
    `dead` 是**没跑成 / 没生效**的跑法名。两者的区别是这门的要害：dead 的那一支**没测**。
    """
    runs, dead = [], []
    txt, err = one_run(mod)
    if txt is None:
        return runs, ["真数据（%s）" % err]
    runs.append(("真数据", txt))
    clean = txt
    modes = getattr(mod, "CARDFIT_FAILURES", None)
    if not modes:
        return runs, dead
    for mode, install in modes:
        label = "注入 %s" % (mode,)
        try:
            restore = install(mod)
        except Exception as e:                  # noqa: BLE001
            dead.append("%s（装不上：%s: %s）" % (label, type(e).__name__, e))
            continue
        try:
            txt, err = one_run(mod)
        finally:
            restore()
        if txt is None:
            dead.append("%s（%s）" % (label, err))
            continue
        if txt == clean:
            # 桩没打进那一支 ⇒ 这一支**没测**。它不制造假绿，它制造**假缺陷**：
            # 这一跑的正文没画出来，于是那些字面量全留在"从未画出"里。
            dead.append("%s（注入未生效：画法与真数据逐字相同）" % label)
            continue
        runs.append((label, txt))
    return runs, dead


SHOW_ALL = "--all" in sys.argv

_selftest()

names = card_names()
print("[第三条尺] 缺陷 = 在**所有跑法**（真数据 ∪ 各注入支）里都没被画到的字面量 —— 交集，不是差集")
print("[量法/对象] 覆盖表 = 扫 cards/*.py 里定义了 build() 的 → %d 张 ｜ 字体 %s" % (len(names), _font_id()))
print("-" * 104)
print("%-22s %-8s %-6s %-10s %s" % ("卡", "字面量", "跑法", "真数据未画到", "所有跑法都没画到（=缺陷）"))
print("-" * 104)

undrawn = 0                  # 缺陷条数 —— **不进退出码**（照约定：只报，不判）
injected_ok = 0              # 真生效的注入支
zero_lit = []                # 一条字面量都没抽到的卡 ⇒ 本尺在这张卡上**什么都没量到**
skipped = []                 # 这张压根没量成 ⇒ 覆盖面静默变小 ⇒ **进退出码**
dead_all = []                # 注入支没测 ⇒ **进退出码**
contradict = []              # 声明「无失败分支」而实测有 ⇒ 硬矛盾 ⇒ **进退出码**
uncovered_by_modes = []      # 声明了支、那支没盖住 ⇒ 报，**不进退出码**（理由见文末）
undeclared, declared_none, declared_some = [], [], []

for name in names:
    try:
        mod = importlib.import_module("cards." + name)
        lits = literals_that_can_be_drawn("cards/%s.py" % name)
    except Exception as e:                   # noqa: BLE001
        skipped.append("%s（%s: %s）" % (name, type(e).__name__, e))
        continue
    runs, dead = all_runs(mod)
    if not runs:                             # 真数据那一跑就没成 ⇒ 这张卡等于没量
        skipped.append("%s（%s）" % (name, dead[0]))
        continue
    dead_all += ["%s → %s" % (name, d) for d in dead]
    injected_ok += len(runs) - 1
    if not lits:
        zero_lit.append(name)
    union = set().union(*[txt for _, txt in runs])
    # **只认 `l in dt` 一个方向。** 反过来那条 `dt in l`（"画出来的字是字面量的一部分"）
    # 看着合理，实际是个**假阴性机器**：`扩展`、`中枢` 这种 2 字的绘制会命中任何含它的长句，
    # 于是**没走到的分支被算成走过**。c06 的 `趋势不少于扩展` 就是这么被漏掉的（实测它从未画出）。
    never = sorted(l for l in lits if not any(l in dt for dt in union))
    never_real = sorted(l for l in lits if not any(l in dt for dt in runs[0][1]))
    if never or dead or SHOW_ALL:
        print("%-22s %-8d %-6d %-10d %d" % (name, len(lits), len(runs), len(never_real), len(never)))
    for l in never[:6]:
        print("      · %s" % (l[:90]))
    if len(never) > 6:
        print("      … 另 %d 条" % (len(never) - 6))
    for d in dead:
        print("      ★ %s" % d)
    if SHOW_ALL:
        # 这一行是**交集与差集的差**：真数据没画到、但被某个注入支画到了 ⇒ 已声明的支覆盖住了。
        # 没有它，`真数据未画到 3 / 所有跑法都没画到 0` 两列会像自相矛盾。
        covered = [l for l in never_real if l not in never]
        if covered:
            print("      ↳ 真数据没画到、**注入支画到了**（= 声明的支盖住了）：%d 条" % len(covered))
            for l in covered[:4]:
                print("        ✓ %s" % l[:90])
    undrawn += len(never)
    modes = getattr(mod, "CARDFIT_FAILURES", None)
    if modes is None:
        undeclared.append(name)
    elif modes:
        declared_some.append(name)
        if never:
            uncovered_by_modes.append("%s（声明 %d 支，仍有 %d 条没画到）" % (name, len(modes), len(never)))
    else:
        declared_none.append((name, getattr(mod, "CARDFIT_NO_FAILURE", "").strip()))
        if never:
            contradict.append("%s（声明「无失败分支」，实测 %d 条没有任何一跑画到）" % (name, len(never)))

print("-" * 104)
print("合计「所有跑法都没画到」的字面量：%d 条" % undrawn)
print("[覆盖] 扫到 %d 张 · 量成 %d 张 · **跳过 %d 张**"
      % (len(names), len(names) - len(skipped), len(skipped)))
for s in skipped:
    print("        ✗ %s" % s)
print("[分支覆盖] 注入支 %d 支生效 · **%d 支没测**" % (injected_ok, len(dead_all)))
for d in dead_all:
    print("        ★ %s" % d)
print("[声明] 声明失败支 %d 张 · 声明「无失败分支」%d 张 · **没声明 %d 张**"
      % (len(declared_some), len(declared_none), len(undeclared)))
if undeclared:
    print("        %s" % "、".join(undeclared))
    print("        ↑ 这 %d 张是**没查过**，不是通过 —— 按约定单列，不进退出码" % len(undeclared))
if declared_none:
    if "--why" in sys.argv:
        for n, why in declared_none:
            print("        %-22s %s" % (n, why))
    else:
        print("        理由写在卡里（加 `--why` 打出来）")
if zero_lit:
    print("[口径] 抽到 0 条字面量的卡 %d 张 —— 本尺在这些卡上**什么也没量到**，不是「没有缺陷」：%s"
          % (len(zero_lit), "、".join(zero_lit)))
if uncovered_by_modes:
    print("[声明的支没盖住] %d 张（**不进退出码**：声明的支可以只针对几何，不必然对应「没画到的正文」）"
          % len(uncovered_by_modes))
    for u in uncovered_by_modes:
        print("        · %s" % u)
print("[声明可信] 矛盾 %d 张（声明「无失败分支」而实测有）" % len(contradict))
for c in contradict:
    print("        ★ %s" % c)
rc = 1 if (skipped or dead_all or contradict) else 0
print("⇒ 退出码 %d —— 进退出码的只有三样：**跳过/没量成的卡**、**没测的注入支**、**声明矛盾**。" % rc)
print("   「所有跑法都没画到」的条数**不进**退出码：c06 那条未画出是**结论**（真数据到不了、注入支到得了），")
print("   照接会让门从接上那天永远红，而唯一的修法是删判据。")
sys.exit(rc)
