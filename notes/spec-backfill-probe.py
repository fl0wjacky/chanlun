#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""探针 · 审计表 #28a / #39 这两条**边界**换掉之后，看盘结果变不变。
  · #28a 是『原文没说、程序自定』 ⇒ 量的是**这个自定有多大后果**；
  · #39 是『**原文有据**』（`L78:39-41`，2026-10-02 由『程序自定』改判）
    ⇒ 量的是**这条边界删了会不会被发现**（防空支：一条没人能观测的判据等于没写）。

用法：python3 probe-boundary.py <tree>
  tree = 仓库树根（要有 core/ 与 data/）

#28a（`core/segment.py::_feature_std` 第 65 行）
     `go_up = up if len(m) < 2 else (a["h"] > m[-2]["h"])`
     特征序列**开头**两元素互相包含时，取高高还是取低低 —— 原文没规定；
     程序选了『跟着本段方向』。探针把它**翻过来**（up → not up）。
     注意 `up` 在这个函数里只出现在这一行 ⇒ 翻转它只动这一支，不牵连别处。

#39（`core/segment.py::_reverse_scan`）
     第二种情况的确认序列，程序加了『价格重新越过端点即止』的边界；
     函数注释原先自承『v2 实测：加不加这条，结果完全一样』（**2026-10-02 已按本探针的
     读数更正** —— 那句话在现树上是假的）。探针**去掉那个 break**
     （仍记录首个越过笔，保证 brk 语义不变），量这句话现在还成不成立。

★ 两侧都有**阳性对照**：补丁必须至少改变过一次被调函数的结论，
  否则『结果没变』只说明补丁没接上。
"""
import hashlib
import json
import os
import sys


def load(tree, name):
    b = json.load(open(os.path.join(tree, "data", name), encoding="utf-8"))
    if isinstance(b, dict):
        b = b.get("bars") or b.get("klines") or b
    return b


def sig(segs):
    return hashlib.sha256(json.dumps(
        [[s["PI0"], s["PI1"], s["dir"], s["case"], round(float(s["p1"]), 8)] for s in segs],
        ensure_ascii=False).encode()).hexdigest()[:12]


def main(tree):
    sys.path.insert(0, tree)
    import core
    import core.segment as S

    runs = []
    for f in sorted(os.listdir(os.path.join(tree, "data"))):
        if not f.endswith(".json"):
            continue
        try:
            runs.append((f, core.analyze(load(tree, f))["pens"]))
        except Exception:
            continue
    base = {f: sig(S.build_segments(p)) for f, p in runs}
    base_n = {f: len(S.build_segments(p)) for f, p in runs}
    print("树 %s ｜ 可跑 %d 份 ｜ %d 笔" % (tree, len(runs), sum(len(p) for _, p in runs)))

    # ---------------------------------------------------------------- #28a
    orig_fs = S._feature_std
    hit = {"n": 0, "diff": 0}

    def flip(elems, up):
        return orig_fs(elems, not up)

    S._feature_std = flip
    e1 = {f: sig(S.build_segments(p)) for f, p in runs}
    n1 = {f: len(S.build_segments(p)) for f, p in runs}
    # 阳性对照：直接调被替换的函数，确认它真的换了行为
    probe = [dict(h=10, l=5, i=0), dict(h=12, l=4, i=1)]
    hit["diff"] = int(orig_fs(probe, True) != flip(probe, True))
    S._feature_std = orig_fs
    d1 = [f for f in base if base[f] != e1[f]]
    print("\n#28a 特征序列开头取高高/低低（翻转）")
    print("   阳性对照：翻转后同一输入的结果不同 = %s" % ("是 ✓" if hit["diff"] else "否 ✗ 补丁没接上"))
    for f in d1:
        print("   ★ %-20s 段 %d → %d" % (f, base_n[f], n1[f]))
    print("   ⇒ 段签名变了 %d/%d 份 %s" % (len(d1), len(runs), "（**会改变结果**）" if d1 else "（本数据上不变）"))

    # ---------------------------------------------------------------- #39
    orig_rs = S._reverse_scan
    calls = {"n": 0, "diff": 0}

    def rs_nobound(pens, end_pen, seg_dir):
        pivot = pens[end_pen]["p1"]
        rev_dir = "down" if seg_dir == "up" else "up"
        want2 = "bot" if rev_dir == "down" else "top"
        tail, brk = [], None
        for j in range(end_pen + 1, len(pens)):
            p = pens[j]
            if brk is None and ((seg_dir == "up" and p["hi"] > pivot)
                                or (seg_dir != "up" and p["lo"] < pivot)):
                brk = j
            tail.append(p)
        r = (False, brk) if len(tail) < 3 else (
            len(S._fractals_of(tail, 0, rev_dir, want2)[0]) > 0, brk)
        calls["n"] += 1
        if r[0] != orig_rs(pens, end_pen, seg_dir)[0]:
            calls["diff"] += 1
        return r

    S._reverse_scan = rs_nobound
    e2 = {f: sig(S.build_segments(p)) for f, p in runs}
    n2 = {f: len(S.build_segments(p)) for f, p in runs}
    S._reverse_scan = orig_rs
    d2 = [f for f in base if base[f] != e2[f]]
    print("\n#39 去掉 _reverse_scan 的『越过端点即止』边界")
    print("   阳性对照：_reverse_scan 被调 %d 次，其中『确认与否』结论不同的 %d 次 %s"
          % (calls["n"], calls["diff"], "✓" if calls["diff"] else "✗ 补丁没接上"))
    for f in d2:
        print("   ★ %-20s 段 %d → %d" % (f, base_n[f], n2[f]))
    print("   ⇒ 段签名变了 %d/%d 份 %s" % (len(d2), len(runs),
                                          "（**会改变结果**）" if d2 else "（本数据上不变）"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "."))
