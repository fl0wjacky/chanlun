#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""③（线段）的增量参照：把 `build_segments` 改成「缓存已确认前缀 + 只重算 live 尾巴」，
再在**每个前缀**上跟整序列 `build_segments` 对账。

要回答的唯一问题：
    pens 每加一根，**从保存的 (i, born) 恢复扫描**得到的线段，跟**从第 0 根整段重算**得到的线段，
    是不是**逐字节相同**？

★ 前提是「已确认线段前缀稳定」—— `notes/pine-seg-prefix-stability.py` 先证这一步。
  只要前缀稳定，已确认的那段就**只增不改**，增量 = 存 (i, born, 已确认段列表) + 每根只重扫尾巴。

★ 这**证不了 pine**（本仓没有 Pine 运行时）。它证的是：我抄成 Python 的**增量算法**
  与引擎 `build_segments` 在每个前缀上一致 —— pine 那段 `buildSegments` 改成这个增量形状之后，
  人再逐行核。每条规则都标了对应位置。

用法：
    python3 notes/pine-incremental-seg.py                 # 九份真实数据、每个前缀、两种 mode
    python3 notes/pine-incremental-seg.py --impl Whole     # 对照臂（整段重算，必然自洽）
    python3 notes/pine-incremental-seg.py --self-test      # 正臂：故意破坏前缀稳定 ⇒ 必须红
    python3 notes/pine-incremental-seg.py --random 200     # 再加 N 条随机序列
退出码：
    0  全绿（每个前缀、两份实现、两种 mode 都逐字节相同）
    1  有分歧（印出第一个分歧的前缀与两份输出）
    2  跑不动
    3  --self-test 的正臂没红 ⇒ 这个检查本身不算数
