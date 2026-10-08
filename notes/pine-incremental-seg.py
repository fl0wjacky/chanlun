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
import core.segment as SG                                           # noqa: E402

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


# ── Pine 的镜像：buildSegments（整段）和 zSegStep（逐根续扫）共用这一份扫描 ──────────────────
# ★ 10-08 重写（card-7a451eef-1e2）：旧版有三处跟 Pine／引擎对不上，42 处分歧全是它自己的口径 ——
#   ① born 不管第几种情况都取 at（引擎 `born = at if case == 1`，Pine `res := cse == 1 ? at : 0`）—— 39 处；
#   ② 没有图头两条修法（HEAD_DIR_FIX／HEAD_EXT_FIX；Pine 是 segs.size() == 0 时那两个 else if）；
#   ③ 拿增量去比 B 模式 —— B 的已确认段前缀本来就不稳（aaplusdt_30m 第 28 笔撤 (11,15)），Pine 在 B 下走整段
#      （chanlun.pine `segs = featModeB ? buildSegments(pens) : array.copy(zSegs)`）—— 3 处。
#   另认 S7 的 case 3（暂定）：不进只增的缓存、扫描位置不动、之后不再往下切（Pine zSegTent）。
BORN_CASE1_ONLY = True        # 只给 --self-test 的臂关：born 退回旧写法（第二种情况的 at 也当 born）
KNOW_TENTATIVE = True         # 只给 --self-test 的臂关：不认 case 3（暂定当成已确认段缓存起来）


def _scan(pens, i, born, have_segs, mode, memo):
    """从 (i, born) 起往后扫，照 Pine 的内层循环。→ (新确认的段, i, born, 暂定 (PI0, PI1) 或 None)。"""
    n, out, tent = len(pens), [], None
    while i + 2 < n:
        if not _opening_overlaps(pens, i):
            i += 1
            continue
        d = _dir(pens[i])
        k = i + 2
        while k < born:
            k += 2
        found = None
        while k < n - 1:
            case, res = _case_at(pens, i, k, d, mode, memo)
            if case:
                found = (k, case, res)
                break
            k += 2
            if res is not None:
                while k < res:
                    k += 2
        if found is None:
            break
        e, case, at = found
        first = not have_segs and not out
        if first and SG.HEAD_DIR_FIX and ((d == "down" and pens[e]["p1"] >= pens[i]["p0"]) or
                                          (d == "up" and pens[e]["p1"] <= pens[i]["p0"])):
            i, born = i + 1, 0
            continue
        if first and SG.HEAD_EXT_FIX and SG._start_check(dict(
                dir=d, PI0=i, PI1=e, p0=pens[i]["p0"],
                hi=max(pens[q]["hi"] for q in range(i, e + 1)),
                lo=min(pens[q]["lo"] for q in range(i, e + 1))), pens, mode, memo,
                cutoff=max(e + 1, at or 0) if SG.HEAD_EXT_CUTOFF else None) == "bad":
            i, born = i + 1, 0
            continue
        if case == 3 and KNOW_TENTATIVE:
            tent = (i, e)
            break
        born = (at or 0) if (case in (1, 3) or not BORN_CASE1_ONLY) else 0
        out.append(_mk_seg(pens, i, e, case, d))
        i = e + 1
    return out, i, born, tent


def _assemble(pens, segs, i, tent):
    out = list(segs)
    n = len(pens)
    if tent is not None:
        s = _mk_seg(pens, tent[0], tent[1], 3, _dir(pens[tent[0]]))
        s.update(tentative=True, live=True)
        out.append(s)
        i = tent[1] + 1
    if n - i >= 3:
        out.append(_mk_live(pens, i, n, _dir(pens[i])))
    return out


def whole(pens, mode):
    """Pine buildSegments 的镜像（B 模式在 Pine 里只走这条）。"""
    segs, i, _, tent = _scan(pens, 0, 0, False, mode, {})
    return _assemble(pens, segs, i, tent)


class IncSegments:
    """Pine zSegStep 的镜像（A 模式）：只存 (i, born) 和只增的已确认段；暂定每次续扫重算、不进缓存。"""
    def __init__(self, mode=FEAT_STD_A):
        self.mode, self.pens, self.segs, self.i, self.born, self.tent = mode, [], [], 0, 0, None

    def feed(self, pen):
        self.pens.append(pen)
        new, self.i, self.born, self.tent = _scan(self.pens, self.i, self.born, bool(self.segs), self.mode, {})
        self.segs += new
        return self

    def result(self):
        return _assemble(self.pens, self.segs, self.i, self.tent)


