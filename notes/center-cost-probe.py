# -*- coding: utf-8 -*-
"""④ 决策前提：在最后一根上把「类中枢 / 线段中枢 / 大级别」从头算一遍要多久。

Nova 要的数：zec15 全量养到最后一根（pens 最多 ~1135），islast 上整段重算
    centers      = find_centers(pens)
    big          = build_hierarchy(centers, pens)
    seg_centers  = find_centers([s for s in segs if not live])
三者各自的单根耗时。目的是判断 ④ 要不要做成逐根增量 —— 若整段算本来就便宜，
就留在最后一根整段算，省掉一整套增量 + 对账。

口径：只测 ④ 这三段（笔/线段已按 ③ 逐根增量，不算它们的成本）。timeit 多遍取稳定值。
"""
import io
import json
import os
import sys
import timeit

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from core.analyze import analyze_file                      # noqa: E402
from core.center import find_centers                       # noqa: E402
from core.extend import build_hierarchy                    # noqa: E402


def main():
    r = analyze_file("zec15.json")
    pens = r["pens"]
    segs = r["segs"]
    done_segs = [s for s in segs if not s.get("live")]
    print("zec15 全量：pens=%d  centers=%d  big=%d  segs=%d(完成 %d)  seg_centers=%d"
          % (len(pens), len(r["centers"]), len(r["big"]),
             len(segs), len(done_segs), len(r["seg_centers"])))

    def centers_only():
        return find_centers(pens)

    def big_only():
        return build_hierarchy(r["centers"], pens)

    def segc_only():
        return find_centers(done_segs)

    for name, fn in (("类中枢 find_centers(pens)", centers_only),
                     ("大级别 build_hierarchy(centers,pens)", big_only),
                     ("线段中枢 find_centers(完成segs)", segc_only)):
        n = 200
        t = timeit.timeit(fn, number=n)
        print("%-32s %8.3f ms/根  (%d 遍)" % (name, t / n * 1000, n))

    # 三样一起（islast 上真正要付的）
    def all_three():
        c = find_centers(pens)
        b = build_hierarchy(c, pens)
        s = find_centers(done_segs)
        return c, b, s

    n = 200
    t = timeit.timeit(all_three, number=n)
    print("%-32s %8.3f ms/根  (%d 遍)" % ("三样合计", t / n * 1000, n))


if __name__ == "__main__":
    main()
