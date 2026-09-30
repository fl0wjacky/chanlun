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


def _named(name, why):
    """点名行的**唯一**拼装函数：`<名字>（<原因>）`（印的时候行首加 `        ✗ `）。

    ★ 为什么必须**只有一种形态**（`card-b9149c38-fab`，@nova-8980 裁决）：

    `tools/selfcheck.py` 那条把尺子输出透传进报告的过滤器（`selfcheck.py:377`）只认行首
    `"✗ "` 或 `"[rc="`。而这张尺原先印「带名字的行」有 **8 种形态**
    （`✗✗ 解析不了（…）：<文件>` ／ 裸名单行 ／ `★ ` ／ `· ` ／ 整句…），
    ⇒ 除「跳过」那一类外，**最需要点名的几类在报告里只剩类名和数，一个名字都没有**。

    ★ **不在线侧加名单**（那是**追不上**的路）：加完还剩 5 种没认，其中 3 种在 rc 里；而且
      "每加一格判据就得回线侧登记一条"正是本仓今天杀掉的病（`card-bb535907-bff` 的三处硬编码、
      本文件当年的前缀白名单，同一个形状）。
    ⇒ 收敛在**尺侧**：所有点名行共用这一个函数，**线侧一个字不改**。

    ★★ 加一个新类 = **两件**事，不是一件（@atlas-791f 2026-09-30 在 `zero_lit` 上量出来的）：
      **(1) 调 `_named()`** —— 行首形态自动跟着走；
      **(2) 把那份 list 加进文末的 `checks` 表** —— 否则**这一类进不了 rc**，而线侧那条透传
           （`selfcheck.py:377` 认行首 `✗ ` **只是前置条件之一**）**还挂在 `_rc != 0` 上**：
           线侧 `if _why is not None or _rc != 0:` 才去吐 `│` 那些行。
      ⇒ **只做 (1) = 本地印得出来、报告里一个字都没有**，而且安静得很像"这一类没问题"。
         `zero_lit` 就是活例：它印 `✗ <卡名>（抽到 0 条字面量…）`，但不在 `checks` 里
         （只有「全库空扫」那一档在）⇒ 尺 `rc=0` ⇒ 那几行**透不出去**。
      上一版这里写的是「加一个新类 = 调 `_named()`」，**那句话说过头了**，此处改正。

    ⚠ 这里只管**拼装**；印的那一行由下面各处的 `print("        ✗ %s" % …)` 出，**格式只有那一串**。
    """
    return "%s（%s）" % (name, why)


def card_names():
    """覆盖表：扫 `cards/*.py` 里**定义了 `build()`** 的。**不写名单、不补名字。**

    ⚠ 为什么不能手写名单：`CARDS = [...13 个名字]` 在 `cards/` 已有 **14** 张卡时**不报错** ——
    报告上那个 `13` 和"全扫过"长得一模一样，而漏掉的恰好是 `model_dissent`。
    **补一个名字下次加卡再漏一次；扫面才是取法。**
    """
    if not os.path.isdir("cards"):           # 目录都不在 ⇒ 空扫的**另一个来源**（见文末 ④）
        return [], []
    out, bad = [], []
    for fn in sorted(os.listdir("cards")):
        if not fn.endswith(".py") or fn.startswith("_"):
            continue
        try:
            tree = ast.parse(open(os.path.join("cards", fn), encoding="utf-8").read())
        except SyntaxError as e:
            # ★ 一个 .py **解析不了** ⇒ 它从覆盖表里**整张消失**：不报错、不跳过、不出现在任何一列。
            #   分母静默变小，而那和「扫过它、它没问题」长得**一模一样**。
            #   这不是假想：我自己的"第 15 张卡"测试就是这么变的 —— 掐声明掐出个 unmatched ')'，
            #   覆盖表照印 **14 张**、rc=0，而那张卡根本不在分母里。
            #   同一形状的第四个来源（前面三个：目录不在 / 一张 build() 都没有 / 抽到 0 条字面量）。
            bad.append(_named(fn, "解析不了：%s 行 %s ⇒ **不在上面那个分母里**"
                              % (e.__class__.__name__, e.lineno)))
            continue
        if any(isinstance(n, ast.FunctionDef) and n.name == "build" for n in tree.body):
            out.append(fn[:-3])
    return out, bad


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
    for i, (mode, install) in enumerate(modes):
        label = "注入 %s" % (mode,)
        try:
            restore = install(mod)
        except Exception as e:                  # noqa: BLE001
            dead.append("%s（装不上：%s: %s）" % (label, type(e).__name__, e))
            continue
        if not callable(restore):
            # `install` 改了模块、却没给还原函数。原先这一支会溜过上面的 except，
            # 然后在下面 `finally: restore()` 上抛 TypeError —— **整张卡的报告全没了**
            # （实测 c05_center 挂一个返回 None 的桩：rc=1，但 14 张的读数一个都不出来）。
            # 更要紧的是：模块现在**是脏的**，这张卡后续任何一跑都不作数 ⇒ 剩下的支一并作废，
            # 不能只跳过这一支然后拿脏模块接着量。
            dead.append("%s（装了但没给还原函数：install 返回 %r）—— 模块已被改脏" % (label, restore))
            for m2, _ in modes[i + 1:]:
                dead.append("注入 %s（上一支没还原，未量）" % (m2,))
            break
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

