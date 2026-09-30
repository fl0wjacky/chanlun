#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""卡片版式体检：**量每一处真的画上去的文字**，看它有没有越界。

为什么不用「渲染成 PNG 再看一眼」当判据：那是代理量——你在缩略图上看到的是
像素，判的却是「这行字放不放得下」，中间隔着一层缩放和一双眼睛。
这里的做法是换定义域（和 fontcheck 包 getmask 同一个套路）：把 ImageDraw.text
包起来，问它**每一次到底被要求把哪串字画在哪个坐标**，再拿字体自己的字宽去量。

口径（与卡片自身一致）：
  横向  右边距  W − 56    （页脚分隔线、各段标题都守这条）
        越界    right > W （真的画到画布外，会被裁掉）
  纵向  出画布  ink_bottom > H            —— 真的画到画布下沿外，会被裁掉（**不容忍**，1px 也是被裁）
        出面板  ink_bottom > 面板底 + 1   —— 字还在画布内，但下半截画在面板外面
                                            （容忍 1px：那 1px 还在面板 width=2 的描边里，报了是噪音）
anchor 按 PIL 语义处理：l 起点 / m 中点 / r 终点。

**纵向量的是墨迹、不是 bbox**：两者差几个像素，而"有没有戳出面板"由墨迹决定。
（2026-09-30 实测：`model_dissent` 那一处 bbox 底说 +6px，墨迹说 +7px。**量法不同数不同。**）

**「合计 N 处」必须连着字体（名字 + sha256）读** —— 同一个仓库同一个提交，两支字体会给出两个数，
而且差的不是零头：Droid `97320619` 合计 3 处 / Noto `2c76254f` 合计 16 处，
多出来的 13 处是**同一个机制**（卡片的小标签框按「字号+内边距」定高，不是逐个字量的；
Noto 的汉字在同一字号下墨迹低 3~4px，就戳出标签底框）。所以下面 main() 会先把字体打出来。
**换字体是发卡前的指定项，不是无关项。**

**`build()` 的契约 —— 什么算「一张成功的卡」**（`check()` 在返回处断言，违约抛 `ContractError`）：
★ 还有**第二张脸**：尺寸**问不出口**（`.width`/`.height`/`.dtype`/`__index__` 自己抛）时抛 `Unaskable`
  —— 「不是正整数」与「问不出口」**不许并成一句**（一个是判决、一个是没跑成）。

    build() 成功  =  返回**一副画好的图**，判据三条（全部可读、与具体实现无关）：
      ① 有 `.width` 和 `.height` 两个属性；
      ② 两者都是**正整数**（`_violations(recs, W, H)` 拿它们做比较，不是数会变成另一类错）；
      ③ 样本（**不是判据**）：`cf76e2a` 上 **14/14** 张真实卡返回 `PIL.Image.Image`。

    为什么不是"用 except AttributeError 兜住"就算：那样读者拿到的仍是 Python 的原话
    （`'bool' object has no attribute 'width'`），还得自己翻译成"哪张卡的 build() 违约了"。
    契约写在**返回处**、违约时抛**领域消息**，翻译这一步就没有了。
    ★ 违约消息里**不带"第 N 张"**：报告里从来不印序号，写 N 等于让读者再翻译一次；
      卡名由汇总行（`measure()`）负责印 —— **一个事实只印一处**。
