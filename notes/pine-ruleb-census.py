# -*- coding: utf-8 -*-
"""规则 B 三档普查：**在哪些数据上、哪一档看得见**（只读）。

给「改后应该看到什么」一个可核的数字 —— 拿 TradingView 对照的人（nova / 小栋）得先知道
在哪份数据上看哪一档，不然只能自己猜，或者看了半天看不到差别以为没生效。

口径与 render/full_common.py 的 box_split() 一致（也就是 pine 现在写的那三档）：
    ① 前三笔（段）里夹着「还没走完」的那一员 ⇒ 整框虚线（笔层＝最后一根笔；线段层没有这一员）
    ② 中枢已结束（not live）                   ⇒ 整框实线
    ③ 中枢仍在延续（live）                     ⇒ 拆两截（前三实线、延续虚线）
★ 只有 live 的中枢才看得出①②③的差别（已结束的一律实线）；一份数据里没有 live 中枢，
  规则 B 在它上面就画不出差别 —— 那种数据只能验配色，不能验虚实。

    python3 notes/pine-ruleb-census.py
"""
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import data                                              # noqa: E402
from core.analyze import analyze_file                                # noqa: E402


def census(fn):
    r = analyze_file(fn)
    pens = r["pens"]
    done = [s for s in r["segs"] if not s.get("live")]
    out = []
    for name, cs, host, uj in (("类中枢", r["centers"], pens, len(pens) - 1),
                               ("线段中枢", r["seg_centers"], done, None)):
        t = {"①": 0, "②": 0, "③": 0, "live": 0}
        for z in cs:
            j0 = z["PI0"]
            if z.get("live"):
                t["live"] += 1
            if uj is not None and j0 <= uj < min(j0 + 3, len(host)):
                t["①"] += 1
            elif not z.get("live"):
                t["②"] += 1
            else:
                t["③"] += 1
        out.append((name, len(cs), t))
    return out, len(pens), len(r["segs"]), len(done)


def main():
    for fn in sorted(os.path.basename(p) for p in glob.glob(data("*.json"))):
        try:
            out, npens, nsegs, ndone = census(fn)
        except Exception as e:
            print("跳过 %-18s（%s: %s）" % (fn, type(e).__name__, str(e)[:50]))
            continue
        print("%-18s 笔 %4d ｜ 段 %3d（完成 %3d）" % (fn, npens, nsegs, ndone))
        for name, total, t in out:
            print("    %-5s 共 %3d ｜ ①整框虚线 %3d ｜ ②整框实线 %3d ｜ ③拆两截 %3d ｜ live %d"
                  % (name, total, t["①"], t["②"], t["③"], t["live"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
