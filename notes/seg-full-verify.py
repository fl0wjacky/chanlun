# -*- coding: utf-8 -*-
"""③「full（非纯追加一律整段重算）」在全量数据（含 zec15 的 20160 根）上逐根对账。

之前的 seg-sync-deepfix-probe 跑的是 --max-bars 5000 的口径，zec15 实际 20160 根、
penCount 能长到 1100+，那段没验过。这里只跑 full 一支（对账 build_segments），
全量不截断，补上 zec15 的尾巴。只跑 full，省掉 old/partial 两支，跑得快些。

用法：python3 notes/seg-full-verify.py [--random K] [--only zec15]
"""
import argparse
import importlib.util
import json
import io
import os
import random
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

SP = os.path.join(HERE, "seg-reset-cost-probe.py")
spec = importlib.util.spec_from_file_location("rc", SP)
rc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rc)
SegEngine = rc.SegEngine
Guarded = rc.Guarded
IncKline = rc.IncKline
rand_bars = rc.rand_bars
tick_of_soft = rc.tick_of_soft
build_segments = rc.build_segments
FEAT_STD_A = rc.FEAT_STD_A
_flatten = rc._flatten

SKIP = ("annot", "mag", "sub")


def probe(bars, tick, name, only_full=True):
    inc_k = IncKline()
    g = Guarded("old", 4)
    eng = SegEngine("full")
    nbad = 0
    first = None
    t = time.time()
    for k in range(len(bars)):
        inc_k.push(bars[k]["h"], bars[k]["l"])
        std, fx = inc_k.snapshot()
        g.update(std, fx)
        seq = g.seq
        eng.step(seq)
        if len(seq) < 3:
            continue
        want = build_segments(_flatten(seq), mode=FEAT_STD_A)
        if eng.result() != want:
            nbad += 1
            if first is None:
                first = (k + 1, want, eng.result())
        if (k + 1) % 2000 == 0:
            print("    %s @%d 根，分歧 %d，%.0fs" % (name, k + 1, nbad, time.time() - t), flush=True)
    return nbad, first


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--random", type=int, default=60)
    ap.add_argument("--only", type=str, default=None)
    a = ap.parse_args()

    files = [f for f in sorted(os.listdir(os.path.join(ROOT, "data")))
             if f.endswith(".json") and not any(x in f for x in SKIP)]
    if a.only:
        files = [f for f in files if a.only in f]

    def load(fn):
        b = json.load(io.open(os.path.join(ROOT, "data", fn), encoding="utf-8"))
        if isinstance(b, dict):
            b = b.get("bars") or b.get("klines") or b
        return b or []

    cache = {fn: load(fn) for fn in files}
    files.sort(key=lambda fn: len(cache[fn]))
    print("── ③ full 全量逐根对账（含 zec15 20160 根）──", flush=True)
    any_bad = False
    for fn in files:
        bars = cache[fn]
        if not bars:
            continue
        try:
            tick = tick_of_soft(fn)
        except Exception:                       # noqa: BLE001
            tick = None
        nbad, first = probe(bars, tick, fn)
        any_bad |= bool(nbad)
        print("  %-18s 根 %6d | 分歧 %d%s" % (fn, len(bars), nbad, "" if not nbad else "  ★★★"), flush=True)
        if first:
            k, want, got = first
            print("    → 首处 @%d 根" % k, flush=True)
            print("      want: %s" % (want[:4],), flush=True)
            print("      got : %s" % (got[:4],), flush=True)

    rng = random.Random(20261002)
    rand_bad = 0
    rand_total = 0
    for t in range(a.random):
        tick = rng.choice((0.1, 0.25, 0.5, 1.0, 2.0))
        n = rng.randint(40, 500)
        bars = rand_bars(rng, n, tick)
        nbad, first = probe(bars, tick, "rand#%d" % t)
        rand_total += len(bars)
        if nbad:
            rand_bad += 1
            any_bad = True
            print("  ✗ 随机 #%d 分歧 %d（@%d）" % (t, nbad, first[0] if first else -1), flush=True)
    print("  随机 %d 条（%d 根）分歧 %d" % (a.random, rand_total, rand_bad), flush=True)
    print("⇒ %s" % ("** 有分歧 **" if any_bad else "full 全量 0 分歧"), flush=True)
    return 1 if any_bad else 0


if __name__ == "__main__":
    sys.exit(main())