"""
import os, sys, glob, importlib, operator
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image, ImageDraw

MARGIN = 56
PANEL_TOL = 1        # 「出面板」容忍 1px：那 1px 还在面板描边（width=2）里，报了就是噪音
RECORDS = []          # 文字：(xy, text, font, anchor)
PANELS = []           # 面板矩形：[x0, y0, x1, y1]
_ORIG = ImageDraw.ImageDraw.text
_ORIG_RR = ImageDraw.ImageDraw.rounded_rectangle
_ORIG_RECT = ImageDraw.ImageDraw.rectangle


def _spy(self, xy, text, *a, **kw):
    RECORDS.append((xy, text, kw.get("font"), kw.get("anchor") or "la"))
    return _ORIG(self, xy, text, *a, **kw)


def _mk_rect_spy(orig):
    """面板探针：**只记不判**。哪个矩形算"面板"不在这里定 —— 判断时按
    「包含这行文字顶部的最内层矩形」取，卡片自己的画法说了算。"""
    def spy(self, xy, *a, **kw):
        try:
            x0, y0, x1, y1 = xy
        except (TypeError, ValueError):
            return orig(self, xy, *a, **kw)
        PANELS.append((x0, y0, x1, y1))
        return orig(self, xy, *a, **kw)
    return spy


def _install():
    """装上探针。**这一步漏了的话，下面的检查会一边倒地报「全部 OK」**——
    本文件第一版就是这样：`_spy` 写好了、忘了赋值，14 张卡全报「文字 0 处」。
    所以装上之后立刻自检一次（见 main 开头），不靠人记得。"""
    ImageDraw.ImageDraw.text = _spy
    ImageDraw.ImageDraw.rounded_rectangle = _mk_rect_spy(_ORIG_RR)
    ImageDraw.ImageDraw.rectangle = _mk_rect_spy(_ORIG_RECT)


def _selftest():
    """探针自检：拿一张 1×1 的图真画一次字，探针必须看得见；看不见就抛。"""
    RECORDS.clear(); PANELS.clear()
    im = Image.new("RGB", (8, 8))
    d = ImageDraw.Draw(im)
    d.text((0, 0), "x")
    d.rounded_rectangle([0, 0, 4, 4], 1)
    got, gotp = len(RECORDS), len(PANELS)
    RECORDS.clear(); PANELS.clear()
    if got != 1:
        raise RuntimeError("版式探针没装上：画了 1 次字、探针只看到 %d 次" % got)
    if gotp != 1:
        raise RuntimeError("面板探针没装上：画了 1 个圆角矩形、探针只看到 %d 个" % gotp)

    # 墨迹口径自证：`_ink_rows` 报的行范围，必须和「真画一遍再逐行找像素」一模一样。
    # 这条是 2026-09-30 立的，代价是一次真错：我当时在**整张已画好的卡**上扫墨迹行来量某一行字，
    # 于是把**面板自己的描边**算成了这行字的墨迹，报出 +11px —— 真值是 +7，多算 4px，
    # 而这个错数被三个人引用过。**工具报的数，它自己得能复算**；不能复算的数，改的是别人的代码。
    from render.style import F as _F
    _f = _F(22)
    for s, x0, y0 in (("三卖", 10, 6), ("[102,108]", 10, 6), ("Ag", 10, 6)):
        canvas = Image.new("L", (260, 60), 0)
        ImageDraw.Draw(canvas).text((x0, y0), s, font=_f, fill=255)
        rows = [y for y in range(60) if any(canvas.getpixel((x, y)) for x in range(260))]
        ink = _ink_rows(s, _f)
        got = (y0 + ink[0], y0 + ink[1]) if ink else None
        want = (rows[0], rows[-1]) if rows else None
        if got != want:
            raise RuntimeError("墨迹口径自证不过：%r 真画一遍是 %s..%s，_ink_rows 报 %s"
                               % (s, want and want[0], want and want[1], got))
    RECORDS.clear(); PANELS.clear()


def _font_id():
    """正在量的那支字体：**全路径** + sha256 前 8 位。

    路径给全，是因为 `CHANLUN_FONT` 只认全路径（给文件名 config 直接 FileNotFoundError）——
    报数时只印文件名，别人照着复现会先撞一个和结论无关的错。
    sha256 是因为**同名两支字体是有的**（见 memory 里那两支 Droid：`97320619` 有 ✔✗✘、
    `23920155` 两样都缺），只写文件名认不出是哪一支。
    """
    import hashlib
    from config import FONT as _FP
    try:
        h = hashlib.sha256(open(_FP, "rb").read()).hexdigest()[:8]
    except OSError as e:
        return "%s（读不出 sha256：%s）" % (_FP, e)
    return "%s  sha256:%s" % (_FP, h)


def _extent(x, text, font, anchor):
    """返回 (left, right)。多行按最宽的一行算。"""
    w = max((font.getlength(ln) for ln in str(text).split("\n")), default=0)
    h = anchor[0] if anchor else "l"
    if h == "m":
        return x - w / 2, x + w / 2
    if h == "r":
        return x - w, x
    return x, x + w


def _ink_rows(text, font):
    """文字**墨迹**的行范围（相对文字原点）；空串/空白返回 None。

    不是 bbox：bbox 是字体给的行盒，墨迹是真正落下去的那几行像素。两者差几像素，
    而"有没有戳出面板"由墨迹决定 —— 拿 bbox 判会把"差 3px 就戳出来"读成"没戳出来"。
    多行文本按整块算（mask 的每一行，行间空白不计）。
    """
    s = str(text)
    if not s.strip():
        return None
    bb = font.getbbox(s)
    m = font.getmask(s)
    w, h = m.size
    if not w or not h:
        return None
    b = bytes(m)
    rows = [y for y in range(h) if any(b[y * w:(y + 1) * w])]
    if not rows:
        return None
    return bb[1] + rows[0], bb[1] + rows[-1]


def _panel_of(x, ink_top):
    """包含 (x, ink_top) 的**最内层**矩形；没有就返回 None。

    "最内层"= 面积最小那个：卡片会在面板里再叠高亮块，取包含它的最小矩形才不会
    把内层高亮当成面板底。
    """
    best = None
    for x0, y0, x1, y1 in PANELS:
        if x0 <= x <= x1 and y0 <= ink_top <= y1:
            if best is None or (x1 - x0) * (y1 - y0) < (best[2] - best[0]) * (best[3] - best[1]):
                best = (x0, y0, x1, y1)
    return best


def _violations(recs, W, H):
    """判据：**一条都没动**，只是从 check() 里挪出来，好让注入跑的正文也过同一套。"""
    bad = []
    for xy, text, font, anchor in recs:
        if font is None or not str(text).strip():
            continue
        left, right = _extent(xy[0], text, font, anchor)
        if right > W or left < 0:
            bad.append((right - W, "越界", xy, text, left, right))
        elif right > W - MARGIN:
            bad.append((right - (W - MARGIN), "破边距", xy, text, left, right))
        ink = _ink_rows(text, font)
        if ink is None:
            continue
        ink_top, ink_bot = xy[1] + ink[0], xy[1] + ink[1]
        if ink_bot > H:
            bad.append((ink_bot - H, "纵向出画布", xy, text, ink_top, ink_bot))
            continue
        p = _panel_of(xy[0], ink_top)
        if p is not None and ink_bot > p[3] + PANEL_TOL:
            bad.append((ink_bot - p[3], "出面板", xy, text, ink_top, ink_bot))
    return bad


def _fingerprint(recs):
    """这一次到底画了哪些字（位置 + 内容）。字体对象不可哈希，不带。

    只用来回答一个问题：**注入之后，画出来的东西变了吗？**
    没变 ⇒ 那一支根本没走到 ⇒ "覆盖过了"这句话自己成了代理量。见 INJECT。
    """
    return tuple((xy, str(t)) for xy, t, _f, _a in recs)


class ContractError(Exception):
    """卡没满足 cardfit 的契约 —— 不是「这张卡画得不好看」，是「它压根没交出一副图」。

    与「版式越界」是两个病，**别并进一个数**：越界 = 交了图、但画出了界；违约 = 没交图。
    """


class Unaskable(Exception):
    """**问不出口** —— 尺寸那一问**没跑成**：`.width`/`.height`/`.dtype`/`__index__` 自己抛了。

    与 `ContractError` 是**两个病，别并进一个数**：违约 = 它没交出一副图（**有判决**）；
    问不出口 = 交了东西，但"尺寸多大"这一问没答上来（**没有判决**）。
    ★ 原话一个字不丢，附在我们这句话**后面** —— 读者先看到"哪一问没答上来"，再看它为什么炸。
    ★ 与 `ContractError` 同规矩：消息里**不带卡名、不带任何数**（印它的是调用方那行，一个事实只印一处）。
      「取 .dtype 时」那半句是**位置**（哪一问没答上来），不是**名**：它只有四个固定取值，反查不回任何对象。
    """


def _unaskable(what, e):
    """**问不出口**那句话 —— **四个位点一种句式**：`取 <哪一问> 时 <类型>: <原话>`。

    `what` 是**位置**（哪一问没答上来），不是**名**：全器只有四个取值（`.dtype` / `.dtype.kind` /
    `__index__` / `.width`｜`.height`），反查不回任何对象 —— 与「消息里不带卡名、不带任何数」同规矩。
    ★ 句式收在一处，是因为本卡治的病正是「同一件事两处两种说法」：位点各写各的，迟早再分家。
    """
    return Unaskable("取 %s 时 %s: %s" % (what, type(e).__name__, e))


def _is_size(v):
    """尺寸判据：**能当整数用（`operator.index`）、为正、且不是布尔**。

    · 用 `operator.index` 而不是 `isinstance(v, int)`：它才是 Python 里"能当整数用"的标准判据
      —— `int` 子类、numpy 整数标量、任何带 `__index__` 的对象都放行（**契约是鸭子类型**）。
    · 排布尔分两步，因为**它们是两种东西**：
        ① Python 的 `bool`：`isinstance(True, int)` 与 `True > 0` 都为真 ⇒ 不排，"真值"会冒充"尺寸"；
        ② **自称布尔元素类型的标量**（`dtype.kind == 'b'`，numpy/pandas 这类数组库的声明）：
           `np.bool_(True)` **不是** Python `bool` 的子类，① 排不掉它，而它一样会印成 `W=1`。
      两步合起来，**理由（"真值不许冒充尺寸"）与正文同宽** —— 这正是本卡今晚立的那条。
    · **射程就到这儿**：本判据认这两种"布尔声明"。别的库若既不是 Python `bool`、也不声明 `dtype.kind`，
      不在射程内 —— 这是**有意划的界**，不是遗漏（要覆盖它就得"按库认类型"，那种规则会随库版本变）。
    · ★ **射程外第一格 =「问不出口」，不是「不是正整数」**：`operator.index(v)` 那一行**以外**的任何异常
      ⇒ 抛 `Unaskable`，**不许压成第一张脸**。
      ★ 切法**切在位点上，不切在异常类型上**：`operator.index` 的协议里 `TypeError` **就是"我不是整数"这个
      合法的否定答案**（⇒ `False`）—— 但**只有那一行**有这个意思。`.dtype` / `.kind` 那两处**探测自己抛的
      `TypeError` 一样是"没答上来"**：`except` 的宽度是**代码**的属性，不是**异常类型**的属性
      ⇒ 三个位点各接各的（`card-8ce1d0ca-087`：把探测抛的 `TypeError` 读成"不是整数"，
      就等于把**一句没发生过的问答印成答案**）。**不采用** blanket `except Exception: return False`
      —— 那样会把**判据自己的毛病**印成"这张卡违约"，拿一个假结论换一句原话（比现状更坏）。
    · ★ **射程外第二格（写下来的约定，不是遗漏）**：`v.dtype` **自己抛 `AttributeError`** 与"**没有** `dtype`"
      在 Python 里走**同一条路**（`getattr(x, 名, default)` 的第三个参数就是一条写不出 `except` 字样的吞）
      ⇒ 本判据**按"没有 dtype"读**。这里把它**写成字面的 `except AttributeError`**：行为与
      `getattr(v, "dtype", None)` 逐格相同，区别只在 `grep -n "except AttributeError"` 找得到它
      —— 静默点从"没人知道"变成"**写下来的**"。
    · 非正、浮点、字符串、None 一律拦住。
    """
    if isinstance(v, bool):
        return False
    try:
        d = v.dtype
    except AttributeError:          # ★ 第二格：与"没有 dtype"同路，写成字面
        d = None
    except Exception as e:          # ★ 探测自己抛 ⇒ **问不出口**（`TypeError` 在这里**不是**"答案"）
        raise _unaskable(".dtype", e) from e
    try:
        kind = getattr(d, "kind", None)
    except AttributeError:          # ★ 同上：按"没有 kind"读，写成字面
        kind = None
    except Exception as e:
        raise _unaskable(".dtype.kind", e) from e
    if kind == "b":
        return False
    try:
        return operator.index(v) > 0
    except TypeError:               # ★ **只有这一行**：协议里合法的否定答案 ⇒ 第一张脸（不是正整数）
        return False
    except Exception as e:          # ★ 其余 = **问不出口** ⇒ 第二张脸（原话附在后面）
        raise _unaskable("__index__", e) from e


def _read_size_attr(im, name):
    """读一个尺寸属性：**没有** ⇒ `None`（第一张脸的事，交给 `_is_size`）；**问不出口** ⇒ `Unaskable`。

    ★ 这里的 `except AttributeError` 是**写下来的约定**，不是新行为：`getattr(im, name, None)` 的
      default 本来就吞 `AttributeError`，"没有这个属性"与"这个属性自己抛 `AttributeError`"在 Python 里
      区分不了 ⇒ 本器**按"没有"读**（要的是 `grep` 找得到它）。
    """
    try:
        return getattr(im, name)
    except AttributeError:
        return None
    except Exception as e:
        raise _unaskable(".%s" % name, e) from e


def assert_card(im):
    """契约断言（契约见模块 docstring）。违约时抛**领域消息**，不让 AttributeError 露出去。

    **两张脸**：判决 = `ContractError`（不是一副图 / 不是正整数）；**没跑成** = `Unaskable`
    （尺寸那一问自己抛了）—— 后者也**不许**是 Python 原话，更**不许**被印成一张判决。

    **消息里不带卡名**：卡名由调用方（`measure()` 的汇总行）负责印 —— 这里再带一次，
    报告上同一个名字会出现两遍。**一个事实只印一处。**
    ★ **消息里也不带任何数**：样本那件事（14/14 张真实卡是 `PIL.Image.Image`）留在模块 docstring 里，
      那里写明了"是样本不是判据"。运行期消息塞一个"实测"的人口数 ⇒ 加一张卡它当场变假、且没人会重算
      （`card-78a38f93-2d7` 整晚那条：**器会数自己的源码，数随版本变**）。
    """
    try:
        w = _read_size_attr(im, "width")
        h = _read_size_attr(im, "height")
        ok = _is_size(w) and _is_size(h)
    except Unaskable as e:
        # 领域壳：先说**哪一问**没答上来，`Unaskable` 里那句话（原话）附在后面。
        raise Unaskable("build() 交出了东西，但**尺寸问不出口** —— %s" % e) from e
    if not ok:
        raise ContractError(
            "build() 返回了 %s，不是一副图 —— 契约：有 .width / .height 两个正整数属性"
            % type(im).__name__)
    return im


def check(mod, name):
    RECORDS.clear(); PANELS.clear()
    im = assert_card(mod.build())
    recs = list(RECORDS)
    return (im.width, im.height, len(recs),
            sorted(_violations(recs, im.width, im.height), reverse=True),
            _fingerprint(recs))


# ---- 失败分支注入 -----------------------------------------------------------
# 为什么需要这一节：探针包在 `ImageDraw.text` 上 —— **谁画它看见谁**。真实数据下
# `cards/model_dissent.py` 的 `cross_check` 返空清单，那条「× 两处实现分家 N 处：…」的正文
# 就一次都画不出来，于是它一次都没被量过。实测那一支比成功支还宽 14px（1560.3 vs 1546.0），
# 而且**宽度是 N 的函数、不是常数**：那串 `中枢1(卡=…/引擎=…)` 随分家条数变长，
# n=1/2/3 一行装得下，n≥4 起破边距（实测表见 card-47bb914a-6c2）。
#
# 所以这一节**不是加判据**（判据一条没动），是**把失败分支真逼出来画一遍**，
# 让现有判据自己开口。代价最小：一个桩，不碰判据。
#
# **每条注入都要自证**：注入后画出来的字和干净跑一模一样 ⇒ 报「注入未生效」并计入退出码。
# 打歪了的桩比不打更危险 —— 它会让"这一支覆盖过了"变成新的代理量，而且长得跟真的一样。
#
# 注入**写在卡那边**（模块属性 `CARDFIT_FAILURES`），不写在这张表里：见 failure_modes()。


def failure_modes(mod):
    """卡**自己**声明的失败分支。本工具不认识任何一张卡的内脏。

    约定：模块**按需**定义

        CARDFIT_FAILURES = [(模式名, 注入函数), …]      # 有失败分支：逐支注入
        注入函数(mod) -> 还原函数；装完后必须真的改变画出来的字。

        CARDFIT_FAILURES = []                            # **声明"本卡没有失败分支"**
        CARDFIT_NO_FAILURE = "……为什么没有……"           # 上面那行必须配这句

    三态，别混（**"空声明"和"没声明"必须分得开**）：

        （无此属性）         = **没查过**  → 报告末尾点名
        CARDFIT_FAILURES = [] = **查过，没有** → 报出你写的理由
        非空列表              = 查过，有 → 逐支注入 + 自证

    **为什么把注入放在卡那边、不放在这张表里**：支的名字叫 `cross_check`、叫 `MISMATCH`，
    那是**卡的内部**。工具一旦知道某张卡的内脏，加一张卡就得改工具，而工具是大家共用的热文件。
    谁拥有卡，谁拥有它的失败分支。

    **为什么空声明还非得写一句理由**：光认 `[]` 的话，`CARDFIT_FAILURES = []` 会变成**一键消音** ——
    把"没查"刷成"查过、没有"，而报告上两者长得一样。那就又造了一个代理绿。
    """
    if not hasattr(mod, "CARDFIT_FAILURES"):
        return None                     # **从没声明** —— 这才是「没查过」
    modes = mod.CARDFIT_FAILURES or []
    for item in modes:
        name, install = item
        if not callable(install):
            raise RuntimeError("%s.CARDFIT_FAILURES 里的 %r 不是可调用的注入函数" % (mod.__name__, name))
    if not modes:
        why = getattr(mod, "CARDFIT_NO_FAILURE", None)
        if not (isinstance(why, str) and why.strip()):
            raise RuntimeError(
                "%s.CARDFIT_FAILURES 声明为空，但没有写 CARDFIT_NO_FAILURE 说明理由 —— "
                "空声明必须写明「本卡没有失败分支，因为 ___」。见 tools/cardfit.py 的 failure_modes()。" % mod.__name__)
    return list(modes)


def _print_bad(bad, indent="    "):
    for over, kind, xy, text, a, b in bad:
        t = str(text).replace("\n", "⏎")
        where = ("x=%-4d→%-6.0f" % (xy[0], b) if kind in ("越界", "破边距")
                 else "y=%-5.0f→%-6.0f" % (a, b))
        print("%s%-8s %+6.0fpx  %-14s %s" % (indent, kind, over, where, t[:70]))


def _cards_dir():
    """被扫的目录 —— **印出来**，因为「扫到 0 张」时读者第一个要知道的就是"你扫的是哪儿"。"""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cards")


def coverage():
    """覆盖表 = **扫面**（cards/*.py 里定义了 build() 的），不引任何名单。

    原先这里是 `CARDS + extra`，两个病叠在一起：
      · `cards/build_all.py` 的 `CARDS` **不是覆盖表** —— 它是「合集顺序 + PDF 目录标题的唯一
        出处」，**按设计就不列不进合集的卡**（实测缺 model_dissent、level_recursion 两张）。
      · 缺的两个名字手工补在 `extra` 里 ⇒ 同一份名单两个副本、**只拼接不去重**。

    后果两个方向都不出声（两条都实测过）：把 model_dissent 也塞进 CARDS ⇒ 同一张卡跑两次，
    「注入支」6→11 而**合计与声明数逐字不变**（旧版）；往 cards/ 加第 15 张卡 ⇒ 两张名单都
    不自长，静默漏扫、分母还是 14（旧版）。扫面把两个方向一起关掉：**有没有卡，由 cards/ 说。**

    四态分得开（跑了 / 不是卡+理由 / **该量却没量成**+理由 / 不许有第五态）：
      · `skipped` = 本来就不是卡（`__init__`、`build_all` 这种没有 build() 的）—— 不进退出码
      · `failed`  = **卡，但没量成**（导入就炸、build() 抛错）—— **进退出码**
    两者分开的理由不是分类癖：`__init__` 进 rc 会让每次跑都红，而一张**倒下**的卡不进 rc
    会让「14 张全 OK」这句话在只有 13 张量成时照样印出来（实测：语法坏一张卡，rc=0）。
    """
    d = _cards_dir()
    run, skipped, failed = [], [], []
    for p in sorted(glob.glob(os.path.join(d, "*.py"))):
        name = os.path.basename(p)[:-3]
        if name == "__init__":
            skipped.append((name, "包入口，不是卡"))
            continue
        try:
            mod = importlib.import_module("cards." + name)
        except Exception as e:
            # **该量却没量成** —— 与上面那个 skipped 不是一回事：`__init__`/`build_all` 本来就不是卡，
            # 而这里是一张**卡倒下了**。它必须进退出码，理由见下面的注释（今天这里印了、rc 还是 0）。
            failed.append((name, "导入失败 %s: %s" % (type(e).__name__, e)))
            continue
        if not callable(getattr(mod, "build", None)):
            skipped.append((name, "没有 build()"))
            continue
        run.append(name)
    # 重名 = 有的卡被量两次（注入支数会虚高）。扫面理论上不会发生，所以这条是防回归的。
    assert len(run) == len(set(run)), "覆盖表里有重名：%s" % (
        sorted({n for n in run if run.count(n) > 1}))
    # 每个没量到的文件**必须带理由**：以后有人加一条"跳过"分支却忘了写 why ⇒ 这里当场红。
    # （先写的是 `files - run - skipped` 那条"不许有第四态"的检查 —— 它是**只会绿的灯**
    #   （由构造恒空），按自己那条规矩删掉了：一条永远不红的检查不是检查。）
    for name, why in skipped + failed:
        assert why.strip(), "跳过 %s 但没给理由 —— 三态里第二态必须自带理由" % name
    return run, skipped, failed


def main():
    _install()
    _selftest()
    print("[版式体检] 字体 %s" % _font_id())
    cards, skipped, failed = coverage()
    # 「扫到 0 张」不是「没有违规」，是「**我什么都没量**」。这里是这扇门最容易被钻的一格：
    # 树不对（cards/ 不在、只复制了半棵仓、工具被挪到别处）⇒ 覆盖表空 ⇒ 下面所有计数都是 0
    # ⇒ 和"干净通过"印得一模一样。跟 @atlas-791f 的 `verify_quotes.py` 空树是同一种塌，
    # 取值也照同一条约定：**0 = 通过 · 1 = 查出来有问题 · 2 = 我没查成**（2 不是 1，也不是 0）。
    # 别把它并进 1：那会让"树指错了"看起来像"卡片有问题"；也别留在 0：那就是今天这个口子。
    if not cards:
        print("\n[覆盖表] **扫到 0 张** —— 这不是「通过」，是「我什么都没量」。")
        print("           被扫的目录 = %s" % _cards_dir())
        print("           多半是这棵树不对：没有 cards/*.py，或者工具不在它本该在的那个仓里。")
        for name, why in skipped + failed:
            print("           %-22s 跳过：%s" % (name, why))
        print("退出原因: 覆盖表 0 张（什么都没量） ⇒ exit=2")
        return 2
    total = 0
    injected = effective = dead = 0
    uncovered = []          # 从没声明 —— 没查过
    declared_none = []      # 声明"没有失败分支" + 理由

    def measure(name):
        """量一张卡；**抛异常 = 这张卡没量成**，由调用处收进 `failed`，不影响其余卡。"""
        nonlocal total, injected, effective, dead
        mod = importlib.import_module("cards." + name)
        W, H, n, bad, clean_fp = check(mod, name)
        total += len(bad)
        print("%-22s W=%-5d H=%-5d 文字 %3d 处  %s" % (
            name, W, H, n, "OK" if not bad else "★ %d 处" % len(bad)))
        _print_bad(bad)
        modes = failure_modes(mod)
        if modes is None:
            uncovered.append(name)
            return
        if not modes:
            declared_none.append((name, mod.CARDFIT_NO_FAILURE.strip()))
            return
        for mode, install in modes:
            restore = install(mod)
            try:
                _W, _H, _n, bad2, fp = check(mod, name)
            finally:
                restore()
            injected += 1
            if fp == clean_fp:
                # 桩没打进那一支 —— 这一支算**没测**，不算通过。计入退出码，但单列出来，
                # 免得和"版式越界"混成一个数（两者根本不是一个病）。
                dead += 1
                print("  ├ %-20s ★ 注入未生效 —— 这一支没走到，**不算覆盖**" % mode)
                return
            effective += 1
            total += len(bad2)
            print("  ├ %-20s 文字 %3d 处  %s" % (
                mode, _n, "OK" if not bad2 else "★ %d 处" % len(bad2)))
            _print_bad(bad2)

    for name in cards:
        try:
            measure(name)
        except Exception as e:
            # 一张卡没量成 ⇒ ① 收进 failed（**进退出码**）② 其余卡照跑 ③ 分母行会写清"没量成 M 张"。
            # 旧写法两半都是漏的：导入失败只 print、rc 照样 0；而 `check(mod, name)`（里面就是
            # `mod.build()`）**根本不在 try 里** ⇒ 一张卡抛错就裸崩，后面十几张的判决一张都不印。
            # 两条探针（语法坏 / build() 抛）见 card-6832f8a4-144。
            failed.append((name, "%s: %s" % (type(e).__name__, e)))
            print("%-22s ★ **没量成**：%s: %s" % (name, type(e).__name__, e))

    print("\n合计 %d 处" % total)
    if dead:
        print("注入未生效 %d 支 —— 那几支**没测**，不是通过" % dead)
    print("[分支覆盖] 注入 %d 支（%d 支确认改了画法）· 声明「无失败分支」%d 张 · **没声明 %d 张**"
          % (injected, effective, len(declared_none), len(uncovered)))
    if declared_none:
        # 十几张卡的理由通常一模一样，默认平铺会把报告淹掉 —— **但要能一眼看出"它们凭什么是空的"**，
        # 所以给个开关而不是把话吞掉：`--why` 逐张打理由。
        if "--why" in sys.argv:
            for name, why in declared_none:
                print("           %-22s 无失败分支 —— %s" % (name, why))
        else:
            print("           %s" % "、".join(n for n, _ in declared_none))
            print("           ↑ 这 %d 张声明了「本卡没有失败分支」（理由写在卡里，加 `--why` 可以打出来）"
                  % len(declared_none))
    if uncovered:
        print("           ★ 没声明：%s" % "、".join(uncovered))
        print("           ↑ 这几张**既没注入、也没说没有** —— 只覆盖了成功路径。"
              "合计 0 处 ≠ 全卡都查过了。")
    # 分母必须自己印出来：少了它，「量了 14 张」和「量了 2 张」在报告上长得一样。
    print("\n[覆盖表] 扫面 cards/*.py 定义了 build() 的：**%d 张**（跳过 %d 个文件，逐条给理由）"
          % (len(cards), len(skipped)))
    for name, why in skipped:
        print("           %-22s 跳过：%s" % (name, why))
    # ★ **量成的张数**单独印一行 —— 这条是今天补的，理由就是"分母静默变小"：
    #   旧版把"导入失败"混进上面那个 skipped（那是"不是卡"的意思），于是
    #     `cards/aa_syntax.py` 语法坏一张 ⇒ 报告印「14 张（跳过 5 个文件）」、rc **0**
    #   —— 「14 张全 OK」这句话在只有 **13** 张量成时照样印出来，而且门槛是绿的。
    #   同树同探针 `cardfit_undrawn.py` 报 `[rc=1] 解析不了的卡（它们不在覆盖表里 ⇒ 分母静默变小）`。
    if failed:
        print("           ★ **没量成 %d 张**（它们**不在上面那个 %d 里**）：" % (len(failed), len(cards)))
        for name, why in failed:
            print("             %-20s %s" % (name, why))
        print("             ↑ 这几张**是卡**，只是这次没量出来 ⇒ 合计 0 处**不等于**它们没问题。")
    # **`uncovered` 现在进退出码了 —— 这是今天改的，理由连同旧理由一起写在这。**
    #
    # 旧写法是"不进"：理由是**落地当下必然一张都没声明**，进了就等于一合上就让 main 变红
    # （那把尺还要接进 selfcheck，一红就是"落地当天砌墙"）。**那个理由今天可测地不成立了**：
    # 真 main 上 `没声明 = 0 张`（本器与 `cardfit_undrawn.py` 两把尺同数），
    # ⇒ 进退出码**不会**让 landing 当天变红，只会让"以后有人加一张不声明的卡"变红 —— 那正是要拦的。
    #
    # 而"只印不进"的形状是今晚反复抓到的同一格：**报告里印了、退出码里没进**（仪表 ≠ 门）。
    # 实测差：同一棵树上 `cardfit_undrawn.py`(A′) 报 `没声明 1 张 ⇒ rc=1`，本器报同一张卡而 `rc=0`
    # ⇒ **两条尺、同一格、两个值**。取值照全仓约定 `0=通过 · 1=查出来有问题 · 2=我没查成`。
    print("退出原因: 版式 %d 处 · 注入未生效 %d 支 · 没声明 %d 张 · 没量成 %d 张 ⇒ exit=%d"
          % (total, dead, len(uncovered), len(failed),
             1 if (total or dead or uncovered or failed) else 0))
    return 1 if (total or dead or uncovered or failed) else 0


if __name__ == "__main__":
    sys.exit(main())
