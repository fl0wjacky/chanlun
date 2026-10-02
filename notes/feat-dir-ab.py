#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""探针 · 特征序列**合并方向**开关（小栋 2026-10-02 ⑤ / card-205e04ea-302）。

三条读数：

  ① **A ≡ 改动前**：把 `origin/main` 那份 core/segment.py 抠出来当旧模块，
     同一份数据上 `新.build_segments(pens, mode="A")` 与 `旧.build_segments(pens)`
     逐条**全字段**比（不是比签名）—— 必须 0 处不同。
  ② **B 的效果**：A/B 两份的段数对照表（逐份列出，不挑）。
  ③ **B 的自洽**：用引擎的独立复核器 `verify_by_definition(segs, pens, mode="B")` 复核 B 的线段，
     违规应为 0（复核器里那份 std_feats 是**另写一遍**的实现，不是共用）。

★ 阳性对照（缺了它就等于没测）：数出开关**真的被走到过** —— 即构建过程中
  有多少次「A 的方向判断」与「B 的方向判断」不同。为 0 ⇒ B 这一支根本没被触发。

用法：python3 notes/feat-dir-ab.py <tree> [<旧 segment.py 路径>]
     旧文件默认从 git 取 `origin/main:core/segment.py`。
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import types


def load(tree, name):
    b = json.load(open(os.path.join(tree, "data", name), encoding="utf-8"))
    if isinstance(b, dict):
        b = b.get("bars") or b.get("klines") or b
    return b


def load_old_module(tree):
    src = subprocess.run(["git", "-C", tree, "show", "origin/main:core/segment.py"],
                         capture_output=True, text=True, check=True).stdout
    # 相对 import 换成绝对，其余一字不动
    src = src.replace("from .kline import fractals", "from core.kline import fractals")
    mod = types.ModuleType("_old_segment")
    mod.__file__ = "<origin/main:core/segment.py>"
    exec(compile(src, "<origin/main:core/segment.py>", "exec"), mod.__dict__)
    return mod, hashlib.sha1(src.encode()).hexdigest()[:8]


def sig(segs):
    return hashlib.sha256(json.dumps(
        [[s["PI0"], s["PI1"], s["dir"], s["case"], round(float(s["p1"]), 8)] for s in segs],
        ensure_ascii=False).encode()).hexdigest()[:12]


def main(tree):
    sys.path.insert(0, tree)
    import core
    import core.segment as S

    old, old_sha = load_old_module(tree)
    print("树 %s ｜ 旧模块 = origin/main:core/segment.py (sha1 %s)" % (tree, old_sha))

    runs = []
    for f in sorted(os.listdir(os.path.join(tree, "data"))):
        if not f.endswith(".json"):
            continue
        try:
            runs.append((f, core.analyze(load(tree, f))["pens"]))
        except Exception as e:
            print("   跳过 %s：%s" % (f, e))
    print("可跑 %d 份 ｜ %d 笔" % (len(runs), sum(len(p) for _, p in runs)))

    # ---------------------------------------------------------------- ① A ≡ 旧
    print("\n① 默认 A 与改动前逐条比（全字段，不是签名）")
    bad = []
    for f, p in runs:
        a, b = S.build_segments(p, mode=S.FEAT_STD_A), old.build_segments(p)
        if a != b:
            bad.append(f)
        # 复核器也要比（它内部另写了一份 std_feats）
        va, vb = S.verify_by_definition(a, p, mode=S.FEAT_STD_A), old.verify_by_definition(b, p)
        if va != vb:
            bad.append(f + "(verify)")
    print("   两份不同的：%d 处 %s" % (len(bad), bad if bad else "✓"))
    # 显式把默认值也走一遍（怕有人把默认改掉）
    d = [f for f, p in runs if S.build_segments(p) != old.build_segments(p)]
    print("   不传 mode（吃默认值）也不同的：%d 处 ✓" % len(d))

    # ---------------------------------------------------------------- 阳性对照
    hits = {"n": 0, "diff": 0}
    real_fs = S._feature_std

    def counting_fs(elems, up, mode=S.FEAT_STD_DEFAULT):
        ra = real_fs(elems, up, S.FEAT_STD_A)
        rb = real_fs(elems, up, S.FEAT_STD_B)
        hits["n"] += 1
        if ra != rb:
            hits["diff"] += 1
        return rb

    S._feature_std = counting_fs
    b_segs = {}
    for f, p in runs:
        b_segs[f] = S.build_segments(p, mode=S.FEAT_STD_B)
    S._feature_std = real_fs
    print("\n阳性对照：_feature_std 被调 %d 次，其中『A 与 B 结论不同』的 %d 次 %s"
          % (hits["n"], hits["diff"], "✓ 开关确实被走到" if hits["diff"] else "✗ B 这一支没被触发"))

    # ---------------------------------------------------------------- ② A/B 对照表
    print("\n② A/B 段数对照（每份都列）")
    print("   %-22s %6s %6s %6s   %s" % ("数据", "笔", "A 段", "B 段", "段签名"))
    n_diff = 0
    for f, p in runs:
        a = S.build_segments(p, mode=S.FEAT_STD_A)
        b = b_segs[f]
        same = sig(a) == sig(b)
        n_diff += (not same)
        print("   %-22s %6d %6d %6d   %s" % (f, len(p), len(a), len(b),
                                             "同" if same else "★ 不同"))
    print("   ⇒ 段数或段界变化的：%d/%d 份" % (n_diff, len(runs)))

    # ---------------------------------------------------------------- ③ B 的自洽
    print("\n③ B 的线段过独立复核器（verify_by_definition, mode=B）")
    tot = 0
    for f, p in runs:
        v = S.verify_by_definition(b_segs[f], p, mode=S.FEAT_STD_B)
        tot += len(v)
        if v:
            print("   ★ %-22s 违规 %d：%s" % (f, len(v), v[:3]))
    print("   违规合计：%d %s" % (tot, "✓" if tot == 0 else "✗"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "."))
