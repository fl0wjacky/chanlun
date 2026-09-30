#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""扫「oracle 依赖被测代码」的检查点：want 里出现了 core.* 的函数调用。

为什么这是个洞：
    一条检查 = (want, got)。got 当然要过被测代码。**want 不该过**——want 是"应该
    等于多少"，它的来源必须独立于被测实现。要是 want 里也调了同一个函数，那函数坏掉
    时两边一起动，检查照样打勾。（`tools/verify_l54.py` 的 L88 就是：want 里写着
    `big_interval(...)`，而 got 那条链内部也调 `big_interval`——变异实测它照绿。）

    这不是"读出来"的结论，是**变异测出来**的：把 `core/extend.py` 的 max/min 对调，
    那种检查点是唯一不会变红的。

它只做静态定位，不下结论：
    打印「哪个文件、哪一行、want 里调了哪个 core 函数、什么参数」。
    **命中不等于有罪**——有时候 want 用 core 函数是对照另一条实现（两套实现互查，
    本来就是一种独立来源）。要定罪得跑变异。工具只负责把候选点排好比人来读。
用法（仓库根目录）：
    python3 tools/scan_oracle.py
"""
import ast
import os
import sys

FILES = ("tools/verify_c03.py", "tools/verify_c05.py", "tools/verify_c06_c07.py",
         "tools/verify_c09.py", "tools/verify_l54.py", "tools/selfcheck.py")


def core_imports(tree):
    """本文件从 core* 导入了哪些名字（函数用）。"""
    names = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom) and (n.module or "").startswith("core"):
            for a in n.names:
                names[a.asname or a.name] = "%s.%s" % (n.module, a.name)
        elif isinstance(n, ast.Import):
            for a in n.names:
                if a.name.startswith("core"):
                    names[a.asname or a.name] = a.name
    return names


def calls_in(node, core):
    """node 里调到的 core 函数名（去重、保序）。"""
    out = []
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            f = n.func
            nm = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else None)
            if nm in core and nm not in out:
                out.append(nm)
    return out


def main():
    total = hits = 0
    for path in FILES:
        if not os.path.exists(path):
            print("!! 没有这个文件：%s" % path)
            continue
        src = open(path, encoding="utf-8").read()
        tree = ast.parse(src)
        core = core_imports(tree)
        rows = []
        for n in ast.walk(tree):
            if not isinstance(n, ast.Call):
                continue
            f = n.func
            nm = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else None)
            if not nm or not nm.startswith(("check", "assert")):
                continue
            # want 的位置：check(label, want, got) → args[1]；check_prop(label, prop, ok) → 没有 want，跳过
            if nm == "check_prop" or len(n.args) < 3:
                continue
            total += 1
            want = n.args[1]
            got = n.args[2]
            w, g = calls_in(want, core), calls_in(got, core)
            if w:
                hits += 1
                rows.append((n.lineno, w, g, ast.get_source_segment(src, want) or ""))
        if rows:
            print("\n=== %s" % path)
            for ln, w, g, seg in rows:
                print("  L%-4d want 调了 %s     ← 候选：oracle 过被测代码" % (ln, ", ".join(w)))
                print("        want = %s" % seg.replace("\n", " ")[:150])
                print("        got  调了 %s" % (", ".join(g) if g else "（没有）"))
    print("\n扫了 %d 个文件，%d 个值型检查点，其中 %d 个的 **want 里调了 core 的函数**。" % (len(FILES), total, hits))
    print("命中只是候选：拿变异跑一遍才算证据（见文件头）。")


if __name__ == "__main__":
    sys.exit(main())