names, unparsable = card_names()
print("[第三条尺] 缺陷 = 在**所有跑法**（真数据 ∪ 各注入支）里都没被画到的字面量 —— 交集，不是差集")
print("[量法/对象] 覆盖表 = 扫 cards/*.py 里定义了 build() 的 → %d 张 ｜ 字体 %s" % (len(names), _font_id()))
print("-" * 104)
print("%-22s %-8s %-6s %-10s %s" % ("卡", "字面量", "跑法", "真数据未画到", "所有跑法都没画到（=缺陷）"))
print("-" * 104)

undrawn = 0                  # 缺陷条数 —— **不进退出码**（照约定：只报，不判）
lits_total = 0               # 量成的卡合计抽出多少条字面量 ⇒ 0 条 = 本尺**什么都没量到**
injected_ok = 0              # 真生效的注入支
zero_lit = []                # 一条字面量都没抽到的卡 ⇒ 本尺在这张卡上**什么都没量到**
skipped = []                 # 这张压根没量成 ⇒ 覆盖面静默变小 ⇒ **进退出码**
dead_all = []                # 注入支没测 ⇒ **进退出码**
contradict = []              # 声明「无失败分支」而实测有 ⇒ 硬矛盾 ⇒ **进退出码**
uncovered_by_modes = []      # 声明了 N 支、这条正文**仍没被任何一跑画到** ⇒ **进退出码**（分支粒度那一格）
undeclared, declared_none, declared_some = [], [], []

for name in names:
    try:
        mod = importlib.import_module("cards." + name)
        lits = literals_that_can_be_drawn("cards/%s.py" % name)
    except Exception as e:                   # noqa: BLE001
        skipped.append(_named(name, "%s: %s" % (type(e).__name__, e)))
        continue
    runs, dead = all_runs(mod)
    if not runs:                             # 真数据那一跑就没成 ⇒ 这张卡等于没量
        skipped.append(_named(name, dead[0]))
        continue
    dead_all += [_named(name, "支没测：%s" % d) for d in dead]
    injected_ok += len(runs) - 1
    lits_total += len(lits)
    if not lits:
        zero_lit.append(_named(name, "抽到 0 条字面量 ⇒ 本尺在这张卡上**什么也没量到**，不是「没有缺陷」"))
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
        undeclared.append(_named(name, "没声明 CARDFIT_FAILURES ⇒ **没查过 ≠ 通过**"))
    elif modes:
        declared_some.append(name)
        if never:
            uncovered_by_modes.append(_named(name, "声明 %d 支，仍有 %d 条没画到" % (len(modes), len(never))))
    else:
        declared_none.append((name, getattr(mod, "CARDFIT_NO_FAILURE", "").strip()))
        if never:
            contradict.append(_named(name, "声明「无失败分支」，实测 %d 条没有任何一跑画到" % len(never)))

print("-" * 104)
print("合计「所有跑法都没画到」的字面量：%d 条" % undrawn)
print("[覆盖] 扫到 %d 张 · 量成 %d 张 · **跳过 %d 张**"
      % (len(names), len(names) - len(skipped), len(skipped)))
