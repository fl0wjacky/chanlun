# -*- coding: utf-8 -*-
"""量：线段层「上一层」只取合成过的（nmerge>1）会改掉多少信号？（临时实验，只读）"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import importlib
S = importlib.import_module("core.signals")
from core.analyze import analyze_file
from core.extend import build_hierarchy

FILES = ["zec15.json", "zec_1h.json", "zec_4h.json", "btc_4h.json",
         "aaplusdt_4h.json", "aaplusdt_30m.json"]

ORIG = S._higher_centers


def filt(r, level):
    if level == "pen":
        return r["seg_centers"]                      # 笔层不动
    done = [s for s in r["segs"] if not s.get("live")]
    H = build_hierarchy(r["seg_centers"], done) if r["seg_centers"] else []
    return [c for c in H if c.get("nmerge", 1) > 1]  # 只取真合成过的


def dump(r, level):
    return {(s["kind"], s["bar"]) for s in S.signals(r, level, "macd")}


tot_o = tot_f = 0
for level in ("pen", "seg"):
    for fn in FILES:
        r = analyze_file(fn)
        S._higher_centers = ORIG
        a = dump(r, level)
        S._higher_centers = filt
        b = dump(r, level)
        tot_o += len(a); tot_f += len(b)
        if a != b:
            print("  %-18s %s  只取合成后 多出/少掉：+%s -%s"
                  % (fn, level, sorted(b - a), sorted(a - b)))
S._higher_centers = ORIG
print("现口径 全部信号 %d ｜ 线段层只取合成过的 %d ⇒ 差 %d" % (tot_o, tot_f, tot_f - tot_o))
