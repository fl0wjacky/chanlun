#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""面差 (whole − literal) 的**逐行**枚举 —— 器外第三条路径，自带 file:line。

用法:  python3 notes/face_diff_probe.py <commit> [--min-len N ...]

为什么要有它：卡上引的 `98` 只有**逐格**分解（config 14 / cards 19 / core 2 / render 9 / tools 54），
而 nova 那张 599 表的 13 行带的是 **file:line** ⇒ 两边**对不上口径**就核不了。
本脚本把 98 逐处展开成 (格, file:line, 引文键)，再挑出键里含 ASCII 双引号的那些，与她的表逐行比。

★ 自证（不信任本脚本自己的枚举）：每一格的处数必须与器 `tally()` 印的逐格处数**逐位相同**；
  不等就当场退出，不印结论。器自己那份是 `_sites()`，本脚本是**第二份实现** ——
  两份对上才叫"器外第三条路径"，只有一份那叫"我把器的代码抄了一遍"。
"""
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import verify_quotes as V          # noqa: E402
import quotes_recount as R         # noqa: E402


def walk_cell(base, cell, a):
    """与 `_sites()` 同一套筛选（.py / SKIP / v1ref），但产出 (file路径, 文本)。"""
    if cell == "config.py":
        p = os.path.join(base, "config.py")
        return [(p, "config.py")] if os.path.isfile(p) else []
    root_ = os.path.join(base, cell)
    if not os.path.isdir(root_):
        return []
    out = []
    for r, _d, fs in os.walk(root_):
        if a.v1ref == "skip" and "v1_ref" in r:
            continue
        if any(("/%s" % s.split("/")[-1]) in r or r.endswith(s)
               for s in V.SKIP if s.split("/")[-1] != "v1_ref" or a.v1ref == "skip"):
            continue
        for f in sorted(fs):
            if f.endswith(".py"):
                out.append((os.path.join(r, f), os.path.join(r, f)[len(base) + 1:]))
    return out


def enum(base, a):
    """→ [(格, 相对路径, 行号, 引文原文, 面)]  —— 面 ∈ {whole, literal}"""
    out = []
    for cell in list(R.CELLS) + (["config.py"] if a.face == "whole" else []):
        for path, rel in walk_cell(base, cell, a):
            t = io.open(path, encoding="utf-8").read()
            if a.face == "whole":
                for m in R.Q.finditer(t):
                    q = R.pair(m)
                    if len(V.norm(q)) < a.min_len or R.found(q, a):
                        continue
                    out.append((cell, rel, t.count("\n", 0, m.start()) + 1, q, "whole"))
            else:
                for m in R.LIT.finditer(t):
                    a0 = t.count("\n", 0, m.start()) + 1
                    try:
                        v = __import__("ast").literal_eval(m.group(0))
                    except Exception:
                        continue
                    if not isinstance(v, str):
                        continue
                    for mm in R.Q.finditer(v):
                        q = R.pair(mm)
                        if len(V.norm(q)) < a.min_len or R.found(q, a):
                            continue
                        out.append((cell, rel, a0, q, "literal"))
    return out


def main():
    commit = sys.argv[1]
    ap = R.build_parser()
    a = ap.parse_args(["--commit", commit] + sys.argv[2:])
    docs = V.load()
    a.corpus = V.Corpus(docs, V.norm) if a.unit == "gone" else None
    d = R.tree_dir(a.tree)
    base = d or V.ROOT
    print("对象 %s → 物化树 %s" % (a.tree, "就地" if d is None else "临时"))
    print("量法 %s" % R.flagline(a).strip())
    try:
        rows, tot = R.tally(base, a)
        printed = {name: n for name, n, _k in rows}
        print("   器印的合计 %d 处 / %d 条" % (tot[0], tot[1]))

        aw = ap.parse_args(["--commit", commit] + sys.argv[2:] + ["--face", "whole"])
        al = ap.parse_args(["--commit", commit] + sys.argv[2:] + ["--face", "literal"])
        aw.corpus = al.corpus = a.corpus      # `found()` 要用；不带上会 AttributeError（我第一版就栽在这）
        W, L = enum(base, aw), enum(base, al)

        # ── 自证①：逐格处数与器印的逐位相同（whole 面）
        bycell = {}
        for cell, _r, _ln, _q, _f in W:
            bycell[cell] = bycell.get(cell, 0) + 1
        ok = all(bycell.get(k, 0) == v for k, v in printed.items()) and \
            len(W) == tot[0] and sum(bycell.values()) == len(W)
        print("   自证① 逐格处数 vs 器印：%s" % ("**逐位相同** ✓" if ok else "★ 不等 ⇒ 本脚本的枚举与器不是同一件事，结论不印"))
        for k in sorted(printed):
            print("          %-10s 本脚本 %4d · 器 %4d" % (k, bycell.get(k, 0), printed[k]))
        if not ok:
            raise SystemExit(9)

        # ── 差集：whole 里配出来、literal 里配不出来的那 98 处
        Lf = {}
        for _c, rel, _ln, q, _f in L:
            Lf.setdefault(rel, set()).add(q)
        D = [x for x in W if x[3] not in Lf.get(x[1], ())]
        print("   自证② whole %d 处 · literal %d 处 ⇒ 差 %d 处（逐格：%s）"
              % (len(W), len(L), len(D),
                 " ".join("%s %d" % (k, sum(1 for x in D if x[0] == k)) for k in sorted(printed))))

        # ── ★★ 两个"差"不是同一个量：**逐格处数相减** vs **按键取集合差**
        #    前者把「同一个键在两侧各出现几次」这对多寡也算进差里 ⇒ 差值里混着**重数**。
        #    卡面那个 98 是前者；本脚本上面印的 91 是后者。
        lbc, wbc = {}, {}
        for cell, _r, _ln, _q, _f in L:
            lbc[cell] = lbc.get(cell, 0) + 1
        for cell, _r, _ln, _q, _f in W:
            wbc[cell] = wbc.get(cell, 0) + 1
        print("   两把尺：逐格处差 Σ = %d · 按键集合差 = %d  ⇒ **差 %d**"
              % (len(W) - len(L), len(D), (len(W) - len(L)) - len(D)))
        print("     %-10s %6s %8s %8s %8s" % ("格", "whole", "literal", "处差", "集合差"))
        for k in sorted(printed):
            print("     %-10s %6d %8d %8d %8d"
                  % (k, wbc.get(k, 0), lbc.get(k, 0), wbc.get(k, 0) - lbc.get(k, 0),
                     sum(1 for x in D if x[0] == k)))
        # 集合差在 config.py 那一格的全部成员（给 nova §一 那条「配对中间有没有一整条语句」当对照）
        print("   集合差里 config.py 那一格的全部 %d 处："
              % sum(1 for x in D if x[0] == "config.py"))
        for cell, rel, ln, q, _f in sorted([x for x in D if x[0] == "config.py"],
                                           key=lambda x: x[2]):
            print("     %-22s 长%3d 内换行%d %s" % ("%s:%d" % (rel, ln), len(q), q.count("\n"),
                                                    q[:46].replace("\n", "⏎")))
        # 重数抵消掉的那几处（在 whole 里、键在 literal 里也有 ⇒ 集合差看不见）
        gone = [x for x in W if x[3] in Lf.get(x[1], ()) and x not in D]
        print("   重数抵消（键在 literal 里也有 ⇒ 集合差看不见的全部）：%d 处" % len(gone))
        for cell, rel, ln, q, _f in sorted(gone, key=lambda x: (x[1], x[2]))[:20]:
            print("     %-40s %-8s 长%3d 内换行%d" % ("%s:%d" % (rel, ln), cell, len(q), q.count("\n")))

        # ── ★ 「条」那一栏同一个病：全局去重也要分**两把尺**
        kw = {x[3] for x in W}
        kl = {x[3] for x in L}
        print("   条：全局去重 raw  whole %d 条 · literal %d 条 ⇒ 逐格条差 Σ = %d · 按键集合差 = %d（Δ%d）"
              % (len(kw), len(kl),
                 sum(len({x[3] for x in W if x[0] == k}) - len({x[3] for x in L if x[0] == k})
                     for k in sorted(printed)), len(kw - kl), (len(kw) - len(kl)) - len(kw - kl)))

        # ── ★ 键里含 ASCII 双引号的那些（= nova 表里那 13 行）
        dq = [x for x in D if '"' in x[3]]
        print("   键里含 ASCII 双引号的差 = %d 处" % len(dq))
        for cell, rel, ln, q, _f in sorted(dq, key=lambda x: (x[1], x[2])):
            inner = [z for z in q.split('"') if z.strip()]
            print("     %-24s %-26s 长%3d 内换行%d 片段%d" %
                  ("%s:%d" % (rel, ln), cell, len(q), q.count("\n"), len(inner)))
    finally:
        if d:
            import shutil
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    main()