# ★ 下面**所有**点名行共用一个形态、一行一个：`_named()` 拼 + `print("        ✗ %s" % …)`。
#   线侧那张过滤器（`selfcheck.py:377`）认的就是行首这个 `✗ ` —— 但那**只是前置条件之一**：
#   线侧还要 `_rc != 0` 才去吐 `│`（`if _why is not None or _rc != 0:`）。
#   ⇒ 上面这几类能进报告，是因为**它们都在文末 `checks` 表里**（各占一格、会进 rc）；
#     `zero_lit` 只在"全库空扫"那一档进 rc，**逐卡那几行透不出去**（@atlas-791f 量到的）。
#   ⇒ **加一类要同时做两件事：调 `_named()` + 进 `checks`。** 详见 `_named()` 的 docstring。
#   ⚠ 上面那张**逐卡表**（`%-22s %-8d …`）和各卡的小结行（`      · ` / `      ★ ` / `      ↳ `）
#     **不在**这里收敛：它们不是「点名某张卡 / 某个文件」的行，是表体与表内细节（卡名在表的第一列）。
for u in unparsable:
    print("        ✗ %s" % u)
for s in skipped:
    print("        ✗ %s" % s)
print("[分支覆盖] 注入支 %d 支生效 · **%d 支没测**" % (injected_ok, len(dead_all)))
for d in dead_all:
    print("        ✗ %s" % d)
print("[声明] 声明失败支 %d 张 · 声明「无失败分支」%d 张 · **没声明 %d 张**"
      % (len(declared_some), len(declared_none), len(undeclared)))
if undeclared:
    for x in undeclared:
        print("        ✗ %s" % x)
    print("        ↑ 这 %d 张是**没查过**，不是通过 —— 进退出码（见文末 ②）" % len(undeclared))
if declared_none:
    if "--why" in sys.argv:
        for n, why in declared_none:
            # ⚠ 理由**空着就照实说空着**，不许编一句填进去（`card-b9149c38-fab` 门槛⑥：
            #   「没有名字可以印的时候不许编」的同一形状 —— 没有理由可印的时候也不许编。）
            print("        ✗ %s" % _named(n, why or "**理由空着（CARDFIT_NO_FAILURE 是空串）**"))
    else:
        print("        理由写在卡里（加 `--why` 打出来）")
if zero_lit:
    print("[口径] 抽到 0 条字面量的卡 %d 张 —— 本尺在这些卡上**什么也没量到**，不是「没有缺陷」"
          % len(zero_lit))
    for x in zero_lit:
        print("        ✗ %s" % x)
if uncovered_by_modes:
    # ⚠ 这里原来写的是「**不进退出码**：声明的支可以只针对几何，不必然对应「没画到的正文」」。
    #   那句话说的是**归因**（这条正文为什么没被画到）；这份 list 数的是**事实**
    #   （有没有任何一跑画到）——声明只针对几何，不改变"它一条跑法都没画到"。
    #   更硬的一条：`undeclared` / `contradict` 两个出口**用的就是同一份 never**，那条理由若成立
    #   必须把它们一起豁免，可它们早就在 rc 里。⇒ 它是三类里**唯一被豁免的一格** = 免死金牌。
    print("[声明的支没盖住] %d 张（声明了 N 支，这条正文**仍没被任何一跑画到**）" % len(uncovered_by_modes))
    for u in uncovered_by_modes:
        print("        ✗ %s" % u)
print("[声明可信] 矛盾 %d 张（声明「无失败分支」而实测有）" % len(contradict))
for c in contradict:
    print("        ✗ %s" % c)
# ---- 退出码：**从下面这份 list 生成**，不再手写那句"只有三样"------------------
# 上一版这里是一行手写的转述（`rc = 1 if (skipped or dead_all or contradict) else 0`
# 加一句人写的解释）。它是**转述**不是**分解**：往上面再加一个该进 rc 的 list，
# 右边那句解释不会跟着多一项 —— @atlas-791f 的判据「加一档，右边会不会自己多一项？」
# 一眼判它不合格。现在 rc 和那行解释都从 checks 出来，加一档右边自己多一项。
measured = len(names) - len(skipped)
empty_scan = None
if not names:
    empty_scan = ("cards/ **目录都不在**" if not os.path.isdir("cards")
                  else "cards/ 在，但 0 个文件定义 build()")
elif measured and len(zero_lit) == measured:
    empty_scan = "%d 张卡全都没抽出字面量（合计 0 条）" % measured