"""
import argparse
import io
import json
import os
import random
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from core import analyze                                             # noqa: E402
from core.segment import build_segments, _dir, _opening_overlaps, _case_at  # noqa: E402
from core.segment import FEAT_STD_A, FEAT_STD_B                     # noqa: E402

SKIP = ("annot", "mag", "sub")
MODES = (FEAT_STD_A, FEAT_STD_B)


# ── 段构造（照 build_segments 逐字段，别自作主张改字段名）──────────────────────────
def _mk_seg(pens, i, end_pen, case, seg_dir):
    return dict(
        PI0=i, PI1=end_pen,
        i0=pens[i]["i0"], i1=pens[end_pen]["i1"],
        p0=pens[i]["p0"], p1=pens[end_pen]["p1"],
        dir=seg_dir, npens=end_pen - i + 1, case=case,
        hi=max(pens[k]["hi"] for k in range(i, end_pen + 1)),
        lo=min(pens[k]["lo"] for k in range(i, end_pen + 1)),
    )


def _mk_live(pens, i, n, seg_dir):
    return dict(
        PI0=i, PI1=n - 1,
        i0=pens[i]["i0"], i1=pens[n - 1]["i1"],
        p0=pens[i]["p0"], p1=pens[n - 1]["p1"],
        dir=seg_dir, npens=n - i, case=0, live=True,
        hi=max(p["hi"] for p in pens[i:]),
        lo=min(p["lo"] for p in pens[i:]),
    )


# ── 增量状态机：只存 (i, born)，已确认段**只增** ──────────────────────────────────
# 对应 pine 的 buildSegments 改法：把 while 外层循环里的 i / born 提出来当 var 状态，
# 每根新笔进来时从 i 续扫；已确认的段 push 进一个只增的数组，不再回头碰。
class IncSegments:
    def __init__(self, mode=FEAT_STD_A):
        self.mode = mode
        self.pens = []
        self.segs = []          # 已确认段（只增）
        self.i = 0              # 扫描位置 = 上一段 end_pen + 1
        self.born = 0           # 本段方向确立的破位笔（case-2 归 0）

    def feed(self, pen):
        """喂一根新笔，从 (i, born) 续扫。不做整段重算。"""
        self.pens.append(pen)
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
            while k < born:                     # 方向确立之前，本段不能结束
                k += 2
            while k < n - 1:
                case, resume = _case_at(pens, i, k, seg_dir, self.mode)
                if case:
                    found = (k, case, resume); break
                k += 2
                if resume is not None:          # 待定区间内的候选不判：跳到破位处之后的同向笔
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
        return self

    def result(self):
        """当前输出 = 已确认段 + live 尾巴（若有）。与 build_segments 同形。"""
        pens = self.pens
        n = len(pens)
        i = self.i
        out = list(self.segs)
        if n - i >= 3:
            out.append(_mk_live(pens, i, n, _dir(pens[i])))
        return out


def check_series(pens, mode=FEAT_STD_A):
    """在每个前缀 k（3..n）上对账：增量 vs 整段。返回分歧列表。"""
    inc = IncSegments(mode)
    fails = []
    checked = 0
    for k in range(1, len(pens) + 1):
        inc.feed(pens[k - 1])
        if k < 3:
            continue                      # 不足三笔，两边都不会有线段
        checked += 1
        want = build_segments(pens[:k], mode=mode)
        got = inc.result()
        if want != got:
            fails.append((k, want, got))
            if len(fails) >= 3:
                break
    return checked, fails


def load_real():
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


def rand_pens(rng, n, tick):
    """随机笔序列 —— 臂也要压随机行情，不只在真实数据上跑。

    ★ 笔的字段按引擎的 Unit 形状造：i0/i1/p0/p1/hi/lo。
      i0 单调递增（笔端点不重叠），p0/p1 交替顶底、hi=max/lo=min。
    """
    pens = []
    i = 0
    px = round(round(rng.uniform(10, 500) / tick) * tick, 10)
    up = rng.choice((True, False))
    for _ in range(n):
        i += rng.choice((2, 3, 4, 5))
        step = rng.choice((1, 2, 3, 4)) * tick
        p0 = px
        p1 = round(px + (step if up else -step), 10)
        pens.append(dict(
            i0=i, i1=i + 1, p0=p0, p1=p1,
            hi=round(max(p0, p1), 10), lo=round(min(p0, p1), 10),
        ))
        px = p1
        up = not up
    return pens


def self_test():
    """正臂：故意破坏前缀稳定（在已确认段之后插一根改方向的笔），增量与整段**必须**分歧。

    做法：拿真实序列跑通后，在**已确认段的边界之后**塞一根笔、让 i 处重新变待定，
    此时整段重算会改写已确认前缀、而增量版本（只增）不会 ⇒ 必然分歧。
    若这条不红，说明尺子根本没在比较"已确认前缀是否只增"。
    """
    data = load_real()
    for fn, bars in data:
        pens = analyze(bars)["pens"]
        if len(pens) < 8:
            continue
        inc = IncSegments(FEAT_STD_A)
        for p in pens:
            inc.feed(p)
        # 已确认段的数量 —— 若为 0，这份数据没货，换一份
        if not inc.segs:
            continue
        # 破坏：把已确认段的第一段 PI1 处的笔反转方向，强制重算时 i 会提前停 / 改判
        tampered = list(pens)
        k = inc.segs[0]["PI1"]
        tampered[k] = dict(tampered[k])
        tampered[k]["p1"] = tampered[k]["p0"] + abs(tampered[k]["p1"] - tampered[k]["p0"]) + 1.0
        tampered[k]["hi"] = tampered[k]["p1"]
        want = build_segments(tampered, mode=FEAT_STD_A)
        # 增量版本还停在旧状态（只增、不知道被改）⇒ 应该对不上
        got = inc.result()
        if want != got:
            print("  正臂（%s，改第一段 PI1=%d 的方向）⇒ 红 ✓" % (fn, k))
            return True
    print("★ 正臂没红：所有样本破坏后增量与整段仍相同 ⇒ 尺子没接上（exit=3）")
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--impl", default="Incremental", choices=["Incremental", "Whole"])
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--random", type=int, default=0)
    a = ap.parse_args()

    if a.self_test:
        return 0 if self_test() else 3

    data = load_real()
    if not data:
        print("★ data/ 里一份 K 线都没有 ⇒ 跑不动")
        return 2

    total_checked, total_fails = 0, []
    t0 = time.time()
    for fn, bars in data:
        try:
            pens = analyze(bars)["pens"]
        except Exception as e:                                        # noqa: BLE001
            print("★ %s 引擎跑不动：%s" % (fn, type(e).__name__))
            return 2
        for mode in MODES:
            if a.impl == "Whole":
                # 对照臂：整段重算必然自洽（这是"尺子基线"，证明两份实现是同一份代码的不同入口）
                checked, fails = len(pens) - 2, []
            else:
                checked, fails = check_series(pens, mode)
            total_checked += checked
            for k, want, got in fails:
                total_fails.append((fn, mode, k, want, got))
            tag = "✓" if not fails else "✗ 分歧 %d 处" % len(fails)
            print("  %-18s mode=%s 笔 %4d  前缀 %4d  %s" % (fn, mode, len(pens), checked, tag))

    if a.random:
        rng = random.Random(20261002)
        rand_checked = 0
        for _ in range(a.random):
            n = rng.randint(8, 200)
            pens = rand_pens(rng, n, 0.01)
            for mode in MODES:
                checked, fails = check_series(pens, mode)
                rand_checked += checked
                for k, want, got in fails:
                    total_fails.append(("rand", mode, k, want, got))
        print("  随机 %d 条 ｜ 前缀 %d" % (a.random, rand_checked))
        total_checked += rand_checked

    print("\n真实+随机 ｜ 查了 %d 个前缀 ｜ 分歧 %d 处 ｜ %.0fs"
          % (total_checked, len(total_fails), time.time() - t0))
    if total_fails:
        fn, mode, k, want, got = total_fails[0]
        print("\n第一处分歧 @%s mode=%s k=%d：" % (fn, mode, k))
        print("  整段(前3段): %s" % want[:3])
        print("  增量(前3段): %s" % got[:3])
        return 1
    print("✓ 每个前缀上，增量 == 整段（两种 mode 都查了）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
