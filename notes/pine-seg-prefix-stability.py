#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""③（线段）增量化的**前提探针**：已确认的线段是不是"前缀稳定"的？

要回答的唯一问题：
    pens 每加一根，`build_segments` 里**已确认（非 live）的段**会不会被改写？
    若只是往尾上 append、从不改更早的段界 ⇒ 增量 = 缓存已确认前缀（不可变），只重算 live 尾巴。
    若有改写 ⇒ 增量化要难得多（可能得保留整个特征序列状态）。

判据：对每个前缀 k（3..n），取 build_segments(pens[:k]) 的已确认段序列，
      它必须是 build_segments(pens[:k+1]) 的已确认段序列的**前缀**（逐 (PI0,PI1,case) 比）。
      任何一个 k 上不是前缀 ⇒ 记一处"改写"。

★ 这**不是证明**，是逐前缀的实证。结论只对**当前 engine + 当前数据**成立；
  改 engine 的段判据（尤其 `_case_at` 的待定/确认逻辑）之后要重跑。

用法：
    python3 notes/pine-seg-prefix-stability.py            # 九份全量、逐前缀
    python3 notes/pine-seg-prefix-stability.py --quick    # 只跑小份（快）
退出码：
    0  全稳定
    1  有改写（印出第一处改写的 k 与前后段界）
    2  跑不动
"""
import argparse
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from core import analyze                                             # noqa: E402
from core.segment import build_segments                             # noqa: E402

SKIP = ("annot", "mag", "sub")
QUICK_MAX_PENS = 120          # --quick 时只跑笔数 ≤ 此值的份


def load():
    d = os.path.join(ROOT, "data")
    out = []
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".json") or any(x in fn for x in SKIP):
            continue
        bars = json.load(io.open(os.path.join(d, fn), encoding="utf-8"))
        if isinstance(bars, dict):
            bars = bars.get("bars") or bars.get("klines")
        if not bars:
            continue
        out.append((fn, bars))
    return out


def confirmed(segs):
    """已确认段的关键三元组序列 —— 用它比前缀（段界 + 情况号）。"""
    return [(s["PI0"], s["PI1"], s["case"]) for s in segs if not s.get("live")]


def check_one(fn, pens):
    n = len(pens)
    changed = []
    # 逐 k 比前缀。O(n) 次 build_segments、每次最坏 O(k^2) —— 大份会慢，别和别的大活并跑。
    prev = confirmed(build_segments(pens[:3]))
    for k in range(4, n + 1):
        cur = confirmed(build_segments(pens[:k]))
        if cur[:len(prev)] != prev:
            changed.append((k, prev, cur))
            if len(changed) >= 3:
                break
        prev = cur
    return changed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()

    data = load()
    if not data:
        print("★ data/ 里一份 K 线都没有 ⇒ 跑不动")
        return 2

    bad = []
    for fn, bars in data:
        try:
            pens = analyze(bars)["pens"]
        except Exception as e:                                        # noqa: BLE001
            print("★ %s 引擎跑不动：%s" % (fn, type(e).__name__))
            return 2
        if a.quick and len(pens) > QUICK_MAX_PENS:
            print("%-18s 笔 %4d  —— --quick 跳过" % (fn, len(pens)))
            continue
        changed = check_one(fn, pens)
        if changed:
            bad.append(fn)
            print("%-18s 笔 %4d  ★★ 有改写（%d 处，头一处 k=%d）" % (fn, len(pens), len(changed), changed[0][0]))
            k, prev, cur = changed[0]
            print("     @k=%d  前一版末段=%s  后一版=%s" % (k, prev[-1] if prev else "()", cur[:len(prev) + 1]))
        else:
            print("%-18s 笔 %4d  ✓ 全程稳定" % (fn, len(pens)))

    if bad:
        print("\n★ 有改写，③ 增量化不能只缓存已确认前缀。")
        return 1
    print("\n✓ 全部稳定 ⇒ ③ 增量 = 缓存已确认前缀 + 只重算 live 尾巴。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