checks = [
    # (rc 值, 名字, 加数的那份 list, **单位**) —— 空的那份不加数，所以它也不出现在下面的分解里。
    # ★ 单位必须跟着每一份 list **分开写**：这些 list 装的不是一个量 ——
    #   六份装**卡名**（一张一项）· `dead_all` 装**注入支**· 空扫那份装**一句情况**。
    #   原先这行生成器对七份**一视同仁印"条"** ⇒ 「1 条」其实是"1 张卡"。
    #   （@atlas-791f 先抓到 ①，@nova-8980 把它推成"是生成器的问题"，又补上最后一刀：
    #     这份 list **压根没有可数的东西** —— 它是**一句情况**的单元素 list，"处"是我瞎安的第二个数。）
    # ⚠ 三档，不是两档：**张** ／ **支** ／ **None（这一格不是计数，别印数）**。
    #   印数就必须有个量；没有量还印个 1，和印错单位是同一种毛病。
    #   （证据：源码里这份 list 只可能是 None 或 `[某句说明]` ⇒ `len()` 恒为 1；
    #     报告下方本来就用 `看到的那半个证据：%s` % items[0] 把它当句子印。）
    (2, "覆盖表空扫", None if empty_scan is None else [empty_scan], None),
    # ② 这里曾经不并进 rc，理由是"一合上就让 main 变红"。那个理由的**前提是存量非空**，
    # 而 @atlas-791f / @iris-64a1 / 我三方在**要落地的那棵树**上独立量到 **没声明 0 张**
    # ⇒ 前提没了 ⇒ 那份"豁免存量"的机制在解决一个不存在的问题。
    # ⇒ 不做清单、不做 blob、不做基线，直接：没声明 ⇒ 点名 + rc=1。
    #    （代价 0 行：今天 rc 仍是 0；收益：新卡钻不过去了，且**今天就能验会红**。）
    (1, "没声明的卡（没查过 ≠ 通过）", undeclared, "张"),
    (1, "解析不了的卡（它们**不在覆盖表里** ⇒ 分母静默变小）", unparsable, "张"),
    (1, "跳过 / 没量成的卡", skipped, "张"),
    # ★ 这一格**原先不在表里**，于是它印着 `✗ <卡名>（抽到 0 条字面量…）` 却**两处都不到**：
    #   不进 rc（尺 rc=0）⇒ 线侧那句 `if _why is not None or _rc != 0:` 不吐 `│` ⇒ 报告里一个字都没有。
    #   @atlas-791f 量到的形状就是"**印着 ✗ 却两处都不到**"——比不说话更坏：本地看着报了，报告看着干净。
    #   ⇒ 按 @nova-8980 裁 `uncovered_by_modes` 那次的同一条理由收进来：**这只剩它一个被豁免**。
    #   理由（和 `unparsable` 同族）：**这张卡的字面量一条都没进分母** ⇒ 有效分母静默变小，
    #   "本尺在这张卡上什么也没量到"不是"这张卡没有缺陷"。
    #   ⚠ 全库都空时 `empty_scan`（rc=2）和这一格（rc=1）会**一起响** —— 两句都是真的，
    #     rc 取 max 得 2（"根本没查成"比"有一张量不到"重），分解行会各印各的。
    (1, "抽到 0 条字面量的卡（本尺在这张卡上什么也没量到）", zero_lit, "张"),
    # 这一份装的**不是卡名**，是 `"%s → %s" % (卡名, 支名)` —— 一卡一支一项 ⇒ 单位是**支**。
    (1, "没测的注入支", dead_all, "支"),
    (1, "声明矛盾", contradict, "张"),
    # ★ 分支粒度这一格（三类卡是**划分**：None ⇒ 上面那条 undeclared ／ 空 ⇒ contradict ／ 非空 ⇒ 本行）。
    #   前两格早就在 checks 里，只有"声明了 N 支"这一类不在 ⇒ **同一份 never，卡上多写一句声明就换个处理**：
    #   声明得越多越安全。那份 list 的内容物**逐字就是**「没有任何已声明支解释得了的正文」
    #   （:270 的 covered 与它恰好切开 never_real，不重不漏）⇒ 缺的不是判据，是这条判据没进出口。
    (1, "声明的支没盖住（声明了 N 支，这条正文仍没被任何一跑画到）", uncovered_by_modes, "张"),
]
# ★ 单位是这个 list 的**第四个字段**，忘了写就印不出数/印错数 —— 那正是这一版修的病。
#   所以它不能只靠"记得"：这里**当场抛**（和 `_selftest` 同一个道理：装不上就别让它安安静静地跑）。
for _c in checks:
    if len(_c) != 4 or _c[3] not in ("张", "支", None):
        raise RuntimeError("checks 这一项少了/写错了单位（第四格只能是 张 / 支 / None）：%r" % (_c,))
