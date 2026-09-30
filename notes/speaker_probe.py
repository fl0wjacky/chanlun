#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""说话人轴 · **先量再落**：三栏的三个分母到底是多少（用器自己的 Q/pair/found/norm，不另写尺）。

跑法：  python3 notes/speaker_probe.py <commit> [--min-len N --ladder ...]

★ 为什么不直接手算：@nova-8980 裁过 —— **拆分脚本必须自己算并印**全局去重的那个数，
  手算上卡 = 卡上两个数长得一样（一个器印的、一个人打的）。
★ 本脚本**不改器**，只是把"三栏要用的分母"量出来给落器那一笔当证据。
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import verify_quotes as V                                   # noqa: E402
import quotes_recount as R                                  # noqa: E402

# 「面」的机械定义：**引文出现在哪几格里** —— 不看内容，只看落点。
#   卡片面 = cards/ + render/（真正在引缠师原文的那两格）
#   代码面 = core/ + tools/ + config.py（我们自己在引自己的话）
# ★ 这是**出现**的属性，不是引文的属性：同一条可以两面都出现 ⇒ 必须单列「两面」，
#   不许折进任一面（折进去 = 把一个"跨"写成一个"是"）。
CARD = ("cards", "render")
CODE = ("core", "tools", "config.py")


def sites(base, a):
    """把器「数出来的每一处」逐处列出来：(格, 引文原文)。判据与 `count()` 逐行同。"""
    out = []
    cells = list(R.CELLS) + (["config.py"] if a.face == "whole" else [])
    for cell in cells:
        root_ = os.path.join(base, cell) if cell != "config.py" else None
        if cell == "config.py":
            if not os.path.isfile(os.path.join(base, "config.py")):
                continue
            files = [(base, "config.py")]
            walk = [files[0]]
        else:
            if not os.path.isdir(root_):
                continue
            walk = []
            for r, _d, fs in os.walk(root_):
                if a.v1ref == "skip" and "v1_ref" in r:
                    continue
                if any(("/%s" % s.split("/")[-1]) in r or r.endswith(s)
                       for s in V.SKIP if s.split("/")[-1] != "v1_ref" or a.v1ref == "skip"):
                    continue
                for f in sorted(fs):
                    if f.endswith(".py"):
                        walk.append((r, f))
        for r, f in walk:
            t = io.open(os.path.join(r, f), encoding="utf-8").read()
            texts = [t] if a.face == "whole" else R.literal_bodies(t)
            for body in texts:
                for m in R.Q.finditer(body):
                    q = R.pair(m)
                    k = V.norm(q)
                    if len(k) < a.min_len:
                        continue
                    if R.found(q, a):
                        continue
                    out.append((cell, q))
    return out


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    commit = sys.argv[1]
    ap = R.build_parser()
    a = ap.parse_args(["--commit", commit] + [x for x in sys.argv[2:]])
    docs = V.load()
    a.corpus = V.Corpus(docs, V.norm) if a.unit == "gone" else None
    d = R.tree_dir(a.tree)
    base = d or V.ROOT
    print("对象 %s → 物化树 %s" % (a.tree, "就地（工作目录）" if d is None else "临时"))
    print("量法 量法=%s" % R.flagline(a).strip())
    try:
        rows, tot = R.tally(base, a)
        for name, n, k in rows:
            print("   %-10s %4d 处 / %4d 条" % (name, n, k))
        print("   %-10s %4d 处 / %4d 条   ← 器印的合计（Σ逐格去重）" % ("合计", tot[0], tot[1]))
        S = sites(base, a)
        assert len(S) == tot[0], "逐处枚举 %d ≠ 器印的 %d" % (len(S), tot[0])
        # 全局去重：两把钥匙，**都印出来并点名**（@iris-64a1：两个都叫「全局去重」）
        raw = {q for _c, q in S}
        nrm = {V.norm(q) for _c, q in S}
        print("   全局去重（raw 钥匙）= %d 条 · （norm 钥匙）= %d 条" % (len(raw), len(nrm)))
        # 面：按"出现在哪几格"分类（跨面单列）
        face = {}
        for q in raw:
            cs = {c for c, x in S if x == q}
            card, code = cs & set(CARD), cs & set(CODE)
            face[q] = "卡片面" if card and not code else ("代码面" if code and not card else "两面")
        for f in ("卡片面", "代码面", "两面"):
            qs = [q for q in raw if face[q] == f]
            occ = sum(1 for _c, q in S if face[q] == f)
            print("   面 %-4s %4d 处 / %4d 条" % (f, occ, len(qs)))
        print("   ★ 三栏的**处**分母 = %d；**条**分母 = 全局去重（raw）= %d（不是 %d）"
              % (tot[0], len(raw), tot[1]))
    finally:
        if d:
            import shutil
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    main()
