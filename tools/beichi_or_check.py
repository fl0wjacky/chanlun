#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""「面积或黄白线」（macd_or_lines，spec 背驰.md 六.3）的两条恒等式 + 计数表。

    python3 tools/beichi_or_check.py              # rc=0 才算过
    python3 tools/beichi_or_check.py --self-test  # 三条变异必须各自红

  ① 并集恒等：同一份数据、同一层，「或」发的一类点 ＝「面积」∪「黄白线」，逐点相等（kind、bar）；
  ② 标记恒等：打了 std 的一类点 ＝「面积」∩「黄白线」；
  ③ 交付要列的数（spec 六.4）：每种看法在 9 份数据上各出多少个一类点、跟默认（面积）的交集多少。
另外核：默认（macd）的输出身上没有 std 这个键（默认逐位不变）。
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core import analyze_file                                 # noqa: E402
import core.signals                                           # noqa: E402,F401
S = sys.modules["core.signals"]

DATA = ("aaplusdt_4h.json", "aaplusdt_2h.json", "aaplusdt_1h.json", "aaplusdt_30m.json", "btc_4h.json",
        "zec_4h.json", "zec_2h.json", "zec_1h.json", "zec15.json")
FIRST = ("一买", "一卖")
_R = {}


def first_kind(sig):
    return {(g["kind"], g["bar"]) for g in sig if g["kind"] in FIRST}


def check(quiet=False):
    bad, rows = [], []
    for fn in DATA:
        r = _R.setdefault(fn, analyze_file(fn))
        for lv in ("pen", "seg"):
            got = {m: S.signals(r, lv, m) for m in S.MEASURES}
            area, lines, orr = (first_kind(got[m]) for m in ("macd", "lines", "macd_or_lines"))
            std = {(g["kind"], g["bar"]) for g in got["macd_or_lines"] if g["kind"] in FIRST and g.get("std")}
            if orr != area | lines:
                bad.append("%s %s 并集不等：多 %s 少 %s" % (fn, lv, sorted(orr - (area | lines))[:3],
                                                         sorted((area | lines) - orr)[:3]))
            if std != area & lines:
                bad.append("%s %s 标记不等：多 %s 少 %s" % (fn, lv, sorted(std - (area & lines))[:3],
                                                         sorted((area & lines) - std)[:3]))
            if any("std" in g for g in got["macd"]):
                bad.append("%s %s 默认面积的输出身上多了 std" % (fn, lv))
            rows.append((fn, lv, {m: (len(first_kind(got[m])), len(first_kind(got[m]) & area)) for m in S.MEASURES},
                         len(std)))
    if not quiet:
        print("一类点个数（跟默认面积的交集）· 9 份 × 两层")
        print("%-18s %-3s " % ("数据", "层") + " ".join("%-14s" % m for m in S.MEASURES) + " std")
        for fn, lv, d, nstd in rows:
            print("%-18s %-3s " % (fn, lv) + " ".join("%-14s" % ("%d（∩%d）" % d[m]) for m in S.MEASURES)
                  + " %d" % nstd)
        for b in bad:
            print("✗ " + b)
        print("全部通过" if not bad else "%d 处不过" % len(bad))
    return len(bad)


def self_test():
    """或→且 ／ std 打成「任一」／ 「或」里黄白线方向反了 —— 各自必须红。"""
    arms = []
    real = S._diverges

    def or_to_and(A, C, want_down, data, measure, ratio):
        if measure == "macd_or_lines":
            return all(real(A, C, want_down, data[m], m, ratio) for m in S.OR_PARTS)
        return real(A, C, want_down, data, measure, ratio)
    arms.append(("或 写成 且", or_to_and))

    real_sig = S.signals

    def sig_std_any(r, level="seg", measure="macd", *a, **k):
        out = real_sig(r, level, measure, *a, **k)
        if measure == "macd_or_lines":
            for g in out:
                if g["kind"] in FIRST:
                    g["std"] = True
        return out
    arms.append(("std 一律打上", None))

    def lines_flip(A, C, want_down, data, measure, ratio):
        if measure == "macd_or_lines":
            return (real(A, C, want_down, data["macd"], "macd", ratio)
                    or real(A, C, not want_down, data["lines"], "lines", ratio))
        return real(A, C, want_down, data, measure, ratio)
    arms.append(("「或」里黄白线方向反了", lines_flip))

    miss = 0
    for name, f in arms:
        if f is None:
            S.signals = sig_std_any
        else:
            S._diverges = f
        try:
            n = check(quiet=True)
        finally:
            S._diverges, S.signals = real, real_sig
        print("%s 变异 %-16s ⇒ %d 处不过" % ("✓" if n else "✗", name, n))
        miss += 0 if n else 1
    return 3 if miss else 0


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else (1 if check() else 0))