fired = [c for c in checks if c[2]]
rc = max([v for v, _, _, _ in fired], default=0)
# ⚠ 这两个 N 数的都是**类**（判据条数），不是下面那些数 —— 它们各有各的单位（张／支／无数）。
#   所以这里必须说"类"：印"项"会让人以为它和上面的 1 张是同一个量（@nova-8980 抓的第二处）。
print("⇒ 退出码 %d —— 由下面 %d 类生成（同源：改这份 list，这行自己变）："
      % (rc, len(fired)))
if fired:
    for v, n, items, unit in fired:
        extra = ""
        if v == 2:
            # 2 是**单独一个类**：「器说什么都没查」—— 不是"查了、有缺陷"。
            # 它必须和 0（干净）分开，否则空扫和干净长得一模一样（@atlas-791f 格⑤）。
            extra = "  ← rc=2 是另一个**类**：不是「查完干净」，是「**根本没查成**」"
            if n == "覆盖表空扫":
                extra += "\n         看到的那半个证据：%s" % items[0]
                extra += "\n         （器分不出「树指错了」和「这棵树本来就该是空的」——两支都 rc=2，靠这行让人去判）"
        # 有单位才印数：单位 None 的那些 list 装的是**句子**不是**项**，数它只会数出个 1。
        head = "[rc=%d] %s" % (v, n) if unit is None else "[rc=%d] %s：%d %s" % (v, n, len(items), unit)
        print("     %s%s" % (head, extra))
else:
    # ⚠ 这里原来写「%d 份 list …… **全空**」：数是对的（7 类），但**有一格装的是句子不是 list**
    #   （覆盖表空扫，见上面三档说明）⇒ 说"7 份 list"和说"全空"都在把那一格当计数格。
    #   rc=0 要断言的是"**一类都没响**"，说这个就够，不用借"list 全空"来替。
    print("     上面参与判定的 %d 类判据（%s）**一类都没响** —— 这才是 rc=0。"
          % (len(checks), "、".join(n for _, n, _, _ in checks)))
# ⚠ 这两行原来写的是「条数**不进**退出码……照接会让门从接上那天**永远红**，而唯一的修法是删判据」。
#   那句理由的**前提是存量非空**（"接上就永远红"是个关于未来每一次跑的断言，证据只能是当下的一次量）；
#   落地当天在干净树上实测：合计「所有跑法都没画到」= **0 条**（14 张卡全扫过 · rc=0）⇒ 前提不成立。
#   逻辑上也早就不成立了：三类卡是划分，前两类用的就是同一份 never。
# ⚠ 我第一版这里写的是「合计只是那三条的**和**（同一个量在报告里印两遍）」—— **单位错了**（@atlas-791f 抓的）：
#   合计数**条**（字面量）· 那三条数**张**（卡）⇒ **两个量，不是同一个量印两遍。**
#   反例（实测）：同一张 c06_trend 挂**两条**夹具正文 ⇒ 合计 2 条 ｜ [声明的支没盖住] 1 张 ⇒ 2 ≠ 1。
#   **结论仍然成立**，但理由要换成：**每张** never ≥ 1 的卡**必恰好**落进三条之一
#   （:277-287 三支互斥穷尽，后两支都带 `if never`）⇒ 这是**卡级完备**，不是数值相等。
#   （`undeclared` 那支**不带** `if never` ⇒ 它连 never=0 的卡也收 —— 那一条管的是"没查过"，与 never 无关。）
#   ⇒ 留着「和」那个说法很危险：下一个人会把它推成"那合计干脆别印了" ——
#     而合计是**唯一按条报**的那一格，别处的数都是按张报的。
print("   `undrawn` 那个合计数**按条**报（字面量）；上面那三类**按张**报（卡）—— 两个量，不是同一个印两遍。")
print("   接上之后**每张** never ≥ 1 的卡必**恰好**落进三类之一 ⇒ 结论是**卡级完备**，不是数值相等")
print("   （一张卡可以带好几条：实测一张卡挂两条夹具 ⇒ 合计 2 条 ／ 那一格 1 张）。")
sys.exit(rc)
