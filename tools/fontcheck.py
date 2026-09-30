#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""字体覆盖检查：出图脚本里出现的字，当前字体**真画得出来**吗？

config.py 只查字体文件存不存在，查不出「字体里没有这个字」。缺字是**静默**失败：
不报错、不返回空、PIL 照画一个 .notdef 方框，然后 selfcheck 报「总违规 0 → 全部通过」。
这个脚本补的就是这一格；判据见 render/style.py 的 glyph_gaps()。

    python3 tools/fontcheck.py                 # 扫 cards/ 与 render/ 里的字符串字面量
    python3 tools/fontcheck.py cards/c01_containment.py
    python3 tools/fontcheck.py --selftest      # 只跑检测器的变异测试
    python3 tools/fontcheck.py --codepoints    # 直接给码位，如 U+2713,U+2081
"""
import ast
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN_DIRS = ["cards", "render"]        # 用 render.style.F() 出图的两处
FALLBACK_FONTS = ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                  "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"]


def default_paths():
    out = []
    for d in SCAN_DIRS:
        full = os.path.join(ROOT, d)
        if os.path.isdir(full):
            out += [os.path.join(full, f) for f in sorted(os.listdir(full)) if f.endswith(".py")]
    return out


def _docstrings(tree):
    """模块 / 类 / 函数体的第一条字符串 —— 文档字符串。返回它们的 id() 集合。"""
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                out.add(id(body[0].value))
    return out


def literal_chars(paths, include_docstrings=False):
    """脚本里**会画上去的**字符串用到的字符集合。注释、变量名天然不算（走 ast，不抓正则）。

    docstring 默认不算：那是写给读代码的人看的，一个像素都不会出现在图上。
    排掉它是有代价的教训 —— `cards/model_dissent.py` 的 docstring 里有个 `⟺ U+27FA`，
    这份字体没有；不排掉，`fontcheck` 会报出一个**永远不可能发生的方框**。
    **对正确的活报错，正是它要防的那个病。**

    剩下的仍是**上界**：只在报错时才 print 的话也还算在里面（不画到卡上，但也是给人看的串）。
    要收得更紧得从 `d.text(...)` 的实参收，代价是跟着出图代码走 —— 值不值另说，先别假装已经收了。
    """
    chars, seen, skipped = set(), [], []
    for p in paths:
        try:
            tree = ast.parse(open(p, encoding="utf-8").read())
        except (SyntaxError, UnicodeDecodeError) as e:
            # 解析不了 = 这个文件的字一个都没进来。**降级成"少一点数据"是错的**：
            # 分母少一个，缺字结论照出，退出码照常 —— 而"扫了 27 个"和"扫了 30 个、跳过 3 个"
            # 打印出来一模一样（调用方还常常 `| tail -N`，连这行都看不见）。
            # 所以往下传，由调用方把它变成非 0 退出码。见 scan() 的 skipped。
            skipped.append((p, "%s: %s" % (type(e).__name__, e)))
            continue
        seen.append(p)
        skip = set() if include_docstrings else _docstrings(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if id(node) in skip:
                    continue
                chars |= set(node.value)
    return chars, seen, skipped


def scan(paths=None):
    """返回 (font, missing, conflict, 字符数, 扫过的文件数, 跳过的文件)。

    最后一个**必须**往下传：跳过的文件里的字一个都没进集合，但缺字结论照样出。
    「查不出来，就不算通过」—— 调用方看到它非空就该让退出码非 0。
    """
    from render.style import F, glyph_gaps, _NOTDEF_PROBE
    font = F(24)
    chars, files, skipped = literal_chars(paths if paths is not None else default_paths())
    # 探测字符是检测器自己的哨兵（render/style.py 里那个私用区码位），不是卡片内容。
    # 不排掉它，扫 cards/ + render/ 会把自己那个哨兵报成"卡片缺字"——检测器举报自己。
    keep = "".join(sorted(c for c in chars
                          if not c.isspace() and ord(c) >= 0x20 and c != _NOTDEF_PROBE))
    missing, conflict = glyph_gaps(keep, font)
    return font, missing, conflict, len(chars), len(files), skipped


def _show(chars, limit=60):
    head = "".join(chars[:limit])
    return head + ("…（共 %d 个）" % len(chars) if len(chars) > limit else "")


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("-")]
    if "--selftest" in argv:
        return selftest()

    try:
        if "--codepoints" in argv:
            spec = (args[0] if args else "").split(",")
            chars, files, skipped = set(chr(int(s.strip().lstrip("Uu+"), 16)) for s in spec if s.strip()), 0, []
            from render.style import F, glyph_gaps
            font = F(24)
            missing, conflict = glyph_gaps("".join(sorted(chars)), font)
            n = len(chars)
        else:
            font, missing, conflict, n, files, skipped = scan(
                [os.path.join(ROOT, a) if not os.path.isabs(a) else a for a in args] or None)
    except Exception as e:                       # 含 config 找不到字体
        print("[字体覆盖] 无法检查：%s" % e)
        return 2

    print("[字体覆盖] %s" % getattr(font, "path", "?"))
    print("  扫了 %d 个脚本%s，会画上去的字符串里 %d 个不同字符（docstring 已排除）"
          % (files, "（**跳过 %d 个**）" % len(skipped) if skipped else "", n))
    for _p, _e in skipped:
        print("  ! 没扫成 %s —— %s" % (os.path.relpath(_p, ROOT), _e))
    if skipped:
        print("    ↑ 这几个文件的字**一个都没进来**，分母少了一截，缺字结论不完整。")
    if missing:
        print("  ✗ 画不出来 %d 个：%s" % (len(missing), _show(missing)))
        print("    这些字会变成方框，而且**不会报错**——上面所有「应为 0」都不覆盖这一格。")
    if conflict:
        print("  ⚠ 两条判据分歧 %d 个：%s" % (len(conflict), _show(conflict)))
        print("    cmap 和渲染结论不一致，别按单条判据下结论，先看一眼这份字体。")
    if not missing and not conflict and not skipped:
        print("  ✓ 这份字体画得出会画上去的字符串里的全部字符")
    # 跳过任何一个文件 → 非 0。跟 config.py 那个 'A' 哨兵同一条：查不出来，就不算通过。
    return 1 if (missing or conflict or skipped) else 0


# ---- 变异测试：检测器必须能分开「有」和「没有」，而且不许对正确的活报错 ----
def _variant(src, dst, remap, text="中A0"):
    """拿一份真字体改 cmap，造出指定行为的测试字体。

    remap: {码位: 字形名}；字形名给 None 表示**把这个码位删掉**。
    需要 fontTools；没装就抛 ImportError，调用方降级（见 selftest）。

    **先子集化再改**，不是洁癖：直接 `TTFont(src).save()` 对一份 16 MB 的 CFF/OTF 要跑
    **好几分钟**（CFF 字符表全量重编），`--selftest` 根本跑不完就被 kill ——
    **一道没人跑得动的门，等于没有门，而且它被杀掉的样子和"跑过了"一模一样。**
    子集到三个字之后 save 是 0.02s（实测 2.05s / 16 MB → 0.02s / 1.9 KB），**判据一个字没少**：
    删掉 U+4E2D 之后 `glyph_gaps("中")` 照样报 `['中']`。
    """
    from fontTools import subset
    from fontTools.ttLib import TTFont
    opts = subset.Options()
    opts.text = text
    opts.layout_features = []
    opts.notdef_outline = True
    opts.recalc_bounds = False
    ft = subset.load_font(src, opts)
    sub = subset.Subsetter(options=opts)
    sub.populate(text=text)
    sub.subset(ft)
    for cp, gname in remap.items():
        for t in ft["cmap"].tables:
            if not t.isUnicode():
                continue
            if gname is None:
                t.cmap.pop(cp, None)
            else:
                t.cmap[cp] = gname
    ft.save(dst)
    return dst


def selftest():
    """变异测试：阳性、阴性**两个方向都现造出来测**。

    注意这里刻意不假设「源字体本来没有汉字」：在装了 Arial Unicode 的机器上那个假设不成立，
    一条对着正确字体报错的检查，本身就是它要防的病。所以阴性样本是把 U+4E2D 的映射**删掉**
    现造的，不是靠源字体碰巧缺字。

    fontTools 只是**造测试字体**要用的，不是判据要用的：没装就跳过那几项并**明说**，
    不静默当通过（tools/fontcheck.py 与 tools/selfcheck.py 本身都不需要它）。
    """
    import tempfile
    from PIL import ImageFont
    from render.style import glyph_gaps, _cmap_codepoints, F
    src = getattr(F(24), "path", None)
    if not src or not os.path.exists(src):
        print("自检跳过：没有可用字体")
        return 2
    ok, skipped = [], []

    def check(label, cond, note=""):
        ok.append(bool(cond))
        print("  %s %s%s" % ("✓" if cond else "✗", label, ("　" + note) if note else ""))

    f0 = F(24)
    m, c = glyph_gaps("A0", f0)
    check("真字形不误报（'A0'）", not m and not c, "缺 %r 分歧 %r" % (m, c))

    # 范围判据：docstring 里的字不算「会画上去的」。这条不碰字体，所以 fontTools 缺了也照跑。
    # 反例是现造的：拿一个**只出现在 docstring 里**的生僻字，确认它不进集合、也不进缺字结论。
    import tempfile as _tf
    _d = _tf.mkdtemp(prefix="fontcheck-scope-")
    _p = os.path.join(_d, "sample.py")
    open(_p, "w", encoding="utf-8").write(
        '# -*- coding: utf-8 -*-\n'
        '"""模块说明里有 ⟺ 和 汉。"""\n'
        'def f():\n'
        '    """函数说明里有 ⟺ 和 汉。"""\n'
        '    return "画上去的 ✓"\n')
    _drawn, _f, _s = literal_chars([_p])
    _all, _, _ = literal_chars([_p], include_docstrings=True)
    check("扫得成的文件不计进「跳过」", not _s and len(_f) == 1, "跳过 %r" % _s)
    check("docstring 里的字不进「会画上去的」", "⟺" not in _drawn and "汉" not in _drawn,
          "拿到 %r" % "".join(sorted(_drawn)))
    check("正文里的字仍然进", "✓" in _drawn)
    check("include_docstrings=True 时能拿回 docstring", "⟺" in _all and "汉" in _all)
    check("两种范围确实不同（扰动真的发生了）", _drawn < _all,
          "默认 %d 个 vs 全量 %d 个" % (len(_drawn), len(_all)))
    _m, _c = glyph_gaps("".join(sorted(_drawn)), f0)
    check("⟺ 不再被报成缺字", "⟺" not in _m and "⟺" not in _c, "缺 %r" % _m)

    tmp = tempfile.mkdtemp(prefix="fontcheck-")
    try:
        # 阳性对照用**同一份子集、不动它**，不去造「把 0x4E2D 指到 'A'」那种变体：
        # 那个赋值会让 fontTools 的 cmap.compile 走进一条 `seen[id(cmap)]` 的 KeyError 路径
        # （4.29.1，实测），拿不到就整组跳过。而"检测器对存在的字说存在"这件事，
        # 用未改动的子集验是一样的 —— **不该为了凑一个更漂亮的实验，把整组判据搭进去。**
        base = _variant(src, os.path.join(tmp, "base.otf"), {})
        no_cjk = _variant(src, os.path.join(tmp, "no-cjk.otf"), {0x4E2D: None})
        broken = _variant(src, os.path.join(tmp, "broken.otf"), {0x41: ".notdef"})
    except Exception as e:                       # 含没装 fontTools
        for lbl in ("删掉映射后报缺字", "未改动的子集报存在", "cmap 声明过的字全都能渲染", "检测器失灵时抛异常"):
            skipped.append(lbl)
        print("  ！这几项跳过：造不出测试字体（%s: %s）" % (type(e).__name__, e))
    else:
        m, c = glyph_gaps("中", ImageFont.truetype(no_cjk, 24))
        check("删掉 U+4E2D 的映射后：'中' 报缺字", m == ["中"] and not c, "缺 %r 分歧 %r" % (m, c))
        m, c = glyph_gaps("中", ImageFont.truetype(base, 24))
        check("同一份子集不改动：'中' 报存在（阳性对照）", not m and not c, "缺 %r 分歧 %r" % (m, c))

        # 整份字体自己声明的码位：不该有一个渲染成 .notdef —— 这是「对正确的活报错」的回归闸
        declared = sorted(cp for cp in (_cmap_codepoints(src) or set()) if 0x20 <= cp <= 0x2FFF)
        m, c = glyph_gaps("".join(chr(x) for x in declared), f0)
        check("cmap 声明过的字全都能渲染", not m and not c,
              "字面 %d 个，误报 %d 个" % (len(declared), len(m) + len(c)))

        # 检测器自检必须真的会响：把 'A' 也指到 .notdef，glyph_gaps 该抛，而不是回「全缺」
        try:
            glyph_gaps("A中", ImageFont.truetype(broken, 24))
            check("检测器失灵时抛异常", False, "它没抛——这就是「对什么都说缺」的静默通过")
        except RuntimeError as e:
            check("检测器失灵时抛异常", "检测器失灵" in str(e))

    print("自检：%d 项通过%s" % (sum(ok), "，%d 项跳过" % len(skipped) if skipped else ""))
    if skipped:
        print("  跳过的不是判据，是「造测试字体」这一步；装 fontTools 后能跑全。")
        print("  tools/fontcheck.py 和 tools/selfcheck.py **本身不需要 fontTools**，缺它也照跑。")
    if not all(ok):
        return 1
    return 2 if skipped else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
