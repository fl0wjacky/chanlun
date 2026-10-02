# -*- coding: utf-8 -*-
"""⑤ 决策前提：买卖点（signals）在最后一根上从头算一遍要多久。

Nova 要的数：⑤ 要按 K 线算 MACD 柱面积，扫的是 K 线不是笔，可能比中枢（④ 才 4.5ms）重。
口径：只测 ⑤ 自己（MACD + beichi 判定），不含 ①②③④（那些要么已增量、要么 4.5ms）。
timeit 多遍取稳定值。zec15 全量 20160 根。
"""
import os
import sys
import timeit

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from core.analyze import analyze_file                      # noqa: E402
from core.signals import signals, macd_hist                # noqa: E402


def main():
    r = analyze_file("zec15.json")
    bars = r["bars"]
    print("zec15 全量：bars=%d  pens=%d  seg_centers=%d  centers=%d"
          % (len(bars), len(r["pens"]), len(r["seg_centers"]), len(r["centers"])))

    def macd_only():
        return macd_hist(bars)

    def sig_seg():
        return signals(r, level="seg")                     # 线段中枢（正规）

    def sig_pen():
        return signals(r, level="pen")                     # 类中枢（对照）

    for name, fn in (("MACD hist(bars) O(20160)", macd_only),
                     ("买卖点 signals(seg)", sig_seg),
                     ("买卖点 signals(pen)", sig_pen)):
        n = 20 if fn is not macd_only else 50
        t = timeit.timeit(fn, number=n)
        print("%-28s %8.2f ms/根  (%d 遍)" % (name, t / n * 1000, n))

    # 完整一根：MACD + signals(seg)（islast 上真正要付的）
    def full():
        h = macd_hist(bars)
        return signals(r, level="seg")

    n = 20
    t = timeit.timeit(full, number=n)
    print("%-28s %8.2f ms/根  (%d 遍)" % ("⑤ 合计(MACD+signals seg)", t / n * 1000, n))


if __name__ == "__main__":
    main()
