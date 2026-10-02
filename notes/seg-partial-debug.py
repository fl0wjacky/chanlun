# -*- coding: utf-8 -*-
"""看 partial 在 zec_1h 首处分歧 @1433 到底差在哪：branch / seg_i / 整段 vs partial 全量。

只跑 zec_1h 到 1433 根，把 partial 每次触发「尾换/缩深」时的状态打出来，定位首处分歧。
"""
import importlib.util
import json
import io
import os
import sys

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
build_segments = rc.build_segments
FEAT_STD_A = rc.FEAT_STD_A
_flatten = rc._flatten
_k = rc._k


def run():
    fn = os.path.join(ROOT, "data", "zec_1h.json")
    b = json.load(io.open(fn, encoding="utf-8"))
    bars = b["bars"] if isinstance(b, dict) else b

    inc_k = IncKline()
    g = Guarded("old", 4)
    eng = SegEngine("partial")
    stop = 1433
    for k in range(stop):
        inc_k.push(bars[k]["h"], bars[k]["l"])
        std, fx = inc_k.snapshot()
        g.update(std, fx)
        seq = g.seq
        M = len(seq)
        e1 = _k(seq[M - 1]) if M >= 1 else -1
        e2 = _k(seq[M - 2]) if M >= 2 else -1
        e3 = _k(seq[M - 3]) if M >= 3 else -1
        penCount = M - 1 if M >= 1 else 0
        # 判断这一根触发了哪一路
        branch = "noop"
        if penCount != len(eng.pens) or e1 != eng.sig[0] or e2 != eng.sig[1] or e3 != eng.sig[2]:
            if penCount == len(eng.pens) + 1 and e2 == eng.sig[0] and e3 == eng.sig[1]:
                branch = "append"
            elif penCount == len(eng.pens) and penCount > 0 and e2 == eng.sig[1]:
                branch = "tail"
            else:
                branch = "reset"
        prev_i, prev_born = eng.i, eng.born
        eng.step(seq)
        if len(seq) < 3:
            continue
        want = build_segments(_flatten(seq), mode=FEAT_STD_A)
        got = eng.result()
        if want != got:
            print("★ 首处分歧 @第 %d 根  branch=%s  penCount=%d  (seg_i %d->%d, born %d->%d)"
                  % (k + 1, branch, penCount, prev_i, eng.i, prev_born, eng.born))
            print("  seq 端点 k 值：%s" % [f["k"] for f in seq])
            print("  ── 整段 build_segments (want) ──")
            for s in want:
                print("    PI0=%d PI1=%d dir=%s case=%d live=%s npens=%d"
                      % (s["PI0"], s["PI1"], s["dir"], s.get("case"), s.get("live"), s["npens"]))
            print("  ── partial (got) ──")
            for s in got:
                print("    PI0=%d PI1=%d dir=%s case=%d live=%s npens=%d"
                      % (s["PI0"], s["PI1"], s["dir"], s.get("case"), s.get("live"), s["npens"]))
            return
    print("没在 %d 根内找到分歧" % stop)


if __name__ == "__main__":
    run()
