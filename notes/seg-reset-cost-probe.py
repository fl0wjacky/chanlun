# -*- coding: utf-8 -*-
"""③ 两种修法的代价 + Nova 的「部分重算」提案，三支同跑、逐根对账。

Nova 钉两点：
  1) 改成「非纯追加一律整段重算」后，尾端点被换（最后一笔延伸）是最常见的动作，
     那增量还剩多少？量：九份数据每根走「整段重算」的比例 + zec15 单根最坏算几笔。
  2) 不想整段重算的话：已确认段之前的位置不会再被翻动吧？那就只从最后一个已确认段
     的末笔之后重扫，不必从 0。能不能既对又省？

三支（同一份 Guarded 的 seq，三支引擎并行喂，比同一份 build_segments 整段参照）：

  old       旧三路（正臂）：尾端点被换只重推最后一笔、扫描游标不动。**必须在
            zec_1h@159 红**（skip-flip：i 只增不回，跳过去的位置不再问）。
  full      现在的 pine：尾换也整段重算（清空摊平 + 从 0 重扫）。已知 0 分歧。
  partial   Nova 的提案：尾换只改最后一笔、已确认段 segs 不动、游标回退到
            「最后已确认段 endPen+1」重扫（born 也回退到该段之后的 born）。
            缩水/跳变/深处回改仍整段重算。

代价口径：
  noop/append = O(1) 那档；tail/reset = O(n) 那档（full 两支都是 O(penCount)；
  partial 的 tail 是 O(penCount − segI)，reset 才 O(penCount)）。
  记 max_pen = 整段重算时的最坏 penCount（zec15 单根最坏要算几笔）、
  max_rescan = partial 尾换时的最坏重扫宽度 penCount − segI。

用法：
    python3 notes/seg-reset-cost-probe.py --max-bars 3000     # 先小跑验
    python3 notes/seg-reset-cost-probe.py                      # 全量
退出码：0 三支都与整段一致 ｜ 1 有分歧 ｜ 2 跑不动
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

S = os.path.join(HERE, "pine-incremental-seg.py")
_sspec = importlib.util.spec_from_file_location("incseg", S)
_incseg = importlib.util.module_from_spec(_sspec)
_sspec.loader.exec_module(_incseg)
_mk_seg = _incseg._mk_seg
_mk_live = _incseg._mk_live

from core.pen import _pens_of                                       # noqa: E402
from core.segment import build_segments, _dir, _opening_overlaps, _case_at, FEAT_STD_A  # noqa: E402

SKIP = ("annot", "mag", "sub")


def _pen_of(a, b):
    return dict(i0=a["i"], i1=b["i"], x0=a["k"], x1=b["k"],
                p0=a["price"], p1=b["price"],
                hi=max(a["price"], b["price"]), lo=min(a["price"], b["price"]))


def _flatten(seq):
    return [_pen_of(seq[t], seq[t + 1]) for t in range(len(seq) - 1)]


def _k(f):
    return f["k"] if f is not None else -1


class SegEngine:
    """zSegStep 的 Python 版，variant 决定「尾端点被换」那一路怎么走。"""

    VARIANTS = ("old", "full", "partial")

    def __init__(self, variant):
        assert variant in self.VARIANTS, variant
        self.variant = variant
        self.pens = []
        self.sig = [-1, -1, -1]
        self.segs = []
        self.i = 0               # 实际扫描游标（skip 会前进）
        self.born = 0
        self.seg_i = 0           # 最后已确认段 endPen+1（只有确认一段才更新）
        self.seg_born = 0        # 最后已确认段之后的 born
        self.n_noop = 0
        self.n_append = 0
        self.n_tail = 0
        self.n_reset = 0
        self.max_pen = 0         # 整段重算时的最坏 penCount
        self.max_rescan = 0      # partial 尾换时的最坏重扫宽度 penCount - seg_i

    def step(self, seq):
        M = len(seq)
        e1 = _k(seq[M - 1]) if M >= 1 else -1
        e2 = _k(seq[M - 2]) if M >= 2 else -1
        e3 = _k(seq[M - 3]) if M >= 3 else -1
        penCount = M - 1 if M >= 1 else 0
        if penCount != len(self.pens) or e1 != self.sig[0] or e2 != self.sig[1] or e3 != self.sig[2]:
            if penCount == len(self.pens) + 1 and e2 == self.sig[0] and e3 == self.sig[1]:
                # 纯追加
                self.pens.append(_pen_of(seq[penCount - 1], seq[penCount]))
                self.n_append += 1
            elif penCount == len(self.pens) and penCount > 0 and e2 == self.sig[1]:
                # 尾端点被换
                self.n_tail += 1
                if self.variant == "old":
                    # 旧三路（正臂）：只重推最后一笔，游标/seg_i/born 全不动 ⇒ skip-flip
                    self.pens[penCount - 1] = _pen_of(seq[penCount - 1], seq[penCount])
                elif self.variant == "full":
                    self.pens = _flatten(seq)
                    self.segs = []
                    self.i = 0
                    self.born = 0
                    self.seg_i = 0
                    self.seg_born = 0
                    self.max_pen = max(self.max_pen, penCount)
                else:  # partial：只改最后一笔，已确认段不动，游标回退到 seg_i 重扫
                    self.pens[penCount - 1] = _pen_of(seq[penCount - 1], seq[penCount])
                    self.i = self.seg_i
                    self.born = self.seg_born
                    self.max_rescan = max(self.max_rescan, penCount - self.seg_i)
            else:
                # 缩水 / 跳变 / 深处回改 ⇒ 一律整段重算
                self.pens = _flatten(seq)
                self.segs = []
                self.i = 0
                self.born = 0
                self.seg_i = 0
                self.seg_born = 0
                self.n_reset += 1
                self.max_pen = max(self.max_pen, penCount)
            self.sig = [e1, e2, e3]
        else:
            self.n_noop += 1
        # 段续扫（镜像 zSegStep 内层）
        pens = self.pens
        n = len(pens)
        i = self.i
        born = self.born
        while i + 2 < n:
            if not _opening_overlaps(pens, i):
                i += 1
                continue
            seg_dir = _dir(pens[i])
            found = None
            k = i + 2
            while k < born:
                k += 2
            while k < n - 1:
                case, resume = _case_at(pens, i, k, seg_dir, FEAT_STD_A)
                if case:
                    found = (k, case, resume)
                    break
                k += 2
                if resume is not None:
                    while k < resume:
                        k += 2
            if found is None:
                break
            end_pen, case, born = found
            born = born or 0
            self.segs.append(_mk_seg(pens, i, end_pen, case, seg_dir))
            i = end_pen + 1
            self.seg_i = i
            self.seg_born = born
        self.i = i
        self.born = born

    def result(self):
        n = len(self.pens)
        i = self.i
        out = list(self.segs)
        if n - i >= 3:
            out.append(_mk_live(self.pens, i, n, _dir(self.pens[i])))
        return out


def probe(bars, tick, name, max_bars=None):
    inc_k = IncKline()
    g = Guarded("old", 4)
    engines = [SegEngine(v) for v in SegEngine.VARIANTS]
    if max_bars:
        bars = bars[:max_bars]
    bad = {v: 0 for v in SegEngine.VARIANTS}
    first = {}
    for k in range(len(bars)):
        inc_k.push(bars[k]["h"], bars[k]["l"])
        std, fx = inc_k.snapshot()
        g.update(std, fx)
        seq = g.seq
        for eng in engines:
            eng.step(seq)
        if len(seq) < 3:
            continue
        want = build_segments(_flatten(seq), mode=FEAT_STD_A)
        for eng in engines:
            if eng.result() != want:
                bad[eng.variant] += 1
                first.setdefault(eng.variant, (k + 1, want, eng.result()))
    return dict(name=name, bars=len(bars), engines=engines, bad=bad, first=first)


def _stat_line(fn, st):
    engs = st["engines"]
    parts = []
    for eng in engs:
        v = eng.variant
        total = st["bars"]
        o1 = eng.n_noop + eng.n_append
        # 各变体的 O(n) 档根数：full 的尾换也整段重算，old/partial 只有缩水/深处才是 O(n)
        heavy = (eng.n_tail + eng.n_reset) if v == "full" else eng.n_reset
        hp = 100.0 * heavy / total if total else 0.0
        cost = ("尾换最宽重扫%d" % eng.max_rescan) if v == "partial" else ("整段最坏%d笔" % eng.max_pen)
        parts.append("%s 分歧%d | O(n)根%.1f%%(尾%d/重%d) | %s"
                     % (v, st["bad"][v], hp, eng.n_tail, eng.n_reset, cost))
    return "  %-20s 根 %6d | %s" % (fn, st["bars"], " | ".join(parts))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-bars", type=int, default=None)
    ap.add_argument("--random", type=int, default=200)
    a = ap.parse_args()

    t0 = time.time()
    print("── ③ 两种修法代价 + partial 提案：old/full/partial 三支同跑、逐根 vs 整段 ──")
    print("  口径：同一份 Guarded 的 seq 喂三支引擎，各自结果逐根比 build_segments。\n")

    files = [f for f in sorted(os.listdir(os.path.join(ROOT, "data")))
             if f.endswith(".json") and not any(x in f for x in SKIP)]

    def load(fn):
        b = json.load(io.open(os.path.join(ROOT, "data", fn), encoding="utf-8"))
        if isinstance(b, dict):
            b = b.get("bars") or b.get("klines") or b
        return b or []

    cache = {fn: load(fn) for fn in files}
    files.sort(key=lambda fn: len(cache[fn]))
    total_bars = 0
    any_bad = False
    for fn in files:
        bars = cache[fn]
        if not bars:
            continue
        try:
            tick = tick_of_soft(fn)
        except Exception:                       # noqa: BLE001
            tick = None
        st = probe(bars, tick, fn, max_bars=a.max_bars)
        total_bars += st["bars"]
        any_bad |= any(st["bad"].values())
        print(_stat_line(fn, st))
        for v, kk in st["first"].items():
            k, want, got = kk
            print("        → %s 首处 @第 %d 根：整段 %s  vs  %s" % (v, k, want[:2], got[:2]))

    print("\n  ── 随机行情（压深处回改）──")
    rng = random.Random(20261002)
    rand_bad = {v: 0 for v in SegEngine.VARIANTS}
    rand_total = 0
    for t in range(a.random):
        tick = rng.choice((0.1, 0.25, 0.5, 1.0, 2.0))
        n = rng.randint(40, 500)
        bars = rand_bars(rng, n, tick)
        st = probe(bars, tick, "rand#%d" % t)
        rand_total += st["bars"]
        for v in SegEngine.VARIANTS:
            if st["bad"][v]:
                rand_bad[v] += 1
                any_bad = True
    print("  ✓ %d 条随机（%d 根）：分歧 old=%d full=%d partial=%d"
          % (a.random, rand_total, rand_bad["old"], rand_bad["full"], rand_bad["partial"]))

    print("\n  真实 %d 根 + 随机 %d 根 | 用时 %.0fs" % (total_bars, rand_total, time.time() - t0))
    if any_bad:
        print("⇒ 有分歧（old 那支本来就该红；full/partial 若红则是新发现）。")
        return 1
    print("⇒ 三支 0 分歧：full 与 partial 都在深处回改下逐根 == 整段。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
