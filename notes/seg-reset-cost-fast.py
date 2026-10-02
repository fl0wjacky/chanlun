# -*- coding: utf-8 -*-
"""③ 的「整段重算比例 + 单根最坏笔数」快量 —— 不跑 build_segments，只数签名分支。

Nova 问：改成「非纯追加一律整段重算」后，尾端点被换最常见，那增量还剩多少？
量两件事：
  · 每根走「整段重算」那一路的比例（full 口径：尾换 + 缩水/深处 都整段；noop/追加才是 O(1)）
  · 单根最坏要算多少笔（整段重算那一刻的 penCount）

只推 Guarded 的 seq、数三路签名，不逐根 build_segments —— 秒级跑完，专门补 zec15 那一格。

用法：python3 notes/seg-reset-cost-fast.py [--max-bars N] [--random K]
"""
import argparse
import importlib.util
import io
import json
import os
import random
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

P = os.path.join(HERE, "pine-incremental-pen.py")
_spec = importlib.util.spec_from_file_location("incpen", P)
_incpen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_incpen)
Guarded = _incpen.Guarded
IncKline = _incpen.IncKline
rand_bars = _incpen.rand_bars
tick_of_soft = _incpen.tick_of_soft

SKIP = ("annot", "mag", "sub")


def _k(f):
    return f["k"] if f is not None else -1


class Counter:
    """数三路签名 + 最坏 penCount（整段重算那一刻）。"""

    def __init__(self):
        self.pens = []
        self.sig = [-1, -1, -1]
        self.n_noop = 0
        self.n_append = 0
        self.n_tail = 0
        self.n_reset = 0
        self.max_pen = 0          # 整段重算时的最坏 penCount
        self.max_rescan = 0       # 尾换时（partial 口径）的最坏重扫宽度 penCount - seg_i
        self.seg_i = 0            # 最后已确认段 endPen+1 的近似：这里没跑段扫描，用 pens 数近似
        # 说明：max_rescan 的精确值在 seg-reset-cost-probe.py（带段扫描）里；这里只给上限参考。

    def apply(self, seq):
        M = len(seq)
        e1 = _k(seq[M - 1]) if M >= 1 else -1
        e2 = _k(seq[M - 2]) if M >= 2 else -1
        e3 = _k(seq[M - 3]) if M >= 3 else -1
        penCount = M - 1 if M >= 1 else 0
        if penCount != len(self.pens) or e1 != self.sig[0] or e2 != self.sig[1] or e3 != self.sig[2]:
            if penCount == len(self.pens) + 1 and e2 == self.sig[0] and e3 == self.sig[1]:
                self.pens.append(None)
                self.n_append += 1
            elif penCount == len(self.pens) and penCount > 0 and e2 == self.sig[1]:
                self.n_tail += 1
                self.max_pen = max(self.max_pen, penCount)      # full 口径：尾换也整段
            else:
                self.n_reset += 1
                self.max_pen = max(self.max_pen, penCount)
            self.sig = [e1, e2, e3]
            self.pens = [None] * penCount                       # 同步长度
        else:
            self.n_noop += 1
        self.max_pen = max(self.max_pen, penCount)              # 全程最坏 penCount 也记一笔
        return


def run(bars, tick, name, max_bars=None):
    inc_k = IncKline()
    g = Guarded("old", 4)
    c = Counter()
    if max_bars:
        bars = bars[:max_bars]
    for k in range(len(bars)):
        inc_k.push(bars[k]["h"], bars[k]["l"])
        std, fx = inc_k.snapshot()
        g.update(std, fx)
        c.apply(g.seq)
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-bars", type=int, default=None)
    ap.add_argument("--random", type=int, default=60)
    a = ap.parse_args()
    t0 = time.time()

    files = [f for f in sorted(os.listdir(os.path.join(ROOT, "data")))
             if f.endswith(".json") and not any(x in f for x in SKIP)]

    def load(fn):
        b = json.load(io.open(os.path.join(ROOT, "data", fn), encoding="utf-8"))
        if isinstance(b, dict):
            b = b.get("bars") or b.get("klines") or b
        return b or []

    cache = {fn: load(fn) for fn in files}
    files.sort(key=lambda fn: len(cache[fn]))
    print("── ③ 整段重算比例 + 单根最坏笔数（full 口径：尾换也整段）──\n")
    for fn in files:
        bars = cache[fn]
        if not bars:
            continue
        try:
            tick = tick_of_soft(fn)
        except Exception:                       # noqa: BLE001
            tick = None
        c = run(bars, tick, fn, max_bars=a.max_bars)
        n = len(bars) if not a.max_bars else min(len(bars), a.max_bars)
        heavy = c.n_tail + c.n_reset
        print("  %-20s 根 %6d | 追加%4d 尾换%4d 缩深%3d 无事%5d | O(n)根 %.1f%% | 最坏 %d 笔"
              % (fn, n, c.n_append, c.n_tail, c.n_reset, c.n_noop,
                 100.0 * heavy / n if n else 0.0, c.max_pen))

    rng = random.Random(20261002)
    print("\n  （随机 %d 条只压稳健性，不单列）" % a.random)
    print("  用时 %.0fs" % (time.time() - t0))


if __name__ == "__main__":
    sys.exit(main())
