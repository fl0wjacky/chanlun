# -*- coding: utf-8 -*-
"""③ 的**整条流水线**实测：增量（笔同步 + 段续扫）跟整段重算，逐根对账。

`pen-sync-deepfix-probe.py` 只证了「三路守卫维护出来的 pens == 整条重摊平的 pens」，
但 Nova 真正要的是**段对不对**：fix_start 深处回改若真碰进已确认段，守卫漏掉的话，
缓存的 `zSegs` 就 stale，段输出就错 —— 光证 pens 同步不够。

这把尺子把 pine ③ **整条搬成 Python**，喂给真实引擎的增量笔序列（`Guarded`，已被 ②
证明逐前缀 == 批量），每根比对：
        增量输出（zSegs 已确认段 + live 尾巴）
    ==  整段重算 `build_segments(拿整条 seq 重摊平的 pens)`

差异一出来当场红。它把 `pen-sync-deepfix-probe.py` 那条「pens 不漏」的证据和
`pine-incremental-seg.py` 那条「段续扫 == 整段（纯追加时）」的证据**合成一件事**，
而且补上了前面两份都没盖到的那一档：**fix_start 深处回改时**。

用法：
    python3 notes/seg-sync-deepfix-probe.py --max-bars 3000     # 只跑前 N 根（调着用）
    python3 notes/seg-sync-deepfix-probe.py                      # 全部数据 × 每个前缀
退出码：0 增量与整段全程相同 ｜ 1 有分歧 ｜ 2 跑不动
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

# 借 ② 那份的 Guarded + 数据加载，借 ③ 参照那份的 _mk_seg/_mk_live。
P = os.path.join(HERE, "pine-incremental-pen.py")
_spec = importlib.util.spec_from_file_location("incpen", P)
_incpen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_incpen)
Guarded = _incpen.Guarded
IncKline = _incpen.IncKline
load_real = _incpen.load_real
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
    """与 core/pen.py::_pens_of 同义的单笔（字段一个不少）。"""
    return dict(i0=a["i"], i1=b["i"], x0=a["k"], x1=b["k"],
                p0=a["price"], p1=b["price"],
                hi=max(a["price"], b["price"]), lo=min(a["price"], b["price"]))


def _flatten(seq):
    return [_pen_of(seq[t], seq[t + 1]) for t in range(len(seq) - 1)]


def _k(f):
    return f["k"] if f is not None else -1


class PineSeg3:
    """pine ③ 的整条流水线：三路笔同步 + 段续扫，逐行对应 zSegStep。"""

    def __init__(self):
        self.pens = []
        self.sig = [-1, -1, -1]      # [e1, e2, e3] 尾部端点签名（用 k 当身份）
        self.segs = []               # 已确认段（只增）
        self.i = 0                   # 扫描位置 = 上一段 endPen + 1
        self.born = 0
        self.n_reset = 0

    def step(self, seq):
        M = len(seq)
        e1 = _k(seq[M - 1]) if M >= 1 else -1
        e2 = _k(seq[M - 2]) if M >= 2 else -1
        e3 = _k(seq[M - 3]) if M >= 3 else -1
        penCount = M - 1 if M >= 1 else 0
        branch = 0
        if penCount != len(self.pens) or e1 != self.sig[0] or e2 != self.sig[1] or e3 != self.sig[2]:
            if penCount == len(self.pens) + 1 and e2 == self.sig[0] and e3 == self.sig[1]:
                self.pens.append(_pen_of(seq[penCount - 1], seq[penCount]))          # 守卫 1
                branch = 1
            elif penCount == len(self.pens) and penCount > 0 and e2 == self.sig[1]:
                # 守卫 2（尾端点被换）：只重摊最后一笔，但**段扫描状态也要重置** ——
                # 换的是最后那根笔，会翻动 openingOverlaps(penCount-3..penCount-1) 那几格的判词，
                # 而已经跳过去的位置（skip）不会再回来问 ⇒ 缓存段 stale。所以这里照守卫 3 整段重算。
                self.pens = _flatten(seq)
                self.segs = []
                self.i = 0
                self.born = 0
                self.n_reset += 1
                branch = 2
            else:
                self.pens = _flatten(seq)                                            # 守卫 3
                self.segs = []
                self.i = 0
                self.born = 0
                self.n_reset += 1
                branch = 3
            self.sig = [e1, e2, e3]
        # 段续扫（镜像 zSegStep 内层 / IncSegments.feed）
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
        self.i = i
        self.born = born
        return branch

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
    p3 = PineSeg3()
    if max_bars:
        bars = bars[:max_bars]
    nbad = 0
    first = None
    for k in range(len(bars)):
        inc_k.push(bars[k]["h"], bars[k]["l"])
        std, fx = inc_k.snapshot()
        g.update(std, fx)
        seq = g.seq
        p3.step(seq)
        if len(seq) < 3:
            continue
        want = build_segments(_flatten(seq), mode=FEAT_STD_A)
        got = p3.result()
        if want != got:
            nbad += 1
            if first is None:
                first = (k + 1, want, got)
    return dict(name=name, bars=len(bars), nbad=nbad, first=first, n_reset=p3.n_reset)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-bars", type=int, default=None)
    ap.add_argument("--random", type=int, default=200)
    a = ap.parse_args()

    t0 = time.time()
    print("── ③ 整条流水线：增量(笔同步+段续扫) == 整段 build_segments ──")
    print("  口径：每根拿真实 `Guarded` 的 seq，跑 zSegStep 的 Python 版，跟整段重算逐字段对账。\n")

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
        any_bad |= bool(st["nbad"])
        mark = "" if not st["nbad"] else "   ★★★ 分歧"
        print("  %-20s 根 %6d | 整段重算 %3d 次 | 分歧 %3d%s"
              % (fn, st["bars"], st["n_reset"], st["nbad"], mark))
        if st["first"]:
            k, want, got = st["first"]
            print("        → 首处分歧 @第 %d 根" % k)
            print("          整段 want: %s" % want[:3])
            print("          增量 got : %s" % got[:3])

    print("\n  ── 随机行情（压深处回改）──")
    rng = random.Random(20261002)
    rand_bad = 0
    rand_bars_total = 0
    for t in range(a.random):
        tick = rng.choice((0.1, 0.25, 0.5, 1.0, 2.0))
        n = rng.randint(40, 500)
        bars = rand_bars(rng, n, tick)
        st = probe(bars, tick, "rand#%d" % t)
        rand_bars_total += st["bars"]
        if st["nbad"]:
            rand_bad += 1
            any_bad = True
            print("  ✗ 随机 #%d 分歧 %d 处（@第 %d 根）" % (t, st["nbad"], st["first"][0] if st["first"] else -1))
    print("  ✓ %d 条随机序列（%d 根）跑完，分歧 %d 处" % (a.random, rand_bars_total, rand_bad))

    print("\n  真实 %d 根 + 随机 %d 根 | 分歧 %s | 用时 %.0fs"
          % (total_bars, rand_bars_total, "有" if any_bad else "0", time.time() - t0))
    if any_bad:
        print("⇒ **分歧**：增量流水线在深处回改时跟整段重算对不上。")
        return 1
    print("⇒ 0 分歧：增量（三路同步 + 段续扫）在真实 fix_start 深处回改下，逐根 == 整段。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
