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


def literal_chars(paths):
    """脚本里**字符串字面量**用到的字符集合。注释、变量名天然不算（走 ast，不抓正则）。

    注意范围：字面量 ├ 真正画上去的字。字面量是超集——比如一句只在报错时才打印的话也算进来。
    所以报出来的缺字是**上界**：真有缺字，就一定在这里；反过来这里有的，不保证每张图都画到。
    """
    chars, seen = set(), []
    for p in paths:
        try:
            tree = ast.parse(open(p, encoding="utf-8").read())
        except (SyntaxError, UnicodeDecodeError) as e:
            print("  ! 跳过 %s：%s" % (os.path.relpath(p, ROOT), e))
            continue
        seen.append(p)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                chars |= set(node.value)
    return chars, seen


def scan(paths=None):
    """返回 (font, missing, conflict, 字面量字符数, 扫过的文件数)。"""
    from render.style import F, glyph_gaps
    font = F(24)
    chars, files = literal_chars(paths if paths is not None else default_paths())
    keep = "".join(sorted(c for c in chars if not c.isspace() and ord(c) >= 0x20))
    missing, conflict = glyph_gaps(keep, font)
    return font, missing, conflict, len(chars), len(files)


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
            chars, files = set(chr(int(s.strip().lstrip("Uu+"), 16)) for s in spec if s.strip()), 0
            from render.style import F, glyph_gaps
            font = F(24)
            missing, conflict = glyph_gaps("".join(sorted(chars)), font)
            n = len(chars)
        else:
            font, missing, conflict, n, files = scan([os.path.join(ROOT, a) if not os.path.isabs(a) else a
                                                      for a in args] or None)
    except Exception as e:                       # 含 config 找不到字体
        print("[字体覆盖] 无法检查：%s" % e)
        return 2

    print("[字体覆盖] %s" % getattr(font, "path", "?"))
    print("  扫了 %d 个脚本，字符串字面量里 %d 个不同字符" % (files, n))
    if missing:
        print("  ✗ 画不出来 %d 个：%s" % (len(missing), _show(missing)))
        print("    这些字会变成方框，而且**不会报错**——上面所有「应为 0」都不覆盖这一格。")
    if conflict:
        print("  ⚠ 两条判据分歧 %d 个：%s" % (len(conflict), _show(conflict)))
        print("    cmap 和渲染结论不一致，别按单条判据下结论，先看一眼这份字体。")
    if not missing and not conflict:
        print("  ✓ 这份字体画得出字面量里出现的全部字符")
    return 1 if (missing or conflict) else 0


# ---- 变异测试：检测器必须能分开「有」和「没有」，而且不许对正确的活报错 ----
def _variant(src, dst, remap):
    """拿一份真字体改 cmap，造出指定行为的测试字体。

    remap: {码位: 字形名}；字形名给 None 表示**把这个码位删掉**。
    需要 fontTools；没装就抛 ImportError，调用方降级（见 selftest）。
    """
    from fontTools.ttLib import TTFont
    ft = TTFont(src)
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

    tmp = tempfile.mkdtemp(prefix="fontcheck-")
    try:
        no_cjk = _variant(src, os.path.join(tmp, "no-cjk.ttf"), {0x4E2D: None})
        with_cjk = _variant(src, os.path.join(tmp, "with-cjk.ttf"), {0x4E2D: "A"})
        broken = _variant(src, os.path.join(tmp, "broken.ttf"), {0x41: ".notdef"})
    except Exception as e:                       # 含没装 fontTools
        for lbl in ("删掉映射后报缺字", "补上映射后报存在", "cmap 声明过的字全都能渲染", "检测器失灵时抛异常"):
            skipped.append(lbl)
        print("  ！这几项跳过：造不出测试字体（%s: %s）" % (type(e).__name__, e))
    else:
        m, c = glyph_gaps("中", ImageFont.truetype(no_cjk, 24))
        check("删掉 U+4E2D 的映射后：'中' 报缺字", m == ["中"] and not c, "缺 %r 分歧 %r" % (m, c))
        m, c = glyph_gaps("中", ImageFont.truetype(with_cjk, 24))
        check("补上 U+4E2D 的映射后：'中' 报存在", not m and not c, "缺 %r 分歧 %r" % (m, c))

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