def check_series(pens, mode=FEAT_STD_A, stop_at=3, tail=None):
    """A：每个前缀上 增量 vs 整段引擎。B：整段镜像 vs 整段引擎（全长 ＋ 每 10 笔一个前缀）。→ (查了几个, 分歧)。"""
    fails, checked = [], 0
    if mode == FEAT_STD_A:
        inc = IncSegments(mode)
        lo = 3 if tail is None else max(3, len(pens) - tail + 1)   # 快档：增量照常从头喂，只在最后 tail 个前缀上跟整段对照
        for k in range(1, len(pens) + 1):
            inc.feed(pens[k - 1])
            if k < lo:
                continue
            checked += 1
            want = build_segments(pens[:k], mode=mode)
            got = inc.result()
            if want != got:
                fails.append((k, want, got))
                if len(fails) >= stop_at:
                    break
    else:
        ks = set(range(10, len(pens) + 1, 10)) | {len(pens)}
        if tail is not None:
            ks = {k for k in ks if k > len(pens) - tail}
        for k in sorted(ks):
            if k < 3:
                continue
            checked += 1
            want, got = build_segments(pens[:k], mode=mode), whole(pens[:k], mode)
            if want != got:
                fails.append((k, want, got))
                if len(fails) >= stop_at:
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
    """正臂（Nova 10-08 16:06 定的牙）：
      ① born 退回旧写法（第二种情况的 at 也当 born）⇒ A 模式必须红；
      ② 不认 case 3（暂定当成已确认段缓存）⇒ 有暂定的那张（data/aaplusdt_2h.json）必须红。"""
    global BORN_CASE1_ONLY, KNOW_TENTATIVE
    data = dict(load_real())
    ok = True
    BORN_CASE1_ONLY = False
    try:
        red = [fn for fn, bars in data.items() if check_series(analyze(bars)["pens"], FEAT_STD_A, 1)[1]]
    finally:
        BORN_CASE1_ONLY = True
    print("  %s 臂 ① born 退回旧写法 ⇒ 红 %d 份 %s" % ("✓" if red else "✗", len(red), red[:3]))
    ok &= bool(red)
    KNOW_TENTATIVE = False
    try:
        fn = "aaplusdt_2h.json"
        red2 = bool(check_series(analyze(data[fn])["pens"], FEAT_STD_A, 1)[1]) if fn in data else False
    finally:
        KNOW_TENTATIVE = True
    print("  %s 臂 ② 不认暂定（case 3）⇒ %s %s" % ("✓" if red2 else "✗", fn, "红" if red2 else "没红"))
    ok &= red2
    if not ok:
        print("★ 正臂没红 ⇒ 这把尺不算数（exit=3）")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--impl", default="Incremental", choices=["Incremental", "Whole"])
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--random", type=int, default=0)
    ap.add_argument("--tail", type=int, default=None, help="快档：每张图只对照最后 N 个前缀（predeploy 用 200）")
    ap.add_argument("--snap", default=None, help="另加一份本地快照（json.gz：{'<品种> <周期>': {'bars': [...]}}），不进仓")
    a = ap.parse_args()

    if a.self_test:
        return 0 if self_test() else 3

    data = load_real()
    if not data:
        print("★ data/ 里一份 K 线都没有 ⇒ 跑不动")
        return 2
    if a.snap:
        import gzip
        snap = json.loads(gzip.open(a.snap).read())
        data += [("快照 " + k, snap[k]["bars"]) for k in sorted(snap)]

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
                checked, fails = check_series(pens, mode, tail=a.tail)
            total_checked += checked
            for k, want, got in fails:
                total_fails.append((fn, mode, k, want, got))
            tag = "✓" if not fails else "✗ 分歧 %d 处" % len(fails)
            print("  %-18s %s 笔 %4d  %s %4d  %s" % (fn, "A" if mode == FEAT_STD_A else "B", len(pens),
                                                   "前缀" if mode == FEAT_STD_A else "B 整段核", checked, tag))

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
    print("✓ A：每个前缀上 增量 == 整段；B：整段镜像 == 引擎。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
