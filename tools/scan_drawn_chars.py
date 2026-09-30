#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""扫出「会被画出来的字符」全集 —— 从源码字面量扒，不猜。

用法（在仓库根目录）：
    python3 scan_drawn_chars.py            # 打印分类清单
    python3 scan_drawn_chars.py --emit     # 打印一行可当 probe 的字符串

判据：把 cards/ charts/ render/ 下所有 .py 里的字符串字面量全部并起来。
这是**上界**（含少量只用于比较、从不渲染的字面量），但上界是安全侧：
probe 多几个字只会保守地拒掉字体，不会漏判。
"""
import ast, os, sys
from collections import defaultdict

# 只扫真的会画字的目录：全仓 `.text(` 只出现在 cards/ 和 render/（core/、tools/ 一处都没有，
# archive/ 是归档死代码不算）。**别再加猜出来的目录名**：os.walk 对不存在的目录返回空列表、
# 不抛异常——一个拼错的 root 会静静地贡献 0 个文件，而总数看起来照样正常。
ROOTS = ("cards", "render")


def walk():
    for root in ROOTS:
        if not os.path.isdir(root):
            raise SystemExit("扫描根目录不存在：%s（拼错的 root 不会报错，只会静默少扫）" % root)
        for dp, _, fns in os.walk(root):
            for fn in fns:
                if fn.endswith(".py"):
                    yield os.path.join(dp, fn)


def collect():
    chars = set()
    n = 0
    for p in sorted(walk()):
        n += 1
        try:
            tree = ast.parse(open(p, encoding="utf-8").read())
        except SyntaxError as e:
            print("!! 解析失败 %s: %s" % (p, e), file=sys.stderr)
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                chars.update(node.value)
    return {c for c in chars if c.strip()}, n


def classify(c):
    o = ord(c)
    if o < 128:
        return "ascii"
    if 0x3000 <= o <= 0x303F or 0xFF00 <= o <= 0xFFEF:
        return "cjk标点"
    if 0x4E00 <= o <= 0x9FFF:
        return "cjk汉字"
    if 0x2460 <= o <= 0x24FF or 0x2070 <= o <= 0x209F:
        return "圈号/下标"
    return "其他符号"


ORDER = ("ascii", "cjk汉字", "cjk标点", "圈号/下标", "其他符号")


def ref():
    """把数绑到 ref 上：同一个口径换个分支，汉字数会差几十个（main 751 / six-pack 765）。

    probe 要当规范用，就必须说清是在哪棵树上数的——否则 A 在 main 上设门、
    B 在合并后的树上验，两边分母不同，谁绿谁红都说不清。
    """
    import subprocess
    def g(*a):
        try:
            return subprocess.check_output(("git",) + a, stderr=subprocess.DEVNULL).decode().strip()
        except Exception:
            return "?"
    return g("rev-parse", "--abbrev-ref", "HEAD"), g("rev-parse", "HEAD")


def main():
    chars, nfile = collect()
    g = defaultdict(set)
    for c in chars:
        g[classify(c)].add(c)
    br, sha = ref()
    print("ref: %s @ %s" % (br, sha[:12]))
    print("扫了 %d 个文件，共 %d 个互不相同的字符" % (nfile, len(chars)))
    for k in ORDER:
        s = "".join(sorted(g[k]))
        print("\n【%s】%d 种\n%s" % (k, len(s), s))
    if "--emit" in sys.argv:
        print("\n\nprobe = %r" % "".join(sorted(chars)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
