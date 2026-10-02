# -*- coding: utf-8 -*-
"""量：前提③ 线段层的「上一层」只取真合成过的（nmerge>1），会改掉多少信号？（只读）

★★ 为什么两支 higher **都显式自己构造**，不去抓 `signals._higher_centers`：

    原来这脚本写的是 `ORIG = S._higher_centers`（从模块里现抓）＋ monkeypatch。**那是个真 bug**：
    代码一改，「现口径」那一栏抓到的就已经是**改后**的版本 ⇒ 变成「滤 vs 滤」自比自，
    **0 是空的**，而屏幕上与一次真结论**逐字同形**。2026-10-02 实测踩过 —— 这脚本合进 main
    之后再跑就不复现当初那个 154｜154 了（@bram-9d29 复跑时撞上，他数出来的）。

    ⇒ 教训（比这一处代码大）：**探针不许读被测对象本身**。读数要能被复跑，探针就得**独立于
      当前版本**把两支都算出来。凡「改前／改后对比」的脚本都适用这一条。

★ 阳性对照：两支 higher **必须真的不同**（不同几组由实测定），否则这次比较不成立 ——
  不然又是一个自比自，屏幕上还是绿的。

    python3 notes/p3-filter-experiment.py
"""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.analyze import analyze_file          # noqa: E402
from core.extend import build_hierarchy        # noqa: E402

S = importlib.import_module("core.signals")

FILES = ["zec15.json", "zec_1h.json", "zec_4h.json", "btc_4h.json",
         "aaplusdt_4h.json", "aaplusdt_30m.json"]
LEVELS = ("pen", "seg")


def higher_unfiltered(r, level):
    """**不滤**的上一层 —— 与 `core/signals.py:_higher_centers` 的几何取法逐行同源，
    但这里**自己写死**，不调那个函数（调它就回到自比自了）。"""
    if level == "pen":
        return r["seg_centers"]
    done = [s for s in r["segs"] if not s.get("live")]
    return build_hierarchy(r["seg_centers"], done) if r["seg_centers"] else []


def higher_filtered(r, level):
    """只取真合成过的。★ **笔层不滤** —— `seg_centers` 是原始中枢、身上没有 `nmerge`，
    一律 `.get(...,1)` 会把它整栏滤空（这是同一类坑的第三次现身）。"""
    if level == "pen":
        return r["seg_centers"]
    return [c for c in higher_unfiltered(r, level) if c.get("nmerge", 1) > 1]


def sig_set(r, level, higher_fn):
    old = S._higher_centers
    S._higher_centers = higher_fn
    try:
        return {(s["kind"], s["bar"]) for s in S.signals(r, level, "macd")}
    finally:
        S._higher_centers = old


def main():
    n_groups = n_higher_diff = n_sig_diff = 0
    tot_unf = tot_fil = 0
    for level in LEVELS:
        for fn in FILES:
            r = analyze_file(fn)
            hu, hf = higher_unfiltered(r, level), higher_filtered(r, level)
            a = sig_set(r, level, higher_unfiltered)
            b = sig_set(r, level, higher_filtered)
            n_groups += 1
            tot_unf += len(a)
            tot_fil += len(b)
            hd = len(hu) != len(hf)
            n_higher_diff += hd
            if a != b:
                n_sig_diff += 1
            print("  %-18s %-3s higher %2d→%2d%s ｜ 信号 %3d / %3d ｜ set 相等 %s"
                  % (fn, level, len(hu), len(hf), " ★" if hd else "  ",
                     len(a), len(b), a == b))

    print()
    # ── 阳性对照：两支 higher 一个组都没差 ⇒ 这次比较是空的，不许印结论 ────────────
    if n_higher_diff == 0:
        print("★ 阳性对照没过：12 组里两支 higher **一组都没不同** ⇒ 探针没接上，"
              "下面的 0 不能当结论。")
        return 3
    print("阳性对照：%d/%d 组的两支 higher 真的不同 ✓（探针接上了）"
          % (n_higher_diff, n_groups))
    print("合计：不滤 %d ｜ 只取合成过的 %d ⇒ 差 %d ｜ 信号 set 不同的组 %d/%d"
          % (tot_unf, tot_fil, tot_fil - tot_unf, n_sig_diff, n_groups))
    print("⇒ %s" % ("线段层的上一层只取 nmerge>1 **不改变任何信号**（差额落在 higher 数组本身，"
                    "不在买卖点上）" if n_sig_diff == 0 else "★ 有信号变了，见上"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
